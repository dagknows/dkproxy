kubectl delete namespace {{PROXY_NAMESPACE}}
kubectl delete pv {{PROXY_NAMESPACE}}-cmd-exec-keys-volume
kubectl delete pv {{PROXY_NAMESPACE}}-cmd-exec-logs-volume
kubectl delete pv {{PROXY_NAMESPACE}}-outpost-jobs-volume
kubectl delete pv {{PROXY_NAMESPACE}}-outpost-logs-volume
kubectl delete pv {{PROXY_NAMESPACE}}-outpost-sidecar-volume
kubectl delete pvc --all -n {{PROXY_NAMESPACE}}
kubectl delete all --all -n {{PROXY_NAMESPACE}}
