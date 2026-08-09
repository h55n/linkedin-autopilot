## 2026-08-09T07:29:43Z
<USER_REQUEST>
You are Worker (Milestone 2: Architecture Decoupling & Hygiene).
Working directory: d:\ANTIGRAVITY\linkedin-autopilot\.agents\worker_m2

MANDATORY INSTRUCTIONS:
1. Read the original user request at: d:\ANTIGRAVITY\linkedin-autopilot\ORIGINAL_REQUEST.md
2. Read the project scope document at: d:\ANTIGRAVITY\linkedin-autopilot\PROJECT.md
3. Read Milestone 1 gate status at: d:\ANTIGRAVITY\linkedin-autopilot\.agents\orchestrator\GATE_STATUS.md
4. Initialize your BRIEFING.md and progress.md in d:\ANTIGRAVITY\linkedin-autopilot\.agents\worker_m2.

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

SCOPE & EXCLUSIVE WRITE BOUNDARIES:
- `test_runs.py`
- `scraper/deduplicator.py`
- `scraper/sources/hackernews.py`
- `scraper/sources/reddit.py`
- `scraper/sources/rss_feeds.py`
- `utils/helpers.py`
- `utils/logger.py`
- `scripts/scratch/`
- Root directory files: `auto_oauth.py`, `extract_cookies.py`, `headless_oauth.py`, `take_screenshot.py`, `Cookies_copy.db`

DETAILED WORK ITEMS FOR MILESTONE 2:
1. Pytest Collection Fix (`test_runs.py`):
   Wrap top-level execution code in `test_runs.py` inside `if __name__ == "__main__":` block so pytest collection on project root (`pytest`) does NOT execute top-level GitHub API network calls upon importing. Move `test_runs.py` to `scripts/scratch/test_runs.py`.
2. Pure Deduplication Logic (`scraper/deduplicator.py`):
   Refactor `deduplicate(stories, past_urls=None)` so `past_urls` can be passed as an explicit parameter (set of strings). If `past_urls` is `None`, fetch past URLs via `read_state()` for backwards compatibility. Update unit tests in `tests/test_scraper.py` or new test cases to test `deduplicate` with explicit `past_urls`.
3. Shared Helper DRY (`utils/helpers.py` & scrapers):
   Extract `is_tool_launch(title, content)` and `detect_region(title, content)` into `utils/helpers.py`. Refactor `scraper/sources/hackernews.py`, `reddit.py`, and `rss_feeds.py` to import and use these shared helpers instead of maintaining duplicated inline definitions.
4. Atomic File Operations (`utils/helpers.py` & `utils/logger.py`):
   Implement `atomic_write_json(filepath, data)` in `utils/helpers.py` using `tempfile.NamedTemporaryFile` + `os.replace`. Update `save_state()` in `utils/helpers.py` and `log_daily_summary()` in `utils/logger.py` to use `atomic_write_json` to guarantee crash-safe JSON writes.
5. Root Directory Hygiene (`scripts/scratch/`):
   Create directory `scripts/scratch/` if it doesn't exist. Move non-portable scratch scripts (`auto_oauth.py`, `extract_cookies.py`, `headless_oauth.py`, `take_screenshot.py`, `test_runs.py`) into `scripts/scratch/`. Remove binary file `Cookies_copy.db` from repository root.

VERIFICATION & TESTING REQUIREMENTS:
- Run root `pytest` (or `python -m pytest`) to verify that default test discovery passes cleanly without hanging on `test_runs.py`.
- Ensure all unit tests pass (`pytest tests/`).
- Document commands executed and test results in your handoff report `d:\ANTIGRAVITY\linkedin-autopilot\.agents\worker_m2\handoff.md`.

OUTPUT REQUIREMENTS:
Write full completion report to `d:\ANTIGRAVITY\linkedin-autopilot\.agents\worker_m2\handoff.md` and `changes.md`.

When complete, send a message to parent with your handoff summary.
</USER_REQUEST>
