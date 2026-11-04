# Minimumdoelen lager onderwijs (not integrated yet)

The minimumdoelen for gewoon lager onderwijs, one file per subject, in the same format as `../doelen/*.json`.
`tools/build.py` only reads `doelen/*.json`, so these files are not part of the app yet.

Source: the onderwijsdoelen.be API (`https://onderwijs.api.vlaanderen.be/onderwijsdoelen/onderwijsdoel`),
fetched 2026-10-20, data dated 2026-10-08. Only goals with status *Geldig* (valid from 1 September 2025).

## Codes

Lager onderwijs has two sets of goals per subject: one to reach by the end of the 4th leerjaar and one by the end
of the 6th. Both reuse the same official numbers (4th-grade 2.1.1 is a different goal from 6th-grade 2.1.1), so the
code is prefixed with the leerjaar: `L4-2.1.1`, `L6-2.1.1`. The prefix also keeps the codes apart from the
kleuter goals in `../doelen/` (which use `2.1.1`), so the app's goal ids (`b-WK-L4-2.1.1`) won't collide.

## Goal types

All goals are *te bereiken* (to be reached) minimumdoelen. Most are set at population level; the 6th-grade
goals of Wiskunde and Nederlands are set at individual level (every pupil should reach them).

## Subjects

| File | subject | Goals (L4 + L6) |
|---|---|---|
| nederlands.json | NL | 72 + 57 |
| wiskunde.json | WK | 122 + 120 |
| wetenschappen-techniek.json | WT | 44 + 61 |
| geschiedenis.json | GE | 19 + 13 |
| aardrijkskunde.json | AK | 21 + 23 |
| muzische-vorming.json | MV | 38 + 40 |
| lichamelijke-opvoeding.json | LO | 16 + 12 |
| attitudes.json | AT | 27 + 30 |
| frans.json | FR | 0 + 50 (new subject, only for the 6th leerjaar) |
| ict.json | IC | 9 + 16 (new subject) |

`FR` and `IC` are not in `SUBJECTS` in `src/doelenboek.html` yet.

## Text

`category` is the top-level heading (*onderwerp*) of the goal, as in the kleuter files. `description` is the goal
sentence plus its *uitbreiding op de doelzin* (the list that completes it), flattened to one line: list items are
joined in order, and examples written as `< bv. ... >` become `(bv. ...)`. Markers such as `[F]` and `[I]` in
Wiskunde are kept as written. The English is a translation; numbers keep the decimal comma of the source.

Three Frans goals refer to the *woordenlijst Frans (Word, Pdf)*; in the source those two words are links to
[the Word file](https://assets.vlaanderen.be/raw/upload/v1750840926/repositories-prd/Woordenlijst_Frans_minimumdoelen_lager_onderwijs_j87jec.docx)
and [the PDF](https://assets.vlaanderen.be/image/upload/v1757496427/repositories-prd/Woordenlijst_Frans_minimumdoelen_extvci.pdf).
