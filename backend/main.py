"""
Video Reframer - Working Version
"""

import uuid
import modal
from fastapi import FastAPI, Header, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

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

# Request/Response Models
class RegisterRequest(BaseModel):
    email: str

@app.get("/health")
def health():
    return {"status": "healthy", "service": "video-reframer"}

@app.post("/register")
def register(req: RegisterRequest):
    user_id = str(uuid.uuid4())
    api_key = f"vr_{uuid.uuid4().hex}"
    users[api_key] = {"user_id": user_id, "email": req.email}
    return {"status": "success", "user_id": user_id, "api_key": api_key}

@app.post("/process")
def process(file: UploadFile = File(...), x_api_key: str = Header(None)):
    if not x_api_key or x_api_key not in users:
        return {"status": "error", "message": "Invalid API key"}
    job_id = str(uuid.uuid4())
    jobs[job_id] = {
        "user_id": users[x_api_key]["user_id"],
        "status": "processing",
        "filename": file.filename,
        "file_size": file.size
    }
    return {"status": "success", "job_id": job_id}

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
    return {"job_id": job_id, "status": "complete", "results": {}}

@app.get("/videos")
def list_videos(x_api_key: str = Header(None)):
    if not x_api_key or x_api_key not in users:
        return {"status": "error"}
    user_id = users[x_api_key]["user_id"]
    user_jobs = [{"job_id": jid, **jobs[jid]} for jid in jobs if jobs[jid]["user_id"] == user_id]
    return {"status": "success", "videos": user_jobs}

image = modal.Image.debian_slim().pip_install("fastapi", "uvicorn")
app_def = modal.App("video-reframer", image=image)

@app_def.function()
@modal.asgi_app()
def web():
    return app
