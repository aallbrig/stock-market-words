#!/usr/bin/env bash
# Note: This script's contract is that it is idempotent

VPC_ID="${VPC_ID:-${1}}"
REGION_ID=$(aws configure get region)
WEBSITE_BUCKET="${WEBSITE_BUCKET:-englishdictionarystocks.com}"
WEBSITE_BUCKET_ACCESS_LOGS="${WEBSITE_BUCKET}-access-logs"
WEBSITE_WWW_BUCKET="${WEBSITE_WWW_BUCKET:-www.englishdictionarystocks.com}"
WEBSITE_WWW_BUCKET_ACCESS_LOGS="${WEBSITE_WWW_BUCKET}-access-logs"
WEBSITE_SRC_DIR="${WEBSITE_SRC_DIR:-static}"

cat <<EOF
Date: $(date)
VPC_ID=${VPC_ID}
REGION_ID=${REGION_ID}
WEBSITE_BUCKET=${WEBSITE_BUCKET}
WEBSITE_BUCKET_ACCESS_LOGS=${WEBSITE_BUCKET_ACCESS_LOGS}
WEBSITE_WWW_BUCKET=${WEBSITE_WWW_BUCKET}
WEBSITE_WWW_BUCKET_ACCESS_LOGS=${WEBSITE_WWW_BUCKET}
WEBSITE_SRC_DIR=${WEBSITE_SRC_DIR}
EOF

# Create all S3 buckets
for bucket in "${WEBSITE_BUCKET}" "${WEBSITE_BUCKET_ACCESS_LOGS}" "${WEBSITE_WWW_BUCKET}" "${WEBSITE_WWW_BUCKET_ACCESS_LOGS}"; do
  echo "bucket: ${bucket}"
  # Check if AWS S3 bucket (static website assets) exists for project
  if aws s3api list-buckets --query "Buckets[].Name" | grep "${bucket}\"" > /dev/null ; then
    echo "✅ ${bucket} S3 bucket exists"
  else
    # If not, create it
    echo "🔨 Creating ${bucket} S3 bucket"
    aws s3api create-bucket \
      --bucket "${bucket}" \
      --region "${REGION_ID}" \
      --create-bucket-configuration LocationConstraint="${REGION_ID}"
  fi
done

for bucket in "${WEBSITE_BUCKET}" "${WEBSITE_WWW_BUCKET}"; do
  echo "✅ 👷 Applying static website bucket policy to website S3 bucket"
  cat <<EOT > /tmp/.s3_bucket_policy.json
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

  aws s3api put-bucket-policy \
    --bucket "${bucket}" \
    --policy file:///tmp/.s3_bucket_policy.json

  if aws s3api get-public-access-block --bucket "${bucket}" > /dev/null ; then
    echo "✅ ${bucket} S3 bucket public access block has been configured for website access"
  else
    aws s3api put-public-access-block \
      --bucket "${bucket}" \
      --public-access-block-configuration \
        "BlockPublicAcls=false,IgnorePublicAcls=false,BlockPublicPolicy=false,RestrictPublicBuckets=false"
  fi

  echo "✅ 👷 Syncing website static assets to bucket"
  aws s3 sync "${WEBSITE_SRC_DIR}" s3://"${bucket}"/
  aws s3 website s3://"${bucket}"/ \
    --index-document index.html \
    --error-document error.html

  echo "✅ 👷 Ensuring website S3 bucket is configured for serving static assets"
  aws s3 website s3://"${bucket}"/ \
    --index-document index.html \
    --error-document error.html

done


# Website S3 Access logs
for bucket in "${WEBSITE_BUCKET}" "${WEBSITE_WWW_BUCKET}" ; do
  echo "✅ 👷 Syncing website static assets to ${bucket}"
  aws s3 sync "${WEBSITE_SRC_DIR}" s3://"${bucket}"/
  aws s3 website s3://"${bucket}"/ \
    --index-document index.html \
    --error-document error.html
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
