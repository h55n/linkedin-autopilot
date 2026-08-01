"""
telegram_bot/bot.py
Telegram bot — the daily interface.
Maintains conversation state in state/today.json.
Only responds to TELEGRAM_CHAT_ID — all other messages are silently ignored.
"""

import os
import re
import asyncio
from telegram import Update, Bot
from telegram.ext import (
    Application, MessageHandler, filters, ContextTypes, CommandHandler
)
from utils.logger import get_logger, log_error, log_skip, log_post, get_streak, get_recent_log
from utils.helpers import read_state, update_state
from telegram_bot.messages import (
    PROCESSING, TRANSCRIBING, DRAFT_TEMPLATE, POSTED_CONFIRM,
    CANCELLED, SKIP_CONFIRM, ERROR_VOICE, ERROR_GENERATE,
    ERROR_POST, IMAGE_INSTRUCTION, FORMAT_LABELS,
    STATUS_IDLE, STATUS_WAITING, STATUS_DRAFT_SENT, STATUS_POSTING,
    STATUS_POSTED, STATUS_SKIPPED, LOG_SUMMARY_HEADER,
    LOG_ENTRY_POSTED, LOG_ENTRY_SKIPPED,
)
from telegram_bot.voice_handler import transcribe_voice
from generator.generator import generate_post, generate_post_with_edit
from linkedin.poster import post_text_to_linkedin, post_carousel_to_linkedin, post_image_to_linkedin
from carousel.carousel_gen import generate_carousel_pdf
from telegram_bot.screenshotter import take_screenshots_for_story
from scraper.researcher import research_topic
from config.settings import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

log = get_logger("telegram_bot")


# ─────────────────────────────────────────────────────────────────
# BOT APPLICATION
# ─────────────────────────────────────────────────────────────────

def build_application() -> Application:
    """Build and return the Telegram bot application."""
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.ALL, _handle_message))
    app.add_handler(CommandHandler("status", _handle_status))
    app.add_handler(CommandHandler("log", _handle_log))
    app.add_handler(CommandHandler("research", _handle_research))
    return app


async def send_message(text: str):
    """Send a message to the owner's Telegram chat."""
    bot = Bot(token=TELEGRAM_BOT_TOKEN)
    await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=text)


async def send_reminder():
    from telegram_bot.messages import REMINDER
    await send_message(REMINDER)
    update_state(status="reminder_sent")
    log.info("Reminder sent")


async def handle_skip_timeout():
    """Called by scheduler when no reply after 2h."""
    state = read_state()
    if state.get("status") in ("waiting", "reminder_sent"):
        log_skip("no_reply")
        update_state(status="skipped")
        log.info("Day skipped — no reply")


# ─────────────────────────────────────────────────────────────────
# MESSAGE HANDLER
# ─────────────────────────────────────────────────────────────────

async def _handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Security: only respond to the owner
    if update.effective_chat.id != TELEGRAM_CHAT_ID:
        return

    msg = update.message
    if not msg:
        return

    state = read_state()
    current_status = state.get("status", "idle")

    # Voice note
    if msg.voice:
        await _handle_voice(msg, state, context)
        return

    text = (msg.text or "").strip()
    if not text:
        return

    text_lower = text.lower()

    # ── Commands that work in any state ──────────────────────────

    if text_lower == "skip":
        log_skip("user_skipped")
        update_state(status="skipped")
        streak = get_streak()
        await msg.reply_text(SKIP_CONFIRM.format(streak=streak))
        return

    if text_lower == "cancel":
        update_state(status="idle")
        await msg.reply_text(CANCELLED)
        return

    # ── State: waiting for story pick ────────────────────────────

    if current_status in ("waiting", "reminder_sent"):
        parsed = _parse_pick(text)
        if parsed:
            story_num, angle = parsed
            picks = state.get("picks", [])

            if story_num < 1 or story_num > len(picks):
                await msg.reply_text(f"pick a number between 1 and {len(picks)}")
                return

            story = picks[story_num - 1]
            format_type = story.get("format_suggestion", "text")

            update_state(
                status="processing",
                selected_story=story,
                user_angle=angle,
                current_format=format_type,
            )

            await msg.reply_text(PROCESSING)
            await _generate_and_send_draft(msg, story, format_type, angle)
        else:
            await msg.reply_text("reply with a number (1, 2, or 3) + your take")
        return

    # ── State: draft sent, waiting for action ────────────────────

    if current_status == "draft_sent":
        story = state.get("selected_story", {})
        current_format = state.get("current_format", "text")
        current_draft = state.get("current_draft", "")

        if text_lower == "post":
            await _publish(msg, state, story, current_format, current_draft)

        elif text_lower.startswith("edit "):
            edit_note = text[5:].strip()
            await msg.reply_text(PROCESSING)
            await _regenerate_with_edit(msg, story, current_format, current_draft, edit_note, state)

        elif text_lower in ("carousel", "image", "text"):
            new_format = text_lower
            angle = state.get("user_angle")
            update_state(current_format=new_format)
            await msg.reply_text(PROCESSING)
            await _generate_and_send_draft(msg, story, new_format, angle)

        else:
            await msg.reply_text(
                "not sure what to do. reply:\n"
                "'post' to publish\n"
                "'edit [instruction]' to tweak\n"
                "'carousel' / 'image' / 'text' to switch format\n"
                "'cancel' to drop it"
            )
        return

    # ── Catch-all for idle state ──────────────────────────────────
    await msg.reply_text(
        "nothing to do right now. next brief at 7 AM IST.\n"
        "reply 'status' to check current state.\n"
        "use '/research <topic>' to research and generate a post on-demand."
    )


async def _handle_voice(msg, state: dict, context):
    """Handle a voice note — transcribe and use as angle."""
    current_status = state.get("status", "idle")

    if current_status not in ("waiting", "reminder_sent"):
        await msg.reply_text("send a story number first, then a voice note with your take.")
        return

    await msg.reply_text(TRANSCRIBING)
    file_id = msg.voice.file_id

    text = transcribe_voice(file_id)
    if not text:
        await msg.reply_text(ERROR_VOICE)
        return

    await msg.reply_text(f"heard: \"{text}\"\n\ngenerating post...")

    # Use the transcribed text like a typed pick — but we need a story number
    # For voice, we assume story was already picked or parse from context
    picks = state.get("picks", [])
    selected = state.get("selected_story")

    if not selected and picks:
        selected = picks[0]   # default to first pick if no selection yet

    if not selected:
        await msg.reply_text("no story selected. reply with 1, 2, or 3 first.")
        return

    format_type = selected.get("format_suggestion", "text")
    update_state(
        status="processing",
        selected_story=selected,
        user_angle=text,
        current_format=format_type,
    )

    await _generate_and_send_draft(msg, selected, format_type, text)


# ─────────────────────────────────────────────────────────────────
# GENERATION
# ─────────────────────────────────────────────────────────────────

async def _generate_and_send_draft(msg, story: dict, format_type: str, angle: str = None):
    try:
        result = generate_post(story, post_type=format_type, angle=angle)
    except Exception as e:
        log_error("Post generation failed", e)
        await msg.reply_text(ERROR_GENERATE)
        update_state(status="waiting")
        return

    post_text = result.get("post_text", "")
    carousel_data = result.get("carousel_data")
    actual_format = result.get("post_type", format_type)

    # Format label for display
    fmt_label = FORMAT_LABELS.get(actual_format, actual_format)

    # Store draft in state
    update_state(
        status="draft_sent",
        current_draft=post_text,
        current_format=actual_format,
        current_carousel_data=carousel_data,
    )

    draft_msg = DRAFT_TEMPLATE.format(
        post_text=post_text,
        format_label=fmt_label,
    )
    await msg.reply_text(draft_msg)

    # If image format — take screenshots automatically and send them
    if actual_format == "image":
        await msg.reply_text("taking screenshots of the url...")
        try:
            screenshot_paths = await take_screenshots_for_story(story)
            if screenshot_paths:
                update_state(current_screenshot_paths=screenshot_paths)
                bot = Bot(token=TELEGRAM_BOT_TOKEN)
                for path in screenshot_paths:
                    with open(path, "rb") as f:
                        await bot.send_photo(
                            chat_id=msg.chat.id,
                            photo=f,
                            caption="screenshot captured automatically — attach this when posting on linkedin.",
                        )
            else:
                instruction = f"screenshot of {story.get('url', 'the tool')}"
                await msg.reply_text(IMAGE_INSTRUCTION.format(screenshot_instruction=instruction))
        except Exception as e:
            log.warning(f"Auto-screenshot failed: {e}")
            instruction = f"screenshot of {story.get('url', 'the tool')}"
            await msg.reply_text(IMAGE_INSTRUCTION.format(screenshot_instruction=instruction))


async def _regenerate_with_edit(msg, story: dict, format_type: str,
                                  original: str, edit_note: str, state: dict):
    try:
        result = generate_post_with_edit(original, edit_note, story, format_type)
    except Exception as e:
        log_error("Edit regeneration failed", e)
        await msg.reply_text(ERROR_GENERATE)
        return

    post_text = result.get("post_text", "")
    fmt_label = FORMAT_LABELS.get(format_type, format_type)

    update_state(
        status="draft_sent",
        current_draft=post_text,
    )

    await msg.reply_text(DRAFT_TEMPLATE.format(post_text=post_text, format_label=fmt_label))


# ─────────────────────────────────────────────────────────────────
# PUBLISHING
# ─────────────────────────────────────────────────────────────────

async def _publish(msg, state: dict, story: dict, format_type: str, post_text: str):
    update_state(status="publishing")
    await msg.reply_text(STATUS_POSTING)

    try:
        if format_type == "carousel":
            carousel_data = state.get("current_carousel_data")
            if not carousel_data:
                raise ValueError("No carousel data in state")

            pdf_path = generate_carousel_pdf(carousel_data)
            headline = carousel_data.get("slides", [{}])[0].get("heading", story.get("title", ""))
            url = post_carousel_to_linkedin(pdf_path, post_text, headline)
        elif format_type == "image":
            paths = state.get("current_screenshot_paths", [])
            if paths and os.path.exists(paths[0]):
                url = post_image_to_linkedin(paths[0], post_text)
            else:
                log.warning("No screenshot found for image post, falling back to text post")
                url = post_text_to_linkedin(post_text)
        else:
            url = post_text_to_linkedin(post_text)

    except Exception as e:
        log_error("LinkedIn publish failed", e)
        await msg.reply_text(ERROR_POST.format(error=str(e)))
        update_state(status="draft_sent")
        return

    streak = get_streak() + 1
    log_post(
        story=story,
        format_type=format_type,
        post_text=post_text,
        your_angle=state.get("user_angle", ""),
        linkedin_url=url,
    )
    update_state(status="posted", linkedin_url=url)

    await msg.reply_text(POSTED_CONFIRM.format(url=url, streak=streak))


# ─────────────────────────────────────────────────────────────────
# STATUS + LOG + RESEARCH COMMANDS
# ─────────────────────────────────────────────────────────────────

async def _handle_research(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != TELEGRAM_CHAT_ID:
        return

    msg = update.message
    query = msg.text.replace("/research", "", 1).strip()
    if not query:
        await msg.reply_text("Please provide a topic. Example:\n/research Apple intelligence. I think they are playing it too safe.")
        return

    await msg.reply_text(f"researching: '{query}'...")
    
    # Run the blocking research_topic call in a separate thread so the bot doesn't freeze
    story = await asyncio.to_thread(research_topic, query)
    
    update_state(
        status="processing",
        selected_story=story,
        user_angle=query,
        current_format="text",
    )
    
    await msg.reply_text(PROCESSING)
    await _generate_and_send_draft(msg, story, "text", query)


async def _handle_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != TELEGRAM_CHAT_ID:
        return
    state = read_state()
    status = state.get("status", "idle")
    streak = get_streak()

    status_map = {
        "idle": STATUS_IDLE,
        "waiting": STATUS_WAITING.format(sent_at=state.get("sent_at", "unknown")),
        "reminder_sent": STATUS_WAITING.format(sent_at=state.get("sent_at", "unknown")),
        "draft_sent": STATUS_DRAFT_SENT,
        "publishing": STATUS_POSTING,
        "posted": STATUS_POSTED.format(
            posted_at=state.get("updated_at", "today"),
            streak=streak,
        ),
        "skipped": STATUS_SKIPPED,
    }

    text = status_map.get(status, f"status: {status}")
    await update.message.reply_text(text)


async def _handle_log(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != TELEGRAM_CHAT_ID:
        return

    entries = get_recent_log(7)
    lines = [LOG_SUMMARY_HEADER.format(days=min(7, len(entries)))]

    for e in entries:
        date = e.get("date", "?")
        status = e.get("status", "?")
        if status == "posted":
            title = e.get("story_title", "")[:40]
            fmt = e.get("format", "text")
            lines.append(LOG_ENTRY_POSTED.format(
                date=date, format_type=fmt, title_excerpt=title
            ))
        else:
            lines.append(LOG_ENTRY_SKIPPED.format(date=date))

    await update.message.reply_text("\n".join(lines))


# ─────────────────────────────────────────────────────────────────
# PARSING
# ─────────────────────────────────────────────────────────────────

def _parse_pick(text: str) -> tuple[int, str | None] | None:
    """
    Parse story pick from user text.
    Formats: "2", "2 here's my take", "2, here's my take", "2. take"
    Returns (story_number, angle_text_or_None) or None if not a pick.
    """
    text = text.strip()
    # Match: digit optionally followed by separator and text
    match = re.match(r'^([123])[,.\s]?\s*(.*)?$', text, re.DOTALL)
    if not match:
        return None

    num = int(match.group(1))
    angle = match.group(2).strip() if match.group(2) else None
    return num, angle or None
