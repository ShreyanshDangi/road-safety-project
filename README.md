<div align="center">

# Road Safety Infrastructure Management System

### An end-to-end AI pipeline that transforms a citizen's pothole photo into a government work order — automatically.

[![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=flat&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.136-009688?style=flat&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18-61DAFB?style=flat&logo=react&logoColor=black)](https://reactjs.org)
[![YOLOv8](https://img.shields.io/badge/YOLOv8-Ultralytics-FF6B00?style=flat)](https://ultralytics.com)
[![HuggingFace](https://img.shields.io/badge/HuggingFace-Spaces-FFD21E?style=flat&logo=huggingface&logoColor=black)](https://huggingface.co/spaces/Aayush814/road-safety-project)
[![License](https://img.shields.io/badge/License-MIT-green?style=flat)](LICENSE)

**[🌐 Live Demo](https://aayush814-road-safety-project.hf.space)** &nbsp;|&nbsp;
**[📚 API Docs](https://aayush814-road-safety-project.hf.space/docs)** &nbsp;|&nbsp;
**[🗺️ Authority Dashboard](https://aayush814-road-safety-project.hf.space/authority)**

</div>

---

## What This Project Does

Road damage reporting in India is broken. Citizens photograph potholes, send them to WhatsApp groups, and nothing happens. Authorities have no structured intake, no prioritisation, and no verification that repairs were actually done.

This system automates the entire lifecycle:

```
Citizen photographs a pothole
        ↓
AI validates the image, extracts GPS, detects damage type
        ↓
Duplicate check prevents the same complaint being filed twice
        ↓
Smart Router assigns the right government authority, priority, and deadline
        ↓
Authority views complaints on a geospatial heatmap dashboard
        ↓
Authority uploads a repair photo → AI verifies the repair happened
        ↓
Complaint closes. Citizen sees status updated in real time.
```

No manual triage. No lost complaints. No fake repair claims getting through.

---

## Live Demo

| Portal | Link | Access |
|---|---|---|
| Landing Page | https://aayush814-road-safety-project.hf.space | Public |
| API Documentation | https://aayush814-road-safety-project.hf.space/docs | Public |

**Authority dashboard demo credentials:**
```
Username: admin
Password: roadsafety2026
```

> **Note:** The project is hosted on Hugging Face Spaces (free tier, CPU-only). YOLO inference may take 5–15 seconds per submission on cold start. All data written during demos persists in the live Supabase database.

---

## Team

| Name | Institution | Contribution |
|---|---|---|
| **Aayush Deshmukh** | The LNM Institute of Information Technology, Jaipur | Module 1 (YOLOv8 fine-tuning), Module 0 (location pipeline), Module 3 (training priority based routers),  Database (PostgreSQL) and Deployment (Docker container on Hugging Face Spaces) |
| **Shreyansh Dangi** | The LNM Institute of Information Technology, Jaipur | Module 2 (duplicate detection), Module 4 (repair verification), Module 5 (real time geospatial dashboard)  |

---

## System Architecture

The system runs as a single consolidated FastAPI server that orchestrates six AI modules. All modules share one PostgreSQL database (Supabase) and one image store (Cloudinary).

```
┌─────────────────────────────────────────────────────────────────┐
│                        CITIZEN PORTAL                           │
│            citizen.html  ·  Browser GPS  ·  Photo Upload        │
└──────────────────────────────┬──────────────────────────────────┘
                               │ POST /complaint/submit
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                    FASTAPI  (port 7860 on HF)                   │
│                                                                 │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────┐     │
│  │ Module 0 │→ │ Module 1 │→ │ Module 2 │→ │   Module 3   │     │
│  │  GPS &   │  │  YOLOv8  │  │Duplicate │  │ Smart Router │     │
│  │ Location │  │ Detector │  │ Checker  │  │(Random Forest│     │
│  │          │  │          │  │          │  │   + SHAP)    │     │
│  └──────────┘  └──────────┘  └──────────┘  └──────────────┘     │
│                                                                 │
│  ┌────────────────────────┐  ┌──────────────────────────────┐   │
│  │       Module 4         │  │          Module 5            │   │
│  │   Repair Verifier      │  │   Authority Dashboard API    │   │
│  │ (SSIM + YOLO + GPS)    │  │   (DBSCAN + Aggregations)    │   │
│  └────────────────────────┘  └──────────────────────────────┘   │
└─────────────┬───────────────────────────────────┬───────────────┘
              │                                   │
              ▼                                   ▼
     ┌─────────────────┐               ┌──────────────────┐
     │   PostgreSQL    │               │    Cloudinary    │
     │   (Supabase)    │               │  (Image Store)   │
     │  5-table schema │               │  complaints/     │
     └─────────────────┘               │  repairs/        │
                                       └──────────────────┘
```

---

## Module Breakdown

### Module 0 — Ingestion & Location Pipeline

**What it does:** Validates that a submitted image is a genuine, geolocated report from an actual road — before any ML model runs.

**Implementation:**

The pipeline runs five sequential validation steps:

1. **EXIF GPS Extraction** — Reads GPS coordinates embedded in the photo's metadata. Handles three real-world failure modes: no EXIF data (WhatsApp strips it), NaN GPS values (no satellite fix at capture), and zero-denominator rational numbers (camera encoding of missing fix).

2. **Timestamp Validation** — Checks `DateTimeOriginal` against server time. Photos older than 24 hours are flagged. A 14-hour future grace window absorbs IST-UTC timezone ambiguity without falsely rejecting fresh photos.

3. **GPS Cross-Validation** — Computes Haversine distance between EXIF GPS and browser-captured GPS. Agreement within 100m confirms location authenticity. Mismatch beyond 100m flags the report.

4. **Reverse Geocoding** — Calls Nominatim (OpenStreetMap) with the validated coordinates to confirm the location resolves to a real Indian road address. Extracts road type from OSM tags when available.

5. **Trust Scoring** — Aggregates all flags into a score from 0.0–1.0 using a weighted deduction model:
   - EXIF GPS present, no issues → 1.0
   - Browser GPS only → −0.15
   - GPS mismatch → −0.25
   - Old timestamp → −0.20
   - Invalid location → −0.40

   Scores below 0.45 are rejected. This prevents fabricated reports with no verifiable location from entering the system.

---

### Module 1 — Road Damage Detector (YOLOv8n)

**What it does:** Runs computer vision on the submitted photo to detect road damage type, count instances, and measure coverage area.

**Model:** YOLOv8n fine-tuned on RDD2022 (Road Damage Dataset 2022) — a combined multi-country dataset of 32,000+ annotated road survey images from India, Japan, Czech Republic, and Norway.

**Training setup:**
- Hardware: Kaggle Tesla T4 GPU
- Duration: 50 epochs · 6.5 hours
- Input resolution: 640×640
- Architecture: 73 layers · 3,006,428 parameters · 8.1 GFLOPs
- Class weighting: Pothole detection errors penalised more heavily during training (pothole is the most safety-critical and most underrepresented class)

**Validation results (best.pt on 5,757 held-out images):**

| Class | Precision | Recall | mAP50 | mAP50-95 |
|---|---|---|---|---|
| **Overall** | 0.595 | 0.522 | **0.549** | 0.283 |
| Longitudinal crack | 0.569 | 0.529 | 0.541 | 0.299 |
| Transverse crack | 0.578 | 0.538 | 0.558 | 0.281 |
| Alligator cracking | 0.640 | 0.621 | **0.650** | 0.354 |
| Pothole | 0.596 | 0.401 | 0.447 | 0.198 |

**Inference speed:** 5.9ms per image (GPU) · ~80–120ms on CPU (production)

**Design decision — Module 1 observes, Module 3 judges.** Module 1 reports only physical facts: damage class, bounding box area, detection count, confidence. It does not assign severity or priority. That responsibility belongs to Module 3, which has road context. This separation means the vision model and routing model can be retrained independently.

**Output per image:**
```json
{
  "damage_class": "Pothole",
  "relative_bbox_area": 0.034,
  "cluster_count": 3,
  "confidence": 0.71,
  "has_pothole": true,
  "total_detections": 3,
  "raw_detections": [...]
}
```

---

### Module 2 — Duplicate & Fraud Checker

**What it does:** Prevents the same complaint from entering the system twice — whether submitted by the same citizen or different citizens photographing the same damage.

**Built by:** Shreyansh Dangi

**Implementation:** Dual-signal verification. Both signals must fire simultaneously for a complaint to be flagged as a duplicate. Neither alone is sufficient.

**Signal 1 — Visual similarity (pHash):**
The image is converted to greyscale, resized to 32×32, and a 64-bit perceptual hash is computed using a Discrete Cosine Transform. Hamming distance ≤ 10 bits between two hashes indicates visual similarity.

**Signal 2 — Geographic proximity (Haversine):**
Haversine formula computes surface distance between complaint GPS coordinates. Distance ≤ 50 metres indicates the same physical location.

**Why both signals are required:** Two photos at the same GPS but looking completely different are not duplicates — one may be before repair, one after. Two visually identical photos 200 metres apart are not duplicates — they are genuinely separate damage sites.

When both signals fire, a row is written to the `duplicate_checks` table with `is_duplicate=true` and `duplicate_of` pointing to the original complaint UUID. The duplicate complaint is stored for audit purposes but receives no routing row and never enters the authority queue.

---

### Module 3 — Smart Priority Router

**What it does:** Takes the raw physical facts from Module 1 and the road context from Module 0, and produces a fully structured complaint ticket with the correct government authority, priority level, SLA deadline, and a human-readable explanation of the routing decision.

**Why this module exists:** Not all road damage is equally urgent. A small longitudinal crack on a rural road and a pothole cluster on a national highway both need fixing — but they need different authorities, different response times, and different resource allocation. This module encodes that domain knowledge systematically.

#### Priority Classification — Random Forest

**Training data:** 10,000 records generated from a domain-knowledge-driven synthetic dataset. Ground-truth labels are assigned by a deterministic scoring formula:

```
hazard = w_damage × (1 + relative_bbox_area)
impact = w_road × (1 + 0.15 × cluster_count)
score  = hazard × impact

score ≥ 22  →  HIGH
score ≥ 10  →  MEDIUM
score  < 10 →  LOW
```

**Domain weights baked into the formula:**

| Damage Type | Weight | Road Type | Weight |
|---|---|---|---|
| Pothole | 4.0 | National Highway | 6.0 |
| Alligator | 3.0 | State Highway | 5.0 |
| Transverse | 1.5 | Major District Road | 3.0 |
| Longitudinal | 1.0 | City Road | 2.0 |
| | | Rural Road | 1.0 |

*Example: Pothole on NH scores 4.0 × 6.0 = 24.0 base — already above the HIGH threshold before bbox or cluster multipliers.*

**Sensor noise injection:** To make the model robust to real-world sensor failures, features (not labels) are corrupted during training:
- YOLO misclassifies damage type 15% of the time (based on known YOLOv8 confusion patterns)
- Camera occlusion shrinks bounding box area 20% of the time
- GPS drift causes wrong road type assignment 10% of the time

The model learns to recover correct priority even when upstream inputs are noisy.

**Model configuration:**
```python
Pipeline([
    ('preprocessor', ColumnTransformer([
        ('ohe', OneHotEncoder(handle_unknown='ignore'), ['damage_class', 'road_type']),
        ('passthrough', 'passthrough', numerical_features)
    ])),
    ('classifier', RandomForestClassifier(
        n_estimators=150,
        max_depth=8,
        min_samples_split=10,
        class_weight='balanced',
        random_state=42
    ))
])
```

**Results on 2,000 held-out test rows:**

| Metric | Value |
|---|---|
| Overall Accuracy | **92%** |
| CV Macro F1 (5-fold stratified) | **0.918 ± 0.007** |
| LOW class F1 | 0.93 |
| MEDIUM class F1 | 0.90 |
| HIGH class F1 | 0.92 |

**Critical error profile:**

| Error Type | Count | Rate |
|---|---|---|
| LOW predicted as HIGH | **0** | 0% |
| HIGH predicted as LOW | **3 / 292** | **1%** |
| All other errors | Adjacent class only | — |

The model never escalates a low-priority complaint to HIGH. The three HIGH→LOW misses all occur in the inherently ambiguous boundary zone. No catastrophic misclassifications.

**Top 5 features by importance:**

| Feature | Importance |
|---|---|
| road_type_national_highway | 0.130 |
| road_type_city_road | 0.115 |
| road_type_state_highway | 0.114 |
| damage_class_longitudinal | 0.108 |
| damage_class_pothole | 0.104 |

Road type dominates — correctly reflecting that traffic volume and vehicle speed matter more than crack pattern for real-world urgency.

#### Authority Routing — Rule-Based (No ML)

Jurisdiction is a legal fact, not a statistical probability. Authority assignment is a deterministic lookup:

```python
AUTHORITY_MAP = {
    "national_highway":    "NHAI",
    "state_highway":       "PWD",
    "major_district_road": "PWD",
    "city_road":           "Municipal",
    "rural_road":          "Panchayat"
}
```

**SLA table (authority × priority):**

| Authority | HIGH | MEDIUM | LOW |
|---|---|---|---|
| NHAI | 3 days | 7 days | 14 days |
| PWD | 5 days | 10 days | 21 days |
| Municipal | 7 days | 14 days | 30 days |
| Panchayat | 14 days | 30 days | 60 days |

#### SHAP Explainability

Every routing decision includes a human-readable reason string generated by SHAP's `TreeExplainer`. The top two features by absolute SHAP value for the predicted class are translated into domain language:

> *"Prioritized due to acute blowout risk (Pothole) compounding with high-speed kinetic vulnerability (National Highway)."*

This explanation is stored in the database and displayed to both the authority and the citizen.

**Artifacts:** `priority_router_pipeline.pkl` · `target_map.pkl`

---

### Module 4 — Repair Verifier

**What it does:** When an authority submits an after-repair photo, this module verifies that the repair actually happened using three independent checks that must reach consensus.

**Built by:** Shreyansh Dangi

**The fraud problem this solves:** Without verification, contractors could submit the original before-photo as the after-photo and close complaints without doing any work. Module 4 makes this impossible.

**Three-factor verification:**

1. **GPS Check** — The after-photo's GPS must be within 30 metres of the original complaint coordinates. This prevents contractors from photographing a different, already-repaired road elsewhere in the city.

2. **SSIM Comparison** — Structural Similarity Index Measure compares before and after images:
   - SSIM < 0.65 → surface has changed significantly → consistent with repair
   - SSIM > 0.85 → images are nearly identical → suspicious (possible photo reuse)

3. **YOLO Re-inference** — The same YOLOv8 weights from Module 1 run on the after-image. Zero damage detections above confidence threshold → semantic confirmation that the road is repaired.

**Four possible verdicts:**

| Verdict | Meaning | Status Update |
|---|---|---|
| `REPAIRED` | Surface changed + no damage detected | RESOLVED |
| `NOT_REPAIRED` | Surface unchanged + damage still visible | PENDING |
| `SUSPICIOUS` | GPS mismatch or images too similar | FLAGGED |
| `INCONCLUSIVE` | Surface changed but damage still detectable | FLAGGED |

**Security design:** Module 4 fetches the before-image directly from the database using the `complaint_id`, rather than accepting it as an upload. This prevents a fraud vector where a contractor could supply a manipulated before-image to make a poor repair look verified.

---

### Module 5 — Authority Dashboard

**What it does:** A real-time geospatial dashboard that transforms raw complaint data from Modules 1–4 into actionable civic intelligence for government authorities.

**Built by:** Shreyansh Dangi (frontend) · Aayush Deshmukh (backend integration & deployment)

**What authorities see:**

- **Interactive Leaflet.js map** — Every complaint as a priority-coloured pin. DBSCAN clusters complaints into hotspot circles sized by density. Authorities immediately see which roads have the most damage concentration.
- **5 metric cards** — Total complaints · High priority count · Open/Pending · Verified resolved · Average AI confidence score
- **Complaint list** — Scrollable, filterable list with damage class, AI confidence, authority assignment, priority, status, and SHAP reason string
- **Filters** — Severity · Authority · Status · DBSCAN radius slider (10–500m) · Exclude duplicates toggle
- **30-day trend chart** — Daily complaint volume, useful for spotting monsoon-season spikes
- **Cluster summary table** — Per-cluster: complaint count, dominant damage type, authority assignment, SLA breach flag
- **CSV export** — Any filtered view downloadable for offline reporting
- **Repair submission panel** — Click any complaint → view before-image → upload after-image → Module 4 runs → verdict displayed inline

**DBSCAN clustering design:**
DBSCAN was chosen over K-Means because the number of damage hotspots in a city is unknown in advance. DBSCAN discovers clusters automatically and marks isolated complaints as noise. K-Means would force every complaint into a cluster, distorting the map. The radius parameter (epsilon in metres) is adjustable via dashboard slider.

**Tech stack (Module 5):**

| Layer | Technology | Why |
|---|---|---|
| UI framework | React 18 + Vite | Near-instant HMR, component-based state |
| Styling | Tailwind CSS | Consistent design system, no CSS files |
| Map | Leaflet.js + React-Leaflet | Zero API key, free OpenStreetMap tiles |
| Charts | Recharts | React-native charts, re-render with state |
| Clustering | scikit-learn DBSCAN | Haversine metric, no k required |
| Auth | JWT (python-jose) | 8-hour tokens, Bearer header |

---

## Complete Tech Stack

### Backend
| Technology | Purpose |
|---|---|
| FastAPI (Python 3.11) | Central API server — all six modules as routers |
| psycopg2 + ThreadedConnectionPool | PostgreSQL connection pooling |
| Ultralytics YOLOv8 | Object detection (Module 1 and 4) |
| scikit-learn 1.6.1 | Random Forest pipeline, DBSCAN clustering |
| SHAP (TreeExplainer) | Model explainability for routing decisions |
| scikit-image (SSIM) | Repair verification image comparison |
| Cloudinary SDK | Image upload and retrieval |
| python-jose | JWT token creation and verification |
| python-dotenv | Environment variable management |

### Frontend
| Technology | Purpose |
|---|---|
| React 18 + Vite | Authority dashboard SPA |
| Tailwind CSS | Utility-first styling |
| Leaflet.js + React-Leaflet | Interactive complaint map |
| Recharts | Trend and analytics charts |
| Vanilla HTML/JS | Citizen portal (no framework — minimal dependency) |

### Infrastructure
| Technology | Purpose |
|---|---|
| PostgreSQL (Supabase) | Primary database — all structured data |
| Cloudinary | Persistent image storage (complaints + repairs) |
| Hugging Face Spaces (Docker) | Production hosting |
| Git LFS | Large model file versioning (best.pt) |

---

## Database Schema

Five tables with UUID primary keys and JSONB for flexible fields:

```
complaints          → GPS, trust score, image URL, address, road type, flags
     │
     ├── detections → damage class, bbox area, cluster count, confidence, raw YOLO output (JSONB)
     │
     ├── duplicate_checks → pHash, is_duplicate, duplicate_of (FK), Hamming distance, GPS distance
     │
     ├── routing    → priority, authority, SLA days, SHAP reason, status (lifecycle)
     │
     └── repairs    → after image URL, verdict, SSIM score, potholes detected, GPS distance
```

Status lifecycle in `routing`:
```
PENDING → IN_PROGRESS → RESOLVED
              ↓
           FLAGGED  (suspicious repair or manual review)
              ↓
           REJECTED (duplicate confirmed or invalid)
```

---

## ML Implementation Highlights

This section summarises the machine learning decisions for technical reviewers.

**1. Domain-specific loss weighting in YOLO training**
Pothole is the most safety-critical class and the most underrepresented in RDD2022 (1,005 validation instances vs. 3,933 for Longitudinal). Training used inverse-frequency class weights to penalise missed pothole detections more heavily than missed cracks. This improved pothole recall from baseline without sacrificing precision on other classes.

**2. Feature noise injection for robustness (Module 3)**
Rather than training a clean classifier on clean data, we deliberately corrupted input features to simulate the three most common real-world sensor failures. The model learns to route correctly even when YOLO misclassifies, bounding boxes are occluded, or GPS drifts to a wrong road type. This is why the model achieves 92% accuracy on test data that includes the same noise patterns.

**3. Separation of observation and judgment**
Module 1 (YOLO) is restricted to reporting physical facts — geometry and class. Priority assignment lives entirely in Module 3, which has road context. This means either model can be retrained or swapped without affecting the other. When better YOLO weights become available, Module 3 retraining is not required.

**4. Rule-based routing as a deliberate architecture choice**
Authority assignment in Module 3 is a deterministic dictionary lookup, not a learned classifier. This was an intentional decision: jurisdiction is a legal boundary, not a statistical pattern. A model that routes NH-48 complaints to Municipal instead of NHAI 3% of the time is not acceptable. Deterministic code eliminates that error class entirely.

**5. SHAP for operational transparency**
Government systems need to justify their decisions. Every complaint ticket includes a SHAP-generated reason string that explains the top two factors driving the priority classification. This makes the system auditable — authorities can understand and challenge individual routing decisions.

**6. Dual-signal duplicate detection**
Using either pHash or GPS alone produces false positives. pHash alone would merge before-repair and after-repair photos of the same location. GPS alone would merge separate damage sites on the same street. Requiring both signals to fire simultaneously eliminates both failure modes.

**7. Three-factor repair verification**
SSIM alone can be fooled by compression artefacts. YOLO alone would flag an incomplete repair as done if the pothole is off-camera. GPS alone can be spoofed. The conjunction of all three — surface change confirmed by SSIM, damage absence confirmed by YOLO, proximity confirmed by GPS — makes fraudulent repair claims statistically infeasible.

---

## API Reference

Full interactive documentation available at: **https://aayush814-road-safety-project.hf.space/docs**

Key endpoints:

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| `POST` | `/complaint/submit` | Public | Submit complaint (multipart form with image) |
| `GET` | `/complaint/{id}/status` | Public | Poll complaint status |
| `POST` | `/auth/login` | Public | Get JWT token |
| `GET` | `/auth/verify` | Bearer | Verify token validity |
| `GET` | `/api/stats` | Bearer | Dashboard aggregate metrics |
| `GET` | `/api/complaints` | Bearer | Filtered complaint list |
| `GET` | `/api/clusters` | Bearer | DBSCAN cluster results |
| `GET` | `/api/reports/{id}` | Bearer | Full complaint detail |
| `POST` | `/repair/submit` | Bearer | Submit after-repair photo |
| `GET` | `/api/export/csv` | Bearer | Download filtered complaints |

---

## Running Locally

### Prerequisites
- Python 3.11+
- Node.js 20+
- PostgreSQL database (or Supabase project)
- Cloudinary account

### Setup

```bash
# Clone the repository
git clone https://github.com/AayushDeshmukh9090/road-safety-project.git
cd road-safety-project

# Install Python dependencies
pip install -r requirements.txt

# Install and build frontend
cd Module_5/frontend
npm install
npm run build
cd ../..

# Configure environment
cp .env.example .env
# Edit .env with your credentials (see below)

# Start the server
uvicorn main:app --reload --port 8000
```

### Environment Variables

Create a `.env` file in the project root:

```env
DATABASE_URL=postgresql://postgres:PASSWORD@db.YOUR_REF.supabase.co:5432/postgres
CLOUDINARY_CLOUD_NAME=your_cloud_name
CLOUDINARY_API_KEY=your_api_key
CLOUDINARY_API_SECRET=your_api_secret
AUTHORITY_USERNAME=admin
AUTHORITY_PASSWORD=your_password
JWT_SECRET=your_jwt_secret_key
```

### Access

| Page | URL |
|---|---|
| Landing | http://localhost:8000 |
| Citizen Portal | http://localhost:8000/citizen |
| Authority Dashboard | http://localhost:8000/authority |
| API Docs | http://localhost:8000/docs |

---

## Project Structure

```
road-safety-project/
│
├── main.py                          # Central FastAPI app — all modules wired here
├── landing.html                     # Landing page
├── citizen.html                     # Citizen complaint portal
├── requirements.txt
├── Dockerfile                       # HF Spaces deployment
│
├── shared/
│   ├── database.py                  # PostgreSQL connection pool + all query functions
│   ├── storage.py                   # Cloudinary upload/fetch/delete
│   └── auth.py                      # JWT creation and verification
│
├── Module_0/                        # GPS validation + trust scoring
│   ├── exif_extractor.py
│   ├── gps_validator.py
│   ├── timestamp_validator.py
│   ├── reverse_geocoder.py
│   └── trust_scorer.py
│
├── Module_1/                        # YOLOv8 road damage detector
│   ├── detector.py
│   └── weights/
│       └── best.pt                  # Fine-tuned YOLOv8n weights (tracked via Git LFS)
│
├── Module_2/                        # Duplicate detection
│   └── duplicate_checker.py
│
├── Module_3/                        # Smart priority router
│   ├── generate_data.py             # Synthetic dataset generation
│   ├── train_router.py              # Random Forest training pipeline
│   ├── explainer.py                 # SHAP reason string generation
│   ├── router.py                    # Inference + authority routing
│   └── models/
│       ├── priority_router_pipeline.pkl
│       └── target_map.pkl
│
├── Module_4/                        # Repair verification
│   ├── api.py                       # FastAPI router
│   ├── verifier.py                  # Three-factor verification logic
│   ├── ssim_compare.py
│   ├── yolo_infer.py
│   └── gps_checker.py
│
├── Module_5/                        # Authority dashboard
│   ├── backend/
│   │   └── main.py                  # Dashboard API router (DBSCAN + aggregations)
│   └── frontend/
│       ├── src/
│       │   ├── App.jsx              # Dashboard SPA
│       │   └── main.jsx
│       ├── vite.config.js
│       └── package.json
│
└── migrations/
    └── init_schema.sql              # PostgreSQL schema
```

---

## Deployment

The project is deployed as a single Docker container on Hugging Face Spaces. The Dockerfile builds the React frontend during the image build phase and serves it as static files from FastAPI — no separate Node.js server required at runtime.

```dockerfile
FROM python:3.11
# Install Node.js, build React, install Python deps, start uvicorn on port 7860
```

All environment variables (database URL, API keys, auth credentials) are configured as Hugging Face Spaces secrets and injected at runtime — never committed to the repository.

Model files (`best.pt`, `.pkl`) are version-controlled via Git LFS.

---

## Acknowledgements

- [RDD2022 Dataset](https://github.com/sekilab/RoadDamageDetector) — Road Damage Dataset 2022 used for YOLO fine-tuning
- [Ultralytics YOLOv8](https://github.com/ultralytics/ultralytics) — Object detection framework
- [OpenStreetMap / Nominatim](https://nominatim.org) — Reverse geocoding
- [Supabase](https://supabase.com) — Managed PostgreSQL hosting
- [Cloudinary](https://cloudinary.com) — Image storage and delivery

---

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.

---

<div align="center">

Built at **The LNM Institute of Information Technology, Jaipur**

*Aayush Deshmukh · Shreyansh Dangi*

</div>
