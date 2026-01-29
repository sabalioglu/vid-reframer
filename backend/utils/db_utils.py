"""
Database Utilities
Neon PostgreSQL Integration
Video Reframer
"""

from __future__ import annotations
import logging
import json
from typing import Optional, Dict, List, Any

try:
    from asyncpg import Pool
except ImportError:
    Pool = None

from config.ai_config import DB_BATCH_INSERT_SIZE

logger = logging.getLogger(__name__)


async def save_detections(
    db_pool: Pool,
    video_id: str,
    detections: Dict[int, List[Dict]],
    fps: float = 30.0
) -> bool:
    """
    Save YOLO detections to database

    Args:
        db_pool: Database connection pool
        video_id: Video ID
        detections: {frame_number: [detection_objects]}
        fps: Frames per second

    Returns:
        True if successful
    """
    if not db_pool or not detections:
        return False

    try:
        async with db_pool.acquire() as conn:
            # Batch insert detections
            records = []

            for frame_num, frame_dets in detections.items():
                for det in frame_dets:
                    timestamp = frame_num / fps

                    record = (
                        video_id,
                        frame_num,
                        timestamp,
                        json.dumps({
                            "class": det.get("class"),
                            "class_id": det.get("class_id"),
                            "confidence": det.get("confidence"),
                            "bbox": det.get("bbox"),
                        })
                    )

                    records.append(record)

            # Insert in batches
            for i in range(0, len(records), DB_BATCH_INSERT_SIZE):
                batch = records[i:i + DB_BATCH_INSERT_SIZE]

                await conn.executemany("""
                    INSERT INTO detections (video_id, frame_number, timestamp_seconds, detection_data)
                    VALUES ($1, $2, $3, $4)
                """, batch)

        logger.info(f"Saved {len(records)} detections for video {video_id}")
        return True

    except Exception as e:
        logger.error(f"Error saving detections: {e}")
        return False


async def save_segmentation_masks(
    db_pool: Pool,
    video_id: str,
    masks: Dict[int, List[Dict]],
    fps: float = 30.0
) -> bool:
    """
    Save SAM2 segmentation masks to database

    Args:
        db_pool: Database connection pool
        video_id: Video ID
        masks: {frame_number: [mask_objects]}
        fps: Frames per second

    Returns:
        True if successful
    """
    if not db_pool or not masks:
        return False

    try:
        async with db_pool.acquire() as conn:
            records = []

            for frame_num, frame_masks in masks.items():
                for mask in frame_masks:
                    timestamp = frame_num / fps

                    record = (
                        video_id,
                        frame_num,
                        timestamp,
                        mask.get("detection_index"),
                        mask.get("class"),
                        mask.get("confidence"),
                        mask.get("mask_rle"),
                        mask.get("mask_area_pixels"),
                        mask.get("stability_score"),
                    )

                    records.append(record)

            # Insert in batches
            for i in range(0, len(records), DB_BATCH_INSERT_SIZE):
                batch = records[i:i + DB_BATCH_INSERT_SIZE]

                await conn.executemany("""
                    INSERT INTO segmentation_masks (
                        video_id, frame_number, timestamp_seconds, detection_index,
                        class_name, confidence, mask_rle, mask_area_pixels, stability_score
                    )
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                """, batch)

        logger.info(f"Saved {len(records)} segmentation masks for video {video_id}")
        return True

    except Exception as e:
        logger.error(f"Error saving segmentation masks: {e}")
        return False


async def save_tracking_trajectories(
    db_pool: Pool,
    video_id: str,
    tracks: Dict[str, Any],
    fps: float = 30.0
) -> bool:
    """
    Save ByteTrack trajectories to database

    Args:
        db_pool: Database connection pool
        video_id: Video ID
        tracks: {track_id: trajectory_data}
        fps: Frames per second

    Returns:
        True if successful
    """
    if not db_pool or not tracks:
        return False

    try:
        async with db_pool.acquire() as conn:
            records = []

            for track_id, track_data in tracks.items():
                record = (
                    video_id,
                    track_id,
                    track_data.get("start_frame"),
                    track_data.get("end_frame"),
                    track_data.get("duration_frames"),
                    track_data.get("duration_seconds"),
                    track_data.get("num_frames_tracked"),
                    track_data.get("avg_confidence"),
                    json.dumps(track_data.get("frames", [])),
                )

                records.append(record)

            # Insert in batches
            for i in range(0, len(records), DB_BATCH_INSERT_SIZE):
                batch = records[i:i + DB_BATCH_INSERT_SIZE]

                await conn.executemany("""
                    INSERT INTO tracking_trajectories (
                        video_id, track_id, start_frame, end_frame,
                        duration_frames, duration_seconds, num_frames_tracked,
                        avg_confidence, trajectory_data
                    )
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                """, batch)

        logger.info(f"Saved {len(records)} tracking trajectories for video {video_id}")
        return True

    except Exception as e:
        logger.error(f"Error saving tracking trajectories: {e}")
        return False


async def save_scene_analysis(
    db_pool: Pool,
    video_id: str,
    scenes: Dict[str, Any]
) -> bool:
    """
    Save Gemini scene analysis to database

    Args:
        db_pool: Database connection pool
        video_id: Video ID
        scenes: Scene analysis data

    Returns:
        True if successful
    """
    if not db_pool or not scenes:
        return False

    try:
        async with db_pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO scene_analysis (video_id, analysis_data)
                VALUES ($1, $2)
                ON CONFLICT (video_id) DO UPDATE
                SET analysis_data = $2
            """, video_id, json.dumps(scenes))

        logger.info(f"Saved scene analysis for video {video_id}")
        return True

    except Exception as e:
        logger.error(f"Error saving scene analysis: {e}")
        return False


async def update_video_status(
    db_pool: Pool,
    video_id: str,
    status: str,
    metadata: Dict[str, Any] = None
) -> bool:
    """
    Update video processing status

    Args:
        db_pool: Database connection pool
        video_id: Video ID
        status: New status (processing, completed, failed)
        metadata: Optional metadata to update

    Returns:
        True if successful
    """
    if not db_pool:
        return False

    try:
        async with db_pool.acquire() as conn:
            if metadata:
                await conn.execute("""
                    UPDATE videos
                    SET status = $1, metadata = $2, updated_at = NOW()
                    WHERE id = $3
                """, status, json.dumps(metadata), video_id)
            else:
                await conn.execute("""
                    UPDATE videos
                    SET status = $1, updated_at = NOW()
                    WHERE id = $2
                """, status, video_id)

        logger.info(f"Updated video {video_id} status to {status}")
        return True

    except Exception as e:
        logger.error(f"Error updating video status: {e}")
        return False


async def get_video_metadata(
    db_pool: Pool,
    video_id: str
) -> Optional[Dict[str, Any]]:
    """
    Get video metadata from database

    Args:
        db_pool: Database connection pool
        video_id: Video ID

    Returns:
        Video metadata dict or None
    """
    if not db_pool:
        return None

    try:
        async with db_pool.acquire() as conn:
            result = await conn.fetchrow(
                "SELECT * FROM videos WHERE id = $1",
                video_id
            )

            return dict(result) if result else None

    except Exception as e:
        logger.error(f"Error getting video metadata: {e}")
        return None


async def get_detections_for_video(
    db_pool: Pool,
    video_id: str
) -> Dict[int, List[Dict]]:
    """
    Get all detections for a video

    Args:
        db_pool: Database connection pool
        video_id: Video ID

    Returns:
        {frame_number: [detections]}
    """
    if not db_pool:
        return {}

    try:
        async with db_pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT frame_number, detection_data FROM detections WHERE video_id = $1 ORDER BY frame_number",
                video_id
            )

            detections = {}
            for row in rows:
                frame_num = row["frame_number"]
                det_data = json.loads(row["detection_data"])

                if frame_num not in detections:
                    detections[frame_num] = []

                detections[frame_num].append(det_data)

            return detections

    except Exception as e:
        logger.error(f"Error getting detections: {e}")
        return {}


async def get_tracking_for_video(
    db_pool: Pool,
    video_id: str
) -> Dict[str, Any]:
    """
    Get all tracking trajectories for a video

    Args:
        db_pool: Database connection pool
        video_id: Video ID

    Returns:
        {track_id: trajectory_data}
    """
    if not db_pool:
        return {}

    try:
        async with db_pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT track_id, trajectory_data FROM tracking_trajectories WHERE video_id = $1",
                video_id
            )

            tracks = {}
            for row in rows:
                track_id = row["track_id"]
                track_data = json.loads(row["trajectory_data"])
                tracks[track_id] = track_data

            return tracks

    except Exception as e:
        logger.error(f"Error getting tracking data: {e}")
        return {}


async def save_processing_job(
    db_pool: Pool,
    job_id: str,
    video_id: str,
    user_id: str,
    status: str = "queued",
    progress: float = 0.0
) -> bool:
    """
    Create or update a processing job record

    Args:
        db_pool: Database connection pool
        job_id: Job ID
        video_id: Video ID
        user_id: User ID
        status: Job status
        progress: Progress percentage (0-100)

    Returns:
        True if successful
    """
    if not db_pool:
        return False

    try:
        async with db_pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO processing_jobs (id, video_id, user_id, status, progress, created_at, updated_at)
                VALUES ($1, $2, $3, $4, $5, NOW(), NOW())
                ON CONFLICT (id) DO UPDATE
                SET status = $4, progress = $5, updated_at = NOW()
            """, job_id, video_id, user_id, status, progress)

        return True

    except Exception as e:
        logger.error(f"Error saving processing job: {e}")
        return False


async def update_processing_job(
    db_pool: Pool,
    job_id: str,
    status: str = None,
    progress: float = None,
    result: Dict = None
) -> bool:
    """
    Update processing job status and progress

    Args:
        db_pool: Database connection pool
        job_id: Job ID
        status: New status
        progress: Progress percentage
        result: Result data

    Returns:
        True if successful
    """
    if not db_pool:
        return False

    try:
        async with db_pool.acquire() as conn:
            # Build update query dynamically
            updates = ["updated_at = NOW()"]
            params = []
            param_idx = 1

            if status is not None:
                updates.append(f"status = ${param_idx}")
                params.append(status)
                param_idx += 1

            if progress is not None:
                updates.append(f"progress = ${param_idx}")
                params.append(progress)
                param_idx += 1

            if result is not None:
                updates.append(f"result_data = ${param_idx}")
                params.append(json.dumps(result))
                param_idx += 1

            params.append(job_id)

            query = f"UPDATE processing_jobs SET {', '.join(updates)} WHERE id = ${param_idx}"

            await conn.execute(query, *params)

        return True

    except Exception as e:
        logger.error(f"Error updating processing job: {e}")
        return False
