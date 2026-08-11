import asyncio
import os
import sys
from datetime import datetime
import pytz

# Make sure project root is on the path when run as a script
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scraper.scraper import scrape_all
from scorer.scorer import rank_and_pick
from generator.generator import generate_morning_brief
from telegram_bot.bot import send_message
from utils.logger import get_logger, log_error
from utils.helpers import read_state, update_state
from config.settings import TIMEZONE

log = get_logger("run_pipeline")

def now_ist():
    return datetime.now(pytz.timezone(TIMEZONE))

def canonical_url(url: str) -> str:
    return url.split("?")[0].strip("/")

async def run_pipeline_logic():
    log.info("=== GitHub Actions: morning pipeline starting ===")
    
    state = read_state()
    today = now_ist().strftime("%Y-%m-%d")
    
    # Don't run twice in one day unless forced
    if state.get("date") == today and state.get("status") in ("waiting", "reminder_sent", "draft_sent", "posted", "skipped"):
        log.info(f"Pipeline already ran today (status: {state.get('status')}).")
        if not os.getenv("RUN_NOW") and not os.getenv("FORCE"):
            return

    update_state(status="processing")
    
    try:
        log.info("Step 1: Scraping stories...")
        stories = scrape_all()
        if not stories:
            await send_message("No stories found today. Scraping failed.")
            update_state(status="failed")
            return
            
        log.info("Step 2: Scoring and ranking...")
        picks = rank_and_pick(stories)
        if not picks:
            await send_message("No valid picks found today after scoring.")
            update_state(status="failed")
            return
            
        log.info("Step 3: Generating brief...")
        brief = generate_morning_brief(picks)
        
        # Save state
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
            current_screenshot_paths=None,
        )
        
        log.info("Step 4: Sending brief to Telegram...")
        await send_message(brief)
        log.info("=== Morning brief sent successfully ===")
        
    except Exception as e:
        log_error("Pipeline failed", e)
        try:
            await send_message(f"pipeline error — check logs/errors.log\\n{str(e)[:200]}")
        except Exception:
            pass
        update_state(status="failed")

if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    asyncio.run(run_pipeline_logic())
