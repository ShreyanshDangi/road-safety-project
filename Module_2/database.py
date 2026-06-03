"""
shared/database.py — PostgreSQL Database Operations
Replaces the old SQLite db.py for the integrated system.

Expects the DATABASE_URL environment variable:
    DATABASE_URL=postgresql://user:password@host:5432/dbname

Changes vs the old db.py
  • PostgreSQL instead of SQLite
  • severity column removed entirely
  • damage_type  → damage_class
  • image_path   → image_url   (Cloudinary URL, set before Module 2 runs)
"""

import os
import psycopg2
import psycopg2.extras

DATABASE_URL = os.environ["DATABASE_URL"]


def get_connection():
    conn = psycopg2.connect(DATABASE_URL)
    return conn


def init_db():
    """
    Create the reports table if it does not already exist.
    Call once at application startup.
    """
    conn = get_connection()
    with conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS reports (
                    id              SERIAL PRIMARY KEY,
                    image_url       TEXT    NOT NULL,
                    phash           TEXT    NOT NULL,
                    latitude        DOUBLE PRECISION NOT NULL,
                    longitude       DOUBLE PRECISION NOT NULL,
                    damage_class    TEXT    DEFAULT 'unknown',
                    is_duplicate    BOOLEAN DEFAULT FALSE,
                    duplicate_of    INTEGER DEFAULT NULL,
                    hamming_dist    INTEGER DEFAULT NULL,
                    gps_dist_m      DOUBLE PRECISION DEFAULT NULL,
                    created_at      TIMESTAMPTZ DEFAULT NOW()
                )
            """)
    conn.close()


def insert_report(image_url, phash, latitude, longitude,
                  damage_class="unknown",
                  is_duplicate=False, duplicate_of=None,
                  hamming_dist=None, gps_dist_m=None):
    conn = get_connection()
    with conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO reports
                    (image_url, phash, latitude, longitude, damage_class,
                     is_duplicate, duplicate_of, hamming_dist, gps_dist_m)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (image_url, phash, latitude, longitude, damage_class,
                  is_duplicate, duplicate_of, hamming_dist, gps_dist_m))
            new_id = cur.fetchone()[0]
    conn.close()
    return new_id


def fetch_genuine_reports():
    conn = get_connection()
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute("""
            SELECT id, image_url, phash, latitude, longitude,
                   damage_class, created_at
            FROM reports
            WHERE is_duplicate = FALSE
            ORDER BY created_at DESC
        """)
        rows = [dict(row) for row in cur.fetchall()]
    conn.close()
    return rows


def fetch_all_reports():
    conn = get_connection()
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute("""
            SELECT r.*,
                   orig.image_url AS original_image_url
            FROM reports r
            LEFT JOIN reports orig ON r.duplicate_of = orig.id
            ORDER BY r.created_at DESC
        """)
        rows = [dict(row) for row in cur.fetchall()]
    conn.close()
    return rows


def fetch_report_by_id(report_id):
    conn = get_connection()
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute("SELECT * FROM reports WHERE id = %s", (report_id,))
        row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def fetch_stats():
    conn = get_connection()
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM reports")
        total = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM reports WHERE is_duplicate = FALSE")
        genuine = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM reports WHERE is_duplicate = TRUE")
        duplicates = cur.fetchone()[0]
    conn.close()
    return {
        "total_reports":     total,
        "genuine_reports":   genuine,
        "duplicate_reports": duplicates,
        "duplicate_rate_pct": round((duplicates / total * 100) if total > 0 else 0, 1),
    }


def clear_all_reports():
    conn = get_connection()
    with conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM reports")
    conn.close()

def fetch_genuine_reports() -> list[dict]:
    """
    Returns all non-duplicate reports for duplicate comparison.
    Module 2 iterates this list checking pHash + GPS against new submission.
    Returns field names matching Module 2's expected keys:
    id, phash, latitude, longitude
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
    image_url:    str   = None,   # kept for signature compatibility
    latitude:     float = None,   # already stored in complaints table
    longitude:    float = None,   # already stored in complaints table
    damage_class: str   = None,   # already stored in detections table
    duplicate_of: str   = None,
    hamming_dist: int   = None,
    gps_dist_m:   float = None,
) -> str:
    """
    Writes Module 2 verdict to duplicate_checks table.
    Complaint record already exists — created by orchestrator before Module 2 runs.
    Returns complaint_id so Module 2 can include it in its response dict.
    """
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
            "is_duplicate": is_duplicate,
            "duplicate_of": duplicate_of,
            "hamming_dist": hamming_dist,
            "gps_dist_m":   gps_dist_m,
        })
    return complaint_id   # Module 2 uses this as new_report_id in its response
