#!/bin/sh

if [ ! -f "./.env" ]; then
  echo "Please make sure .env file exists and it has a PROXY_ALIAS"
  exit 1
fi

CURRFOLDER=`pwd`
PROXY_FOLDER=`basename $CURRFOLDER`
echo "Proxy Folder: $PROXY_FOLDER"

PROXY_ALIAS=`cat .env | grep PROXY_ALIAS | sed -e 's/PROXY_ALIAS=//g'`
echo "Proxy Alias: $PROXY_ALIAS"

if [ x"$PROXY_ALIAS" = "x" ]; then
  echo "Please make sure .env file exists and it has a PROXY_ALIAS"
  exit 1
fi

PROXY_NAME=${PROXY_ALIAS}
echo "Proxy Name: $PROXY_NAME"
CONTAINER_ID=$(docker ps | grep cmd-exec | grep ${PROXY_NAME} | awk '{print $1}')
if [ x"$CONTAINER_ID" = "x" ]; then
  echo "Container not found for ${PROXY_NAME}.  Checking parent folder $PROXY_FOLDER"
  CONTAINER_ID=$PROXY_FOLDER
fi

echo "Connecting to container: ${CONTAINER_ID}"

if [ x"$CONTAINER_ID" = "x" ]; then
  echo "Container ID is empty"
  exit 1
fi

CMD="docker exec -it ${CONTAINER_ID} dkvault --vault-url=https://vault:8200 --vault-unseal-tokens-file ./src/keys/vault_unseal.keys $*"
eval $CMD
