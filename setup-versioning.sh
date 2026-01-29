#!/bin/bash
# DagKnows Proxy Version Management Setup Script
# Migrates existing deployment to use versioned image management
#
# Usage:
#   bash setup-versioning.sh
#
# This script sets up version tracking for Docker images, enabling:
# - Pinned versions for reproducible deployments
# - Easy rollback to previous versions
# - Version history tracking
# - Safe updates with automatic backups

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

print_header "DagKnows Proxy Version Management Setup"

cd "$SCRIPT_DIR"
print_info "Working directory: $SCRIPT_DIR"
echo ""

# Check prerequisites
print_info "Checking prerequisites..."

# Check Python3 is available
if ! command -v python3 &> /dev/null; then
    print_error "Python3 is not installed or not in PATH"
    echo ""
    echo "Please install Python3 first."
    exit 1
fi
print_success "Python3 is available"

# Check version-manager.py exists
if [ ! -f "$SCRIPT_DIR/version-manager.py" ]; then
    print_error "version-manager.py not found"
    echo ""
    echo "This file is required for version management."
    echo "Please ensure you have the latest dkproxy installation."
    exit 1
fi
print_success "version-manager.py found"

# Check migrate-to-versioned.py exists
if [ ! -f "$SCRIPT_DIR/migrate-to-versioned.py" ]; then
    print_error "migrate-to-versioned.py not found"
    echo ""
    echo "This file is required for migration."
    echo "Please ensure you have the latest dkproxy installation."
    exit 1
fi
print_success "migrate-to-versioned.py found"

echo ""

# Check if already migrated
if [ -f "$SCRIPT_DIR/version-manifest.yaml" ]; then
    print_header "Version Management Already Enabled"

    print_success "version-manifest.yaml found - versioning is already enabled!"
    echo ""

    print_info "Current versions:"
    echo ""
    python3 "$SCRIPT_DIR/version-manager.py" show 2>/dev/null || {
        print_warning "Could not display versions. Manifest may need regeneration."
        echo ""
        echo "Try running: make migrate-versions"
    }
    echo ""

    echo -e "${BOLD}Available Version Commands:${NC}"
    echo -e "  ${BLUE}make version${NC}                  - Show current versions"
    echo -e "  ${BLUE}make version-history${NC}          - Show version history"
    echo -e "  ${BLUE}make check-updates${NC}            - Check for available updates"
    echo -e "  ${BLUE}make update-safe${NC}              - Safe update with backup"
    echo -e "  ${BLUE}make rollback${NC}                 - Rollback to previous versions"
    echo -e "  ${BLUE}make help-version${NC}             - Show all version commands"
    echo ""

    # Offer to show full help
    read -r -p "Show all version management commands? [y/N]: " show_help
    if [[ "$show_help" =~ ^[Yy] ]]; then
        echo ""
        make help-version 2>/dev/null || python3 "$SCRIPT_DIR/version-manager.py" --help
    fi

    exit 0
fi

# Not yet migrated - proceed with migration
print_header "Setting Up Version Management"

echo "This will enable version tracking for your Docker images."
echo ""
echo -e "${BOLD}Benefits:${NC}"
echo "  - Pin specific versions for reproducible deployments"
echo "  - Easy rollback if an update causes issues"
echo "  - Track version history over time"
echo "  - Safe updates with automatic backups"
echo ""

read -r -p "Proceed with version management setup? [Y/n]: " proceed
proceed=${proceed:-Y}

if [[ ! "$proceed" =~ ^[Yy] ]]; then
    print_info "Setup cancelled."
    exit 0
fi

echo ""
print_info "Running migration..."
echo ""

# Run the migration script
if python3 "$SCRIPT_DIR/migrate-to-versioned.py"; then
    echo ""
    print_header "Version Management Setup Complete"

    print_success "Migration completed successfully!"
    echo ""

    # Show current versions
    if [ -f "$SCRIPT_DIR/version-manifest.yaml" ]; then
        print_info "Current versions:"
        echo ""
        python3 "$SCRIPT_DIR/version-manager.py" show 2>/dev/null || true
        echo ""
    fi

    echo -e "${BOLD}Quick Reference:${NC}"
    echo -e "  ${BLUE}make version${NC}         - Show current versions"
    echo -e "  ${BLUE}make update-safe${NC}     - Safe update with backup"
    echo -e "  ${BLUE}make rollback${NC}        - Rollback to previous versions"
    echo -e "  ${BLUE}make help-version${NC}    - Show all version commands"
    echo ""

    echo -e "${BOLD}Files Created:${NC}"
    echo "  - version-manifest.yaml  (version tracking)"
    echo "  - versions.env           (docker-compose overrides)"
    echo ""

    print_info "Version management is now active!"
    print_info "Your images are now pinned to specific versions."
else
    print_error "Migration failed"
    echo ""
    echo "Please check the error messages above and try again."
    echo "You can also run manually: python3 migrate-to-versioned.py"
    exit 1
fi
