"""
SAM2 Segmentation Utilities
Pixel-Perfect Mask Generation
Video Reframer
"""

from __future__ import annotations
import logging
from typing import Dict, List, Any, Tuple

try:
    import numpy as np
    import cv2
    import torch
except ImportError:
    np = None
    cv2 = None
    torch = None
from config.ai_config import (
    SAM2_MODEL,
    SAM2_DEVICE,
    SAM2_BATCH_SIZE,
    SAM2_IMAGE_SIZE,
    SAM2_STABILITY_SCORE_THRESH,
    SAM2_MIN_MASK_REGION_AREA,
)

logger = logging.getLogger(__name__)

# Global model cache
_sam2_model = None
_device = None


def load_sam2_model():
    """
    Load SAM2 model (Meta Segment Anything Model 2)

    Note: Requires GPU for efficient processing
    Returns model predictor instance
    """
    global _sam2_model, _device

    try:
        if _sam2_model is None:
            logger.info(f"Loading SAM2 model: {SAM2_MODEL}")

            # Set device
            _device = torch.device(SAM2_DEVICE if torch.cuda.is_available() else "cpu")
            logger.info(f"Using device: {_device}")

            # Try to import SAM2
            try:
                from sam2.build_sam import build_sam2
                from sam2.sam2_image_predictor import SAM2ImagePredictor
            except ImportError:
                logger.warning("SAM2 not installed. Install from: https://github.com/facebookresearch/segment-anything-2")
                return None

            # Build and load model
            sam2_model = build_sam2(
                config_file="sam2_hiera_b+.yaml",
                ckpt_path=SAM2_MODEL,
                device=_device
            )

            _sam2_model = SAM2ImagePredictor(sam2_model)
            logger.info("SAM2 model loaded successfully")

        return _sam2_model

    except Exception as e:
        logger.error(f"Error loading SAM2 model: {e}")
        logger.warning("Segmentation will be skipped. Install SAM2 for full functionality.")
        return None


def encode_rle(mask: np.ndarray) -> str:
    """
    Encode binary mask to RLE (Run-Length Encoding)

    Args:
        mask: Binary numpy array (uint8 or bool)

    Returns:
        RLE encoded string (compressed ~10x vs PNG)
    """
    try:
        # Flatten mask
        flat_mask = mask.flatten()

        # Find runs
        runs = []
        current_val = flat_mask[0]
        current_count = 1

        for i in range(1, len(flat_mask)):
            if flat_mask[i] == current_val:
                current_count += 1
            else:
                runs.append(str(current_count))
                current_val = flat_mask[i]
                current_count = 1

        runs.append(str(current_count))

        # RLE format: "count1,count2,count3,..." alternating 0s and 1s
        return ",".join(runs)

    except Exception as e:
        logger.error(f"Error encoding RLE: {e}")
        return ""


def decode_rle(rle_string: str, height: int, width: int) -> np.ndarray:
    """
    Decode RLE string back to binary mask

    Args:
        rle_string: RLE encoded string
        height: Mask height
        width: Mask width

    Returns:
        Binary numpy array
    """
    try:
        counts = list(map(int, rle_string.split(",")))

        # Reconstruct mask
        mask = []
        current_val = 0

        for count in counts:
            mask.extend([current_val] * count)
            current_val = 1 - current_val

        # Reshape to image dimensions
        mask = np.array(mask, dtype=np.uint8)
        mask = mask[:height * width].reshape(height, width)

        return mask

    except Exception as e:
        logger.error(f"Error decoding RLE: {e}")
        return np.zeros((height, width), dtype=np.uint8)


def get_mask_area(mask: np.ndarray) -> int:
    """Get number of pixels in mask"""
    return int(np.sum(mask > 0))


def run_sam2_segmentation(
    frames: List[Tuple[int, np.ndarray]],
    detections: Dict[int, List[Dict[str, Any]]],
    sample_rate: int = 1,
) -> Dict[int, List[Dict[str, Any]]]:
    """
    Run SAM2 segmentation on detected objects

    Args:
        frames: List of (frame_number, frame_array) tuples
        detections: YOLO detection results
        sample_rate: Process every Nth frame

    Returns:
        {frame_number: [segmentation_masks]}
        Each mask: {track_id, mask_rle, mask_area_pixels, confidence}
    """
    logger.info(f"Running SAM2 segmentation on detected objects")

    segmentation = {}
    model = load_sam2_model()

    if model is None:
        logger.warning("SAM2 model not available. Returning empty segmentation.")
        return segmentation

    try:
        for idx, (frame_num, frame) in enumerate(frames):
            # Sample frames
            if idx % sample_rate != 0:
                continue

            # Get detections for this frame
            frame_detections = detections.get(frame_num, [])

            if not frame_detections:
                segmentation[frame_num] = []
                continue

            logger.info(f"Processing frame {frame_num} with {len(frame_detections)} detections")

            # Set image for SAM2
            model.set_image(frame)

            frame_masks = []

            # Process each detection
            for det_idx, detection in enumerate(frame_detections):
                try:
                    bbox = detection["bbox"]

                    # Convert bbox to coordinates
                    x1, y1 = int(bbox["x"]), int(bbox["y"])
                    x2, y2 = int(bbox["x"] + bbox["width"]), int(bbox["y"] + bbox["height"])

                    # SAM2 prompt with bounding box
                    box = np.array([x1, y1, x2, y2])

                    # Run segmentation
                    masks, scores, logits = model.predict(
                        box=box,
                        multimask_output=False
                    )

                    # Get best mask
                    best_mask_idx = np.argmax(scores)
                    mask = masks[best_mask_idx]

                    # Filter by stability score and area
                    stability_score = scores[best_mask_idx]

                    if stability_score < SAM2_STABILITY_SCORE_THRESH:
                        logger.debug(f"Mask too unstable (score={stability_score}), skipping")
                        continue

                    mask_area = get_mask_area(mask)

                    if mask_area < SAM2_MIN_MASK_REGION_AREA:
                        logger.debug(f"Mask too small ({mask_area} px), skipping")
                        continue

                    # Encode mask with RLE
                    mask_rle = encode_rle(mask)

                    segment_data = {
                        "detection_index": det_idx,
                        "class": detection.get("class", "unknown"),
                        "confidence": detection.get("confidence", 0.0),
                        "mask_rle": mask_rle,
                        "mask_area_pixels": mask_area,
                        "stability_score": float(stability_score),
                    }

                    frame_masks.append(segment_data)

                except Exception as e:
                    logger.warning(f"Error segmenting detection {det_idx}: {e}")
                    continue

            segmentation[frame_num] = frame_masks

            if (idx + 1) % 5 == 0:
                total_masks = sum(len(m) for m in segmentation.values())
                logger.info(f"Processed {idx + 1} frames with {total_masks} total masks")

        logger.info(f"SAM2 segmentation complete. Generated {sum(len(m) for m in segmentation.values())} masks")
        return segmentation

    except Exception as e:
        logger.error(f"Error in SAM2 segmentation: {e}")
        return {}


def filter_masks_by_area(
    masks: Dict[int, List[Dict]],
    min_area: int,
    max_area: int = None
) -> Dict[int, List[Dict]]:
    """
    Filter masks by area size

    Args:
        masks: Segmentation results
        min_area: Minimum pixel count
        max_area: Maximum pixel count (None = unlimited)

    Returns:
        Filtered masks
    """
    filtered = {}

    for frame_num, frame_masks in masks.items():
        filtered[frame_num] = [
            mask for mask in frame_masks
            if (mask["mask_area_pixels"] >= min_area and
                (max_area is None or mask["mask_area_pixels"] <= max_area))
        ]

    return filtered


def get_segmentation_statistics(
    masks: Dict[int, List[Dict]]
) -> Dict[str, Any]:
    """
    Calculate statistics from segmentation masks

    Args:
        masks: Segmentation results

    Returns:
        Statistics dictionary
    """
    total_masks = sum(len(m) for m in masks.values())
    frames_with_masks = len([f for f in masks.values() if len(f) > 0])

    all_areas = [
        mask["mask_area_pixels"]
        for frame_masks in masks.values()
        for mask in frame_masks
    ]

    avg_area = sum(all_areas) / len(all_areas) if all_areas else 0
    avg_confidence = sum(
        mask["confidence"]
        for frame_masks in masks.values()
        for mask in frame_masks
    ) / total_masks if total_masks > 0 else 0

    return {
        "total_masks": total_masks,
        "frames_with_masks": frames_with_masks,
        "average_mask_area": avg_area,
        "average_stability_score": sum(
            mask.get("stability_score", 0)
            for frame_masks in masks.values()
            for mask in frame_masks
        ) / total_masks if total_masks > 0 else 0,
        "average_confidence": avg_confidence,
    }
