#!/usr/bin/env bash
# pia-rotate.sh — Rotate PIA VPN IP address before pipeline run.
# Called by pia-rotate.service (systemd oneshot).
# Exits 0 even if PIA is unavailable (graceful degradation).
set -euo pipefail

PIACTL="/usr/local/bin/piactl"
MAX_WAIT=30  # seconds to wait for connection

log() { echo "$(date -u '+%Y-%m-%d %H:%M:%S UTC') [pia-rotate] $*"; }

# Check if piactl is installed
if ! command -v "$PIACTL" &>/dev/null; then
    log "WARNING: piactl not found — PIA VPN is not installed. Skipping rotation."
    exit 0
fi

# Check current connection state
STATE=$("$PIACTL" get connectionstate 2>/dev/null || echo "Unknown")
if [[ "$STATE" == "Disconnected" || "$STATE" == "Unknown" ]]; then
    log "WARNING: PIA VPN is not connected (state: $STATE). Attempting to connect..."
    "$PIACTL" connect || true
    sleep 5
    STATE=$("$PIACTL" get connectionstate 2>/dev/null || echo "Unknown")
    if [[ "$STATE" != *"Connected"* ]]; then
        log "WARNING: Could not establish VPN connection (state: $STATE). Skipping rotation."
        exit 0
    fi
fi

# Record old IP
OLD_IP=$("$PIACTL" get vpnip 2>/dev/null || echo "unknown")
log "Current IP: $OLD_IP"

# Disconnect
log "Disconnecting..."
"$PIACTL" disconnect 2>/dev/null || true
sleep 2

# Set region to auto (fastest available)
log "Setting region to auto..."
"$PIACTL" set region auto 2>/dev/null || true

# Reconnect
log "Reconnecting..."
"$PIACTL" connect 2>/dev/null || true

# Wait for connection
ELAPSED=0
while [ "$ELAPSED" -lt "$MAX_WAIT" ]; do
    STATE=$("$PIACTL" get connectionstate 2>/dev/null || echo "Unknown")
    if [[ "$STATE" == *"Connected"* ]]; then
        NEW_IP=$("$PIACTL" get vpnip 2>/dev/null || echo "unknown")
        log "Rotation complete: $OLD_IP → $NEW_IP"
        exit 0
    fi
    sleep 1
    ELAPSED=$((ELAPSED + 1))
done

# Timeout — log but don't fail the pipeline
STATE=$("$PIACTL" get connectionstate 2>/dev/null || echo "Unknown")
log "WARNING: Connection timeout after ${MAX_WAIT}s (state: $STATE). Pipeline will proceed without fresh IP."
exit 0
