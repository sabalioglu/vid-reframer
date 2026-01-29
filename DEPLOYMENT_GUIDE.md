# 🚀 Deployment Guide - Video Reframer Phase 2

**Target Platform:** Modal
**Environment:** Production
**Expected Time:** 20-30 minutes

---

## Prerequisites

Before deployment, ensure you have:

- ✅ Modal account (free tier available)
- ✅ Gemini API key (already configured)
- ✅ Neon PostgreSQL connection (already set up)
- ✅ Netlify frontend deployed
- ✅ Python 3.11+
- ✅ Git access

---

## Step 1: Verify Local Dependencies

```bash
# Navigate to project
cd /Users/sabalioglu/Desktop/video-reframer

# Check Python version
python3 --version  # Should be 3.11+

# Install requirements locally (optional, for testing)
pip install -r backend/requirements.txt

# Verify imports work
python3 -c "from utils import run_yolov8_detection; print('✅ Imports OK')"
```

---

## Step 2: Configure Modal

### 2.1 Verify Modal Setup

```bash
# Check if Modal CLI is installed
modal --version

# If not installed:
pip install modal

# Authenticate with Modal
modal setup
# Follow interactive prompt to enter your API token
```

### 2.2 Verify Modal Secrets

Secrets should already be configured, but verify:

```bash
# List all secrets
modal secret list

# Should see:
# gemini-api
# neon-db
```

**If secrets missing, create them:**

```bash
# Get Gemini API key from Google Cloud (stored in .env, never commit)
echo "GEMINI_API_KEY=$GEMINI_API_KEY" | \
  modal secret create gemini-api

# Get Neon connection string
echo "DATABASE_URL=postgresql://..." | \
  modal secret create neon-db
```

---

## Step 3: Prepare for Deployment

### 3.1 Update CORS Origins (if using custom domain)

Edit `backend/config/modal_config.py`:

```python
ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "https://delightful-cascaron-e1dc20.netlify.app",  # Keep existing
    "https://yourdomain.com",  # Add your domain
]
```

### 3.2 Verify Requirements

```bash
# Check all dependencies are in requirements.txt
grep -E "ultralytics|torch|sam2|ByteTrack|google-generativeai" \
  backend/requirements.txt

# Should see all major packages
```

### 3.3 Test Locally (Optional)

```bash
# Start local development server
cd backend
python main.py

# Test endpoints
curl http://localhost:8000/health
```

---

## Step 4: Deploy to Modal

### 4.1 Deploy the Application

```bash
# Navigate to backend directory
cd /Users/sabalioglu/Desktop/video-reframer/backend

# Deploy to Modal (builds and deploys automatically)
modal deploy main.py

# You should see output like:
# 🔨 Building image...
# 📦 Pushing image...
# 🚀 Deploying application...
# ✅ App deployed!
# URL: https://sabalioglu--video-reframer-app.modal.run
```

### 4.2 Wait for Deployment

First deployment takes 2-5 minutes (building image, pulling dependencies).

```bash
# Watch deployment progress
modal logs main.py

# Press Ctrl+C when you see "✅ App deployed"
```

---

## Step 5: Verify Deployment

### 5.1 Health Check

```bash
# Test health endpoint
curl https://sabalioglu--video-reframer-app.modal.run/health

# Expected response:
# {
#   "status": "healthy",
#   "database": "connected",
#   "models": ["yolov8", "sam2", "bytetrack", "gemini"],
#   "timestamp": "2026-01-28T..."
# }
```

### 5.2 Register Test User

```bash
# Create test user
curl -X POST https://sabalioglu--video-reframer-app.modal.run/register \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com"}'

# Response:
# {
#   "status": "success",
#   "user_id": "uuid...",
#   "email": "test@example.com",
#   "api_key": "vr_..."
# }

# Save the API key for testing
API_KEY="vr_..."
```

### 5.3 Test Video Upload

```bash
# Download a test video or use your own
# For quick test, create a 5-second video:
ffmpeg -f lavfi -i testsrc=s=640x480:d=5 -f lavfi -i sine=f=440:d=5 \
  test_video.mp4

# Upload for processing
curl -X POST https://sabalioglu--video-reframer-app.modal.run/process \
  -H "X-API-Key: $API_KEY" \
  -F "file=@test_video.mp4"

# Response:
# {
#   "job_id": "uuid...",
#   "status": "queued",
#   "message": "Video processing started..."
# }

# Save job_id for polling
JOB_ID="uuid..."
```

### 5.4 Monitor Processing

```bash
# Check job status (poll every 10 seconds)
for i in {1..30}; do
  curl https://sabalioglu--video-reframer-app.modal.run/job/$JOB_ID \
    -H "X-API-Key: $API_KEY"
  sleep 10
  echo "Polling... ($i/30)"
done
```

### 5.5 Get Results

```bash
# When status is "completed", get results
curl https://sabalioglu--video-reframer-app.modal.run/results/$JOB_ID \
  -H "X-API-Key: $API_KEY" | jq .

# View statistics
# Should see: detections, segmentation, tracking, scene_analysis
```

---

## Step 6: Monitor & Maintain

### 6.1 View Logs

```bash
# Real-time logs
modal logs main.py

# Follow logs
modal logs main.py -f

# View specific time range
modal logs main.py --since 1h
```

### 6.2 Check Resource Usage

```bash
# Monitor function executions
modal acl list

# View metrics in Modal dashboard:
# https://modal.com/home
```

### 6.3 Update Deployment

If you make code changes:

```bash
# Redeploy (incremental update)
modal deploy backend/main.py

# This is much faster than first deployment (~10-30s)
```

---

## Step 7: Production Checklist

Before going live, verify:

- [ ] Health endpoint responds correctly
- [ ] User registration works
- [ ] Video upload succeeds
- [ ] Processing completes successfully
- [ ] Results are returned correctly
- [ ] Database saves data
- [ ] Logs show no errors
- [ ] CORS origins configured correctly
- [ ] Secrets are set
- [ ] Rate limiting considered
- [ ] Error handling tested
- [ ] Frontend can call API

---

## Troubleshooting

### Issue: Deployment Fails

**Error: `modal: command not found`**
```bash
pip install modal --upgrade
modal setup
```

**Error: `Secret not found: gemini-api`**
```bash
modal secret create gemini-api --name "GEMINI_API_KEY" \
  --value "YOUR_KEY_HERE"
```

**Error: `Build failed`**
- Check requirements.txt syntax
- Verify all packages are available on PyPI
- Check Python 3.11 compatibility

### Issue: Health Check Fails

**Error: `database: error`**
```bash
# Verify Neon connection string
echo $DATABASE_URL

# Should be: postgresql://user:pass@host/db?sslmode=require

# Re-set secret if needed
modal secret delete neon-db
modal secret create neon-db --value "..."
```

**Error: `YOLO model download fails`**
- First run tries to download YOLOv8 model (~170MB)
- May timeout on slow connections
- Retry deployment or pre-cache model in image

### Issue: Processing Times Out

**5-10 minute videos may timeout**

Solution: Increase timeout in `backend/config/modal_config.py`:
```python
TIMEOUT_SECONDS = 1200  # 20 minutes instead of 600
```

Then redeploy:
```bash
modal deploy backend/main.py
```

### Issue: High Memory Usage

**Models loaded consume 4-6GB**

Solution: Optimize in `backend/config/modal_config.py`:
```python
SAMPLE_EVERY_N_FRAMES = 5  # Skip frames (2x faster, less memory)
SAM2_BATCH_SIZE = 2       # Reduce batch size
```

---

## Performance Optimization

### For Faster Processing:

1. **Skip Segmentation** (if not needed)
   ```python
   # In main.py, comment out SAM2 step
   # segmentation = {}
   ```

2. **Reduce Frame Rate**
   ```python
   SAMPLE_EVERY_N_FRAMES = 5  # Process every 5th frame
   ```

3. **Use GPU** (costs extra)
   ```python
   REQUEST_GPU = True  # Enable in modal_config.py
   ```

### For Lower Costs:

1. **Shorter Processing Windows**
   - Process only first 60 seconds of videos
   - Skip Gemini analysis (costs more)

2. **Batch Processing**
   - Queue multiple videos
   - Process overnight for cost optimization

3. **Cache Models**
   ```python
   CACHE_MODELS = True  # Already enabled
   ```

---

## Monitoring & Alerts

### Set Up Alerts (Optional)

```bash
# Get webhook URL from your monitoring service
# Update Modal with webhook for errors

modal deploy --with-monitoring backend/main.py
```

### Key Metrics to Monitor

- Average processing time per video
- Error rate
- Database connection health
- API response latency
- Queue depth

---

## Rollback

If something breaks:

```bash
# Revert to previous version
modal history

# Deploy specific version
modal deploy backend/main.py --tag version-name
```

---

## Support

**Modal Documentation:** https://modal.com/docs
**Neon Documentation:** https://neon.tech/docs
**FastAPI Documentation:** https://fastapi.tiangolo.com/

**Issues?** Check logs:
```bash
modal logs main.py
```

---

## Next Steps

After successful deployment:

1. Update frontend API endpoint (if needed)
2. Configure custom domain (optional)
3. Set up rate limiting
4. Enable request logging
5. Create monitoring dashboard
6. Document API for users

---

**Deployment Complete!** 🎉

Your Video Reframer is now live and processing videos!

