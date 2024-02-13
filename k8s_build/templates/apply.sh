
# Apply the namespace on the given namespace
kubectl apply -f namespace.yaml

# Use 
kubectl -n {{PROXY_NAMESPACE}} create secret generic com.dagknows.secret.frontend --from-env-file=./.env

# Create the vault too
kubectl -n {{PROXY_NAMESPACE}} create configmap vault-configs --from-file=./vault/config/
#
# For Vault certificates
kubectl -n {{PROXY_NAMESPACE}} create secret generic vault-keys \
    --from-file=vault.crt=./vault/config/ssl/vault.crt \
    --from-file=vault.key=./vault/config/ssl/vault.key

kubectl apply -f vault.yaml -n {{PROXY_NAMESPACE}}
kubectl apply -f cmd-exec-pvcs.yaml -n {{PROXY_NAMESPACE}}
kubectl apply -f cmd-exec-main.yaml -n {{PROXY_NAMESPACE}}
kubectl apply -f outpost-pvcs.yaml -n {{PROXY_NAMESPACE}}
kubectl apply -f outpost-main.yaml -n {{PROXY_NAMESPACE}}
