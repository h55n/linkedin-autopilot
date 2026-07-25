"""
scripts/test_send_all_formats.py
Sends a test post in all 3 formats to Telegram to verify the full pipeline.
Does NOT post to LinkedIn.

Usage:
    python scripts/test_send_all_formats.py
"""

import sys
import os
import asyncio

if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from telegram import Bot
from telegram.constants import ParseMode
from telegram.request import HTTPXRequest
from generator.generator import generate_post
from carousel.carousel_gen import generate_carousel_pdf, generate_carousel_pngs
from config.settings import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID


def _make_bot() -> Bot:
    """Create bot with generous timeouts for large file uploads."""
    return Bot(
        token=TELEGRAM_BOT_TOKEN,
        request=HTTPXRequest(read_timeout=60, write_timeout=60, connect_timeout=30),
    )

STORY = {
    "title": "NVIDIA launches NIM microservices for accelerated AI inference",
    "url": "https://developer.nvidia.com/nim",
    "source": "nvidia_blog",
    "summary": (
        "NVIDIA has launched NIM, a suite of microservices designed to accelerate "
        "the deployment of open-source AI models like Llama 3 across cloud, data "
        "center, and edge environments."
    ),
}
ANGLE = "focus on how this reduces deployment friction for indie devs and startups"


async def main():
    bot = _make_bot()
    chat = TELEGRAM_CHAT_ID

    # ── 1. TEXT POST ──────────────────────────────────────────────
    print("Generating text post...")
    res = generate_post(STORY, "text", ANGLE)
    await bot.send_message(
        chat_id=chat,
        text=f"📝 *TEST — TEXT POST*\n\n{res['post_text']}",
        parse_mode=ParseMode.MARKDOWN,
    )
    print("  [OK] Text post sent")

    # ── 2. IMAGE CAPTION POST ────────────────────────────────────
    print("Generating image caption post...")
    res = generate_post(STORY, "image", ANGLE)
    await bot.send_message(
        chat_id=chat,
        text=(
            f"🖼️ *TEST — IMAGE CAPTION*\n\n{res['post_text']}\n\n"
            f"_[Take a screenshot of {STORY['url']} to attach]_"
        ),
        parse_mode=ParseMode.MARKDOWN,
    )
    print("  [OK] Image caption sent")

    # ── 3. CAROUSEL POST ─────────────────────────────────────────
    print("Generating carousel post...")
    res = generate_post(STORY, "carousel", ANGLE)
    carousel_data = res.get("carousel_data")

    # Send the intro caption
    await bot.send_message(
        chat_id=chat,
        text=f"🎠 *TEST — CAROUSEL CAPTION*\n\n{res['post_text']}",
        parse_mode=ParseMode.MARKDOWN,
    )

    if carousel_data:
        # Render as individual PNG slides and send as a media group
        png_paths = generate_carousel_pngs(carousel_data)
        if png_paths:
            import time
            for i, path in enumerate(png_paths, 1):
                for attempt in range(3):
                    try:
                        with open(path, "rb") as f:
                            await bot.send_photo(
                                chat_id=chat,
                                photo=f,
                                caption=f"Slide {i}/{len(png_paths)}" if i == 1 else None,
                            )
                        await asyncio.sleep(1)  # rate-limit between slides
                        break
                    except Exception as e:
                        print(f"  Slide {i} attempt {attempt+1} failed: {e}")
                        await asyncio.sleep(3)
            print(f"  [OK] Carousel slides sent ({len(png_paths)} slides)")

        # Also generate the PDF (this is what gets posted to LinkedIn)
        pdf_path = generate_carousel_pdf(carousel_data)
        with open(pdf_path, "rb") as f:
            await bot.send_document(
                chat_id=chat,
                document=f,
                filename="carousel_linkedin.pdf",
                caption="📄 This PDF is what gets uploaded to LinkedIn.",
            )
        print("  [OK] Carousel PDF sent")

    print("\nDone! All 3 formats sent to Telegram.")


if __name__ == "__main__":
    asyncio.run(main())
