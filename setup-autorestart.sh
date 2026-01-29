#!/bin/bash
# DagKnows Proxy Auto-Restart Setup Script
# Configures systemd service for automatic startup on system boot
#
# Usage:
#   make setup-autorestart
#
# This script sets up systemd to automatically start the proxy services
# when the system boots. Unlike dkapp, dkproxy uses an unencrypted .env
# file, so no passphrase handling is required.

set -e

# Handle interruptions gracefully
trap 'echo ""; echo -e "\033[0;31m✗ ERROR: Setup interrupted by user\033[0m"; exit 1' INT TERM

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_DIR="${DKPROXY_INSTALL_DIR:-$SCRIPT_DIR}"

# Derive unique service name from PROXY_ALIAS in .env
# e.g., PROXY_ALIAS=freshproxy15 -> dkproxy-freshproxy15.service
# Falls back to parent directory if PROXY_ALIAS not found
if [ -f "$INSTALL_DIR/.env" ]; then
    PROXY_ALIAS=$(grep -E "^PROXY_ALIAS=" "$INSTALL_DIR/.env" 2>/dev/null | cut -d'=' -f2 | tr -d '"' | tr -d "'" || true)
fi
if [ -z "$PROXY_ALIAS" ]; then
    # Fallback to parent directory if no PROXY_ALIAS
    PROXY_ALIAS=$(basename "$(dirname "$INSTALL_DIR")")
fi
SERVICE_NAME="dkproxy-${PROXY_ALIAS}.service"
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m' # No Color

print_header() {
    echo ""
    echo -e "${GREEN}${BOLD}============================================${NC}"
    echo -e "${GREEN}${BOLD}  $1${NC}"
    echo -e "${GREEN}${BOLD}============================================${NC}"
    echo ""
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ ERROR: $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ $1${NC}"
}

print_header "DagKnows Proxy Auto-Restart Setup"

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    print_error "This script must be run as root (use sudo)"
    echo ""
    echo "Usage: sudo bash setup-autorestart.sh"
    exit 1
fi

print_info "Installation directory: $INSTALL_DIR"
print_info "Service name: $SERVICE_NAME"
echo ""

# Check prerequisites
print_info "Checking prerequisites..."

# Check .env file exists
if [ ! -f "$INSTALL_DIR/.env" ]; then
    print_error ".env file not found in $INSTALL_DIR"
    echo ""
    echo "The .env file is required for the proxy to start."
    echo "Please complete the proxy setup first:"
    echo "  1. Activate venv: source ~/dkenv/bin/activate"
    echo "  2. Create proxy: dk proxy new <proxy_name>"
    echo "  3. Get env vars: dk proxy getenv <proxy_name>"
    exit 1
fi
print_success ".env file found"

# Check docker-compose.yaml exists
if [ ! -f "$INSTALL_DIR/docker-compose.yaml" ]; then
    print_error "docker-compose.yaml not found in $INSTALL_DIR"
    exit 1
fi
print_success "docker-compose.yaml found"

# Check dkproxy.service template exists
if [ ! -f "$INSTALL_DIR/dkproxy.service" ]; then
    print_error "dkproxy.service template not found in $INSTALL_DIR"
    exit 1
fi
print_success "dkproxy.service template found"

# Check dkproxy-startup.sh exists
if [ ! -f "$INSTALL_DIR/dkproxy-startup.sh" ]; then
    print_error "dkproxy-startup.sh not found in $INSTALL_DIR"
    exit 1
fi
print_success "dkproxy-startup.sh found"

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    print_error "Docker is not installed"
    echo "Please install Docker first."
    exit 1
fi
print_success "Docker is installed"

# Check if systemd is available
if ! command -v systemctl &> /dev/null; then
    print_error "systemctl not found - systemd is required"
    echo "This script requires a systemd-based Linux distribution."
    exit 1
fi
print_success "systemd is available"

echo ""

# Enable Docker service to start on boot
print_info "Enabling Docker service to start on boot..."
if systemctl is-enabled docker &>/dev/null; then
    print_success "Docker service already enabled for boot startup"
else
    if systemctl enable docker; then
        print_success "Docker service enabled for boot startup"
    else
        print_error "Failed to enable Docker service"
        exit 1
    fi
fi

# Copy and configure startup script
print_info "Configuring startup script..."
chmod +x "$INSTALL_DIR/dkproxy-startup.sh"

# Update paths in startup script (in-place edit)
sed -i "s|DKPROXY_DIR:-/opt/dkproxy|DKPROXY_DIR:-$INSTALL_DIR|g" "$INSTALL_DIR/dkproxy-startup.sh"
print_success "Startup script configured"

# Install systemd service file
print_info "Installing systemd service file..."

# Copy service file to systemd directory with unique name
cp "$INSTALL_DIR/dkproxy.service" "$SERVICE_FILE"

# Update paths in service file
sed -i "s|/opt/dkproxy|$INSTALL_DIR|g" "$SERVICE_FILE"

# Update description to include the identifier
sed -i "s|DagKnows Proxy Services|DagKnows Proxy Services ($PROXY_ALIAS)|g" "$SERVICE_FILE"

print_success "Systemd service file installed: $SERVICE_NAME"

# Reload systemd daemon
print_info "Reloading systemd daemon..."
systemctl daemon-reload
print_success "Systemd daemon reloaded"

# Enable the service
print_info "Enabling $SERVICE_NAME..."
systemctl enable "$SERVICE_NAME"
print_success "Service enabled for automatic startup"

print_header "Auto-Restart Setup Complete"

echo -e "${BOLD}What this means:${NC}"
echo "  - Proxy services will start automatically when the system boots"
echo "  - Log capture will start automatically"
echo "  - You can use 'make start/stop/restart' commands"
echo ""

echo -e "${BOLD}Service Management Commands:${NC}"
echo -e "  ${BLUE}make start${NC}              - Start proxy services"
echo -e "  ${BLUE}make stop${NC}               - Stop proxy services"
echo -e "  ${BLUE}make restart${NC}            - Restart proxy services"
echo -e "  ${BLUE}make autorestart-status${NC} - Check auto-restart status"
echo ""

echo -e "${BOLD}Systemd Commands (alternative):${NC}"
echo -e "  ${BLUE}sudo systemctl start $SERVICE_NAME${NC}   - Start services"
echo -e "  ${BLUE}sudo systemctl stop $SERVICE_NAME${NC}    - Stop services"
echo -e "  ${BLUE}sudo systemctl status $SERVICE_NAME${NC}  - Check status"
echo ""

echo -e "${BOLD}View Logs:${NC}"
echo -e "  ${BLUE}make logs${NC}                              - View live container logs"
echo -e "  ${BLUE}cat /var/log/dkproxy-startup-${PROXY_ALIAS}.log${NC} - View startup log"
echo ""

echo -e "${BOLD}To Disable Auto-Restart:${NC}"
echo -e "  ${BLUE}make disable-autorestart${NC}"
echo "  or: sudo systemctl disable $SERVICE_NAME"
echo ""

# Offer to start services now
echo -e "${YELLOW}Would you like to start the proxy services now?${NC}"
read -r -p "Start services? [Y/n]: " start_now
start_now=${start_now:-Y}

if [[ "$start_now" =~ ^[Yy] ]]; then
    echo ""
    # Use make start which handles everything properly:
    # - Stops existing services
    # - Loads versions.env if present
    # - Starts via systemd (since we just installed it)
    # - Starts log capture
    print_info "Starting proxy services..."
    cd "$INSTALL_DIR"
    if make start; then
        print_success "Proxy services started successfully!"

        # Verify log capture is running
        LOG_PID_FILE="$INSTALL_DIR/logs/.capture.pid"
        if [ -f "$LOG_PID_FILE" ] && kill -0 $(cat "$LOG_PID_FILE") 2>/dev/null; then
            print_success "Background log capture running (PID: $(cat "$LOG_PID_FILE"))"
        else
            print_warning "Background log capture may not be running"
            echo "  You can start it manually with: make logs-start"
        fi
        echo ""
        echo "View logs with: make logs"
    else
        print_error "Failed to start services"
        echo "Check logs with: journalctl -u $SERVICE_NAME"
    fi
else
    echo ""
    print_info "Services not started. Use 'make start' when ready."
fi

echo ""
