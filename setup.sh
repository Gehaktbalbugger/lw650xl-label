#!/bin/bash
# Eenmalige installatie van de complete etiketten-workflow.
#
#   cd ~/Documents/Standaardproject/label-printer
#   ./setup.sh
#
# Het script vraagt om je macOS-wachtwoord (nodig voor de CUPS-filter,
# de gedeelde map en de launchd-watcher).
set -euo pipefail

if [[ $EUID -ne 0 ]]; then
    exec sudo "$0" "$@"
fi

HERE="$(cd "$(dirname "$0")" && pwd)"
DEVICE_URI="${DEVICE_URI:-socket://172.16.1.20:9100}"

echo "== 1/2  CUPS-queue =="
DEVICE_URI="$DEVICE_URI" "$HERE/install.sh"

echo
echo "== 2/2  Gedeelde inbox + watcher =="
"$HERE/workflow/install-workflow.sh"

echo
echo "=================================================================="
echo "Klaar. Vanaf nu:"
echo "  • Zet een PDF in /Users/Shared/Labelprinter/inbox"
echo "  • of op een ander systeem in \\\\$(scutil --get LocalHostName 2>/dev/null || hostname)\\Labelprinter\\inbox"
echo "  • de iMac print hem automatisch op de LW650XL PRO."
echo "=================================================================="
