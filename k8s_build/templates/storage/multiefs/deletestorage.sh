
# delete pvcs
kubectl delete pvc outpost-jobs-pvc -n {{PROXY_NAMESPACE}}
kubectl delete pvc outpost-logs-pvc -n {{PROXY_NAMESPACE}}
kubectl delete pvc outpost-sidecar-pvc -n {{PROXY_NAMESPACE}}
kubectl delete pvc cmd-exec-logs-pvc -n {{PROXY_NAMESPACE}}
kubectl delete pvc cmd-exec-keys-pvc -n {{PROXY_NAMESPACE}}
kubectl delete pvc vault-data-pvc -n {{PROXY_NAMESPACE}}

# del individual pvs on efs
kubectl delete pv {{PROXY_NAMESPACE}}-cmdexec-logs-volume
kubectl delete pv {{PROXY_NAMESPACE}}-cmdexec-keys-volume
kubectl delete pv {{PROXY_NAMESPACE}}-outpost-logs-volume
kubectl delete pv {{PROXY_NAMESPACE}}-outpost-jobs-volume
kubectl delete pv {{PROXY_NAMESPACE}}-outpost-sidecar-volume
kubectl delete pv {{PROXY_NAMESPACE}}-vault-data-volume

# Delete each common storage class
kubectl delete sc {{PROXY_NAMESPACE}}-efs-storageclass
