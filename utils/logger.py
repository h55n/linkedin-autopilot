"""
utils/logger.py
Structured logging — writes to daily_log.json, streak.json, errors.log
"""

import json
import logging
import os
import traceback
from datetime import date, datetime
from config.settings import DAILY_LOG_FILE, ERROR_LOG_FILE
from utils.helpers import read_state, update_state

# ── Python standard logger ────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


# ── File helpers ──────────────────────────────────────────────────

def _ensure_file(path: str, default):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if not os.path.exists(path):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(default, f, indent=2)


def _read_json(path: str, default):
    _ensure_file(path, default)
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return default


def _write_json(path: str, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


# ── Daily log ─────────────────────────────────────────────────────

def log_post(
    story: dict,
    format_type: str,
    post_text: str,
    your_angle: str,
    linkedin_url: str,
    status: str = "posted",
):
    """Append a post entry to daily_log.json."""
    log = _read_json(DAILY_LOG_FILE, [])
    entry = {
        "date": date.today().isoformat(),
        "timestamp": datetime.now().isoformat(),
        "story_title": story.get("title", ""),
        "story_url": story.get("url", ""),
        "story_source": story.get("source", ""),
        "format": format_type,
        "post_text": post_text,
        "your_angle": your_angle,
        "linkedin_url": linkedin_url,
        "status": status,
    }
    log.append(entry)
    _write_json(DAILY_LOG_FILE, log)
    _update_streak(status)
    return entry


def log_skip(reason: str = "no_reply"):
    """Log a skipped day."""
    log = _read_json(DAILY_LOG_FILE, [])
    entry = {
        "date": date.today().isoformat(),
        "timestamp": datetime.now().isoformat(),
        "status": "skipped",
        "reason": reason,
    }
    log.append(entry)
    _write_json(DAILY_LOG_FILE, log)
    _update_streak("skipped")


def get_recent_log(days: int = 7) -> list:
    """Return the last N log entries."""
    log = _read_json(DAILY_LOG_FILE, [])
    return log[-days:]


# ── Streak ────────────────────────────────────────────────────────

def _update_streak(status: str):
    state = read_state()
    streak_data = state.get("streak", {"count": 0, "last_posted": None})
    today = date.today().isoformat()

    if status == "posted":
        last = streak_data.get("last_posted")
        if last == today:
            pass  # already counted today
        else:
            # Check if yesterday was posted
            from datetime import timedelta
            yesterday = (date.today() - timedelta(days=1)).isoformat()
            if last == yesterday:
                streak_data["count"] += 1
            else:
                streak_data["count"] = 1
            streak_data["last_posted"] = today
    else:
        # skipped or cancelled — reset streak
        streak_data["count"] = 0

    update_state(streak=streak_data)


def get_streak() -> int:
    state = read_state()
    data = state.get("streak", {"count": 0})
    return data.get("count", 0)


# ── Error log ─────────────────────────────────────────────────────

def log_error(context: str, exc: Exception = None):
    """Append error with full traceback to errors.log."""
    os.makedirs(os.path.dirname(ERROR_LOG_FILE), exist_ok=True)
    timestamp = datetime.now().isoformat()
    with open(ERROR_LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"\n{'='*60}\n")
        f.write(f"{timestamp} | {context}\n")
        if exc:
            f.write(traceback.format_exc())
        f.write("\n")
    logging.getLogger("error").error(f"{context}: {exc}")
