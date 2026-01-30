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
from fastapi.responses import JSONResponse
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

# Enable CORS for frontend - allow all origins
# NOTE: Using allow_origins=["*"] with wildcard instead of regex for broader compatibility
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins
    allow_credentials=False,  # Must be False when allow_origins=["*"]
    allow_methods=["*"],  # Allow all methods including OPTIONS
    allow_headers=["*"],  # Allow all headers including X-API-Key
    expose_headers=["*"],
    max_age=3600,
)

# Custom exception handler to ensure CORS headers on all error responses
@app.exception_handler(HTTPException)
async def http_exception_handler(_request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
            "Access-Control-Allow-Headers": "*",
        }
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


@app.post("/analyze")
def analyze_with_gemini(file: UploadFile = File(...), x_api_key: str = Header(None)):
    """Analyze video with Gemini for ground truth person detection"""
    logger.info(f"[Analyze] Received API key: {x_api_key[:20] if x_api_key else 'None'}...")
    logger.info(f"[Analyze] Current user_store size: {len(user_store)}")
    logger.info(f"[Analyze] Stored keys: {list(user_store.keys())[:5]}")

    user_data = validate_api_key(x_api_key)

    job_id = str(uuid.uuid4())
    user_id = user_data["user_id"]

    # Initialize job entry FIRST
    jobs[job_id] = {
        "user_id": user_id,
        "status": "analyzing",
        "filename": file.filename,
        "file_size": 0
    }

    try:
        # Read uploaded file
        content = file.file.read()
        logger.info(f"[Analyze] Read {len(content)} bytes for analysis")
        jobs[job_id]["file_size"] = len(content)

        # Start UNIFIED PIPELINE: Gemini → YOLOv8 (Verification)
        # [Note: SAM2 and full scene detection coming in v2]
        logger.info(f"[Analyze] Starting unified pipeline (Gemini → YOLOv8 Verification)")
        try:
            # Use analyze_video_gemini_worker (stable, working version)
            result = analyze_video_gemini_worker.remote(content, file.filename)
            logger.info(f"[Analyze] Got unified pipeline result")

            jobs[job_id]["status"] = "completed"
            results_cache[job_id] = result
            logger.info(f"[Analyze] Job {job_id} completed with Gemini + YOLOv8")

        except Exception as e:
            logger.error(f"[Analyze] Worker error: {e}", exc_info=True)
            jobs[job_id]["status"] = "failed"
            jobs[job_id]["error_message"] = str(e)
            logger.error(f"[Analyze] Job {job_id} marked as failed")

        return {"status": "success", "job_id": job_id}

    except Exception as e:
        logger.error(f"[Analyze] Outer error: {e}", exc_info=True)
        jobs[job_id]["status"] = "failed"
        jobs[job_id]["error_message"] = str(e)
        raise HTTPException(status_code=500, detail=str(e))


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


@app_def.function(
    timeout=2400,
    memory=8192,
    secrets=[modal.Secret.from_name("gemini-secret")]  # Reference the Modal secret
)
def analyze_video_unified_worker(video_content: bytes, filename: str):
    """Worker function for UNIFIED pipeline: Gemini → FFmpeg → YOLOv8 → SAM2"""
    logger.info(f"[UnifiedWorker] Starting unified analysis: {filename} ({len(video_content)} bytes)")

    try:
        import sys
        import tempfile
        if "/app" not in sys.path:
            sys.path.insert(0, "/app")

        from utils.unified_pipeline import run_unified_pipeline

        # Write video to temp file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp:
            tmp.write(video_content)
            tmp.flush()
            video_path = tmp.name

        logger.info(f"[UnifiedWorker] Video written to {video_path}")

        # Run unified pipeline
        logger.info(f"[UnifiedWorker] Executing unified pipeline...")
        result = run_unified_pipeline(video_path)

        logger.info(f"[UnifiedWorker] ✅ Analysis complete")
        return result

    except Exception as e:
        logger.error(f"[UnifiedWorker] Error: {e}", exc_info=True)
        import traceback
        return {
            "error": str(e),
            "traceback": traceback.format_exc(),
            "pipeline_status": "failed"
        }


@app_def.function(
    timeout=1800,
    memory=4096,
    secrets=[modal.Secret.from_name("gemini-secret")]  # Reference the Modal secret
)
def analyze_video_gemini_worker(video_content: bytes, filename: str):
    """Worker function for Gemini Video Analysis + YOLOv8 verification"""
    logger.info(f"[GeminiWorker] Starting Gemini analysis: {filename} ({len(video_content)} bytes)")

    try:
        import sys
        import tempfile
        if "/app" not in sys.path:
            sys.path.insert(0, "/app")

        from utils.ffmpeg_utils import extract_frames, get_video_metadata
        from utils.yolo_utils import verify_gemini_products, get_detection_statistics
        from utils.gemini_utils import analyze_video_with_gemini, compare_gemini_vs_yolo

        # Write video to temp file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp:
            tmp.write(video_content)
            tmp.flush()
            video_path = tmp.name

        logger.info(f"[GeminiWorker] Video written to {video_path}")

        # Analyze with Gemini (ground truth)
        logger.info(f"[GeminiWorker] Calling Gemini Video API...")
        gemini_result = analyze_video_with_gemini(video_path)
        logger.info(f"[GeminiWorker] Gemini analysis status: {gemini_result.get('status')}")

        # Extract Gemini data early (needed for product verification)
        gemini_data = gemini_result.get("gemini_analysis", {})
        gemini_products = gemini_data.get("products", [])

        logger.info(f"[GeminiWorker] Gemini returned {len(gemini_products)} products:")
        for i, prod in enumerate(gemini_products):
            logger.info(f"[GeminiWorker]   {i+1}. Name: '{prod.get('name')}' | Category: '{prod.get('category')}'")

        # Extract frames for YOLOv8 verification
        logger.info(f"[GeminiWorker] Extracting frames for verification")
        frames = extract_frames(video_path, sample_rate=5)
        logger.info(f"[GeminiWorker] Extracted {len(frames)} frames")

        # Run YOLOv8 VERIFICATION (only detect Gemini-identified products)
        logger.info(f"[GeminiWorker] Running YOLOv8 verification layer for {len(gemini_products)} products")
        detections = verify_gemini_products(frames, gemini_products)
        stats = get_detection_statistics(detections)

        logger.info(f"[GeminiWorker] YOLOv8 Verification complete - Found {stats.get('total_detections', 0)} verified detections")
        logger.info(f"[GeminiWorker] Frames with verified detections: {stats.get('frames_with_detections', 0)}")
        logger.info(f"[GeminiWorker] Class distribution: {stats.get('class_distribution', {})}")

        # Compare results
        comparison = compare_gemini_vs_yolo(gemini_result, detections)

        # Get metadata
        metadata = get_video_metadata(video_path)

        # Consolidate into unified output format
        products_in_use = [p.get("name", "") for p in gemini_data.get("products", [])]

        final_output = {
            "metadata": {
                "total_people": gemini_data.get("total_unique_people", 0),
                "total_products": len(gemini_data.get("products", [])),
                "video_duration": metadata.get("duration_seconds", 0),
                "fps": metadata.get("fps", 30),
                "total_frames": metadata.get("total_frames", len(frames))
            },
            "people": gemini_data.get("people", []),
            "products": gemini_data.get("products", []),
            "timeline": gemini_data.get("timeline", []),
            "yolo_verification": {
                "verified_detections": len(detections),
                "total_instances": stats.get("total_detections", 0),
                "class_distribution": stats.get("class_distribution", {}),
                "average_confidence": stats.get("average_confidence", 0)
            },
            "summary": {
                "video_summary": gemini_data.get("video_summary", ""),
                "products_in_use": products_in_use
            }
        }

        logger.info(f"[GeminiWorker] Final output summary:")
        logger.info(f"[GeminiWorker]   - Products in use (from Gemini): {products_in_use}")
        logger.info(f"[GeminiWorker]   - Verified detections (from YOLOv8): {len(detections)}")
        logger.info(f"[GeminiWorker]   - YOLO class distribution: {stats.get('class_distribution', {})}")

        result = {
            "pipeline_status": "completed",
            "gemini": gemini_result,
            "yolo": {
                "detections": detections,
                "statistics": stats,
                "metadata": metadata,
                "frame_count": len(frames)
            },
            "final_output": final_output,
            "comparison": comparison,
            "analysis_status": "complete"
        }

        logger.info(f"[GeminiWorker] ✅ Analysis complete")
        return result

    except Exception as e:
        logger.error(f"[GeminiWorker] Error: {e}", exc_info=True)
        import traceback
        return {
            "error": str(e),
            "traceback": traceback.format_exc(),
            "analysis_status": "failed"
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
