# Module 4 — Repair Verifier

Verifies whether a reported road pothole has actually been repaired by comparing
**before** and **after** photos using three independent checks.

---

## How It Works

```
Before Photo  +  After Photo  +  Original GPS
        |
        ├─ [1] GPS Metadata Check     → Is after-photo from same location?
        ├─ [2] SSIM Comparison        → Did the surface actually change?
        └─ [3] YOLOv8 Re-inference   → Is a pothole still visible?
                |
                └─ VERDICT: REPAIRED / NOT_REPAIRED / SUSPICIOUS / INCONCLUSIVE
```

---

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Add Your Module 1 Model Weights

Copy your trained YOLOv8 weights from Module 1 into this folder:

```bash
cp /path/to/module1/runs/detect/train/weights/best.pt ./best.pt
```

---

## How to Run

### Option A — Command Line (Quick Test)

```bash
python verifier.py \
  --before path/to/before.jpg \
  --after  path/to/after.jpg \
  --lat    28.6139 \
  --lon    77.2090
```

**With extra options:**

```bash
python verifier.py \
  --before before.jpg \
  --after  after.jpg \
  --lat    28.6139 \
  --lon    77.2090 \
  --model  best.pt \
  --gps-thresh 30 \
  --conf   0.35 \
  --save-diff \
  --save-annotated \
  --json
```

| Flag              | Default  | Description                              |
|-------------------|----------|------------------------------------------|
| `--before`        | required | Path to before-repair image              |
| `--after`         | required | Path to after-repair image               |
| `--lat`           | required | Original complaint latitude              |
| `--lon`           | required | Original complaint longitude             |
| `--model`         | best.pt  | Path to YOLOv8 weights from Module 1     |
| `--gps-thresh`    | 30.0     | GPS distance threshold (meters)          |
| `--conf`          | 0.35     | YOLO detection confidence threshold      |
| `--save-diff`     | False    | Save SSIM difference heatmap image       |
| `--save-annotated`| False    | Save YOLO annotated after-image          |
| `--json`          | False    | Print result as JSON                     |

---

### Option B — FastAPI Server

```bash
uvicorn api:app --reload --port 8004
```

Then open: http://localhost:8004/docs

**Test with curl:**

```bash
curl -X POST http://localhost:8004/verify-repair \
  -F "before_image=@before.jpg" \
  -F "after_image=@after.jpg" \
  -F "original_lat=28.6139" \
  -F "original_lon=77.2090"
```

---

### Option C — Use as Python Module

```python
from verifier import verify_repair

result = verify_repair(
    before_path  = "before.jpg",
    after_path   = "after.jpg",
    original_gps = (28.6139, 77.2090),
    model_path   = "best.pt"
)

print(result["verdict"])     # REPAIRED / NOT_REPAIRED / SUSPICIOUS / INCONCLUSIVE
print(result["confidence"])  # HIGH / MEDIUM / LOW
print(result["reason"])      # Human-readable explanation
```

---

## Verdict Logic

| SSIM Score        | YOLO on After     | GPS       | Verdict         |
|-------------------|-------------------|-----------|-----------------|
| Low (changed)     | No pothole        | Valid     | ✅ REPAIRED     |
| High (unchanged)  | Pothole found     | Valid     | ❌ NOT_REPAIRED |
| Any               | Any               | Invalid   | ⚠️ SUSPICIOUS  |
| High (unchanged)  | No pothole        | Valid     | ⚠️ SUSPICIOUS  |
| Low (changed)     | Pothole found     | Valid     | ❓ INCONCLUSIVE |

---

## File Structure

```
module4_repair_verifier/
├── verifier.py        ← Main pipeline (start here)
├── gps_checker.py     ← EXIF GPS extraction & Haversine distance
├── ssim_compare.py    ← SSIM computation with lighting normalization
├── yolo_infer.py      ← Module 1 YOLOv8 pothole detection
├── decision.py        ← Verdict logic combining all 3 checks
├── api.py             ← FastAPI REST endpoint
├── requirements.txt   ← All Python dependencies
└── README.md          ← This file
```

---

## Connecting to Other Modules

- **Module 1** → Provides `best.pt` model weights used by `yolo_infer.py`
- **Module 2** → Provides original GPS coordinates stored with each complaint
- **Module 5** → Reads verdict from this module to update heatmap dashboard status

---

## Troubleshooting

| Problem | Solution |
|---|---|
| `best.pt not found` | Copy Module 1 weights into this folder |
| `No GPS EXIF` | GPS stripped by phone/app — pass coordinates manually |
| Low SSIM but pothole still found | Partial repair — flag for re-inspection |
| Wrong verdict on night photos | Lighting normalization (CLAHE) is applied but angle changes can affect SSIM |
