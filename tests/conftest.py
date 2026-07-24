"""
tests/conftest.py
Shared fixtures for all tests.
"""

import pytest
import time


def make_story(**kwargs) -> dict:
    """Create a minimal valid story dict with overridable fields."""
    base = {
        "id": "test123",
        "source": "hackernews",
        "title": "openai releases new model that runs locally",
        "url": "https://example.com/story",
        "discussion_url": "https://news.ycombinator.com/item?id=1",
        "summary": "openai has released a new model that can run on consumer hardware",
        "score": 500,
        "comments": 100,
        "timestamp": int(time.time()) - 3600,  # 1h ago
        "is_tool_launch": False,
        "region": "global",
        "age_hours": 1.0,
    }
    base.update(kwargs)
    return base


@pytest.fixture
def sample_story():
    return make_story()


@pytest.fixture
def india_story():
    return make_story(
        id="india456",
        source="inc42",
        title="bangalore startup raises $12m for ai in indian languages",
        url="https://inc42.com/story/startup",
        summary="a bangalore-based startup raised $12m to build ai for indian languages",
        score=100,
        region="india",
        age_hours=1.5,
    )


@pytest.fixture
def tool_launch_story():
    return make_story(
        id="tool789",
        title="open-source tool that converts figma to react code",
        url="https://github.com/owner/figma-to-react",
        is_tool_launch=True,
        score=600,
        age_hours=2.0,
    )


@pytest.fixture
def noise_story():
    return make_story(
        id="noise000",
        title="bitcoin hits new high as crypto markets rally",
        url="https://coindesk.com/story",
        score=800,
        age_hours=0.5,
    )


@pytest.fixture
def many_stories(sample_story, india_story, tool_launch_story, noise_story):
    """A list of stories covering all scoring scenarios."""
    extras = [
        make_story(id=f"extra{i}", title=f"story {i} about machine learning", score=200, age_hours=i * 2)
        for i in range(5)
    ]
    return [sample_story, india_story, tool_launch_story, noise_story] + extras
