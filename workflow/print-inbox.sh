#!/bin/bash
# Print alles wat in de gedeelde etiketten-inbox verschijnt.
#
#   *.pdf  -> naar de CUPS-queue LW650XL_Labels (formaat uit de PDF)
#   *.csv  -> één etiket per rij via de label-CLI (UTF-8, ; of , als scheiding)
#
# Wordt gestart door launchd (WatchPaths) en is ook handmatig te draaien:
#   ./print-inbox.sh
#   LW_DRY_RUN=1 ./print-inbox.sh        # laat alleen de lp-opdrachten zien
#
set -u

BASE="${LW_BASE:-/Users/Shared/Labelprinter}"
INBOX="$BASE/inbox"
DONE="$BASE/printed"
FAIL="$BASE/failed"
LOG="$BASE/logs/print.log"
QUEUE="${LW_QUEUE:-LW650XL_Labels}"
HERE="$(cd "$(dirname "$0")" && pwd)"
PPD="${LW_PPD:-/etc/cups/ppd/$QUEUE.ppd}"
[[ -r "$PPD" ]] || PPD="$HERE/lw650xl-labels.ppd"
[[ -r "$PPD" ]] || PPD="$HERE/../cups/lw650xl-labels.ppd"
PY="${LW_PYTHON:-/usr/bin/python3}"
# Afstand tussen de etiketten (0 voor continu materiaal). Standaard leeg: de
# PPD-per-maat-waarde (zie add-size.sh) mag beslissen, anders overschrijft deze
# globale instelling elke individuele rol.
GAP="${LW_GAP:-}"
DENSITY="${LW_DENSITY:-15}"
SPEED="${LW_SPEED:-1}"
HOST="${LW_HOST:-172.16.1.20}"
export PATH="/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"

# launchd start dit als de gebruiker; zorg dat ~/Library/Python (Pillow)
# vindbaar is, ook als HOME niet is gezet.
REAL_HOME="$(dscl . -read "/Users/$(id -un)" NFSHomeDirectory 2>/dev/null | awk '{print $2}')"
[[ -n "$REAL_HOME" ]] && export HOME="$REAL_HOME"

mkdir -p "$INBOX" "$DONE" "$FAIL" "$BASE/logs"

log() { printf '%s  %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*" >>"$LOG"; }

# Eén watcher tegelijk; mkdir is atomair op macOS.
if ! mkdir "$BASE/.watcher.lock" 2>/dev/null; then
    # Opruimen als een vorige run hard is afgebroken (> 10 min oud).
    if [[ -n "$(find "$BASE/.watcher.lock" -maxdepth 0 -mmin +10 2>/dev/null)" ]]; then
        rmdir "$BASE/.watcher.lock" 2>/dev/null || true
        mkdir "$BASE/.watcher.lock" 2>/dev/null || exit 0
    else
        exit 0
    fi
fi
trap 'rmdir "$BASE/.watcher.lock" 2>/dev/null' EXIT

# Wacht tot een bestand niet meer groeit (SMB-kopiëren kan even duren).
stable() {
    local f="$1" a b
    a=$(stat -f '%z:%m' "$f" 2>/dev/null) || return 1
    sleep 2
    b=$(stat -f '%z:%m' "$f" 2>/dev/null) || return 1
    [[ -n "$a" && "$a" == "$b" ]]
}

move_to() {
    local f="$1" dir="$2"
    mkdir -p "$dir"
    mv -f "$f" "$dir/$(basename "$f")" 2>/dev/null || true
}

print_pdf() {
    local f="$1" media="" orient="" opts

    if ! opts=$("$PY" "$HERE/pdfmedia.py" "$f" --ppd "$PPD" 2>>"$LOG"); then
        log "OVERGESLAGEN (formaat) $f"
        move_to "$f" "$FAIL"
        printf 'Kon het paginaformaat niet bepalen of het past niet.\n%s\n' "$opts" \
            >"$FAIL/$(basename "$f").error.txt"
        return 1
    fi

    while IFS='=' read -r k v; do
        case "$k" in
            media) media="$v" ;;
            orientation) orient="$v" ;;
        esac
    done <<<"$opts"

    if [[ -z "$media" ]]; then
        log "OVERGESLAGEN (geen media) $f"
        move_to "$f" "$FAIL"
        return 1
    fi

    local -a args=(
        -d "$QUEUE"
        -o "media=$media"
        -o "lw-density=$DENSITY"
        -o "lw-speed=$SPEED"
        -t "$(basename "$f")"
    )
    [[ -n "$GAP" ]] && args+=(-o "lw-gap=$GAP")
    [[ -n "${LW_PITCH:-}" ]] && args+=(-o "lw-pitch=$LW_PITCH")
    [[ -n "$orient" ]] && args+=(-o "orientation-requested=$orient")

    if [[ "${LW_DRY_RUN:-0}" == "1" ]]; then
        log "DRY-RUN: lp ${args[*]} $f"
        echo "DRY-RUN: lp ${args[*]} $f"
        return 0
    fi

    if lp "${args[@]}" "$f" >>"$LOG" 2>&1; then
        log "PDF  $media  $(basename "$f")"
        move_to "$f" "$DONE/$(date '+%Y-%m-%d')"
        return 0
    fi

    log "MISLUKT (lp) $f"
    move_to "$f" "$FAIL"
    return 1
}

print_csv() {
    local f="$1"
    local size="${LW_CSV_SIZE:-57x32}"
    if [[ "${LW_DRY_RUN:-0}" == "1" ]]; then
        "$PY" "$HERE/csv2labels.py" "$f" --size "$size" --host "$HOST" --dry-run >>"$LOG" 2>&1
        echo "DRY-RUN: csv2labels $f"
        return 0
    fi
    if "$PY" "$HERE/csv2labels.py" "$f" --size "$size" --host "$HOST" >>"$LOG" 2>&1; then
        log "CSV  $(basename "$f")"
        move_to "$f" "$DONE/$(date '+%Y-%m-%d')"
        return 0
    fi
    log "MISLUKT (csv) $f"
    move_to "$f" "$FAIL"
    return 1
}

shopt -s nullglob nocasematch
for f in "$INBOX"/*; do
    base="$(basename "$f")"
    case "$base" in
        .*|~$*|*.part|*.tmp|*.error.txt) continue ;;
    esac
    [[ -f "$f" ]] || continue
    [[ -s "$f" ]] || continue
    stable "$f" || continue

    case "$base" in
        *.pdf) print_pdf "$f" ;;
        *.csv) print_csv "$f" ;;
        *)     log "ONBEKEND type genegeerd: $base" ;;
    esac
done
