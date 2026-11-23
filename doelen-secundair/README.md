# Eindtermen secundair onderwijs, 1ste graad (A- and B-stroom)

The goals for the first two years of secundair onderwijs, one file per app subject. `tools/build.py` reads them
into the app as two levels: `S1A` (A-stroom) and `S1B` (B-stroom), shown as **Sec1A** and **Sec1B**.

Source: the "Onderwijsdoelen in Excel" download on
[onderwijsdoelen.be](https://onderwijsdoelen.be/doelen/SO_1STE_GRAAD_V2_1) (version 2.1, valid from 1 September 2024),
downloaded 2026-11-23. The Excel itself and a plain extraction of it are kept outside the repo, in `stuff/onderwijsdoelen/`.

## Format

Unlike `../doelen/` and `../doelen-lager/`, a goal has a code per stream:

```json
{ "codes": { "S1A": "03.08", "S1B": "03.07" }, "extension": ["S1B"], "category": "", "categoryEn": "",
  "description": "De leerlingen ...", "descriptionEn": "Pupils ..." }
```

- `codes`: the official number in each stream the goal belongs to. A goal worded exactly the same in both streams
  (same sleutelcompetentie, same text) is **one** goal with two codes, so a child's tick carries over when they
  change stream. The numbers can differ between streams. The app id uses the first stream: `b-FR-S1A-03.08`.
- `extension` (optional): the streams in which the goal is an *uitbreidingsdoel*; the app labels it there.
- `category` only for Maatschappij and Attitudes, which hold several sleutelcompetenties.

## From sleutelcompetenties to subjects

| Subject (file) | Sleutelcompetentie(s) |
|---|---|
| NL nederlands | 2 Nederlands |
| FR andere-talen | 3 Andere talen (named "Andere talen" in the secundair) |
| WK wiskunde | 6, first part: A 06.01-06.23, B 06.01-06.11, and BG06 (basisgeletterdheid) |
| WT wetenschappen-techniek | 6, second part: A 06.24-06.44, B 06.12-06.28 |
| GE geschiedenis | 8 Historisch bewustzijn |
| AK aardrijkskunde | 9 Ruimtelijk bewustzijn |
| MA maatschappij | 7 Burgerschap, 11 Economische en financiële competenties (10 Duurzaamheid, 12 Juridische competenties: see below) |
| MV muzische-vorming | 16 Cultureel bewustzijn |
| LO lichamelijke-opvoeding | 1 Lichamelijke en geestelijke gezondheid |
| IC ict | 4 Digitale competentie en mediawijsheid |
| AT attitudes | 5 Sociaal-relationele competenties, 13 Leercompetenties, 15 Initiatief en ondernemingszin (14 Zelfbewustzijn: see below) |

Sleutelcompetentie 6 is one block in the source; the official numbering lists all mathematics first, then science
and technology. Measuring instruments, quantities and units, and the STEM goals go to Wetenschappen & techniek.

## Left out

- Sleutelcompetenties 10, 12 and 14 have no eindtermen of their own: the source holds one row each (code `000` or
  `0000`) saying they are covered by other sleutelcompetenties. Those rows are notes, not goals.
- Uitbreidingsdoelen (`UD…`, all Nederlands) whose text is exactly that of an eindterm of the same stream: the
  source holds no difference between the two. Kept: A UD02.09, UD02.11; B UD02.02, UD02.04, UD02.05, UD02.06, UD02.11.

## Counts

A-stroom 126 goals, B-stroom 103, of which 66 in both: 163 goals in all.
The English is a translation in the style of the lager goals.
