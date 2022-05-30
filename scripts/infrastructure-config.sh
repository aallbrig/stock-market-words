#!/usr/bin/env bash

# AWS common configuration, for use in infrastructure-up & infrastructure-test and whatever else

DEPENDENCIES=(aws python3)
# TODO: Validate dependencies

REGION_ID=$(aws configure get region)
WEBSITE_BUCKET="${WEBSITE_BUCKET:-stockmarketwords.com}"
WEBSITE_BUCKET_ACCESS_LOGS="${WEBSITE_BUCKET}-access-logs"
WEBSITE_WWW_BUCKET="${WEBSITE_WWW_BUCKET:-www.stockmarketwords.com}"
WEBSITE_WWW_BUCKET_ACCESS_LOGS="${WEBSITE_WWW_BUCKET}-access-logs"
WEBSITE_SRC_DIR="${WEBSITE_SRC_DIR:-static}"
BUCKET_OWNER_ID="$(aws s3api list-buckets | python3 -c "import sys, json; print(json.load(sys.stdin)['Owner']['ID'])")"
