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

@patch("scraper.sources.hackernews.requests.get")
def test_hackernews_returns_stories_mocked(mock_get):
    """HN scraper returns correctly shaped stories with mocked responses."""
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

    mock_get.side_effect = [mock_top, mock_item1, mock_item2]

    from scraper.sources.hackernews import scrape_hackernews
    stories = scrape_hackernews()

    assert len(stories) >= 1
    assert all(f in stories[0] for f in REQUIRED_FIELDS)
    assert stories[0]["source"] == "hackernews"


@patch("scraper.sources.reddit.requests.get")
def test_reddit_returns_stories_mocked(mock_get):
    """Reddit scraper returns correctly shaped stories with mocked response."""
    now = int(time.time())
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
    mock_get.return_value = mock_resp

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
