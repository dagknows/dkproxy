#!/bin/bash
# Docker command wrapper that handles docker group permission issues
# Automatically uses 'sg docker' if docker group is not active in current session
#
# Usage: ./run-docker.sh docker compose logs -f
#        ./run-docker.sh docker compose up -d

# Check if docker is accessible directly
if docker ps >/dev/null 2>&1; then
    # Direct access works - run command normally
    exec "$@"
fi

# Check if docker daemon is even running
if ! (systemctl is-active docker >/dev/null 2>&1 || pgrep -x dockerd >/dev/null 2>&1); then
    echo "ERROR: Docker daemon is not running" >&2
    echo "Start it with: sudo systemctl start docker" >&2
    exit 1
fi

# Docker is running but we don't have permission - try sg docker
if sg docker -c 'docker ps' >/dev/null 2>&1; then
    # Build command string for sg docker
    cmd=""
    for arg in "$@"; do
        # Escape single quotes in arguments
        escaped_arg="${arg//\'/\'\\\'\'}"
        cmd="$cmd '$escaped_arg'"
    done
    exec sg docker -c "$cmd"
fi

# Neither direct nor sg docker works
echo "ERROR: Cannot access Docker" >&2
echo "Make sure you're in the docker group: groups | grep docker" >&2
echo "If just added, try: newgrp docker (or logout/login)" >&2
exit 1
