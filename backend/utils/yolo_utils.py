import logging
from ultralytics import YOLO
import numpy as np

logger = logging.getLogger(__name__)

# Load YOLOv8 model once
try:
    model = YOLO('yolov8m.pt')  # Medium model
    logger.info("YOLOv8 model loaded successfully")
except Exception as e:
    logger.error(f"Error loading YOLOv8 model: {e}")
    model = None


def run_yolov8_detection(frames: list) -> dict:
    """
    Run YOLOv8 object detection on video frames.
    
    Args:
        frames: List of numpy arrays (frames from video)
    
    Returns:
        Dict with detections per frame
    """
    detections = {}
    
    if model is None:
        logger.warning("YOLOv8 model not available")
        return detections
    
    if not frames:
        logger.warning("No frames provided for detection")
        return detections
    
    try:
        logger.info(f"Running YOLOv8 detection on {len(frames)} frames")
        
        for frame_idx, frame in enumerate(frames):
            try:
                # Run inference
                results = model(frame, verbose=False)
                
                frame_detections = []
                
                # Extract detections from results
                for result in results:
                    boxes = result.boxes
                    
                    for box in boxes:
                        detection = {
                            "class_id": int(box.cls[0]),
                            "class_name": result.names[int(box.cls[0])],
                            "confidence": float(box.conf[0]),
                            "bbox": {
                                "x1": float(box.xyxy[0][0]),
                                "y1": float(box.xyxy[0][1]),
                                "x2": float(box.xyxy[0][2]),
                                "y2": float(box.xyxy[0][3])
                            }
                        }
                        frame_detections.append(detection)
                
                if frame_detections:
                    detections[f"frame_{frame_idx}"] = frame_detections
                
            except Exception as e:
                logger.warning(f"Error processing frame {frame_idx}: {e}")
                continue
        
        logger.info(f"Detection complete: {len(detections)} frames with detections")
        
    except Exception as e:
        logger.error(f"Error in YOLOv8 detection: {e}")
    
    return detections


def get_detection_statistics(detections: dict) -> dict:
    """
    Calculate statistics from detection results.
    
    Args:
        detections: Dict from run_yolov8_detection
    
    Returns:
        Dict with statistics
    """
    stats = {
        "total_detections": 0,
        "frames_with_detections": len(detections),
        "average_confidence": 0.0,
        "class_distribution": {}
    }
    
    try:
        if not detections:
            return stats
        
        all_confidences = []
        
        for frame_key, frame_dets in detections.items():
            if not frame_dets:
                continue
            
            for detection in frame_dets:
                stats["total_detections"] += 1
                confidence = detection.get("confidence", 0)
                all_confidences.append(confidence)
                
                class_name = detection.get("class_name", "unknown")
                stats["class_distribution"][class_name] = stats["class_distribution"].get(class_name, 0) + 1
        
        # Calculate average confidence
        if all_confidences:
            stats["average_confidence"] = round(np.mean(all_confidences), 3)
        
        logger.info(f"Detection stats: {stats['total_detections']} detections in {stats['frames_with_detections']} frames")

    except Exception as e:
        logger.error(f"Error calculating statistics: {e}")

    return stats


def verify_gemini_products(frames: list, gemini_products: list) -> dict:
    """
    VERIFICATION LAYER: Only detect products identified by Gemini.

    Args:
        frames: List of numpy arrays (video frames)
        gemini_products: List of products from Gemini analysis
            [{"name": "knife", "category": "tool"}, ...]

    Returns:
        Dict with verified detections (ONLY Gemini-identified products)
    """
    detections = {}

    if model is None:
        logger.warning("YOLOv8 model not available for verification")
        return detections

    if not frames or not gemini_products:
        logger.warning("No frames or products provided")
        return detections

    # Extract product names from Gemini
    product_names = set()
    for product in gemini_products:
        name = product.get("name", "").lower().strip()
        if name:
            product_names.add(name)

    logger.info(f"[YOLO Verification] Looking for {len(product_names)} Gemini products: {product_names}")

    try:
        for frame_idx, frame in enumerate(frames):
            try:
                # Run inference
                results = model(frame, verbose=False)

                frame_detections = []

                # Extract detections from results
                for result in results:
                    boxes = result.boxes

                    for box in boxes:
                        class_name = result.names[int(box.cls[0])].lower().strip()

                        # FILTER: Only keep products Gemini identified
                        if class_name not in product_names:
                            continue

                        detection = {
                            "class_id": int(box.cls[0]),
                            "class_name": class_name,
                            "confidence": float(box.conf[0]),
                            "gemini_verified": True,
                            "bbox": {
                                "x1": float(box.xyxy[0][0]),
                                "y1": float(box.xyxy[0][1]),
                                "x2": float(box.xyxy[0][2]),
                                "y2": float(box.xyxy[0][3])
                            }
                        }
                        frame_detections.append(detection)

                if frame_detections:
                    detections[f"frame_{frame_idx}"] = frame_detections

            except Exception as e:
                logger.warning(f"Error processing frame {frame_idx}: {e}")
                continue

        logger.info(f"[YOLO Verification] Complete: {len(detections)} frames with verified detections")

    except Exception as e:
        logger.error(f"Error in YOLOv8 verification: {e}")

    return detections
