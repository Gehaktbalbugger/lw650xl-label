#!/bin/bash
# One-time installation of the complete label workflow.
#
#   cd ~/Documents/Standaardproject/label-printer
#   ./setup.sh
#
# The script asks for your macOS password (needed for the CUPS filter,
# the shared folder and the launchd watcher).
set -euo pipefail

if [[ $EUID -ne 0 ]]; then
    exec sudo "$0" "$@"
fi

HERE="$(cd "$(dirname "$0")" && pwd)"
DEVICE_URI="${DEVICE_URI:-socket://172.16.1.20:9100}"

echo "== 1/2  CUPS-queue =="
DEVICE_URI="$DEVICE_URI" "$HERE/install.sh"

echo
echo "== 2/2  Shared inbox + watcher =="
"$HERE/workflow/install-workflow.sh"

echo
echo "=================================================================="
echo "Done. From now on:"
echo "  • Drop a PDF into /Users/Shared/Labelprinter/inbox"
echo "  • or, from another system, into \\\\$(scutil --get LocalHostName 2>/dev/null || hostname)\\Labelprinter\\inbox"
echo "  • the iMac prints it automatically on the LW650XL PRO."
echo "=================================================================="
