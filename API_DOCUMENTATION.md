# Video Reframer API Documentation

## 🚀 Base URL

```
https://sabalioglu--video-reframer-web.modal.run
```

## 📋 Overview

Video Reframer is an AI-powered video analysis API built with FastAPI and deployed on Modal. It provides endpoints for user registration, video processing, job tracking, and result retrieval.

**Current Version:** 1.0.0
**Status:** ✅ Production Ready

---

## 🔐 Authentication

All endpoints except `/health` and `/register` require API key authentication via the `X-API-Key` header.

### Getting Your API Key

1. Call the `/register` endpoint with your email
2. You'll receive an `api_key` in the response
3. Use this key in the `X-API-Key` header for all subsequent requests

**Example:**
```bash
X-API-Key: vr_f2f34844cb584fab85af0a8a1797595c
```

---

## 📡 Endpoints

### 1. Health Check

**Endpoint:** `GET /health`

**Description:** Check if the API is running and healthy.

**Parameters:** None (no authentication required)

**Response:**
```json
{
  "status": "healthy",
  "service": "video-reframer"
}
```

**Example:**
```bash
curl https://sabalioglu--video-reframer-web.modal.run/health
```

---

### 2. Register User

**Endpoint:** `POST /register`

**Description:** Register a new user and receive an API key.

**Parameters:**
- `email` (string, query): User's email address (required)

**Response:**
```json
{
  "status": "success",
  "user_id": "b0dd3d97-00ab-4511-9edb-cd4d9171e98e",
  "api_key": "vr_f2f34844cb584fab85af0a8a1797595c"
}
```

**Example:**
```bash
curl -X POST "https://sabalioglu--video-reframer-web.modal.run/register?email=user@example.com"
```

---

### 3. Upload & Process Video

**Endpoint:** `POST /process`

**Description:** Upload a video file for processing.

**Headers:**
- `X-API-Key` (required): Your API key

**Parameters:**
- `file` (file): Video file to upload

**Response:**
```json
{
  "status": "success",
  "job_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

**Example:**
```bash
curl -X POST https://sabalioglu--video-reframer-web.modal.run/process \
  -H "X-API-Key: vr_f2f34844cb584fab85af0a8a1797595c" \
  -F "file=@video.mp4"
```

---

### 4. Get Job Status

**Endpoint:** `GET /job/{job_id}`

**Description:** Check the status of a video processing job.

**Headers:**
- `X-API-Key` (required): Your API key

**Parameters:**
- `job_id` (path): Job ID from `/process` response

**Response:**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "processing"
}
```

**Status Values:**
- `processing` - Job is currently being processed
- `complete` - Job has finished successfully
- `failed` - Job encountered an error

**Example:**
```bash
curl https://sabalioglu--video-reframer-web.modal.run/job/550e8400-e29b-41d4-a716-446655440000 \
  -H "X-API-Key: vr_f2f34844cb584fab85af0a8a1797595c"
```

---

### 5. Get Processing Results

**Endpoint:** `GET /results/{job_id}`

**Description:** Retrieve the complete processing results for a job.

**Headers:**
- `X-API-Key` (required): Your API key

**Parameters:**
- `job_id` (path): Job ID from `/process` response

**Response:**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "complete",
  "results": {
    "detections": {},
    "segmentation": {},
    "tracking": {},
    "analysis": {}
  }
}
```

**Example:**
```bash
curl https://sabalioglu--video-reframer-web.modal.run/results/550e8400-e29b-41d4-a716-446655440000 \
  -H "X-API-Key: vr_f2f34844cb584fab85af0a8a1797595c"
```

---

### 6. List All Videos

**Endpoint:** `GET /videos`

**Description:** Get a list of all videos uploaded by the authenticated user.

**Headers:**
- `X-API-Key` (required): Your API key

**Response:**
```json
{
  "status": "success",
  "videos": [
    {
      "job_id": "550e8400-e29b-41d4-a716-446655440000",
      "status": "complete"
    }
  ]
}
```

**Example:**
```bash
curl https://sabalioglu--video-reframer-web.modal.run/videos \
  -H "X-API-Key: vr_f2f34844cb584fab85af0a8a1797595c"
```

---

## 📊 Complete Workflow Example

### Step 1: Register
```bash
curl -X POST "https://sabalioglu--video-reframer-web.modal.run/register?email=user@example.com"
```

Response:
```json
{
  "status": "success",
  "user_id": "b0dd3d97-00ab-4511-9edb-cd4d9171e98e",
  "api_key": "vr_f2f34844cb584fab85af0a8a1797595c"
}
```

### Step 2: Check Health
```bash
curl https://sabalioglu--video-reframer-web.modal.run/health
```

### Step 3: Upload Video
```bash
curl -X POST https://sabalioglu--video-reframer-web.modal.run/process \
  -H "X-API-Key: vr_f2f34844cb584fab85af0a8a1797595c" \
  -F "file=@video.mp4"
```

Response:
```json
{
  "status": "success",
  "job_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

### Step 4: Check Job Status
```bash
curl https://sabalioglu--video-reframer-web.modal.run/job/550e8400-e29b-41d4-a716-446655440000 \
  -H "X-API-Key: vr_f2f34844cb584fab85af0a8a1797595c"
```

### Step 5: Get Results
```bash
curl https://sabalioglu--video-reframer-web.modal.run/results/550e8400-e29b-41d4-a716-446655440000 \
  -H "X-API-Key: vr_f2f34844cb584fab85af0a8a1797595c"
```

### Step 6: List All Videos
```bash
curl https://sabalioglu--video-reframer-web.modal.run/videos \
  -H "X-API-Key: vr_f2f34844cb584fab85af0a8a1797595c"
```

---

## 🐍 Python Example

```python
import requests
import json

BASE_URL = "https://sabalioglu--video-reframer-web.modal.run"

# 1. Register
response = requests.post(f"{BASE_URL}/register?email=user@example.com")
api_key = response.json()["api_key"]
print(f"API Key: {api_key}")

# 2. Health check
response = requests.get(f"{BASE_URL}/health")
print(f"Health: {response.json()}")

# 3. Upload video
files = {"file": open("video.mp4", "rb")}
headers = {"X-API-Key": api_key}
response = requests.post(f"{BASE_URL}/process", files=files, headers=headers)
job_id = response.json()["job_id"]
print(f"Job ID: {job_id}")

# 4. Check status
response = requests.get(f"{BASE_URL}/job/{job_id}", headers=headers)
print(f"Status: {response.json()}")

# 5. Get results
response = requests.get(f"{BASE_URL}/results/{job_id}", headers=headers)
print(f"Results: {json.dumps(response.json(), indent=2)}")

# 6. List videos
response = requests.get(f"{BASE_URL}/videos", headers=headers)
print(f"Videos: {response.json()}")
```

---

## 📦 JavaScript/Fetch Example

```javascript
const BASE_URL = "https://sabalioglu--video-reframer-web.modal.run";

// 1. Register
async function register(email) {
  const response = await fetch(`${BASE_URL}/register?email=${email}`, {
    method: "POST"
  });
  return await response.json();
}

// 2. Get health
async function health() {
  const response = await fetch(`${BASE_URL}/health`);
  return await response.json();
}

// 3. Upload video
async function uploadVideo(file, apiKey) {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch(`${BASE_URL}/process`, {
    method: "POST",
    headers: { "X-API-Key": apiKey },
    body: formData
  });
  return await response.json();
}

// 4. Check job status
async function getJobStatus(jobId, apiKey) {
  const response = await fetch(`${BASE_URL}/job/${jobId}`, {
    headers: { "X-API-Key": apiKey }
  });
  return await response.json();
}

// 5. Get results
async function getResults(jobId, apiKey) {
  const response = await fetch(`${BASE_URL}/results/${jobId}`, {
    headers: { "X-API-Key": apiKey }
  });
  return await response.json();
}

// 6. List videos
async function listVideos(apiKey) {
  const response = await fetch(`${BASE_URL}/videos`, {
    headers: { "X-API-Key": apiKey }
  });
  return await response.json();
}

// Usage
(async () => {
  const user = await register("user@example.com");
  console.log("Registered:", user);

  const h = await health();
  console.log("Health:", h);
})();
```

---

## ⚠️ Error Handling

The API returns appropriate HTTP status codes:

- `200 OK` - Request successful
- `400 Bad Request` - Invalid parameters
- `401 Unauthorized` - Missing or invalid API key
- `404 Not Found` - Resource not found
- `500 Internal Server Error` - Server error

**Error Response Format:**
```json
{
  "status": "error",
  "message": "Invalid API key"
}
```

---

## 🔄 Rate Limits

Currently no rate limits applied. Future versions may implement rate limiting.

---

## 📈 Future Enhancements

The following features are planned for future releases:

- ✅ Batch video processing
- ✅ Webhook notifications
- ✅ Real-time WebSocket updates
- ✅ Advanced analytics
- ✅ Multi-region deployment

---

## 📞 Support

For issues or questions:
- Check `/health` endpoint first
- Review this documentation
- Check deployment logs on Modal dashboard

---

**Last Updated:** 2026-01-28
**API Version:** 1.0.0
