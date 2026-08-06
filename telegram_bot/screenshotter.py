"""
telegram_bot/screenshotter.py
Takes automated screenshots of URLs using Playwright (headless Chromium).
Uses a subprocess to isolate the Playwright event loop from python-telegram-bot's SelectorEventLoop on Windows.
"""

import os
import sys
import asyncio
import subprocess
from utils.logger import get_logger

log = get_logger("screenshotter")
SCREENSHOT_DIR = "carousel/output/screenshots"

async def take_screenshot(url: str, filename: str = None) -> str | None:
    """
    Take a full-page screenshot of the given URL using a subprocess to avoid Event Loop conflicts.
    Returns the path to the saved PNG, or None on failure.
    """
    os.makedirs(SCREENSHOT_DIR, exist_ok=True)
    if not filename:
        safe = url.replace("https://", "").replace("http://", "").replace("/", "_")[:60]
        filename = f"{safe}.png"

    out_path = os.path.abspath(os.path.join(SCREENSHOT_DIR, filename))

    try:
        script_path = os.path.abspath(__file__)
        def _run_subprocess():
            return subprocess.run(
                [sys.executable, script_path, url, out_path],
                capture_output=True,
                text=True,
                timeout=40.0
            )

        result = await asyncio.to_thread(_run_subprocess)

        if result.returncode == 0 and os.path.exists(out_path):
            log.info(f"Screenshot saved: {out_path}")
            return out_path
        else:
            log.warning(f"Screenshot failed for {url}. Return code: {result.returncode}, Stderr: {result.stderr}")
            return None
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
    path1 = await take_screenshot(url, filename="screenshot_1.png")
    if path1:
        paths.append(path1)

    return paths

if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit(1)

    url_arg = sys.argv[1]
    out_arg = sys.argv[2]

    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

    try:
        from playwright.async_api import async_playwright
    except ImportError:
        print("Playwright not installed — run: playwright install chromium", file=sys.stderr)
        sys.exit(1)

    async def _capture():
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
            await page.goto(url_arg, wait_until="domcontentloaded", timeout=25000)
            await page.wait_for_timeout(2000)

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

            await page.screenshot(path=out_arg, full_page=False)
            await browser.close()

    try:
        asyncio.run(asyncio.wait_for(_capture(), timeout=35.0))
    except Exception as e:
        print(f"Playwright error: {e}", file=sys.stderr)
        sys.exit(1)
