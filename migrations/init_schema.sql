-- migrations/init_schema.sql

-- Required for UUID generation
CREATE EXTENSION IF NOT EXISTS "pgcrypto";


-- ─────────────────────────────────────────────────────────────────────────────
-- TABLE 1: complaints
-- Source: Module 0 (GPS + trust) + Cloudinary (image_url)
-- One row per citizen submission, regardless of duplicate status
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE complaints (
    complaint_id        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    submitted_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- GPS coordinates (Module 0: gps_validator output)
    lat                 DOUBLE PRECISION NOT NULL,
    lon                 DOUBLE PRECISION NOT NULL,
    gps_source          TEXT NOT NULL,
    -- CHECK enforces only known source values
    CONSTRAINT chk_gps_source CHECK (
        gps_source IN ('exif', 'browser', 'exif_flagged')
    ),

    -- Trust (Module 0: trust_scorer output)
    gps_trust_score     NUMERIC(4,3) NOT NULL,
    recommendation      TEXT NOT NULL,
    CONSTRAINT chk_recommendation CHECK (
        recommendation IN ('ACCEPT', 'REVIEW', 'REJECT')
    ),
    flags               JSONB NOT NULL DEFAULT '[]',

    -- Location context (Module 0: reverse_geocoder output)
    address             TEXT,
    road_name           TEXT,
    road_type           TEXT,
    road_type_source    TEXT NOT NULL DEFAULT 'default',
    CONSTRAINT chk_road_type_source CHECK (
        road_type_source IN ('osm', 'user_form', 'default')
    ),
    city                TEXT,
    state               TEXT,

    -- Image (Cloudinary — set after upload)
    image_url           TEXT NOT NULL,

    -- Citizen form input
    damage_note         TEXT
);


-- ─────────────────────────────────────────────────────────────────────────────
-- TABLE 2: detections
-- Source: Module 1 (YOLOv8 inference)
-- One row per complaint — stores both summary and raw detections
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE detections (
    detection_id        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    complaint_id        UUID NOT NULL
                            REFERENCES complaints(complaint_id)
                            ON DELETE CASCADE,
    detected_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Summary fields (feed into Module 3)
    damage_class        TEXT,
    -- 'Pothole' | 'Longitudinal' | 'Transverse' | 'Alligator' | NULL (no detection)
    relative_bbox_area  NUMERIC(7,6),           -- 0.000000 to 1.000000
    cluster_count       INTEGER NOT NULL DEFAULT 0,
    confidence          NUMERIC(4,3),           -- primary detection confidence

    -- From notebook detect_damage output
    has_pothole         BOOLEAN NOT NULL DEFAULT FALSE,
    total_detections    INTEGER NOT NULL DEFAULT 0,

    -- Full raw detections array stored for audit and Module 4 reference
    -- Format: [{"class": str, "confidence": float, "bbox": [x1,y1,x2,y2], "severity": str}]
    raw_detections      JSONB NOT NULL DEFAULT '[]'
);


-- ─────────────────────────────────────────────────────────────────────────────
-- TABLE 3: duplicate_checks
-- Source: Module 2 (pHash + Haversine)
-- One row per complaint — even genuine reports get a row (is_duplicate=false)
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE duplicate_checks (
    check_id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    complaint_id        UUID NOT NULL
                            REFERENCES complaints(complaint_id)
                            ON DELETE CASCADE,
    checked_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- pHash for future comparisons
    phash               TEXT NOT NULL,

    -- Duplicate verdict
    is_duplicate        BOOLEAN NOT NULL DEFAULT FALSE,
    duplicate_of        UUID REFERENCES complaints(complaint_id),
    -- NULL when is_duplicate = false
    hamming_dist        INTEGER,
    gps_dist_m          DOUBLE PRECISION
);


-- ─────────────────────────────────────────────────────────────────────────────
-- TABLE 4: routing
-- Source: Module 3 (Random Forest classifier + SLA matrix)
-- Only created for genuine complaints (is_duplicate = false)
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE routing (
    routing_id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    complaint_id        UUID NOT NULL
                            REFERENCES complaints(complaint_id)
                            ON DELETE CASCADE,
    routed_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Module 3 core output
    priority            TEXT NOT NULL,
    CONSTRAINT chk_priority CHECK (priority IN ('LOW', 'MEDIUM', 'HIGH')),
    authority           TEXT NOT NULL,
    CONSTRAINT chk_authority CHECK (
        authority IN ('NHAI', 'PWD', 'Municipal', 'Panchayat')
    ),
    sla_days            INTEGER NOT NULL,
    shap_reason         TEXT,

    -- Complaint lifecycle — Module 5 reads and updates this
    status              TEXT NOT NULL DEFAULT 'PENDING',
    CONSTRAINT chk_status CHECK (
        status IN ('PENDING', 'IN_PROGRESS', 'RESOLVED', 'FLAGGED', 'REJECTED')
    ),
    status_updated_at   TIMESTAMPTZ,
    assigned_to         TEXT                    -- authority worker (future use)
);


-- ─────────────────────────────────────────────────────────────────────────────
-- TABLE 5: repairs
-- Source: Module 4 (YOLO + SSIM + GPS tri-factor)
-- One row per repair submission — a complaint may have multiple attempts
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE repairs (
    repair_id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    complaint_id        UUID NOT NULL
                            REFERENCES complaints(complaint_id)
                            ON DELETE CASCADE,
    submitted_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- After image (Cloudinary)
    after_image_url     TEXT NOT NULL,

    -- Module 4 decision.py output — column names match dict keys exactly
    verdict             TEXT NOT NULL,
    CONSTRAINT chk_verdict CHECK (
        verdict IN ('REPAIRED', 'REJECTED', 'MANUAL_REVIEW')
    ),
    confidence_level    TEXT,                   -- 'HIGH' | 'MEDIUM' | 'LOW'
    reason              TEXT,
    ssim_score          NUMERIC(6,4),
    potholes_detected   INTEGER,
    gps_distance_m      DOUBLE PRECISION,       -- NULL when no GPS in after-image
    gps_valid           BOOLEAN,                -- NULL when GPS unavailable
    gps_note            TEXT
);


-- ─────────────────────────────────────────────────────────────────────────────
-- INDEXES
-- Only on columns that will be queried frequently
-- ─────────────────────────────────────────────────────────────────────────────
-- Module 5 map: fetches all complaints by location
CREATE INDEX idx_complaints_location
    ON complaints (lat, lon);

-- Module 2: checks duplicates against existing pHashes
CREATE INDEX idx_phash
    ON duplicate_checks (phash);

-- Module 5 queue: authority filters by status
CREATE INDEX idx_routing_status
    ON routing (status);

-- Module 5 queue: authority filters by priority
CREATE INDEX idx_routing_priority
    ON routing (priority);

-- Module 5 map: filter genuine complaints only
CREATE INDEX idx_duplicate_genuine
    ON duplicate_checks (is_duplicate)
    WHERE is_duplicate = FALSE;