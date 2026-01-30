#!/bin/bash
# DagKnows Proxy Startup Script for Systemd
# This script handles container startup and log capture

set -e

# Configuration - these are set during setup-autorestart installation
DKPROXY_DIR="${DKPROXY_DIR:-/opt/dkproxy}"

# Derive unique log file name from PROXY_ALIAS in .env
# e.g., PROXY_ALIAS=freshproxy15 -> /var/log/dkproxy-startup-freshproxy15.log
if [ -f "$DKPROXY_DIR/.env" ]; then
    PROXY_ALIAS=$(grep -E "^PROXY_ALIAS=" "$DKPROXY_DIR/.env" 2>/dev/null | cut -d'=' -f2 | tr -d '"' | tr -d "'" || true)
fi
if [ -z "$PROXY_ALIAS" ]; then
    # Fallback to parent directory if no PROXY_ALIAS
    PROXY_ALIAS=$(basename "$(dirname "$DKPROXY_DIR")")
fi
LOG_FILE="/var/log/dkproxy-startup-${PROXY_ALIAS}.log"

log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$LOG_FILE"
}

log "Starting DagKnows Proxy services"

cd "$DKPROXY_DIR"

# Network is created automatically by Docker Compose with named network config

# Generate versions.env from manifest if it exists
if [ -f "$DKPROXY_DIR/version-manifest.yaml" ]; then
    if ! python3 "$DKPROXY_DIR/version-manager.py" generate-env 2>/dev/null; then
        log "Warning: Failed to generate versions.env - using default versions"
    fi
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

if [ ! -f "$LOG_PID_FILE" ] || ! ps -p $(cat "$LOG_PID_FILE") > /dev/null 2>&1; then
    log "Starting background log capture"
    nohup docker compose logs -f >> "$LOG_CAPTURE_DIR/$(date +%Y-%m-%d).log" 2>&1 &
    echo $! > "$LOG_PID_FILE"
    log "Log capture started (PID: $!)"
else
    log "Log capture already running (PID: $(cat "$LOG_PID_FILE"))"
fi

log "Startup complete"
