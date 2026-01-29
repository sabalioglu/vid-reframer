# Video Reframer - Agent Handoff Document

**Date:** 2026-01-29 (Updated)
**Status:** ✅ **Core YOLOv8 working + Gemini integration added for ground truth**
**Constraint:** ⚠️ **ONLY modify /Users/sabalioglu/Desktop/video-reframer/, NEVER modify KEMIK**

---

## 🎯 Current Status

### ✅ Working
- **Backend (Modal):** Fully operational
  - Registration: ✅ Creates API keys
  - Upload: ✅ Accepts video files (8.5MB test video)
  - Processing: ✅ Extracts 153 frames, detects 1063 objects
  - Results: ✅ Returns JSON with detections and statistics
  - Time: ~52-54 seconds end-to-end

- **Frontend (Netlify):** Deployed and partially working
  - Registration form: ✅ Works
  - Video upload: ✅ Works (after CORS fix)
  - Polling: ✅ Works
  - JSON display: ✅ Shows raw detections (proof data exists!)

### ✅ Recently Fixed
- **Results Display:** ✅ Fixed in commits f285575 + 0d0eabc
  - Fixed detection data path: `results.detections` (not `detections`)
  - Fixed product counting: exact match instead of substring match
  - **Result:** Now shows correct: Persons=130, Products=102, Frames=130

### 🆕 Phase 2: Gemini Ground Truth + Verification
- **New Endpoint:** `POST /analyze` - Gemini Video API analysis
  - Analyzes video with Gemini 2.0 to extract unique people count
  - Returns timestamps for when each person appears
  - Compares Gemini results with YOLOv8 detections
  - **Status:** ✅ Backend code ready, needs API key setup

---

## 🔧 Technical Stack

### Backend
```
Modal.com serverless platform
├─ FastAPI REST API
├─ YOLOv8 object detection (1063 detections on test video)
├─ imageio frame extraction (153 frames sampled every 5th)
├─ In-memory storage (API keys + job results)
└─ CORS: wildcard allow_origins=["*"]
```

**URL:** https://sabalioglu--video-reframer-web.modal.run

### Frontend
```
Vanilla JavaScript + HTML/Tailwind CSS
├─ Registration → API key saved to localStorage
├─ Video upload → FormData with X-API-Key header
├─ Polling → GET /job/{job_id} every 1 second
├─ Results fetch → GET /results/{job_id}
└─ Display → Parse detections and show stats
```

**URL:** https://video-reframer.netlify.app (auto-deployed from main branch)

---

## 📊 Test Results (Last Run)

**Input Video:** 8.5 MB Cloudinary video
**Output (Backend):**
```json
{
  "frame_count": 153,
  "detections": {
    "frame_0": [
      {
        "class_id": 0,
        "class_name": "person",
        "confidence": 0.904,
        "bbox": {...}
      },
      ...
    ]
  },
  "statistics": {
    "total_detections": 1063,
    "average_confidence": 0.85
  }
}
```

**Frontend Display Issue:**
```
Shows: Persons Found: 0
Should show: Persons Found: [count of class_name="person"]
```

---

## 🐛 Current Debug Session

### Problem
- Backend returns correct JSON with detections
- Frontend shows JSON correctly (user can see "class_name": "person")
- But `displayResults()` function displays 0 for all counts

### Debug Code Added (commit 96c87bf)
Added detailed console logging in `displayResults()`:
```javascript
console.log('[displayResults] Detections:', Object.keys(detections).length, 'frames');
console.log('[displayResults] First detection class_name:', className);
console.log('[displayResults] Results: persons=', personCount);
```

### Next Steps
1. **Wait for Netlify deploy** (2-3 minutes after last push)
2. **Hard refresh incognito tab:** Ctrl+Shift+R (Windows) or Cmd+Shift+R (Mac)
3. **Upload a new video**
4. **Open browser console (F12)** and check for logs:
   - Look for `[displayResults]` prefix
   - Check if `Detections: X frames` appears
   - Verify `class_name` is being parsed
   - See actual count vs 0

---

## 📁 Key Files & Commands

### Critical Files
```
/Users/sabalioglu/Desktop/video-reframer/

Backend:
├── backend/main.py              # FastAPI + Modal config
├── backend/requirements.txt      # Dependencies
├── backend/utils/ffmpeg_utils.py # Frame extraction (imageio)
└── backend/utils/yolo_utils.py   # YOLOv8 detection

Frontend:
├── frontend/app.js              # Main logic (displayResults function line 323)
├── frontend/index.html          # UI (results section at line 240)
├── frontend/.netlify/netlify.toml # Deploy config
└── package.json                 # (Frontend has no build step - vanilla JS)
```

### Deploy Commands
```bash
# Backend - Deploy to Modal
cd /Users/sabalioglu/Desktop/video-reframer/backend
modal deploy main.py::app_def

# Frontend - Auto-deployed by Netlify on git push
cd /Users/sabalioglu/Desktop/video-reframer
git add .
git commit -m "..."
git push origin main
```

### Test Command
```bash
python3 << 'EOF'
import requests
import time

BASE_URL = "https://sabalioglu--video-reframer-web.modal.run"

# Register
resp = requests.post(f"{BASE_URL}/register", json={"email": "test@modal.com"}, timeout=10)
api_key = resp.json()["api_key"]

# Download video
video = requests.get("https://res.cloudinary.com/dlnh3x5ki/video/upload/v1769685602/video_ksyyrf.mp4", timeout=30)

# Upload
files = {'file': ('test.mp4', video.content, 'video/mp4')}
headers = {'X-API-Key': api_key}
resp = requests.post(f"{BASE_URL}/process", files=files, headers=headers, timeout=120)
job_id = resp.json()["job_id"]

# Wait for completion
for i in range(180):
    resp = requests.get(f"{BASE_URL}/job/{job_id}", headers=headers, timeout=10)
    if resp.json()["status"] == "completed":
        break
    time.sleep(1)

# Get results
resp = requests.get(f"{BASE_URL}/results/{job_id}", headers=headers, timeout=10)
results = resp.json()["results"]
print(f"Frames: {results['frame_count']}")
print(f"Detections: {results['statistics']['total_detections']}")
EOF
```

---

## 🔍 The Bug: displayResults() Function

**Location:** `/Users/sabalioglu/Desktop/video-reframer/frontend/app.js` line 323

**Expected Behavior:**
```javascript
// For each detection in detections object
// Count if class_name === 'person' → personCount++
// Count if class_name includes 'oven', 'cup', etc. → productCount++
// Display counts in UI
```

**Actual Behavior:**
```javascript
// Counts stay 0 even though JSON shows detections exist
```

**Possible Causes:**
1. `detections` object is empty (not passed correctly from API)
2. `class_name` field is not being read (wrong field name?)
3. Loop not executing (detections structure is different)
4. UI not updating (DOM element IDs wrong?)

**How to Fix:**
- Check console logs output when video completes
- Verify `detections` object structure
- Check if `class_name` exists in detection objects
- Verify loop is executing and counting

---

## 📝 Recent Commits

```
96c87bf debug: add detailed logging to displayResults function
2eed283 fix: simplify CORS configuration using wildcard instead of regex
253c2a9 fix: correct detection class_name field in results display
903fa2a fix: add CORS headers to error responses with regex pattern
f948a93 feat: working YOLOv8 video processing pipeline with imageio
```

---

## 🚀 Next Steps

### Frontend Testing (Already Complete)
- [x] Fixed displayResults() function (data path)
- [x] Fixed product counting (exact match)
- [x] Deployed to Netlify
- [x] Verified counts now show correctly

### Gemini Integration Setup
- [ ] **Set GOOGLE_API_KEY environment variable** on Modal
  - Get API key from: https://aistudio.google.com/apikey
  - On Modal dashboard: Settings → Environment Variables
  - Set: `GOOGLE_API_KEY=<your-key>`
- [ ] Test new `/analyze` endpoint with test video
- [ ] Verify Gemini returns person counts with timestamps
- [ ] Check /results shows comparison (Gemini vs YOLOv8)
- [ ] Optionally add ByteTrack for object tracking

### Full Workflow Test
1. Register user
2. Upload video (existing `/process` for YOLOv8 only)
3. Upload same video to `/analyze` for Gemini + YOLOv8
4. Compare results: Gemini unique people vs YOLOv8 per-frame

---

## 💡 Important Notes

1. **Frame Sampling:** Every 5th frame is extracted (sample_rate=5) to speed up processing. Full processing would be slower.

2. **CORS:** Netlify generates new preview URLs on each deployment. Fixed with wildcard `allow_origins=["*"]`.

3. **Processing Time:** ~52 seconds because:
   - First run downloads YOLOv8 model (~200MB)
   - Subsequent runs will be faster (cached)
   - imageio library is reliable for video reading

4. **In-Memory Storage:** API keys and results stored in app memory. Persists within Modal container. Clears on redeploy.

5. **Test Video:** Public Cloudinary URL that works for testing
   ```
   https://res.cloudinary.com/dlnh3x5ki/video/upload/v1769685602/video_ksyyrf.mp4
   ```

---

## 📞 Contact

If stuck, check:
1. Browser console for errors
2. Modal logs: https://modal.com/apps/sabalioglu/main/deployed/video-reframer
3. Recent git commits for context
4. This file for debugging steps

Good luck! 🎯
