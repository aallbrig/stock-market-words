#!/usr/bin/env bash

# Optionally configurable
WEBSITE_PORT="${WEBSITE_PORT:-8668}"

cd hugo/site && hugo server --bind 0.0.0.0 --port "${WEBSITE_PORT}" --disableLiveReload &
echo "Hugo development server running on port ${WEBSITE_PORT}"