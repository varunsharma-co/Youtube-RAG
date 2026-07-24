# ==========================================
# STAGE 1: Builder (Full Python image)
# ==========================================
FROM python:3.11 AS builder

ENV PYTHONDONTWRITEBYTECODE=1

WORKDIR /build

# Create an isolated virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy requirements and install dependencies into virtual environment
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt


# ==========================================
# STAGE 2: Production Runner (Slim Runtime)
# ==========================================
FROM python:3.11-slim AS runner

ENV PYTHONDONTWRITEBYTECODE=1 \
    PATH="/opt/venv/bin:$PATH" \
    PORT=8080

WORKDIR /app

# Create non-root system user & group and set working directory ownership
RUN groupadd -r appgroup && useradd -r -g appgroup appuser && \
    chown -R appuser:appgroup /app

# Copy virtual environment from builder stage
COPY --from=builder /opt/venv /opt/venv

# Explicitly copy ONLY the source code files required for FastAPI & Retrieval
COPY --chown=appuser:appgroup api_main.py .
COPY --chown=appuser:appgroup main_retrieval.py .
COPY --chown=appuser:appgroup Final_Files/Retrieval ./Final_Files/Retrieval

# Native Python health check dynamically checking active PORT against FastAPI health endpoint
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import os, urllib.request; urllib.request.urlopen(f'http://localhost:{os.getenv(\"PORT\", \"8080\")}/')" || exit 1

# Switch to non-root user
USER appuser

EXPOSE 8080

# Start FastAPI app using Uvicorn on Cloud Run's dynamic PORT
CMD ["sh", "-c", "exec uvicorn api_main:app --host 0.0.0.0 --port ${PORT:-8080}"]
