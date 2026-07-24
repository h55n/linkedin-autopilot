"""
tests/test_pipeline.py
End-to-end integration tests — all external calls mocked.
Tests the full pipeline flow from scrape to post.
"""

import pytest
import json
import asyncio
import time
from unittest.mock import patch, MagicMock, AsyncMock
from tests.conftest import make_story


SAMPLE_POST = "mistral 7b just matched gpt-4 on humaneval. runs locally on a macbook. indian devs on tight budgets now have a real option."

MOCK_PICKS = [
    make_story(
        id="p1", url="https://example.com/1",
        title="mistral releases 7b model that matches gpt-4",
        format_suggestion="text", source="hackernews", score=800, age_hours=1.0,
    ),
    make_story(
        id="p2", url="https://inc42.com/story",
        title="bangalore startup raises 12m for ai in bharat languages",
        format_suggestion="text", source="inc42", region="india", score=200, age_hours=1.5,
    ),
    make_story(
        id="p3", url="https://github.com/cool/tool",
        title="open source tool that converts figma to react",
        format_suggestion="image", source="hackernews", is_tool_launch=True, score=600, age_hours=2.0,
    ),
]


# ─────────────────────────────────────────────────────────────────
# FULL PIPELINE TEST
# ─────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
@patch("main.send_message", new_callable=AsyncMock)
@patch("main.scrape_all", return_value=MOCK_PICKS)
@patch("main.rank_and_pick", return_value=MOCK_PICKS)
@patch("main.read_state", return_value={"date": "1970-01-01", "status": "idle"})
@patch("main.update_state")
async def test_full_pipeline_sends_brief(mock_update, mock_state, mock_rank, mock_scrape, mock_send):
    """Pipeline runs, scrapes, ranks, and sends morning brief via Telegram."""
    from main import main_pipeline

    await main_pipeline()

    assert mock_send.called
    brief_text = mock_send.call_args[0][0]

    # Brief should contain all 3 picks
    assert "1." in brief_text
    assert "2." in brief_text
    assert "3." in brief_text


@pytest.mark.asyncio
@patch("main.send_message", new_callable=AsyncMock)
@patch("main.scrape_all", return_value=[])
@patch("main.read_state", return_value={"date": "1970-01-01", "status": "idle"})
@patch("main.update_state")
async def test_pipeline_handles_empty_scrape(mock_update, mock_state, mock_scrape, mock_send):
    """Pipeline should notify and exit gracefully when no stories found."""
    from main import main_pipeline

    await main_pipeline()

    assert mock_send.called
    message = mock_send.call_args[0][0]
    assert "no stories" in message.lower()


@pytest.mark.asyncio
@patch("main.send_message", new_callable=AsyncMock)
@patch("main.scrape_all", side_effect=Exception("network error"))
@patch("main.read_state", return_value={"date": "1970-01-01", "status": "idle"})
@patch("main.update_state")
async def test_pipeline_handles_scrape_exception(mock_update, mock_state, mock_scrape, mock_send):
    """Pipeline should send error message and not crash on scrape failure."""
    from main import main_pipeline

    await main_pipeline()  # Should not raise

    assert mock_send.called


# ─────────────────────────────────────────────────────────────────
# SKIP FLOW TEST
# ─────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
@patch("main.send_message", new_callable=AsyncMock)
@patch("main.read_state")
@patch("main.handle_skip_timeout", new_callable=AsyncMock)
async def test_pipeline_skips_on_no_reply(mock_skip_timeout, mock_read, mock_send):
    """After 2h timeout, handle_skip_timeout is called and skip message sent."""
    from main import check_skip, now_ist

    today = now_ist().strftime("%Y-%m-%d")
    mock_read.return_value = {
        "date": today,
        "status": "waiting",
        "sent_at": "07:00 IST",
    }

    await check_skip()

    assert mock_skip_timeout.called
    assert mock_send.called
    skip_msg = mock_send.call_args[0][0]
    assert "skip" in skip_msg.lower()


# ─────────────────────────────────────────────────────────────────
# REMINDER FLOW TEST
# ─────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
@patch("main.send_reminder", new_callable=AsyncMock)
@patch("main.read_state")
async def test_reminder_sent_after_1h(mock_read, mock_reminder):
    """Reminder should be sent when status is 'waiting'."""
    from main import check_reminder, now_ist

    today = now_ist().strftime("%Y-%m-%d")
    mock_read.return_value = {
        "date": today,
        "status": "waiting",
    }

    await check_reminder()
    assert mock_reminder.called


@pytest.mark.asyncio
@patch("main.send_reminder", new_callable=AsyncMock)
@patch("main.read_state")
async def test_no_reminder_if_already_posted(mock_read, mock_reminder):
    """No reminder if status is 'posted'."""
    from main import check_reminder, now_ist

    today = now_ist().strftime("%Y-%m-%d")
    mock_read.return_value = {"date": today, "status": "posted"}

    await check_reminder()
    assert not mock_reminder.called


# ─────────────────────────────────────────────────────────────────
# STATE PERSISTENCE TEST
# ─────────────────────────────────────────────────────────────────

def test_state_write_and_read():
    """State should survive a write/read cycle."""
    import tempfile, os
    from utils.helpers import read_state, write_state

    test_data = {
        "date": "2025-01-01",
        "status": "waiting",
        "picks": MOCK_PICKS,
    }

    # Patch STATE_FILE to a temp file
    with patch("utils.helpers.STATE_FILE", "state/test_state_temp.json"):
        write_state(test_data)
        recovered = read_state()

    assert recovered["status"] == "waiting"
    assert len(recovered["picks"]) == 3

    # Cleanup
    try:
        os.remove("state/test_state_temp.json")
    except OSError:
        pass


# ─────────────────────────────────────────────────────────────────
# LOGGER TEST
# ─────────────────────────────────────────────────────────────────

def test_log_post_writes_entry():
    """log_post should write a valid entry to daily_log.json."""
    import os, json
    from utils.logger import log_post

    story = MOCK_PICKS[0]
    with patch("utils.logger.DAILY_LOG_FILE", "logs/test_daily_log_temp.json"):
        with patch("utils.logger.STREAK_FILE", "logs/test_streak_temp.json"):
            entry = log_post(
                story=story,
                format_type="text",
                post_text=SAMPLE_POST,
                your_angle="my angle here",
                linkedin_url="https://linkedin.com/feed/update/123",
            )

    assert entry["story_title"] == story["title"]
    assert entry["format"] == "text"
    assert entry["status"] == "posted"

    # Cleanup
    for f in ["logs/test_daily_log_temp.json", "logs/test_streak_temp.json"]:
        try:
            os.remove(f)
        except OSError:
            pass
