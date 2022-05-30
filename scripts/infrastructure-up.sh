#!/usr/bin/env bash
# Note: This script's contract is meant to be idempotent (like Ansible)

SCRIPT_DIR="$( cd -- "$( dirname -- "${BASH_SOURCE[0]:-$0}"; )" &> /dev/null && pwd 2> /dev/null; )";
. "${SCRIPT_DIR}"/infrastructure-config.sh

function create_bucket() {
  bucket=${1}
  region_id=${2}
  echo "ℹ️ (info) bucket: ${bucket}"
  echo "ℹ️ (info) region ID: ${region_id}"

  for required_field in "${bucket}" "${region_id}" ; do
    if [ -z "${required_field}" ] ; then
      echo "❌ required field ${!required_field@} not defined"
      exit 1
    fi
  done

  # Check if AWS S3 bucket (static website assets) exists for project
  echo "ℹ️ Checking if bucket ${bucket} is list of buckets"
  if aws s3api list-buckets --query "Buckets[].Name" | grep "${bucket}\"" > /dev/null ; then
    echo "✅ ${bucket} S3 bucket has already been created"
  else
    echo "🔨 Creating ${bucket} S3 bucket"
    aws s3api create-bucket \
      --bucket "${bucket}" \
      --region "${REGION_ID}" \
      --create-bucket-configuration \
      LocationConstraint="${REGION_ID}" \
        | sed 's/^/    /'

    echo "✅ ${bucket} S3 bucket is now created"
  fi
}

function configure_bucket_as_static_site() {
  bucket=${1}

  for required_field in "${bucket}" ; do
    echo "ℹ️ (info) ${!required_field}: ${required_field}"
    if [ -z "${required_field}" ] ; then
      echo "❌ required field ${!required_field@} not defined"
      exit 1
    fi
  done

  # TODO: correct the "get policy" statement so this doesn't have to happen every time
  echo "🔨 👷 Writing S3 bucket policy to temp directory"
  cat <<EOT | tee /tmp/.s3_bucket_policy.json
{
  "Version":"2012-10-17",
  "Statement":[
    {
      "Sid":"AddPerm",
      "Effect":"Allow",
      "Principal": "*",
      "Action":["s3:GetObject"],
      "Resource":["arn:aws:s3:::${bucket}/*"]
    }
  ]
}
EOT

  echo "🔨 👷 Updating policy for bucket ${bucket} with S3 bucket policy from temp file"
  aws s3api put-bucket-policy \
    --bucket "${bucket}" \
    --policy file:///tmp/.s3_bucket_policy.json \
      | sed 's/^/    /'

  echo "✅ bucket ${bucket} web access configured"

  # TODO: correct the "get public access block" statement so this doesn't have to happen every time
  # if aws s3api get-public-access-block --bucket "${bucket}" | tee /dev/null ; then
    # echo "✅ ${bucket} S3 public access block has already been applied"
  # else
  # fi
  echo "🔨 👷 Configuring public access to the S3 bucket"
  aws s3api put-public-access-block \
    --bucket "${bucket}" \
    --public-access-block-configuration \
      "BlockPublicAcls=false,IgnorePublicAcls=false,BlockPublicPolicy=false,RestrictPublicBuckets=false" \
    | sed 's/^/    /'

  echo "✅ ${bucket} S3 public access block has been applied"

  # TODO write a get statement to detect if this is already done
  echo "🔨 👷 Syncing website static assets to bucket"
  aws s3 sync "${WEBSITE_SRC_DIR}" s3://"${bucket}"/ | sed 's/^/    /'

  # TODO write a get statement to detect if this is already done
  echo "🔨 👷 Setting index.html and error.html pages for the S3 bucket"
  aws s3 website s3://"${bucket}"/ \
    --index-document index.html \
    --error-document error.html

  echo "✅ S3 Bucket ${bucket} setup has been completed"
}

function configure_static_site_access_logs() {
  access_log_bucket=${1}
  website_bucket=${2}

  for required_field in "${access_log_bucket}" "${website_bucket}" ; do
    echo "ℹ️ (info) required field K:V ${!required_field@}:${required_field}"
    if [ -z "${required_field}" ] ; then
      echo "❌ required field ${!required_field@} not defined"
      exit 1
    fi
  done

  echo "🔨👷 Updating bucket ACL for access log bucket ${access_log_bucket}"
  if aws s3api put-bucket-acl \
    --bucket "${access_log_bucket}" \
    --grant-write URI=http://acs.amazonaws.com/groups/s3/LogDelivery \
    --grant-read-acp URI=http://acs.amazonaws.com/groups/s3/LogDelivery ; then
    echo "✅ bucket ${access_log_bucket} configured to be able to use log delivery"
  else
    echo "❌ bucket ${access_log_bucket} NOT configured to be able to use log delivery"
  fi

  echo "🔨👷 Writing access log bucket policy to temp json file"
  cat <<EOT | tee /tmp/.s3_access_log_bucket_policy.json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "S3ServerAccessLogsPolicy",
            "Effect": "Allow",
            "Principal": {
                "Service": "logging.s3.amazonaws.com"
            },
            "Action": "s3:PutObject",
            "Resource": "arn:aws:s3:::${access_log_bucket}/*"
        }
    ]
}
EOT

  echo "🔨 👷 Applying policy to access log bucket ${access_log_bucket}"
  if aws s3api put-bucket-policy \
    --bucket "${access_log_bucket}" \
    --policy file:///tmp/.s3_access_log_bucket_policy.json ; then
    echo "✅ bucket ${access_log_bucket} is allowed to work with the AWS logging service"
  else
    echo "❌ bucket ${access_log_bucket} is not configured to work with the AWS logging service"
  fi

  echo "🔨 👷 Writing access log bucket policy to temp json file"
  cat <<EOT | tee /tmp/.s3_website_logging.json
{
    "LoggingEnabled": {
        "TargetBucket": "${access_log_bucket}",
        "TargetPrefix": "${website_bucket}/"
    }
}
EOT
  echo "🔨 👷 Enabling logging on ${website_bucket} to ${access_log_bucket}"
  if aws s3api put-bucket-logging --bucket "${website_bucket}" --bucket-logging-status file:///tmp/.s3_website_logging.json ; then
    echo "✅ Logging enabled for ${website_bucket} to ${access_log_bucket}"
  else
    echo "❌ Logging NOT enabled for ${website_bucket} to ${access_log_bucket}"
  fi
}

function setup_cloudfront_CDN() {
  website_bucket=${1}

  for required_field in "${website_bucket}" ; do
    echo "ℹ️ (info) required field K:V ${!required_field@}:${required_field}"
    if [ -z "${required_field}" ] ; then
      echo "❌ required field ${!required_field@} not defined"
      exit 1
    fi
  done

  cat <<EOT | tee /tmp/.cloudfront-distribution-configuration.json
{
  "CallerReference": "${website_bucket}-cloudfront-distribution"
}
EOT
}

function main() {
  # VPC ID is provided by user
  # VPC_ID="${VPC_ID:-${1}}"

  cat <<EOF
Infrastructure Up (aka create resources script) Script Run Date: $(date)
Environment
  REGION_ID=${REGION_ID}
  WEBSITE_BUCKET=${WEBSITE_BUCKET}
  WEBSITE_BUCKET_ACCESS_LOGS=${WEBSITE_BUCKET_ACCESS_LOGS}
  WEBSITE_WWW_BUCKET=${WEBSITE_WWW_BUCKET}
  WEBSITE_WWW_BUCKET_ACCESS_LOGS=${WEBSITE_WWW_BUCKET}
  WEBSITE_SRC_DIR=${WEBSITE_SRC_DIR}
EOF

  bucket_accesslog_pairs=("${WEBSITE_BUCKET}:${WEBSITE_BUCKET_ACCESS_LOGS}" "${WEBSITE_WWW_BUCKET}:${WEBSITE_WWW_BUCKET_ACCESS_LOGS}")
  for bucket_accesslog_pair in ${bucket_accesslog_pairs[@]}; do
    IFS=':'
    read -a pair <<< "${bucket_accesslog_pair}"
    website_bucket="${pair[0]}"
    access_log_bucket="${pair[1]}"
    create_bucket "${website_bucket}" "${REGION_ID}"
    create_bucket "${access_log_bucket}" "${REGION_ID}"
    configure_bucket_as_static_site "${website_bucket}"
    configure_static_site_access_logs "${access_log_bucket}" "${website_bucket}"
    setup_cloudfront_CDN "${website_bucket}"
  done

  # Check if AWS Certificate Manager cert exists for project
    # If not, create it

  # Check if AWS cloudfront exists for project
    # If not, create it
}

main