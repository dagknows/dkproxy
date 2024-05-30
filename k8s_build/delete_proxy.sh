#!/bin/sh

PROXY_NAMESPACE=$1
COMMIT=$2

if [ x"$PROXY_NAMESPACE" = "x" ]; then
  echo "Usage: delete_proxy <PROXY_NAMESPACE>"
  exit 1
fi


echo "kubectl -n $PROXY_NAMESPACE delete deploy --all"
for res in `kubectl -n $PROXY_NAMESPACE get pvc -o name`
do
  echo "kubectl -n $PROXY_NAMESPACE patch $res  -p '{"metadata": {"finalizers": null}}'"
  echo "kubectl -n $PROXY_NAMESPACE delete $res"
done

echo "Patching and deleting all PVs for proxy..."
for res in `kubectl get pv -o name | grep "$PROXY_NAMESPACE-"`
do
  echo "kubectl patch $res  -p '{"metadata": {"finalizers": null}}'"
  echo "kubectl delete $res"
done

echo "kubectl delete ns $PROXY_NAMESPACE"

if [ x"$COMMIT" = "xyes" ]; then
  echo "Actually doing the deletion...."
  kubectl -n $PROXY_NAMESPACE delete deploy --all

  echo "Patching and deleting all PVCs for proxy..."
  for res in `kubectl -n $PROXY_NAMESPACE get pvc -o name`
  do
    echo "Patching Res: $res"
    kubectl -n $PROXY_NAMESPACE patch $res  -p '{"metadata": {"finalizers": null}}'
    kubectl -n $PROXY_NAMESPACE delete $res
  done

  echo "Patching and deleting all PVs for proxy..."
  for res in `kubectl get pv -o name | grep "$PROXY_NAMESPACE-"`
  do
    echo "Patching Res: $res"
    kubectl patch $res  -p '{"metadata": {"finalizers": null}}'
    kubectl delete $res
  done

  echo "Deleting namespace...."
  kubectl delete ns $PROXY_NAMESPACE
fi
