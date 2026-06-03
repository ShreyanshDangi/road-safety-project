# module0/trust_scorer.py

def compute_trust_score(
    gps_source:        str,
    mismatch_flag:     bool,
    timestamp_flag:    bool,
    is_valid_location: bool,
    nominatim_failed:  bool,
    road_type_source:  str,   # "osm" | "user_form" | "default"
) -> dict:
    """
    Computes GPS trust score from all validation flags.

    Starts at 1.0, deducts per flag based on severity.
    Never hard-rejects here — that is the pipeline's decision in Step 6.

    Returns:
    {
        "gps_trust_score": float,       # 0.0 – 1.0
        "recommendation":  str,         # "ACCEPT" | "REVIEW" | "REJECT"
        "deductions":      list[str],   # audit trail of what was deducted
    }
    """

    score      = 1.0
    deductions = []

    # ── GPS source penalty ────────────────────────────────────────────────────
    if gps_source == "browser":
        score -= 0.15
        deductions.append("-0.15: GPS from browser only, no EXIF")

    elif gps_source == "exif_flagged":
        score -= 0.25
        deductions.append("-0.25: EXIF and browser GPS mismatch >100m")

    elif gps_source == "none":
        score -= 0.60
        deductions.append("-0.60: No GPS from any source")

    # ── Mismatch flag (already covered in exif_flagged, skip double-deduct) ──
    if mismatch_flag and gps_source != "exif_flagged":
        score -= 0.10
        deductions.append("-0.10: GPS mismatch flag (secondary)")

    # ── Timestamp flag ────────────────────────────────────────────────────────
    if timestamp_flag:
        score -= 0.20
        deductions.append("-0.20: Photo timestamp suspicious (old or future)")

    # ── Location validity ─────────────────────────────────────────────────────
    if not is_valid_location and not nominatim_failed:
        # Nominatim responded but location is invalid (ocean, forest, etc.)
        score -= 0.40
        deductions.append("-0.40: Coordinates do not resolve to a valid road")

    if nominatim_failed:
        # Nominatim timed out or errored — can't verify, small deduction
        score -= 0.05
        deductions.append("-0.05: Reverse geocoding unavailable, location unverified")

    # ── Road type source ──────────────────────────────────────────────────────
    if road_type_source == "default":
        score -= 0.05
        deductions.append("-0.05: Road type defaulted, not confirmed")

    # ── Clamp to valid range ──────────────────────────────────────────────────
    score = round(max(0.0, min(1.0, score)), 3)

    # ── Recommendation ────────────────────────────────────────────────────────
    if score >= 0.75:
        recommendation = "ACCEPT"
    elif score >= 0.45:
        recommendation = "REVIEW"
    else:
        recommendation = "REJECT"

    return {
        "gps_trust_score": score,
        "recommendation":  recommendation,
        "deductions":      deductions,
    }