# DK Proxy

The DagKnows proxy runner.   This repo contains a minimal set of compose files for running a DagKnows proxy anywhere.

## Installation

### Basic Requirements

1. Ensure you have git and Docker installed

2. Checkout this repo.

3. Install the DagKnows CLI

```
pip install dagknows
```

The CLI has some easy wrappers to interact with DagKnows as well as setting up/upgrading proxies.

### Create a proxy

You can see what proxies you already have access to with:

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

