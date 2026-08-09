"""
scraper/sources/rss_feeds.py
Parses India + global tech RSS feeds.
"""

import time
import feedparser
import requests
from utils.logger import get_logger
from utils.helpers import url_to_id, timestamp_to_age_hours, is_tool_launch, detect_region, get_http_session
from config.settings import (
    RSS_FEEDS, REQUEST_TIMEOUT, REQUEST_USER_AGENT, MAX_AGE_HOURS
)

log = get_logger("scraper.rss")

INDIA_SOURCES = {"inc42", "yourstory", "entrackr", "ettech"}


def scrape_rss_feeds(session=None) -> list[dict]:
    """Parse all configured RSS feeds and return story dicts."""
    if session is None:
        session = get_http_session()
    all_stories = []

    for source_key, feed_url in RSS_FEEDS.items():
        try:
            stories = _parse_feed(source_key, feed_url, session=session)
            all_stories.extend(stories)
            log.info(f"{source_key}: {len(stories)} stories")
        except Exception as e:
            log.warning(f"RSS feed {source_key} failed: {e}")
            continue

    return all_stories


def _parse_feed(source_key: str, feed_url: str, session=None) -> list[dict]:
    if session is None:
        session = get_http_session()
    # Use session to set proper user agent, then pass to feedparser
    try:
        resp = session.get(
            feed_url,
            headers={"User-Agent": REQUEST_USER_AGENT},
            timeout=REQUEST_TIMEOUT,
        )
        feed = feedparser.parse(resp.content)
    except Exception:
        # Fallback: let feedparser handle it directly
        feed = feedparser.parse(feed_url)

    stories = []
    is_india = source_key in INDIA_SOURCES

    for entry in feed.entries:
        try:
            story = _parse_entry(entry, source_key, is_india)
            if story:
                stories.append(story)
        except Exception as e:
            log.debug(f"Skipping RSS entry from {source_key}: {e}")
            continue

    return stories


def _parse_entry(entry, source_key: str, is_india: bool) -> dict | None:
    title = getattr(entry, "title", "").strip()
    url = getattr(entry, "link", "").strip()

    if not title or not url:
        return None

    # Parse publish time
    published_parsed = getattr(entry, "published_parsed", None)
    updated_parsed = getattr(entry, "updated_parsed", None)
    time_struct = published_parsed or updated_parsed

    if time_struct:
        import calendar
        timestamp = int(calendar.timegm(time_struct))
    else:
        timestamp = int(time.time())

    age_hours = timestamp_to_age_hours(timestamp)
    if age_hours > MAX_AGE_HOURS:
        return None

    # Summary from description or content
    summary = ""
    if hasattr(entry, "summary"):
        summary = entry.summary
    elif hasattr(entry, "description"):
        summary = entry.description

    # Strip HTML tags from summary
    import re
    summary = re.sub(r"<[^>]+>", "", summary).strip()[:400]

    if not summary:
        summary = title

    region = "india" if is_india else detect_region(title, summary)

    return {
        "id": url_to_id(url),
        "source": source_key,
        "title": title,
        "url": url,
        "discussion_url": url,
        "summary": summary,
        "score": 0,   # RSS feeds don't have scores — recency drives ranking
        "comments": 0,
        "timestamp": timestamp,
        "is_tool_launch": is_tool_launch(title, summary),
        "region": region,
        "age_hours": age_hours,
    }

