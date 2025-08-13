#!/bin/sh
CONTAINER_ID=$(kubectl get pods -n {{PROXY_NAMESPACE}} | grep cmd-exec | awk '{print $1}')
CMD="kubectl -n {{PROXY_NAMESPACE}} exec -it ${CONTAINER_ID} -- dkvault --vault-url=https://vault:8200 --vault-unseal-tokens-file /root/.keys/vault_unseal.keys $*"
eval $CMD
