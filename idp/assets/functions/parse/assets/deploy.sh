#!/bin/bash
profile=$1
template_file_name=$2
stack_name=$3

res=$(aws --profile $profile cloudformation deploy --template-file $template_file_name --stack-name $stack_name --no-fail-on-empty-changeset --capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM CAPABILITY_AUTO_EXPAND 2>&1)
if [[ $? != 0 ]]; then
    if [[ $res == *"is in ROLLBACK_FAILED state and can not be updated"* ]]; then
        aws --profile $profile cloudformation delete-stack --stack-name $stack_name
        aws --profile $profile cloudformation deploy --template-file $template_file_name --stack-name $stack_name --no-fail-on-empty-changeset --capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM CAPABILITY_AUTO_EXPAND
    fi
fi
