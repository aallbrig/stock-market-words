#!/usr/bin/env bash
SCRIPT_DIR="$( cd -- "$( dirname -- "${BASH_SOURCE[0]:-$0}"; )" &> /dev/null && pwd 2> /dev/null; )";
. "${SCRIPT_DIR}"/infrastructure-config.sh
test_counter=0

# Dependencies... JUST for this particular script
DEPENDENCIES=(aws python3 grep)
for required_executable in ${DEPENDENCIES[@]} ; do
  if ! which "${required_executable}" > /dev/null ; then
    echo "❌ required executable \"${required_executable}\" is not defined"
    exit 1
  fi
done

# Fact: I know that relevant S3 buckets exist
for bucket in "${WEBSITE_BUCKET}" "${WEBSITE_BUCKET_ACCESS_LOGS}" "${WEBSITE_WWW_BUCKET}" "${WEBSITE_WWW_BUCKET_ACCESS_LOGS}"; do
  if aws s3api list-buckets --query "Buckets[].Name" | grep "${bucket}\"" > /dev/null ; then
    echo "✅ $((++test_counter)) Test Passed: S3 bucket ${bucket} exists"
  else
    echo "❌ $((++test_counter)) TEST FAIL: S3 bucket ${bucket} DOES NOT EXIST"
  fi
done

bucket_accesslog_pairs=("${WEBSITE_BUCKET}:${WEBSITE_BUCKET_ACCESS_LOGS}" "${WEBSITE_WWW_BUCKET}:${WEBSITE_WWW_BUCKET_ACCESS_LOGS}")
for bucket_accesslog_pair in ${bucket_accesslog_pairs[@]} ; do
  IFS=':'
  read -a pair <<< "${bucket_accesslog_pair}"
  website_bucket="${pair[0]}"
  access_log_bucket="${pair[1]}"

  # Fact: Access logs have a log policy
  # TODO: update this so it doesn't just check for existence of a bucket policy
  if aws s3api get-bucket-policy --bucket "${access_log_bucket}" &> /dev/null ; then
    echo "✅ $((++test_counter)) Test Passed: S3 bucket access log policy for ${access_log_bucket} exists"
  else
    echo "❌ $((++test_counter)) TEST FAIL: S3 bucket access log policy for ${access_log_bucket} DOES NOT EXIST"
  fi

  # Fact: The access log bucket has proper ACL configured
  # --output text results in an empty string if this isn't set up
  # This alternative setup detects an empty string (versus a failing command)
  get_bucket_acl_query_result=$(aws s3api get-bucket-acl \
    --bucket "${access_log_bucket}" \
    --query 'Grants[?Grantee.URI==`http://acs.amazonaws.com/groups/s3/LogDelivery`]' \
    --output text)
  if [ -n "${get_bucket_acl_query_result}" ] ; then
    echo "✅ $((++test_counter)) Test Passed: S3 access log bucket has bucket acl policy for ${access_log_bucket}"
  else
    echo "❌ $((++test_counter)) TEST FAIL: S3 access log bucket has bucket acl policy for ${access_log_bucket}"
  fi

  if aws s3api get-bucket-logging --bucket "${website_bucket}" | \
    python3 -c "import sys, json; print(json.load(sys.stdin)['LoggingEnabled'])" 2&>/dev/null ; then
    echo "✅ $((++test_counter)) Test Passed: website S3 bucket ${website_bucket} is configured for logging"
  else
    echo "❌ $((++test_counter)) TEST FAIL: website S3 bucket ${website_bucket} NOT CONFIGURED FOR LOGGING"
  fi
done


