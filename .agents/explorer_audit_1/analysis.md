# Code Architecture & Structure Audit Report

**Project**: LinkedIn Autopilot (`d:\ANTIGRAVITY\linkedin-autopilot`)  
**Auditor**: Explorer 1 (Architecture & Structure Auditor)  
**Date**: 2026-08-09  

---

## Executive Summary

LinkedIn Autopilot is a Python-based automated content curation and publishing platform. It scrapes tech news, AI developments, tool launches, and opportunities across multiple sources (HackerNews, Reddit, RSS feeds, Product Hunt, GitHub Trending), ranks stories using a multi-criteria scoring algorithm, formats drafts using multi-provider LLM APIs (Nvidia NIM, Mistral, Groq), generates PDF carousels or Playwright screenshots, and publishes directly to LinkedIn with an interactive Telegram bot control plane.

The codebase is well-structured overall with clean module separation (`scraper`, `scorer`, `generator`, `carousel`, `linkedin`, `telegram_bot`, `utils`). However, the audit revealed several critical architectural smells, root-level script clutter, a pytest collection blocker (`test_runs.py`), state-coupling issues, and leftover binary files.

---

## 1. Repository Structure & Entry Points

### Repository Layout
```
linkedin-autopilot/
├── .github/workflows/         # Serverless GitHub Actions workflows
│   ├── morning-pipeline.yml   # Daily scheduled morning pipeline (07:00 IST / 01:30 UTC)
│   └── bot-session.yml        # Single-shot Telegram webhook session runner
├── carousel/                  # Carousel PDF/PNG generation engine
│   ├── assets/fonts/          # Custom TTF fonts (Caprasimo, Inter)
│   ├── output/                # Output PDF slides and Playwright screenshots
│   └── carousel_gen.py        # Pillow-based 1080x1080 canvas renderer & PDF compiler
├── config/                    # Global settings & single source of truth
│   └── settings.py            # Constants, scoring weights, prompts, keyword lists
├── generator/                 # LLM generation & prompt engineering
│   ├── generator.py           # LLM caller (Nvidia NIM -> Mistral -> Groq) & formatting
│   └── prompts.py             # Prompt templates (text, carousel, image, intent parsing)
├── linkedin/                  # LinkedIn API integration
│   ├── auth.py                # OAuth token retrieval & refresh logic
│   └── poster.py              # UGC post, image upload, carousel PDF upload API client
├── logs/                      # Log file persistence
│   ├── daily_log.json         # Post log history
│   ├── errors.log             # Exception tracebacks
│   └── streak.json            # Posting streak counter
├── scorer/                    # Story ranking & mix pass engine
│   └── scorer.py              # Pure scoring functions, keyword bonus calculation, mix pass
├── scraper/                   # Content aggregation pipeline
│   ├── deduplicator.py        # URL canonicalization & title fuzzy matching
│   ├── enricher.py            # Article full-text extraction (Trafilatura / BeautifulSoup)
│   ├── researcher.py          # DuckDuckGo live web research synthetic story builder
│   ├── scraper.py             # Scraper orchestrator with isolated source exception handling
│   └── sources/               # Source-specific scraper implementations
│       ├── github_trending.py # GitHub Trending HTML scraper
│       ├── hackernews.py      # HackerNews Firebase REST API scraper
│       ├── producthunt.py     # Product Hunt RSS feed parser
│       ├── reddit.py          # Reddit JSON/OAuth API scraper (11 subreddits)
│       └── rss_feeds.py       # India & global tech RSS feed parser
├── scripts/                   # CLI scripts & deployment runners
│   ├── get_linkedin_token.py  # Local OAuth flow helper
│   ├── get_linkedin_urn.py    # LinkedIn person URN fetcher
│   ├── refresh_linkedin_token.py # Token refresh script
│   ├── run_bot_session.py     # Single-shot GHA Telegram webhook processor
│   ├── run_pipeline.py        # Single-shot GHA morning pipeline runner
│   ├── setup_fonts.py         # Font downloader script
│   ├── setup_gist_state.py    # GitHub Gist state initialization script
│   ├── test_pipeline_dry_run.py # Dry-run test pipeline
│   └── test_send_all_formats.py # Multi-format Telegram test sender
├── state/                     # Local disk state storage
│   ├── linkedin_token_date.txt# Token creation timestamp
│   └── today.json             # Daily workflow execution state
├── telegram_bot/              # Telegram interaction interface
│   ├── bot.py                 # Telegram bot handlers & command processors
│   ├── messages.py            # Telegram user message templates
│   ├── screenshotter.py       # Playwright automated screenshot capturer
│   └── voice_handler.py       # Groq Whisper voice note transcription
├── tests/                     # Automated unit and integration test suite
│   ├── conftest.py            # Test fixtures and mock story generators
│   ├── test_generator.py      # Tests for generator module
│   ├── test_linkedin.py       # Tests for LinkedIn API poster
│   ├── test_pipeline.py       # Tests for main pipeline orchestration
│   ├── test_scorer.py         # Tests for scoring rules & mix pass
│   ├── test_scraper.py        # Tests for deduplication and scrapers
│   └── test_telegram.py       # Tests for Telegram bot handlers
├── utils/                     # Cross-cutting utility modules
│   ├── helpers.py             # Dual state storage (File vs Gist), URL parsing, date helpers
│   └── logger.py              # Structured logging & error recording
├── main.py                    # Legacy continuous server mode entry point (APScheduler + bot loop)
├── render.yaml                # Render build & deployment specification
├── requirements.txt           # Pinned Python dependencies
└── ORIGINAL_REQUEST.md        # Original user request instructions
```

### Entry Points Overview
1. **GitHub Actions Morning Pipeline Entry Point**: `scripts/run_pipeline.py`
   - Invoked by `.github/workflows/morning-pipeline.yml`.
   - Executes `main_pipeline()` once and exits (`STATE_BACKEND=gist`).
2. **GitHub Actions Webhook Entry Point**: `scripts/run_bot_session.py`
   - Invoked by `.github/workflows/bot-session.yml`.
   - Parses `TELEGRAM_PAYLOAD` JSON, processes Telegram user response, updates state, and exits.
3. **Local / Render Continuous Server Entry Point**: `main.py`
   - Runs `AsyncIOScheduler` for morning pipeline (07:00 IST), reminder (08:00 IST), and token check (06:00 IST).
   - Runs `aiohttp` web server on `$PORT` (default 8080) for Render health checks.
   - Starts long-polling Telegram bot via `python-telegram-bot`.
4. **CLI Utility Scripts**:
   - `scripts/refresh_linkedin_token.py`: Manually or automatically refreshes OAuth access token.
   - `scripts/setup_gist_state.py`: Initializes state Gist on GitHub.
   - `scripts/setup_fonts.py`: Downloads required fonts for carousel generator.

---

## 2. Complete Feature Inventory

| Feature | Description | Primary Location | Current State |
|---|---|---|---|
| **Multi-Source News Scraping** | Aggregates tech news from HackerNews, Reddit (11 subreddits), 10 RSS feeds, Product Hunt RSS, and GitHub Trending. | `scraper/sources/*`, `scraper/scraper.py` | Operational (Isolated try-except per source) |
| **Story Deduplication** | Deduplicates stories by canonical URL (against current & past state) and fuzzy title ratio (`thefuzz` threshold 85). | `scraper/deduplicator.py` | Operational |
| **Article Context Enrichment** | Fetches full article content using `trafilatura` and HTML stripping to supply context to LLMs. | `scraper/enricher.py` | Operational |
| **On-Demand Web Research** | Conducts live web search via `duckduckgo_search` (`/research` command) and builds synthetic story dicts. | `scraper/researcher.py` | Operational |
| **Multi-Criteria Scoring Engine** | Ranks stories using upvote scores, recency multipliers, comment velocity thresholds, keyword bonuses, and noise penalties. | `scorer/scorer.py` | Operational |
| **Diversity Mix Pass** | Enforces balanced top 3 selection (1 Opportunity, 1 India story, 1 General AI/Tool story). | `scorer/scorer.py` | Operational |
| **Format Suggestion** | Recommends post format (`text`, `carousel`, `image`) based on story attributes (e.g. GitHub repos -> image). | `scorer/scorer.py` | Operational |
| **Multi-Provider LLM Generator** | Generates posts/carousels using fallback chain: Nvidia NIM (`llama-3.1-70b`) -> Mistral (`mistral-large`) -> Groq (`llama-3.3-70b`). | `generator/generator.py`, `prompts.py` | Operational |
| **Interactive Post Editing** | Regenerates post text using user edit instructions via natural language prompts. | `generator/generator.py` | Operational |
| **Natural Language Intent Parsing** | LLM-backed fallback parsing to map ambiguous Telegram text/voice replies to story selections. | `generator/generator.py`, `telegram_bot/bot.py` | Operational |
| **Pillow Carousel PDF Generator** | Renders 1080x1080px branded slide PNGs with custom fonts, colors, pilmoji, and compiles multi-page PDF. | `carousel/carousel_gen.py` | Operational |
| **Automated Web Screenshots** | Captures headless Chromium screenshots of target URLs using Playwright for image posts. | `telegram_bot/screenshotter.py` | Operational |
| **LinkedIn REST API Publishing** | Publishes text, image, and document carousel posts via LinkedIn UGC Posts API v2 with automatic token refresh. | `linkedin/poster.py`, `auth.py` | Operational |
| **Telegram Bot Interface** | Interactive control plane for morning brief delivery, post approval, format switching, edit instructions, and status. | `telegram_bot/bot.py`, `messages.py` | Operational |
| **Whisper Voice Note Transcription** | Transcribes Telegram voice notes using Groq Whisper API (`whisper-large-v3`). | `telegram_bot/voice_handler.py` | Operational |
| **Dual-Backend State Management** | Abstraction layer for reading/writing state to local JSON file (`state/today.json`) or remote GitHub Gist API. | `utils/helpers.py` | Operational |
| **Dual-Deployment Mode** | Supports both serverless execution via GitHub Actions workflows and continuous daemon execution via `main.py`. | `main.py`, `scripts/*`, `.github/workflows/*` | Operational |

---

## 3. Architecture Audit Findings

### Strengths
1. **Clear Modular Separation**: Codebase follows clean separation of concerns. `scraper` handles fetching, `scorer` handles ranking, `generator` handles LLM interactions, `carousel` handles slide rendering, `linkedin` handles API transport, and `telegram_bot` handles user interface.
2. **Scraper Fault Isolation**: `scrape_all()` wraps each source scraper in isolated `try...except` blocks, guaranteeing that a failure or timeout in one scraper (e.g. Reddit rate limit or invalid RSS feed) never crashes the entire morning pipeline.
3. **Resilient LLM Strategy**: Multi-provider fallback chain (Nvidia NIM -> Mistral -> Groq) ensures post generation succeeds even if one provider API is degraded or rate-limited.
4. **Dual State Abstraction**: `utils/helpers.py` provides transparent state read/write API (`read_state()`, `update_state()`) switching between local disk and GitHub Gist based on `STATE_BACKEND` env var.
5. **Side-Effect Free Scoring**: `scorer/scorer.py` consists of pure functions that do not perform network or disk I/O, allowing instantaneous unit testing.

### Architectural Smells & Issues

#### 1. Pytest Test Discovery Blocker (`test_runs.py`)
- **Location**: `d:\ANTIGRAVITY\linkedin-autopilot\test_runs.py`
- **Issue**: Root-level script named `test_runs.py` is picked up by `pytest` default file discovery. Upon import during collection, it executes synchronous unauthenticated HTTP calls to GitHub API without a `User-Agent` header (`urllib.request.urlopen(...)`).
- **Impact**: Running `pytest` from repository root hangs or fails during test collection.
- **Fix**: Move or rename `test_runs.py` to `scripts/check_github_runs.py` or `scratch/`.

#### 2. Root Directory Clutter & Leftover Debug Scripts
- **Location**: `auto_oauth.py`, `extract_cookies.py`, `headless_oauth.py`, `take_screenshot.py`, `Cookies_copy.db`
- **Issue**: Debugging and GUI automation scripts reside directly in the root directory.
  - `auto_oauth.py` and `take_screenshot.py` contain hardcoded local Windows user paths (`C:\Users\hassa\.gemini\antigravity-ide\brain\...`) and import `pyautogui`, which fails in headless Linux environments.
  - `extract_cookies.py` attempts to decrypt local Chrome DPAPI cookies.
  - `Cookies_copy.db` is a 120KB binary SQLite database file checked into git.
- **Impact**: Pollutes repository root, violates project structure guidelines, introduces OS-specific non-portable dependencies.
- **Fix**: Remove `Cookies_copy.db` and relocate scratch scripts to `scratch/` or `scripts/`.

#### 3. State Side-Effects in Deduplication
- **Location**: `scraper/deduplicator.py:20`
- **Issue**: `deduplicate()` calls `read_state()` directly inside its filtering loop to check `past_urls`.
- **Impact**: High coupling between the deduplication logic and the state backend/filesystem. Makes unit testing non-deterministic unless state is mocked.
- **Fix**: Pass `past_urls: set[str]` as an explicit parameter into `deduplicate(stories, past_urls)`.

#### 4. Inline Imports & Coupling in `main.py`
- **Location**: `main.py:94-97`
- **Issue**: `main_pipeline()` contains inline conditional imports inside the `AUTOPILOT_MODE` block:
  ```python
  from generator.generator import generate_post
  from linkedin.poster import post_text_to_linkedin, post_carousel_to_linkedin, post_image_to_linkedin
  from carousel.carousel_gen import generate_carousel_pdf
  from telegram_bot.screenshotter import take_screenshots_for_story
  ```
- **Impact**: Hidden dependencies, harder to trace imports, potential circular import workarounds.
- **Fix**: Move imports to top level or refactor pipeline services into clean dependency-injected modules.

#### 5. Scraper Timeouts & Blocking Sleep Calls
- **Location**: `scraper/sources/reddit.py:82` (`time.sleep(60)`), `scraper/sources/hackernews.py:39` (`time.sleep(...)`)
- **Issue**: Synchronous `time.sleep()` calls inside scraper routines block the event loop in `main.py` daemon mode.
- **Impact**: Can delay async scheduler tasks or web server responsiveness.
- **Fix**: Replace synchronous sleep with non-blocking rate limiters or retry decorators (`tenacity`).

---

## 4. Test Suite and Build Analysis

### Test Suite Execution Summary
- **Test Framework**: `pytest 8.2.0`, `pytest-cov 5.0.0`, `pytest-asyncio 0.23.7`
- **Test Location**: `tests/` directory
- **Test Execution Command**: `pytest tests/`

```
============================= test session starts =============================
platform win32 -- Python 3.11.15, pytest-8.2.0, pluggy-1.6.0
rootdir: D:\ANTIGRAVITY\linkedin-autopilot
plugins: anyio-4.4.0, asyncio-0.23.7, cov-5.0.0
collected 66 items

tests\test_generator.py ................                                 [ 24%]
tests\test_linkedin.py ........                                          [ 36%]
tests\test_pipeline.py ........                                          [ 48%]
tests\test_scorer.py .............                                       [ 68%]
tests\test_scraper.py ...........                                        [ 84%]
tests\test_telegram.py ....                                              [100%]

============================== 66 passed in 9.84s ==============================
```

### Coverage Analysis
- **Scorer Tests (`test_scorer.py`)**: 13 tests covering scoring logic, keyword bonuses, recency decay multipliers, noise penalties, mix pass rules, and format recommendations.
- **Generator Tests (`test_generator.py`)**: 16 tests covering post generation, lowercasing rules, em-dash & exclamation mark bans, carousel JSON schema validation, fallback mechanisms, and morning brief text formatting.
- **LinkedIn Poster Tests (`test_linkedin.py`)**: 8 tests covering UGC API call payloads, PDF carousel registration & binary upload sequence, URL formatting, and token age check.
- **Pipeline Tests (`test_pipeline.py`)**: 8 tests covering end-to-end execution, double-run prevention, state serialization, and autopilot mode execution.
- **Scraper Tests (`test_scraper.py`)**: 17 tests covering deduplication algorithms, fuzzy title matching, RSS/HN/Reddit source parsing, and article enrichment.
- **Telegram Bot Tests (`test_telegram.py`)**: 4 tests covering command handlers, pick parsing, status formatting, and log rendering.

### Build & Dependencies
- `requirements.txt`: Cleanly pinned packages (`apscheduler`, `python-telegram-bot`, `groq`, `feedparser`, `thefuzz`, `Pillow`, `img2pdf`, `playwright`, `tenacity`, `trafilatura`, `pytest`).
- Build verification: Clean python syntax across all source files.

---

## 5. Recommended Architectural Refactoring Milestones

### Milestone 1: Repository Hygiene & Test Harness Fixes (Priority: High)
1. **Fix Pytest Discovery**: Rename root `test_runs.py` to `scripts/check_github_runs.py` so running `pytest` works cleanly without arguments.
2. **Root Cleanup**: Move `auto_oauth.py`, `extract_cookies.py`, `headless_oauth.py`, and `take_screenshot.py` into `scratch/` or `scripts/`.
3. **Remove Binary Artifacts**: Remove `Cookies_copy.db` from repository root and add `*.db` to `.gitignore`.

### Milestone 2: Code Decoupling & Pure Logic Refactoring (Priority: Medium)
1. **Deduplicator Decoupling**: Modify `scraper/deduplicator.py` so `deduplicate(stories, past_urls)` takes `past_urls` as an argument instead of calling `read_state()` inside the function.
2. **Top-Level Import Hygiene**: Eliminate inline imports in `main.py` and standardise imports across modules.
3. **Configuration Schema Validation**: Add a configuration validator function in `config/settings.py` to verify environment variables on startup.

### Milestone 3: Async & Transport Optimization (Priority: Low)
1. **Non-blocking Rate Limiting**: Refactor synchronous `time.sleep()` calls in `scraper/sources/reddit.py` and `hackernews.py` to use non-blocking async sleeps or rate limiters.
2. **Structured Service Interface**: Wrap LinkedIn poster and Telegram bot notifications in generic interface adapters (`NotificationProvider`, `PublishingProvider`) for cleaner unit testing and mockability.
