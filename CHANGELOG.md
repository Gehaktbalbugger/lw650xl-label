# Changelog

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
