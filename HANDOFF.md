# Handoff — verder werken aan deze printer

Sessies van 9 t/m 12 november 2026. Alles staat op GitHub; er is niets open in de
werkomgeving. Kennis en meetwaarden staan in [`KNOWLEDGE.md`](KNOWLEDGE.md); hier staat
alleen **waar we zijn en wat de volgende stap is**.

## Status

| | |
|---|---|
| repo | https://github.com/Gehaktbalbugger/lw650xl-label — **public** |
| releases | **t/m v1.7** (Latest): v1.0 AM11354, v1.1 AM99012, v1.2 `./measure`, v1.3 S0929120, v1.4/v1.5 vierkant, v1.6 AM11353 2-up geijkt, v1.7 `./measure --markers` |
| laatste commit | deze handoff op `0cadb4a` (KAPOT + status), daarna alleen doc-correcties |
| rollen | **5 geïnstalleerd**: AM11354 (57×32), AM99012 (36×89 staand), S0929120 (vierkant, 2 mm rondom), AM11353 (blok 2-up, geijkt), **S0904980 (104×159 verzendetiket, max inkt)** |
| afgetekend | **AM99012, AM11354, AM11353 2-up, S0904980** door de gebruiker (12 nov); vierkante rol geïnstalleerd op 2 mm rondom |
| iMac | filter + PPD geïnstalleerd en identiek aan de repo (`/usr/libexec/cups/filter/lw650xl.py`, `/etc/cups/ppd/LW650XL_Labels.ppd`) |
| tests | `python3 test_filter.py`, `test_measure.py`, `test_label.py` — alle OK |
| MacBook | nog **niet** bijgewerkt: `cd ~/label-printer && git pull && sudo ./install.sh` |
| `gh` CLI | staat in `~/.local/bin` (niet in PATH): `export PATH="$HOME/.local/bin:$PATH"` |
| gereedschap | `brew` is op deze Mac kapot (mankende schrijfrechten op `/usr/local/share/man/man8`) — download rechtstreeks |

Vier rollen in de driver: AM99012 en AM11354 zijn afgetekend, S0929120 staat
geïnstalleerd met 2 mm rondom, AM11353 is 2-up geijkt en goedgekeurd (v1.6).

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
- Verdere formaten: de PPD bevat 8 maten die **nooit op een echte rol gemeten
  zijn** (102x59, 101x54, 89x36, 89x28, 54x25, 50x12, 57x57, 62x100).
  Ze hebben geen `lw-media`-regel, dus hun pitch is "hoogte + 3 mm" en hun
  zijdelingse marge is de default. Zodra zo'n rol echt geladen wordt: meten met
  `./measure <b> <h> --markers --pitch <vendor> --gap <gap>`, dan `add-size.sh`
  met de gemeten waarden, dan `install.sh`.
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

## Morgen in een nieuwe context (eerste taak: KAPOT)

1. Repo klonen of pullen (github.com/Gehaktbalbugger/lw650xl-label, public),
   dan `HANDOFF.md` openen. De --two/2-up-tak is **opgelost, geijkt,
   geïnstalleerd en goedgekeurd in v1.6** — er is geen fysieke test meer
   tegoed behalve de MacBook (punt 3).
2. **Klaar (nov 12):** het T/B/L/R-marker-vel staat in `./measure` als
   `--markers` (+ `solve --T --B --L --R`), met de §4A-rotatiemapping in
   `MARKER_EDGES` en 15 checks in `test_measure.py`. Eerste nieuwe rol:
   `./measure <b> <h> --markers [--rotate 270]`; de genummerde schaal blijft
   achterwege — één kader op het oude printvlak plus vier letters. De 90-map
   staat er als spiegelbeeld van 270 maar is nog **ongeijkt**; een gedraaide
   rol voor het eerst met `--markers` meten = fysieke bevestiging van de map.
   **Fysiek getest op de AM11353** (vel van 12 nov, 15:5x): L-lijn afwezig
   zoals voorspeld (kader op x −2,03 = onbereikbaar, de negatieve-knip werkt),
   R en B op 0 = ijk bevestigd; solve reproduceerde `xoffset −2,0` en maat
   25,0. `--gap`-afleiding is daarna uit de markers-solve gehaald (was fout:
   8,5 i.p.v. 3 — er zit extra liner om de kloof).
   **Tangent-test gesloten (12 nov, 16:0x)**: testlijnen op 3,99 en 29,85 mm
   vielen allebei BUITEN het etiket, de ankerlijnen op 4,49/29,46 erop →
   label ≈ 4,0..29,5+ (hoogte ~25,0-25,3), de geijkte band 4,49..29,46 sluit
   rondom in. De T=0,5 van het marker-vel was leesruis; `top` blijft 4,5 en
   er is geen `h=25,5`-winst. Les voor de volgende: bij een aflezing van
   0,5 mm naast een 0,25-mm-lijn eerst de tangent printen, dan de PPD aanraken.
3. MacBook bijwerken: `cd ~/label-printer && git pull && sudo ./install.sh`,
   daarna daar één etiket per rol printen.
4. Dan pas de rest: "Sporen om morgen op te pakken", "Nog te doen" en de
   punten onder "Wat er nu op de iMac draait".

We stoppen hier. Continuïteit voor de volgende context: releases t/m
**v1.5** staan op GitHub, de repo is **public**, en alles wat gemeten is
staat vast in KNOWLEDGE.md en CHANGELOG.md — er hoeft niets meer opgetoond
te worden. Er is deze sessie niets kapotgemaakt: de iMac draait de state
hierboven, de MacBook wacht op `git pull && sudo ./install.sh`.

## OPGELOST: label --two prints bijna niets (v1.6; fysiek geijkt en goedgekeurd)

Fysiek velletje bij de vierkante rol leverde "a few pixels" in plaats van
twee etiketten. De fout zat in de **--two-compositie van de CLI**, niet in
de rol en niet in de filter.

**De fout** (bewezen 10 nov): de compose was in **canvas-maten** —
`Image.new("L", (box[3] * 2, box[2]))` = **590 × 287 dots** in plaats van de
**295 × 288 ontwerp-dots** — en liet de rotatie vallen. De twee helften
plakte hij op (0,0) en (295,0), dus 0..590 dots over de kop; het beeld viel
daardoor vooral buiten het etiket — op het vel: "a few pixels". Derde bug op
dezelfde tak: de enkele-label-rotatie-crash (`args.box` werd een 3-tuple,
`render_label` wilde er 4 uit pakken) — `--rotate 270` crashte dus altijd al.

**De oplossing** (omgezet, precies zoals voorgeschreven): composeer in het
ONTWERP-frame, twee halve pagina's boven elkaar, en pas daarna de
enke-label-rotatie erop (270°; bovenste helft wordt linkerkolom, onderste de
rechter — zoals csv2labels belooft). In `label` staat nu:

```python
ox, oy, ch, cw = args.box            # venster: (-24, 53, 295, 295) na kalibratie
half = ch // 2                       # halve pagina: 295 × ~144 dots
a2.box = (ox, oy, half, cw)
img = Image.new("1", (cw, ch), 1)    # ontwerp-frame, géén canvas
img.paste(e_boven, (0, 0))           # etiket A (linker kolom na rotatie)
img.paste(e_onder, (0, half))        # etiket B (rechter kolom na rotatie)
img = img.rotate(-rot, expand=True)  # de enkele-label-rotatie, rot=270 voor 2-up
```

**Daarna bleek ook de rolgeometrie anders** (12 nov, drie voedingen): het eerste
gecomposeerde vel landde 10 mm te ver rechts en 5 mm te vroeg — de oude
liner-aanname (7,5..32,5 mm) was door liniaal + Labellife nooit fysiek
bewezen. Kaders van 6 × 10 mm werden gecentreerd met `xoffset=-2,5 top=4,5`;
een loodlijn van 0,25 mm pinpointte de snijrail op **10,5 mm** → definitief
`xoffset=-2`. Negatieve xoffset knipt de onbereikbare 2 mm van baan A weg
(`content_box`/`print_window`/`pack_canvas` zijn daarop aangepast).

**Rooktest gevangen** (`test_label.py`, vanger + bits-controle): canvas
160 B × 354 regels zoals de vendor, inkt binnen 0..271 dots, beide halve
kolommen inkt, snijlijn wit, rijen < 53 en ≥ 348 leeg. Fixjes meegenomen:
`--two`-tekst vervangt nu ook `\n` (csv2labels-documentatie), en de CLI-
vlaggen `--rows/--rotate/--xoffset/--sense/--gapoff` werden door een reset
na argparse altijd genegeerd — die reset is weg; `--media-bottom` en
`--media-right` zijn nu echt doorlussen naar het printvlak.

**Afgetekend**: geïnstalleerd op de iMac (rsync + `install.sh`, md5's
identiek), Anna/Piet-vel goedgekeurd — beide etiketten gecentreerd, tekst
zijwaarts zoals de vendor-app. Eens per rolwissel: de snijlood-lijn van
`diag`-formaat terugprinten als herijking (KNOWLEDGE §AM11353).

## S0904980: verzendetiket gemeten en geregistreerd (12 nov, goedgekeurd)

De rol die Labellife zelf al kon printen — onze taak: de PPD-maat
`LW_104x159` (een van de negen ongemeten) naar fysieke waarheid zetten:

1. **Vendor gevangen met tcpdump**: `SIZE 104 mm,162 mm · GAP 3 mm,0 mm ·
   DENSITY 10 · SPEED 4 · BITMAP 0,0,160,1902,4` — pitch 162 = 159+3 ✓,
   canvas 1901 (vendor 1902). Recept: `tcpdump -i en0 -nn -s0 -w vel.pcap
   -C 8 tcp port 9100` (root; `-i any` doet het niet in Apple's tcpdump),
   daarna `strings vel.pcap | grep -aE 'SIZE|GAP|BITMAP|SPEED|DENSITY'`.
2. **`./measure 104 159 --markers --pitch 162 --gap 3`** → vier aflezingen →
   `solve`: gemeten **104,2 × 159,9 mm** (binnen 0,2 van de nominal!),
   labellijnen x −2,0..102,2 (dezelfde 2 mm-dode zone links als de vierkante
   rol), y 0,08..159,95 (etiket begint vrijwel op de bitmap-oorsprong).
3. **Geregistreerd op max inkt**: `left=0 right=2 top=0.6 bottom=0` — inkt
   tot de randen, links alleen de onvermijdelijke dode zone.
4. **Frame-proef via de CUPS-route** (eerste keer op deze rol!): kader op de
   printbare rand, tekst, cirkel Ø 51 mm. De bovenkaderlijn viel af bij
   `top=0.08` (marge 0 naast een lijn van 0,5 mm) → veiligheidmarge
   `top=0.6` → alles binnen. Les: marge 0 maak je nooit bij een eerste rol;
   0,5–0,6 is de ondergrens.

## Wat er nu op de iMac draait (v1.7, geïnstalleerd en afgetekend)

- **driver**: 5 rollen geïnstalleerd — AM11354, AM99012, S0929120 (2 mm rondom),
  AM11353 als blok met de **gekalibreerde** regel
  `LW_25x25 pitch=34 gap=3 rows=354 xoffset=-2 top=4.5` en **S0904980** met
  `LW_104x159 pitch=162 gap=3 left=0 right=2 top=0.6 bottom=0` (max inkt;
  filter en PPD geïnstalleerd via `install.sh`, md5's identiek aan de repo).
- AM99012, AM11354, de AM11353 2-up en S0904980: door de gebruiker afgetekend.
- releases t/m **v1.7**; repo **public**.

## Nog open bij de start van de volgende sessie

- AM11353: de linker **2,0 mm van baan A** valt links van kop-x=0 en wordt
  weggeknippen. `SHIFT` (punt hieronder) zou die strook misschien kunnen
  terughalen — de kop dan 24 dots later laten beginnen.
- `SHIFT` accepteert de firmware (`SHIFT 0` gaf geen `Cmd error`) maar is nooit
  getest. Verzet het de kopstart zijdelings, dan win je ~2 mm.
- Afstandsdopje rechts van de rol als mechanisch alternatief.
- De T/B/L/R-markerstand in `./measure` bouwen, met de les erbij: alleen
  letters op het vel, geen woorden in overleg (zie KNOWLEDGE §4A).
- **Bevestigd en gecorrigeerd**: de uitvaartkant is de **kleinste canvas-y**
  (eerst mijn +y genoteerd, dat was een mislezing van een woordantwoord; het
  pijlvel wees het omgekeerde aan en dat werd door de gebruiker bevestigd).
- **Opgelost**: de hoekletters P/Q/R/S bepaalden de leesrichting. Links/rechts
  zit op de canvas-y-as, boven/beneden op de canvas-x-as, en een normaal
  getekend ontwerp komt na `rotate=270` rechtop op het etiket (zie KNOWLEDGE
  §4A). Er is dus geen ontwerpdraai nodig in Word/Excel.
- Zet dit meetvel (kader + TOP/BOTTOM + FEED + etiketcirkel) om in een
  vast commando, bij voorbeeld `./measure --markers`, zodat een nieuwe rol in
  één afdruk is uit te meten zonder woorden te vertalen.
- **Geïnstalleerd**: de vierkante rol draait nu de maximale rechthoek
  `left=1.5 right=1.4 top=1.9 voffset=2.5 bottom=0 rows=356 pitch=33.97 gap=3
  rotate=270`. Printbaar vlak 23,03 × 24,98 mm; wit 2,00 mm aan de bovenkant
  (dode zone), 0,47 mm beneden, en langs de y-randen 0,00 / 0,61 mm.
- Restpunt: de uitvaartkant (uw rechts) heeft 0,00 mm reserve. Als die lijn
  ooit net afloopt, verhoog `bottom` met 0,5 mm — niet `voffset`.
- **Zijdeffect van dezelfde meting**: het etiket is 25,5 mm hoog in de
  feed-richting, maar de PPD-snaam `LW_26x25` geeft 25 mm, dus er blijft
  0,5 mm ongebruikt. `w=`/`h=`-overschrijving in `lw-media` is de nette fix.
- Acht PPD-maten zijn nog nooit op een echte rol gemeten (104x159 is gemeten:
  S0904980, 12 nov).
