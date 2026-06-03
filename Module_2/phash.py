"""
phash.py — Perceptual Hashing
Computes a 64-bit visual fingerprint using DCT.
Built with only numpy + Pillow + requests. No extra libraries needed.

Change vs original:
  • compute_phash() now accepts a Cloudinary URL (or any HTTP/S URL).
    It downloads the image into memory; no local file is written.
"""

import io
import requests
import numpy as np
from PIL import Image

HAMMING_THRESHOLD = 10


def _dct_1d(x):
    N = len(x)
    n = np.arange(N)
    k = n.reshape((N, 1))
    cos_matrix = np.cos(np.pi * k * (2 * n + 1) / (2 * N))
    return 2 * np.dot(cos_matrix, x)


def _dct_2d(block):
    row_dct = np.apply_along_axis(_dct_1d, axis=1, arr=block.astype(float))
    col_dct = np.apply_along_axis(_dct_1d, axis=0, arr=row_dct)
    return col_dct


def compute_phash(image_url: str) -> str:
    """
    Download the image at *image_url* and return its 16-character hex pHash.
    Accepts any publicly accessible URL (Cloudinary, S3, etc.).
    """
    response = requests.get(image_url, timeout=15)
    response.raise_for_status()
    img = Image.open(io.BytesIO(response.content)).convert("L")
    img = img.resize((32, 32), Image.LANCZOS)
    pixels = np.array(img, dtype=float)

    dct = _dct_2d(pixels)
    low_freq = dct[:8, :8].flatten()
    low_freq[0] = 0  # remove DC component

    threshold = np.median(low_freq[1:])
    bits = (low_freq > threshold)

    hex_chars = []
    for i in range(0, 64, 4):
        nibble = bits[i:i + 4]
        val = (int(nibble[0]) * 8 + int(nibble[1]) * 4
               + int(nibble[2]) * 2 + int(nibble[3]))
        hex_chars.append(format(val, 'x'))

    return ''.join(hex_chars)


def _hex_to_bits(hex_str):
    bits = []
    for ch in hex_str:
        val = int(ch, 16)
        bits.extend([(val >> (3 - i)) & 1 for i in range(4)])
    return np.array(bits, dtype=bool)


def hamming_distance(hash1, hash2):
    b1 = _hex_to_bits(hash1)
    b2 = _hex_to_bits(hash2)
    return int(np.sum(b1 != b2))


def are_images_similar(hash1, hash2):
    dist = hamming_distance(hash1, hash2)
    return dist <= HAMMING_THRESHOLD, dist


def similarity_percentage(dist):
    return round((1 - dist / 64) * 100, 2)
