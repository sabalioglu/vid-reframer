import logging
import imageio
import os

logger = logging.getLogger(__name__)


def extract_frames(video_path: str, sample_rate: int = 1) -> list:
    """
    Extract frames from video file using imageio.

    Args:
        video_path: Path to MP4 video file
        sample_rate: Extract every Nth frame (1 = all, 2 = every 2nd, etc.)

    Returns:
        List of numpy arrays (frames in RGB format)
    """
    frames = []

    try:
        logger.info(f"[Extract] Opening video: {video_path}")
        logger.info(f"[Extract] File exists: {os.path.exists(video_path)}")

        # Validate file exists and is readable
        if not os.path.exists(video_path):
            logger.error(f"[Extract] ❌ Video file not found: {video_path}")
            return frames

        if not os.path.isfile(video_path):
            logger.error(f"[Extract] ❌ Path is not a file: {video_path}")
            return frames

        # Get file size
        try:
            file_size = os.path.getsize(video_path)
            logger.info(f"[Extract] File size: {file_size / 1024 / 1024:.2f} MB")
            if file_size == 0:
                logger.error(f"[Extract] ❌ File is empty (0 bytes)")
                return frames
        except Exception as e:
            logger.error(f"[Extract] Could not get file size: {e}")
            return frames

        # Check if ffmpeg is available
        import subprocess
        try:
            subprocess.run(["ffmpeg", "-version"], capture_output=True, timeout=5)
            logger.info(f"[Extract] ffmpeg is available")
        except Exception as e:
            logger.error(f"[Extract] ffmpeg not available: {e}")

        # Open video with imageio
        logger.info(f"[Extract] Calling imageio.get_reader()...")
        vid = imageio.get_reader(video_path)
        logger.info(f"[Extract] Video reader created successfully")

        # Get metadata
        meta = vid.get_meta_data()
        logger.info(f"[Extract] Metadata: {meta}")

        fps = meta.get('fps', 30)
        logger.info(f"[Extract] Video FPS: {fps}")

        # Extract frames
        frame_count = 0
        extracted_count = 0

        logger.info(f"[Extract] Starting frame extraction...")
        for frame_idx, frame in enumerate(vid):
            # Extract every Nth frame
            if frame_idx % sample_rate == 0:
                # Convert RGB to BGR for OpenCV compatibility
                if len(frame.shape) == 3 and frame.shape[2] == 3:
                    frame_bgr = frame[:, :, ::-1]  # RGB -> BGR
                else:
                    frame_bgr = frame

                frames.append(frame_bgr)
                extracted_count += 1

                if extracted_count % 10 == 0:
                    logger.debug(f"[Extract] Extracted {extracted_count} frames")

            frame_count += 1

        logger.info(f"[Extract] COMPLETE: {extracted_count} frames from {frame_count} total")

    except ImportError as e:
        logger.error(f"[Extract] Import error - imageio not available: {e}")
    except Exception as e:
        logger.error(f"[Extract] Error extracting frames: {type(e).__name__}: {e}", exc_info=True)

    return frames


def get_video_metadata(video_path: str) -> dict:
    """
    Get metadata from video file.

    Args:
        video_path: Path to MP4 video file

    Returns:
        Dict with duration, fps, width, height, frames
    """
    metadata = {
        "duration": 0,
        "fps": 30,
        "width": 0,
        "height": 0,
        "frames": 0
    }

    try:
        logger.info(f"Getting metadata for: {video_path}")

        vid = imageio.get_reader(video_path)
        meta = vid.get_meta_data()

        # Get dimensions
        if len(vid) > 0:
            first_frame = vid.get_data(0)
            if len(first_frame.shape) >= 2:
                metadata["height"] = first_frame.shape[0]
                metadata["width"] = first_frame.shape[1]

        # Get FPS
        fps = meta.get('fps', 30)
        metadata["fps"] = int(fps) if fps else 30

        # Get duration and frame count
        frame_count = len(vid)
        metadata["frames"] = frame_count
        metadata["duration"] = round(frame_count / metadata["fps"], 2) if metadata["fps"] > 0 else 0

        logger.info(f"Metadata: {metadata}")

    except Exception as e:
        logger.error(f"Error getting metadata: {e}", exc_info=True)

    return metadata
