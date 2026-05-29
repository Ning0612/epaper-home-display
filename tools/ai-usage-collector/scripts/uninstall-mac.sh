#!/usr/bin/env bash
# uninstall-mac.sh — Remove the launchd job for ai-usage-collector.

set -euo pipefail

LABEL="com.epaper.ai-usage-collector"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"

if [[ -f "$PLIST" ]]; then
    launchctl unload "$PLIST" 2>/dev/null || true
    rm "$PLIST"
    echo "[uninstall] Removed launchd job and plist: $PLIST"
else
    echo "[uninstall] Plist not found — nothing to remove."
fi
