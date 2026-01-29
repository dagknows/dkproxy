# DK Proxy

The DagKnows proxy runner.   This repo contains a minimal set of compose files for running a DagKnows proxy anywhere.

## Requirements

* One of the linux distros (with 50GB of disk space):
  * Ubuntu 22.04+
  * Amazon Linux 2023+
  * RedHat
* git
* Python 3

## Installation

### Option 1: Automated Installation (Recommended)

Run the installation wizard which automates all steps:

```bash
git clone https://github.com/dagknows/dkproxy.git
cd dkproxy
python3 install.py
```

The wizard will guide you through dependency installation, CLI configuration, proxy setup, and service startup.

### Option 2: Manual Installation

#### 1. Checkout this repo

```bash
git clone https://github.com/dagknows/dkproxy.git
cd dkproxy
```

#### 2. Install required packages

```bash
sh install.sh

# Refresh docker group membership (or logout/login)
newgrp docker
```

#### 3. Activate virtual environment

```bash
source ~/dkenv/bin/activate
```

#### 4. Configure DagKnows CLI

The installation script installs the DagKnows CLI which provides wrappers to interact with DagKnows and manage proxies. You will need to configure it with your DagKnows server URL and authenticate with an access token.

**Important:** 
- Use `https` for the server URL, even with IP addresses
- Obtain an access token from the DagKnows App's Settings page before running this command

```bash
dk config init --api-host https://YOUR_DAGKNOWS_SERVER_URL
```

This will prompt you for an access token to configure the proxy with the application.

#### 5. Install your Proxy

```bash
sh install_proxy.sh myproxy
```

Replace `myproxy` with your desired proxy name (alphanumeric only).

#### 6. Download Docker images

```bash
make pull
```

#### 7. Run your proxy

```bash
make start
```

## Managing Your Proxy

### Service Commands

| Command | Description |
|---------|-------------|
| `make start` | Start all services (handles systemd if configured) |
| `make stop` | Stop all services and log capture |
| `make restart` | Restart all services |
| `make status` | Check proxy status and versions |
| `make logs` | View live logs (last 300 lines + follow) |

### Update proxy
```bash
make update
make start
```

## Optional Setup

### Auto-Restart on Reboot

Configure the proxy to start automatically when the system boots:

```bash
make setup-autorestart
```

This installs a systemd service that:
- Starts proxy services automatically on boot
- Manages services via `make start/stop/restart`
- Uses PROXY_ALIAS for unique service naming (supports multiple proxies)

### Log Rotation

Set up automatic log rotation to prevent disk space issues:

```bash
make setup-log-rotation
```

This installs a cron job that runs daily at midnight:
- Logs 0-3 days old: kept uncompressed
- Logs 3-7 days old: compressed (.gz)
- Logs 7+ days old: deleted automatically

### Version Management

Enable version tracking for reproducible deployments:

```bash
make setup-versioning
```

This creates a version manifest that:
- Tracks exact Docker image versions
- Enables version pinning and rollback
- Supports safe updates with `make update-safe`

## All Available Commands

Run `make help` to see all available commands:

```bash
make help
```

### Quick Reference

| Category | Command | Description |
|----------|---------|-------------|
| **Services** | `make start` | Start all services |
| | `make stop` | Stop all services |
| | `make restart` | Restart all services |
| | `make status` | Check status and versions |
| **Logs** | `make logs` | View live logs |
| | `make logs-today` | View today's captured logs |
| | `make logs-errors` | View errors only |
| **Updates** | `make update` | Update to latest version |
| | `make update-safe` | Safe update with rollback |
| **Setup** | `make setup-autorestart` | Configure auto-start on boot |
| | `make setup-log-rotation` | Configure daily log rotation |
| | `make setup-versioning` | Enable version tracking |
