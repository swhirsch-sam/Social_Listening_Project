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


def _log(msg):
    """Print a timestamped progress line (visible in terminal + Streamlit logs)."""
    import sys
    ts = time.strftime("%H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)
    sys.stdout.flush()


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
    global source_warnings
    if not config.ENABLE_FIRECRAWL:
        return []
    # Support both old (FirecrawlApp) and new (Firecrawl) SDK class names
    try:
        from firecrawl import Firecrawl as _FirecrawlCls
    except ImportError:
        _FirecrawlCls = FirecrawlApp
    app = _FirecrawlCls(api_key=config.FIRECRAWL_API_KEY)
    results = []
    seen_urls = set()

    # Firecrawl /search caps a single request near 100 results, so issue
    # several varied queries and dedupe by URL to reach the configured total.
    queries = [
        f"{brand} brand sentiment",
        f"{brand} reviews",
        f"{brand} opinions",
        f"{brand} complaints",
        f"{brand} press",
    ]
    per_query_limit = min(100, max(1, config.FIRECRAWL_MAX_RESULTS // len(queries) + 5))

    def _extract_items(response):
        # New SDK: response.data is dict with keys web/news/images
        data = getattr(response, "data", None)
        if data is None and isinstance(response, dict):
            data = response.get("data", response)
        if data is None:
            return []
        if isinstance(data, dict):
            out = []
            for key in ("web", "news", "images"):
                vals = data.get(key)
                if isinstance(vals, list):
                    out.extend(vals)
            if not out and "data" in data and isinstance(data["data"], list):
                out = data["data"]
            return out
        if isinstance(data, list):
            return data
        return []

    for q in queries:
        if len(results) >= config.FIRECRAWL_MAX_RESULTS:
            break
        try:
            _log(f"Firecrawl: searching '{q}' (limit {per_query_limit}, have {len(results)})")
            response = app.search(query=q, limit=per_query_limit)
            for item in _extract_items(response):
                if hasattr(item, "__dict__"):
                    item = item.__dict__
                url = item.get("url") or item.get("sourceURL") or ""
                if not url or url in seen_urls:
                    continue
                seen_urls.add(url)
                content = (
                    item.get("markdown") or
                    item.get("content") or
                    item.get("description") or
                    item.get("snippet") or
                    item.get("extract") or ""
                )
                if not content:
                    continue
                results.append({
                    "platform": "Web/News",
                    "author": url,
                    "content": content[:500],
                    "url": url,
                })
                if len(results) >= config.FIRECRAWL_MAX_RESULTS:
                    break
        except Exception as e:
            source_warnings.append(f"Web/News ('{q}'): {e}")
            _log(f"Firecrawl: ERROR on '{q}': {e}")
    _log(f"Firecrawl: collected {len(results)} items")
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
