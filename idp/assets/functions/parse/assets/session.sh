#!/bin/bash

role_arn=$1
OUTPUT_PROFILE=$2

echo $OUTPUT_PROFILE
echo Assume Role: $role_arn
sts=$(aws sts assume-role --role-arn $role_arn --role-session-name $OUTPUT_PROFILE --query 'Credentials.[AccessKeyId,SecretAccessKey,SessionToken]' --output text)
# echo 'Converting sts to array'
# echo $sts
# IFS=', ' read -r -a sts <<< $sts
sts=($sts)
echo AWS_ACCESS_KEY_ID is ${sts[0]}
aws configure set aws_access_key_id ${sts[0]} --profile $OUTPUT_PROFILE
aws configure set aws_secret_access_key ${sts[1]} --profile $OUTPUT_PROFILE
aws configure set aws_session_token ${sts[2]} --profile $OUTPUT_PROFILE
echo credentials stored in the profile named $OUTPUT_PROFILE
