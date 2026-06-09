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
    # Articles, conjunctions, prepositions
    "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "into", "onto", "upon", "about", "above",
    "below", "between", "through", "during", "before", "after", "since",
    "until", "unless", "although", "because", "though", "while", "where",
    # Auxiliary / modal verbs
    "is", "are", "was", "were", "be", "been", "being", "have", "has", "had",
    "do", "does", "did", "will", "would", "could", "should", "may", "might",
    "shall", "can", "cannot", "need", "dare", "used",
    # Negation / conjunctions
    "not", "no", "nor", "so", "yet", "both", "either", "neither",
    # Demonstratives / pronouns
    "this", "that", "these", "those", "it", "its", "itself",
    "i", "me", "my", "mine", "myself",
    "we", "us", "our", "ours", "ourselves",
    "you", "your", "yours", "yourself",
    "he", "him", "his", "himself",
    "she", "her", "hers", "herself",
    "they", "them", "their", "theirs", "themselves",
    # Question words
    "what", "which", "who", "whom", "whose", "when", "where", "why", "how",
    # Quantifiers / determiners
    "all", "any", "each", "every", "some", "none", "few", "many", "much",
    "more", "most", "less", "least", "other", "another", "same", "such",
    "own", "only", "one", "two", "three", "first", "last", "next",
    # Common adverbs / fillers
    "also", "just", "very", "really", "quite", "already", "still", "even",
    "never", "always", "often", "sometimes", "ever", "now", "then", "here",
    "there", "too", "well", "back", "out", "up", "down", "again", "away",
    "around", "always", "perhaps", "probably", "maybe", "actually",
    # Common verbs that give no insight
    "get", "got", "getting", "go", "going", "gone", "went", "come", "came",
    "coming", "make", "made", "making", "take", "took", "taken", "taking",
    "see", "saw", "seen", "say", "said", "says", "know", "knew", "think",
    "thought", "look", "looks", "looked", "want", "wanted", "need", "needed",
    "use", "used", "using", "give", "gave", "given", "keep", "kept",
    "let", "lets", "put", "set", "try", "tried", "ask", "asked", "told",
    "told", "show", "showed", "feel", "felt", "find", "found", "buy", "bought",
    "like", "liked", "love", "loved", "hate", "hated",
    # URL / web fragments
    "http", "https", "www", "com", "org", "net", "co", "ly", "bit",
    "url", "link", "via",
    # Social media noise
    "rt", "dm", "lol", "omg", "imo", "tbh", "aka", "irl",
    # Generic filler / low-signal words
    "people", "person", "thing", "things", "time", "times", "day", "days",
    "year", "years", "week", "way", "ways", "place", "places", "world",
    "new", "good", "bad", "great", "big", "little", "old", "high", "low",
    "right", "left", "long", "small", "large", "real", "true", "false",
    "sure", "able", "else", "going",
    # Generic food/restaurant/business terms (too broad to be useful)
    "restaurant", "restaurants", "food", "service", "store", "shop",
    "customer", "customers", "order", "ordered", "ordering",
    "menu", "price", "prices", "location", "locations",
    # Contractions / apostrophe fragments
    "s", "t", "re", "ve", "ll", "d", "m", "n",
    # Numeric strings / single chars
    "0", "1", "2", "3", "4", "5", "6", "7", "8", "9",
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



def _is_spam_promo(text):
    """Return True if the post looks like a promotional spam / ad post.

    Signals:
    - Price/discount patterns  (R$, $, EUR, GBP + numbers; percentage discounts)
    - Promo keywords           (cupom, desconto, discount, coupon, sale, shop now)
    - Sponsored hashtags       (#ad, #anuncio, #publicidade, #sponsored)
    - Excessive emoji density  (>25% non-ASCII characters)
    - Hashtag spam             (5 or more hashtags)
    - Link dump                (more than 2 bare URLs)
    """
    if not text:
        return False
    t_lower = text.lower()

    # Price / discount numeric patterns
    price_pats = [
        r'r\$\s*\d',
        r'\$\s*\d',
        r'€\s*\d',
        r'£\s*\d',
        r'de r\s+\d',
        r'por r\s+\d',
        r'\d+\s*%\s*off',
        r'\d+\s*%\s*de\s+desconto',
        r'até\s+\d+\s*%',
    ]
    for pat in price_pats:
        if re.search(pat, t_lower):
            return True

    # Promo / coupon / CTA keywords
    promo_kws = [
        'cupom', 'desconto', 'oferta', 'promoção', 'promocao',
        'frete gratis', 'frete grátis', 'compre agora', 'compre já',
        'clique aqui', 'acesse o link', 'link na bio', 'link in bio',
        'discount code', 'promo code', 'coupon code', 'use code', 'use coupon',
        'shop now', 'buy now', 'order now',
        'limited time offer', 'flash sale', 'huge sale',
        'free shipping', 'special offer', 'exclusive deal',
    ]
    for kw in promo_kws:
        if kw in t_lower:
            return True

    # Sponsored / ad hashtags
    if re.search(r'#(ad|ads|sponsored|publicidade|publi|anuncio|an\u00FAncio)\b', t_lower):
        return True

    # 5 or more hashtags = hashtag spam
    if len(re.findall(r'#\w+', text)) >= 5:
        return True

    # High non-ASCII / emoji density > 25%
    non_ascii = sum(1 for ch in text if ord(ch) > 127)
    if len(text) > 0 and non_ascii / len(text) > 0.25:
        return True

    # More than 2 URLs = link dump
    if len(re.findall(r'https?://\S+', text)) > 2:
        return True

    return False

def extract_top_terms(posts, sentiment, brand, n=5):
    """Return top-n meaningful words from posts of a given sentiment.

    Improvements over v1:
    - Strips URLs before tokenising so fragments like 'https', 'com' don't appear
    - Expands stop-word list to cover generic fillers
    - Filters out the brand name and its slug variants (e.g. 'wendy' for 'Wendy\'s')
    - Requires minimum word length > 3 (was > 2)
    - Returns top-5 by default (was 3) so callers get richer context
    """
    words = []
    # Build brand filter: full name words + slug (lowercase, letters only)
    brand_lower = set(brand.lower().split())
    brand_slug = re.sub(r"[^a-z]", "", brand.lower())
    if brand_slug:
        brand_lower.add(brand_slug)
    for post in posts:
        if post.get('sentiment') == sentiment:
            text = post.get('content', '')
            # Remove URLs first so fragments don't pollute token list
            text = re.sub(r'https?://\S+|www\.\S+', '', text, flags=re.IGNORECASE)
            tokens = re.findall(r"[a-z]+", text.lower())
            for w in tokens:
                if (
                    len(w) > 3
                    and w not in _STOP_WORDS
                    and w not in brand_lower
                    and not w.isdigit()
                ):
                    words.append(w)
    if not words:
        return []
    return [word for word, _ in Counter(words).most_common(n)]


def _scrape_window_since(scrape_window):
    """Return a YYYY-MM-DD string for the start of the requested scrape window."""
    days_map = {'day': 1, 'week': 7, 'month': 30, '3months': 91, '6months': 182, 'year': 365}
    days = days_map.get(scrape_window, 365)
    return (datetime.date.today() - datetime.timedelta(days=days)).strftime('%Y-%m-%d')


def fetch_tiktok(brand, scrape_window='year'):
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
                        "dateFrom": _scrape_window_since(scrape_window),
                        "dateTo":   datetime.date.today().strftime("%Y-%m-%d"),
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
            if not _is_english(text):
                continue
            if _is_spam_promo(text):
                continue
            results.append({
                'platform': 'TikTok',
                'author': (item.get('channel') or {}).get('username') or (item.get('authorMeta') or {}).get('name') or 'unknown',
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


def fetch_linkedin(brand, scrape_window='year'):
    global source_warnings
    if not config.ENABLE_LINKEDIN:
        return []
    client = ApifyClient(config.APIFY_API_KEY)
    results = []
    query = _search_query(brand)
    try:
        run_input = {
            "searchQueries": [query],
            "maxPosts": config.APIFY_MAX_RESULTS,
            "postedLimit": {"week": "week", "6months": "6months", "year": "year"}.get(scrape_window, "year"),
            "sortBy": "relevance",
            "scrapeReactions": False,
            "scrapeComments": False,
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
                item.get('text') or '',
                item.get('content') or '',
                item.get('description') or '',
            ]
            text = ' '.join(p for p in parts if p).strip()
            if not text or len(text.strip()) < 15:
                continue
            if not _is_english(text):
                continue
            if _is_spam_promo(text):
                continue
            author_obj = item.get('author') or {}
            if isinstance(author_obj, dict):
                author = (author_obj.get('name') or author_obj.get('fullName') or '').strip()
            else:
                author = str(author_obj).strip()
            results.append({
                'platform': 'LinkedIn',
                'author': author,
                'content': text[:500],
                'url': (
                    item.get('url')
                    or item.get('postUrl')
                    or ''
                ),
            })
    except Exception as e:
        source_warnings.append(f'LinkedIn: {e}')
        _log(f'LinkedIn: ERROR {e}')
    _log(f'LinkedIn: collected {len(results)} items')
    return results
def fetch_twitter(brand, scrape_window='year'):
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
            "queryType": "Top",
            "lang":      "en",
            "since":     _scrape_window_since(scrape_window),
            "until":     datetime.date.today().strftime('%Y-%m-%d'),
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
            if not _is_english(text_val):
                continue
            if _is_spam_promo(text_val):
                continue
            results.append({
                'platform': 'Twitter/X',
                'author': (item.get('author') or {}).get('userName') or item.get('username') or 'unknown',
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
def fetch_reddit(brand, scrape_window='year'):
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
            "timeFilter": "week" if scrape_window == "week" else "year",
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
            if not _is_english(text):
                continue
            if _is_spam_promo(text):
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



def fetch_youtube(brand, scrape_window='year'):
    """Fetch YouTube videos mentioning the brand via apidojo/youtube-scraper."""
    global source_warnings
    if not config.ENABLE_YOUTUBE:
        return []
    client = ApifyClient(config.APIFY_API_KEY)
    results = []
    # Map scrape_window to uploadDate values supported by the actor
    upload_date_map = {
        'week':    'w',
                '6months': 'm',         # actor has no 6-month option; round to month
        'year':    'y',
                        'day':     't',
                        'month':   'm',
                        '3months': 'm',
    }
    upload_date = upload_date_map.get(scrape_window, 'y')
    try:
        run_input = {
            "keywords":   [brand],
            "maxItems":   config.APIFY_MAX_RESULTS,
            "uploadDate": upload_date,
            "sort":       "r",   # relevance
            "gl":         "us",
            "hl":         "en",
            "scrapeComments": False,
        }
        _log(f"YouTube: starting run for '{brand}'")
        run = client.actor(config.APIFY_YOUTUBE_ACTOR).start(
            run_input=run_input,
            max_items=config.APIFY_MAX_RESULTS,
        )
        client.run(run.id).wait_for_finish()
        _log(f'YouTube: run finished')
        for item in client.dataset(run.default_dataset_id).iterate_items():
            text = (
                item.get('description') or
                item.get('title') or
                item.get('text') or ''
            ).strip()
            if not text or len(text) < 15:
                continue
            if not _is_english(text):
                continue
            if _is_spam_promo(text):
                continue
            results.append({
                'platform': 'YouTube',
                'author':   (item.get('channelName') or (item.get('channel') or {}).get('name') or '').strip(),
                'content':  text[:500],
                'url':      item.get('url') or item.get('videoUrl') or '',
            })
    except Exception as e:
        source_warnings.append(f'YouTube: {e}')
        _log(f'YouTube: ERROR {e}')
    _log(f'YouTube: collected {len(results)} items')
    return results


def fetch_instagram(brand, scrape_window='year'):
    """Fetch Instagram posts mentioning the brand via apidojo/instagram-scraper."""
    global source_warnings
    if not config.ENABLE_INSTAGRAM:
        return []
    client = ApifyClient(config.APIFY_API_KEY)
    results = []
    # Build a hashtag search URL from the brand slug
    brand_slug = re.sub(r'[^a-z0-9]', '', brand.lower())
    # until = oldest date we want (actor returns posts NEWER than this)
    window_days_map = {'week': 7, '6months': 182, 'year': 365}
    days_back = window_days_map.get(scrape_window, 365)
    until_date = (datetime.date.today() - datetime.timedelta(days=days_back)).strftime('%Y-%m-%d')
    hashtag_url = f'https://www.instagram.com/explore/tags/{brand_slug}/'
    try:
        run_input = {
            "startUrls": [hashtag_url],
            "maxItems":  config.APIFY_MAX_RESULTS,
            "until":     until_date,
        }
        _log(f"Instagram: starting run for '#{brand_slug}'")
        run = client.actor(config.APIFY_INSTAGRAM_ACTOR).start(
            run_input=run_input,
            max_items=config.APIFY_MAX_RESULTS,
        )
        client.run(run.id).wait_for_finish()
        _log(f'Instagram: run finished')
        for item in client.dataset(run.default_dataset_id).iterate_items():
            text = (
                item.get('caption') or
                item.get('text') or
                item.get('description') or ''
            ).strip()
            if not text or len(text) < 15:
                continue
            if not _is_english(text):
                continue
            if _is_spam_promo(text):
                continue
            owner = item.get('ownerUsername') or item.get('username') or ''
            results.append({
                'platform': 'Instagram',
                'author':   owner,
                'content':  text[:500],
                'url':      item.get('url') or item.get('shortCode') and f"https://www.instagram.com/p/{item['shortCode']}/" or '',
            })
    except Exception as e:
        source_warnings.append(f'Instagram: {e}')
        _log(f'Instagram: ERROR {e}')
    _log(f'Instagram: collected {len(results)} items')
    return results


def filter_brand_relevant(posts, brand, brand_hint='', batch_size=50):
    """Use Claude to filter out posts that are not about the brand/company.

    Posts are evaluated in batches. If a batch hits a content-policy 400,
    it falls back to per-post filtering so only the offending post(s) are
    dropped rather than keeping an unfiltered chunk. All other errors are
    fail-open (chunk kept) so no posts are silently lost.
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
            f'You are a social media content moderator performing brand-relevance classification.\n\n'
            f'For each numbered post below, reply YES if it is clearly about the brand/company '
            f'named "{brand}"{hint_clause}, or NO if it is not or if you are unsure.\n\n'
            f'Important: "{brand}" may refer to multiple things (a company, a person, a place, '
            f'a common word, etc.). Only keep posts where the context makes it clear the author '
            f'is talking about a commercial brand or company -- not a celebrity, athlete, '
            f'fictional character, place, or unrelated use of the word.\n\n'
            f'Posts:\n{numbered}\n\n'
            f'Return ONLY a JSON array of YES/NO answers in order, e.g. ["YES","NO","YES"].\n'
            f'No explanation, just the JSON array.'
        )
        try:
            response = client.messages.create(
                model=config.CLAUDE_MODEL,
                max_tokens=batch_size * 6,
                system="You are a content moderation assistant classifying social media posts for brand relevance.",
                messages=[{'role': 'user', 'content': prompt}],
            )
            raw = response.content[0].text.strip()
            match = re.search(r'\[.*?\]', raw, re.DOTALL)
            answers = json.loads(match.group()) if match else []
            if not answers:
                _log('Brand filter: no valid JSON in response for chunk, keeping chunk')
                relevant.extend(chunk)
            else:
                for idx, post in enumerate(chunk):
                    # Fail open: if Claude returned fewer answers than posts,
                    # keep the unanswered tail instead of silently dropping it.
                    ans = answers[idx] if idx < len(answers) else 'YES'
                    if str(ans).upper() == 'YES':
                        relevant.append(post)
        except anthropic.BadRequestError as e:
            _log(f'Brand filter: content policy hit on batch, falling back to per-post filtering')
            for post in chunk:
                snippet = str(post.get('content', ''))[:300]
                single_prompt = (
                    f'Does this post mention the brand or company "{brand}"{hint_clause}? '
                    f'Reply YES or NO only.\n\nPost: {snippet}'
                )
                try:
                    r = client.messages.create(
                        model=config.CLAUDE_MODEL,
                        max_tokens=10,
                        system="You are a content moderation assistant.",
                        messages=[{'role': 'user', 'content': single_prompt}],
                    )
                    if 'YES' in r.content[0].text.upper():
                        relevant.append(post)
                except Exception:
                    relevant.append(post)
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
    failed_chunks = 0
    chunk_size = 50  # smaller chunks = shorter JSON response = no truncation risk
    chunk_count = (len(posts) + chunk_size - 1) // chunk_size
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
            failed_chunks += 1
            _log(f'Sentiment batch error (chunk {chunk_idx + 1}): {e} — defaulting to neutral')
            sentiments = []
        for i, post in enumerate(chunk):
            s = _validate_sentiment(sentiments[i]) if i < len(sentiments) else 'neutral'
            results.append({**post, 'sentiment': s})
    if failed_chunks:
        source_warnings.append(
            f'Sentiment analysis: {failed_chunks} of {chunk_count} batches could not be '
            f'classified and were counted as neutral — results may be skewed.'
        )
    return results


def run_analysis(brand, brand_hint='', scrape_window=None):
    global source_warnings
    source_warnings = []
    all_posts = []
    window = scrape_window or config.SCRAPE_WINDOW
    _log(f'Scrape window: {window}')
    _log('Step 1/7: TikTok')
    all_posts.extend(fetch_tiktok(brand, window))
    _log('Step 2/7: LinkedIn')
    all_posts.extend(fetch_linkedin(brand, window))
    _log('Step 3/7: Twitter/X')
    all_posts.extend(fetch_twitter(brand, window))
    _log('Step 4/7: Reddit')
    all_posts.extend(fetch_reddit(brand, window))
    _log('Step 5/7: YouTube')
    all_posts.extend(fetch_youtube(brand, window))
    _log('Step 6/7: Instagram')
    all_posts.extend(fetch_instagram(brand, window))
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
    _log('Step 7/7: Conducting sentiment analysis...')
    analyzed = analyze_sentiment(all_posts)
    counts = {'positive': 0, 'negative': 0, 'neutral': 0}
    for post in analyzed:
        counts[post['sentiment']] = counts.get(post['sentiment'], 0) + 1
    total = len(analyzed)
    dominant = max(counts, key=counts.get)
    agreement = counts[dominant] / total if total else 0
    net_sentiment = (counts['positive'] - counts['negative']) / total if total else 0

    platform_breakdown = {}
    for post in analyzed:
        p = post['platform']
        if p not in platform_breakdown:
            platform_breakdown[p] = {'positive': 0, 'negative': 0, 'neutral': 0, 'total': 0}
        platform_breakdown[p][post['sentiment']] += 1
        platform_breakdown[p]['total'] += 1

    top_positive = extract_top_terms(analyzed, 'positive', brand)
    top_negative = extract_top_terms(analyzed, 'negative', brand)

    funnel = {
        'collected': _before_lang,
        'lang_spam_dropped': _lang_dropped,
        'duplicates_dropped': _dedup_dropped,
        'off_brand_dropped': _filter_dropped if config.ENABLE_BRAND_FILTER else 0,
        'analyzed': total,
    }

    return {
        'brand': brand,
        'total': total,
        'counts': counts,
        'dominant': dominant,
        'agreement': agreement,
        'net_sentiment': net_sentiment,
        'posts': analyzed,
        'platform_breakdown': platform_breakdown,
        'top_positive_terms': top_positive,
        'top_negative_terms': top_negative,
        'funnel': funnel,
        'warnings': source_warnings[:],
    }
