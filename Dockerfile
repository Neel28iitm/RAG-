# ============================================
# Stage 1: Builder (Dependencies install)
# ============================================
FROM python:3.11-slim as builder

# Set working directory
WORKDIR /build

# Install system dependencies for compilation
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    make \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv

# Activate virtual environment
ENV PATH="/opt/venv/bin:$PATH"

# Upgrade pip
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
# --prefer-binary: Use pre-compiled wheels (faster, less RAM)
# --no-cache-dir: Don't store cache (smaller image)
RUN pip install --no-cache-dir --prefer-binary -r requirements.txt

# ============================================
# Stage 2: Runtime (Final lightweight image)
# ============================================
FROM python:3.11-slim

# Install runtime dependencies only (not build tools)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv

# Set virtual environment in PATH
ENV PATH="/opt/venv/bin:$PATH"

# Create non-root user (SECURITY BEST PRACTICE!)
RUN useradd -m -u 1000 appuser && \
    mkdir -p /app && \
    chown -R appuser:appuser /app

# Set working directory
WORKDIR /app

# Copy application code
COPY --chown=appuser:appuser . .

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8501

# Health check (optional but recommended)
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl --fail http://localhost:8501/_stcore/health || exit 1

# Run application
# Pointing to src/streamlit_app.py as the actual Streamlit app
CMD ["streamlit", "run", "src/streamlit_app.py", "--server.address", "0.0.0.0", "--server.port", "8501"]
