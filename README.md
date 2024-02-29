# DK Proxy

The DagKnows proxy runner.   This repo contains a minimal set of compose files for running a DagKnows proxy anywhere.

## Requirements

You will need the following:

* git
* python (3.10+)

## Installation

### Checkout this repo.

```
git clone https://github.com/dagknows/dkproxy.git
```

### Prepare Instance

Ubuntu:

Run the following installer.  It will setup all the dependencies needed to run your proxy.

```
cd dkproxy && sh install.sh
```

### Configure DagKnows CLI

The above installation script also installs the dagknows cli.  The CLI has some easy wrappers to interact with DagKnows as well as setting up/upgrading proxies.  Configure the DagKnows cli by providing an access token:

```
dk config init
```

This will ask you for the host where the saas instance is running.   Replace "localhost" with the address of the host where DagKnows is running (this can vary for onprem or custom installations).  You can obtain an access token from the the App's settings page.

### Create or Use a proxy

Once configured you can see what proxies you already have access to with:

```
dk proxy list
```

You can either use an existing proxy or create a new one with:

```
dk proxy new <LABEL>
```

#### Or Install proxy's envfile.

If you want to use an existing proxy, you can run the following command to get a particular existing proxy's env vars which will be saved into an .env file.    This will install a basic .env file your proxy can use to connect to the SaaS instance.

```
dk proxy getenv <LABEL>
```

### (Optional) Update your proxy

This will let you pull the latest images

### Run your proxy

```
make up logs
```

