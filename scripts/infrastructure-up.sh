#!/usr/bin/env bash
# Note: This script's contract is that it is idempotent

VPC_ID="${VPC_ID:-${1}}"
REGION_ID="${REGION_ID:-us-east-2}"
WEBSITE_BUCKET="${WEBSITE_BUCKET:-english-dictionary-stocks-website}"

# Check if AWS S3 bucket (static website assets) exists for project
if $(aws s3api list-buckets --query "Buckets[].Name" | grep "english-dictionary-stocks-website"); then
  # If not, create it
  echo "🔨 Creating S3 bucket for the website static assets in REGION ${REGION_ID}"
  aws s3api create-bucket \
    --bucket "${WEBSITE_BUCKET}" \
    --region "${REGION_ID}" \
    --create-bucket-configuration LocationConstraint="${REGION_ID}"
else
  echo "✅ S3 bucket exists for the website"
fi

echo "🔨 Ensuring S3 bucket is configured for serving static assets"
aws s3 website s3://"${WEBSITE_BUCKET}"/ \
  --index-document index.html \
  --error-document error.html

# Check if AWS Certificate Manager cert exists for project
  # If not, create it

# Check if AWS cloudfront exists for project
  # If not, create it
