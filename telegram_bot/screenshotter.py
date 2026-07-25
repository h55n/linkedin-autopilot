"""
telegram_bot/screenshotter.py
Takes automated screenshots of URLs using Playwright (headless Chromium).
Used for image pair posts — captures before/after, or tool homepage + a key feature view.
Falls back gracefully if Playwright is not installed.
"""

import os
import asyncio
from utils.logger import get_logger

log = get_logger("screenshotter")

SCREENSHOT_DIR = "carousel/output/screenshots"


async def take_screenshot(url: str, filename: str = None) -> str | None:
    """
    Take a full-page screenshot of the given URL.
    Returns the path to the saved PNG, or None on failure.
    """
    os.makedirs(SCREENSHOT_DIR, exist_ok=True)
    if not filename:
        safe = url.replace("https://", "").replace("http://", "").replace("/", "_")[:60]
        filename = f"{safe}.png"

    out_path = os.path.join(SCREENSHOT_DIR, filename)

    try:
        from playwright.async_api import async_playwright
    except ImportError:
        log.warning("Playwright not installed — run: playwright install chromium")
        return None

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                viewport={"width": 1280, "height": 800},
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
            )
            page = await context.new_page()

            # Navigate and wait for content to settle
            await page.goto(url, wait_until="networkidle", timeout=20000)
            await page.wait_for_timeout(2000)

            # Dismiss cookie banners / modals if present
            for selector in [
                "[class*='cookie'] button",
                "[id*='cookie'] button",
                "[class*='modal'] button[class*='close']",
                "[class*='banner'] button",
            ]:
                try:
                    btn = page.locator(selector).first
                    if await btn.is_visible(timeout=500):
                        await btn.click()
                        await page.wait_for_timeout(500)
                except Exception:
                    pass

            await page.screenshot(path=out_path, full_page=False)
            await browser.close()

        log.info(f"Screenshot saved: {out_path}")
        return out_path

    except Exception as e:
        log.warning(f"Screenshot failed for {url}: {e}")
        return None


async def take_screenshots_for_story(story: dict) -> list[str]:
    """
    Take 1-2 screenshots for a story.
    Returns a list of local PNG paths (may be empty if screenshots fail).
    """
    url = story.get("url", "")
    if not url:
        return []

    paths = []

    # Primary: homepage / article screenshot
    path1 = await take_screenshot(url, filename="screenshot_1.png")
    if path1:
        paths.append(path1)

    return paths
