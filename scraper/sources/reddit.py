"""
scraper/sources/reddit.py
Fetches hot posts from relevant subreddits via public JSON API.
"""

import time
import requests
from utils.logger import get_logger
from utils.helpers import clean_title, url_to_id, timestamp_to_age_hours
from config.settings import (
    REQUEST_TIMEOUT, REDDIT_RATE_LIMIT_MS, REDDIT_MIN_SCORE,
    REDDIT_STARTUPS_MIN_SCORE, REDDIT_TOP_PER_SUB,
    REDDIT_SUBREDDITS, REQUEST_USER_AGENT, MAX_AGE_HOURS,
    REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET, REDDIT_USER_AGENT,
)

log = get_logger("scraper.reddit")
HEADERS = {"User-Agent": REQUEST_USER_AGENT}


def scrape_reddit() -> list[dict]:
    """Return story dicts from all configured subreddits."""
    all_stories = []

    for sub in REDDIT_SUBREDDITS:
        try:
            time.sleep(REDDIT_RATE_LIMIT_MS / 1000)
            stories = _scrape_subreddit(sub)
            all_stories.extend(stories)
            log.info(f"r/{sub}: {len(stories)} stories")
        except Exception as e:
            log.warning(f"r/{sub} failed: {e}")
            continue

    return all_stories


def _scrape_subreddit(subreddit: str) -> list[dict]:
    url = f"https://www.reddit.com/r/{subreddit}/hot.json?limit={REDDIT_TOP_PER_SUB}"

    resp = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)

    if resp.status_code == 429:
        log.warning(f"r/{subreddit} rate limited — backing off 60s")
        time.sleep(60)
        resp = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)

    resp.raise_for_status()
    data = resp.json()

    posts = data.get("data", {}).get("children", [])
    stories = []

    min_score = REDDIT_STARTUPS_MIN_SCORE if subreddit == "startups" else REDDIT_MIN_SCORE

    for post in posts:
        d = post.get("data", {})

        if d.get("stickied"):
            continue
        if d.get("is_self") and not d.get("selftext"):
            continue

        score = d.get("score", 0)
        if score < min_score:
            continue

        timestamp = d.get("created_utc", 0)
        age_hours = timestamp_to_age_hours(timestamp)
        if age_hours > MAX_AGE_HOURS:
            continue

        title = clean_title(d.get("title", ""))
        post_url = d.get("url", "")
        permalink = f"https://reddit.com{d.get('permalink', '')}"

        # Self posts → use permalink as URL
        if d.get("is_self") or not post_url or post_url == permalink:
            post_url = permalink

        comments = d.get("num_comments", 0)
        flair = d.get("link_flair_text", "") or ""
        selftext = (d.get("selftext", "") or "")[:400]

        # Build summary from title + flair + selftext excerpt
        summary_parts = [title]
        if flair:
            summary_parts.append(f"[{flair}]")
        if selftext and len(selftext) > 20:
            summary_parts.append(selftext[:200])
        summary = " ".join(summary_parts)[:400]

        region = "india" if subreddit == "india" else _detect_region(title + " " + selftext)

        stories.append({
            "id": url_to_id(post_url),
            "source": f"reddit/r/{subreddit}",
            "title": title,
            "url": post_url,
            "discussion_url": permalink,
            "summary": summary,
            "score": score,
            "comments": comments,
            "timestamp": int(timestamp),
            "is_tool_launch": _is_tool_launch(title),
            "region": region,
            "age_hours": age_hours,
        })

    return stories


def _detect_region(text: str) -> str:
    from config.settings import INDIA_KEYWORDS
    t = text.lower()
    if any(kw in t for kw in INDIA_KEYWORDS):
        return "india"
    return "global"


def _is_tool_launch(title: str) -> bool:
    from config.settings import TOOL_LAUNCH_KEYWORDS
    t = title.lower()
    return any(kw in t for kw in TOOL_LAUNCH_KEYWORDS)
