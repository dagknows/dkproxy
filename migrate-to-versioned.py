#!/usr/bin/env python3
"""
DagKnows Proxy Migration Script
Converts existing dkproxy deployments to use version tracking.

This interactive wizard will:
1. Detect currently running container versions
2. Create a version-manifest.yaml from current state
3. Generate versions.env for docker-compose
4. Verify the configuration works

NOTE: vault service defaults to :latest (HashiCorp-controlled)
      ECR services (outpost, cmd_exec) will have versions resolved if possible

Usage:
    python3 migrate-to-versioned.py
"""

import json
import os
import shutil
import subprocess
import sys
import yaml
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Tuple


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

# Map docker-compose service names to manifest service names
COMPOSE_TO_SERVICE = {
    'outpost': 'outpost',
    'cmd-exec': 'cmd_exec',  # Note: hyphen in compose, underscore in manifest
    'vault': 'vault'
}

DEFAULT_REGISTRY = 'public.ecr.aws/n5k3t9x2'


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


def print_step(text: str):
    """Print a step indicator"""
    print(f"\n{Colors.OKBLUE}{Colors.BOLD}>>> {text}{Colors.ENDC}")


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


# ============================================
# UTILITIES
# ============================================

def run_command(cmd: str, capture: bool = True, timeout: int = 60) -> Tuple[bool, str]:
    """Run a shell command and return success status and output"""
    try:
        if capture:
            result = subprocess.run(
                cmd, shell=True, capture_output=True, text=True, timeout=timeout
            )
            return result.returncode == 0, result.stdout.strip()
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
    try:
        response = input(prompt + suffix).strip().lower()
        if not response:
            return default
        return response in ('yes', 'y')
    except (EOFError, KeyboardInterrupt):
        print()
        return False


def backup_file(filepath: str) -> Optional[str]:
    """Create a timestamped backup of a file"""
    if os.path.exists(filepath):
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        backup_path = f"{filepath}.backup.{timestamp}"
        shutil.copy(filepath, backup_path)
        return backup_path
    return None


def restore_backup(filepath: str, backup_path: str):
    """Restore a file from backup"""
    if os.path.exists(backup_path):
        shutil.copy(backup_path, filepath)


# ============================================
# MIGRATION FUNCTIONS
# ============================================

def resolve_latest_tag_from_ecr(service_name: str, digest: str, registry: str = DEFAULT_REGISTRY) -> Optional[str]:
    """
    Query ECR to find semantic version tag for a digest when container uses :latest

    NOTE: Only works for ECR services (outpost, cmd_exec). Skips vault (DockerHub).

    Args:
        service_name: Name of the service (e.g., 'outpost', 'cmd_exec')
        digest: Image digest (e.g., 'sha256:abc123...')
        registry: ECR registry URL

    Returns:
        Semantic version tag (e.g., '1.42') or None if unable to resolve
    """
    # Skip non-ECR services (vault uses DockerHub, defaults to :latest)
    if service_name not in ECR_SERVICES:
        return None

    # Extract registry and repository info
    if 'public.ecr.aws' in registry:
        # For public ECR, we need to query using AWS CLI
        # The registry alias is the last part of the registry URL (e.g., 'n5k3t9x2' from 'public.ecr.aws/n5k3t9x2')
        parts = registry.rstrip('/').split('/')
        registry_alias = parts[-1] if len(parts) > 1 else None
        
        if not registry_alias:
            print_warning(f"Could not parse registry alias from {registry}")
            return None
        
        # Query AWS ECR Public API for image details
        # Note: This requires AWS CLI configured with valid credentials AND
        # you must be the owner of the registry or have explicit permissions
        repo_name = service_name
        
        # Try the describe-images command for public ECR
        success, output = run_command(
            f"aws ecr-public describe-images --repository-name {repo_name} "
            f"--region us-east-1 --output json 2>&1",
            timeout=30
        )

        if success:
            try:
                ecr_data = json.loads(output)
                # Find images with matching digest
                for image_detail in ecr_data.get('imageDetails', []):
                    image_digest = image_detail.get('imageDigest', '')
                    # Match digest - handle both full and short digest formats
                    if digest and (image_digest == digest or digest.endswith(image_digest) or image_digest.endswith(digest.split(':')[-1] if ':' in digest else digest)):
                        # Get tags for this image, prefer semantic versions over 'latest'
                        tags = image_detail.get('imageTags', [])
                        semantic_tags = [t for t in tags if t != 'latest' and not t.startswith('sha')]
                        if semantic_tags:
                            # Sort to get the most recent semantic version
                            try:
                                semantic_tags.sort(key=lambda x: [int(p) if p.isdigit() else p for p in x.replace('-', '.').split('.')], reverse=True)
                            except (ValueError, AttributeError):
                                pass
                            return semantic_tags[0]
                
                # If we couldn't match by digest, try to find the image tagged as 'latest'
                for image_detail in ecr_data.get('imageDetails', []):
                    tags = image_detail.get('imageTags', [])
                    if 'latest' in tags:
                        semantic_tags = [t for t in tags if t != 'latest' and not t.startswith('sha')]
                        if semantic_tags:
                            try:
                                semantic_tags.sort(key=lambda x: [int(p) if p.isdigit() else p for p in x.replace('-', '.').split('.')], reverse=True)
                            except (ValueError, AttributeError):
                                pass
                            return semantic_tags[0]
                            
            except json.JSONDecodeError:
                print_warning(f"Failed to parse ECR response for {repo_name}")
            except KeyError:
                pass
        else:
            # AWS CLI failed - show appropriate message
            if "could not be found" in output.lower() or "repositorynotfound" in output.lower():
                print_warning(f"Repository {repo_name} not found in your ECR account")
            elif "accessdenied" in output.lower() or "not authorized" in output.lower():
                print_warning(f"Not authorized to query ECR for {repo_name}")
                print_info("  Note: You need to be the registry owner to query ECR Public API")
            elif "unable to locate credentials" in output.lower():
                print_warning("AWS credentials not configured")
            else:
                print_warning(f"Unable to query ECR for {repo_name} - will use 'latest'")

    return None


def get_running_images() -> Dict:
    """Get currently running container images and their versions"""
    images = {}

    # Try docker compose ps with JSON format
    success, output = run_command("docker compose ps --format json")
    if not success or not output.strip():
        return images

    try:
        for line in output.strip().split('\n'):
            if not line.strip():
                continue
            container = json.loads(line)
            compose_service = container.get('Service', '')

            if compose_service not in COMPOSE_TO_SERVICE:
                continue

            service_name = COMPOSE_TO_SERVICE[compose_service]
            container_id = container.get('ID', '')

            if not container_id:
                continue

            # Get image info from docker inspect
            success, inspect_output = run_command(f"docker inspect {container_id}")
            if success:
                inspect_data = json.loads(inspect_output)
                if inspect_data:
                    image = inspect_data[0].get('Config', {}).get('Image', '')
                    digest = inspect_data[0].get('Image', '')

                    # Parse image:tag
                    tag = 'latest'
                    image_name = image
                    if ':' in image:
                        parts = image.rsplit(':', 1)
                        image_name = parts[0]
                        tag = parts[1]

                    # If tag is 'latest', try to resolve actual version from ECR
                    if tag == 'latest' and digest:
                        print_info(f"Detected 'latest' tag for {service_name}, querying ECR for actual version...")
                        resolved_tag = resolve_latest_tag_from_ecr(service_name, digest, image_name)
                        if resolved_tag:
                            tag = resolved_tag
                            print_success(f"Resolved {service_name}: latest → {tag}")
                        else:
                            print_warning(f"Could not resolve version for {service_name}, using 'latest'")

                    images[service_name] = {
                        'image': image_name,
                        'tag': tag,
                        'digest': digest,
                        'container_id': container_id
                    }
    except json.JSONDecodeError:
        pass

    return images


def show_current_state(images: Dict):
    """Display detected images"""
    print("\nDetected running containers:\n")

    for service in SERVICES:
        info = images.get(service, {})
        if info:
            tag = info.get('tag', 'unknown')
            print(f"  {Colors.OKGREEN}\u2713{Colors.ENDC} {service:.<40} {tag}")
        else:
            print(f"  {Colors.WARNING}?{Colors.ENDC} {service:.<40} (not running)")


def create_manifest_from_current(images: Dict, customer_id: str = '', deployment_id: str = '', proxy_location: str = '') -> Dict:
    """Create a version manifest from current running images"""
    import socket
    now = datetime.now().isoformat()

    manifest = {
        'schema_version': '1.0',
        'deployment_id': deployment_id or f'dkproxy-{socket.gethostname()}',
        'customer_id': customer_id,
        'proxy_location': proxy_location,  # NEW: Track proxy location for distributed deployments
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

    for service in SERVICES:
        info = images.get(service, {})
        tag = info.get('tag', 'latest')
        digest = info.get('digest', '')

        service_data = {
            'current_tag': tag,
            'deployed_at': now,
            'deployed_by': 'migration',
            'image_digest': digest
        }

        # Add note for vault
        if service == 'vault':
            service_data['notes'] = 'HashiCorp vault - defaults to :latest, manual pinning supported'

        manifest['services'][service] = service_data

        manifest['history'][service] = [{
            'tag': tag,
            'deployed_at': now,
            'status': 'current'
        }]

    return manifest


def generate_versions_env(manifest: Dict) -> str:
    """Generate versions.env content from manifest"""
    ecr = manifest.get('ecr', {})
    registry = ecr.get('registry', 'public.ecr.aws')
    alias = ecr.get('repository_alias', 'n5k3t9x2')
    full_registry = f"{registry}/{alias}"

    lines = [
        "# DagKnows Proxy Service Versions",
        "# Auto-generated from version-manifest.yaml - DO NOT EDIT MANUALLY",
        f"# Generated: {datetime.now().isoformat()}",
        "",
        "# ECR Services",
        f"DK_ECR_REGISTRY={full_registry}",
        ""
    ]

    services = manifest.get('services', {})
    for name in SERVICES:
        info = services.get(name, {})
        var_name = name.upper()
        tag = info.get('current_tag', 'latest')

        # Handle different registries
        if name in ECR_SERVICES:
            image = f"{full_registry}/{name}"
        elif name == 'vault':
            image = "hashicorp/vault"
            if len(lines) > 0 and not lines[-1].startswith('#'):
                lines.append("")
            lines.append("# DockerHub Services")
        else:
            image = f"{full_registry}/{name}"  # Fallback

        lines.append(f"DK_{var_name}_IMAGE={image}")
        lines.append(f"DK_{var_name}_TAG={tag}")
        lines.append("")

    return '\n'.join(lines)


def verify_config() -> bool:
    """Verify the configuration is valid"""
    # Check manifest exists and is valid YAML
    if not os.path.exists('version-manifest.yaml'):
        print_error("version-manifest.yaml not found")
        return False

    try:
        with open('version-manifest.yaml', 'r') as f:
            manifest = yaml.safe_load(f)
        if not manifest or 'services' not in manifest:
            print_error("Invalid manifest structure")
            return False
        print_success("version-manifest.yaml is valid")
    except yaml.YAMLError as e:
        print_error(f"Invalid YAML: {e}")
        return False

    # Check versions.env exists
    if not os.path.exists('versions.env'):
        print_error("versions.env not found")
        return False
    print_success("versions.env exists")

    # Check docker-compose.yml has variable references
    if os.path.exists('docker-compose.yml'):
        with open('docker-compose.yml', 'r') as f:
            content = f.read()
        if 'DK_REQ_ROUTER_TAG' in content:
            print_success("docker-compose.yml uses version variables")
        else:
            print_warning("docker-compose.yml may need updating to use version variables")

    return True


# ============================================
# MAIN MIGRATION WORKFLOW
# ============================================

def login_to_public_ecr() -> bool:
    """
    Login to public ECR registry for docker commands
    
    Returns:
        True if login successful, False otherwise
    """
    success, output = run_command(
        "aws ecr-public get-login-password --region us-east-1 2>/dev/null | "
        "docker login --username AWS --password-stdin public.ecr.aws 2>&1",
        timeout=30
    )
    return success and "Login Succeeded" in output


def check_aws_cli() -> Tuple[bool, bool]:
    """
    Check if AWS CLI is available and can access ECR Public
    
    Returns:
        Tuple of (aws_cli_available, ecr_public_accessible)
    """
    # Check if AWS CLI is installed
    success, _ = run_command("aws --version", timeout=5)
    if not success:
        return False, False
    
    # Check if we can access ECR Public (test with a simple describe call)
    # Try to describe one of our repositories
    success, output = run_command(
        "aws ecr-public describe-images --repository-name req_router "
        "--region us-east-1 --max-results 1 --output json 2>&1",
        timeout=15
    )
    
    if success:
        return True, True
    
    # Check specific error types
    if "AccessDenied" in output or "not authorized" in output.lower():
        return True, False  # CLI works but no permissions
    if "Unable to locate credentials" in output:
        return True, False  # CLI works but not configured
    if "could not be found" in output.lower() or "RepositoryNotFoundException" in output:
        # Repository not found might mean we don't own this registry
        # but CLI is working - this is expected for public ECR we don't own
        return True, False
    
    return True, False


def migrate():
    """Main migration workflow"""
    print_header("DagKnows Version Migration Wizard")

    print("This wizard will enable version tracking for your DagKnows deployment.")
    print("It will create a version manifest based on your currently running containers.")
    print()

    # Check for AWS CLI (optional)
    aws_available, ecr_accessible = check_aws_cli()
    
    if aws_available and ecr_accessible:
        print_success("AWS CLI detected with ECR Public access - can resolve ':latest' tags to actual versions")
        # Try to login to public ECR for docker commands
        print_info("Logging into public ECR...")
        if login_to_public_ecr():
            print_success("Logged into public.ecr.aws")
        else:
            print_warning("Could not login to public ECR (docker commands may still work)")
    elif aws_available:
        print_success("AWS CLI detected")
        # Try to login to public ECR anyway - might work for pulling
        print_info("Attempting to login to public ECR...")
        if login_to_public_ecr():
            print_success("Logged into public.ecr.aws")
        else:
            print_info("Could not login to public ECR (this is optional)")
        print()
        print_warning("Note: Cannot query ECR Public API to resolve ':latest' to specific versions")
        print_info("This is normal if you don't own the DagKnows ECR registry.")
        print_info("The migration will track versions as 'latest' - you can update later with:")
        print_info("  make version-set SERVICE=taskservice TAG=1.42")
        print()
    else:
        print_warning("AWS CLI not found (optional)")
        print_info("Without AWS CLI, containers using ':latest' will be tracked as 'latest'")
        print_info("You can still manually set versions later with: make version-set SERVICE=x TAG=y")
        print_info("To install: pip install awscli  OR  brew install awscli")
        print()

    # Step 1: Confirm
    if not confirm("This will enable version tracking. Continue?"):
        print("Migration cancelled.")
        return False

    # Step 2: Check if already migrated
    if os.path.exists('version-manifest.yaml'):
        print_warning("version-manifest.yaml already exists!")
        if not confirm("Overwrite existing manifest?"):
            print("Migration cancelled.")
            return False

    # Step 3: Detect current state
    print_step("Detecting current deployment state...")

    images = get_running_images()

    if not images:
        print_warning("No running containers detected.")
        print_info("Make sure services are running with 'make up' before migration.")
        if not confirm("Continue anyway (will use 'latest' for all services)?"):
            print("Migration cancelled.")
            return False
    else:
        show_current_state(images)

        # Check if any services are using 'latest' and inform user
        latest_services = [svc for svc, info in images.items() if info.get('tag') == 'latest']
        if latest_services:
            print()
            print_info("Note: Some services are using 'latest' tag:")
            for svc in latest_services:
                print(f"  - {svc}")
            print()
            print_info("The migration attempted to resolve actual versions from ECR.")
            print_info("If resolution failed, these will be tracked as 'latest' in the manifest.")
            print_info("You can update to specific versions later using: make version-pull TAG=1.35")

    if not confirm("\nCreate manifest from detected images?"):
        print("Migration cancelled.")
        return False

    # Step 4: Get optional deployment info
    print_step("Deployment Information (optional)")

    customer_id = input("Customer ID (press Enter to skip): ").strip()
    deployment_id = input("Deployment ID (press Enter for auto-generated): ").strip()

    # Step 5: Create manifest
    print_step("Creating version-manifest.yaml...")

    manifest = create_manifest_from_current(images, customer_id, deployment_id)

    with open('version-manifest.yaml', 'w') as f:
        yaml.dump(manifest, f, default_flow_style=False, sort_keys=False)

    print_success("Created version-manifest.yaml")

    # Step 6: Generate versions.env
    print_step("Generating versions.env...")

    env_content = generate_versions_env(manifest)
    with open('versions.env', 'w') as f:
        f.write(env_content)

    print_success("Created versions.env")

    # Step 7: Verify
    print_step("Verifying configuration...")

    if verify_config():
        print_success("Migration completed successfully!")
        print()
        print(f"{Colors.BOLD}Next steps:{Colors.ENDC}")
        print("  1. Run 'make version' to see current versions")
        print("  2. Run 'make up' to restart with version tracking")
        print("  3. Run 'make help-version' for all version commands")
        print()
        return True
    else:
        print_error("Migration verification failed!")
        return False


def main():
    """Entry point"""
    # Change to script directory
    script_dir = Path(__file__).parent.absolute()
    os.chdir(script_dir)

    try:
        success = migrate()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print(f"\n{Colors.WARNING}Migration cancelled{Colors.ENDC}")
        sys.exit(1)
    except Exception as e:
        print(f"\n{Colors.FAIL}Error during migration: {e}{Colors.ENDC}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
