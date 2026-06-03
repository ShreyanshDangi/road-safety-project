# module0/ingest.py

from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional
import uuid

# ingest.py — change all imports from module0 → Module_0
from module_0.exif_extractor     import extract_exif_gps
from module_0.timestamp_validator import validate_timestamp
from module_0.gps_validator      import validate_gps
from module_0.reverse_geocoder   import reverse_geocode
from module_0.trust_scorer       import compute_trust_score

app = FastAPI(title="Pothole Reporting — Ingestion API")

VALID_ROAD_TYPES = {
    "national_highway", "state_highway",
    "major_district_road", "city_road", "rural_road"
}


class IngestResponse(BaseModel):
    complaint_id:    str
    status:          str          # ACCEPTED | REVIEW | REJECTED
    lat:             Optional[float]
    lon:             Optional[float]
    gps_source:      str
    road_type:       Optional[str]
    road_type_source: str         # osm | user_form | default
    address:         Optional[str]
    city:            Optional[str]
    state:           Optional[str]
    gps_trust_score: float
    recommendation:  str
    flags:           list[str]    # audit trail


@app.post("/ingest", response_model=IngestResponse)
async def ingest_complaint(
    image:       UploadFile         = File(...),
    browser_lat: Optional[float]    = Form(None),
    browser_lon: Optional[float]    = Form(None),
    road_type_form: Optional[str]   = Form(None),   # user's dropdown
    damage_note: Optional[str]      = Form(None),
):
    flags        = []
    image_bytes  = await image.read()

    # ── Step 1: EXIF extraction ───────────────────────────────────────────────
    exif = extract_exif_gps(image_bytes)
    if exif["error"]:
        flags.append(exif["error"])

    # ── Step 2: Timestamp validation ─────────────────────────────────────────
    ts = validate_timestamp(exif["timestamp"])
    if ts["flag_reason"]:
        flags.append(ts["flag_reason"])

    # ── Step 3: GPS cross-validation ─────────────────────────────────────────
    gps = validate_gps(
        exif_lat    = exif["lat"],
        exif_lon    = exif["lon"],
        browser_lat = browser_lat,
        browser_lon = browser_lon,
    )
    if gps["flag_reason"]:
        flags.append(gps["flag_reason"])

    # Hard stop — no GPS from any source, cannot proceed
    if gps["gps_source"] == "none":
        return JSONResponse(status_code=422, content={
            "status":  "REJECTED",
            "reason":  "No GPS coordinates available from any source",
            "flags":   flags,
        })

    # ── Step 4: Reverse geocoding ─────────────────────────────────────────────
    geo = reverse_geocode(gps["final_lat"], gps["final_lon"])
    if geo["flag_reason"]:
        flags.append(geo["flag_reason"])

    nominatim_failed = not geo["is_valid_location"] and geo["address"] is None

    # Hard stop — coordinates outside India or in water
    if not geo["is_valid_location"] and not nominatim_failed:
        return JSONResponse(status_code=422, content={
            "status": "REJECTED",
            "reason": geo["flag_reason"],
            "flags":  flags,
        })

    # ── Road type resolution: OSM → user form → default ──────────────────────
    if geo["road_type"]:
        road_type        = geo["road_type"]
        road_type_source = "osm"

    elif road_type_form and road_type_form in VALID_ROAD_TYPES:
        road_type        = road_type_form
        road_type_source = "user_form"

    else:
        road_type        = "city_road"
        road_type_source = "default"
        flags.append("Road type defaulted to city_road — not confirmed by OSM or user")

    # ── Step 5: Trust score ───────────────────────────────────────────────────
    trust = compute_trust_score(
        gps_source        = gps["gps_source"],
        mismatch_flag     = gps["mismatch_flag"],
        timestamp_flag    = ts["timestamp_flag"],
        is_valid_location = geo["is_valid_location"],
        nominatim_failed  = nominatim_failed,
        road_type_source  = road_type_source,
    )

    complaint_id = str(uuid.uuid4())

    # ── Store to DB here (PostgreSQL call goes here in full build) ────────────
    # db.insert_complaint({complaint_id, lat, lon, road_type, trust_score, ...})

    return IngestResponse(
        complaint_id     = complaint_id,
        status           = trust["recommendation"],
        lat              = gps["final_lat"],
        lon              = gps["final_lon"],
        gps_source       = gps["gps_source"],
        road_type        = road_type,
        road_type_source = road_type_source,
        address          = geo["address"],
        city             = geo["city"],
        state            = geo["state"],
        gps_trust_score  = trust["gps_trust_score"],
        recommendation   = trust["recommendation"],
        flags            = flags + trust["deductions"],
    )
    
    
    #uvicorn module0.ingest:app --reload