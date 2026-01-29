"""
Google Gemini AI Integration
Scene Analysis & Understanding
Video Reframer
"""

from __future__ import annotations
import logging
import os
import json
from typing import Dict, List, Any

try:
    import google.generativeai as genai
except ImportError:
    genai = None
from config.ai_config import (
    GEMINI_MODEL,
    GEMINI_TEMPERATURE,
    GEMINI_MAX_TOKENS,
    GEMINI_TOP_P,
)

logger = logging.getLogger(__name__)

# Global Gemini client
_genai_client = None


def init_gemini():
    """
    Initialize Gemini API client

    Returns:
        True if initialized successfully
    """
    global _genai_client

    try:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            logger.error("GEMINI_API_KEY not set")
            return False

        genai.configure(api_key=api_key)
        _genai_client = genai.GenerativeModel(GEMINI_MODEL)

        logger.info(f"Gemini initialized with model: {GEMINI_MODEL}")
        return True

    except Exception as e:
        logger.error(f"Error initializing Gemini: {e}")
        return False


async def analyze_video_with_gemini(
    video_path: str,
) -> Dict[str, Any]:
    """
    Analyze video with Gemini 2.0 Flash for scene understanding

    Args:
        video_path: Path to video file

    Returns:
        Scene analysis data
    """
    logger.info(f"Analyzing video with Gemini: {video_path}")

    try:
        if not _genai_client:
            if not init_gemini():
                return {"error": "Gemini not initialized"}

        # For video analysis, we need to send the video file
        # Note: Gemini Vision API can process video files directly

        prompt = """
        Analyze this video and provide:
        1. Scene description: What happens in this video?
        2. Key moments: When are the important events?
        3. Objects: What objects are visible?
        4. People: How many people, what are they doing?
        5. Overall purpose: What is the video about?

        Provide response as JSON with these fields:
        {
            "description": "...",
            "key_moments": [...],
            "objects": [...],
            "people_count": 0,
            "people_activities": [...],
            "purpose": "...",
            "duration_seconds": 0,
            "scenes": [...]
        }
        """

        # Upload video file
        video_file = genai.upload_file(video_path)

        # Generate analysis
        response = _genai_client.generate_content(
            [
                prompt,
                video_file,
            ],
            generation_config=genai.types.GenerationConfig(
                temperature=GEMINI_TEMPERATURE,
                max_output_tokens=GEMINI_MAX_TOKENS,
                top_p=GEMINI_TOP_P,
            ),
        )

        # Parse response
        response_text = response.text

        # Try to extract JSON from response
        try:
            # Look for JSON in response
            if "{" in response_text:
                json_start = response_text.find("{")
                json_end = response_text.rfind("}") + 1
                json_str = response_text[json_start:json_end]
                analysis = json.loads(json_str)
            else:
                analysis = {
                    "description": response_text,
                    "raw_response": response_text,
                }
        except json.JSONDecodeError:
            analysis = {
                "description": response_text,
                "raw_response": response_text,
            }

        logger.info("Gemini analysis complete")
        return analysis

    except Exception as e:
        logger.error(f"Error in Gemini analysis: {e}")
        return {"error": str(e)}


async def analyze_frame_with_gemini(
    frame_base64: str,
    prompt: str = None,
) -> Dict[str, Any]:
    """
    Analyze single frame with Gemini Vision

    Args:
        frame_base64: Base64 encoded image
        prompt: Custom analysis prompt

    Returns:
        Analysis result
    """
    logger.info("Analyzing frame with Gemini Vision")

    try:
        if not _genai_client:
            if not init_gemini():
                return {"error": "Gemini not initialized"}

        if prompt is None:
            prompt = """
            Analyze this image and provide:
            1. Objects detected
            2. People visible (count and activities)
            3. Scene description
            4. Confidence in analysis (0-1)

            Respond as JSON:
            {
                "objects": [...],
                "people_count": 0,
                "people_activities": [...],
                "scene_description": "...",
                "confidence": 0.0
            }
            """

        # Create image object from base64
        import base64
        image_bytes = base64.b64decode(frame_base64)

        image = genai.types.ContentDict(
            mime_type="image/png",
            data=image_bytes,
        )

        # Generate analysis
        response = _genai_client.generate_content(
            [prompt, image],
            generation_config=genai.types.GenerationConfig(
                temperature=GEMINI_TEMPERATURE,
                max_output_tokens=GEMINI_MAX_TOKENS,
            ),
        )

        response_text = response.text

        # Try to parse JSON
        try:
            if "{" in response_text:
                json_start = response_text.find("{")
                json_end = response_text.rfind("}") + 1
                json_str = response_text[json_start:json_end]
                analysis = json.loads(json_str)
            else:
                analysis = {"description": response_text}
        except json.JSONDecodeError:
            analysis = {"description": response_text}

        return analysis

    except Exception as e:
        logger.error(f"Error in Gemini Vision analysis: {e}")
        return {"error": str(e)}


async def batch_analyze_frames(
    frames_base64: List[str],
    prompt: str = None,
) -> Dict[int, Dict[str, Any]]:
    """
    Analyze multiple frames with Gemini

    Args:
        frames_base64: List of base64 encoded images
        prompt: Analysis prompt

    Returns:
        {frame_index: analysis_result}
    """
    logger.info(f"Analyzing {len(frames_base64)} frames with Gemini")

    results = {}

    for idx, frame_b64 in enumerate(frames_base64):
        analysis = await analyze_frame_with_gemini(frame_b64, prompt)
        results[idx] = analysis

        if (idx + 1) % 5 == 0:
            logger.info(f"Analyzed {idx + 1}/{len(frames_base64)} frames")

    return results


def create_scene_summary(
    detections: Dict[int, List[Dict]],
    tracks: Dict[str, Any],
    gemini_analysis: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Create summary combining detections, tracking, and Gemini analysis

    Args:
        detections: YOLO detection results
        tracks: ByteTrack results
        gemini_analysis: Gemini analysis results

    Returns:
        Combined scene summary
    """
    summary = {
        "detection_summary": {
            "total_detections": sum(len(d) for d in detections.values()),
            "frames_with_detections": len([f for f in detections.values() if len(f) > 0]),
        },
        "tracking_summary": {
            "total_tracks": len(tracks),
            "average_track_duration": sum(t.get("duration_seconds", 0) for t in tracks.values()) / len(tracks) if tracks else 0,
        },
        "gemini_analysis": gemini_analysis,
    }

    return summary
