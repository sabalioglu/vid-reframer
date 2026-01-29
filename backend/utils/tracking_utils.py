"""
ByteTrack Object Tracking Utilities
Cross-Frame Consistency
Video Reframer
"""

from __future__ import annotations
import logging
from typing import Dict, List, Any, Tuple

try:
    import numpy as np
except ImportError:
    np = None
from config.ai_config import (
    BYTETRACK_TRACK_THRESH,
    BYTETRACK_TRACK_BUFFER,
    BYTETRACK_MATCH_THRESH,
    BYTETRACK_FRAME_RATE,
    BYTETRACK_ASPECT_RATIO_THRESH,
    BYTETRACK_MIN_BOX_AREA,
)

logger = logging.getLogger(__name__)

# Global tracker cache
_bytetrack = None


def load_bytetrack_tracker():
    """
    Load ByteTrack tracker instance

    Returns:
        ByteTrack tracker
    """
    global _bytetrack

    try:
        if _bytetrack is None:
            logger.info("Initializing ByteTrack tracker")

            try:
                from bytetrack import ByteTrack
            except ImportError:
                logger.warning("ByteTrack not installed. Install with: pip install ByteTrack")
                return None

            _bytetrack = ByteTrack(
                track_thresh=BYTETRACK_TRACK_THRESH,
                track_buffer=BYTETRACK_TRACK_BUFFER,
                match_thresh=BYTETRACK_MATCH_THRESH,
                frame_rate=BYTETRACK_FRAME_RATE,
                aspect_ratio_thresh=BYTETRACK_ASPECT_RATIO_THRESH,
                min_box_area=BYTETRACK_MIN_BOX_AREA,
            )

            logger.info("ByteTrack tracker initialized")

        return _bytetrack

    except Exception as e:
        logger.error(f"Error initializing ByteTrack: {e}")
        return None


def detections_to_bytetrack_format(
    detections: Dict[int, List[Dict]]
) -> Dict[int, np.ndarray]:
    """
    Convert YOLO detections to ByteTrack format

    ByteTrack expects: [[x1, y1, x2, y2, confidence], ...]

    Args:
        detections: YOLO detection results

    Returns:
        {frame_number: detection_array}
    """
    formatted = {}

    for frame_num, frame_detections in detections.items():
        dets = []

        for det in frame_detections:
            bbox = det["bbox"]

            # Convert from x, y, width, height to x1, y1, x2, y2
            x1 = bbox["x"]
            y1 = bbox["y"]
            x2 = bbox["x"] + bbox["width"]
            y2 = bbox["y"] + bbox["height"]
            confidence = det["confidence"]

            dets.append([x1, y1, x2, y2, confidence])

        formatted[frame_num] = np.array(dets, dtype=np.float32) if dets else np.empty((0, 5))

    return formatted


def run_bytetrack_tracking(
    detections: Dict[int, List[Dict]],
    frames: List[Tuple[int, np.ndarray]]
) -> Dict[str, Any]:
    """
    Run ByteTrack object tracking across frames

    Args:
        detections: YOLO detection results
        frames: List of (frame_number, frame_array) tuples

    Returns:
        {track_id: trajectory_data}
        Each trajectory: start_frame, end_frame, duration, frames=[...]
    """
    logger.info("Running ByteTrack tracking")

    tracker = load_bytetrack_tracker()

    if tracker is None:
        logger.warning("ByteTrack not available. Returning empty tracking.")
        return {}

    try:
        # Convert detections to ByteTrack format
        detection_array = detections_to_bytetrack_format(detections)

        # Dictionary to store tracks
        tracks_data = {}

        # Process frames in order
        sorted_frames = sorted(frames, key=lambda x: x[0])

        for frame_idx, (frame_num, frame) in enumerate(sorted_frames):
            # Get detections for this frame
            dets = detection_array.get(frame_num, np.empty((0, 5)))

            # Update tracker
            online_targets = tracker.update(dets, frame.shape)

            # Process tracked objects
            for track in online_targets:
                track_id = str(track.track_id)

                # Initialize track if new
                if track_id not in tracks_data:
                    tracks_data[track_id] = {
                        "track_id": track_id,
                        "start_frame": frame_num,
                        "end_frame": frame_num,
                        "frames": [],
                    }

                # Get bounding box from track
                bbox = track.bbox  # [x1, y1, x2, y2]

                track_frame = {
                    "frame_number": frame_num,
                    "timestamp": frame_num / BYTETRACK_FRAME_RATE,  # seconds
                    "bbox": {
                        "x1": float(bbox[0]),
                        "y1": float(bbox[1]),
                        "x2": float(bbox[2]),
                        "y2": float(bbox[3]),
                        "width": float(bbox[2] - bbox[0]),
                        "height": float(bbox[3] - bbox[1]),
                    },
                    "confidence": float(track.score),
                    "is_activated": track.is_activated,
                }

                tracks_data[track_id]["frames"].append(track_frame)
                tracks_data[track_id]["end_frame"] = frame_num

            if (frame_idx + 1) % 10 == 0:
                logger.info(f"Processed {frame_idx + 1}/{len(sorted_frames)} frames, tracking {len(tracks_data)} objects")

        # Calculate statistics for each track
        for track_id, track_data in tracks_data.items():
            frames_list = track_data["frames"]

            track_data["duration_frames"] = track_data["end_frame"] - track_data["start_frame"] + 1
            track_data["duration_seconds"] = track_data["duration_frames"] / BYTETRACK_FRAME_RATE
            track_data["num_frames_tracked"] = len(frames_list)

            # Average confidence
            if frames_list:
                track_data["avg_confidence"] = sum(f["confidence"] for f in frames_list) / len(frames_list)
            else:
                track_data["avg_confidence"] = 0.0

        logger.info(f"ByteTrack complete. Tracked {len(tracks_data)} objects across {len(sorted_frames)} frames")
        return tracks_data

    except Exception as e:
        logger.error(f"Error in ByteTrack tracking: {e}")
        return {}


def filter_tracks_by_duration(
    tracks: Dict[str, Any],
    min_frames: int
) -> Dict[str, Any]:
    """
    Filter tracks that are too short

    Args:
        tracks: Tracking results
        min_frames: Minimum frame count to keep

    Returns:
        Filtered tracks
    """
    filtered = {
        track_id: track_data
        for track_id, track_data in tracks.items()
        if track_data["num_frames_tracked"] >= min_frames
    }

    logger.info(f"Filtered from {len(tracks)} to {len(filtered)} tracks (min {min_frames} frames)")
    return filtered


def calculate_track_velocity(
    track: Dict[str, Any]
) -> Dict[str, float]:
    """
    Calculate average velocity of tracked object

    Args:
        track: Single track data

    Returns:
        {vx: pixels/frame, vy: pixels/frame}
    """
    frames = track["frames"]

    if len(frames) < 2:
        return {"vx": 0.0, "vy": 0.0}

    # Calculate center positions
    centers = []
    for frame in frames:
        bbox = frame["bbox"]
        cx = (bbox["x1"] + bbox["x2"]) / 2
        cy = (bbox["y1"] + bbox["y2"]) / 2
        centers.append((cx, cy))

    # Calculate average velocity
    velocities_x = [centers[i + 1][0] - centers[i][0] for i in range(len(centers) - 1)]
    velocities_y = [centers[i + 1][1] - centers[i][1] for i in range(len(centers) - 1)]

    vx = sum(velocities_x) / len(velocities_x) if velocities_x else 0.0
    vy = sum(velocities_y) / len(velocities_y) if velocities_y else 0.0

    return {"vx": vx, "vy": vy}


def get_tracking_statistics(
    tracks: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Calculate statistics from tracking results

    Args:
        tracks: Tracking results

    Returns:
        Statistics dictionary
    """
    if not tracks:
        return {
            "total_tracks": 0,
            "average_duration": 0.0,
            "average_confidence": 0.0,
        }

    durations = [t["duration_frames"] for t in tracks.values()]
    confidences = [t["avg_confidence"] for t in tracks.values()]

    return {
        "total_tracks": len(tracks),
        "average_duration_frames": sum(durations) / len(durations),
        "average_duration_seconds": sum(t["duration_seconds"] for t in tracks.values()) / len(tracks),
        "average_confidence": sum(confidences) / len(confidences),
        "min_duration": min(durations),
        "max_duration": max(durations),
    }


class SimpleTracker:
    """
    Fallback simple tracker if ByteTrack not available
    Uses simple centroid matching
    """

    def __init__(self, max_distance=50):
        self.max_distance = max_distance
        self.tracks = {}
        self.next_id = 0

    def update(self, detections: List[Dict], frame_num: int) -> Dict[str, Any]:
        """
        Simple centroid-based tracking

        Args:
            detections: List of detection dictionaries
            frame_num: Current frame number

        Returns:
            Updated tracks
        """
        # Calculate centroids of current detections
        current_centroids = []
        for det in detections:
            bbox = det["bbox"]
            cx = bbox["x"] + bbox["width"] / 2
            cy = bbox["y"] + bbox["height"] / 2
            current_centroids.append({"x": cx, "y": cy, "det": det})

        # Update existing tracks or create new ones
        updated_tracks = {}

        for det_cent in current_centroids:
            # Find closest track
            best_track_id = None
            best_distance = self.max_distance

            for track_id, track in self.tracks.items():
                if track["end_frame"] + 5 < frame_num:  # Track too old
                    continue

                last_pos = track["frames"][-1] if track["frames"] else None
                if last_pos:
                    last_cx = last_pos["bbox"]["x"] + last_pos["bbox"]["width"] / 2
                    last_cy = last_pos["bbox"]["y"] + last_pos["bbox"]["height"] / 2

                    distance = ((det_cent["x"] - last_cx) ** 2 + (det_cent["y"] - last_cy) ** 2) ** 0.5

                    if distance < best_distance:
                        best_distance = distance
                        best_track_id = track_id

            # Assign to track or create new
            if best_track_id:
                track_id = best_track_id
            else:
                track_id = str(self.next_id)
                self.next_id += 1
                self.tracks[track_id] = {
                    "track_id": track_id,
                    "start_frame": frame_num,
                    "frames": [],
                }

            # Add frame to track
            self.tracks[track_id]["end_frame"] = frame_num
            self.tracks[track_id]["frames"].append({
                "frame_number": frame_num,
                "bbox": det_cent["det"]["bbox"],
                "confidence": det_cent["det"].get("confidence", 0.0),
            })

            updated_tracks[track_id] = self.tracks[track_id]

        return updated_tracks
