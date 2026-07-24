"""
scripts/refresh_linkedin_token.py
Refresh your LinkedIn access token before it expires (60-day limit).
Run this when you receive the expiry warning.

Usage:
    python scripts/refresh_linkedin_token.py
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

# Re-use the same flow as initial setup
from scripts.get_linkedin_token import main

if __name__ == "__main__":
    print("\n─────────────────────────────────────────")
    print("LinkedIn Autopilot — Token Refresh")
    print("─────────────────────────────────────────")
    main()
