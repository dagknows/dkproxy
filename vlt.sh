#!/bin/sh

if [ ! -f "./.env" ]; then
  echo "Please make sure .env file exists and it has a PROXY_ALIAS"
  exit 1
fi

PROXY_ALIAS=`cat .env | grep PROXY_ALIAS | sed -e 's/PROXY_ALIAS=//g'`

if [ x"$PROXY_ALIAS" = "x" ]; then
  echo "Please make sure .env file exists and it has a PROXY_ALIAS"
  exit 1
fi

PROXY_NAME=${PROXY_ALIAS}
CONTAINER_ID=$(docker ps | grep cmd-exec | grep ${PROXY_NAME} | awk '{print $1}')
CMD="docker exec -it ${CONTAINER_ID} dkvault --vault-url=https://vault:8200 --vault-unseal-tokens-file ./src/keys/vault_unseal.keys $*"
eval $CMD
