"""
main.py
Entry point for LinkedIn Autopilot.

DEPLOYMENT MODES
────────────────
GitHub Actions (recommended / primary):
  - Schedule + bot session are handled by two separate GHA workflows:
      .github/workflows/morning-pipeline.yml  → runs scripts/run_pipeline.py
      .github/workflows/bot-session.yml       → runs scripts/run_bot_session.py
  - This file is NOT used by GHA.  State is persisted via GitHub Gist.
  - See scripts/setup_gist_state.py to create the Gist before first deploy.

Local / Render (legacy fallback):
  - Run `python main.py` to start the APScheduler + Telegram bot polling loop.
  - State is stored in state/today.json on disk.
  - Set STATE_BACKEND=file (or leave unset) in .env for local mode.
"""

import sys
import asyncio

# Fix Playwright asyncio subprocess error on Windows
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

import time
import os
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz
from aiohttp import web

from config.settings import TIMEZONE, POST_TIME, SKIP_AFTER_MINUTES, RUN_NOW, AUTOPILOT_MODE
from utils.logger import get_logger, log_error, log_skip, log_post, get_streak
from utils.helpers import read_state, update_state, now_ist, canonical_url
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
    await check_linkedin_token()
    state = read_state()

    # Don't run twice on the same day
    today = now_ist().strftime("%Y-%m-%d")
    if state.get("date") == today and state.get("status") not in ("idle", None, "skipped", "posted", "cancelled", "failed"):
        log.info(f"Pipeline already ran today ({state.get('status')}) — skipping")
        return

    update_state(status="processing", date=today)

    try:
        # Step 1: Scrape
        log.info("Step 1: Scraping...")
        stories = scrape_all()

        if not stories:
            log.warning("No stories scraped — skipping today")
            await send_message("no stories found today. check logs/errors.log")
            update_state(status="failed", date=today)
            return

        # Step 2 & 3: Score and rank
        log.info(f"Step 2: Scoring {len(stories)} stories...")
        picks = rank_and_pick(stories)

        if not picks:
            log.warning("No picks after scoring")
            await send_message("scoring returned no picks. check logs/errors.log")
            update_state(status="failed", date=today)
            return

        if AUTOPILOT_MODE:
            log.info("AUTOPILOT_MODE is ON. Automatically generating and publishing top pick.")
            story = picks[0]
            format_type = story.get("format_suggestion", "text")
            
            from generator.generator import generate_post
            from linkedin.poster import post_text_to_linkedin, post_carousel_to_linkedin, post_image_to_linkedin
            from carousel.carousel_gen import generate_carousel_pdf
            from telegram_bot.screenshotter import take_screenshots_for_story
            
            log.info(f"Auto-generating {format_type} post...")
            try:
                result = generate_post(story, post_type=format_type, angle=None)
            except Exception as e:
                log_error("Auto-generation failed", e)
                await send_message(f"Autopilot generation failed: {e}")
                update_state(status="failed", date=today)
                return
                
            post_text = result.get("post_text", "")
            carousel_data = result.get("carousel_data")
            actual_format = result.get("post_type", format_type)
            
            log.info(f"Publishing {actual_format} post to LinkedIn...")
            try:
                if actual_format == "carousel":
                    pdf_path = generate_carousel_pdf(carousel_data)
                    headline = carousel_data.get("slides", [{}])[0].get("heading", story.get("title", ""))
                    url = post_carousel_to_linkedin(pdf_path, post_text, headline)
                elif actual_format == "image":
                    paths = await take_screenshots_for_story(story)
                    if paths and os.path.exists(paths[0]):
                        url = post_image_to_linkedin(paths[0], post_text)
                    else:
                        log.warning("No screenshot found for image post, falling back to text post")
                        url = post_text_to_linkedin(post_text)
                else:
                    url = post_text_to_linkedin(post_text)
            except Exception as e:
                log_error("Auto-publish failed", e)
                await send_message(f"Autopilot publishing failed: {e}")
                update_state(status="failed", date=today)
                return
                
            log_post(
                story=story,
                format_type=actual_format,
                post_text=post_text,
                your_angle="[AUTOPILOT]",
                linkedin_url=url,
            )
            update_state(status="posted", linkedin_url=url, date=today)
            await send_message(f"Autopilot run complete. Published to LinkedIn:\n{url}")
            return

        # Step 4: Format morning brief
        log.info("Step 3: Formatting morning brief...")
        brief = generate_morning_brief(picks)

        # Step 5: Save state
        sent_at = now_ist().strftime("%H:%M IST")
        
        past_urls = set(state.get("past_urls", []))
        for p in picks:
            past_urls.add(canonical_url(p.get("url", "")))
            
        update_state(
            date=today,
            picks=picks,
            past_urls=list(past_urls),
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
    finally:
        current_state = read_state()
        if current_state.get("status") == "processing":
            log.warning("Pipeline exited while still in processing state — resetting status to failed")
            update_state(status="failed")


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

        # Webhook Protection: Prevent accidental deletion of production webhooks
        webhook_info = await app.bot.get_webhook_info()
        if webhook_info.url:
            log.warning(f"A webhook is currently active: {webhook_info.url}")
            if os.getenv("FORCE_POLLING") != "true":
                log.error("Aborting local polling to protect production webhook. Set FORCE_POLLING=true in .env to override.")
                return

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
