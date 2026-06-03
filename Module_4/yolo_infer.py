"""
Module 4 - Repair Verifier
yolo_infer.py: Runs Module 1's YOLOv8 pothole detector on the after-repair image
"""

import os


def load_model(model_path="best.pt"):
    """
    Loads the YOLOv8 model trained in Module 1.

    Args:
        model_path: Path to the .pt weights file from Module 1

    Returns:
        YOLO model object
    """
    try:
        from ultralytics import YOLO
        if not os.path.exists(model_path):
            raise FileNotFoundError(
                f"Model not found at '{model_path}'.\n"
                "Please copy your Module 1 trained weights (best.pt) here."
            )
        model = YOLO(model_path)
        print(f"[YOLO] Model loaded from {model_path}")
        return model
    except ImportError:
        raise ImportError("ultralytics not installed. Run: pip install ultralytics")


def detect_potholes(image_path, model_path="best.pt", confidence_threshold=0.35):
    """
    Runs pothole detection on the given image using the Module 1 YOLO model.

    Args:
        image_path           : path to image to run inference on
        model_path           : path to YOLOv8 .pt weights
        confidence_threshold : minimum confidence to count a detection

    Returns:
        dict with:
            count        : number of potholes detected
            detections   : list of dicts with class, confidence, bbox
            raw_results  : raw YOLO results object
    """
    model = load_model(model_path)
    results = model(image_path, conf=confidence_threshold, verbose=False)

    detections = []
    for box in results[0].boxes:
        detections.append({
            "class_id"  : int(box.cls[0]),
            "class_name": model.names[int(box.cls[0])],
            "confidence": round(float(box.conf[0]), 3),
            "bbox"      : box.xyxy[0].tolist()  # [x1, y1, x2, y2]
        })

    count = len(detections)
    print(f"[YOLO] Detected {count} pothole(s) in {image_path}")

    return {
        "count"      : count,
        "detections" : detections,
        "raw_results": results
    }


def save_annotated_image(results, output_path="annotated_after.jpg"):
    """Saves the YOLO-annotated image with bounding boxes drawn."""
    annotated = results[0].plot()
    import cv2
    cv2.imwrite(output_path, annotated)
    print(f"[YOLO] Annotated image saved to {output_path}")


if __name__ == "__main__":
    result = detect_potholes("test_after.jpg", model_path="best.pt")
    print(f"Potholes found : {result['count']}")
    for d in result["detections"]:
        print(f"  - {d['class_name']} | confidence: {d['confidence']}")
