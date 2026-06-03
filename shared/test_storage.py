# shared/test_storage.py

from pathlib import Path
from dotenv import load_dotenv
load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")

from storage import upload_image, fetch_image_bytes, delete_image

TEST_IMAGE = Path(__file__).parent.parent / "test_image2.jpg"

# ── Test 1: upload ────────────────────────────────────────────────────────────
print("Test 1 — upload to complaints folder...")
with open(TEST_IMAGE, "rb") as f:
    image_bytes = f.read()

url = upload_image(image_bytes, folder="complaints")
print(f"  URL: {url}")
assert url.startswith("https://"), "Expected HTTPS URL"
assert "cloudinary" in url,        "Expected Cloudinary domain"
print("  PASSED")

# ── Test 2: fetch back ────────────────────────────────────────────────────────
print("\nTest 2 — fetch bytes back from URL...")
fetched = fetch_image_bytes(url)
assert len(fetched) > 0,              "Expected non-empty bytes"
assert len(fetched) == len(image_bytes) or len(fetched) > 1000, "Fetched bytes look wrong"
print(f"  Fetched {len(fetched):,} bytes")
print("  PASSED")

# ── Test 3: upload to repairs folder ─────────────────────────────────────────
print("\nTest 3 — upload to repairs folder...")
with open(TEST_IMAGE, "rb") as f:
    repair_url = upload_image(f.read(), folder="repairs")

assert "repairs" in repair_url, "Expected repairs folder in URL"
print(f"  URL: {repair_url}")
print("  PASSED")

# ── Test 4: delete ────────────────────────────────────────────────────────────
print("\nTest 4 — delete test images from Cloudinary...")
delete_image(url)
delete_image(repair_url)
print("  Deleted both test uploads")
print("  PASSED")

print("\nshared/storage.py ready.")