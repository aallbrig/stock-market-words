#!/usr/bin/env bash
# Note: This script's contract is that it is idempotent

VPC_ID="${VPC_ID:-${1}}"
REGION_ID=$(aws configure get region)
WEBSITE_BUCKET="${WEBSITE_BUCKET:-english-dictionary-stocks-website}"
WEBSITE_SRC_DIR="${WEBSITE_SRC_DIR:-static}"

cat <<EOF
Date: $(date)
VPC_ID=${VPC_ID}
REGION_ID=${REGION_ID}
WEBSITE_BUCKET=${WEBSITE_BUCKET}
WEBSITE_SRC_DIR=${WEBSITE_SRC_DIR}
EOF

# Check if AWS S3 bucket (static website assets) exists for project
if aws s3api list-buckets --query "Buckets[].Name" | grep "${WEBSITE_BUCKET}\"" > /dev/null ; then
  echo "✅ website S3 bucket exists"
else
  # If not, create it
  echo "🔨 Creating S3 bucket for the website static assets"
  aws s3api create-bucket \
    --bucket "${WEBSITE_BUCKET}" \
    --region "${REGION_ID}" \
    --create-bucket-configuration LocationConstraint="${REGION_ID}"
fi

echo "✅ 👷 Syncing website static assets to bucket"
aws s3 sync "${WEBSITE_SRC_DIR}" s3://"${WEBSITE_BUCKET}"/
aws s3 website s3://"${WEBSITE_BUCKET}"/ \
  --index-document index.html \
  --error-document error.html


# Website S3 Access logs
if aws s3api list-buckets --query "Buckets[].Name" | grep "${WEBSITE_BUCKET}-access-logs\"" > /dev/null ; then
  echo "✅ website access logs S3 bucket exists"
else
  # If not, create it
  echo "🔨 Creating S3 bucket for website access logs"
  aws s3api create-bucket \
    --bucket "${WEBSITE_BUCKET}-access-logs" \
    --region "${REGION_ID}" \
    --create-bucket-configuration LocationConstraint="${REGION_ID}"
fi

if aws s3api get-public-access-block --bucket "${WEBSITE_BUCKET}" > /dev/null ; then
  echo "✅ website S3 bucket public access block has been configured for public access"
else
  aws s3api put-public-access-block \
    --bucket "${WEBSITE_BUCKET}" \
    --public-access-block-configuration \
      "BlockPublicAcls=false,IgnorePublicAcls=false,BlockPublicPolicy=false,RestrictPublicBuckets=false"
fi

echo "✅ 👷 Applying static website bucket policy to website S3 bucket"
cat <<EOT > /tmp/.s3_bucket_policy
{
  "Version":"2012-10-17",
  "Statement":[
    {
      "Sid":"AddPerm",
      "Effect":"Allow",
      "Principal": "*",
      "Action":["s3:GetObject"],
      "Resource":["arn:aws:s3:::$WEBSITE_BUCKET/*"]
    }
  ]
}
EOT

aws s3api put-bucket-policy \
  --bucket "${WEBSITE_BUCKET}" \
  --policy file:///tmp/.s3_bucket_policy

echo "✅ 👷 Ensuring website S3 bucket is configured for serving static assets"
aws s3 website s3://"${WEBSITE_BUCKET}"/ \
  --index-document index.html \
  --error-document error.html

# Check if AWS Certificate Manager cert exists for project
  # If not, create it

# Check if AWS cloudfront exists for project
  # If not, create it
