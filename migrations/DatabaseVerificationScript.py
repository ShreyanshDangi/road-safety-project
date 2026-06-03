# verify_setup.py
import os
from dotenv import load_dotenv
load_dotenv()

print("─" * 40)
print("Checking environment variables...")
print("─" * 40)

DATABASE_URL          = os.getenv("DATABASE_URL")
CLOUDINARY_CLOUD_NAME = os.getenv("CLOUDINARY_CLOUD_NAME")
CLOUDINARY_API_KEY    = os.getenv("CLOUDINARY_API_KEY")
CLOUDINARY_API_SECRET = os.getenv("CLOUDINARY_API_SECRET")

assert DATABASE_URL,          "DATABASE_URL missing from .env"
assert CLOUDINARY_CLOUD_NAME, "CLOUDINARY_CLOUD_NAME missing from .env"
assert CLOUDINARY_API_KEY,    "CLOUDINARY_API_KEY missing from .env"
assert CLOUDINARY_API_SECRET, "CLOUDINARY_API_SECRET missing from .env"

print("All environment variables present")

# ── Test PostgreSQL connection ─────────────────────────────────────────────
print("\nTesting PostgreSQL connection...")
import psycopg2
conn = psycopg2.connect(DATABASE_URL)
cur  = conn.cursor()

cur.execute("""
    SELECT table_name
    FROM information_schema.tables
    WHERE table_schema = 'public'
    ORDER BY table_name
""")
tables = [row[0] for row in cur.fetchall()]

expected = {"complaints", "detections", "duplicate_checks", "repairs", "routing"}
missing  = expected - set(tables)

if missing:
    print(f"Missing tables: {missing}")
    print("Re-run init_schema.sql in Supabase SQL editor")
else:
    print(f"All 5 tables confirmed: {sorted(tables)}")

cur.close()
conn.close()

# ── Test Cloudinary connection ─────────────────────────────────────────────
print("\nTesting Cloudinary connection...")
import cloudinary
import cloudinary.api

cloudinary.config(
    cloud_name = CLOUDINARY_CLOUD_NAME,
    api_key    = CLOUDINARY_API_KEY,
    api_secret = CLOUDINARY_API_SECRET,
)

result = cloudinary.api.ping()
assert result.get("status") == "ok", "Cloudinary ping failed"
print("Cloudinary connection confirmed")

print("\n" + "─" * 40)
print("Step 1 complete. Infrastructure ready.")
print("─" * 40)