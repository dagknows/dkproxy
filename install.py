#!/usr/bin/env python3
"""
DagKnows Proxy Installation Wizard
Automates the installation process for DagKnows Proxy on docker-compose setups
"""

import os
import sys
import subprocess
import shutil
import getpass
import re
import time
from pathlib import Path

# ANSI color codes for better UX
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def print_header(text):
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'='*60}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{text:^60}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'='*60}{Colors.ENDC}\n")

def print_success(text):
    print(f"{Colors.OKGREEN}✓ {text}{Colors.ENDC}")

def print_error(text):
    print(f"{Colors.FAIL}✗ {text}{Colors.ENDC}")

def print_warning(text):
    print(f"{Colors.WARNING}⚠ {text}{Colors.ENDC}")

def print_info(text):
    print(f"{Colors.OKBLUE}ℹ {text}{Colors.ENDC}")

def run_command(cmd, shell=True, check=True, capture_output=False):
    """Run a shell command and return the result"""
    try:
        if capture_output:
            result = subprocess.run(cmd, shell=shell, check=check, 
                                    capture_output=True, text=True)
            return result.stdout.strip()
        else:
            result = subprocess.run(cmd, shell=shell, check=check)
            return result.returncode == 0
    except subprocess.CalledProcessError:
        if check:
            raise
        return False

def check_installation_state():
    """Check the current state of installation to allow resuming"""
    state = {
        'docker_installed': shutil.which('docker') is not None,
        'make_installed': shutil.which('make') is not None,
        'venv_exists': os.path.exists(os.path.expanduser('~/dkenv')),
        'dk_installed': False,
        'dk_configured': False,
        'proxy_running': False,
        'proxy_name': None
    }
    
    # Check if dk is installed in venv
    if state['venv_exists']:
        dk_path = os.path.expanduser('~/dkenv/bin/dk')
        if os.path.exists(dk_path):
            state['dk_installed'] = True
            
            # Check if dk is configured
            dk_config_path = os.path.expanduser('~/.dk/config')
            if os.path.exists(dk_config_path):
                state['dk_configured'] = True
    
    # Check if docker containers are running
    if state['docker_installed']:
        try:
            # Try regular docker command first
            result = run_command("docker ps --filter name=outpost --filter name=cmd_exec --format '{{.Names}}'", 
                               capture_output=True, check=False)
            if result and ('outpost' in result or 'cmd_exec' in result):
                state['proxy_running'] = True
        except (subprocess.CalledProcessError, Exception):
            # If docker commands fail, try with sg docker
            try:
                result = run_command("sg docker -c \"docker ps --filter name=outpost --filter name=cmd_exec --format '{{.Names}}'\"", 
                                   capture_output=True, check=False)
                if result and ('outpost' in result or 'cmd_exec' in result):
                    state['proxy_running'] = True
            except (subprocess.CalledProcessError, Exception):
                pass
    
    # Try to detect proxy name from .env file
    if os.path.exists('.env'):
        try:
            with open('.env', 'r') as f:
                for line in f:
                    if line.startswith('PROXY_NAME='):
                        state['proxy_name'] = line.split('=', 1)[1].strip()
        except Exception:
            pass
    
    return state

def check_os():
    """Check if the OS is supported"""
    print_info("Checking operating system...")
    
    try:
        with open('/etc/os-release', 'r') as f:
            os_info = f.read().lower()
            if 'ubuntu' in os_info:
                print_success("Ubuntu detected")
                return True
            elif 'amazon linux' in os_info:
                print_success("Amazon Linux detected")
                return True
            elif 'red hat' in os_info or 'rhel' in os_info:
                print_success("Red Hat Enterprise Linux detected")
                return True
    except FileNotFoundError:
        pass
    
    print_warning("Could not detect OS. This script is optimized for Ubuntu/Amazon Linux/RHEL.")
    print_warning("Proceeding anyway, but installation may fail.")
    return True

def check_internet():
    """Check internet connectivity"""
    print_info("Checking internet connectivity...")
    if run_command("ping -c 1 google.com > /dev/null 2>&1", check=False):
        print_success("Internet connection verified")
        return True
    else:
        print_error("No internet connection detected")
        return False

def install_dependencies():
    """Install system dependencies using install.sh"""
    print_header("Installing System Dependencies")
    
    print_info("Running install.sh to detect OS and install dependencies...")
    print_info("This will install: make, docker, docker-compose, python3-pip, python3-venv, etc.")
    print()
    
    if run_command("bash install.sh", check=False):
        print_success("Dependencies installed successfully")
        return True
    else:
        print_error("Failed to install dependencies")
        print_error("Please check the error messages above")
        return False

def setup_docker_group():
    """Ensure user is in docker group and determine if sg docker is needed"""
    print_header("Docker Group Configuration")
    
    username = os.environ.get('USER', run_command("whoami", capture_output=True))
    print_info(f"Ensuring user '{username}' is in docker group...")
    
    # Check if user is in docker group
    groups_output = run_command("groups", capture_output=True)
    if 'docker' not in groups_output:
        print_info("Adding user to docker group...")
        if run_command(f"sudo usermod -aG docker {username}", check=False):
            print_success(f"User '{username}' added to docker group")
        else:
            print_error("Failed to add user to docker group")
            print_error("Please run: sudo usermod -aG docker $USER")
            sys.exit(1)
    else:
        print_success(f"User '{username}' is in docker group")
    
    # Check if we can run docker without sg (group active in current session)
    can_run_docker = run_command("docker ps > /dev/null 2>&1", check=False)
    
    if can_run_docker:
        print_success("Docker group is active in current session")
        return False  # No sg needed
    
    print_info("Docker group not active in current session")
    print_info("Will use 'sg docker' to run Docker commands with group permissions")
    print_warning("After installation, run 'newgrp docker' or logout/login for permanent access")
    
    return True  # sg docker needed

def setup_virtual_environment():
    """Setup Python virtual environment and install dagknows CLI"""
    print_header("Verifying Virtual Environment and DagKnows CLI")
    
    venv_path = os.path.expanduser('~/dkenv')
    dk_path = os.path.join(venv_path, 'bin', 'dk')
    
    # Check if venv exists
    if os.path.exists(venv_path):
        print_success("Virtual environment exists at ~/dkenv")
    else:
        print_info("Virtual environment not found at ~/dkenv")
        print_info("Creating virtual environment...")
        if not run_command("python3 -m venv ~/dkenv", check=False):
            print_error("Failed to create virtual environment")
            return False
        print_success("Virtual environment created")
        
        print_info("Installing setuptools...")
        if not run_command("~/dkenv/bin/pip install setuptools", check=False):
            print_warning("Failed to install setuptools, but continuing...")
    
    # Check if dagknows CLI is installed
    if os.path.exists(dk_path):
        print_success("dagknows CLI found in virtual environment")
        
        # Check version
        try:
            result = run_command(f"{dk_path} version 2>&1", capture_output=True, check=False)
            if result and 'DagKnows CLI Version' in result:
                # Extract version
                for line in result.split('\n'):
                    if 'DagKnows CLI Version' in line:
                        version = line.split(':')[-1].strip()
                        print_info(f"Current dagknows CLI version: {version}")
                        break
            else:
                print_warning("Could not determine dagknows CLI version")
        except Exception:
            print_warning("Could not check dagknows CLI version")
        
        # Ask if user wants to reinstall
        response = input(f"{Colors.BOLD}Do you want to reinstall dagknows CLI? (yes/no) [no]: {Colors.ENDC}").strip().lower()
        if response not in ['yes', 'y']:
            print_info("Keeping existing dagknows CLI installation")
            return True
        
        print_info("Reinstalling dagknows CLI...")
    else:
        print_info("dagknows CLI not found in virtual environment")
        print_info("Installing dagknows CLI (this may take a moment)...")
    
    # Install or reinstall dagknows CLI
    if run_command("~/dkenv/bin/pip install dagknows --force-reinstall", check=False):
        print_success("dagknows CLI installed successfully")
        
        # Verify installation
        try:
            result = run_command(f"{dk_path} version 2>&1", capture_output=True, check=False)
            if result and 'DagKnows CLI Version' in result:
                for line in result.split('\n'):
                    if 'DagKnows CLI Version' in line:
                        version = line.split(':')[-1].strip()
                        print_success(f"dagknows CLI version: {version}")
                        break
        except Exception:
            pass
        
        return True
    else:
        print_error("Failed to install dagknows CLI")
        print_error("You can try manually: ~/dkenv/bin/pip install dagknows --force-reinstall")
        return False

def validate_url(url):
    """Basic URL validation"""
    pattern = r'^https?://[a-zA-Z0-9.-]+(:[0-9]+)?(/.*)?$'
    return re.match(pattern, url) is not None

def configure_dk_cli():
    """Configure DagKnows CLI with server URL"""
    print_header("Configuring DagKnows CLI")
    
    dk_config_path = os.path.expanduser('~/.dk/config')
    if os.path.exists(dk_config_path):
        print_success("DagKnows CLI already configured")
        print_info(f"Config file: {dk_config_path}")
        
        response = input(f"{Colors.BOLD}Do you want to reconfigure? (yes/no) [no]: {Colors.ENDC}").strip().lower()
        if response not in ['yes', 'y']:
            print_info("Keeping existing configuration")
            return True
    
    print_info("Please provide your DagKnows server information")
    print_warning("IMPORTANT: DAGKNOWS_SERVER_URL must use https even when using IP address")
    print()
    
    while True:
        server_url = input(f"{Colors.BOLD}DagKnows Server URL (e.g., https://your-server.com or https://your-ip): {Colors.ENDC}").strip()
        
        if not server_url:
            print_error("Server URL is required!")
            continue
        
        if not server_url.startswith('https://'):
            print_error("Server URL must start with https://")
            continue
        
        if not validate_url(server_url):
            print_error("Invalid URL format!")
            continue
        
        break
    
    print()
    print_info(f"Configuring DagKnows CLI with server: {server_url}")
    print_info("You will be prompted for authentication...")
    print()
    
    dk_path = os.path.expanduser('~/dkenv/bin/dk')
    
    try:
        # Run dk config init with the server URL
        subprocess.run(f"{dk_path} config init --api-host {server_url}", shell=True, check=True)
        print_success("DagKnows CLI configured successfully")
        return True
    except subprocess.CalledProcessError:
        print_error("Failed to configure DagKnows CLI")
        print_error("Please check your server URL and credentials")
        return False
    except KeyboardInterrupt:
        print_info("\nConfiguration interrupted by user")
        return False

def validate_proxy_name(name):
    """Validate proxy name - only alphanumeric characters"""
    pattern = r'^[a-zA-Z0-9]+$'
    return re.match(pattern, name) is not None

def setup_proxy():
    """Setup DagKnows proxy"""
    print_header("Setting Up DagKnows Proxy")
    
    print_info("Now you can install DagKnows proxy")
    print_warning("Use only alphanumeric characters for proxy name. No special characters.")
    print_info("Preferably use the same name as the label you used for the token")
    print()
    
    while True:
        proxy_name = input(f"{Colors.BOLD}Enter Proxy Name: {Colors.ENDC}").strip()
        
        if not proxy_name:
            print_error("Proxy name is required!")
            continue
        
        if not validate_proxy_name(proxy_name):
            print_error("Invalid proxy name! Use only alphanumeric characters (no spaces, no special characters)")
            continue
        
        break
    
    print()
    print_info(f"Creating proxy: {proxy_name}")
    print_info("This will run: sh install_proxy.sh {proxy_name}")
    print()
    
    dk_path = os.path.expanduser('~/dkenv/bin/dk')
    
    # Source the virtual environment and run install_proxy.sh
    try:
        # The install_proxy.sh script runs dk commands, so we need the venv active
        cmd = f"source ~/dkenv/bin/activate && sh install_proxy.sh {proxy_name}"
        subprocess.run(cmd, shell=True, check=True, executable='/bin/bash')
        print_success(f"Proxy '{proxy_name}' created successfully")
        
        # Save proxy name to .env for future reference
        with open('.env', 'w') as f:
            f.write(f"PROXY_NAME={proxy_name}\n")
        
        return True
    except subprocess.CalledProcessError:
        print_error("Failed to create proxy")
        print_error("Please check:")
        print_error("  1. DagKnows CLI is properly configured: ~/dkenv/bin/dk config init")
        print_error("  2. You have proper authentication and permissions")
        print_error(f"  3. Try manually: source ~/dkenv/bin/activate && sh install_proxy.sh {proxy_name}")
        return False
    except KeyboardInterrupt:
        print_info("\nProxy setup interrupted by user")
        return False

def pull_docker_images(use_sg=False):
    """Pull Docker images for proxy"""
    print_header("Pulling Docker Images")
    
    print_info("Downloading Docker images for proxy...")
    print_warning("Being careful to avoid rate limits on public ECR")
    print_info("This may take several minutes depending on your internet speed...")
    print()
    
    # Use sg docker if needed
    if use_sg:
        cmd = "sg docker -c 'make pull'"
    else:
        cmd = "make pull"
    
    try:
        subprocess.run(cmd, shell=True, check=True)
        print_success("Docker images pulled successfully")
        return True
    except subprocess.CalledProcessError:
        print_error("Failed to pull Docker images")
        print_warning("You can try manually later: make pull")
        return False
    except KeyboardInterrupt:
        print_info("\nImage pull interrupted by user")
        return False

def start_proxy(use_sg=False):
    """Start the proxy services"""
    print_header("Starting Proxy Services")
    
    print_info("Running 'make up logs'...")
    print_info("This will start the proxy containers and show logs")
    print_info("Press Ctrl+C to stop viewing logs (proxy will keep running)")
    print()
    
    # Use sg docker if needed
    if use_sg:
        cmd = "sg docker -c 'make up logs'"
    else:
        cmd = "make up logs"
    
    try:
        subprocess.run(cmd, shell=True, check=True)
        print_success("Proxy services started successfully")
        return True
    except subprocess.CalledProcessError:
        print_error("Failed to start proxy services")
        return False
    except KeyboardInterrupt:
        print_info("\nLogs stopped by user")
        print_success("Proxy is running in the background")
        return True

def print_final_instructions(proxy_name, used_sg=False):
    """Print final success message and instructions"""
    print_header("Installation Complete!")
    
    print_success("DagKnows Proxy has been successfully installed!")
    print()
    
    if proxy_name:
        print(f"{Colors.BOLD}Proxy Name:{Colors.ENDC} {Colors.OKCYAN}{proxy_name}{Colors.ENDC}")
        print()
    
    if used_sg:
        print(f"{Colors.WARNING}{Colors.BOLD}⚠ IMPORTANT - Docker Group Activation:{Colors.ENDC}")
        print(f"{Colors.WARNING}The installation used 'sg docker' to run Docker commands.{Colors.ENDC}")
        print(f"{Colors.WARNING}To run commands manually, you need to activate the docker group:{Colors.ENDC}")
        print()
        print(f"{Colors.BOLD}Option 1 (Recommended): Activate for current session{Colors.ENDC}")
        print(f"  {Colors.OKCYAN}newgrp docker{Colors.ENDC}")
        print("  Then run commands normally: make logs, make down, etc.")
        print()
        print(f"{Colors.BOLD}Option 2: Log out and back in{Colors.ENDC}")
        print("  The docker group will be active in all new sessions")
        print()
        print(f"{Colors.BOLD}Option 3: Prefix each command{Colors.ENDC}")
        print(f"  {Colors.OKCYAN}sg docker -c 'make logs'{Colors.ENDC}")
        print()
    
    print(f"{Colors.BOLD}Useful commands:{Colors.ENDC}")
    print(f"  {Colors.OKBLUE}make logs{Colors.ENDC}        - View proxy logs")
    print(f"  {Colors.OKBLUE}make down{Colors.ENDC}        - Stop proxy services")
    print(f"  {Colors.OKBLUE}make up{Colors.ENDC}          - Start proxy services")
    print(f"  {Colors.OKBLUE}make update{Colors.ENDC}      - Update proxy to latest version")
    print()
    
    print(f"{Colors.BOLD}DagKnows CLI commands (activate venv first):{Colors.ENDC}")
    print(f"  {Colors.OKBLUE}source ~/dkenv/bin/activate{Colors.ENDC}")
    print(f"  {Colors.OKBLUE}dk version{Colors.ENDC}       - Check CLI version")
    print(f"  {Colors.OKBLUE}dk proxy list{Colors.ENDC}    - List all proxies")
    print()
    
    print(f"{Colors.OKBLUE}Note: If 'dk' command is not found, add it to PATH:{Colors.ENDC}")
    print(f"  {Colors.OKCYAN}export PATH=$PATH:~/.local/bin{Colors.ENDC}")
    print(f"  Or use the full path: {Colors.OKCYAN}~/dkenv/bin/dk{Colors.ENDC}")
    print()
    
    print(f"{Colors.BOLD}{Colors.HEADER}Next Steps:{Colors.ENDC}")
    print()
    print(f"{Colors.BOLD}1. Create roles to access credentials in proxy{Colors.ENDC}")
    print("   • Log into DagKnows")
    print("   • Go to Settings → Proxies tab")
    print("   • Look for 'Proxy Roles' table")
    print("   • Add a role label (e.g., admin, superuser) - No special characters")
    print("   • Click Add")
    print()
    
    print(f"{Colors.BOLD}2. Assign the proxy role to a user{Colors.ENDC}")
    print("   • Log into DagKnows")
    print("   • Click 'User Management' in left navbar")
    print("   • Click on the user ID you want to assign roles to")
    print("   • Click 'Modify settings'")
    print("   • Look for 'Proxy Roles' and select a role to assign on a proxy")
    print("   • Click modify")
    print("   • Ensure the user now has the role assigned")
    print()
    
    print(f"{Colors.BOLD}3. Enable 'Auto Exec' and 'Send Execution Result to LLM' (if desired){Colors.ENDC}")
    print("   • Log into DagKnows")
    print("   • Click 'Adjust Settings' in left navbar")
    print("   • Toggle 'Auto Exec' if not enabled")
    print("   • Toggle 'Send Execution Result to LLM' if not enabled")
    print()
    
    print(f"{Colors.BOLD}4. Execute a simple task on the proxy{Colors.ENDC}")
    print("   • Create a runbook with a simple command")
    print("   • Try executing it - the command will execute on the proxy")
    print()

def main():
    """Main installation workflow"""
    print_header("DagKnows Proxy Installation Wizard")
    print(f"{Colors.BOLD}This wizard will guide you through the installation of DagKnows Proxy{Colors.ENDC}\n")
    
    # Change to dkproxy directory if not already there
    script_dir = Path(__file__).parent.absolute()
    os.chdir(script_dir)
    print_info(f"Working directory: {os.getcwd()}")
    
    # Check current installation state
    state = check_installation_state()
    
    # Handle resume scenarios
    if state['proxy_running']:
        print_header("Existing Installation Detected")
        print_success("Proxy services are already running!")
        
        if state['proxy_name']:
            print_info(f"Detected proxy: {state['proxy_name']}")
        
        print()
        print(f"{Colors.BOLD}Your DagKnows Proxy installation appears to be complete.{Colors.ENDC}")
        print()
        print("Available actions:")
        print("  1. View logs: make logs")
        print("  2. Stop proxy: make down")
        print("  3. Update proxy: make update")
        print()
        response = input(f"{Colors.BOLD}Do you want to reinstall anyway? (yes/no) [no]: {Colors.ENDC}").strip().lower()
        if response not in ['yes', 'y']:
            print_info("Installation skipped. Proxy is already running.")
            sys.exit(0)
    
    # Confirmation for install
    print_warning("This script will:")
    print("  1. Install system dependencies (Docker, make, Python venv, etc.)")
    print("  2. Setup Python virtual environment at ~/dkenv")
    print("  3. Install and configure DagKnows CLI")
    print("  4. Create and configure a proxy")
    print("  5. Pull Docker images and start proxy services")
    print()
    
    response = input(f"{Colors.BOLD}Do you want to continue? (yes/no): {Colors.ENDC}").strip().lower()
    if response not in ['yes', 'y']:
        print_info("Installation cancelled by user")
        sys.exit(0)
    
    try:
        # Pre-flight checks
        check_os()
        if not check_internet():
            print_error("Internet connection required for installation")
            sys.exit(1)
        
        # Install dependencies if needed
        if not state['docker_installed'] or not state['make_installed']:
            if not install_dependencies():
                print_error("Dependency installation failed")
                sys.exit(1)
        else:
            print_success("System dependencies already installed (skipping)")
        
        # Ensure Docker service is running
        print_header("Ensuring Docker Service is Running")
        if not run_command("docker ps > /dev/null 2>&1", check=False):
            print_info("Starting Docker service...")
            if run_command("sudo systemctl start docker", check=False):
                time.sleep(3)
                print_success("Docker started successfully")
            else:
                print_error("Failed to start Docker")
                print_info("Try manually: sudo systemctl start docker")
                sys.exit(1)
        else:
            print_success("Docker is running")
        
        # Setup docker group
        use_sg = setup_docker_group()
        
        # Setup virtual environment and install dagknows CLI
        if not setup_virtual_environment():
            print_error("Virtual environment setup failed")
            sys.exit(1)
        
        # Configure DagKnows CLI
        if not state['dk_configured']:
            if not configure_dk_cli():
                print_error("DagKnows CLI configuration failed")
                sys.exit(1)
        else:
            print_success("DagKnows CLI already configured")
            response = input(f"{Colors.BOLD}Reconfigure DagKnows CLI? (yes/no) [no]: {Colors.ENDC}").strip().lower()
            if response in ['yes', 'y']:
                if not configure_dk_cli():
                    print_error("DagKnows CLI configuration failed")
                    sys.exit(1)
        
        # Setup proxy
        proxy_name = state.get('proxy_name')
        if not proxy_name:
            if not setup_proxy():
                print_error("Proxy setup failed")
                sys.exit(1)
            
            # Get proxy name from .env
            if os.path.exists('.env'):
                with open('.env', 'r') as f:
                    for line in f:
                        if line.startswith('PROXY_NAME='):
                            proxy_name = line.split('=', 1)[1].strip()
        else:
            print_success(f"Proxy '{proxy_name}' already exists")
            response = input(f"{Colors.BOLD}Create a new proxy? (yes/no) [no]: {Colors.ENDC}").strip().lower()
            if response in ['yes', 'y']:
                if not setup_proxy():
                    print_error("Proxy setup failed")
                    sys.exit(1)
        
        # Pull Docker images
        if not pull_docker_images(use_sg):
            print_error("Failed to pull Docker images")
            print_info("You can try manually later: make pull")
            # Don't exit, continue to try starting anyway
        
        # Start proxy
        if not start_proxy(use_sg):
            print_error("Proxy startup failed")
            sys.exit(1)
        
        # Success!
        print_final_instructions(proxy_name, use_sg)
        
    except KeyboardInterrupt:
        print_error("\n\nInstallation interrupted by user")
        sys.exit(1)
    except Exception as e:
        print_error(f"\n\nUnexpected error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()

