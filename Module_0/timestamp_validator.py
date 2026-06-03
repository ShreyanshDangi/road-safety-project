# module0/timestamp_validator.py

from datetime import datetime, timezone, timedelta
import logging

logger = logging.getLogger(__name__)

EXIF_TIMESTAMP_FORMAT = "%Y:%m:%d %H:%M:%S"  # cameras use colons in date too
MAX_AGE_HOURS = 24   # photos older than this get flagged
MAX_AGE_HOURS      = 24   # photos older than this → flag
FUTURE_GRACE_HOURS = 14   # timezone buffer — real future manipulation exceeds this


def validate_timestamp(exif_timestamp: str | None) -> dict:
    """
    Validates photo capture time against current UTC time.

    Args:
        exif_timestamp: raw string from EXIF, e.g. "2026:05:17 14:30:00"
                        None if EXIF had no timestamp.

    Returns:
    {
        "photo_time":       str | None,   # parsed, ISO format
        "age_hours":        float | None, # how old the photo is
        "timestamp_flag":   bool,         # True = suspiciously old
        "flag_reason":      str | None
    }
    """
    result = {
        "photo_time":     None,
        "age_hours":      None,
        "timestamp_flag": False,
        "flag_reason":    None,
    }

    if exif_timestamp is None:
        # No timestamp available — cannot validate, but don't flag
        # Missing timestamp is common (WhatsApp, screenshots)
        result["flag_reason"] = "No EXIF timestamp — cannot validate age"
        return result

    try:
        photo_dt = datetime.strptime(exif_timestamp, EXIF_TIMESTAMP_FORMAT)
    except ValueError:
        result["timestamp_flag"] = True
        result["flag_reason"]    = f"Unparseable timestamp format: {exif_timestamp}"
        return result

    # Treat photo time as UTC for comparison (conservative — see note above)
    # Worst case: 5.5hr IST offset means we're off by 5.5hrs on age calculation
    # Acceptable for a 24hr threshold
    now_utc   = datetime.now(timezone.utc).replace(tzinfo=None)
    age_delta = now_utc - photo_dt
    age_hours = age_delta.total_seconds() / 3600.0

    result["photo_time"] = photo_dt.isoformat()
    result["age_hours"]  = round(age_hours, 2)

    if age_hours < -FUTURE_GRACE_HOURS:
        result["timestamp_flag"] = True
        result["flag_reason"]    = (
            f"Photo timestamp is {abs(age_hours):.1f}hrs in the future — "
            f"exceeds {FUTURE_GRACE_HOURS}hr timezone tolerance"
    )

    elif age_hours > MAX_AGE_HOURS:
        result["timestamp_flag"] = True
        result["flag_reason"]    = (
            f"Photo is {age_hours:.1f}hrs old — exceeds {MAX_AGE_HOURS}hr limit"
        )

    return result