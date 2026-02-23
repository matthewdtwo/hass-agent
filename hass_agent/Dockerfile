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

# Register as an s6-overlay v3 longrun service
RUN mkdir -p /etc/s6-overlay/s6-rc.d/ha_agent
COPY run.sh /etc/s6-overlay/s6-rc.d/ha_agent/run
RUN chmod a+x /etc/s6-overlay/s6-rc.d/ha_agent/run \
    && echo "longrun" > /etc/s6-overlay/s6-rc.d/ha_agent/type \
    && mkdir -p /etc/s6-overlay/s6-rc.d/user/contents.d \
    && touch /etc/s6-overlay/s6-rc.d/user/contents.d/ha_agent

CMD ["/init"]
