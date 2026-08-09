"""
scraper/scraper.py
Orchestrates all source scrapers and returns a single deduplicated list.
Each source failure is isolated — one bad source never crashes the pipeline.
"""

from concurrent.futures import ThreadPoolExecutor, as_completed
from utils.logger import get_logger, log_error
from scraper.sources.hackernews import scrape_hackernews
from scraper.sources.reddit import scrape_reddit
from scraper.sources.rss_feeds import scrape_rss_feeds
from scraper.sources.producthunt import scrape_producthunt
from scraper.sources.github_trending import scrape_github_trending
from scraper.deduplicator import deduplicate

log = get_logger("scraper")


def scrape_all() -> list[dict]:
    """
    Run all scrapers concurrently in parallel, merge results, deduplicate.
    Returns a flat list of story dicts ready for scoring.
    """
    all_stories: list[dict] = []

    sources = [
        ("HackerNews", scrape_hackernews),
        ("Reddit", scrape_reddit),
        ("RSS Feeds", scrape_rss_feeds),
        ("Product Hunt", scrape_producthunt),
        ("GitHub Trending", scrape_github_trending),
    ]

    with ThreadPoolExecutor(max_workers=5) as executor:
        future_to_source = {
            executor.submit(scraper_fn): name
            for name, scraper_fn in sources
        }

        for future in as_completed(future_to_source):
            name = future_to_source[future]
            try:
                stories = future.result()
                all_stories.extend(stories)
                log.info(f"{name}: +{len(stories)} (total so far: {len(all_stories)})")
            except Exception as e:
                log_error(f"Scraper '{name}' failed", e)
                log.warning(f"{name} scraper failed — continuing without it")

    deduped = deduplicate(all_stories)
    log.info(f"scrape_all complete: {len(deduped)} unique stories")
    return deduped
