#!/usr/bin/env python3
"""
Social Listening - Brand Sentiment Analyzer
"""

import time
import re
import anthropic
from collections import Counter
from apify_client import ApifyClient
from urllib.parse import quote_plus
import config

source_warnings = []

_log_callback = None


def set_log_callback(fn):
    global _log_callback
    _log_callback = fn


def _log(msg):
    import sys
    ts = time.strftime('%H:%M:%S')
    line = f'[{ts}] {msg}'
    print(line, flush=True)
    sys.stdout.flush()
    if _log_callback is not None:
        try:
            _log_callback(line)
        except Exception:
            pass


_STOP_WORDS = {
    "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "is", "are", "was", "were", "be", "been",
    "being", "have", "has", "had", "do", "does", "did", "will", "would",
    "could", "should", "may", "might", "shall", "can", "not", "no", "nor",
    "so", "yet", "both", "either", "neither", "this", "that", "these",
    "those", "it", "its", "i", "me", "my", "we", "our", "you", "your",
    "he", "she", "they", "them", "their", "what", "which", "who", "when",
    "where", "why", "how", "all", "more", "also", "just", "get", "got",
    "s", "t", "re", "ve", "ll", "d", "m",
}


def _search_query(brand, context):
    """Append context hint to brand so search is more specific."""
    if context and context.strip():
        return f'{brand} {context.strip()}'
    return brand


def extract_top_terms(posts, sentiment, brand, n=3):
    """Return top-n words from posts of a given sentiment."""
    words = []
    brand_lower = brand.lower().split()
    for post in posts:
        if post.get('sentiment') == sentiment:
            text = post.get('content', '')
            tokens = re.findall(r"[a-z']+", text.lower())
            for w in tokens:
                if w not in _STOP_WORDS and w not in brand_lower and len(w) > 2:
                    words.append(w)
    if not words:
        return []
    return [word for word, _ in Counter(words).most_common(n)]


def fetch_tiktok(brand, context=''):
    global source_warnings
    if not config.ENABLE_TIKTOK:
        return []
    client = ApifyClient(config.APIFY_API_KEY)
    results = []
    query = _search_query(brand, context)
    try:
        run_input = {
            "keywords": [query],
            "maxItems": config.APIFY_MAX_RESULTS,
            "sortType": "RELEVANCE",
            "dateFrom": "2026-01-01",
            "dateTo": "2026-12-31",
        }
        _log(f"TikTok: starting run for '{query}'")
        run = client.actor(config.APIFY_TIKTOK_ACTOR).call(
            run_input=run_input,
            max_items=config.APIFY_MAX_RESULTS,
            wait_secs=600,
        )
        _log(f'TikTok: run finished')
        for item in client.dataset(run['defaultDatasetId']).iterate_items():
            text = item.get('title') or item.get('text') or item.get('description') or ''
            if not text:
                continue
            results.append({
                'platform': 'TikTok',
                'author': (item.get('channel') or {}).get('username') or item.get('authorMeta', {}).get('name') or 'unknown',
                'content': text[:500],
                'url': (
                    item.get('webVideoUrl')
                    or item.get('videoUrl')
                    or item.get('shareUrl')
                    or (
                        'https://www.tiktok.com/@'
                        + str((item.get('authorMeta') or {}).get('name') or (item.get('channel') or {}).get('username') or 'unknown')
                        + '/video/'
                        + str(item.get('id') or '')
                        if item.get('id') else ''
                    )
                    or ''
                ),
            })
    except Exception as e:
        source_warnings.append(f'TikTok: {e}')
        _log(f'TikTok: ERROR {e}')
    _log(f'TikTok: collected {len(results)} items')
    return results

"""
Social Listening - Brand Sentiment Analyzer
"""

import time
import re
import anthropic
from collections import Counter
from apify_client import ApifyClient
from urllib.parse import quote_plus
import config

source_warnings = []

_log_callback = None


def set_log_callback(fn):
    global _log_callback
    _log_callback = fn


def _log(msg):
    import sys
    ts = time.strftime('%H:%M:%S')
    line = f'[{ts}] {msg}'
    print(line, flush=True)
    sys.stdout.flush()
    if _log_callback is not None:
        try:
            _log_callback(line)
        except Exception:
            pass


_STOP_WORDS = {
    "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "is", "are", "was", "were", "be", "been",
    "being", "have", "has", "had", "do", "does", "did", "will", "would",
    "could", "should", "may", "might", "shall", "can", "not", "no", "nor",
    "so", "yet", "both", "either", "neither", "this", "that", "these",
    "those", "it", "its", "i", "me", "my", "we", "our", "you", "your",
    "he", "she", "they", "them", "their", "what", "which", "who", "when",
    "where", "why", "how", "all", "more", "also", "just", "get", "got",
    "s", "t", "re", "ve", "ll", "d", "m",
}


def _search_query(brand, context):
    """Append context hint to brand so search is more specific."""
    if context and context.strip():
        return f'{brand} {context.strip()}'
    return brand


def extract_top_terms(posts, sentiment, brand, n=3):
    """Return top-n words from posts of a given sentiment."""
    words = []
    brand_lower = brand.lower().split()
    for post in posts:
        if post.get('sentiment') == sentiment:
            text = post.get('content', '')
            tokens = re.findall(r"[a-z']+", text.lower())
            for w in tokens:
                if w not in _STOP_WORDS and w not in brand_lower and len(w) > 2:
                    words.append(w)
    if not words:
        return []
    return [word for word, _ in Counter(words).most_common(n)]


def fetch_tiktok(brand, context=''):
    global source_warnings
    if not config.ENABLE_TIKTOK:
        return []
    client = ApifyClient(config.APIFY_API_KEY)
    results = []
    query = _search_query(brand, context)
    try:
        run_input = {
            "keywords": [query],
            "maxItems": config.APIFY_MAX_RESULTS,
            "sortType": "RELEVANCE",
            "dateFrom": "2026-01-01",
            "dateTo": "2026-12-31",
        }
        _log(f"TikTok: starting run for '{query}'")
        run = client.actor(config.APIFY_TIKTOK_ACTOR).call(
            run_input=run_input,
            max_items=config.APIFY_MAX_RESULTS,
            wait_secs=600,
        )
        _log(f'TikTok: run finished')
        for item in client.dataset(run['defaultDatasetId']).iterate_items():
            text = item.get('title') or item.get('text') or item.get('description') or ''
            if not text:
                continue
            results.append({
                'platform': 'TikTok',
                'author': (item.get('channel') or {}).get('username') or item.get('authorMeta', {}).get('name') or 'unknown',
                'content': text[:500],
                'url': item.get('webVideoUrl') or '',
            })
    except Exception as e:
        source_warnings.append(f'TikTok: {e}')
        _log(f'TikTok: ERROR {e}')
    _log(f'TikTok: collected {len(results)} items')
    return results


def fetch_linkedin(brand, context=''):
    global source_warnings
    if not config.ENABLE_LINKEDIN:
        return []
    client = ApifyClient(config.APIFY_API_KEY)
    results = []
    query = _search_query(brand, context)
    try:
        search_url = (
            'https://www.linkedin.com/search/results/content/?keywords='
            + quote_plus(query)
            + '&datePosted=past-year'
        )
        run_input = {
            "urls": [search_url],
            "count": config.APIFY_MAX_RESULTS,
            "startDate": "2026-01-01",
            "endDate": "2026-12-31",
        }
        _log(f"LinkedIn: starting run for '{query}'")
        run = client.actor(config.APIFY_LINKEDIN_ACTOR).call(
            run_input=run_input,
            max_items=config.APIFY_MAX_RESULTS,
            wait_secs=600,
        )
        _log(f'LinkedIn: run finished')
        for item in client.dataset(run['defaultDatasetId']).iterate_items():
            text = item.get('text') or item.get('content') or item.get('description') or ''
            if not text:
                continue
            results.append({
                'platform': 'LinkedIn',
                'author': item.get('author') or item.get('name') or 'unknown',
                'content': text[:500],
                'url': item.get('url') or item.get('postUrl') or '',
            })
    except Exception as e:
        source_warnings.append(f'LinkedIn: {e}')
        _log(f'LinkedIn: ERROR {e}')
    _log(f'LinkedIn: collected {len(results)} items')
    return results


def fetch_twitter(brand, context=''):
    """
    Fetch tweets via Apify (kaitoeasyapi/twitter-x-data-tweet-scraper-pay-per-result-cheapest).
    ntscraper was removed because public Nitter instances are unreliable.
    """
    global source_warnings
    if not config.ENABLE_TWITTER:
        return []
    client = ApifyClient(config.APIFY_API_KEY)
    results = []
    query = _search_query(brand, context)
    try:
        run_input = {
            "searchTerms": [query],
            "maxItems": config.APIFY_MAX_RESULTS,
            "queryType": "Latest",
            "since": "2026-01-01",
            "until": "2026-12-31",
        }
        _log(f"Twitter/X: starting Apify run for '{query}'")
        run = client.actor(config.APIFY_TWITTER_ACTOR).call(
            run_input=run_input,
            max_items=config.APIFY_MAX_RESULTS,
            wait_secs=600,
        )
        _log(f'Twitter/X: run finished')
        for item in client.dataset(run['defaultDatasetId']).iterate_items():
            text_val = item.get('text') or item.get('fullText') or item.get('content') or ''
            if not text_val:
                continue
            results.append({
                'platform': 'Twitter/X',
                'author': item.get('author', {}).get('userName') or item.get('username') or 'unknown',
                'content': text_val[:500],
                'url': item.get('url') or item.get('tweetUrl') or '',
            })
    except Exception as e:
        source_warnings.append(f'Twitter/X: {e}')
        _log(f'Twitter/X: ERROR {e}')
    _log(f'Twitter/X: collected {len(results)} items')
    return results
def fetch_reddit(brand, context=''):
    global source_warnings
    if not config.ENABLE_REDDIT:
        return []
    client = ApifyClient(config.APIFY_API_KEY)
    results = []
    query = _search_query(brand, context)
    try:
        run_input = {
            "searchQuery": query,
            "maxPostsPerSource": config.APIFY_MAX_RESULTS,
            "afterDate": "2026-01-01",
            "beforeDate": "2026-12-31",
        }
        _log(f"Reddit: starting run for '{query}'")
        run = client.actor(config.APIFY_REDDIT_ACTOR).call(
            run_input=run_input,
            max_items=config.APIFY_MAX_RESULTS,
            wait_secs=600,
        )
        _log(f'Reddit: run finished')
        for item in client.dataset(run['defaultDatasetId']).iterate_items():
            title = item.get('title') or ''
            body = item.get('body') or item.get('selftext') or ''
            text = (title + ' ' + body).strip()
            if not text:
                continue
            results.append({
                'platform': 'Reddit',
                'author': item.get('author') or 'unknown',
                'content': text[:500],
                'url': item.get('url') or item.get('postUrl') or '',
            })
    except Exception as e:
        source_warnings.append(f'Reddit: {e}')
        _log(f'Reddit: ERROR {e}')
    _log(f'Reddit: collected {len(results)} items')
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
                messages=[
                    {
                        'role': 'user',
                        'content': (
                            'Analyze the sentiment of this social media post. '
                            'Reply with ONLY one word: positive, negative, or neutral.'
                            + '\n\nPost: ' + post['content'][:300]
                        ),
                    }
                ],
            )
            sentiment = message.content[0].text.strip().lower()
            if sentiment not in ('positive', 'negative', 'neutral'):
                sentiment = 'neutral'
            results.append({**post, 'sentiment': sentiment})
        except Exception as e:
            _log(f'Sentiment error: {e}')
            results.append({**post, 'sentiment': 'neutral'})
    return results


def run_analysis(brand, context=''):
    global source_warnings
    source_warnings = []
    all_posts = []
    _log('Step 1/5: TikTok')
    all_posts.extend(fetch_tiktok(brand, context))
    _log('Step 2/5: LinkedIn')
    all_posts.extend(fetch_linkedin(brand, context))
    _log('Step 3/5: Twitter/X')
    all_posts.extend(fetch_twitter(brand, context))
    _log('Step 4/5: Reddit')
    all_posts.extend(fetch_reddit(brand, context))
    _log(f'Fetching complete: {len(all_posts)} posts')
    if not all_posts:
        detail = ' | '.join(source_warnings) if source_warnings else 'No content returned.'
        return {'error': f"No data found for '{brand}'. Details: {detail}"}
    _log('Step 5/5: Conducting sentiment analysis...')
    analyzed = analyze_sentiment(all_posts)
    counts = {'positive': 0, 'negative': 0, 'neutral': 0}
    for post in analyzed:
        counts[post['sentiment']] = counts.get(post['sentiment'], 0) + 1
    total = len(analyzed)
    dominant = max(counts, key=counts.get)
    confidence = counts[dominant] / total if total else 0

    platform_breakdown = {}
    for post in analyzed:
        p = post['platform']
        if p not in platform_breakdown:
            platform_breakdown[p] = {'positive': 0, 'negative': 0, 'neutral': 0, 'total': 0}
        platform_breakdown[p][post['sentiment']] += 1
        platform_breakdown[p]['total'] += 1

    top_positive = extract_top_terms(analyzed, 'positive', brand)
    top_negative = extract_top_terms(analyzed, 'negative', brand)

    return {
        'brand': brand,
        'total': total,
        'counts': counts,
        'dominant': dominant,
        'confidence': confidence,
        'posts': analyzed,
        'platform_breakdown': platform_breakdown,
        'top_positive_terms': top_positive,
        'top_negative_terms': top_negative,
}
