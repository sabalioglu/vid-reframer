"""
Frame Extraction and Visualization
Extracts key frames from video with YOLO detection annotations
"""

import logging
import cv2
import numpy as np
import os
from pathlib import Path
from typing import Dict, List, Tuple

logger = logging.getLogger(__name__)


def extract_frames_with_detections(
    video_path: str,
    detections: dict,
    output_dir: str = None,
    max_frames: int = None
) -> dict:
    """
    Extract frames from video with YOLO detections drawn on them.

    Args:
        video_path: Path to video file
        detections: Dict from verify_gemini_products with frame indices
        output_dir: Directory to save annotated frames (optional)
        max_frames: Maximum number of frames to extract (for preview)

    Returns:
        Dict with frame data and metadata
    """
    try:
        logger.info(f"[FrameExtractor] Extracting frames with detections from {video_path}")

        # Open video
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            logger.error(f"[FrameExtractor] Failed to open video: {video_path}")
            return {"status": "failed", "error": "Could not open video"}

        # Get video properties
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        logger.info(f"[FrameExtractor] Video: {width}x{height} @ {fps}fps, {total_frames} frames")

        # Parse frame indices from detections
        frame_indices = []
        for frame_key in detections.keys():
            if frame_key.startswith("frame_"):
                try:
                    frame_idx = int(frame_key.split("_")[1])
                    frame_indices.append(frame_idx)
                except ValueError:
                    continue

        frame_indices = sorted(set(frame_indices))
        logger.info(f"[FrameExtractor] Found {len(frame_indices)} frames with detections")

        # Limit frames if requested
        if max_frames and len(frame_indices) > max_frames:
            # Sample frames evenly
            step = len(frame_indices) // max_frames
            frame_indices = frame_indices[::step][:max_frames]
            logger.info(f"[FrameExtractor] Limited to {len(frame_indices)} frames for preview")

        # Create output directory if needed
        if output_dir:
            Path(output_dir).mkdir(parents=True, exist_ok=True)
            logger.info(f"[FrameExtractor] Output directory: {output_dir}")

        extracted_frames = {}

        for frame_idx in frame_indices:
            try:
                # Seek to frame
                cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
                ret, frame = cap.read()

                if not ret:
                    logger.warning(f"[FrameExtractor] Failed to read frame {frame_idx}")
                    continue

                # Get detections for this frame
                frame_key = f"frame_{frame_idx}"
                frame_detections = detections.get(frame_key, [])

                # Draw detections on frame
                annotated_frame = frame.copy()
                for detection in frame_detections:
                    bbox = detection.get("bbox", {})
                    class_name = detection.get("class_name", "unknown")
                    confidence = detection.get("confidence", 0)

                    x1 = int(bbox.get("x1", 0))
                    y1 = int(bbox.get("y1", 0))
                    x2 = int(bbox.get("x2", 0))
                    y2 = int(bbox.get("y2", 0))

                    # Draw bounding box
                    cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), (0, 255, 0), 2)

                    # Draw label
                    label = f"{class_name} {confidence:.2f}"
                    cv2.putText(annotated_frame, label, (x1, y1 - 10),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

                # Calculate timestamp
                timestamp_s = frame_idx / fps if fps > 0 else 0
                timestamp_ms = int(timestamp_s * 1000)

                # Save frame if output dir specified
                frame_path = None
                if output_dir:
                    frame_path = os.path.join(output_dir, f"frame_{frame_idx:06d}_{timestamp_s:.2f}s.jpg")
                    cv2.imwrite(frame_path, annotated_frame)
                    logger.info(f"[FrameExtractor] Saved frame {frame_idx} to {frame_path}")

                # Store frame info
                extracted_frames[frame_idx] = {
                    "frame_number": frame_idx,
                    "timestamp_s": timestamp_s,
                    "timestamp_ms": timestamp_ms,
                    "detection_count": len(frame_detections),
                    "detections": frame_detections,
                    "frame_path": frame_path,
                    "frame_shape": annotated_frame.shape,
                    "base64": None  # Will be filled if needed
                }

            except Exception as e:
                logger.warning(f"[FrameExtractor] Error processing frame {frame_idx}: {e}")
                continue

        cap.release()

        # Create timeline data
        timeline = create_detection_timeline(extracted_frames, fps)

        result = {
            "status": "success",
            "total_frames_extracted": len(extracted_frames),
            "frames": extracted_frames,
            "metadata": {
                "video_fps": fps,
                "video_resolution": f"{width}x{height}",
                "total_video_frames": total_frames,
                "detected_frames_count": len(detections)
            },
            "timeline": timeline
        }

        logger.info(f"[FrameExtractor] ✅ Extracted {len(extracted_frames)} annotated frames")
        return result

    except Exception as e:
        logger.error(f"[FrameExtractor] Error: {e}", exc_info=True)
        return {
            "status": "failed",
            "error": str(e)
        }


def create_detection_timeline(frames: dict, fps: float) -> List[Dict]:
    """
    Create a timeline of detections across the video.

    Returns list of timeline events with detection information
    """
    try:
        timeline = []

        for frame_idx in sorted(frames.keys()):
            frame_data = frames[frame_idx]
            timestamp_s = frame_data["timestamp_s"]

            # Aggregate detections by class
            class_counts = {}
            for detection in frame_data["detections"]:
                class_name = detection.get("class_name", "unknown")
                class_counts[class_name] = class_counts.get(class_name, 0) + 1

            if class_counts:
                timeline.append({
                    "frame": frame_idx,
                    "timestamp_s": timestamp_s,
                    "timestamp_ms": frame_data["timestamp_ms"],
                    "detections_summary": class_counts,
                    "total_detections": frame_data["detection_count"]
                })

        return timeline

    except Exception as e:
        logger.error(f"[Timeline] Error: {e}")
        return []


def get_keyframes(detections: dict, method: str = "diverse") -> List[int]:
    """
    Select representative keyframes from detected frames.

    Args:
        detections: Dict from verify_gemini_products
        method: "diverse" (spread across video) or "high_confidence" (best matches)

    Returns:
        List of frame indices to highlight
    """
    frame_indices = []

    for frame_key in detections.keys():
        if frame_key.startswith("frame_"):
            try:
                frame_idx = int(frame_key.split("_")[1])
                frame_indices.append(frame_idx)
            except ValueError:
                continue

    if not frame_indices:
        return []

    frame_indices = sorted(set(frame_indices))

    if method == "diverse":
        # Return evenly spaced frames (max 5)
        if len(frame_indices) <= 5:
            return frame_indices
        step = len(frame_indices) // 5
        return frame_indices[::step][:5]

    elif method == "high_confidence":
        # Return frames with highest confidence detections
        frame_scores = {}
        for frame_idx in frame_indices:
            frame_key = f"frame_{frame_idx}"
            frame_detections = detections.get(frame_key, [])
            avg_confidence = np.mean([d.get("confidence", 0) for d in frame_detections]) if frame_detections else 0
            frame_scores[frame_idx] = avg_confidence

        # Sort by confidence and return top 5
        top_frames = sorted(frame_scores.items(), key=lambda x: x[1], reverse=True)[:5]
        return [f[0] for f in top_frames]

    return frame_indices[:5]


def encode_frame_to_base64(frame_path: str) -> str:
    """
    Encode a frame image to base64 for frontend display.
    """
    try:
        import base64
        with open(frame_path, "rb") as f:
            frame_data = f.read()
        return base64.b64encode(frame_data).decode("utf-8")
    except Exception as e:
        logger.error(f"[FrameEncoder] Error encoding frame: {e}")
        return None
