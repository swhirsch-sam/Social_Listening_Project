#!/usr/bin/env python3
"""
Social Listening - Brand Sentiment Analyzer
"""

import time
import datetime
import json
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


def _search_query(brand):
    """Build an exact-phrase search query so APIs don't match individual words."""
    return f'"{brand}"'


def _is_english(text):
    """Return True if text appears to be English (predominantly ASCII, min 4 words).
    Uses no external libraries — works by checking the ratio of non-ASCII characters.
    """
    if not text or not text.strip():
        return False
    words = text.split()
    if len(words) < 4:
        return False  # too short / spam
    non_ascii = sum(1 for ch in text if ord(ch) > 127)
    ratio = non_ascii / len(text)
    return ratio < 0.3  # >70% ASCII → likely English


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


def fetch_tiktok(brand):
    global source_warnings
    if not config.ENABLE_TIKTOK:
        return []
    client = ApifyClient(config.APIFY_API_KEY)
    results = []
    query = _search_query(brand)
    try:
        run_input = {
            "keywords": [query],
            "maxItems": config.APIFY_MAX_RESULTS,
            "sortType": "RELEVANCE",
                        "dateFrom": (datetime.date.today() - datetime.timedelta(days=365)).strftime("%Y-%m-%d"),
                        "dateTo": datetime.date.today().strftime("%Y-%m-%d"),
        }
        _log(f"TikTok: starting run for '{query}'")
        run = client.actor(config.APIFY_TIKTOK_ACTOR).start(
            run_input=run_input,
            max_items=config.APIFY_MAX_RESULTS,
        )
        client.run(run.id).wait_for_finish()
        _log(f'TikTok: run finished')
        for item in client.dataset(run.default_dataset_id).iterate_items():
            text = item.get('title') or item.get('text') or item.get('description') or ''
            if not text or len(text.strip()) < 15:
                continue
            results.append({
                'platform': 'TikTok',
                'author': (item.get('channel') or {}).get('username') or item.get('authorMeta', {}).get('name') or 'unknown',
                'content': text[:500],
                'url': (
                    item.get('postPage')
                    or item.get('webVideoUrl')
                    or item.get('videoUrl')
                    or item.get('url')
                    or (
                        'https://www.tiktok.com/@'
                        + str((item.get('channel') or {}).get('username') or item.get('authorMeta', {}).get('name') or 'unknown')
                        + '/video/'
                        + str(item.get('id') or '')
                        if item.get('id') else ''
                    )
                ),
            })
    except Exception as e:
        source_warnings.append(f'TikTok: {e}')
        _log(f'TikTok: ERROR {e}')
    _log(f'TikTok: collected {len(results)} items')
    return results


def _linkedin_author(item):
    """Extract author name from a linkedin-post Apify actor result item."""
    # Top-level flat field used by supreme_coder/linkedin-post
    if item.get('authorFullName'):
        return item['authorFullName']
    # Dict with firstName / lastName
    author = item.get('author')
    if isinstance(author, dict):
        full = ' '.join(filter(None, [author.get('firstName'), author.get('lastName')])).strip()
        if full:
            return full
        return author.get('universalName') or author.get('name') or ''
    # Plain string fallback
    if isinstance(author, str) and author:
        return author
    # Other top-level fields
    return item.get('authorProfileId') or item.get('name') or 'Unknown'


def fetch_linkedin(brand):
    global source_warnings
    if not config.ENABLE_LINKEDIN:
        return []
    client = ApifyClient(config.APIFY_API_KEY)
    results = []
    query = _search_query(brand)
    try:
        search_url = (
            'https://www.linkedin.com/search/results/content/?keywords='
            + quote_plus(query)
            + '&datePosted=past-year'
        )
        run_input = {
            "urls": [search_url],
            "count": config.APIFY_MAX_RESULTS,
                        "startDate": (datetime.date.today() - datetime.timedelta(days=365)).strftime("%Y-%m-%d"),
                        "endDate": datetime.date.today().strftime("%Y-%m-%d"),
        }
        _log(f"LinkedIn: starting run for '{query}'")
        run = client.actor(config.APIFY_LINKEDIN_ACTOR).start(
            run_input=run_input,
            max_items=config.APIFY_MAX_RESULTS,
        )
        client.run(run.id).wait_for_finish()
        _log(f'LinkedIn: run finished')
        for item in client.dataset(run.default_dataset_id).iterate_items():
            parts = [
                item.get('title') or '',
                item.get('text') or '',
                item.get('content') or '',
                item.get('description') or '',
                item.get('subtitle') or '',
            ]
            text = ' '.join(p for p in parts if p).strip()
            if not text or len(text.strip()) < 15:
                continue
            results.append({
                'platform': 'LinkedIn',
                'author': _linkedin_author(item),
                'content': text[:500],
                'url': (
                    item.get('postUrl')
                    or item.get('url')
                    or (
                        'https://www.linkedin.com/feed/update/' + item.get('postId')
                        if item.get('postId') else ''
                    )
                ),
            })
    except Exception as e:
        source_warnings.append(f'LinkedIn: {e}')
        _log(f'LinkedIn: ERROR {e}')
    _log(f'LinkedIn: collected {len(results)} items')
    return results


def fetch_twitter(brand):
    """
    Fetch tweets via Apify (kaitoeasyapi/twitter-x-data-tweet-scraper-pay-per-result-cheapest).
    ntscraper was removed because public Nitter instances are unreliable.
    """
    global source_warnings
    if not config.ENABLE_TWITTER:
        return []
    client = ApifyClient(config.APIFY_API_KEY)
    results = []
    query = _search_query(brand)
    try:
        run_input = {
            "searchTerms": [query],
            "maxItems": config.APIFY_MAX_RESULTS,
            "queryType": "Latest",
            "lang": "en",
            "since":(datetime.date.today() - datetime.timedelta(days=365)).strftime('%Y-%m-%d')
        }
        _log(f"Twitter/X: starting Apify run for '{query}'")
        run = client.actor(config.APIFY_TWITTER_ACTOR).start(
            run_input=run_input,
            max_items=config.APIFY_MAX_RESULTS,
        )
        client.run(run.id).wait_for_finish()
        _log(f'Twitter/X: run finished')
        for item in client.dataset(run.default_dataset_id).iterate_items():
            parts = [
                item.get('text') or '',
                item.get('fullText') or '',
                item.get('content') or '',
                (item.get('quotedTweet') or {}).get('text') or '',
                (item.get('retweetedTweet') or {}).get('text') or '',
            ]
            text_val = ' '.join(p for p in parts if p).strip()
            if not text_val or len(text_val.strip()) < 15:
                continue
            results.append({
                'platform': 'Twitter/X',
                'author': item.get('author', {}).get('userName') or item.get('username') or 'unknown',
                'content': text_val[:500],
                'url': (
                    item.get('url')
                    or item.get('tweetUrl')
                    or (
                        'https://x.com/'
                        + str((item.get('author') or {}).get('userName') or item.get('username') or 'i')
                        + '/status/'
                        + str(item.get('id') or item.get('tweetId') or '')
                        if (item.get('id') or item.get('tweetId')) else ''
                    )
                ),
            })
    except Exception as e:
        source_warnings.append(f'Twitter/X: {e}')
        _log(f'Twitter/X: ERROR {e}')
    _log(f'Twitter/X: collected {len(results)} items')
    return results
def fetch_reddit(brand):
    global source_warnings
    if not config.ENABLE_REDDIT:
        return []
    client = ApifyClient(config.APIFY_API_KEY)
    results = []
    query = _search_query(brand)
    try:
        run_input = {
            "searchQuery": query,
            "maxPostsPerSource": config.APIFY_MAX_RESULTS,
            "sort": "relevance",
            "timeFilter": "year",
            "includeComments": False,
        }
        _log(f"Reddit: starting run for '{query}'")
        run = client.actor(config.APIFY_REDDIT_ACTOR).start(
            run_input=run_input,
            max_items=config.APIFY_MAX_RESULTS,
        )
        client.run(run.id).wait_for_finish()
        _log(f'Reddit: run finished')
        for item in client.dataset(run.default_dataset_id).iterate_items():
            title = item.get('title') or ''
            body = item.get('body') or item.get('selftext') or ''
            text = (title + ' ' + body).strip()
            if not text or len(text.strip()) < 15:
                continue
            results.append({
                'platform': 'Reddit',
                'author': item.get('author') or 'unknown',
                'content': text[:500],
                'url': (
                    (
                        'https://www.reddit.com' + item.get('permalink')
                        if item.get('permalink') else None
                    )
                    or item.get('postUrl')
                    or item.get('url')
                    or ''
                ),
            })
    except Exception as e:
        source_warnings.append(f'Reddit: {e}')
        _log(f'Reddit: ERROR {e}')
    _log(f'Reddit: collected {len(results)} items')
    return results



def filter_brand_relevant(posts, brand, brand_hint='', batch_size=50):
    """Use Claude to filter out posts that are not about the brand/company.

    Posts are evaluated in batches. If the API call fails for any batch,
    that batch is kept (fail-open) so no posts are silently dropped.
    """
    if not posts:
        return posts
    if not config.ENABLE_BRAND_FILTER:
        return posts
    client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
    hint_clause = f' ({brand_hint})' if brand_hint else ''
    relevant = []
    for i in range(0, len(posts), batch_size):
        chunk = posts[i:i + batch_size]
        numbered = '\n'.join(
            f"{j + 1}. {str(p.get('content', ''))[:300]}"
            for j, p in enumerate(chunk)
        )
        prompt = (
            f'You are a social media content filter. Your job is to decide whether each post '
            f'is about the brand or company named "{brand}"{hint_clause}.\n\n'
            f'Important: "{brand}" may refer to multiple things (a company, a person, a place, '
            f'a common word, etc.). Only keep posts where the context makes it clear the author '
            f'is talking about a commercial brand or company -- not a celebrity, athlete, '
            f'fictional character, place, or unrelated use of the word.\n\n'
            f'For each numbered post below, reply YES if it is clearly about the {brand} '
            f'brand/company, or NO if it is not or if you are unsure.\n\n'
            f'Posts:\n{numbered}\n\n'
            f'Return ONLY a JSON array of YES/NO answers in order, e.g. ["YES","NO","YES"].\n'
            f'No explanation, just the JSON array.'
        )
        try:
            response = client.messages.create(
                model=config.CLAUDE_MODEL,
                max_tokens=256,
                messages=[{'role': 'user', 'content': prompt}],
            )
            raw = response.content[0].text.strip()
            match = re.search(r'\[.*?\]', raw, re.DOTALL)
            answers = json.loads(match.group()) if match else []
            for post, ans in zip(chunk, answers):
                if str(ans).upper() == 'YES':
                    relevant.append(post)
            if not answers:
                _log(f'Brand filter: no valid JSON in response for chunk, keeping chunk')
                relevant.extend(chunk)
        except Exception as e:
            _log(f'Brand filter error (keeping chunk): {e}')
            relevant.extend(chunk)
        time.sleep(config.CLAUDE_DELAY_SECONDS)
    return relevant


def _validate_sentiment(s):
    """Validate and normalise a sentiment string returned by Claude."""
    if isinstance(s, str) and s.strip().lower() in ('positive', 'negative', 'neutral'):
        return s.strip().lower()
    return 'neutral'


def analyze_sentiment(posts):
    """Classify all posts in a single batched Claude call for speed."""
    import re as _re
    if not posts:
        return []
    client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
    results = []
    chunk_size = 50  # smaller chunks = shorter JSON response = no truncation risk
    for chunk_idx, chunk_start in enumerate(range(0, len(posts), chunk_size)):
        chunk = posts[chunk_start:chunk_start + chunk_size]
        post_texts = '\n'.join(
            f'{i + 1}. {str(post.get("content") or "")[:300]}'
            for i, post in enumerate(chunk)
        )
        prompt = (
            'Classify the sentiment of each social media post below as positive, negative, or neutral. '
            'Reply with ONLY a JSON array of strings in the same order, '
            'e.g. ["positive","neutral","negative"]. No explanation, no markdown.\n\n'
            + post_texts
        )
        sentiments = []
        try:
            # max_tokens: each label ~12 chars, 50 posts = ~600 chars; use 1024 for headroom
            message = client.messages.create(
                model=config.CLAUDE_MODEL,
                max_tokens=1024,
                messages=[{'role': 'user', 'content': prompt}],
            )
            raw = message.content[0].text.strip()
            # Strip markdown fences if Claude wraps the array
            raw = _re.sub(r'```[a-z]*\n?', '', raw).strip()
            # Extract just the JSON array in case there is surrounding text
            m = _re.search(r'\[.*\]', raw, _re.DOTALL)
            raw = m.group(0) if m else raw
            sentiments = json.loads(raw)
            if not isinstance(sentiments, list):
                raise ValueError(f'Expected list, got {type(sentiments)}')
        except Exception as e:
            _log(f'Sentiment batch error (chunk {chunk_idx + 1}): {e} — defaulting to neutral')
            sentiments = []
        for i, post in enumerate(chunk):
            s = _validate_sentiment(sentiments[i]) if i < len(sentiments) else 'neutral'
            results.append({**post, 'sentiment': s})
    return results


def run_analysis(brand, brand_hint=''):
    global source_warnings
    source_warnings = []
    all_posts = []
    _log('Step 1/5: TikTok')
    all_posts.extend(fetch_tiktok(brand))
    _log('Step 2/5: LinkedIn')
    all_posts.extend(fetch_linkedin(brand))
    _log('Step 3/5: Twitter/X')
    all_posts.extend(fetch_twitter(brand))
    _log('Step 4/5: Reddit')
    all_posts.extend(fetch_reddit(brand))
    _log(f'Fetching complete: {len(all_posts)} posts')
    # --- English / spam filter ---
    _before_lang = len(all_posts)
    all_posts = [p for p in all_posts if _is_english(p.get('content', ''))]
    _lang_dropped = _before_lang - len(all_posts)
    if _lang_dropped:
        _log(f'Language filter: dropped {_lang_dropped} non-English/spam posts; {len(all_posts)} remain')
    # --- Deduplication: remove posts with identical content ---
    _before_dedup = len(all_posts)
    _seen_hashes = set()
    _deduped = []
    for _p in all_posts:
        _key = hash(_p.get('content', '')[:200])
        if _key not in _seen_hashes:
            _seen_hashes.add(_key)
            _deduped.append(_p)
    all_posts = _deduped
    _dedup_dropped = _before_dedup - len(all_posts)
    if _dedup_dropped:
        _log(f'Deduplication: removed {_dedup_dropped} duplicate posts; {len(all_posts)} remain')
    
    # --- LLM brand relevance filter ---
    if config.ENABLE_BRAND_FILTER:
        _before_filter = len(all_posts)
        all_posts = filter_brand_relevant(all_posts, brand, brand_hint)
        _filter_dropped = _before_filter - len(all_posts)
        if _filter_dropped:
            _log(f'Brand filter: removed {_filter_dropped} off-brand posts, kept {len(all_posts)}')
    
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
        'warnings': source_warnings[:],
    }
