# 🚀 RAG API - EC2 Production Deployment Guide

Complete step-by-step guide to deploy your RAG FastAPI application on AWS EC2 with Docker.

## 📋 Table of Contents
- [Prerequisites](#prerequisites)
- [EC2 Setup](#ec2-setup)
- [Deployment Steps](#deployment-steps)
- [Accessing Swagger UI](#accessing-swagger-ui)
- [Troubleshooting](#troubleshooting)
- [Monitoring](#monitoring)

---

## Prerequisites

### AWS EC2 Instance Requirements
- **Instance Type**: `t2.medium` or larger (minimum 2 vCPU, 4 GB RAM)
- **OS**: Ubuntu 22.04 LTS
- **Storage**: 20 GB minimum
- **Security Group**: See configuration below

### Security Group Configuration
**Critical**: Configure inbound rules in your EC2 security group:

| Type | Protocol | Port | Source | Description |
|------|----------|------|--------|-------------|
| SSH | TCP | 22 | Your IP | SSH access |
| Custom TCP | TCP | 8000 | 0.0.0.0/0 | **FastAPI Swagger UI** |
| HTTP | TCP | 80 | 0.0.0.0/0 | Optional (nginx reverse proxy) |

> [!IMPORTANT]
> **Port 8000 MUST be open** for your developer to access Swagger UI at `http://YOUR_EC2_IP:8000/docs`

### Required API Keys
Before deployment, ensure you have:
- ✅ `GOOGLE_API_KEY` (Gemini 2.5 Flash for generation)
- ✅ `LLAMA_CLOUD_API_KEY` (LlamaParse for document parsing)
- ✅ `COHERE_API_KEY` (Multilingual reranker)
- ✅ `QDRANT_URL` and `QDRANT_API_KEY` (if using Qdrant Cloud)
- ✅ AWS credentials (if using S3 for document storage)

---

## EC2 Setup

### Step 1: Connect to EC2
```bash
ssh -i your-key.pem ubuntu@YOUR_EC2_PUBLIC_IP
```

### Step 2: Clone Your Repository
```bash
cd ~
git clone https://github.com/YOUR_USERNAME/RAG-.git
cd RAG-
```

### Step 3: Create Environment File
```bash
# Copy template
cp .env.production.template .env

# Edit with your credentials
nano .env
```

**Edit `.env` file with your production values:**
```bash
# Core API Keys (REQUIRED)
GOOGLE_API_KEY=your_google_gemini_api_key_here
LLAMA_CLOUD_API_KEY=your_llamaparse_api_key_here
COHERE_API_KEY=your_cohere_api_key_here

# Qdrant Configuration
# Option A: Qdrant Cloud
QDRANT_URL=https://your-cluster.qdrant.io
QDRANT_API_KEY=your_qdrant_api_key

# Option B: Local Qdrant (uncomment qdrant service in docker-compose.api.yml)
# QDRANT_URL=http://qdrant:6333
# QDRANT_API_KEY=

# AWS (if using S3)
AWS_ACCESS_KEY_ID=your_aws_key
AWS_SECRET_ACCESS_KEY=your_aws_secret
AWS_REGION=ap-south-1
S3_BUCKET_NAME=your_bucket_name

# Database (auto-configured by Docker)
DATABASE_URL=postgresql://rag_user:rag_password@postgres:5432/rag_db
REDIS_URL=redis://redis:6379/0
```

Save and exit (`Ctrl+X`, then `Y`, then `Enter`).

---

## Deployment Steps

### One-Command Deployment
The deployment script handles everything automatically:

```bash
# Make script executable
chmod +x deploy_api_ec2.sh

# Run deployment
bash deploy_api_ec2.sh
```

**What the script does:**
1. ✅ Checks and installs Docker + Docker Compose
2. ✅ Detects EC2 public IP
3. ✅ Validates environment file
4. ✅ Stops old containers
5. ✅ Builds Docker images
6. ✅ Starts all services (API + PostgreSQL + Redis + Celery)
7. ✅ Waits for health checks to pass
8. ✅ **Displays Swagger UI URL**

### Expected Output
If successful, you'll see:
```
╔════════════════════════════════════════════════════════════╗
║                                                            ║
║           ✅ DEPLOYMENT SUCCESSFUL! 🎉                     ║
║                                                            ║
╚════════════════════════════════════════════════════════════╝

📡 SWAGGER UI (Share this with your developer):
   🔗 http://98.81.35.99:8000/docs

📋 API Endpoints:
   • Health Check:      http://98.81.35.99:8000/health
   • Document Status:   http://98.81.35.99:8000/document/status/{filename}
   • All Documents:     http://98.81.35.99:8000/documents/status
   • Query RAG:         http://98.81.35.99:8000/query
```

---

## Accessing Swagger UI

### For Your Developer
Share this URL with your developer:
```
http://YOUR_EC2_PUBLIC_IP:8000/docs
```

### What They'll See
- **Interactive API documentation** (Swagger UI)
- **"Try it out" buttons** to test endpoints directly
- **Request/Response schemas** with examples
- **Authentication** (if needed)

### Test the API
From Swagger UI, your developer can:
1. **Test `/health`** - Verify API is running
2. **Test `/query`** - Ask questions to the RAG system
3. **Test `/document/status/{filename}`** - Check ingestion status
4. **Test `/documents/status`** - List all documents

---

## Troubleshooting

### Problem 1: Port 8000 Not Accessible

**Symptom**: Cannot open `http://YOUR_EC2_IP:8000/docs`

**Solution**:
1. Check EC2 Security Group inbound rules
2. Verify port 8000 is open to `0.0.0.0/0` (or your IP)
3. Test from EC2 itself:
   ```bash
   curl http://localhost:8000/health
   ```

### Problem 2: Health Check Failing

**Symptom**: Deployment script fails at "Waiting for services to be healthy"

**Solution**:
```bash
# Check API logs
docker logs rag_api

# Common issues:
# - Missing API keys in .env
# - Qdrant connection failed
# - Database connection failed

# Restart services
docker-compose -f docker-compose.api.yml restart
```

### Problem 3: API Returns 503 Service Unavailable

**Symptom**: Swagger loads but endpoints return errors

**Solution**:
```bash
# Check if Qdrant is accessible
docker exec rag_api curl http://qdrant:6333/health

# Check database connection
docker exec rag_postgres pg_isready -U rag_user

# Check all container status
docker-compose -f docker-compose.api.yml ps

# All should show "Up" status
```

### Problem 4: Celery Worker Not Processing Documents

**Symptom**: Documents stuck in "PENDING" status

**Solution**:
```bash
# Check Celery worker logs
docker logs rag_celery_worker -f

# Restart worker
docker-compose -f docker-compose.api.yml restart celery_worker

# Check Redis connection
docker exec rag_redis redis-cli ping
# Should return "PONG"
```

### Problem 5: Out of Memory on EC2

**Symptom**: Services crash or restart frequently

**Solution**:
1. **Upgrade instance** to `t2.large` or `t2.xlarge`
2. **Or reduce resources** in `docker-compose.api.yml`:
   ```yaml
   celery_worker:
     command: celery -A src.worker.celery_app worker --concurrency=1  # Reduce from 2 to 1
   ```

---

## Monitoring

### View Logs

**All services:**
```bash
docker-compose -f docker-compose.api.yml logs -f
```

**API only:**
```bash
docker logs rag_api -f
```

**Celery worker:**
```bash
docker logs rag_celery_worker -f
```

**Database:**
```bash
docker logs rag_postgres
```

### Check Service Status
```bash
docker-compose -f docker-compose.api.yml ps
```

**Expected output:**
```
NAME                 STATUS              PORTS
rag_api              Up (healthy)        0.0.0.0:8000->8000/tcp
rag_celery_worker    Up                  
rag_postgres         Up (healthy)        5432/tcp
rag_redis            Up (healthy)        6379/tcp
```

### Resource Usage
```bash
# CPU and memory usage
docker stats

# Disk usage
docker system df
```

---

## Useful Commands

### Restart Services
```bash
docker-compose -f docker-compose.api.yml restart
```

### Stop Everything
```bash
docker-compose -f docker-compose.api.yml down
```

### Rebuild After Code Changes
```bash
# Pull latest code from GitHub
git pull origin main

# Rebuild and restart
docker-compose -f docker-compose.api.yml up -d --build
```

### Clean Up (Nuclear Option)
```bash
# Stop and remove everything (INCLUDING DATA!)
docker-compose -f docker-compose.api.yml down -v

# Remove old images
docker system prune -a

# Redeploy fresh
bash deploy_api_ec2.sh
```

---

## Production Best Practices

### 1. Use Nginx Reverse Proxy (Optional)
For production, route traffic through nginx:
```bash
sudo apt install nginx

# Configure nginx to proxy port 80 -> 8000
# Then access: http://YOUR_EC2_IP/docs (no port needed)
```

### 2. Enable HTTPS with Let's Encrypt
```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

### 3. Monitor System Resources
Install monitoring tools:
```bash
# Install htop for resource monitoring
sudo apt install htop

# Run to see CPU/RAM usage
htop
```

### 4. Regular Backups
Backup PostgreSQL data:
```bash
docker exec rag_postgres pg_dump -U rag_user rag_db > backup_$(date +%Y%m%d).sql
```

### 5. Log Rotation
Docker automatically rotates logs (configured in docker-compose.api.yml):
```yaml
logging:
  options:
    max-size: "10m"  # Max 10 MB per log file
    max-file: "3"    # Keep 3 files
```

---

## Next Steps

1. ✅ Share Swagger URL with your developer: `http://YOUR_EC2_IP:8000/docs`
2. ✅ Test document ingestion workflow
3. ✅ Monitor logs for first 24 hours
4. ✅ Set up automated backups
5. ✅ (Optional) Configure custom domain + HTTPS

---

## Support

**If deployment fails:**
1. Check logs: `docker-compose -f docker-compose.api.yml logs`
2. Verify `.env` has all required keys
3. Confirm security group port 8000 is open
4. Test health: `curl http://localhost:8000/health`

**Common Issues:**
- **Cannot connect to Qdrant**: Check `QDRANT_URL` and `QDRANT_API_KEY` in `.env`
- **502 Bad Gateway**: API container crashed, check logs
- **Database errors**: PostgreSQL not ready, wait 30 seconds and retry

---

**🎉 You're all set! Your RAG API is now running in production on EC2.**
