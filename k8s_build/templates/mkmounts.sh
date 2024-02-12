
LOCAL_PV_ROOT={{LOCAL_PV_ROOT}}
MINIKUBE_MOUNT_ROOT={{MINIKUBE_MOUNT_ROOT}}
minikube mount ${LOCAL_PV_ROOT}:${MINIKUBE_MOUNT_ROOT}

# mkdir -p ${LOCAL_PV_ROOT}/vault/data
# minikube mount ${LOCAL_PV_ROOT}/vault/data:/vault/data &
