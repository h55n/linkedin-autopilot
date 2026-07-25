"""
main.py
Entry point for LinkedIn Autopilot.
Starts the APScheduler (cron) and the Telegram bot polling loop.
"""

import asyncio
import time
import os
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz
from aiohttp import web

from config.settings import TIMEZONE, POST_TIME, SKIP_AFTER_MINUTES, RUN_NOW
from utils.logger import get_logger, log_error, log_skip
from utils.helpers import read_state, update_state, now_ist
from telegram_bot.bot import build_application, send_message, send_reminder, handle_skip_timeout
from scraper.scraper import scrape_all
from scorer.scorer import rank_and_pick
from generator.generator import generate_morning_brief

log = get_logger("main")

# Ensure state and logs dirs exist
os.makedirs("state", exist_ok=True)
os.makedirs("logs", exist_ok=True)
os.makedirs("carousel/output", exist_ok=True)


# ─────────────────────────────────────────────────────────────────
# PIPELINE
# ─────────────────────────────────────────────────────────────────

async def main_pipeline():
    """
    The daily pipeline: scrape → score → brief → wait for reply.
    Called at 07:00 AM IST by scheduler.
    """
    log.info("=== Pipeline starting ===")
    state = read_state()

    # Don't run twice on the same day
    today = now_ist().strftime("%Y-%m-%d")
    if state.get("date") == today and state.get("status") not in ("idle", None, "skipped", "posted", "cancelled"):
        log.info(f"Pipeline already ran today ({state.get('status')}) — skipping")
        return

    try:
        # Step 1: Scrape
        log.info("Step 1: Scraping...")
        stories = scrape_all()

        if not stories:
            log.warning("No stories scraped — skipping today")
            await send_message("no stories found today. check logs/errors.log")
            return

        # Step 2 & 3: Score and rank
        log.info(f"Step 2: Scoring {len(stories)} stories...")
        picks = rank_and_pick(stories)

        if not picks:
            log.warning("No picks after scoring")
            await send_message("scoring returned no picks. check logs/errors.log")
            return

        # Step 4: Format morning brief
        log.info("Step 3: Formatting morning brief...")
        brief = generate_morning_brief(picks)

        # Step 5: Save state
        sent_at = now_ist().strftime("%H:%M IST")
        update_state(
            date=today,
            picks=picks,
            status="waiting",
            sent_at=sent_at,
            selected_story=None,
            user_angle=None,
            current_draft=None,
            current_format=None,
            current_carousel_data=None,
            linkedin_url=None,
        )

        # Step 6: Send brief
        await send_message(brief)
        log.info("Morning brief sent")

    except Exception as e:
        log_error("Pipeline failed", e)
        try:
            await send_message(f"pipeline error — check logs/errors.log\n{str(e)[:200]}")
        except Exception:
            pass


async def check_reminder():
    """Called 1h after brief — send reminder if still waiting."""
    state = read_state()
    today = now_ist().strftime("%Y-%m-%d")

    if state.get("date") != today:
        return
    if state.get("status") == "waiting":
        log.info("Sending reminder")
        await send_reminder()


async def check_skip():
    """Called 2h after brief — skip if still no reply."""
    state = read_state()
    today = now_ist().strftime("%Y-%m-%d")

    if state.get("date") != today:
        return
    if state.get("status") in ("waiting", "reminder_sent"):
        log.info("Skip timeout reached")
        await handle_skip_timeout()
        await send_message("no reply in 2 hours. skipping today. see you tomorrow at 7.")


async def check_linkedin_token():
    """Daily check: warn if LinkedIn token is approaching expiry."""
    from linkedin.poster import _check_token_age
    from telegram_bot.messages import TOKEN_EXPIRY_WARNING

    days_old = _check_token_age()
    if days_old >= 55:
        days_left = 60 - days_old
        await send_message(TOKEN_EXPIRY_WARNING.format(days_old=days_old, days_left=days_left))


# ─────────────────────────────────────────────────────────────────
# SCHEDULER SETUP
# ─────────────────────────────────────────────────────────────────

def build_scheduler() -> AsyncIOScheduler:
    tz = pytz.timezone(TIMEZONE)
    scheduler = AsyncIOScheduler(timezone=tz)

    # Parse POST_TIME (default "07:00")
    try:
        post_hour, post_minute = [int(x) for x in POST_TIME.split(":")]
    except ValueError:
        post_hour, post_minute = 7, 0

    # Main pipeline job
    scheduler.add_job(
        main_pipeline,
        CronTrigger(hour=post_hour, minute=post_minute, timezone=tz),
        id="main_pipeline",
        replace_existing=True,
    )

    # Reminder job (1h after pipeline)
    reminder_minute = (post_minute + 60) % 60
    reminder_hour = post_hour + ((post_minute + 60) // 60)
    scheduler.add_job(
        check_reminder,
        CronTrigger(hour=reminder_hour % 24, minute=reminder_minute, timezone=tz),
        id="reminder",
        replace_existing=True,
    )

    # Skip job (2h after pipeline)
    skip_minute = (post_minute + 120) % 60
    skip_hour = post_hour + ((post_minute + 120) // 60)
    scheduler.add_job(
        check_skip,
        CronTrigger(hour=skip_hour % 24, minute=skip_minute, timezone=tz),
        id="skip_check",
        replace_existing=True,
    )

    # Token check job (daily at 06:00)
    scheduler.add_job(
        check_linkedin_token,
        CronTrigger(hour=6, minute=0, timezone=tz),
        id="token_check",
        replace_existing=True,
    )

    return scheduler


# ─────────────────────────────────────────────────────────────────
# DUMMY WEB SERVER (For Render Free Tier)
# ─────────────────────────────────────────────────────────────────

async def health_check(request):
    return web.Response(text="OK")

async def start_web_server():
    port = int(os.environ.get("PORT", 8080))
    app = web.Application()
    app.add_routes([web.get('/', health_check)])
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    log.info(f"Dummy web server started on port {port}")

# ─────────────────────────────────────────────────────────────────
# ENTRYPOINT
# ─────────────────────────────────────────────────────────────────

async def run():
    log.info("LinkedIn Autopilot starting up")

    # Build Telegram bot
    app = build_application()

    # Build scheduler
    scheduler = build_scheduler()
    scheduler.start()

    log.info(f"Scheduler started — daily pipeline at {POST_TIME} {TIMEZONE}")

    # Start dummy web server for Render Free Tier
    await start_web_server()

    # If RUN_NOW env var is set — run pipeline immediately (for testing)
    if RUN_NOW:
        log.info("RUN_NOW=true — running pipeline immediately")
        asyncio.create_task(main_pipeline())

    # Start bot polling (this blocks until stopped)
    async with app:
        await app.initialize()
        await app.start()
        await app.updater.start_polling()
        log.info("Telegram bot polling started")

        # Keep alive
        try:
            while True:
                await asyncio.sleep(1)
        except (KeyboardInterrupt, SystemExit):
            log.info("Shutdown signal received")
        finally:
            scheduler.shutdown()
            await app.stop()
            await app.shutdown()


if __name__ == "__main__":
    asyncio.run(run())
