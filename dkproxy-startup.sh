#!/bin/bash
# DagKnows Proxy Startup Script for Systemd
# This script handles container startup and log capture

set -e

# Configuration - these are set during setup-autorestart installation
DKPROXY_DIR="${DKPROXY_DIR:-/opt/dkproxy}"
LOG_FILE="/var/log/dkproxy-startup.log"

log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$LOG_FILE"
}

log "Starting DagKnows Proxy services"

cd "$DKPROXY_DIR"

# Ensure network exists
docker network create saaslocalnetwork 2>/dev/null || true

# Generate versions.env from manifest if it exists
if [ -f "$DKPROXY_DIR/version-manifest.yaml" ]; then
    python3 "$DKPROXY_DIR/version-manager.py" generate-env 2>/dev/null || true
fi

# Load versions.env if available
if [ -f "$DKPROXY_DIR/versions.env" ]; then
    log "Loading version overrides from versions.env"
    set -a && . "$DKPROXY_DIR/versions.env" && set +a
fi

# Start containers
log "Starting containers..."
if ! docker compose up -d; then
    log "ERROR: Failed to start containers"
    exit 1
fi

# Wait for containers to stabilize
log "Waiting for containers to stabilize..."
sleep 3

# Start background log capture
LOG_CAPTURE_DIR="$DKPROXY_DIR/logs"
LOG_PID_FILE="$LOG_CAPTURE_DIR/.capture.pid"

mkdir -p "$LOG_CAPTURE_DIR"
# Preserve ownership for non-root users
if [ -d "$DKPROXY_DIR" ]; then
    DKPROXY_OWNER=$(stat -c '%U:%G' "$DKPROXY_DIR" 2>/dev/null || stat -f '%Su:%Sg' "$DKPROXY_DIR" 2>/dev/null)
    if [ -n "$DKPROXY_OWNER" ] && [ "$DKPROXY_OWNER" != "root:root" ]; then
        chown -R "$DKPROXY_OWNER" "$LOG_CAPTURE_DIR" 2>/dev/null || true
    fi
fi

if [ ! -f "$LOG_PID_FILE" ] || ! kill -0 $(cat "$LOG_PID_FILE") 2>/dev/null; then
    log "Starting background log capture"
    nohup docker compose logs -f >> "$LOG_CAPTURE_DIR/$(date +%Y-%m-%d).log" 2>&1 &
    echo $! > "$LOG_PID_FILE"
    log "Log capture started (PID: $!)"
else
    log "Log capture already running (PID: $(cat "$LOG_PID_FILE"))"
fi

log "Startup complete"
