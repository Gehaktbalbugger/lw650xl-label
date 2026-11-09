#!/bin/bash
# Installeer de gedeelde etiketten-inbox + automatische watcher.
# Moet als root draaien (het script vraagt zelf om sudo).
#
#   sudo ./install-workflow.sh
#
set -euo pipefail

if [[ $EUID -ne 0 ]]; then
    exec sudo "$0" "$@"
fi

REAL_USER="${SUDO_USER:-benno}"
REAL_UID="$(id -u "$REAL_USER")"
REAL_HOME="$(dscl . -read "/Users/$REAL_USER" NFSHomeDirectory | awk '{print $2}')"
HERE="$(cd "$(dirname "$0")" && pwd)"
BASE="/Users/Shared/Labelprinter"
APP="$BASE/app"
SCRIPT="$APP/print-inbox.sh"
PLIST="/Library/LaunchDaemons/com.benno.labelprinter.watcher.plist"

echo "== Gedeelde map =="
mkdir -p "$BASE/inbox" "$BASE/printed" "$BASE/failed" "$BASE/logs" "$APP"
chown -R "$REAL_USER:staff" "$BASE"
chmod 755 "$BASE" "$BASE/printed" "$BASE/failed" "$BASE/logs"
chmod 1777 "$BASE/inbox"          # iedereen mag er PDF's/CSV's in droppen
echo "   $BASE/inbox"

echo "== Runtime kopiëren naar $APP =="
cp "$HERE/print-inbox.sh" "$HERE/pdfmedia.py" "$HERE/csv2labels.py" \
   "$HERE/../label" "$HERE/../lzo.py" "$HERE/../cups/lw650xl-labels.ppd" "$APP/"
chmod 755 "$SCRIPT" "$APP/pdfmedia.py" "$APP/csv2labels.py" "$APP/label"
chown -R "$REAL_USER:staff" "$APP"
echo "   $SCRIPT"

echo "== SMB-share 'Labelprinter' =="
# Let op: 'sharing -l | grep -q' faalt onder 'set -o pipefail' omdat grep
# eerder stopt en sharing dan SIGPIPE krijgt. Daarom eerst inlezen.
SHARES="$(sharing -l 2>/dev/null || true)"
if grep -qE '^name:[[:space:]]+Labelprinter$' <<<"$SHARES"; then
    # Bestaat al: alleen delen/guest/lezen-schrijven bijwerken. GEEN -S meegeven,
    # want de SMB-naam is dan al "Labelprinter" en sharing meldt anders
    # "smb name already exists".
    sharing -e Labelprinter -s 001 -g 001 -R 0
else
    sharing -a "$BASE" -S Labelprinter -s 001 -g 001 -R 0
fi
echo "   smb://$(scutil --get LocalHostName 2>/dev/null || hostname).local/Labelprinter"

echo "== Watcher (launchd) =="
sed -e "s|__SCRIPT__|$SCRIPT|g" -e "s|__USER__|$REAL_USER|g" \
    "$HERE/com.benno.labelprinter.watcher.plist" >"$PLIST"
chown root:wheel "$PLIST"
chmod 644 "$PLIST"

launchctl bootout system/com.benno.labelprinter.watcher 2>/dev/null || true
if ! launchctl bootstrap system "$PLIST" 2>/dev/null; then
    launchctl load -w "$PLIST"
fi
launchctl enable "system/com.benno.labelprinter.watcher" 2>/dev/null || true
launchctl kickstart -k "system/com.benno.labelprinter.watcher" 2>/dev/null || true

echo
echo "Klaar. Testen:"
echo "  cp \"$HERE/../cups/test.pdf\" \"$BASE/inbox/\""
echo "  sleep 3; tail -n 20 \"$BASE/logs/print.log\""
