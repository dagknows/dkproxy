# DagKnows Proxy Version Management

This guide explains how to manage Docker image versions for your DagKnows proxy deployment.

---

## TL;DR - Just Tell Me How to Update

**For customers who just want to update to the latest version:**

```bash
make pull-latest           # Pull newest images
make restart               # Restart proxy
```

That's it! Everything else is optional.

---

## What Changed?

| Before | After | Notes |
|--------|-------|-------|
| `make pull` | `make pull` or `make pull-latest` | Still works! |
| `make restart` | `make restart` | Same! |
| No rollback | `make rollback` | **New capability** |
| No version history | `make version` | **New capability** |

**Bottom line:** Your existing workflow (`make pull && make restart`) still works exactly the same. You now have additional rollback and version tracking capabilities.

**Backwards Compatibility:** Proxies without `version-manifest.yaml` can continue using `make pull` and `make pull-latest` exactly as before - no changes required.

---

## Quick Reference

| Action | Command |
|--------|---------|
| Start proxy | `make start` |
| Stop proxy | `make stop` |
| **Pull latest images** | `make pull` or `make pull-latest` |
| **Restart proxy** | `make restart` |
| View current versions | `make version` |
| Rollback a service | `make rollback-service SERVICE=outpost` |
| Rollback all services | `make rollback` |
| View all version commands | `make help-version` |

---

## Command Comparison: Pull vs Update

### `make pull` vs `make pull-latest`

| Command | Behavior | When to Use |
|---------|----------|-------------|
| `make pull` | **Smart pull** - respects version manifest | Normal updates when you want to use tracked versions |
| `make pull-latest` | **Update to latest** - pulls `:latest`, updates manifest | When you want to update to newest images |

**Details:**

- **`make pull`**:
  - If `version-manifest.yaml` exists → pulls the **specific versions** from manifest
  - If no manifest → pulls `:latest` for all services (backwards compatible)
  - **Use this** when you want to maintain version consistency

- **`make pull-latest`**:
  - Pulls `:latest` for all services
  - If manifest exists: **updates manifest** and optionally **resolves semantic tags** from ECR
  - If no manifest: just pulls images (backwards compatible)
  - **Use this** when you want to update to newest images

### `make update` vs `make update-safe`

| Command | What It Does | Safety Features |
|---------|-------------|----------------|
| `make update` | `down` → `pull` → `build` | No backup, no rollback |
| `make update-safe` | Pulls latest → Creates backup → Restarts → Health checks | Backup, rollback on failure |

**Details:**

- **`make update`**:
  - Stops services, pulls images, rebuilds
  - No automatic backup
  - **Use this** for development

- **`make update-safe`**:
  - Creates backup of manifest
  - Pulls `:latest` for all services
  - Resolves tags from ECR (if AWS CLI configured)
  - Auto-rollback if issues detected
  - **Use this** for production updates

### Quick Decision Guide

**I want to...**
- **Update to latest images (simple)** → `make pull-latest` then `make restart`
- **Update to latest images (with backup)** → `make update-safe`
- **Rebuild from source** → `make update` then `make start`
- **Pull specific versions from manifest** → `make pull` then `make restart`

---

## How It Works

The versioning system uses two files:

1. **`version-manifest.yaml`** - Tracks all service versions, history, and **image digests**
2. **`versions.env`** - Auto-generated environment variables for docker-compose

**Important:** Even when a tag is `latest`, the manifest stores the **image digest** (SHA256 hash). This uniquely identifies the exact image version, enabling reliable rollbacks.

Example from manifest:
```yaml
services:
  outpost:
    current_tag: latest
    image_digest: 'sha256:cbd982440a966d1b814c7853caa89c430f0ddc0f...'  # Exact image ID
```

When you run `make start`, the system:
1. Reads `version-manifest.yaml`
2. Generates `versions.env` with the correct image tags
3. Starts containers with the specified versions

---

## Initial Setup (Migration)

If you have an existing proxy deployment using `:latest` tags:

```bash
# 1. Make sure proxy is running
make status

# 2. Run the migration wizard
make migrate-versions

# 3. Follow the prompts (press Enter for defaults)

# 4. Restart to apply version tracking
make restart
```

Or use the interactive setup:
```bash
make setup-versioning
```

After migration, you'll have:
- `version-manifest.yaml` - tracking your versions
- `versions.env` - environment file for docker-compose

---

## Starting and Stopping the Proxy

### Start Proxy
```bash
make start
```

This command:
- Generates `versions.env` from manifest (if exists)
- Starts all containers
- Starts background log capture

### Stop Proxy
```bash
make stop
```

This stops all containers and log capture.

### Restart Proxy
```bash
make restart
```

Equivalent to `make stop && make start`.

### View Logs
```bash
# Follow live logs
make logs

# View today's captured logs
make logs-today

# View errors only
make logs-errors
```

---

## Updating All Images (Most Common)

This is the typical workflow for updating your proxy:

```bash
# 1. Pull latest images for all services
make pull-latest

# 2. Restart the proxy
make restart

# 3. Verify everything is working
make status
make logs
```

Or use the safe update which includes backup:

```bash
make update-safe
```

This will:
1. Create a backup of current manifest
2. Pull `:latest` for all services
3. Restart the proxy
4. Show status

---

## Rollback

Rollback uses the **version history** stored in the manifest. Each service tracks its last 5 deployments.

### How Rollback Works

When you rollback, the system:
1. Looks up the **previous tag** from history
2. Pulls that specific version
3. **Automatically updates** `version-manifest.yaml` and `versions.env`

You just need to restart: `make restart`

**Note:** The manifest also stores image digests (SHA256), which uniquely identify each image even when the tag is `latest`.

### Rollback Single Service
```bash
# Rollback to previous version
make rollback-service SERVICE=outpost

# Apply
make restart
```

### Rollback to Specific Version
```bash
make rollback-to SERVICE=outpost TAG=1.41
make restart
```

### Rollback All Services
```bash
make rollback
make restart
```

**Note:** Rollback only affects services that have a **different** previous version. If a service's current and previous versions are the same, it won't appear in the rollback list.

### View Rollback History
```bash
# See what versions are available for rollback
make version-history SERVICE=outpost
```

Example output:
```
outpost:
  latest              2026-01-12T12:29:08  [current]
  1.63                2026-01-12T12:20:31  [previous]  ← Can rollback to this
```

---

## Advanced: Single Service Updates

### `make version-pull` vs `make rollback-service`

| Command | What It Does | When to Use |
|---------|-------------|-------------|
| `make version-pull SERVICE=x TAG=y` | Pulls **any version** you specify, updates manifest & env | When you know the exact version you want |
| `make rollback-service SERVICE=x` | Pulls the **previous version** from history, updates manifest & env | When you want to undo the last change |

**Both commands:**
- Pull the image
- Update `version-manifest.yaml`
- Update `versions.env`
- Add entry to version history
- Require `make restart` to apply

**Example:**

```bash
# Pull a specific version (forward or backward)
make version-pull SERVICE=outpost TAG=1.42
make restart

# Rollback to previous version (automatic)
make rollback-service SERVICE=outpost
make restart
```

### Pull Specific Version

For hotfixes or testing specific versions of individual services:

```bash
# Pull specific version for one service
make version-pull SERVICE=outpost TAG=1.42

# Apply
make restart
```

### Custom Hotfix Versions

For customer-specific patches:

```bash
# Set a custom tag
make version-set SERVICE=outpost TAG=1.42-hotfix-customer123

# Apply
make restart
```

Custom versions are tracked separately and shown with `[custom]` in status.

---

## Viewing Version Information

```bash
# Show current versions
make version

# Show version history
make version-history

# Show history for specific service
make version-history SERVICE=outpost

# Check for updates
make check-updates
```

---

## Troubleshooting

### Services won't start after version change

```bash
# Check logs for errors
make logs

# Verify versions.env is correct
cat versions.env

# Regenerate versions.env from manifest
make generate-env

# Try restarting
make restart
```

### Manifest is corrupted

```bash
# List backups
ls -la .version-backups/

# Restore from backup
cp .version-backups/version-manifest.yaml.YYYYMMDDHHMMSS version-manifest.yaml

# Regenerate env
make generate-env
```

### Running without version management

The proxy still works without `version-manifest.yaml`:

```bash
# Remove version files (optional)
rm version-manifest.yaml versions.env

# Start normally - uses :latest for all
make restart
```

---

## AWS CLI Configuration (For Tag Resolution)

To resolve `latest` tags to semantic versions, you need AWS CLI configured with ECR access.

### Setup

```bash
# Install AWS CLI (if not installed)
pip install awscli
# or
sudo apt install awscli

# Configure with provided credentials
aws configure
# Enter:
#   AWS Access Key ID: <provided by DagKnows>
#   AWS Secret Access Key: <provided by DagKnows>
#   Default region: us-east-1
#   Default output format: json
```

### Required IAM Permissions

The AWS credentials need only ECR read access:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ecr-public:DescribeImages",
        "ecr-public:DescribeRepositories"
      ],
      "Resource": "*"
    }
  ]
}
```

### Verify Access

```bash
# Test ECR access
aws ecr-public describe-images --repository-name outpost --region us-east-1 --max-results 1
```

### Resolve Tags

After configuring AWS CLI:
```bash
make resolve-tags   # Query ECR and update manifest with real versions
```

---

## File Locations

| File | Purpose |
|------|---------|
| `version-manifest.yaml` | Version tracking database |
| `versions.env` | Auto-generated env vars (DO NOT EDIT) |
| `.version-backups/` | Automatic backups before changes |

### Which Commands Auto-Update Files?

| Command | Updates Manifest? | Updates versions.env? |
|---------|-------------------|----------------------|
| `make pull-latest` | Yes | Yes |
| `make version-pull SERVICE=x TAG=y` | Yes | Yes |
| `make rollback` | Yes | Yes |
| `make rollback-service SERVICE=x` | Yes | Yes |
| `make rollback-to SERVICE=x TAG=y` | Yes | Yes |
| `make version-set SERVICE=x TAG=y` | Yes | Yes |
| `make update-safe` | Yes | Yes |
| `make pull` | No (uses existing) | No |
| `make generate-env` | No | Yes (regenerates from manifest) |

---

## Available Services

These services can be independently versioned:

| Service | Description | Image Source |
|---------|-------------|--------------|
| `outpost` | Proxy orchestration - manages proxy connections and command routing | ECR (public.ecr.aws) |
| `cmd_exec` | Command execution - runs commands on target systems | ECR (public.ecr.aws) |
| `vault` | HashiCorp Vault - secrets management | Docker Hub |

---

## Example Workflows

### Standard Update (Most Common)

Update all services to latest versions:

```bash
# 1. Check current versions
make version

# 2. Pull latest images
make pull-latest

# 3. Restart
make restart

# 4. Verify
make status
make logs
```

### Update with Backup (Recommended for Production)

```bash
# This creates backup, pulls latest, and restarts
make update-safe
```

### Rollback After Bad Update

```bash
# 1. See what previous versions are available
make version-history

# 2. Rollback all services
make rollback
make restart

# Or rollback just one problematic service
make rollback-service SERVICE=outpost
make restart
```

### Test a Specific Service Version

```bash
# Pull specific version
make version-pull SERVICE=outpost TAG=1.42
make restart

# If it works, keep it. If not, rollback:
make rollback-service SERVICE=outpost
make restart
```

### Hotfix for Customer Issue

```bash
# Pull a customer-specific hotfix
make version-set SERVICE=cmd_exec TAG=1.15-hotfix-acme

# Apply
make restart

# Later, return to standard version
make version-pull SERVICE=cmd_exec TAG=1.15
make restart
```

---

## Command Aliases

For convenience, these aliases are available:

| Alias | Equivalent |
|-------|------------|
| `make upgrade` | `make update-safe` |
| `make downgrade` | `make rollback` |
| `make whatversion` | `make version` |
