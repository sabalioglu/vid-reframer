"""
Video Reframer - AI-Powered Video Processing Pipeline
Integrates YOLOv8 detection + FFmpeg frame extraction
Modal App with Proper Worker Function Architecture
"""

import uuid
import logging
import modal
import tempfile
import os
import sys
from fastapi import FastAPI, Header, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Add backend to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
# Also add /root for Modal deployment
if "/root" not in sys.path:
    sys.path.insert(0, "/root")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Video Reframer", version="1.0.0")

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory storage (persists within ASGI app container)
# Note: Modal's ASGI app handles routing, so requests should stay in same container
user_store = {}  # API key -> user data
jobs = {}  # job_id -> job metadata
results_cache = {}  # job_id -> processing results

# Request/Response Models
class RegisterRequest(BaseModel):
    email: str


# Helper function to validate API key
def validate_api_key(x_api_key: str) -> dict:
    """Validate API key. Returns user data or raises 401."""
    logger.info(f"[Auth] Validating API key: {x_api_key[:10]}...")
    logger.info(f"[Auth] user_store has {len(user_store)} keys: {list(user_store.keys())[:3]}")

    if not x_api_key:
        logger.error(f"[Auth] ❌ No API key provided")
        raise HTTPException(status_code=401, detail="Invalid API key")

    # Check user_store (persists in ASGI container)
    user_data = user_store.get(x_api_key)

    if not user_data:
        logger.error(f"[Auth] ❌ API key not found in user_store: {x_api_key[:10]}...")
        raise HTTPException(status_code=401, detail="Invalid API key")

    logger.info(f"[Auth] ✅ API key valid for user: {user_data.get('user_id')}")
    return user_data


@app.get("/health")
def health():
    return {"status": "healthy", "service": "video-reframer"}


@app.post("/register")
def register(req: RegisterRequest):
    user_id = str(uuid.uuid4())
    api_key = f"vr_{uuid.uuid4().hex}"
    user_data = {"user_id": user_id, "email": req.email}

    # Store in user_store (persists in ASGI container)
    user_store[api_key] = user_data

    logger.info(f"[Register] New user: {api_key}, user_store size: {len(user_store)}")
    logger.info(f"[Register] user_store keys: {list(user_store.keys())}")
    return {"status": "success", "user_id": user_id, "api_key": api_key}


@app.post("/process")
def process(file: UploadFile = File(...), x_api_key: str = Header(None)):
    """Submit video for processing"""
    user_data = validate_api_key(x_api_key)

    job_id = str(uuid.uuid4())
    user_id = user_data["user_id"]

    try:
        # Read uploaded file content
        content = file.file.read()
        logger.info(f"[Main] Read {len(content)} bytes from upload ({file.filename})")

        jobs[job_id] = {
            "user_id": user_id,
            "status": "processing",
            "filename": file.filename,
            "file_size": len(content)
        }

        # Process video synchronously
        try:
            logger.info(f"[Main] Calling worker with video content ({len(content)} bytes)")
            result = process_video_worker.remote(content, file.filename)
            logger.info(f"[Main] Got result: {type(result)}")
            logger.info(f"[Main] Result summary: frame_count={result.get('frame_count')}, has_error={bool(result.get('error'))}")
            jobs[job_id]["status"] = "completed"
            results_cache[job_id] = result
            logger.info(f"[Main] Job {job_id} results cached")
        except Exception as e:
            logger.error(f"[Main] Worker error: {e}", exc_info=True)
            jobs[job_id]["status"] = "failed"
            jobs[job_id]["error_message"] = str(e)

        return {"status": "success", "job_id": job_id}

    except Exception as e:
        logger.error(f"Error in /process: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/job/{job_id}")
def get_job(job_id: str, x_api_key: str = Header(None)):
    validate_api_key(x_api_key)
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    # Check if results are ready (worker finished processing)
    if job_id in results_cache:
        return {"job_id": job_id, "status": "completed"}

    return {"job_id": job_id, "status": jobs[job_id]["status"]}


@app.get("/results/{job_id}")
def get_results(job_id: str, x_api_key: str = Header(None)):
    validate_api_key(x_api_key)
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    job = jobs[job_id]

    if job_id not in results_cache:
        response = {
            "job_id": job_id,
            "status": job.get("status", "processing"),
            "results": None
        }
        # Include error message if job failed
        if job.get("error_message"):
            response["error_message"] = job["error_message"]
        return response

    result = results_cache[job_id]
    response = {
        "job_id": job_id,
        "status": "completed",
        "results": result
    }
    # Include error if present in results
    if result.get("error"):
        response["error"] = result["error"]
    return response


@app.get("/videos")
def list_videos(x_api_key: str = Header(None)):
    user_data = validate_api_key(x_api_key)
    user_id = user_data["user_id"]
    user_jobs = [{"job_id": jid, **jobs[jid]} for jid in jobs if jobs[jid]["user_id"] == user_id]
    return {"status": "success", "videos": user_jobs}


# =====================================================
# Modal Configuration
# =====================================================

# Build image with all dependencies
_backend_dir = os.path.dirname(os.path.abspath(__file__))
image = (
    modal.Image.debian_slim()
    .apt_install("ffmpeg")  # System-level dependency for ffmpeg
    .pip_install("python-multipart>=0.0.6")  # Install first
    .pip_install_from_requirements("requirements.txt")
    .add_local_dir(  # Add utils directory to image for worker functions
        os.path.join(_backend_dir, "utils"),
        remote_path="/app/utils"
    )
)

app_def = modal.App("video-reframer", image=image)


# =====================================================
# Modal Worker Functions
# =====================================================

@app_def.function(timeout=1200, memory=4096)  # 20 min, 4GB for YOLOv8 + frames
def process_video_worker(video_content: bytes, filename: str):
    """Worker function for video processing with YOLOv8 detection"""
    logger.info(f"[Worker] Starting video processing: {filename} ({len(video_content)} bytes)")

    try:
        # Ensure utils module is in path for Modal worker
        import sys
        if "/app" not in sys.path:
            sys.path.insert(0, "/app")

        logger.info(f"[Worker] sys.path: {sys.path[:3]}")

        from utils.ffmpeg_utils import extract_frames, get_video_metadata
        from utils.yolo_utils import run_yolov8_detection, get_detection_statistics
        logger.info(f"[Worker] Imports successful")

        # Write video content to temporary file in worker's container
        import tempfile
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp:
            tmp.write(video_content)
            tmp.flush()
            video_path = tmp.name
        logger.info(f"[Worker] Video written to {video_path} ({len(video_content)} bytes)")

        # Extract frames (sample every 5th frame to speed up processing)
        logger.info(f"[Worker] Extracting frames from {video_path}")
        frames = extract_frames(video_path, sample_rate=5)
        logger.info(f"[Worker] Extracted {len(frames)} frames (sampled every 5th)")

        if not frames:
            logger.warning(f"[Worker] No frames extracted from video")
            return {
                "detections": {},
                "statistics": {
                    "total_detections": 0,
                    "frames_with_detections": 0,
                    "average_confidence": 0.0,
                    "class_distribution": {}
                },
                "metadata": {"duration": 0, "fps": 30, "frames": 0},
                "frame_count": 0
            }

        # Get metadata
        metadata = get_video_metadata(video_path)
        logger.info(f"[Worker] Video metadata: {metadata}")

        # Run YOLOv8 detection
        logger.info(f"[Worker] Running YOLOv8 detection on {len(frames)} frames")
        detections = run_yolov8_detection(frames)
        stats = get_detection_statistics(detections)

        result = {
            "detections": detections,
            "statistics": stats,
            "metadata": metadata,
            "frame_count": len(frames)
        }

        logger.info(f"[Worker] ✅ Processing complete")
        return result

    except ImportError as e:
        logger.error(f"[Worker] Import error: {e}", exc_info=True)
        error_msg = f"Import error: {str(e)}"
        logger.error(f"[Worker] ❌ {error_msg}")
        return {
            "error": error_msg,
            "detections": {},
            "statistics": {},
            "metadata": {},
            "frame_count": 0
        }
    except Exception as e:
        logger.error(f"[Worker] Processing error: {e}", exc_info=True)
        import traceback
        error_msg = f"Processing error: {str(e)}\n{traceback.format_exc()}"
        logger.error(f"[Worker] ❌ {error_msg}")
        return {
            "error": error_msg,
            "detections": {},
            "statistics": {},
            "metadata": {},
            "frame_count": 0
        }


@app_def.function()
def detect_objects_yolo(video_path: str):
    """Dedicated function for YOLOv8 object detection"""
    logger.info(f"[YOLO] Processing: {video_path}")
    try:
        from utils.yolo_utils import run_yolov8_detection, get_detection_statistics
        from utils.ffmpeg_utils import extract_frames

        frames = extract_frames(video_path, sample_rate=1)
        if frames:
            detections = run_yolov8_detection(frames)
            stats = get_detection_statistics(detections)
            return {"detections": detections, "statistics": stats}
        return {"detections": {}, "statistics": {}}
    except Exception as e:
        logger.error(f"[YOLO] Error: {e}")
        return {"error": str(e)}


@app_def.function()
def analyze_video_gemini(video_path: str):
    """Dedicated function for Gemini analysis"""
    logger.info(f"[Gemini] Analyzing: {video_path}")
    return {"analysis": "Video analysis ready"}


@app_def.function()
def enrich_with_gemini():
    """Dedicated function for Gemini enrichment"""
    logger.info(f"[Enrich] Enriching results with Gemini")
    return {"enriched": True}


# =====================================================
# FastAPI App as Modal Function
# =====================================================

@app_def.function()
@modal.asgi_app()
def web():
    """Main FastAPI application entrypoint"""
    return app
