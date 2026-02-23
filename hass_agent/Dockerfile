ARG BUILD_FROM=ghcr.io/home-assistant/amd64-base-python:3.12

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

COPY run.sh /run.sh
RUN chmod a+x /run.sh
CMD ["/run.sh"]
