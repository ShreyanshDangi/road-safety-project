# shared/database.py

import os
import psycopg2
import psycopg2.pool
import psycopg2.extras
from contextlib import contextmanager
from dotenv import load_dotenv
import logging

load_dotenv()
logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL")

# ─── Connection pool ──────────────────────────────────────────────────────────
# Created once when module is imported — not on every request
# min=1 keeps one connection alive, max=10 handles concurrent requests
_pool: psycopg2.pool.ThreadedConnectionPool = None


def _get_pool() -> psycopg2.pool.ThreadedConnectionPool:
    global _pool
    if _pool is None or _pool.closed:
        _pool = psycopg2.pool.ThreadedConnectionPool(
            minconn=1,
            maxconn=10,
            dsn=DATABASE_URL,
        )
        logger.info("[database] Connection pool initialised")
    return _pool


@contextmanager
def get_db():
    """
    Context manager — borrows a connection from the pool,
    commits on success, rolls back on any exception,
    always returns connection to pool.

    Usage:
        with get_db() as (conn, cur):
            cur.execute("SELECT * FROM complaints WHERE complaint_id = %s", (id,))
            row = cur.fetchone()   # comes back as a dict
    """
    pool = _get_pool()
    conn = pool.getconn()
    # RealDictCursor returns rows as dicts instead of tuples
    cur  = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        yield conn, cur
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        pool.putconn(conn)


# ─── Query helpers ────────────────────────────────────────────────────────────
# One function per table operation.
# All SQL lives here — nothing in main.py writes raw SQL.

def insert_complaint(data: dict) -> str:
    """
    Inserts one row into complaints table.
    Returns the generated complaint_id (UUID string).
    """
    with get_db() as (conn, cur):
        cur.execute("""
            INSERT INTO complaints (
                lat, lon, gps_source, gps_trust_score,
                recommendation, flags,
                address, road_name, road_type, road_type_source,
                city, state,
                image_url, damage_note
            ) VALUES (
                %(lat)s, %(lon)s, %(gps_source)s, %(gps_trust_score)s,
                %(recommendation)s, %(flags)s,
                %(address)s, %(road_name)s, %(road_type)s, %(road_type_source)s,
                %(city)s, %(state)s,
                %(image_url)s, %(damage_note)s
            )
            RETURNING complaint_id
        """, {
            "lat":              data["lat"],
            "lon":              data["lon"],
            "gps_source":       data["gps_source"],
            "gps_trust_score":  data["gps_trust_score"],
            "recommendation":   data["recommendation"],
            "flags":            psycopg2.extras.Json(data.get("flags", [])),
            "address":          data.get("address"),
            "road_name":        data.get("road_name"),
            "road_type":        data.get("road_type"),
            "road_type_source": data.get("road_type_source", "default"),
            "city":             data.get("city"),
            "state":            data.get("state"),
            "image_url":        data["image_url"],
            "damage_note":      data.get("damage_note"),
        })
        return str(cur.fetchone()["complaint_id"])


def insert_detection(complaint_id: str, data: dict):
    """Inserts Module 1 output into detections table."""
    with get_db() as (conn, cur):
        cur.execute("""
            INSERT INTO detections (
                complaint_id,
                damage_class, relative_bbox_area, cluster_count,
                confidence, has_pothole, total_detections, raw_detections
            ) VALUES (
                %(complaint_id)s,
                %(damage_class)s, %(relative_bbox_area)s, %(cluster_count)s,
                %(confidence)s, %(has_pothole)s, %(total_detections)s, %(raw_detections)s
            )
        """, {
            "complaint_id":      complaint_id,
            "damage_class":      data.get("damage_class"),
            "relative_bbox_area":data.get("relative_bbox_area", 0.0),
            "cluster_count":     data.get("cluster_count", 0),
            "confidence":        data.get("confidence", 0.0),
            "has_pothole":       data.get("has_pothole", False),
            "total_detections":  data.get("total_detections", 0),
            "raw_detections":    psycopg2.extras.Json(data.get("raw_detections", [])),
        })


def insert_duplicate_check(complaint_id: str, data: dict):
    """Inserts Module 2 output into duplicate_checks table."""
    with get_db() as (conn, cur):
        cur.execute("""
            INSERT INTO duplicate_checks (
                complaint_id, phash,
                is_duplicate, duplicate_of,
                hamming_dist, gps_dist_m
            ) VALUES (
                %(complaint_id)s, %(phash)s,
                %(is_duplicate)s, %(duplicate_of)s,
                %(hamming_dist)s, %(gps_dist_m)s
            )
        """, {
            "complaint_id": complaint_id,
            "phash":        data["phash"],
            "is_duplicate": data["is_duplicate"],
            "duplicate_of": data.get("duplicate_of"),   # None if not duplicate
            "hamming_dist": data.get("hamming_dist"),
            "gps_dist_m":   data.get("gps_dist_m"),
        })


def insert_routing(complaint_id: str, data: dict):
    """Inserts Module 3 output into routing table."""
    with get_db() as (conn, cur):
        cur.execute("""
            INSERT INTO routing (
                complaint_id,
                priority, authority, sla_days, shap_reason,
                status
            ) VALUES (
                %(complaint_id)s,
                %(priority)s, %(authority)s, %(sla_days)s, %(shap_reason)s,
                'PENDING'
            )
        """, {
            "complaint_id": complaint_id,
            "priority":     data["priority"],
            "authority":    data["authority"],
            "sla_days":     data["sla_days"],
            "shap_reason":  data.get("shap_reason"),
        })


def insert_repair(complaint_id: str, data: dict) -> str:
    """Inserts Module 4 output into repairs table. Returns repair_id."""
    with get_db() as (conn, cur):
        cur.execute("""
            INSERT INTO repairs (
                complaint_id, after_image_url,
                verdict, confidence_level, reason,
                ssim_score, potholes_detected,
                gps_distance_m, gps_valid, gps_note
            ) VALUES (
                %(complaint_id)s, %(after_image_url)s,
                %(verdict)s, %(confidence_level)s, %(reason)s,
                %(ssim_score)s, %(potholes_detected)s,
                %(gps_distance_m)s, %(gps_valid)s, %(gps_note)s
            )
            RETURNING repair_id
        """, {
            "complaint_id":    complaint_id,
            "after_image_url": data["after_image_url"],
            "verdict":         data["verdict"],
            "confidence_level":data.get("confidence"),
            "reason":          data.get("reason"),
            "ssim_score":      data.get("ssim_score"),
            "potholes_detected":data.get("potholes_detected"),
            "gps_distance_m":  data.get("gps_distance_m"),
            "gps_valid":       data.get("gps_valid"),
            "gps_note":        data.get("gps_note"),
        })
        return str(cur.fetchone()["repair_id"])


def update_routing_status(complaint_id: str, status: str):
    """Updates complaint lifecycle status. Called by Module 4 after verification."""
    valid = {"PENDING", "IN_PROGRESS", "RESOLVED", "FLAGGED", "REJECTED"}
    if status not in valid:
        raise ValueError(f"Invalid status: {status}")
    with get_db() as (conn, cur):
        cur.execute("""
            UPDATE routing
            SET    status = %s,
                   status_updated_at = NOW()
            WHERE  complaint_id = %s
        """, (status, complaint_id))


def get_complaint(complaint_id: str) -> dict | None:
    """
    Fetches full complaint detail — used by citizen status tracker
    and Module 4 (to get before_image_url).
    """
    with get_db() as (conn, cur):
        cur.execute("""
            SELECT
                c.complaint_id, c.submitted_at,
                c.lat, c.lon, c.gps_source, c.gps_trust_score,
                c.address, c.road_type, c.city, c.state,
                c.image_url, c.flags, c.recommendation,
                d.damage_class, d.confidence, d.cluster_count,
                d.has_pothole, d.relative_bbox_area,
                r.priority, r.authority, r.sla_days,
                r.shap_reason, r.status,
                dc.is_duplicate, dc.duplicate_of
            FROM       complaints      c
            LEFT JOIN  detections      d  ON d.complaint_id = c.complaint_id
            LEFT JOIN  routing         r  ON r.complaint_id = c.complaint_id
            LEFT JOIN  duplicate_checks dc ON dc.complaint_id = c.complaint_id
            WHERE c.complaint_id = %s
        """, (complaint_id,))
        row = cur.fetchone()
        return dict(row) if row else None


def get_all_genuine_complaints() -> list[dict]:
    """
    Returns all non-duplicate complaints with routing info.
    Used by Module 5 dashboard map and Module 2 duplicate check.
    """
    with get_db() as (conn, cur):
        cur.execute("""
            SELECT
                c.complaint_id, c.lat, c.lon,
                c.image_url, c.address, c.city,
                c.submitted_at,
                d.damage_class, d.confidence, d.has_pothole,
                r.priority, r.authority, r.sla_days, r.status
            FROM       complaints       c
            LEFT JOIN  detections       d  ON d.complaint_id = c.complaint_id
            LEFT JOIN  routing          r  ON r.complaint_id = c.complaint_id
            INNER JOIN duplicate_checks dc ON dc.complaint_id = c.complaint_id
            WHERE dc.is_duplicate = FALSE
            ORDER BY c.submitted_at DESC
        """)
        return [dict(row) for row in cur.fetchall()]


def get_dashboard_stats() -> dict:
    with get_db() as (conn, cur):
        cur.execute("""
            SELECT
                COUNT(*)                                           AS total,
                COUNT(*) FILTER (WHERE r.status = 'PENDING')      AS pending,
                COUNT(*) FILTER (WHERE r.status = 'RESOLVED')     AS resolved,
                COUNT(*) FILTER (WHERE r.status = 'FLAGGED')      AS flagged,
                COUNT(*) FILTER (WHERE r.status = 'IN_PROGRESS')  AS in_progress,
                COUNT(*) FILTER (WHERE r.priority = 'HIGH')       AS high_priority,
                COUNT(*) FILTER (WHERE r.priority = 'MEDIUM')     AS medium_priority,
                COUNT(*) FILTER (WHERE r.priority = 'LOW')        AS low_priority,
                AVG(d.confidence)                                  AS avg_confidence
            FROM       routing          r
            INNER JOIN duplicate_checks dc ON dc.complaint_id = r.complaint_id
            LEFT JOIN  detections       d  ON d.complaint_id = r.complaint_id
            WHERE dc.is_duplicate = FALSE
        """)
        row = dict(cur.fetchone())
        total = int(row["total"] or 0)

        return {
            # Flat fields — used by main.py dashboard endpoints
            "total":       total,
            "pending":     int(row["pending"]     or 0),
            "resolved":    int(row["resolved"]    or 0),
            "flagged":     int(row["flagged"]     or 0),
            "in_progress": int(row["in_progress"] or 0),

            # Fields Module 5 frontend expects
            "total_complaints": total,
            "severity": {
                "high":   int(row["high_priority"]   or 0),
                "medium": int(row["medium_priority"] or 0),
                "low":    int(row["low_priority"]    or 0),
            },
            "status": {
                "open":     int(row["pending"]  or 0),
                "verified": int(row["resolved"] or 0),
            },
            "avg_ai_score": float(row["avg_confidence"] or 0.0),
        }


def get_all_phashes() -> list[dict]:
    """
    Returns all phashes with their GPS coordinates.
    Used by Module 2 duplicate checker to scan existing reports.
    """
    with get_db() as (conn, cur):
        cur.execute("""
            SELECT
                dc.complaint_id,
                dc.phash,
                c.lat,
                c.lon
            FROM duplicate_checks dc
            JOIN complaints       c ON c.complaint_id = dc.complaint_id
            WHERE dc.is_duplicate = FALSE
        """)
        return [dict(row) for row in cur.fetchall()]
    
def fetch_genuine_reports() -> list[dict]:
    """
    Returns all non-duplicate reports for Module 2 duplicate comparison.
    Field names match what duplicate.py expects: id, phash, latitude, longitude.
    """
    with get_db() as (conn, cur):
        cur.execute("""
            SELECT
                c.complaint_id  AS id,
                dc.phash        AS phash,
                c.lat           AS latitude,
                c.lon           AS longitude
            FROM duplicate_checks dc
            JOIN complaints       c ON c.complaint_id = dc.complaint_id
            WHERE dc.is_duplicate = FALSE
        """)
        return [dict(row) for row in cur.fetchall()]


def insert_report(
    complaint_id: str,
    phash:        str,
    is_duplicate: bool,
    image_url:    str   = None,
    latitude:     float = None,
    longitude:    float = None,
    damage_class: str   = None,
    duplicate_of: str   = None,
    hamming_dist: int   = None,
    gps_dist_m:   float = None,
) -> str:
    with get_db() as (conn, cur):
        cur.execute("""
            INSERT INTO duplicate_checks (
                complaint_id, phash,
                is_duplicate, duplicate_of,
                hamming_dist, gps_dist_m
            ) VALUES (
                %(complaint_id)s, %(phash)s,
                %(is_duplicate)s, %(duplicate_of)s,
                %(hamming_dist)s, %(gps_dist_m)s
            )
        """, {
            "complaint_id": complaint_id,
            "phash":        phash,
            "is_duplicate": bool(is_duplicate),
            "duplicate_of": str(duplicate_of) if duplicate_of is not None else None,
            "hamming_dist": int(hamming_dist) if hamming_dist is not None else None,
            "gps_dist_m":   float(gps_dist_m) if gps_dist_m is not None else None,
        })
    return complaint_id