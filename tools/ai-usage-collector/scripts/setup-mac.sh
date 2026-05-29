#!/usr/bin/env bash
# setup-mac.sh — Install ai-usage-collector and register a launchd job (every 3 min).
#
# 1. Verifies .env exists
# 2. npm install + npm run build
# 3. Creates logs/ directory
# 4. Writes ~/Library/LaunchAgents/com.epaper.ai-usage-collector.plist
# 5. Loads via launchctl
#
# To remove: scripts/uninstall-mac.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"   # tools/ai-usage-collector
LABEL="com.epaper.ai-usage-collector"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"

echo "[setup] Project dir: $PROJECT_DIR"

# ── Guard: .env must exist ─────────────────────────────────────────────────────
if [[ ! -f "$PROJECT_DIR/.env" ]]; then
    echo "[setup] ERROR: .env not found."
    echo "         cp \"$PROJECT_DIR/.env.example\" \"$PROJECT_DIR/.env\""
    echo "         Then edit it and set PI_URL."
    exit 1
fi

# ── npm install + build ────────────────────────────────────────────────────────
cd "$PROJECT_DIR"
echo "[setup] Installing npm dependencies..."
npm install --prefer-offline
echo "[setup] Building TypeScript..."
npm run build

DIST_ENTRY="$PROJECT_DIR/dist/index.js"
if [[ ! -f "$DIST_ENTRY" ]]; then
    echo "[setup] ERROR: Build failed — $DIST_ENTRY not found."
    exit 1
fi

# ── Create logs directory ──────────────────────────────────────────────────────
mkdir -p "$PROJECT_DIR/logs"

# ── Resolve node path ─────────────────────────────────────────────────────────
NODE_PATH="$(command -v node || true)"
if [[ -z "$NODE_PATH" ]]; then
    echo "[setup] ERROR: node not found in PATH."
    exit 1
fi
echo "[setup] Using node: $NODE_PATH"

# ── Write launchd plist ────────────────────────────────────────────────────────
mkdir -p "$HOME/Library/LaunchAgents"

cat > "$PLIST" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>$LABEL</string>

  <key>ProgramArguments</key>
  <array>
    <string>$NODE_PATH</string>
    <string>$DIST_ENTRY</string>
  </array>

  <key>WorkingDirectory</key>
  <string>$PROJECT_DIR</string>

  <key>StartInterval</key>
  <integer>180</integer>

  <key>RunAtLoad</key>
  <true/>

  <key>StandardOutPath</key>
  <string>$PROJECT_DIR/logs/collector.log</string>

  <key>StandardErrorPath</key>
  <string>$PROJECT_DIR/logs/collector.err</string>

  <key>EnvironmentVariables</key>
  <dict>
    <key>PATH</key>
    <string>$(dirname "$NODE_PATH"):/usr/local/bin:/usr/bin:/bin</string>
  </dict>
</dict>
</plist>
EOF

echo "[setup] Wrote: $PLIST"

# ── Load launchd job ───────────────────────────────────────────────────────────
# Unload first in case an old version is running
launchctl unload "$PLIST" 2>/dev/null || true
launchctl load "$PLIST"

echo "[setup] Loaded launchd job: $LABEL (every 3 min)"
echo "[setup] Logs: $PROJECT_DIR/logs/"
echo "[setup] Done. Use scripts/uninstall-mac.sh to remove."
