# module0/gps_validator.py

import math
import logging

logger = logging.getLogger(__name__)

MISMATCH_THRESHOLD_METRES = 100   # beyond this → suspicious
EARTH_RADIUS_METRES       = 6_371_000


def _haversine_metres(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Straight-line surface distance between two GPS points in metres.
    Standard Haversine formula — accurate to within ~0.3% for short distances.
    """
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = math.sin(dlat / 2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2)**2
    c = 2 * math.asin(math.sqrt(a))

    return round(EARTH_RADIUS_METRES * c, 2)


def validate_gps(
    exif_lat:    float | None,
    exif_lon:    float | None,
    browser_lat: float | None,
    browser_lon: float | None,
) -> dict:
    """
    Resolves final GPS coordinates from EXIF and browser sources.

    Priority:
        1. Both present   → cross-validate, use EXIF if clean
        2. EXIF only      → use directly, high trust
        3. Browser only   → use, lower trust
        4. Neither        → reject

    Returns:
    {
        "final_lat":      float | None,
        "final_lon":      float | None,
        "gps_source":     "exif" | "browser" | "exif_flagged" | "none",
        "distance_metres": float | None,   # only when both sources present
        "mismatch_flag":  bool,
        "flag_reason":    str | None
    }
    """
    result = {
        "final_lat":       None,
        "final_lon":       None,
        "gps_source":      "none",
        "distance_metres": None,
        "mismatch_flag":   False,
        "flag_reason":     None,
    }

    exif_present    = exif_lat is not None and exif_lon is not None
    browser_present = browser_lat is not None and browser_lon is not None

    # ── Case 1: both sources present ─────────────────────────────────────────
    if exif_present and browser_present:
        distance = _haversine_metres(exif_lat, exif_lon, browser_lat, browser_lon)
        result["distance_metres"] = distance

        if distance <= MISMATCH_THRESHOLD_METRES:
            # Sources agree → EXIF is more precise, use it
            result["final_lat"]  = exif_lat
            result["final_lon"]  = exif_lon
            result["gps_source"] = "exif"
        else:
            # Sources disagree → flag, still use EXIF but mark it
            result["final_lat"]   = exif_lat
            result["final_lon"]   = exif_lon
            result["gps_source"]  = "exif_flagged"
            result["mismatch_flag"] = True
            result["flag_reason"] = (
                f"EXIF and browser GPS differ by {distance:.0f}m "
                f"(threshold: {MISMATCH_THRESHOLD_METRES}m)"
            )

    # ── Case 2: EXIF only ────────────────────────────────────────────────────
    elif exif_present:
        result["final_lat"]  = exif_lat
        result["final_lon"]  = exif_lon
        result["gps_source"] = "exif"

    # ── Case 3: browser only ─────────────────────────────────────────────────
    elif browser_present:
        result["final_lat"]  = browser_lat
        result["final_lon"]  = browser_lon
        result["gps_source"] = "browser"
        result["flag_reason"] = "No EXIF GPS — using browser GPS, lower trust"

    # ── Case 4: neither ──────────────────────────────────────────────────────
    else:
        result["flag_reason"] = "No GPS from any source — complaint cannot be geolocated"

    return result