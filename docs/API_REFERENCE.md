# Video Reframer - API Reference

**Base URL:** `https://sabalioglu--video-reframer-app.modal.run`
**Authentication:** API Key in `X-API-Key` header
**Content-Type:** `application/json` (except upload)

---

## Authentication

### API Key Format
```
vr_xxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

### Register to Get Key
```bash
curl -X POST https://sabalioglu--video-reframer-app.modal.run/register \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com"}'
```

Response:
```json
{
  "user_id": "uuid",
  "email": "user@example.com",
  "api_key": "vr_xxxxxxxxxxxx"
}
```

---

## Endpoints

### 1. Health Check

**Endpoint:** `GET /health`

**Description:** Check API status and database connectivity

**Headers:** None required

**Example:**
```bash
curl https://sabalioglu--video-reframer-app.modal.run/health
```

**Response (200):**
```json
{
  "status": "healthy",
  "database": "connected",
  "models": ["yolov8", "sam2", "bytetrack"],
  "timestamp": "2026-01-28T10:30:00.000000"
}
```

**Status Values:**
- `"healthy"` - All systems operational
- `"degraded"` - Some features unavailable
- `"unhealthy"` - Major issues

---

### 2. Register User

**Endpoint:** `POST /register`

**Description:** Create new user account and receive API key

**Headers:**
```
Content-Type: application/json
```

**Request Body:**
```json
{
  "email": "user@example.com"
}
```

**Example:**
```bash
curl -X POST https://sabalioglu--video-reframer-app.modal.run/register \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com"}'
```

**Response (200):**
```json
{
  "status": "success",
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "email": "user@example.com",
  "api_key": "vr_a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6"
}
```

**Errors:**
- `400` - Invalid email format
- `400` - Email already registered

---

### 3. Upload & Process Video

**Endpoint:** `POST /process`

**Description:** Upload video file for analysis (YOLO + SAM2 + ByteTrack + Gemini)

**Headers:**
```
X-API-Key: vr_xxxxxxxxxxxx
```

**Request Body:** (multipart/form-data)
```
file: <video_file>
```

**Example:**
```bash
curl -X POST https://sabalioglu--video-reframer-app.modal.run/process \
  -H "X-API-Key: vr_xxxxxxxxxxxx" \
  -F "file=@path/to/video.mp4"
```

**Response (200):**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "queued",
  "message": "Video queued for processing"
}
```

**File Constraints:**
- Max size: 500MB
- Supported formats: MP4, MOV, AVI, MKV
- Min duration: 1 second
- Min resolution: 320x240

**Errors:**
- `400` - Invalid file format
- `400` - File too large
- `401` - Missing or invalid API key
- `413` - Payload too large

---

### 4. Get Job Status

**Endpoint:** `GET /job/{job_id}`

**Description:** Poll processing job status

**Headers:**
```
X-API-Key: vr_xxxxxxxxxxxx
```

**Path Parameters:**
```
job_id (UUID): Job ID from /process response
```

**Example:**
```bash
curl https://sabalioglu--video-reframer-app.modal.run/job/550e8400-e29b-41d4-a716-446655440000 \
  -H "X-API-Key: vr_xxxxxxxxxxxx"
```

**Response (200):**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "processing",
  "progress_percent": 45,
  "current_step": "Running SAM2 segmentation...",
  "video_id": "550e8400-e29b-41d4-a716-446655440001"
}
```

**Status Values:**
- `"queued"` - Waiting to start
- `"processing"` - Currently running
- `"completed"` - Done, results ready
- `"failed"` - Error occurred

**Response (completed):**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "progress_percent": 100,
  "current_step": "Processing complete",
  "video_id": "550e8400-e29b-41d4-a716-446655440001"
}
```

**Response (failed):**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "failed",
  "error_message": "FFmpeg error: invalid video codec"
}
```

**Errors:**
- `401` - Invalid API key
- `404` - Job not found

---

### 5. Get Processing Results

**Endpoint:** `GET /results/{job_id}`

**Description:** Retrieve complete processing results (detections, masks, tracking)

**Headers:**
```
X-API-Key: vr_xxxxxxxxxxxx
```

**Path Parameters:**
```
job_id (UUID): Job ID from /process response
```

**Example:**
```bash
curl https://sabalioglu--video-reframer-app.modal.run/results/550e8400-e29b-41d4-a716-446655440000 \
  -H "X-API-Key: vr_xxxxxxxxxxxx" | jq .
```

**Response (200):**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "success",
  "metadata": {
    "duration_seconds": 25.5,
    "width": 1080,
    "height": 1920,
    "fps": 30,
    "codec": "h264",
    "total_frames": 765
  },
  "detections": {
    "5": [
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
    ],
    "10": [ ... ]
  },
  "segmentation_masks": {
    "5": [
      {
        "track_id": "obj_001",
        "class": "person",
        "mask_rle": "3,5,10,3,2,...",
        "mask_area_pixels": 24000
      }
    ]
  },
  "tracking": {
    "obj_001": {
      "class": "person",
      "start_frame": 5,
      "end_frame": 250,
      "duration_frames": 245,
      "avg_confidence": 0.92,
      "frames": [
        {
          "frame": 5,
          "timestamp": 0.17,
          "confidence": 0.92
        }
      ]
    }
  },
  "scenes": [
    {
      "scene_number": 1,
      "start_frame": 0,
      "end_frame": 150,
      "description": "Woman enters house with package",
      "importance": 8,
      "replaceable_elements": [
        {
          "type": "person",
          "description": "Woman in blue dress",
          "difficulty": "medium"
        }
      ]
    }
  ]
}
```

**Errors:**
- `401` - Invalid API key
- `404` - Job not found
- `202` - Still processing (retry later)

---

### 6. List User Videos

**Endpoint:** `GET /videos`

**Description:** List all videos processed by user

**Headers:**
```
X-API-Key: vr_xxxxxxxxxxxx
```

**Query Parameters:**
```
status (optional): pending|processing|completed|failed
limit (optional): default 20, max 100
offset (optional): default 0
```

**Example:**
```bash
curl "https://sabalioglu--video-reframer-app.modal.run/videos?status=completed&limit=10" \
  -H "X-API-Key: vr_xxxxxxxxxxxx"
```

**Response (200):**
```json
{
  "total": 5,
  "videos": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "filename": "video.mp4",
      "status": "completed",
      "duration_seconds": 25.5,
      "processed_at": "2026-01-28T10:30:00Z",
      "created_at": "2026-01-28T10:25:00Z"
    }
  ]
}
```

**Errors:**
- `401` - Invalid API key

---

## Data Formats

### Detection Object
```json
{
  "class": "person|product",
  "confidence": 0.0-1.0,
  "bbox": {
    "x": integer,       // left edge
    "y": integer,       // top edge
    "width": integer,
    "height": integer
  }
}
```

### Segmentation Mask (RLE)
```
"3,5,10,2" means:
- 3 zeros
- 5 ones
- 10 zeros
- 2 ones
```

Decode back to binary array:
```python
def decode_rle(rle_string):
    rle = [int(x) for x in rle_string.split(',')]
    result = []
    is_zero = True
    for count in rle:
        result.extend([is_zero] * count)
        is_zero = not is_zero
    return result
```

### Tracking Trajectory
```json
{
  "track_id": "obj_001",
  "class": "person|product",
  "start_frame": integer,
  "end_frame": integer,
  "duration_frames": integer,
  "avg_confidence": 0.0-1.0,
  "frames": [
    {
      "frame": integer,
      "timestamp": float,
      "confidence": 0.0-1.0
    }
  ]
}
```

---

## Error Handling

### Error Response Format
```json
{
  "detail": "Error message describing what went wrong"
}
```

### Common HTTP Status Codes
- `200` - Success
- `202` - Accepted (still processing)
- `400` - Bad request (invalid input)
- `401` - Unauthorized (missing/invalid API key)
- `404` - Not found (job/video doesn't exist)
- `413` - Payload too large
- `429` - Too many requests (rate limited)
- `500` - Server error
- `503` - Service unavailable

### Error Examples

**Invalid email:**
```json
{
  "detail": "Invalid email format"
}
```

**Missing API key:**
```json
{
  "detail": "Missing API key"
}
```

**File too large:**
```json
{
  "detail": "File size exceeds 500MB limit"
}
```

---

## Rate Limiting

**Current Limits (per API key):**
- 100 requests per hour
- 10 concurrent uploads
- Max file size: 500MB
- Max job duration: 10 minutes

**Response Headers:**
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1234567890
```

---

## Polling Strategy

For production applications:

1. **POST /process** → Get `job_id`
2. **Poll GET /job/{id}** every 2-5 seconds
3. **When status = "completed"** → **GET /results/{id}**

**Example Polling Loop:**
```python
import requests
import time

job_id = "..."
api_key = "vr_..."

while True:
    response = requests.get(
        f"https://sabalioglu--video-reframer-app.modal.run/job/{job_id}",
        headers={"X-API-Key": api_key}
    )
    data = response.json()

    if data["status"] == "completed":
        results = requests.get(
            f"https://sabalioglu--video-reframer-app.modal.run/results/{job_id}",
            headers={"X-API-Key": api_key}
        ).json()
        print("Results:", results)
        break
    elif data["status"] == "failed":
        print("Error:", data["error_message"])
        break
    else:
        print(f"Progress: {data['progress_percent']}%")
        time.sleep(2)
```

---

## SDK Examples (Placeholder)

### Python
```python
from video_reframer import Client

client = Client(api_key="vr_xxxx")
job = client.process("video.mp4")
results = job.wait()
print(results.detections)
```

### JavaScript
```javascript
const client = new VideoReframer("vr_xxxx");
const job = await client.process(videoFile);
const results = await job.wait();
console.log(results.detections);
```

### cURL
```bash
# See examples above
```

---

## Changelog

### v2.0.0 (2026-01-28)
- ✅ YOLO detection endpoint
- ✅ SAM2 segmentation support
- ✅ ByteTrack tracking
- ✅ Gemini scene analysis
- ✅ Async job processing
- 🔄 Rate limiting (in progress)
- 🔄 WebSocket updates (planned)

### v1.0.0 (2026-01-23)
- ✅ Basic FFmpeg extraction
- ✅ Gemini scene detection
- ✅ Frame extraction and gallery

---

**Last Updated:** 2026-01-28
**API Version:** 2.0.0
**Status:** Stable (Phase 2)
