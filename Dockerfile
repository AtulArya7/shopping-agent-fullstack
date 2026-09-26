# syntax=docker/dockerfile:1

# ---------------------------------------------------------------------------
# Stage 1 — build the React frontend into static files
# ---------------------------------------------------------------------------
FROM node:20-slim AS frontend-build
WORKDIR /frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
# Baked in at build time — this is a public-facing URL, not a secret, and
# since the frontend is served from the same container as the API, the
# default of the browser's own origin (empty string, see api.js) works too.
ARG VITE_API_URL=""
ENV VITE_API_URL=${VITE_API_URL}
RUN npm run build

# ---------------------------------------------------------------------------
# Stage 2 — the FastAPI app that serves both the API and the built frontend
# ---------------------------------------------------------------------------
FROM python:3.11-slim

# Hugging Face Spaces runs containers as UID 1000 — match that so file
# permissions work whether you deploy here or anywhere else.
RUN useradd -m -u 1000 appuser
WORKDIR /home/appuser/app

COPY backend/requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

COPY --chown=appuser:appuser backend/ .
COPY --chown=appuser:appuser --from=frontend-build /frontend/dist ./static

USER appuser
ENV HOME=/home/appuser

EXPOSE 7860
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-7860}"]
#CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "7860"]
