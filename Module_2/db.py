"""
db.py — SQLite Database Operations
All reports (genuine + duplicates) stored here.
"""

import sqlite3
import os

# DB file sits right next to this script — works on Windows flat structure
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "reports.db")


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS reports (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            image_path      TEXT    NOT NULL,
            phash           TEXT    NOT NULL,
            latitude        REAL    NOT NULL,
            longitude       REAL    NOT NULL,
            damage_type     TEXT    DEFAULT 'unknown',
            severity        TEXT    DEFAULT 'unknown',
            is_duplicate    INTEGER DEFAULT 0,
            duplicate_of    INTEGER DEFAULT NULL,
            hamming_dist    INTEGER DEFAULT NULL,
            gps_dist_m      REAL    DEFAULT NULL,
            created_at      TEXT    DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()


def insert_report(image_path, phash, latitude, longitude,
                  damage_type="unknown", severity="unknown",
                  is_duplicate=False, duplicate_of=None,
                  hamming_dist=None, gps_dist_m=None):
    conn = get_connection()
    cursor = conn.execute("""
        INSERT INTO reports
            (image_path, phash, latitude, longitude, damage_type, severity,
             is_duplicate, duplicate_of, hamming_dist, gps_dist_m)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (image_path, phash, latitude, longitude, damage_type, severity,
          int(is_duplicate), duplicate_of, hamming_dist, gps_dist_m))
    conn.commit()
    new_id = cursor.lastrowid
    conn.close()
    return new_id


def fetch_genuine_reports():
    conn = get_connection()
    cursor = conn.execute("""
        SELECT id, image_path, phash, latitude, longitude,
               damage_type, severity, created_at
        FROM reports
        WHERE is_duplicate = 0
        ORDER BY created_at DESC
    """)
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows


def fetch_all_reports():
    conn = get_connection()
    cursor = conn.execute("""
        SELECT r.*,
               orig.image_path as original_image_path
        FROM reports r
        LEFT JOIN reports orig ON r.duplicate_of = orig.id
        ORDER BY r.created_at DESC
    """)
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows


def fetch_report_by_id(report_id):
    conn = get_connection()
    cursor = conn.execute("SELECT * FROM reports WHERE id = ?", (report_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def fetch_stats():
    conn = get_connection()
    total     = conn.execute("SELECT COUNT(*) FROM reports").fetchone()[0]
    genuine   = conn.execute("SELECT COUNT(*) FROM reports WHERE is_duplicate = 0").fetchone()[0]
    duplicates = conn.execute("SELECT COUNT(*) FROM reports WHERE is_duplicate = 1").fetchone()[0]
    conn.close()
    return {
        "total_reports":    total,
        "genuine_reports":  genuine,
        "duplicate_reports": duplicates,
        "duplicate_rate_pct": round((duplicates / total * 100) if total > 0 else 0, 1)
    }


def clear_all_reports():
    conn = get_connection()
    conn.execute("DELETE FROM reports")
    conn.commit()
    conn.close()
