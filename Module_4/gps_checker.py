"""
Module 4 - Repair Verifier
gps_checker.py: Extracts GPS from image EXIF and validates location match
"""

import math
from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS


def extract_gps_from_image(image_path: str):
    """
    Extracts GPS coordinates from image EXIF metadata.
    Returns (latitude, longitude) in decimal degrees, or None if not found.
    """
    try:
        img = Image.open(image_path)
        exif_data = img._getexif()

        if not exif_data:
            print(f"[GPS] No EXIF data found in {image_path}")
            return None

        gps_info = {}
        for tag_id, value in exif_data.items():
            tag_name = TAGS.get(tag_id)
            if tag_name == "GPSInfo":
                for gps_tag_id, gps_val in value.items():
                    gps_tag_name = GPSTAGS.get(gps_tag_id)
                    gps_info[gps_tag_name] = gps_val

        if not gps_info:
            print(f"[GPS] No GPS tags found in EXIF of {image_path}")
            return None

        lat = _convert_to_degrees(gps_info.get("GPSLatitude"))
        lon = _convert_to_degrees(gps_info.get("GPSLongitude"))

        if lat is None or lon is None:
            return None

        if gps_info.get("GPSLatitudeRef") == "S":
            lat = -lat
        if gps_info.get("GPSLongitudeRef") == "W":
            lon = -lon

        return (round(lat, 7), round(lon, 7))

    except Exception as e:
        print(f"[GPS] Error reading EXIF: {e}")
        return None


def _convert_to_degrees(value):
    """Converts GPS DMS (degrees, minutes, seconds) to decimal degrees."""
    if value is None:
        return None
    try:
        d = float(value[0])
        m = float(value[1])
        s = float(value[2])
        return d + (m / 60.0) + (s / 3600.0)
    except Exception:
        return None


def haversine_distance(coord1, coord2):
    """
    Calculates distance between two GPS points in meters using Haversine formula.
    coord1, coord2: (latitude, longitude) in decimal degrees
    """
    R = 6371000  # Earth radius in meters
    lat1, lon1 = map(math.radians, coord1)
    lat2, lon2 = map(math.radians, coord2)
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return round(R * 2 * math.asin(math.sqrt(a)), 2)


def validate_gps(after_image_path, original_gps, threshold_meters=30.0):
    """
    Validates whether the after-repair photo was taken at the complaint location.

    Args:
        after_image_path : path to the after-repair image
        original_gps     : (lat, lon) tuple of the original complaint
        threshold_meters : max acceptable distance in meters (default 30 m)

    Returns:
        dict with gps_found, after_gps, distance_m, is_valid, note
    """
    after_gps = extract_gps_from_image(after_image_path)

    if after_gps is None:
        return {
            "gps_found": False,
            "after_gps": None,
            "distance_m": None,
            "is_valid": None,
            "note": "No GPS EXIF data in after-image. Cannot verify location."
        }

    distance = haversine_distance(original_gps, after_gps)
    is_valid = distance <= threshold_meters

    return {
        "gps_found": True,
        "after_gps": after_gps,
        "distance_m": distance,
        "is_valid": is_valid,
        "note": (
            f"After photo taken {distance}m from complaint site. "
            f"{'Within' if is_valid else 'EXCEEDS'} {threshold_meters}m threshold."
        )
    }


if __name__ == "__main__":
    result = validate_gps(
        after_image_path="test_after.jpg",
        original_gps=(28.6139, 77.2090),
        threshold_meters=30
    )
    print(result)
