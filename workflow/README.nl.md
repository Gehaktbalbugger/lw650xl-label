# Etiketten printen vanaf Word en Excel (meerdere systemen)

Deze opzet laat de **iMac** alle etiketten maken. Word en Excel op
Windows, macOS of zelfs een telefoon hoeven alleen een **PDF** of **CSV**
in een gedeelde map te zetten. De iMac zet dat om naar de eigen taal van
de printer (TSPL) en stuurt het naar `172.16.1.20:9100`.

Er is dus **geen printerdriver op de clients nodig** en de printer hoeft
geen PCL5 of PostScript te begrijpen.

```
Word / Excel / telefoon
        │  PDF of CSV
        ▼
/Users/Shared/Labelprinter/inbox        (SMB-share "Labelprinter")
        │  launchd-watcher
        ▼
CUPS-queue LW650XL_Labels
        │  cgpdftoraster (300 dpi) → lw650xl-filter
        ▼
TSPL (bitmap mode 0)  →  socket://172.16.1.20:9100  →  LW650XL PRO
```

---

## 1. Eenmalige installatie

Open Terminal op de iMac:

```bash
cd ~/Documents/Standaardproject/label-printer
./setup.sh
```

Het script vraagt om je macOS-wachtwoord. Het doet drie dingen:

1. installeert de CUPS-filter en de queue **LW650XL_Labels**;
2. maakt de gedeelde map **Labelprinter** aan (SMB);
3. installeert de watcher die de inbox automatisch leegprint.

Controleer daarna:

```bash
lpstat -p LW650XL_Labels
lp -d LW650XL_Labels -o media=LW_57x32 ~/Documents/Standaardproject/label-printer/cups/test.pdf
```

De tweede opdracht print één testetiket. Komt er niets uit, zie
[Problemen oplossen](#7-problemen-oplossen).

---

## 2. Word: etiket ontwerpen en printen

### 2.1 Paginaformaat gelijk zetten aan het etiket

Dit is de belangrijkste stap: **de pagina in Word moet precies zo groot
zijn als het etiket**. Anders schaalt de printer het beeld of weigert de
watcher het bestand.

Tip: direct printen vanaf Word naar de printer **LW650XL PRO Labels (TSPL)**
mag ook, mits je bij papierformaat hetzelfde etiket kiest (bijv.
*Etiket 57x32 mm*). De filter corrigeert de staande pagina en het
`Custom`-formaat dat Word doorgeeft; elk documentpagina wordt één etiket.

In Word:

1. **Indeling → Grootte → Meer papierformaten…**
2. Kies **Aangepast** en vul in:
   - Etiket 57 × 32 mm (AM11354, standaard in de printer): breedte
     **5,7 cm**, hoogte **3,2 cm**, liggend.
   - Verzendetiket 102 × 59 mm: breedte **10,2 cm**, hoogte **5,9 cm**,
     liggend.
   - PostNL XL 104 × 159 mm: breedte **10,4 cm**, hoogte **15,9 cm**,
     staand.
3. **Marges → Aangepast**: 0,2 cm rondom, kop- en voettekst 0 cm.
4. Zet **Schalen** op **100%** (niet "aanpassen aan pagina").

Snel invullen kan met de macro's `Label_Pagina_57x32`,
`Label_Pagina_102x59` en `Label_Pagina_104x159` (zie 2.2).

### 2.2 De macro installeren

1. In Word: **Extra → Macro → Visual Basic** (Alt+F11).
2. **Bestand → Bestand importeren…** en kies
   `workflow/word/LabelPrinter.bas`.
3. Sluit de editor.
4. Zet **Label_NaarPrinter** op de werkbalk Snelle toegang:
   pijl rechtsboven → **Meer opdrachten → Alle opdrachten → Macro's**.

De macro exporteert het document als PDF naar de gedeelde inbox. De
iMac pakt hem automatisch op. Je hoeft dus **niet** de printer te kiezen.

> Op de iMac zelf kun je ook gewoon ⌘P → **LW650XL Labels** doen. Kies
> dan het papierformaat dat bij de rol hoort.

### 2.3 Etiket printen

1. Ontwerp het etiket (tekst, tabel, logo, eventueel een barcode-font).
2. Klik op **Label_NaarPrinter**.
3. De melding "Etiket(ten) naar de labelprinter gestuurd" verschijnt.
4. Binnen enkele seconden rolt het etiket eruit.

### 2.4 Mail merge: veel etiketten in één keer (adressen uit Excel)

1. Maak in Excel een lijst met kolommen (bijv. `Naam`, `Straat`, `Postcode`,
   `Plaats`).
2. In Word: **Verzendlijsten → Start samenvoegen → Brieven**.
3. **Ontvangers selecteren → Bestaande lijst gebruiken** → kies het
   Excel-bestand.
4. Zet de velden op het etiket (één etiket per pagina).
5. **Samenvoegen voltooien → Afzonderlijke documenten bewerken… → Alle**.
6. Er opent een nieuw document met één etiket per pagina. Klik op
   **Label_NaarPrinter**.

De PDF bevat alle pagina's; de filter print **één etiket per pagina**.
Dit is de snelste route voor tientallen adressen.

---

## 3. Excel: één etiket per rij (CSV)

Voor losse labels of een adressenlijst zonder Word is er een tweede
route: Excel schrijft een CSV, de iMac print elke rij als etiket.

### 3.1 Blad klaarzetten

Zet in **rij 1** deze koppen (alleen `text` is verplicht):

| text | qr | barcode | copies | size |
|---|---|---|---|---|
| Anna de Bakker\nKeukenstraat 12\n1011 AB Amsterdam | https://track/1 | CODE128:ABC123 | 1 | 57x32 |
| Pakket #1234 | | | 2 | |

- `text`: gebruik de tekens `\n` voor een nieuwe regel.
- `qr`, `barcode`, `copies`, `size` mogen leeg blijven.
- `size` is de etiketmaat in mm; leeg = 57x32.

### 3.2 Versturen

**Methode A – met de macro (Windows):**

1. Extra → Macro → Visual Basic → Bestand importeren →
   `workflow/excel/LabelPrinter.bas`.
2. Extra → Macro → Macro's → **Label_ExportCSV**.

**Methode B – handmatig (elk systeem):**

1. **Bestand → Opslaan als → CSV UTF-8 (door komma's gescheiden)**.
2. Zet het bestand in de gedeelde map `Labelprinter/inbox`.

De watcher print één etiket per rij. Het scheidingsteken (`;` of `,`)
maakt niet uit; dat wordt automatisch herkend.

> Wil je liever met de hand een los etiket printen? Op de iMac:
> `./label "Tekst\nregel 2" --size 57x32`

---

## 4. Vanaf een ander systeem

### Windows

Open Verkenner en ga naar:

```
\\iMac2020\Labelprinter\inbox
```

of, als de naam niet werkt:

```
\\172.16.1.101\Labelprinter\inbox
```

Meld je aan met het macOS-account van de iMac (of gast, als dat aanstaat).
Sleep de PDF of CSV erin. Klaar.

### macOS / iPhone / iPad

Finder → **Ga → Verbinden met server…** →

```
smb://iMac2020.local/Labelprinter
```

Daarna staat de map onder `/Volumes/Labelprinter/inbox`.

### MacBook: eigen printerqueue (direct uit Word printen)

```bash
xcode-select --install                       # alleen de eerste keer (Python 3 + git)
git clone https://github.com/Gehaktbalbugger/lw650xl-label.git ~/label-printer
cd ~/label-printer
sudo ./install.sh
```

Kloon **niet** in `Documenten`, `Bureaublad` of `Downloads`: macOS staat
`sudo` niet toe die mappen te lezen, dan faalt de installatie met
"Operation not permitted". Een gewone map in je thuismap (hier
`~/label-printer`) of `/tmp` werkt wel.

Bijwerken later: `cd ~/label-printer && git pull && sudo ./install.sh`.
Testen: `lp -d LW650XL_Labels ~/label-printer/cups/test.pdf`.

Op een tweede Mac alleen **`install.sh`** draaien: die maakt de queue aan.
`setup.sh` (of `workflow/install-workflow.sh`) is voor de iMac; dat is de
map met gedeelde inbox plus de watcher, en die wil je twee keer niet hebben.

Kies daarna in Word of Excel printer **LW650XL PRO Labels (TSPL)** en
papierformaat **Etiket 57x32 mm (AM11354)**.

De Labellife-driver en -queues van de maker kun je weghalen:
Systeeminstellingen → **Printer en scanner** → oude LW650XL-queue verwijderen.
Ze doen niets mee en staan alleen in de weg.

Zonder installatie kan ook, maar dan via de iMac:

- PDF/CSV in de share hierboven (geen driver nodig), of
- queue toevoegen met **`ipp://iMac2020.local:631/printers/LW650XL_Labels`**.
  Let op: macOS kopieert dan het PPD van de iMac en rendert soms lokaal —
  de filter ontbreekt dan op die Mac en de taak faalt. Dan `install.sh`
  gebruiken.

### Wat de clients nodig hebben

Alleen schrijfrechten op de share. Geen driver, geen software, geen
printerinstellingen. De iMac doet het werk.

---

## 5. Wat de watcher precies doet

- **PDF**: leest het paginaformaat uit de PDF, kiest de bijpassende
  etiketmaat (of een vrije maat), en print via de CUPS-queue.
- **CSV**: leest de rijen en print per rij een etiket via de `label`-CLI
  (met tekst, QR en/of barcode).
- Bestanden die klaar zijn gaan naar `printed/<datum>/`; mislukte naar
  `failed/` met een `.error.txt`.
- De watcher start bij het inloggen/booten, kijkt continu naar de map en
  draait daarnaast elke 60 seconden als vangnet.

Bestandsnamen mogen alles zijn; gebruik geen `~$` aan het begin (dat zijn
Word-vergrendelingsbestanden).

---

## 6. Etiketmaten

Standaard beschikbaar (uit de PPD):

| Naam | Formaat |
|---|---|
| `LW_104x159` | Verzendetiket XL 104 × 159 mm |
| `LW_57x32` | Etiket 57 × 32 mm (AM11354, standaard) |
| `LW_102x59` | Verzendetiket 102 × 59 mm |
| `LW_101x54` | Naambadge 101 × 54 mm |
| `LW_89x36` | Adres breed 89 × 36 mm |
| `LW_36x89` | Adres 36 × 89 mm (AM99012 / Dymo S0722400, **staand**) |
| `LW_26x25` | Vierkant multipurpose 26 × 25 mm (S0929120 / Dymo 30332), zijwaarts geprint |
| `LW_89x28` | Adres 89 × 28 mm |
| `LW_54x25` | Retour 54 × 25 mm |
| `LW_50x12` | Hangmap 50 × 12 mm |
| `LW_57x57` | CD/DVD 57 × 57 mm |
| `LW_62x100` | Continu 62 × 100 mm |

**Zo werkt een nieuwe rol:** de PPD is de enige plaats waar een rol
gedefinieerd wordt. `add-size.sh` schrijft het papierformaat (dat je in Word
kiest) plus één commentaarregel met de geometrie:

```bash
./add-size.sh LW_76x51 "Logistiek 76x51 mm" 76 51 --gap 3 --pitch 54.5 --voffset 0.34
./add-size.sh LW_36x89 "Adres 36x89 mm (AM99012, staand)" 36 89 \
    --gap 4 --pitch 93 --left 3 --right 3 --top -0.5 --bottom 1
sudo ./install.sh
```

```
*% lw-media LW_36x89 pitch=93 gap=4 left=3 right=3 top=-0.5 bottom=1
```

Filter en `label`-CLI lezen die regel, dus Word, `lp` en de gedeelde inbox
werken meteen mee — code aanpassen hoeft niet. `--gap`, `--pitch` en
`--voffset` mag je weglaten: dan is de afstand 3 mm, de steek = hoogte +
afstand en begint de print aan de bovenrand van het etiket.

Daarnaast drie getallen voor de rol die **anders op de liner zit** (smaller,
heter of hoger dan de standaardrol). Die vind je met een meet-etiket:

- `--left` — mm etiket dat links van de kop valt. Die rand is onbereikbaar en
  dus altijd wit. AM11354: 2 mm, AM99012 (36 mm smal): 3 mm.
- `--right` — mm die rechts vrij blijft. Inkt kan niet linkser dan x=0, dus een
  rol met een onbereikbare linkerrand centreer je door rechts evenveel in te
  leveren (AM99012: left 3, right 3 → 30 mm breed printsel, rondom gelijk).
- `--top` — mm van bitmap-oorsprong tot de bovenrand van het etiket. Bij een
  hoog etiket kan dat negatief zijn (AM99012: -0,5 mm); die regels worden dan
  niet geprint.
- `--bottom` — mm die onderaan vrij blijft. Zet dit gelijk aan een onbereikbare
  bovenrand, dan is het printsel gecentreerd (AM99012: 1 mm bij -0,5 mm boven).
- `--gap` en `--gapoff` — lengte van de kloof/het gaatje, en apart hoeveel
  blanco liner er tussen het etiket en dat gaatje zit. Deze rol is
  25 mm etiket + 4 mm liner + 3 mm gaatje + 5 mm liner.
- `--sense` — `gap` (standaard) of `bline` voor zwarte merken. Een 26 mm-roll
  tegen de linkergeleider bereikt een sensor in het midden van het pad nooit;
  `BLINE` geeft dan alleen een papieren-fout. Wat de beurten wél herhaalbaar
  maakt is dat `SIZE-hoogte + gap` gelijk is aan de echte steek.
- `--rows` — hoogte van de bitmap in dots, in plaats van de standaard
  `steek - 12`. Labellife stuurt 356 rijen voor de vierkante rol; die waarde
  overnemen gaf dezelfde registratie als de vendor-app.
- `--rotate` — `90` of `270`: het ontwerp zijwaarts printen (zoals Labellife
  doet bij vierkante rollen). Dit verandert de dode zone niet, alleen de
  leesrichting.

**`--voffset`** schuift de hele print naar beneden op het etiket. Het printbare
vlak begint precies op de bovenrand, waardoor een pagina die Word verticaal
centreert iets te hoog staat. Proefdrukken op de AM11354-rol centreerden op
0,34 mm (4 dots; 0 mm te hoog, 0,5 mm te laag). Met `--voffset 0` print je
weer vanaf de bovenrand.

**Steek (pitch) is de aanvoe-afstand per etiket, niet de etikethoogte.**
Voor de 57 × 32 mm-rol is dat 38,6 mm. Loopt de printer langzaam scheef
na een paar etiketten? Meet dan de afstand tussen dezelfde punt op twee
opeenvolgende etiketten op de rol en geef die opnieuw op. Continu materiaal:
`--gap 0`, dan is de steek gelijk aan de hoogte.

**Een onbekende rol meten** kan in twee opdrachten, zonder driver of root:

```bash
./measure 36 89 --name LW_36x89 --pitch 93 --gap 4    # kruis-etiket printen
./measure solve --N -44.5 --Z 44.5 --W -18 --O 18      # aflezing -> add-size.sh
```

`measure` print één etiket met `0,0` in het midden van het verwachte printvlak,
1-mm streepjes met getallen en N/Z/W/O op de verwachte randen. Lees op het
etiket af welke mm-waarde op de vier echte randen valt; `solve` print de
bijbehorende `add-size.sh`-opdracht met `--left`, `--right`, `--top` en
`--bottom`. Met `--preview plaatje.png` of `--dry-run` niets sturen naar de
printer. De steek (`--pitch`) staat niet op dat kruis: meet 20 etiketten en
deel door 20.

**Rol wisselen** is omhoog: de juiste maat kiezen in Word. Staat de print
scheef of aan één kant afgesneden, meet de vier randen na met een kruis-etiket
(0,0 in het midden, 1-mm-schaal, letters N/Z/W/O) en pas `--left`, `--top`,
`--bottom` en `--voffset` aan met `add-size.sh` + `sudo ./install.sh`.

**Regelmaat valt of staat met de voeding.** Deze printer telt `SIZE-hoogte +
gap` als afstand per etiket. Voor de vierkante rol is dat 34 + 3 = 37 mm,
gelijk aan de gemeten steek; vijf losse afdrukken vielen daarna exact same.
Een verkeerde som zie je meteen: dan staat elk etiket iets hoger of lager.

De watcher leest diezelfde PPD; alleen voor één afwijkende rol kun je
`LW_GAP` of `LW_PITCH` in de LaunchDaemon zetten. Voor een eenmalige test:

```bash
lp -d LW650XL_Labels -o media=LW_76x51 -o lw-pitch=55 -o lw-gap=2 job.pdf
./label "tekst" --size 76x51 --pitch 55 --gap 2
```

---

## 7. Problemen oplossen

**Er komt niets uit de printer**

```bash
lpstat -p LW650XL_Labels -l          # is de queue actief?
lpq -P LW650XL_Labels                # staan er nog jobs?
nc -z -G 2 172.16.1.20 9100 && echo "printer bereikbaar"
```

- Staat de printer aan en op het netwerk (niet alleen Bluetooth)?
- Heeft de printer nog een vast IP? Zo niet, maak een DHCP-reservering
  voor `172.16.1.20`.
- Sluit de Labelife-app eens af; sommige printers accepteren maar één
  verbinding tegelijk.

**Installatie faalt met "Operation not permitted"**

`sudo` mag op macOS de mappen **Documenten**, **Bureaublad** en **Downloads**
niet lezen. Zet de repo in een gewone map, bijvoorbeeld `~/label-printer`,
en draai `sudo ./install.sh` vanaf daar.

**Een afdruktaak blijft hangen of meldt "Filter failed"**

```bash
lpstat -W completed -l -o LW650XL_Labels     # laatste taken + waarschuwing
sudo cp /var/log/cups/error_log /tmp/cups.err && tail -40 /tmp/cups.err
```

- "geen werkende Python 3 gevonden": `xcode-select --install` of
  `brew install python`, daarna `sudo ./install.sh` opnieuw.
- "bad raster magic": de geïnstalleerde filter is verouderd — `git pull`
  en `sudo ./install.sh`.
- Filter en PPD staan in `/usr/libexec/cups/filter/` en
  `/etc/cups/ppd/LW650XL_Labels.ppd`; ze moeten identiek zijn aan de repo
  (`md5 /usr/libexec/cups/filter/lw650xl.py`).

**Het bestand verdwijnt naar `failed/`**

Open `failed/<naam>.error.txt` en `/Users/Shared/Labelprinter/logs/print.log`.
Meestal is het paginaformaat niet gelijk aan het etiket (bijv. A4). Zet
in Word het aangepaste paginaformaat goed.

**De afdruk staat scheef of te hoog/laag**

- Controleer of de geladen rol bij de gekozen maat hoort.
- Pas de etiketafstand aan: `lw-gap` (standaard 3 mm). Voor continu
  materiaal: `-o lw-gap=0` of een maat met `add-size.sh ... --gap 0`.
- Staat de print te hoog of te laag op het etiket: `--voffset` in `add-size.sh`
  (of eenmalig `-o lw-voffset=<mm>` / `--voffset <mm>`). Staat het printsel
te ver naar één zijkant en is die kant onbereikbaar: zet `--left` en `--right`
aan elkaar gelijk.
- De feed-hoogte (`SIZE`) is de etiket*steek* (etiket + tussenruimte),
  niet de etikethoogte: 38,6 mm voor de 57 × 32 mm-rol. Voor een andere
  rol: `-o lw-pitch=<mm>`.
- De filter gebruikt de rand van de pagina als referentie; houd 0,2 cm
  marge aan in Word.

**De share is niet zichtbaar**

- Systeeminstellingen → Algemeen → Delen → **Bestandsdeling** aan.
- Controleer of `Labelprinter` bij de gedeelde mappen staat.
- Firewall: sta inkomend verkeer voor `cupsd` en `smbd` toe.

**Logboeken en status**

```bash
tail -f /Users/Shared/Labelprinter/logs/print.log
tail -f /Users/Shared/Labelprinter/logs/watcher.err.log
sudo launchctl print system/com.benno.labelprinter.watcher
```

**Watcher herstarten**

```bash
sudo launchctl kickstart -k system/com.benno.labelprinter.watcher
```

**Alles verwijderen**

```bash
sudo ./workflow/uninstall-workflow.sh
sudo ./uninstall.sh
```

---

## 8. Bestanden

| Bestand | Functie |
|---|---|
| `setup.sh` | eenmalige complete installatie |
| `install.sh` | alleen de CUPS-queue |
| `workflow/print-inbox.sh` | de watcher |
| `workflow/pdfmedia.py` | paginaformaat → CUPS-media |
| `workflow/csv2labels.py` | CSV → één etiket per rij |
| `workflow/word/LabelPrinter.bas` | Word-macro's |
| `workflow/excel/LabelPrinter.bas` | Excel-macro (CSV) |
| `workflow/com.benno.labelprinter.watcher.plist` | launchd-template |
