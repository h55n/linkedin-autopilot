"""
tests/test_scorer.py
Tests for the scoring engine — pure functions, no network.
"""

import pytest
import time
from scorer.scorer import rank_and_pick, _score_story, suggest_format
from tests.conftest import make_story


def test_recent_stories_score_higher_than_old():
    fresh = make_story(id="fresh", score=200, age_hours=1.0)
    old = make_story(id="old", url="https://example.com/old", title="slightly older story", score=200, age_hours=20.0)

    s_fresh = _score_story(fresh)
    s_old = _score_story(old)

    assert s_fresh["final_score"] > s_old["final_score"]


def test_india_keyword_adds_bonus():
    with_india = make_story(
        id="india_kw",
        url="https://example.com/india",
        title="bangalore startup launches new ai platform",
        region="india",
    )
    without_india = make_story(id="no_india", score=500, age_hours=1.0)

    s_with = _score_story(with_india)
    s_without = _score_story(without_india)

    # india story with lower raw score should still get bonus
    assert s_with["india_relevant"] is True
    assert s_with["final_score"] > _score_story(
        make_story(id="baseline", url="https://example.com/base2", title="some random story")
    )["final_score"]


def test_tool_launch_adds_bonus():
    tool = make_story(id="tool", is_tool_launch=True, score=200, age_hours=2.0)
    no_tool = make_story(id="notool", url="https://example.com/notool", title="no tool here", is_tool_launch=False, score=200, age_hours=2.0)

    s_tool = _score_story(tool)
    s_no = _score_story(no_tool)

    assert s_tool["final_score"] > s_no["final_score"]


def test_noise_keyword_penalizes_score():
    # PRD: noise_penalty x0.2 (not a hard block — a very high-score crypto story can
    # still outrank a low-score AI story). Test with equal raw scores to isolate penalty.
    noise = make_story(
        id="noise",
        url="https://example.com/crypto",
        title="bitcoin hits all time high as crypto markets rally",
        score=300,
        age_hours=1.0,
    )
    normal = make_story(
        id="normal2",
        url="https://example.com/normal",
        title="ai model reduces inference cost by 50 percent",
        score=300,
        age_hours=1.0,
    )

    s_noise = _score_story(noise)
    s_normal = _score_story(normal)

    # With same raw score, noise story should score significantly lower
    assert s_noise["final_score"] < s_normal["final_score"]


def test_ai_keyword_adds_bonus():
    ai_story = make_story(
        id="ai",
        url="https://example.com/ai2",
        title="new llm model outperforms gpt-4 on benchmarks",
        score=200,
    )
    non_ai = make_story(id="nonai", url="https://example.com/nonai", title="new restaurant opens in town", score=200)

    s_ai = _score_story(ai_story)
    s_non = _score_story(non_ai)

    assert s_ai["is_ai_related"] is True
    assert s_ai["final_score"] > s_non["final_score"]


def test_diversity_pass_has_three_slots():
    """Mix pass should fill Tool/Agent, Hackathon, and News/Fellowship slots."""
    tool = make_story(
        id="tool1",
        url="https://github.com/owner/cool-agent",
        title="new open-source agent framework for python",
        score=100,
        age_hours=1.0,
    )
    hackathon = make_story(
        id="hack1",
        url="https://mlh.io/hackathon",
        title="MLH hackathon 2026 applications open now",
        score=50,
        age_hours=2.0,
    )
    news = make_story(
        id="news1",
        url="https://techcrunch.com/story",
        title="openai releases new reasoning model",
        score=80,
        age_hours=3.0,
    )

    picks = rank_and_pick([tool, hackathon, news])

    assert len(picks) == 3
    ids = {s["id"] for s in picks}
    assert "tool1" in ids, "Tool/Agent slot should be present"
    assert "hack1" in ids, "Hackathon slot should be present"
    assert "news1" in ids, "News/Fellowship slot should be present"


def test_rank_and_pick_returns_at_most_3():
    stories = [
        make_story(id=f"s{i}", url=f"https://s{i}.com", title=f"story {i}", score=100 + i * 10)
        for i in range(10)
    ]
    picks = rank_and_pick(stories)
    assert len(picks) <= 3


def test_rank_and_pick_handles_empty_input():
    picks = rank_and_pick([])
    assert picks == []


def test_format_suggestion_carousel_for_tool_with_github():
    story = make_story(
        url="https://github.com/owner/cool-tool",
        is_tool_launch=True,
    )
    assert suggest_format(story) == "carousel"


def test_format_suggestion_carousel_for_benchmark_story():
    story = make_story(
        title="new model beats gpt-4 on benchmark tests",
        summary="comparison shows 20% improvement over baseline",
        url="https://example.com/benchmark",
    )
    assert suggest_format(story) == "carousel"


def test_format_suggestion_text_for_india_news_story():
    story = make_story(
        id="india_news",
        title="india startup raises funding in Series B round",
        url="https://inc42.com/story",
        summary="a pune-based fintech startup closed its Series B funding round",
        region="india",
        is_tool_launch=False,
        age_hours=2.0,
        source="inc42",
    )
    fmt = suggest_format(story)
    assert fmt == "text"


def test_format_suggestion_text_as_default():
    story = make_story(
        id="generic_news",
        title="tech company reports quarterly revenue growth",
        url="https://techcrunch.com/story",
        summary="a tech company reported strong revenue numbers this quarter",
        is_tool_launch=False,
        source="rss",
    )
    assert suggest_format(story) == "text"


def test_rank_and_pick_attaches_format_suggestion():
    stories = [
        make_story(id=f"s{i}", url=f"https://s{i}.com", title=f"story {i}", score=100)
        for i in range(3)
    ]
    picks = rank_and_pick(stories)
    for pick in picks:
        assert "format_suggestion" in pick
        assert pick["format_suggestion"] in ("text", "carousel", "image")


def test_score_stories_returns_scored_list():
    from scorer.scorer import score_stories
    stories = [
        make_story(id="s1", title="domain name registration update", score=100),
        make_story(id="s2", title="new ai breakthrough in vision", score=100),
    ]
    scored = score_stories(stories)
    assert len(scored) == 2
    assert "final_score" in scored[0]
    assert "final_score" in scored[1]


def test_ai_keyword_word_boundary_no_false_positives():
    from scorer.scorer import _score_story
    # Words like domain, email, stipend, maintain, chain contain 'ai' substring but are NOT AI related
    story_domain = make_story(id="d", url="https://example.com/d", title="company updates domain name and email system", summary="routine maintenance for email server")
    story_stipend = make_story(id="s", url="https://example.com/s", title="stipend increased to maintain supply chain", summary="supply chain updates for logistics")
    story_ai = make_story(id="a", url="https://example.com/a", title="new ai agent framework released", summary="an open source ai agent framework")

    s_domain = _score_story(story_domain)
    s_stipend = _score_story(story_stipend)
    s_ai = _score_story(story_ai)

    assert s_domain["is_ai_related"] is False
    assert s_stipend["is_ai_related"] is False
    assert s_ai["is_ai_related"] is True

