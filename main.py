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
    global source_warnings
    if not config.ENABLE_FIRECRAWL:
        return []

    # Support both old (FirecrawlApp, v1.x) and new (Firecrawl, v2+) SDK class names.
    _FirecrawlCls = None
    try:
        from firecrawl import Firecrawl as _FirecrawlCls  # v2+
        _log("Firecrawl: using modern Firecrawl class")
    except ImportError:
        try:
            from firecrawl import FirecrawlApp as _FirecrawlCls  # legacy
            _log("Firecrawl: using legacy FirecrawlApp class")
        except ImportError as e:
            source_warnings.append(f"Web/News: firecrawl import failed: {e}")
            _log(f"Firecrawl: ERROR import failed: {e}")
            return []

    if not config.FIRECRAWL_API_KEY:
        source_warnings.append("Web/News: FIRECRAWL_API_KEY is empty")
        _log("Firecrawl: ERROR FIRECRAWL_API_KEY is empty")
        return []

    try:
        app = _FirecrawlCls(api_key=config.FIRECRAWL_API_KEY)
    except Exception as e:
        source_warnings.append(f"Web/News: client init failed: {e}")
        _log(f"Firecrawl: ERROR client init: {e}")
        return []

    results = []
    seen_urls = set()

    queries = [
        f"{brand} brand sentiment",
        f"{brand} reviews",
        f"{brand} opinions",
        f"{brand} complaints",
        f"{brand} press",
    ]
    # Firecrawl /search caps a single request around 100 results. Stay well under it.
    per_query_limit = min(50, max(1, config.FIRECRAWL_MAX_RESULTS // len(queries) + 5))

    def _coerce_dict(x):
        """Return x as a dict if possible (handles pydantic models / objects with __dict__)."""
        if isinstance(x, dict):
            return x
        if hasattr(x, "model_dump"):
            try:
                return x.model_dump()
            except Exception:
                pass
        if hasattr(x, "dict"):
            try:
                return x.dict()
            except Exception:
                pass
        if hasattr(x, "__dict__"):
            return {k: v for k, v in x.__dict__.items() if not k.startswith("_")}
        return {}

    def _extract_items(response):
        """Pull web/news/images lists out of the search response across SDK versions."""
        # Modern SDK: response itself is dict-like (response.get('web', []))
        # Older SDK: response.data is dict or list
        # Even older: response is dict with key 'data' which is a list
        candidates = []
        # 1) Try direct .get('web') / .get('news') on the response
        if hasattr(response, "get"):
            try:
                for key in ("web", "news", "images"):
                    vals = response.get(key)
                    if isinstance(vals, list):
                        candidates.extend(vals)
            except Exception:
                pass
        # 2) Try response.data
        data = getattr(response, "data", None)
        if data is None and isinstance(response, dict):
            data = response.get("data")
        if data is not None:
            if isinstance(data, dict):
                for key in ("web", "news", "images"):
                    vals = data.get(key)
                    if isinstance(vals, list):
                        candidates.extend(vals)
                # Some old shapes: data is itself the list
                if not candidates and isinstance(data.get("data"), list):
                    candidates.extend(data["data"])
            elif isinstance(data, list):
                candidates.extend(data)
        # 3) Last-ditch: object with .web/.news/.images attributes
        if not candidates:
            for key in ("web", "news", "images"):
                vals = getattr(response, key, None)
                if isinstance(vals, list):
                    candidates.extend(vals)
        return candidates

    for q in queries:
        if len(results) >= config.FIRECRAWL_MAX_RESULTS:
            break
        try:
            _log(f"Firecrawl: searching '{q}' (limit {per_query_limit}, have {len(results)})")
            response = app.search(query=q, limit=per_query_limit)
            items = _extract_items(response)
            _log(f"Firecrawl: response type={type(response).__name__}, items_found={len(items)}")
            for item in items:
                item = _coerce_dict(item)
                url = item.get("url") or item.get("sourceURL") or ""
                if not url or url in seen_urls:
                    continue
                seen_urls.add(url)
                content = (
                    item.get("markdown") or
                    item.get("content") or
                    item.get("description") or
                    item.get("snippet") or
                    item.get("extract") or
                    item.get("title") or ""
                )
                if not content:
                    continue
                results.append({
                    "platform": "Web/News",
                    "author": url,
                    "content": str(content)[:500],
                    "url": url,
                })
                if len(results) >= config.FIRECRAWL_MAX_RESULTS:
                    break
        except Exception as e:
            source_warnings.append(f"Web/News ('{q}'): {type(e).__name__}: {e}")
            _log(f"Firecrawl: ERROR on '{q}': {type(e).__name__}: {e}")
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
