# Changelog

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
