#!/usr/bin/env python3
"""
Test script to verify the arXiv OAI-PMH scraper works correctly.
Run this before starting a full overnight sync.
"""

import asyncio
import sys
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, '.')

from arxiv_collector import ArxivCollector, CATEGORY_TO_SETSPEC, MAX_RETRIES, RATE_LIMIT_DELAY


async def test_oai_pmh_connection():
    """Test basic OAI-PMH connectivity."""
    print("=" * 60)
    print("TEST 1: OAI-PMH Connection Test")
    print("=" * 60)

    collector = ArxivCollector()

    # Test with a simple ListIdentifiers request
    params = {
        "verb": "ListIdentifiers",
        "metadataPrefix": "oai_dc",
        "set": "cs",
        "from": "2024-01-01",
        "until": "2024-01-02",  # Just 2 days
    }

    print(f"Fetching CS papers from 2024-01-01 to 2024-01-02...")

    root, token = await collector.fetch_oai_page(params)
    await collector.close()

    if root is not None:
        # Count records
        count = len(root.findall(".//{http://www.openarchives.org/OAI/2.0/}header"))
        print(f"SUCCESS: Found {count} records")
        return True
    else:
        print("FAILED: Could not connect to OAI-PMH")
        return False


async def test_category_counting():
    """Test counting papers for a specific category."""
    print("\n" + "=" * 60)
    print("TEST 2: Category Counting Test")
    print("=" * 60)

    collector = ArxivCollector()

    # Test counting for cs.AI in January 2024
    print("Counting cs.AI papers for January 2024...")

    counts = await collector.count_papers_by_category_for_month(2024, 1, "cs")
    await collector.close()

    # Find cs.AI count
    cs_ai_setspec = CATEGORY_TO_SETSPEC["cs.AI"]
    cs_ai_count = counts.get(cs_ai_setspec, 0)

    print(f"Results for CS parent set:")
    ai_related = {k: v for k, v in counts.items() if "AI" in k or "LG" in k or "CV" in k}
    for spec, count in sorted(ai_related.items()):
        print(f"  {spec}: {count}")

    if cs_ai_count > 0:
        print(f"\nSUCCESS: cs.AI has {cs_ai_count} papers")
        return True
    else:
        print(f"\nWARNING: cs.AI count is 0 (might need different date range)")
        return len(counts) > 0  # At least some data was found


async def test_batch_month_fetch():
    """Test fetching all categories for a month."""
    print("\n" + "=" * 60)
    print("TEST 3: Batch Month Fetch Test")
    print("=" * 60)

    collector = ArxivCollector()

    print("Fetching all categories for January 2024...")
    print("(This tests the main sync logic)")

    counts = await collector.sync_month_batch(2024, 1)
    await collector.close()

    print(f"\nResults ({len(counts)} categories with data):")
    for cat_id, count in sorted(counts.items()):
        if count > 0:
            print(f"  {cat_id}: {count}")

    if len(counts) > 0:
        total = sum(counts.values())
        print(f"\nSUCCESS: Total papers across all categories: {total}")
        return True
    else:
        print("\nFAILED: No data retrieved")
        return False


async def test_configuration():
    """Test that configuration is reasonable."""
    print("\n" + "=" * 60)
    print("TEST 4: Configuration Check")
    print("=" * 60)

    print(f"Max retries: {MAX_RETRIES}")
    print(f"Rate limit delay: {RATE_LIMIT_DELAY}s")
    print(f"Categories mapped: {len(CATEGORY_TO_SETSPEC)}")

    # Verify all categories have mappings
    from database import ARXIV_CATEGORIES
    all_cats = []
    for parent_data in ARXIV_CATEGORIES.values():
        for sub_id in parent_data["subcategories"].keys():
            all_cats.append(sub_id)

    missing = [c for c in all_cats if c not in CATEGORY_TO_SETSPEC]
    if missing:
        print(f"WARNING: Missing category mappings: {missing}")
        return False

    print(f"All {len(all_cats)} categories have OAI-PMH mappings")
    return True


async def estimate_full_sync_time():
    """Estimate how long a full sync will take."""
    print("\n" + "=" * 60)
    print("FULL SYNC TIME ESTIMATE")
    print("=" * 60)

    # Calculate months from 2022 to now
    now = datetime.now()
    start_year = 2022
    months = 0
    for year in range(start_year, now.year + 1):
        if year == now.year:
            months += now.month
        else:
            months += 12

    # For OAI-PMH approach:
    # - We fetch 7 parent sets per month
    # - Each fetch can have multiple pages (pagination)
    # - Rate limit is 3s between requests

    parent_sets = 7
    avg_pages_per_set = 3  # Estimate - depends on data volume
    time_per_request = RATE_LIMIT_DELAY + 2  # Request + rate limit

    total_requests = months * parent_sets * avg_pages_per_set
    total_seconds = total_requests * time_per_request
    total_hours = total_seconds / 3600

    print(f"Months to sync: {months} (from {start_year} to now)")
    print(f"Parent sets per month: {parent_sets}")
    print(f"Estimated pages per set: ~{avg_pages_per_set}")
    print(f"Time per request: ~{time_per_request}s")
    print(f"")
    print(f"Estimated requests: ~{total_requests}")
    print(f"Estimated time: ~{total_hours:.1f} hours")
    print(f"")
    print("Note: Actual time may vary based on data volume and pagination")

    return True


async def main():
    print("arXiv OAI-PMH Scraper Test Suite")
    print(f"Started at: {datetime.now().isoformat()}")
    print("")

    tests = [
        ("OAI-PMH Connection", test_oai_pmh_connection),
        ("Category Counting", test_category_counting),
        ("Batch Month Fetch", test_batch_month_fetch),
        ("Configuration", test_configuration),
        ("Time Estimate", estimate_full_sync_time),
    ]

    results = []
    for name, test_func in tests:
        try:
            result = await test_func()
            results.append((name, result))
        except Exception as e:
            print(f"ERROR in {name}: {e}")
            import traceback
            traceback.print_exc()
            results.append((name, False))

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    all_passed = True
    for name, passed in results:
        status = "PASS" if passed else "FAIL"
        print(f"  {name}: {status}")
        if not passed:
            all_passed = False

    print("")
    if all_passed:
        print("All tests passed! Safe to run full sync.")
        print("")
        print("To start overnight sync:")
        print("  1. cd backend")
        print("  2. source venv/bin/activate")
        print("  3. nohup uvicorn main:app --host 0.0.0.0 --port 8000 > server.log 2>&1 &")
        print("  4. curl -X POST 'http://localhost:8000/api/sync?full=true'")
        print("  5. Monitor: tail -f logs/sync_*.log")
        return 0
    else:
        print("Some tests failed. Check the output above.")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
