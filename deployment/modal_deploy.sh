#!/bin/bash
#
# Video Reframer - Modal Deployment Script
# Automated setup and deployment to Modal
#
# Usage:
#   bash modal_deploy.sh [--gpu] [--no-secrets]
#

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Configuration
PROJECT_NAME="video-reframer"
BACKEND_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/backend"
GPU_FLAG=""
SKIP_SECRETS=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --gpu)
            GPU_FLAG="--gpu=A10G"
            echo -e "${YELLOW}GPU mode enabled (A10G - $1.10/hr)${NC}"
            shift
            ;;
        --no-secrets)
            SKIP_SECRETS=true
            echo -e "${YELLOW}Skipping secret verification${NC}"
            shift
            ;;
        *)
            echo "Unknown argument: $1"
            exit 1
            ;;
    esac
done

# =====================================================
# 1. Check Prerequisites
# =====================================================

echo -e "${YELLOW}========================================${NC}"
echo -e "${YELLOW}Checking prerequisites...${NC}"
echo -e "${YELLOW}========================================${NC}"

# Check Modal is installed
if ! command -v modal &> /dev/null; then
    echo -e "${RED}❌ Modal CLI not found${NC}"
    echo "Install with: pip install modal"
    exit 1
fi
echo -e "${GREEN}✅ Modal CLI found${NC}"

# Check Python
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python 3 not found${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Python 3 found${NC}"

# Check authentication
if ! modal token verify 2>/dev/null; then
    echo -e "${RED}❌ Modal authentication failed${NC}"
    echo "Run: modal token set --token-id ak-xxx --token-secret as-xxx"
    exit 1
fi
echo -e "${GREEN}✅ Modal authentication verified${NC}"

# =====================================================
# 2. Verify Backend Directory
# =====================================================

if [ ! -f "$BACKEND_DIR/main.py" ]; then
    echo -e "${RED}❌ Backend not found at $BACKEND_DIR${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Backend found at $BACKEND_DIR${NC}"

# =====================================================
# 3. Check & Create Secrets
# =====================================================

if [ "$SKIP_SECRETS" = false ]; then
    echo -e "${YELLOW}========================================${NC}"
    echo -e "${YELLOW}Setting up Modal secrets...${NC}"
    echo -e "${YELLOW}========================================${NC}"

    # Check Gemini secret
    if ! modal secret list 2>/dev/null | grep -q "gemini-api"; then
        echo -e "${YELLOW}Creating Gemini API secret...${NC}"
        if [ -z "$GEMINI_API_KEY" ]; then
            read -p "Enter GEMINI_API_KEY: " GEMINI_API_KEY
        fi
        modal secret create gemini-api GEMINI_API_KEY="$GEMINI_API_KEY"
        echo -e "${GREEN}✅ Gemini secret created${NC}"
    else
        echo -e "${GREEN}✅ Gemini secret already exists${NC}"
    fi

    # Check Neon secret
    if ! modal secret list 2>/dev/null | grep -q "neon-db"; then
        echo -e "${YELLOW}Neon secret not found${NC}"
        echo "Create with: modal secret create neon-db DATABASE_URL=\"postgresql://...\""
    else
        echo -e "${GREEN}✅ Neon secret exists${NC}"
    fi
fi

# =====================================================
# 4. Install Dependencies
# =====================================================

echo -e "${YELLOW}========================================${NC}"
echo -e "${YELLOW}Installing dependencies...${NC}"
echo -e "${YELLOW}========================================${NC}"

cd "$BACKEND_DIR"
if [ -f "requirements.txt" ]; then
    echo "Installing from requirements.txt..."
    pip install -r requirements.txt -q
    echo -e "${GREEN}✅ Dependencies installed${NC}"
fi

# =====================================================
# 5. Build Modal Image
# =====================================================

echo -e "${YELLOW}========================================${NC}"
echo -e "${YELLOW}Building Modal image...${NC}"
echo -e "${YELLOW}========================================${NC}"

echo "This may take 2-3 minutes..."
modal image build main.py

echo -e "${GREEN}✅ Image built successfully${NC}"

# =====================================================
# 6. Deploy to Modal
# =====================================================

echo -e "${YELLOW}========================================${NC}"
echo -e "${YELLOW}Deploying to Modal...${NC}"
echo -e "${YELLOW}========================================${NC}"

if [ -z "$GPU_FLAG" ]; then
    echo "Deploying without GPU..."
    modal deploy main.py
else
    echo "Deploying with GPU (A10G)..."
    modal deploy main.py --force $GPU_FLAG
fi

# =====================================================
# 7. Verify Deployment
# =====================================================

echo -e "${YELLOW}========================================${NC}"
echo -e "${YELLOW}Verifying deployment...${NC}"
echo -e "${YELLOW}========================================${NC}"

# Get deployment URL
DEPLOYMENT_URL=$(modal app list 2>/dev/null | grep "video-reframer" | awk '{print $NF}')

if [ -n "$DEPLOYMENT_URL" ]; then
    echo -e "${GREEN}✅ Deployment successful!${NC}"
    echo ""
    echo -e "${GREEN}API URL: $DEPLOYMENT_URL${NC}"
    echo ""

    # Test health check
    echo "Testing health endpoint..."
    HEALTH_RESPONSE=$(curl -s "$DEPLOYMENT_URL/health" || echo "failed")

    if echo "$HEALTH_RESPONSE" | grep -q "healthy"; then
        echo -e "${GREEN}✅ Health check passed${NC}"
    else
        echo -e "${YELLOW}⚠️  Health check inconclusive${NC}"
        echo "Response: $HEALTH_RESPONSE"
    fi

    # Show next steps
    echo ""
    echo -e "${YELLOW}========================================${NC}"
    echo -e "${YELLOW}Next Steps:${NC}"
    echo -e "${YELLOW}========================================${NC}"
    echo "1. Update frontend API URL:"
    echo "   Edit: frontend/app.js"
    echo "   Set: const API_URL = \"$DEPLOYMENT_URL\""
    echo ""
    echo "2. Deploy frontend:"
    echo "   cd frontend"
    echo "   netlify deploy --prod"
    echo ""
    echo "3. Update CORS in main.py:"
    echo "   Change allow_origins to your Netlify domain"
    echo "   Redeploy: modal deploy main.py"
    echo ""
    echo "4. Test with curl:"
    echo "   curl $DEPLOYMENT_URL/health"
    echo ""

else
    echo -e "${RED}❌ Deployment URL not found${NC}"
    echo "Check Modal dashboard: https://modal.com/apps/$USER"
    exit 1
fi

# =====================================================
# 7. Show Deployment Info
# =====================================================

echo -e "${YELLOW}========================================${NC}"
echo -e "${YELLOW}Deployment Information:${NC}"
echo -e "${YELLOW}========================================${NC}"
echo "Project: $PROJECT_NAME"
echo "Backend: $BACKEND_DIR"
echo "Status: ✅ Deployed"
echo "Monitor: modal app logs video-reframer"
echo ""

# Save info to file
cat > /tmp/video-reframer-deployment.txt << EOF
Video Reframer Deployment Info
Generated: $(date)

API URL: $DEPLOYMENT_URL
Health: $DEPLOYMENT_URL/health
Logs: modal app logs video-reframer

Modal Commands:
- View logs: modal app logs video-reframer -n 100
- Stream logs: modal app logs video-reframer --follow
- List apps: modal app list
- View usage: modal acct info

Next Steps:
1. Update frontend API_URL
2. Deploy frontend to Netlify
3. Update CORS in main.py
4. Test with curl

See README.md for full setup guide.
EOF

echo -e "${GREEN}ℹ️  Deployment info saved to /tmp/video-reframer-deployment.txt${NC}"
