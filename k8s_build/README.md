
## Install Dagknows CLI

```
pip install dagknows --force-reinstall
```

The CLI has some easy wrappers to interact with DagKnows as well as setting up/upgrading proxies.

Configure the DagKnows cli by providing an access token:

## Minikube Setup (if testing on MK)


### Download and Install

Follow this - https://minikube.sigs.k8s.io/docs/start/

Shows you how to install on various platfomrs

### Start Minikube

```
minikube start
```

## K8S Setup

TBD

## Initialize a Proxy

Ensure you are in the k8s_build folder (this folder).

Assuming you have setup your DK cli from [here](https://github.com/dagknows/dkproxy/blob/main/README.md), do the following:

1. Create a new proxy (optional - you can an existing one too)

```
dk proxy new <YOUR_PROXY_NAME>
```

2. Get the configs for the proxy you want to run:

```
dk proxy getenv <YOUR_PROXY_NAME>
```

The above will download an `.env` file to [the](the) current folder

3. Now Initialize the k8s proxy with:

```
`dk proxy initk8s <PATH_TO_DOT_ENV_FILE>`
```

The PATH_TO_DOT_ENV_FILE is where the `.env` file was downloaded in the step 2 (getenv)

This will setup your proxy in `./proxies/<YOUR_PROXY_NAME>` folder

## Start your proxy

Go into the newly created proxy folder 

```
cd `./proxies/<YOUR_PROXY_NAME>`
```

### Minikube Specific Setup - Mount local folders on minikube

If you are running this on minikube then ensure minikube has mounted a few local folders so they are visible to your pods on the MK cluster.
This step only needs to be run once (per proxy install).

```
sh mkmount.sh
```

### K8S Specific Setup

TBD

### Start your cluster!

```
sh.apply.sh
```

## Destroying your proxy

To remove *ALL* resources associated with your proxy cluster do:

```
sh deleteall.sh
```
