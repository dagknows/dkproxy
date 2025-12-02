# DagKnows Proxy Installation Wizard

## Overview

A comprehensive installation wizard for DagKnows Proxy, similar to the dkapp installation wizard. This wizard automates the entire installation process and provides a user-friendly experience.

## What Was Created

### 1. `install.py` - Main Installation Wizard

A Python-based interactive installation wizard that handles:

- **System Requirements Check**: Verifies OS compatibility and internet connectivity
- **Dependency Installation**: Calls existing `install.sh` to install Docker, make, Python packages
- **Docker Group Management**: Handles docker group permissions using `sg docker` when needed (avoiding the need for manual `newgrp docker`)
- **Virtual Environment Setup**: Creates and manages Python virtual environment at `~/dkenv`
- **DagKnows CLI Installation**: Installs and configures the dagknows CLI tool
- **CLI Configuration**: Interactive configuration with DagKnows server (enforces HTTPS)
- **Proxy Setup**: Creates proxy with validated alphanumeric name
- **Docker Image Pulling**: Pulls images carefully to avoid ECR rate limits
- **Service Startup**: Starts proxy containers and displays logs
- **Resume Capability**: Can detect existing installations and resume from any step

### 2. Updated `README.md`

Comprehensive documentation covering:
- Two installation methods (Automated Wizard vs Manual)
- Post-installation configuration steps
- Proxy management commands
- Troubleshooting guide

### 3. New Documentation: `INSTALLATION_WIZARD.md`

This file - documenting the wizard implementation and usage.

## Features

### User Experience Enhancements

1. **Color-coded Output**: Uses ANSI colors for better readability
   - Green ✓ for success
   - Red ✗ for errors
   - Yellow ⚠ for warnings
   - Blue ℹ for information

2. **Progress Tracking**: Clear indication of current step and progress

3. **Smart Resume**: Detects existing installations and allows resuming from any point

4. **Validation**: Validates user inputs (proxy names, URLs, etc.)

5. **Helpful Instructions**: Provides clear next steps after installation

### Technical Features

1. **Docker Group Handling**: Automatically uses `sg docker` when docker group isn't active in current session

2. **Consistent Virtual Environment**: Ensures venv is created regardless of OS-specific installer behavior

3. **Error Recovery**: Handles errors gracefully with helpful error messages

4. **Non-interactive Modes**: Can be extended for automated deployments

## Usage

### Basic Installation

```bash
cd dkproxy
python3 install.py
```

The wizard will prompt you for:
1. Confirmation to proceed with installation
2. DagKnows server URL (must be HTTPS)
3. Authentication credentials for DagKnows CLI
4. Proxy name (alphanumeric only)

### Installation Flow

```
1. Pre-flight Checks
   ├── OS Detection (Ubuntu/Amazon Linux/RHEL)
   └── Internet Connectivity Check

2. System Dependencies (Always Runs)
   ├── Run install.sh (OS-specific)
   ├── Install Docker, make, Python tools
   └── Add user to docker group

3. Docker Service
   ├── Start Docker if not running
   └── Setup docker group permissions

4. Python Virtual Environment
   ├── Create ~/dkenv if doesn't exist
   ├── Install setuptools
   └── Install/update dagknows CLI

5. DagKnows CLI Configuration
   ├── Prompt for server URL (HTTPS enforced)
   └── Authenticate with DagKnows server

6. Proxy Setup
   ├── Prompt for proxy name (validation)
   └── Run install_proxy.sh

7. Docker Images
   ├── Pull proxy images (rate-limit aware)
   └── Verify image availability

8. Start Services
   ├── Run make up
   └── Show logs (Ctrl+C to exit)

9. Post-Installation Instructions
   ├── Docker group activation options
   ├── Useful commands
   └── Next steps for proxy configuration
```

## Integration with Existing Scripts

The wizard integrates seamlessly with existing installation scripts:

- **install.sh**: Detects OS and calls appropriate installer (unchanged)
- **install_ubuntu.sh**: Installs Ubuntu-specific packages (unchanged)
- **install_amazonlinux.sh**: Installs Amazon Linux packages (unchanged)
- **install_rhel.sh**: Installs RHEL packages (unchanged)
- **install_proxy.sh**: Creates proxy using dk CLI (unchanged)
- **Makefile**: Used for docker operations (unchanged)

## Comparison with dkapp Installation Wizard

### Similarities

1. Color-coded interactive UI
2. Progress tracking and clear status messages
3. Docker group handling with `sg docker`
4. Resume capability for interrupted installations
5. Comprehensive error handling
6. Post-installation instructions

### Differences

1. **No Configuration Encryption**: dkproxy doesn't use encrypted .env files like dkapp
2. **CLI Authentication**: Uses dk CLI authentication instead of manual .env configuration
3. **Proxy Name**: Requires proxy name input (alphanumeric validation)
4. **Virtual Environment**: Always uses venv for consistency across OS types
5. **Simpler Dependency Management**: Leverages existing install.sh instead of custom per-OS logic

## Post-Installation Steps

After running the wizard, users need to configure the proxy in DagKnows:

### 1. Create Proxy Roles
- Settings → Proxies → Proxy Roles
- Add role labels (e.g., admin, superuser)

### 2. Assign Roles to Users
- User Management → Select User → Modify Settings
- Assign proxy roles

### 3. Configure Settings (Optional)
- Adjust Settings → Enable Auto Exec
- Enable "Send Execution Result to LLM"

### 4. Test Proxy
- Create runbook with simple command
- Execute on proxy

## Troubleshooting

### Docker Group Issues

If docker commands fail:
```bash
# Option 1: Activate for current session
newgrp docker

# Option 2: Log out and back in

# Option 3: Use sg docker prefix
sg docker -c 'make logs'
```

The wizard handles this automatically during installation.

### CLI Not Found

If `dk` command not found:
```bash
# Activate venv
source ~/dkenv/bin/activate

# Or add to PATH
export PATH=$PATH:~/.local/bin

# Or use full path
~/dkenv/bin/dk version
```

### Re-running the Wizard

The wizard can be re-run safely:
- Detects existing installations
- Offers to skip or reconfigure each step
- Won't break existing setups

## Future Enhancements

Potential improvements:

1. **Non-interactive Mode**: Add command-line arguments for automated deployments
2. **Configuration File**: Support config file for batch installations
3. **Health Checks**: Verify proxy connectivity after installation
4. **Backup/Restore**: Backup existing proxy configurations before changes
5. **Multi-proxy Support**: Install multiple proxies in one session
6. **Update Wizard**: Separate wizard for updating existing installations

## Development Notes

### Code Structure

```python
# Color definitions for UI
class Colors

# Utility functions
run_command()          # Execute shell commands
check_installation_state()  # Detect existing installation

# Pre-flight checks
check_os()            # Detect OS type
check_internet()      # Verify connectivity

# Installation steps
install_dependencies()      # Run install.sh
setup_docker_group()       # Handle docker permissions
setup_virtual_environment() # Setup Python venv
configure_dk_cli()         # Configure DagKnows CLI
setup_proxy()              # Create proxy
pull_docker_images()       # Pull images
start_proxy()              # Start services

# User interface
print_header()        # Section headers
print_success()       # Success messages
print_error()         # Error messages
print_warning()       # Warnings
print_info()          # Information
print_final_instructions()  # Post-install guide

# Main workflow
main()               # Orchestrates installation
```

### Testing Recommendations

1. **Fresh Installation**: Test on clean VM of each supported OS
2. **Resume Testing**: Interrupt at each step and verify resume works
3. **Error Handling**: Test with network issues, permission problems
4. **Edge Cases**: Test with existing venv, existing proxy, etc.

## Manual Installation Process (Original)

For reference, the original manual steps that the wizard automates:

```bash
# 1. Clone repository
git clone https://github.com/dagknows/dkproxy.git

# 2. Install dependencies
cd dkproxy && sh install.sh

# 3. Refresh docker group
newgrp docker

# 4. Activate virtual environment
source ~/dkenv/bin/activate

# 5. Verify dk CLI
dk version

# 6. Reinstall if needed
pip install dagknows --force-reinstall

# 7. Add to PATH if needed
export PATH=$PATH:/home/ubuntu/.local/bin

# 8. Configure CLI
dk config init --api-host <DAGKNOWS_SERVER_URL>

# 9. Install proxy
sh install_proxy.sh {{PROXY_NAME}}

# 10. Pull images
make pull

# 11. Start proxy
make up logs
```

The wizard handles all these steps interactively with validation and error handling.

