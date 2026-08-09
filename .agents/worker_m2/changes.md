# Changes Summary - Milestone 2 (Architecture Decoupling & Hygiene)

## 1. Pytest Collection Fix & Move (`scripts/scratch/test_runs.py`)
- **File modified**: `scripts/scratch/test_runs.py` (moved from root `test_runs.py`)
- **Changes**: Wrapped top-level GitHub API network request in `if __name__ == "__main__":` block to prevent top-level execution when imported by pytest collection.
- **Root Cleanup**: Removed `test_runs.py` from repository root.

## 2. Pure Deduplication Logic (`scraper/deduplicator.py` & `tests/test_scraper.py`)
- **File modified**: `scraper/deduplicator.py`
  - Updated `deduplicate(stories: list[dict], past_urls: set[str] | list[str] | None = None) -> list[dict]`.
  - Allowed explicit `past_urls` parameter. If `past_urls is None`, falls back to `read_state()` for backwards compatibility.
- **File modified**: `tests/test_scraper.py`
  - Added unit test `test_deduplication_with_explicit_past_urls` to verify pure deduplication with explicit `past_urls`.

## 3. Shared Helper DRY (`utils/helpers.py`, scrapers)
- **File modified**: `utils/helpers.py`
  - Added shared classification helpers `is_tool_launch(title: str, content: str = "")` and `detect_region(title: str, content: str = "")`.
- **Files modified**:
  - `scraper/sources/hackernews.py`: Removed duplicate `_is_tool_launch`, imported and used `is_tool_launch`.
  - `scraper/sources/reddit.py`: Removed duplicate `_is_tool_launch` and `_detect_region`, imported and used `is_tool_launch` and `detect_region`.
  - `scraper/sources/rss_feeds.py`: Removed duplicate `_is_tool_launch` and `_detect_region`, imported and used `is_tool_launch` and `detect_region`.

## 4. Atomic File Operations (`utils/helpers.py`, `utils/logger.py`)
- **File modified**: `utils/helpers.py`
  - Implemented `atomic_write_json(filepath, data, indent=2, ensure_ascii=False)` using `tempfile.NamedTemporaryFile` + `os.replace`.
  - Refactored `_write_file_state(data)` to call `atomic_write_json`.
  - Added `save_state(data)` alias for `write_state`.
- **File modified**: `utils/logger.py`
  - Imported `atomic_write_json` from `utils.helpers`.
  - Refactored `_write_json(path, data)` to call `atomic_write_json`.
  - Implemented `log_daily_summary(summary_data)` calling `atomic_write_json`.

## 5. Root Directory Hygiene (`scripts/scratch/`)
- **Created directory**: `scripts/scratch/`
- **Files moved**:
  - `auto_oauth.py` -> `scripts/scratch/auto_oauth.py`
  - `extract_cookies.py` -> `scripts/scratch/extract_cookies.py`
  - `headless_oauth.py` -> `scripts/scratch/headless_oauth.py`
  - `take_screenshot.py` -> `scripts/scratch/take_screenshot.py`
  - `test_runs.py` -> `scripts/scratch/test_runs.py`
- **File deleted**: `Cookies_copy.db` removed from repository root.
