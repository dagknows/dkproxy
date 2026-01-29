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

### View logs
```bash
make logs
```

### Stop proxy
```bash
make stop
```

### Update proxy
```bash
make update
make start
```
