#!/bin/bash
set -u

LOG_TAG="epaper-auto-update"
REPO_DIR="/home/pi/epaper-home-display"
SERVICE="epaper-home-display.service"

log() { logger -t "$LOG_TAG" "$*"; }

cd "$REPO_DIR" || { log "ERROR: cannot cd to $REPO_DIR"; exit 1; }

# Prevent +x conflicts: Windows commits don't carry execute bits, but the Pi
# needs scripts to be executable.  Tracking fileMode would cause every pull to
# see modified files and abort.  This setting is idempotent.
git config core.fileMode false

# Fetch; skip if network unavailable
if ! git fetch origin --quiet 2>/dev/null; then
    log "git fetch failed (network issue?), skipping"
    exit 0
fi

LOCAL=$(git rev-parse HEAD)
REMOTE=$(git rev-parse origin/main 2>/dev/null || echo "")

[ -z "$REMOTE" ] && { log "cannot resolve origin/main, skipping"; exit 0; }
[ "$LOCAL" = "$REMOTE" ] && exit 0

log "Update available: ${LOCAL:0:7} -> ${REMOTE:0:7}, pulling..."

REQ_BEFORE=$(md5sum requirements.txt 2>/dev/null | cut -d' ' -f1 || echo "")

git pull 2>&1 | logger -t "$LOG_TAG"
PULL_STATUS="${PIPESTATUS[0]}"
if [ "$PULL_STATUS" -ne 0 ]; then
    log "git pull failed (exit $PULL_STATUS), aborting update"
    exit 1
fi

# Restore execute permissions on scripts after pull (Windows commits strip +x).
chmod +x "$REPO_DIR/scripts/"*.sh

REQ_AFTER=$(md5sum requirements.txt 2>/dev/null | cut -d' ' -f1 || echo "")
if [ "$REQ_BEFORE" != "$REQ_AFTER" ]; then
    log "requirements.txt changed, updating dependencies..."
    .venv/bin/pip install -r requirements.txt --quiet 2>&1 | logger -t "$LOG_TAG"
    PIP_STATUS="${PIPESTATUS[0]}"
    if [ "$PIP_STATUS" -ne 0 ]; then
        log "pip install failed (exit $PIP_STATUS), aborting restart"
        exit 1
    fi
fi

if ! /usr/bin/sudo /usr/bin/systemctl restart "$SERVICE"; then
    log "systemctl restart failed"
    exit 1
fi
log "Service restarted after update to ${REMOTE:0:7}"
