# ==============================================================================
# Aurevia Motors — Production Docker Containerfile
# Python 3.12 Slim with optimized caching, security, and WSGI runtime
# ==============================================================================

FROM python:3.12-slim-bookworm AS base

# Prevent Python from writing .pyc files and enable unbuffered logging
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_ENV=production \
    PORT=8000

WORKDIR /app

# Install essential system runtime dependencies for Pillow image rendering
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libjpeg-dev \
    zlib1g-dev \
    libpng-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY . .

# Ensure storage directories exist
RUN mkdir -p /app/staticfiles /app/media /app/backups

# Expose HTTP port
EXPOSE 8000

# Copy and make entrypoint executable
RUN chmod +x /app/entrypoint.sh

# Run via automated production entrypoint
ENTRYPOINT ["/app/entrypoint.sh"]
