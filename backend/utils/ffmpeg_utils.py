"""
FFmpeg Utilities for Frame Extraction
Video Reframer
"""

from __future__ import annotations
import os
import logging
from typing import List, Tuple, Any
import subprocess
import json

try:
    import cv2
    import numpy as np
except ImportError:
    cv2 = None
    np = None

from config.ai_config import (
    FRAME_EXTRACTION_FPS,
    FRAME_EXTRACTION_FORMAT,
    TEMP_FRAME_DIR,
)

logger = logging.getLogger(__name__)


def get_video_metadata(video_path: str) -> dict:
    """
    Get video metadata using ffprobe

    Returns:
        dict with: duration, width, height, fps, codec, total_frames
    """
    try:
        cmd = [
            "ffprobe",
            "-v", "error",
            "-select_streams", "v:0",
            "-show_entries", "stream=width,height,r_frame_rate,duration,codec_name",
            "-show_entries", "format=duration",
            "-of", "json",
            video_path
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        data = json.loads(result.stdout)

        stream = data['streams'][0]
        fmt = data.get('format', {})

        width = stream.get('width', 0)
        height = stream.get('height', 0)

        # Parse frame rate
        fps_str = stream.get('r_frame_rate', '30/1')
        num, den = map(float, fps_str.split('/'))
        fps = num / den

        # Duration from format or stream
        duration = float(fmt.get('duration', stream.get('duration', 0)))
        total_frames = int(duration * fps)

        codec = stream.get('codec_name', 'unknown')

        logger.info(f"Video metadata: {width}x{height} @ {fps:.2f}fps, {duration:.2f}s, {total_frames} frames")

        return {
            'width': width,
            'height': height,
            'fps': fps,
            'duration': duration,
            'total_frames': total_frames,
            'codec': codec,
        }

    except Exception as e:
        logger.error(f"Error getting video metadata: {e}")
        return {}


def extract_frames(
    video_path: str,
    sample_rate: int = 1,
    max_frames: int = None,
):
    """
    Extract frames from video file using ffmpeg

    Args:
        video_path: Path to video file
        sample_rate: Extract every Nth frame (1 = all frames)
        max_frames: Maximum frames to extract (None = all)

    Returns:
        List of (frame_number, frame_array) tuples
    """
    logger.info(f"Extracting frames from {video_path} (sample_rate={sample_rate})")

    frames = []
    frame_count = 0
    extracted_count = 0

    try:
        # Use OpenCV for frame extraction
        cap = cv2.VideoCapture(video_path)

        if not cap.isOpened():
            logger.error(f"Cannot open video: {video_path}")
            return []

        while True:
            ret, frame = cap.read()

            if not ret:
                break

            # Sample frames
            if frame_count % sample_rate == 0:
                # Convert BGR to RGB if needed
                if FRAME_EXTRACTION_FORMAT == "RGB":
                    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

                frames.append((frame_count, frame))
                extracted_count += 1

                if max_frames and extracted_count >= max_frames:
                    break

            frame_count += 1

        cap.release()

        logger.info(f"Extracted {extracted_count} frames from {frame_count} total frames")
        return frames

    except Exception as e:
        logger.error(f"Error extracting frames: {e}")
        return []


def encode_frames_to_base64_batch(
    frames: List,
) -> List[str]:
    """
    Encode multiple frames to base64 strings (for Gemini API)

    Args:
        frames: List of numpy arrays (frames)

    Returns:
        List of base64 encoded strings
    """
    import base64
    from io import BytesIO
    from PIL import Image

    encoded = []

    try:
        for frame in frames:
            # Convert to PIL Image
            img = Image.fromarray(frame)

            # Encode to PNG in memory
            buffer = BytesIO()
            img.save(buffer, format='PNG')

            # Base64 encode
            b64_str = base64.b64encode(buffer.getvalue()).decode('utf-8')
            encoded.append(b64_str)

    except Exception as e:
        logger.error(f"Error encoding frames: {e}")

    return encoded


def frames_to_video(
    frames: List[Tuple[int, Any]],
    output_path: str,
    fps: float = 30.0,
    codec: str = "mp4v"
) -> bool:
    """
    Convert frames back to video file

    Args:
        frames: List of (frame_number, frame_array) tuples
        output_path: Output video file path
        fps: Frames per second
        codec: Video codec (mp4v, h264, etc.)

    Returns:
        True if successful, False otherwise
    """
    try:
        if not frames:
            logger.error("No frames to write")
            return False

        _, first_frame = frames[0]
        height, width = first_frame.shape[:2]

        # Create video writer
        fourcc = cv2.VideoWriter_fourcc(*codec)
        out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

        if not out.isOpened():
            logger.error(f"Cannot create video writer for {output_path}")
            return False

        # Write all frames
        for _, frame in frames:
            # Convert RGB back to BGR for OpenCV
            if len(frame.shape) == 3 and frame.shape[2] == 3:
                frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)

            out.write(frame)

        out.release()
        logger.info(f"Video written to {output_path}")
        return True

    except Exception as e:
        logger.error(f"Error writing video: {e}")
        return False


def resize_frame(
    frame: Any,
    target_size: int = 640
) -> Any:
    """
    Resize frame while maintaining aspect ratio

    Args:
        frame: Input frame
        target_size: Target size (for YOLO input)

    Returns:
        Resized frame
    """
    h, w = frame.shape[:2]
    scale = target_size / max(h, w)

    new_h, new_w = int(h * scale), int(w * scale)
    resized = cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_LINEAR)

    return resized


def create_temp_dir() -> str:
    """Create temporary directory for frames"""
    os.makedirs(TEMP_FRAME_DIR, exist_ok=True)
    return TEMP_FRAME_DIR


def cleanup_temp_dir() -> None:
    """Clean up temporary frame directory"""
    try:
        import shutil
        if os.path.exists(TEMP_FRAME_DIR):
            shutil.rmtree(TEMP_FRAME_DIR)
            logger.info(f"Cleaned up {TEMP_FRAME_DIR}")
    except Exception as e:
        logger.warning(f"Error cleaning up temp dir: {e}")
