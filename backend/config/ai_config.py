"""
AI Model Configuration
Video Reframer Phase 2
"""

# =====================================================
# YOLOv8 Configuration
# =====================================================
YOLO_MODEL = "yolov8m.pt"  # Medium size (balanced speed/accuracy)
YOLO_CONFIDENCE = 0.5       # Confidence threshold (0.0-1.0)
YOLO_IOU = 0.45             # NMS IoU threshold
YOLO_DEVICE = "cuda"        # "cuda" or "cpu"
YOLO_IMG_SIZE = 640         # Input image size
YOLO_BATCH_SIZE = 16        # Batch size for inference
YOLO_MAX_DET = 300          # Maximum detections per image

# Frame sampling for efficiency
SAMPLE_EVERY_N_FRAMES = 1   # Process every frame (set to 5 for faster processing)
MIN_FRAME_SIZE = 64         # Skip very small objects (pixels)

# Classes to detect
YOLO_CLASSES_TO_DETECT = [0, 26]  # 0=person, 26=backpack (customize as needed)

# =====================================================
# SAM2 Configuration
# =====================================================
SAM2_MODEL = "sam2_hiera_base_plus.pt"
SAM2_GPU_REQUIRED = True
SAM2_BATCH_SIZE = 4
SAM2_DEVICE = "cuda"
SAM2_IMAGE_SIZE = 1024

# Segmentation parameters
SAM2_STABILITY_SCORE_THRESH = 0.95
SAM2_MIN_MASK_REGION_AREA = 100  # Minimum pixels for valid mask

# =====================================================
# ByteTrack Configuration
# =====================================================
BYTETRACK_TRACK_THRESH = 0.5        # Confidence threshold for tracking
BYTETRACK_TRACK_BUFFER = 30         # Frames to keep dead tracks alive
BYTETRACK_MATCH_THRESH = 0.8        # Matching threshold
BYTETRACK_FRAME_RATE = 30           # Video frame rate (fps)
BYTETRACK_ASPECT_RATIO_THRESH = 1.6 # Aspect ratio threshold
BYTETRACK_MIN_BOX_AREA = 10         # Minimum box area

# =====================================================
# Frame Extraction
# =====================================================
FRAME_EXTRACTION_FPS = 30           # Target FPS for extraction
FRAME_EXTRACTION_FORMAT = "RGB"     # "RGB" or "BGR"
TEMP_FRAME_DIR = "/tmp/video_frames"  # Temporary frame storage
MAX_FRAMES_IN_MEMORY = 500          # Max frames to keep in RAM simultaneously

# =====================================================
# Video Processing
# =====================================================
MAX_VIDEO_SIZE_MB = 500              # Maximum video file size
ALLOWED_FORMATS = [".mp4", ".avi", ".mov", ".mkv", ".webm"]
PROCESS_TIMEOUT_SECONDS = 600        # 10 minutes
MAX_VIDEO_DURATION = 3600            # 1 hour max

# =====================================================
# Gemini Configuration
# =====================================================
GEMINI_MODEL = "gemini-2.0-flash"
GEMINI_TEMPERATURE = 0.7
GEMINI_MAX_TOKENS = 1000
GEMINI_TOP_P = 0.95

# =====================================================
# Database Configuration
# =====================================================
DB_BATCH_INSERT_SIZE = 100  # Batch insert records
DB_CONNECTION_TIMEOUT = 10  # seconds
DB_POOL_MIN_SIZE = 1
DB_POOL_MAX_SIZE = 10

# =====================================================
# Output Configuration
# =====================================================
RLE_COMPRESSION = True      # Use RLE for mask compression
SAVE_INTERMEDIATE_FRAMES = False  # Save detection visualization
MAX_RESULTS_PER_FRAME = 50  # Limit results returned

# =====================================================
# Performance Tuning
# =====================================================
USE_GPU = True              # Use GPU acceleration
ASYNC_PROCESSING = True     # Use async database operations
PARALLEL_FRAME_LOADING = 4  # Number of parallel frame loaders
CACHE_MODELS = True         # Cache loaded models in memory

# =====================================================
# Logging Configuration
# =====================================================
LOG_LEVEL = "INFO"
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
SAVE_LOGS = True
LOGS_DIR = "/tmp/video_reframer_logs"
