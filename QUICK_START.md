# DagKnows Proxy - Quick Start Guide

## Installation in 3 Commands

```bash
git clone https://github.com/dagknows/dkproxy.git
cd dkproxy
python3 install.py
```

That's it! The wizard handles everything else.

## What the Wizard Does

```
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│  DagKnows Proxy Installation Wizard                         │
│                                                             │
└─────────────────────────────────────────────────────────────┘

Step 1: Pre-flight Checks
  ✓ Detect OS (Ubuntu/Amazon Linux/RHEL)
  ✓ Check internet connectivity

Step 2: Install Dependencies
  ✓ Run install.sh for your OS
  ✓ Install Docker, make, Python tools
  ✓ Add user to docker group

Step 3: Setup Docker
  ✓ Start Docker service
  ✓ Handle group permissions

Step 4: Python Virtual Environment
  ✓ Create ~/dkenv
  ✓ Install dagknows CLI
  ✓ Verify installation

Step 5: Configure DagKnows CLI
  → Enter DagKnows server URL (HTTPS)
  → Authenticate with credentials

Step 6: Create Proxy
  → Enter proxy name (alphanumeric only)
  ✓ Create proxy using dk CLI

Step 7: Pull Docker Images
  ✓ Download proxy images
  ✓ Avoid ECR rate limits

Step 8: Start Proxy
  ✓ Start containers
  ✓ Show logs

Step 9: Post-Installation Instructions
  ✓ Next steps for proxy configuration
  ✓ Useful commands
```

## What You'll Be Asked

1. **DagKnows Server URL**
   - Example: `https://your-dagknows-server.com`
   - Must be HTTPS (even for IP addresses)

2. **Authentication**
   - Token or credentials for your DagKnows instance

3. **Proxy Name**
   - Alphanumeric only (e.g., "myproxy", "prod01")
   - No spaces or special characters

## After Installation

### View Proxy Logs
```bash
make logs
```

### Stop Proxy
```bash
make down
```

### Start Proxy
```bash
make up
```

### Update Proxy
```bash
make update up logs
```

## Configure in DagKnows Web UI

### 1. Create Proxy Role
Settings → Proxies → Add Role (e.g., "admin")

### 2. Assign Role to User
User Management → Select User → Modify Settings → Assign Proxy Role

### 3. Enable Settings (Optional)
Adjust Settings → Enable "Auto Exec" and "Send Execution Result to LLM"

### 4. Test Proxy
Create Runbook → Add Command → Execute on Proxy

## Troubleshooting

### Docker Permission Issues
```bash
newgrp docker
```
Or log out and back in.

### DagKnows CLI Not Found
```bash
source ~/dkenv/bin/activate
dk version
```

### Re-run Wizard
The wizard can be safely re-run. It will detect existing installations and let you reconfigure.

## Getting Help

- **Full Documentation**: See `README.md`
- **Wizard Details**: See `INSTALLATION_WIZARD.md`
- **Changes**: See `CHANGES_SUMMARY.md`

## Manual Installation

If you prefer manual installation, see the "Method 2: Manual Installation" section in `README.md`.

