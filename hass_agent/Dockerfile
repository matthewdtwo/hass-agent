ARG BUILD_FROM=ghcr.io/home-assistant/amd64-base-python:3.13-alpine3.23

# Stage 1: Build frontend
FROM node:22-alpine AS frontend-builder
WORKDIR /build
COPY src/frontend/package*.json ./
RUN npm ci
COPY src/frontend/ ./
RUN npm run build

# Stage 2: Final image
FROM $BUILD_FROM

# Install uv
RUN pip3 install --no-cache-dir uv

# Install Python dependencies
WORKDIR /app
COPY src/backend/pyproject.toml src/backend/uv.lock ./
RUN uv sync --no-dev --frozen

# Copy app source
COPY src/backend/app/ ./app/

# Copy built frontend
COPY --from=frontend-builder /build/dist/ ./frontend/dist/

ENV FRONTEND_DIR=/app/frontend/dist

# Install as an s6 service so the base image's s6 init stays as PID 1
COPY run.sh /etc/services.d/ha_agent/run
RUN chmod a+x /etc/services.d/ha_agent/run
