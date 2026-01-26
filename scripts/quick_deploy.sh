#!/bin/bash
set -e

echo "🚀 RAG App - Quick Deployment"

# Install Docker if not present
if ! command -v docker &> /dev/null; then
    echo "📦 Installing Docker..."
    curl -fsSL https://get.docker.com | sh
    sudo usermod -aG docker $USER
fi

# Create app directory
mkdir -p ~/rag-app
cd ~/rag-app

# Download compose file (Assuming repo is public or accessible, otherwise this might need modification)
echo "📥 Downloading configuration..."
# NOTE: Replace with actual URL if different
curl -O https://raw.githubusercontent.com/Neel28iitm/RAG-/main/docker-compose.yml

# Check .env
if [ ! -f .env ]; then
    echo "⚠️  Please create .env file with your API keys"
    echo "Example:"
    cat << EOF
GOOGLE_API_KEY=your_key
LLAMA_CLOUD_API_KEY=your_key
COHERE_API_KEY=your_key
QDRANT_URL=your_url
QDRANT_API_KEY=your_key
AWS_ACCESS_KEY_ID=your_key
AWS_SECRET_ACCESS_KEY=your_key
AWS_REGION=ap-south-1
S3_BUCKET_NAME=your_bucket
EOF
    exit 1
fi

# Pull and start
echo "🐳 Pulling Docker images..."
docker-compose pull

echo "🚀 Starting services..."
docker-compose up -d

echo "✅ Deployment complete!"
# Trying to get public IP, might vary by provider
echo "🌐 Access: http://$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4):8501"
