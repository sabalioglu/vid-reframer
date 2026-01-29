"""
Video Reframer - AI-Powered Video Processing Pipeline
Integrates YOLOv8 detection + FFmpeg frame extraction
"""

import uuid
import logging
import modal
from fastapi import FastAPI, Header, File, UploadFile, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import sys
import os

# Add backend to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Video Reframer", version="1.0.0")

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins (restrict in production)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

users = {}
jobs = {}
results_cache = {}

# Request/Response Models
class RegisterRequest(BaseModel):
    email: str

# Try to import AI utilities (optional for MVP)
try:
    from utils.ffmpeg_utils import extract_frames, get_video_metadata
    from utils.yolo_utils import run_yolov8_detection, get_detection_statistics
    PROCESSING_AVAILABLE = True
    logger.info("✅ Video processing libraries loaded")
except ImportError as e:
    PROCESSING_AVAILABLE = False
    logger.warning(f"⚠️ Processing libraries not available: {e}")

@app.get("/health")
def health():
    return {"status": "healthy", "service": "video-reframer"}

@app.post("/register")
def register(req: RegisterRequest):
    user_id = str(uuid.uuid4())
    api_key = f"vr_{uuid.uuid4().hex}"
    users[api_key] = {"user_id": user_id, "email": req.email}
    return {"status": "success", "user_id": user_id, "api_key": api_key}

async def process_video_background(job_id: str, video_path: str):
    """Background task for video processing"""
    try:
        logger.info(f"Starting video processing for job {job_id}")
        jobs[job_id]["status"] = "extracting_frames"

        # Extract frames
        frames = extract_frames(video_path, sample_rate=1)
        logger.info(f"Extracted {len(frames)} frames")

        # Get metadata
        metadata = get_video_metadata(video_path)
        jobs[job_id]["metadata"] = metadata
        jobs[job_id]["status"] = "detecting_objects"

        # Run YOLOv8 detection
        if frames:
            detections = run_yolov8_detection(frames)
            stats = get_detection_statistics(detections)

            results_cache[job_id] = {
                "detections": detections,
                "statistics": stats,
                "metadata": metadata,
                "frame_count": len(frames)
            }

            jobs[job_id]["status"] = "complete"
            logger.info(f"✅ Job {job_id} completed")
        else:
            jobs[job_id]["status"] = "error"

    except Exception as e:
        logger.error(f"Error processing video: {e}")
        jobs[job_id]["status"] = "error"
        jobs[job_id]["error"] = str(e)

@app.post("/process")
def process(file: UploadFile = File(...), x_api_key: str = Header(None), background_tasks: BackgroundTasks = None):
    if not x_api_key or x_api_key not in users:
        return {"status": "error", "message": "Invalid API key"}

    job_id = str(uuid.uuid4())
    user_id = users[x_api_key]["user_id"]

    try:
        # Save uploaded file
        import tempfile
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp:
            content = file.file.read()
            tmp.write(content)
            temp_path = tmp.name

        jobs[job_id] = {
            "user_id": user_id,
            "status": "processing",
            "filename": file.filename,
            "file_size": len(content)
        }

        # Start background processing if available
        if PROCESSING_AVAILABLE and background_tasks:
            background_tasks.add_task(process_video_background, job_id, temp_path)
        else:
            # MVP mode: instant completion with mock data
            results_cache[job_id] = {
                "detections": {},
                "statistics": {
                    "total_detections": 0,
                    "frames_with_detections": 0,
                    "average_confidence": 0.0,
                    "class_distribution": {}
                },
                "metadata": {"duration": 0, "fps": 30}
            }
            jobs[job_id]["status"] = "complete"

        return {"status": "success", "job_id": job_id}

    except Exception as e:
        logger.error(f"Error in /process: {e}")
        return {"status": "error", "message": str(e)}

@app.get("/job/{job_id}")
def get_job(job_id: str, x_api_key: str = Header(None)):
    if not x_api_key or x_api_key not in users:
        return {"status": "error"}
    if job_id not in jobs:
        return {"status": "error"}
    return {"job_id": job_id, "status": jobs[job_id]["status"]}

@app.get("/results/{job_id}")
def get_results(job_id: str, x_api_key: str = Header(None)):
    if not x_api_key or x_api_key not in users:
        return {"status": "error"}
    if job_id not in jobs:
        return {"status": "error"}

    if job_id not in results_cache:
        return {"job_id": job_id, "status": jobs[job_id]["status"], "results": None}

    return {
        "job_id": job_id,
        "status": "complete",
        "results": results_cache[job_id]
    }

@app.get("/videos")
def list_videos(x_api_key: str = Header(None)):
    if not x_api_key or x_api_key not in users:
        return {"status": "error"}
    user_id = users[x_api_key]["user_id"]
    user_jobs = [{"job_id": jid, **jobs[jid]} for jid in jobs if jobs[jid]["user_id"] == user_id]
    return {"status": "success", "videos": user_jobs}

# Build Modal image with all dependencies
image = (
    modal.Image.debian_slim()
    .apt_install("ffmpeg")  # System-level dependency for ffmpeg
    .pip_install_from_requirements("requirements.txt")
)

app_def = modal.App("video-reframer", image=image)

@app_def.function()
@modal.asgi_app()
def web():
    return app
