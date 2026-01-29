# Video Reframer - Architecture Documentation

**Phase:** 2 (Detection + Segmentation + Tracking)
**Status:** Foundation (skeleton ready for implementation)
**Last Updated:** 2026-01-28

---

## 🏗️ System Architecture

### Overall Pipeline Flow

```
User                          Frontend (Netlify)
 │
 ├──► Video Upload
 │         │
 │         ▼
 │    API Request (HTTPS)
 │         │
 │         ▼
Backend (Modal FastAPI)  ◄────────┘
 │
 ├─► Video Processing Pipeline
 │     │
 │     ├─► FFmpeg: Extract Frames
 │     │
 │     ├─► YOLOv8: Detect Objects
 │     │     ├─► Person detection
 │     │     └─► Product detection
 │     │
 │     ├─► SAM2: Segment Objects
 │     │     ├─► Generate masks
 │     │     └─► Compress (RLE)
 │     │
 │     ├─► ByteTrack: Track Objects
 │     │     ├─► Cross-frame matching
 │     │     └─► Trajectory building
 │     │
 │     ├─► Gemini: Scene Analysis
 │     │     ├─► Scene detection
 │     │     └─► Semantic understanding
 │     │
 │     └─► Database: Save Results
 │
 └──► Job Status (polling)
       │
       ▼
    Database (Neon PostgreSQL)
```

---

## 🔄 Processing Pipeline Details

### Phase 1: Video Ingestion

**Input:** MP4 / MOV / AVI file (up to 500MB)

**Processing:**
1. Save to temporary file
2. Run ffprobe to extract metadata
3. Save video record to database with `status='processing'`

**Output:**
- video_id (UUID)
- Metadata: duration, fps, resolution, codec
- Database record created

```python
# Example metadata
{
  "duration_seconds": 25.5,
  "width": 1080,
  "height": 1920,
  "fps": 30,
  "codec": "h264",
  "total_frames": 765
}
```

---

### Phase 2: Frame Extraction (FFmpeg)

**Input:** Video file

**Processing:**
- FFmpeg with sampling rate (default: every 5th frame)
- Skip tiny objects (min_frame_size=64)
- Output: RGB NumPy arrays

**Output:**
```python
[
  (frame_number=0, frame_array),
  (frame_number=5, frame_array),
  (frame_number=10, frame_array),
  ...
]
```

**Performance:**
- 30 FPS video, 765 frames = 153 sampled frames
- ~100ms per frame extraction

---

### Phase 3: YOLOv8 Detection

**Model:** yolov8m.pt (medium size)

**Classes Detected:**
- `person` - human figures
- `product` - objects to be replaced

**Input:** RGB frame (1080x1920)

**Processing:**
1. Normalize frame
2. Run YOLO inference
3. Filter by confidence (default: 0.5)
4. Apply NMS (IoU: 0.45)

**Output per frame:**
```json
{
  "frame_number": 5,
  "timestamp_seconds": 0.17,
  "detections": [
    {
      "class": "person",
      "confidence": 0.92,
      "bbox": {
        "x": 100,
        "y": 50,
        "width": 120,
        "height": 200
      }
    },
    {
      "class": "product",
      "confidence": 0.87,
      "bbox": {
        "x": 300,
        "y": 150,
        "width": 80,
        "height": 100
      }
    }
  ]
}
```

**Storage:** Saved to `detections` table with JSONB

---

### Phase 4: SAM2 Segmentation

**Model:** sam2_hiera_base_plus.pt (Meta)

**Purpose:** Generate pixel-perfect masks for detected objects

**Input:**
- Frame (from detection phase)
- Bounding boxes (from YOLOv8)

**Processing:**
1. For each bounding box:
   - Prompt SAM2 with bbox coordinates
   - Generate binary mask (H × W array)
   - Calculate mask area (# of True pixels)
   - Compress with RLE or base64

**Output per detection:**
```python
{
  "track_id": "obj_001",
  "class": "person",
  "confidence": 0.92,
  "mask_rle": "3,5,10,3,2,...",  # Run-length encoded
  "mask_area_pixels": 24000,
  "frame": 5
}
```

**RLE Format:**
- `3,5,10` = 3 zeros, 5 ones, 10 zeros
- ~10x compression vs PNG
- Easy to decode back to binary mask

**Storage:** `segmentation_masks` table with JSONB + RLE

**GPU Requirement:**
- SAM2 needs GPU (Modal A10G, $1.10/hour)
- Can batch multiple detections
- ~50ms per mask

---

### Phase 5: ByteTrack Tracking

**Purpose:** Assign consistent IDs to same object across frames

**Algorithm:**
- Frame-by-frame matching using appearance + motion
- Handles occlusions and short-term disappearances

**Input:**
- Detections from all frames (sorted by frame number)
- Frame-to-frame motion constraints

**Processing:**
1. Initialize tracker with first frame detections
2. For each subsequent frame:
   - Match detections to existing tracks
   - Update track positions
   - Create new tracks for unmatched detections
   - Prune lost tracks (buffer=30 frames)

**Output per track:**
```json
{
  "track_id": "obj_001",
  "class": "person",
  "start_frame": 5,
  "end_frame": 250,
  "duration_frames": 245,
  "avg_confidence": 0.92,
  "frames": [
    {"frame": 5, "timestamp": 0.17, "bbox": {...}, "confidence": 0.92},
    {"frame": 10, "timestamp": 0.33, "bbox": {...}, "confidence": 0.93},
    ...
  ]
}
```

**Storage:** `tracking_trajectories` table with JSONB

---

### Phase 6: Gemini Scene Analysis

**Model:** Gemini 2.0 Flash

**Purpose:** High-level understanding of what's happening in each scene

**Input:**
- Video file
- Or keyframes from detections

**Processing:**
1. Upload video to Gemini File API
2. Wait for ACTIVE state (critical!)
3. Send analysis prompt
4. Parse JSON response

**Output:**
```json
{
  "scenes": [
    {
      "scene_number": 1,
      "start_frame": 0,
      "end_frame": 150,
      "description": "Woman enters house with package",
      "importance": 8,
      "scene_type": "both",  // person + product
      "replaceable_elements": [
        {
          "type": "person",
          "description": "Woman in blue dress",
          "difficulty": "medium"
        },
        {
          "type": "product",
          "description": "Box package",
          "difficulty": "hard"
        }
      ]
    }
  ]
}
```

**Storage:** `scene_analysis` table with JSONB

**Important:** Gemini metadata is hallucinated - we use ffprobe for truth

---

## 💾 Database Schema

### Core Tables

```
users
├── id (UUID)
├── email (unique)
├── api_key (unique)
└── created_at

videos
├── id (UUID)
├── user_id (FK)
├── filename, duration, resolution, fps
├── status (pending/processing/completed/failed)
└── timestamps

detections (YOLOv8 results)
├── id (UUID)
├── video_id (FK)
├── frame_number, timestamp
├── detection_data (JSONB)
└── created_at

segmentation_masks (SAM2 results)
├── id (UUID)
├── video_id (FK)
├── detection_id (FK)
├── mask_rle (compressed)
├── mask_area_pixels
└── created_at

tracking_trajectories (ByteTrack results)
├── id (UUID)
├── video_id (FK)
├── track_id, object_class
├── trajectory_data (JSONB)
├── start_frame, end_frame
└── created_at

scene_analysis (Gemini results)
├── id (UUID)
├── video_id (FK)
├── scene_number
├── analysis_data (JSONB)
└── created_at
```

### Indexes

Optimized for common queries:
- `idx_videos_user_id` - List user's videos
- `idx_videos_status` - Find processing jobs
- `idx_detections_frame_number` - Get detections for specific frame
- `idx_detections_data` (GIN) - Query by detection properties
- `idx_trajectories_track_id` - Get full trajectory for object
- `idx_scenes_frame_range` - Get scenes covering frame range

---

## 🔐 Authentication & Security

### API Key Based

- No OAuth complexity
- Better for B2B/server-to-server
- Keys stored in Neon with hashing (future)

### Request Headers

```bash
X-API-Key: vr_xxxxxxxxxxxx
```

### Database Security

- Neon: SSL by default
- Connection pooling: asyncpg (built-in)
- No hardcoded credentials (Modal secrets)

---

## ⚙️ Configuration

### Model Settings (`backend/config/ai_config.py`)

```python
# YOLOv8
YOLO_MODEL = "yolov8m.pt"  # tiny, small, medium, large, xlarge
YOLO_CONFIDENCE = 0.5
YOLO_IOU = 0.45

# SAM2
SAM2_MODEL = "sam2_hiera_base_plus.pt"
SAM2_GPU_REQUIRED = True

# ByteTrack
BYTETRACK_TRACK_THRESH = 0.5
BYTETRACK_TRACK_BUFFER = 30
BYTETRACK_MATCH_THRESH = 0.8

# Frame Sampling
SAMPLE_EVERY_N_FRAMES = 5
MIN_FRAME_SIZE = 64
```

### Modal Settings (`backend/config/modal_config.py`)

```python
# Compute
MODAL_GPU = "A10G"  # None, T4, A40, A10G
MODAL_TIMEOUT = 600  # seconds
MODAL_MEMORY = 8096  # MB

# Performance
BATCH_SIZE = 4  # Frames per batch
MAX_WORKERS = 2
```

---

## 📊 Performance Characteristics

### Processing Time (per video)

| Component | Time | FPS | Cost |
|-----------|------|-----|------|
| FFmpeg extraction | 5s | 30 | $0.01 |
| YOLOv8 detection | 15s | 10fps | $0.02 |
| SAM2 segmentation | 30s | 5fps | $0.50 (GPU) |
| ByteTrack tracking | 5s | 30 | $0.01 |
| Gemini analysis | 10s | 1 | $0.00 |
| **Total** | **65s** | | **$0.54** |

### Memory Usage

- Base: 2GB (Python + FastAPI)
- YOLO model: 1.5GB
- SAM2 model: 2.5GB
- Processing overhead: 1GB
- **Total:** ~7GB (fits in 8GB Modal memory)

### Throughput

- Sequential: 1 video per 65 seconds
- Parallel (Modal): Multiple workers per app
- Scaling: Horizontal (more Modal workers)

---

## 🚀 Deployment Architecture

### Current Stack

```
┌─────────────────────────┐
│ Netlify (Frontend)      │  Static site
│ - index.html            │  100GB bandwidth (free)
│ - app.js                │
│ - styles.css            │
└──────────┬──────────────┘
           │ HTTPS
           ▼
┌─────────────────────────┐
│ Modal (Backend)         │  Serverless compute
│ - FastAPI               │  $30 free credits
│ - YOLO, SAM2, ByteTrack │  GPU: A10G (+$1.10/hr)
│ - FFmpeg                │  Timeout: 600s
│ - Gemini integration    │  Auto-scaling
└──────────┬──────────────┘
           │ asyncpg
           ▼
┌─────────────────────────┐
│ Neon (Database)         │  PostgreSQL serverless
│ - Schema: 8 tables      │  0.5GB free (branching)
│ - Indexes: 10+          │  Connection pooling
│ - JSONB storage         │  SSL included
└─────────────────────────┘
```

### Deployment Commands

```bash
# Backend
modal deploy backend/main.py
# → https://sabalioglu--video-reframer-app.modal.run

# Frontend
cd frontend
netlify deploy --prod
# → https://video-reframer-xxxxx.netlify.app

# Database
psql "postgresql://..." -f database/schema.sql
```

---

## 🔄 Async Job Processing (Future)

For long videos (>10 min), implement async:

```
POST /jobs → returns job_id
GET /jobs/{id} → poll status
GET /jobs/{id}/result → get result when done
```

Uses `processing_jobs` table with status tracking.

---

## 📈 Scalability Considerations

### Bottlenecks

1. **SAM2 GPU Time** (expensive)
   - Solution: Batch multiple detections
   - Or: Only segment key frames

2. **Gemini API Calls**
   - Rate limit: 60 req/min
   - Solution: Cache results

3. **Database Size** (Neon 0.5GB free)
   - Solution: Archive old results to S3
   - Or: Use RLE compression for masks

### Optimization Strategies

1. **Frame Sampling**
   - Skip every Nth frame
   - Process high-confidence regions only

2. **Model Selection**
   - YOLO: tiny/small for speed, large/xlarge for accuracy
   - SAM2: base+ for memory, base for speed

3. **Batch Processing**
   - Process multiple frames in parallel
   - Modal auto-scaling handles workers

---

## 🎓 Lessons from KEMIK

### What Worked

✅ Modal for serverless compute (FFmpeg works!)
✅ Gemini File API for video analysis
✅ Neon for production database
✅ API key authentication (simple & secure)

### What Failed

❌ n8n for video processing (no FFmpeg, timeouts)
❌ Binary data in n8n workflows
❌ Gemini metadata as ground truth

### Best Practices

✅ Always use ffprobe for real metadata
✅ Wait for Gemini file ACTIVE state (critical!)
✅ Compress masks with RLE (10x savings)
✅ Use JSONB for flexible schema

---

## 📚 References

- **Modal Docs:** https://modal.com/docs
- **FastAPI:** https://fastapi.tiangolo.com/
- **YOLOv8:** https://docs.ultralytics.com/
- **SAM2:** https://github.com/facebookresearch/sam2
- **ByteTrack:** https://github.com/ifzhang/ByteTrack
- **Neon:** https://neon.tech/docs
- **Gemini:** https://ai.google.dev/

---

**Architecture Version:** 2.0
**Last Updated:** 2026-01-28
**Status:** Ready for Phase 2 implementation
