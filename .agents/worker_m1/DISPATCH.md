## 2026-08-09T07:19:17Z
You are Worker (Milestone 1: Critical Bug Fixes & Code Safety).
Working directory: d:\ANTIGRAVITY\linkedin-autopilot\.agents\worker_m1

MANDATORY INSTRUCTIONS:
1. Read the original user request at: d:\ANTIGRAVITY\linkedin-autopilot\ORIGINAL_REQUEST.md
2. Read the project scope document at: d:\ANTIGRAVITY\linkedin-autopilot\PROJECT.md
3. Initialize your BRIEFING.md and progress.md in d:\ANTIGRAVITY\linkedin-autopilot\.agents\worker_m1.

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

SCOPE & EXCLUSIVE WRITE BOUNDARIES:
You are assigned to implement Milestone 1 fixes in these files:
- `generator/generator.py`
- `scorer/scorer.py`
- `scraper/sources/github_trending.py`
- `utils/helpers.py`
- `telegram_bot/voice_handler.py`
- `main.py`

DETAILED WORK ITEMS FOR MILESTONE 1:
1. `generator/generator.py`: Add missing `import os` at top of file (used on line 34 inside `_get_groq_client()`).
2. `scorer/scorer.py`: Replace naive `kw in text` substring matching in `score_stories()` and AI keyword matching with word-boundary regex checks (e.g. `re.search(r"\b" + re.escape(kw) + r"\b", text, re.IGNORECASE)`). Ensure words like "domain", "email", "stipend", "maintain", "chain" do NOT trigger false positive matches for keyword "ai".
3. `scraper/sources/github_trending.py`: Fix star count parsing logic in `_parse_article`. Currently `.replace("k", "00").replace(".", "")` converts `"12.35k"` to `"123500"`. Refactor to properly parse `"12.35k"` as `float(text.replace("k", "")) * 1000` (yielding `12350`).
4. `utils/helpers.py`: In `timestamp_to_age_hours(ts)`, add null checking `if ts is None: return 0.0` before performing float subtraction `(now - ts)` to prevent `TypeError`.
5. `telegram_bot/voice_handler.py`: Replace global `client = Groq(api_key=GROQ_API_KEY)` module-level instantiation with a lazy getter function `_get_groq_client()` to prevent unauthenticated crashes when imported during tests or when `GROQ_API_KEY` is not configured.
6. `main.py`: In `main_pipeline()`, wrap the pipeline steps in a `try...finally` block so that if an uncaught exception occurs after setting `state["status"] = "processing"`, `state["status"]` is safely reset to `"idle"` or `"failed"` instead of leaving state stuck in `"processing"`.

VERIFICATION & TESTING REQUIREMENTS:
- Run `pytest tests/` after completing changes to verify that all 66 unit tests pass.
- Write unit tests for new/fixed functionality in `tests/test_scorer.py`, `tests/test_helpers.py`, `tests/test_scraper.py` or new test cases if needed.
- Document exact build/test commands executed and their output in your `handoff.md`.

OUTPUT REQUIREMENTS:
Write a full completion report to `d:\ANTIGRAVITY\linkedin-autopilot\.agents\worker_m1\handoff.md` and `changes.md`.

When complete, send a message to parent with your handoff summary.
