#!/usr/bin/env bash

WEBSITE_PORT="${WEBSITE_PORT:-8668}"

lsof -i tcp:"${WEBSITE_PORT}" | awk 'NR!=1 {print $2}' | xargs kill
