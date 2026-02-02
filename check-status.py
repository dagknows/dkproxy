#!/usr/bin/env python3
"""
DagKnows Proxy Status Checker
Verifies that the proxy installation is working correctly

Automatically handles docker group permission issues by using 'sg docker'
if the docker group is not active in the current session.
"""

import os
import sys
import subprocess
import json
from typing import Tuple

try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False

# Global flag to track if we need sg docker wrapper
USE_SG_DOCKER = False

# ANSI color codes
class Colors:
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'


def print_header(text):
    print(f"\n{Colors.BOLD}{'='*60}{Colors.ENDC}")
    print(f"{Colors.BOLD}{text:^60}{Colors.ENDC}")
    print(f"{Colors.BOLD}{'='*60}{Colors.ENDC}\n")


def run_command(cmd: str) -> Tuple[bool, str]:
    """Run a shell command and return success status and output"""
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=60
        )
        return result.returncode == 0, result.stdout.strip()
    except subprocess.TimeoutExpired:
        return False, "Command timed out"
    except Exception as e:
        return False, str(e)


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
            print(f"  {Colors.WARNING}Using 'sg docker' (docker group not active){Colors.ENDC}")
            return True
        else:
            # Even sg docker didn't work
            print(f"  {Colors.FAIL}Docker permission denied{Colors.ENDC}")
            print(f"  Make sure you're in docker group: sudo usermod -aG docker $USER")
            print(f"  Then: newgrp docker (or logout/login)")
            return False
    else:
        # Docker daemon not running
        print(f"  {Colors.FAIL}Docker daemon not running{Colors.ENDC}")
        print(f"  Start with: sudo systemctl start docker")
        return False


def docker_command(cmd: str) -> str:
    """Wrap a docker command with sg docker if needed."""
    global USE_SG_DOCKER
    if USE_SG_DOCKER:
        # Escape single quotes in the command
        escaped_cmd = cmd.replace("'", "'\\''")
        return f"sg docker -c '{escaped_cmd}'"
    return cmd


def check_versions():
    """Check proxy service versions"""
    print_header("Proxy Versions")

    manifest_file = 'version-manifest.yaml'

    if not os.path.exists(manifest_file):
        print(f"  {Colors.WARNING}Version tracking not enabled{Colors.ENDC}")
        print(f"  Run: make migrate-versions")
        print()
        return False

    if YAML_AVAILABLE:
        with open(manifest_file, 'r') as f:
            manifest = yaml.safe_load(f)

        deployment_id = manifest.get('deployment_id', 'unknown')
        proxy_location = manifest.get('proxy_location', 'unknown')

        print(f"  Deployment: {deployment_id}")
        print(f"  Location: {proxy_location}")
        print()

        for name, info in manifest.get('services', {}).items():
            tag = info.get('current_tag', 'unknown')
            deployed = info.get('deployed_at', '')[:10]

            # Check for override
            override = manifest.get('custom_overrides', {}).get(name, {})
            if override.get('tag'):
                tag = override['tag']
                print(f"  ✓ {name:.<30} {tag:<15} {Colors.WARNING}[custom]{Colors.ENDC}")
            else:
                print(f"  ✓ {name:.<30} {tag:<15} ({deployed})")

        return True
    else:
        print(f"  {Colors.WARNING}YAML module not available{Colors.ENDC}")
        print(f"  Install: pip install pyyaml")
        print(f"  Or run: make version")
        return True


def check_containers():
    """Check proxy container status"""
    print_header("Container Status")

    cmd = docker_command("docker compose ps --format json")
    result = subprocess.run(
        cmd,
        shell=True, capture_output=True, text=True
    )

    if result.returncode != 0 or not result.stdout.strip():
        print(f"  {Colors.FAIL}No containers running{Colors.ENDC}")
        print(f"  Run: make start")
        return False

    # Load versions
    versions = {}
    if os.path.exists('version-manifest.yaml') and YAML_AVAILABLE:
        with open('version-manifest.yaml') as f:
            manifest = yaml.safe_load(f)
            for svc, info in manifest.get('services', {}).items():
                versions[svc] = info.get('current_tag', '?')

    # Parse containers
    for line in result.stdout.strip().split('\n'):
        if not line.strip():
            continue

        container = json.loads(line)
        service = container.get('Service', '').replace('-', '_')
        state = container.get('State', '')

        version = versions.get(service, '?')
        version_str = f" ({version})" if version != '?' else ""

        status_ok = state == 'running'
        symbol = f"{Colors.OKGREEN}✓{Colors.ENDC}" if status_ok else f"{Colors.FAIL}✗{Colors.ENDC}"

        print(f"  {symbol} {service}{version_str:.<35} {state}")

    return True


def main():
    print_header("DagKnows Proxy Status Check")

    # Change to script directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)

    # Check Docker access (sets USE_SG_DOCKER if needed)
    if not check_docker_access():
        sys.exit(1)

    checks = {}
    checks['containers'] = check_containers()
    checks['versions'] = check_versions()

    print()
    if all(checks.values()):
        print(f"{Colors.OKGREEN}Proxy is operational!{Colors.ENDC}\n")
        sys.exit(0)
    else:
        print(f"{Colors.WARNING}Some checks failed{Colors.ENDC}\n")
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{Colors.WARNING}Check interrupted{Colors.ENDC}")
        sys.exit(1)
    except Exception as e:
        print(f"\n{Colors.FAIL}Error during status check: {e}{Colors.ENDC}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
