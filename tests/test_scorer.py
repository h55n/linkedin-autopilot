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


def test_diversity_pass_inserts_india_story():
    """If no India story in top 3, the 3rd slot should be replaced."""
    # Build 4 high-scoring global stories and 1 lower-scoring India story
    global_stories = [
        make_story(id=f"g{i}", url=f"https://g{i}.com", title=f"global story {i}", score=500, age_hours=1.0)
        for i in range(4)
    ]
    india = make_story(
        id="india_div",
        url="https://inc42.com/india-story",
        title="bangalore startup raises $10m for vernacular ai",
        score=50,   # low score — would normally not make top 3
        region="india",
        age_hours=2.0,
    )

    all_stories = global_stories + [india]
    picks = rank_and_pick(all_stories)

    assert len(picks) <= 3
    india_in_picks = any(s.get("india_relevant") for s in picks)
    assert india_in_picks, "Diversity pass should inject an India story"


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


def test_format_suggestion_image_for_tool_with_github():
    story = make_story(
        url="https://github.com/owner/cool-tool",
        is_tool_launch=True,
    )
    assert suggest_format(story) == "image"


def test_format_suggestion_carousel_for_benchmark_story():
    story = make_story(
        title="new model beats gpt-4 on benchmark tests",
        summary="comparison shows 20% improvement over baseline",
        url="https://example.com/benchmark",
    )
    assert suggest_format(story) == "carousel"


def test_format_suggestion_text_for_india_story():
    story = make_story(
        title="india startup raises funding for ai",
        url="https://inc42.com/story",
        region="india",
        is_tool_launch=False,
        age_hours=2.0,
    )
    fmt = suggest_format(story)
    assert fmt == "text"


def test_format_suggestion_text_as_default():
    story = make_story(
        title="some general tech news story",
        url="https://techcrunch.com/story",
        is_tool_launch=False,
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
