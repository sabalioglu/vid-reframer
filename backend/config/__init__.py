"""
Video Reframer Configuration Module
"""

from .ai_config import (
    # YOLOv8
    YOLO_MODEL,
    YOLO_CONFIDENCE,
    YOLO_IOU,
    YOLO_DEVICE,
    SAMPLE_EVERY_N_FRAMES,
    # SAM2
    SAM2_MODEL,
    SAM2_GPU_REQUIRED,
    SAM2_BATCH_SIZE,
    # ByteTrack
    BYTETRACK_TRACK_THRESH,
    BYTETRACK_TRACK_BUFFER,
    # Gemini
    GEMINI_MODEL,
    GEMINI_TEMPERATURE,
)

from .modal_config import (
    APP_NAME,
    APP_VERSION,
    MEMORY_MB,
    TIMEOUT_SECONDS,
    GPU_TYPE,
    REQUEST_GPU,
)

__all__ = [
    # AI Config
    "YOLO_MODEL",
    "YOLO_CONFIDENCE",
    "SAM2_MODEL",
    "BYTETRACK_TRACK_THRESH",
    "GEMINI_MODEL",
    # Modal Config
    "APP_NAME",
    "APP_VERSION",
    "MEMORY_MB",
    "TIMEOUT_SECONDS",
]
