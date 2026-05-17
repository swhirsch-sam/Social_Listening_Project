#!/usr/bin/env python3
"""
Social Listening - Brand Sentiment Analyzer
"""
import time

import anthropic
from apify_client import ApifyClient

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
        run_input = {
            "searchQueries": [brand],
            "resultsPerPage": config.APIFY_MAX_RESULTS,
            "searchSection": "/video",
        }
        _log(f"TikTok: starting Apify run for '{brand}' (max {config.APIFY_MAX_RESULTS})")
        run = client.actor(config.APIFY_TIKTOK_ACTOR).call(
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
        run_input = {
            "searchQueries": [brand],
            "maxPosts": config.APIFY_MAX_RESULTS,
        }
        _log(f"LinkedIn: starting Apify run for '{brand}' (max {config.APIFY_MAX_RESULTS})")
        run = client.actor(config.APIFY_LINKEDIN_ACTOR).call(
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


def fetch_instagram(brand):
    """Pull Instagram posts mentioning the brand via apify/instagram-scraper (hashtag search)."""
    global source_warnings
    if not config.ENABLE_INSTAGRAM:
        return []
    client = ApifyClient(config.APIFY_API_KEY)
    results = []
    try:
        # Use the brand name as a hashtag-style search; strip spaces for hashtag compatibility.
        hashtag = brand.replace(" ", "").lower()
        run_input = {
            "search": hashtag,
            "searchType": "hashtag",
            "searchLimit": 1,
            "resultsType": "posts",
            "resultsLimit": config.APIFY_MAX_RESULTS,
        }
        _log(f"Instagram: starting Apify run for '#{hashtag}' (max {config.APIFY_MAX_RESULTS})")
        run = client.actor(config.APIFY_INSTAGRAM_ACTOR).call(
            run_input=run_input,
            max_items=config.APIFY_MAX_RESULTS,
            wait_secs=600,
        )
        _log(f"Instagram: Apify run finished (datasetId={run.get('defaultDatasetId')}); reading items...")
        for item in client.dataset(run["defaultDatasetId"]).iterate_items():
            text = item.get("caption") or item.get("text") or ""
            if text:
                results.append({
                    "platform": "Instagram",
                    "author": item.get("ownerUsername") or item.get("ownerFullName") or "",
                    "content": text,
                    "url": item.get("url") or item.get("displayUrl") or "",
                })
    except Exception as e:
        source_warnings.append(f"Instagram: {e}")
        _log(f"Instagram: ERROR {e}")
    _log(f"Instagram: collected {len(results)} items")
    return results


def fetch_twitter(brand):
    """Pull tweets mentioning the brand via xquik/x-tweet-scraper (keyword search)."""
    global source_warnings
    if not config.ENABLE_TWITTER:
        return []
    client = ApifyClient(config.APIFY_API_KEY)
    results = []
    try:
        run_input = {
            "searchTerms": [brand],
            "maxItems": config.APIFY_MAX_RESULTS,
        }
        _log(f"Twitter/X: starting Apify run for '{brand}' (max {config.APIFY_MAX_RESULTS})")
        run = client.actor(config.APIFY_TWITTER_ACTOR).call(
            run_input=run_input,
            max_items=config.APIFY_MAX_RESULTS,
            wait_secs=600,
        )
        _log(f"Twitter/X: Apify run finished (datasetId={run.get('defaultDatasetId')}); reading items...")
        for item in client.dataset(run["defaultDatasetId"]).iterate_items():
            text = item.get("text") or item.get("fullText") or item.get("content") or ""
            if text:
                author = (
                    (item.get("user") or {}).get("userName")
                    or (item.get("author") or {}).get("userName")
                    or item.get("username")
                    or ""
                )
                results.append({
                    "platform": "Twitter/X",
                    "author": author,
                    "content": text,
                    "url": item.get("url") or item.get("twitterUrl") or "",
                })
    except Exception as e:
        source_warnings.append(f"Twitter/X: {e}")
        _log(f"Twitter/X: ERROR {e}")
    _log(f"Twitter/X: collected {len(results)} items")
    return results


def fetch_reddit(brand):
    """Pull Reddit posts mentioning the brand via automation-lab/reddit-scraper (keyword search)."""
    global source_warnings
    if not config.ENABLE_REDDIT:
        return []
    client = ApifyClient(config.APIFY_API_KEY)
    results = []
    try:
        run_input = {
            "searchQuery": brand,
            "maxPostsPerSource": config.APIFY_MAX_RESULTS,
        }
        _log(f"Reddit: starting Apify run for '{brand}' (max {config.APIFY_MAX_RESULTS})")
        run = client.actor(config.APIFY_REDDIT_ACTOR).call(
            run_input=run_input,
            max_items=config.APIFY_MAX_RESULTS,
            wait_secs=600,
        )
        _log(f"Reddit: Apify run finished (datasetId={run.get('defaultDatasetId')}); reading items...")
        for item in client.dataset(run["defaultDatasetId"]).iterate_items():
            title = item.get("title") or ""
            body = item.get("body") or item.get("selftext") or item.get("text") or ""
            text = (title + " " + body).strip()
            if text:
                results.append({
                    "platform": "Reddit",
                    "author": item.get("author") or item.get("username") or "",
                    "content": text,
                    "url": item.get("url") or item.get("permalink") or "",
                })
    except Exception as e:
        source_warnings.append(f"Reddit: {e}")
        _log(f"Reddit: ERROR {e}")
    _log(f"Reddit: collected {len(results)} items")
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
    _log("Step 1/5: TikTok")
    all_posts.extend(fetch_tiktok(brand))
    _log("Step 2/5: LinkedIn")
    all_posts.extend(fetch_linkedin(brand))
    _log("Step 3/5: Instagram")
    all_posts.extend(fetch_instagram(brand))
    _log("Step 4/5: Twitter/X")
    all_posts.extend(fetch_twitter(brand))
    _log("Step 5/5: Reddit")
    all_posts.extend(fetch_reddit(brand))
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
