# Module_4/api.py — full replacement

import os
import sys
import shutil
import tempfile

from uuid import UUID
from fastapi import APIRouter, File, UploadFile, Form, HTTPException, Depends
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent))

from verifier import verify_repair
from shared.database import get_complaint, insert_repair, update_routing_status
from shared.storage  import upload_image, fetch_image_bytes
from shared.auth     import verify_token

router = APIRouter(prefix="/repair", tags=["repair"])

MODULE_1_WEIGHTS = str(
    Path(__file__).parent.parent / "Module_1" / "weights" / "best.pt"
)

VERDICT_TO_STATUS = {
    "REPAIRED":     "RESOLVED",
    "NOT_REPAIRED": "PENDING",
    "SUSPICIOUS":   "FLAGGED",
    "INCONCLUSIVE": "FLAGGED",
}

_bearer = HTTPBearer()

def require_auth(credentials: HTTPAuthorizationCredentials = Depends(_bearer)):
    if not verify_token(credentials.credentials):
        raise HTTPException(status_code=401, detail="Invalid or expired token")


@router.get("/health")
def health():
    return {"status": "ok", "module": "repair_verifier"}


@router.post("/submit", dependencies=[Depends(require_auth)])
async def submit_repair(
    complaint_id  : UUID       = Form(...),
    after_image   : UploadFile = File(...),
    repair_lat    : float      = Form(...),
    repair_lon    : float      = Form(...),
    gps_threshold : float      = Form(30.0),
    conf_threshold: float      = Form(0.35),
):
    complaint = get_complaint(str(complaint_id))
    if not complaint:
        raise HTTPException(status_code=404, detail=f"Complaint {complaint_id} not found")

    before_image_url = complaint["image_url"]
    original_gps     = (complaint["lat"], complaint["lon"])

    after_bytes = await after_image.read()
    try:
        after_image_url = upload_image(after_bytes, folder="repairs")
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=f"After-image upload failed: {e}")

    tmp_dir = tempfile.mkdtemp()
    try:
        before_path = os.path.join(tmp_dir, "before.jpg")
        try:
            before_bytes = fetch_image_bytes(before_image_url)
            with open(before_path, "wb") as f:
                f.write(before_bytes)
        except RuntimeError as e:
            raise HTTPException(status_code=502, detail=f"Before-image fetch failed: {e}")

        after_path = os.path.join(tmp_dir, "after.jpg")
        with open(after_path, "wb") as f:
            f.write(after_bytes)

        result = verify_repair(
            before_path    = before_path,
            after_path     = after_path,
            original_gps   = original_gps,
            model_path     = MODULE_1_WEIGHTS,
            gps_threshold  = gps_threshold,
            conf_threshold = conf_threshold,
        )
        result.pop("diff_image",  None)
        result.pop("raw_results", None)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Verification failed: {e}")
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)

    repair_id  = insert_repair(str(complaint_id), {
        "after_image_url":  after_image_url,
        "verdict":          result["verdict"],
        "confidence":       result.get("confidence"),
        "reason":           result.get("reason"),
        "ssim_score":       result.get("ssim_score"),
        "potholes_detected":result.get("potholes_detected"),
        "gps_distance_m":   result.get("gps_distance_m"),
        "gps_valid":        result.get("gps_valid"),
        "gps_note":         result.get("gps_note"),
    })

    new_status = VERDICT_TO_STATUS.get(result["verdict"], "FLAGGED")
    update_routing_status(str(complaint_id), new_status)

    return JSONResponse(content={
        **result,
        "complaint_id":    str(complaint_id),
        "repair_id":       repair_id,
        "after_image_url": after_image_url,
        "routing_status":  new_status,
    })