"""
Module 4 - Repair Verifier
verifier.py: Main entry point — orchestrates GPS, SSIM, and YOLO checks
"""

import json
import argparse
from gps_checker  import validate_gps
from ssim_compare import compute_ssim
from yolo_infer   import detect_potholes
from decision     import make_verdict, print_verdict


def verify_repair(
    before_path,
    after_path,
    original_gps,
    model_path         = "best.pt",
    gps_threshold      = 30.0,
    conf_threshold     = 0.35,
    save_diff          = False,
    save_annotated     = False
):
    """
    Full pipeline: runs GPS check, SSIM, and YOLO then returns a verdict.

    Args:
        before_path    : path to the original complaint image
        after_path     : path to the after-repair image submitted by contractor
        original_gps   : (lat, lon) tuple from the complaint record
        model_path     : path to Module 1 YOLOv8 weights (.pt file)
        gps_threshold  : max GPS distance in meters (default 30)
        conf_threshold : YOLO confidence threshold (default 0.35)
        save_diff      : if True, saves SSIM diff image to disk
        save_annotated : if True, saves YOLO annotated after-image to disk

    Returns:
        Full verdict dict
    """
    print(f"\n[Verifier] Before image : {before_path}")
    print(f"[Verifier] After image  : {after_path}")
    print(f"[Verifier] Original GPS : {original_gps}\n")

    # ── Step 1: GPS Validation ─────────────────────────────────────────────────
    print("[Step 1/3] Running GPS validation...")
    gps_result = validate_gps(after_path, original_gps, gps_threshold)
    print(f"           {gps_result['note']}")

    # ── Step 2: SSIM Comparison ────────────────────────────────────────────────
    print("[Step 2/3] Computing SSIM...")
    ssim_result = compute_ssim(before_path, after_path)
    print(f"           SSIM Score: {ssim_result['ssim_score']} — {ssim_result['interpretation']}")

    if save_diff:
        from ssim_compare import save_diff_image
        save_diff_image(ssim_result["diff_image"], "diff_output.jpg")

    # ── Step 3: YOLO Detection on After Image ──────────────────────────────────
    print("[Step 3/3] Running YOLO pothole detection on after-image...")
    yolo_result = detect_potholes(after_path, model_path, conf_threshold)
    print(f"           Potholes detected: {yolo_result['count']}")

    if save_annotated and yolo_result["raw_results"]:
        from yolo_infer import save_annotated_image
        save_annotated_image(yolo_result["raw_results"], "annotated_after.jpg")

    # ── Step 4: Final Decision ─────────────────────────────────────────────────
    verdict = make_verdict(ssim_result, yolo_result, gps_result)
    print_verdict(verdict)

    return verdict


# ── CLI Interface ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Module 4 — Repair Verifier")
    parser.add_argument("--before",       required=True,  help="Path to before image")
    parser.add_argument("--after",        required=True,  help="Path to after image")
    parser.add_argument("--lat",          required=True,  type=float, help="Original complaint latitude")
    parser.add_argument("--lon",          required=True,  type=float, help="Original complaint longitude")
    parser.add_argument("--model",        default="best.pt", help="YOLOv8 model path (default: best.pt)")
    parser.add_argument("--gps-thresh",   default=30.0,   type=float, help="GPS distance threshold in meters")
    parser.add_argument("--conf",         default=0.35,   type=float, help="YOLO confidence threshold")
    parser.add_argument("--save-diff",    action="store_true", help="Save SSIM diff image")
    parser.add_argument("--save-annotated", action="store_true", help="Save YOLO annotated image")
    parser.add_argument("--json",         action="store_true", help="Output result as JSON")

    args = parser.parse_args()

    result = verify_repair(
        before_path    = args.before,
        after_path     = args.after,
        original_gps   = (args.lat, args.lon),
        model_path     = args.model,
        gps_threshold  = args.gps_thresh,
        conf_threshold = args.conf,
        save_diff      = args.save_diff,
        save_annotated = args.save_annotated
    )

    if args.json:
        # Remove non-serializable keys before printing
        result.pop("diff_image", None)
        print(json.dumps(result, indent=2))
