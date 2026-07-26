"""
scripts/run_bot_session.py
Bounded Telegram polling session for the GitHub Actions bot-session workflow.

Replaces the forever-running app.updater.start_polling() + APScheduler combo
with a clean async loop that:
  - Polls Telegram for new messages (long-polling, 30s timeout)
  - Routes each message through the existing _handle_message logic
  - Sends a reminder at REMINDER_AFTER_MINUTES (default 60 min)
  - Exits cleanly when:
      * User posts to LinkedIn   (status == "posted")
      * User skips               (status == "skipped" / "cancelled")
      * SKIP_AFTER_MINUTES pass  (default 120 min) with no action → auto-skip
      * Unhandled exception

Usage:
    python -m scripts.run_bot_session
    python scripts/run_bot_session.py
"""

import asyncio
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from telegram import Bot, Update
from telegram.ext import Application

from config.settings import (
    TELEGRAM_BOT_TOKEN,
    TELEGRAM_CHAT_ID,
    REMINDER_AFTER_MINUTES,
    SKIP_AFTER_MINUTES,
)
from utils.helpers import read_state
from utils.logger import get_logger
from telegram_bot.bot import build_application, send_reminder, handle_skip_timeout, send_message

log = get_logger("bot_session")

# Terminal states — when we hit any of these, the session is done
TERMINAL_STATUSES = {"posted", "skipped", "cancelled"}


async def run_session():
    """
    Bounded polling loop.  Polls Telegram, routes messages through the
    existing handler, and exits when the session is done or timeout hits.
    """
    log.info("=== GitHub Actions: bot session starting ===")

    app = build_application()
    bot: Bot = app.bot

    session_start = time.monotonic()
    reminder_sent = False
    last_update_id = 0

    # Initialize the application so handlers are registered
    await app.initialize()
    log.info("Bot application initialized — starting polling loop")

    try:
        while True:
            elapsed_min = (time.monotonic() - session_start) / 60

            # ── Check terminal state ──────────────────────────────
            state = read_state()
            status = state.get("status", "idle")
            if status in TERMINAL_STATUSES:
                log.info(f"Session complete — status: {status}")
                break

            # ── Reminder ──────────────────────────────────────────
            if not reminder_sent and elapsed_min >= REMINDER_AFTER_MINUTES:
                if status in ("waiting", "reminder_sent"):
                    log.info("Sending reminder")
                    await send_reminder()
                    reminder_sent = True

            # ── Auto-skip timeout ─────────────────────────────────
            if elapsed_min >= SKIP_AFTER_MINUTES:
                log.info(f"{SKIP_AFTER_MINUTES} min elapsed with no action — auto-skipping")
                await handle_skip_timeout()
                await send_message(
                    f"no reply in {SKIP_AFTER_MINUTES} min. skipping today. "
                    "see you tomorrow at 7."
                )
                break

            # ── Fetch Telegram updates ────────────────────────────
            try:
                updates = await bot.get_updates(
                    offset=last_update_id + 1,
                    timeout=30,          # long-poll timeout (seconds)
                    allowed_updates=["message"],
                )
            except Exception as e:
                log.warning(f"get_updates error: {e} — retrying in 5s")
                await asyncio.sleep(5)
                continue

            for raw_update in updates:
                last_update_id = raw_update.update_id
                try:
                    update = Update.de_json(raw_update.to_dict(), bot)
                    # Process through all registered handlers
                    await app.process_update(update)
                except Exception as e:
                    log.error(f"Error processing update {raw_update.update_id}: {e}")

            # Short sleep between poll cycles when no updates
            if not updates:
                await asyncio.sleep(1)

    finally:
        await app.shutdown()
        log.info("=== Bot session ended ===")


if __name__ == "__main__":
    asyncio.run(run_session())
