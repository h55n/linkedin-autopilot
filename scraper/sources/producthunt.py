"""
scraper/sources/producthunt.py
Parses Product Hunt RSS feed, filtering for AI-related launches.
"""

import time
import re
import feedparser
import requests
from utils.logger import get_logger
from utils.helpers import url_to_id, timestamp_to_age_hours
from config.settings import (
    PRODUCT_HUNT_RSS, REQUEST_TIMEOUT, REQUEST_USER_AGENT,
    MAX_AGE_HOURS, AI_KEYWORDS
)

log = get_logger("scraper.producthunt")


def scrape_producthunt() -> list[dict]:
    """Return AI-related Product Hunt launches from the last 24h."""
    try:
        resp = requests.get(
            PRODUCT_HUNT_RSS,
            headers={"User-Agent": REQUEST_USER_AGENT},
            timeout=REQUEST_TIMEOUT,
        )
        feed = feedparser.parse(resp.content)
    except Exception as e:
        log.warning(f"Product Hunt RSS failed: {e}")
        return []

    stories = []
    for entry in feed.entries[:20]:
        try:
            story = _parse_entry(entry)
            if story:
                stories.append(story)
        except Exception as e:
            log.debug(f"Skipping PH entry: {e}")
            continue

    log.info(f"Product Hunt: {len(stories)} AI stories")
    return stories


def _parse_entry(entry) -> dict | None:
    title = getattr(entry, "title", "").strip()
    url = getattr(entry, "link", "").strip()

    if not title or not url:
        return None

    summary = ""
    if hasattr(entry, "summary"):
        summary = re.sub(r"<[^>]+>", "", entry.summary).strip()[:400]
    if not summary:
        summary = title

    # Filter: only AI-related products
    combined = (title + " " + summary).lower()
    if not any(kw in combined for kw in AI_KEYWORDS):
        return None

    published_parsed = getattr(entry, "published_parsed", None)
    if published_parsed:
        import calendar
        timestamp = int(calendar.timegm(published_parsed))
    else:
        timestamp = int(time.time())

    age_hours = timestamp_to_age_hours(timestamp)
    if age_hours > MAX_AGE_HOURS:
        return None

    return {
        "id": url_to_id(url),
        "source": "producthunt",
        "title": title,
        "url": url,
        "discussion_url": url,
        "summary": summary,
        "score": 50,      # PH entries get a base score
        "comments": 0,
        "timestamp": timestamp,
        "is_tool_launch": True,   # everything on PH is a launch
        "region": "global",
        "age_hours": age_hours,
    }
