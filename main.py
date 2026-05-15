#!/usr/bin/env python3
"""
Social Listening - Brand Sentiment Analyzer
"""
import time

import anthropic
from apify_client import ApifyClient
from firecrawl import FirecrawlApp

import config

source_warnings = []


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
        run = client.actor("clockworks/tiktok-scraper").call(
            run_input=run_input,
            max_items=config.APIFY_MAX_RESULTS,
        )
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
            "keywords": brand,
            "maxItems": config.APIFY_MAX_RESULTS,
        }
        run = client.actor("harvestapi/linkedin-post-search").call(run_input=run_input)
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
    return results


def fetch_web_news(brand):
    global source_warnings
    if not config.ENABLE_FIRECRAWL:
        return []
    app = FirecrawlApp(api_key=config.FIRECRAWL_API_KEY)
    results = []
    try:
        response = app.search(query=f"{brand} brand sentiment reviews opinions", limit=config.FIRECRAWL_MAX_RESULTS)
        # Handle both dict response and SearchData object
        if hasattr(response, "data"):
            items = response.data
        elif isinstance(response, dict):
            items = response.get("data", [])
        elif isinstance(response, list):
            items = response
        else:
            items = []
        for item in items:
            # item may be a dict or an object with attributes
            if hasattr(item, "__dict__"):
                item = item.__dict__
            content = (
                item.get("markdown") or
                item.get("content") or
                item.get("description") or
                item.get("snippet") or
                item.get("extract") or ""
            )
            url = item.get("url") or item.get("sourceURL") or ""
            if content:
                results.append({
                    "platform": "Web/News",
                    "author": url,
                    "content": content[:500],
                    "url": url,
                })
    except Exception as e:
        source_warnings.append(f"Web/News: {e}")
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

    all_posts = []
    all_posts.extend(fetch_tiktok(brand))
    all_posts.extend(fetch_linkedin(brand))
    all_posts.extend(fetch_web_news(brand))

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
