"""
scripts/scratch/test_m3_stress.py
Empirical stress testing script for Milestone 3 optimizations.
"""

import sys
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests

from utils.helpers import get_http_session
from scraper.deduplicator import deduplicate
from scraper.scraper import scrape_all
import utils.helpers as helpers

def test_session_thread_safety_and_pooling():
    print("--- Test 1: get_http_session() Race Condition & Thread Pooling ---")
    
    # 1. Test initialization race condition across 50 threads
    helpers._HTTP_SESSION = None # Reset
    sessions = [None] * 50
    barrier = threading.Barrier(50)

    def worker(idx):
        barrier.wait()
        sessions[idx] = get_http_session()

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(50)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    unique_sessions = set(id(s) for s in sessions)
    print(f"Concurrent initialization from 50 threads produced {len(unique_sessions)} distinct Session object(s).")
    race_condition_detected = len(unique_sessions) > 1
    if race_condition_detected:
        print("  WARNING: Race condition detected in get_http_session() initial allocation!")
    else:
        print("  PASS: Single session instance returned despite simultaneous initial calls.")

    # 2. Test actual HTTP connection pooling under thread concurrency
    session = get_http_session()
    # Check adapters on session
    http_adapter = session.adapters.get("http://")
    https_adapter = session.adapters.get("https://")
    print(f"  HTTP Adapter pool_connections: {getattr(http_adapter, '_pool_connections', None)}, pool_maxsize: {getattr(http_adapter, '_pool_maxsize', None)}")
    print(f"  HTTPS Adapter pool_connections: {getattr(https_adapter, '_pool_connections', None)}, pool_maxsize: {getattr(https_adapter, '_pool_maxsize', None)}")

    return race_condition_detected

def test_deduplicate_performance_and_accuracy():
    print("\n--- Test 2: deduplicate() Length Pre-filtering Stress & Accuracy ---")
    
    # Construct synthetic dataset with short titles vs long titles
    # Case A: Long title vs Short title (should be skipped by length pre-filtering)
    # Case B: Similar length, near duplicates (should be caught by fuzzy dedup)
    # Case C: Same title (should be caught)
    # Case D: High volume performance check (1,000 stories)

    short_titles = [f"AI App {i}" for i in range(100)] # len ~ 8
    long_titles = [f"This is a very detailed and expansive announcement about artificial intelligence startup version {i} launching next week with full features" for i in range(100)] # len ~ 140

    stories = []
    # Mix long and short stories
    for i in range(100):
        stories.append({"title": short_titles[i], "url": f"https://example.com/short/{i}"})
        stories.append({"title": long_titles[i], "url": f"https://example.com/long/{i}"})

    # Add near duplicates
    stories.append({"title": "Show HN: Fast AI Scraper Tool in Python", "url": "https://example.com/hn/1"})
    stories.append({"title": "Show HN: Fast AI Scraper Tooling in Python!", "url": "https://example.com/hn/2"}) # near dup

    # Measure execution time
    t0 = time.perf_counter()
    deduped = deduplicate(stories)
    t1 = time.perf_counter()

    print(f"Processed {len(stories)} stories into {len(deduped)} unique stories in {(t1-t0)*1000:.3f} ms.")

    # Verify near duplicate was eliminated
    titles_out = [s["title"] for s in deduped]
    has_dup = "Show HN: Fast AI Scraper Tooling in Python!" in titles_out and "Show HN: Fast AI Scraper Tool in Python" in titles_out
    print(f"Near-duplicate check: {'FAILED (duplicate survived)' if has_dup else 'PASSED (duplicate removed)'}")

    # Stress test scaling with 2,000 items
    large_dataset = []
    for i in range(1000):
        large_dataset.append({"title": f"Short Title {i}", "url": f"https://test.org/s/{i}"})
        large_dataset.append({"title": f"Extremely Long Title Designed To Test String Length Pre-Filtering Efficiency In Deduplication Module Number {i}", "url": f"https://test.org/l/{i}"})
    
    t0 = time.perf_counter()
    large_deduped = deduplicate(large_dataset)
    t1 = time.perf_counter()
    print(f"Large dataset (2,000 items) dedup time: {(t1-t0)*1000:.2f} ms (Yielded {len(large_deduped)} items).")

    # Boundary check: Edge case where titles differ by close to 50% length
    # max_len > 0 and (abs(len_title - len_seen) / max_len) > 0.50
    # What if two titles are near-duplicates in meaning/words but one has extra trailing words that make length diff 51%?
    # E.g. "GPT-4 Release" (13 chars) vs "GPT-4 Release: OpenAI launches GPT-4 today" (42 chars) -> (42-13)/42 = 69% > 50%.
    # Length pre-filter skips fuzzy check, even though one title is contained in the other.
    t_short = "GPT-4 Release"
    t_long = "GPT-4 Release: OpenAI launches GPT-4 today"
    stories_boundary = [
        {"title": t_short, "url": "https://a.com/1"},
        {"title": t_long, "url": "https://b.com/2"}
    ]
    res_b = deduplicate(stories_boundary)
    print(f"Boundary test (Sub-phrase with >50% length diff): {len(res_b)} items returned (Titles: {[s['title'] for s in res_b]}).")

def test_parallel_scraper_execution():
    print("\n--- Test 3: Parallel Scraper Execution in scrape_all() ---")
    
    # We can mock individual scraper functions with sleeping dummies to verify true parallel execution speed
    import scraper.scraper as scraper_module
    from unittest.mock import patch

    def dummy_scraper(name, delay, count):
        time.sleep(delay)
        return [{"title": f"{name} story {i}", "url": f"https://{name}.com/{i}"} for i in range(count)]

    with patch("scraper.scraper.scrape_hackernews", side_effect=lambda: dummy_scraper("hn", 0.5, 5)), \
         patch("scraper.scraper.scrape_reddit", side_effect=lambda: dummy_scraper("reddit", 0.5, 5)), \
         patch("scraper.scraper.scrape_rss_feeds", side_effect=lambda: dummy_scraper("rss", 0.5, 5)), \
         patch("scraper.scraper.scrape_producthunt", side_effect=lambda: dummy_scraper("ph", 0.5, 5)), \
         patch("scraper.scraper.scrape_github_trending", side_effect=lambda: dummy_scraper("gh", 0.5, 5)):
        
        t0 = time.perf_counter()
        results = scraper_module.scrape_all()
        t1 = time.perf_counter()
        elapsed = t1 - t0

        print(f"5 scrapers with 0.5s delay each finished in {elapsed:.3f}s total.")
        if elapsed < 0.9:
            print("  PASS: Scrapers executed in parallel (elapsed ~0.5s, well under sequential 2.5s).")
        else:
            print("  FAIL: Scrapers did not execute in parallel.")

        print(f"Total deduplicated stories returned: {len(results)}")

    # Test error isolation in parallel execution
    def failing_scraper():
        raise RuntimeError("Simulated scraper crash!")

    with patch("scraper.scraper.scrape_hackernews", side_effect=failing_scraper), \
         patch("scraper.scraper.scrape_reddit", side_effect=lambda: dummy_scraper("reddit", 0.1, 3)), \
         patch("scraper.scraper.scrape_rss_feeds", side_effect=lambda: dummy_scraper("rss", 0.1, 3)), \
         patch("scraper.scraper.scrape_producthunt", side_effect=lambda: dummy_scraper("ph", 0.1, 3)), \
         patch("scraper.scraper.scrape_github_trending", side_effect=lambda: dummy_scraper("gh", 0.1, 3)):
        
        results = scraper_module.scrape_all()
        print(f"Error isolation test: 1 failing scraper out of 5 yielded {len(results)} stories.")
        if len(results) == 12:
            print("  PASS: Failing scraper was isolated cleanly.")
        else:
            print("  FAIL: Failing scraper impacted other results.")

if __name__ == "__main__":
    race = test_session_thread_safety_and_pooling()
    test_deduplicate_performance_and_accuracy()
    test_parallel_scraper_execution()
