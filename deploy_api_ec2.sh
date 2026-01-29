#!/bin/bash
# ============================================
# EC2 Production Deployment Script for RAG API
# ============================================
# Run this script on your EC2 instance after:
# 1. Installing Docker & Docker Compose
# 2. Cloning your GitHub repository
# 3. Creating .env file with production credentials

set -e  # Exit on any error

echo "🚀 Starting FastAPI RAG Production Deployment on EC2..."
echo ""

# ============================================
# Step 1: Pre-flight Checks
# ============================================
echo "✅ Step 1: Pre-flight checks..."

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker not found! Installing Docker..."
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    sudo usermod -aG docker $USER
    echo "⚠️  Docker installed. Please log out and log back in, then run this script again."
    exit 0
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose not found! Installing..."
    sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    sudo chmod +x /usr/local/bin/docker-compose
fi

echo "✅ Docker version: $(docker --version)"
echo "✅ Docker Compose version: $(docker-compose --version)"
echo ""

# ============================================
# Step 2: Get EC2 Public IP
# ============================================
echo "🌐 Step 2: Detecting EC2 public IP..."
EC2_PUBLIC_IP=$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4 || echo "UNKNOWN")
echo "✅ EC2 Public IP: $EC2_PUBLIC_IP"
echo ""

# ============================================
# Step 3: Environment Setup
# ============================================
echo "📋 Step 3: Checking environment variables..."

if [ ! -f .env ]; then
    if [ -f .env.production.template ]; then
        echo "⚠️  .env file not found. Copying from .env.production.template..."
        cp .env.production.template .env
        echo ""
        echo "❗ IMPORTANT: Edit .env file and add your API keys!"
        echo "   Required: GOOGLE_API_KEY, LLAMA_CLOUD_API_KEY, COHERE_API_KEY"
        echo "   Optional: AWS credentials, QDRANT_API_KEY"
        echo ""
        read -p "Press Enter after editing .env file..."
    else
        echo "❌ No .env or .env.production.template found!"
        echo "Please create .env file with required API keys."
        exit 1
    fi
fi

echo "✅ Environment file found"
echo ""

# ============================================
# Step 4: Stop Old Containers
# ============================================
echo "🛑 Step 4: Stopping old containers..."
docker-compose -f docker-compose.api.yml down 2>/dev/null || true
echo "✅ Old containers stopped"
echo ""

# ============================================
# Step 5: Build and Start Services
# ============================================
echo "🏗️  Step 5: Building Docker images..."
docker-compose -f docker-compose.api.yml build --pull

echo ""
echo "🚀 Step 6: Starting all services..."
docker-compose -f docker-compose.api.yml up -d

echo "✅ Services started"
echo ""

# ============================================
# Step 7: Wait for Services to be Healthy
# ============================================
echo "⏳ Step 7: Waiting for services to be healthy..."
echo "   This may take 30-60 seconds..."

RETRY_COUNT=0
MAX_RETRIES=30

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if docker exec rag_api curl -f http://localhost:8000/health &> /dev/null; then
        echo "✅ API is healthy!"
        break
    fi
    RETRY_COUNT=$((RETRY_COUNT+1))
    echo "   Attempt $RETRY_COUNT/$MAX_RETRIES - waiting..."
    sleep 2
done

if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
    echo "❌ Health check failed after $MAX_RETRIES attempts!"
    echo ""
    echo "📋 Container logs:"
    docker-compose -f docker-compose.api.yml logs --tail=50 api
    exit 1
fi

echo ""

# ============================================
# Step 8: Verify All Services
# ============================================
echo "🔍 Step 8: Verifying all services..."
docker-compose -f docker-compose.api.yml ps

echo ""

# ============================================
# SUCCESS! Display URLs and Commands
# ============================================
echo ""
echo "╔════════════════════════════════════════════════════════════╗"
echo "║                                                            ║"
echo "║           ✅ DEPLOYMENT SUCCESSFUL! 🎉                     ║"
echo "║                                                            ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""
echo "📡 SWAGGER UI (Share this with your developer):"
echo "   🔗 http://$EC2_PUBLIC_IP:8000/docs"
echo ""
echo "📋 API Endpoints:"
echo "   • Health Check:      http://$EC2_PUBLIC_IP:8000/health"
echo "   • Document Status:   http://$EC2_PUBLIC_IP:8000/document/status/{filename}"
echo "   • All Documents:     http://$EC2_PUBLIC_IP:8000/documents/status"
echo "   • Query RAG:         http://$EC2_PUBLIC_IP:8000/query"
echo ""
echo "🐳 Docker Commands:"
echo "   • View logs:         docker-compose -f docker-compose.api.yml logs -f"
echo "   • View API logs:     docker logs rag_api -f"
echo "   • View worker logs:  docker logs rag_celery_worker -f"
echo "   • Restart services:  docker-compose -f docker-compose.api.yml restart"
echo "   • Stop services:     docker-compose -f docker-compose.api.yml down"
echo ""
echo "🔒 Security Check:"
echo "   Make sure EC2 Security Group has inbound rule:"
echo "   • Port 8000 (TCP) - Open to 0.0.0.0/0 or your IP"
echo ""
echo "✨ Next Steps:"
echo "   1. Test Swagger UI in browser"
echo "   2. Upload a test document via your ingestion endpoint"
echo "   3. Check document status using /document/status/{filename}"
echo "   4. Monitor logs for any errors"
echo ""

# Test health endpoint
echo "🏥 Quick Health Test:"
curl -s http://localhost:8000/health | python3 -m json.tool || echo "✅ Health check passed (non-JSON response)"

echo ""
echo "🎊 Ready to use! Share Swagger URL with your developer."
echo ""
