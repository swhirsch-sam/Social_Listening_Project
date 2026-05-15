#!/usr/bin/env python3
"""
Social Listening - Brand Sentiment Analyzer
"""
import json
import re
import time
import datetime

import anthropic
from apify_client import ApifyClient
from firecrawl import FirecrawlApp

import config


def is_2026(date_str):
    if not date_str:
        return False
    try:
        for fmt in ["%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%dT%H:%M:%SZ",
                    "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"]:
            try:
                dt = datetime.datetime.strptime(str(date_str)[:19], fmt[:19])
                return dt.year == 2026
            except ValueError:
                continue
        return bool(re.search(r'\b2026\b', str(date_str)))
    except Exception:
        return False


def fetch_tiktok(brand):
    if not config.ENABLE_TIKTOK:
        return []
    client = ApifyClient(config.APIFY_API_KEY)
    results = []
    try:
        run_input = {"keywords": [brand], "maxItems": config.APIFY_MAX_RESULTS}
        run = client.actor(config.APIFY_TIKTOK_ACTOR).call(run_input=run_input)
        for item in client.dataset(run["defaultDatasetId"]).iterate_items():
            date_str = (item.get("createTime") or item.get("createdAt") or item.get("date") or "")
            if not is_2026(str(date_str)):
                continue
            results.append({
                "platform": "TikTok",
                "author": (item.get("authorMeta") or {}).get("name") or item.get("author", ""),
                "content": item.get("text") or item.get("comment") or "",
                "url": item.get("webVideoUrl") or item.get("url") or "",
                "date": str(date_str),
            })
    except Exception as e:
        print(f"[TikTok] Error: {e}")
    return results


def fetch_linkedin(brand):
    if not config.ENABLE_LINKEDIN:
        return []
    client = ApifyClient(config.APIFY_API_KEY)
    results = []
    try:
        run_input = {"keywords": brand, "maxResults": config.APIFY_MAX_RESULTS}
        run = client.actor(config.APIFY_LINKEDIN_ACTOR).call(run_input=run_input)
        for item in client.dataset(run["defaultDatasetId"]).iterate_items():
            date_str = (item.get("postedAt") or item.get("date") or item.get("publishedAt") or "")
            if not is_2026(str(date_str)):
                continue
            results.append({
                "platform": "LinkedIn",
                "author": item.get("authorName") or item.get("author") or "",
                "content": item.get("text") or item.get("content") or "",
                "url": item.get("url") or item.get("postUrl") or "",
                "date": str(date_str),
            })
    except Exception as e:
        print(f"[LinkedIn] Error: {e}")
    return results


def fetch_web_news(brand):
    if not config.ENABLE_FIRECRAWL:
        return []
    app = FirecrawlApp(api_key=config.FIRECRAWL_API_KEY)
    results = []
    try:
        search_results = app.search(query=f"{brand} 2026", limit=config.FIRECRAWL_MAX_RESULTS)
        items = (search_results if isinstance(search_results, list) else search_results.get("data", []))
        for item in items:
            meta = item.get("metadata") or {}
            date_str = (meta.get("publishedDate") or meta.get("date") or item.get("publishedDate") or item.get("date") or "")
            content = (item.get("markdown") or item.get("content") or item.get("description") or "")
            if date_str and not is_2026(str(date_str)):
                if "2026" not in content:
                    continue
            results.append({
                "platform": "Web/News",
                "author": meta.get("author") or item.get("author") or "",
                "content": content[:1000],
                "url": item.get("url") or meta.get("sourceURL") or "",
                "date": str(date_str),
            })
    except Exception as e:
        print(f"[Web/News] Error: {e}")
    return results


def analyze_sentiment(item, brand):
    client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
    prompt = (
        f'You are a brand sentiment analyst. Analyze the following content about "{brand}".\n\n'
        f'Platform: {item["platform"]}\nContent: {item["content"]}\n\n'
        'Respond in JSON only: {"sentiment": "positive|neutral|negative", "confidence": 0.0-1.0, "reason": "one sentence"}'
    )
    try:
        message = client.messages.create(
            model=config.CLAUDE_MODEL,
            max_tokens=200,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = message.content[0].text.strip()
        json_match = re.search(r'\{.*\}', raw, re.DOTALL)
        if json_match:
            result = json.loads(json_match.group())
            return {**item, **result}
    except Exception as e:
        print(f"[Claude] Error: {e}")
    return {**item, "sentiment": "neutral", "confidence": 0.0, "reason": "Analysis failed"}


def run_analysis(brand):
    brand = brand.strip()
    all_items = []
    all_items.extend(fetch_tiktok(brand))
    all_items.extend(fetch_linkedin(brand))
    all_items.extend(fetch_web_news(brand))

    if not all_items:
        return {
            "brand": brand,
            "total_posts": 0,
            "sentiment_summary": {"positive": 0, "neutral": 0, "negative": 0},
            "overall_sentiment": "neutral",
            "confidence": 0.0,
            "posts": [],
            "error": "No 2026 data found for this brand across all sources.",
        }

    analyzed = []
    for item in all_items:
        result = analyze_sentiment(item, brand)
        analyzed.append(result)
        time.sleep(config.CLAUDE_DELAY_SECONDS)

    counts = {"positive": 0, "neutral": 0, "negative": 0}
    for item in analyzed:
        s = item.get("sentiment", "neutral").lower()
        if s in counts:
            counts[s] += 1

    total = len(analyzed)
    overall = max(counts, key=counts.get)
    avg_conf = sum(item.get("confidence", 0.0) for item in analyzed) / total if total > 0 else 0.0

    return {
        "brand": brand,
        "total_posts": total,
        "sentiment_summary": counts,
        "overall_sentiment": overall,
        "confidence": round(avg_conf, 2),
        "posts": analyzed,
        "error": None,
    }
