"""
scripts/run_pipeline.py
Thin entrypoint for GitHub Actions morning-pipeline workflow.

Runs main_pipeline() exactly once, then exits.
No scheduler, no web server, no Telegram polling loop.

Usage:
    python -m scripts.run_pipeline
    python scripts/run_pipeline.py
"""

import asyncio
import os
import sys
import time
from datetime import datetime, timedelta

# Make sure project root is on the path when run as a script
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytz
from config.settings import TIMEZONE, POST_TIME
from utils.logger import get_logger
from main import main_pipeline

log = get_logger("run_pipeline")


async def wait_for_post_time():
    """Wait until exactly POST_TIME (e.g. 07:00) in the configured TIMEZONE."""
    tz = pytz.timezone(TIMEZONE)
    now = datetime.now(tz)
    
    try:
        post_hour, post_minute = [int(x) for x in POST_TIME.split(":")]
    except ValueError:
        post_hour, post_minute = 7, 0

    target = now.replace(hour=post_hour, minute=post_minute, second=0, microsecond=0)
    
    # If the target time has already passed today, we assume we're running late
    # and just execute immediately.
    if now >= target:
        log.info(f"Target time {POST_TIME} {TIMEZONE} has already passed. Executing immediately.")
        return

    wait_seconds = (target - now).total_seconds()
    log.info(f"Woke up early! Waiting {wait_seconds / 60:.1f} minutes until {POST_TIME} {TIMEZONE}...")
    await asyncio.sleep(wait_seconds)
    log.info(f"Target time {POST_TIME} {TIMEZONE} reached! Executing now.")


async def run():
    log.info("=== GitHub Actions: morning pipeline starting ===")
    await wait_for_post_time()
    await main_pipeline()
    log.info("=== Pipeline complete — exiting ===")


if __name__ == "__main__":
    asyncio.run(run())
