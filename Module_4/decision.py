"""
Module 4 - Repair Verifier
decision.py: Combines SSIM + YOLO + GPS results into a final verdict
"""


# Thresholds — tune these based on your dataset
SSIM_REPAIRED_THRESHOLD   = 0.65   # Below this = surface clearly changed
SSIM_SUSPICIOUS_THRESHOLD = 0.85   # Above this + no pothole = suspicious (wrong photo?)
GPS_DISTANCE_THRESHOLD    = 30.0   # Meters


def make_verdict(ssim_result, yolo_result, gps_result):
    """
    Combines results from all three checks into a single verdict.

    Args:
        ssim_result : dict from ssim_compare.compute_ssim()
        yolo_result : dict from yolo_infer.detect_potholes()
        gps_result  : dict from gps_checker.validate_gps()

    Returns:
        dict with verdict, confidence, reason, all sub-scores
    """
    ssim_score     = ssim_result["ssim_score"]
    pothole_count  = yolo_result["count"]
    gps_valid      = gps_result.get("is_valid")     # True / False / None
    gps_found      = gps_result.get("gps_found")

    surface_changed = ssim_score < SSIM_REPAIRED_THRESHOLD
    no_pothole      = pothole_count == 0
    highly_similar  = ssim_score >= SSIM_SUSPICIOUS_THRESHOLD

    # ── Decision tree ──────────────────────────────────────────────────────────
    if gps_found and gps_valid is False:
        verdict    = "SUSPICIOUS"
        confidence = "HIGH"
        reason     = (
            f"GPS mismatch detected. After-photo taken "
            f"{gps_result['distance_m']}m away from complaint location "
            f"(threshold: {GPS_DISTANCE_THRESHOLD}m). Possible fraud."
        )

    elif surface_changed and no_pothole:
        verdict    = "REPAIRED"
        confidence = "HIGH"
        reason     = (
            f"Surface clearly changed (SSIM={ssim_score}) "
            f"AND no potholes detected by YOLO. Repair confirmed."
        )

    elif not surface_changed and pothole_count > 0:
        verdict    = "NOT_REPAIRED"
        confidence = "HIGH"
        reason     = (
            f"Surface unchanged (SSIM={ssim_score}) "
            f"AND {pothole_count} pothole(s) still detected. Repair not done."
        )

    elif highly_similar and no_pothole:
        verdict    = "SUSPICIOUS"
        confidence = "MEDIUM"
        reason     = (
            f"Images are very similar (SSIM={ssim_score}) but no pothole found. "
            "Contractor may have submitted the original photo again."
        )

    elif surface_changed and pothole_count > 0:
        verdict    = "INCONCLUSIVE"
        confidence = "LOW"
        reason     = (
            f"Surface changed (SSIM={ssim_score}) but "
            f"{pothole_count} pothole(s) still visible. Partial repair possible."
        )

    else:
        verdict    = "INCONCLUSIVE"
        confidence = "LOW"
        reason     = "Mixed signals from SSIM and YOLO. Manual review recommended."

    return {
        "verdict"          : verdict,
        "confidence"       : confidence,
        "reason"           : reason,
        "ssim_score"       : ssim_score,
        "potholes_detected": pothole_count,
        "gps_distance_m"   : gps_result.get("distance_m"),
        "gps_valid"        : gps_valid,
        "gps_note"         : gps_result.get("note"),
    }


def print_verdict(verdict_dict):
    """Pretty-prints the final verdict to console."""
    print("\n" + "=" * 55)
    print("       MODULE 4 — REPAIR VERIFICATION RESULT")
    print("=" * 55)
    print(f"  VERDICT     : {verdict_dict['verdict']}")
    print(f"  CONFIDENCE  : {verdict_dict['confidence']}")
    print(f"  REASON      : {verdict_dict['reason']}")
    print("-" * 55)
    print(f"  SSIM Score  : {verdict_dict['ssim_score']}")
    print(f"  Potholes    : {verdict_dict['potholes_detected']}")
    print(f"  GPS Distance: {verdict_dict['gps_distance_m']} m")
    print(f"  GPS Valid   : {verdict_dict['gps_valid']}")
    print("=" * 55 + "\n")
