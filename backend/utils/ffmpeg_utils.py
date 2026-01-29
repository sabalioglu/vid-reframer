import logging
import subprocess
import numpy as np

logger = logging.getLogger(__name__)


def extract_frames(video_path: str, sample_rate: int = 1) -> list:
    """
    Extract frames from video file using FFmpeg.

    Args:
        video_path: Path to MP4 video file
        sample_rate: Extract every Nth frame

    Returns:
        List of numpy arrays (frames)
    """
    frames = []

    try:
        logger.info(f"Opening video: {video_path}")

        # Get video properties using ffmpeg in verbose mode
        cmd = [
            "ffmpeg",
            "-i", video_path,
            "-f", "null",
            "-"
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        ffmpeg_output = result.stderr + result.stdout

        # Parse dimensions from ffmpeg output
        import re
        dim_match = re.search(r'(\d+)x(\d+)', ffmpeg_output)
        if not dim_match:
            logger.error(f"Could not determine video dimensions from ffmpeg output")
            logger.error(f"FFmpeg output:\n{ffmpeg_output[:500]}")
            return frames

        width = int(dim_match.group(1))
        height = int(dim_match.group(2))
        logger.info(f"Video: {width}x{height}")

        # Extract frames via FFmpeg pipe
        extract_cmd = [
            "ffmpeg",
            "-i", video_path,
            "-vf", f"fps=1/{sample_rate}",
            "-f", "rawvideo",
            "-pix_fmt", "bgr24",
            "-loglevel", "error",
            "-"
        ]

        logger.info(f"Extracting frames...")
        process = subprocess.Popen(
            extract_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

        frame_size = width * height * 3
        frame_count = 0
        chunk_size = 1024 * 1024  # Read 1MB at a time

        buffer = b""

        while True:
            chunk = process.stdout.read(chunk_size)
            if not chunk:
                # Process any remaining data
                if buffer:
                    remaining = len(buffer) % frame_size
                    if remaining > 0:
                        buffer = buffer[:-remaining]

                    # Process final frames
                    for i in range(0, len(buffer), frame_size):
                        frame_data = buffer[i:i+frame_size]
                        if len(frame_data) == frame_size:
                            frame = np.frombuffer(frame_data, dtype=np.uint8)
                            frame = frame.reshape((height, width, 3))
                            frames.append(frame)
                break

            buffer += chunk

            # Extract complete frames from buffer
            while len(buffer) >= frame_size:
                frame_data = buffer[:frame_size]
                buffer = buffer[frame_size:]

                try:
                    frame = np.frombuffer(frame_data, dtype=np.uint8)
                    frame = frame.reshape((height, width, 3))
                    frames.append(frame)
                    frame_count += 1

                    if frame_count % 10 == 0:
                        logger.debug(f"Extracted {frame_count} frames")
                except Exception as e:
                    logger.warning(f"Error processing frame: {e}")

        process.wait()
        logger.info(f"Extracted {len(frames)} frames")

    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)

    return frames


def get_video_metadata(video_path: str) -> dict:
    """
    Get metadata from video file.
    """
    metadata = {
        "duration": 0,
        "fps": 30,
        "width": 0,
        "height": 0,
        "frames": 0
    }

    try:
        import re

        # Get metadata using ffmpeg
        cmd = ["ffmpeg", "-i", video_path]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        output = result.stderr + result.stdout

        # Parse resolution
        dim_match = re.search(r'(\d+)x(\d+)', output)
        if dim_match:
            metadata["width"] = int(dim_match.group(1))
            metadata["height"] = int(dim_match.group(2))

        # Parse duration
        dur_match = re.search(r'Duration: (\d+):(\d+):(\d+\.\d+)', output)
        if dur_match:
            h, m, s = int(dur_match.group(1)), int(dur_match.group(2)), float(dur_match.group(3))
            metadata["duration"] = round(h * 3600 + m * 60 + s, 2)

        # Parse FPS
        fps_match = re.search(r'(\d+(?:\.\d+)?) fps', output)
        if fps_match:
            metadata["fps"] = int(float(fps_match.group(1)))

        if metadata["duration"] > 0 and metadata["fps"] > 0:
            metadata["frames"] = int(metadata["duration"] * metadata["fps"])

        logger.info(f"Metadata: {metadata}")

    except Exception as e:
        logger.error(f"Error getting metadata: {e}")

    return metadata
