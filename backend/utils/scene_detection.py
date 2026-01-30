"""
FFmpeg Scene Detection
Identifies scene changes and extracts key frames
"""

import subprocess
import json
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)


def detect_scenes(video_path: str, threshold: float = 0.4) -> dict:
    """
    Detect scene changes in video using FFmpeg.

    Args:
        video_path: Path to video file
        threshold: Scene detection threshold (0-1, higher = more sensitive)

    Returns:
        Dict with scenes and key frames
    """
    try:
        logger.info(f"[SceneDetection] Analyzing: {video_path}")

        # Get video metadata
        metadata = get_video_metadata(video_path)
        fps = metadata.get("fps", 30)
        duration = metadata.get("duration", 0)
        total_frames = int(duration * fps)

        logger.info(f"[SceneDetection] Video: {duration:.2f}s, {total_frames} frames @ {fps}fps")

        # Run scene detection
        scenes = extract_scene_boundaries(video_path, threshold)

        # Extract key frames from each scene
        key_frames = extract_key_frames(video_path, scenes)

        result = {
            "status": "success",
            "metadata": {
                "duration_seconds": duration,
                "fps": fps,
                "total_frames": total_frames
            },
            "scenes": scenes,
            "key_frames": key_frames,
            "scene_count": len(scenes)
        }

        logger.info(f"[SceneDetection] Detected {len(scenes)} scenes")
        return result

    except Exception as e:
        logger.error(f"[SceneDetection] Error: {e}", exc_info=True)
        return {"status": "failed", "error": str(e)}


def get_video_metadata(video_path: str) -> dict:
    """Get video metadata using ffprobe."""
    try:
        cmd = [
            "ffprobe", "-v", "error",
            "-select_streams", "v:0",
            "-show_entries", "stream=r_frame_rate,duration",
            "-show_entries", "format=duration",
            "-of", "json",
            video_path
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        data = json.loads(result.stdout)

        # Get FPS
        fps = 30  # default
        if data.get("streams"):
            frame_rate = data["streams"][0].get("r_frame_rate", "30/1")
            if "/" in frame_rate:
                num, den = map(float, frame_rate.split("/"))
                fps = num / den

        # Get duration
        duration = float(data.get("format", {}).get("duration", 0))
        if not duration and data.get("streams"):
            duration = float(data["streams"][0].get("duration", 0))

        return {"fps": fps, "duration": duration}

    except Exception as e:
        logger.warning(f"[Metadata] Error: {e}")
        return {"fps": 30, "duration": 0}


def extract_scene_boundaries(video_path: str, threshold: float) -> list:
    """
    Detect scene changes using FFmpeg's scene filter.

    Returns list of scenes with start/end frames
    """
    try:
        # Get metadata first
        metadata = get_video_metadata(video_path)
        fps = metadata.get("fps", 30)

        # Use FFmpeg scene detection filter
        cmd = [
            "ffmpeg", "-i", video_path,
            "-vf", f"select='gt(scene\\,{threshold})',showinfo",
            "-vsync", "0",
            "-f", "null", "-"
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

        # Parse scene transitions from stderr
        scenes = []
        current_frame = 0

        for line in result.stderr.split("\n"):
            if "Parsed_showinfo" in line and "pts_time:" in line:
                # Extract timestamp
                try:
                    import re
                    match = re.search(r"pts_time:([\d.]+)", line)
                    if match:
                        time_s = float(match.group(1))
                        frame_num = int(time_s * fps)

                        if frame_num > current_frame + int(fps):  # At least 1 second apart
                            if scenes:
                                scenes[-1]["end_frame"] = frame_num
                                scenes[-1]["end_second"] = time_s
                            scenes.append({
                                "scene_id": len(scenes) + 1,
                                "start_frame": frame_num,
                                "start_second": time_s,
                                "end_frame": None,
                                "end_second": None
                            })
                            current_frame = frame_num
                except:
                    pass

        # If no scenes detected, return whole video as one scene
        if not scenes:
            metadata = get_video_metadata(video_path)
            duration = metadata.get("duration", 0)
            total_frames = int(duration * fps)
            scenes = [{
                "scene_id": 1,
                "start_frame": 0,
                "start_second": 0,
                "end_frame": total_frames,
                "end_second": duration
            }]
        else:
            # Set last scene's end
            metadata = get_video_metadata(video_path)
            duration = metadata.get("duration", 0)
            total_frames = int(duration * fps)
            scenes[-1]["end_frame"] = total_frames
            scenes[-1]["end_second"] = duration

        logger.info(f"[SceneDetection] Found {len(scenes)} scenes")
        return scenes

    except Exception as e:
        logger.warning(f"[SceneDetection] Scene detection failed: {e}")
        return []


def extract_key_frames(video_path: str, scenes: list) -> dict:
    """
    Extract middle frame from each scene as key frame.

    Returns dict mapping scene_id to frame info
    """
    try:
        key_frames = {}

        for scene in scenes:
            scene_id = scene["scene_id"]
            start_frame = scene.get("start_frame", 0)
            end_frame = scene.get("end_frame", start_frame + 1)

            # Get middle frame
            middle_frame = (start_frame + end_frame) // 2
            start_second = scene.get("start_second", 0)
            end_second = scene.get("end_second", 0)
            middle_second = (start_second + end_second) / 2

            key_frames[f"scene_{scene_id}"] = {
                "frame": middle_frame,
                "second": middle_second,
                "start_frame": start_frame,
                "end_frame": end_frame,
                "start_second": start_second,
                "end_second": end_second
            }

        logger.info(f"[KeyFrames] Extracted {len(key_frames)} key frames")
        return key_frames

    except Exception as e:
        logger.error(f"[KeyFrames] Error: {e}")
        return {}


def get_frames_for_timestamp_range(start_second: float, end_second: float, fps: float) -> dict:
    """
    Convert time range to frame range.

    Returns: {"start_frame": int, "end_frame": int, "frame_count": int}
    """
    start_frame = int(start_second * fps)
    end_frame = int(end_second * fps)
    frame_count = end_frame - start_frame + 1

    return {
        "start_frame": start_frame,
        "end_frame": end_frame,
        "frame_count": frame_count,
        "frame_range": f"frame_{start_frame} to frame_{end_frame}"
    }
