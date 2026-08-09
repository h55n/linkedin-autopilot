# Milestone 1 Code Modifications Summary

## Modified Files and Changes

### 1. `generator/generator.py`
- **Change**: Added missing `import os` at top of file.
- **Rationale**: `_get_groq_client()` uses `os.getenv("GROQ_API_KEY", "")` which was throwing `NameError: name 'os' is not defined` when executed.

### 2. `scorer/scorer.py`
- **Change**: Replaced naive substring matching (`kw in text`) with word-boundary regex checks using `re.search(r"\b" + re.escape(kw) + r"\b", text, re.IGNORECASE)`. Added public `score_stories(stories: list[dict]) -> list[dict]` interface.
- **Rationale**: Words containing "ai" as a substring (e.g. "domain", "email", "stipend", "maintain", "chain") caused false-positive matches for the "ai" keyword, incorrectly inflating scores and misclassifying non-AI stories. Word-boundary matching isolates standalone keywords.

### 3. `scraper/sources/github_trending.py`
- **Change**: Refactored star count parsing in `_parse_article`. Converted `"k"` suffixed strings using `int(float(stars_text.replace("k", "").strip()) * 1000)`.
- **Rationale**: Naive string replacement `.replace("k", "00").replace(".", "")` transformed `"12.35k"` into `123500` (10x inflated value). The new logic calculates `12.35 * 1000 = 12350`.

### 4. `utils/helpers.py`
- **Change**: Added null check `if ts is None: return 0.0` to `timestamp_to_age_hours(ts)`. Updated type hint to `ts: int | float | None`.
- **Rationale**: Prevents `TypeError: unsupported operand type(s) for -: 'float' and 'NoneType'` when stories lack a valid timestamp.

### 5. `telegram_bot/voice_handler.py`
- **Change**: Replaced top-level module instantiation `client = Groq(api_key=GROQ_API_KEY)` with a lazy getter function `_get_groq_client()`.
- **Rationale**: Module-level client creation crashed tests and imports whenever `GROQ_API_KEY` was unconfigured or invalid in test environments.

### 6. `main.py`
- **Change**: Wrapped `main_pipeline()` steps in a `try...finally` block. Added `update_state(status="processing", date=today)` at startup and safety reset in `finally` to set status to `"failed"` if the status remains `"processing"` upon exit.
- **Rationale**: If an unhandled exception or crash occurred during execution, state would remain permanently locked in `"processing"`, blocking future runs.

### 7. Tests (`tests/test_scorer.py`, `tests/test_scraper.py`, `tests/test_pipeline.py`)
- **Change**: Added 6 new unit tests covering all Milestone 1 bug fixes.
- **Rationale**: Ensures regression testing and validates all edge cases under test runner. Total test count increased from 66 to 72.
