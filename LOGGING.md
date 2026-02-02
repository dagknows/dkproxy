# DagKnows Proxy Logging Guide

This guide explains how logging works in dkproxy and how to use it for debugging and monitoring.

## Quick Start

```bash
# Start the proxy (logging starts automatically)
make start       # Start services + auto-starts background log capture

# View live logs when needed
make logs        # Real-time log stream (Ctrl+C to exit)

# Check captured logs
make logs-today  # View today's logs
make logs-errors # View errors only
```

## How It Works

When you run `make start`, two things happen:
1. Proxy services start in Docker containers (outpost, cmd-exec, vault)
2. Background log capture automatically starts

Logs are captured to `./logs/YYYY-MM-DD.log` (e.g., `./logs/2026-01-10.log`).

All services are logged together chronologically, making it easy to trace issues across services.

## Log Commands

### Viewing Logs

| Command | Description |
|---------|-------------|
| `make logs` | View live logs (last 300 lines + follow) |
| `make logs-today` | View today's captured logs |
| `make logs-errors` | Show only error/exception/fail lines |
| `make logs-service SERVICE=outpost` | Filter to specific service |
| `make logs-search PATTERN='text'` | Search for pattern in logs |

### Managing Log Capture

| Command | Description |
|---------|-------------|
| `make logs-start` | Manually start background capture |
| `make logs-stop` | Stop background capture |
| `make logs-status` | Show log directory size and files |

### Log Maintenance

| Command | Description |
|---------|-------------|
| `make logs-rotate` | Compress logs >3 days, delete >7 days |
| `make logs-clean` | Delete all captured logs (with confirmation) |
| `make logs-cron-install` | Setup daily auto-rotation at midnight |
| `make logs-cron-remove` | Remove auto-rotation cron job |

## Log File Format

Logs are stored in `./logs/` with one file per day:

```
./logs/
  2026-01-10.log      # Today's logs
  2026-01-09.log      # Yesterday's logs
  2026-01-08.log.gz   # Compressed older logs
```

Each log line includes the service name prefix:

```
outpost-1    | 2026-01-10 14:30:00 INFO Connected to DagKnows server
cmd-exec-1   | 2026-01-10 14:30:01 INFO Command execution service ready
vault-1      | 2026-01-10 14:30:01 INFO Vault server started
outpost-1    | 2026-01-10 14:30:05 INFO Received command request
cmd-exec-1   | 2026-01-10 14:30:05 ERROR Failed to execute command: timeout
```

## Proxy Services

The dkproxy consists of 3 services:

| Service | Description |
|---------|-------------|
| `outpost` | Main proxy service - handles communication with DagKnows server |
| `cmd-exec` | Command execution service - runs commands on target systems |
| `vault` | HashiCorp Vault - manages secrets and credentials |

## Startup Procedure

### Standard Startup

```bash
# Start proxy (auto-starts log capture)
make start

# View live logs if needed
make logs        # Ctrl+C to exit (capture continues in background)
```

### After Restart/Reboot

```bash
# Simply run make start again
make start
```

### With Auto-Restart Configured

If you've run `make setup-autorestart`, services start automatically on boot:
- Proxy services start via systemd
- Log capture starts automatically
- Use `make start/stop/restart` for manual control
- Logs go to `./logs/YYYY-MM-DD.log` as usual

### Checking Status

```bash
# Check if services are running
make status

# Check if log capture is running
make logs-status

# View any errors
make logs-errors
```

## Debugging with Logs

### Find Errors

```bash
# Show all errors from captured logs
make logs-errors

# Search for specific error
make logs-search PATTERN='connection refused'
```

### Filter by Service

```bash
# View only outpost logs
make logs-service SERVICE=outpost

# View only cmd-exec logs
make logs-service SERVICE=cmd-exec

# View only vault logs
make logs-service SERVICE=vault
```

### Search for Patterns

```bash
# Find all connection-related logs
make logs-search PATTERN='connection'

# Find specific command executions
make logs-search PATTERN='executing'

# Find authentication issues
make logs-search PATTERN='auth'
```

### Using grep Directly

For more complex searches, use grep on the log files:

```bash
# Find errors around a specific time
grep "14:30" ./logs/2026-01-10.log | grep -i error

# Count errors per service
grep -i error ./logs/2026-01-10.log | cut -d'|' -f1 | sort | uniq -c

# Find last 50 errors
grep -i error ./logs/2026-01-10.log | tail -50

# View context around an error (5 lines before/after)
grep -B5 -A5 "Connection timeout" ./logs/2026-01-10.log
```

## Log Retention Policy

| Age | Action |
|-----|--------|
| 0-3 days | Kept as `.log` (uncompressed) |
| 3-7 days | Compressed to `.log.gz` |
| 7+ days | Deleted |

### Manual Rotation

```bash
make logs-rotate
```

### Automatic Rotation (Recommended)

Use the interactive setup wizard:

```bash
make setup-log-rotation
```

This wizard:
- Shows current log disk usage
- Explains the retention policy
- Installs a cron job for daily rotation at midnight
- Uses PROXY_ALIAS for unique cron job identification (supports multiple proxies)

Or use the direct commands:

```bash
make logs-cron-install   # Setup cron job
crontab -l               # Verify installation
make logs-cron-remove    # Remove if needed
```

## Storage Estimates

| Timeframe | Size |
|-----------|------|
| Per day (uncompressed) | 20-100 MB |
| Per day (compressed) | 5-20 MB |
| 7-day retention total | ~150-400 MB |

Check current usage:

```bash
make logs-status
```

## Troubleshooting

### Log capture not running

```bash
# Check if capture is running (uses PID file)
cat ./logs/.capture.pid 2>/dev/null && echo "PID file exists"

# Manually start if needed
make logs-start
```

### Logs not appearing

```bash
# Check if services are running
docker compose ps

# Check log file exists
ls -la ./logs/

# Try viewing live logs
make logs
```

### Disk space issues

```bash
# Check log size
make logs-status

# Force rotation
make logs-rotate

# Or clean all logs
make logs-clean
```

### Multiple log capture processes

```bash
# Stop all capture processes
make logs-stop

# Start fresh
make logs-start
```

### Log capture started by systemd (root-owned)

If auto-restart is configured, log capture may be started by systemd as root.
The `make logs-stop` command handles this automatically by using sudo if needed:

```bash
# This works even for root-owned processes
make logs-stop
```

### Proxy not connecting to DagKnows server

```bash
# Check outpost logs for connection errors
make logs-service SERVICE=outpost

# Look for specific connection issues
make logs-search PATTERN='DAGKNOWS_URL'
make logs-search PATTERN='connection'
```
