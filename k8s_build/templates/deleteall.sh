kubectl delete namespace {{PROXY_NAMESPACE}}
kubectl delete pv {{PROXY_NAMESPACE}}-cmd-exec-keys-volume
kubectl delete pv {{PROXY_NAMESPACE}}-cmd-exec-logs-volume
kubectl delete pv {{PROXY_NAMESPACE}}-outpost-jobs-volume
kubectl delete pv {{PROXY_NAMESPACE}}-outpost-logs-volume
kubectl delete pv {{PROXY_NAMESPACE}}-outpost-sidecar-volume
kubectl delete pv {{PROXY_NAMESPACE}}-vault-data-volume

kubectl delete sc {{PROXY_NAMESPACE}}-efs-storageclass-cmd-exec-logs
kubectl delete sc {{PROXY_NAMESPACE}}-efs-storageclass-cmd-exec-keys
kubectl delete sc {{PROXY_NAMESPACE}}-efs-storageclass-outpost-jobs
kubectl delete sc {{PROXY_NAMESPACE}}-efs-storageclass-outpost-logs
kubectl delete sc {{PROXY_NAMESPACE}}-efs-storageclass-outpost-sidecar
kubectl delete sc {{PROXY_NAMESPACE}}-efs-storageclass-vault-data

kubectl delete pvc --all -n {{PROXY_NAMESPACE}}
kubectl delete all --all -n {{PROXY_NAMESPACE}}
