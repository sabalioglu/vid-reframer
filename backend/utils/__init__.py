"""
Video Reframer Utilities
All AI/ML processing modules
"""

from __future__ import annotations

try:
    from .ffmpeg_utils import (
        get_video_metadata,
        extract_frames,
        encode_frames_to_base64_batch,
        frames_to_video,
    )

    from .yolo_utils import (
        load_yolo_model,
        run_yolov8_detection,
        filter_detections_by_class,
        filter_detections_by_confidence,
        get_detection_statistics,
    )

    from .sam2_utils import (
        load_sam2_model,
        run_sam2_segmentation,
        encode_rle,
        decode_rle,
        filter_masks_by_area,
        get_segmentation_statistics,
    )

    from .tracking_utils import (
        load_bytetrack_tracker,
        run_bytetrack_tracking,
        filter_tracks_by_duration,
        calculate_track_velocity,
        get_tracking_statistics,
        SimpleTracker,
    )

    from .db_utils import (
        save_detections,
        save_segmentation_masks,
        save_tracking_trajectories,
        save_scene_analysis,
        update_video_status,
        get_video_metadata as get_video_metadata_db,
        save_processing_job,
        update_processing_job,
    )

    from .gemini_utils import (
        init_gemini,
        analyze_video_with_gemini,
        analyze_frame_with_gemini,
        batch_analyze_frames,
        create_scene_summary,
    )

except ImportError:
    # Fallback if modules not available
    pass

__all__ = [
    # FFmpeg
    "get_video_metadata",
    "extract_frames",
    "encode_frames_to_base64_batch",
    "frames_to_video",
    # YOLO
    "load_yolo_model",
    "run_yolov8_detection",
    "filter_detections_by_class",
    "filter_detections_by_confidence",
    "get_detection_statistics",
    # SAM2
    "load_sam2_model",
    "run_sam2_segmentation",
    "encode_rle",
    "decode_rle",
    "filter_masks_by_area",
    "get_segmentation_statistics",
    # ByteTrack
    "load_bytetrack_tracker",
    "run_bytetrack_tracking",
    "filter_tracks_by_duration",
    "calculate_track_velocity",
    "get_tracking_statistics",
    "SimpleTracker",
    # Database
    "save_detections",
    "save_segmentation_masks",
    "save_tracking_trajectories",
    "save_scene_analysis",
    "update_video_status",
    "get_video_metadata_db",
    "save_processing_job",
    "update_processing_job",
    # Gemini
    "init_gemini",
    "analyze_video_with_gemini",
    "analyze_frame_with_gemini",
    "batch_analyze_frames",
    "create_scene_summary",
]
