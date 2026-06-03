"""
Module 4 - Repair Verifier
ssim_compare.py: Computes Structural Similarity Index between before and after images
"""

import cv2
import numpy as np
from skimage.metrics import structural_similarity as ssim


def preprocess_images(before_path, after_path):
    """
    Loads and preprocesses both images:
    - Converts to grayscale
    - Resizes after-image to match before-image dimensions
    - Applies CLAHE for lighting normalization
    """
    before = cv2.imread(before_path, cv2.IMREAD_GRAYSCALE)
    after = cv2.imread(after_path, cv2.IMREAD_GRAYSCALE)

    if before is None:
        raise FileNotFoundError(f"Cannot read before image: {before_path}")
    if after is None:
        raise FileNotFoundError(f"Cannot read after image: {after_path}")

    # Resize after image to match before image dimensions
    after = cv2.resize(after, (before.shape[1], before.shape[0]))

    # CLAHE - Contrast Limited Adaptive Histogram Equalization
    # Normalizes lighting differences between photos taken at different times
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    before = clahe.apply(before)
    after = clahe.apply(after)

    return before, after


def compute_ssim(before_path, after_path):
    """
    Computes SSIM score between before and after images.

    Returns:
        score      : float between 0 and 1 (higher = more similar)
        diff_image : numpy array showing where differences occur
        interpretation : human-readable meaning of the score
    """
    before, after = preprocess_images(before_path, after_path)

    score, diff = ssim(before, after, full=True)
    score = round(float(score), 4)

    # Normalize diff for visualization
    diff_image = (diff * 255).astype(np.uint8)

    # Interpretation
    if score >= 0.85:
        interpretation = "Very similar — surface barely changed. Likely NOT repaired."
    elif score >= 0.65:
        interpretation = "Moderately different — some surface change detected."
    else:
        interpretation = "Significantly different — surface has clearly changed. Likely repaired."

    return {
        "ssim_score": score,
        "diff_image": diff_image,
        "interpretation": interpretation
    }


def save_diff_image(diff_image, output_path="diff_output.jpg"):
    """Saves the SSIM difference heatmap to disk for inspection."""
    # Threshold the diff to highlight changed regions
    _, thresh = cv2.threshold(diff_image, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # Create color diff map
    diff_colored = cv2.applyColorMap(255 - diff_image, cv2.COLORMAP_JET)
    cv2.imwrite(output_path, diff_colored)
    print(f"[SSIM] Diff image saved to {output_path}")


if __name__ == "__main__":
    result = compute_ssim("test_before.jpg", "test_after.jpg")
    print(f"SSIM Score     : {result['ssim_score']}")
    print(f"Interpretation : {result['interpretation']}")
