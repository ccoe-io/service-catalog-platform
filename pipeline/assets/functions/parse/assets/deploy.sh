#!/bin/bash

# Define variables from arguments
profile="$1"
template_file_name="$2"
stack_name="$3"

# Shift the positional parameters to leave only tags
shift 3
tags=("$@")

# Logging function
log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S'): $*"
}

# Function to deploy the CloudFormation stack
deploy_stack() {
    log "Deploying stack $stack_name..."
    aws --profile "$profile" cloudformation deploy \
        --template-file "$template_file_name" \
        --stack-name "$stack_name" \
        --no-fail-on-empty-changeset \
        --capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM CAPABILITY_AUTO_EXPAND \
        --tags "${tags[@]}" 2>&1
}

# Function to delete the CloudFormation stack
delete_stack() {
    log "Deleting stack $stack_name..."
    aws --profile "$profile" cloudformation delete-stack --stack-name "$stack_name"
    aws --profile "$profile" cloudformation wait stack-delete-complete --stack-name "$stack_name"
    log "Stack $stack_name deleted."
}

# Deploy the stack and capture the result and status
res=$(deploy_stack)
status=$?

# Check both status and result in a single conditional block
if [[ $status != 0 && ( $res == *"FAILED"* || $res == *"ROLLBACK"* ) ]]; then
    log "Deployment failed or stack rolled back. Deleting stack..."
    delete_stack       # Delete the stack if deployment failed

    log "Redeploying stack $stack_name..."
    res=$(deploy_stack)    # Attempt to deploy the stack again
    status=$?              # Update the status with the result of the redeployment
fi

if [[ $status == 0 ]]; then
    log "Deployment successful."
else
    log "Final attempt to deploy failed. Status: $status"
    log "Error: $res"
fi

# Exit with the final status
exit $status
