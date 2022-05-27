#!/usr/bin/env bash
SCRIPT_DIR="$( cd -- "$( dirname -- "${BASH_SOURCE[0]:-$0}"; )" &> /dev/null && pwd 2> /dev/null; )";
count=0

# source configuration
. "${SCRIPT_DIR}"/infrastructure-config.sh

# Can I see access logs for all websites in S3?

# 2.
# It show that I have a static website AWS S3 resource
  # Note: for each S3 bucket representing all the domains I own
for bucket in "${WEBSITE_BUCKET}" "${WEBSITE_BUCKET_ACCESS_LOGS}" "${WEBSITE_WWW_BUCKET}" "${WEBSITE_WWW_BUCKET_ACCESS_LOGS}"; do
  if aws s3api list-buckets --query "Buckets[].Name" | grep "${bucket}\"" > /dev/null ; then
    echo "✅ $((++count)) Test Passed: S3 bucket ${bucket} exists"
  else
    echo "❌ TEST FAIL: S3 bucket ${bucket} DOES NOT EXIST"
  fi
done
# 1.
# It shows that I can see access logs for the static website deployed in S3
bucket_accesslog_pairs=("${WEBSITE_BUCKET}:${WEBSITE_BUCKET_ACCESS_LOGS}" "${WEBSITE_WWW_BUCKET}:${WEBSITE_WWW_BUCKET_ACCESS_LOGS}")
for bucket_accesslog_pair in ${bucket_accesslog_pairs[@]} ; do
  IFS=':'
  read -a pair <<< "${bucket_accesslog_pair}"
  website_bucket="${pair[0]}"
  access_log_bucket="${pair[1]}"
  # echo "website bucket ${website_bucket}"
  # echo "access log bucket ${access_log_bucket}"
  if aws s3api get-bucket-policy --bucket "${access_log_bucket}" &> /dev/null ; then
    echo "✅ $((++count)) Test Passed: S3 bucket access log policy for ${access_log_bucket} exists"
  else
    echo "❌ $((++count)) TEST FAIL: S3 bucket access log policy for ${access_log_bucket} DOES NOT EXIST"
  fi

  # --output text results in an empty string if this isn't set up
  # This alternative setup detects an empty string (versus a failing command)
  get_bucket_acl_query_result=$(aws s3api get-bucket-acl --bucket "${access_log_bucket}" --query 'Grants[?Grantee.URI==`http://acs.amazonaws.com/groups/s3/LogDelivery`]' --output text)
  if [ -n "${get_bucket_acl_query_result}" ] ; then
    echo "✅ $((++count)) Test Passed: S3 access log bucket has bucket acl policy for ${access_log_bucket}"
  else
    echo "❌ $((++count)) TEST FAIL: S3 access log bucket has bucket acl policy for ${access_log_bucket}"
  fi

  if aws s3api get-bucket-logging --bucket "${website_bucket}" | \
    python3 -c "import sys, json; print(json.load(sys.stdin)['LoggingEnabled'])" 2&>/dev/null ; then
    echo "✅ $((++count)) Test Passed: website S3 bucket ${website_bucket} is configured for logging"
  else
    echo "❌ $((++count)) TEST FAIL: website S3 bucket ${website_bucket} NOT CONFIGURED FOR LOGGING"
  fi
done


