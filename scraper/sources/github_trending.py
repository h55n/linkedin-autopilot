"""
scraper/sources/github_trending.py
Scrapes GitHub Trending page for top repos (HTML scrape, no auth needed).
"""

import time
import requests
from bs4 import BeautifulSoup
from utils.logger import get_logger
from utils.helpers import url_to_id
from config.settings import (
    REQUEST_TIMEOUT, REQUEST_USER_AGENT, GITHUB_TRENDING_TOP
)

log = get_logger("scraper.github")

GITHUB_TRENDING_URL = "https://github.com/trending?since=daily"


def scrape_github_trending() -> list[dict]:
    """Return top N trending GitHub repos as story dicts."""
    try:
        resp = requests.get(
            GITHUB_TRENDING_URL,
            headers={"User-Agent": REQUEST_USER_AGENT},
            timeout=REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
    except Exception as e:
        log.warning(f"GitHub Trending scrape failed: {e}")
        return []

    soup = BeautifulSoup(resp.text, "lxml")
    articles = soup.select("article.Box-row")[:GITHUB_TRENDING_TOP]

    stories = []
    for article in articles:
        try:
            story = _parse_article(article)
            if story:
                stories.append(story)
        except Exception as e:
            log.debug(f"Skipping GitHub trending item: {e}")
            continue

    log.info(f"GitHub Trending: {len(stories)} repos")
    return stories


def _parse_article(article) -> dict | None:
    # Repo link
    link_tag = article.select_one("h2 a")
    if not link_tag:
        return None

    repo_path = link_tag.get("href", "").strip().lstrip("/")
    if not repo_path:
        return None

    url = f"https://github.com/{repo_path}"
    title = repo_path.replace("/", " / ")

    # Description
    desc_tag = article.select_one("p")
    summary = desc_tag.get_text(strip=True) if desc_tag else title

    # Stars
    stars_tag = article.select_one("a[href*='stargazers']")
    stars_text = stars_tag.get_text(strip=True).replace(",", "") if stars_tag else "0"
    try:
        stars = int(stars_text.replace("k", "00").replace(".", ""))
    except ValueError:
        stars = 0

    # Today's stars
    today_tag = article.select_one("span.d-inline-block.float-sm-right")
    today_text = today_tag.get_text(strip=True) if today_tag else ""
    try:
        today_stars = int("".join(filter(str.isdigit, today_text.split()[0])))
    except (ValueError, IndexError):
        today_stars = 0

    from config.settings import AI_KEYWORDS, TOOL_LAUNCH_KEYWORDS
    combined = (title + " " + summary).lower()
    is_ai = any(kw in combined for kw in AI_KEYWORDS)
    is_tool = any(kw in combined for kw in TOOL_LAUNCH_KEYWORDS)

    return {
        "id": url_to_id(url),
        "source": "github_trending",
        "title": f"{title} — {summary[:80]}" if summary != title else title,
        "url": url,
        "discussion_url": url,
        "summary": summary[:400],
        "score": today_stars + (stars // 100),   # weight today's stars more
        "comments": 0,
        "timestamp": int(time.time()),   # trending = now
        "is_tool_launch": True,           # trending repos are de facto launches
        "region": "global",
        "age_hours": 0.5,                 # treat as very fresh
    }
