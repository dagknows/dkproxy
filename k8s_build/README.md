# Dagknows Proxy setup instructions for Kubernetes

## Install Helm

Download helm:

```
curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash
```

## Install Dagknows CLI


The CLI has some easy wrappers to interact with DagKnows as well as setting up/upgrading proxies.  Configure the DagKnows cli by providing an access token.

```
pip install dagknows --force-reinstall
```

## Setup/Configure your Kubernetes Cluster

### Minikube Setup (if testing on MK)

#### Download and Install

Follow this - https://minikube.sigs.k8s.io/docs/start/

Shows you how to install on various platfomrs

#### Start Minikube

```
minikube start
```

### K8S Setup


* Make sure your cluster is running.
* You will need to set this in the EKS_CLUSTER_NAME in either .env or the .params file (down below).
* Setup an EFS mount as well as 6 Access Points for storing the jobs/keys/logs/output/artifacts for cmdexec, outpost and vault.

The above will ensure that our proxy can be deployed on this cluster and use the mounts correctly (when we are in the deploy step).

## Initialize a Proxy

Ensure you are in the k8s_build folder (this folder).

Assuming you have setup your DK cli from [here](https://github.com/dagknows/dkproxy/blob/main/README.md), do the following:

### Create a new proxy (optional - you can an existing one too)

```
dk proxy new <YOUR_PROXY_ALIAS>
```

### Get the configs for the proxy you want to run

```
dk proxy getenv <YOUR_PROXY_ALIAS>
```

The above will download an `.env` file to the current folder

### Now Initialize the k8s proxy with:

The PATH_TO_DOT_ENV_FILE is where the `.env` file will be downloaded to (in the `getenv` step). You can have an additional .params file that stores more details about your cluster setup (this is usually stuff that wont be in the .env file).  See the `default_params` files for an example.

If you do not specify the `<PROXY_FOLDER>` the proxy will be installed in `./proxies/<YOUR_PROXY_ALIAS>` folder.

```
dk proxy initk8s <PATH_TO_DOT_ENV_FILE> <PATH_TO_DOT_PARAMS_FILE> <PROXY_FOLDER> --storage-type=[local|multiefs]
```

## Start your proxy

Go into the newly created proxy folder 

```
cd ./proxies/<YOUR_PROXY_ALIAS>
```

## Create your namespace

Regardless of whether you are on minikube or EKS you have to create a namespace for the proxy on your cluster.   This step also only need to be run once per proxy.

```
sh namespace.sh
```

## Setup any access-control and policies

Usually a bunch of roles may need to be created.  And this can also be cluster specific.  Dont worry this is all abstracted in the generated policies.sh file which is created when you run `dk proxy initk8s` above:

```
sh policies.sh
```

## Setup your storage

### Minikube Specific Setup - Mount local folders on minikube

Now ensure minikube has mounted the above created local folders so they are visible to your pods on the MK cluster.  This step only needs to be run once (per proxy install).

```
sh mkmount.sh
```

You should see something like the below.   Do not kill this process - open in a new window if necessary (or run as a daemon mode if you are running on a seperate VM).

```
 % sh mkmounts.sh
📁  Mounting host path /Users/dkproxy/k8s_build/sridaily/localpv into VM as /minikubemount ...
    ▪ Mount type:   9p
    ▪ User ID:      docker
    ▪ Group ID:     docker
    ▪ Version:      9p2000.L
    ▪ Message Size: 262144
    ▪ Options:      map[]
    ▪ Bind Address: 127.0.0.1:52825
🚀  Userspace file server: ufs starting
✅  Successfully mounted /Users/dkproxy/k8s_build/sridaily/localpv to /minikubemount

📌  NOTE: This process must stay alive for the mount to be accessible ...
```

### Start your Storage

You can setup your storage (storage classes, PVCs, PVs etc) with the command below.  Note that this file is also generated as part of the `dk proxy initk8s` command.   There you can choose whether you want to do local or efs etc.

```
sh storage.sh
```

## Start your cluster!

Once your namespace, policies and storage is setup you can start your cluster:

```
sh apply.sh
```

## Destroying your proxy

To remove *ALL* resources associated with your proxy cluster do:

```
sh deleteall.sh
```
