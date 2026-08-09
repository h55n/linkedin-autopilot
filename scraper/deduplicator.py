"""
scraper/deduplicator.py
Removes duplicate and near-duplicate stories.
"""

from thefuzz import fuzz
from utils.helpers import canonical_url, read_state
from utils.logger import get_logger
from config.settings import FUZZY_DEDUP_THRESHOLD

log = get_logger("scraper.dedup")


def deduplicate(stories: list[dict], past_urls: set[str] | list[str] | None = None) -> list[dict]:
    """
    Remove stories that share a URL or have near-identical titles.
    Also removes stories with no URL.
    Returns the deduplicated list (order preserved for first occurrence).

    If past_urls is None, fetches past URLs via read_state() for backwards compatibility.
    """
    if past_urls is None:
        state = read_state()
        past_urls_set = set(state.get("past_urls", []))
    else:
        past_urls_set = set(past_urls)

    
    seen_urls: set[str] = set()
    seen_titles: list[tuple[str, int]] = []
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
        if canon in past_urls_set:
            log.debug(f"URL dedup (past runs): {title[:60]}")
            continue

        # Pre-lowercase and compute length once per title
        title_lower = title.lower()
        len_title = len(title_lower)

        # Fuzzy title dedup
        is_dup = False
        for seen_title_lower, len_seen in seen_titles:
            # Length pre-filtering: skip fuzzy comparison if length difference > 50%
            max_len = max(len_title, len_seen)
            if max_len > 0 and (abs(len_title - len_seen) / max_len) > 0.50:
                continue

            ratio = fuzz.token_sort_ratio(title_lower, seen_title_lower)
            if ratio >= FUZZY_DEDUP_THRESHOLD:
                log.debug(f"Title dedup ({ratio}%): {title[:60]}")
                is_dup = True
                break

        if is_dup:
            continue

        seen_urls.add(canon)
        seen_titles.append((title_lower, len_title))
        unique.append(story)

    log.info(f"Dedup: {len(stories)} → {len(unique)} stories")
    return unique
