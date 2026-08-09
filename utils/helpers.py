"""
utils/helpers.py
Shared utility functions used across modules.

State backend:
  STATE_BACKEND=file (default) — reads/writes state/today.json on disk.
  STATE_BACKEND=gist           — reads/writes a GitHub Gist, so state
                                  survives across ephemeral GHA runs.
                                  Requires GIST_TOKEN and GIST_ID env vars.
"""

import hashlib
import json
import os
import re
import tempfile
import time
from datetime import datetime
from urllib.parse import urlparse, urlunparse

import pytz
import requests
from requests.adapters import HTTPAdapter
from config.settings import TIMEZONE, STATE_FILE, REQUEST_USER_AGENT


# ── Connection Pooling ──────────────────────────────────────────

_HTTP_SESSION = None

def get_http_session(
    pool_connections: int = 10,
    pool_maxsize: int = 10,
    user_agent: str | None = None,
) -> requests.Session:
    """
    Return a process-wide shared requests.Session configured with connection pool limits
    and default User-Agent headers.
    """
    global _HTTP_SESSION
    if _HTTP_SESSION is None:
        session = requests.Session()
        adapter = HTTPAdapter(
            pool_connections=pool_connections,
            pool_maxsize=pool_maxsize,
        )
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        ua = user_agent or REQUEST_USER_AGENT
        session.headers.update({"User-Agent": ua})
        _HTTP_SESSION = session
    return _HTTP_SESSION



# ── Atomic file operations ──────────────────────────────────────

def atomic_write_json(filepath: str, data: dict | list, indent: int = 2, ensure_ascii: bool = False):
    """Write JSON data to filepath atomically using a temporary file and os.replace."""
    dir_name = os.path.dirname(os.path.abspath(filepath))
    os.makedirs(dir_name, exist_ok=True)
    
    tf = tempfile.NamedTemporaryFile("w", dir=dir_name, delete=False, encoding="utf-8")
    temp_name = tf.name
    try:
        json.dump(data, tf, indent=indent, ensure_ascii=ensure_ascii)
        tf.flush()
        tf.close()
        os.replace(temp_name, filepath)
    except Exception:
        tf.close()
        if os.path.exists(temp_name):
            try:
                os.remove(temp_name)
            except OSError:
                pass
        raise



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


def timestamp_to_age_hours(ts: int | float | None) -> float:
    """Convert a Unix timestamp to age in hours from now."""
    if ts is None:
        return 0.0
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
# Backend is chosen once at import time via STATE_BACKEND env var.

_STATE_BACKEND = os.getenv("STATE_BACKEND", "file").lower()
_GIST_TOKEN = os.getenv("GIST_TOKEN", "")
_GIST_ID = os.getenv("GIST_ID", "")
_GIST_FILENAME = "linkedin_autopilot_state.json"
_GIST_API = f"https://api.github.com/gists/{_GIST_ID}"


# ── Gist helpers ──────────────────────────────────────────────────

def _gist_headers() -> dict:
    return {
        "Authorization": f"Bearer {_GIST_TOKEN}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def _read_gist_state() -> dict:
    """Fetch state JSON from the GitHub Gist."""
    if not _GIST_TOKEN or not _GIST_ID:
        return {}
    try:
        session = get_http_session()
        resp = session.get(_GIST_API, headers=_gist_headers(), timeout=10)
        resp.raise_for_status()
        content = resp.json()["files"][_GIST_FILENAME]["content"]
        return json.loads(content)
    except Exception as e:
        from utils.logger import get_logger
        get_logger("helpers").warning(f"Gist state read failed ({e}) — falling back to local file state")
        return {}


def _write_gist_state(data: dict):
    """Push state JSON to the GitHub Gist."""
    if not _GIST_TOKEN or not _GIST_ID:
        return
    payload = {
        "files": {
            _GIST_FILENAME: {
                "content": json.dumps(data, indent=2, ensure_ascii=False)
            }
        }
    }
    session = get_http_session()
    resp = session.patch(_GIST_API, headers=_gist_headers(),
                          json=payload, timeout=10)
    resp.raise_for_status()


# ── File helpers ──────────────────────────────────────────────────

def _read_file_state() -> dict:
    if not os.path.exists(STATE_FILE):
        return {}
    try:
        with open(STATE_FILE, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def _write_file_state(data: dict):
    atomic_write_json(STATE_FILE, data)


def save_state(data: dict):
    """Save state to local file state and Gist (alias for write_state)."""
    write_state(data)


# ── Classification helpers ────────────────────────────────────────

def is_tool_launch(title: str, content: str = "") -> bool:
    """Check if title or content indicates a tool launch."""
    from config.settings import TOOL_LAUNCH_KEYWORDS
    text = (title + " " + content).lower()
    return any(kw in text for kw in TOOL_LAUNCH_KEYWORDS)


def detect_region(title: str, content: str = "") -> str:
    """Detect whether text is region-specific (e.g. india) or global."""
    from config.settings import INDIA_KEYWORDS
    text = (title + " " + content).lower()
    if any(kw in text for kw in INDIA_KEYWORDS):
        return "india"
    return "global"



# ── Public API (same interface as before) ─────────────────────────

def read_state() -> dict:
    """Read today's state from Gist if configured, falling back to local file state."""
    state = {}
    if _STATE_BACKEND == "gist":
        state = _read_gist_state()
    
    # Fall back to local file if Gist was empty or failed
    if not state:
        state = _read_file_state()
        
    return state


def write_state(data: dict):
    """Write today's state to local file state and Gist (if configured)."""
    # Always write to local file state as fallback
    _write_file_state(data)
    
    if _STATE_BACKEND == "gist":
        try:
            _write_gist_state(data)
        except Exception as e:
            from utils.logger import get_logger
            get_logger("helpers").error(f"Failed to push state to Gist: {e}")


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
