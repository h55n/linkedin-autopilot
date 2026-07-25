"""
scraper/enricher.py
Fetches the full article text for a story URL to give the LLM much richer context.
Uses trafilatura for clean article extraction — falls back to BeautifulSoup.
Gracefully times out so a slow site never blocks the pipeline.
"""

import re
import requests
from utils.logger import get_logger
from config.settings import REQUEST_TIMEOUT, REQUEST_USER_AGENT

log = get_logger("enricher")


def enrich_story(story: dict) -> dict:
    """
    Fetch full article text for a story and add it to story['full_text'].
    Returns the story dict (mutated in place, also returned for convenience).
    Non-blocking — any failure leaves story['full_text'] = ''.
    """
    url = story.get("url", "")
    if not url or story.get("full_text"):
        return story

    try:
        full_text = _fetch_article_text(url)
        story["full_text"] = full_text[:3000]   # cap at 3k chars to stay within LLM context
        log.debug(f"Enriched {url[:60]} ({len(story['full_text'])} chars)")
    except Exception as e:
        log.debug(f"Enrichment failed for {url[:60]}: {e}")
        story["full_text"] = ""

    return story


def _fetch_article_text(url: str) -> str:
    """Fetch and clean article text from a URL."""
    # Try trafilatura first (best quality)
    try:
        import trafilatura
        downloaded = trafilatura.fetch_url(url)
        if downloaded:
            text = trafilatura.extract(
                downloaded,
                include_comments=False,
                include_tables=False,
                no_fallback=False,
            )
            if text and len(text.strip()) > 150:
                return text.strip()
    except Exception:
        pass

    # Fallback: raw requests + regex strip HTML
    try:
        resp = requests.get(
            url,
            headers={"User-Agent": REQUEST_USER_AGENT},
            timeout=REQUEST_TIMEOUT,
            allow_redirects=True,
        )
        resp.raise_for_status()
        # Strip tags
        text = re.sub(r"<[^>]+>", " ", resp.text)
        text = re.sub(r"\s+", " ", text).strip()
        if len(text) > 150:
            return text
    except Exception:
        pass

    return ""
