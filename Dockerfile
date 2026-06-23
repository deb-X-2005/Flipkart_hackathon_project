# syntax=docker/dockerfile:1.7
# All-in-one: builds the React frontend AND runs the FastAPI backend.
# Backend serves /api/* routes and / (SPA fallback) from the same process.

# ───────── Stage 1: frontend build ─────────
FROM node:20-alpine AS frontend-build
WORKDIR /fe
# Empty VITE_API_URL => frontend calls same origin without /api prefix
# (backend routes live at /auth/login, /chat, etc.)
ENV VITE_API_URL=""
COPY frontend/package*.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ .
RUN npm run build

# ───────── Stage 2: python deps ─────────
FROM python:3.11-slim AS python-deps
WORKDIR /build
ENV PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1
RUN apt-get update && apt-get install -y --no-install-recommends build-essential \
 && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --user --no-warn-script-location -r requirements.txt

# ───────── Stage 3: runtime ─────────
FROM python:3.11-slim AS runtime
WORKDIR /app
RUN useradd -m -u 1000 app
COPY --from=python-deps /root/.local /home/app/.local
ENV PATH=/home/app/.local/bin:$PATH \
    PYTHONPATH=/app \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8000

# Backend source + baked data/model artifacts
COPY src/             ./src/
COPY data/processed/  ./data/processed/
COPY data/rag/        ./data/rag/
COPY models/          ./models/

# Frontend build output -> /app/static (served by FastAPI)
COPY --from=frontend-build /fe/dist ./static/

RUN mkdir -p logs && chown -R app:app /app
USER app
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:'+'${PORT:-8000}'+'/health', timeout=3).read()" || exit 1

# HF Spaces sets PORT=7860; respect it. Otherwise default 8000.
CMD ["sh", "-c", "uvicorn src.api.main:app --host 0.0.0.0 --port ${PORT:-8000} --log-level info"]
