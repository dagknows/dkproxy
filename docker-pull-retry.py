#!/usr/bin/env python3
"""
Docker Pull Wrapper with Auto-Retry for Expired Tokens

This script wraps 'docker pull' to automatically handle expired Docker
credentials for public ECR repositories. If an expired token is detected,
it clears the stale credential and retries the pull.

Automatically handles docker group permission issues by using 'sg docker'
if the docker group is not active in the current session.

Usage:
    python3 docker-pull-retry.py <image-name>

Example:
    python3 docker-pull-retry.py public.ecr.aws/n5k3t9x2/outpost:latest
"""

import subprocess
import sys
from typing import Tuple

# Global flag to track if we need sg docker wrapper
USE_SG_DOCKER = False


def run_command(cmd: str) -> Tuple[bool, str]:
    """Run a shell command and return success status and output"""
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=300
        )
        # Combine stdout and stderr
        output = result.stdout.strip()
        if result.stderr.strip():
            output = f"{output}\n{result.stderr.strip()}" if output else result.stderr.strip()
        return result.returncode == 0, output
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
            print("ℹ Using 'sg docker' for Docker commands (docker group not active in session)", file=sys.stderr)
            return True
        else:
            # Even sg docker didn't work
            print("✗ Docker is running but you don't have permission to access it", file=sys.stderr)
            print("  Make sure your user is in the docker group: sudo usermod -aG docker $USER", file=sys.stderr)
            print("  Then log out and back in, or run: newgrp docker", file=sys.stderr)
            return False
    else:
        # Docker daemon not running
        print("✗ Docker daemon is not running", file=sys.stderr)
        print("  Start Docker with: sudo systemctl start docker", file=sys.stderr)
        return False


def docker_command(cmd: str) -> str:
    """Wrap a docker command with sg docker if needed."""
    global USE_SG_DOCKER
    if USE_SG_DOCKER:
        # Escape single quotes in the command
        escaped_cmd = cmd.replace("'", "'\\''")
        return f"sg docker -c '{escaped_cmd}'"
    return cmd


def clear_stale_ecr_credentials(registry: str) -> bool:
    """Clear stale Docker credentials for public ECR"""
    if 'public.ecr.aws' in registry:
        print("⚠ Clearing stale Docker credentials for public.ecr.aws...", file=sys.stderr)
        run_command(docker_command("docker logout public.ecr.aws") + " 2>&1")
        return True
    return False


def docker_pull_with_retry(image: str, max_retries: int = 2) -> bool:
    """
    Pull a Docker image with automatic retry on expired token errors.
    Uses sg docker wrapper if needed.

    Returns:
        True if successful, False otherwise
    """
    for attempt in range(max_retries):
        cmd = docker_command(f"docker pull {image}")
        success, output = run_command(cmd)
        
        if success:
            # Print output to stdout (Docker's normal output)
            if output:
                print(output)
            return True
        
        # Check if error is due to expired token
        if "authorization token has expired" in output.lower() or "reauthenticate" in output.lower():
            if attempt < max_retries - 1:
                # Extract registry from image
                if 'public.ecr.aws' in image:
                    clear_stale_ecr_credentials('public.ecr.aws')
                    print("ℹ Retrying pull...", file=sys.stderr)
                    continue
        
        # For other errors or final attempt, print error and fail
        print(f"✗ Failed to pull {image}", file=sys.stderr)
        if output:
            print(f"  {output}", file=sys.stderr)
        return False
    
    return False


def main():
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <image-name>", file=sys.stderr)
        print(f"Example: {sys.argv[0]} public.ecr.aws/n5k3t9x2/outpost:latest", file=sys.stderr)
        sys.exit(1)

    # Check Docker access (sets USE_SG_DOCKER if needed)
    if not check_docker_access():
        sys.exit(1)

    image = sys.argv[1]
    success = docker_pull_with_retry(image)
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
