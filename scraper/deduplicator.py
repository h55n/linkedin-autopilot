"""
scraper/deduplicator.py
Removes duplicate and near-duplicate stories.
"""

from thefuzz import fuzz
from utils.helpers import canonical_url, read_state
from utils.logger import get_logger
from config.settings import FUZZY_DEDUP_THRESHOLD

log = get_logger("scraper.dedup")


def deduplicate(stories: list[dict]) -> list[dict]:
    """
    Remove stories that share a URL or have near-identical titles.
    Also removes stories with no URL.
    Returns the deduplicated list (order preserved for first occurrence).
    """
    state = read_state()
    past_urls = set(state.get("past_urls", []))
    
    seen_urls: set[str] = set()
    seen_titles: list[str] = []
    unique: list[dict] = []

    for story in stories:
        url = story.get("url", "")
        title = story.get("title", "")

        if not url or not title:
            continue

        # URL dedup (current run and past runs)
        canon = canonical_url(url)
        if canon in seen_urls:
            log.debug(f"URL dedup (current run): {title[:60]}")
            continue
        if canon in past_urls:
            log.debug(f"URL dedup (past runs): {title[:60]}")
            continue

        # Fuzzy title dedup
        is_dup = False
        for seen_title in seen_titles:
            ratio = fuzz.token_sort_ratio(title.lower(), seen_title.lower())
            if ratio >= FUZZY_DEDUP_THRESHOLD:
                log.debug(f"Title dedup ({ratio}%): {title[:60]}")
                is_dup = True
                break

        if is_dup:
            continue

        seen_urls.add(canon)
        seen_titles.append(title)
        unique.append(story)

    log.info(f"Dedup: {len(stories)} → {len(unique)} stories")
    return unique
