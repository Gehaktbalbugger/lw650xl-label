# Wat we weten over de LW650XL PRO

Verzamelde bevindingen van het reverse-engineeren en afstellen van deze
printer. Elk punt is gemeten aan de echte printer, niet uit documentatie —
de fabrieksheet klopt voor deze firmware niet. Zie `HANDOFF.md` om verder te
werken.

## 1. De hardware

- LW650XL PRO is een herdoopte **Aimo 650** (Xiamen Aimo Technology).
- Direct-thermaal, zwart-wit, 300 dpi, **1280 dots kop ≈ 108 mm**.
- Taal: **TSPL** over raw TCP **poort 9100**. USB-beschuiging bestaat ook,
  maar alles hier is via het netwerk geverifieerd.
- 1 dot = 25,4/300 = **0,0847 mm**. Fijnste instelbare stap is dus ~0,085 mm;
  "0,3 mm" bestaat fysiek niet, wel 3 dots = 0,254 mm of 4 dots = 0,339 mm.
- De printer praat terug op dezelfde poort:

  | melding | betekenis |
  |---|---|
  | `SSSGETPRINTING:DOING` → `:DONE` | taak geaccepteerd en afgedrukt |
  | `SSSGETPAPER:NO` | geen papier / sensor vindt geen referentie |
  | `SSSGETCAP:OPEN` / `:CLOSE` | deksel of mediahefboom bewoog |
  | `Cmd error:<token>` | commando (of token) niet begrepen |

## 2. Commando-matrix (gepiept, één commando per verbinding)

| aanvaard | geweigerd |
|---|---|
| `SIZE`, `GAP`, `BLINE`, `REFERENCE`, `OFFSET`, `DIRECTION`, `DENSITY`, `SPEED`, `CLS`, `BITMAP`, `PRINT`, `SET TEAR ON`, `SHIFT`, `SET MEDIA GAP` | `GAPAUTO`, `SET MEDIA MARK`, `SET BACK`, `SET SHIFT`, `VREF`, `PRINTM`, `SSSGETMEDIA:`, `SSSGETDEVINFO:`, `SSSGETSTATUS:` |

Alleen deze lijst is daadwerkelijk gepiept. Commando's die er niet staan
(`CODEPAGE`, `PAUSE`, `FORMFEED`, …) zijn ongetest — ze zijn niet afgewezen,
maar ook niet bevestigd.

Let op bij pelen: de printer antwoordt **asynchroon en één stap later** dan
het commando dat je net stuurde. Eén commando per TCP-verbinding, anders
schuiven de antwoorden weg en lees je `Cmd error:GAP` bij een `SPEED`-regel.

**`SHIFT` is aanvaard maar nooit uitgeprobeerd.** Als het de startpositie van
de kop in dots verzet, is het de enige manier om de onbereikbare linkerrand
van smalle rollen terug te winnen. Zie HANDOFF, punt "open".

## 3. BITMAP-formaat

- **mode 0 = ongecomprimeerd** en dat is wat werkt.
- Syntaxis: `BITMAP x,y,breedte_in_bytes,hoogte,mode,` — het binaire payload
  begint **meteen na de laatste komma**: geen lengteveld, geen CRLF.
- **Bit 1 = wit, bit 0 = geprint punt.** Rijtjes MSB-first, per rij afgerond
  naar bytes. Een 1280-dots bitmap is dus 160 bytes per rij.
- mode 3 (classic LZO) wordt door deze firmware **stilletjes inslikd**: de
  printer meldt DONE maar print niets. mode 4 is de LZO-variant van de vendor
  zelf: 18 blokken van `[4-byte LE lengte][data]`, elk eindigend op `11 00 00`;
  ons `lzo.py` kan het niet decoderen en dat hoeft niet meer.
- De bitmap wordt **1-op-1 op de kop** gelegd: een 57 mm-etiket beslaat het
  linker deel van de 1280 dots, de rest is lege liner.

## 4. Registratie: dit is de kern

1. **De printer verankert de bitmap aan de ONDERKANT.** Een hogere bitmap
   schuift het beeld dus omhoog op het etiket. Wil je een kort etiket, vul de
   bitmap dan op tot de volledige voedinghoogte; anders gaat het beeld misplaatst.
2. **`SIZE`-hoogte + `GAP`-lengte = de afstand per etiket.** Dat is wat de
   printer aanvoert. Klop die som niet, dan zoekt hij een referentie die er
   niet is en begint elke beurt elders. Klop ze wél, dan liggen vijf losse
   beurten exact gelijk — ook al zien de gaatjes of zelfs de kloof de sensor
   sensor gezien worden.
3. De standaardvulling van de bitmap is `pitch_dots - 12` (dat is wat de
   vendor-app op de 57 × 32-rol stuurt: 444 rijen bij 456 dots). Rols die
   dat patroon breken, pinnen hun hoogte met `rows=`.
4. **Inkt kan niet linkser dan x=0.** Een smalle rol die tegen de linkergeleider
   ligt, steelt daardoor mm van het etiket die software nooit kan halen.
   Centreren doe je door rechts evenveel in te leveren als links onbereikbaar
   is (`left` = `right`), niet door te verschuiven.
5. De sensor zit in het **midden van het media-pad** (~54 mm van links). Een
   rol van 26 mm bereikt hem nooit, dus merkinformatie (BLINE) is daar waardeloos;
   `BLINE 12 mm` zette de printer zelfs in een papierfout.

## 4A. Coördinaten: wat op het etiket waar is

Definitief vastgesteld met een vel dat vier hoekletters draeg (P/Q/R/S) en
waarvan de canvas-positie van elke letter bekend was. De gebruiker hield het
etiket zoals hij het wil lezen:

| zijn kijk | letters op het vel | canvas |
|---|---|---|
| linkerboven | P | x 3,64 / y 25,65 mm |
| rechterboven | Q | x 3,64 / y 7,87 mm |
| linkeronder | R | x 19,73 / y 25,65 mm |
| rechteronder | S | x 19,73 / y 7,87 mm |

Dus, met `rotate=270`:

| zijn richting | canvas |
|---|---|
| **boven** (draagt de 2 mm onbereikbaar) | kleine x, x=0 kant |
| **beneden** | grote x (23,5 mm kant) |
| **links** | grote y = achterkant |
| **rechts** | kleine y = **uitvaartkant**, daar wijst de FEED-pijl heen |

Twee conclusies die het waard zijn:

1. Links/rechts zit op de **y-as** (de voedingsrichting), niet op de x-as. Al
   mijn eerdere "pijl wijst naar de B"-interpretaties liepen dlatego stuk.
2. Een ontwerp dat je normaal tekent (linksboven = linksboven) komt na
   `rotate=270` **rechtop** op het etiket te staan: hoek voor hoek identiek.
   Je hoeft je Word- of Python-ontwerp dus niet te draaien; alleen de
   paginamaat moet passen bij het printbare vlak.

Regel voor diagnostics: benoem een positie altijd als canvas-getal of als
letter van het vel, nooit met boven/links/onder.

## 5. Geometrie per rol, alles in de PPD

Eén commentaarregel per rol, door `add-size.sh` geschreven en door zowel de
CUPS-filter (`$PPD`-omgeving, fallback `/etc/cups/ppd/LW650XL_Labels.ppd`) als
de `label`-CLI gelezen. CUPS houdt commentaarregels intact bij installatie
(geverifieerd).

```
*% lw-media <naam> pitch=.. gap=.. [gapoff=..] [left=..] [right=..]
               [top=..] [bottom=..] [voffset=..] [rows=..] [rotate=..] [sense=..]
```

| veld | betekenis |
|---|---|
| `pitch` | wat de printer per etiket aanvoert (SIZE-hoogte), niet de etikethoogte |
| `gap` | lengte van de kloof / het merk / het gaatje |
| `gapoff` | mm blanco liner tussen etiketeinde en die kloof |
| `left` | dode zone: mm etiket links van x=0, onbereikbaar |
| `right` | mm vrij aan de rechterkant; gelijk aan `left` = gecentreerd |
| `top` | mm van bitmap-oorsprong tot de bovenrand van het etiket (mag negatief) |
| `bottom` | mm vrij onderaan; spiegelt een onbereikbare bovenrand |
| `voffset` | schuift de hele print naar beneden (centrering met het oog beoordeeld) |
| `rows` | bitmap-hoogte in dots, overstemmt `pitch - 12` |
| `rotate` | 90 of 270: het ontwerp zijwaarts; het bitmap-loopt alsnog over de kop |
| `sense` | `gap` (default) of `bline` |
| `xoffset` | mm tussen de kopstart (x=0) en de linker rand van de liner; nodig als de rol rechts van de kop begint |

### De drie rollen die nu werken

| rol | maat | rollijn | pitch | geometrie | resultaat |
|---|---|---|---|---|---|
| AM11354 | 57 × 32 mm, liggend | — | 38,6 mm, gap 3 | `voffset=0.34` (4 dots), `left`/`right` default | printbaar 640 × 370 dots, door gebruiker als "in het midden" beoordeeld |
| AM99012 / Dymo S0722400 | 36 × 89 mm, **staand** | — | 93 mm, gap 4 | `left=3 right=3 top=-0.5 bottom=1` | 30 × 88 mm, 3 mm wit rondom |
| S0929120 / Dymo 30332 | **25,5 × 25,5 mm** (1 inch; het etiket is dus noch 26 × 25, noch exact 25 × 25) | 25,5 mm etiket + 4 mm liner + 3 mm gaatje + 5 mm liner | **36,97 mm** = `pitch 33,97 + gap 3` (canvas `rows=356`) | `left=1.5 right=3.0 top=1.9 voffset=4.5 bottom=3.5 rotate=270 rows=356` | **21,51 × 21,51 mm** vierkant, gemeten 2,00/1,99 mm en 2,03/1,96 mm wit |
| AM11353 / Dymo 11353 | blok **2 × 12,5 × 25 mm** (2-up) | liner 30 mm: −3,5…26,5; rail 10,5; 34 + 3 = 37 mm steek | **34 mm**, gap 3 (canvas `rows=354`) | `xoffset=-2 top=4.5 left=0 right=0 bottom=0` (2-up forceert rotatie 270) | fysiek geijkt met kaders + snijlood (12 nov); beide banen gecentreerd, goedgekeurd |
| S0904980 | **104,2 × 159,9 mm** verzendetiket (nominal 104 × 159) | steek **162 mm** = 159 + 3 (vendor `SIZE 104,162`), gap 3, canvas 1901 (vendor 1902) | `left=0 right=2 top=0.6 bottom=0` — **max inkt**; vendor drukt density 10, speed 4 | gemeten met `--markers` binnen 0,2 mm; frame-proef op de CUPS-route bevestigde na top 0,08 → 0,6; 2 mm-dode zone links, zelfde kop-begrenzing als de vierkante rol | goedgekeurd 12 nov |

Bijbehorende etiketranden in bitmap-coordinaten (x = over de kop, y = voedingsrichting):

- AM11354: x -2…55 mm, y 5,1…37,1 mm.
- AM99012: x -3…33 mm, y -0,5…88,5 mm.
- S0929120: x -2…23,5 mm, y 4,4…29,9 mm. De 2 mm links is onbereikbaar; de
  bereikbare strook is dus 23,5 × 25,5 mm en het grootste gecentreerde
  vierkant 21,5 mm.

- S0904980: x −2,0…102,2 mm (2 mm links onbereikbaar, kop-begrenzing), y
  0,6…159,9 mm; inktband op max bereik.

### AM11353 / Dymo 11353: de rol begint LINKS van de kopstart (fysiek gekalibreerd)

Labellife-capture (10 november, en1 bereikte de printer via 172.16.1.133):

```
SIZE 25.6 mm,34 mm · GAP 3 mm,0 mm · DENSITY 15 · SPEED 6
BITMAP 0,0,160,354,4,,   PRINT 1,1
```

Oude aanname — **op 12 november door de fysiek weerlegd**: de 1-mm liniaal
zei dat de liner bij x = 6 mm begon (blok 7,5..32,5, snijlijn 20 mm). Eerste
gedrukte velletjes landden echter 10 mm te ver rechts en 5 mm te vroeg in de
voeding; twee kaders van 6 × 10 mm werden daarna keurig gecentreerd, en een
loodlijn van 0,25 mm op de vermeende snijlijn (x = 10 mm) viel 0,5 mm **op
etiket A**. De gemeten waarheid, sindsdien in de PPD:

| | x in bitmap-coordinaten |
|---|---|
| liner | −3,5 … 26,5 mm |
| etiket A | −2,0 … 10,5 mm (linker 2,0 mm: dode zone vóór kop-x=0) |
| snijrail A/B | 10,5 mm = dot 124 |
| etiket B | 10,5 … 23,0 mm |
| label bovenkant | rij 53 = 4,5 mm onder de bitmap-oorsprong (top=4,5) |
| label onderkant | ~29,5 mm (kader-rij 348; testlijn 29,85 viel erbuiten) |

De tangent-test (lijnen op 3,99/29,85 mm) bewaakt beide flanken: de
labelbovenkant ligt in (4,0, 4,4], de onderkant in [29,5, 29,9). Bij een
aflezing van 0,5 mm naast een lijn van 0,25 mm is dát het instrument,
niet de PPD.

`xoffset` is hier dus **negatief**: de liner begint links van de kopstart en
onbereikbare strip wordt weggeknippen (CLI: `canvas.paste` met negatieve ox;
filter: `pack_canvas` negeert `px < 0`). De voeding volgt weer uit onze eigen
regel: `34 + 3 = 37 mm`, precies als de vendor.

**Les 2-up-kalibratie**: één loodlijn van 3 dots op de verwachte voeg is het
snelste meetinstrument voor zo'n rol — één voeding, één getal, geen
nummerieke schaal die bijrotateerd misleest. Zet de rol opnieuw? Print de
loodlijn terug; hij hoort in het groefje te staan.

## 6. CUPS-raster (cgpdftoraster, "RaS3")

- Layout: `[4-byte sync "3SaR"] [1796-byte paginaheader] [W*H bytes grijs]`
  en dat herhaalt zich per pagina **zonder** syncwoord. Wie 1800 bytes per
  pagina aanneemt, leest pagina 2 als rommel (de eerste bug die wij hadden).
- Header-relative velden: `u32 @0x114` = dpi x, `@0x118` = dpi y,
  `@0x174` = breedte in pixels, `@0x178` = hoogte.
- Pixels: 8-bit grijs, 0 = zwart, 255 = wit, rijen ongepadd (W bytes).
- `cupsBytesPerLine` staat op offset 0 van de header en is in de praktijk 0;
  tel gewoon W.

## 7. Wat macOS/Word dwarsboomt

- Word stuurt **niet** `media=LW_57x32` maar `media=Custom.90.71x161.57`. De
  gekozen PPD-maat staat in `com.apple.print.PageToPaperMappingMediaName`;
  daar haalt de filter de rolmaat uit.
- Word stuurt `orientation-requested=4`, waardoor `cgpdftoraster` de pagina
  90° **met de klok mee** in het raster draait. De filter draait terug; de
  richting is nagetekend tegen het PDF-beeld zelf (correlatie 0,455 vs 0,000).
- Waardes met spaties zijn geëscaped (`job-name=Microsoft\ Word\ -\ x.docx`):
  split only op niet-geëscape wit, anders ontstaan verzonnen opties.
- Opties van de queue (`lpadmin -o lw-gap=…`) winnen het van de filter-defaults;
  de queue stond lange tijd op `lw-density=8` terwijl de filter 15 gebruikt.
- macOS kopieert bij een IPP-queue het PPD van de server en rendert soms lokaal;
  ontbreekt daar de filter, dan faalt de taak. Op een tweede Mac dus gewoon
  `install.sh` draaien.

## 8. Valleien buiten de printer

- `/usr/bin/python3` is een stub die zonder Xcode Command Line Tools alleen een
  installatiedialoog opent. De filter-wrapper kiest op volgorde: CLT,
  Homebrew (arm64 + Intel), python.org, dan pas de stub.
- `root` mag `~/Documents`, `~/Desktop` en `~/Downloads` niet lezen (TCC):
  "Operation not permitted". Installeren doe je vanuit `/Users/Shared/...`.
- `osascript … with administrator privileges`: `with prompt "…"` moet
  **achter** `with administrator privileges` staan.
- `add-size.sh | head -2` geeft SIGPIPE en bakt de PPD halverwege af.
- `pkill -f "tcpdump -i en"` dood ook zijn eigen shell (het patroon staat in
  de commandregel). Dood op PID.
- Een test mag nooit `git checkout` op de werkboom doen; die van ons
  quietly vernietigde zo een zojuist gemeten rol.

## 9. Bewijs: wat Labellife echt stuurt

Twee keer gepiept met `tcpdump -i en0 tcp port 9100` op de vierkante rol.
Woord voor woord identiek, alleen `DENSITY` volgde de keuze in de app:

```
SIZE 25 mm,33.97 mm
REFERENCE 0,0
GAP  3 mm, 0 mm
OFFSET 0 mm
DIRECTION 0,0
DENSITY 15
BITMAP 0,0,160,356,4,,<LZO-variant>
PRINT 1,1
SPEED 4
```

Wat deze capture opleverde: de breedte in de `SIZE` is het **etiket** (25 mm),
de hoogte is de **voeding minus de gap** (33,97 + 3 ≈ 37 mm), het canvas is
160 × **356** rijen, en mode 4 is hun eigen LZO-variant (twee komma's na de
mode, daarna blokken). Een kruis dat wij met `rows=356 pitch=33.97` printen,
valt exact op het kruis van Labellife — gecontroleerd door de twee etiketten
op elkaar te leggen.

## 10. Hoe een nieuwe rol meten

1. `./measure <breedte> <hoogte> --name LW_XxY [--pitch .. --gap ..] [--rotate ..]`
   drukt één etiket met `0,0` in het midden van het verwachte printvlak,
   1-mm (of `--step` 2/5) streepjes en letters N/Z/W/O.
2. Lees op het echte etiket de vier mm-waarden op de randen af.
3. `./measure solve --N .. --Z .. --W .. --O .. [--pitch .. --gap ..]`
   rekent ze om naar `left`/`right`/`top`/`bottom`/`voffset` en schrijft de
   `add-size.sh`-opdracht.
4. Loopt de startpositie per beurt uiteen: meet de **steek** over 10–20
   etiketten en zorg dat `SIZE-hoogte + gap` er exact aan gelijk is.
5. Twijfel over herhaalbaarheid: print vijf losse beurten van hetzelfde beeld
   en leg ze op elkaar.
6. **Bij een gedraaide of verschoven rol: `--markers`.** `./measure <b> <h>
   --markers [--rotate 270]` drukt één vel met het kader OP de randen van het
   aangenomen printbare vlak en één letter per kant, met de kroon naar haar
   eigen rand; `./measure solve --T <mm> --B <mm> --L <mm> --R <mm>` rekent
   de vier witstroken om (per rotatie gemapt volgens §4A: bij 270 zijn T/B de
   kopkant, L/R de voeding). Bij `rotate` is de genummerde schaal van punt 1
   onleesbaar — letters N/Z/W/O wijzen dan de verkeerde kant op en getalletjes
   op de liner zijn onbruikbaar; drie sessies lang vastgelopen voordat één
   T/B/L/R-vel het in twee afdrukken oploste. De velletjes van §5 (kaders +
   snijlood) zijn de 2-up-variatie hierop.
