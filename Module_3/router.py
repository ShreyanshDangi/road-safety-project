"""
Module 3 — Smart Router
Step 4: route_complaint() — Public API

Accepts Module 1 output + GPS metadata.
Returns a fully structured complaint ticket.

Usage:
    from router import route_complaint, load_models

    load_models()   # call once at startup

    ticket = route_complaint(
        damage_class="Pothole",
        road_type="national_highway",
        relative_bbox_area=0.35,
        cluster_count=4
    )
"""

import uuid
import datetime
import numpy as np
import pandas as pd
import joblib
import shap
from pathlib import Path



from explainer import generate_reason

MODULE_DIR = Path(__file__).parent

# ─── Global model references (lazy-loaded) ───────────────────────────────────
_PIPELINE   = None
_TARGET_MAP = None
_EXPLAINER  = None

# ─── Rule-based authority routing ────────────────────────────────────────────
ROAD_TO_AUTHORITY = {
    "national_highway":    "NHAI",
    "state_highway":       "PWD",
    "major_district_road": "PWD",
    "city_road":           "Municipal",
    "rural_road":          "Panchayat",
}

# Expected resolution SLA per authority × priority (days)
SLA_TABLE = {
    "NHAI":       {"HIGH": 3,  "MEDIUM": 7,  "LOW": 14},
    "PWD":        {"HIGH": 5,  "MEDIUM": 10, "LOW": 21},
    "Municipal":  {"HIGH": 7,  "MEDIUM": 14, "LOW": 30},
    "Panchayat":  {"HIGH": 14, "MEDIUM": 30, "LOW": 60},
}


def load_models():
    """Load all serialised artefacts once at startup."""
    global _PIPELINE, _TARGET_MAP, _EXPLAINER
    
    _PIPELINE   = joblib.load(MODULE_DIR / "models" / "priority_router_pipeline.pkl")
    _TARGET_MAP = joblib.load(MODULE_DIR / "models" / "target_map.pkl")
    
    # Initialize SHAP explainer directly from the pipeline's Random Forest
    rf_model = _PIPELINE.named_steps["classifier"]
    _EXPLAINER = shap.TreeExplainer(rf_model)
    
    print("[router] Pipeline, Target Map, and SHAP Explainer loaded successfully.")


# ─── Main public function ─────────────────────────────────────────────────────
def route_complaint(
    damage_class: str,
    road_type: str,
    relative_bbox_area: float,
    cluster_count: int,
) -> dict:
    """
    Route a complaint and return a structured ticket.

    Parameters
    ----------
    damage_class       : e.g. "Pothole", "Alligator", "Longitudinal", "Transverse"
    road_type          : "national_highway" | "state_highway" | "major_district_road" |
                         "city_road" | "rural_road"
    relative_bbox_area : bounding box area ratio (0.01 to 0.60)
    cluster_count      : count of damage instances in the image

    Returns
    -------
    dict with keys: complaint_id, authority, priority, expected_resolution_days,
                    reason, timestamp, input_summary
    """
    if _PIPELINE is None:
        raise RuntimeError("Models not loaded. Call load_models() first.")

    raw_inputs = {
        "damage_class": damage_class,
        "road_type": road_type,
        "relative_bbox_area": relative_bbox_area,
        "cluster_count": cluster_count
    }
    
    # Pipeline requires a DataFrame
    df_input = pd.DataFrame([raw_inputs])

    # ── Predict priority ──────────────────────────────────────────────────
    pred_idx   = _PIPELINE.predict(df_input)[0]
    pred_proba = _PIPELINE.predict_proba(df_input)[0]
    
    priority   = _TARGET_MAP[pred_idx]
    confidence = float(pred_proba[pred_idx])

    # ── SHAP explanation ──────────────────────────────────────────────────
    preprocessor = _PIPELINE.named_steps["preprocessor"]
    encoded_input = preprocessor.transform(df_input)
    
    # Dynamically fetch feature names created by the OneHotEncoder
    cat_feats = preprocessor.named_transformers_["cat"].get_feature_names_out(["damage_class", "road_type"])
    num_feats = ["relative_bbox_area", "cluster_count"]
    all_feat_names = list(cat_feats) + num_feats

    shap_values = _EXPLAINER.shap_values(encoded_input)
    
    # Robust SHAP extraction for multi-class
    if isinstance(shap_values, list):
        class_shap = shap_values[pred_idx][0] 
    else:
        class_shap = shap_values[0, :, pred_idx]
        
    shap_impacts = dict(zip(all_feat_names, class_shap))
    
    # Generate human-readable reason
    reason = generate_reason(raw_inputs, shap_impacts, top_k=2)

    # ── Resolution SLA ────────────────────────────────────────────────────
    authority = ROAD_TO_AUTHORITY.get(road_type, "Municipal")
    resolution_days = SLA_TABLE.get(authority, {}).get(priority, 14)

    # ── Build ticket ──────────────────────────────────────────────────────
    complaint_id = f"CMP-{datetime.datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"

    ticket = {
        "complaint_id":             complaint_id,
        "authority":                authority,
        "priority":                 priority,
        "confidence":               round(confidence, 3),
        "expected_resolution_days": resolution_days,
        "reason":                   reason,
        "timestamp":                datetime.datetime.utcnow().isoformat() + "Z",
        "input_summary":            raw_inputs,
    }

    return ticket


# ─── Quick demo ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import json

    load_models()

    test_cases = [
        dict(damage_class="Pothole",      road_type="national_highway", relative_bbox_area=0.35, cluster_count=4),
        dict(damage_class="Alligator",    road_type="state_highway",    relative_bbox_area=0.20, cluster_count=2),
        dict(damage_class="Longitudinal", road_type="city_road",        relative_bbox_area=0.05, cluster_count=1),
        dict(damage_class="Transverse",   road_type="rural_road",       relative_bbox_area=0.02, cluster_count=1),
    ]

    print("\n" + "="*60)
    print("  MODULE 3 — SMART ROUTER — TEST OUTPUT")
    print("="*60 + "\n")

    for tc in test_cases:
        ticket = route_complaint(**tc)
        print(json.dumps(ticket, indent=2))
        print("-" * 60)