# Multi-stage / Lightweight Production Dockerfile for Batch Watermark Studio
FROM python:3.11-slim

# Install system fonts and dependencies for high-quality text watermark rendering in Linux
RUN apt-get update && apt-get install -y --no-install-recommends \
    fonts-dejavu-core \
    fonts-freefont-ttf \
    fonts-liberation \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY . .

# Ensure storage directories exist with write permissions
RUN mkdir -p uploads watermarked_output web

# Default network configuration
ENV HOST=0.0.0.0
ENV PORT=7860
EXPOSE 7860

# Healthcheck for container orchestration (Docker Compose / Kubernetes)
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:${PORT}/health || exit 1

# Run the high-performance watermarker server
CMD ["python3", "server.py"]
