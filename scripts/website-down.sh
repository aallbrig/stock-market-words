#!/usr/bin/env bash

WEBSITE_PORT="${WEBSITE_PORT:-8668}"

# Kill Hugo server process
pkill -f "hugo server.*${WEBSITE_PORT}"
