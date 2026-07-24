# LinkedIn Autopilot — Claude Code Initialization Prompt

Paste this entire prompt into Claude Code when you first open the project.

---

## Context

You are helping complete and maintain **LinkedIn Autopilot** — a fully automated daily LinkedIn content pipeline built in Python. The codebase is complete and all 66 tests pass. You are continuing from where the initial build left off.

**Read the PRD first:**
```
cat linkedin-autopilot-PRD.md
```

**Then read the README:**
```
cat README.md
```

**Project root:** `linkedin-autopilot/`

---

## What Is Already Built and Tested

All core modules are complete with 66 passing tests:

- `config/settings.py` — all config, scoring weights, personality prompt (LOCKED)
- `scraper/` — HN, Reddit, RSS, Product Hunt, GitHub Trending + deduplicator
- `scorer/scorer.py` — full scoring engine with diversity pass + format suggestion
- `generator/generator.py` — Groq LLM integration (text, carousel, image)
- `generator/prompts.py` — all prompt templates
- `telegram_bot/bot.py` — full state machine, all 11 user intents
- `telegram_bot/voice_handler.py` — Groq Whisper transcription
- `carousel/carousel_gen.py` — Pillow-based slide renderer → PDF (4 slide types)
- `linkedin/poster.py` — UGC Posts API + PDF carousel upload
- `linkedin/auth.py` — OAuth 2.0 flow
- `main.py` — APScheduler + Telegram bot polling
- `scripts/` — setup, token management, dry run
- `tests/` — 66 tests across 5 modules

---

## What Needs To Be Done Next

Work through these in order. Each phase is independently testable.

---

### PHASE 4: Real API Setup + First Post

**Goal:** Get the pipeline running end-to-end with real credentials.

**Steps:**

1. **Set up `.env`** with real credentials:
   ```bash
   cp .env.example .env
   # Then fill in all values
   ```

2. **Get Groq API key:**
   - Visit https://console.groq.com → API Keys → Create Key
   - Add to `.env` as `GROQ_API_KEY`

3. **Set up Telegram bot:**
   - Message `@BotFather` → `/newbot`
   - Get token → `TELEGRAM_BOT_TOKEN`
   - Get your chat ID → `TELEGRAM_CHAT_ID`
   - See README for exact steps

4. **Set up LinkedIn:**
   - Create app at https://www.linkedin.com/developers/apps
   - Add `LINKEDIN_CLIENT_ID` and `LINKEDIN_CLIENT_SECRET` to `.env`
   - Add redirect URI `http://localhost:8080/callback` in app settings
   - Run: `python scripts/get_linkedin_token.py`
   - This saves `LINKEDIN_ACCESS_TOKEN` and `LINKEDIN_PERSON_URN` automatically

5. **Download fonts:**
   ```bash
   python scripts/setup_fonts.py
   ```

6. **Dry run (no posting):**
   ```bash
   python scripts/test_pipeline_dry_run.py
   ```
   Verify it finds and ranks real stories. Check output looks right.

7. **Test full flow with `RUN_NOW`:**
   ```bash
   RUN_NOW=true python main.py
   ```
   - You should receive Telegram brief
   - Pick a story
   - Approve the draft
   - Verify it posts to LinkedIn

---

### PHASE 5: Deploy to Render.com

**Goal:** Have the pipeline run automatically at 07:00 AM IST every day.

**Steps:**

1. Push to GitHub:
   ```bash
   git init
   git add .
   git commit -m "initial build: linkedin autopilot"
   git remote add origin <your-github-repo-url>
   git push -u origin main
   ```

2. Go to https://render.com → New → Background Worker

3. Connect your GitHub repo

4. Settings:
   - **Build command:** `pip install -r requirements.txt && python scripts/setup_fonts.py`
   - **Start command:** `python main.py`

5. Environment variables: add each key from your `.env` file

6. Persistent disk: enable, mount at `/opt/render/project/src`, 1GB

7. Deploy and check logs

8. Verify: the next 07:00 AM IST, you should get a Telegram message

---

### PHASE 5b: Fix the Handle

In `config/settings.py`, update this line:
```python
CAROUSEL_YOUR_HANDLE = "@yourhandle"   # ← change to your actual LinkedIn handle
```

---

### PHASE 6: Tuning (After 1 Week of Posts)

After 7+ posts, review what you actually liked vs skipped. Then tune:

**Scoring weights** (in `config/settings.py`):
```python
INDIA_BONUS = 30        # increase if India stories aren't surfacing enough
TOOL_LAUNCH_BONUS = 25  # increase if you want more tool launches
AI_KEYWORD_BONUS = 20   # adjust based on your content preferences
```

**Sources** — if a source is noisy, remove it from `RSS_FEEDS` or increase its min score filter in the scraper.

**Format suggestion** — if you find yourself always overriding carousel suggestions, tune the `BENCHMARK_KEYWORDS` list in `config/settings.py`.

---

### PHASE 7: Enhancements (Optional)

These were marked as Phase 2 in the PRD. Build them if you want them:

**Auto-screenshots for image posts:**
- Install Playwright: `pip install playwright && playwright install chromium`
- Create `scraper/screenshot.py` that uses `playwright.async_api` to navigate to the story URL and capture a screenshot
- Integrate in `telegram_bot/bot.py` when `format_type == "image"` and user says `post`
- Skip gracefully if Playwright fails (fall back to manual instruction)

**Analytics dashboard:**
- Read `logs/daily_log.json`
- Build a simple HTML report: posts per week, formats used, sources picked
- Run: `python scripts/generate_report.py` → opens `report.html`

**Story memory / "already covered" filter:**
- Track URLs of stories already posted in `logs/daily_log.json`
- In `scorer.py`, penalise or skip stories whose domain/topic was recently covered
- Prevents covering the same story twice if it stays viral for 2+ days

**Multi-post mode (optional):**
- The PRD specifies 1 post/day. Only build this if you want to post more.
- Add a second pipeline job at 12:00 PM IST
- Use separate state file: `state/today_afternoon.json`

---

## Key Rules — Never Break These

1. **`config/settings.py`** is the single source of truth. Never hard-code values in other files.

2. **`PERSONALITY_PROMPT`** in `config/settings.py` is LOCKED. Do not modify it per-request or dynamically construct it. It is a constant.

3. Every post must go through `generate_post()` in `generator/generator.py`. No prompts constructed elsewhere.

4. LinkedIn is only called after explicit `post` command from the Telegram owner. Never auto-post.

5. `TELEGRAM_CHAT_ID` guard is in `telegram_bot/bot.py`. Never remove it — only the owner's messages are processed.

6. All secrets come from `.env` via `config/settings.py`. Never commit `.env`.

7. Run `pytest tests/ -v` after any change. All 66 tests must pass.

---

## Common Commands

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=. --cov-report=term-missing

# Dry run (no APIs needed)
python scripts/test_pipeline_dry_run.py

# Full run (needs .env)
python main.py

# Force immediate pipeline run
RUN_NOW=true python main.py

# Refresh LinkedIn token (run every 55 days)
python scripts/refresh_linkedin_token.py

# Check file structure
find . -name "*.py" | grep -v __pycache__ | sort
```

---

## Environment Variables Reference

| Variable | Where to get it | Required |
|---|---|---|
| `GROQ_API_KEY` | console.groq.com | Yes |
| `TELEGRAM_BOT_TOKEN` | @BotFather on Telegram | Yes |
| `TELEGRAM_CHAT_ID` | getUpdates API (see README) | Yes |
| `LINKEDIN_ACCESS_TOKEN` | `python scripts/get_linkedin_token.py` | Yes |
| `LINKEDIN_PERSON_URN` | auto-set by above script | Yes |
| `LINKEDIN_CLIENT_ID` | developers.linkedin.com | Yes (for token setup) |
| `LINKEDIN_CLIENT_SECRET` | developers.linkedin.com | Yes (for token setup) |
| `REDDIT_CLIENT_ID` | reddit.com/prefs/apps | Optional |
| `REDDIT_CLIENT_SECRET` | reddit.com/prefs/apps | Optional |
| `POST_TIME` | Set in .env (default: 07:00) | Optional |
| `RUN_NOW` | Set to `true` to run immediately | Optional |

---

## Architecture Summary

```
main.py (scheduler + bot polling)
    │
    ├── 07:00 AM cron → main_pipeline()
    │   ├── scraper/scraper.py → scrape_all()
    │   │   ├── hackernews.py, reddit.py, rss_feeds.py
    │   │   ├── producthunt.py, github_trending.py
    │   │   └── deduplicator.py
    │   ├── scorer/scorer.py → rank_and_pick()
    │   ├── generator/generator.py → generate_morning_brief()
    │   └── telegram_bot/bot.py → send_message()
    │
    └── Telegram polling → _handle_message()
        ├── Parse pick (1/2/3 + angle)
        ├── Voice → voice_handler.py → Groq Whisper
        ├── generator.py → generate_post()
        ├── Send draft → wait for "post"
        ├── carousel_gen.py → PDF (if carousel)
        └── linkedin/poster.py → publish
```

---

Start with Phase 4 (real API setup). The dry run will confirm everything works before you touch LinkedIn.
