# test_database.py
from database import (
    get_dashboard_stats,
    get_all_genuine_complaints,
    get_db
)

# Test 1: raw connection
print("Testing raw connection...")
with get_db() as (conn, cur):
    cur.execute("SELECT NOW()")
    print(f"  DB time: {cur.fetchone()['now']}")

# Test 2: stats query on empty tables
print("\nTesting stats query...")
stats = get_dashboard_stats()
print(f"  Stats: {stats}")

# Test 3: genuine complaints on empty tables
print("\nTesting reports query...")
reports = get_all_genuine_complaints()
print(f"  Reports: {len(reports)} (expected 0 — tables are empty)")

print("\nshared/database.py ready.")