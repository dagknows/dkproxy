## Deployment Steps
# 1. Create a namespace for the proxy

kubectl apply -f namespace.yaml

# 2. Deploy gcr secret to authenticate with gcr.io

kubectl -n {{PROXY_NAMESPACE}} create secret docker-registry gcr-json-key \
--docker-server=gcr.io \
--docker-username=_json_key \
--docker-password="$(cat gcr_auth.json)" \
--docker-email=<email>

# 3. Then to make our namespace use the credentials, we need to update service account's property.

kubectl -n {{PROXY_NAMESPACE}} patch serviceaccount default -p '{"imagePullSecrets": [{"name": "gcr-json-key"}]}'

# 4. Create K8s components from .env:

kubectl -n {{PROXY_NAMESPACE}} create secret generic com.dagknows.secret.frontend --from-env-file=../.env

# 5. Vault: Create K8s secrets from repository.

# For local.json
kubectl -n {{PROXY_NAMESPACE}} create configmap vault-configs --from-file=../vault/config/

# For Vault certificates
kubectl -n {{PROXY_NAMESPACE}} create secret generic vault-keys \
    --from-file=vault.crt=../vault/config/ssl/vault.crt \
    --from-file=vault.key=../vault/config/ssl/vault.key

# 6. Deploy the proxy
kubectl apply -f vault-main.yaml -n {{PROXY_NAMESPACE}}
kubectl apply -f cmd-exec-main.yaml -n {{PROXY_NAMESPACE}}
kubectl apply -f outpost-main.yaml -n {{PROXY_NAMESPACE}}
