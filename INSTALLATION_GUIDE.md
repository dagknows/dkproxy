# DagKnows Proxy Installation Guide

This comprehensive guide covers everything you need to know about installing, configuring, and managing the DagKnows Proxy.

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [Prerequisites](#prerequisites)
3. [Automated Installation](#automated-installation)
4. [What Gets Automated](#what-gets-automated)
5. [Installation Wizard Flow](#installation-wizard-flow)
6. [Post-Installation Features](#post-installation-features)
7. [Resume Capability](#resume-capability)
8. [Management Commands](#management-commands)
9. [Troubleshooting](#troubleshooting)
10. [Multi-Proxy Deployments](#multi-proxy-deployments)
11. [Technical Details](#technical-details)
12. [Security Best Practices](#security-best-practices)

---

## Quick Start

```bash
# Clone the repository
git clone https://github.com/dagknows/dkproxy.git
cd dkproxy

# Run the installation wizard
python3 install.py
```

The wizard will guide you through the entire setup process.

---

## Prerequisites

### Supported Operating Systems

| OS | Version | Status |
|----|---------|--------|
| Ubuntu | 22.04+ | Recommended |
| Amazon Linux | 2023+ | Supported |
| Red Hat Enterprise Linux | 8+ | Supported |
| Debian | 11+ | Supported |

### Hardware Requirements

- **Disk Space:** 50 GB minimum
- **Memory:** 4 GB minimum (8 GB recommended)
- **CPU:** 2 cores minimum

### Network Requirements

- Internet access for:
  - Downloading Docker images from public ECR and Docker Hub
  - Connecting to DagKnows SaaS or on-prem server
- Outbound HTTPS (port 443) to DagKnows server

### Required Information

Before starting, you'll need:

1. **DagKnows Server URL** - Your DagKnows instance (e.g., `https://app.dagknows.com` or `https://your-server.com`)
2. **Authentication Credentials** - Either:
   - Username/password for an account with proxy creation permissions, OR
   - Access token from DagKnows Settings page
3. **Proxy Name** - Alphanumeric name for your proxy (e.g., `prod1`, `devproxy`)

---

## Automated Installation

### Option 1: Using Python Directly

```bash
cd dkproxy
python3 install.py
```

### Option 2: Using Make

```bash
cd dkproxy
make install
```

Both methods run the same installation wizard.

---

## What Gets Automated

The installation wizard automates the following:

### 1. System Package Installation

| Package | Purpose |
|---------|---------|
| Docker | Container runtime |
| Docker Compose | Multi-container orchestration |
| make | Build automation |
| Python3 | Required for DagKnows CLI |
| python3-pip | Python package manager |
| python3-venv | Virtual environment support |
| curl | HTTP client |
| git | Version control |

### 2. Docker Configuration

- Installs Docker if not present
- Adds current user to `docker` group
- Starts Docker service
- Enables Docker to start on boot

### 3. DagKnows CLI Installation

- Creates Python virtual environment at `~/dkenv`
- Installs `dagknows` CLI package
- Configures CLI with your DagKnows server URL
- Authenticates with your credentials

### 4. Proxy Registration

- Creates a new proxy on your DagKnows server
- Downloads proxy configuration (`.env` file)
- Validates all required environment variables

### 5. Docker Images

- Pulls required Docker images:
  - `outpost` - Proxy orchestration service
  - `cmd_exec` - Command execution service
  - `vault` - HashiCorp Vault for secrets

### 6. Service Startup

- Starts all proxy containers
- Initiates background log capture
- Verifies services are running

### 7. Optional Features (Auto-Offered)

- **Log Rotation** - Daily cron job for log management
- **Auto-Restart** - Systemd service for boot recovery
- **Version Management** - Docker image version tracking

---

## Installation Wizard Flow

The wizard proceeds through these steps:

### Step 1: Pre-flight Checks

```
✓ Ubuntu detected
✓ Internet connection verified
```

The wizard checks:
- Operating system compatibility
- Internet connectivity
- Existing installation state

### Step 2: System Dependencies

```
ℹ Running install.sh to detect OS and install dependencies...
✓ Dependencies installed successfully
```

Installs required packages using your system's package manager.

### Step 3: Docker Group Configuration

```
ℹ Ensuring user 'ubuntu' is in docker group...
✓ User 'ubuntu' is in docker group
✓ Docker group is active in current session
```

If the docker group isn't active:
```
ℹ Docker group not active in current session
ℹ Will use 'sg docker' to run Docker commands
⚠ After installation, run 'newgrp docker' or logout/login
```

### Step 4: Virtual Environment Setup

```
✓ Virtual environment exists at ~/dkenv
✓ dagknows CLI found in virtual environment
ℹ Current dagknows CLI version: 1.2.3
ℹ Reinstalling dagknows CLI to ensure latest version...
✓ dagknows CLI installed successfully
```

### Step 5: DagKnows CLI Configuration

```
ℹ Please provide your DagKnows server information
⚠ IMPORTANT: Server URL must use https even when using IP address

DagKnows Server URL: https://your-server.com
```

You'll be prompted for authentication (username/password or token).

### Step 6: Proxy Setup

```
ℹ Now you can install DagKnows proxy
⚠ Use only alphanumeric characters for proxy name

Enter Proxy Name: myproxy

ℹ Creating proxy: myproxy
✓ All required environment variables found!
  PROXY_ALIAS: myproxy
  DAGKNOWS_URL: https://your-server.com
  DAGKNOWS_PROXY_URL: wss://your-server.com
  PROXY_SESSION_ID: abc123...
```

### Step 7: Docker Image Pull

```
ℹ Downloading Docker images for proxy...
⚠ Being careful to avoid rate limits on public ECR
✓ Docker images pulled successfully
```

### Step 8: Service Startup

```
ℹ Running 'make start'...
✓ Proxy services started successfully
✓ Background log capture running (PID: 1234)
ℹ View logs anytime with: make logs
```

### Step 9: Optional Features

```
Log Rotation Setup
ℹ Setting up automatic log rotation...
✓ Log rotation cron job installed!

Auto-Restart Setup
ℹ Setting up auto-restart on system boot...
✓ Auto-restart configured! Service: dkproxy-myproxy.service

Version Management Setup
ℹ Setting up version management...
✓ Version management configured!
```

---

## Post-Installation Features

After the proxy starts, the wizard automatically configures these optional features:

### Log Rotation

- **Cron job** runs daily at midnight
- **Compression** - Logs older than 3 days are gzipped
- **Deletion** - Logs older than 7 days are deleted
- See [LOGGING.md](LOGGING.md) for details

### Auto-Restart

- **Systemd service** starts proxy on boot
- **Unique naming** - Each proxy gets its own service
- See [AUTORESTART.md](AUTORESTART.md) for details

### Version Management

- **Manifest file** tracks current versions
- **Rollback support** - Easily revert to previous versions
- See [VERSION-MANAGEMENT.md](VERSION-MANAGEMENT.md) for details

---

## Resume Capability

The installation wizard can resume from where it left off if interrupted.

### Smart State Detection

The wizard detects:

| State | Detected By |
|-------|-------------|
| Docker installed | `docker` command exists |
| Virtual env exists | `~/dkenv` directory exists |
| DagKnows CLI installed | `~/dkenv/bin/dk` exists |
| CLI configured | `~/.dk/config` file exists |
| Proxy running | Container names contain `outpost` or `cmd_exec` |
| Proxy name | `PROXY_NAME` in `.env` file |

### Resume Scenarios

**Scenario 1: Interrupted During Dependencies**
```
Wizard detects docker not installed → Runs install.sh
```

**Scenario 2: CLI Configured, Proxy Not Created**
```
✓ DagKnows CLI already configured
Do you want to reconfigure? (yes/no) [no]: no
ℹ Keeping existing configuration

→ Proceeds to proxy setup
```

**Scenario 3: Proxy Already Running**
```
⚠ WARNING: Proxy containers are already running:
CONTAINER NAME    STATUS         IMAGE
outpost           Up 2 hours     public.ecr.aws/n5k3t9x2/outpost:latest

Do you want to continue with installation? (yes/no) [no]:
```

---

## Management Commands

### Service Control

| Command | Description |
|---------|-------------|
| `make start` | Start all proxy services |
| `make stop` | Stop all services and log capture |
| `make restart` | Restart all services |
| `make status` | Check proxy status and versions |

### Logs

| Command | Description |
|---------|-------------|
| `make logs` | View live logs (last 300 lines + follow) |
| `make logs-today` | View today's captured logs |
| `make logs-errors` | View errors from captured logs |
| `make logs-service SERVICE=outpost` | View specific service logs |

### Updates

| Command | Description |
|---------|-------------|
| `make update` | Update to latest version |
| `make update-safe` | Safe update with backup |
| `make pull` | Pull images from manifest |
| `make pull-latest` | Pull latest images |

### Setup

| Command | Description |
|---------|-------------|
| `make setup-autorestart` | Configure auto-start on boot |
| `make setup-log-rotation` | Configure daily log rotation |
| `make setup-versioning` | Enable version tracking |

### DagKnows CLI

```bash
# Activate virtual environment first
source ~/dkenv/bin/activate

# Then use dk commands
dk version           # Check CLI version
dk proxy list        # List all proxies
dk proxy getenv NAME # Download proxy config
```

---

## Troubleshooting

### Docker Permission Denied

**Problem:**
```
Got permission denied while trying to connect to the Docker daemon
```

**Solution:**
```bash
# Option 1: Activate docker group in current session
newgrp docker

# Option 2: Log out and back in
# The docker group will be active automatically

# Option 3: Prefix commands
sg docker -c "make logs"
```

### Proxy Not Connecting to DagKnows

**Check container status:**
```bash
make status
make logs
```

**Verify .env file:**
```bash
cat .env | grep DAGKNOWS
```

**Required variables:**
- `DAGKNOWS_URL` - Must be reachable
- `DAGKNOWS_PROXY_URL` - WebSocket URL for proxy connection
- `PROXY_SESSION_ID` - Must be valid

**Regenerate .env:**
```bash
source ~/dkenv/bin/activate
dk proxy getenv <proxy_name>
make restart
```

### Services Not Starting

**Check logs:**
```bash
make logs
journalctl -u dkproxy-*.service
```

**Verify Docker is running:**
```bash
sudo systemctl status docker
```

**Check disk space:**
```bash
df -h
```

### Token Expiration

If authentication fails with 401 errors:

1. Get a new access token from DagKnows Settings
2. Reconfigure the CLI:
   ```bash
   source ~/dkenv/bin/activate
   dk config init --api-host https://your-server.com
   ```

### Installation Script Fails

**Check logs:**
```bash
# View install.sh output
bash install.sh 2>&1 | tee install.log
```

**Common issues:**
- No sudo access
- Package manager locked
- Network connectivity

---

## Multi-Proxy Deployments

You can run multiple proxies on the same server.

### Setup Multiple Proxies

```bash
# First proxy
cd /opt/proxy1
python3 install.py  # Creates proxy "prod1"

# Second proxy
cd /opt/proxy2
python3 install.py  # Creates proxy "dev1"
```

### Unique Service Names

Each proxy gets a unique systemd service based on `PROXY_ALIAS`:

| PROXY_ALIAS | Service Name | Log File |
|-------------|--------------|----------|
| prod1 | `dkproxy-prod1.service` | `/var/log/dkproxy-startup-prod1.log` |
| dev1 | `dkproxy-dev1.service` | `/var/log/dkproxy-startup-dev1.log` |

### Independent Control

Each proxy can be managed independently:

```bash
# In /opt/proxy1
make start   # Starts only proxy1

# In /opt/proxy2
make start   # Starts only proxy2
```

---

## Technical Details

### Files Created During Installation

| Location | File | Purpose |
|----------|------|---------|
| `~/dkenv/` | Virtual environment | Python environment with dagknows CLI |
| `~/.dk/config` | CLI config | DagKnows server URL and auth |
| `{proxy_dir}/.env` | Proxy config | Environment variables for containers |
| `{proxy_dir}/version-manifest.yaml` | Version tracking | Docker image versions |
| `{proxy_dir}/versions.env` | Version overrides | Generated from manifest |
| `{proxy_dir}/logs/` | Log files | Captured container logs |
| `/etc/systemd/system/dkproxy-*.service` | Systemd service | Auto-restart configuration |
| `/var/log/dkproxy-startup-*.log` | Startup log | Systemd startup logs |

### Docker Group Handling

The wizard handles the docker group in two scenarios:

**Group Active (normal case):**
- Docker commands run directly
- No special handling needed

**Group Not Active (new session):**
- Uses `sg docker -c "command"` to run with group permissions
- Reminds user to run `newgrp docker` or logout/login

### Container Images

| Image | Source | Purpose |
|-------|--------|---------|
| outpost | public.ecr.aws/n5k3t9x2/outpost | Proxy orchestration |
| cmd_exec | public.ecr.aws/n5k3t9x2/cmd_exec | Command execution |
| vault | hashicorp/vault (Docker Hub) | Secrets management |

---

## Security Best Practices

### File Permissions

```bash
# Protect .env file
chmod 600 .env
```

### Network Security

- Use firewall rules to restrict access to proxy server
- Only allow outbound HTTPS to DagKnows server
- Consider VPN for on-premises deployments

### Token Management

- Use access tokens instead of username/password when possible
- Rotate tokens periodically
- Store tokens securely (never in code)

### Server Hardening

- Keep OS and Docker updated
- Disable unnecessary services
- Use disk encryption (LUKS)
- Enable audit logging

### Proxy Roles

- Create specific roles for proxy access in DagKnows
- Assign roles based on least-privilege principle
- Review role assignments regularly

---

## Next Steps After Installation

1. **Create Proxy Roles in DagKnows**
   - Go to Settings → Proxies tab
   - Add role labels (e.g., "admin", "developer")

2. **Assign Roles to Users**
   - Go to User Management
   - Select user → Modify settings
   - Assign proxy roles

3. **Enable Auto Exec (Optional)**
   - Go to Adjust Settings
   - Toggle "Auto Exec"
   - Toggle "Send Execution Result to LLM"

4. **Test the Proxy**
   - Create a runbook with a simple command
   - Execute on the proxy
   - Verify results

---

## Support

For issues and support:
- GitHub Issues: https://github.com/dagknows/dkproxy/issues
- Documentation: See other guides in this directory
