#!/bin/bash
# Install the LW650XL Labels CUPS driver (macOS).
#
# Installs:
#   /usr/libexec/cups/filter/lw650xl           (raster -> TSPL filter)
#   /etc/cups/ppd/LW650XL_Labels.ppd           (label-size definitions)
# and creates the printer queue "LW650XL_Labels" (raw socket, port 9100).
#
# Run from the repo root:  sudo ./install.sh
set -euo pipefail

PRINTER_NAME="LW650XL_Labels"
PRINTER_DESC="LW650XL PRO Labels (TSPL)"
DEVICE_URI="socket://172.16.1.20:9100"
HERE="$(cd "$(dirname "$0")" && pwd)"

if [[ $EUID -ne 0 ]]; then
    echo "Run as root:  sudo $0" >&2
    exit 1
fi

echo "Installing filter ..."
cp "$HERE/cups/lw650xl" /usr/libexec/cups/filter/lw650xl
chown root:wheel /usr/libexec/cups/filter/lw650xl
chmod 755 /usr/libexec/cups/filter/lw650xl

echo "Registering queue $PRINTER_NAME ..."
lpadmin -x "$PRINTER_NAME" 2>/dev/null || true
lpadmin -p "$PRINTER_NAME" \
    -E \
    -v "$DEVICE_URI" \
    -D "$PRINTER_DESC" \
    -P "$HERE/cups/lw650xl-labels.ppd" \
    -o printer-is-shared=false

cupsenable "$PRINTER_NAME"
cupsaccept  "$PRINTER_NAME"

echo
echo "Done. Test it with:"
echo "  lp -d $PRINTER_NAME $HERE/cups/test.pdf"
