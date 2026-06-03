# module0/reverse_geocoder.py

import requests
import logging

logger = logging.getLogger(__name__)

NOMINATIM_URL   = "https://nominatim.openstreetmap.org/reverse"
HEADERS         = {"User-Agent": "PotholeReportingSystem/1.0"}
TIMEOUT_SECONDS = 5
VALID_COUNTRY   = "in"   # reject anything outside India

# OSM highway tags → your internal road_type classification
OSM_TO_ROAD_TYPE = {
    "motorway":     "national_highway",
    "trunk":        "national_highway",
    "primary":      "state_highway",
    "secondary":    "major_district_road",
    "tertiary":     "city_road",
    "residential":  "city_road",
    "service":      "city_road",
    "unclassified": "rural_road",
    "track":        "rural_road",
}


def reverse_geocode(lat: float, lon: float) -> dict:
    """
    Reverse geocode coordinates via Nominatim.

    Returns:
    {
        "address":            str | None,   # full display address
        "road_name":          str | None,   # street name
        "road_type":          str | None,   # internal classification, None if OSM tag missing
        "city":               str | None,
        "state":              str | None,
        "country_code":       str | None,
        "is_valid_location":  bool,
        "flag_reason":        str | None
    }
    """
    result = {
        "address":           None,
        "road_name":         None,
        "road_type":         None,
        "city":              None,
        "state":             None,
        "country_code":      None,
        "is_valid_location": False,
        "flag_reason":       None,
    }

    try:
        response = requests.get(
            NOMINATIM_URL,
            params={
                "lat":            lat,
                "lon":            lon,
                "format":         "json",
                "addressdetails": 1,
                "extratags":      1,    # needed for OSM highway tag
            },
            headers=HEADERS,
            timeout=TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        data = response.json()

    except requests.exceptions.Timeout:
        result["flag_reason"] = "Nominatim timed out — GPS valid but address unverified"
        return result
    except requests.exceptions.RequestException as e:
        result["flag_reason"] = f"Nominatim request failed: {str(e)}"
        return result

    # Nominatim returns {"error": ...} for coordinates in the ocean
    if "error" in data:
        result["flag_reason"] = f"Coordinates resolve to nothing: {data['error']}"
        return result

    address_block = data.get("address",   {})
    extratags     = data.get("extratags", {})

    # ── Country check ─────────────────────────────────────────────────────────
    country_code = address_block.get("country_code", "").lower()
    result["country_code"] = country_code

    if country_code != VALID_COUNTRY:
        result["flag_reason"] = (
            f"Coordinates resolve to {country_code.upper()}, not India"
        )
        return result

    # ── Location type sanity ──────────────────────────────────────────────────
    # addresstype tells you what the closest feature is
    location_type = data.get("addresstype", "")
    if location_type in ("water", "natural", "boundary", "forest"):
        result["flag_reason"] = (
            f"Coordinates fall on '{location_type}', not a road"
        )
        return result

    # ── Extract road info ─────────────────────────────────────────────────────
    result["road_name"] = (
        address_block.get("road")
        or address_block.get("pedestrian")
        or address_block.get("path")
    )

    # road_type from OSM extratags — may be None, Step 5 handles fallback
    osm_highway       = extratags.get("highway")
    result["road_type"] = OSM_TO_ROAD_TYPE.get(osm_highway)

    # ── Location fields ───────────────────────────────────────────────────────
    result["city"] = (
        address_block.get("city")
        or address_block.get("town")
        or address_block.get("village")
    )
    result["state"]   = address_block.get("state")
    result["address"] = data.get("display_name")

    result["is_valid_location"] = True
    return result