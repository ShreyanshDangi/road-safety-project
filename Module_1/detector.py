# module_1/detector.py

from ultralytics import YOLO
from PIL import Image
from io import BytesIO
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

# ─── Config ───────────────────────────────────────────────────────────────────
WEIGHTS_PATH   = Path(__file__).parent / "weights" / "best.pt"
CONF_THRESHOLD = 0.28   # tuned during RDD2022 training

# Priority order for selecting primary class when multiple types detected
# Higher value = more dangerous = becomes the reported damage_class
CLASS_PRIORITY = {
    "Pothole":      4,
    "Alligator":    3,
    "Transverse":   2,
    "Longitudinal": 1,
}

# ─── Load model once at import time ───────────────────────────────────────────
# This runs when FastAPI starts, not on every request
try:
    _model = YOLO(str(WEIGHTS_PATH))
    logger.info(f"[detector] Model loaded from {WEIGHTS_PATH}")
except Exception as e:
    _model = None
    logger.error(f"[detector] Failed to load model: {e}")


# ─── Internal helpers ─────────────────────────────────────────────────────────
def _relative_area(bbox: list, img_w: int, img_h: int) -> float:
    """
    bbox area as fraction of total image area.
    bbox: [x1, y1, x2, y2] in pixels.
    Returns value between 0.0 and 1.0.
    """
    x1, y1, x2, y2 = bbox
    bbox_area  = max(0.0, (x2 - x1) * (y2 - y1))
    image_area = img_w * img_h
    if image_area == 0:
        return 0.0
    return round(bbox_area / image_area, 6)


def _primary_class(detections: list) -> dict | None:
    """
    From all detections, return the one with highest danger priority.
    Pothole > Alligator > Transverse > Longitudinal.
    Ties broken by confidence.
    """
    if not detections:
        return None
    return max(
        detections,
        key=lambda d: (CLASS_PRIORITY.get(d["class"], 0), d["confidence"])
    )


# ─── Public inference function ────────────────────────────────────────────────
def detect_damage(image_bytes: bytes, conf: float = CONF_THRESHOLD) -> dict:
    """
    Run YOLOv8 inference on road image bytes.

    Args:
        image_bytes : raw bytes from UploadFile.read() or open(path, "rb").read()
        conf        : confidence threshold, default 0.28

    Returns:
        {
            damage_class       : str | None   — primary (most dangerous) class detected
            relative_bbox_area : float        — largest single bbox / image area
            cluster_count      : int          — total detections in frame
            confidence         : float        — confidence of primary detection
            has_pothole        : bool         — True if any Pothole class detected
            total_detections   : int          — same as cluster_count
            raw_detections     : list         — full audit list stored in PostgreSQL JSONB
            error              : str | None   — set only if inference crashed
        }

    Note: NO severity field. severity/priority is Module 3's responsibility.
    """
    result = {
        "damage_class":       None,
        "relative_bbox_area": 0.0,
        "cluster_count":      0,
        "confidence":         0.0,
        "has_pothole":        False,
        "total_detections":   0,
        "raw_detections":     [],
        "error":              None,
    }

    if _model is None:
        result["error"] = "Model not loaded — check weights path"
        return result

    try:
        img    = Image.open(BytesIO(image_bytes)).convert("RGB")
        img_w, img_h = img.size

        yolo_out = _model.predict(source=img, conf=conf, verbose=False)[0]

        if len(yolo_out.boxes) == 0:
            # Clean no-detection — not an error
            return result

        # ── Parse detections ──────────────────────────────────────────────────
        detections = []
        for box in yolo_out.boxes:
            class_name = yolo_out.names[int(box.cls)]
            bbox       = [round(v, 2) for v in box.xyxy[0].tolist()]
            detections.append({
                "class":      class_name,
                "confidence": round(float(box.conf), 3),
                "bbox":       bbox,                              # [x1, y1, x2, y2] pixels
                "rel_area":   _relative_area(bbox, img_w, img_h),
            })

        # ── Primary class selection ───────────────────────────────────────────
        primary = _primary_class(detections)

        # ── Largest single bbox area ──────────────────────────────────────────
        max_rel_area = max(d["rel_area"] for d in detections)

        result["damage_class"]       = primary["class"]
        result["relative_bbox_area"] = max_rel_area
        result["cluster_count"]      = len(detections)
        result["confidence"]         = primary["confidence"]
        result["has_pothole"]        = any(d["class"] == "Pothole" for d in detections)
        result["total_detections"]   = len(detections)
        result["raw_detections"]     = detections

    except Exception as e:
        result["error"] = str(e)
        logger.exception("[detector] detect_damage crashed")

    return result