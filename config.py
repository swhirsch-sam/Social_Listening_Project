# config.py - centralised settings for Social Listening MVP
# -------------------------------------------------------------------------
# API keys are read from environment variables (set in Streamlit Secrets or
# your shell). Never hardcode real secrets in this file.

import os

# -- API Keys ---------------------------------------------------------------
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
APIFY_API_KEY = os.environ.get("APIFY_API_KEY", "")

# -- Apify actor IDs --------------------------------------------------------
APIFY_TIKTOK_ACTOR = "clockworks/tiktok-scraper"
APIFY_LINKEDIN_ACTOR = "harvestapi/linkedin-post-search"
APIFY_INSTAGRAM_ACTOR = "apify/instagram-scraper"
APIFY_TWITTER_ACTOR = "xquik/x-tweet-scraper"
APIFY_REDDIT_ACTOR = "automation-lab/reddit-scraper"

# -- Source toggles ---------------------------------------------------------
ENABLE_TIKTOK = True
ENABLE_LINKEDIN = True
ENABLE_INSTAGRAM = True
ENABLE_TWITTER = True
ENABLE_REDDIT = True

# -- Scraping limits (per source, per run) ----------------------------------
APIFY_MAX_RESULTS = 150  # max items per Apify actor run

# -- Claude model & rate-limit ----------------------------------------------
CLAUDE_MODEL = "claude-opus-4-5"
CLAUDE_DELAY_SECONDS = 0.5  # seconds to pause between Claude API calls
