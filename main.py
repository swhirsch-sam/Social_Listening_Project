#!/usr/bin/env python3
"""
Social Listening MVP - Brand Mention Tracker
============================================
Sources
  - Apify: futurizerush/tiktok-comment-scraper
  - Apify: supreme_coder/linkedin-post
  - Firecrawl: web/news search

Pipeline
  1. Fetch brand mentions from each source
  2. Send each post to Claude for sentiment + key topics
  3. Append results to Google Sheets

Config: edit config.py before running.
"""
import json
import re
import time
import datetime

import anthropic
import gspread
from google.oauth2.service_account import Credentials
from apify_client import ApifyClient
from firecrawl import FirecrawlApp

import config


# ── Google Sheets ─────────────────────────────────────────────────────────────

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

HEADERS = [
    "Timestamp",
    "Source",
    "Platform",
    "Author",
    "Content",
    "Sentiment",
    "Confidence",
    "Key Topics",
    "URL",
    "Raw JSON",
]


def get_sheet():
    """Authenticate with Google Sheets and return the first worksheet.

    Writes the header row if the sheet is empty.
    """
    creds = Credentials.from_service_account_file(
        config.GOOGLE_CREDENTIALS_FILE, scopes=SCOPES
    )
    client = gspread.authorize(creds)
    sheet = client.open_by_key(config.GOOGLE_SHEET_ID).sheet1
    if not sheet.row_values(1):
        sheet.append_row(HEADERS)
    return sheet


# ── Claude sentiment analysis ────────────────────────────────────────────────

def analyse_sentiment(text):
    """Send *text* to Claude; return a dict with sentiment, confidence, topics.

    Returns
    -------
    dict
        {
            "sentiment":  "positive" | "negative" | "neutral",
            "confidence": "high" | "medium" | "low",
            "topics":     ["topic1", "topic2", ...],   # up to 5
        }
    """
    if not text or not text.strip():
        return {"sentiment": "neutral", "confidence": "low", "topics": []}

    claude = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)

    prompt = (
        "Analyse the following social-media post or article excerpt for brand/product sentiment.\n\n"
        "Return a JSON object with exactly these keys:\n"
        '  "sentiment"  : one of "positive", "negative", or "neutral"\n'
        '  "confidence" : one of "high", "medium", or "low"\n'
        '  "topics"     : a JSON array of up to 5 short key-topic strings\n\n'
        "Post/excerpt:\n\"\"\"\n"
        f"{text[:3000]}\n\"\"\"\n\n"
        "Respond with raw JSON only — no markdown fences, no extra text."
    )

    message = claude.messages.create(
        model=config.CLAUDE_MODEL,
        max_tokens=256,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = message.content[0].text.strip()
    # Strip accidental markdown code fences
    raw = re.sub(r"^```[a-z]*\s*", "", raw, flags=re.MULTILINE)
    raw = re.sub(r"```\s*$", "", raw, flags=re.MULTILINE).strip()

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {
            "sentiment": "neutral",
            "confidence": "low",
            "topics": [],
            "parse_error": raw,
        }


# ── Apify: TikTok comment scraper ────────────────────────────────────────────

def fetch_tiktok_comments():
    """Run the Apify TikTok comment scraper and return normalised items."""
    print(f"[Apify/TikTok] keywords: {config.BRAND_KEYWORDS}")
    apify = ApifyClient(config.APIFY_API_KEY)
    run_input = {
        "searchQueries": config.BRAND_KEYWORDS,
        "resultsPerPage": config.APIFY_MAX_RESULTS,
        "maxItems": config.APIFY_MAX_RESULTS,
    }
    run = apify.actor(config.APIFY_TIKTOK_ACTOR).call(run_input=run_input)
    items = []
    for item in apify.dataset(run["defaultDatasetId"]).iterate_items():
        text = (
            item.get("text")
            or item.get("commentText")
            or item.get("content")
            or ""
        )
        items.append(
            {
                "source": "apify",
                "platform": "tiktok",
                "author": (
                    (item.get("authorMeta") or {}).get("name")
                    or item.get("uniqueId")
                    or ""
                ),
                "content": text,
                "url": item.get("webVideoUrl") or item.get("url") or "",
                "raw": str(item)[:300],
            }
        )
    print(f"[Apify/TikTok] {len(items)} items fetched")
    return items


# ── Apify: LinkedIn post scraper ──────────────────────────────────────────────

def fetch_linkedin_posts():
    """Run the Apify LinkedIn post scraper and return normalised items."""
    print(f"[Apify/LinkedIn] keywords: {config.BRAND_KEYWORDS}")
    apify = ApifyClient(config.APIFY_API_KEY)
    run_input = {
        "searchQuery": " OR ".join(config.BRAND_KEYWORDS),
        "maxResults": config.APIFY_MAX_RESULTS,
    }
    run = apify.actor(config.APIFY_LINKEDIN_ACTOR).call(run_input=run_input)
    items = []
    for item in apify.dataset(run["defaultDatasetId"]).iterate_items():
        text = (
            item.get("text")
            or item.get("content")
            or item.get("description")
            or ""
        )
        items.append(
            {
                "source": "apify",
                "platform": "linkedin",
                "author": (
                    (item.get("author") or {}).get("name")
                    or item.get("authorName")
                    or ""
                ),
                "content": text,
                "url": item.get("url") or item.get("postUrl") or "",
                "raw": str(item)[:300],
            }
        )
    print(f"[Apify/LinkedIn] {len(items)} items fetched")
    return items


# ── Firecrawl: web/news search ───────────────────────────────────────────────

def fetch_firecrawl_mentions():
    """Use Firecrawl to search web/news for every brand keyword."""
    print(f"[Firecrawl] keywords: {config.BRAND_KEYWORDS}")
    fc = FirecrawlApp(api_key=config.FIRECRAWL_API_KEY)
    items = []
    for kw in config.BRAND_KEYWORDS:
        try:
            results = fc.search(
                query=kw,
                params={
                    "limit": config.FIRECRAWL_MAX_RESULTS,
                    "scrapeOptions": {"formats": ["markdown"]},
                },
            )
            # Firecrawl can return a dict with a "data" key or a list directly
            if isinstance(results, dict):
                data = results.get("data") or []
            elif isinstance(results, list):
                data = results
            else:
                data = []

            for r in data:
                content = (
                    r.get("markdown")
                    or r.get("content")
                    or r.get("description")
                    or r.get("snippet")
                    or ""
                )
                items.append(
                    {
                        "source": "firecrawl",
                        "platform": "web/news",
                        "author": r.get("author") or r.get("siteName") or "",
                        "content": content,
                        "url": r.get("url") or r.get("sourceURL") or "",
                        "raw": str(r)[:300],
                    }
                )
        except Exception as exc:
            print(f"[Firecrawl] Error for keyword '{kw}': {exc}")

    print(f"[Firecrawl] {len(items)} items fetched")
    return items


# ── Google Sheets writer ──────────────────────────────────────────────────────

def write_to_sheet(sheet, item, analysis):
    """Append one row to the Google Sheet."""
    topics_str = ", ".join(analysis.get("topics") or [])
    row = [
        datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
        item["source"],
        item["platform"],
        item["author"],
        item["content"][:500],        # cap cell length
        analysis.get("sentiment", ""),
        analysis.get("confidence", ""),
        topics_str,
        item["url"],
        item["raw"],
    ]
    sheet.append_row(row, value_input_option="USER_ENTERED")


# ── Main orchestrator ─────────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("Social Listening MVP — starting run")
    print("=" * 60)

    sheet = get_sheet()

    all_items = []
    if config.ENABLE_TIKTOK:
        all_items += fetch_tiktok_comments()
    if config.ENABLE_LINKEDIN:
        all_items += fetch_linkedin_posts()
    if config.ENABLE_FIRECRAWL:
        all_items += fetch_firecrawl_mentions()

    total = len(all_items)
    print(f"\nTotal items collected: {total}")
    if total == 0:
        print("No items found. Check your BRAND_KEYWORDS in config.py.")
        return

    print("\nRunning sentiment analysis...\n")
    analysed = 0
    skipped = 0

    for i, item in enumerate(all_items, 1):
        if not item["content"].strip():
            print(f"  [{i}/{total}] SKIP  — empty content ({item['platform']})")
            skipped += 1
            continue

        label = (item["author"] or "(unknown)")[:35]
        print(f"  [{i}/{total}] {item['platform']:<10} {label:<36}", end="", flush=True)

        analysis = analyse_sentiment(item["content"])
        sentiment = analysis.get("sentiment", "?")
        confidence = analysis.get("confidence", "?")
        topics_preview = ", ".join((analysis.get("topics") or [])[:3])
        print(f"  {sentiment} ({confidence})  |  {topics_preview}")

        write_to_sheet(sheet, item, analysis)
        analysed += 1
        time.sleep(config.CLAUDE_DELAY_SECONDS)

    print("\n" + "=" * 60)
    print(f"Run complete")
    print(f"  Analysed : {analysed}")
    print(f"  Skipped  : {skipped}")
    print(f"  Sheet ID : {config.GOOGLE_SHEET_ID}")
    print("=" * 60)


if __name__ == "__main__":
    main()
