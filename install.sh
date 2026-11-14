#!/bin/bash
# Install the LW650XL Labels CUPS driver (macOS).
#
# Installs:
#   /usr/libexec/cups/filter/lw650xl           (wrapper: picks Python 3)
#   /usr/libexec/cups/filter/lw650xl.py        (raster -> TSPL filter)
#   /etc/cups/ppd/LW650XL_Labels.ppd           (label-size definitions)
# and creates the printer queue "LW650XL_Labels" (raw socket, port 9100).
#
# Run from the repo root:  sudo ./install.sh
set -euo pipefail

PRINTER_NAME="LW650XL_Labels"
PRINTER_DESC="LW650XL PRO Labels (TSPL)"
DEVICE_URI="${DEVICE_URI:-socket://172.16.1.20:9100}"
HERE="$(cd "$(dirname "$0")" && pwd)"

if [[ $EUID -ne 0 ]]; then
    echo "Run as root:  sudo $0" >&2
    exit 1
fi

echo "Installing filter ..."
cp "$HERE/cups/lw650xl" "$HERE/cups/lw650xl.py" /usr/libexec/cups/filter/
chown root:wheel /usr/libexec/cups/filter/lw650xl /usr/libexec/cups/filter/lw650xl.py
chmod 755 /usr/libexec/cups/filter/lw650xl /usr/libexec/cups/filter/lw650xl.py

# Printer icon (Word/macOS shows it for the queue; *APPrinterIconPath in the
# PPD points here).
if [ -f "$HERE/cups/LW650XL_Labels.icns" ]; then
    echo "Installing printer icon ..."
    mkdir -p /Library/Printers/Icons
    cp "$HERE/cups/LW650XL_Labels.icns" /Library/Printers/Icons/
    chown root:wheel /Library/Printers/Icons/LW650XL_Labels.icns
    chmod 644 /Library/Printers/Icons/LW650XL_Labels.icns
fi

# Same search order as the filter wrapper: the queue is useless without a
# Python 3 that actually runs (a bare CLT-less /usr/bin/python3 is only a
# stub that pops up an installer dialog).
PY_OK=""
for py in \
    /Library/Developer/CommandLineTools/usr/bin/python3 \
    /opt/homebrew/bin/python3 \
    /usr/local/bin/python3 \
    /Library/Frameworks/Python.framework/Versions/Current/bin/python3
do
    if [ -x "$py" ] && "$py" -c 'import sys' >/dev/null 2>&1; then
        PY_OK="$py"
        break
    fi
done
if [ -z "$PY_OK" ]; then
    echo "WARNING: geen werkende Python 3 gevonden." >&2
    echo "         installeer de Xcode Command Line Tools:  xcode-select --install" >&2
    echo "         of Python 3 via Homebrew:               brew install python" >&2
fi

echo "Registering queue $PRINTER_NAME ..."
lpadmin -x "$PRINTER_NAME" 2>/dev/null || true
lpadmin -p "$PRINTER_NAME" \
    -E \
    -v "$DEVICE_URI" \
    -D "$PRINTER_DESC" \
    -P "$HERE/cups/lw650xl-labels.ppd" \
    -o printer-is-shared=true \
    -o lw-gap=3 \
    -o lw-density=15 \
    -o lw-speed=1

cupsenable "$PRINTER_NAME"
cupsaccept  "$PRINTER_NAME"

# Deel de queue via IPP/Bonjour met de rest van het netwerk.
cupsctl --share-printers >/dev/null 2>&1 || true

HOSTNAME_LOCAL="$(scutil --get LocalHostName 2>/dev/null || hostname)"
echo
echo "Queue $PRINTER_NAME is aangemaakt en gedeeld."
echo "  lokaal:  lp -d $PRINTER_NAME $HERE/cups/test.pdf"
echo "  IPP:     ipp://$HOSTNAME_LOCAL.local:631/printers/$PRINTER_NAME"
echo
echo "Let op: de printer moet op $DEVICE_URI bereikbaar zijn."
