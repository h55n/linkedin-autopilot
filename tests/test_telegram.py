"""
tests/test_telegram.py
Tests for Telegram bot message parsing and state machine logic.
"""

import pytest
from telegram_bot.bot import _parse_pick


# ─────────────────────────────────────────────────────────────────
# PARSE_PICK TESTS
# ─────────────────────────────────────────────────────────────────

def test_story_number_parsed_correctly():
    result = _parse_pick("2, here's my take on this")
    assert result is not None
    num, angle = result
    assert num == 2
    assert "here's my take" in angle


def test_story_number_only():
    result = _parse_pick("1")
    assert result is not None
    num, angle = result
    assert num == 1
    assert angle is None


def test_story_number_with_period():
    result = _parse_pick("3. use this for your own project")
    assert result is not None
    num, angle = result
    assert num == 3
    assert "use this" in angle


def test_story_number_with_space():
    result = _parse_pick("2 this is my angle on the story")
    assert result is not None
    num, angle = result
    assert num == 2
    assert "this is my angle" in angle


def test_invalid_pick_returns_none():
    assert _parse_pick("post") is None
    assert _parse_pick("skip") is None
    assert _parse_pick("edit make it shorter") is None
    assert _parse_pick("") is None
    assert _parse_pick("hello there") is None


def test_out_of_range_number_returns_none():
    # 4, 5, 0 are not valid picks (only 1-3)
    assert _parse_pick("4") is None
    assert _parse_pick("0") is None


def test_pick_with_multiline_angle():
    result = _parse_pick("1\nthis is a longer take\nthat spans multiple lines")
    assert result is not None
    num, angle = result
    assert num == 1
    assert angle is not None


# ─────────────────────────────────────────────────────────────────
# STATE MACHINE TESTS (isolated, no real bot)
# ─────────────────────────────────────────────────────────────────

def test_skip_command_recognized():
    """'skip' should be handled at any state."""
    result = _parse_pick("skip")
    assert result is None   # skip is not a pick — handled separately


def test_cancel_command_recognized():
    result = _parse_pick("cancel")
    assert result is None


def test_format_override_commands_not_picks():
    for cmd in ("carousel", "image", "text", "post"):
        result = _parse_pick(cmd)
        assert result is None, f"'{cmd}' should not be parsed as a pick"
