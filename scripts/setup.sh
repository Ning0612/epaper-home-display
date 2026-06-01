#!/bin/bash
# setup.sh — Complete first-time deployment for ePaper Home Display
# Run once on a fresh Pi (or after a clean re-flash):
#   bash ~/epaper-home-display/scripts/setup.sh
#
# Idempotent: safe to re-run after updates or troubleshooting.
set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"

log()  { echo "[INFO]  $*"; }
warn() { echo "[WARN]  $*"; }
die()  { echo "[ERROR] $*" >&2; exit 1; }

log "=== ePaper Home Display — Full Setup ==="
log "Repo: $REPO_DIR"
cd "$REPO_DIR"

# ── 1. Git: disable fileMode to prevent +x conflicts from Windows commits ──────
log "Configuring git..."
git config core.fileMode false
log "  core.fileMode = false (avoids +x conflicts from Windows commits)"

# ── 2. Script permissions ────────────────────────────────────────────────────────
log "Setting script permissions..."
chmod +x "$REPO_DIR/scripts/"*.sh
log "  chmod +x scripts/*.sh"

# ── 3. Python virtual environment ───────────────────────────────────────────────
log "Setting up Python virtual environment..."
if [ ! -f "$REPO_DIR/.venv/bin/python" ]; then
    python3 -m venv "$REPO_DIR/.venv"
    log "  Created .venv"
fi
"$REPO_DIR/.venv/bin/pip" install -r requirements.txt --quiet \
    && log "  Dependencies installed" \
    || die "pip install failed"

# ── 4. Sudoers: WiFi provisioning (nmcli) ───────────────────────────────────────
log "Installing sudoers rules..."
NMCLI=$(command -v nmcli) || die "nmcli not found — is NetworkManager installed?"

SUDOERS_WIFI="/etc/sudoers.d/epaper-wifi"
sudo tee "$SUDOERS_WIFI" > /dev/null << EOF
# ePaper Home Display — WiFi provisioning (managed by setup.sh)
pi ALL=(ALL) NOPASSWD: ${NMCLI} -t -f * dev wifi list --rescan no
pi ALL=(ALL) NOPASSWD: ${NMCLI} -t -f * dev wifi list --rescan auto
pi ALL=(ALL) NOPASSWD: ${NMCLI} dev wifi hotspot ifname wlan0 ssid * password *
pi ALL=(ALL) NOPASSWD: ${NMCLI} connection add type wifi *
pi ALL=(ALL) NOPASSWD: ${NMCLI} connection up EpaperWifiSetup
pi ALL=(ALL) NOPASSWD: ${NMCLI} connection delete EpaperHotspot
pi ALL=(ALL) NOPASSWD: ${NMCLI} connection delete EpaperWifiSetup
EOF
sudo chmod 440 "$SUDOERS_WIFI"
sudo visudo -c -f "$SUDOERS_WIFI" || die "WiFi sudoers syntax check failed"
log "  $SUDOERS_WIFI"

# ── 5. Sudoers: service restart (for auto_update.sh) ────────────────────────────
SUDOERS_SVC="/etc/sudoers.d/epaper-service"
sudo tee "$SUDOERS_SVC" > /dev/null << EOF
# ePaper Home Display — service management (managed by setup.sh)
pi ALL=(ALL) NOPASSWD: /usr/bin/systemctl restart epaper-home-display.service
pi ALL=(ALL) NOPASSWD: /usr/bin/systemctl restart epaper-wifi-check.service
EOF
sudo chmod 440 "$SUDOERS_SVC"
sudo visudo -c -f "$SUDOERS_SVC" || die "Service sudoers syntax check failed"
log "  $SUDOERS_SVC"

# ── 6. Systemd service files ─────────────────────────────────────────────────────
log "Installing systemd service files..."
sudo cp "$REPO_DIR/systemd/epaper-wifi-check.service"   /etc/systemd/system/
sudo cp "$REPO_DIR/systemd/epaper-home-display.service" /etc/systemd/system/
sudo cp "$REPO_DIR/systemd/epaper-auto-update.service"  /etc/systemd/system/
sudo cp "$REPO_DIR/systemd/epaper-auto-update.timer"    /etc/systemd/system/
sudo systemctl daemon-reload
log "  daemon-reload complete"

# ── 7. Enable services ───────────────────────────────────────────────────────────
log "Enabling services..."
sudo systemctl enable epaper-wifi-check.service
sudo systemctl enable epaper-home-display.service
sudo systemctl enable epaper-auto-update.timer
log "  epaper-wifi-check.service   → enabled"
log "  epaper-home-display.service → enabled"
log "  epaper-auto-update.timer    → enabled"

# ── 8. Start / restart services ──────────────────────────────────────────────────
log "Starting services..."
sudo systemctl start  epaper-auto-update.timer

# wifi-check is a oneshot; run it now to decide AP vs client before starting app.
# Ignore failure here — the service logs its own errors.
sudo systemctl start epaper-wifi-check.service 2>/dev/null || true

sudo systemctl restart epaper-home-display.service
log "  Services started"

# ── 9. Status ────────────────────────────────────────────────────────────────────
echo ""
log "=== Service Status ==="
for svc in \
    epaper-wifi-check.service \
    epaper-home-display.service \
    epaper-auto-update.timer; do
    STATUS=$(systemctl is-active "$svc" 2>/dev/null || echo "unknown")
    if [ "$STATUS" = "active" ] || [ "$STATUS" = "activating" ]; then
        log "  $svc: $STATUS"
    else
        warn "  $svc: $STATUS  (run: journalctl -u $svc -n 30)"
    fi
done

echo ""
log "=== Quick Reference ==="
log "  Tail app logs:   journalctl -u epaper-home-display -f"
log "  Tail update log: journalctl -t epaper-auto-update -n 20"
log "  Timer status:    systemctl list-timers epaper-auto-update.timer"
log ""
log "Setup complete."
