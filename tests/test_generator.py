"""
tests/test_generator.py
Tests for the generator module — mocked Groq calls.
"""

import pytest
import json
from unittest.mock import patch, MagicMock
from generator.generator import (
    generate_post, generate_post_with_edit, generate_morning_brief,
    _clean_text_post, _parse_carousel_json,
)
from tests.conftest import make_story


# ─────────────────────────────────────────────────────────────────
# Mock Groq response helper
# ─────────────────────────────────────────────────────────────────

def mock_groq_response(text: str):
    """Create a mock Groq completion response."""
    mock = MagicMock()
    mock.choices[0].message.content = text
    return mock


SAMPLE_TEXT_POST = "mistral just released a 7b model that matches gpt-4 on coding benchmarks. the interesting part is that it runs on a macbook, no cloud needed. indian devs on tight infra budgets now have a real option."

SAMPLE_CAROUSEL_JSON = json.dumps({
    "intro_text": "a 7b model just matched gpt-4 on code. here's what that actually means.",
    "slides": [
        {
            "type": "cover",
            "category_label": "AI TOOLS",
            "heading": "smaller models, bigger impact",
            "subheading": "what mistral's 7b means for everyone"
        },
        {
            "type": "content",
            "heading": "the benchmark shift",
            "body": "mistral 7b scored higher than gpt-4 on humaneval. this is the first time a sub-10b parameter model has done this.",
            "highlight_phrase": "first time a sub-10b model"
        },
        {
            "type": "cta",
            "heading": "what to do now",
            "body": "download it. run it locally. test it on your actual use case before trusting the benchmarks.",
            "highlight_phrase": "test it on your actual use case"
        }
    ]
})


# ─────────────────────────────────────────────────────────────────
# TEXT POST TESTS
# ─────────────────────────────────────────────────────────────────

@patch("generator.generator._call_llm")
def test_text_post_is_lowercase(mock_llm):
    mock_llm.return_value = SAMPLE_TEXT_POST
    story = make_story()
    result = generate_post(story, post_type="text")
    post_text = result["post_text"]
    assert post_text == post_text.lower(), "Post must be all lowercase"


@patch("generator.generator._call_llm")
def test_text_post_has_no_em_dashes(mock_llm):
    mock_llm.return_value = SAMPLE_TEXT_POST
    story = make_story()
    result = generate_post(story, post_type="text")
    assert "—" not in result["post_text"]


@patch("generator.generator._call_llm")
def test_text_post_has_no_exclamation_marks(mock_llm):
    mock_llm.return_value = SAMPLE_TEXT_POST
    story = make_story()
    result = generate_post(story, post_type="text")
    assert "!" not in result["post_text"]


@patch("generator.generator._call_llm")
def test_text_post_type_in_result(mock_llm):
    mock_llm.return_value = SAMPLE_TEXT_POST
    result = generate_post(make_story(), post_type="text")
    assert result["post_type"] == "text"
    assert result["post_text"]
    assert result["carousel_data"] is None


# ─────────────────────────────────────────────────────────────────
# CAROUSEL TESTS
# ─────────────────────────────────────────────────────────────────

@patch("generator.generator._call_llm")
def test_carousel_json_is_valid(mock_llm):
    mock_llm.return_value = SAMPLE_CAROUSEL_JSON
    result = generate_post(make_story(), post_type="carousel")
    assert result["post_type"] == "carousel"
    assert result["carousel_data"] is not None
    slides = result["carousel_data"]["slides"]
    assert isinstance(slides, list)
    assert len(slides) <= 5
    for slide in slides:
        assert "heading" in slide


@patch("generator.generator._call_llm")
def test_carousel_slides_are_lowercase(mock_llm):
    mock_llm.return_value = SAMPLE_CAROUSEL_JSON
    result = generate_post(make_story(), post_type="carousel")
    for slide in result["carousel_data"]["slides"]:
        heading = slide.get("heading", "")
        body = slide.get("body", "")
        if heading:
            first_word = heading.split()[0]
            if len(first_word) > 3:  # skip acronyms
                assert first_word == first_word.lower(), f"Heading has uppercase: {heading}"


@patch("generator.generator._call_llm")
def test_carousel_max_5_slides_enforced(mock_llm):
    """Even if LLM returns 7 slides, we cap at 5."""
    big_carousel = json.dumps({
        "intro_text": "hook sentence here",
        "slides": [
            {"type": "content", "heading": f"slide {i}", "body": f"body {i}"}
            for i in range(7)
        ]
    })
    mock_llm.return_value = big_carousel
    result = generate_post(make_story(), post_type="carousel")
    assert len(result["carousel_data"]["slides"]) <= 5


@patch("generator.generator._call_llm")
def test_carousel_fallback_to_text_on_bad_json(mock_llm):
    """If carousel JSON is invalid twice, falls back to text post."""
    mock_llm.side_effect = [
        "this is not valid json at all",
        "also not json",
        SAMPLE_TEXT_POST,  # fallback text post call
    ]
    result = generate_post(make_story(), post_type="carousel")
    assert result["post_type"] == "text"
    assert result["post_text"]


# ─────────────────────────────────────────────────────────────────
# EDIT POST TEST
# ─────────────────────────────────────────────────────────────────

@patch("generator.generator._call_llm")
def test_edit_post_applies_instruction(mock_llm):
    edited_text = "mistral 7b matches gpt-4 on code. runs locally on a macbook."
    mock_llm.return_value = edited_text

    result = generate_post_with_edit(
        original_post=SAMPLE_TEXT_POST,
        edit_instruction="make it shorter",
        story=make_story(),
        post_type="text",
    )
    assert result["post_type"] == "text"
    assert result["post_text"]


# ─────────────────────────────────────────────────────────────────
# MORNING BRIEF TESTS
# ─────────────────────────────────────────────────────────────────

def test_morning_brief_contains_3_picks():
    picks = [
        make_story(id=f"p{i}", url=f"https://s{i}.com", title=f"story {i}",
                   format_suggestion="text", source="hackernews")
        for i in range(1, 4)
    ]
    brief = generate_morning_brief(picks)
    assert "1." in brief
    assert "2." in brief
    assert "3." in brief


def test_morning_brief_contains_urls():
    picks = [
        make_story(id=f"p{i}", url=f"https://example.com/story-{i}", title=f"story {i}",
                   format_suggestion="text")
        for i in range(1, 4)
    ]
    brief = generate_morning_brief(picks)
    for pick in picks:
        assert pick["url"] in brief


def test_morning_brief_is_lowercase():
    picks = [make_story(id="p1", format_suggestion="text")]
    brief = generate_morning_brief(picks)
    # Brief should not start with uppercase words (only emoji/numbers)
    assert "Good Morning" not in brief
    assert "Here Are" not in brief


# ─────────────────────────────────────────────────────────────────
# HELPER TESTS
# ─────────────────────────────────────────────────────────────────

def test_clean_text_post_strips_preamble():
    raw = "Here's your post:\n\nthe actual post content here."
    cleaned = _clean_text_post(raw)
    assert "Here's your post" not in cleaned
    assert "actual post content" in cleaned


def test_parse_carousel_json_valid():
    data = _parse_carousel_json(SAMPLE_CAROUSEL_JSON)
    assert data is not None
    assert "slides" in data


def test_parse_carousel_json_strips_fences():
    fenced = f"```json\n{SAMPLE_CAROUSEL_JSON}\n```"
    data = _parse_carousel_json(fenced)
    assert data is not None
    assert "slides" in data


def test_parse_carousel_json_returns_none_for_garbage():
    data = _parse_carousel_json("this is not json")
    assert data is None
