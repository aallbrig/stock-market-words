#!/usr/bin/env bash
# Note: This script's contract is meant to be idempotent (like Ansible)

SCRIPT_DIR="$( cd -- "$( dirname -- "${BASH_SOURCE[0]:-$0}"; )" &> /dev/null && pwd 2> /dev/null; )";

# source configuration
. "${SCRIPT_DIR}"/infrastructure-config.sh


function main() {
  # VPC ID is provided by user
  # VPC_ID="${VPC_ID:-${1}}"

  cat <<EOF
Infrastructure Down (aka delete resources script) Script Run Date: $(date)
Environment
  REGION_ID=${REGION_ID}
  WEBSITE_BUCKET=${WEBSITE_BUCKET}
  WEBSITE_BUCKET_ACCESS_LOGS=${WEBSITE_BUCKET_ACCESS_LOGS}
  WEBSITE_WWW_BUCKET=${WEBSITE_WWW_BUCKET}
  WEBSITE_WWW_BUCKET_ACCESS_LOGS=${WEBSITE_WWW_BUCKET}
  WEBSITE_SRC_DIR=${WEBSITE_SRC_DIR}
EOF

  # Delete all S3 buckets, if they exist
  for bucket in "${WEBSITE_BUCKET}" "${WEBSITE_BUCKET_ACCESS_LOGS}" "${WEBSITE_WWW_BUCKET}" "${WEBSITE_WWW_BUCKET_ACCESS_LOGS}"; do
    # Check if AWS S3 bucket (static website assets) exists for project
    if aws s3api list-buckets --query "Buckets[].Name" | grep "${bucket}\"" > /dev/null ; then
      echo "ℹ️ ${bucket} S3 bucket detected. Deleting bucket"
      set -v
      aws s3 rb s3://"${bucket}" --force
      set +v
      echo "✅ ${bucket} S3 bucket has been deleted"
    else
      echo "✅ ${bucket} S3 bucket is already deleted"
    fi
  done
}

main