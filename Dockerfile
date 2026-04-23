# ---- Stage 1: Build React frontend ----
FROM node:20-slim AS frontend-build

WORKDIR /app/frontend

# Chromium para react-snap (prerender)
RUN apt-get update && apt-get install -y chromium --no-install-recommends && rm -rf /var/lib/apt/lists/*
ENV PUPPETEER_EXECUTABLE_PATH=/usr/bin/chromium

# Install dependencies
COPY frontend/package.json frontend/yarn.lock* ./
RUN yarn install --network-timeout 300000

# Copy source and build (no REACT_APP_BACKEND_URL so it defaults to '' = same origin)
COPY frontend/ ./
RUN yarn build

# ---- Stage 2: Python backend + serve frontend ----
FROM python:3.11-slim

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

WORKDIR /app/backend
CMD uvicorn server:app --host 0.0.0.0 --port ${PORT}
