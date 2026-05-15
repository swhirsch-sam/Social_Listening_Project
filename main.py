#!/usr/bin/env python3
"""
Social Listening - Brand Sentiment Analyzer
"""
import json
import time

import anthropic
from apify_client import ApifyClient
from firecrawl import FirecrawlApp

import config


def fetch_tiktok(brand):
    if not config.ENABLE_TIKTOK:
        return []
    client = ApifyClient(config.APIFY_API_KEY)
    results = []
    try:
        run_input = {"keywords": [brand], "maxItems": config.APIFY_MAX_RESULTS}
        run = client.actor(config.APIFY_TIKTOK_ACTOR).call(run_input=run_input)
        for item in client.dataset(run["defaultDatasetId"]).iterate_items():
            results.append({
                "platform": "TikTok",
                "author": (item.get("authorMeta") or {}).get("name") or item.get("author", ""),
                "content": item.get("text") or item.get("comment") or "",
                "url": item.get("webVideoUrl") or item.get("url") or "",
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
        run_input = {"keywords": [brand], "maxItems": config.APIFY_MAX_RESULTS}
        run = client.actor(config.APIFY_LINKEDIN_ACTOR).call(run_input=run_input)
        for item in client.dataset(run["defaultDatasetId"]).iterate_items():
            results.append({
                "platform": "LinkedIn",
                "author": item.get("author") or item.get("authorName") or "",
                "content": item.get("text") or item.get("content") or "",
                "url": item.get("url") or item.get("postUrl") or "",
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
        response = app.search(
            f"{brand} brand reviews opinions",
            limit=config.FIRECRAWL_MAX_RESULTS
        )
        items = response if isinstance(response, list) else response.get("data", [])
        for item in items:
            content = item.get("markdown") or item.get("content") or item.get("description") or ""
            if content:
                results.append({
                    "platform": "Web/News",
                    "author": item.get("source") or item.get("url") or "",
                    "content": content[:500],
                    "url": item.get("url") or "",
                })
    except Exception as e:
        print(f"[Firecrawl] Error: {e}")
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
            print(f"[Claude] Error: {e}")
            results.append({**post, "sentiment": "neutral"})
    return results


def run_analysis(brand):
    all_posts = []
    all_posts.extend(fetch_tiktok(brand))
    all_posts.extend(fetch_linkedin(brand))
    all_posts.extend(fetch_web_news(brand))

    if not all_posts:
        return {"error": f"No data found for '{brand}' across all sources."}

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
    }
