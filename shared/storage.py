# shared/storage.py

import os
import uuid
import requests
import cloudinary
import cloudinary.uploader
from pathlib import Path
from dotenv import load_dotenv
import logging

load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")
logger = logging.getLogger(__name__)

# ─── Configure Cloudinary once at import ─────────────────────────────────────
cloudinary.config(
    cloud_name = os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key    = os.getenv("CLOUDINARY_API_KEY"),
    api_secret = os.getenv("CLOUDINARY_API_SECRET"),
    secure     = True,   # always use HTTPS URLs
)


def upload_image(image_bytes: bytes, folder: str = "complaints") -> str:
    """
    Upload raw image bytes to Cloudinary.

    Args:
        image_bytes : raw bytes from UploadFile.read()
        folder      : Cloudinary folder — "complaints" or "repairs"

    Returns:
        Secure HTTPS URL of the uploaded image (permanent, CDN-backed)

    Raises:
        RuntimeError if upload fails
    """
    try:
        # Generate unique public_id so filenames never collide
        public_id = f"{folder}/{uuid.uuid4().hex}"

        result = cloudinary.uploader.upload(
            image_bytes,
            public_id       = public_id,
            resource_type   = "image",
            overwrite       = False,
            invalidate      = True,
        )

        url = result.get("secure_url")
        if not url:
            raise RuntimeError("Cloudinary returned no URL")

        logger.info(f"[storage] Uploaded → {url}")
        return url

    except Exception as e:
        logger.exception("[storage] upload_image failed")
        raise RuntimeError(f"Image upload failed: {str(e)}")


def fetch_image_bytes(url: str) -> bytes:
    """
    Download image bytes from a Cloudinary URL.
    Used by Module 4 to retrieve the before-image for SSIM comparison.

    Args:
        url : Cloudinary secure URL stored in complaints.image_url

    Returns:
        Raw image bytes

    Raises:
        RuntimeError if download fails
    """
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.content

    except Exception as e:
        logger.exception(f"[storage] fetch_image_bytes failed for {url}")
        raise RuntimeError(f"Image fetch failed: {str(e)}")


def delete_image(url: str):
    """
    Delete an image from Cloudinary by its URL.
    Optional — use when rejecting a complaint to save storage quota.
    """
    try:
        # Extract public_id from URL
        # URL format: https://res.cloudinary.com/{cloud}/image/upload/v{ver}/{public_id}.jpg
        path      = url.split("/upload/")[-1]           # "v1234567/complaints/abc123.jpg"
        public_id = path.split("/", 1)[-1].rsplit(".", 1)[0]  # "complaints/abc123"

        cloudinary.uploader.destroy(public_id)
        logger.info(f"[storage] Deleted {public_id}")

    except Exception as e:
        # Non-critical — log and continue, don't crash the request
        logger.warning(f"[storage] delete_image failed: {e}")