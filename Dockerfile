# ---- Stage 1: Build React frontend ----
# Node 22+ exigido por camera-controls@3.x (dep transitiva de @react-three/drei).
FROM node:22-slim AS frontend-build

WORKDIR /app/frontend

# Install dependencies
COPY frontend/package.json frontend/yarn.lock* ./
RUN yarn install --network-timeout 300000

# Copy source and build (no REACT_APP_BACKEND_URL so it defaults to '' = same origin)
COPY frontend/ ./
RUN yarn build

# ---- Stage 2: Python backend + serve frontend ----
FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    openssl \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/* \
    && update-ca-certificates

WORKDIR /app

# Install Python dependencies
COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

# Copy backend source
COPY backend/ ./backend/

# Copy frontend build from stage 1
COPY --from=frontend-build /app/frontend/build ./frontend/build

# Railway injects PORT; default to 8000 for local testing
ENV PORT=8000

EXPOSE ${PORT}

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 CMD python -c "import os, sys, urllib.request; port=os.getenv('PORT','8000'); urllib.request.urlopen(f'http://127.0.0.1:{port}/api/', timeout=3); sys.exit(0)"

WORKDIR /app/backend
CMD ["python", "run_server.py"]
