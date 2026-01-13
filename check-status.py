#!/usr/bin/env python3
"""
DagKnows Proxy Status Checker
Verifies that the proxy installation is working correctly
"""

import os
import sys
import subprocess
import json

try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False

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

    result = subprocess.run(
        "docker compose ps --format json",
        shell=True, capture_output=True, text=True
    )

    if result.returncode != 0 or not result.stdout.strip():
        print(f"  {Colors.FAIL}No containers running{Colors.ENDC}")
        print(f"  Run: make up")
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
