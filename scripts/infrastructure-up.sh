#!/usr/bin/env bash
# Note: This script's contract is meant to be idempotent (like Ansible)

SCRIPT_DIR="$( cd -- "$( dirname -- "${BASH_SOURCE[0]:-$0}"; )" &> /dev/null && pwd 2> /dev/null; )";

# source configuration
. "${SCRIPT_DIR}"/infrastructure-config.sh

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

  # Create all S3 buckets
  for bucket in "${WEBSITE_BUCKET}" "${WEBSITE_BUCKET_ACCESS_LOGS}" "${WEBSITE_WWW_BUCKET}" "${WEBSITE_WWW_BUCKET_ACCESS_LOGS}"; do
    echo "ℹ️ (info) bucket: ${bucket}"
    # Check if AWS S3 bucket (static website assets) exists for project
    echo "🔨👷 Checking if bucket ${bucket} is list of buckets"
    if aws s3api list-buckets --query "Buckets[].Name" | grep "${bucket}\"" > /dev/null ; then
      echo "✅ ${bucket} S3 bucket has already been created"
    else
      # If not, create it
      echo "🔨 Creating ${bucket} S3 bucket"
      aws s3api create-bucket \
        --bucket "${bucket}" \
        --region "${REGION_ID}" \
        --create-bucket-configuration LocationConstraint="${REGION_ID}" | sed 's/^/    /'

      echo "✅ ${bucket} S3 bucket is now created"
    fi
  done

  # Apply a S3 policy to allow for static website access for the buckets intended to be simple static web hosts
  for bucket in "${WEBSITE_BUCKET}" "${WEBSITE_WWW_BUCKET}"; do
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
      --policy file:///tmp/.s3_bucket_policy.json | sed 's/^/    /'

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
  done

  # Website S3 Access logs
   bucket_accesslog_pairs=("${WEBSITE_BUCKET}:${WEBSITE_BUCKET_ACCESS_LOGS}" "${WEBSITE_WWW_BUCKET}:${WEBSITE_WWW_BUCKET_ACCESS_LOGS}")
  for bucket_accesslog_pair in ${bucket_accesslog_pairs[@]}; do
    IFS=':'
    read -a pair <<< "${bucket_accesslog_pair}"
    website_bucket="${pair[0]}"
    access_log_bucket="${pair[1]}"
    echo "ℹ️ website bucket ${website_bucket}"
    echo "ℹ️ access log bucket ${access_log_bucket}"

    echo "🔨👷 Writing access log bucket policy to temp json file"
    cat <<EOT | tee /tmp/.s3_access_log_bucket_policy.json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "S3ServerAccessLogsPolicy",
            "Effect": "Allow",
            "Principal": {"Service": "logging.s3.amazonaws.com"},
            "Action": "s3:PutObject",
            "Resource": "arn:aws:s3:::${access_log_bucket}/Logs/*",
            "Condition": {
                "ArnLike": {"aws:SourceARN": "arn:aws:s3:::${access_log_bucket}"},
                "StringEquals": {"aws:SourceAccount": "${BUCKET_OWNER_ID}"}
            }
        }
    ]
}
EOT
    echo "🔨 👷 Applying policy to access log bucket ${access_log_bucket}"
    if aws s3api put-bucket-policy --bucket "${access_log_bucket}" --policy file:///tmp/.s3_access_log_bucket_policy.json ; then
      echo "✅ bucket ${access_log_bucket} configured with access log bucket policy"
    else
      echo "❌ bucket ${access_log_bucket} not configured with access log bucket policy"
    fi

    echo "🔨👷 Updating bucket ACL for access log bucket ${access_log_bucket}"
    if aws s3api put-bucket-acl \
      --bucket "${access_log_bucket}" \
      --grant-write URI=http://acs.amazonaws.com/groups/s3/LogDelivery \
      --grant-read-acp URI=http://acs.amazonaws.com/groups/s3/LogDelivery ; then
      echo "✅ bucket ${access_log_bucket} configured with updated bucket ACL for logging"
    else
      echo "❌ bucket ${access_log_bucket} NOT configured with expected ACL log delivery policy"
    fi


    echo "🔨 👷 Writing access log bucket policy to temp json file"
    cat <<EOT | tee /tmp/.s3_website_logging.json
{
    "LoggingEnabled": {
        "TargetBucket": "${access_log_bucket}",
        "TargetPrefix": "/"
    }
}
EOT
    echo "🔨 👷 Enabling logging on ${website_bucket} to ${access_log_bucket}"
    if aws s3api put-bucket-logging --bucket "${wesbite_bucket}" --bucket-logging-status file:///tmp/.s3_website_logging.json --debug ; then
      echo "✅ Logging enabled for ${website_bucket}"
    else
      echo "❌ Logging NOT enabled for ${website_bucket}"
    fi
  done

  # Check if AWS Certificate Manager cert exists for project
    # If not, create it

  # Check if AWS cloudfront exists for project
    # If not, create it
}

main