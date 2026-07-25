"""
scripts/test_pipeline_dry_run.py
Dry-run the pipeline without actually posting to LinkedIn or Telegram.
Useful for verifying scraping and scoring are working.

Usage:
    python scripts/test_pipeline_dry_run.py
"""

import os
import sys
import json
import codecs

if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from scraper.scraper import scrape_all
from scorer.scorer import rank_and_pick
from generator.generator import generate_morning_brief


def main():
    print("\n-----------------------------------------")
    print("LinkedIn Autopilot - Pipeline Dry Run")
    print("-----------------------------------------\n")

    print("Step 1: Scraping...")
    stories = scrape_all()
    print(f"  -> {len(stories)} unique stories found\n")

    if not stories:
        print("No stories found. Check internet connection and logs.")
        return

    print("Step 2: Scoring and ranking...")
    picks = rank_and_pick(stories)
    print(f"  -> Top {len(picks)} picks:\n")

    for i, story in enumerate(picks, 1):
        print(f"  {i}. [{story.get('source', '?')}] {story['title'][:70]}")
        print(f"     Score: {story.get('final_score', 0):.1f} | Age: {story.get('age_hours', 0):.1f}h")
        print(f"     Format: {story.get('format_suggestion', 'text')} | Region: {story.get('region', 'global')}")
        print(f"     URL: {story.get('url', '')[:80]}")
        print()

    print("\nStep 3: Generating morning brief...")
    brief = generate_morning_brief(picks)
    print("\n" + "="*50)
    print(brief)
    print("="*50)

    print(f"\n+ Dry run complete. {len(stories)} stories -> {len(picks)} picks.")
    print("Run main.py to start the full pipeline with Telegram and LinkedIn.\n")


if __name__ == "__main__":
    main()
