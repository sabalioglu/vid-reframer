# 📚 API Usage Guide - Video Reframer

**API Base URL:** `https://sabalioglu--video-reframer-app.modal.run`
**API Version:** 2.0.0
**Authentication:** API Key (Header: `X-API-Key`)

---

## Quick Start

### 1. Register User & Get API Key

```bash
curl -X POST https://sabalioglu--video-reframer-app.modal.run/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "your@email.com"
  }'
```

**Response:**
```json
{
  "status": "success",
  "user_id": "a1b2c3d4-e5f6-7890-1234-567890abcdef",
  "email": "your@email.com",
  "api_key": "vr_abc123def456ghi789jkl012mno345"
}
```

**Save the `api_key` - you'll need it for all requests!**

### 2. Upload Video for Processing

```bash
curl -X POST https://sabalioglu--video-reframer-app.modal.run/process \
  -H "X-API-Key: vr_abc123def456ghi789jkl012mno345" \
  -F "file=@/path/to/video.mp4"
```

**Response:**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "queued",
  "message": "Video processing started. Monitor with /job/550e8400-e29b-41d4-a716-446655440000"
}
```

**Save the `job_id` - use it to track progress!**

### 3. Check Processing Progress

```bash
curl https://sabalioglu--video-reframer-app.modal.run/job/550e8400-e29b-41d4-a716-446655440000 \
  -H "X-API-Key: vr_abc123def456ghi789jkl012mno345"
```

**Response (while processing):**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "detecting_objects",
  "progress": 35,
  "created_at": "2026-01-28T15:30:00.000Z",
  "updated_at": "2026-01-28T15:30:45.000Z"
}
```

### 4. Get Results

```bash
curl https://sabalioglu--video-reframer-app.modal.run/results/550e8400-e29b-41d4-a716-446655440000 \
  -H "X-API-Key: vr_abc123def456ghi789jkl012mno345"
```

**Response (when completed):**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "video_id": "550e8400-e29b-41d4-a716-446655440000",
  "results": {
    "success": true,
    "statistics": {
      "video": {
        "duration": 25.5,
        "width": 1920,
        "height": 1080,
        "fps": 30.0
      },
      "detections": {
        "total_detections": 145,
        "frames_with_detections": 25
      },
      "tracking": {
        "total_tracks": 8,
        "average_duration_seconds": 5.2
      }
    }
  },
  "completed_at": "2026-01-28T15:32:30.000Z"
}
```

---

## Detailed API Reference

### POST /register
**Register a new user**

**Request:**
```bash
curl -X POST https://sabalioglu--video-reframer-app.modal.run/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com"
  }'
```

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| email | string | Yes | User email address |

**Response (200 OK):**
```json
{
  "status": "success",
  "user_id": "uuid",
  "email": "user@example.com",
  "api_key": "vr_..."
}
```

**Response (400 Bad Request):**
```json
{
  "detail": "User with this email already exists"
}
```

---

### POST /process
**Upload and process video**

**Request:**
```bash
curl -X POST https://sabalioglu--video-reframer-app.modal.run/process \
  -H "X-API-Key: vr_..." \
  -F "file=@video.mp4"
```

**Headers:**
| Name | Required | Description |
|------|----------|-------------|
| X-API-Key | Yes | Your API key |
| Content-Type | Auto | multipart/form-data |

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| file | file | Yes | Video file (MP4, AVI, MOV, MKV, WebM) |

**Response (200 OK):**
```json
{
  "job_id": "uuid",
  "status": "queued",
  "message": "Video processing started. Monitor with /job/uuid"
}
```

**Response (401 Unauthorized):**
```json
{
  "detail": "Invalid API key"
}
```

**Response (413 Payload Too Large):**
```json
{
  "detail": "File exceeds maximum size (500MB)"
}
```

---

### GET /job/{job_id}
**Get processing job status**

**Request:**
```bash
curl https://sabalioglu--video-reframer-app.modal.run/job/uuid \
  -H "X-API-Key: vr_..."
```

**Response (200 OK):**
```json
{
  "job_id": "uuid",
  "status": "processing",
  "progress": 45,
  "created_at": "2026-01-28T15:30:00.000Z",
  "updated_at": "2026-01-28T15:30:45.000Z"
}
```

**Status Values:**
- `queued` - Waiting to start
- `extracting_metadata` - Getting video info
- `extracting_frames` - Reading frames
- `detecting_objects` - Running YOLOv8
- `segmenting` - Running SAM2
- `tracking` - Running ByteTrack
- `analyzing_scenes` - Running Gemini
- `completed` - Done!
- `failed` - Error occurred

**Progress Range:** 0-100 (percentage)

---

### GET /results/{job_id}
**Get complete processing results**

**Request:**
```bash
curl https://sabalioglu--video-reframer-app.modal.run/results/uuid \
  -H "X-API-Key: vr_..."
```

**Response (200 OK):**
```json
{
  "job_id": "uuid",
  "status": "completed",
  "video_id": "uuid",
  "results": {
    "success": true,
    "detections": {
      "5": [
        {
          "class": "person",
          "class_id": 0,
          "confidence": 0.92,
          "bbox": {
            "x": 100.5,
            "y": 50.3,
            "width": 120.0,
            "height": 200.0
          }
        }
      ],
      "10": [...]
    },
    "segmentation": {
      "5": [
        {
          "detection_index": 0,
          "class": "person",
          "confidence": 0.92,
          "mask_rle": "3,5,10,2,...",
          "mask_area_pixels": 24000,
          "stability_score": 0.95
        }
      ],
      "10": [...]
    },
    "tracking": {
      "obj_001": {
        "track_id": "obj_001",
        "start_frame": 5,
        "end_frame": 250,
        "duration_frames": 245,
        "duration_seconds": 8.17,
        "num_frames_tracked": 50,
        "avg_confidence": 0.92,
        "frames": [
          {
            "frame_number": 5,
            "timestamp": 0.17,
            "bbox": {...},
            "confidence": 0.92,
            "is_activated": true
          }
        ]
      },
      "obj_002": {...}
    },
    "scene_analysis": {
      "description": "Person walking in office...",
      "objects": ["person", "desk", "computer"],
      "people_count": 1,
      "people_activities": ["walking", "working"],
      "purpose": "Office scene"
    },
    "statistics": {
      "video": {
        "duration": 25.5,
        "width": 1920,
        "height": 1080,
        "fps": 30.0,
        "total_frames": 765,
        "codec": "h264"
      },
      "detections": {
        "total_detections": 145,
        "frames_with_detections": 25,
        "average_confidence": 0.89,
        "class_distribution": {
          "person": 140,
          "laptop": 5
        }
      },
      "tracking": {
        "total_tracks": 8,
        "average_duration_seconds": 5.2,
        "average_confidence": 0.88,
        "min_duration": 1.5,
        "max_duration": 15.3
      }
    }
  },
  "completed_at": "2026-01-28T15:32:30.000Z"
}
```

**Result Structure:**

| Section | Description |
|---------|-------------|
| `detections` | Frame-by-frame object detection results (YOLOv8) |
| `segmentation` | Pixel masks for detected objects (SAM2, RLE encoded) |
| `tracking` | Object trajectories across frames (ByteTrack) |
| `scene_analysis` | AI understanding of video content (Gemini) |
| `statistics` | Summary statistics about the video and processing |

---

### GET /videos
**List user's videos**

**Request:**
```bash
curl https://sabalioglu--video-reframer-app.modal.run/videos \
  -H "X-API-Key: vr_..."
```

**Response (200 OK):**
```json
{
  "videos": [
    {
      "id": "uuid1",
      "filename": "office_video.mp4",
      "duration": 25.5,
      "status": "completed",
      "created_at": "2026-01-28T15:30:00.000Z"
    },
    {
      "id": "uuid2",
      "filename": "product_demo.mp4",
      "duration": 60.0,
      "status": "processing",
      "created_at": "2026-01-28T15:25:00.000Z"
    }
  ]
}
```

---

### GET /health
**System health check**

**Request:**
```bash
curl https://sabalioglu--video-reframer-app.modal.run/health
```

**Response (200 OK):**
```json
{
  "status": "healthy",
  "database": "connected",
  "models": ["yolov8", "sam2", "bytetrack", "gemini"],
  "timestamp": "2026-01-28T15:30:00.000Z"
}
```

---

## Response Codes

| Code | Meaning | Description |
|------|---------|-------------|
| 200 | OK | Request successful |
| 400 | Bad Request | Invalid parameters |
| 401 | Unauthorized | Missing/invalid API key |
| 404 | Not Found | Job/video not found |
| 413 | Payload Too Large | File exceeds size limit |
| 500 | Server Error | Internal error (check logs) |

---

## Error Handling

### Example Error Response

```bash
curl https://sabalioglu--video-reframer-app.modal.run/results/invalid-id \
  -H "X-API-Key: vr_..."
```

**Response (404):**
```json
{
  "detail": "Job not found"
}
```

### Best Practices

1. **Always validate API key** before making requests
2. **Check job status** before querying results
3. **Handle timeouts** - processing can take 1-3 minutes
4. **Implement exponential backoff** for polling
5. **Store API keys securely** (environment variables, not in code)

---

## Implementation Examples

### Python

```python
import requests
import time
from pathlib import Path

BASE_URL = "https://sabalioglu--video-reframer-app.modal.run"

class VideoReframer:
    def __init__(self, api_key):
        self.api_key = api_key
        self.headers = {"X-API-Key": api_key}

    def register(self, email):
        """Register new user"""
        resp = requests.post(
            f"{BASE_URL}/register",
            json={"email": email}
        )
        return resp.json()

    def process_video(self, video_path):
        """Upload video for processing"""
        with open(video_path, 'rb') as f:
            files = {'file': f}
            resp = requests.post(
                f"{BASE_URL}/process",
                headers=self.headers,
                files=files
            )
        return resp.json()

    def get_status(self, job_id):
        """Check job status"""
        resp = requests.get(
            f"{BASE_URL}/job/{job_id}",
            headers=self.headers
        )
        return resp.json()

    def get_results(self, job_id):
        """Get processing results"""
        resp = requests.get(
            f"{BASE_URL}/results/{job_id}",
            headers=self.headers
        )
        return resp.json()

    def wait_for_completion(self, job_id, timeout=600):
        """Poll until job completes"""
        start = time.time()
        while time.time() - start < timeout:
            status = self.get_status(job_id)
            print(f"Status: {status['status']} ({status['progress']}%)")

            if status['status'] == 'completed':
                return self.get_results(job_id)

            time.sleep(10)  # Poll every 10 seconds

        raise TimeoutError(f"Job {job_id} timed out")

# Usage
client = VideoReframer("vr_abc123...")
result = client.process_video("video.mp4")
job_id = result['job_id']
results = client.wait_for_completion(job_id)
print(results)
```

### JavaScript

```javascript
const API_BASE = "https://sabalioglu--video-reframer-app.modal.run";

class VideoReframer {
  constructor(apiKey) {
    this.apiKey = apiKey;
  }

  async register(email) {
    const resp = await fetch(`${API_BASE}/register`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email })
    });
    return resp.json();
  }

  async processVideo(file) {
    const formData = new FormData();
    formData.append("file", file);

    const resp = await fetch(`${API_BASE}/process`, {
      method: "POST",
      headers: { "X-API-Key": this.apiKey },
      body: formData
    });
    return resp.json();
  }

  async getStatus(jobId) {
    const resp = await fetch(`${API_BASE}/job/${jobId}`, {
      headers: { "X-API-Key": this.apiKey }
    });
    return resp.json();
  }

  async getResults(jobId) {
    const resp = await fetch(`${API_BASE}/results/${jobId}`, {
      headers: { "X-API-Key": this.apiKey }
    });
    return resp.json();
  }

  async waitForCompletion(jobId, timeout = 600000) {
    const start = Date.now();
    while (Date.now() - start < timeout) {
      const status = await this.getStatus(jobId);
      console.log(`Status: ${status.status} (${status.progress}%)`);

      if (status.status === "completed") {
        return await this.getResults(jobId);
      }

      await new Promise(r => setTimeout(r, 10000));
    }

    throw new Error(`Job ${jobId} timed out`);
  }
}

// Usage
const client = new VideoReframer("vr_abc123...");
const result = await client.processVideo(fileInput.files[0]);
const results = await client.waitForCompletion(result.job_id);
console.log(results);
```

---

## Rate Limiting & Quotas

**Current Limits (Soft):**
- No official rate limiting implemented yet
- Monitor usage and implement if needed

**Recommendations:**
- Max 10 concurrent jobs per user
- Max 100 jobs per hour
- Max 500MB file size
- Max 60 minute video duration

---

## Support & Issues

**API Not Responding?**
- Check `/health` endpoint
- View Modal logs: `modal logs main.py`

**Video Processing Failed?**
- Check logs for specific error
- Verify video format (MP4, AVI, MOV supported)
- Try smaller video (< 60 seconds) first

**High Latency?**
- First request may be slow (cold start)
- Subsequent requests are faster
- Monitor from `/job/{job_id}` endpoint

---

**Happy Processing!** 🎬

