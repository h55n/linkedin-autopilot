import os
import time
import subprocess
import pyautogui

def complete_oauth():
    print("Starting token script in background...")
    # Start the token script which spins up the server and opens the browser
    import sys
    proc = subprocess.Popen([sys.executable, '-u', 'scripts/get_linkedin_token.py'])
    
    print("Waiting 10 seconds for browser to open and load...")
    time.sleep(10)
    
    # In Windows, opening a URL usually brings the default browser to the foreground.
    # Take a screenshot before attempting interaction
    screenshot_path = r'C:\Users\hassa\.gemini\antigravity-ide\brain\dd01a5fc-6e1e-4f39-b210-71c3257c0ab5\host_screen_before_click.png'
    pyautogui.screenshot(screenshot_path)
    print(f"Saved pre-click screenshot to {screenshot_path}")
    
    # Try clicking. The LinkedIn OAuth screen usually has "Allow" in focus or 1-2 tabs away.
    # On most setups, we can just press Tab twice and Enter.
    print("Pressing Tab twice and Enter...")
    pyautogui.press('tab', presses=3, interval=0.2)
    pyautogui.press('enter')
    
    print("Waiting 5 seconds for redirect...")
    time.sleep(5)
    
    screenshot_path2 = r'C:\Users\hassa\.gemini\antigravity-ide\brain\dd01a5fc-6e1e-4f39-b210-71c3257c0ab5\host_screen_after_click.png'
    pyautogui.screenshot(screenshot_path2)
    print(f"Saved post-click screenshot to {screenshot_path2}")
    
    # Wait for the process to finish
    try:
        proc.wait(timeout=10)
        print(f"Token script completed with exit code {proc.returncode}")
    except subprocess.TimeoutExpired:
        print("Token script didn't finish. Clicking didn't work.")
        proc.terminate()

if __name__ == '__main__':
    complete_oauth()
