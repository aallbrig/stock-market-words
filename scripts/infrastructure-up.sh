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
    if aws s3api list-buckets --query "Buckets[].Name" | grep "${bucket}\"" > /dev/null ; then
      echo "✅ ${bucket} S3 bucket has already been created"
    else
      # If not, create it
      echo "🔨 Creating ${bucket} S3 bucket"
      set -v
      aws s3api create-bucket \
        --bucket "${bucket}" \
        --region "${REGION_ID}" \
        --create-bucket-configuration LocationConstraint="${REGION_ID}" > /dev/null
      set +v

      echo "✅ ${bucket} S3 bucket is now created"
    fi
  done

  # Apply a S3 policy to allow for static website access for the buckets intended to be simple static web hosts
  for bucket in "${WEBSITE_BUCKET}" "${WEBSITE_WWW_BUCKET}"; do
    # TODO: correct the "get policy" statement so this doesn't have to happen every time
    echo "🔨 👷 Writing S3 bucket policy to temp directory"
    set -v
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
    set -v
    aws s3api put-bucket-policy \
      --bucket "${bucket}" \
      --policy file:///tmp/.s3_bucket_policy.json | tee /dev/null
    set +v

    echo "✅ bucket ${bucket} web access configured"

    # TODO: correct the "get public access block" statement so this doesn't have to happen every time
    # if aws s3api get-public-access-block --bucket "${bucket}" | tee /dev/null ; then
      # echo "✅ ${bucket} S3 public access block has already been applied"
    # else
    # fi
    echo "🔨 👷 Configuring public access to the S3 bucket"
    set -v
    aws s3api put-public-access-block \
      --bucket "${bucket}" \
      --public-access-block-configuration \
        "BlockPublicAcls=false,IgnorePublicAcls=false,BlockPublicPolicy=false,RestrictPublicBuckets=false" \
      | tee /dev/null
    set +v

    echo "✅ ${bucket} S3 public access block has been applied"

    # TODO write a get statement to detect if this is already done
    echo "🔨 👷 Syncing website static assets to bucket"
    set -v
    aws s3 sync "${WEBSITE_SRC_DIR}" s3://"${bucket}"/
    set +v

    # TODO write a get statement to detect if this is already done
    echo "🔨 👷 Setting index.html and error.html pages for the S3 bucket"
    set -v
    aws s3 website s3://"${bucket}"/ \
      --index-document index.html \
      --error-document error.html
    set +v

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

    echo "🔨 👷 Writing access log bucket policy to json file"
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
    echo "🔨 👷 Applying policy to access log bucket"
    if aws s3api put-bucket-policy --bucket "${access_log_bucket}" --policy file:///tmp/.s3_access_log_bucket_policy.json ; then
      echo "✅ bucket ${access_log_bucket} configured with access log bucket policy"
    else
      echo "❌ bucket ${access_log_bucket} not configured with access log bucket policy"
    fi
  done
  for website_bucket in "${WEBSITE_BUCKET_ACCESS_LOGS}" "${WEBSITE_WWW_BUCKET_ACCESS_LOGS}" ; do
    echo "ℹ️ TODO configure S3 website access log website_bucket ${website_bucket}"
    # What do I need to do to configure the access log buckets?

    # echo "🔨 👷 Syncing website static assets to ${website_bucket}"
    # aws s3 sync "${WEBSITE_SRC_DIR}" s3://"${website_bucket}"/
    # echo "🔨 👷 Setting index.html and error.html for S3 website_bucket ${website_bucket}"
    # aws s3 website s3://"${website_bucket}"/ \
      # --index-document index.html \
      # --error-document error.html
    # echo "✅ ${website_bucket} access log S3 website_bucket has been configured for web access logging"
  done

  # If the get-bucket-logging returns an empty response
  # TODO: check if it matches a specific value
  # cat <<EOT > /tmp/.s3_access_logs_policy.json
  # {
  #     "Version": "2012-10-17",
  #     "Statement": [
  #         {
  #             "Sid": "S3ServerAccessLogsPolicy",
  #             "Effect": "Allow",
  #             "Principal": {
  #                 "Service": "logging.s3.amazonaws.com"
  #             },
  #             "Action": [
  #                 "s3:PutObject"
  #             ],
  #             "Resource": "arn:aws:s3:::awsexamplebucket1-logs/*",
  #             "Condition": {
  #                 "ArnLike": {
  #                     "aws:SourceArn": "arn:aws:s3:::SOURCE-BUCKET-NAME"
  #                 },
  #                 "StringEquals": {
  #                     "aws:SourceAccount": "SOURCE-ACCOUNT-ID"
  #                 }
  #             }
  #         }
  #     ]
  # }
  # EOT
  # if [ -z "$(aws s3api get-bucket-logging --bucket english-dictionary-stocks-website)" ] ; then
  #   echo "🔨 Configuring website access logs s3 bucket"
  #   aws s3api put-bucket-policy \
  #     "${WEBSITE_BUCKET}-access-logs" \
  #     --policy file:///tmp/.s3_access_logs_policy.json
  # else
  #   echo "✅ aws logging bucket configured"
  # fi

  # Check if AWS Certificate Manager cert exists for project
    # If not, create it

  # Check if AWS cloudfront exists for project
    # If not, create it
}

main