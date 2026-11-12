# Changelog

## 1.7 — `./measure --markers`: het T/B/L/R-vel als commando (12 nov, geïnstalleerd)

- Nieuwe stand in `./measure`: `--markers` drukt **één vel** met het kader
  precies op de randen van het aangenomen printbare vlak plus één letter per
  kant (T B L R), elk met de kroon naar zijn eigen etiketrand. De letters
  staan in **canvas-coördinaten** en worden met `lw-orient=off` +
  `lw-rotate=0` 1:1 op het venster gezet — dus geen schaalvervorming en
  geen N/Z/W/O-richtingsverdriet bij `rotate=270` (de les van §4A/§10).
- `./measure solve --T <mm> --B <mm> --L <mm> --R <mm>` leest de vier
  witstroken tussen kader en etiketrand; `MARKER_EDGES` mapt ze per rotatie
  terug naar kop-richting/voeding (270: T/B→left/right, L/R→top/bottom;
  de 90-mapping staat er als spiegelbeeld, nog **ongeijkt**). Output:
  gemeten maat, labellijnen in bitmap-mm, centrumcorrectie en de
  `add-size.sh`-opdracht (inclusief `--xoffset` bij een verschoven rol, en de
  reminder voor het snijlood-velletje).
- Filter: `lw-orient=off` zet de auto-oriëntatiedraai uit (nodig voor een
  raster dat al venster-shape in canvas-oriëntatie is). Standaard aan, dus
  geen gedrag verandert voor printen via Word/CLI.
- `test_measure.py`: 15 nieuwe checks — state, frame==venster, rastermaat
  1:1, rot0- én rot270-doorrekenen, ontbrekende letters = fout.

## 1.6 — AM11353 2-up gefixt én fysiek gekalibreerd (12 november, goedgekeurd)

- `label --two` composeert nu in het **ONTWERP-frame** (295 × 287/288 dots),
  als twee halve pagina's van 295 × ~144 dots boven elkaar, en daarna pas
  **de enkele-label-rotatie** (270°) erop: bovenste helft → linker kolom,
  onderste → rechter. De oude opbouw was canvas-maten (590 × 287) zonder
  rotatie; het beeld viel grotendeels buiten het blok (7,5..32,5 mm) — op
  het vel "a few pixels". 2-up Forceert 270° als de PPD geen rotatie geeft,
  want twee halve banen van 12,5 mm naast elkaar staan altijd op z'n kant.
- **Bug in de rotatie-tak** meegenomen: `args.box` werd er een 3-tuple van
  gemaakt terwijl `render_label` er 4 waarden uit haalt — dus elke
  `rotate=270`-print via de CLI crashte ("niet enough values to unpack").
  Nu een proper swap van h en w; het geroteerde beeld valt precies in het
  meetvenster (getest op de vierkante rol: canvas 356, inkt binnen x/y-venster).
- Rooktest in `test_label.py`: de vanger (TCP-verfanger) pakt de wire-bytes
  en de bits-controle verifieert voor AM11353: BITMAP 160 B × 354 regels
  (zoals de vendor-capture), inkt binnen het bereik 0..271 dots, beide halve
  kolommen dragen inkt, de snijlijn blijft wit en de witranden vóór rij 53
  en ná rij 348 (top=4,5 mm) zijn leeg.
- Twee CLI-draadjes gerepareerd: `--rows/--rotate/--xoffset/--sense/--gapoff`
  werden na argparse onvoorwaardelijk op `None` gezet, waardoor PPD-hints
  gebruikervlaggen altijd overschreven; en `--media-bottom`/`--media-right`
  deden niets — ze zijn nu doorlussen naar het printvlak. `--two`-tekst vervangt
  nu ook `\n` in regeleinden, zoals csv2labels documenteert.
- **Fysieke kalibratie van de rol** (3 voedingen, 12 nov): het oude liner-verhaal
  (x 6..36, blok 7,5..32,5, rail 20 mm — 1-mm-liniaal + Labellife) klopte niet;
  eerste velletje landde 10 mm te rechts en 5 mm te vroeg. Twee kaders van
  6 × 10 mm gecentreerd na xoffset −2,5/top 4,5; een loodlijn van 0,25 mm
  pinpointte de rail op **x = 10,5 mm** → definitief `xoffset=-2 top=4.5`.
  Zie KNOWLEDGE §AM11353; les: één snijlijn-lood kalibreert een 2-up-rol.
- **Negatieve xoffset** is nu een legaal concept: `content_box` (CLI) en
  `print_window` (filter) knippen de onbereikbare strip links van kop-x=0
  weg; `pack_canvas` negeert pixels met `px < 0` (was negatief indexeren!).
  `test_filter` 6a en de rooktest draaien op de gemeten getallen.
- Geïnstalleerd op de iMac (`install.sh`, md5 filter/PPD identiek aan de
  repo); `./label --two` zonder vlaggen composeert vanaf de geïnstalleerde
  PPD-rules 295 × 295. Vel goedgekeurd door de gebruiker.

## 1.5 — vierkante rol geïnstalleerd op maximale breedte; coördinaten definitief

- De S0929120-rol is gemeten en **geïnstalleerd** op de maximale rechthoek:
  `pitch=33.97 gap=3 rows=356 left=1.5 right=1.4 top=1.9 voffset=2.5 bottom=0
  rotate=270` → printbaar vlak 23,03 × 24,98 mm, wit 2,00 mm aan de bovenkant
  (onbereikbaar), 0,47 mm beneden, 0,00 / 0,61 mm langs de voeding.
- Eerste R/S-kaderlijn liep van het etiket af; `right` 0,95 → **1,4 mm** lost
  dat op zonder meetbaar verlies.
- **Coördinaten opgelost met een hoekvelletje** (P/Q/R/S): een gebruiker ziet
  links/rechts langs de **canvas-y-as** (de voedingsrichting), boven/beneden
  langs de canvas-x-as. Een normaal getekend ontwerp komt na `rotate=270`
  rechtop op het etiket: er is géén ontwerpdraai nodig in Word of Excel.
- De uitvaartkant is de **kleinste canvas-y**. Een eerdere, verkeerd
  geïnterpreteerde "+y-bevestiging" is expliciet ingetrokken in de documentatie.
- Nieuw: **`test-print.sh`** — dezelfde proefprinten met per-taak-opties
  (`--status`, `--flush`, `--final`) en `--commit` om ze daarna in de PPD te
  zetten en te installeren. Zo hoef je voor een test geen admin-rechten.
- Twee valkuilen vastgelegd in `KNOWLEDGE.md`: een canvas-pagina door
  `convert()` sturen schaalt het hele meetbeeld terug (vervormd vel), en
  `26 × 11,811` dots in een ontwerp van 295 dots valt van de rand af
  (onleesbare pijl). Diagnostiek benoemt posities alleen nog als
  canvas-getal of hoekletter.
- `./measure` kreeg `--rows`/`--rotate`; `KNOWLEDGE.md` §4A bevat nu de gemeten
  mapping, `HANDOFF.md` de geïnstalleerde toestand en de restpunten.

## 1.4 — vierkante rol gecentreerd, meetgereedschap uitgebreid, kennis gedocumenteerd

- De vierkante rol is gemeten en gecentreerd: etiket is **25,5 × 25,5 mm**
  (1 inch), niet 26 × 25 zoals de verpakting en ons eerste advies zeiden.
  2 mm links van x=0 is onbereikbaar, dus het grootste gecentreerde vierkant
  is 21,51 mm met 2 mm wit rondom.
- `lw-media` kreeg vier velden erbij: `rows` (bitmap-hoogte in dots; Labellife
  stuurt 356 voor deze rol), `rotate` (90/270: het ontwerp zijwaarts, zoals de
  vendor-app doet), `sense` (`gap`/`bline`) en `gapoff` (mm liner tussen
  etiketeinde en de kloof). `add-size.sh` en de `label`-CLI volgen dat.
- De PPD-parser bewaart nu ook niet-numerieke waarden (`sense=bline`); tot die
  tijd werd er stilletjes `GAP` verstuurd.
- `./measure`: `--rows`, `--rotate` en een `ladder`-stand (genummerde banden
  over één voeding) voor rollen waarvan de startpositie onbekend is.
- Regel die alles verklaart en nu gedocumenteerd staat: **`SIZE-hoogte + GAP`
  is de afstand per etiket**. Labellife stuurt `SIZE 25 mm,33,97 mm` +
  `GAP 3 mm` = 36,97 mm, precies de gemeten steek; overleg van ons kruis op
  het hunne toont dezelfde plaats.
- Test die de werkboom beschadigde (`git checkout` op de PPD) draait nu op een
  kopie via `LW_PPD`, en een expliciete `--top 0` blijft behouden: nul is een
  meting, geen ontbrekende optie.
- Nieuwe documenten: **`KNOWLEDGE.md`** (alles wat aan de printer gemeten is,
  inclusief de Labellife-capture en de commando-matrix) en **`HANDOFF.md`**
  (stand van zaken, open punten, de les dat hoekletters T/B/L/R beter werken
  dan een genummerde schaal bij een gedraaide rol).

## 1.3 — S0929120 (25 × 25 mm vierkant) en twee nieuwe rolknoppen

- Nieuw formaat `LW_26x25`: de Dymo S0929120 / 30332-role is gemeten
  26 × 25 mm (niet 25 × 25). De rollijn is: 25 mm etiket, 4 mm liner,
  3 mm gaatje, 5 mm liner = 37 mm steek.
  Een 25 × 25 Word-pagina wordt er automatisch naartoe gemapt.
- De roldefinities kregen twee velden erbij:
  `rows` (bitmaphoogte in dots; standaard `pitch - 12`, zoals de
  vendor-app stuurt) en `rotate` (90 / 270: het ontwerp zijwaarts
  printen). `add-size.sh` kreeg `--rows` en `--rotate`.
- Labellife bleek voor deze rol `SIZE 25 mm,33.97 mm`, `GAP 3 mm` en
  356 bitmapproeren te sturen; met die waarden en 0,6 mm wit rondom
  staat het beeld gecentreerd. Eerdere aannames (steek 38 mm,
  tussenruimte 13 mm) waren de reden dat de printer elke beurt elders
  begon: die kloof bestaat niet, dus de gap-zoeker sprong rond.
- Inkt kan niet linkser dan x=0; bij een smallere rol is dat een
  fysieke dode zone. Centreren doe je door rechts evenveel in te
  leveren als links onbereikbaar is. Het grootste gecentreerde vierkant
  op deze rol is daarmee 23,03 × 23,03 mm (1,5 mm links/rechts,
  1,0 mm boven/onder): `left=1.5 right=1.45 voffset=5.1 bottom=1.95`.
- Belangrijkste inzicht: voor deze printer telt **SIZE-hoogte + GAP =
  de echte steek**. Met `SIZE 26 mm,34 mm` + `GAP 3 mm` (37 mm) vielen
  vijf losse beurten exact gelijk; zolang de som klopte maakte het de
  sensor niet uit dat de gaatjes buiten het sensorbereik vallen.
- Bug in `./measure`: de kruis-print stuurde `SIZE <w>,<h>` in plaats
  van de meegegeven `--pitch`/`--gap`, waardoor de printer te weinig
  voerde en het beeld half op de liner belandde. Beide meetmodi sturen
  nu exact de berekende geometrie.
- `./measure` kreeg een `ladder`-stand (genummerde banden over één
  voeding) om te zien waar een rol begint, en `--step` voor leesbare
  schalen op kleine etiketten.
- `test_filter.py` (40 checks) en `test_measure.py` (20 checks) dekken
  `rows`, `rotate`, de inverse rotatie en de pitch/gap-doorvoer.

## 1.2 — ./measure, een nieuwe rol in twee opdrachten

- `./measure <breedte> <hoogte>` drukt één etiket met `0,0` in het midden van
  het verwachte printvlak, 1-mm streepjes en N/Z/W/O op de verwachte randen,
  als mode-0 TSPL direct naar poort 9100 — zonder driver en zonder root.
- `./measure solve --N .. --Z .. --W .. --O ..` rekent de vier aflezingen om
  naar `left`/`right`/`top`/`bottom` en drukt de passende
  `add-size.sh`-opdracht af. De gebruikte middenpositie blijft in een
  statusbestand achter, dus de aflezingen gaan niet meer verloren.
- De berekening komt uit `cups/lw650xl.py` zelf: meten en printen rekenen
  identiek. `--preview` en `--dry-run` tonen zonder te printen.
- `test_measure.py` dekt de print/solve-roundtrip.

## 1.1 — AM99012 / Dymo S0722400 (36 × 89 mm, staand)

- Nieuw formaat `LW_36x89`: deze rol staat 90° anders op de printer dan de
  AM11354 — 36 mm over de kop, 89 mm in de voederrichting, steek 93 mm.
- Rolpositionering is nu per maat instelbaar in de PPD: `left`, `right`,
  `top` and `bottom` naast `pitch`, `gap` en `voffset`
  (`*% lw-media LW_36x89 pitch=93 gap=4 left=3 right=3 top=-0.5 bottom=1`).
- `left`/`right`/`top`/`bottom` zijn ook als CUPS-optie (`-o lw-right=3`) en
  als CLI-optie (`--media-right 3`, `--media-top`, `--media-bottom`) te zetten.
- Het model klopt nu met de werkelijkheid: een negatieve `top` (etiket begint
  boven het bereik van de kop) wordt afgekapt op rij 0, en inkt kan niet
  linkser dan x=0 — dus is de rechterkant van het printsel met evenveel
  ingeleverd als de onbereikbare linkerrand. Gemeten marges: 3,34 / 3,28 mm
  (W/O) en 0,84 / 0,87 mm (N/Z).
- `add-size.sh` kreeg `--left`, `--right`, `--top` en `--bottom`; handleiding
  (NL) en README beschrijven hoe je een rol met een meet-etiket afleest.
- `test_filter.py`: 34 checks, inclusief de AM99012-geometrie en de
  gelijke marges links/rechts.

## 1.0 — eerste werkende versie

- TSPL `BITMAP` mode 0, bit 1 = wit, 1-op-1 op de 1280-dots kop.
- Meetbaar gecentreerde geometrie voor de AM11354 (57 × 32 mm, steek 38,6 mm,
  printbaar vlak x 0–640, `voffset` 0,34 mm).
- CUPS-filter die de rasters van cgpdftoraster echt uitleest: header van 1796
  bytes per pagina, syncwoord alleen vóór pagina 1, en meerdere pagina's =
  meerdere etiketten.
- Word-achtige opties worden ongedaan gemaakt: `media=Custom.90.71x161.57`
  + `orientation-requested=4` (etiket komt staand binnen → 90° rechtsom
  terugdraaien) en de PPD-keuze via `com.apple.print.PageToPaperMappingMediaName`.
- Gedeelde SMB-inbox (Labelprinter) met launchd-watcher, Word- en Excel-macro's,
  `label`-CLI, `setup.sh` / `install.sh` / `add-size.sh`, tests.
