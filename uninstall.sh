#!/bin/bash
# Uninstall the LW650XL Labels driver and remove the CUPS queue.
# Run:  sudo ./uninstall.sh
set -euo pipefail

PRINTER_NAME="LW650XL_Labels"

if [[ $EUID -ne 0 ]]; then
    echo "Run as root:  sudo $0" >&2
    exit 1
fi

echo "Removing queue $PRINTER_NAME ..."
lpadmin -x "$PRINTER_NAME" 2>/dev/null || true

echo "Removing filter and PPD ..."
rm -f /usr/libexec/cups/filter/lw650xl /usr/libexec/cups/filter/lw650xl.py
rm -f "/etc/cups/ppd/$PRINTER_NAME.ppd"

echo "Uninstalled."
