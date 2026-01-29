#!/bin/bash
# DagKnows Proxy Log Rotation Setup Script
# Installs a cron job for automatic log rotation
#
# Usage:
#   bash setup-log-rotation.sh
#
# Log rotation policy:
#   - 0-3 days: uncompressed (.log)
#   - 3-7 days: compressed (.log.gz)
#   - 7+ days: deleted
#
# The cron job runs daily at midnight.

set -e

# Handle interruptions gracefully
trap 'echo ""; echo -e "\033[0;31m✗ ERROR: Setup interrupted by user\033[0m"; exit 1' INT TERM

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

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

print_header "DagKnows Proxy Log Rotation Setup"

cd "$SCRIPT_DIR"
print_info "Working directory: $SCRIPT_DIR"
echo ""

# Check if cron is available
if ! command -v crontab &> /dev/null; then
    print_error "crontab command not found"
    echo ""
    echo "cron is required for automatic log rotation."
    echo "Please install cron first:"
    echo "  Ubuntu/Debian: sudo apt install cron"
    echo "  Amazon Linux:  sudo yum install cronie"
    echo "  RHEL:          sudo yum install cronie"
    exit 1
fi

# Check if cron job already exists
if crontab -l 2>/dev/null | grep -q "dkproxy.*logs-rotate"; then
    print_header "Log Rotation Already Configured"

    print_success "Cron job for log rotation is already installed!"
    echo ""

    print_info "Current cron entry:"
    crontab -l 2>/dev/null | grep "dkproxy.*logs-rotate"
    echo ""

    print_info "Log rotation policy:"
    echo "  - Logs 0-3 days old: kept as .log files"
    echo "  - Logs 3-7 days old: compressed to .log.gz"
    echo "  - Logs 7+ days old:  automatically deleted"
    echo ""

    echo -e "${BOLD}Log Management Commands:${NC}"
    echo -e "  ${BLUE}make logs-status${NC}      - Show log disk usage"
    echo -e "  ${BLUE}make logs-rotate${NC}      - Run rotation now (manual)"
    echo -e "  ${BLUE}make logs-today${NC}       - View today's logs"
    echo -e "  ${BLUE}make logs-errors${NC}      - View errors from logs"
    echo ""

    read -r -p "Remove and reinstall cron job? [y/N]: " reinstall
    if [[ ! "$reinstall" =~ ^[Yy] ]]; then
        exit 0
    fi

    # Remove existing cron job
    print_info "Removing existing cron job..."
    crontab -l 2>/dev/null | grep -v "dkproxy.*logs-rotate" | crontab -
    print_success "Existing cron job removed"
    echo ""
fi

# Display log rotation policy
print_header "Log Rotation Policy"

echo "This will install a cron job that runs daily at midnight."
echo ""
echo -e "${BOLD}Log Retention Policy:${NC}"
echo ""
echo "  ┌─────────────────┬──────────────────────────────┐"
echo "  │  Age            │  Action                      │"
echo "  ├─────────────────┼──────────────────────────────┤"
echo "  │  0-3 days       │  Keep as .log (uncompressed) │"
echo "  │  3-7 days       │  Compress to .log.gz         │"
echo "  │  7+ days        │  Delete automatically        │"
echo "  └─────────────────┴──────────────────────────────┘"
echo ""
echo "Log directory: $SCRIPT_DIR/logs/"
echo ""

# Check current log disk usage
if [ -d "$SCRIPT_DIR/logs" ]; then
    print_info "Current log disk usage:"
    du -sh "$SCRIPT_DIR/logs" 2>/dev/null || echo "  (empty)"
    echo ""
fi

# Confirm with user
read -r -p "Install log rotation cron job? [Y/n]: " confirm
confirm=${confirm:-Y}

if [[ ! "$confirm" =~ ^[Yy] ]]; then
    print_info "Setup cancelled."
    exit 0
fi

echo ""
print_info "Installing cron job..."

# Install cron job using make target
if make logs-cron-install 2>/dev/null; then
    echo ""
    print_header "Log Rotation Setup Complete"

    print_success "Cron job installed successfully!"
    echo ""

    print_info "Cron job details:"
    echo "  Schedule: Daily at midnight (0 0 * * *)"
    echo "  Command:  make logs-rotate"
    echo "  Log file: $SCRIPT_DIR/logs/cron.log"
    echo ""

    echo -e "${BOLD}Useful Commands:${NC}"
    echo -e "  ${BLUE}crontab -l${NC}            - View all cron jobs"
    echo -e "  ${BLUE}make logs-rotate${NC}      - Run rotation manually"
    echo -e "  ${BLUE}make logs-status${NC}      - Check log disk usage"
    echo -e "  ${BLUE}make logs-cron-remove${NC} - Remove cron job"
    echo ""

    echo -e "${BOLD}Other Log Commands:${NC}"
    echo -e "  ${BLUE}make logs${NC}             - View live logs"
    echo -e "  ${BLUE}make logs-today${NC}       - View today's captured logs"
    echo -e "  ${BLUE}make logs-errors${NC}      - View errors from logs"
    echo -e "  ${BLUE}make logs-search PATTERN='text'${NC} - Search logs"
    echo ""
else
    print_error "Failed to install cron job"
    echo ""
    echo "You can try manually:"
    echo "  cd $SCRIPT_DIR && make logs-cron-install"
    exit 1
fi
