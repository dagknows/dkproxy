kubectl delete pvc --all -n {{PROXY_NAMESPACE}}
kubectl delete all --all -n {{PROXY_NAMESPACE}}
kubectl delete namespace {{PROXY_NAMESPACE}}
