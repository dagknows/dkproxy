#!/bin/sh

PROXY_NAME={{PROXY_NAMESPACE}}
CONTAINER_ID=$(docker ps | grep cmd-exec | grep ${PROXY_NAME} | awk '{print $1}')
CMD="docker exec -it ${CONTAINER_ID} dkvault --vault-url=https://vault:8200 --vault-unseal-tokens-file ./src/keys/vault_unseal.keys $*"
eval $CMD
