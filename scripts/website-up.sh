#!/usr/bin/env bash

# Optionally configurable
WEBSITE_PORT="${WEBSITE_PORT:-8668}"

python3 -m http.server "${WEBSITE_PORT}" --directory=static > /dev/null &
echo "Local website hosted on ${WEBSITE_PORT}"