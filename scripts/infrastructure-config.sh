#!/usr/bin/env bash

# AWS common configuration, for use in infrastructure-up & infrastructure-test and whatever else

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

