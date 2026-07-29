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
from utils.logger import get_logger
from telegram_bot.bot import build_application

log = get_logger("bot_session")

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
    
    app = build_application()
    
    # Initialize the application so handlers are registered
    await app.initialize()
    
    try:
        data = json.loads(payload_str)
        update = Update.de_json(data, app.bot)
        log.info(f"Processing update_id: {update.update_id}")
        
        # Process the single update
        await app.process_update(update)
        
    except json.JSONDecodeError as e:
        log.error(f"Failed to parse TELEGRAM_PAYLOAD JSON: {e}")
    except Exception as e:
        log.error(f"Error processing update: {e}")
    finally:
        await app.shutdown()
        log.info("=== Bot session ended ===")

if __name__ == "__main__":
    asyncio.run(run_single_update())
