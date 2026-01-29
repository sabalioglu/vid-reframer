# Video Reframer - Project Summary

**Project Location:** ~/Desktop/video-reframer  
**Created:** 2026-01-28  
**Status:** Phase 2 Ready (Skeleton + Infrastructure)  
**Parent Project:** KEMIK (Phase 1 complete)

---

## 📁 Project Structure

```
video-reframer/
├── README.md ........................ Project overview & quick start
├── PROJECT_SUMMARY.md ............... This file
├── .env.example ..................... Environment variables template
│
├── backend/ ......................... Modal Python backend
│   ├── main.py ...................... FastAPI app (skeleton)
│   ├── requirements.txt ............. Python dependencies
│   ├── config/ ...................... Configuration modules
│   ├── models/ ...................... Pre-trained model weights
│   └── utils/ ....................... Utility functions (TODO)
│       ├── ffmpeg_utils.py .......... FFmpeg frame extraction
│       ├── gemini_utils.py .......... Gemini scene analysis (from KEMIK)
│       ├── yolo_utils.py ............ YOLOv8 detection (TODO)
│       ├── sam2_utils.py ............ SAM2 segmentation (TODO)
│       ├── tracking_utils.py ........ ByteTrack tracking (TODO)
│       └── db_utils.py .............. Database operations
│
├── frontend/ ........................ Netlify static site
│   ├── index.html ................... Main UI (Tailwind CSS)
│   ├── app.js ....................... Application logic
│   └── styles/ ...................... Custom CSS (optional)
│
├── database/ ........................ Neon PostgreSQL
│   ├── schema.sql ................... Complete DB schema (9 tables, 10+ indexes)
│   └── migrations/ .................. SQL migration files
│
├── deployment/ ...................... Deployment configs
│   ├── modal_deploy.sh .............. Automated Modal deployment script
│   └── netlify.toml ................. Netlify configuration
│
└── docs/ ............................ Documentation
    ├── SETUP.md ..................... Detailed setup guide (30 min setup time)
    ├── ARCHITECTURE.md .............. Technical deep dive
    ├── API_REFERENCE.md ............. All endpoints documented
    └── ROADMAP.md ................... Feature timeline (TODO)
```

---

## 🎯 Project Goals

**Phase 2 Objectives:**
1. ✅ Project infrastructure created
2. ✅ Backend skeleton with FastAPI
3. ✅ Database schema designed (9 tables, JSONB storage)
4. ✅ Frontend UI designed (HTML + Tailwind CSS + vanilla JS)
5. ✅ Deployment scripts created
6. ✅ Documentation complete
7. 🔄 Implement YOLOv8 detection
8. 🔄 Implement SAM2 segmentation
9. 🔄 Implement ByteTrack tracking
10. 🔄 Integration testing

**End Goal:** Production-ready AI video pipeline that detects, segments, and tracks objects in video.

---

## 🚀 Tech Stack

| Layer | Technology | Why |
|-------|-----------|-----|
| **Compute** | Modal (serverless) | Native FFmpeg, GPU support, no timeout |
| **API** | FastAPI | Fast, async, modern Python |
| **Detection** | YOLOv8 | Fast, accurate person/product detection |
| **Segmentation** | SAM2 | Pixel-perfect object masks |
| **Tracking** | ByteTrack | Cross-frame object identity |
| **Analysis** | Gemini 2.0 Flash | Scene understanding |
| **Database** | Neon PostgreSQL | Serverless, branching, no vendor lock-in |
| **Frontend** | HTML/CSS/JS | Simple, fast, static deployment |
| **Hosting** | Netlify | Free CDN, drag-drop deploy |

---

## 📊 Database Schema

**9 Tables, 10+ Indexes, JSONB storage:**

1. **users** - API key management
2. **videos** - Video metadata & status
3. **detections** - YOLOv8 bounding boxes
4. **segmentation_masks** - SAM2 pixel masks
5. **tracking_trajectories** - ByteTrack object IDs
6. **scene_analysis** - Gemini scene understanding
7. **processing_jobs** - Async job queue
8. **api_activity_log** - Request logging
9. **extras** - Reserved for future features

---

## 🔑 Key Features

### Processing Pipeline
1. **FFmpeg** - Extract frames from video
2. **YOLOv8** - Detect persons & products (bounding boxes)
3. **SAM2** - Generate pixel-perfect masks
4. **ByteTrack** - Assign consistent IDs across frames
5. **Gemini** - Analyze scenes semantically

### Output Format
```json
{
  "detections": {
    "frame_5": [
      {
        "class": "person",
        "confidence": 0.92,
        "bbox": {"x": 100, "y": 50, "width": 120, "height": 200}
      }
    ]
  },
  "segmentation_masks": {
    "frame_5": [
      {
        "track_id": "obj_001",
        "mask_rle": "3,5,10,3,2,...",
        "mask_area_pixels": 24000
      }
    ]
  },
  "tracking": {
    "obj_001": {
      "class": "person",
      "start_frame": 5,
      "end_frame": 250,
      "duration_frames": 245,
      "avg_confidence": 0.92
    }
  },
  "scenes": [
    {
      "scene_number": 1,
      "description": "Woman enters house",
      "importance": 8
    }
  ]
}
```

---

## 💻 Development Workflow

### 1. Clone Repository
```bash
cd ~/Desktop/video-reframer
```

### 2. Install Backend Dependencies
```bash
cd backend
pip install -r requirements.txt
```

### 3. Set Up Environment
```bash
cp ../.env.example ../.env
# Edit .env with Modal credentials, Gemini API key, etc.
```

### 4. Deploy Backend (Modal)
```bash
bash ../deployment/modal_deploy.sh
# → API URL: https://sabalioglu--video-reframer-app.modal.run
```

### 5. Deploy Frontend (Netlify)
```bash
cd ../frontend
netlify deploy --prod
# → Frontend URL: https://video-reframer-xxxxx.netlify.app
```

### 6. Set Up Database (Neon)
```bash
# 1. Create account at https://neon.tech
# 2. Create database
# 3. Run: psql "postgresql://..." -f database/schema.sql
# 4. Get connection string
# 5. Create Modal secret: modal secret create neon-db DATABASE_URL="..."
```

---

## 🎓 Learning from KEMIK

### What Works ✅
- **Modal** for serverless compute (native FFmpeg!)
- **Gemini File API** for video analysis
- **Neon** for serverless PostgreSQL
- **API Key auth** (simple & secure)
- **FFmpeg with ffprobe** for real metadata

### What Failed ❌
- **n8n** for video processing (no FFmpeg, binary data issues, timeouts)
- **Gemini metadata** as ground truth (hallucinated values)

### Best Practices 📚
- Always wait for Gemini file ACTIVE state (polling!)
- Use ffprobe for real metadata, not Gemini
- Compress masks with RLE (10x savings vs PNG)
- Use JSONB for flexible schema storage
- API key authentication over OAuth (simpler for servers)

---

## 📈 Implementation Checklist

### Phase 2 - Object Detection & Tracking (IN PROGRESS)

#### Backend
- [ ] Implement `ffmpeg_utils.py` - Frame extraction
- [ ] Implement `yolo_utils.py` - YOLOv8 detection
- [ ] Implement `sam2_utils.py` - SAM2 segmentation (GPU)
- [ ] Implement `tracking_utils.py` - ByteTrack tracking
- [ ] Implement `gemini_utils.py` - Scene analysis (from KEMIK)
- [ ] Implement database save functions
- [ ] Error handling & retries
- [ ] Async job queue (if videos > 10 min)

#### Frontend
- [ ] Test registration flow
- [ ] Test video upload
- [ ] Test progress tracking
- [ ] Test results display
- [ ] Mobile responsiveness
- [ ] Error handling UI

#### Deployment
- [ ] Modal secret creation (Gemini, Neon)
- [ ] Neon database schema deploy
- [ ] Modal backend deploy
- [ ] Netlify frontend deploy
- [ ] CORS configuration
- [ ] Health check verification

#### Testing
- [ ] Test with sample videos (various formats)
- [ ] Test detection accuracy
- [ ] Test segmentation quality
- [ ] Test tracking consistency
- [ ] Performance benchmarking
- [ ] Error scenarios

### Phase 3 - Composition & Replacement (FUTURE)

- [ ] Object removal (inpainting)
- [ ] AI image insertion
- [ ] Video composition
- [ ] Transition handling
- [ ] Quality optimization

---

## 🌍 Production Deployment Checklist

Before going live:

- [ ] Set up Neon database (production)
- [ ] Create Modal secrets (all keys)
- [ ] Update CORS in main.py (Netlify domain)
- [ ] Set rate limiting (Upstash Redis)
- [ ] Enable HTTPS (automatic on Modal + Netlify)
- [ ] Add API key rotation mechanism
- [ ] Monitor Modal logs daily
- [ ] Monitor Neon database size
- [ ] Set up error alerting
- [ ] Create backup strategy
- [ ] Document SLAs and limits
- [ ] Set up analytics

---

## 💰 Cost Structure

### Monthly Costs (1000 videos)

| Service | Cost | Notes |
|---------|------|-------|
| Modal compute | $1-5 | $30 free credits/month |
| Modal GPU (SAM2) | $80-100 | Optional, if using A10G |
| Neon database | $0 | Free tier: 0.5GB |
| Gemini API | $0 | Free: 60 req/min |
| Netlify frontend | $0 | Free: 100GB bandwidth |
| **Total** | **$80-105** | **Or $0 with CPU only** |

### Cost Optimization
- Use CPU-only mode for testing (no SAM2)
- Sample frames to reduce processing time
- Archive old results to reduce DB size
- Use RLE compression for masks

---

## 📞 Support & Troubleshooting

### Quick Links
- **Setup Guide:** `docs/SETUP.md`
- **Architecture:** `docs/ARCHITECTURE.md`
- **API Reference:** `docs/API_REFERENCE.md`
- **Parent Project:** `/Users/sabalioglu/Desktop/KEMIK`

### Common Issues

**"FFmpeg not found"**
- Modal should auto-install, but check: `modal run -q 'apt install ffmpeg'`

**"Database connection refused"**
- Verify Neon connection string: `psql "postgresql://..."`
- Check Modal secret: `modal secret list`

**"API timeout"**
- Long videos need async processing (implement job queue)
- Check Modal logs: `modal app logs video-reframer`

**"SAM2 out of memory"**
- Use A10G GPU or reduce frame sampling
- Batch process detections

---

## 🔗 External Resources

- **Modal:** https://modal.com/docs
- **FastAPI:** https://fastapi.tiangolo.com/
- **YOLOv8:** https://docs.ultralytics.com/
- **SAM2:** https://github.com/facebookresearch/sam2
- **ByteTrack:** https://github.com/ifzhang/ByteTrack
- **Neon:** https://neon.tech/docs
- **Gemini:** https://ai.google.dev/
- **Netlify:** https://docs.netlify.com/

---

## 👨‍💻 Development Notes

### Code Style
- Python: PEP 8 (use black formatter)
- JavaScript: Vanilla JS (no frameworks needed)
- SQL: Clear table/column names, proper indexing

### Git Workflow
- Branch: `feature/xxx` for new features
- Commit: Descriptive messages
- PR: Link to GitHub issues

### Documentation
- Update README when adding features
- Document all API changes in API_REFERENCE.md
- Keep ARCHITECTURE.md in sync with actual implementation

---

## 📝 Next Steps

1. **Immediate (this session)**
   - Review project structure
   - Set up local environment
   - Create Modal/Neon accounts
   
2. **Short-term (1-2 days)**
   - Implement YOLOv8 detection module
   - Implement SAM2 segmentation
   - Implement ByteTrack tracking
   
3. **Medium-term (3-5 days)**
   - Integration testing
   - Performance optimization
   - Production deployment
   
4. **Long-term (1-2 weeks)**
   - Phase 3: Video composition
   - Advanced features
   - Scale to production load

---

## 📞 Contact & Questions

- **Project Owner:** Semih (sabalioglu)
- **Parent Project:** KEMIK (Phase 1)
- **Status:** Phase 2 - Skeleton ready for implementation

---

**Last Updated:** 2026-01-28  
**Project Status:** ✅ Infrastructure Complete → 🔄 Implementation Ready  
**Est. Implementation Time:** 3-5 days (YOLOv8 + SAM2 + ByteTrack)
