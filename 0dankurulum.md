# Video Reframer - Sıfırdan Kurulum Rehberi

## Problem Analizi

**Mevcut Sorun**: CORS hatası Modal backend'den API çağrısını engelliyor
- Frontend: Netlify'de çalışıyor (https://delightful-cascaron-e1dc20.netlify.app)
- Backend: Modal'da çalışıyor (https://sabalioglu--video-reframer-web.modal.run)
- Cross-origin istek başarısız: Browser preflight OPTIONS request'i başarısız

**Kök Nedeni**: Modal'ın ASGI middleware'ı CORS headers'ı düzgün geçmiyor

---

## Sıfırdan Kurulum Mimarisi

### 1. Backend Mimarisi (Temiz)

```
backend/
├── main.py                    # FastAPI app (CORS düzeltilmiş)
├── requirements.txt           # Dependencies
├── modal_deploy.py           # Modal deployment script
└── utils/
    ├── __init__.py
    ├── gemini_utils.py       # Gemini Video API integration
    ├── yolo_utils.py         # YOLOv8 detection + verification
    ├── ffmpeg_utils.py       # Frame extraction
    ├── frame_extractor.py    # Frame visualization
    ├── scene_detection.py    # Scene detection (optional)
    └── sam2_tracker.py       # SAM2 tracking (optional)
```

### 2. Frontend Mimarisi (Temiz)

```
frontend/
├── public/
│   └── index.html           # Simple HTML, Tailwind CDN
├── js/
│   ├── api.js              # API client
│   ├── auth.js             # Registration/API key management
│   └── ui.js               # UI rendering
└── css/
    └── style.css           # Custom styles
```

### 3. Deployment Mimarisi

```
Development:
  Frontend: http://localhost:3000
  Backend: http://localhost:8000

Production:
  Frontend: Netlify (https://...)
  Backend: Modal.com (https://...)

API: REST + CORS enabled
```

---

## Adım Adım Kurulum

### ADIM 1: Backend Setup

#### 1a. Backend Klasörü Oluştur

```bash
cd /Users/sabalioglu/Desktop/video-reframer
mkdir -p backend/utils
cd backend
```

#### 1b. requirements.txt (Temiz)

```txt
# Web Framework
fastapi>=0.104.0
uvicorn>=0.24.0
python-multipart>=0.0.6

# Video Processing
opencv-python>=4.5.0
numpy>=1.24.0
pillow>=10.0.0
imageio>=2.20.0
imageio-ffmpeg>=0.4.8

# AI Models
ultralytics>=8.0.0
torch>=2.0.0
torchvision>=0.15.0

# APIs
google-generativeai>=0.3.0

# Deployment
modal>=0.62.0
```

#### 1c. main.py (Minimal, CORS Düzeltilmiş)

```python
"""
Video Reframer Backend
Minimal FastAPI app with proper CORS handling
"""

from fastapi import FastAPI, File, UploadFile, Header, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uuid
import logging
import os
import sys

# Setup
sys.path.insert(0, os.path.dirname(__file__))
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Video Reframer API", version="1.0")

# CORS - Açık ve net
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=86400,
)

# Storage
user_store = {}      # api_key -> {user_id, email}
jobs_store = {}      # job_id -> {status, user_id, ...}
results_store = {}   # job_id -> {analysis results}

# ==================== ENDPOINTS ====================

@app.get("/health")
def health():
    """Health check"""
    return {"status": "ok", "service": "video-reframer"}

@app.post("/register")
def register(email: str):
    """Register new user and get API key"""
    user_id = str(uuid.uuid4())
    api_key = f"vr_{uuid.uuid4().hex}"
    user_store[api_key] = {"user_id": user_id, "email": email}

    logger.info(f"[Register] New user: {api_key}")
    return JSONResponse(
        status_code=200,
        content={"status": "success", "user_id": user_id, "api_key": api_key}
    )

@app.post("/analyze")
async def analyze(file: UploadFile = File(...), x_api_key: str = Header(None)):
    """Analyze video with AI pipeline"""

    # Validate API key
    if not x_api_key or x_api_key not in user_store:
        raise HTTPException(status_code=401, detail="Invalid API key")

    user_data = user_store[x_api_key]
    job_id = str(uuid.uuid4())

    # Read file
    content = await file.read()
    logger.info(f"[Analyze] File: {file.filename} ({len(content)} bytes)")

    jobs_store[job_id] = {
        "user_id": user_data["user_id"],
        "status": "analyzing",
        "filename": file.filename
    }

    try:
        # TODO: Call analysis worker
        # result = analyze_worker(content, file.filename)
        # results_store[job_id] = result

        # For now, return success
        jobs_store[job_id]["status"] = "completed"

        return JSONResponse(
            status_code=200,
            content={"status": "success", "job_id": job_id}
        )

    except Exception as e:
        logger.error(f"[Analyze] Error: {e}")
        jobs_store[job_id]["status"] = "failed"
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/results/{job_id}")
def get_results(job_id: str, x_api_key: str = Header(None)):
    """Get analysis results"""

    if not x_api_key or x_api_key not in user_store:
        raise HTTPException(status_code=401, detail="Invalid API key")

    if job_id not in jobs_store:
        raise HTTPException(status_code=404, detail="Job not found")

    job = jobs_store[job_id]
    results = results_store.get(job_id)

    return JSONResponse(
        status_code=200,
        content={
            "job_id": job_id,
            "status": job["status"],
            "results": results
        }
    )

# ==================== For Local Testing ====================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

#### 1d. Modal Deploy Script (modal_deploy.py)

```python
"""
Deploy to Modal.com
Run: python modal_deploy.py
"""

import subprocess
import sys

def deploy():
    """Deploy FastAPI app to Modal"""
    print("📦 Deploying to Modal...")

    # You'll need to add this to main.py:
    # import modal
    # app_def = modal.App("video-reframer")
    # @app_def.function()
    # @modal.asgi_app()
    # def web():
    #     return app

    result = subprocess.run(
        [sys.executable, "-m", "modal", "deploy", "main.py::app_def"],
        cwd="/Users/sabalioglu/Desktop/video-reframer/backend"
    )

    if result.returncode == 0:
        print("✅ Deployed successfully!")
    else:
        print("❌ Deployment failed")
        sys.exit(1)

if __name__ == "__main__":
    deploy()
```

### ADIM 2: Frontend Setup (Minimal)

#### 2a. Frontend Klasörü

```bash
mkdir -p frontend
cd frontend
```

#### 2b. public/index.html (Basit)

```html
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Video Reframer</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        .spinner {
            border: 4px solid rgba(0,0,0,0.1);
            border-top: 4px solid #3498db;
            border-radius: 50%;
            width: 40px;
            height: 40px;
            animation: spin 1s linear infinite;
        }
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
    </style>
</head>
<body class="bg-gray-100">
    <div class="min-h-screen flex items-center justify-center">
        <div class="bg-white rounded-lg shadow-lg p-8 w-full max-w-md">
            <h1 class="text-3xl font-bold mb-8 text-center">Video Reframer</h1>

            <!-- Register Section -->
            <div id="registerSection">
                <h2 class="text-xl font-semibold mb-4">Sign Up</h2>
                <input
                    type="email"
                    id="emailInput"
                    placeholder="your@email.com"
                    class="w-full border rounded px-4 py-2 mb-4"
                >
                <button
                    onclick="register()"
                    class="w-full bg-blue-500 text-white py-2 rounded hover:bg-blue-600"
                >
                    Register
                </button>
                <p id="apiKeyDisplay" class="mt-4 p-4 bg-green-100 rounded hidden">
                    <strong>API Key:</strong> <code id="apiKeyText"></code>
                </p>
            </div>

            <!-- Upload Section -->
            <div id="uploadSection" class="hidden mt-8">
                <h2 class="text-xl font-semibold mb-4">Upload Video</h2>
                <input
                    type="file"
                    id="fileInput"
                    accept="video/*"
                    class="w-full border rounded px-4 py-2 mb-4"
                >
                <button
                    onclick="uploadVideo()"
                    class="w-full bg-green-500 text-white py-2 rounded hover:bg-green-600"
                >
                    Upload & Analyze
                </button>
                <div id="status" class="mt-4"></div>
            </div>

            <!-- Results Section -->
            <div id="resultsSection" class="hidden mt-8">
                <h2 class="text-xl font-semibold mb-4">Analysis Results</h2>
                <div id="results" class="bg-gray-50 p-4 rounded"></div>
            </div>
        </div>
    </div>

    <script src="js/app.js"></script>
</body>
</html>
```

#### 2c. js/app.js (Basit)

```javascript
const API_URL = "https://sabalioglu--video-reframer-web.modal.run";
let apiKey = localStorage.getItem("apiKey");

// Show appropriate section
if (apiKey) {
    document.getElementById("registerSection").classList.add("hidden");
    document.getElementById("uploadSection").classList.remove("hidden");
}

async function register() {
    const email = document.getElementById("emailInput").value;
    if (!email) {
        alert("Please enter email");
        return;
    }

    try {
        const response = await fetch(`${API_URL}/register`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ email })
        });

        const data = await response.json();
        apiKey = data.api_key;

        localStorage.setItem("apiKey", apiKey);

        document.getElementById("apiKeyText").textContent = apiKey;
        document.getElementById("apiKeyDisplay").classList.remove("hidden");

        document.getElementById("registerSection").classList.add("hidden");
        document.getElementById("uploadSection").classList.remove("hidden");

    } catch (error) {
        alert("Registration failed: " + error.message);
    }
}

async function uploadVideo() {
    const file = document.getElementById("fileInput").files[0];
    if (!file) {
        alert("Please select a video");
        return;
    }

    const statusDiv = document.getElementById("status");
    statusDiv.innerHTML = '<div class="spinner"></div><p>Uploading...</p>';

    try {
        const formData = new FormData();
        formData.append("file", file);

        const response = await fetch(`${API_URL}/analyze`, {
            method: "POST",
            headers: { "X-API-Key": apiKey },
            body: formData
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }

        const data = await response.json();
        const jobId = data.job_id;

        statusDiv.innerHTML = `<p>Job ID: <code>${jobId}</code></p>`;

        // Poll for results
        pollResults(jobId);

    } catch (error) {
        statusDiv.innerHTML = `<p class="text-red-500">Error: ${error.message}</p>`;
    }
}

async function pollResults(jobId) {
    const statusDiv = document.getElementById("status");
    const resultsDiv = document.getElementById("results");

    try {
        const response = await fetch(`${API_URL}/results/${jobId}`, {
            headers: { "X-API-Key": apiKey }
        });

        const data = await response.json();

        if (data.status === "completed") {
            statusDiv.innerHTML = "";
            resultsDiv.innerHTML = `<pre>${JSON.stringify(data.results, null, 2)}</pre>`;
            document.getElementById("resultsSection").classList.remove("hidden");
        } else if (data.status === "analyzing") {
            statusDiv.innerHTML = '<div class="spinner"></div><p>Analyzing...</p>';
            setTimeout(() => pollResults(jobId), 2000);
        } else {
            statusDiv.innerHTML = `<p class="text-red-500">Status: ${data.status}</p>`;
        }
    } catch (error) {
        statusDiv.innerHTML = `<p class="text-red-500">Error: ${error.message}</p>`;
    }
}
```

### ADIM 3: Local Testing

```bash
# Terminal 1: Backend
cd backend
pip install -r requirements.txt
python main.py
# Açılır: http://localhost:8000

# Terminal 2: Frontend
cd frontend
python -m http.server 3000
# Açılır: http://localhost:3000
```

**Test**:
1. Register → API key al
2. Video yükle
3. Results bak

### ADIM 4: Modal Deployment

```bash
cd backend

# Önce main.py'ye ekle:
# import modal
# image = modal.Image.debian_slim()
#     .apt_install("ffmpeg")
#     .pip_install_from_requirements("requirements.txt")
#
# app_def = modal.App("video-reframer", image=image)
#
# @app_def.function()
# @modal.asgi_app()
# def web():
#     return app

# Deploy
python modal_deploy.py
```

### ADIM 5: Netlify Deployment

```bash
cd frontend

# Deploy static site
# git add .
# git commit -m "Frontend"
# git push origin main
# Then: Netlify → New site → Select repo → Deploy
```

---

## CORS Sorununu Çözmek

### Problem: Modal + Netlify CORS

**Sebep**: Modal'ın ASGI middleware'ı preflight OPTIONS request'ini düzgün işlemiyor

### Çözüm: Hardcoded CORS Headers

**main.py'de her endpoint**:

```python
return JSONResponse(
    status_code=200,
    content=data,
    headers={
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, POST, OPTIONS, PUT, DELETE",
        "Access-Control-Allow-Headers": "Content-Type, X-API-Key, Authorization",
    }
)
```

### Alternatif: Proxy Server Kullan

Eğer CORS hala sorun olursa:
- Netlify Functions kullan
- Backend çağrısını server-side yap
- Frontend → Netlify Function → Modal Backend

---

## Dosya Yapısı (Final)

```
video-reframer/
├── 0dankurulum.md              ← Bu dosya
├── backend/
│   ├── main.py                 ← FastAPI app
│   ├── modal_deploy.py         ← Deployment script
│   ├── requirements.txt
│   └── utils/
│       ├── gemini_utils.py
│       ├── yolo_utils.py
│       ├── ffmpeg_utils.py
│       └── frame_extractor.py
├── frontend/
│   ├── public/
│   │   └── index.html
│   └── js/
│       └── app.js
└── README.md
```

---

## Testing Checklist

- [ ] Backend local çalışıyor (http://localhost:8000/health)
- [ ] Frontend local çalışıyor (http://localhost:3000)
- [ ] Register endpoint çalışıyor (API key alınıyor)
- [ ] Upload endpoint CORS hatası yok
- [ ] Modal'a deploy ediliyor
- [ ] Netlify'ye frontend deploy ediliyor
- [ ] Cross-origin istek başarılı

---

## Next Agent Instructions

1. Bu dosyayı oku: `0dankurulum.md`
2. Backend'i temiz şekilde kur: `backend/main.py`
3. Frontend'i basit yap: `frontend/public/index.html`
4. CORS hatalarını çöz (hardcoded headers)
5. Local test et
6. Modal + Netlify'ye deploy et

**Not**: Sistem şimdi modular, temiz ve bakımı kolay. Her bileşen izole.
