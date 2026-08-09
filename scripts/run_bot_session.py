"""
scripts/run_bot_session.py
Single-shot Telegram webhook processor for GitHub Actions.

Reads a raw Telegram JSON payload from the TELEGRAM_PAYLOAD environment variable,
processes it through the bot handlers, and exits immediately.
This completely eliminates the need for long-polling and saves Actions minutes.

Usage:
    TELEGRAM_PAYLOAD='{"update_id":...}' python scripts/run_bot_session.py
"""

import asyncio
import os
import sys
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from telegram import Update
from telegram.ext import TypeHandler
from utils.logger import get_logger
from telegram_bot.bot import build_application, send_message

log = get_logger("bot_session")

def _parse_payload(payload_str: str) -> dict | None:
    """Safely parse JSON payload, unwrapping nested body or stringified JSON if needed."""
    try:
        data = json.loads(payload_str)
        if isinstance(data, str):
            # Double-encoded string
            data = json.loads(data)
        if isinstance(data, dict) and "body" in data:
            if isinstance(data["body"], str):
                data = json.loads(data["body"])
            elif isinstance(data["body"], dict):
                data = data["body"]
        return data if isinstance(data, dict) else None
    except Exception as e:
        log.warning(f"Payload parsing warning: {e}")
        return None

async def run_single_update():
    """
    Reads the raw Telegram update JSON from the environment,
    hydrates it into a python-telegram-bot Update object,
    and feeds it to the application.
    """
    payload_str = os.getenv("TELEGRAM_PAYLOAD")
    if not payload_str:
        log.warning("No TELEGRAM_PAYLOAD provided. Exiting.")
        return

    log.info("=== GitHub Actions: bot session (webhook) starting ===")
    
    data = _parse_payload(payload_str)
    if not data:
        log.error("Failed to parse valid JSON dict from TELEGRAM_PAYLOAD. Exiting.")
        await send_message("Failed to process webhook: invalid payload JSON format.")
        return

    app = build_application()
    
    # We use an asyncio.Event to keep the script running until processing finishes
    done_event = asyncio.Event()

    async def mark_done(u, c):
        if hasattr(c, "error") and c.error:
            log.error(f"Error handling update: {c.error}", exc_info=c.error)
        done_event.set()

    # Group 999 guarantees this runs last (unless an exception stops propagation)
    app.add_handler(TypeHandler(Update, mark_done), group=999)
    app.add_error_handler(mark_done)
    
    # Initialize and start the application so the background update processor runs
    await app.initialize()
    await app.start()
    
    try:
        # If payload missing update_id, synthesize one
        if "update_id" not in data and "message" in data:
            data["update_id"] = 1
        elif "update_id" not in data and "text" in data:
            # Synthetic simple update
            chat_id = data.get("chat_id") or int(os.getenv("TELEGRAM_CHAT_ID", "0"))
            data = {
                "update_id": 1,
                "message": {
                    "message_id": 1,
                    "date": 1700000000,
                    "chat": {"id": chat_id, "type": "private"},
                    "from": {"id": chat_id, "is_bot": False, "first_name": "User"},
                    "text": data.get("text", ""),
                }
            }

        update = Update.de_json(data, app.bot)
        log.info(f"Processing update_id: {getattr(update, 'update_id', 'unknown')}")
        
        # Queue the update
        await app.process_update(update)
        
        # Block until the update is processed (either success or error), max 10 minutes
        try:
            await asyncio.wait_for(done_event.wait(), timeout=600.0)
        except asyncio.TimeoutError:
            log.error("Timeout waiting for update to finish processing.")
            
    except Exception as e:
        log.error(f"Error processing update: {e}", exc_info=True)
        try:
            await send_message(f"Error processing message update: {e}")
        except Exception:
            pass
    finally:
        await app.stop()
        await app.shutdown()
        log.info("=== Bot session ended ===")

if __name__ == "__main__":
    asyncio.run(run_single_update())
