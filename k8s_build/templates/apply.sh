

if [ x"$1" = "xdelete" ]; then
  kubectl delete -f vault-main.yaml -n {{PROXY_NAMESPACE}}
  kubectl delete -f cmd-exec-main.yaml -n {{PROXY_NAMESPACE}}
  kubectl delete -f outpost-main.yaml -n {{PROXY_NAMESPACE}}
else
  kubectl apply -f vault-main.yaml -n {{PROXY_NAMESPACE}}
  kubectl apply -f cmd-exec-main.yaml -n {{PROXY_NAMESPACE}}
  kubectl apply -f outpost-main.yaml -n {{PROXY_NAMESPACE}}
fi

