
# Apply the namespace on the given namespace
kubectl apply -f namespace.yaml

# Use 
kubectl -n {{PROXY_NAMESPACE}} create secret generic com.dagknows.secret.frontend --from-env-file=./.env

# Create the vault too
kubectl -n {{PROXY_NAMESPACE}} create configmap vault-configs --from-file=./vault/config/
#
# For Vault certificates
kubectl -n {{PROXY_NAMESPACE}} create secret generic vault-keys \
    --from-file=vault.crt=./vault/config/ssl/vault.crt \
    --from-file=vault.key=./vault/config/ssl/vault.key

# Create local PVs if we are in local PV mode - otherwise if we are in say efs do somethign else!
LOCAL_PV_ROOT={{LOCAL_PV_ROOT}}
MINIKUBE_MOUNT_ROOT={{MINIKUBE_MOUNT_ROOT}}
# minikube mount ${LOCAL_PV_ROOT}:${MINIKUBE_MOUNT_ROOT} & 

mkdir -p ${LOCAL_PV_ROOT}/vault/data
# minikube mount ${LOCAL_PV_ROOT}/vault/data:/vault/data &

echo "Creating local PV folders for cmd-exec..."
mkdir -p ${LOCAL_PV_ROOT}/cmd-exec/keys
mkdir -p ${LOCAL_PV_ROOT}/cmd-exec/logs
kubectl apply -f cmd-exec-storageclass.yaml -n {{PROXY_NAMESPACE}}
kubectl apply -f cmd-exec-localpvs.yaml -n {{PROXY_NAMESPACE}}
kubectl apply -f cmd-exec-pvcs.yaml -n {{PROXY_NAMESPACE}}

echo "Creating local PV folders for outpost..."
mkdir -p ${LOCAL_PV_ROOT}/outpost/jobs
mkdir -p ${LOCAL_PV_ROOT}/outpost/logs
mkdir -p ${LOCAL_PV_ROOT}/outpost/sidecar
if [ ! -f $LOCAL_PV_ROOT/outpost/jobs/daglib.py ]; then
  cp daglib.py  $LOCAL_PV_ROOT/outpost/jobs/daglib.py 
fi
kubectl apply -f outpost-storageclass.yaml -n {{PROXY_NAMESPACE}}
kubectl apply -f outpost-localpvs.yaml -n {{PROXY_NAMESPACE}}
kubectl apply -f outpost-pvcs.yaml -n {{PROXY_NAMESPACE}}

kubectl apply -f vault.yaml -n {{PROXY_NAMESPACE}}
kubectl apply -f cmd-exec-main.yaml -n {{PROXY_NAMESPACE}}
kubectl apply -f outpost-main.yaml -n {{PROXY_NAMESPACE}}
