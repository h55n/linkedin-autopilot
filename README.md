# LinkedIn Autopilot

A fully automated daily LinkedIn content pipeline with a single human checkpoint — you, on Telegram, every morning.

**Total time per day: under 3 minutes.**

---

## How It Works

```
07:00 AM IST  → System scrapes HN, Reddit, RSS feeds, Product Hunt, GitHub Trending
               → Scores and ranks top stories
               → Sends you 3 picks on Telegram

You reply     → "2, this matters because most AI tools ignore Indian languages"
               → System generates post in your voice
               → Sends you draft for approval

You say "post" → Published to LinkedIn
               → Confirmation with URL sent back
```

---

## Setup (One-Time)

### 1. Clone and install

```bash
git clone <your-repo-url>
cd linkedin-autopilot
pip install -r requirements.txt
python scripts/setup_fonts.py   # downloads Inter + Playfair Display
```

### 2. Copy env template

```bash
cp .env.example .env
```

### 3. Get your API keys

**Groq (LLM + Whisper):**
1. Go to [console.groq.com](https://console.groq.com)
2. API Keys → Create Key
3. Paste into `.env` as `GROQ_API_KEY`

**Telegram Bot:**
1. Open Telegram → search `@BotFather`
2. `/newbot` → follow prompts → copy token
3. Paste as `TELEGRAM_BOT_TOKEN`
4. Message your new bot once, then visit:
   `https://api.telegram.org/bot{TOKEN}/getUpdates`
5. Find `"chat":{"id":XXXXXXXX}` → paste as `TELEGRAM_CHAT_ID`

**LinkedIn:**
1. Go to [developers.linkedin.com](https://www.linkedin.com/developers/apps)
2. Create app → add products: **Share on LinkedIn** + **Sign In with LinkedIn**
3. Under App settings, add redirect URL: `http://localhost:8080/callback`
4. Add to `.env`: `LINKEDIN_CLIENT_ID` and `LINKEDIN_CLIENT_SECRET`
5. Run the auth flow:
   ```bash
   python scripts/get_linkedin_token.py
   ```
   This opens a browser, you approve, token is saved automatically.

**Reddit (optional — higher rate limits):**
1. Go to [reddit.com/prefs/apps](https://www.reddit.com/prefs/apps)
2. Create app → type: **script**
3. Paste `client_id` and `client_secret` into `.env`

---

## Running Locally

```bash
# Dry run (no Telegram or LinkedIn — just see what stories would be picked)
python scripts/test_pipeline_dry_run.py

# Full pipeline (starts at 07:00 AM IST daily)
python main.py

# Force-run pipeline immediately (for testing)
RUN_NOW=true python main.py
```

---

## Telegram Commands

| Command | What it does |
|---|---|
| `1` / `2` / `3` | Pick a story |
| `2, your take here` | Pick + add your angle |
| Voice note | Pick a story + speak your angle |
| `post` | Publish the draft to LinkedIn |
| `edit make it shorter` | Regenerate with instruction |
| `carousel` / `image` / `text` | Switch format |
| `skip` | Skip today |
| `cancel` | Cancel after draft |
| `status` | What's the system doing now |
| `log` | Last 7 days of posts |

---

## Deployment on Render.com (Free)

1. Push your repo to GitHub (`.env` is in `.gitignore` — never commits)
2. Go to [render.com](https://render.com) → New → Background Worker
3. Connect your GitHub repo
4. Build command: `pip install -r requirements.txt && python scripts/setup_fonts.py`
5. Start command: `python main.py`
6. Set all environment variables from your `.env` in Render's dashboard
7. Add a persistent disk (1GB free): mount path `/opt/render/project/src`
8. Deploy

Or use `render.yaml` (already included) for one-click deploy.

---

## LinkedIn Token Refresh (Every 60 Days)

LinkedIn access tokens expire every 60 days. The system will warn you at 55 days via Telegram.

When you get the warning:
```bash
python scripts/refresh_linkedin_token.py
```

---

## Running Tests

```bash
# All tests
pytest tests/ -v

# Single module
pytest tests/test_scorer.py -v

# With coverage
pytest tests/ --cov=. --cov-report=term-missing

# Integration only
pytest tests/test_pipeline.py -v -s
```

---

## Project Structure

```
linkedin-autopilot/
├── main.py                    # Entry point — scheduler + Telegram bot
├── config/settings.py         # ALL config, weights, personality prompt
├── scraper/                   # Data collection
│   ├── scraper.py             # Orchestrates all sources
│   ├── deduplicator.py        # URL + fuzzy title dedup
│   └── sources/               # HN, Reddit, RSS, Product Hunt, GitHub
├── scorer/scorer.py           # Scoring, ranking, diversity pass
├── generator/                 # Groq LLM calls
│   ├── generator.py           # generate_post(), generate_morning_brief()
│   └── prompts.py             # All prompt templates (constants)
├── telegram_bot/              # Daily interface
│   ├── bot.py                 # State machine, message handlers
│   ├── voice_handler.py       # Voice note → Groq Whisper
│   └── messages.py            # All message templates
├── carousel/carousel_gen.py   # Pillow-based slide renderer → PDF
├── linkedin/                  # LinkedIn API
│   ├── poster.py              # UGC Posts API, PDF upload
│   └── auth.py                # OAuth 2.0 flow
├── scripts/                   # One-time setup + utilities
├── tests/                     # 66 tests across 5 modules
├── state/today.json           # Pipeline state (auto-managed)
└── logs/                      # daily_log.json, streak.json, errors.log
```

---

## Customisation

Everything is in `config/settings.py`:

- **`POST_TIME`** — change the daily posting time (default 07:00)
- **`INDIA_KEYWORDS`** — add cities or publications you follow
- **`CAROUSEL_YOUR_HANDLE`** — your LinkedIn handle for carousel footers
- **`PERSONALITY_PROMPT`** — the locked writing voice (edit carefully)
- **Scoring weights** — `INDIA_BONUS`, `TOOL_LAUNCH_BONUS`, etc.

---

## Cost

| Component | Cost |
|---|---|
| Groq LLM + Whisper | Free tier (covers ~₹0 / day) |
| Telegram Bot API | Free |
| LinkedIn API | Free |
| Render.com hosting | Free tier |
| **Total** | **₹0 / month** |
