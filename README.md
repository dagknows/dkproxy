# DK Proxy

The DagKnows proxy runner.   This repo contains a minimal set of compose files for running a DagKnows proxy anywhere.

## Requirements

You will need the following:

* One of the linux distros:
  * Ubuntu 22.04+
  * Amazon Linux 2023+
  * RedHat
* git
* python (3.10+)

## Setup your Environment

### Checkout this repo.

```
git clone https://github.com/dagknows/dkproxy.git
```

### Install required packages

Run the following installer.  It will setup all the dependencies needed to run your proxy.

```
cd dkproxy
sh install.sh

# This logs you out so you can log back in - this is needed because current user was
# added to the docker group and a logout/login is needed for this to take effect.
exit  
```

### Configure DagKnows CLI

The above installation script also installs the dagknows cli.  The CLI has some easy wrappers to interact with DagKnows as well as setting up/upgrading proxies.  Configure the DagKnows cli by providing an access token.  This will ask you for the host where the saas instance is running.   Replace "localhost" with the address of the host where DagKnows is running (this can vary for onprem or custom installations).  You can obtain an access token from the the App's settings page.

```
dk config init
```


### Install your Proxy

You can directly install a proxy with:

```
sh install_proxy.sh {{PROXY_NAME}}

eg:

sh install_proxy.sh myproxy
```

## Run your proxy

```
make up logs
```

## (Optional) Update your proxy

To update your proxy, simply do:

```
make update up logs
```
