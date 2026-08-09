"""
scraper/enricher.py
Fetches the full article text for a story URL to give the LLM much richer context.
Uses trafilatura for clean article extraction — falls back to BeautifulSoup.
Gracefully times out so a slow site never blocks the pipeline.
"""

import re
import requests
from utils.logger import get_logger
from utils.helpers import get_http_session
from config.settings import REQUEST_TIMEOUT, REQUEST_USER_AGENT

log = get_logger("enricher")


def enrich_story(story: dict, session=None) -> dict:
    """
    Fetch full article text for a story and add it to story['full_text'].
    Returns the story dict (mutated in place, also returned for convenience).
    Non-blocking — any failure leaves story['full_text'] = ''.
    """
    url = story.get("url", "")
    if not url or story.get("full_text"):
        return story

    try:
        full_text = _fetch_article_text(url, session=session)
        story["full_text"] = full_text[:3000]   # cap at 3k chars to stay within LLM context
        log.debug(f"Enriched {url[:60]} ({len(story['full_text'])} chars)")
    except Exception as e:
        log.debug(f"Enrichment failed for {url[:60]}: {e}")
        story["full_text"] = ""

    return story


def _fetch_article_text(url: str, session=None) -> str:
    """Fetch and clean article text from a URL."""
    if session is None:
        session = get_http_session()
    try:
        # 1. Fetch raw HTML, explicitly resolving redirects (crucial for Google News RSS)
        resp = session.get(
            url,
            headers={"User-Agent": REQUEST_USER_AGENT},
            timeout=REQUEST_TIMEOUT,
            allow_redirects=True,
        )
        resp.raise_for_status()
        html_content = resp.text
    except Exception as e:
        log.debug(f"Failed to fetch HTML for {url}: {e}")
        return ""

    # 2. Try trafilatura extraction on the downloaded HTML
    try:
        import trafilatura
        text = trafilatura.extract(
            html_content,
            include_comments=False,
            include_tables=False,
            no_fallback=False,
        )
        if text and len(text.strip()) > 150:
            return text.strip()
    except Exception as e:
        log.debug(f"Trafilatura extraction failed for {url}: {e}")

    # 3. Fallback: regex strip HTML
    try:
        text = re.sub(r"<[^>]+>", " ", html_content)
        text = re.sub(r"\s+", " ", text).strip()
        if len(text) > 150:
            return text
    except Exception:
        pass

    return ""
