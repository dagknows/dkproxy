# Create local PVs if we are in local PV mode - otherwise if we are in say efs do somethign else!

LOCAL_PV_ROOT={{LOCAL_PV_ROOT}}
MINIKUBE_MOUNT_ROOT={{MINIKUBE_MOUNT_ROOT}}

echo "Creating local PV folders for cmd-exec..."
mkdir -p ${LOCAL_PV_ROOT}/cmd-exec/keys
mkdir -p ${LOCAL_PV_ROOT}/cmd-exec/logs
kubectl apply -f cmd-exec-storageclass.yaml -n {{PROXY_NAMESPACE}}
kubectl apply -f cmd-exec-localpvs.yaml -n {{PROXY_NAMESPACE}}

echo "Creating local PV folders for outpost..."
mkdir -p ${LOCAL_PV_ROOT}/outpost/jobs
mkdir -p ${LOCAL_PV_ROOT}/outpost/logs
mkdir -p ${LOCAL_PV_ROOT}/outpost/sidecar
if [ ! -f $LOCAL_PV_ROOT/outpost/jobs/daglib.py ]; then
  cp daglib.py  $LOCAL_PV_ROOT/outpost/jobs/daglib.py 
fi
kubectl apply -f outpost-storageclass.yaml -n {{PROXY_NAMESPACE}}
kubectl apply -f outpost-localpvs.yaml -n {{PROXY_NAMESPACE}}
