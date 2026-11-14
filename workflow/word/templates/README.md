# Word templates — one per roll

These are the working templates the printer owner designs in, with the page
settings that match each roll's 1:1 printable-area page. Open one, replace
the content, print to the **LW650XL_Labels** queue with the matching paper
size selected. What you see is what prints (the pages are the printable
area — no scaling, no hidden clipping).

The paper sizes must exist in the queue: install the driver first
(`install.sh` at the repo root, or update an existing queue the same way).

| template | roll | Word paper size (select in the print dialog) | page |
|---|---|---|---|
| `AM99017 Hangmap Etiket 50x21.docx` | AM99017 50 × 21.3 Hangmap | **AM99017 50x21.3 Hangmap (49.8x19.3)** | portrait 49.8 × 19.3 mm |
| `AM11353 Price Tag 2x13x25.docx` | AM11353 2 × 12.5 × 25 block | **AM11353 25x25 Blok 2x 12.5 (25x23)** | portrait 25 × 23 mm — design both 12.5 mm labels side by side; the cut groove sits at 10.5 mm from the left edge |
| `AM11354 Generic 57x32.docx` | AM11354 57 × 32 | **AM11354 32x57 Etiket (31.3x54.2)** | portrait 54.2 × 31.3 mm — use **landscape** orientation for upright text |
| `AM99012 Adres Etiket breed 89x36.docx` | AM99012 36 × 89 Adres | **AM99012 89x36 Adres staand (88.5x33)** | portrait 88.5 × 33 mm — landscape works too: feed runs left → right on the screen, top margin = white on the label's far side |
| `S0929120 Square Tag 25x26.docx` | S0929120 25.5 square | **S0929120 25.5x25.5 Vierkant (25.5x23.5)** | portrait 25.5 × 23.5 mm |
| `S0904980 PostNL large 159x104 Landscape.docx` | S0904980 104 × 159 shipping | **S0904980 159x104 Verzendetiket (159.8x102.2)** | landscape layout of the portrait 159.8 × 102.2 mm page |
| `S0904980 PostNL large 159x104 Portrait.docx` | S0904980 104 × 159 shipping | **S0904980 159x104 Verzendetiket (159.8x102.2)** | portrait layout of the same page |

Design notes (the same for every roll):

- **Left edge**: the page starts at the first printable millimetre; the
  dead zone (2–3 mm, roll-dependent) is *outside* the page and always
  stays white. Left margin 0 is safe.
- **Right/top/bottom edges**: the page reaches the physical label edges —
  add your own margins there. The old centred looks (2–3 mm white) are now
  ordinary page margins.
- **Orientation**: portrait-dimensioned pages offer Word's straight /
  landscape toggle. Landscape = content upright on a sideways label; the
  feed runs left → right on the screen (leading edge at the left margin).
- Margins of 0 mm are accepted: the driver's ImageableArea covers the full
  page by design.

The shipping-label templates also demonstrate the Word mail-merge route
(`LabelPrinter.bas` one directory up) for label-per-page documents.
