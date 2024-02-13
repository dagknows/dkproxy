# Create local PVs if we are in local PV mode - otherwise if we are in say efs do somethign else!

LOCAL_PV_ROOT={{LOCAL_PV_ROOT}}
MINIKUBE_MOUNT_ROOT={{MINIKUBE_MOUNT_ROOT}}

echo "Creating local PV folders for vault..."
mkdir -p ${LOCAL_PV_ROOT}/vault/data
kubectl apply -f vault-storageclass-local.yaml
kubectl apply -f vault-pv-local.yaml
kubectl apply -f vault-pvcs-local.yaml -n {{PROXY_NAMESPACE}}

echo "Creating local PV folders for cmd-exec..."
mkdir -p ${LOCAL_PV_ROOT}/cmd-exec/keys
mkdir -p ${LOCAL_PV_ROOT}/cmd-exec/logs
kubectl apply -f cmd-exec-storageclass-local.yaml
kubectl apply -f cmd-exec-pv-local.yaml
kubectl apply -f cmd-exec-pvcs-local.yaml -n {{PROXY_NAMESPACE}}

echo "Creating local PV folders for outpost..."
mkdir -p ${LOCAL_PV_ROOT}/outpost/jobs
mkdir -p ${LOCAL_PV_ROOT}/outpost/logs
mkdir -p ${LOCAL_PV_ROOT}/outpost/sidecar
kubectl apply -f outpost-storageclass-local.yaml
kubectl apply -f outpost-pv-local.yaml
kubectl apply -f outpost-pvcs-local.yaml -n {{PROXY_NAMESPACE}}
