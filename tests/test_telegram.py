"""
tests/test_telegram.py
Tests for Telegram bot message parsing and state machine logic.
"""

import pytest
from telegram_bot.bot import _parse_pick


MOCK_PICKS = [{"title": "t1"}, {"title": "t2"}, {"title": "t3"}]

# ─────────────────────────────────────────────────────────────────
# PARSE_PICK TESTS
# ─────────────────────────────────────────────────────────────────

from unittest.mock import patch

def test_story_number_parsed_correctly():
    result = _parse_pick("2, here's my take on this", MOCK_PICKS)
    assert result is not None
    num, angle, fmt = result
    assert num == 2
    assert "here's my take" in angle


def test_story_number_only():
    result = _parse_pick("1", MOCK_PICKS)
    assert result is not None
    num, angle, fmt = result
    assert num == 1
    assert angle is None


def test_story_number_with_period():
    result = _parse_pick("3. use this for your own project", MOCK_PICKS)
    assert result is not None
    num, angle, fmt = result
    assert num == 3
    assert "use this" in angle


def test_story_number_with_space():
    result = _parse_pick("2 this is my angle on the story", MOCK_PICKS)
    assert result is not None
    num, angle, fmt = result
    assert num == 2
    assert "this is my angle" in angle


@patch("generator.generator.parse_pick_with_llm", return_value=None)
def test_invalid_pick_returns_none(mock_llm):
    assert _parse_pick("post", MOCK_PICKS) is None
    assert _parse_pick("skip", MOCK_PICKS) is None
    assert _parse_pick("edit make it shorter", MOCK_PICKS) is None
    assert _parse_pick("", MOCK_PICKS) is None
    assert _parse_pick("hello there", MOCK_PICKS) is None


@patch("generator.generator.parse_pick_with_llm", return_value=None)
def test_out_of_range_number_returns_none(mock_llm):
    # 4, 5, 0 are not valid picks (only 1-3)
    assert _parse_pick("4", MOCK_PICKS) is None
    assert _parse_pick("0", MOCK_PICKS) is None


def test_pick_with_multiline_angle():
    result = _parse_pick("1\nthis is a longer take\nthat spans multiple lines", MOCK_PICKS)
    assert result is not None
    num, angle, fmt = result
    assert num == 1
    assert angle is not None


# ─────────────────────────────────────────────────────────────────
# STATE MACHINE TESTS (isolated, no real bot)
# ─────────────────────────────────────────────────────────────────

@patch("generator.generator.parse_pick_with_llm", return_value=None)
def test_skip_command_recognized(mock_llm):
    """'skip' should be handled at any state."""
    result = _parse_pick("skip", MOCK_PICKS)
    assert result is None   # skip is not a pick — handled separately


@patch("generator.generator.parse_pick_with_llm", return_value=None)
def test_cancel_command_recognized(mock_llm):
    result = _parse_pick("cancel", MOCK_PICKS)
    assert result is None


@patch("generator.generator.parse_pick_with_llm", return_value=None)
def test_format_override_commands_not_picks(mock_llm):
    for cmd in ("carousel", "image", "text", "post"):
        result = _parse_pick(cmd, MOCK_PICKS)
        assert result is None, f"'{cmd}' should not be parsed as a pick"
