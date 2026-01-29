-- =====================================================
-- Video Reframer Database Schema (Neon PostgreSQL)
-- =====================================================
-- Last Updated: 2026-01-28
-- Status: Phase 2 (YOLO + SAM2 + ByteTrack)
-- =====================================================

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- =====================================================
-- 1. Users Table
-- =====================================================
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    api_key VARCHAR(64) UNIQUE NOT NULL DEFAULT gen_random_uuid()::text,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    CONSTRAINT email_valid CHECK (email ~ '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}$')
);

CREATE INDEX idx_users_api_key ON users(api_key);
CREATE INDEX idx_users_email ON users(email);

-- =====================================================
-- 2. Videos Table
-- =====================================================
CREATE TABLE IF NOT EXISTS videos (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,

    -- File metadata
    filename VARCHAR(512) NOT NULL,
    file_size_mb FLOAT,
    mime_type VARCHAR(50),

    -- Video metadata
    duration_seconds FLOAT,
    width INTEGER,
    height INTEGER,
    fps INTEGER,
    codec VARCHAR(20),
    total_frames INTEGER,

    -- Processing status
    status VARCHAR(20) DEFAULT 'pending',  -- pending, processing, completed, failed
    error_message TEXT,

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    processing_started_at TIMESTAMP WITH TIME ZONE,
    processing_completed_at TIMESTAMP WITH TIME ZONE,

    -- Indexes
    CONSTRAINT status_valid CHECK (status IN ('pending', 'processing', 'completed', 'failed'))
);

CREATE INDEX idx_videos_user_id ON videos(user_id);
CREATE INDEX idx_videos_status ON videos(status);
CREATE INDEX idx_videos_created_at ON videos(created_at DESC);

-- =====================================================
-- 3. Detections Table (YOLO Results)
-- =====================================================
-- Stores person/product detections per frame
CREATE TABLE IF NOT EXISTS detections (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    video_id UUID NOT NULL REFERENCES videos(id) ON DELETE CASCADE,

    -- Frame info
    frame_number INTEGER NOT NULL,
    timestamp_seconds FLOAT NOT NULL,

    -- Detection data (JSONB for flexibility)
    -- Example:
    -- {
    --   "objects": [
    --     {
    --       "class": "person",
    --       "confidence": 0.92,
    --       "bbox": {"x": 100, "y": 50, "width": 120, "height": 200},
    --       "track_id": "obj_001"
    --     },
    --     {
    --       "class": "product",
    --       "confidence": 0.87,
    --       "bbox": {"x": 300, "y": 150, "width": 80, "height": 100},
    --       "track_id": "obj_002"
    --     }
    --   ]
    -- }
    detection_data JSONB NOT NULL,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_detections_video_id ON detections(video_id);
CREATE INDEX idx_detections_frame_number ON detections(video_id, frame_number);
CREATE INDEX idx_detections_data ON detections USING GIN(detection_data);

-- =====================================================
-- 4. Segmentation Masks Table (SAM2 Results)
-- =====================================================
-- Stores pixel-perfect masks for detected objects
CREATE TABLE IF NOT EXISTS segmentation_masks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    video_id UUID NOT NULL REFERENCES videos(id) ON DELETE CASCADE,
    detection_id UUID NOT NULL REFERENCES detections(id) ON DELETE CASCADE,

    -- Object identification
    frame_number INTEGER NOT NULL,
    object_class VARCHAR(50),  -- 'person', 'product', etc.
    track_id VARCHAR(20),      -- matches detection track_id

    -- Mask storage options:
    -- Option A: RLE (Run-Length Encoding) - compact
    -- Option B: Base64 PNG - easy to visualize
    mask_rle TEXT,             -- Compressed format
    mask_png_base64 BYTEA,     -- Visual format (optional)

    -- Metadata
    mask_area_pixels BIGINT,   -- Number of True pixels in mask
    confidence FLOAT,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_masks_video_id ON segmentation_masks(video_id);
CREATE INDEX idx_masks_track_id ON segmentation_masks(video_id, track_id);
CREATE INDEX idx_masks_frame ON segmentation_masks(video_id, frame_number);

-- =====================================================
-- 5. Tracking Data Table (ByteTrack Results)
-- =====================================================
-- Cross-frame object identity and trajectories
CREATE TABLE IF NOT EXISTS tracking_trajectories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    video_id UUID NOT NULL REFERENCES videos(id) ON DELETE CASCADE,

    -- Track identity
    track_id VARCHAR(20) NOT NULL,
    object_class VARCHAR(50),  -- 'person', 'product'

    -- Trajectory data (JSONB)
    -- Example:
    -- {
    --   "frames": [
    --     {"frame": 10, "timestamp": 0.33, "bbox": {...}, "confidence": 0.95},
    --     {"frame": 11, "timestamp": 0.37, "bbox": {...}, "confidence": 0.93},
    --     ...
    --   ],
    --   "start_frame": 10,
    --   "end_frame": 250,
    --   "duration_frames": 240,
    --   "avg_confidence": 0.92
    -- }
    trajectory_data JSONB NOT NULL,

    -- Aggregates (for easy querying)
    start_frame INTEGER,
    end_frame INTEGER,
    duration_frames INTEGER,
    avg_confidence FLOAT,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_trajectories_video_id ON tracking_trajectories(video_id);
CREATE INDEX idx_trajectories_track_id ON tracking_trajectories(video_id, track_id);

-- =====================================================
-- 6. Scene Analysis Table (Gemini Results)
-- =====================================================
-- High-level scene understanding from Gemini
CREATE TABLE IF NOT EXISTS scene_analysis (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    video_id UUID NOT NULL REFERENCES videos(id) ON DELETE CASCADE,

    -- Scene info
    scene_number INTEGER,
    start_frame INTEGER,
    end_frame INTEGER,
    start_timestamp_seconds FLOAT,
    end_timestamp_seconds FLOAT,

    -- Gemini analysis (JSONB)
    -- Example:
    -- {
    --   "description": "Woman enters house with package",
    --   "scene_type": "both",  // person + product
    --   "importance": 8,
    --   "replaceable_elements": [
    --     {
    --       "type": "person",
    --       "description": "Woman in blue dress",
    --       "difficulty": "medium"
    --     },
    --     {
    --       "type": "product",
    --       "description": "Package in hands",
    --       "difficulty": "hard"
    --     }
    --   ]
    -- }
    analysis_data JSONB NOT NULL,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_scenes_video_id ON scene_analysis(video_id);
CREATE INDEX idx_scenes_frame_range ON scene_analysis(video_id, start_frame, end_frame);

-- =====================================================
-- 7. Processing Jobs Queue Table
-- =====================================================
-- For async job tracking (future enhancement)
CREATE TABLE IF NOT EXISTS processing_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    video_id UUID REFERENCES videos(id) ON DELETE CASCADE,

    -- Job metadata
    job_type VARCHAR(50),  -- 'detection', 'segmentation', 'tracking', 'full_pipeline'
    status VARCHAR(20) DEFAULT 'queued',  -- queued, processing, completed, failed

    -- Progress tracking
    progress_percent INTEGER DEFAULT 0,
    current_step VARCHAR(100),

    -- Timing
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,

    -- Error handling
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3,

    CONSTRAINT status_valid CHECK (status IN ('queued', 'processing', 'completed', 'failed'))
);

CREATE INDEX idx_jobs_user_id ON processing_jobs(user_id);
CREATE INDEX idx_jobs_status ON processing_jobs(status);
CREATE INDEX idx_jobs_video_id ON processing_jobs(video_id);

-- =====================================================
-- 8. API Activity Log Table
-- =====================================================
-- For monitoring and debugging
CREATE TABLE IF NOT EXISTS api_activity_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,

    -- Request info
    endpoint VARCHAR(255),
    method VARCHAR(10),  -- GET, POST, etc.
    status_code INTEGER,

    -- Performance
    response_time_ms INTEGER,

    -- Timestamp
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_activity_user_id ON api_activity_log(user_id);
CREATE INDEX idx_activity_timestamp ON api_activity_log(created_at DESC);

-- =====================================================
-- Helper Functions
-- =====================================================

-- Update video processing status
CREATE OR REPLACE FUNCTION update_video_status(
    p_video_id UUID,
    p_status VARCHAR
)
RETURNS void AS $$
BEGIN
    UPDATE videos
    SET status = p_status,
        processing_started_at = CASE WHEN p_status = 'processing' THEN NOW() ELSE processing_started_at END,
        processing_completed_at = CASE WHEN p_status = 'completed' THEN NOW() ELSE processing_completed_at END,
        updated_at = NOW()
    WHERE id = p_video_id;
END;
$$ LANGUAGE plpgsql;

-- Get detection summary for a video
CREATE OR REPLACE FUNCTION get_detection_summary(p_video_id UUID)
RETURNS TABLE (
    total_frames INTEGER,
    total_detections BIGINT,
    unique_track_ids INTEGER,
    class_distribution JSONB
) AS $$
BEGIN
    RETURN QUERY
    WITH detection_stats AS (
        SELECT
            COUNT(DISTINCT frame_number)::INTEGER as total_frames,
            COUNT(*)::BIGINT as total_detections,
            COUNT(DISTINCT detection_data->>'track_id')::INTEGER as unique_tracks,
            jsonb_object_agg(
                COALESCE(detection_data->'objects'->0->>'class', 'unknown'),
                COUNT(*)
            ) as class_dist
        FROM detections
        WHERE video_id = p_video_id
    )
    SELECT
        total_frames,
        total_detections,
        unique_tracks,
        class_dist
    FROM detection_stats;
END;
$$ LANGUAGE plpgsql;

-- =====================================================
-- Grants (for application user)
-- =====================================================
-- Grant permissions to application user if using separate db user
-- GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA public TO app_user;
-- GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO app_user;

-- =====================================================
-- Notes
-- =====================================================
/*
DATABASE STRUCTURE NOTES:

1. JSONB fields for flexibility:
   - detection_data: Raw YOLO output with bbox, confidence, etc.
   - trajectory_data: Complete tracking history across frames
   - analysis_data: Gemini scene understanding

2. Indexing strategy:
   - User lookups: idx_users_api_key, idx_users_email
   - Video queries: idx_videos_user_id, idx_videos_status
   - Frame queries: idx_detections_frame_number
   - JSONB queries: idx_detections_data (GIN index)
   - Tracking: idx_trajectories_track_id

3. Storage optimization:
   - Use mask_rle for compact mask storage (vs base64)
   - JSONB allows future schema expansion without migrations
   - Proper CASCADE deletes prevent orphaned data

4. Future enhancements:
   - Add vector embeddings for semantic search
   - Add Redis caching for frequently accessed results
   - Implement data partitioning by date
   - Add full-text search on descriptions

5. Cost considerations (Neon free tier = 0.5GB):
   - Keep retention policy for old results
   - Archive processed data to S3 after 30 days
   - Use RLE format for masks (5-10x compression vs PNG)
*/
