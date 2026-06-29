# syntax=docker/dockerfile:1.6
FROM python:3.12-slim AS base

# Build metadata
LABEL org.opencontainers.image.title="OCR Platform Backend"
LABEL org.opencontainers.image.description="Backend service for the OCR Benchmark Platform"
LABEL org.opencontainers.image.version="0.1.0"

# Environment
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONFAULTHANDLER=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# ───────────────────────────────────────────────
# Dependencies stage
# ───────────────────────────────────────────────
FROM base AS deps

# Install system dependencies for PDF/image processing (future milestones)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt requirements-dev.txt ./
RUN pip install --no-cache-dir -r requirements.txt -r requirements-dev.txt

# ───────────────────────────────────────────────
# Production stage
# ───────────────────────────────────────────────
FROM base AS production

# Install only runtime system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

COPY --from=deps /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=deps /usr/local/bin /usr/local/bin

COPY src/ ./src/
COPY tests/ ./tests/
COPY pyproject.toml ./

# Install the package in editable mode
RUN pip install -e .

# Healthcheck
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "ocr_platform.main:app", "--host", "0.0.0.0", "--port", "8000"]
