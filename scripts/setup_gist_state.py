"""
scripts/setup_gist_state.py
One-time setup: creates the GitHub Gist that stores today's state
across GitHub Actions runs.

Run this ONCE locally before deploying:
    python scripts/setup_gist_state.py

It will print the GIST_ID you need to add to your repo secrets.

Requirements:
    - GIST_TOKEN env var: a GitHub Personal Access Token with `gist` scope.
      Create one at: https://github.com/settings/tokens/new
      (Select only the 'gist' scope — no other permissions needed)
"""

import json
import os
import sys

import requests


def main():
    token = os.getenv("GIST_TOKEN", "").strip()
    if not token:
        print("ERROR: GIST_TOKEN env var is not set.")
        print()
        print("Create a PAT at: https://github.com/settings/tokens/new")
        print("  - Select ONLY the 'gist' scope")
        print("  - Copy the token, then run:")
        print()
        print("  $env:GIST_TOKEN='ghp_your_token_here'")
        print("  python scripts/setup_gist_state.py")
        sys.exit(1)

    initial_state = {
        "date": None,
        "picks": [],
        "status": "idle",
        "sent_at": None,
        "selected_story": None,
        "user_angle": None,
        "current_draft": None,
        "current_format": None,
        "current_carousel_data": None,
        "linkedin_url": None,
    }

    payload = {
        "description": "LinkedIn Autopilot — daily state (managed by GitHub Actions)",
        "public": False,   # private gist — not visible to anyone but you
        "files": {
            "linkedin_autopilot_state.json": {
                "content": json.dumps(initial_state, indent=2)
            }
        }
    }

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    print("Creating private Gist...")
    resp = requests.post("https://api.github.com/gists", json=payload, headers=headers, timeout=10)

    if resp.status_code != 201:
        print(f"ERROR: GitHub API returned {resp.status_code}")
        print(resp.text)
        sys.exit(1)

    gist = resp.json()
    gist_id = gist["id"]
    gist_url = gist["html_url"]

    print()
    print("=" * 60)
    print("✅  Gist created successfully!")
    print("=" * 60)
    print()
    print(f"  Gist URL : {gist_url}")
    print(f"  GIST_ID  : {gist_id}")
    print()
    print("Next steps — add these two secrets to your GitHub repo:")
    print("  Repo → Settings → Secrets and variables → Actions → New secret")
    print()
    print(f"  Name: GIST_TOKEN   Value: {token[:8]}... (your PAT)")
    print(f"  Name: GIST_ID      Value: {gist_id}")
    print()
    print("Also add all other secrets listed in .github/workflows/morning-pipeline.yml")
    print("(TELEGRAM_BOT_TOKEN, GROQ_API_KEY, LINKEDIN_ACCESS_TOKEN, etc.)")


if __name__ == "__main__":
    main()
