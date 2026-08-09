"""
scraper/sources/hackernews.py
Fetches top stories from Hacker News via Firebase REST API.
"""

import time
from concurrent.futures import ThreadPoolExecutor
import requests
from utils.logger import get_logger
from utils.helpers import clean_title, url_to_id, timestamp_to_age_hours, is_tool_launch, get_http_session
from config.settings import (
    REQUEST_TIMEOUT, HN_RATE_LIMIT_MS, HN_MIN_SCORE,
    HN_TOP_LIMIT, REQUEST_USER_AGENT, MAX_AGE_HOURS, SHOW_HN_RAW_BONUS
)

log = get_logger("scraper.hn")

HN_BASE = "https://hacker-news.firebaseio.com/v0"
HEADERS = {"User-Agent": REQUEST_USER_AGENT}


def scrape_hackernews(session=None) -> list[dict]:
    """Return list of story dicts from HN top stories."""
    if session is None:
        session = get_http_session()
    stories = []

    try:
        resp = session.get(
            f"{HN_BASE}/topstories.json",
            timeout=REQUEST_TIMEOUT,
            headers=HEADERS,
        )
        resp.raise_for_status()
        top_ids = resp.json()[:HN_TOP_LIMIT]
    except Exception as e:
        log.warning(f"Failed to fetch HN top stories: {e}")
        return []

    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [
            executor.submit(_fetch_item, item_id, session)
            for item_id in top_ids
        ]
        for future in futures:
            try:
                item = future.result()
                if item:
                    stories.append(item)
            except Exception as e:
                log.debug(f"Skipping HN item: {e}")

    log.info(f"HN: fetched {len(stories)} stories")
    return stories


def _fetch_item(item_id: int, session=None) -> dict | None:
    if session is None:
        session = get_http_session()
    resp = session.get(
        f"{HN_BASE}/item/{item_id}.json",
        timeout=REQUEST_TIMEOUT,
        headers=HEADERS,
    )
    resp.raise_for_status()
    item = resp.json()

    if not item:
        return None

    # Skip dead, deleted, or non-stories
    if item.get("dead") or item.get("deleted"):
        return None
    if item.get("type") != "story":
        return None

    score = item.get("score", 0)
    title = item.get("title", "")
    url = item.get("url", "")
    timestamp = item.get("time", 0)
    comments = item.get("descendants", 0)

    # Skip Ask HN (no useful URL)
    if title.startswith("Ask HN:"):
        return None

    # Age filter
    age_hours = timestamp_to_age_hours(timestamp)
    if age_hours > MAX_AGE_HOURS:
        return None

    is_show_hn = title.startswith("Show HN:")
    raw_score = score + (SHOW_HN_RAW_BONUS if is_show_hn else 0)

    # Score filter (after bonus)
    if raw_score < HN_MIN_SCORE:
        return None

    # If Show HN, URL might be in comments
    if not url:
        url = f"https://news.ycombinator.com/item?id={item_id}"

    clean = clean_title(title)

    return {
        "id": url_to_id(url),
        "source": "hackernews",
        "title": clean,
        "url": url,
        "discussion_url": f"https://news.ycombinator.com/item?id={item_id}",
        "summary": clean,   # HN has no description — title is the summary
        "score": raw_score,
        "comments": comments,
        "timestamp": timestamp,
        "is_tool_launch": is_show_hn or is_tool_launch(clean),
        "region": "global",
        "age_hours": age_hours,
    }

