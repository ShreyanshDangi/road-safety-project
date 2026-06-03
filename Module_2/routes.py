"""
routes.py — All FastAPI Endpoints

Changes vs original:
  • severity form field removed entirely
  • damage_type  → damage_class
  • image upload (UploadFile) replaced by image_url (str) —
    Cloudinary URL is set by the pipeline before Module 2 is called,
    so Module 2 no longer handles file I/O at all
  • /image/{filename} route removed (images live on Cloudinary now)
  • DB imports point to shared.database
"""

from fastapi import APIRouter, Form, HTTPException

from duplicate import check_and_store_report
from shared.database import fetch_all_reports, fetch_report_by_id, fetch_stats, clear_all_reports

router = APIRouter()


@router.post("/check-duplicate")
async def check_duplicate(
    image_url:    str   = Form(...),
    latitude:     float = Form(...),
    longitude:    float = Form(...),
    damage_class: str   = Form("unknown"),
):
    """
    Accepts a Cloudinary image URL + GPS coordinates + damage class from Module 1.
    Returns a duplicate verdict with a full audit trail.
    """
    result = check_and_store_report(
        image_url=image_url,
        latitude=latitude,
        longitude=longitude,
        damage_class=damage_class,
    )
    return result


@router.get("/reports")
def get_all_reports():
    reports = fetch_all_reports()
    return {"count": len(reports), "reports": reports}


@router.get("/reports/{report_id}")
def get_report(report_id: int):
    report = fetch_report_by_id(report_id)
    if not report:
        raise HTTPException(status_code=404, detail=f"Report #{report_id} not found")
    return report


@router.get("/stats")
def get_stats():
    return fetch_stats()


@router.post("/reset")
def reset_database():
    clear_all_reports()
    return {"message": "Database cleared."}
