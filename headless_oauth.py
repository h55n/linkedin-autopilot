import asyncio
import os
import time
import subprocess
from playwright.async_api import async_playwright

async def run():
    print("Killing Chrome...")
    subprocess.run(["taskkill", "/F", "/IM", "chrome.exe"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(2)
    
    import sys
    print("Starting token script...")
    env = os.environ.copy()
    env["HEADLESS_OAUTH_MODE"] = "1"
    token_proc = subprocess.Popen([sys.executable, '-u', 'scripts/get_linkedin_token.py'], env=env)
    time.sleep(3)
    
    print("Starting Chrome with remote debugging...")
    chrome_path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
    user_data_dir = r"C:\Users\hassa\AppData\Local\Google\Chrome\User Data"
    
    chrome_proc = subprocess.Popen([
        chrome_path, 
        f"--user-data-dir={user_data_dir}", 
        "--remote-debugging-port=9222"
    ])
    
    time.sleep(5) # wait for Chrome to start
    
    auth_url = "https://www.linkedin.com/oauth/v2/authorization?response_type=code&client_id=86cfckbwl22ocm&redirect_uri=http%3A%2F%2Flocalhost%3A8080%2Fcallback&scope=openid+profile+w_member_social&state=linkedin_autopilot_auth"

    async with async_playwright() as p:
        print("Connecting Playwright over CDP...")
        try:
            browser = await p.chromium.connect_over_cdp("http://127.0.0.1:9222")
        except Exception as e:
            print(f"Failed to connect to Chrome: {e}")
            chrome_proc.terminate()
            token_proc.terminate()
            return
            
        context = browser.contexts[0]
        page = await context.new_page()
        
        print(f"Navigating to OAuth URL...")
        await page.goto(auth_url, wait_until="networkidle", timeout=30000)
        
        content = await page.content()
        if "Sign in" in content and "password" in content.lower():
            print("ERROR: User is not logged into LinkedIn in Chrome.")
            await browser.close()
            chrome_proc.terminate()
            token_proc.terminate()
            return
            
        print("Looking for 'Allow' button...")
        try:
            allow_btn = page.locator("button:has-text('Allow'), button:has-text('Accept'), button[type='submit']").first
            if await allow_btn.is_visible(timeout=5000):
                print("Clicking 'Allow'...")
                await allow_btn.click()
                print("Clicked. Waiting for redirect...")
                await page.wait_for_timeout(5000)
            else:
                print("No Allow button found.")
                await page.wait_for_timeout(2000)
        except Exception as e:
            print(f"Could not click Allow: {e}")
            
        print(f"Current URL after flow: {page.url}")
        
        await browser.close()
        
    print("Waiting for token script to finish...")
    try:
        token_proc.wait(timeout=10)
        print(f"Token script completed with exit code {token_proc.returncode}")
    except subprocess.TimeoutExpired:
        print("Token script didn't finish.")
        token_proc.terminate()
        
    chrome_proc.terminate()

if __name__ == "__main__":
    asyncio.run(run())
