"""
utils/helpers.py
Shared utility functions used across modules.
"""

import hashlib
import json
import os
import re
import time
from datetime import datetime
from urllib.parse import urlparse, urlunparse

import pytz
from config.settings import TIMEZONE, STATE_FILE


# ── URL helpers ───────────────────────────────────────────────────

def canonical_url(url: str) -> str:
    """Strip query params and fragment for dedup comparison."""
    try:
        parsed = urlparse(url)
        return urlunparse((parsed.scheme, parsed.netloc, parsed.path, "", "", ""))
    except Exception:
        return url


def url_to_id(url: str) -> str:
    """Create a stable short ID from a URL."""
    return hashlib.md5(canonical_url(url).encode()).hexdigest()[:12]


def extract_domain(url: str) -> str:
    try:
        return urlparse(url).netloc.replace("www.", "")
    except Exception:
        return ""


# ── Time helpers ──────────────────────────────────────────────────

def now_ist() -> datetime:
    tz = pytz.timezone(TIMEZONE)
    return datetime.now(tz)


def timestamp_to_age_hours(ts: int) -> float:
    """Convert a Unix timestamp to age in hours from now."""
    now = time.time()
    return max(0.0, (now - ts) / 3600)


def age_label(age_hours: float) -> str:
    """Human-readable age string."""
    if age_hours < 1:
        mins = int(age_hours * 60)
        return f"{mins}m ago"
    elif age_hours < 24:
        return f"{int(age_hours)}h ago"
    else:
        return f"{int(age_hours / 24)}d ago"


# ── State management ──────────────────────────────────────────────

def read_state() -> dict:
    if not os.path.exists(STATE_FILE):
        return {}
    try:
        with open(STATE_FILE) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def write_state(data: dict):
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def update_state(**kwargs):
    state = read_state()
    state.update(kwargs)
    write_state(state)


# ── Text helpers ──────────────────────────────────────────────────

def clean_title(title: str) -> str:
    """Strip HN/Reddit prefixes and normalize whitespace."""
    prefixes = ["Show HN: ", "Ask HN: ", "Tell HN: "]
    for p in prefixes:
        if title.startswith(p):
            title = title[len(p):]
    return re.sub(r"\s+", " ", title).strip()


def sentence_count(text: str) -> int:
    """Rough sentence count — split on . ! ? """
    sentences = re.split(r"[.!?]+", text)
    return len([s for s in sentences if s.strip()])


def word_count(text: str) -> int:
    return len(text.split())


def truncate_text(text: str, max_chars: int = 700) -> str:
    """Truncate to LinkedIn's sweet spot, preserving word boundaries."""
    if len(text) <= max_chars:
        return text
    truncated = text[:max_chars].rsplit(" ", 1)[0]
    return truncated + "…"


# ── Format helpers ────────────────────────────────────────────────

def format_source_label(source: str) -> str:
    """Turn source string into display label."""
    labels = {
        "hackernews": "hackernews",
        "reddit/r/artificial": "r/artificial",
        "reddit/r/MachineLearning": "r/ml",
        "reddit/r/singularity": "r/singularity",
        "reddit/r/programming": "r/programming",
        "reddit/r/startups": "r/startups",
        "reddit/r/india": "r/india",
        "inc42": "inc42",
        "yourstory": "yourstory",
        "entrackr": "entrackr",
        "ettech": "et tech",
        "techcrunch_ai": "techcrunch",
        "venturebeat_ai": "venturebeat",
        "betalist": "betalist",
        "producthunt": "product hunt",
        "github_trending": "github trending",
    }
    return labels.get(source, source)


def format_score_label(score: int, source: str) -> str:
    """Create a concise engagement label."""
    if "hackernews" in source or "reddit" in source:
        return f"{score}pts"
    return f"~{score} engagement"


def emoji_for_story(story: dict) -> str:
    if story.get("region") == "india":
        return "🇮🇳"
    if story.get("is_tool_launch"):
        return "🔧"
    if story.get("is_ai_related"):
        return "🤖"
    return "📰"
