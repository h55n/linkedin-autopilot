# Project: LinkedIn Autopilot Codebase Refactoring & Optimization

## Architecture
- `config/`: Environment configuration & settings loading
- `scraper/`: News & trend scraping from HackerNews, Reddit, ProductHunt, GitHub Trending, RSS feeds + Deduplication & Enrichment
- `scorer/`: Multi-criteria scoring, AI relevance classification, diversity mix selection
- `generator/`: Multi-provider LLM post generation (Nvidia NIM -> Mistral -> Groq fallback chain)
- `carousel/`: Pillow PDF carousel slide generator
- `linkedin/`: OAuth authentication & UGC API post publisher
- `telegram_bot/`: Interactive Telegram bot, voice handler, Playwright web screenshotter
- `utils/`: Logging, state persistence, atomic helpers, age formatting

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | Missing `os` Import Fix | Fix missing `import os` in `generator/generator.py` | M1 | audit |
| 2 | Word-Boundary Regex Scorer | Replace naive `kw in text` with regex word boundaries in `scorer/scorer.py` | M1 | audit |
| 3 | GitHub Star Parsing | Fix `"12.35k"` star math bug in `scraper/sources/github_trending.py` | M1 | audit |
| 4 | Null Timestamp Safety | Handle `None` timestamps in `utils/helpers.py:timestamp_to_age_hours` | M1 | audit |
| 5 | Lazy Groq Client | Convert global `Groq()` instantiation to lazy getter in `telegram_bot/voice_handler.py` | M1 | audit |
| 6 | Exception Status Reset | Add `try...finally` block in `main.py` to prevent state status lockups | M1 | audit |
| 7 | Pytest Collection Fix | Move/refactor `test_runs.py` so root `pytest` doesn't hang on import | M2 | audit |
| 8 | Pure Deduplication Logic | Decouple `deduplicate()` from direct `read_state()` in `scraper/deduplicator.py` | M2 | audit |
| 9 | Shared Helper DRY | Extract `_is_tool_launch` and `_detect_region` into `utils/helpers.py` | M2 | audit |
| 10| Atomic File Operations | Implement atomic write helper for JSON state and logs in `utils/helpers.py` | M2 | audit |
| 11| Repository Root Hygiene | Move scratch scripts to `scripts/scratch/` and clean `Cookies_copy.db` | M2 | audit |
| 12| Concurrent Scraper Loop | Implement `ThreadPoolExecutor` parallel source execution in `scraper/scraper.py` | M3 | audit |
| 13| Async/Concurrent HN & Reddit | Parallelize HN top story requests & fix Reddit 60s blocking sleep | M3 | audit |
| 14| HTTP Session Reuse | Implement `requests.Session()` connection pooling across scrapers | M3 | audit |
| 15| Optimized Deduplication | Optimize $O(N^2)$ fuzzy deduplication loop with pre-lowercasing & length filter | M3 | audit |
| 16| E2E Verification & Test Suite | Run full `pytest` suite to verify zero regressions | M4 | audit |
| 17| Project Changelog | Update `changelog.md` at root with detailed modification records | M4 | audit |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | Critical Bug Fixes & Code Safety | Features 1-6 | None | DONE |
| M2 | Architecture Decoupling & Hygiene | Features 7-11 | M1 | DONE |
| M3 | Performance Optimization | Features 12-15 | M2 | DONE |
| M4 | Verification & Changelog | Features 16-17 | M3 | DONE |

## Interface Contracts
### `scorer/scorer.py`
- `score_stories(stories: list[dict]) -> list[dict]`: Preserves return structure, uses `r"\b" + re.escape(kw) + r"\b"` matching.

### `scraper/deduplicator.py`
- `deduplicate(stories: list[dict], past_urls: set[str] = None) -> list[dict]`: Accepts `past_urls` explicitly, defaults to state lookup if omitted for backwards compatibility.

### `utils/helpers.py`
- `timestamp_to_age_hours(ts: float | int | None) -> float`: Returns `0.0` if `ts` is `None`.
- `atomic_write_json(file_path: str, data: dict | list)`: Writes to temporary file and atomically replaces destination.
