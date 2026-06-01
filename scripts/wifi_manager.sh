#!/bin/bash
# wifi_manager.sh — run at boot (root) by epaper-wifi-check.service
# Waits for NetworkManager to connect to a known WiFi network.
# If no connection within CONNECT_TIMEOUT seconds, starts an AP hotspot
# and writes AP info to STATUS_FILE for the Python app to read.
set -u

LOG_TAG="epaper-wifi-manager"
STATUS_FILE="/tmp/epaper-ap-mode.json"
AP_SSID="${EPAPER_AP_SSID:-EpaperSetup}"
AP_PASS="${EPAPER_AP_PASS:-epaper123}"
CONNECT_TIMEOUT="${EPAPER_CONNECT_TIMEOUT:-30}"
CON_NAME="EpaperHotspot"

log() { logger -t "$LOG_TAG" -- "$*"; }

# Remove stale status file from previous boot
rm -f "$STATUS_FILE"

log "Waiting up to ${CONNECT_TIMEOUT}s for WiFi connection..."

ELAPSED=0
while [ "$ELAPSED" -lt "$CONNECT_TIMEOUT" ]; do
    # Check for an active WiFi client connection (not AP mode)
    if nmcli -t -f TYPE,STATE dev 2>/dev/null | grep -q "^wifi:connected$"; then
        SSID=$(iwgetid wlan0 -r 2>/dev/null || echo "unknown")
        log "WiFi connected (SSID=${SSID}), AP mode not needed"
        exit 0
    fi
    sleep 2
    ELAPSED=$((ELAPSED + 2))
done

log "No WiFi connection after ${CONNECT_TIMEOUT}s — starting AP hotspot"

# Remove any leftover connection profile from a previous run
nmcli connection delete "$CON_NAME" 2>/dev/null || true

# Create hotspot (NetworkManager assigns 10.42.0.1 to wlan0 by default)
if ! nmcli dev wifi hotspot ifname wlan0 ssid "$AP_SSID" password "$AP_PASS" \
        con-name "$CON_NAME" 2>/dev/null; then
    log "ERROR: Failed to start hotspot"
    exit 1
fi

# Give NetworkManager a moment to assign the IP
sleep 2

AP_IP=$(ip -4 addr show wlan0 2>/dev/null \
    | grep -oP '(?<=inet\s)\d+(\.\d+){3}' | head -1)
AP_IP="${AP_IP:-10.42.0.1}"

# Write status file using python3 to ensure correct JSON escaping
python3 -c "
import json, sys
data = {'mode': 'ap', 'ssid': sys.argv[1], 'password': sys.argv[2], 'ip': sys.argv[3]}
print(json.dumps(data))
" "$AP_SSID" "$AP_PASS" "$AP_IP" > "$STATUS_FILE"
chmod 600 "$STATUS_FILE"

log "AP hotspot started: SSID=${AP_SSID} IP=${AP_IP}"
exit 0
