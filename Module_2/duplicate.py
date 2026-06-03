"""
duplicate.py — Core Duplicate Detection Logic
Combines pHash (visual) + GPS (location) to detect duplicate reports.
Both signals must fire for a duplicate flag.

Changes vs original:
  • severity parameter removed entirely
  • damage_type  → damage_class
  • image_path   → image_url  (Cloudinary URL)
  • DB calls route through shared.database instead of db
"""

from phash import compute_phash, are_images_similar, similarity_percentage
from gps_cluster import are_gps_within_radius
from shared.database import fetch_genuine_reports, insert_report


def check_and_store_report(complaint_id: str, image_url: str, latitude: float,
                            longitude: float, damage_class: str = "unknown"):
    """
    Main entry point called by routes.py.
    Returns a result dict with duplicate verdict + per-comparison audit trail.

    Parameters
    ----------
    image_url    : Cloudinary (or any public) URL for the uploaded image.
    latitude     : GPS latitude of the report.
    longitude    : GPS longitude of the report.
    damage_class : Damage classification label from Module 1.
    """
    new_hash = compute_phash(image_url)
    existing_reports = fetch_genuine_reports()
    
    # ── DEBUG — remove after fixing ───────────────────────────────────────────
    print(f"\n[DEBUG] New pHash: {new_hash}")
    print(f"[DEBUG] Existing reports found: {len(existing_reports)}")
    for r in existing_reports:
        _, hamming = are_images_similar(new_hash, r["phash"])
        _, gps_dist = are_gps_within_radius(latitude, longitude, r["latitude"], r["longitude"])
        print(f"  Report {r['id']}: phash={r['phash']} hamming={hamming} gps_dist={gps_dist}m")
    # ─────────────────────────────────────────────────────────────────────────

    audit_trail = []

    for report in existing_reports:
        report_id     = report["id"]
        existing_hash = report["phash"]
        ex_lat        = report["latitude"]
        ex_lng        = report["longitude"]

        hash_similar, hamming_dist = are_images_similar(new_hash, existing_hash)
        gps_close, gps_dist_m     = are_gps_within_radius(latitude, longitude, ex_lat, ex_lng)

        audit_trail.append({
            "compared_with_report_id": report_id,
            "hamming_distance":        hamming_dist,
            "similarity_pct":          similarity_percentage(hamming_dist),
            "gps_distance_m":          gps_dist_m,
            "hash_similar":            hash_similar,
            "gps_close":               gps_close,
            "flagged_as_duplicate":    hash_similar and gps_close,
        })

        if hash_similar and gps_close:
            new_id = insert_report(
                complaint_id = complaint_id,    
                image_url    = image_url,
                phash        = new_hash,
                latitude     = latitude,
                longitude    = longitude,
                damage_class = damage_class,
                is_duplicate = True,
                duplicate_of = report_id,
                hamming_dist = hamming_dist,
                gps_dist_m   = gps_dist_m,
            )
            return {
                "status":           "duplicate",
                "new_report_id":    new_id,
                "duplicate_of":     report_id,
                "hamming_distance": hamming_dist,
                "similarity_pct":   similarity_percentage(hamming_dist),
                "gps_distance_m":   gps_dist_m,
                "phash":            new_hash,
                "message": (
                    f"Duplicate of report #{report_id}. "
                    f"Images are {similarity_percentage(hamming_dist)}% similar, "
                    f"located {gps_dist_m}m apart."
                ),
                "checks": audit_trail,
            }

    new_id = insert_report(
    complaint_id = complaint_id,    
    image_url    = image_url,
    phash        = new_hash,
    latitude     = latitude,
    longitude    = longitude,
    damage_class = damage_class,
    is_duplicate = False,
    )
    return {
        "status":           "genuine",
        "new_report_id":    new_id,
        "duplicate_of":     None,
        "hamming_distance": None,
        "similarity_pct":   None,
        "gps_distance_m":   None,
        "phash":            new_hash,
        "message":          f"New unique report registered with ID #{new_id}.",
        "checks":           audit_trail,
    }
