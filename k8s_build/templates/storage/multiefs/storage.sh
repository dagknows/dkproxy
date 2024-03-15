# Create local PVs if we are in local PV mode - otherwise if we are in say efs do somethign else!
#
#
if [ x"$1" = "xdelete" ]; then
  kubectl delete -f vault-pvcs-efs.yaml -n {{PROXY_NAMESPACE}} --grace-period=0 --force
  kubectl delete -f cmd-exec-pvcs-efs.yaml -n {{PROXY_NAMESPACE}} --grace-period=0 --force
  kubectl delete -f outpost-pvcs-efs.yaml -n {{PROXY_NAMESPACE}} --grace-period=0 --force
  kubectl delete -f vault-pvs-efs.yaml --grace-period=0 --force &
  kubectl delete -f cmd-exec-pvs-efs.yaml --grace-period=0 --force &
  kubectl delete -f outpost-pvs-efs.yaml --grace-period=0 --force &
  kubectl delete -f storageclasses-efs.yaml
else
  # Create all storage classes
  kubectl apply -f storageclasses-efs.yaml

  echo "Dynamic PVCs with a hardcoded EFS ID and AccessPoint for vault..."
  kubectl apply -f vault-pvs-efs.yaml -n {{PROXY_NAMESPACE}}
  kubectl apply -f vault-pvcs-efs.yaml -n {{PROXY_NAMESPACE}}

  echo "Dynamic PVCs with a hardcoded EFS ID and AccessPoint for Cmd-Exec..."
  kubectl apply -f cmd-exec-pvs-efs.yaml -n {{PROXY_NAMESPACE}}
  kubectl apply -f cmd-exec-pvcs-efs.yaml -n {{PROXY_NAMESPACE}}

  echo "Dynamic PVCs with a hardcoded EFS ID and AccessPoint for outpost..."
  kubectl apply -f outpost-pvs-efs.yaml -n {{PROXY_NAMESPACE}}
  kubectl apply -f outpost-pvcs-efs.yaml -n {{PROXY_NAMESPACE}}
fi
