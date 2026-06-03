# main.py

import logging
import sys
from typing import Optional

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from dotenv import load_dotenv
from pathlib import Path

from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi import Depends, Security
from pydantic import BaseModel
from shared.auth import create_token, verify_token, check_credentials

load_dotenv(dotenv_path=Path(__file__).parent / ".env")

# ─── Module 0 imports ─────────────────────────────────────────────────────────
from Module_0.exif_extractor      import extract_exif_gps
from Module_0.timestamp_validator import validate_timestamp
from Module_0.gps_validator       import validate_gps
from Module_0.reverse_geocoder    import reverse_geocode
from Module_0.trust_scorer        import compute_trust_score

# ─── Module 1 import ──────────────────────────────────────────────────────────
from Module_1.detector import detect_damage

sys.path.insert(0, "Module_2")
sys.path.insert(0, "Module_3")

# ─── Module 2 import ──────────────────────────────────────────────────────────
from Module_2.duplicate import check_and_store_report

# ─── Module 3 import ──────────────────────────────────────────────────────────
from Module_3.router import load_models, route_complaint

# ─── Shared utilities ─────────────────────────────────────────────────────────
from shared.database import (
    get_complaint,
    get_all_genuine_complaints,
    get_dashboard_stats,
    insert_complaint,
    insert_detection,
    insert_routing,
    update_routing_status,
)
from shared.storage import upload_image

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ─── Valid road types ─────────────────────────────────────────────────────────
VALID_ROAD_TYPES = {
    "national_highway", "state_highway",
    "major_district_road", "city_road", "rural_road",
}

# ─── FastAPI app ──────────────────────────────────────────────────────────────
app = FastAPI(
    title="Road Safety — Central API",
    description="Orchestrates Modules 0-3 for citizen complaint submission",
    version="1.0.0",
)

import sys
sys.path.insert(0, "Module_2")
sys.path.insert(0, "Module_3")

# Import routers from Module 4 and Module 5
from Module_4.api              import router as repair_router
from Module_5.backend.main     import router as dashboard_router
from fastapi.staticfiles        import StaticFiles
from fastapi.responses          import FileResponse

# Wire in the routers
app.include_router(repair_router)
app.include_router(dashboard_router)

# Serve built React app at /dashboard
# This runs AFTER npm run build creates Module_5/frontend/dist/
import os
REACT_BUILD = "Module_5/frontend/dist"
if os.path.exists(REACT_BUILD):
    app.mount(
        "/dashboard",
        StaticFiles(directory=REACT_BUILD, html=True),
        name="dashboard"
    )

# Serve citizen portal
@app.get("/citizen")
def citizen_portal():
    return FileResponse("citizen.html")

# Redirect root to login
@app.get("/")
def root():
    return FileResponse("citizen.html")

# ── Auth dependency ───────────────────────────────────────────────────────────
_bearer = HTTPBearer()

def require_auth(
    credentials: HTTPAuthorizationCredentials = Security(_bearer)
) -> str:
    """
    FastAPI dependency — protects any route it is added to.
    Returns username if token valid, raises 401 otherwise.
    """
    username = verify_token(credentials.credentials)
    if not username:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token. Please log in again."
        )
    return username


# ── Login endpoint (public — no auth required) ────────────────────────────────
class LoginRequest(BaseModel):
    username: str
    password: str

@app.post("/auth/login")
def login(req: LoginRequest):
    if not check_credentials(req.username, req.password):
        raise HTTPException(
            status_code=401,
            detail="Incorrect username or password"
        )
    token = create_token(req.username)
    return {
        "access_token": token,
        "token_type":   "bearer",
        "username":     req.username,
        "expires_in":   f"8 hours",
    }


@app.get("/auth/verify")
def verify_auth(username: str = Depends(require_auth)):
    """Used by frontend to check if stored token is still valid."""
    return {"valid": True, "username": username}

from fastapi.responses import FileResponse



app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # tighten this in production
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Load ML models at startup ────────────────────────────────────────────────
@app.on_event("startup")
def startup():
    logger.info("[main] Loading Module 3 models...")
    load_models()
    logger.info("[main] All models ready. Server accepting requests.")


# ──────────────────────────────────────────────────────────────────────────────
# ENDPOINT 1 — Citizen submits complaint
# POST /complaint/submit
# ──────────────────────────────────────────────────────────────────────────────
@app.post("/complaint/submit")
async def submit_complaint(
    image:          UploadFile        = File(...),
    browser_lat:    Optional[float]   = Form(None),
    browser_lon:    Optional[float]   = Form(None),
    road_type_form: Optional[str]     = Form(None),
    damage_note:    Optional[str]     = Form(None),
):
    flags       = []
    image_bytes = await image.read()

    # ── Step 1: Module 0 — GPS extraction & validation ────────────────────────
    exif = extract_exif_gps(image_bytes)
    if exif["error"]:
        flags.append(exif["error"])

    ts = validate_timestamp(exif.get("timestamp"))
    if ts["flag_reason"]:
        flags.append(ts["flag_reason"])

    gps = validate_gps(
        exif_lat    = exif.get("lat"),
        exif_lon    = exif.get("lon"),
        browser_lat = browser_lat,
        browser_lon = browser_lon,
    )
    if gps["flag_reason"]:
        flags.append(gps["flag_reason"])

    # Hard stop — no GPS from any source
    if gps["gps_source"] == "none":
        raise HTTPException(
            status_code=422,
            detail={
                "status": "REJECTED",
                "reason": "No GPS coordinates available from any source",
                "flags":  flags,
            }
        )

    geo = reverse_geocode(gps["final_lat"], gps["final_lon"])
    if geo["flag_reason"]:
        flags.append(geo["flag_reason"])

    nominatim_failed = not geo["is_valid_location"] and geo["address"] is None

    # Hard stop — coordinates outside India or in water
    if not geo["is_valid_location"] and not nominatim_failed:
        raise HTTPException(
            status_code=422,
            detail={
                "status": "REJECTED",
                "reason": geo["flag_reason"],
                "flags":  flags,
            }
        )

    # Road type resolution: OSM → user form → default
    if geo.get("road_type"):
        road_type        = geo["road_type"]
        road_type_source = "osm"
    elif road_type_form and road_type_form in VALID_ROAD_TYPES:
        road_type        = road_type_form
        road_type_source = "user_form"
    else:
        road_type        = "city_road"
        road_type_source = "default"
        flags.append("Road type defaulted to city_road")

    trust = compute_trust_score(
        gps_source        = gps["gps_source"],
        mismatch_flag     = gps["mismatch_flag"],
        timestamp_flag    = ts["timestamp_flag"],
        is_valid_location = geo["is_valid_location"],
        nominatim_failed  = nominatim_failed,
        road_type_source  = road_type_source,
    )

    if trust["recommendation"] == "REJECT":
        raise HTTPException(
            status_code=422,
            detail={
                "status":          "REJECTED",
                "gps_trust_score": trust["gps_trust_score"],
                "reason":          trust["deductions"],
                "flags":           flags,
            }
        )

    # ── Step 2: Cloudinary — upload image ─────────────────────────────────────
    try:
        image_url = upload_image(image_bytes, folder="complaints")
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=f"Image upload failed: {e}")

    # ── Step 3: Module 1 — pothole detection ──────────────────────────────────
    detection      = detect_damage(image_bytes)
    detection_flag = "DETECTED"

    if detection.get("error"):
        # Model crashed — flag but continue with defaults
        flags.append(f"Detection error: {detection['error']}")
        detection_flag = "DETECTION_ERROR"

    if detection["cluster_count"] == 0:
        # No damage found — flag for manual review, use safe defaults for routing
        flags.append("No damage detected — flagged for manual review")
        detection_flag  = "NO_DAMAGE_DETECTED"
        routing_damage  = "Longitudinal"   # safest default for Module 3
    else:
        routing_damage  = detection["damage_class"]

    # ── Step 4: Insert complaint to PostgreSQL — get complaint_id ─────────────
    complaint_id = insert_complaint({
        "lat":              gps["final_lat"],
        "lon":              gps["final_lon"],
        "gps_source":       gps["gps_source"],
        "gps_trust_score":  trust["gps_trust_score"],
        "recommendation":   trust["recommendation"],
        "flags":            flags + trust["deductions"],
        "address":          geo.get("address"),
        "road_name":        geo.get("road_name"),
        "road_type":        road_type,
        "road_type_source": road_type_source,
        "city":             geo.get("city"),
        "state":            geo.get("state"),
        "image_url":        image_url,
        "damage_note":      damage_note,
    })

    # ── Step 5: Insert detection to PostgreSQL ────────────────────────────────
    insert_detection(complaint_id, detection)

    # ── Step 6: Module 2 — duplicate check ───────────────────────────────────
    # Note: check_and_store_report must accept complaint_id
    # Ask your friend to add it as the first parameter
    duplicate = check_and_store_report(
        complaint_id = complaint_id,
        image_url    = image_url,
        latitude     = gps["final_lat"],
        longitude    = gps["final_lon"],
        damage_class = routing_damage,
    )

    if duplicate.get("status") == "duplicate":
        return JSONResponse(status_code=200, content={
            "status":              "DUPLICATE",
            "complaint_id":        complaint_id,
            "linked_to":           str(duplicate.get("duplicate_of")),
            "hamming_distance":    duplicate.get("hamming_dist"),
            "gps_distance_metres": duplicate.get("gps_dist_m"),
            "message": (
                "This complaint matches an existing report nearby. "
                "Your submission has been linked to the original."
            ),
        })

    # ── Step 7: Module 3 — smart routing ─────────────────────────────────────
    ticket = route_complaint(
        damage_class       = routing_damage,
        road_type          = road_type,
        relative_bbox_area = detection["relative_bbox_area"],
        cluster_count      = detection["cluster_count"],
    )

    # ── Step 8: Insert routing to PostgreSQL ──────────────────────────────────
    insert_routing(complaint_id, {
        "priority":    ticket["priority"],
        "authority":   ticket["authority"],
        "sla_days":    ticket["expected_resolution_days"],
        "shap_reason": ticket["reason"],
    })

    # ── Final response to citizen ─────────────────────────────────────────────
    return JSONResponse(status_code=201, content={
        "status":          "ACCEPTED",
        "complaint_id":    complaint_id,
        "priority":        ticket["priority"],
        "authority":       ticket["authority"],
        "sla_days":        ticket["expected_resolution_days"],
        "reason":          ticket["reason"],
        "damage_detected": detection["damage_class"],
        "detection_flag":  detection_flag,
        "gps_trust_score": trust["gps_trust_score"],
        "address":         geo.get("address"),
        "image_url":       image_url,
        "flags":           flags,
    })


# ──────────────────────────────────────────────────────────────────────────────
# ENDPOINT 2 — Citizen checks complaint status
# GET /complaint/{id}/status
# ──────────────────────────────────────────────────────────────────────────────
@app.get("/complaint/{complaint_id}/status")
def get_status(complaint_id: str):
    complaint = get_complaint(complaint_id)

    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found")

    return {
        "complaint_id": complaint_id,
        "status":        complaint.get("status", "PENDING"),
        "priority":      complaint.get("priority"),
        "authority":     complaint.get("authority"),
        "sla_days":      complaint.get("sla_days"),
        "damage_class":  complaint.get("damage_class"),
        "address":       complaint.get("address"),
        "submitted_at":  str(complaint.get("submitted_at")),
    }


# ──────────────────────────────────────────────────────────────────────────────
# ENDPOINT 3 — Dashboard stats (Module 5)
# GET /dashboard/stats
# ──────────────────────────────────────────────────────────────────────────────
@app.get("/dashboard/stats", dependencies=[Depends(require_auth)])
def dashboard_stats():
    return get_dashboard_stats()


# ──────────────────────────────────────────────────────────────────────────────
# ENDPOINT 4 — Dashboard reports map (Module 5)
# GET /dashboard/reports
# ──────────────────────────────────────────────────────────────────────────────
@app.get("/dashboard/reports", dependencies=[Depends(require_auth)])
def dashboard_reports():
    return get_all_genuine_complaints()


# ──────────────────────────────────────────────────────────────────────────────
# ENDPOINT 5 — Manual authority override (Module 5)
# POST /dashboard/reports/{id}/verify
# ──────────────────────────────────────────────────────────────────────────────
@app.post("/dashboard/reports/{complaint_id}/verify", dependencies=[Depends(require_auth)])
def manual_verify(complaint_id: str, status: str = Form(...)):
    valid = {"RESOLVED", "FLAGGED", "REJECTED", "IN_PROGRESS"}
    if status not in valid:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid status. Must be one of: {valid}"
        )
    update_routing_status(complaint_id, status)
    return {"complaint_id": complaint_id, "updated_status": status}