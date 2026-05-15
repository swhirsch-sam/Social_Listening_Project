# config.py - centralised settings for Social Listening MVP
# -------------------------------------------------------------------------
# Fill in every value marked TODO before running app.py.
# This file is in .gitignore - NEVER commit real secrets to a public repo.

# -- API Keys ---------------------------------------------------------------
ANTHROPIC_API_KEY  = "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"
APIFY_API_KEY      = "apify_api_AgNBEW5Ylr1sabl0EOcMyeiFzuh1P92Duwvp"
FIRECRAWL_API_KEY  = "fc-ed8e643b1de944238ee4286d39f8aa3b"

# -- Apify actor IDs --------------------------------------------------------
APIFY_TIKTOK_ACTOR   = "futurizerush/tiktok-comment-scraper"
APIFY_LINKEDIN_ACTOR = "supreme_coder/linkedin-post"

# -- Source toggles ---------------------------------------------------------
ENABLE_TIKTOK    = True
ENABLE_LINKEDIN  = True
ENABLE_FIRECRAWL = True

# -- Scraping limits --------------------------------------------------------
APIFY_MAX_RESULTS    = 50   # items per Apify actor run
FIRECRAWL_MAX_RESULTS = 20  # web/news results per search

# -- Claude model & rate-limit ----------------------------------------------
CLAUDE_MODEL          = "claude-opus-4-5"
CLAUDE_DELAY_SECONDS  = 0.5  # seconds to pause between Claude API calls
