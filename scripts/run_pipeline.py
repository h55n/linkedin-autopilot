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

# Make sure project root is on the path when run as a script
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.logger import get_logger
from main import main_pipeline

log = get_logger("run_pipeline")


async def run():
    log.info("=== GitHub Actions: morning pipeline starting ===")
    await main_pipeline()
    log.info("=== Pipeline complete — exiting ===")


if __name__ == "__main__":
    asyncio.run(run())
