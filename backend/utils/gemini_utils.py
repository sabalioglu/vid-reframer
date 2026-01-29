"""
Gemini Video Analysis - Ground Truth for Person Detection
Uses Google's Gemini Video API to understand video content
"""

import logging
import json
import os
import time
from pathlib import Path

logger = logging.getLogger(__name__)


def analyze_video_with_gemini(video_path: str) -> dict:
    """
    Analyze video with Gemini Video API to extract ground truth data.

    Args:
        video_path: Path to video file

    Returns:
        Dict with person detection ground truth from Gemini
    """
    try:
        import google.generativeai as genai
    except ImportError:
        logger.warning("google-generativeai not installed, skipping Gemini analysis")
        return {"status": "skipped", "reason": "library not available"}

    # Check for API key
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        logger.warning("GOOGLE_API_KEY environment variable not set")
        return {"status": "skipped", "reason": "API key not configured"}

    try:
        genai.configure(api_key=api_key)
        logger.info(f"Gemini API configured")

        # Upload video file
        logger.info(f"[Gemini] Uploading video: {video_path}")
        video_file = genai.upload_file(path=video_path)
        logger.info(f"[Gemini] Video uploaded: {video_file.name}")

        # Wait for video processing
        while video_file.state.name == "PROCESSING":
            logger.info(f"[Gemini] Waiting for video processing...")
            time.sleep(2)
            video_file = genai.get_file(video_file.name)

        if video_file.state.name != "ACTIVE":
            logger.error(f"[Gemini] Video failed to process: {video_file.state.name}")
            return {"status": "failed", "reason": "video processing failed"}

        logger.info(f"[Gemini] Video ready for analysis")

        # Create model and send prompt
        model = genai.GenerativeModel("gemini-2.0-flash")

        prompt = """Analyze this video carefully and provide a detailed JSON response with the following structure:
{
    "total_unique_people": <number>,
    "people": [
        {
            "person_id": <number>,
            "description": "<brief description>",
            "appearances": [
                {
                    "start_second": <float>,
                    "end_second": <float>,
                    "frame_range": "<frame_0 to frame_X>"
                }
            ]
        }
    ],
    "video_summary": "<brief description of scene>",
    "confidence": "<high/medium/low>"
}

Guidelines:
- Count UNIQUE people (same person appearing multiple times = 1 person)
- For each appearance, provide start/end timestamps in seconds
- If frame count is available, estimate frame ranges (assuming 30fps)
- Be conservative: only count clear, distinct human figures
- Ignore reflections, shadows, or partial figures"""

        logger.info(f"[Gemini] Sending analysis request...")
        response = model.generate_content(
            [prompt, video_file],
            generation_config={"temperature": 0.3}
        )

        logger.info(f"[Gemini] Received response")

        # Parse response
        response_text = response.text
        logger.info(f"[Gemini] Raw response: {response_text[:500]}")

        # Extract JSON from response
        result = extract_json_from_response(response_text)

        # Cleanup: delete uploaded file
        try:
            genai.delete_file(video_file.name)
            logger.info(f"[Gemini] Cleaned up uploaded file")
        except Exception as e:
            logger.warning(f"[Gemini] Failed to delete file: {e}")

        return {
            "status": "success",
            "gemini_analysis": result,
            "raw_response": response_text
        }

    except Exception as e:
        logger.error(f"[Gemini] Analysis error: {e}", exc_info=True)
        return {
            "status": "failed",
            "reason": str(e)
        }


def extract_json_from_response(text: str) -> dict:
    """Extract JSON from Gemini response text."""
    try:
        # Try to find JSON block
        import re
        json_match = re.search(r'\{[\s\S]*\}', text)
        if json_match:
            json_str = json_match.group()
            return json.loads(json_str)
    except Exception as e:
        logger.warning(f"Failed to extract JSON: {e}")

    # Fallback: try to parse entire response
    try:
        return json.loads(text)
    except:
        logger.warning("Could not parse Gemini response as JSON")
        return {"status": "parse_error", "raw": text}


def compare_gemini_vs_yolo(gemini_result: dict, yolo_detections: dict) -> dict:
    """
    Compare Gemini ground truth with YOLOv8 detection results.

    Args:
        gemini_result: Output from analyze_video_with_gemini
        yolo_detections: Output from run_yolov8_detection

    Returns:
        Comparison report
    """
    if gemini_result.get("status") != "success":
        return {"comparison_status": "skipped", "reason": "Gemini analysis not available"}

    try:
        gemini_data = gemini_result.get("gemini_analysis", {})
        gemini_person_count = gemini_data.get("total_unique_people", 0)

        # Count YOLOv8 detections
        yolo_person_count = 0
        yolo_frames_with_person = 0

        for frame_id, detections in yolo_detections.items():
            has_person = False
            for detection in detections:
                if detection.get("class_name", "").lower() == "person":
                    yolo_person_count += 1
                    has_person = True
            if has_person:
                yolo_frames_with_person += 1

        return {
            "comparison": {
                "gemini_unique_people": gemini_person_count,
                "yolo_person_detections": yolo_person_count,
                "yolo_frames_with_person": yolo_frames_with_person,
                "note": "Gemini = unique people, YOLOv8 = per-frame detections"
            },
            "gemini_details": gemini_data
        }
    except Exception as e:
        logger.error(f"Comparison error: {e}")
        return {"comparison_status": "error", "reason": str(e)}
