# Create local PVs if we are in local PV mode - otherwise if we are in say efs do somethign else!
#
#
if [ x"$1" = "xdelete" ]; then
  kubectl delete -f storageclasses-efs.yaml
  kubectl delete -f vault-pvcs-efs.yaml -n {{PROXY_NAMESPACE}}
  kubectl delete -f cmd-exec-pvcs-efs.yaml -n {{PROXY_NAMESPACE}}
  kubectl delete -f outpost-pvcs-efs.yaml -n {{PROXY_NAMESPACE}}
fi

# Create all storage classes
kubectl apply -f storageclasses-efs.yaml

echo "Dynamic PVCs with a hardcoded EFS ID and AccessPoint for vault..."
kubectl apply -f vault-pv-efs.yaml
kubectl apply -f vault-pvcs-efs.yaml -n {{PROXY_NAMESPACE}}

echo "Dynamic PVCs with a hardcoded EFS ID and AccessPoint for Cmd-Exec..."
# kubectl apply -f cmd-exec-pvcs-efs.yaml -n {{PROXY_NAMESPACE}}

echo "Dynamic PVCs with a hardcoded EFS ID and AccessPoint for outpost..."
# kubectl apply -f outpost-pvcs-efs.yaml -n {{PROXY_NAMESPACE}}
