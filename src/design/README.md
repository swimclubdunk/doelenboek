# Design

Everything that decides how Doelenboek looks lives in this folder. You can change any of it without
touching the app's code, its data or how accounts work.

```
tokens.css            colours (light and dark), subject colours, fonts, corner radius, shadow
fonts/                the font files (woff2) and their licences (SIL Open Font License)
app.css               layout and the look of every screen and component
favicon.svg           the browser-tab icon
animals/animals.json  which animals exist, their order in the picker, and the emoji each belongs to
animals/*.svg         one drawing per animal
```

What is **not** here: the texts (Dutch and English, in `src/doelenboek.html`), the page structure
and behaviour (also there), and `src/core.css`, a handful of rules the code depends on.

## Working on the design

```
python tools/serve.py
```

Then open http://localhost:8000. Every refresh rebuilds the page from the current files, so the loop is
"save the file, refresh the browser". http://localhost:8000/animals shows every animal on light and
dark, at all sizes the app uses, and checks that each one fills its frame.

By default the preview keeps its data in your browser only, so you can add and delete test children
freely. `python tools/serve.py --live` logs into your real account instead (careful: changes are real).

When it looks right, build and publish as usual (see the main README).

## Tokens (`tokens.css`)

Start here: most of the look comes from these values, and every screen uses them.

| Token | Used for |
|---|---|
| `--chrome`, `--on-chrome`, `--on-chrome-muted` | the header band; text and icons on it |
| `--bg` | page background |
| `--surface`, `--surface-2` | cards and dialogs; quieter fills (bars, inputs, avatar fallback) |
| `--fg`, `--muted` | main text; secondary text |
| `--line` | borders and dividers |
| `--accent`, `--accent-fg` | primary buttons, active tab, links; text on top of the accent |
| `--danger`, `--ok`, `--warn-bg`, `--warn-fg` | delete and errors; "connected"; notices |
| `--s-nl`, `--s-wk`, `--s-wt`, `--s-ge`, `--s-ak`, `--s-mv`, `--s-lo`, `--s-at` | one colour per subject (bars, dots, goal codes) |
| `--f-display`, `--f-body`, `--f-mono` | headings; everything else; goal codes and numbers |
| `--r`, `--r-sm` | corner radius of cards, dialogs and pop-ups; of small controls (buttons, fields, chips) |
| `--shadow` | card shadow |

Every text colour reaches WCAG AA contrast (4.5:1) on the surfaces it sits on, in both themes. Check
again when you change a colour.

- **Bright and dark** live side by side: each colour is written once as `light-dark(bright, dark)`, so
  changing a colour in one theme is a single edit next to its counterpart. The app starts bright; the
  sun/moon button in the header switches to dark, and that choice is remembered for the next visit.
  Colours written outside the tokens (in `app.css`) are the same in both themes, so prefer a token.
- **Fonts** are loaded by the `@import` on the first line. Change the URL and the `--f-*` names together.
- The subject tokens must keep these names: the code refers to them as `--s-` plus the subject key.

## Components (`app.css`)

Restyle freely: rename nothing, and the app keeps working. The class names below are what the code
puts in the page, so they are the hooks you style. Adding a new class means changing the code.

- **Header:** `top`, `top-inner`, `brand`, `tabs` (links get `aria-current="page"` when active),
  `top-right`, `status` (+ `ok` / `warn`), `theme-btn` (the sun/moon button), `lang-switch` (buttons get `aria-pressed="true"`), `site-foot` (with `support`, the donation line), `about` (on the login screen: what the app is for), `thanks` (the one-time donation thank-you: `thanks-art`,
  `thanks-animal`, `thanks-cup`, `thanks-actions`)
- **Page:** `page-head`, `lede`, `head-actions`, `toolbar`, `search`, `select`, `notice`, `empty`,
  `loading`, `count-line`, `muted`, `meta`
- **Buttons:** `btn` (+ `primary`, `ghost`, `small`, `danger`), `icon-btn` (+ `del`), `linkish`, `back`,
  `fchip` (filter chips, `aria-pressed`)
- **Children:** `child-grid`, `child-card`, `cc-head`, `cc-id`, `cc-pct`, `cc-foot`, `bars` (rows with
  `b-lbl`, `bar`, `b-num`; `none` when a subject has no goals), `kid-head`, `kid-name`
- **Avatars:** `avatar` (+ `lg`, `sm`; `off` = goal not mastered yet). Animal drawings fill the box;
  the grey circle only shows for an animal without a drawing.
- **Child cards:** `bars` rows end in `touch` (activity tags, `zero` when none)
- **Goals per child:** `seg` (All / To do / Mastered, `seg-n` counts), `subj` (a `<details>`, `open`
  when expanded), `status-list` (rows `done` when mastered, `untouched` when no activity tagged them),
  `code`, `g-body`, `g-meta`, `g-desc`, `since`, `via`, `touch`, `mastery` (the tick pill)
- **Activities:** `act-list`, `act`, `act-date` (`d` day, `m` month), `act-body`, `act-kids`,
  `goal-chips`, `goal-chip`, `act-photos` (the photo column), `thumbs`, `thumb`, `photo-count`, `notes`, `row-actions`, `month`
- **Goal list:** `chips-filter`, `goal-list`, `goal-row`, `g-side`, `kids-row`, `tag`
- **Dialogs:** `dlg-form`, `dlg-body`, `field`, `field-label`, `hint`, `form-error`, `info`, `row2`,
  `animal-grid`, `kid-picks`, `kid-pick`, `goal-field`, `sel-chips`,
  `data-actions`, picker (`picker-dlg`, `picker-bar`, `picker-scroll`, `pick-group`, `pick`,
  `pick-count`, `pick-more`), photos (`photo-edit`, `pe`, `pe-x`, `photo-add`, `drop` while dragging)
- **Overlays:** `lightbox` (`lb-btn`, `lb-prev`, `lb-next`, `lb-close`), `peek` and `gpeek` hover
  previews (`show` when visible), `toast` (`show`), `auth` login screen (`auth-links`, `privacy`)
- **Classes that mean something to the code** (style them, but don't rely on removing them): `w` marks
  controls that change data, `bi` holds a label in both languages, `dot` is a subject-coloured dot whose
  colour comes from `--c`.

## Animals (`animals/`)

Each animal is a plain SVG file, so you can draw or edit it in any tool (Figma, Illustrator, Inkscape)
and save it here.

- **The viewBox must hug the drawing**, with no empty margin, and the background must be transparent.
  The app scales every animal until it touches the edge of the avatar, so they all look the same size.
  `/animals` in the preview tells you if one doesn't fill its frame.
- **Add an animal:** save `name.svg` here and add `{"animal": "name", "emoji": "🦔"}` to
  `animals.json`. The emoji is how a child's choice is stored; pick one that isn't used yet.
- **Never change or remove the emoji of an existing animal.** Children who chose it would lose their
  drawing (they fall back to showing the emoji). Changing the drawing itself is always safe.
- **Reorder the picker** by reordering `animals.json`.
- Files from design tools are fine: the build removes the XML header, comments and metadata, and keeps
  gradients working. Scripts aren't allowed in a drawing; the build refuses them.

The current set shares one style: flat, front-facing heads; ink-coloured eyes `#2B2523` with a small
white highlight; soft cheeks (`#EF7D7D` at 40% opacity); no outlines.
