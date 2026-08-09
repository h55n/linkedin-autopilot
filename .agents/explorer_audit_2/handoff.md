# Handoff Report — Explorer 2 (Bugs & Reliability Auditor)

## 1. Observation
Direct, verifiable findings from inspecting `d:\ANTIGRAVITY\linkedin-autopilot`:

- **Keyword Matching Bug in Scorer (`scorer/scorer.py:63-65, 82-101, 116`):**
  Substring membership check (`kw in text`) causes false positive keyword hits. For example, 2-letter keyword `"ai"` matches words like `domain`, `main`, `stipend`, `email`, `maintain`, `chain`, incorrectly setting `is_ai_related = True` for non-AI content.
- **Null Timestamp Dereference (`utils/helpers.py:54-58`):**
  `timestamp_to_age_hours(ts)` directly subtracts `(now - ts)` without validating `ts is not None`. If HN or Reddit item has missing `time`/`created_utc`, `TypeError: unsupported operand type(s) for -: 'float' and 'NoneType'` is thrown.
- **Pipeline Lockout / Stuck Status (`main.py:66-68`):**
  If `main_pipeline()` encounters an uncaught error after `status` is set to `"processing"` or `"publishing"`, the state remains in that status for the day. Subsequent runs evaluate `state.get("status") not in ("idle", None, "skipped", "posted", "cancelled")` and abort.
- **Star Math Calculation Error (`scraper/sources/github_trending.py:70-74`):**
  `stars_text.replace("k", "00").replace(".", "")` converts `"12.35k"` into `"123500"`, multiplying the star count by 10x due to naive string substitution.
- **Destructive Automation & Hardcoded Paths (`headless_oauth.py:9, 20-21`, `auto_oauth.py:17`):**
  `taskkill /F /IM chrome.exe` forcibly closes user's active Chrome browsers. Paths contain hardcoded host paths like `C:\Users\hassa\...`.
- **Exposed Local Credentials (`.env`, `Cookies_copy.db`):**
  Live production secrets (Groq, Telegram Token, LinkedIn Client Secret, OAuth Tokens) exist in working directory files.

## 2. Logic Chain
1. *Observation:* Scorer checks `any(kw in text for kw in AI_KEYWORDS)`.
   *Logic:* `"ai"` is a substring in common words (`domain`, `email`, `chain`). Thus, any text containing those words gets flagged as AI-related, boosting score unnaturally and distorting topic categorization.
2. *Observation:* Scraper entries occasionally omit timestamps (`time = None`).
   *Logic:* Passing `None` to `timestamp_to_age_hours(None)` attempts float arithmetic on `None`, causing unhandled exceptions that break the scraper loop for that source.
3. *Observation:* `main.py` checks state status before running and skips if status is active (`"processing"`/`"publishing"`).
   *Logic:* If an unhandled exception strikes mid-pipeline, state is never reset to `"idle"` or `"waiting"`. The system locks up for the remainder of the day until manually reset.

## 3. Caveats
- No live network requests to LinkedIn or Telegram APIs were sent during this read-only audit to prevent unintended side effects on production accounts.
- Test runner execution was checked locally; minor environmental differences on Windows proactor loop may require verification when running in headless GitHub Actions runners.

## 4. Conclusion
The codebase has a clean modular structure, but exhibits critical bugs in keyword matching, potential null-pointer crashes in scrapers, pipeline state deadlock vulnerability on exceptions, and risky credentials/process handling in auxiliary scripts. Immediate refactoring of keyword matching to regex word boundaries, null-checking timestamp calculations, and wrapping state transitions in try/finally blocks is strongly recommended.

## 5. Verification Method
- **Verify Keyword Scorer Fix:**
  Run `pytest tests/test_scorer.py` after implementing regex boundary checks to confirm `"domain"` does not flag `is_ai_related`.
- **Verify Null Timestamp Handling:**
  Call `timestamp_to_age_hours(None)` in a test case and verify it returns `0.0` or handles `None` without raising `TypeError`.
- **Verify Star Math:**
  Test `_parse_article` in `github_trending.py` with `"12.3k"` and `"12.35k"` to verify star counts evaluate to `12300` and `12350`.
