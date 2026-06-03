# module0/exif_extractor.py

from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS
import logging

logger = logging.getLogger(__name__)

    
def _dms_to_decimal(dms: tuple, ref: str) -> float:
    """
    Returns None if any component has a zero denominator
    (GPS block exists but no satellite fix was acquired).
    """
    components = []
    for rational in dms:
        if int(rational.denominator) == 0:
            return None   # signal: GPS tag present but no valid fix
        components.append(float(rational))

    degrees = components[0]
    minutes = components[1] / 60.0
    seconds = components[2] / 3600.0

    decimal = degrees + minutes + seconds
    if ref in ("S", "W"):
        decimal = -decimal

    return round(decimal, 7)


def extract_exif_gps(image_bytes: bytes) -> dict:
    """
    Extract GPS coordinates and capture timestamp from image EXIF.

    Accepts raw image bytes (not a file path) so it works
    directly with FastAPI's UploadFile without saving to disk.

    Returns:
    {
        "lat":       float | None,
        "lon":       float | None,
        "timestamp": str | None,    # "YYYY:MM:DD HH:MM:SS" — camera's local time
        "source":    "exif" | "none",
        "error":     str | None     # None means clean extraction
    }
    """
    result = {
        "lat":       None,
        "lon":       None,
        "timestamp": None,
        "source":    "none",
        "error":     None,
    }

    try:
        from io import BytesIO
        img  = Image.open(BytesIO(image_bytes))
        exif = img._getexif()

        if exif is None:
            result["error"] = "No EXIF data in image"
            return result

        # Convert raw integer tag IDs → readable names
        exif_named = {TAGS.get(tag, tag): val for tag, val in exif.items()}

        # Timestamp — prefer DateTimeOriginal (shutter moment) over DateTime (file write time)
        result["timestamp"] = (
            exif_named.get("DateTimeOriginal")
            or exif_named.get("DateTime")
        )

        gps_raw = exif_named.get("GPSInfo")
        if not gps_raw:
            result["error"] = "EXIF present but no GPSInfo block — location permission was off"
            return result

        # Convert GPS tag IDs → readable names
        gps = {GPSTAGS.get(tag, tag): val for tag, val in gps_raw.items()}

        lat_dms = gps.get("GPSLatitude")
        lat_ref = gps.get("GPSLatitudeRef")
        lon_dms = gps.get("GPSLongitude")
        lon_ref = gps.get("GPSLongitudeRef")

        lat = _dms_to_decimal(lat_dms, lat_ref)
        lon = _dms_to_decimal(lon_dms, lon_ref)
        
        if lat is None or lon is None:
            result["error"] = "GPSInfo block present but coordinates are zero — no satellite fix"
            return result
        
        result["lat"]    = lat
        result["lon"]    = lon
        result["source"] = "exif"

    except Exception as e:
        result["error"] = f"Extraction failed: {str(e)}"
        logger.exception("extract_exif_gps crashed")

    return result