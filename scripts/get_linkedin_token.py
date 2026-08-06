"""
scripts/get_linkedin_token.py
One-time OAuth flow to get your LinkedIn access token.
Run this once to set up, then again every 60 days to refresh.

Usage:
    python scripts/get_linkedin_token.py
"""

import os
import sys
import codecs

if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv, set_key
load_dotenv()

from linkedin.auth import get_access_token, get_person_urn
from linkedin.poster import record_token_date

ENV_FILE = ".env"

def main():
    print("\n─────────────────────────────────────────")
    print("LinkedIn Autopilot — Token Setup")
    print("─────────────────────────────────────────")
    print("\nYou need your LinkedIn app credentials.")
    print("Create an app at: https://www.linkedin.com/developers/apps")
    print("Add products: 'Share on LinkedIn' + 'Sign In with LinkedIn'\n")

    client_id = os.getenv("LINKEDIN_CLIENT_ID") or input("Enter your LinkedIn Client ID: ").strip()
    client_secret = os.getenv("LINKEDIN_CLIENT_SECRET") or input("Enter your LinkedIn Client Secret: ").strip()

    print("\nStarting OAuth flow...")
    try:
        token_data = get_access_token(client_id, client_secret)
        token = token_data.get("access_token")
        refresh_token = token_data.get("refresh_token")
        urn = get_person_urn(token)

        print(f"\n✓ Access token: {token[:20]}...")
        print(f"✓ Person URN: {urn}")

        # Write to .env
        if not os.path.exists(ENV_FILE):
            with open(ENV_FILE, "w") as f:
                f.write("")

        set_key(ENV_FILE, "LINKEDIN_ACCESS_TOKEN", token)
        if refresh_token:
            set_key(ENV_FILE, "LINKEDIN_REFRESH_TOKEN", refresh_token)
            print("✓ Refresh token saved")
        set_key(ENV_FILE, "LINKEDIN_PERSON_URN", urn)

        # Record token date for expiry tracking
        record_token_date()

        print(f"\n✓ Saved to {ENV_FILE}")
        print("✓ Token date recorded (will warn you at 55 days)")
        print("\nSetup complete. Run main.py to start the pipeline.")

    except Exception as e:
        print(f"\n✗ Failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
