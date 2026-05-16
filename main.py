#!/usr/bin/env python3
"""
Social Listening - Brand Sentiment Analyzer
"""
import time

import anthropic
from apify_client import ApifyClient
# Web search now uses Serper (https://serper.dev) instead of Firecrawl.
import json
import requests

import config

source_warnings = []


# Optional UI callback so a Streamlit app can render progress live.
# When set via set_log_callback(fn), every _log() call also invokes fn(line).
_log_callback = None


def set_log_callback(fn):
    """Register a function(str) to receive each progress log line. Pass None to clear."""
    global _log_callback
    _log_callback = fn


def _log(msg):
    """Print a timestamped progress line (visible in terminal + any registered UI callback)."""
    import sys
    ts = time.strftime("%H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    sys.stdout.flush()
    cb = _log_callback
    if cb is not None:
        try:
            cb(line)
        except Exception:
            # Never let UI logging break the pipeline
            pass


def fetch_tiktok(brand):
    global source_warnings
    if not config.ENABLE_TIKTOK:
        return []
    client = ApifyClient(config.APIFY_API_KEY)
    results = []
    try:
        # clockworks/tiktok-scraper supports keyword search
        run_input = {
            "searchQueries": [brand],
            "resultsPerPage": config.APIFY_MAX_RESULTS,
            "searchSection": "/video",
        }
        _log(f"TikTok: starting Apify run for '{brand}' (max {config.APIFY_MAX_RESULTS})")
        run = client.actor("clockworks/tiktok-scraper").call(
            run_input=run_input,
            max_items=config.APIFY_MAX_RESULTS,
            wait_secs=600,
        )
        _log(f"TikTok: Apify run finished (datasetId={run.get('defaultDatasetId')}); reading items...")
        for item in client.dataset(run["defaultDatasetId"]).iterate_items():
            text = item.get("text") or item.get("description") or item.get("title") or ""
            if text:
                results.append({
                    "platform": "TikTok",
                    "author": (item.get("authorMeta") or {}).get("name") or item.get("author", ""),
                    "content": text,
                    "url": item.get("webVideoUrl") or item.get("url") or "",
                })
    except Exception as e:
        source_warnings.append(f"TikTok: {e}")
        _log(f"TikTok: ERROR {e}")
    _log(f"TikTok: collected {len(results)} items")
    return results


def fetch_linkedin(brand):
    global source_warnings
    if not config.ENABLE_LINKEDIN:
        return []
    client = ApifyClient(config.APIFY_API_KEY)
    results = []
    try:
        # harvestapi/linkedin-post-search supports keyword search
        run_input = {
            "searchQueries": [brand],
            "maxPosts": config.APIFY_MAX_RESULTS,
        }
        _log(f"LinkedIn: starting Apify run for '{brand}' (max {config.APIFY_MAX_RESULTS})")
        run = client.actor("harvestapi/linkedin-post-search").call(
            run_input=run_input,
            max_items=config.APIFY_MAX_RESULTS,
            wait_secs=600,
        )
        _log(f"LinkedIn: Apify run finished (datasetId={run.get('defaultDatasetId')}); reading items...")
        for item in client.dataset(run["defaultDatasetId"]).iterate_items():
            text = item.get("text") or item.get("content") or item.get("commentary") or ""
            if text:
                results.append({
                    "platform": "LinkedIn",
                    "author": item.get("author") or item.get("authorName") or item.get("actorName") or "",
                    "content": text,
                    "url": item.get("url") or item.get("postUrl") or "",
                })
    except Exception as e:
        source_warnings.append(f"LinkedIn: {e}")
        _log(f"LinkedIn: ERROR {e}")
    _log(f"LinkedIn: collected {len(results)} items")
    return results


def fetch_web_news(brand):
    """Pull web/news mentions of the brand via Serper (Google Search API).

    Up to config.FIRECRAWL_MAX_RESULTS (hard-capped at 250) items are returned,
    aggregated across several brand-related queries and deduped by URL.
    """
    global source_warnings
    if not config.ENABLE_FIRECRAWL:
        return []

    api_key = getattr(config, "SERPER_API_KEY", "") or ""
    if not api_key:
        source_warnings.append("Web/News: SERPER_API_KEY is empty (set it in your environment)")
        _log("Serper: ERROR SERPER_API_KEY is empty")
        return []

    # Hard cap at 250 even if config says higher.
    overall_cap = min(250, max(1, int(getattr(config, "FIRECRAWL_MAX_RESULTS", 250))))

    queries = [
        f"{brand} brand sentiment",
        f"{brand} reviews",
        f"{brand} opinions",
        f"{brand} complaints",
        f"{brand} press",
    ]
    # Serper allows up to 100 per request; we'll be modest to spread queries.
    per_query = min(100, max(10, overall_cap // len(queries) + 5))

    results = []
    seen_urls = set()
    endpoints = [
        ("https://google.serper.dev/search", "web"),    # organic web results
        ("https://google.serper.dev/news", "news"),     # news results
    ]

    headers = {
        "X-API-KEY": api_key,
        "Content-Type": "application/json",
    }

    for q in queries:
        if len(results) >= overall_cap:
            break
        for url, kind in endpoints:
            if len(results) >= overall_cap:
                break
            try:
                _log(f"Serper: {kind} search '{q}' (limit {per_query}, have {len(results)})")
                payload = {"q": q, "num": per_query}
                resp = requests.post(url, headers=headers, data=json.dumps(payload), timeout=20)
                if resp.status_code != 200:
                    source_warnings.append(
                        f"Web/News ('{q}' {kind}): HTTP {resp.status_code}: {resp.text[:200]}"
                    )
                    _log(f"Serper: ERROR HTTP {resp.status_code} for '{q}' ({kind})")
                    continue
                data = resp.json()
                # Serper /search returns 'organic' for web results; /news returns 'news'.
                items = data.get("organic") or data.get("news") or []
                _log(f"Serper: '{q}' ({kind}) returned {len(items)} items")
                for item in items:
                    if len(results) >= overall_cap:
                        break
                    link = item.get("link") or ""
                    if not link or link in seen_urls:
                        continue
                    seen_urls.add(link)
                    title = item.get("title") or ""
                    snippet = item.get("snippet") or item.get("description") or ""
                    content_parts = [p for p in (title, snippet) if p]
                    if not content_parts:
                        continue
                    content = " — ".join(content_parts)
                    results.append({
                        "platform": "News" if kind == "news" else "Web",
                        "author": item.get("source") or link,
                        "content": content[:500],
                        "url": link,
                    })
            except Exception as e:
                source_warnings.append(
                    f"Web/News ('{q}' {kind}): {type(e).__name__}: {e}"
                )
                _log(f"Serper: EXCEPTION on '{q}' ({kind}): {type(e).__name__}: {e}")
    _log(f"Serper: collected {len(results)} items")
    return results

def analyze_sentiment(posts):
    client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
    results = []
    for post in posts:
        try:
            time.sleep(config.CLAUDE_DELAY_SECONDS)
            message = client.messages.create(
                model=config.CLAUDE_MODEL,
                max_tokens=100,
                messages=[{
                    "role": "user",
                    "content": (
                        f"Analyze the sentiment of this social media post. "
                        f"Reply with ONLY one word: positive, negative, or neutral.\n\n"
                        f"Post: {post['content'][:300]}"
                    )
                }]
            )
            sentiment = message.content[0].text.strip().lower()
            if sentiment not in ("positive", "negative", "neutral"):
                sentiment = "neutral"
            results.append({**post, "sentiment": sentiment})
        except Exception as e:
            source_warnings.append(f"Claude: {e}")
            results.append({**post, "sentiment": "neutral"})
    return results


def run_analysis(brand):
    global source_warnings
    source_warnings = []
    _log(f"=== run_analysis('{brand}') starting ===")

    all_posts = []
    _log("Step 1/3: TikTok")
    all_posts.extend(fetch_tiktok(brand))
    _log("Step 2/3: LinkedIn")
    all_posts.extend(fetch_linkedin(brand))
    _log("Step 3/3: Firecrawl web/news")
    all_posts.extend(fetch_web_news(brand))
    _log(f"Fetching complete: {len(all_posts)} total posts; running sentiment analysis...")

    if not all_posts:
        warning_detail = " | ".join(source_warnings) if source_warnings else "No content returned from any source."
        return {"error": f"No data found for '{brand}'. Details: {warning_detail}"}

    analyzed = analyze_sentiment(all_posts)

    counts = {"positive": 0, "negative": 0, "neutral": 0}
    for post in analyzed:
        counts[post["sentiment"]] = counts.get(post["sentiment"], 0) + 1

    total = len(analyzed)
    dominant = max(counts, key=counts.get)
    confidence = counts[dominant] / total if total else 0

    return {
        "brand": brand,
        "total_posts": total,
        "overall_sentiment": dominant,
        "confidence": confidence,
        "sentiment_summary": counts,
        "posts": analyzed,
        "warnings": source_warnings,
    }
