# Module_5/backend/main.py

import sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).parent.parent.parent / ".env")
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from shared.database import (
    get_dashboard_stats, get_all_genuine_complaints,
    get_complaint, update_routing_status,
)
from shared.auth import verify_token

from fastapi import APIRouter, Query, HTTPException, Form, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import StreamingResponse
from typing import Optional
import numpy as np
import pandas as pd
from sklearn.cluster import DBSCAN
import io

router = APIRouter(prefix="/api", tags=["dashboard"])

_bearer = HTTPBearer()

def require_auth(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer)
):
    if not verify_token(credentials.credentials):
        raise HTTPException(status_code=401, detail="Invalid or expired token")


def run_dbscan_clustering(df, eps_meters=50.0, min_samples=2):
    if df.empty:
        return {"clusters": [], "noise": []}

    coords  = df[["lat", "lon"]].values
    eps_rad = eps_meters / 6_371_000

    db = DBSCAN(
        eps=eps_rad, min_samples=min_samples,
        algorithm="ball_tree", metric="haversine",
    ).fit(np.radians(coords))

    df = df.copy()
    df["cluster_id"] = db.labels_

    clusters = []
    for cid in sorted(df["cluster_id"].unique()):
        if cid == -1:
            continue
        group   = df[df["cluster_id"] == cid]
        n       = len(group)
        density = "high" if n >= 5 else "medium" if n >= 3 else "low"
        clusters.append({
            "cluster_id":      int(cid),
            "count":           n,
            "density":         density,
            "centroid_lat":    float(group["lat"].mean()),
            "centroid_lon":    float(group["lon"].mean()),
            "priority_counts": group["priority"].value_counts().to_dict(),
            "authorities":     group["authority"].value_counts().to_dict(),
            "dominant_city":   group["city"].mode().iloc[0] if not group["city"].isna().all() else "",
            "statuses":        group["status"].value_counts().to_dict(),
            "members":         group["complaint_id"].tolist(),
        })

    noise = df[df["cluster_id"] == -1].to_dict(orient="records")
    return {"clusters": clusters, "noise": noise}


@router.get("/stats", dependencies=[Depends(require_auth)])
def get_stats():
    return get_dashboard_stats()


@router.get("/complaints", dependencies=[Depends(require_auth)])
def get_complaints(
    priority:           Optional[str] = Query(None),
    authority:          Optional[str] = Query(None),
    status:             Optional[str] = Query(None),
    exclude_duplicates: bool          = Query(True),
    date_from:          Optional[str] = Query(None),
    date_to:            Optional[str] = Query(None),
):
    data = get_all_genuine_complaints()
    if priority:  data = [d for d in data if d.get("priority")  == priority]
    if authority: data = [d for d in data if d.get("authority") == authority]
    if status:    data = [d for d in data if d.get("status")    == status]
    if date_from: data = [d for d in data if str(d.get("submitted_at", ""))[:10] >= date_from]
    if date_to:   data = [d for d in data if str(d.get("submitted_at", ""))[:10] <= date_to]
    return {"total": len(data), "complaints": data}


@router.get("/reports/{complaint_id}", dependencies=[Depends(require_auth)])
def get_report(complaint_id: str):
    c = get_complaint(complaint_id)
    if not c:
        raise HTTPException(status_code=404, detail="Complaint not found")
    return c


@router.post("/reports/{complaint_id}/verify", dependencies=[Depends(require_auth)])
def verify_report(complaint_id: str, status: str = Form(...)):
    valid = {"RESOLVED", "FLAGGED", "REJECTED", "IN_PROGRESS"}
    if status not in valid:
        raise HTTPException(status_code=422, detail=f"Invalid status: {valid}")
    update_routing_status(complaint_id, status)
    return {"complaint_id": complaint_id, "updated_status": status}


@router.get("/clusters", dependencies=[Depends(require_auth)])
def get_clusters(
    eps:       float         = Query(50.0),
    min_pts:   int           = Query(2),
    priority:  Optional[str] = Query(None),
    authority: Optional[str] = Query(None),
    status:    Optional[str] = Query(None),
):
    data = get_all_genuine_complaints()
    if priority:  data = [d for d in data if d.get("priority")  == priority]
    if authority: data = [d for d in data if d.get("authority") == authority]
    if status:    data = [d for d in data if d.get("status")    == status]
    if not data:
        return {"clusters": [], "noise": [], "params": {"eps": eps, "min_pts": min_pts}}
    df     = pd.DataFrame(data)
    result = run_dbscan_clustering(df, eps_meters=eps, min_samples=min_pts)
    result["params"] = {"eps": eps, "min_pts": min_pts, "total_input": len(data)}
    return result


@router.get("/heatmap-geojson", dependencies=[Depends(require_auth)])
def get_heatmap_geojson(
    eps:       float         = Query(50.0),
    authority: Optional[str] = Query(None),
    priority:  Optional[str] = Query(None),
):
    data = get_all_genuine_complaints()
    if authority: data = [d for d in data if d.get("authority") == authority]
    if priority:  data = [d for d in data if d.get("priority")  == priority]
    if not data:
        return {"type": "FeatureCollection", "features": []}
    df     = pd.DataFrame(data)
    result = run_dbscan_clustering(df, eps_meters=eps)
    features = []
    for cl in result["clusters"]:
        features.append({
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [cl["centroid_lon"], cl["centroid_lat"]]},
            "properties": {
                "cluster_id":      cl["cluster_id"],
                "count":           cl["count"],
                "density":         cl["density"],
                "dominant_city":   cl["dominant_city"],
                "priority_counts": cl["priority_counts"],
                "authorities":     cl["authorities"],
            },
        })
    for pt in result["noise"]:
        features.append({
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [pt.get("lon"), pt.get("lat")]},
            "properties": {**pt, "cluster_id": -1, "density": "isolated"},
        })
    return {"type": "FeatureCollection", "features": features}


@router.get("/export/csv", dependencies=[Depends(require_auth)])
def export_csv(
    priority:  Optional[str] = Query(None),
    authority: Optional[str] = Query(None),
    status:    Optional[str] = Query(None),
):
    data = get_all_genuine_complaints()
    if priority:  data = [d for d in data if d.get("priority")  == priority]
    if authority: data = [d for d in data if d.get("authority") == authority]
    if status:    data = [d for d in data if d.get("status")    == status]
    df  = pd.DataFrame(data)
    buf = io.StringIO()
    df.to_csv(buf, index=False)
    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=complaints.csv"},
    )