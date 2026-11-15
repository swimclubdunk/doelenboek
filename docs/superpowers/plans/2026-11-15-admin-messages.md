# Admin messages Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** The admin writes, schedules and withdraws messages on `/admin/`; every signed-in user sees each live message once, in a popup, the next time they open the app.

**Architecture:** One pure, Node-tested module (`src/messages.js`) holds the formatting-code renderer and every rule about which message is live, pending, replaced or seen. `tools/build.py` inlines it, plus a shared image-compression module (`src/images.js`), into both the app and the admin page. Messages live in a top-level Firestore collection `messages` with an `images` subcollection; each account's seen ids go in its existing `profile/main` record.

**Tech Stack:** Vanilla JS in single-file HTML pages, Firebase JS SDK 10.14.1 (Auth, Firestore) loaded from gstatic, Python build script, `node --test`, Python `unittest`.

**Spec:** `docs/superpowers/specs/2026-11-15-admin-messages-design.md`

## Global Constraints

- No new libraries or CDN scripts. Everything is plain JS/CSS in the existing files and the two new shared modules.
- Shared modules are pure where stated (`messages.js`: no DOM, no Firebase) and follow the `admin-stats.js` pattern: `const X = (() => { ... return {...}; })(); if (typeof module !== 'undefined') module.exports = X;`. Neither may contain `</script`.
- The app's UI strings go in both `T.nl` and `T.en` of `src/doelenboek.html`; the admin page's in both `T.nl` and `T.en` of `src/admin.html`, rendered with `bt()` like every other admin label.
- Image compression: steps `[[1600, .82], [1280, .78], [1024, .74], [800, .7], [640, .65]]`, JPEG, at most `PHOTO_MAX_B64` = 240000 base64 characters.
- Lifetime: whole days, minimum 1, maximum 365, default 30. Scheduled start: at least 60 seconds after the moment the admin presses Send/Save.
- `seen`: a list of at most 1000 message ids.
- Never use browser `alert()`/`confirm()`/`prompt()`; confirmations are in-page.
- Both pages must work at phone width (no horizontal page scroll) and in light and dark theme.
- **Deviation from the spec (the user is told at plan handoff):** the app's query is `where('startAt', '<=', Date.now() - CLOCK_MARGIN)`, `orderBy('startAt', 'desc')`, `limit(50)`, with `endAt` filtered in the app. This needs no composite index, so the rollout only needs the rules published. `CLOCK_MARGIN` = 300000 ms (5 minutes) keeps the query inside the rule when a device clock runs up to 5 minutes ahead.

## Review Focus

1. **A full admin re-render while a draft is open** (language switch, tab switch, Refresh) must keep every typed character, image and setting of the draft. `render()` in `src/admin.html` replaces `#main` wholesale, so the draft must live in `state.draft`, not only in the DOM. Test: Task 6, Step 4.
2. **The message popup opening on top of another dialog** (an activity form open while messages arrive, the lightbox, the thank-you popup) must not happen; it waits. Test: Task 5, Step 6.
3. **Daylight saving time in the end date:** "30 days from 24 Dec 08:00" must end at 08:00 local time, also across the March DST change. Test: Task 2, `endFrom` cases.
4. **Many or very large images in one message** must not break the save: each image is compressed, and the composer refuses a 21st image (cap 20, which keeps one save under Firestore's 10 MiB request limit). Test: Task 6, Step 4.
5. **No connection when the app opens:** the message load must fail silently (console only) and never block the app; a `seen` write made offline is queued by Firestore and applied later. Test: Task 5, Step 6.

---

### Task 1: Formatting codes renderer (`src/messages.js`, part 1)

**Files:**
- Create: `src/messages.js`
- Create: `tests/messages.test.mjs`

**Interfaces:**
- Produces: global `Messages` (and `module.exports`) with
  - `Messages.ZOOMS = ['click', 'hover', 'none']`
  - `Messages.render(text: string, imageIds: Set<string>) -> { title: string, html: string }`
  - `Messages.imageRefs(text: string) -> string[]` (image ids in order of appearance, unique)
  - `Messages.firstLine(text: string) -> string` (first non-empty line, codes stripped, at most 80 characters)

**Rendering rules** (from the spec's *Formatting codes* table):
- `title`: when the first non-empty line is `# text`, `title` is that text (inline codes stripped, HTML-escaped) and the line is left out of `html`. Otherwise `title` is `''`.
- Block level: `# ` → `<h3>`, `## ` → `<h4>`, consecutive `- ` lines → one `<ul>`, consecutive `1. ` (any number + `. `) lines → one `<ol>`, an image line → `<figure class="msg-fig"><img class="msg-img" data-img="ID" data-zoom="ZOOM" alt="ALT"></figure>`, other lines grouped into `<p>` by empty lines, single line breaks inside a paragraph → `<br>`.
- Inline: `**x**` → `<strong>`, `*x*` → `<em>`, `[t](url)` → `<a href="url" target="_blank" rel="noopener noreferrer">t</a>` only for `https:`, `http:`, `mailto:`; any other link stays as its literal escaped text.
- Image line: `![alt](img:ID ZOOM)` alone on its line; ID matches `/^[A-Za-z0-9]{1,20}$/`; ZOOM in `ZOOMS`. An ID not in `imageIds`, or a bad ZOOM, drops the line.
- Everything else is HTML-escaped (`& < > " '`).

- [ ] **Step 1: Write the failing tests** in `tests/messages.test.mjs` (`import M from '../src/messages.js'`):

```js
test('heading on the first line becomes the title', () => {
  const r = M.render('# Vrolijk **kerst**\nTekst', new Set());
  assert.equal(r.title, 'Vrolijk kerst');
  assert.equal(r.html, '<p>Tekst</p>');
});
test('no leading heading: empty title', () => assert.equal(M.render('Tekst\n# Kop', new Set()).title, ''));
test('inline codes', () => assert.equal(M.render('**b** en *i*', new Set()).html, '<p><strong>b</strong> en <em>i</em></p>'));
test('paragraphs and line breaks', () => assert.equal(M.render('a\nb\n\nc', new Set()).html, '<p>a<br>b</p><p>c</p>'));
test('lists', () => {
  assert.equal(M.render('- a\n- b', new Set()).html, '<ul><li>a</li><li>b</li></ul>');
  assert.equal(M.render('1. a\n2. b', new Set()).html, '<ol><li>a</li><li>b</li></ol>');
});
test('subheading', () => assert.equal(M.render('x\n## Sub', new Set()).html, '<p>x</p><h4>Sub</h4>'));
test('raw HTML is shown as text', () => assert.equal(M.render('<img src=x onerror=alert(1)>', new Set()).html, '<p>&lt;img src=x onerror=alert(1)&gt;</p>'));
test('allowed links', () => assert.match(M.render('[site](https://doelenboek.be/?a=1&b=2)', new Set()).html, /<a href="https:\/\/doelenboek\.be\/\?a=1&amp;b=2" target="_blank" rel="noopener noreferrer">site<\/a>/));
test('javascript: link stays text', () => assert.doesNotMatch(M.render('[x](javascript:alert(1))', new Set()).html, /<a /));
test('known image', () => assert.equal(M.render('![Boom](img:ab12 hover)', new Set(['ab12'])).html,
  '<figure class="msg-fig"><img class="msg-img" data-img="ab12" data-zoom="hover" alt="Boom"></figure>'));
test('unknown image id or zoom is dropped', () => {
  assert.equal(M.render('![x](img:zz99 click)', new Set(['ab12'])).html, '');
  assert.equal(M.render('![x](img:ab12 big)', new Set(['ab12'])).html, '');
});
test('imageRefs', () => assert.deepEqual(M.imageRefs('![a](img:x1 click)\n![b](img:y2 none)\n![c](img:x1 hover)'), ['x1', 'y2']));
test('firstLine strips codes and cuts at 80', () => {
  assert.equal(M.firstLine('\n# **Hallo** [daar](https://a.be)\nmeer'), 'Hallo daar');
  assert.equal(M.firstLine('x'.repeat(100)).length, 80);
});
test('empty text', () => assert.deepEqual(M.render('', new Set()), { title: '', html: '' }));
```

- [ ] **Step 2: Run** `node --test "tests/*.test.mjs"`. Expected: the new tests FAIL (module not found); `admin-stats` tests pass.
- [ ] **Step 3: Implement** `render`, `imageRefs`, `firstLine` and `ZOOMS` in `src/messages.js` with the header comment and module pattern from *Global Constraints*.
- [ ] **Step 4: Run** `node --test "tests/*.test.mjs"`. Expected: all PASS.
- [ ] **Step 5: Commit** `git add src/messages.js tests/messages.test.mjs && git commit -m "Messages: formatting-code renderer"`.

---

### Task 2: Message rules (`src/messages.js`, part 2)

**Files:**
- Modify: `src/messages.js`
- Modify: `tests/messages.test.mjs`

**Interfaces:**
- Consumes: Task 1's module.
- Produces (all on `Messages`):
  - `clean(id: string, data: object) -> Msg | null`, where `Msg = { id, langs: ['nl']|['en']|['nl','en'], body: { nl?: string, en?: string }, startAt, endAt, replace: boolean, newAccounts: boolean, replacedBy: string|null, replacedAt: number|null, createdAt: number }`. Returns `null` when `langs` isn't one of the three lists, a language in `langs` has no non-blank `body` entry, `startAt`/`endAt` aren't finite numbers, or `endAt <= startAt`. Body entries for languages not in `langs` are dropped.
  - `endFrom(startAt: number, days: number) -> number`: same local clock time, `days` calendar days later (`Date#setDate`).
  - `effectiveEnd(m: Msg) -> number`: `min(m.endAt, m.replacedAt ?? Infinity)`.
  - `status(m: Msg, now: number) -> 'scheduled'|'live'|'ended'`: `scheduled` when `now < startAt`; `live` when `startAt <= now < effectiveEnd(m)`; otherwise `ended`.
  - `pending(msgs: Msg[], who: { seen: string[], createdAt: number, now: number }) -> Msg[]`: live, id not in `seen`, and (`newAccounts` or `who.createdAt <= m.startAt`); sorted by `startAt` ascending, then `id`.
  - `replacements(msgs: Msg[], now: number) -> Map<string, { replacedBy: string, replacedAt: number } | null>`: one entry per message. A message whose current `replacedAt` is set and `<= now` keeps its current values. For every other message M: the replacing message is the R with `R.replace === true`, `R.startAt > M.startAt` and `R.startAt < M.endAt` that has the earliest `startAt`; the entry is `{ replacedBy: R.id, replacedAt: R.startAt }`, or `null` when there's no such R.
  - `seenCounts(profiles: Array<{ data: object|null }>) -> Map<string, number>`: per message id, the number of profiles whose `data.seen` list holds it (non-string entries ignored, duplicates in one list count once).

- [ ] **Step 1: Write the failing tests.** Use `const day = (m, d, h = 12, y = 2026) => new Date(y, m, d, h).getTime()` and a helper `msg(id, over)` that returns a valid raw record (`langs: ['nl']`, `body: { nl: 'x' }`, `startAt: day(11, 1)`, `endAt: day(11, 31)`, `replace: false`, `newAccounts: false`, `createdAt: day(10, 30)`) merged with `over`.

```js
test('clean rejects bad records', () => {
  assert.equal(M.clean('a', msg('a', { langs: ['de'] })), null);
  assert.equal(M.clean('a', msg('a', { langs: ['nl', 'en'], body: { nl: 'x', en: '  ' } })), null);
  assert.equal(M.clean('a', msg('a', { endAt: day(11, 1) })), null);
  assert.equal(M.clean('a', null), null);
});
test('clean drops body of unlisted language', () => assert.deepEqual(M.clean('a', msg('a', { body: { nl: 'x', en: 'y' } })).body, { nl: 'x' }));
test('endFrom keeps the clock time', () => {
  assert.equal(M.endFrom(day(11, 24, 8), 30), day(0, 23, 8, 2027));
  assert.equal(M.endFrom(day(2, 20, 8, 2027), 30), day(3, 19, 8, 2027));   // across the 28 March 2027 DST change
});
test('status edges', () => {
  const m = M.clean('a', msg('a'));
  assert.equal(M.status(m, day(11, 1) - 1), 'scheduled');
  assert.equal(M.status(m, day(11, 1)), 'live');
  assert.equal(M.status(m, day(11, 31) - 1), 'live');
  assert.equal(M.status(m, day(11, 31)), 'ended');
  assert.equal(M.status({ ...m, replacedAt: day(11, 10) }, day(11, 10)), 'ended');
});
test('pending: seen, new accounts, order', () => {
  const a = M.clean('a', msg('a', { startAt: day(11, 5) }));
  const b = M.clean('b', msg('b', { startAt: day(11, 2) }));
  const c = M.clean('c', msg('c', { startAt: day(11, 3), newAccounts: true }));
  const now = day(11, 10);
  assert.deepEqual(M.pending([a, b, c], { seen: [], createdAt: day(0, 1), now }).map(m => m.id), ['b', 'c', 'a']);
  assert.deepEqual(M.pending([a, b, c], { seen: ['b'], createdAt: day(0, 1), now }).map(m => m.id), ['c', 'a']);
  // account created 4 Dec: b (2 Dec) is hidden, c shows because newAccounts is on, a (5 Dec) started after the account
  assert.deepEqual(M.pending([a, b, c], { seen: [], createdAt: day(11, 4), now }).map(m => m.id), ['c', 'a']);
  assert.deepEqual(M.pending([a, b, c], { seen: [], createdAt: day(0, 1), now: day(11, 31) }), []);   // all ended
});
```

```js
test('replacements: earliest later replacing message wins', () => {
  const m = M.clean('m', msg('m', { startAt: day(11, 1), endAt: day(1, 28, 12, 2027) }));
  const r1 = M.clean('r1', msg('r1', { startAt: day(11, 24), replace: true }));
  const r2 = M.clean('r2', msg('r2', { startAt: day(11, 20), replace: true }));
  const later = M.clean('l', msg('l', { startAt: day(11, 26) }));
  const out = M.replacements([m, r1, r2, later], day(11, 1));
  assert.deepEqual(out.get('m'), { replacedBy: 'r2', replacedAt: day(11, 20) });
  assert.deepEqual(out.get('r2'), { replacedBy: 'r1', replacedAt: day(11, 24) });
  assert.equal(out.get('l'), null);   // starts after r1 and r2
  assert.equal(out.get('r1'), null);
});
test('replacements: no effect on a message that ended before R starts', () => {
  const m = M.clean('m', msg('m', { startAt: day(11, 1), endAt: day(11, 5) }));
  const r = M.clean('r', msg('r', { startAt: day(11, 6), replace: true }));
  assert.equal(M.replacements([m, r], day(11, 1)).get('m'), null);
});
test('replacements: an effective replacement stays after R is withdrawn', () => {
  const m = M.clean('m', msg('m', { replacedBy: 'gone', replacedAt: day(11, 3) }));
  assert.deepEqual(M.replacements([m], day(11, 10)).get('m'), { replacedBy: 'gone', replacedAt: day(11, 3) });
});
test('replacements: a scheduled replacement is recomputed', () => {
  const m = M.clean('m', msg('m', { replacedBy: 'gone', replacedAt: day(11, 20) }));
  assert.equal(M.replacements([m], day(11, 10)).get('m'), null);
});
test('seenCounts', () => {
  const c = M.seenCounts([{ data: { seen: ['a', 'b', 'a', 3] } }, { data: { seen: ['a'] } }, { data: null }, { data: {} }]);
  assert.equal(c.get('a'), 2); assert.equal(c.get('b'), 1); assert.equal(c.size, 2);
});
```

- [ ] **Step 2: Run** `node --test "tests/*.test.mjs"`. Expected: the new tests FAIL (functions undefined).
- [ ] **Step 3: Implement** `clean`, `endFrom`, `effectiveEnd`, `status`, `pending`, `replacements`, `seenCounts` in `src/messages.js` and add them to the returned object.
- [ ] **Step 4: Run** `node --test "tests/*.test.mjs"`. Expected: all PASS.
- [ ] **Step 5: Commit** `git commit -am "Messages: live, pending, replace and seen rules"` (add the test file if untracked).

---

### Task 3: Shared image compression and build inlining

**Files:**
- Create: `src/images.js` (moved from `src/doelenboek.html:516-540`, `processImage`)
- Modify: `src/doelenboek.html` (remove `processImage`, add the two `<script src>` placeholders before the main `<script>` at line 50, call `Images.process(f, PHOTO_MAX_B64)` at line 968)
- Modify: `src/admin.html` (add the two placeholders next to `<script src="admin-stats.js"></script>`)
- Modify: `tools/build.py`
- Modify: `tests/test_build_admin.py`

**Interfaces:**
- Produces: global `Images` with `Images.process(file: Blob, maxB64: number) -> Promise<{ mime: 'image/jpeg', w: number, h: number, data: string }>` (the current `processImage` body, `PHOTO_MAX_B64` replaced by `maxB64`).
- Produces: `build.inline_script(text: str, src_dir: Path, name: str) -> str` in `tools/build.py`: replaces `<script src="NAME"></script>` with the file's contents in a `<script>` block; calls `fail()` when the file contains `</script` (case-insensitive). `build()` and `build_admin()` both inline `messages.js` and `images.js` with it; `build_admin()` also uses it for `admin-stats.js` instead of its current inline code.

- [ ] **Step 1: Write the failing tests** in `tests/test_build_admin.py`:

```python
class SharedScripts(unittest.TestCase):
    def test_both_pages_inline_messages_and_images(self):
        app = build.build(APP, None, rules_with('OWNER_UID'))
        admin = build.build_admin(build.ADMIN_SRC, APP, None, rules_with('OWNER_UID'))
        for page in (app, admin):
            self.assertIn('const Messages = ', page)
            self.assertIn('const Images = ', page)
            self.assertNotIn('<script src="messages.js">', page)
            self.assertNotIn('<script src="images.js">', page)

    def test_script_with_closing_tag_is_refused(self):
        d = Path(tempfile.mkdtemp())
        (d / 'x.js').write_text('const a = "</script>";', encoding='utf-8')
        with self.assertRaises(build.BuildError):
            build.inline_script('<script src="x.js"></script>', d, 'x.js')
```

  The existing `BuiltPagesParse` tests already check that every inline script in both built pages parses.
- [ ] **Step 2: Run** `python -m unittest discover -s tests`. Expected: the two new tests FAIL.
- [ ] **Step 3: Implement** `src/images.js`, `inline_script`, the placeholders and the call-site change.
- [ ] **Step 4: Run** `python -m unittest discover -s tests` and `node --test "tests/*.test.mjs"`. Expected: all PASS.
- [ ] **Step 5: Check the app's photo upload still works:** `python tools/serve.py --port 8000`, open `http://localhost:8000/`, add an activity with a photo. Expected: the photo appears in the activity and in the lightbox.
- [ ] **Step 6: Commit** `git add -A src tools tests && git commit -m "Share image compression; inline messages.js and images.js into both pages"`.

---

### Task 4: Firestore rules

**Files:**
- Modify: `firestore.rules`

**Interfaces:**
- Produces: the access the app (Task 5) and admin page (Task 7) rely on.

- [ ] **Step 1: Add** inside `match /databases/{database}/documents`:

```
    // Admin messages: the admin reads and writes everything; a signed-in user reads only what has started.
    function started() { return request.auth != null && resource.data.startAt <= request.time.toMillis(); }
    match /messages/{msgId} {
      allow read: if isAdmin() || started();
      allow write: if isAdmin();
      match /images/{imgId} {
        allow read: if isAdmin() || started();
        allow write: if isAdmin();
      }
    }
```

- [ ] **Step 2: Change** the profile rule: `keys().hasOnly(['email', 'createdAt', 'lastSeen', 'seen'])`, keep `hasAll(['email', 'createdAt', 'lastSeen'])`, and add `&& (!('seen' in request.resource.data) || (request.resource.data.seen is list && request.resource.data.seen.size() <= 1000))`. Update the comment above it to name `seen`.
- [ ] **Step 3: Run** `python -m unittest discover -s tests`. Expected: PASS (the admin-uid parsing still finds the uid).
- [ ] **Step 4: Commit** `git commit -am "Rules: messages readable once started; seen list on the profile"`.

  The rules are verified live in Task 8, after the user publishes them.

---

### Task 5: The message popup in the app

**Files:**
- Modify: `src/doelenboek.html` (HTML: a `<dialog id="msgdlg" class="msg" aria-labelledby="msg-h"></dialog>` and a `<dialog id="msgzoom" class="msgzoom"></dialog>` after `#thanks`; JS near the thank-you code and in `enterAccount`/`writeProfile`; strings in `T.nl`/`T.en`)
- Modify: `src/design/app.css` (popup, header with title/toggle/✕, `.msg-fig`/`.msg-img`, zoom overlay, hover preview)

**Interfaces:**
- Consumes: `Messages.clean`, `Messages.pending`, `Messages.render`, `Messages.imageRefs` (Tasks 1–2).
- Produces: `loadMessages(user) -> Promise<void>`, `markSeen(id: string) -> Promise<void>`, `showMessages(list: Msg[], images: Map<string, string>)` where the map is image id → `data:` URL.

**Behaviour** (spec, *User side*):
- `enterAccount(user)` calls `loadMessages(user)` after `writeProfile(user)`. `loadMessages` runs one query: `query(collection(fs, 'messages'), where('startAt', '<=', Date.now() - CLOCK_MARGIN), orderBy('startAt', 'desc'), limit(50))`, plus `getDoc` of `users/{uid}/profile/main` for `seen`. It applies `Messages.clean`, then `Messages.pending(msgs, { seen, createdAt: Date.parse(user.metadata.creationTime) || 0, now: Date.now() })`. For the pending messages it loads each referenced image with `getDoc(messages/{id}/images/{imgId})` and makes `data:image/jpeg;base64,` URLs. Any failure: `console.warn('doelenboek: messages not loaded', e && e.code)` and stop.
- `showMessages` waits (1 s polling, like `scheduleThanks`) while `dlg`, `dlg2`, `lb` or `thanksDlg` is open, and only after `loaded.children && loaded.activities`. `scheduleThanks` also waits while `#msgdlg` is open or messages are queued.
- Popup: title (from `render().title` of the current language) on the left; an NL | EN `seg` toggle (`data-msg-lang`) only when `langs.length === 2`; ✕ (`data-close`). Body: `render().html`, then each `img[data-img]` gets its `src` from the map. Footer only with 2+ messages: counter `t('msg_count', i + 1, n)` and a button `t('msg_next')` / `t('close')` on the last.
- Language: starts at `lang` when the message has it, else `langs[0]`; the toggle's choice carries over to the next message in the same popup when that message has the language.
- Seen: `markSeen(id)` on Next, on Close, and in the `close` event for the message on screen. Only that message. `markSeen` calls `setDoc(profileRef, { email: user.email || '', createdAt: Date.parse(user.metadata.creationTime) || now, lastSeen: now, seen: arrayUnion(id) }, { merge: true })`, catches and `console.warn`s.
- `writeProfile` passes `{ merge: true }` to its `setDoc`, so `seen` survives.
- Zoom: `data-zoom="click"` → click opens `#msgzoom` (image at most 92vw × 88vh; closes on click, ✕, Escape). `data-zoom="hover"` → on `pointerenter` with `pointerType === 'mouse'` show a fixed, centred, `pointer-events: none` enlarged copy, removed on `pointerleave`; when `matchMedia('(hover: none)').matches`, behave as `click`. `data-zoom="none"` → nothing, `cursor: default`.
- New strings: `msg_next: 'Volgende'/'Next'`, `msg_count: (a, b) => \`${a} / ${b}\``, `msg_lang: 'Taal van dit bericht'/'Language of this message'`.
- Local preview: on `localhost`/`127.0.0.1` with `?messages` in the URL, `showMessages` runs, after the number of seconds given as its value (`?messages=5`; default 0) and through the same waiting as real messages, with two sample messages: one two-language message with a heading, a list, a link and one image per zoom setting (use the favicon SVG as a `data:` URL), and one Dutch-only message. This mirrors `?thanks`.

- [ ] **Step 1: Write** the dialog markup, CSS and the new strings.
- [ ] **Step 2: Implement** `showMessages` with the popup, language toggle, Next/Close, zoom handling and the `?messages` preview.
- [ ] **Step 3: Implement** `loadMessages`, `markSeen`, the `writeProfile` merge, the `enterAccount` call and the waiting in `showMessages` and `scheduleThanks`.
- [ ] **Step 4: Run** `python -m unittest discover -s tests` and `node --test "tests/*.test.mjs"`. Expected: all PASS.
- [ ] **Step 5: Check the preview** at `http://localhost:8000/?messages` (`python tools/serve.py --port 8000`), at 1280 px and 375 px wide, light and dark theme. Expected: title in the header, toggle only on the two-language message, toggle switches only the message, counter "1 / 2" and Volgende then Sluiten, click-zoom opens and closes, hover-zoom shows on mouse hover at 1280 px and acts as click with touch emulation, the no-zoom image does nothing, no horizontal scroll at 375 px.
- [ ] **Step 6: Check the Review Focus cases.** Load `?messages=5`, open the "add activity" dialog within 5 s, and keep it open past 5 s; expected: the popup appears only after the dialog closes. With `--live` and DevTools set to Offline, reload as a signed-in account; expected: the app opens normally and the console shows `doelenboek: messages not loaded`.
- [ ] **Step 7: Commit** `git commit -am "App: show pending admin messages once, with language toggle and image zoom"`.

---

### Task 6: Admin Messages tab, composer and preview

**Files:**
- Modify: `src/admin.html` (`TABS` gains `'berichten'`; `VIEWS.berichten`; `state.draft`, `state.messages`; composer markup and handlers; styles in its `<style>`; strings in `T.nl`/`T.en`)

**Interfaces:**
- Consumes: `Messages.render`, `Messages.imageRefs`, `Messages.endFrom`, `Messages.ZOOMS`, `Images.process`.
- Produces: `state.draft = { editing: string|null, mode: 'both'|'nl'|'en', body: { nl: string, en: string }, images: Map<string, { data, w, h }>, start: 'now'|'scheduled', startLocal: string /* datetime-local value */, days: number, replace: boolean, newAccounts: boolean, confirming: boolean }`, and `draftToRecord(draft, now: number) -> { langs, body, startAt, endAt, replace, newAccounts }` for Task 7.

**Behaviour** (spec, *Admin side → Writing*):
- Tab labels: `berichten: 'Berichten'` / `'Messages'`.
- Language radio (NL + EN, NL only, EN only); two columns side by side with `grid-template-columns: repeat(auto-fit, minmax(min(100%, 340px), 1fr))`, so they stack on a phone.
- Per column: toolbar (B, I, H, •, 1., link, image), a `<textarea data-draft-lang="nl|en">`, and a preview `<div class="msg-preview">` styled with the same CSS classes as the app popup (copy the `.msg*` rules from `app.css` into the admin `<style>`, or move them to `core.css`, which both pages inline).
- Toolbar actions on the textarea selection: B wraps in `**`, I in `*`, H toggles `# ` → `## ` → none at the line start, • prefixes `- `, 1. prefixes `1. `, link wraps the selection as `[selection](https://)` and selects `https://`. Image: hidden file input, then an in-page mini form (zoom select with the three settings, alt text) → `Images.process(file, 240000)` → id of 8 random `[a-z0-9]` → stored in `state.draft.images` → inserts `![alt](img:ID zoom)` on its own line. A 21st image is refused with a message.
- Typing updates `state.draft` and redraws only that column's preview (no full `render()`); preview images use `data:image/jpeg;base64,` from `state.draft.images`.
- Start radio (Now / Scheduled with `<input type="datetime-local">`), lifetime number input (min 1, max 365, default 30) with the computed end date shown next to it via `Messages.endFrom`; the two checkboxes from the spec.
- Send (or Save when `editing`) is disabled while a chosen language's text is blank, the lifetime is outside 1–365, or a scheduled start is less than 60 s ahead. Pressing it sets `confirming: true`, which shows an in-page summary (start, end, Replace, Also show to new accounts) with Confirm and Back.
- `beforeunload` asks for confirmation while the draft has any text or image and isn't saved.

- [ ] **Step 1: Implement** the tab, `state.draft`, the composer, toolbar, image insert, previews, start/lifetime/toggles and the confirmation summary; Confirm calls `saveDraft()` (Task 7). In this task `saveDraft` only does `console.log(draftToRecord(state.draft, Date.now()))`.
- [ ] **Step 2: Run** `python -m unittest discover -s tests`. Expected: PASS (both pages parse).
- [ ] **Step 3: Check** `http://localhost:8000/admin/#berichten` (demo mode) at 1280 px and 375 px, light and dark: side-by-side columns stack at 375 px, every toolbar button inserts its code, previews match the app popup's look, the end date updates with the lifetime, Send disables in each of the three conditions.
- [ ] **Step 4: Check the Review Focus cases:** type text in both columns and insert two images, then switch NL/EN, switch to another tab and back, and press Refresh (in `--live`); expected: draft, images and settings unchanged. Insert 21 images; expected: the 21st is refused.
- [ ] **Step 5: Commit** `git commit -am "Admin: Messages tab with side-by-side editor and live preview"`.

---

### Task 7: Admin sending, message list, withdraw and delete

**Files:**
- Modify: `src/admin.html`

**Interfaces:**
- Consumes: `draftToRecord` and `state.draft` (Task 6); `Messages.clean`, `status`, `effectiveEnd`, `firstLine`, `replacements`, `seenCounts` (Tasks 1–2).
- Produces: `saveDraft() -> Promise<void>`, `removeMessage(id: string) -> Promise<void>`, `state.messages: Msg[]`, `state.seen: Map<string, number>`.

**Behaviour** (spec, *The message list*, *Replace*, *Data*):
- `load()` also runs `getDocs(collection(fs, 'messages'))` → `state.messages` via `Messages.clean`, and sets `state.seen = Messages.seenCounts(profiles)` from the raw profile rows before `buildDataset`.
- `saveDraft()`: in one `writeBatch`: the message record (`createdAt` kept on edit), every image in `state.draft.images` that the text still references (`images/{imgId}` = `{ data, w, h, startAt }`), deletion of the editing message's images no longer referenced, and for every message where `Messages.replacements(all, Date.now())` differs from its stored `replacedBy`/`replacedAt`, an update (`deleteField()` for `null`). Then reload messages, clear the draft, toast-like status line.
- Before Save on an `editing` message, re-check that its `startAt` is still in the future; otherwise refuse with a message ("this message has already started").
- `removeMessage(id)` (Withdraw for live, Delete for scheduled and ended), after an in-page confirmation: in one batch delete the message, its images (list them with `getDocs(collection(fs, 'messages', id, 'images'))`) and apply the recomputed replacements.
- List: newest `startAt` first; each row: `Messages.firstLine` of `body.nl ?? body.en`, languages, status text per the spec table (scheduled: starts/until; live: until; ended: ended date, or "replaced by" + the replacing message's first line), "seen by N" once started; actions per the spec table. Edit loads the record and its images (`getDocs` of `images`) into `state.draft` with `editing` set.
- Demo mode (no Firebase): `saveDraft` and `removeMessage` work on `state.messages` in memory, images kept in memory, seen counts 0.
- Error on any write: show the Firebase error code with the existing `rules_hint` text.

- [ ] **Step 1: Implement** loading, `saveDraft`, `removeMessage`, the list and Edit.
- [ ] **Step 2: Run** `python -m unittest discover -s tests` and `node --test "tests/*.test.mjs"`. Expected: all PASS.
- [ ] **Step 3: Check in demo mode** at `/admin/#berichten`: send now (status live), schedule one (status scheduled, Edit and Delete), edit it and change its start, send a Replace message and see the older live one show "replaced by …", withdraw the live one, delete an ended one.
- [ ] **Step 4: Commit** `git commit -am "Admin: send, schedule, list, withdraw and delete messages"`.

---

### Task 8: Rollout and live check

**Files:**
- Modify: `README.md` (one paragraph under *Development*: messages are written at `/admin/#berichten`; `firestore.rules` must be republished when it changes)
- Rebuilt: `index.html`, `admin/index.html` (`python tools/build.py src/doelenboek.html index.html firebase-config.json`)

- [ ] **Step 1: Build** with the command above. Expected: `wrote index.html`, `wrote admin/index.html`, no errors. Run both test suites; expected PASS.
- [ ] **Step 2: Commit** `git add -A && git commit -m "Rebuild the app and /admin/ with admin messages"`.
- [ ] **Step 3: The user publishes** `firestore.rules` in the Firebase console (Firestore Database → Rules → Publish). Staging and doelenboek.be share this Firebase project, so the rules apply to both; they only add access, so the current live site keeps working.
- [ ] **Step 4: Live check** with `python tools/serve.py --live --port 8000` (real Firebase): as the admin, schedule a test message 3 minutes ahead with "Also show to new accounts" on. As a normal test account, open the app before the start: no popup, and in the console `getDocs(query(collection(fs,'messages')))` without a filter fails with `permission-denied`. After the start, reopen the app: popup shows; close it; reopen: no popup; open on a second browser: no popup. On the admin list: "seen by 1". Withdraw the test message.
- [ ] **Step 5: If the rules reject the app's query** in Step 4 (popup never shows, console `permission-denied` on the filtered query): stop and ask the user before falling back to `allow read: if request.auth != null` for messages and images (spec, *Access*).
- [ ] **Step 6: Report** to the user; merging to `main` and the staging copy follow the user's choice (superpowers:finishing-a-development-branch).
