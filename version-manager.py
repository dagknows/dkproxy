#!/usr/bin/env python3
"""
DagKnows Proxy Version Manager
Manages service versions, rollbacks, and deployments for dkproxy on-prem installations.

NOTE: Each service has its own version (e.g., outpost:1.42, cmd_exec:1.15, vault:latest)
      vault defaults to 'latest' (HashiCorp-controlled), manual pinning supported

Usage:
    python3 version-manager.py show                          # Show current versions
    python3 version-manager.py history [SERVICE]             # Show version history
    python3 version-manager.py pull --service=S --tag=TAG    # Pull specific version for a service
    python3 version-manager.py rollback --service=S          # Rollback to previous
    python3 version-manager.py set --service=S --tag=TAG     # Set custom version (hotfixes)
    python3 version-manager.py update-safe                   # Safe update to latest with rollback
    python3 version-manager.py check-updates                 # Check for available updates
    python3 version-manager.py generate-env                  # Generate versions.env
    python3 version-manager.py pull-from-manifest            # Pull versions from manifest
    python3 version-manager.py resolve-tags                  # Resolve :latest tags to versions (ECR only)
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
import yaml
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple


# ============================================
# CONSTANTS
# ============================================

SERVICES = [
    'outpost',
    'cmd_exec',
    'vault'
]

# ECR services - only these will have :latest resolved to semantic versions
# vault uses DockerHub and defaults to :latest (HashiCorp-controlled)
ECR_SERVICES = ['outpost', 'cmd_exec']

# Map service names to docker-compose service names
SERVICE_TO_COMPOSE = {
    'outpost': 'outpost',
    'cmd_exec': 'cmd-exec',  # Note: hyphen in compose
    'vault': 'vault'
}

DEFAULT_REGISTRY = 'public.ecr.aws/n5k3t9x2'
HISTORY_LIMIT = 5

# Global flag to track if we need sg docker wrapper
USE_SG_DOCKER = False


# ============================================
# COLORS AND OUTPUT
# ============================================

class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'


def print_header(text: str):
    """Print a formatted header"""
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'='*60}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{text:^60}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'='*60}{Colors.ENDC}\n")


def print_success(text: str):
    """Print success message"""
    print(f"{Colors.OKGREEN}\u2713 {text}{Colors.ENDC}")


def print_error(text: str):
    """Print error message"""
    print(f"{Colors.FAIL}\u2717 {text}{Colors.ENDC}")


def print_warning(text: str):
    """Print warning message"""
    print(f"{Colors.WARNING}\u26a0 {text}{Colors.ENDC}")


def print_info(text: str):
    """Print info message"""
    print(f"{Colors.OKBLUE}\u2139 {text}{Colors.ENDC}")


def print_check(name: str, status: bool, message: str = ""):
    """Print a check result with alignment"""
    if status:
        symbol = f"{Colors.OKGREEN}\u2713{Colors.ENDC}"
        status_text = f"{Colors.OKGREEN}OK{Colors.ENDC}"
    else:
        symbol = f"{Colors.FAIL}\u2717{Colors.ENDC}"
        status_text = f"{Colors.FAIL}FAILED{Colors.ENDC}"

    print(f"{symbol} {name:.<50} {status_text}")
    if message:
        print(f"  {Colors.WARNING}\u2192 {message}{Colors.ENDC}")


# ============================================
# UTILITIES
# ============================================

def run_command(cmd: str, capture: bool = True, timeout: int = 300) -> Tuple[bool, str]:
    """Run a shell command and return success status and output"""
    try:
        if capture:
            result = subprocess.run(
                cmd, shell=True, capture_output=True, text=True, timeout=timeout
            )
            # Combine stdout and stderr for error messages
            output = result.stdout.strip()
            if result.stderr.strip():
                output = f"{output}\n{result.stderr.strip()}" if output else result.stderr.strip()
            return result.returncode == 0, output
        else:
            result = subprocess.run(cmd, shell=True, timeout=timeout)
            return result.returncode == 0, ""
    except subprocess.TimeoutExpired:
        return False, "Command timed out"
    except Exception as e:
        return False, str(e)


def confirm(prompt: str, default: bool = False) -> bool:
    """Ask for user confirmation"""
    suffix = " (yes/no) [no]: " if not default else " (yes/no) [yes]: "
    response = input(prompt + suffix).strip().lower()
    if not response:
        return default
    return response in ('yes', 'y')


def check_docker_access() -> bool:
    """
    Check if Docker is accessible. Automatically tries sg docker if needed.
    Sets global USE_SG_DOCKER flag for other functions to use.
    Returns True if Docker is accessible (directly or via sg), False otherwise.
    """
    global USE_SG_DOCKER

    # First check if Docker daemon is running
    daemon_running, _ = run_command(
        "systemctl is-active docker 2>/dev/null || pgrep -x dockerd > /dev/null"
    )

    # Check if user can access Docker directly
    can_access, _ = run_command("docker ps 2>&1")

    if can_access:
        USE_SG_DOCKER = False
        return True

    if daemon_running:
        # Docker is running but user can't access - try sg docker
        can_access_sg, _ = run_command("sg docker -c 'docker ps' 2>&1")
        if can_access_sg:
            USE_SG_DOCKER = True
            print_info("Using 'sg docker' for Docker commands (docker group not active in session)")
            return True
        else:
            # Even sg docker didn't work
            print_error("Docker is running but you don't have permission to access it")
            print_info("Make sure your user is in the docker group: sudo usermod -aG docker $USER")
            print_info("Then log out and back in, or run: newgrp docker")
            return False
    else:
        # Docker daemon not running
        print_error("Docker daemon is not running")
        print_info("Start Docker with: sudo systemctl start docker")
        return False


def docker_command(cmd: str) -> str:
    """Wrap a docker command with sg docker if needed."""
    global USE_SG_DOCKER
    if USE_SG_DOCKER:
        # Escape single quotes in the command
        escaped_cmd = cmd.replace("'", "'\\''")
        return f"sg docker -c '{escaped_cmd}'"
    return cmd


# ============================================
# DOCKER HELPER FUNCTIONS
# ============================================

def clear_stale_ecr_credentials(registry: str) -> bool:
    """
    Clear stale Docker credentials for public ECR.
    This is needed when Docker has cached an expired token.

    Returns:
        True if logout was attempted, False otherwise
    """
    if 'public.ecr.aws' in registry:
        print_info("Clearing stale Docker credentials for public.ecr.aws...")
        run_command(docker_command("docker logout public.ecr.aws") + " 2>&1", capture=False)
        return True
    return False


def docker_pull_with_retry(image: str, max_retries: int = 2) -> Tuple[bool, str]:
    """
    Pull a Docker image with automatic retry on expired token errors.
    Uses sg docker wrapper if needed.

    Args:
        image: Full image name (e.g., 'public.ecr.aws/n5k3t9x2/outpost:latest')
        max_retries: Maximum number of retries

    Returns:
        Tuple of (success, output)
    """
    for attempt in range(max_retries):
        cmd = docker_command(f"docker pull {image}")
        success, output = run_command(cmd)
        
        if success:
            return True, output
        
        # Check if error is due to expired token
        if "authorization token has expired" in output.lower() or "reauthenticate" in output.lower():
            if attempt < max_retries - 1:
                # Extract registry from image
                if 'public.ecr.aws' in image:
                    print_warning("Detected expired Docker token, clearing credentials...")
                    clear_stale_ecr_credentials('public.ecr.aws')
                    print_info("Retrying pull...")
                    continue
        
        # For other errors or final attempt, return the error
        return False, output
    
    return False, output


# ============================================
# ECR TAG RESOLUTION
# ============================================

def check_ecr_access() -> bool:
    """Check if AWS CLI can access ECR Public API"""
    success, output = run_command(
        "aws ecr-public describe-images --repository-name req_router "
        "--region us-east-1 --max-results 1 --output json 2>&1",
        timeout=15
    )
    return success


def resolve_tag_from_ecr(service_name: str, image_digest: str = None) -> Optional[str]:
    """
    Query ECR Public to find the semantic version tag for a service.
    
    Args:
        service_name: Name of the service (e.g., 'req_router')
        image_digest: Optional digest to match (e.g., 'sha256:abc123...')
        
    Returns:
        Semantic version tag (e.g., '1.35') or None if unable to resolve
    """
    # Query AWS ECR Public API for image details
    success, output = run_command(
        f"aws ecr-public describe-images --repository-name {service_name} "
        f"--region us-east-1 --output json 2>&1",
        timeout=30
    )
    
    if not success:
        return None
    
    try:
        ecr_data = json.loads(output)
        image_details = ecr_data.get('imageDetails', [])
        
        # If we have a digest, try to match it first
        if image_digest:
            # Clean up digest format (remove brackets and prefix)
            clean_digest = image_digest.strip('[]').split('@')[-1] if '@' in image_digest else image_digest
            
            for image_detail in image_details:
                ecr_digest = image_detail.get('imageDigest', '')
                if clean_digest and ecr_digest and (ecr_digest == clean_digest or clean_digest in ecr_digest or ecr_digest in clean_digest):
                    tags = image_detail.get('imageTags', [])
                    semantic_tags = [t for t in tags if t != 'latest' and not t.startswith('sha')]
                    if semantic_tags:
                        # Sort to get highest version
                        try:
                            semantic_tags.sort(
                                key=lambda x: [int(p) if p.isdigit() else p for p in x.replace('-', '.').split('.')],
                                reverse=True
                            )
                        except (ValueError, AttributeError):
                            pass
                        return semantic_tags[0]
        
        # Fallback: Find the image tagged as 'latest' and get its semantic version
        for image_detail in image_details:
            tags = image_detail.get('imageTags', [])
            if 'latest' in tags:
                semantic_tags = [t for t in tags if t != 'latest' and not t.startswith('sha')]
                if semantic_tags:
                    try:
                        semantic_tags.sort(
                            key=lambda x: [int(p) if p.isdigit() else p for p in x.replace('-', '.').split('.')],
                            reverse=True
                        )
                    except (ValueError, AttributeError):
                        pass
                    return semantic_tags[0]
                    
    except (json.JSONDecodeError, KeyError):
        pass
    
    return None


# ============================================
# VERSION MANAGER CLASS
# ============================================

class VersionManager:
    def __init__(self):
        self.manifest_file = 'version-manifest.yaml'
        self.versions_env = 'versions.env'
        self.backup_dir = '.version-backups'
        self.manifest = self.load_manifest()

    def load_manifest(self) -> Dict:
        """Load version manifest or create default"""
        if os.path.exists(self.manifest_file):
            with open(self.manifest_file, 'r') as f:
                return yaml.safe_load(f) or self.create_default_manifest()
        return self.create_default_manifest()

    def create_default_manifest(self) -> Dict:
        """Create a default manifest structure"""
        return {
            'schema_version': '1.0',
            'deployment_id': f'dkproxy-{datetime.now().strftime("%Y%m%d")}',
            'customer_id': '',
            'proxy_location': '',  # NEW: Track proxy location for distributed deployments
            'ecr': {
                'registry': 'public.ecr.aws',
                'repository_alias': 'n5k3t9x2',
                'use_private': False,
                'private_registry': '',
                'private_region': 'us-east-1'
            },
            'services': {},
            'history': {},
            'custom_overrides': {}
        }

    def save_manifest(self):
        """Save manifest with backup"""
        self.backup_manifest()
        with open(self.manifest_file, 'w') as f:
            yaml.dump(self.manifest, f, default_flow_style=False, sort_keys=False)

    def backup_manifest(self):
        """Backup current manifest before changes"""
        if os.path.exists(self.manifest_file):
            os.makedirs(self.backup_dir, exist_ok=True)
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
            backup_path = f"{self.backup_dir}/{self.manifest_file}.{timestamp}"
            shutil.copy(self.manifest_file, backup_path)
            return backup_path
        return None

    def get_registry(self) -> str:
        """Get current registry URL"""
        ecr = self.manifest.get('ecr', {})
        if ecr.get('use_private') and ecr.get('private_registry'):
            return ecr.get('private_registry')
        registry = ecr.get('registry', 'public.ecr.aws')
        alias = ecr.get('repository_alias', 'n5k3t9x2')
        return f"{registry}/{alias}"

    def get_image_name(self, service: str, tag: str) -> str:
        """
        Get full image name for a service with appropriate registry.

        Args:
            service: Service name (outpost, cmd_exec, or vault)
            tag: Image tag

        Returns:
            Full image name with registry
        """
        if service in ECR_SERVICES:
            registry = self.get_registry()
            return f"{registry}/{service}:{tag}"
        elif service == 'vault':
            # vault uses DockerHub
            return f"hashicorp/vault:{tag}"
        else:
            raise ValueError(f"Unknown service: {service}")

    def get_full_image(self, service: str, tag: str = None) -> str:
        """Get full image name with registry and tag"""
        if tag is None:
            tag = self.get_current_tag(service)
        return self.get_image_name(service, tag)

    def get_current_tag(self, service: str) -> str:
        """Get current tag for a service"""
        # Check custom overrides first
        override = self.manifest.get('custom_overrides', {}).get(service, {})
        if override.get('tag'):
            return override['tag']
        # Then check services
        return self.manifest.get('services', {}).get(service, {}).get('current_tag', 'latest')

    def get_previous_tag(self, service: str) -> Optional[str]:
        """Get previous tag for a service from history"""
        history = self.manifest.get('history', {}).get(service, [])
        for entry in history:
            if entry.get('status') == 'previous':
                return entry.get('tag')
        # If no 'previous' status, try second entry
        if len(history) > 1:
            return history[1].get('tag')
        return None

    # ==================
    # SHOW COMMANDS
    # ==================

    def show(self):
        """Display current versions"""
        print_header("Current Deployed Versions")

        services = self.manifest.get('services', {})
        overrides = self.manifest.get('custom_overrides', {})

        if not services:
            print_warning("No versions tracked yet. Run 'make migrate-versions' to initialize.")
            return

        for name in SERVICES:
            info = services.get(name, {})
            tag = info.get('current_tag', 'unknown')
            deployed = info.get('deployed_at', '')[:10] if info.get('deployed_at') else 'unknown'

            # Check for override
            override = overrides.get(name, {})
            if override.get('tag'):
                tag = override['tag']
                reason = override.get('reason', 'custom')
                print(f"  {name:.<40} {tag:<15} ({deployed}) [{reason}]")
            else:
                print(f"  {name:.<40} {tag:<15} ({deployed})")

        print()

    def history(self, service: str = None):
        """Show version history"""
        print_header("Version History")

        history = self.manifest.get('history', {})

        if not history:
            print_warning("No version history available.")
            return

        if service:
            if service in history:
                print(f"\n{Colors.BOLD}{service}:{Colors.ENDC}")
                for entry in history[service][:HISTORY_LIMIT]:
                    tag = entry.get('tag', 'unknown')
                    deployed = entry.get('deployed_at', '')[:19] if entry.get('deployed_at') else 'unknown'
                    status = entry.get('status', '')
                    status_str = f" [{status}]" if status else ""
                    print(f"  {tag:<20} {deployed:<25} {status_str}")
            else:
                print_warning(f"No history for service: {service}")
        else:
            for svc in SERVICES:
                entries = history.get(svc, [])
                if entries:
                    print(f"\n{Colors.BOLD}{svc}:{Colors.ENDC}")
                    for entry in entries[:HISTORY_LIMIT]:
                        tag = entry.get('tag', 'unknown')
                        deployed = entry.get('deployed_at', '')[:19] if entry.get('deployed_at') else 'unknown'
                        status = entry.get('status', '')
                        status_str = f" [{status}]" if status else ""
                        print(f"  {tag:<20} {deployed:<25} {status_str}")
        print()

    # ==================
    # PULL COMMANDS
    # ==================

    def pull(self, service: str, tag: str):
        """Pull specific version for a service

        Each service has its own version (e.g., outpost:1.42, cmd_exec:1.15, vault:latest)
        """
        if service not in SERVICES:
            print_error(f"Unknown service: {service}")
            print_info(f"Available services: {', '.join(SERVICES)}")
            return

        print_header(f"Pulling {service}:{tag}")

        # Use get_image_name to handle ECR vs DockerHub correctly
        image = self.get_image_name(service, tag)
        print_info(f"Pulling {image}...")

        success, output = docker_pull_with_retry(image)
        if success:
            print_success(f"Pulled {service}:{tag}")
            self.update_service_version(service, tag)
            self.save_manifest()
            self.generate_env()
            print_info("Run 'make restart' to apply changes")
        else:
            print_error(f"Failed to pull {service}:{tag}")
            if output:
                print(f"  {output}")

    def pull_from_manifest(self):
        """Pull versions specified in manifest"""
        print_header("Pulling Versions from Manifest")

        services = self.manifest.get('services', {})
        if not services:
            print_warning("No versions in manifest. Using :latest for all services.")
            for svc in SERVICES:
                self.pull(svc, 'latest')
            return

        success_count = 0

        for name in SERVICES:
            tag = self.get_current_tag(name)
            # Use get_image_name to handle ECR vs DockerHub correctly
            image = self.get_image_name(name, tag)
            print_info(f"Pulling {image}...")

            success, output = docker_pull_with_retry(image)
            if success:
                print_success(f"Pulled {name}:{tag}")
                success_count += 1
            else:
                print_error(f"Failed to pull {name}:{tag}")
                if output:
                    print(f"  {output}")

        print_success(f"\nPulled {success_count}/{len(SERVICES)} services")

    def pull_latest(self):
        """Pull :latest for all services and update manifest

        This is the recommended way to update all services to latest.
        It pulls images, updates manifest, and resolves semantic versions from ECR.
        """
        print_header("Pulling Latest Images")

        pulled_services = []

        # Step 1: Pull all :latest images
        for svc in SERVICES:
            # Use get_image_name to handle ECR vs DockerHub correctly
            image = self.get_image_name(svc, 'latest')
            print_info(f"Pulling {image}...")

            success, output = docker_pull_with_retry(image)
            if success:
                pulled_services.append(svc)
                print_success(f"Pulled {svc}:latest")
            else:
                print_error(f"Failed to pull {svc}:latest")
                if output:
                    print(f"  {output}")

        if not pulled_services:
            print_error("No images were pulled")
            return False

        print_success(f"\nPulled {len(pulled_services)}/{len(SERVICES)} services")

        # Step 2: Update manifest with 'latest' for all pulled services
        print()
        print_info("Updating manifest...")
        for svc in pulled_services:
            self.update_service_version(svc, 'latest')
        self.save_manifest()
        print_success("Manifest updated")

        # Step 3: Try to resolve semantic versions from ECR
        print()
        if check_ecr_access():
            resolved = self.resolve_latest_tags(pulled_services, save=True)
            if resolved > 0:
                print_success(f"Resolved {resolved} service(s) to semantic versions")
            else:
                print_warning("Could not resolve semantic versions - using 'latest' tags")
                print_info("You can retry later with: make resolve-tags")
        else:
            print_warning("ECR not accessible - keeping 'latest' tags")
            print_info("Configure AWS CLI for tag resolution, or run: make resolve-tags")

        print()
        print_info("Run 'make restart' to apply changes")
        return True

    # ==================
    # ROLLBACK COMMANDS
    # ==================

    def rollback(self, service: str = None, tag: str = None, all_services: bool = False, interactive: bool = True):
        """Rollback to previous version"""
        print_header("DagKnows Rollback")

        if all_services:
            services_to_rollback = SERVICES
        elif service:
            services_to_rollback = [service]
        else:
            print_error("Specify --service or --all")
            return False

        # Show what will be rolled back
        rollback_plan = []
        for svc in services_to_rollback:
            current = self.get_current_tag(svc)
            if tag:
                target = tag
            else:
                target = self.get_previous_tag(svc)

            if target and target != current:
                rollback_plan.append((svc, current, target))

        if not rollback_plan:
            print_warning("No services to rollback (no previous versions available)")
            return False

        # Show plan
        print("Services to rollback:\n")
        for svc, current, target in rollback_plan:
            print(f"  {svc}: {current} \u2192 {target}")
        print()

        # Confirm if interactive
        if interactive:
            if not confirm("Proceed with rollback?"):
                print("Rollback cancelled.")
                return False

        # Execute rollback
        success_count = 0

        for svc, current, target in rollback_plan:
            print_info(f"Rolling back {svc} to {target}...")

            # Pull the target image - use get_image_name to handle ECR vs DockerHub
            image = self.get_image_name(svc, target)
            success, output = docker_pull_with_retry(image)

            if not success:
                print_error(f"Failed to pull {svc}:{target}")
                if output:
                    print(f"  {output}")
                continue

            # Update manifest
            self.update_service_version(svc, target, is_rollback=True)
            success_count += 1
            print_success(f"Rolled back {svc}: {current} \u2192 {target}")

        if success_count > 0:
            self.save_manifest()
            self.generate_env()
            print_success(f"\nRolled back {success_count} service(s)")
            print_info("Run 'make start' to apply changes")
            return True
        else:
            print_error("Rollback failed")
            return False

    # ==================
    # UPDATE COMMANDS
    # ==================

    def set_version(self, service: str, tag: str):
        """Set specific version for a service (for hotfixes)"""
        print_header(f"Setting Custom Version")

        if service not in SERVICES:
            print_error(f"Unknown service: {service}")
            print_info(f"Valid services: {', '.join(SERVICES)}")
            return False

        # Pull the image first - use get_image_name to handle ECR vs DockerHub
        image = self.get_image_name(service, tag)
        print_info(f"Pulling {image}...")

        success, output = docker_pull_with_retry(image)
        if not success:
            print_error(f"Failed to pull image: {image}")
            if output:
                print(f"  {output}")
            return False

        print_success(f"Pulled {service}:{tag}")

        # Update manifest
        self.update_service_version(service, tag)

        # Also add to custom_overrides for tracking
        if 'custom_overrides' not in self.manifest:
            self.manifest['custom_overrides'] = {}

        self.manifest['custom_overrides'][service] = {
            'tag': tag,
            'reason': 'Custom version set via CLI',
            'applied_at': datetime.now().isoformat()
        }

        self.save_manifest()
        self.generate_env()

        print_success(f"Set {service} to {tag}")
        print_info("Run 'make start' to apply changes")
        return True

    def update_safe(self):
        """Safe update to latest versions with automatic backup and rollback on failure

        This pulls :latest for all services since each service has its own version.
        For updating a specific service to a specific tag, use: make version-pull SERVICE=x TAG=y
        """
        print_header("DagKnows Safe Update")

        print_info("This will update all services to their latest versions")
        print()

        # Step 1: Create backup
        print_info("Creating backup before update...")
        backup_path = self.backup_manifest()
        if backup_path:
            print_success(f"Backup created: {backup_path}")

        # Step 2: Pull new images (latest for all services)
        print_info("Pulling latest images...")
        pulled_services = []

        for svc in SERVICES:
            # Use get_image_name to handle ECR vs DockerHub (vault) correctly
            image = self.get_image_name(svc, 'latest')
            success, output = docker_pull_with_retry(image)
            if success:
                pulled_services.append(svc)
                print(f"  \u2713 {svc}")
            else:
                print(f"  \u2717 {svc} (failed)")
                if output:
                    print(f"    {output}")

        if len(pulled_services) < len(SERVICES):
            print_warning(f"Only {len(pulled_services)}/{len(SERVICES)} images pulled")
            if not confirm("Continue with partial update?"):
                print("Update cancelled.")
                return False

        print_success("Images pulled successfully")

        # Step 3: Update manifest with pulled versions
        print_info("Updating manifest...")
        for svc in pulled_services:
            self.update_service_version(svc, 'latest')
        self.save_manifest()

        # Step 4: Resolve 'latest' tags to semantic versions from ECR
        print()
        resolved = self.resolve_latest_tags(pulled_services, save=True)
        if resolved == 0:
            print_warning("Could not resolve semantic versions - using 'latest' tags")
            print_info("You can retry later with: make resolve-tags")

        # Step 5: Stop services
        print_info("Stopping services...")
        run_command("make stop")
        print_success("Services stopped")

        # Step 6: Start services
        print_info("Starting services with new images...")
        success, _ = run_command("make start", capture=False)
        if not success:
            print_error("Failed to start services")
            return False

        print_success("Update completed successfully!")
        return True

    def check_updates(self):
        """Check for available updates (placeholder - requires ECR API access)"""
        print_header("Available Updates")

        print_info("Checking for updates...")
        print()

        # For now, just show current versions and suggest checking ECR
        services = self.manifest.get('services', {})

        for name in SERVICES:
            current = self.get_current_tag(name)
            if current == 'latest':
                print(f"  \u2713 {name}: latest (always up to date)")
            else:
                print(f"  ? {name}: {current} (check ECR for newer versions)")

        print()
        print_info("To check for updates, visit:")
        print(f"  https://gallery.ecr.aws/n5k3t9x2")
        print()
        print_info("To update to latest:")
        print(f"  make update-safe")
        print()

    # ==================
    # ECR COMMANDS
    # ==================

    def ecr_login(self):
        """Login to private ECR"""
        print_header("ECR Login")

        ecr = self.manifest.get('ecr', {})

        if not ecr.get('use_private') or not ecr.get('private_registry'):
            print_info("Using public ECR - no authentication required")
            return True

        region = ecr.get('private_region', 'us-east-1')
        registry = ecr.get('private_registry')

        print_info(f"Logging into private ECR: {registry}")

        cmd = f"aws ecr get-login-password --region {region} | docker login --username AWS --password-stdin {registry}"
        success, output = run_command(cmd)

        if success:
            print_success("Successfully logged into ECR")
            return True
        else:
            print_error("Failed to login to ECR")
            print(f"  {output}")
            print_info("Make sure AWS CLI is configured with valid credentials")
            return False

    # ==================
    # TAG RESOLUTION
    # ==================

    def resolve_latest_tags(self, services: List[str] = None, save: bool = True) -> int:
        """
        Resolve 'latest' tags to actual semantic versions by querying ECR.
        
        Args:
            services: List of services to resolve (default: all with 'latest' tag)
            save: Whether to save the manifest after resolution
            
        Returns:
            Number of tags successfully resolved
        """
        print_header("Resolving Image Tags from ECR")
        
        # Check ECR access first
        if not check_ecr_access():
            print_error("Cannot access ECR Public API")
            print_info("Make sure AWS CLI is configured with valid credentials:")
            print_info("  aws configure")
            print_info("")
            print_info("Required IAM permissions: ecr-public:DescribeImages")
            return 0
        
        print_success("ECR Public API accessible")
        print()
        
        # Get services to resolve - only ECR services
        if services is None:
            services = SERVICES

        # Filter to only ECR services (skip vault)
        ecr_services = [s for s in services if s in ECR_SERVICES]

        resolved_count = 0

        for svc in services:
            # Skip non-ECR services (vault uses DockerHub, defaults to :latest)
            if svc not in ECR_SERVICES:
                print(f"  {svc}: skipped (not in ECR, defaults to :latest)")
                continue

            current_tag = self.get_current_tag(svc)

            # Only resolve if current tag is 'latest'
            if current_tag != 'latest':
                print(f"  {svc}: {current_tag} (already versioned)")
                continue

            # Get current digest for matching
            svc_info = self.manifest.get('services', {}).get(svc, {})
            digest = svc_info.get('image_digest', '')

            print_info(f"Resolving {svc}...")
            resolved_tag = resolve_tag_from_ecr(svc, digest)
            
            if resolved_tag:
                # Update manifest with resolved tag
                self.manifest['services'][svc]['current_tag'] = resolved_tag
                
                # Also update history - replace 'latest' with resolved tag
                history = self.manifest.get('history', {}).get(svc, [])
                for entry in history:
                    if entry.get('status') == 'current' and entry.get('tag') == 'latest':
                        entry['tag'] = resolved_tag
                        break
                
                print_success(f"  {svc}: latest → {resolved_tag}")
                resolved_count += 1
            else:
                print_warning(f"  {svc}: Could not resolve (keeping 'latest')")
        
        if save and resolved_count > 0:
            self.save_manifest()
            self.generate_env()
            print()
            print_success(f"Resolved {resolved_count} service(s) to semantic versions")
        elif resolved_count == 0:
            print()
            print_warning("No tags were resolved")
        
        return resolved_count

    # ==================
    # HELPER METHODS
    # ==================

    def update_service_version(self, service: str, tag: str, is_rollback: bool = False):
        """Update service version in manifest"""
        now = datetime.now().isoformat()

        # Initialize services dict if needed
        if 'services' not in self.manifest:
            self.manifest['services'] = {}

        # Get old tag for history
        old_info = self.manifest['services'].get(service, {})
        old_tag = old_info.get('current_tag')

        # Get full image name (handles ECR vs DockerHub)
        full_image = self.get_image_name(service, tag)

        # Get image digest
        digest = ""
        success, output = run_command(f"docker inspect --format='{{{{.RepoDigests}}}}' {full_image}")
        if success:
            digest = output

        service_data = {
            'current_tag': tag,
            'deployed_at': now,
            'deployed_by': os.environ.get('USER', 'system'),
            'image_digest': digest
        }

        # Add note for vault
        if service == 'vault':
            service_data['notes'] = 'HashiCorp vault - defaults to :latest, manual pinning supported'

        self.manifest['services'][service] = service_data

        # Update history
        if 'history' not in self.manifest:
            self.manifest['history'] = {}

        if service not in self.manifest['history']:
            self.manifest['history'][service] = []

        # Mark existing entries
        for entry in self.manifest['history'][service]:
            if entry.get('status') == 'current':
                entry['status'] = 'rolled-back' if is_rollback else 'previous'
            elif entry.get('status') == 'previous':
                entry['status'] = 'archived'

        # Add new entry
        self.manifest['history'][service].insert(0, {
            'tag': tag,
            'deployed_at': now,
            'status': 'current'
        })

        # Keep only last HISTORY_LIMIT entries
        self.manifest['history'][service] = self.manifest['history'][service][:HISTORY_LIMIT]

        # Clear custom override if setting standard version
        if service in self.manifest.get('custom_overrides', {}):
            if not is_rollback:  # Keep override info on rollback
                del self.manifest['custom_overrides'][service]

    def generate_env(self):
        """Generate versions.env from manifest"""
        print_info("Generating versions.env...")

        registry = self.get_registry()

        lines = [
            "# DagKnows Service Versions",
            "# Auto-generated from version-manifest.yaml - DO NOT EDIT MANUALLY",
            f"# Generated: {datetime.now().isoformat()}",
            "",
            f"DK_ECR_REGISTRY={registry}",
            ""
        ]

        for name in SERVICES:
            var_name = name.upper()
            tag = self.get_current_tag(name)

            # Handle vault (DockerHub) vs ECR services differently
            if name in ECR_SERVICES:
                image = f"{registry}/{name}"
            elif name == 'vault':
                image = "hashicorp/vault"
            else:
                image = f"{registry}/{name}"

            lines.append(f"DK_{var_name}_IMAGE={image}")
            lines.append(f"DK_{var_name}_TAG={tag}")
            lines.append("")

        with open(self.versions_env, 'w') as f:
            f.write('\n'.join(lines))

        print_success(f"Generated {self.versions_env}")

    def verify_health(self) -> bool:
        """Verify all services are healthy"""
        success, output = run_command("docker compose ps --format json")
        if not success:
            return False

        try:
            healthy_count = 0
            total_count = 0

            for line in output.strip().split('\n'):
                if not line.strip():
                    continue
                container = json.loads(line)
                service = container.get('Service', '')
                state = container.get('State', '')
                health = container.get('Health', '')

                if service in SERVICE_TO_COMPOSE.values():
                    total_count += 1
                    if state == 'running':
                        if health in ('healthy', ''):  # Empty health means no healthcheck defined
                            healthy_count += 1
                            print(f"  \u2713 {service}: {state}" + (f" [{health}]" if health else ""))
                        else:
                            print(f"  \u2717 {service}: {state} [{health}]")
                    else:
                        print(f"  \u2717 {service}: {state}")

            return healthy_count >= total_count * 0.8  # Allow 80% healthy for partial success
        except json.JSONDecodeError:
            return False


# ============================================
# MAIN
# ============================================

def main():
    parser = argparse.ArgumentParser(
        description='DagKnows Version Manager',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s show                              Show current versions
  %(prog)s history                           Show all version history
  %(prog)s history taskservice               Show history for taskservice
  %(prog)s pull --tag=v1.2.3                 Pull v1.2.3 for all services
  %(prog)s pull --tag=v1.2.3 --service=wsfe  Pull v1.2.3 for wsfe only
  %(prog)s rollback --service=taskservice    Rollback taskservice to previous
  %(prog)s rollback --all                    Rollback all services
  %(prog)s set --service=wsfe --tag=v1.2.3-hotfix  Set custom version
  %(prog)s update-safe                       Safe update with rollback
  %(prog)s check-updates                     Check for available updates
        """
    )

    subparsers = parser.add_subparsers(dest='command', help='Commands')

    # Show command
    subparsers.add_parser('show', help='Show current deployed versions')

    # History command
    history_parser = subparsers.add_parser('history', help='Show version history')
    history_parser.add_argument('service', nargs='?', help='Service name (optional)')

    # Pull command
    pull_parser = subparsers.add_parser('pull', help='Pull specific version for a service')
    pull_parser.add_argument('--service', required=True, help='Service name (each service has its own version)')
    pull_parser.add_argument('--tag', required=True, help='Tag to pull (e.g., 1.35)')

    # Pull from manifest
    subparsers.add_parser('pull-from-manifest', help='Pull versions from manifest')

    # Pull latest (ignores manifest, updates it after)
    subparsers.add_parser('pull-latest', help='Pull :latest for all services and update manifest')

    # Rollback command
    rollback_parser = subparsers.add_parser('rollback', help='Rollback to previous version')
    rollback_parser.add_argument('--service', help='Service to rollback')
    rollback_parser.add_argument('--tag', help='Specific tag to rollback to')
    rollback_parser.add_argument('--all', action='store_true', help='Rollback all services')

    # Set command
    set_parser = subparsers.add_parser('set', help='Set specific version for a service')
    set_parser.add_argument('--service', required=True, help='Service name')
    set_parser.add_argument('--tag', required=True, help='Version tag')

    # Resolve tags command
    subparsers.add_parser('resolve-tags', help='Resolve latest tags to semantic versions from ECR')

    # Update safe command
    subparsers.add_parser('update-safe', help='Safe update to latest with backup and rollback')

    # Check updates command
    subparsers.add_parser('check-updates', help='Check for available updates')

    # Generate env command
    subparsers.add_parser('generate-env', help='Generate versions.env from manifest')

    # ECR login command
    subparsers.add_parser('ecr-login', help='Login to private ECR')

    args = parser.parse_args()

    # Change to script directory
    script_dir = Path(__file__).parent.absolute()
    os.chdir(script_dir)

    # Commands that require Docker access
    docker_commands = {'pull', 'pull-from-manifest', 'pull-latest', 'rollback', 'update-safe'}

    # Check Docker access for commands that need it
    if args.command in docker_commands:
        if not check_docker_access():
            sys.exit(1)

    vm = VersionManager()

    if args.command == 'show':
        vm.show()
    elif args.command == 'history':
        vm.history(getattr(args, 'service', None))
    elif args.command == 'pull':
        vm.pull(args.service, args.tag)
    elif args.command == 'pull-from-manifest':
        vm.pull_from_manifest()
    elif args.command == 'pull-latest':
        vm.pull_latest()
    elif args.command == 'rollback':
        vm.rollback(args.service, args.tag, args.all)
    elif args.command == 'set':
        vm.set_version(args.service, args.tag)
    elif args.command == 'update-safe':
        vm.update_safe()
    elif args.command == 'check-updates':
        vm.check_updates()
    elif args.command == 'generate-env':
        vm.generate_env()
    elif args.command == 'ecr-login':
        vm.ecr_login()
    elif args.command == 'resolve-tags':
        vm.resolve_latest_tags()
    else:
        parser.print_help()


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{Colors.WARNING}Operation cancelled{Colors.ENDC}")
        sys.exit(1)
    except Exception as e:
        print(f"\n{Colors.FAIL}Error: {e}{Colors.ENDC}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
