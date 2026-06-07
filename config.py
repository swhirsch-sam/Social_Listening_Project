# config.py - centralised settings for Social Listening MVP
# -------------------------------------------------------------------------
# API keys are read from environment variables (set in Streamlit Secrets or
# your shell). Never hardcode real secrets in this file.


import os


# -- API Keys ---------------------------------------------------------------
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
APIFY_API_KEY     = os.environ.get("APIFY_API_KEY", "")


# -- Apify actor IDs --------------------------------------------------------
APIFY_TIKTOK_ACTOR     = "apidojo/tiktok-scraper"
APIFY_LINKEDIN_ACTOR   = "supreme_coder/linkedin-post"
APIFY_INSTAGRAM_ACTOR  = "apidojo/instagram-scraper"
APIFY_TWITTER_ACTOR    = "kaitoeasyapi/twitter-x-data-tweet-scraper-pay-per-result-cheapest"
APIFY_REDDIT_ACTOR     = "automation-lab/reddit-scraper"
APIFY_YOUTUBE_ACTOR    = "apidojo/youtube-scraper"


# -- Source toggles ---------------------------------------------------------
ENABLE_TIKTOK     = True
ENABLE_LINKEDIN   = True
ENABLE_INSTAGRAM  = True  # requires Apify paid plan (Free plan = 10-item demo mode only)
ENABLE_TWITTER    = True
ENABLE_REDDIT     = True
ENABLE_YOUTUBE    = True  # requires Apify paid plan (Free plan = 10-item demo mode only)


# -- Scraping limits (per source, per run) ----------------------------------
APIFY_MAX_RESULTS = 150        # max items per Apify actor run


# -- Time-range window for scrapers -----------------------------------------
# Options: "day" | "week" | "month" | "3months" | "6months" | "year"
SCRAPE_WINDOW = "year"


# -- Claude model & rate-limit ----------------------------------------------
CLAUDE_MODEL          = "claude-haiku-4-5"
CLAUDE_DELAY_SECONDS  = 0.5   # seconds to pause between Claude API calls


# -- LLM brand-relevance filter ---------------------------------------------
ENABLE_BRAND_FILTER = True    # set False to skip the brand-relevance check


# -- IP rate limiting -------------------------------------------------------
RATE_LIMIT_MAX_RUNS    = 2     # max analysis runs allowed per IP
RATE_LIMIT_WINDOW_HOURS = 24   # rolling window in hours
