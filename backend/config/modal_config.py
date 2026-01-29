"""
Modal Configuration
Video Reframer Backend
"""

# =====================================================
# Modal App Configuration
# =====================================================
APP_NAME = "video-reframer"
APP_VERSION = "2.0.0"

# =====================================================
# Image Configuration
# =====================================================
# Base image for Modal deployment
BASE_IMAGE = "debian_slim"
PYTHON_VERSION = "3.11"

# System packages to install
SYSTEM_PACKAGES = [
    "ffmpeg",
    "libsm6",
    "libxext6",
    "libxrender-dev",
    "libgomp1",  # For OpenMP (PyTorch)
    "libopenblas-dev",
    "liblapack-dev",
]

# =====================================================
# Resource Configuration
# =====================================================
MEMORY_MB = 8096          # 8GB RAM
TIMEOUT_SECONDS = 600     # 10 minutes
SCALEDOWN_WINDOW = 60     # Scale down after 60s idle

# GPU Configuration (optional, for SAM2)
GPU_TYPE = "A10G"         # Modal GPU type
GPU_MEMORY = 40           # GB VRAM
REQUEST_GPU = False       # Set True when using SAM2

# =====================================================
# Secrets Configuration
# =====================================================
SECRETS = [
    "gemini-api",          # GEMINI_API_KEY
    "neon-db",             # DATABASE_URL
]

# =====================================================
# FastAPI Configuration
# =====================================================
API_TITLE = "Video Reframer API"
API_DESCRIPTION = "AI-powered video frame analysis and replacement"
API_VERSION = "2.0.0"

# CORS Configuration (UPDATE FOR PRODUCTION)
ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:8000",
    "https://delightful-cascaron-e1dc20.netlify.app",
    # Add your production domain here
]

# =====================================================
# Deployment Configuration
# =====================================================
ENVIRONMENT = "production"  # "development" or "production"
DEBUG = False
RELOAD = False  # Auto-reload on code change (dev only)

# =====================================================
# Modal Web Endpoint Configuration
# =====================================================
WEB_ENDPOINT_ENABLED = True
WEB_ENDPOINT_METHOD = "asgi_app"

# =====================================================
# Caching Configuration
# =====================================================
ENABLE_MODEL_CACHING = True
CACHE_TTL_SECONDS = 3600   # Cache models for 1 hour
ENABLE_RESULT_CACHING = True
RESULT_CACHE_TTL = 1800    # Cache results for 30 minutes

# =====================================================
# Logging Configuration
# =====================================================
LOG_LEVEL = "INFO"
ENABLE_REQUEST_LOGGING = True
ENABLE_ERROR_LOGGING = True

# =====================================================
# Rate Limiting (optional)
# =====================================================
ENABLE_RATE_LIMITING = False
RATE_LIMIT_REQUESTS_PER_MINUTE = 60
RATE_LIMIT_BY_API_KEY = False

# =====================================================
# Health Check Configuration
# =====================================================
HEALTH_CHECK_ENABLED = True
HEALTH_CHECK_MODELS = ["yolov8", "sam2", "bytetrack"]
HEALTH_CHECK_DATABASE = True
