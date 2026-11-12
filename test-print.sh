#!/bin/bash
# Print-proef met de uitlijning die nog NIET in de driver staat.
#
#   ./test-print.sh adres.pdf                 # vierkante rol, 270 graden
#   ./test-print.sh adres.pdf --size LW_57x32 # andere rol
#   ./test-print.sh adres.pdf --flush         # rand aan rand
#   ROL=a ./test-print.sh adres.pdf           # zie ROLLEN hieronder
#   ./test-print.sh --status                  # welke waarden gelden nu waar?
#
# CUPS-opties van één taak overschrijven de queue- en PPD-waarden, dus je
# hoef niets te installeren en er is geen wachtwoord nodig. Met
# ./test-print.sh --commit schrijf je ze alsnog in de PPD en installeer je.
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
QUEUE="${QUEUE:-LW650XL_Labels}"
PPD_SRC="$HERE/cups/lw650xl-labels.ppd"

# Uitgefijnde rollen. left/right/top/bottom/voffset/rows komen uit
# KNOWLEDGE.md; de gemeten waarden van deze sessie staan als "proef".
ROL="vierkant"
MODE="proef"
PDF=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --size)   ROL="${2:?--size heeft een naam nodig}"; shift 2 ;;
        --final)  MODE="geinstalleerd"; shift ;;
        --flush)  MODE="flush"; shift ;;
        --status) MODE="status"; shift ;;
        --commit) MODE="commit"; shift ;;
        -h|--help) sed -n '2,15p' "$0"; exit 0 ;;
        *) PDF="$1"; shift ;;
    esac
done

case "$ROL" in
    LW_26x25|vierkant) ROL="LW_26x25"; PITCH=33.97; GAP=3; ROWS=356; ROTATE=270
        LEFT=1.5; RIGHT=1.4; TOP=1.9; VOFFSET=2.5; BOTTOM=0 ;;
    LW_57x32) ROL="LW_57x32"; PITCH=38.6; GAP=3; ROWS=0; ROTATE=0
        LEFT=2.03; RIGHT=0.76; TOP=5.08; VOFFSET=0.34; BOTTOM=0.68 ;;
    LW_36x89) ROL="LW_36x89"; PITCH=93; GAP=4; ROWS=0; ROTATE=0
        LEFT=3.0; RIGHT=3.0; TOP=-0.5; VOFFSET=0; BOTTOM=1.0 ;;
    *) echo "onbekende rol: $ROL (bekend: vierkant/LW_26x25, LW_57x32, LW_36x89)" >&2; exit 1 ;;
esac

if [[ "$MODE" == "flush" ]]; then
    # use the full width: only the dead zone on the left remains
    RIGHT=0; BOTTOM=0; VOFFSET="$TOP"
fi

if [[ "$MODE" == "status" || -z "$PDF" ]]; then
    echo "roll $ROL: pitch=$PITCH gap=$GAP rows=$ROWS rotate=$ROTATE"
    echo "left=$LEFT right=$RIGHT top=$TOP voffset=$VOFFSET bottom=$BOTTOM"
    echo "geinstalleerde PPD:"
    grep -o "lw-media $ROL.*" /etc/cups/ppd/$QUEUE.ppd 2>/dev/null || echo "  (geen lw-media-regel gevonden)"
    if [[ -z "$PDF" ]]; then
        echo
        echo "gebruik: $0 bestand.pdf [--size NAAM] [--flush|--final] | --commit"
    fi
    exit 0
fi

if [[ "$MODE" == "commit" ]]; then
    # deze proefwaarden in de repo-PPD zetten en installeren (root nodig)
    python3 - "$PPD_SRC" "$ROL" "$PITCH" "$GAP" "$ROWS" "$ROTATE" "$LEFT" "$RIGHT" "$TOP" "$VOFFSET" "$BOTTOM" <<'PY'
import re, sys
ppd, name, pitch, gap, rows, rotate, left, right, top, voffset, bottom = sys.argv[1:12]
line = (f"*% lw-media {name} pitch={pitch} gap={gap} left={left} right={right} "
        f"top={top} voffset={voffset} bottom={bottom} rotate={rotate}")
if rows != "0":
    line += f" rows={rows}"
s = open(ppd).read()
s = re.sub(rf"^\*%\s*lw-media\s+{name}\b.*\n", "", s, flags=re.M)
i = s.find("*EOF")
s = (s[:i] + line + "\n" + s[i:]) if i != -1 else (s + line + "\n")
open(ppd, "w").write(s)
print(line)
PY
    rsync -a --exclude .git --exclude .DS_Store "$HERE/" /Users/Shared/Labelprinter/setup/
    echo "installeren (vraagt om je wachtwoord) ..."
    sudo /Users/Shared/Labelprinter/setup/install.sh
    exit 0
fi

[[ -f "$PDF" ]] || { echo "bestand niet gevonden: $PDF" >&2; exit 1; }

OPTS=(-d "$QUEUE" -o "media=$ROL")
[[ "$MODE" == "proef" || "$MODE" == "flush" ]] && OPTS+=(
    -o "lw-pitch=$PITCH" -o "lw-gap=$GAP" -o "lw-left=$LEFT" -o "lw-right=$RIGHT"
    -o "lw-top=$TOP" -o "lw-voffset=$VOFFSET" -o "lw-bottom=$BOTTOM"
    -o "lw-rotate=$ROTATE")
[[ "${ROWS:-0}" != "0" && ("$MODE" == "proef" || "$MODE" == "flush") ]] && OPTS+=(-o "lw-rows=$ROWS")

echo "proef met: ${OPTS[*]} $PDF"
lp "${OPTS[@]}" "$(pwd)/$PDF"
