#!/bin/zsh
TARGET_OUS=("Security" "Infrastructure" "Workloads")
SharedServicesAccountId=$1
STACK_SET_NAME="core-deployments-servicecatalog-role"
REGION=$2

echo "SharedServicesAccountId: ${SharedServicesAccountId}"
echo "REGION: ${REGION}"
ou_id_root=$(aws organizations list-roots --query "Roots[0].Id" --output text --no-cli-pager)
level1_ous_ids=$(aws organizations list-children --parent-id $ou_id_root --child-type ORGANIZATIONAL_UNIT --no-cli-pager --query "Children[].Id" --output text)
echo "level1_ous_ids: ${level1_ous_ids}"
declare -A org_unit_map
for ou_id in $=level1_ous_ids; do
  echo "ou-id: ${ou_id}"
  ou_name=$(aws organizations describe-organizational-unit --organizational-unit-id $ou_id --no-cli-pager --query "OrganizationalUnit.Name" --output text)
  echo "ou_name: $ou_name"
  if [[ "${(j:|:)TARGET_OUS}" != *"$ou_name"* ]]; then
    continue
  fi
  org_unit_map[$ou_name]=$ou_id
done
echo "map: ${org_unit_map}"
for k v in "${(@kv)org_unit_map}"; do
  echo "Key: $k, Value: ${org_unit_map[$k]}"
done

deployment_ous="${(j:,:)org_unit_map}"
echo "deployment_ous: ${deployment_ous}"

# Deploy to managment account
# aws cloudformation deploy \
#   --stack-name $STACK_SET_NAME \
#   --template-file role.yml \
#   --capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM \
#   --no-cli-pager

# Create the stack set
echo "Creating stack set..."
aws cloudformation create-stack-set \
  --stack-set-name "$STACK_SET_NAME" \
  --template-body "file://./role.yml" \
  --description "Deploying role for the service catalog platform to assume in core accounts" \
  --capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM \
  --permission-model SERVICE_MANAGED \
  --auto-deployment Enabled=true,RetainStacksOnAccountRemoval=true \
  --managed-execution Active=true \
  --no-cli-pager \
  --parameters ParameterKey=TrustedAccount,ParameterValue=$SharedServicesAccountId

# Create the stack instances
echo "Creating stack instances..."
aws cloudformation create-stack-instances \
  --stack-set-name "$STACK_SET_NAME" \
  --deployment-targets OrganizationalUnitIds=$deployment_ous \
  --regions $REGION \
  --operation-preferences FailureTolerancePercentage=0,MaxConcurrentPercentage=100 \
  --region "$REGION" \
  --no-cli-pager

sleep 60
# Update the stack set
echo "Updating stack set..."
aws cloudformation update-stack-set \
  --stack-set-name "$STACK_SET_NAME" \
  --template-body "file://./role.yml" \
  --description "Deploying role for the service catalog platform to assume in core accounts" \
  --capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM \
  --permission-model SERVICE_MANAGED \
  --auto-deployment Enabled=true,RetainStacksOnAccountRemoval=true \
  --managed-execution Active=true \
  --deployment-targets OrganizationalUnitIds=$deployment_ous \
  --regions $REGION \
  --operation-preferences FailureTolerancePercentage=0,MaxConcurrentPercentage=100 \
  --region "$REGION" \
  --no-cli-pager \
  --parameters ParameterKey=TrustedAccount,ParameterValue=$SharedServicesAccountId

# Monitor the stack set deployment
echo "Monitoring deployment progress..."
aws cloudformation describe-stack-set-operation \
  --stack-set-name "$STACK_SET_NAME" \
  --operation-id $(aws cloudformation list-stack-set-operations --stack-set-name "$STACK_SET_NAME" \
  --query 'Summaries[0].OperationId' --output text --region "$REGION") \
  --region "$REGION" \
  --no-cli-pager
