"""
scripts/get_linkedin_urn.py
Fetch your LinkedIn Person URN using an existing access token.
Run this if you already have a token but forgot to save your URN.

Usage:
    python scripts/get_linkedin_urn.py
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv, set_key
load_dotenv()

from linkedin.auth import get_person_urn

def main():
    token = os.getenv("LINKEDIN_ACCESS_TOKEN", "")
    if not token:
        print("No LINKEDIN_ACCESS_TOKEN in .env — run get_linkedin_token.py first")
        sys.exit(1)

    try:
        urn = get_person_urn(token)
        print(f"Your URN: {urn}")
        set_key(".env", "LINKEDIN_PERSON_URN", urn)
        print("Saved to .env")
    except Exception as e:
        print(f"Failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
