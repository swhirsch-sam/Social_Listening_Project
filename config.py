# config.py - centralised settings for Social Listening MVP
# -------------------------------------------------------------------------
# API keys are read from environment variables (set in Streamlit Secrets or
# your shell). Never hardcode real secrets in this file.

import os

# -- API Keys ---------------------------------------------------------------
ANTHROPIC_API_KEY  = os.environ.get("ANTHROPIC_API_KEY", "")
APIFY_API_KEY      = os.environ.get("APIFY_API_KEY", "")
FIRECRAWL_API_KEY  = os.environ.get("FIRECRAWL_API_KEY", "")
SERPER_API_KEY     = os.environ.get("SERPER_API_KEY", "")

# -- Apify actor IDs --------------------------------------------------------
APIFY_TIKTOK_ACTOR   = "clockworks/tiktok-scraper"
APIFY_LINKEDIN_ACTOR = "harvestapi/linkedin-post-search"

# -- Source toggles ---------------------------------------------------------
ENABLE_TIKTOK     = True
ENABLE_LINKEDIN   = True
ENABLE_FIRECRAWL  = True   # toggle web search (now powered by Serper)

# -- Scraping limits (per source, per run) ----------------------------------
APIFY_MAX_RESULTS      = 250   # max items per Apify actor run
FIRECRAWL_MAX_RESULTS  = 250   # max web/news results per search

# -- Claude model & rate-limit ----------------------------------------------
CLAUDE_MODEL          = "claude-opus-4-5"
CLAUDE_DELAY_SECONDS  = 0.5   # seconds to pause between Claude API calls
