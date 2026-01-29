#!/bin/bash
# Production Deployment Script for RAG API with Document Status
# Run this on EC2 server after cloning from GitHub

set -e  # Exit on error

echo "🚀 Starting RAG API Production Deployment..."

# Step 1: Stop old processes
echo "📛 Stopping old processes..."
pkill -f "uvicorn" || true
pkill -f "celery" || true
sudo systemctl stop rag-api.service 2>/dev/null || true
sudo systemctl stop rag-celery.service 2>/dev/null || true

# Step 2: Setup Python environment
echo "🐍 Setting up Python environment..."
cd ~/RAG-
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Step 3: Setup PostgreSQL
echo "🗄️ Setting up PostgreSQL..."
if ! sudo systemctl is-active --quiet postgresql; then
    sudo apt update
    sudo apt install -y postgresql postgresql-contrib
    sudo systemctl start postgresql
    sudo systemctl enable postgresql
fi

# Create database and user
sudo -u postgres psql << EOF
SELECT 'CREATE DATABASE rag_db' WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'rag_db')\gexec
SELECT 'CREATE USER rag_user WITH PASSWORD '\''rag_password'\''' WHERE NOT EXISTS (SELECT FROM pg_user WHERE usename = 'rag_user')\gexec
GRANT ALL PRIVILEGES ON DATABASE rag_db TO rag_user;
EOF

echo "✅ PostgreSQL setup complete"

# Step 4: Setup Redis
echo "📦 Setting up Redis..."
if ! sudo systemctl is-active --quiet redis-server; then
    sudo apt install -y redis-server
    sudo systemctl start redis-server
    sudo systemctl enable redis-server
fi
echo "✅ Redis setup complete"

# Step 5: Initialize Database Schema
echo "🏗️ Initializing database schema..."
python3 << EOF
import sys
sys.path.append('.')
from src.core.database import init_db
init_db()
print("✅ Database initialized")
EOF

# Step 6: Create systemd service for API
echo "⚙️ Creating systemd service..."
sudo tee /etc/systemd/system/rag-api.service > /dev/null << EOF
[Unit]
Description=RAG API Service with Document Status Tracking
After=network.target postgresql.service redis-server.service

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/RAG-
EnvironmentFile=/home/ubuntu/RAG-/.env
ExecStart=/home/ubuntu/RAG-/.venv/bin/uvicorn api.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=10
StandardOutput=append:/var/log/rag-api.log
StandardError=append:/var/log/rag-api-error.log

[Install]
WantedBy=multi-user.target
EOF

# Step 7: Create systemd service for Celery Worker
echo "⚙️ Creating Celery worker service..."
sudo tee /etc/systemd/system/rag-celery.service > /dev/null << EOF
[Unit]
Description=RAG Celery Worker for Document Ingestion
After=network.target redis-server.service

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/RAG-
EnvironmentFile=/home/ubuntu/RAG-/.env
ExecStart=/home/ubuntu/RAG-/.venv/bin/celery -A src.worker.celery_app worker --loglevel=info --concurrency=2
Restart=always
RestartSec=10
StandardOutput=append:/var/log/rag-celery.log
StandardError=append:/var/log/rag-celery-error.log

[Install]
WantedBy=multi-user.target
EOF

# Step 8: Reload systemd and start services
echo "🔄 Starting services..."
sudo systemctl daemon-reload
sudo systemctl enable rag-api.service
sudo systemctl enable rag-celery.service
sudo systemctl start rag-api.service
sudo systemctl start rag-celery.service

# Step 9: Wait for API to start
echo "⏳ Waiting for API to start..."
sleep 5

# Step 10: Verify health
echo "🏥 Checking health..."
curl -f http://localhost:8000/health || {
    echo "❌ Health check failed! Check logs:"
    sudo journalctl -u rag-api -n 50 --no-pager
    exit 1
}

echo ""
echo "✅ =========================================="
echo "✅ DEPLOYMENT SUCCESSFUL!"
echo "✅ =========================================="
echo ""
echo "📡 API Endpoints:"
echo "   - Swagger UI: http://98.81.35.99:8000/docs"
echo "   - Health: http://98.81.35.99:8000/health"
echo "   - Document Status: http://98.81.35.99:8000/document/status/{filename}"
echo "   - All Documents: http://98.81.35.99:8000/documents/status"
echo ""
echo "📊 Service Status:"
sudo systemctl status rag-api.service --no-pager -l
echo ""
echo "📝 View Logs:"
echo "   - API: sudo journalctl -u rag-api -f"
echo "   - Celery: sudo journalctl -u rag-celery -f"
echo ""
