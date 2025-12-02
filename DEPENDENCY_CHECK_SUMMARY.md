# Dependency Check Summary

## What install_ubuntu.sh Installs vs What install.py Checks

This document shows the complete mapping between what `install_ubuntu.sh` installs and what `install.py` checks for before deciding to skip the installation script.

### Complete Dependency List

| Package/Tool | Installed by install_ubuntu.sh | Checked by install.py | Check Method |
|-------------|-------------------------------|----------------------|--------------|
| **make** | ✅ `sudo apt-get install -y make` | ✅ | `shutil.which('make')` |
| **docker.io** | ✅ `sudo apt-get install -y docker.io` | ✅ | `shutil.which('docker')` |
| **docker-compose** | ✅ `sudo apt-get install -y docker-compose` | ✅ | `shutil.which('docker-compose')` |
| **docker-compose-v2** | ✅ `sudo apt-get install -y docker-compose-v2` | ✅ | Check `~/.docker/cli-plugins/docker-compose` |
| **unzip** | ✅ `sudo apt-get install -y unzip` | ✅ | `shutil.which('unzip')` |
| **python3-pip** | ✅ `sudo apt-get install -y python3-pip` | ✅ | `shutil.which('pip3')` or `shutil.which('pip')` |
| **python3-venv** | ✅ `sudo apt-get install -y python3-venv` | ✅ | `python3 -m venv --help` |
| **ca-certificates** | ✅ `sudo apt-get install ca-certificates` | ⚠️ | Indirect (trusted by system) |
| **curl** | ✅ `sudo apt-get install curl` | ✅ | `shutil.which('curl')` |
| **gnupg** | ✅ `sudo apt-get install gnupg` | ✅ | `shutil.which('gpg')` |
| **Docker GPG key** | ✅ Setup in script | ⏭️ | Handled by install.sh |
| **User in docker group** | ✅ `sudo usermod -aG docker ${USER}` | ✅ | Later in wizard (setup_docker_group) |
| **make prepare** | ✅ Run in script | ⏭️ | Not checked (runs if needed) |
| **Virtual environment** | ✅ `python3 -m venv ~/dkenv` | ✅ | Check if `~/dkenv` exists |
| **setuptools** | ✅ `~/dkenv/bin/pip install setuptools` | ⏭️ | Installed later in wizard |
| **dagknows CLI** | ✅ `~/dkenv/bin/pip install dagknows` | ✅ | Check if `~/dkenv/bin/dk` exists |

### Legend
- ✅ Explicitly checked before deciding to skip installation
- ⚠️ Indirectly checked or assumed to be present
- ⏭️ Not checked because it will be handled later in the wizard flow

## Dependency Check Code

```python
def check_installation_state():
    """Check the current state of installation to allow resuming"""
    state = {
        'docker_installed': shutil.which('docker') is not None,
        'make_installed': shutil.which('make') is not None,
        'docker_compose_installed': shutil.which('docker-compose') is not None or 
                                     os.path.exists(os.path.expanduser('~/.docker/cli-plugins/docker-compose')),
        'unzip_installed': shutil.which('unzip') is not None,
        'python3_pip_available': check_pip_available(),
        'python3_venv_available': check_python_venv_available(),
        'curl_installed': shutil.which('curl') is not None,
        'gnupg_installed': shutil.which('gpg') is not None,
        'venv_exists': os.path.exists(os.path.expanduser('~/dkenv')),
        'dk_installed': False,
        'dk_configured': False,
        'proxy_running': False,
        'proxy_name': None
    }
```

## Why We Check All These Dependencies

### Critical Dependencies (Must be present)

1. **docker** - Required to run proxy containers
2. **make** - Required to run Makefile commands (pull, up, down, etc.)
3. **docker-compose** - Required to manage multi-container setup
4. **python3-venv** - Required to create isolated Python environment
5. **python3-pip** - Required to install Python packages

### Important Dependencies (Should be present)

6. **unzip** - Used by install scripts and make targets
7. **curl** - Used to fetch Docker GPG keys and other resources
8. **gnupg** - Required for GPG operations with Docker keys

### Why This Matters

If the wizard only checked for Docker and make (original implementation), it would skip `install.sh` even though:
- `python3-venv` is not installed → Virtual environment creation fails ❌
- `python3-pip` is not installed → Cannot install packages ❌
- `curl` is not installed → Cannot fetch Docker keys ❌
- `gnupg` is not installed → Cannot verify Docker keys ❌

## Behavior

The wizard **always** runs `install.sh` to ensure all dependencies are properly installed and up to date:

```
ℹ Checking operating system...
✓ Ubuntu detected
ℹ Checking internet connectivity...
✓ Internet connection verified
ℹ Running install.sh to ensure all dependencies are properly installed...

============================================================
         Installing System Dependencies             
============================================================

ℹ Running install.sh to detect OS and install dependencies...
ℹ This will install: make, docker, docker-compose, python3-pip, python3-venv, etc.

[Runs bash install.sh]

✓ Dependencies installed successfully
```

This ensures:
- All required packages are installed
- Packages are up to date
- Docker group membership is configured
- Consistent installation regardless of system state

## Notes on ca-certificates

We don't explicitly check for `ca-certificates` because:
1. It's typically pre-installed on most systems
2. There's no easy command-line check without inspecting package manager
3. If it's missing, `curl` operations will fail and the user will get clear errors
4. The install script will install it anyway

If this becomes an issue, we can add:
```bash
dpkg -l | grep ca-certificates  # Ubuntu/Debian
rpm -qa | grep ca-certificates  # RHEL/Amazon Linux
```

## Testing

To test the dependency checking:

```bash
# Remove a dependency
sudo apt-get remove python3-venv

# Run the wizard
python3 install.py

# Should detect missing python3-venv and run install.sh
```

## Related Files

- `install.py` - Main wizard with dependency checking
- `install.sh` - OS detection and installer delegation
- `install_ubuntu.sh` - Ubuntu-specific package installation
- `install_amazonlinux.sh` - Amazon Linux package installation
- `install_rhel.sh` - RHEL package installation

