# Video Reframer - Setup Guide

**Last Updated:** 2026-01-28
**Foundation:** KEMIK project phase 1 + Modal deployment

---

## Prerequisites

- Python 3.10+
- Modal account (https://modal.com)
- Gemini API key
- Neon account (https://neon.tech)
- Netlify account (https://netlify.com)

---

## Step 1: Clone & Install Backend

```bash
cd ~/Desktop/video-reframer/backend
pip install -r requirements.txt
```

### Key Dependencies
- **modal** - Serverless compute
- **fastapi** - REST API framework
- **opencv-python** - Image processing
- **ultralytics** - YOLOv8 model
- **sam2** - SAM2 segmentation
- **bytetrack** - Object tracking
- **google-generativeai** - Gemini API
- **asyncpg** - Neon database driver

---

## Step 2: Set Up Credentials

### 2a. Modal Authentication
```bash
modal token set \
  --token-id ak-eeLoMx6PdNiH4pA49hEIgp \
  --token-secret as-NlD7cX3M1jY3O0pUrwVG5j
```

### 2b. Create Environment File
```bash
cp .env.example .env
```

Edit `.env`:
```bash
# Modal
MODAL_TOKEN_ID=ak-eeLoMx6PdNiH4pA49hEIgp
MODAL_TOKEN_SECRET=as-NlD7cX3M1jY3O0pUrwVG5j

# Gemini
GEMINI_API_KEY=YOUR-GEMINI-API-KEY-HERE

# Neon Database
DATABASE_URL=postgresql://user:pass@ep-xxx.neon.tech/db?sslmode=require

# Frontend
VITE_API_URL=https://video-reframer-api.modal.run
```

### 2c. Modal Secrets
```bash
# Create Gemini secret
modal secret create gemini-api \
  GEMINI_API_KEY=YOUR-GEMINI-API-KEY-HERE

# Create Neon secret (after DB setup)
modal secret create neon-db \
  DATABASE_URL="postgresql://..."
```

---

## Step 3: Set Up Neon Database

### 3a. Create Account & Database
1. Go to https://neon.tech
2. Create new database `video-reframer`
3. Copy connection string

### 3b. Run Schema
```bash
# Using psql
psql "postgresql://user:pass@ep-xxx.neon.tech/video-reframer?sslmode=require" \
  -f database/schema.sql

# Or: Copy SQL from database/schema.sql and run in Neon console
```

### 3c. Verify Schema
```sql
\dt  -- List tables
SELECT * FROM users;  -- Should be empty
```

---

## Step 4: Deploy Backend (Modal)

```bash
cd ~/Desktop/video-reframer/backend
modal deploy main.py
```

Output should show:
```
Building image...
Deploying...
Deployed at: https://sabalioglu--video-reframer-app.modal.run
```

Save this URL - you'll need it for the frontend.

### Test Backend Health
```bash
curl https://sabalioglu--video-reframer-app.modal.run/health
```

Expected response:
```json
{
  "status": "healthy",
  "database": "connected",
  "models": ["yolov8", "sam2", "bytetrack"]
}
```

---

## Step 5: Deploy Frontend (Netlify)

### 5a. Update API URL
Edit `frontend/app.js`:
```javascript
const API_URL = "https://sabalioglu--video-reframer-app.modal.run";
```

### 5b. Deploy to Netlify
```bash
# Option 1: Netlify CLI
cd ~/Desktop/video-reframer/frontend
netlify deploy --prod

# Option 2: Drag & Drop
# Visit: https://app.netlify.com/drop
# Drag: frontend folder
```

Save the deployment URL (e.g., `https://video-reframer-xxxxx.netlify.app`)

### 5c. Update CORS (Important!)
Edit `backend/main.py`:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://video-reframer-xxxxx.netlify.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

Redeploy:
```bash
cd ~/Desktop/video-reframer/backend
modal deploy main.py
```

---

## Step 6: Test End-to-End

### 6a. Register User
```bash
curl -X POST https://sabalioglu--video-reframer-app.modal.run/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com"}'
```

Response:
```json
{
  "api_key": "vr_xxxxxxxxxxxx",
  "user_id": "uuid"
}
```

### 6b. Upload Video
```bash
curl -X POST https://sabalioglu--video-reframer-app.modal.run/process \
  -H "X-API-Key: vr_xxxxxxxxxxxx" \
  -F "file=@/Users/sabalioglu/Downloads/video.mp4"
```

Response:
```json
{
  "job_id": "job_xxxx",
  "status": "processing"
}
```

### 6c. Check Status
```bash
curl https://sabalioglu--video-reframer-app.modal.run/job/job_xxxx \
  -H "X-API-Key: vr_xxxxxxxxxxxx"
```

### 6d. Get Results
```bash
curl https://sabalioglu--video-reframer-app.modal.run/results/job_xxxx \
  -H "X-API-Key: vr_xxxxxxxxxxxx" | jq .
```

---

## Troubleshooting

### "FFmpeg not found"
```bash
# Modal should auto-install, but verify:
modal run -q 'apt install ffmpeg'
```

### "Database connection refused"
```bash
# Check Neon connection string
psql "postgresql://..." -c "SELECT 1"

# Verify Modal secret
modal secret list
```

### "API timeout"
- Long videos need async processing
- Check Modal logs: `modal app logs video-reframer`
- Increase timeout in `backend/config/modal_config.py`

### "CORS error in frontend"
- Update `allow_origins` in `backend/main.py`
- Redeploy: `modal deploy main.py`

### "SAM2 out of memory"
- Use Modal A10G GPU (expensive but necessary)
- Or reduce frame sampling rate

---

## Development Workflow

### Local Testing (without Modal)
```bash
cd ~/Desktop/video-reframer/backend

# Install dev dependencies
pip install -r requirements.txt

# Run locally (won't work for models, but good for API testing)
python main.py
```

### Deploying Updates
```bash
# 1. Edit backend code
nano ~/Desktop/video-reframer/backend/main.py

# 2. Redeploy to Modal
cd ~/Desktop/video-reframer/backend
modal deploy main.py

# 3. Update frontend if needed
cd ../frontend
netlify deploy --prod
```

### Checking Modal Logs
```bash
# View last 100 lines
modal app logs video-reframer -n 100

# Stream logs (live)
modal app logs video-reframer --follow
```

---

## Production Checklist

- [ ] Neon database created & schema deployed
- [ ] Modal API deployed & health check passing
- [ ] Frontend deployed to Netlify
- [ ] CORS configured with correct Netlify domain
- [ ] Test video processed successfully
- [ ] Results saved to database
- [ ] Custom domain configured (optional)
- [ ] Rate limiting enabled (TODO)
- [ ] Error handling tested
- [ ] Documentation updated

---

## Cost Monitoring

### Modal
```bash
# Check usage
modal acct info  # Shows credits used

# Monitor deployment
modal app list   # List all apps
```

### Neon
```bash
# Monitor database size
# Via https://neon.tech console
SELECT pg_size_pretty(pg_database_size('video-reframer'));
```

### Netlify
- Check dashboard: https://app.netlify.com
- Bandwidth usage in Settings → Usage

---

## Next Steps

1. Complete YOLOv8 detection module
2. Add SAM2 segmentation
3. Implement ByteTrack tracking
4. Test with various video formats
5. Optimize performance with Modal A10G
6. Add async job queue for long videos

---

**Setup Time:** ~30 minutes (all services)
**Cost:** Free tier sufficient for 100+ videos
**Support:** Check README.md for troubleshooting
