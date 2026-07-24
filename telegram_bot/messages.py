"""
telegram_bot/messages.py
All Telegram message templates as constants.
No string formatting logic here — just raw templates.
"""

REMINDER = """\
hey, still waiting on today's pick.
which story are you going with? (reply 1, 2, or 3 + your take)
or reply 'skip' to skip today.\
"""

SKIP_CONFIRM = """\
ok, skipping today. see you tomorrow at 7.
current streak: {streak} days\
"""

PROCESSING = "got it, generating your post..."

TRANSCRIBING = "transcribing voice note..."

DRAFT_TEMPLATE = """\
────────────────────────────
here's your post:

{post_text}

format: {format_label}
────────────────────────────
reply 'post' to publish
reply 'edit [what to change]' to tweak
reply 'carousel' / 'image' / 'text' to switch format
reply 'cancel' to drop it\
"""

POSTED_CONFIRM = """\
✓ posted.
{url}

streak: {streak} days in a row 🔥\
"""

CANCELLED = "cancelled. see you tomorrow at 7."

IMAGE_INSTRUCTION = """\
for this post, grab a screenshot of:
{screenshot_instruction}

attach both images when posting on linkedin.
or reply 'text' to switch to a text post instead.\
"""

TOKEN_EXPIRY_WARNING = """\
⚠️ linkedin token warning
your token is {days_old} days old and expires in {days_left} days.
run: python scripts/refresh_linkedin_token.py to refresh.\
"""

STATUS_IDLE = "no pipeline running. next brief at 7 AM IST."

STATUS_WAITING = "brief sent at {sent_at}. waiting for your pick."

STATUS_DRAFT_SENT = "draft sent. waiting for 'post', 'edit', or 'cancel'."

STATUS_POSTING = "publishing to linkedin..."

STATUS_POSTED = "posted today at {posted_at}. streak: {streak} days."

STATUS_SKIPPED = "skipped today. see you tomorrow."

ERROR_VOICE = """\
couldn't transcribe the voice note. please resend as text.\
"""

ERROR_GENERATE = """\
generation failed. want to try again? reply with your pick again.\
"""

ERROR_POST = """\
linkedin post failed: {error}
check logs/errors.log for details.\
"""

LOG_SUMMARY_HEADER = "last {days} days:\n" + "─" * 30

LOG_ENTRY_POSTED = "{date} ✓ {format_type}: {title_excerpt}"
LOG_ENTRY_SKIPPED = "{date} — skipped"
LOG_ENTRY_CANCELLED = "{date} ✗ cancelled"

FORMAT_LABELS = {
    "text": "text post",
    "carousel": "carousel (pdf)",
    "image": "image pair",
}
