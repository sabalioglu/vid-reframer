"""
Unified Video Analysis Pipeline
Orchestrates: Gemini (semantic) → FFmpeg (scenes) → YOLOv8 (verification) → SAM2 (tracking)
"""

import logging
import os
import tempfile
from typing import Dict, List

logger = logging.getLogger(__name__)


def run_unified_pipeline(video_path: str) -> dict:
    """
    Execute complete video analysis pipeline.

    Pipeline:
    1. Gemini: Temporal semantic analysis (people, products, timeline)
    2. FFmpeg: Scene detection and key frame extraction
    3. YOLOv8: Verification of Gemini-identified products
    4. SAM2: Tracking and segmentation

    Args:
        video_path: Path to video file

    Returns:
        Comprehensive analysis results
    """
    logger.info(f"[Pipeline] Starting unified analysis: {video_path}")

    result = {
        "pipeline_status": "initialized",
        "stages": {},
        "final_output": {}
    }

    try:
        # ==================== STAGE 1: GEMINI (Temporal Semantic Analysis) ====================
        logger.info("[Pipeline] Stage 1: Gemini Temporal Analysis")
        from utils.gemini_utils import analyze_video_with_gemini

        gemini_result = analyze_video_with_gemini(video_path)
        result["stages"]["gemini"] = gemini_result

        if gemini_result.get("status") != "success":
            logger.error(f"[Pipeline] Gemini stage failed: {gemini_result.get('reason')}")
            return result

        gemini_data = gemini_result.get("gemini_analysis", {})
        logger.info(f"[Pipeline] Gemini found: {gemini_data.get('total_unique_people', 0)} people")
        logger.info(f"[Pipeline] Gemini found: {len(gemini_data.get('products', []))} products")

        # ==================== STAGE 2: FFMPEG (Scene Detection) ====================
        logger.info("[Pipeline] Stage 2: FFmpeg Scene Detection")
        from utils.scene_detection import detect_scenes

        scene_result = detect_scenes(video_path, threshold=0.4)
        result["stages"]["scene_detection"] = scene_result

        if scene_result.get("status") != "success":
            logger.warning(f"[Pipeline] Scene detection skipped: {scene_result.get('error')}")
        else:
            logger.info(f"[Pipeline] Detected {scene_result.get('scene_count', 0)} scenes")

        # ==================== STAGE 3: Frame Extraction ====================
        logger.info("[Pipeline] Stage 3: Frame Extraction")
        from utils.ffmpeg_utils import extract_frames

        frames = extract_frames(video_path, sample_rate=1)  # Every frame for tracking
        logger.info(f"[Pipeline] Extracted {len(frames)} frames")

        if not frames:
            logger.error("[Pipeline] Frame extraction failed")
            return result

        # ==================== STAGE 4: YOLOv8 Verification ====================
        logger.info("[Pipeline] Stage 4: YOLOv8 Verification")
        from utils.yolo_utils import verify_gemini_products, get_detection_statistics

        gemini_products = gemini_data.get("products", [])
        yolo_result = verify_gemini_products(frames, gemini_products)
        yolo_stats = get_detection_statistics(yolo_result)

        result["stages"]["yolo_verification"] = {
            "status": "success" if yolo_result else "no_detections",
            "detections": yolo_result,
            "statistics": yolo_stats
        }

        logger.info(f"[Pipeline] YOLO verified {yolo_stats.get('total_detections', 0)} product instances")

        # ==================== STAGE 5: SAM2 Tracking ====================
        logger.info("[Pipeline] Stage 5: SAM2 Tracking")

        sam2_result = run_sam2_if_available(video_path, gemini_products, frames)
        result["stages"]["sam2_tracking"] = sam2_result

        if sam2_result.get("status") == "success":
            logger.info(f"[Pipeline] SAM2 tracked {sam2_result.get('objects_tracked', 0)} objects")
        else:
            logger.info(f"[Pipeline] SAM2 skipped: {sam2_result.get('reason', 'not available')}")

        # ==================== CONSOLIDATE RESULTS ====================
        logger.info("[Pipeline] Consolidating results")

        result["final_output"] = consolidate_results(
            gemini_data=gemini_data,
            scene_data=scene_result.get("scenes", []),
            yolo_data=yolo_result,
            yolo_stats=yolo_stats,
            sam2_data=sam2_result.get("tracking_results", {}),
            video_metadata=scene_result.get("metadata", {})
        )

        result["pipeline_status"] = "completed"
        logger.info("[Pipeline] Analysis complete!")

        return result

    except Exception as e:
        logger.error(f"[Pipeline] Error: {e}", exc_info=True)
        result["pipeline_status"] = "failed"
        result["error"] = str(e)
        return result


def run_sam2_if_available(video_path: str, objects_to_track: List, frames: Dict) -> dict:
    """
    Try to run SAM2 tracking, gracefully fall back if not available.
    """
    try:
        from utils.sam2_tracker import track_objects_with_sam2

        logger.info("[SAM2] Initializing tracking")
        result = track_objects_with_sam2(video_path, objects_to_track, frames)
        return result

    except ImportError:
        logger.info("[SAM2] SAM2 not installed, skipping tracking")
        return {"status": "skipped", "reason": "SAM2 not installed"}
    except Exception as e:
        logger.error(f"[SAM2] Error: {e}")
        return {"status": "skipped", "reason": str(e)}


def consolidate_results(
    gemini_data: dict,
    scene_data: list,
    yolo_data: dict,
    yolo_stats: dict,
    sam2_data: dict,
    video_metadata: dict
) -> dict:
    """
    Consolidate all pipeline stages into unified output.

    Returns comprehensive analysis with:
    - Semantic info (Gemini)
    - Temporal info (FFmpeg scenes)
    - Verification info (YOLOv8)
    - Tracking info (SAM2)
    """
    return {
        "metadata": {
            "total_people": gemini_data.get("total_unique_people", 0),
            "total_products": len(gemini_data.get("products", [])),
            "total_scenes": len(scene_data),
            "video_duration": video_metadata.get("duration_seconds", 0),
            "fps": video_metadata.get("fps", 30),
            "total_frames": video_metadata.get("total_frames", 0)
        },
        "people": gemini_data.get("people", []),
        "products": gemini_data.get("products", []),
        "timeline": gemini_data.get("timeline", []),
        "scenes": scene_data,
        "yolo_verification": {
            "verified_detections": len(yolo_data),
            "total_instances": yolo_stats.get("total_detections", 0),
            "class_distribution": yolo_stats.get("class_distribution", {}),
            "average_confidence": yolo_stats.get("average_confidence", 0)
        },
        "sam2_tracking": sam2_data,
        "summary": {
            "video_summary": gemini_data.get("video_summary", ""),
            "key_events": extract_key_events(gemini_data.get("timeline", [])),
            "products_in_use": [p["name"] for p in gemini_data.get("products", [])]
        }
    }


def extract_key_events(timeline: List[Dict]) -> List[str]:
    """
    Extract important events from timeline for summary.
    """
    try:
        events = []
        for item in timeline:
            if item.get("event"):
                event_str = f"{item.get('second', 0):.1f}s: {item['event']}"
                if event_str not in events:
                    events.append(event_str)
        return events[:10]  # Top 10 events
    except:
        return []
