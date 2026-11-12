#!/bin/bash
# Verwijder de watcher en de SMB-share (de map en de CUPS-queue blijven staan).
set -euo pipefail

if [[ $EUID -ne 0 ]]; then
    exec sudo "$0" "$@"
fi

PLIST="/Library/LaunchDaemons/com.benno.labelprinter.watcher.plist"

launchctl bootout system/com.benno.labelprinter.watcher 2>/dev/null || true
rm -f "$PLIST"
sharing -r Labelprinter 2>/dev/null || true

echo "Watcher and share removed. Files remain in /Users/Shared/Labelprinter."
