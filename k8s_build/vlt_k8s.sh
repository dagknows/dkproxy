#!/bin/sh
CONTAINER_ID=$(kubectl get pods -n {{PROXY_NAMESPACE}} | grep frontend | awk '{print $1}')
CMD="kubectl exec -it ${CONTAINER_ID} -n {{PROXY_NAMESPACE}} -- python src/vlt.py"
eval $CMD
