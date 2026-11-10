# Handoff — verder werken aan deze printer

Sessie van 9 november 2026. Alles staat op GitHub, er is niets open staan in
de werkomgeving. Kennis en meetwaarden staan in [`KNOWLEDGE.md`](KNOWLEDGE.md);
hier staat alleen **waar we zijn en wat de volgende stap is**.

## Status

| | |
|---|---|
| repo | https://github.com/Gehaktbalbugger/lw650xl-label (privé) |
| releases | v1.0 (AM11354), v1.1 (AM99012), v1.2 (`./measure`), **v1.3 Latest** (S0929120) |
| laatste commit | `1630e35` (kennis + handoff), daarna de vierkante rol gecentreerd |
| rollen | AM11354, AM99012 en **S0929120: 21,51 mm vierkant, 2 mm wit rondom**, gebruiker akkoord |
| tag | **geen nieuwe tag** — v1.3 blijft Latest, in overleg pas later vastzetten |
| iMac | filter + PPD geïnstalleerd en identiek aan de repo (`/usr/libexec/cups/filter/lw650xl.py`, `/etc/cups/ppd/LW650XL_Labels.ppd`), 12 maten in de PPD |
| tests | `python3 test_filter.py` (40 checks), `test_measure.py` (20), `test_label.py` — alle OK |
| MacBook | nog **niet** bijgewerkt: `cd ~/label-printer && git pull && sudo ./install.sh` |
| `gh` CLI | staat in `~/.local/bin` (niet in PATH): `export PATH="$HOME/.local/bin:$PATH"` |
| gereedschap | `brew` is op deze Mac kapot (mankende schrijfrechten op `/usr/local/share/man/man8`) — download rechtstreeks |

Drie rollen werken en zijn door de gebruiker afgetekend: AM11354 (57×32),
AM99012 (36×89 staand) en S0929120.

## De vierkante rol: stand van zaken

Centreren is klaar: **21,51 × 21,51 mm met 2 mm wit rondom**. Het etiket bleek
bij nadere meting **25,5 × 25,5 mm** (1 inch), niet 26 × 25 zoals de verpakking
en ons eerste advies suggereerden; de bereikbare strook is 23,5 × 25,5 mm want
2 mm valt links buiten x=0.

Wit gemeten door de gebruiker: links 2,00 / rechts 1,99 / boven 2,03 / onder
1,96 mm. Geometrie in de PPD: `left=1.5 right=3.0 top=1.9 voffset=4.5
bottom=3.5 rotate=270 rows=356 pitch=33.97 gap=3`.

Het vierkant vult 84% van de bereikbare breedte. Meer winnen kan alleen door
die dode zone kleiner te maken (punten 1 en 2) of door het vierkant op te
geven en de volle strook van 23,5 mm te gebruiken met scheef wit.

### Sporen om morgen op te pakken, in volgorde van hoop

1. **`SHIFT`** — de firmware accepteerde `SHIFT 0` (geen `Cmd error`), maar we
   hebben nooit geprobeerd wat het doet. Vraag: verzet het de start van de
   kop in dots? Test zonder veel etiketten te verbruiken:
   `printf '\r\nSHIFT 18\r\n' | nc -w2 172.16.1.20 9100` en daarna één
   vierkant printen; als de linkerrand minder wit wordt, is dit de knob om de
   dode zone terug te winnen. Probeer ook `SHIFT -18` en `SHIFT 400`.
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

## Les van deze sessie: zo meet je, en zo niet

Een genummerde schaal aflezen **werkt niet** op deze rol: bij `rotate=270`
wijzen N/Z/W/O de verkeerde kant op, en de getalletjes die buiten het etiket vallen
(op de liner naast het kader) zijn onleesbaar. Drie afdrukken meten hielp niet.
Eén vel met een kader en één letter per hoek — **T, B, L, R** — en de vraag
"hoeveel wit tussen kader en rand per hoek" loste het in twee afdrukken op.

Volgende rol dus meteen met het T/B/L/R-kader meten; dat hoort in `./measure`
te komen als `--markers` in plaats van het kruis. Vraag dat als eerste na het
pullen van deze sessie.

## Nog open bij de start van de volgende sessie

- `SHIFT` accepteert de firmware (`SHIFT 0` gaf geen `Cmd error`) maar is nooit
  getest. Verzet het de kopstart zijdelings, dan win je ~2 mm.
- Afstandsdopje rechts van de rol als mechanisch alternatief.
- De T/B/L/R-markerstand in `./measure` bouwen, met de les erbij: alleen
  letters op het vel, geen woorden in overleg (zie KNOWLEDGE §4A).
- **Bevestigd en gecorrigeerd**: de uitvaartkant is de **kleinste canvas-y**
  (eerst mijn +y genoteerd, dat was een mislezing van een woordantwoord; het
  pijlvel wees het omgekeerde aan en dat werd door de gebruiker bevestigd).
- **Open**: TOP/BOTTOM op het meetvel staan langs canvas-x, maar worden door
  de gebruiker langs een andere as gelezen. Volgende vel: letters in de vier
  hoeken, en posities alleen nog als canvas-getal of hoekletter benoemen.
- Zet dit meetvel (kader + TOP/BOTTOM + FEED + etiketcirkel) om in een
  vast commando, bij voorbeeld `./measure --markers`, zodat een nieuwe rol in
  één afdruk is uit te meten zonder woorden te vertalen.
- **Open**: de vierkante rol is nog NIET geïnstalleerd. In de driver staat de
  2-mm-versie (`left=1.5 right=3.0 voffset=4.5 bottom=3.5`). De grotere
  rechthoek `right=0.95 bottom=0 voffset=2.5` is alleen met per-taak-opties
  geprobeerd; vastzetten met `./test-print.sh --commit` (vraagt wachtwoord).
- **Zijdeffect van dezelfde meting**: het etiket is 25,5 mm hoog in de
  feed-richting, maar de PPD-snaam `LW_26x25` geeft 25 mm, dus er blijft
  0,5 mm ongebruikt. `w=`/`h=`-overschrijving in `lw-media` is de nette fix.
- Negen PPD-maten zijn nog nooit op een echte rol gemeten.

