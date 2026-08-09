# Changelog

All notable changes, bug fixes, architectural refactors, and performance optimizations made to the LinkedIn Autopilot project during the audit are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

---

## [Unreleased] - 2026-08-09

### Milestone 1: Critical Bug Fixes & Code Safety

#### Added
- **`utils/helpers.py`**: Added explicit null handling in `timestamp_to_age_hours(ts)` to safely return `0.0` when `ts` is `None` or invalid, preventing `TypeError` during story age computation.
- **`telegram_bot/voice_handler.py`**: Implemented lazy `Groq` client initialization via getter function `_get_groq_client()` to prevent module load crashes when `GROQ_API_KEY` or `groq` package is uninitialized.

#### Fixed
- **`generator/generator.py`**: Added missing `import os` statement required for environment variable lookups and file system operations.
- **`scorer/scorer.py`**: Replaced naive substring keyword matching (`kw in text`) with regex word-boundary matching (`r"\b" + re.escape(kw) + r"\b"`) to eliminate false-positive scoring (e.g. matching "ai" inside "paid" or "chair").
- **`scraper/sources/github_trending.py`**: Corrected star parsing math for formatted string counts like `"12.35k"` to correctly convert to `12350` instead of dropping decimals or crashing.
- **`main.py`**: Wrapped execution flow in a `try...finally` block to ensure system state (e.g. `running` status) is reliably reset on execution finish or unhandled exceptions.

---

## Milestone 2: Architecture Decoupling & Root Hygiene

#### Added
- **`utils/helpers.py`**: Extracted shared helper functions `is_tool_launch` and `detect_region` (DRY refactoring across modules).
- **`utils/helpers.py` & `utils/logger.py`**: Created `atomic_write_json` helper function to perform atomic JSON writes via temp file replacement, preventing data corruption on interrupted file writes.

#### Fixed
- **`test_runs.py`**: Fixed pytest collection issue by decoupling standalone test runner execution from pytest test discovery mechanisms.
- **`scraper/deduplicator.py`**: Decoupled `deduplicate()` from tight coupling to state loading by accepting an explicit `past_urls: set[str] = None` parameter.

#### Removed / Security & Hygiene
- **Repository Root Hygiene**: Relocated scratch/utility scripts to `scripts/scratch/` directory.
- **`Cookies_copy.db`**: Removed unversioned binary database artifact from repository root.

---

## Milestone 3: Performance Optimization & Concurrency

#### Changed / Performance
- **`scraper/scraper.py`**: Implemented concurrent multi-source scraping using `ThreadPoolExecutor(max_workers=5)`, dramatically reducing aggregate scrape times across HackerNews, Reddit, ProductHunt, GitHub Trending, and RSS.
- **`scraper/sources/hackernews.py`**: Parallelized individual story detail fetching with `ThreadPoolExecutor(max_workers=10)` instead of sequential HTTP requests.
- **`scraper/sources/reddit.py`**: Implemented non-blocking 429 rate limit backoff and retry handling to prevent thread stalling.
- **`utils/helpers.py`**: Added `get_http_session()` for HTTP connection pooling and TCP keep-alive re-use across all scrapers.
- **`scraper/deduplicator.py`**: Optimized $O(N^2)$ fuzzy deduplication algorithm using string length pre-filtering and pre-lowercased cache structures.

---

## Milestone 4: Verification & Suite Validation

#### Verified
- **Full Pytest Suite**: 100% test pass rate achieved (77/77 tests passing) across all unit test modules without regressions.
