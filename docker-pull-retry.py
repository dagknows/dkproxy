#!/usr/bin/env python3
"""
Docker Pull Wrapper with Auto-Retry for Expired Tokens

This script wraps 'docker pull' to automatically handle expired Docker
credentials for public ECR repositories. If an expired token is detected,
it clears the stale credential and retries the pull.

Usage:
    python3 docker-pull-retry.py <image-name>

Example:
    python3 docker-pull-retry.py public.ecr.aws/n5k3t9x2/outpost:latest
"""

import subprocess
import sys
from typing import Tuple


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


def clear_stale_ecr_credentials(registry: str) -> bool:
    """Clear stale Docker credentials for public ECR"""
    if 'public.ecr.aws' in registry:
        print("⚠ Clearing stale Docker credentials for public.ecr.aws...", file=sys.stderr)
        run_command("docker logout public.ecr.aws 2>&1")
        return True
    return False


def docker_pull_with_retry(image: str, max_retries: int = 2) -> bool:
    """
    Pull a Docker image with automatic retry on expired token errors.
    
    Returns:
        True if successful, False otherwise
    """
    for attempt in range(max_retries):
        success, output = run_command(f"docker pull {image}")
        
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
    
    image = sys.argv[1]
    success = docker_pull_with_retry(image)
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
