
# Delete deployments first
kubectl delete deploy vault -n {{PROXY_NAMESPACE}}
kubectl delete deploy cmd-exec -n {{PROXY_NAMESPACE}}
kubectl delete deploy outpost -n {{PROXY_NAMESPACE}}

# then PV
sh deletestorage.sh

kubectl delete namespace {{PROXY_NAMESPACE}}

# helm uninstall aws-efs-csi-driver -n kube-system
