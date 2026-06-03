"""
gps_cluster.py — GPS Distance & Clustering
Haversine formula for accurate Earth-surface distance.
DBSCAN for clustering multiple nearby reports.
"""

import numpy as np
from sklearn.cluster import DBSCAN

EARTH_RADIUS_M = 6_371_000
DUPLICATE_RADIUS_M = 50
DBSCAN_RADIUS_RAD = DUPLICATE_RADIUS_M / EARTH_RADIUS_M


def haversine_distance(lat1, lng1, lat2, lng2):
    lat1_r, lat2_r = np.radians(lat1), np.radians(lat2)
    dlat = np.radians(lat2 - lat1)
    dlng = np.radians(lng2 - lng1)
    a = (np.sin(dlat / 2) ** 2
         + np.cos(lat1_r) * np.cos(lat2_r) * np.sin(dlng / 2) ** 2)
    return round(2 * EARTH_RADIUS_M * np.arcsin(np.sqrt(a)), 2)


def are_gps_within_radius(lat1, lng1, lat2, lng2, radius_m=DUPLICATE_RADIUS_M):
    dist = haversine_distance(lat1, lng1, lat2, lng2)
    return dist <= radius_m, dist


def cluster_gps_points(coords):
    if len(coords) < 2:
        return [-1] * len(coords)
    coords_rad = np.radians(coords)
    db = DBSCAN(
        eps=DBSCAN_RADIUS_RAD,
        min_samples=2,
        algorithm='ball_tree',
        metric='haversine'
    ).fit(coords_rad)
    return db.labels_.tolist()
