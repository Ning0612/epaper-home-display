#!/bin/bash
# wifi_manager.sh — run at boot (root) by epaper-wifi-check.service
# Waits for NetworkManager to connect to a known WiFi network.
# If no connection within CONNECT_TIMEOUT seconds, starts an AP hotspot
# and writes AP info to STATUS_FILE for the Python app to read.
set -u

LOG_TAG="epaper-wifi-manager"
STATUS_FILE="/tmp/epaper-ap-mode.json"
SCAN_CACHE_FILE="/tmp/epaper-wifi-scan-cache.txt"
AP_SSID="${EPAPER_AP_SSID:-EpaperSetup}"
AP_PASS="${EPAPER_AP_PASS:-epaper123}"
CONNECT_TIMEOUT="${EPAPER_CONNECT_TIMEOUT:-30}"
CON_NAME="EpaperHotspot"

log() { logger -t "$LOG_TAG" -- "$*"; }

# Remove stale status file from previous boot.
# Guard against TOCTOU: if STATUS_FILE is a directory (e.g. local privilege escalation attempt), abort.
if [ -d "$STATUS_FILE" ]; then
    log "ERROR: $STATUS_FILE is a directory — possible TOCTOU; aborting"
    exit 1
fi
rm -f "$STATUS_FILE" \
    || { log "ERROR: Failed to remove stale STATUS_FILE — aborting to prevent partial state"; exit 1; }
# Clean stale scan cache from previous boot (non-critical; ignore failure).
rm -f "$SCAN_CACHE_FILE" || true

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

# Pre-scan before AP: Pi Zero 2W single radio cannot scan while in hotspot mode.
# Use mktemp + mv -T for atomic write to prevent symlink TOCTOU in /tmp.
log "Pre-scanning WiFi networks before starting hotspot..."
TMP_SCAN="$(mktemp /tmp/.epaper-scan-XXXXXX)" \
    || { log "WARN: mktemp for scan cache failed; skipping pre-scan"; TMP_SCAN=""; }
if [ -n "$TMP_SCAN" ]; then
    if nmcli -t -f SSID,SIGNAL,SECURITY dev wifi list --rescan auto \
            > "$TMP_SCAN" 2>/dev/null; then
        COUNT=$(grep -c . "$TMP_SCAN" 2>/dev/null || echo 0)
        if getent group pi > /dev/null 2>&1; then
            chown root:pi "$TMP_SCAN" 2>/dev/null || true
            chmod 640 "$TMP_SCAN" 2>/dev/null || true
        else
            chmod 644 "$TMP_SCAN" 2>/dev/null || true
        fi
        mv -T "$TMP_SCAN" "$SCAN_CACHE_FILE" \
            && log "Pre-scan complete: ${COUNT} networks cached" \
            || { rm -f "$TMP_SCAN"; log "WARN: scan cache mv -T failed"; }
    else
        rm -f "$TMP_SCAN"
        log "Pre-scan failed — portal will show empty list"
    fi
fi

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

# Write AP status file with explicit error handling and temp-file cleanup.
TMP_STATUS="$(mktemp /tmp/.epaper-ap-XXXXXX)" || { log "ERROR: mktemp failed"; exit 1; }
# Guarantee cleanup of temp file on any exit after this point.
trap 'rm -f "$TMP_STATUS"' EXIT INT TERM

python3 -c "
import json, sys
data = {'mode': 'ap', 'ssid': sys.argv[1], 'password': sys.argv[2], 'ip': sys.argv[3]}
print(json.dumps(data))
" "$AP_SSID" "$AP_PASS" "$AP_IP" > "$TMP_STATUS" \
    || { log "ERROR: Failed to write AP status JSON"; exit 1; }

if getent group pi > /dev/null 2>&1; then
    # pi group exists: hard fail rather than silently downgrade to world-readable.
    chown root:pi "$TMP_STATUS" \
        || { log "ERROR: chown root:pi failed — cannot safely restrict AP status file"; exit 1; }
    chmod 640 "$TMP_STATUS" \
        || { log "ERROR: chmod 640 failed"; exit 1; }
else
    # No pi group on this OS; 644 is the only option to let the service user read the file.
    # Known trade-off — see docs/configuration.md for security implications.
    chmod 644 "$TMP_STATUS" \
        || { log "ERROR: chmod 644 failed"; exit 1; }
fi

# mv -T (Linux): fails if STATUS_FILE was replaced by a directory after the initial rm -f check.
mv -T "$TMP_STATUS" "$STATUS_FILE" \
    || { log "ERROR: mv -T to STATUS_FILE failed — possible TOCTOU or filesystem error"; exit 1; }
trap - EXIT INT TERM  # mv succeeded; unregister cleanup so STATUS_FILE is not deleted

log "AP hotspot started: SSID=${AP_SSID} IP=${AP_IP}"
exit 0
