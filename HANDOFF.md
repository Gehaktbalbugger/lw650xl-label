# Handoff — verder werken aan deze printer

Sessie van 9 november 2026. Alles staat op GitHub, er is niets open staan in
de werkomgeving. Kennis en meetwaarden staan in [`KNOWLEDGE.md`](KNOWLEDGE.md);
hier staat alleen **waar we zijn en wat de volgende stap is**.

## Status

| | |
|---|---|
| repo | https://github.com/Gehaktbalbugger/lw650xl-label (privé) |
| releases | v1.0 (AM11354), v1.1 (AM99012), v1.2 (`./measure`), **v1.3 Latest** (S0929120) |
| laatste commit | `b135fe2` "Docs: sense, gapoff and the SIZE+GAP feed rule…" |
| iMac | filter + PPD geïnstalleerd en identiek aan de repo (`/usr/libexec/cups/filter/lw650xl.py`, `/etc/cups/ppd/LW650XL_Labels.ppd`), 12 maten in de PPD |
| tests | `python3 test_filter.py` (40 checks), `test_measure.py` (20), `test_label.py` — alle OK |
| MacBook | nog **niet** bijgewerkt: `cd ~/label-printer && git pull && sudo ./install.sh` |
| `gh` CLI | staat in `~/.local/bin` (niet in PATH): `export PATH="$HOME/.local/bin:$PATH"` |
| gereedschap | `brew` is op deze Mac kapot (mankende schrijfrechten op `/usr/local/share/man/man8`) — download rechtstreeks |

Drie rollen werken: AM11354 (57×32), AM99012 (36×89 staand) en S0929120
(26×25). De twee eerste zijn door de gebruiker afgetekend als "goed".

## Wat de gebruiker nog niet goed vindt

**De vierkante rol.** Het printbare vierkant is 23,03 × 23,03 mm in een
etiket van 26 × 25 mm: hij is kleiner dan het etiket en het vierkant-in-een
vierkant ziet eruit alsof er ruimte verspild wordt. Uitspraak van de
gebruiker: *"goed genoeg voor nu"*.

Oorzaak (zie KNOWLEDGE §4.4): de inkt begint altijd op x=0 en het etiket
steekt 1,5 mm voorbij die grens uit. Links is dus altijd 1,5 mm wit; om dat
te wegnemen moet de kop verder links kunnen beginnen.

### Sporen om morgen op te pakken, in volgorde van hoop

1. **`SHIFT`** — de firmware accepteerde `SHIFT 0` (geen `Cmd error`), maar we
   hebben nooit geprobeerd wat het doet. Waardeer: verzet het de start van de
   kop in dots? Test zonder veel etiketten te verbruiken:
   `printf '\r\nSHIFT 18\r\n' | nc -w2 172.16.1.20 9100` en daarna één
   vierkant printen; als de linkerrand minder wit wordt, is dit de knob om de
   dode zone te recoveren. Probeer ook `SHIFT -18` en `SHIFT 400`.
2. **Mechanisch**: de rol ligt tegen de linkergeleider. Als daar 1,5 mm
   ruimte bij gezet kan worden (dikker ringetje, stukje liner als spacer),
   schuift het hele etiket naar het midden van de kop en win je dezelfde
   1,5 mm terug — zonder firmware en voor alle rollen van dit formaat.
3. **Niet-centreren**: `right` op 0 zetten (`-o lw-right=0` of in de PPD) geeft
   24,5 × 25 mm aan inkt met 1,5 mm wit links en geen wit rechts. Als de
   gebruiker "maximaal" mooier vindt dan "gecentreerd", is dit één getal.
4. **Label-rotatie heroverwegen**: hij print nu `rotate=270` (zijwaarts, zoals
   Labellife). `rotate=0` is ook mogelijk; de meetwaarden blijven dan in dezelfde
   richting als de PPD-maten, wat makkelijker redeneren is.

## Nog te doen / nog te vragen

- MacBook bijwerken (commando hierboven) en daar één etiket per rol printen.
- Verdere formaten: de PPD bevat 9 maten die **nooit op een echte rol gemeten
  zijn** (104x159, 102x59, 101x54, 89x36, 89x28, 54x25, 50x12, 57x57, 62x100).
  Ze hebben geen `lw-media`-regel, dus hun pitch is "hoogte + 3 mm" en hun
  zijdelingse marge is de default. Zodra zo'n rol echt geladen wordt: meten met
  `./measure`, dan `add-size.sh` met de gemeten waarden, dan `install.sh`.
- Regression: de marges van de drie known-good rollen staan nu alleen in
  KNOWLEDGE.md. Een tabeltest die per rol de inktbbox uit de gegenereerde TSPL
  haalt en de verwachte marges vergelijkt, vangt drift in `print_window`
  direct — nu moet daarvoor een handmatige print.
- `./measure` kan de **steek** niet uit het kruis halen; die is nog liniaal-
  werk. Idee: `PRINT 20,1` met een leeg bitmap, dan de 20 gevoede etiketten
  meten (totale lengte / 20) en dat getal in `solve` als `--pitch` in te
  vullen. Moet nog gebouwd worden.

## Werken met deze repo

```bash
cd ~/Documents/Standaardproject/label-printer    # of op de MacBook: ~/label-printer
git pull
python3 test_filter.py && python3 test_measure.py && python3 test_label.py

# rol meten (print niet onnodig: --preview of --dry-run)
./measure 26 25 --name LW_26x25 --step 5 --preview /tmp/x.png
./measure 26 25 --name LW_26x25 --step 5
./measure solve --N -8 --Z 17 --W -13 --O 13 --pitch 34 --gap 3

# rol vastleggen en installeren (root; bron kopieeren naar /Users/Shared eerst)
./add-size.sh LW_26x25 "Vierkant multipurpose 26x25 mm" 26 25 \
    --pitch 34 --gap 3 --left 1.5 --right 1.45 --top 0 --voffset 5.1 --bottom 1.95 --rotate 270
rsync -a --exclude .git --exclude .DS_Store ./ /Users/Shared/Labelprinter/setup/
sudo /Users/Shared/Labelprinter/setup/install.sh

# printen voor controle
lp -d LW650XL_Labels -o media=LW_26x25 /tmp/label.pdf
./label "test" --size 26x25                      # CLI/Excel-route, eigen pad
```

Controleer na iedere installatie of de machine echt dezelfde bestanden draait
als de repo (dit was deze sessie twee keer niet zo, beide keren door een
vergeten `rsync`):

```bash
md5 -q cups/lw650xl.py            /usr/libexec/cups/filter/lw650xl.py
md5 -q cups/lw650xl-labels.ppd    /etc/cups/ppd/LW650XL_Labels.ppd
grep -n "lw-media" /etc/cups/ppd/LW650XL_Labels.ppd
lpoptions -p LW650XL_Labels -l | head -2          # maten + default
```

CUPS kopieert het PPD letterlijk, dus de `*% lw-media`-regels moeten daar
ook staan; ontbreken ze, dan is de bron-PPD of de kopieer-stap verkeerd.

Twee valkuilen die deze sessie tijd kostten (volledige lijst: KNOWLEDGE §8):

- `install.sh`/`setup.sh` moeten vanuit `/Users/Shared/Labelprinter/setup`
  draaien; root kan `~/Documents` niet lezen.
- Na elke PPD-wijziging: `rsync` **én** `install.sh`. De queue en de filter
  lezen `/etc/cups/ppd/LW650XL_Labels.ppd`, niet de repo.

## Vastzetten als een versie

```bash
export PATH="$HOME/.local/bin:$PATH"
git add -A && git commit -F <bericht>
git tag -a v1.4 -m "<korte samenvatting>" && git push origin main v1.4
gh release create v1.4 --title "…" --notes-file <(sed -n '/## 1.4/,/## 1.3/p' CHANGELOG.md | sed '$d')
```

Houd `CHANGELOG.md` bij: per versie de meetwaarden en de reden ervan, want die
getallen zijn anders onherleidbaar uit de code.

## Vraaggesteld aan de gebruiker (nog onbeantwoord)

- Of de vijf vierkante testetiketten exact same lagen (de driver gaf bij elke
  beurt `DOING → DONE`, visueel beoordeeld nog niet bevestigd).
- Of `SHIFT`/afstandsdopje geprobeerd mag worden, of dat het zo "goed genoeg"
  blijft en we door naar volgende formaten.
