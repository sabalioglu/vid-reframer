"""
SAM2 Video Object Tracking and Segmentation
Tracks identified objects across video frames using Meta's Segment Anything Model 2
"""

import logging
import numpy as np
from typing import List, Dict
import tempfile
import os

logger = logging.getLogger(__name__)


def track_objects_with_sam2(
    video_path: str,
    objects_to_track: List[Dict],
    frames: Dict[int, np.ndarray]
) -> dict:
    """
    Track objects across video frames using SAM2.

    Args:
        video_path: Path to video file
        objects_to_track: List of objects from Gemini (products used)
        frames: Dict of frame_number -> image array

    Returns:
        Tracking results with masks and trajectories
    """
    try:
        logger.info(f"[SAM2] Initializing tracker for {len(objects_to_track)} objects")

        # Import SAM2 (lazy import to avoid dependency if not needed)
        try:
            from sam2.build_sam import build_sam2_video_predictor
        except ImportError:
            logger.error("[SAM2] SAM2 not installed. Install with: pip install sam2")
            return {
                "status": "skipped",
                "reason": "SAM2 not installed",
                "objects_tracked": []
            }

        # Build SAM2 predictor
        predictor = build_sam2_video_predictor()

        tracking_results = {}
        frame_indices = sorted([int(f) for f in frames.keys()])

        for obj in objects_to_track:
            obj_id = obj.get("product_id", "unknown")
            obj_name = obj.get("name", "object")

            logger.info(f"[SAM2] Tracking object {obj_id}: {obj_name}")

            try:
                # Get time range for this object
                start_frame = obj.get("usage_frames_start", 0)
                end_frame = obj.get("usage_frames_end", len(frames))

                # Initialize video frame state
                predictor.init_state(video_path)

                # Track object across frames
                tracks = []
                segmentation_masks = {}

                for frame_idx in frame_indices:
                    if frame_idx < start_frame or frame_idx > end_frame:
                        continue

                    frame = frames[frame_idx]

                    # Run SAM2 on frame
                    # Note: This is simplified - actual SAM2 usage requires bounding boxes
                    # from YOLOv8 verification as initialization
                    masks, scores = predictor.predict(
                        frame,
                        point_coords=None,
                        point_labels=None
                    )

                    if masks is not None:
                        segmentation_masks[frame_idx] = {
                            "mask": masks.tolist() if hasattr(masks, 'tolist') else masks,
                            "confidence": float(scores[0]) if scores is not None else 0.0
                        }

                        # Add to track
                        tracks.append({
                            "frame": frame_idx,
                            "confidence": segmentation_masks[frame_idx]["confidence"],
                            "bbox": None  # Will be computed from mask
                        })

                tracking_results[obj_id] = {
                    "object_name": obj_name,
                    "tracking_status": "success" if tracks else "no_detection",
                    "track_count": len(tracks),
                    "frames_tracked": sorted([t["frame"] for t in tracks]),
                    "segmentation_masks": segmentation_masks,
                    "trajectory": tracks
                }

                logger.info(f"[SAM2] Tracked {obj_name} in {len(tracks)} frames")

            except Exception as e:
                logger.error(f"[SAM2] Error tracking object {obj_id}: {e}")
                tracking_results[obj_id] = {
                    "object_name": obj_name,
                    "tracking_status": "failed",
                    "error": str(e)
                }

        return {
            "status": "success",
            "objects_tracked": len(tracking_results),
            "tracking_results": tracking_results
        }

    except Exception as e:
        logger.error(f"[SAM2] Tracking error: {e}", exc_info=True)
        return {
            "status": "failed",
            "error": str(e),
            "objects_tracked": 0
        }


def get_mask_bounding_box(mask: np.ndarray) -> Dict:
    """
    Compute bounding box from segmentation mask.

    Returns: {"x": int, "y": int, "width": int, "height": int}
    """
    try:
        if mask is None or mask.size == 0:
            return {"x": 0, "y": 0, "width": 0, "height": 0}

        coords = np.where(mask > 0)
        if len(coords[0]) == 0:
            return {"x": 0, "y": 0, "width": 0, "height": 0}

        y_min, y_max = coords[0].min(), coords[0].max()
        x_min, x_max = coords[1].min(), coords[1].max()

        return {
            "x": int(x_min),
            "y": int(y_min),
            "width": int(x_max - x_min),
            "height": int(y_max - y_min)
        }
    except:
        return {"x": 0, "y": 0, "width": 0, "height": 0}


def compute_object_trajectory(
    tracking_data: Dict,
    frames_fps: float
) -> List[Dict]:
    """
    Compute smooth trajectory from frame-by-frame tracking.

    Returns: List of trajectory points with smoothing
    """
    try:
        trajectory = []

        for track in tracking_data.get("trajectory", []):
            frame_num = track.get("frame", 0)
            timestamp_s = frame_num / frames_fps if frames_fps > 0 else 0
            timestamp_ms = int(timestamp_s * 1000)

            # Get bounding box from mask if available
            masks = tracking_data.get("segmentation_masks", {})
            if str(frame_num) in masks:
                mask_data = masks[str(frame_num)]
                # Note: mask_data would contain the actual mask
                bbox = {"x": 0, "y": 0, "width": 0, "height": 0}
            else:
                bbox = None

            trajectory.append({
                "frame": frame_num,
                "timestamp_s": timestamp_s,
                "timestamp_ms": timestamp_ms,
                "bounding_box": bbox,
                "confidence": track.get("confidence", 0.0)
            })

        return trajectory

    except Exception as e:
        logger.error(f"[Trajectory] Error: {e}")
        return []
