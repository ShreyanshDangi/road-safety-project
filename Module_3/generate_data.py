import numpy as np
import pandas as pd

np.random.seed(42)
N_SAMPLES = 10000

DAMAGE_WEIGHTS = {"Longitudinal": 1.0, "Transverse": 1.5, "Alligator": 3.0, "Pothole": 4.0}
ROAD_WEIGHTS = {"rural_road": 1.0, "city_road": 2.0, "major_district_road": 3.0, "state_highway": 5.0, "national_highway": 6.0}

ROAD_PROBS = [0.10, 0.50, 0.20, 0.10, 0.10] 
DAMAGE_PROBS = [0.15, 0.15, 0.30, 0.40]

def compute_ground_truth_priority(damage, road, bbox, clusters):
    """Calculates the absolute mathematical truth before any sensor errors occur."""
    w_damage = DAMAGE_WEIGHTS[damage]
    w_road = ROAD_WEIGHTS[road]
    
    hazard = w_damage * (1.0 + bbox)
    impact = w_road * (1.0 + (0.15 * clusters))
    score = hazard * impact
    
    if score >= 22.0: return "HIGH"
    elif score >= 10.0: return "MEDIUM"
    else: return "LOW"

def apply_real_world_corruption(row):
    """Simulates the failures of YOLOv8, Citizens, and GPS."""
    corrupted_row = row.copy()
    
    # 1. YOLOv8 Confusion Matrix Simulation (~15% error rate)
    if np.random.rand() < 0.15:
        if row["damage_class"] == "Pothole":
            # YOLO sees a cluster of potholes as just alligator cracking
            corrupted_row["damage_class"] = np.random.choice(["Alligator", "Transverse"], p=[0.8, 0.2])
        elif row["damage_class"] == "Alligator":
            # YOLO sees severe alligator cracking and just draws a box around a piece of it as a pothole
            corrupted_row["damage_class"] = "Pothole"
        elif row["damage_class"] in ["Longitudinal", "Transverse"]:
            # YOLO mixes up crack orientations
            corrupted_row["damage_class"] = np.random.choice(["Longitudinal", "Transverse"])
            
    # 2. Camera Angle / Occlusion Simulation (20% chance)
    if np.random.rand() < 0.20:
        # A parked car or shadow hides part of the damage, shrinking the bounding box
        corrupted_row["relative_bbox_area"] = float(np.clip(row["relative_bbox_area"] * np.random.uniform(0.4, 0.7), 0.01, 0.60))
        
    # 3. GPS Reverse-Geocoding / Human Error (10% chance)
    if np.random.rand() < 0.10:
        if row["road_type"] == "national_highway":
            corrupted_row["road_type"] = "state_highway" # GPS drifted off the highway to a service road
        elif row["road_type"] == "city_road":
            corrupted_row["road_type"] = "major_district_road"

    return corrupted_row

# ─── Generate Perfect Data ──────────────────────────────────────────────────
print(f"Generating {N_SAMPLES} records...")
records = []

for _ in range(N_SAMPLES):
    road_type = np.random.choice(list(ROAD_WEIGHTS.keys()), p=ROAD_PROBS)
    damage_class = np.random.choice(list(DAMAGE_WEIGHTS.keys()), p=DAMAGE_PROBS)
    bbox_area = float(np.clip(np.random.beta(a=2, b=10), 0.01, 0.60))
    cluster_count = int(np.clip(np.random.poisson(lam=2.5), 1, 15))
    
    true_priority = compute_ground_truth_priority(damage_class, road_type, bbox_area, cluster_count)
    
    records.append({
        "damage_class": damage_class,
        "road_type": road_type,
        "relative_bbox_area": round(bbox_area, 3),
        "cluster_count": cluster_count,
        "priority": true_priority # THIS IS THE PERFECT LABEL
    })

df_perfect = pd.DataFrame(records)

# ─── Corrupt the Features ───────────────────────────────────────────────────
print("Applying YOLOv8 and GPS corruption simulations...")
df_corrupted = df_perfect.apply(apply_real_world_corruption, axis=1)

df_corrupted.to_csv("/kaggle/working/data/noisy_smart_router_data.csv", index=False)
print("Dataset saved as 'noisy_smart_router_data.csv'")

# Calculate how many rows were actually altered
changed = (df_perfect['damage_class'] != df_corrupted['damage_class']).sum()
print(f"Total YOLO misclassifications injected: {changed} ({(changed/N_SAMPLES)*100:.1f}%)")