# Social Listening MVP

Pulls brand mentions from **TikTok** (Apify), **LinkedIn** (Apify), and **web/news** (Firecrawl), runs each item through **Claude** for sentiment analysis + key-topic extraction, and writes every result into a **Google Sheet**.

---

## Architecture

```
Apify  (clockworks/tiktok-scraper)            ──┐
Apify  (supreme_coder/linkedin-post)           ──┼──► main.py ──► Claude API ──► Google Sheets
Firecrawl (web/news search)                    ──┘
```

---

## Quick Start

### 1. Clone & install

```bash
git clone https://github.com/swhirsch-sam/Social_Listening_Project.git
cd Social_Listening_Project
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
```

### 2. Configure credentials

Open `config.py` and fill in every **TODO** value:

| Variable | Where to get it |
|---|---|
| `ANTHROPIC_API_KEY` | [console.anthropic.com](https://console.anthropic.com) |
| `APIFY_API_KEY` | [console.apify.com](https://console.apify.com) → Settings → API |
| `FIRECRAWL_API_KEY` | [firecrawl.dev](https://firecrawl.dev) dashboard |
| `GOOGLE_SHEET_ID` | Long ID in your Sheet URL (between `/d/` and `/edit`) |
| `GOOGLE_CREDENTIALS_FILE` | Path to service-account JSON key (default: `credentials.json`) |
| `BRAND_KEYWORDS` | List of brand/product terms to search for |

### 3. Google Sheets service account

1. Go to [Google Cloud Console](https://console.cloud.google.com) → project **social-listening-mvp-496415**
2. Enable **Google Sheets API** and **Google Drive API**
3. Create a **Service Account** → download the JSON key → save as `credentials.json` (project root)
4. Open your Google Sheet → click **Share** → add the service account email → grant **Editor** access

### 4. Run

```bash
python main.py
```

---

## Output columns (Google Sheet)

| Timestamp | Source | Platform | Author | Content | Sentiment | Confidence | Key Topics | URL | Raw JSON |
|---|---|---|---|---|---|---|---|---|---|

- **Sentiment**: `positive` / `negative` / `neutral`
- **Confidence**: `high` / `medium` / `low`
- **Key Topics**: up to 5 comma-separated phrases

---

## Configuration (`config.py`)

| Setting | Default | Description |
|---|---|---|
| `BRAND_KEYWORDS` | `[]` | Terms to search across all sources |
| `ENABLE_TIKTOK` | `True` | Toggle TikTok scraper |
| `ENABLE_LINKEDIN` | `True` | Toggle LinkedIn scraper |
| `ENABLE_FIRECRAWL` | `True` | Toggle web/news search |
| `APIFY_MAX_RESULTS` | `50` | Items per Apify run |
| `FIRECRAWL_MAX_RESULTS` | `20` | Results per keyword |
| `CLAUDE_MODEL` | `claude-opus-4-5` | Claude model to use |
| `CLAUDE_DELAY_SECONDS` | `0.5` | Pause between API calls |

---

## Security

`credentials.json` and `config.py` are listed in `.gitignore` — never commit them to a public repository.
