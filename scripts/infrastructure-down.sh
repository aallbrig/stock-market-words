#!/usr/bin/env bash
# Note: This script's contract is meant to be idempotent (like Ansible)

SCRIPT_DIR="$( cd -- "$( dirname -- "${BASH_SOURCE[0]:-$0}"; )" &> /dev/null && pwd 2> /dev/null; )";

# source configuration
. "${SCRIPT_DIR}"/infrastructure-config.sh

# VPC ID is passed in as an argument
VPC_ID="${VPC_ID:-${1}}"

# Delete all S3 buckets, if they exist
for bucket in "${WEBSITE_BUCKET}" "${WEBSITE_BUCKET_ACCESS_LOGS}" "${WEBSITE_WWW_BUCKET}" "${WEBSITE_WWW_BUCKET_ACCESS_LOGS}"; do
  # Check if AWS S3 bucket (static website assets) exists for project
  if aws s3api list-buckets --query "Buckets[].Name" | grep "${bucket}\"" > /dev/null ; then
    echo "ℹ️ ${bucket} S3 bucket detected. Deleting bucket"
    set -v
    aws s3 rb s3://"${bucket}" --force
    set +v
  else
    echo "✅ ${bucket} S3 bucket DOES NOT exist"
  fi
done
