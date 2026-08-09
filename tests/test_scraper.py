"""
tests/test_scraper.py
Tests for scraper module — deduplication and schema validation.
Network tests are skipped unless explicitly enabled.
"""

import pytest
import time
from unittest.mock import patch, MagicMock
from scraper.deduplicator import deduplicate
from tests.conftest import make_story


# ─────────────────────────────────────────────────────────────────
# DEDUPLICATION TESTS (no network required)
# ─────────────────────────────────────────────────────────────────

def test_deduplication_removes_duplicate_urls():
    stories = [
        make_story(id="a", url="https://example.com/story?utm=foo"),
        make_story(id="b", url="https://example.com/story?ref=bar"),  # same canonical URL
    ]
    result = deduplicate(stories)
    assert len(result) == 1


def test_deduplication_keeps_different_urls():
    stories = [
        make_story(id="a", url="https://example.com/story-1"),
        make_story(id="b", url="https://example.com/story-2", title="completely different story"),
    ]
    result = deduplicate(stories)
    assert len(result) == 2


def test_deduplication_removes_near_duplicate_titles():
    stories = [
        make_story(id="a", url="https://a.com/1",
                   title="openai releases gpt-5 with massive improvements"),
        make_story(id="b", url="https://b.com/2",
                   title="openai released gpt-5 with massive improvement"),  # ~95% similar
    ]
    result = deduplicate(stories)
    assert len(result) == 1


def test_deduplication_keeps_different_titles():
    stories = [
        make_story(id="a", url="https://a.com/1",
                   title="openai releases gpt-5 model"),
        make_story(id="b", url="https://b.com/2",
                   title="anthropic launches claude 4 with new features"),
    ]
    result = deduplicate(stories)
    assert len(result) == 2


def test_deduplication_removes_stories_without_url():
    stories = [
        make_story(id="a", url=""),
        make_story(id="b", url="https://example.com/valid"),
    ]
    result = deduplicate(stories)
    assert len(result) == 1
    assert result[0]["url"] == "https://example.com/valid"


def test_deduplication_preserves_order():
    stories = [
        make_story(id="a", url="https://a.com/1", title="first story"),
        make_story(id="b", url="https://b.com/2", title="second story"),
        make_story(id="c", url="https://c.com/3", title="third story"),
    ]
    result = deduplicate(stories)
    assert result[0]["id"] == "a"
    assert result[1]["id"] == "b"
    assert result[2]["id"] == "c"


def test_deduplication_with_explicit_past_urls():
    past = {"https://example.com/past-story"}
    stories = [
        make_story(id="a", url="https://example.com/past-story", title="old story"),
        make_story(id="b", url="https://example.com/new-story", title="new story"),
    ]
    result = deduplicate(stories, past_urls=past)
    assert len(result) == 1
    assert result[0]["id"] == "b"



# ─────────────────────────────────────────────────────────────────
# SCHEMA VALIDATION
# ─────────────────────────────────────────────────────────────────

REQUIRED_FIELDS = ["id", "source", "title", "url", "summary", "score",
                   "comments", "timestamp", "is_tool_launch", "region"]

def test_story_schema_has_required_fields():
    story = make_story()
    for field in REQUIRED_FIELDS:
        assert field in story, f"Missing required field: {field}"


# ─────────────────────────────────────────────────────────────────
# MOCKED NETWORK TESTS
# ─────────────────────────────────────────────────────────────────

@patch("scraper.sources.hackernews.get_http_session")
def test_hackernews_returns_stories_mocked(mock_get_session):
    """HN scraper returns correctly shaped stories with mocked responses."""
    mock_session = MagicMock()
    mock_get_session.return_value = mock_session

    # Mock top stories list
    mock_top = MagicMock()
    mock_top.json.return_value = [1, 2]
    mock_top.raise_for_status = MagicMock()

    # Mock individual items
    now = int(time.time())
    mock_item1 = MagicMock()
    mock_item1.json.return_value = {
        "id": 1, "type": "story", "score": 200,
        "title": "Show HN: New AI tool for developers",
        "url": "https://example.com/tool",
        "time": now - 3600, "descendants": 50,
    }
    mock_item1.raise_for_status = MagicMock()

    mock_item2 = MagicMock()
    mock_item2.json.return_value = {
        "id": 2, "type": "story", "score": 150,
        "title": "Ask HN: What LLM should I use?",  # should be skipped
        "url": "", "time": now - 7200, "descendants": 20,
    }
    mock_item2.raise_for_status = MagicMock()

    mock_session.get.side_effect = [mock_top, mock_item1, mock_item2]

    from scraper.sources.hackernews import scrape_hackernews
    stories = scrape_hackernews()

    assert len(stories) >= 1
    assert all(f in stories[0] for f in REQUIRED_FIELDS)
    assert stories[0]["source"] == "hackernews"


@patch("scraper.sources.reddit.get_http_session")
def test_reddit_returns_stories_mocked(mock_get_session):
    """Reddit scraper returns correctly shaped stories with mocked response."""
    now = int(time.time())
    mock_session = MagicMock()
    mock_get_session.return_value = mock_session

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "data": {
            "children": [
                {
                    "data": {
                        "title": "New paper on LLM reasoning published",
                        "url": "https://arxiv.org/paper",
                        "score": 300,
                        "num_comments": 45,
                        "created_utc": now - 3600,
                        "permalink": "/r/MachineLearning/comments/abc",
                        "is_self": False,
                        "stickied": False,
                    }
                }
            ]
        }
    }
    mock_resp.raise_for_status = MagicMock()
    mock_session.get.return_value = mock_resp

    from scraper.sources.reddit import scrape_reddit
    stories = scrape_reddit()

    assert len(stories) >= 1
    assert all(f in stories[0] for f in REQUIRED_FIELDS)


@patch("scraper.scraper.scrape_hackernews")
@patch("scraper.scraper.scrape_reddit")
@patch("scraper.scraper.scrape_rss_feeds")
@patch("scraper.scraper.scrape_producthunt")
@patch("scraper.scraper.scrape_github_trending")
def test_scrape_all_returns_nonempty_list(mock_gh, mock_ph, mock_rss, mock_reddit, mock_hn):
    """scrape_all merges all sources and returns deduplicated stories."""
    now = int(time.time())
    mock_hn.return_value = [make_story(id="hn1", url="https://hn.com/1", title="hn story one")]
    mock_reddit.return_value = [make_story(id="rd1", url="https://reddit.com/1", title="reddit story")]
    mock_rss.return_value = [make_story(id="rss1", url="https://inc42.com/1", title="india startup news")]
    mock_ph.return_value = [make_story(id="ph1", url="https://ph.com/1", title="product hunt launch")]
    mock_gh.return_value = [make_story(id="gh1", url="https://github.com/1", title="github trending tool")]

    from scraper.scraper import scrape_all
    result = scrape_all()

    assert len(result) > 0
    for story in result:
        for field in REQUIRED_FIELDS:
            assert field in story


@patch("scraper.scraper.scrape_hackernews")
@patch("scraper.scraper.scrape_reddit")
@patch("scraper.scraper.scrape_rss_feeds")
@patch("scraper.scraper.scrape_producthunt")
@patch("scraper.scraper.scrape_github_trending")
def test_scrape_all_handles_partial_failure(mock_gh, mock_ph, mock_rss, mock_reddit, mock_hn):
    """scrape_all continues even if some scrapers fail."""
    mock_hn.side_effect = Exception("HN is down")
    mock_reddit.side_effect = Exception("Reddit rate limited")
    mock_rss.return_value = [make_story(id="rss1", url="https://inc42.com/1", title="india startup news")]
    mock_ph.return_value = []
    mock_gh.return_value = []

    from scraper.scraper import scrape_all
    result = scrape_all()

    assert len(result) >= 1  # RSS stories still come through


def test_github_trending_star_parsing():
    """Verify that star count '12.35k' parses to 12350, not 123500."""
    from bs4 import BeautifulSoup
    from scraper.sources.github_trending import _parse_article

    html_k = """
    <article class="Box-row">
        <h2><a href="/owner/repo1">owner/repo1</a></h2>
        <p>A cool repo description</p>
        <a href="/owner/repo1/stargazers">12.35k</a>
        <span class="d-inline-block float-sm-right">150 stars today</span>
    </article>
    """
    soup_k = BeautifulSoup(html_k, "html.parser").select_one("article")
    parsed_k = _parse_article(soup_k)
    assert parsed_k is not None
    # score calculation: today_stars (150) + (stars // 100) -> 12350 // 100 = 123 -> total score = 273
    # If stars were 123500, (123500 // 100) = 1235 -> total score would be 1385
    assert parsed_k["score"] == 150 + (12350 // 100)

    html_plain = """
    <article class="Box-row">
        <h2><a href="/owner/repo2">owner/repo2</a></h2>
        <p>Another repo</p>
        <a href="/owner/repo2/stargazers">500</a>
        <span class="d-inline-block float-sm-right">50 stars today</span>
    </article>
    """
    soup_plain = BeautifulSoup(html_plain, "html.parser").select_one("article")
    parsed_plain = _parse_article(soup_plain)
    assert parsed_plain is not None
    assert parsed_plain["score"] == 50 + (500 // 100)


# ─────────────────────────────────────────────────────────────────
# MILESTONE 3: PERFORMANCE & CONCURRENCY TESTS
# ─────────────────────────────────────────────────────────────────

def test_get_http_session_returns_configured_session():
    """Verify get_http_session returns a process-wide requests.Session with proper pool limits and User-Agent."""
    import requests
    from utils.helpers import get_http_session

    session1 = get_http_session()
    session2 = get_http_session()

    assert isinstance(session1, requests.Session)
    assert session1 is session2, "get_http_session must reuse process-wide Session instance"
    assert "User-Agent" in session1.headers
    assert session1.adapters["http://"]._pool_connections == 10
    assert session1.adapters["https://"]._pool_connections == 10


@patch("scraper.scraper.scrape_hackernews")
@patch("scraper.scraper.scrape_reddit")
@patch("scraper.scraper.scrape_rss_feeds")
@patch("scraper.scraper.scrape_producthunt")
@patch("scraper.scraper.scrape_github_trending")
def test_parallel_scraper_execution(mock_gh, mock_ph, mock_rss, mock_reddit, mock_hn):
    """Verify scrape_all executes scrapers concurrently via ThreadPoolExecutor(max_workers=5)."""
    import time
    from scraper.scraper import scrape_all

    distinct_stories = {
        "hn": ("hn_1", "https://hn.com/item1", "Hacker News reports quantum computing breakthrough in superconductors"),
        "reddit": ("rd_1", "https://reddit.com/item1", "Reddit machine learning community discusses deep reinforcement learning"),
        "rss": ("rss_1", "https://rss.com/item1", "Indian tech startup ecosystem sees record venture capital investment"),
        "ph": ("ph_1", "https://ph.com/item1", "Product Hunt launches new developer productivity tool for visual workflow"),
        "gh": ("gh_1", "https://gh.com/item1", "GitHub repository trends with high star growth for rust backend framework"),
    }

    def delayed_scraper(name, delay=0.1):
        time.sleep(delay)
        story_id, url, title = distinct_stories[name]
        return [make_story(
            id=story_id,
            url=url,
            discussion_url=f"{url}_discuss",
            title=title,
        )]

    mock_hn.side_effect = lambda: delayed_scraper("hn")
    mock_reddit.side_effect = lambda: delayed_scraper("reddit")
    mock_rss.side_effect = lambda: delayed_scraper("rss")
    mock_ph.side_effect = lambda: delayed_scraper("ph")
    mock_gh.side_effect = lambda: delayed_scraper("gh")

    start_time = time.time()
    results = scrape_all()
    duration = time.time() - start_time

    assert len(results) == 5
    # Total delay if sequential = 0.5s. Parallel execution should complete in ~0.15s (< 0.45s).
    assert duration < 0.45, f"Scraper execution took {duration:.2f}s, expected concurrent execution"


@patch("scraper.sources.reddit.REDDIT_SUBREDDITS", ["artificial", "MachineLearning"])
@patch("scraper.sources.reddit.get_http_session")
def test_reddit_http_429_rate_limit_non_blocking(mock_get_session):
    """Verify Reddit HTTP 429 returns empty list immediately without 60s blocking sleep."""
    import time
    from scraper.sources.reddit import scrape_reddit

    mock_session = MagicMock()
    mock_get_session.return_value = mock_session

    mock_resp = MagicMock()
    mock_resp.status_code = 429
    mock_session.get.return_value = mock_resp

    start = time.time()
    results = scrape_reddit()
    elapsed = time.time() - start

    assert elapsed < 1.5, f"Rate limit handled slowly: took {elapsed:.2f}s"
    assert results == [], "HTTP 429 should gracefully return empty list for affected subreddits"


def test_optimized_deduplication_length_filtering():
    """Verify string length pre-filtering (>50% difference) skips fuzzy comparison accurately."""
    from scraper.deduplicator import deduplicate

    stories = [
        make_story(id="1", url="https://a.com/1", title="Short title"),
        make_story(
            id="2",
            url="https://b.com/2",
            title="Short title but with an extraordinarily long suffix that makes the total length difference strictly greater than fifty percent compared to the first story title",
        ),
        make_story(id="3", url="https://c.com/3", title="short title"),  # Near dupe of #1 (case difference)
    ]

    result = deduplicate(stories)
    # Story #1 and #3 are near duplicates -> #3 is removed. Story #2 is kept due to length filter / low similarity.
    assert len(result) == 2
    assert result[0]["id"] == "1"
    assert result[1]["id"] == "2"


