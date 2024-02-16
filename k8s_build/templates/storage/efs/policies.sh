
export cluster_name={{EKS_CLUSTER_NAME}}
export role_name=AmazonEKS_EFS_CSI_DriverRole
export OIDC=`aws --region {{AWS_REGION}} eks describe-cluster --name $cluster_name --query "cluster.identity.oidc.issuer" --output text | grep http | sed -e 's/http.*\/id\///g'`
export AWS_ACCOUNT_ID=`aws sts get-caller-identity --query "Account" --output text`
echo OIDC=$OIDC
echo AWS_ACCOUNT_ID=$AWS_ACCOUNT_ID
envsubst < aws-efs-csi-driver-trust-policy.json.template > aws-efs-csi-driver-trust-policy.json

echo "Creating IAM Role for EFS"
aws iam create-role --role-name $role_name \
  --assume-role-policy-document file://"aws-efs-csi-driver-trust-policy.json"

echo "Associated builtin EFSCSIDriver role with the new Role..."
aws iam attach-role-policy \
  --policy-arn arn:aws:iam::aws:policy/service-role/AmazonEFSCSIDriverPolicy \
  --role-name $role_name

echo "Creating service account..."
eksctl create iamserviceaccount \
    --region {{AWS_REGION}}     \
    --name efs-csi-controller-sa \
    --namespace kube-system \
    --cluster $cluster_name \
    --role-name $role_name \
    --role-only \
    --attach-policy-arn arn:aws:iam::aws:policy/service-role/AmazonEFSCSIDriverPolicy \
    --approve

TRUST_POLICY=$(aws iam get-role --role-name $role_name --query 'Role.AssumeRolePolicyDocument' | \
    sed -e 's/efs-csi-controller-sa/efs-csi-*/' -e 's/StringEquals/StringLike/')

aws iam update-assume-role-policy --role-name $role_name --policy-document "$TRUST_POLICY"

helm upgrade --install aws-efs-csi-driver --namespace kube-system aws-efs-csi-driver/aws-efs-csi-driver \
             --set controller.serviceAccount.create=false \
             --set controller.serviceAccount.name=efs-csi-controller-sa
