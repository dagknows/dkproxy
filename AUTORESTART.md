# DagKnows Proxy Auto-Restart Configuration

This guide explains how to configure your DagKnows proxy to automatically start after system reboots.

---

## TL;DR - Quick Setup

```bash
make setup-autorestart
```

After setup, your proxy will automatically start when the system boots. No additional configuration needed.

---

## Overview

The auto-restart feature uses **systemd** to automatically start proxy services after system reboots. This ensures your proxy recovers automatically from:

- System reboots (planned maintenance)
- Power outages
- Kernel updates requiring restart
- System crashes

**Key difference from dkapp:** The proxy uses an unencrypted `.env` file, so no passphrase handling is required. Setup is simpler and fully automatic.

---

## Quick Setup

```bash
# Run setup (requires sudo)
make setup-autorestart
```

The setup script will:
1. Verify prerequisites (.env file, docker-compose.yaml, etc.)
2. Enable Docker to start on boot
3. Configure the startup script with your installation path
4. Install a systemd service file
5. Enable automatic startup
6. Start the proxy immediately

---

## How It Works

### Startup Flow

```
System Boot
    │
    ▼
Docker Service
    │
    ▼
dkproxy-{PROXY_ALIAS}.service
    │
    ├─► Ensure required directories exist
    ├─► Set directory permissions
    ├─► Generate versions.env (if versioning enabled)
    ├─► Start Docker containers
    ├─► Wait 15s for containers to stabilize
    ├─► Start background log capture
    └─► Log completion to startup log
```

### Startup Script

The `dkproxy-startup.sh` script:
1. Creates required directories (outpost, cmd_exec, vault)
2. Sets proper permissions for shared volumes
3. Loads version overrides if `version-manifest.yaml` exists
4. Starts containers with `docker compose up -d`
5. Starts background log capture to daily log files

---

## Multi-Proxy Support

You can run multiple proxies on the same system. Each proxy gets a **unique systemd service name** based on its `PROXY_ALIAS`.

### How It Works

The service name is derived from your proxy's `PROXY_ALIAS` in `.env`:

| PROXY_ALIAS | Service Name |
|-------------|--------------|
| `prod-proxy` | `dkproxy-prod-proxy.service` |
| `dev-proxy1` | `dkproxy-dev-proxy1.service` |
| `staging` | `dkproxy-staging.service` |

### Example: Running Multiple Proxies

```bash
# Setup for first proxy (in /opt/proxy1)
cd /opt/proxy1
make setup-autorestart
# Creates: dkproxy-prod-proxy.service

# Setup for second proxy (in /opt/proxy2)
cd /opt/proxy2
make setup-autorestart
# Creates: dkproxy-dev-proxy.service
```

Each proxy:
- Has its own systemd service
- Can be started/stopped independently
- Has its own log capture process
- Has its own startup log file

---

## Systemd Service

### Service Configuration

A single systemd service manages the proxy:

**Service name:** `dkproxy-{PROXY_ALIAS}.service`

**Configuration:**
```ini
[Unit]
Description=DagKnows Proxy Services ({PROXY_ALIAS})
Requires=docker.service
After=docker.service network-online.target

[Service]
Type=oneshot
RemainAfterExit=yes
ExecStart={install_dir}/dkproxy-startup.sh
ExecStop=docker compose down
TimeoutStartSec=120
TimeoutStopSec=60

[Install]
WantedBy=multi-user.target
```

**Key settings:**
- `Type=oneshot` with `RemainAfterExit=yes` - Service stays "active" after startup completes
- `Requires=docker.service` - Ensures Docker is running first
- `TimeoutStartSec=120` - Allows 2 minutes for containers to start

---

## Management Commands

### Using Make (Recommended)

```bash
# Start proxy
make start

# Stop proxy
make stop

# Restart proxy
make restart

# Check auto-restart status
make autorestart-status

# Disable auto-restart
make disable-autorestart
```

The `make start/stop/restart` commands automatically detect if systemd is configured and use the appropriate method.

### Using systemctl Directly

```bash
# Replace {PROXY_ALIAS} with your proxy's alias

# Start services
sudo systemctl start dkproxy-{PROXY_ALIAS}.service

# Stop services
sudo systemctl stop dkproxy-{PROXY_ALIAS}.service

# Restart services
sudo systemctl restart dkproxy-{PROXY_ALIAS}.service

# Check status
sudo systemctl status dkproxy-{PROXY_ALIAS}.service

# View service logs
journalctl -u dkproxy-{PROXY_ALIAS}.service
```

---

## Viewing Logs

### Startup Log

Each proxy has its own startup log:

```bash
# View startup log (replace {PROXY_ALIAS} with your proxy's alias)
cat /var/log/dkproxy-startup-{PROXY_ALIAS}.log

# Or tail for latest entries
tail -50 /var/log/dkproxy-startup-{PROXY_ALIAS}.log
```

Example startup log:
```
2026-01-15 08:30:01 - Starting DagKnows Proxy services
2026-01-15 08:30:01 - Ensuring required directories and permissions...
2026-01-15 08:30:02 - Loading version overrides from versions.env
2026-01-15 08:30:02 - Starting containers...
2026-01-15 08:30:10 - Waiting for containers to stabilize...
2026-01-15 08:30:25 - Starting background log capture
2026-01-15 08:30:26 - Log capture started (PID: 1234)
2026-01-15 08:30:26 - Startup complete
```

### Container Logs

```bash
# Live logs
make logs

# Today's captured logs
make logs-today

# Errors only
make logs-errors

# Specific service
make logs-service SERVICE=outpost
```

### Systemd Journal

```bash
# View systemd journal
journalctl -u dkproxy-{PROXY_ALIAS}.service

# Follow in real-time
journalctl -u dkproxy-{PROXY_ALIAS}.service -f
```

---

## Checking Auto-Restart Status

```bash
make autorestart-status
```

Example output:
```
=== Auto-Restart Status ===
Service name: dkproxy-myproxy.service
Systemd service: INSTALLED
Service enabled: YES
Service active: YES
```

Status meanings:
- **INSTALLED** - Service file exists in systemd
- **enabled** - Service will start on boot
- **active** - Service is currently running

---

## Disabling Auto-Restart

```bash
make disable-autorestart
```

This will:
1. Stop all proxy containers
2. Disable the systemd service
3. Remove the service file
4. Reload systemd daemon

After disabling, you'll need to manually start the proxy with `make start`.

---

## Troubleshooting

### Services Not Starting After Reboot

**Check systemd status:**
```bash
sudo systemctl status dkproxy-{PROXY_ALIAS}.service
```

**Check startup log:**
```bash
cat /var/log/dkproxy-startup-{PROXY_ALIAS}.log
```

**Common issues:**

1. **Docker not running**
   ```bash
   sudo systemctl status docker
   sudo systemctl start docker
   ```

2. **Missing .env file**
   - Ensure `.env` exists in the proxy directory
   - Re-run `dk proxy getenv {proxy_name}` if needed

3. **Permission issues**
   - Check directory ownership matches the proxy installation user

### Root-Owned Log Capture Process

When auto-restart is configured, systemd runs the startup script as root. This means the log capture process is owned by root.

**Symptom:** `make logs-stop` says "Could not stop log capture"

**Solution:**
```bash
# Stop with sudo
sudo kill $(cat logs/.capture.pid)
rm logs/.capture.pid

# Or restart with make (handles this automatically)
make restart
```

### Service File Not Found

If `make autorestart-status` shows "NOT INSTALLED":

```bash
# Check if service file exists
ls -la /etc/systemd/system/dkproxy-*.service

# Re-run setup
make setup-autorestart
```

### Proxy Connection Issues After Restart

If the proxy starts but doesn't connect to DagKnows:

1. Check container status: `make status`
2. Check container logs: `make logs`
3. Verify `.env` has correct `DAGKNOWS_URL` and `PROXY_SESSION_ID`
4. Check network connectivity to DagKnows server

---

## File Locations

| File | Purpose |
|------|---------|
| `/etc/systemd/system/dkproxy-{PROXY_ALIAS}.service` | Systemd service file |
| `/var/log/dkproxy-startup-{PROXY_ALIAS}.log` | Startup script log |
| `{proxy_dir}/dkproxy-startup.sh` | Startup script |
| `{proxy_dir}/dkproxy.service` | Service file template |
| `{proxy_dir}/.env` | Proxy configuration |
| `{proxy_dir}/logs/*.log` | Container log files |
| `{proxy_dir}/logs/.capture.pid` | Log capture process PID |

---

## Security Considerations

Unlike dkapp (which encrypts `.env`), the proxy uses an **unencrypted** `.env` file. This simplifies auto-restart but has security implications:

### Recommendations

1. **File permissions** - Ensure `.env` is readable only by the proxy user:
   ```bash
   chmod 600 .env
   ```

2. **Disk encryption** - Consider using LUKS or similar for the filesystem

3. **Network security** - Use firewalls to restrict access to the proxy server

4. **Token rotation** - Periodically refresh proxy tokens in DagKnows

5. **Physical security** - Ensure the server is physically secure

---

## Command Reference

| Command | Description |
|---------|-------------|
| `make setup-autorestart` | Configure auto-start on boot |
| `make autorestart-status` | Check auto-restart configuration |
| `make disable-autorestart` | Remove auto-restart configuration |
| `make start` | Start proxy (uses systemd if configured) |
| `make stop` | Stop proxy |
| `make restart` | Restart proxy |
| `make status` | Check proxy status |
| `make logs` | View live container logs |

---

## Comparison with dkapp

| Feature | dkapp | dkproxy |
|---------|-------|---------|
| Passphrase handling | 3 options (file, unencrypted, manual) | Not needed (unencrypted .env) |
| Services | 2 (dkapp-db, dkapp) | 1 (dkproxy-{alias}) |
| Multi-instance | Single instance | Multiple proxies supported |
| Service naming | Fixed names | Dynamic based on PROXY_ALIAS |
| Setup complexity | Requires passphrase decision | Fully automatic |
