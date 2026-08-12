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
@patch("scripts.run_pipeline.send_message", new_callable=AsyncMock)
@patch("scripts.run_pipeline.scrape_all", return_value=MOCK_PICKS)
@patch("scripts.run_pipeline.rank_and_pick", return_value=MOCK_PICKS)
@patch("scripts.run_pipeline.read_state", return_value={"date": "1970-01-01", "status": "idle"})
@patch("scripts.run_pipeline.update_state")
async def test_full_pipeline_sends_brief(mock_update, mock_state, mock_rank, mock_scrape, mock_send):
    """Pipeline runs, scrapes, ranks, and sends morning brief via Telegram."""
    from scripts.run_pipeline import run_pipeline_logic

    await run_pipeline_logic()

    assert mock_send.called
    brief_text = mock_send.call_args[0][0]

    # Brief should contain all 3 picks
    assert "1." in brief_text
    assert "2." in brief_text
    assert "3." in brief_text


@pytest.mark.asyncio
@patch("scripts.run_pipeline.send_message", new_callable=AsyncMock)
@patch("scripts.run_pipeline.scrape_all", return_value=[])
@patch("scripts.run_pipeline.read_state", return_value={"date": "1970-01-01", "status": "idle"})
@patch("scripts.run_pipeline.update_state")
async def test_pipeline_handles_empty_scrape(mock_update, mock_state, mock_scrape, mock_send):
    """Pipeline should notify and exit gracefully when no stories found."""
    from scripts.run_pipeline import run_pipeline_logic

    await run_pipeline_logic()

    assert mock_send.called
    message = mock_send.call_args[0][0]
    assert "no stories" in message.lower()


@pytest.mark.asyncio
@patch("scripts.run_pipeline.send_message", new_callable=AsyncMock)
@patch("scripts.run_pipeline.scrape_all", side_effect=Exception("network error"))
@patch("scripts.run_pipeline.read_state", return_value={"date": "1970-01-01", "status": "idle"})
@patch("scripts.run_pipeline.update_state")
async def test_pipeline_handles_scrape_exception(mock_update, mock_state, mock_scrape, mock_send):
    """Pipeline should send error message and not crash on scrape failure."""
    from scripts.run_pipeline import run_pipeline_logic

    await run_pipeline_logic()  # Should not raise

    assert mock_send.called





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
    try:
        os.remove("logs/test_daily_log_temp.json")
    except OSError:
        pass


def test_timestamp_to_age_hours_null_safety():
    """Verify timestamp_to_age_hours(None) returns 0.0 without raising TypeError."""
    from utils.helpers import timestamp_to_age_hours
    assert timestamp_to_age_hours(None) == 0.0


def test_voice_handler_lazy_groq_client():
    """Verify voice_handler imports cleanly and initializes client lazily."""
    import telegram_bot.voice_handler as vh
    # Module import should not instantiate Groq client immediately
    assert vh._client is None
    with patch("telegram_bot.voice_handler.Groq") as mock_groq:
        mock_groq.return_value = MagicMock()
        client = vh._get_groq_client()
        assert client is not None
        mock_groq.assert_called_once()


@pytest.mark.asyncio
@patch("scripts.run_pipeline.send_message", new_callable=AsyncMock)
@patch("scripts.run_pipeline.scrape_all", side_effect=RuntimeError("unexpected crash"))
@patch("scripts.run_pipeline.read_state")
@patch("scripts.run_pipeline.update_state")
async def test_main_pipeline_finally_resets_processing_status(mock_update, mock_read, mock_scrape, mock_send):
    """If an uncaught exception occurs during processing, main_pipeline finally resets status to failed."""
    from scripts.run_pipeline import run_pipeline_logic
    mock_read.side_effect = [
        {"date": "1970-01-01", "status": "idle"},
        {"date": "2026-08-09", "status": "processing"}
    ]

    await run_pipeline_logic()

    # Verify update_state was called with status="failed"
    status_calls = [call.kwargs.get("status") for call in mock_update.call_args_list]
    assert "failed" in status_calls

