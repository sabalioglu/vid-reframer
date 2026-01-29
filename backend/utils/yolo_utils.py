"""
YOLOv8 Object Detection Utilities
Video Reframer
"""

from __future__ import annotations
import logging
from typing import Dict, List, Any

try:
    import numpy as np
    from ultralytics import YOLO
except ImportError:
    np = None
    YOLO = None

from config.ai_config import (
    YOLO_MODEL,
    YOLO_CONFIDENCE,
    YOLO_IOU,
    YOLO_DEVICE,
    YOLO_IMG_SIZE,
    YOLO_BATCH_SIZE,
    YOLO_MAX_DET,
    YOLO_CLASSES_TO_DETECT,
    MIN_FRAME_SIZE,
)

logger = logging.getLogger(__name__)

# Global model cache
_yolo_model = None


def load_yolo_model() -> YOLO:
    """
    Load YOLOv8 model with caching

    Returns:
        YOLO model instance
    """
    global _yolo_model

    try:
        if _yolo_model is None:
            logger.info(f"Loading YOLOv8 model: {YOLO_MODEL}")
            _yolo_model = YOLO(YOLO_MODEL)
            _yolo_model.to(YOLO_DEVICE)
            logger.info("YOLOv8 model loaded successfully")

        return _yolo_model

    except Exception as e:
        logger.error(f"Error loading YOLO model: {e}")
        raise


def run_yolov8_detection(
    frames: List,
    sample_rate: int = 1,
) -> Dict[int, List[Dict[str, Any]]]:
    """
    Run YOLOv8 detection on video frames

    Args:
        frames: List of (frame_number, frame_array) tuples
        sample_rate: Process every Nth frame

    Returns:
        {frame_number: [detection_objects]}
        Each detection: {class, confidence, bbox: {x, y, width, height}}
    """
    logger.info(f"Running YOLOv8 detection on {len(frames)} frames")

    detections = {}
    model = load_yolo_model()

    try:
        for idx, (frame_num, frame) in enumerate(frames):
            # Sample frames for efficiency
            if idx % sample_rate != 0:
                continue

            # Run inference
            results = model(
                frame,
                conf=YOLO_CONFIDENCE,
                iou=YOLO_IOU,
                imgsz=YOLO_IMG_SIZE,
                device=YOLO_DEVICE,
                max_det=YOLO_MAX_DET,
                verbose=False
            )

            # Parse results
            detections_for_frame = []

            for result in results:
                boxes = result.boxes

                for box_idx in range(len(boxes)):
                    box = boxes[box_idx]

                    # Get class
                    class_id = int(box.cls.cpu().numpy()[0])

                    # Filter classes if specified
                    if YOLO_CLASSES_TO_DETECT and class_id not in YOLO_CLASSES_TO_DETECT:
                        continue

                    # Get confidence
                    confidence = float(box.conf.cpu().numpy()[0])

                    # Get bounding box (xyxy format)
                    xyxy = box.xyxy.cpu().numpy()[0]
                    x1, y1, x2, y2 = xyxy

                    # Convert to x, y, width, height
                    bbox_x = float(x1)
                    bbox_y = float(y1)
                    bbox_width = float(x2 - x1)
                    bbox_height = float(y2 - y1)

                    # Skip very small objects
                    if bbox_width < MIN_FRAME_SIZE or bbox_height < MIN_FRAME_SIZE:
                        continue

                    # Get class name
                    class_name = result.names.get(class_id, f"class_{class_id}")

                    detection = {
                        "class": class_name,
                        "class_id": class_id,
                        "confidence": confidence,
                        "bbox": {
                            "x": bbox_x,
                            "y": bbox_y,
                            "width": bbox_width,
                            "height": bbox_height,
                        }
                    }

                    detections_for_frame.append(detection)

            detections[frame_num] = detections_for_frame

            if (idx + 1) % 10 == 0:
                logger.info(f"Processed {idx + 1} frames, found {len(detections_for_frame)} detections in frame {frame_num}")

        logger.info(f"YOLOv8 detection complete. Found {sum(len(d) for d in detections.values())} total detections")
        return detections

    except Exception as e:
        logger.error(f"Error in YOLOv8 detection: {e}")
        return {}


def filter_detections_by_class(
    detections: Dict[int, List[Dict]],
    class_names: List[str]
) -> Dict[int, List[Dict]]:
    """
    Filter detections to only include specific classes

    Args:
        detections: Detection results
        class_names: List of class names to keep

    Returns:
        Filtered detections
    """
    filtered = {}

    for frame_num, frame_detections in detections.items():
        filtered[frame_num] = [
            det for det in frame_detections
            if det["class"] in class_names
        ]

    return filtered


def filter_detections_by_confidence(
    detections: Dict[int, List[Dict]],
    min_confidence: float
) -> Dict[int, List[Dict]]:
    """
    Filter detections by minimum confidence threshold

    Args:
        detections: Detection results
        min_confidence: Minimum confidence (0.0-1.0)

    Returns:
        Filtered detections
    """
    filtered = {}

    for frame_num, frame_detections in detections.items():
        filtered[frame_num] = [
            det for det in frame_detections
            if det["confidence"] >= min_confidence
        ]

    return filtered


def get_detection_statistics(
    detections: Dict[int, List[Dict]]
) -> Dict[str, Any]:
    """
    Calculate statistics from detections

    Args:
        detections: Detection results

    Returns:
        Statistics dictionary
    """
    total_detections = sum(len(dets) for dets in detections.values())
    frames_with_detections = len([f for f in detections.values() if len(f) > 0])

    class_counts = {}
    for frame_dets in detections.values():
        for det in frame_dets:
            class_name = det["class"]
            class_counts[class_name] = class_counts.get(class_name, 0) + 1

    avg_confidence = 0
    if total_detections > 0:
        all_confidences = [
            det["confidence"]
            for frame_dets in detections.values()
            for det in frame_dets
        ]
        avg_confidence = sum(all_confidences) / len(all_confidences)

    return {
        "total_detections": total_detections,
        "frames_with_detections": frames_with_detections,
        "average_confidence": avg_confidence,
        "class_distribution": class_counts,
    }
