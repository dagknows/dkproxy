# DK Proxy

The DagKnows proxy runner.   This repo contains a minimal set of compose files for running a DagKnows proxy anywhere.

## Requirements

### Packages

```
apt-get update
apt-get install -y docker.io docker-compose unzip python-pip3
```

## Installation

1. Checkout this repo.

### Install DagKnows CLI

```
pip install dagknows --force-reinstall
```

The CLI has some easy wrappers to interact with DagKnows as well as setting up/upgrading proxies.

Configure the DagKnows cli by providing an access token:

```
dk config init
```

This will ask you for the host where the saas instance is running.   Replace "localhost" with the address of the host where DagKnows is running (this can vary for onprem or custom installations).
You can obtain an access token from the the App's settings page.

### Create a proxy

Once configured you can see what proxies you already have access to with:

```
dk proxy list
```

You can either use an existing proxy or create a new one with:

```
dk proxy new <LABEL>
```

4. Get an env file for your proxy with `dk proxy getenv <LABEL>`

This will install a basic .env file your proxy can use to connect to the SaaS instance.

5. (Optional) Update your proxy

This will let you pull the latest images

6. Run your proxy

```
make up logs
```

