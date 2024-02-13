

kubectl apply -f vault-main.yaml -n {{PROXY_NAMESPACE}}
kubectl apply -f cmd-exec-main.yaml -n {{PROXY_NAMESPACE}}
kubectl apply -f outpost-main.yaml -n {{PROXY_NAMESPACE}}
