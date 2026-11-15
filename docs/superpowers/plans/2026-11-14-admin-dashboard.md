# Admin Dashboard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A private page at `doelenboek.be/admin/` with five tabs (Overzicht, Groei, Gebruik, Inhoud, Accounts) showing platform numbers to the site owner only.

**Architecture:** `src/admin.html` is a standalone page built by `tools/build.py` into `admin/index.html`, reusing the app's CSS, goals, subjects and tiers. It signs in with Firebase Auth, runs three collection-group queries (allowed only for the owner's uid by `firestore.rules`), and passes the raw records to `src/admin-stats.js`. That file holds pure functions that drop names and notes and compute every number. The app writes a small `users/{uid}/profile/main` record (email, sign-up date, last seen) so the admin can see emails and activity.

**Tech Stack:** Plain HTML/CSS/JS (no framework, no bundler), Firebase JS SDK 10.14.1 from gstatic, Firestore, Python 3 build scripts, `node --test "tests/*.test.mjs"` (Node 24) for the stats module, Python `unittest` for the build.

**Spec:** `docs/superpowers/specs/2026-11-14-admin-dashboard-design.md`

## Global Constraints

- All admin UI text is in Dutch. Tier labels come from the app's `TIERS[].badge.nl` exactly ("Kleuter", "Lager LJ 1-4", "Lager LJ 5-6", with hyphens, not en dashes).
- Counts only: child names, activity titles and notes, and photos are never stored in page state or rendered. Children are shown as "Kind 1", "Kind 2"…
- Records with `example: true` are excluded everywhere.
- No chart library and no new dependencies. Charts are CSS bars. Firebase SDK version `10.14.1`, the same URL as the app.
- Numbers use `Intl.NumberFormat('nl-BE')` (`6.840`). Weeks start on Monday, local time.
- Admin can read but never write other accounts. `photos` and the legacy `goals` stay closed to the admin.
- The page carries `<meta name="robots" content="noindex, nofollow">` and isn't linked anywhere. `robots.txt` gets `Disallow: /admin/`.
- The layout works at phone width (360px) without horizontal page scroll (wide tables scroll inside their card), in light and dark themes.
- Work stays on branch `feature/admin-dashboard`. Commit messages end with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- Spec refinement: `lastSeen` counts as activity in the week it falls in (not only the current week). It is an exact visit, so this is strictly more accurate. The spec is updated in the same commit as this plan.

## Review Focus

1. **Accounts from before the profile update** (no profile record): they must still appear, with a "~" sign-up date from their oldest record and "last active" from their record timestamps. Pinned in Task 1 (`u2` fixture) and Task 3 (row fields).
2. **Malformed or hand-edited records** (missing name or title, `createdAt` as text, `goalIds` not an array, more than 24 photo ids, ids with illegal characters): skipped or cleaned, never a crash or `NaN`. Pinned in Task 1.
3. **Empty platform** (no accounts at all, or rules not yet published so nothing loads): every tile shows 0, percentages show 0 (no division by zero), and a query failure shows the "regels publiceren" hint. Pinned in Tasks 1–3 (empty-input tests) and Task 6 (error view).
4. **Week and day boundaries in local time** (Sunday 23:59 vs Monday 00:00, the exact 30- and 90-day edges, "vandaag" vs "gisteren" around midnight). Pinned in Task 2 and Task 3.
5. **Goal ids that aren't built-in** (from the legacy custom `goals` collection or removed goals): counted as "Onbekend" per subject and left out of the top-goals table, never shown as `undefined`. Pinned in Task 3.

---

## File map

| File | Status | Responsibility |
|---|---|---|
| `src/admin-stats.js` | create | Pure functions: clean records, build accounts, compute each tab's numbers, relative-day text. |
| `tests/admin-stats.test.mjs` | create | `node --test` tests for `admin-stats.js`. |
| `src/admin.html` | create | Admin page: header, tabs, sign-in, loading, demo data, rendering, events. |
| `tests/test_build_admin.py` | create | `unittest` tests for `build_admin()` and `robots()`. |
| `tools/build.py` | modify | `goals_js()`, `js_block()`, `admin_uid()`, `build_admin()`; main writes `admin/index.html`. |
| `tools/serve.py` | modify | Route `/admin/` to `build_admin()`. |
| `tools/public.py` | modify | `robots()` gets `Disallow: /admin/`; privacy texts (Task 9). |
| `firestore.rules` | modify | `isAdmin()`, profile rules, admin collection-group reads. |
| `src/doelenboek.html` | modify | `writeProfile()` on sign-in; delete `profile` on account deletion; privacy text (Task 9). |

---

### Task 1: Stats module — cleaning records and building accounts

**Files:**
- Create: `src/admin-stats.js`
- Test: `tests/admin-stats.test.mjs`

**Interfaces:**
- Produces (used by every later task):
  - `AdminStats.DAY` = `86400000`
  - `AdminStats.buildDataset(raw, tierKeys = ['KO','L4','L6']) → Account[]`
    - `raw = { profiles?: Row[], children?: Row[], activities?: Row[] }`, where `Row = { uid: string, id: string, data: object }`
    - `Account = { uid, email: string, hasProfile: boolean, signupAt: number, signupApprox: boolean, lastSeen: number, lastActive: number, children: Child[], activities: Activity[] }`
    - `Child = { id, createdAt, updatedAt, tier, mastered: string[] }`, sorted by `createdAt`, then `id`
    - `Activity = { id, createdAt, updatedAt, childIds: string[], goalIds: string[], photos: number }`
    - Accounts appear in insertion order: profiles first, then children, then activities.
- The file is a classic script that defines a global `AdminStats`, and also does `module.exports = AdminStats` when `module` exists, so Node can import it.

- [ ] **Step 1: Write the failing test**

Create `tests/admin-stats.test.mjs`:

```js
// Tests for src/admin-stats.js. Run: node --test "tests/*.test.mjs"
import test from 'node:test';
import assert from 'node:assert/strict';
import S from '../src/admin-stats.js';

// "now" is Saturday 14 Nov 2026, 12:00 local time. Months are 0-based (10 = November).
export const NOW = new Date(2026, 10, 14, 12).getTime();
export const day = (m, d, h = 12, y = 2026) => new Date(y, m, d, h).getTime();

export const RAW = {
  profiles: [
    { uid: 'u1', id: 'main', data: { email: 'An@Example.be', createdAt: day(2, 12), lastSeen: day(10, 14, 9) } },
    { uid: 'u4', id: 'main', data: { email: 'x@y.be', createdAt: day(10, 10), lastSeen: day(10, 10) } },
    { uid: 'u9', id: 'main', data: null },
  ],
  children: [
    { uid: 'u1', id: 'c2', data: { name: 'Bo', tier: 'L4', createdAt: day(3, 1), updatedAt: day(10, 1), mastered: { 'b-NL-1.1.2': '2026-10-01', 'bad id!': 'x' } } },
    { uid: 'u1', id: 'c1', data: { name: 'Ada', tier: 'XX', createdAt: day(2, 20), updatedAt: 0 } },
    { uid: 'u1', id: 'cx', data: { name: 'Voorbeeld', example: true, createdAt: day(2, 12) } },
    { uid: 'u2', id: 'k1', data: { name: '  ', createdAt: day(5, 1) } },
    { uid: 'u2', id: 'k2', data: { name: 'Cas', tier: 'L6', createdAt: day(5, 2), updatedAt: day(7, 3) } },
  ],
  activities: [
    { uid: 'u1', id: 'a1', data: { title: 'Lezen', createdAt: day(9, 1), updatedAt: day(9, 2), childIds: ['c1', 'c2', 'c1'], goalIds: ['b-NL-1.1.2', 'b-??', 'zz'], photoIds: ['p1', 'p2'] } },
    { uid: 'u2', id: 'a2', data: { title: '', createdAt: day(6, 1) } },
    { uid: 'u2', id: 'a3', data: { title: 'Tellen', createdAt: 'gisteren', updatedAt: day(7, 1), goalIds: 'nope', photoIds: Array.from({ length: 30 }, (_, i) => 'p' + i) } },
    { uid: 'u3', id: 'a4', data: { title: 'Voorbeeld', example: true, createdAt: day(1, 1) } },
  ],
};
export const accounts = () => S.buildDataset(RAW);

test('buildDataset: one account per uid with real data or a profile; example-only uids are left out', () => {
  assert.deepEqual(accounts().map(a => a.uid), ['u1', 'u4', 'u2']);
});

test('buildDataset: profile fields, children sorted by createdAt, invalid tier falls back to KO, names dropped', () => {
  const u1 = accounts()[0];
  assert.equal(u1.email, 'An@Example.be');
  assert.equal(u1.hasProfile, true);
  assert.equal(u1.signupAt, day(2, 12));
  assert.equal(u1.signupApprox, false);
  assert.deepEqual(u1.children.map(c => [c.id, c.tier]), [['c1', 'KO'], ['c2', 'L4']]);
  assert.deepEqual(u1.children[1].mastered, ['b-NL-1.1.2']);
  assert.equal('name' in u1.children[0], false);
  assert.equal(u1.lastActive, day(10, 14, 9));
});

test('buildDataset: activities are de-duplicated and cleaned, photos capped at 24, titles dropped', () => {
  const [u1, , u2] = accounts();
  const a1 = u1.activities[0];
  assert.deepEqual(a1.childIds, ['c1', 'c2']);
  assert.deepEqual(a1.goalIds, ['b-NL-1.1.2', 'zz']);
  assert.equal(a1.photos, 2);
  assert.equal('title' in a1, false);
  assert.deepEqual(u2.activities.map(a => a.id), ['a3']);
  assert.equal(u2.activities[0].createdAt, 0);
  assert.deepEqual(u2.activities[0].goalIds, []);
  assert.equal(u2.activities[0].photos, 24);
});

test('buildDataset: an account without a profile gets an approximate sign-up date and last-active from its records', () => {
  const u2 = accounts()[2];
  assert.equal(u2.hasProfile, false);
  assert.equal(u2.email, '');
  assert.deepEqual(u2.children.map(c => c.id), ['k2']);
  assert.equal(u2.signupAt, day(5, 2));
  assert.equal(u2.signupApprox, true);
  assert.equal(u2.lastActive, day(7, 3));
});

test('buildDataset: profile-only account has no children or activities; last active is its last visit', () => {
  const u4 = accounts()[1];
  assert.equal(u4.children.length, 0);
  assert.equal(u4.activities.length, 0);
  assert.equal(u4.lastActive, day(10, 10));
});

test('buildDataset: empty or missing input gives no accounts', () => {
  assert.deepEqual(S.buildDataset({}), []);
  assert.deepEqual(S.buildDataset({ profiles: [], children: [], activities: [] }), []);
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `node --test "tests/*.test.mjs"`
Expected: FAIL with `Cannot find module '…/src/admin-stats.js'`.

- [ ] **Step 3: Write minimal implementation**

Create `src/admin-stats.js`:

```js
/* Doelenboek admin: turns the raw Firestore records into the numbers the admin tabs show.
   Pure functions only (no DOM, no Firebase), so tests/admin-stats.test.mjs runs them in Node.
   tools/build.py inlines this file into admin/index.html.
   Names, titles and notes are dropped while cleaning: the admin page only ever holds counts. */
const AdminStats = (() => {
'use strict';
const DAY = 86400000;
const MAX_PHOTOS = 24;   // per activity, as in the app
const ID_RE = /^[A-Za-z0-9_\-~:@+.]{1,120}$/;
const num = v => typeof v === 'number' && isFinite(v) ? v : 0;
const ids = v => Array.isArray(v) ? [...new Set(v.filter(x => typeof x === 'string' && ID_RE.test(x)))] : [];
const named = v => typeof v === 'string' && v.trim() !== '';
const maxOf = arr => arr.reduce((m, v) => v > m ? v : m, 0);

/* The same rules as clean() in doelenboek.html: a child needs a name, an activity a title. */
function cleanChild(b, tierKeys) {
  if (!b || typeof b !== 'object' || b.example === true || !named(b.name)) return null;
  const m = b.mastered && typeof b.mastered === 'object' && !Array.isArray(b.mastered) ? Object.keys(b.mastered).filter(k => ID_RE.test(k)) : [];
  return { createdAt: num(b.createdAt), updatedAt: num(b.updatedAt), tier: tierKeys.includes(b.tier) ? b.tier : tierKeys[0], mastered: m };
}
function cleanActivity(b) {
  if (!b || typeof b !== 'object' || b.example === true || !named(b.title)) return null;
  return { createdAt: num(b.createdAt), updatedAt: num(b.updatedAt), childIds: ids(b.childIds), goalIds: ids(b.goalIds), photos: Math.min(ids(b.photoIds).length, MAX_PHOTOS) };
}
function cleanProfile(b) {
  if (!b || typeof b !== 'object') return null;
  return { email: typeof b.email === 'string' ? b.email.slice(0, 320) : '', createdAt: num(b.createdAt), lastSeen: num(b.lastSeen) };
}
const stamps = a => [...a.children, ...a.activities].flatMap(r => [r.createdAt, r.updatedAt]);

/* raw: { profiles, children, activities }, each a list of { uid, id, data } */
function buildDataset(raw, tierKeys = ['KO', 'L4', 'L6']) {
  const map = new Map();
  const acc = uid => {
    if (!map.has(uid)) map.set(uid, { uid, email: '', hasProfile: false, signupAt: 0, signupApprox: false, lastSeen: 0, lastActive: 0, children: [], activities: [] });
    return map.get(uid);
  };
  for (const r of raw.profiles || []) {
    const p = cleanProfile(r.data);
    if (!p) continue;
    Object.assign(acc(r.uid), { hasProfile: true, email: p.email, signupAt: p.createdAt, lastSeen: p.lastSeen });
  }
  for (const r of raw.children || []) { const c = cleanChild(r.data, tierKeys); if (c) acc(r.uid).children.push({ id: r.id, ...c }); }
  for (const r of raw.activities || []) { const x = cleanActivity(r.data); if (x) acc(r.uid).activities.push({ id: r.id, ...x }); }
  for (const a of map.values()) {
    a.children.sort((x, y) => x.createdAt - y.createdAt || (x.id < y.id ? -1 : 1));
    a.lastActive = Math.max(a.lastSeen, maxOf(stamps(a)));
    if (!a.signupAt) {
      const created = [...a.children, ...a.activities].map(r => r.createdAt).filter(Boolean);
      if (created.length) { a.signupAt = created.reduce((m, v) => v < m ? v : m); a.signupApprox = true; }
    }
  }
  return [...map.values()];
}

return { DAY, buildDataset };
})();
if (typeof module !== 'undefined') module.exports = AdminStats;
```

- [ ] **Step 4: Run test to verify it passes**

Run: `node --test "tests/*.test.mjs"`
Expected: PASS, 6 tests.

- [ ] **Step 5: Commit**

```bash
git add src/admin-stats.js tests/admin-stats.test.mjs
git commit -m "Admin stats: clean records and build accounts (names dropped)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 2: Stats module — periods, Overzicht, Groei, Gebruik

**Files:**
- Modify: `src/admin-stats.js` (add functions before the `return`, extend the returned object)
- Test: `tests/admin-stats.test.mjs` (append)

**Interfaces:**
- Consumes: `buildDataset`, `DAY`, `Account` from Task 1.
- Produces:
  - `weekStart(ts) → number`: Monday 00:00 local time.
  - `monthStart(ts) → number`: the 1st of the month, 00:00 local time.
  - `periodStarts(period: 'weeks'|'months'|'all', now, earliest = 0) → number[]`: weeks gives 12 week starts and months gives 12 month starts, both ending with the current one. `all` gives month starts from `monthStart(earliest || now)` up to the current month.
  - `isActive(account, now, days) → boolean`: `lastActive > 0 && now - lastActive <= days * DAY`.
  - `isInactive(account, now) → boolean`: `!lastActive || now - lastActive > 90 * DAY`.
  - `activeWeekly(accounts, now) → [{ start, count }]`: 12 weeks.
  - `overview(accounts, now) → { accounts, accountsThisMonth, active30, active30Pct, children, childrenThisMonth, activities, activitiesThisMonth, activeWeekly, recent: [{ uid, email, lastActive }] }`, with at most 8 recent accounts.
  - `growth(accounts, period, now) → { totals: { accounts, children, activities, photos }, rows: [{ start, accounts, children, activities, total }] }`
  - `usage(accounts, now) → { active7, active30, inactive90, neverLogged, funnel: [{ key: 'account'|'child'|'activity'|'ten', count, pct }], activeWeekly }`
  - `pct(n, d) → number`: rounded percentage, 0 when `d` is 0.

- [ ] **Step 1: Write the failing tests**

Append to `tests/admin-stats.test.mjs`:

```js
test('weekStart: weeks start on Monday 00:00 local time', () => {
  assert.equal(S.weekStart(new Date(2026, 10, 15, 23, 59).getTime()), new Date(2026, 10, 9).getTime());
  assert.equal(S.weekStart(new Date(2026, 10, 16, 0, 0).getTime()), new Date(2026, 10, 16).getTime());
  assert.equal(S.weekStart(NOW), new Date(2026, 10, 9).getTime());
});

test('periodStarts: 12 weeks, 12 months, or every month since the earliest record', () => {
  const w = S.periodStarts('weeks', NOW);
  assert.equal(w.length, 12);
  assert.equal(w[11], new Date(2026, 10, 9).getTime());
  assert.equal(w[0], new Date(2026, 7, 24).getTime());
  const m = S.periodStarts('months', NOW);
  assert.equal(m.length, 12);
  assert.equal(m[0], new Date(2025, 11, 1).getTime());
  assert.equal(m[11], new Date(2026, 10, 1).getTime());
  assert.equal(S.periodStarts('all', NOW, day(2, 12)).length, 9);
  assert.deepEqual(S.periodStarts('all', NOW, 0), [new Date(2026, 10, 1).getTime()]);
});

test('isActive / isInactive: exact 30- and 90-day edges, and never active', () => {
  assert.equal(S.isActive({ lastActive: NOW - 30 * S.DAY }, NOW, 30), true);
  assert.equal(S.isActive({ lastActive: NOW - 30 * S.DAY - 1 }, NOW, 30), false);
  assert.equal(S.isActive({ lastActive: 0 }, NOW, 30), false);
  assert.equal(S.isInactive({ lastActive: NOW - 90 * S.DAY }, NOW), false);
  assert.equal(S.isInactive({ lastActive: NOW - 90 * S.DAY - 1 }, NOW), true);
  assert.equal(S.isInactive({ lastActive: 0 }, NOW), true);
});

test('overview: tiles, weekly active accounts and recent list', () => {
  const o = S.overview(accounts(), NOW);
  assert.equal(o.accounts, 3);
  assert.equal(o.accountsThisMonth, 1);
  assert.equal(o.active30, 2);
  assert.equal(o.active30Pct, 67);
  assert.equal(o.children, 3);
  assert.equal(o.childrenThisMonth, 0);
  assert.equal(o.activities, 2);
  assert.equal(o.activitiesThisMonth, 0);
  assert.equal(o.activeWeekly.length, 12);
  assert.equal(o.activeWeekly[11].count, 2);
  assert.equal(o.activeWeekly.find(w => w.start === new Date(2026, 9, 26).getTime()).count, 1);
  assert.deepEqual(o.recent.map(r => r.uid), ['u1', 'u4', 'u2']);
});

test('growth: new per period, running total and totals', () => {
  const g = S.growth(accounts(), 'months', NOW);
  assert.deepEqual(g.totals, { accounts: 3, children: 3, activities: 2, photos: 26 });
  assert.equal(g.rows.length, 12);
  const at = (y, m) => g.rows.find(r => r.start === new Date(y, m, 1).getTime());
  assert.equal(at(2026, 10).accounts, 1);
  assert.equal(at(2026, 2).accounts, 1);
  assert.equal(at(2026, 2).children, 1);
  assert.equal(at(2026, 9).activities, 1);
  assert.equal(g.rows[11].total, 3);
  const w = S.growth(accounts(), 'weeks', NOW);
  assert.equal(w.rows[0].total, 2);
  assert.equal(w.rows[11].accounts, 1);
  assert.equal(w.rows[11].total, 3);
});

test('usage: active, inactive, never logged and the funnel', () => {
  const u = S.usage(accounts(), NOW);
  assert.equal(u.active7, 2);
  assert.equal(u.active30, 2);
  assert.equal(u.inactive90, 1);
  assert.equal(u.neverLogged, 1);
  assert.deepEqual(u.funnel.map(f => [f.key, f.count, f.pct]), [['account', 3, 100], ['child', 2, 67], ['activity', 2, 67], ['ten', 0, 0]]);
});

test('overview, growth and usage on an empty platform: zeros, no NaN', () => {
  const o = S.overview([], NOW);
  assert.equal(o.active30Pct, 0);
  assert.equal(o.activeWeekly.every(w => w.count === 0), true);
  assert.deepEqual(S.growth([], 'all', NOW).rows.map(r => r.total), [0]);
  assert.deepEqual(S.usage([], NOW).funnel.map(f => f.pct), [0, 0, 0, 0]);
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `node --test "tests/*.test.mjs"`
Expected: the 7 new tests FAIL with `S.weekStart is not a function` (and similar). The Task 1 tests still pass.

- [ ] **Step 3: Implement**

In `src/admin-stats.js`, insert before `return { DAY, buildDataset };`:

```js
const pct = (n, d) => d ? Math.round(100 * n / d) : 0;
const sum = (arr, f) => arr.reduce((s, x) => s + f(x), 0);

/* ---------- time: weeks start on Monday, everything in local time ---------- */
function weekStart(ts) {
  const d = new Date(ts);
  d.setHours(0, 0, 0, 0);
  d.setDate(d.getDate() - (d.getDay() + 6) % 7);
  return d.getTime();
}
function monthStart(ts) { const d = new Date(ts); return new Date(d.getFullYear(), d.getMonth(), 1).getTime(); }
function periodStarts(period, now, earliest = 0) {
  const out = [];
  if (period === 'weeks') {
    const w = new Date(weekStart(now));
    for (let i = 11; i >= 0; i--) out.push(new Date(w.getFullYear(), w.getMonth(), w.getDate() - 7 * i).getTime());
    return out;
  }
  const n = new Date(now);
  if (period === 'months') {
    for (let i = 11; i >= 0; i--) out.push(new Date(n.getFullYear(), n.getMonth() - i, 1).getTime());
    return out;
  }
  const e = new Date(monthStart(earliest || now));
  for (let d = e; d.getTime() <= now; d = new Date(d.getFullYear(), d.getMonth() + 1, 1)) out.push(d.getTime());
  return out;
}
/* index of the period ts falls in; -1 before the first; anything after now counts in the last */
function bucketOf(starts, ts) {
  if (!ts || ts < starts[0]) return -1;
  let i = starts.length - 1;
  while (starts[i] > ts) i--;
  return i;
}

/* ---------- activity ---------- */
const isActive = (a, now, days) => a.lastActive > 0 && now - a.lastActive <= days * DAY;
const isInactive = (a, now) => !a.lastActive || now - a.lastActive > 90 * DAY;

/* An account is active in a week when it created or changed a record that week, or opened the app (lastSeen). */
function activeWeekly(accounts, now) {
  const starts = periodStarts('weeks', now);
  const counts = starts.map(() => 0);
  for (const a of accounts) {
    const weeks = new Set([...stamps(a), a.lastSeen].map(ts => bucketOf(starts, ts)).filter(i => i >= 0));
    for (const i of weeks) counts[i]++;
  }
  return starts.map((start, i) => ({ start, count: counts[i] }));
}

/* ---------- tabs ---------- */
function overview(accounts, now) {
  const ms = monthStart(now);
  const kids = accounts.flatMap(a => a.children), acts = accounts.flatMap(a => a.activities);
  const active30 = accounts.filter(a => isActive(a, now, 30)).length;
  return {
    accounts: accounts.length, accountsThisMonth: accounts.filter(a => a.signupAt >= ms).length,
    active30, active30Pct: pct(active30, accounts.length),
    children: kids.length, childrenThisMonth: kids.filter(c => c.createdAt >= ms).length,
    activities: acts.length, activitiesThisMonth: acts.filter(x => x.createdAt >= ms).length,
    activeWeekly: activeWeekly(accounts, now),
    recent: accounts.filter(a => a.lastActive).sort((x, y) => y.lastActive - x.lastActive).slice(0, 8)
      .map(a => ({ uid: a.uid, email: a.email, lastActive: a.lastActive })),
  };
}

function growth(accounts, period, now) {
  const kids = accounts.flatMap(a => a.children), acts = accounts.flatMap(a => a.activities);
  const firsts = [...accounts.map(a => a.signupAt), ...kids.map(c => c.createdAt), ...acts.map(x => x.createdAt)].filter(Boolean);
  const starts = periodStarts(period, now, firsts.length ? firsts.reduce((m, v) => v < m ? v : m) : 0);
  const rows = starts.map(start => ({ start, accounts: 0, children: 0, activities: 0, total: 0 }));
  let before = 0;
  for (const a of accounts) { const i = bucketOf(starts, a.signupAt); if (i >= 0) rows[i].accounts++; else if (a.signupAt) before++; }
  for (const c of kids) { const i = bucketOf(starts, c.createdAt); if (i >= 0) rows[i].children++; }
  for (const x of acts) { const i = bucketOf(starts, x.createdAt); if (i >= 0) rows[i].activities++; }
  let total = before;
  for (const r of rows) { total += r.accounts; r.total = total; }
  return { totals: { accounts: accounts.length, children: kids.length, activities: acts.length, photos: sum(acts, x => x.photos) }, rows };
}

function usage(accounts, now) {
  const all = accounts.length;
  const step = (key, count) => ({ key, count, pct: pct(count, all) });
  return {
    active7: accounts.filter(a => isActive(a, now, 7)).length,
    active30: accounts.filter(a => isActive(a, now, 30)).length,
    inactive90: accounts.filter(a => isInactive(a, now)).length,
    neverLogged: accounts.filter(a => !a.activities.length).length,
    funnel: [step('account', all), step('child', accounts.filter(a => a.children.length).length),
      step('activity', accounts.filter(a => a.activities.length).length), step('ten', accounts.filter(a => a.activities.length >= 10).length)],
    activeWeekly: activeWeekly(accounts, now),
  };
}
```

Replace the return line with:

```js
return { DAY, pct, buildDataset, weekStart, monthStart, periodStarts, isActive, isInactive, activeWeekly, overview, growth, usage };
```

Note: the `before` count in `growth` gives the weeks view its starting total of 2: accounts u1 (March) and u2 (June) signed up before the first of the 12 weeks.

- [ ] **Step 4: Run tests to verify they pass**

Run: `node --test "tests/*.test.mjs"`
Expected: PASS, 13 tests.

- [ ] **Step 5: Commit**

```bash
git add src/admin-stats.js tests/admin-stats.test.mjs
git commit -m "Admin stats: periods, overview, growth and usage

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 3: Stats module — Inhoud, Accounts, relative days

**Files:**
- Modify: `src/admin-stats.js`
- Test: `tests/admin-stats.test.mjs` (append)

**Interfaces:**
- Consumes: everything from Tasks 1–2.
- Produces:
  - `content(accounts, goals, subjectKeys, tierKeys) → { bySubject: [{ key, count, pct }], byTier: [{ key, count, pct }], photos: { total, withPhotoPct, avgGoals }, topGoals: [GoalRow & { activities, mastered }], neverLinked: GoalRow[] }`
    - `goals` is the app's `BUILTIN_GOALS`: `[{ id, subject, tier, code, description, … }]`.
    - `GoalRow = { id, subject, tier, code, description }`.
    - Unknown goal ids count under subject key `'?'`. `bySubject` leaves out zero rows and is sorted by count, highest first. `'?'` always comes last. `topGoals` has at most 10 rows.
  - `accountRows(accounts, { query = '', filter = 'all', sort = 'lastActive', dir = 'desc' } = {}, now) → Row[]`, where `Row = { uid, email, hasProfile, signupAt, signupApprox, lastActive, children, activities, photos }`.
    - `filter`: `'all'`, `'active'` (active in the last 30 days) or `'inactive'` (more than 90 days).
    - `sort`: `'email'`, `'signupAt'`, `'lastActive'`, `'children'`, `'activities'` or `'photos'`. Ties are broken by uid, ascending.
  - `accountDetail(account) → { uid, lastChange, kids: [{ label, tier, activities, mastered }] }`
  - `relDays(ts, now) → string`: `'—'`, `'vandaag'`, `'gisteren'`, `'N d geleden'` (under 31 days), `'N mnd geleden'` (under 365 days) or `'N j geleden'`.

- [ ] **Step 1: Write the failing tests**

Append to `tests/admin-stats.test.mjs`:

```js
const GOALS = [
  { id: 'b-NL-1.1.2', subject: 'NL', tier: 'KO', code: '1.1.2', description: 'Luistert' },
  { id: 'b-WK-2.1', subject: 'WK', tier: 'KO', code: '2.1', description: 'Telt' },
];
const SUBJECT_KEYS = ['NL', 'WK', 'WT'], TIER_KEYS = ['KO', 'L4', 'L6'];

test('content: links per subject with unknown goals as "?", tiers, photos, top and never-linked goals', () => {
  const c = S.content(accounts(), GOALS, SUBJECT_KEYS, TIER_KEYS);
  assert.deepEqual(c.bySubject, [{ key: 'NL', count: 1, pct: 50 }, { key: '?', count: 1, pct: 50 }]);
  assert.deepEqual(c.byTier, [{ key: 'KO', count: 1, pct: 33 }, { key: 'L4', count: 1, pct: 33 }, { key: 'L6', count: 1, pct: 33 }]);
  assert.deepEqual(c.photos, { total: 26, withPhotoPct: 100, avgGoals: 1 });
  assert.deepEqual(c.topGoals, [{ id: 'b-NL-1.1.2', subject: 'NL', tier: 'KO', code: '1.1.2', description: 'Luistert', activities: 1, mastered: 1 }]);
  assert.deepEqual(c.neverLinked.map(g => g.id), ['b-WK-2.1']);
});

test('content on an empty platform: zeros, every goal never linked', () => {
  const c = S.content([], GOALS, SUBJECT_KEYS, TIER_KEYS);
  assert.deepEqual(c.bySubject, []);
  assert.deepEqual(c.byTier.map(t => [t.count, t.pct]), [[0, 0], [0, 0], [0, 0]]);
  assert.deepEqual(c.photos, { total: 0, withPhotoPct: 0, avgGoals: 0 });
  assert.equal(c.neverLinked.length, 2);
});

test('accountRows: default sort, case-insensitive search on email and uid, filters', () => {
  const a = accounts();
  assert.deepEqual(S.accountRows(a, {}, NOW).map(r => r.uid), ['u1', 'u4', 'u2']);
  assert.deepEqual(S.accountRows(a, { query: 'EXAMPLE' }, NOW).map(r => r.uid), ['u1']);
  assert.deepEqual(S.accountRows(a, { query: ' u2 ' }, NOW).map(r => r.uid), ['u2']);
  assert.deepEqual(S.accountRows(a, { filter: 'active' }, NOW).map(r => r.uid), ['u1', 'u4']);
  assert.deepEqual(S.accountRows(a, { filter: 'inactive' }, NOW).map(r => r.uid), ['u2']);
});

test('accountRows: sorting with ties broken by uid, email falls back to uid', () => {
  const a = accounts();
  assert.deepEqual(S.accountRows(a, { sort: 'activities' }, NOW).map(r => r.uid), ['u1', 'u2', 'u4']);
  assert.deepEqual(S.accountRows(a, { sort: 'activities', dir: 'asc' }, NOW).map(r => r.uid), ['u4', 'u1', 'u2']);
  assert.deepEqual(S.accountRows(a, { sort: 'email', dir: 'asc' }, NOW).map(r => r.uid), ['u1', 'u2', 'u4']);
  const u2 = S.accountRows(a, { query: 'u2' }, NOW)[0];
  assert.deepEqual(u2, { uid: 'u2', email: '', hasProfile: false, signupAt: day(5, 2), signupApprox: true, lastActive: day(7, 3), children: 1, activities: 1, photos: 24 });
});

test('accountDetail: children as Kind 1, 2… in creation order with counts, never names', () => {
  const d = S.accountDetail(accounts()[0]);
  assert.equal(d.uid, 'u1');
  assert.equal(d.lastChange, day(10, 1));
  assert.deepEqual(d.kids, [
    { label: 'Kind 1', tier: 'KO', activities: 1, mastered: 0 },
    { label: 'Kind 2', tier: 'L4', activities: 1, mastered: 1 },
  ]);
});

test('relDays: today, yesterday across midnight, days, months, years, never', () => {
  assert.equal(S.relDays(day(10, 14, 8), NOW), 'vandaag');
  assert.equal(S.relDays(day(10, 13, 23), NOW), 'gisteren');
  assert.equal(S.relDays(day(10, 4), NOW), '10 d geleden');
  assert.equal(S.relDays(day(7, 3), NOW), '3 mnd geleden');
  assert.equal(S.relDays(day(0, 1, 12, 2025), NOW), '1 j geleden');
  assert.equal(S.relDays(0, NOW), '—');
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `node --test "tests/*.test.mjs"`
Expected: the 6 new tests FAIL with `S.content is not a function` (and similar).

- [ ] **Step 3: Implement**

In `src/admin-stats.js`, insert before the `return`:

```js
const goalRow = g => ({ id: g.id, subject: g.subject, tier: g.tier, code: g.code, description: g.description });

function content(accounts, goals, subjectKeys, tierKeys) {
  const byId = new Map(goals.map(g => [g.id, g]));
  const kids = accounts.flatMap(a => a.children), acts = accounts.flatMap(a => a.activities);
  const subj = new Map(subjectKeys.map(k => [k, 0]));
  const actsPerGoal = new Map(), masteredPerGoal = new Map();
  let links = 0, unknown = 0;
  for (const x of acts) for (const id of x.goalIds) {
    links++;
    const g = byId.get(id);
    if (g && subj.has(g.subject)) subj.set(g.subject, subj.get(g.subject) + 1); else unknown++;
    actsPerGoal.set(id, (actsPerGoal.get(id) || 0) + 1);
  }
  for (const c of kids) for (const id of c.mastered) masteredPerGoal.set(id, (masteredPerGoal.get(id) || 0) + 1);
  const bySubject = [...subj].filter(([, n]) => n).sort((x, y) => y[1] - x[1]).map(([key, count]) => ({ key, count, pct: pct(count, links) }));
  if (unknown) bySubject.push({ key: '?', count: unknown, pct: pct(unknown, links) });
  return {
    bySubject,
    byTier: tierKeys.map(key => { const count = kids.filter(c => c.tier === key).length; return { key, count, pct: pct(count, kids.length) }; }),
    photos: { total: sum(acts, x => x.photos), withPhotoPct: pct(acts.filter(x => x.photos).length, acts.length), avgGoals: acts.length ? links / acts.length : 0 },
    topGoals: [...actsPerGoal].filter(([id]) => byId.has(id)).sort((x, y) => y[1] - x[1] || (x[0] < y[0] ? -1 : 1)).slice(0, 10)
      .map(([id, n]) => ({ ...goalRow(byId.get(id)), activities: n, mastered: masteredPerGoal.get(id) || 0 })),
    neverLinked: goals.filter(g => !actsPerGoal.has(g.id)).map(goalRow),
  };
}

function accountRows(accounts, { query = '', filter = 'all', sort = 'lastActive', dir = 'desc' } = {}, now) {
  const q = query.trim().toLowerCase();
  const rows = accounts
    .filter(a => filter === 'active' ? isActive(a, now, 30) : filter === 'inactive' ? isInactive(a, now) : true)
    .filter(a => !q || a.email.toLowerCase().includes(q) || a.uid.toLowerCase().includes(q))
    .map(a => ({ uid: a.uid, email: a.email, hasProfile: a.hasProfile, signupAt: a.signupAt, signupApprox: a.signupApprox, lastActive: a.lastActive,
      children: a.children.length, activities: a.activities.length, photos: sum(a.activities, x => x.photos) }));
  const sign = dir === 'asc' ? 1 : -1;
  const key = sort === 'email' ? (x, y) => (x.email || x.uid).localeCompare(y.email || y.uid, 'nl', { sensitivity: 'base' }) : (x, y) => x[sort] - y[sort];
  return rows.sort((x, y) => sign * key(x, y) || (x.uid < y.uid ? -1 : x.uid > y.uid ? 1 : 0));
}

function accountDetail(a) {
  return {
    uid: a.uid,
    lastChange: maxOf(stamps(a)),
    kids: a.children.map((c, i) => ({ label: `Kind ${i + 1}`, tier: c.tier, activities: a.activities.filter(x => x.childIds.includes(c.id)).length, mastered: c.mastered.length })),
  };
}

function relDays(ts, now) {
  if (!ts) return '—';
  const midnight = t => { const d = new Date(t); return new Date(d.getFullYear(), d.getMonth(), d.getDate()).getTime(); };
  const d = Math.max(0, Math.round((midnight(now) - midnight(ts)) / DAY));
  if (d === 0) return 'vandaag';
  if (d === 1) return 'gisteren';
  if (d < 31) return `${d} d geleden`;
  if (d < 365) return `${Math.floor(d / 30)} mnd geleden`;
  return `${Math.floor(d / 365)} j geleden`;
}
```

Replace the return line with:

```js
return { DAY, pct, buildDataset, weekStart, monthStart, periodStarts, isActive, isInactive, activeWeekly, overview, growth, usage, content, accountRows, accountDetail, relDays };
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `node --test "tests/*.test.mjs"`
Expected: PASS, 19 tests.

- [ ] **Step 5: Commit**

```bash
git add src/admin-stats.js tests/admin-stats.test.mjs
git commit -m "Admin stats: content, account rows and detail, relative days

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 4: Firestore rules and the profile record in the app

**Files:**
- Modify: `firestore.rules` (whole file)
- Modify: `src/doelenboek.html`: `enterAccount()` (around line 1361), the delete loop in `deleteAccountDialog()` (around line 1451), and a new `writeProfile()` placed right after `leaveAccount()`.

**Interfaces:**
- Produces: the document `users/{uid}/profile/main` = `{ email: string, createdAt: number, lastSeen: number }` (read by the admin page in Task 6). It also produces the `isAdmin()` function in `firestore.rules`, whose uid literal `tools/build.py` reads in Task 5 using the regex `request\.auth\.uid == '([^']*)'`.

- [ ] **Step 1: Get the owner uid from the user**

Ask the user for their account's uid: Firebase console → Authentication → Users → the "User UID" column of their own account. Until they answer, use the literal `OWNER_UID`. The build treats that as "no admin yet".

- [ ] **Step 2: Replace `firestore.rules`**

```
rules_version = '2';

// Doelenboek: every account can only read and write its own data under users/{uid}/...
// One admin account (isAdmin) may also read, never write, every account's children, activities and profile, for /admin/.
// Paste this into Firebase console → Firestore Database → Rules, then Publish.
service cloud.firestore {
  match /databases/{database}/documents {

    function isOwner(uid) {
      return request.auth != null && request.auth.uid == uid;
    }

    // The site owner's uid (Firebase console → Authentication). tools/build.py reads it from here for /admin/.
    function isAdmin() {
      return request.auth != null && request.auth.uid == 'OWNER_UID';
    }

    match /users/{uid}/{collection}/{docId} {
      allow read, delete: if isOwner(uid)
        && collection in ['children', 'activities', 'goals', 'photos', 'profile'];

      // 'goals' only held goals parents once added themselves; it can still be read and cleared.
      allow create, update: if isOwner(uid)
        && collection in ['children', 'activities', 'photos']
        && request.resource.data.size() <= 20
        && (collection != 'photos' || request.resource.data.data.size() <= 400000);
    }

    // One small record per account for /admin/: email, sign-up date and the last day the app was opened.
    match /users/{uid}/profile/{docId} {
      allow create, update: if isOwner(uid) && docId == 'main'
        && request.resource.data.keys().hasOnly(['email', 'createdAt', 'lastSeen'])
        && request.resource.data.keys().hasAll(['email', 'createdAt', 'lastSeen'])
        && request.resource.data.email == request.auth.token.email
        && request.resource.data.createdAt is number
        && request.resource.data.lastSeen is number;
    }

    // Admin: read-only, across all accounts (collection-group queries from /admin/).
    match /{path=**}/children/{docId}   { allow read: if isAdmin(); }
    match /{path=**}/activities/{docId} { allow read: if isAdmin(); }
    match /{path=**}/profile/{docId}    { allow read: if isAdmin(); }

    // Everything else is closed.
  }
}
```

If the user gave their uid, replace `OWNER_UID` with it.

- [ ] **Step 3: Write the profile on sign-in**

In `src/doelenboek.html`, change `enterAccount` to:

```js
function enterAccount(user) {
  if (fbUser && fbUser.uid === user.uid) return;
  fbUser = user; db = firestoreStore(user.uid);
  mode = 'db'; canWrite = true; canWriteKnown = true;
  resetData(); closeDialog(); render(); subscribeAll();
  readLocalSummary();
  writeProfile(user);
}
```

Directly after the closing `}` of `leaveAccount()`, add:

```js
/* The small users/{uid}/profile/main record the /admin/ page counts with: email, sign-up date and the
   last day this account opened the app. Written at most once a day; a failure never bothers the user. */
async function writeProfile(user) {
  const { F, fs } = fb;
  const ref = F.doc(fs, 'users', user.uid, 'profile', 'main');
  const now = Date.now();
  try {
    const s = await F.getDoc(ref);
    const p = s.exists() ? s.data() : null;
    if (p && p.email === user.email && typeof p.lastSeen === 'number' && new Date(p.lastSeen).toDateString() === new Date(now).toDateString()) return;
    await F.setDoc(ref, { email: user.email || '', createdAt: Date.parse(user.metadata.creationTime) || now, lastSeen: now });
  } catch (e) { console.warn('doelenboek: profile not saved', e && e.code); }
}
```

- [ ] **Step 4: Delete the profile with the account**

In `deleteAccountDialog()`, change:

```js
    /* 'goals' holds goals parents could once add themselves; cleared along with the rest */
    for (const c of [...COLS, 'goals', 'photos']) {
```

to:

```js
    /* 'goals' holds goals parents could once add themselves; cleared along with the rest, as is the admin profile */
    for (const c of [...COLS, 'goals', 'photos', 'profile']) {
```

- [ ] **Step 5: Check the app still builds and runs locally**

Run: `python tools/build.py src/doelenboek.html index.html firebase-config.json`
Expected: `wrote index.html (…)` and `wrote N public files`, with no error.

Run: `python tools/serve.py --port 8000` (in the background), open `http://localhost:8000/`, and add and delete a test child. Local mode has no Firebase, so `writeProfile` isn't called and nothing changes visibly. Check the browser console for errors: there must be none. Stop the server.

The live check (profile written, account deletion removes it) happens in Task 10, after the rules are published.

- [ ] **Step 6: Commit**

```bash
git add firestore.rules src/doelenboek.html
git commit -m "Rules: admin read access and the profile record; app writes the profile once a day

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 5: Build and preview for `/admin/`

**Files:**
- Create: `src/admin.html` (a minimal shell here; Task 6 fills in the full page)
- Modify: `tools/build.py` (add `goals_js`, `js_block`, `admin_uid`, `build_admin`, `ADMIN_SRC`, `RULES`; use `goals_js` in `build`; main writes `admin/index.html`)
- Modify: `tools/serve.py` (route `/admin`)
- Modify: `tools/public.py`: `robots()`
- Test: `tests/test_build_admin.py`

**Interfaces:**
- Consumes: `firestore.rules` from Task 4, and `src/admin-stats.js` from Tasks 1–3.
- Produces: `build_admin(src, app_src, firebase_config=None, rules=RULES) → str`. It fills these exact placeholders in `src/admin.html`, each of which must appear exactly once:
  - `const SUBJECTS = [];`
  - `const TIERS = [];`
  - `const BUILTIN_GOALS = [];`
  - `const FIREBASE_CONFIG = null;`, filled only when a config file is given
  - `const ADMIN_UID = null;`, filled only when the rules hold a real uid
  - `<script src="admin-stats.js"></script>`
  - the three `<link rel="stylesheet" …>` lines (via `inline_styles`)
  - the page must contain `<header class="top">`

- [ ] **Step 1: Write the failing test**

Create `tests/test_build_admin.py`:

```python
"""Tests for the /admin/ build. Run: python -m unittest discover -s tests"""
import sys, tempfile, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'tools'))
import build, public  # noqa: E402

APP = ROOT / 'src' / 'doelenboek.html'


def rules_with(uid):
    f = tempfile.NamedTemporaryFile('w', suffix='.rules', delete=False, encoding='utf-8')
    f.write(f"function isAdmin() {{ return request.auth != null && request.auth.uid == '{uid}'; }}\n")
    f.close()
    return Path(f.name)


class BuildAdmin(unittest.TestCase):
    def test_fills_every_placeholder_and_inlines_stats(self):
        page = build.build_admin(build.ADMIN_SRC, APP, None, rules_with('AbCdEf1234567890xyz'))
        self.assertIn('<meta name="robots" content="noindex, nofollow">', page)
        self.assertIn('const AdminStats = ', page)
        self.assertIn("{ key: 'NL'", page)
        self.assertIn("badge: { nl: 'Lager LJ 1-4'", page)
        self.assertIn('"id": "b-NL-', page)
        self.assertIn('const ADMIN_UID = "AbCdEf1234567890xyz";', page)
        for left in ('const SUBJECTS = [];', 'const TIERS = [];', 'const BUILTIN_GOALS = [];', '<script src="admin-stats.js">', '<link rel="stylesheet"'):
            self.assertNotIn(left, page)

    def test_fonts_point_one_folder_up(self):
        page = build.build_admin(build.ADMIN_SRC, APP, None, rules_with('OWNER_UID'))
        self.assertIn('url("../fonts/', page)
        self.assertNotIn('url("fonts/', page)

    def test_placeholder_uid_means_no_admin(self):
        page = build.build_admin(build.ADMIN_SRC, APP, None, rules_with('OWNER_UID'))
        self.assertIn('const ADMIN_UID = null;', page)

    def test_firebase_config_is_filled_in(self):
        page = build.build_admin(build.ADMIN_SRC, APP, ROOT / 'firebase-config.json', rules_with('OWNER_UID'))
        self.assertIn('"projectId": "doelenboek-e78ca"', page)

    def test_robots_keeps_crawlers_out_of_admin(self):
        self.assertIn('Disallow: /admin/', public.robots())


if __name__ == '__main__':
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest discover -s tests -v`
Expected: FAIL/ERROR with `AttributeError: module 'build' has no attribute 'build_admin'`.

- [ ] **Step 3: Create the minimal admin shell**

Create `src/admin.html` (Task 6 replaces the script body with the full page):

```html
<title>doelenboek.be admin</title>
<!-- tools/build.py builds this into admin/index.html; the stylesheets and admin-stats.js are inlined -->
<link rel="stylesheet" href="design/tokens.css">
<link rel="stylesheet" href="design/app.css">
<link rel="stylesheet" href="core.css">
<script>let t = 'light'; try { if (localStorage.getItem('doelenboek.theme') === 'dark') t = 'dark'; } catch (e) {} document.documentElement.dataset.theme = t;</script>
<header class="top">
  <div class="top-inner">
    <div class="brand"><b>doelenboek.be</b>&nbsp;<span class="adm-tag">admin</span></div>
    <nav class="tabs" id="tabs" aria-label="Admin"></nav>
    <div class="top-right">
      <span class="status" id="status"></span>
      <button class="btn small" id="refresh-btn" type="button" hidden>Vernieuwen</button>
      <button class="btn small ghost" id="out-btn" type="button" hidden>Afmelden</button>
    </div>
  </div>
</header>
<main id="main"><p class="loading">Gegevens laden…</p></main>
<script src="admin-stats.js"></script>
<script>
(() => {
'use strict';
const SUBJECTS = [];
const TIERS = [];
const BUILTIN_GOALS = [];
const FIREBASE_CONFIG = null;
const ADMIN_UID = null;
})();
</script>
```

- [ ] **Step 4: Implement the build**

In `tools/build.py`, after `LAGER_TIERS`/`GOAL_FIELDS`, add:

```python
ADMIN_SRC = ROOT / 'src' / 'admin.html'
RULES = ROOT / 'firestore.rules'
```

After `subject_keys_of()`, add:

```python
def goals_js(subject_keys):
    """The built-in goals as a JavaScript array literal, in the order of the app's subjects."""
    goals = sorted(load_goals(subject_keys), key=lambda g: subject_keys.index(g["subject"]))  # stable: keeps file order within a subject
    return json.dumps(goals, ensure_ascii=False, indent=1).replace('</', '<\\/')


def js_block(text, name):
    """The `const NAME = [ ... ];` list from the app source, word for word, so the admin page shares it."""
    start = text.index(f'const {name} = [')
    return text[start:text.index('\n];', start) + 3]


def admin_uid(rules):
    """The uid in isAdmin() of firestore.rules, or None while it still holds the OWNER_UID placeholder."""
    m = re.search(r"request\.auth\.uid == '([^']*)'", Path(rules).read_text(encoding='utf-8'))
    uid = m.group(1) if m else ''
    return uid if re.fullmatch(r'[A-Za-z0-9]{10,128}', uid) and uid != 'OWNER_UID' else None


def build_admin(src, app_src, firebase_config=None, rules=RULES):
    """The /admin/ page as a string: src/admin.html with the app's subjects, tiers, goals and styles,
    admin-stats.js and the Firebase config inlined. Raises BuildError for a mistake in an input file."""
    src, app_src = Path(src).resolve(), Path(app_src).resolve()
    app_text = app_src.read_text(encoding='utf-8')
    text = src.read_text(encoding='utf-8')

    text = fill(text, 'const SUBJECTS = [];', js_block(app_text, 'SUBJECTS'), 'subjects')
    text = fill(text, 'const TIERS = [];', js_block(app_text, 'TIERS'), 'tiers')
    text = fill(text, 'const BUILTIN_GOALS = [];', 'const BUILTIN_GOALS = ' + goals_js(subject_keys_of(app_text)) + ';', 'goals')
    uid = admin_uid(rules)
    if uid:
        text = fill(text, 'const ADMIN_UID = null;', 'const ADMIN_UID = ' + json.dumps(uid) + ';', 'admin uid')
    if firebase_config:
        cfg = json.loads(Path(firebase_config).read_text(encoding='utf-8'))
        text = fill(text, 'const FIREBASE_CONFIG = null;', 'const FIREBASE_CONFIG = ' + json.dumps(cfg, ensure_ascii=False) + ';', 'Firebase config')

    stats_path = src.parent / 'admin-stats.js'
    stats = stats_path.read_text(encoding='utf-8').rstrip()
    if '</script' in stats.lower():
        fail(stats_path.relative_to(ROOT), 'may not contain "</script"')
    text = fill(text, '<script src="admin-stats.js"></script>', f'<script>\n{stats}\n</script>', 'admin-stats.js')

    # the page lives one folder down, at admin/index.html; the fonts are at fonts/ in the site root
    text = inline_styles(text, src.parent).replace('url("fonts/', 'url("../fonts/')
    i = text.index('<header class="top">')
    head, body = text[:i].rstrip(), text[i:].rstrip()

    return f"""<!doctype html>
<html lang="nl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="robots" content="noindex, nofollow">
<link rel="icon" href="{favicon_uri(src.parent / 'design' / 'favicon.svg')}">
{head}
</head>
<body>
{body}
</body>
</html>
"""
```

In `build()`, replace the two lines

```python
    goals = sorted(load_goals(subject_keys), key=lambda g: subject_keys.index(g["subject"]))  # stable: keeps file order within a subject
    goals_js = json.dumps(goals, ensure_ascii=False, indent=1).replace('</', '<\\/')
    text = fill(text, 'const BUILTIN_GOALS = [];', 'const BUILTIN_GOALS = ' + goals_js + ';', 'goals')
```

with

```python
    text = fill(text, 'const BUILTIN_GOALS = [];', 'const BUILTIN_GOALS = ' + goals_js(subject_keys) + ';', 'goals')
```

Replace the whole `if __name__ == '__main__':` block with:

```python
if __name__ == '__main__':
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    config = sys.argv[3] if len(sys.argv) > 3 else None
    try:
        page = build(sys.argv[1], config)
        admin = build_admin(ADMIN_SRC, sys.argv[1], config)
    except BuildError as e:
        sys.exit(str(e))
    out = sys.argv[2]
    open(out, 'w', encoding='utf-8', newline='\n').write(page)
    out_dir = Path(out).resolve().parent
    copy_fonts(sys.argv[1], out_dir)
    print(f'wrote {out} ({len(page.encode("utf-8")):,} bytes)')
    (out_dir / 'admin').mkdir(exist_ok=True)
    (out_dir / 'admin' / 'index.html').write_text(admin, encoding='utf-8', newline='\n')
    print(f'wrote admin/index.html ({len(admin.encode("utf-8")):,} bytes)')
    if not admin_uid(RULES):
        print('note: firestore.rules has no admin uid yet (OWNER_UID), so /admin/ shows "Geen toegang" to everyone', file=sys.stderr)
    src = Path(sys.argv[1]).resolve()
    written = public.write_site(out_dir, src.parent / 'design', DOELEN_DIR, subject_keys_of(src.read_text(encoding='utf-8')))
    print(f'wrote {len(written)} public files (pages, robots.txt, sitemap.xml, llms.txt, ...)')
```

Also add `admin/index.html` to the module docstring list: `- the admin page src/admin.html is built to admin/index.html next to OUT.html (see build_admin)`.

- [ ] **Step 5: robots.txt**

In `tools/public.py`, change `robots()` to:

```python
def robots():
    return f"""# Doelenboek welcomes search engines and AI assistants: everything public may be crawled,
# indexed, quoted and used to answer questions. The app's own data sits behind a login and is
# never part of the pages. /admin/ is the owner's private page.
User-agent: *
Allow: /
Disallow: /admin/

Sitemap: {SITE}/sitemap.xml
"""
```

- [ ] **Step 6: Preview route**

In `tools/serve.py`, change the import line to:

```python
from build import ROOT, DOELEN_DIR, ADMIN_SRC, BuildError, build, build_admin, animal_symbols, subject_keys_of  # noqa: E402
```

In `do_GET`, after the `if path in ('/', '/index.html'):` branch, add:

```python
            elif path in ('/admin', '/admin/', '/admin/index.html'):
                body, status = build_admin(ADMIN_SRC, SRC, CONFIG if self.live else None), 200
```

Add `  http://localhost:8000/admin/     the admin dashboard (sample data unless --live)` to the docstring URL list.

- [ ] **Step 7: Run tests to verify they pass**

Run: `python -m unittest discover -s tests -v`
Expected: PASS, 5 tests.
Run: `node --test "tests/*.test.mjs"`
Expected: PASS, 19 tests. (the glob only matches the `.mjs` file)

- [ ] **Step 8: Commit**

```bash
git add src/admin.html tools/build.py tools/serve.py tools/public.py tests/test_build_admin.py
git commit -m "Build /admin/ from src/admin.html with the app's subjects, tiers, goals and styles

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 6: Admin page — shell, sign-in, loading, demo data, Overzicht

**Files:**
- Modify: `src/admin.html` (replace the whole file)

**Interfaces:**
- Consumes: `AdminStats.{buildDataset, overview, relDays}` and the build placeholders from Task 5.
- Produces, used by Tasks 7–8:
  - The module-level `state` object: `{ view, err, accounts, loadedAt, demo, growthPeriod, subjOpen, showNever, q, filter, sort, dir, open }`.
  - Helpers: `n(v)`, `esc(s)`, `fmtDate(ts)`, `subjName(k)`, `subjColor(k)`, `tierName(k)`, `tile(value, label, sub)`, `colChart(rows, period)` where `rows = [{ start, value, title }]`, `barList(items, cls)` where `items = [{ label, value, pct, color }]`, `section(title, inner, aside)`.
  - `VIEWS`, an object mapping tab key to a render function. Tasks 7–8 replace the entries for `groei`, `gebruik`, `inhoud` and `accounts`.
  - `ACTIONS`, an object mapping `data-action` to `(el) => void`. Tasks 7–8 add entries.

- [ ] **Step 1: Replace `src/admin.html` with the full page**

```html
<title>doelenboek.be admin</title>
<!-- The owner's dashboard. tools/build.py builds this into admin/index.html; the stylesheets and admin-stats.js are inlined.
     Only the account in firestore.rules (isAdmin) can read other accounts' data; this page only ever shows counts. -->
<link rel="stylesheet" href="design/tokens.css">
<link rel="stylesheet" href="design/app.css">
<link rel="stylesheet" href="core.css">
<script>let t = 'light'; try { if (localStorage.getItem('doelenboek.theme') === 'dark') t = 'dark'; } catch (e) {} document.documentElement.dataset.theme = t;</script>
<style>
/* admin-only pieces; everything else comes from the app's design files */
.adm-tag { opacity: .75; }
.adm { max-width: 1120px; margin: 0 auto; padding: 20px 16px 48px; display: grid; gap: 14px; }
.adm h1 { margin: 0; }
.kpis { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 10px; }
.kpi { padding: 12px 14px; }
.k-n { font-family: var(--f-display); font-size: 1.6rem; line-height: 1.1; font-variant-numeric: tabular-nums; }
.k-l { color: var(--muted); font-size: .82rem; }
.k-s { color: var(--muted); font-size: .76rem; font-family: var(--f-mono); }
.panel { padding: 14px; min-width: 0; }
.panel h3 { margin: 0 0 10px; font-size: .95rem; display: flex; justify-content: space-between; gap: 8px; align-items: baseline; flex-wrap: wrap; }
.panel h3 small { font-weight: 400; color: var(--muted); font-size: .78rem; }
.two { display: grid; grid-template-columns: repeat(auto-fit, minmax(min(100%, 340px), 1fr)); gap: 14px; }
.colchart { display: flex; align-items: flex-end; gap: 3px; height: 110px; border-bottom: 1px solid var(--line); }
.colchart i { flex: 1; min-height: 2px; background: var(--accent); border-radius: 3px 3px 0 0; }
.colchart i.zero { background: var(--line); }
.axis { display: flex; justify-content: space-between; color: var(--muted); font-size: .72rem; margin-top: 4px; font-family: var(--f-mono); }
.tbl-wrap { overflow-x: auto; }
table.t { width: 100%; border-collapse: collapse; font-size: .84rem; }
table.t th { text-align: left; color: var(--muted); font-weight: 600; padding: 6px; border-bottom: 1px solid var(--line); white-space: nowrap; }
table.t th button { background: none; border: 0; padding: 0; font: inherit; color: inherit; cursor: pointer; }
table.t td { padding: 6px; border-bottom: 1px solid var(--line); font-variant-numeric: tabular-nums; }
table.t .r { text-align: right; }
table.t tr.open > td, table.t tr.detail > td { background: var(--surface-2); }
.pill { font-size: .72rem; padding: 1px 7px; border-radius: 99px; background: var(--warn-bg); color: var(--warn-fg); white-space: nowrap; }
.mono { font-family: var(--f-mono); font-size: .76rem; }
.bars.funnel li { grid-template-columns: minmax(0, 11rem) 1fr 3.4rem 2.4rem; }
.acc-tools { display: flex; gap: 8px; flex-wrap: wrap; align-items: center; }
</style>
<header class="top">
  <div class="top-inner">
    <div class="brand"><b>doelenboek.be</b>&nbsp;<span class="adm-tag">admin</span></div>
    <nav class="tabs" id="tabs" aria-label="Admin"></nav>
    <div class="top-right">
      <span class="status" id="status"></span>
      <button class="btn small" id="refresh-btn" type="button" hidden>Vernieuwen</button>
      <button class="btn small ghost" id="out-btn" type="button" hidden>Afmelden</button>
    </div>
  </div>
</header>
<main id="main"><p class="loading">Gegevens laden…</p></main>
<script src="admin-stats.js"></script>
<script>
(() => {
'use strict';
/* Filled in by tools/build.py: the app's subjects, tiers and goals, the Firebase config and the admin uid from firestore.rules. */
const SUBJECTS = [];
const TIERS = [];
const BUILTIN_GOALS = [];
const FIREBASE_CONFIG = null;
const ADMIN_UID = null;
const FIREBASE_SDK = 'https://www.gstatic.com/firebasejs/10.14.1/';

const S = AdminStats;
const SUBJ = Object.fromEntries(SUBJECTS.map(s => [s.key, s]));
const TIER = Object.fromEntries(TIERS.map(x => [x.key, x]));
const TIER_KEYS = TIERS.map(x => x.key);
const TABS = [['overzicht', 'Overzicht'], ['groei', 'Groei'], ['gebruik', 'Gebruik'], ['inhoud', 'Inhoud'], ['accounts', 'Accounts']];

/* ---------- formatting ---------- */
const nf = new Intl.NumberFormat('nl-BE');
const n = v => nf.format(v);
const esc = s => String(s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const dateFmt = new Intl.DateTimeFormat('nl-BE', { day: 'numeric', month: 'short', year: 'numeric' });
const timeFmt = new Intl.DateTimeFormat('nl-BE', { hour: '2-digit', minute: '2-digit' });
const fmtDate = ts => ts ? dateFmt.format(ts) : '—';
const subjName = k => SUBJ[k] ? SUBJ[k].name.nl : 'Onbekend';
const subjColor = k => SUBJ[k] ? `var(--s-${k.toLowerCase()})` : 'var(--muted)';
const tierName = k => TIER[k] ? TIER[k].badge.nl : k;

/* ---------- state ---------- */
const state = { view: 'loading', err: '', accounts: [], loadedAt: 0, demo: false,
  growthPeriod: 'weeks', subjOpen: false, showNever: false,
  q: '', filter: 'all', sort: 'lastActive', dir: 'desc', open: null };
let fb = null;
const $ = id => document.getElementById(id);
const currentTab = () => { const h = location.hash.slice(1); return TABS.some(x => x[0] === h) ? h : 'overzicht'; };

/* ---------- building blocks ---------- */
const tile = (value, label, sub = '') => `<div class="card kpi"><div class="k-n">${value}</div><div class="k-l">${esc(label)}</div>${sub ? `<div class="k-s">${esc(sub)}</div>` : ''}</div>`;
const section = (title, inner, aside = '') => `<section class="adm"><div class="page-head"><div><h1>${esc(title)}</h1></div>${aside}</div>${inner}</section>`;
const axisFmt = { weeks: new Intl.DateTimeFormat('nl-BE', { day: 'numeric', month: 'short' }), months: new Intl.DateTimeFormat('nl-BE', { month: 'short', year: '2-digit' }) };
/* rows: [{ start, value, title }]; one bar per period, three dates under it */
function colChart(rows, period) {
  const max = Math.max(1, ...rows.map(r => r.value));
  const f = axisFmt[period === 'weeks' ? 'weeks' : 'months'];
  const ticks = rows.length > 2 ? [rows[0], rows[Math.floor(rows.length / 2)], rows[rows.length - 1]] : rows;
  return `<div class="colchart" role="img" aria-label="${esc(rows.map(r => r.title).join('; '))}">${rows.map(r =>
    `<i class="${r.value ? '' : 'zero'}" style="height:${Math.round(100 * r.value / max)}%" title="${esc(r.title)}"></i>`).join('')}</div>
    <div class="axis">${ticks.map(r => `<span>${esc(f.format(r.start))}</span>`).join('')}</div>`;
}
/* items: [{ label, value, pct, color }], in the app's .bars style */
const barList = (items, cls = '') => `<ul class="bars ${cls}">${items.map(it =>
  `<li><span class="b-lbl" title="${esc(it.label)}">${esc(it.label)}</span><span class="bar"><i style="width:${it.pct}%;background:${it.color || 'var(--accent)'}"></i></span><span class="b-num">${n(it.value)}</span><span class="b-num">${it.pct}%</span></li>`).join('')}</ul>`;
const weekRows = weekly => weekly.map(w => ({ start: w.start, value: w.count, title: `week van ${dateFmt.format(w.start)}: ${w.count} actief` }));
const who = a => a.email ? esc(a.email) : `<span class="mono">${esc(a.uid.slice(0, 6))}…</span> <span class="pill">geen profiel</span>`;
const FOOTNOTE = '<p class="count-line">Accounts zonder gegevens en zonder profiel zijn niet zichtbaar.</p>';

/* ---------- tabs ---------- */
function overviewView() {
  const now = Date.now(), o = S.overview(state.accounts, now);
  const recent = o.recent.length
    ? `<div class="tbl-wrap"><table class="t"><tr><th>Account</th><th class="r">Laatst actief</th></tr>${o.recent.map(r => `<tr><td>${who(r)}</td><td class="r">${esc(S.relDays(r.lastActive, now))}</td></tr>`).join('')}</table></div>`
    : '<p class="muted">Nog niemand actief.</p>';
  return section('Overzicht', `
    <div class="kpis">
      ${tile(n(o.accounts), 'Accounts', `+${n(o.accountsThisMonth)} deze maand`)}
      ${tile(n(o.active30), 'Actief (30 d)', `${o.active30Pct}% van alle`)}
      ${tile(n(o.children), 'Kinderen', `+${n(o.childrenThisMonth)} deze maand`)}
      ${tile(n(o.activities), 'Activiteiten', `+${n(o.activitiesThisMonth)} deze maand`)}
    </div>
    <div class="two">
      <div class="card panel"><h3>Actieve accounts per week</h3>${colChart(weekRows(o.activeWeekly), 'weeks')}</div>
      <div class="card panel"><h3>Recent actief</h3>${recent}</div>
    </div>${FOOTNOTE}`);
}
/* Tasks 7 and 8 replace these with the real tabs. */
const VIEWS = {
  overzicht: overviewView,
  groei: () => section('Groei', ''),
  gebruik: () => section('Gebruik', ''),
  inhoud: () => section('Inhoud', ''),
  accounts: () => section('Accounts', ''),
};
const ACTIONS = {
  retry: () => fb && fb.auth.currentUser ? load() : start(),
};

/* ---------- screens ---------- */
function loginView() {
  return `<section class="card auth"><div><h1>Admin</h1><p class="lede">Meld je aan met je Doelenboek-account.</p></div>
    <form id="login-form" novalidate>
      <label class="field"><span>E-mail</span><input name="email" type="email" autocomplete="email" inputmode="email" required></label>
      <label class="field"><span>Wachtwoord</span><input name="password" type="password" autocomplete="current-password" required></label>
      <p class="form-error" role="alert">${esc(state.err)}</p>
      <button class="btn primary" type="submit">Aanmelden</button>
    </form></section>`;
}
const noAccessView = () => `<section class="card auth"><div><h1>Geen toegang</h1><p class="lede">Dit account heeft geen beheerdersrechten.</p>
  ${ADMIN_UID ? '' : '<p class="muted">Er staat nog geen beheerder in firestore.rules (OWNER_UID).</p>'}</div></section>`;
const errorView = () => `<section class="adm"><div class="notice"><p>${esc(state.err)}</p><button class="btn small" type="button" data-action="retry">Opnieuw</button></div></section>`;

function render() {
  const dash = state.view === 'dash';
  $('out-btn').hidden = !(fb && fb.auth.currentUser);
  $('refresh-btn').hidden = !dash || state.demo;
  $('status').textContent = dash ? (state.demo ? 'Voorbeeldgegevens' : `Bijgewerkt om ${timeFmt.format(state.loadedAt)}`) : '';
  const tab = currentTab();
  $('tabs').innerHTML = dash ? TABS.map(([k, label]) => `<a href="#${k}"${k === tab ? ' aria-current="page"' : ''}>${label}</a>`).join('') : '';
  $('main').innerHTML = state.view === 'login' ? loginView()
    : state.view === 'noaccess' ? noAccessView()
    : state.view === 'error' ? errorView()
    : dash ? VIEWS[tab]()
    : '<p class="loading">Gegevens laden…</p>';
}

/* ---------- data ---------- */
/* Every record of every account, via collection-group queries (allowed for the admin only by firestore.rules).
   buildDataset drops names, titles and notes, so they never stay in memory. */
async function load() {
  state.view = 'loading'; render();
  const { F, fs } = fb;
  const rows = snap => snap.docs.flatMap(d => {
    const user = d.ref.parent.parent;
    return user && user.parent.id === 'users' ? [{ uid: user.id, id: d.id, data: d.data() }] : [];
  });
  try {
    const [profiles, children, activities] = await Promise.all(['profile', 'children', 'activities'].map(c => F.getDocs(F.collectionGroup(fs, c)).then(rows)));
    state.accounts = S.buildDataset({ profiles, children, activities }, TIER_KEYS);
    state.loadedAt = Date.now();
    state.view = 'dash';
  } catch (e) {
    const code = e && e.code || 'onbekende fout';
    state.err = `Laden mislukt (${code}).` + (code === 'permission-denied' ? ' Zijn de regels uit firestore.rules gepubliceerd in de Firebase-console?' : '');
    state.view = 'error';
  }
  render();
}

/* Without a Firebase config (python tools/serve.py without --live) the page shows made-up accounts. */
function demoRaw(now) {
  let seed = 7;
  const rnd = () => { seed = (seed * 16807) % 2147483647; return seed / 2147483647; };
  const pick = arr => arr[Math.floor(rnd() * arr.length)];
  const raw = { profiles: [], children: [], activities: [] };
  for (let i = 1; i <= 40; i++) {
    const uid = 'demo' + String(i).padStart(3, '0') + 'xxxxxxxxxxxxxxxxxxx';
    const signup = now - Math.floor(rnd() * 420) * S.DAY;
    const quiet = rnd() < 0.3;
    const last = quiet ? signup + Math.floor(rnd() * 20) * S.DAY : now - Math.floor(rnd() * 25) * S.DAY;
    if (i % 5) raw.profiles.push({ uid, id: 'main', data: { email: `ouder${i}@voorbeeld.be`, createdAt: signup, lastSeen: Math.min(now, last) } });
    const kids = Math.floor(rnd() * 4);
    for (let k = 0; k < kids; k++) raw.children.push({ uid, id: 'c' + k, data: { name: 'x', tier: pick(TIER_KEYS), createdAt: signup + k * S.DAY, updatedAt: last,
      mastered: Object.fromEntries(Array.from({ length: Math.floor(rnd() * 30) }, () => [pick(BUILTIN_GOALS).id, '2026-01-01'])) } });
    const acts = kids ? Math.floor(rnd() * (quiet ? 8 : 150)) : 0;
    for (let a = 0; a < acts; a++) {
      const at = signup + rnd() * Math.max(S.DAY, Math.min(now, last) - signup);
      raw.activities.push({ uid, id: 'a' + a, data: { title: 'x', createdAt: at, updatedAt: at, childIds: ['c' + Math.floor(rnd() * kids)],
        goalIds: Array.from({ length: 1 + Math.floor(rnd() * 3) }, () => pick(BUILTIN_GOALS).id), photoIds: rnd() < 0.35 ? ['p1', 'p2'].slice(0, 1 + Math.floor(rnd() * 2)) : [] } });
    }
  }
  raw.children.push({ uid: 'demo001xxxxxxxxxxxxxxxxxxx', id: 'ex', data: { name: 'Voorbeeld', example: true, createdAt: now } });
  return raw;
}

async function start() {
  if (!FIREBASE_CONFIG) {
    state.demo = true; state.accounts = S.buildDataset(demoRaw(Date.now()), TIER_KEYS); state.loadedAt = Date.now(); state.view = 'dash';
    return render();
  }
  try {
    const [appM, authM, fsM] = await Promise.all(['firebase-app.js', 'firebase-auth.js', 'firebase-firestore.js'].map(f => import(FIREBASE_SDK + f)));
    const cfg = { ...FIREBASE_CONFIG }, emu = cfg.emulator; delete cfg.emulator;
    const app = appM.initializeApp(cfg);
    fb = { auth: authM.getAuth(app), fs: fsM.getFirestore(app), A: authM, F: fsM };
    if (emu) { authM.connectAuthEmulator(fb.auth, emu.auth, { disableWarnings: true }); fsM.connectFirestoreEmulator(fb.fs, emu.host, emu.port); }
    authM.onAuthStateChanged(fb.auth, user => {
      state.err = '';
      if (!user) { state.accounts = []; state.view = 'login'; render(); }
      else if (!ADMIN_UID || user.uid !== ADMIN_UID) { state.view = 'noaccess'; render(); }
      else load();
    });
  } catch (e) {
    state.err = 'De Firebase-bibliotheek kon niet laden. Controleer je verbinding.'; state.view = 'error'; render();
  }
}

/* ---------- events ---------- */
document.addEventListener('click', e => {
  const el = e.target.closest('[data-action]');
  if (el && ACTIONS[el.dataset.action]) ACTIONS[el.dataset.action](el);
});
document.addEventListener('submit', async e => {
  if (e.target.id !== 'login-form') return;
  e.preventDefault();
  const f = e.target;
  try { await fb.A.signInWithEmailAndPassword(fb.auth, f.email.value.trim(), f.password.value); }
  catch (err) { state.err = 'Aanmelden mislukt: controleer je e-mailadres en wachtwoord.'; render(); }
});
window.addEventListener('hashchange', render);
$('refresh-btn').addEventListener('click', () => load());
$('out-btn').addEventListener('click', () => fb.A.signOut(fb.auth));
start();
})();
</script>
```

- [ ] **Step 2: Build and check in the browser (demo data)**

Run: `python -m unittest discover -s tests` (expected: 5 pass; the placeholders are still present exactly once).
Run in the background: `python tools/serve.py --port 8000`
Open `http://localhost:8000/admin/` in the browser:
- The header shows "doelenboek.be admin", five tabs with Overzicht selected, and the status "Voorbeeldgegevens".
- Four tiles with numbers, a 12-bar weekly chart with three date labels, a "Recent actief" table where some rows show "geen profiel", and the footnote.
- No errors in the console. Clicking another tab shows its title (empty for now).
- At 360px width there's no horizontal scroll. With `localStorage['doelenboek.theme'] = 'dark'` and a reload, the dark theme shows.

Stop the server.

- [ ] **Step 3: Commit**

```bash
git add src/admin.html
git commit -m "Admin page: sign-in, loading, demo data and the Overzicht tab

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 7: Admin page — Groei, Gebruik, Inhoud

**Files:**
- Modify: `src/admin.html`: add three view functions before `const VIEWS`, change the three `VIEWS` entries, and add three `ACTIONS` entries.

**Interfaces:**
- Consumes: `S.growth`, `S.usage`, `S.content`; the helpers `tile`, `section`, `colChart`, `barList`, `weekRows`, `n`, `esc`, `subjName`, `subjColor`, `tierName`; and `state.growthPeriod`, `state.subjOpen`, `state.showNever` (all from Task 6).

- [ ] **Step 1: Add the views**

In `src/admin.html`, insert directly above the comment `/* Tasks 7 and 8 replace these with the real tabs. */`:

```js
const PERIODS = [['weeks', '12 weken'], ['months', '12 maanden'], ['all', 'Alles']];
function growthView() {
  const p = state.growthPeriod, g = S.growth(state.accounts, p, Date.now());
  const seg = `<div class="seg" role="tablist" aria-label="Periode">${PERIODS.map(([k, label]) =>
    `<button type="button" role="tab" aria-selected="${k === p}" data-action="period" data-v="${k}">${label}</button>`).join('')}</div>`;
  const label = p === 'weeks' ? 'week' : 'maand';
  const rows = key => g.rows.map(r => ({ start: r.start, value: r[key], title: `${dateFmt.format(r.start)}: ${r[key]} nieuw` + (key === 'accounts' ? `, totaal ${r.total}` : '') }));
  return section('Groei', `
    <div class="kpis">
      ${tile(n(g.totals.accounts), 'Accounts')}${tile(n(g.totals.children), 'Kinderen')}${tile(n(g.totals.activities), 'Activiteiten')}${tile(n(g.totals.photos), "Foto's")}
    </div>
    <div class="card panel"><h3>Nieuwe accounts per ${label} <small>totaal aan het einde: ${n(g.rows[g.rows.length - 1].total)}</small></h3>${colChart(rows('accounts'), p)}</div>
    <div class="two">
      <div class="card panel"><h3>Nieuwe kinderen per ${label}</h3>${colChart(rows('children'), p)}</div>
      <div class="card panel"><h3>Nieuwe activiteiten per ${label}</h3>${colChart(rows('activities'), p)}</div>
    </div>`, seg);
}

const FUNNEL = { account: 'Account aangemaakt', child: 'Eerste kind toegevoegd', activity: 'Eerste activiteit', ten: '10+ activiteiten' };
function usageView() {
  const u = S.usage(state.accounts, Date.now());
  return section('Gebruik', `
    <div class="kpis">
      ${tile(n(u.active7), 'Actief, 7 dagen')}${tile(n(u.active30), 'Actief, 30 dagen')}${tile(n(u.inactive90), 'Inactief > 90 dagen')}${tile(n(u.neverLogged), 'Nooit iets gelogd')}
    </div>
    <div class="card panel"><h3>Van aanmelden tot vaste gebruiker <small>van alle ${n(u.funnel[0].count)} accounts</small></h3>
      ${barList(u.funnel.map(f => ({ label: FUNNEL[f.key], value: f.count, pct: f.pct })), 'funnel')}</div>
    <div class="card panel"><h3>Actieve accounts per week <small>iets gewijzigd of de app geopend</small></h3>${colChart(weekRows(u.activeWeekly), 'weeks')}</div>`);
}

function contentView() {
  const c = S.content(state.accounts, BUILTIN_GOALS, SUBJECTS.map(s => s.key), TIER_KEYS);
  const subjects = state.subjOpen ? c.bySubject : c.bySubject.slice(0, 5);
  const more = c.bySubject.length > 5
    ? `<button type="button" class="linkish" data-action="subj-more">${state.subjOpen ? 'minder' : `… ${c.bySubject.length - 5} meer`}</button>` : '';
  const goalTable = (rows, extra) => `<div class="tbl-wrap"><table class="t"><tr><th>Code</th><th>Niveau</th><th>Doel</th>${extra ? '<th class="r">Activiteiten</th><th class="r">Kinderen beheerst</th>' : ''}</tr>${rows.map(g =>
    `<tr><td class="mono">${esc(g.subject)} ${esc(g.code)}</td><td>${esc(tierName(g.tier))}</td><td>${esc(g.description)}</td>${extra ? `<td class="r">${n(g.activities)}</td><td class="r">${n(g.mastered)}</td>` : ''}</tr>`).join('')}</table></div>`;
  return section('Inhoud', `
    <div class="two">
      <div class="card panel"><h3>Gekoppelde doelen per vak</h3>
        ${c.bySubject.length ? barList(subjects.map(s => ({ label: subjName(s.key), value: s.count, pct: s.pct, color: subjColor(s.key) }))) : '<p class="muted">Nog geen doelen gekoppeld.</p>'}${more}</div>
      <div class="card panel"><h3>Kinderen per niveau</h3>
        ${barList(c.byTier.map(x => ({ label: tierName(x.key), value: x.count, pct: x.pct })))}
        <h3 style="margin-top:14px">Foto's</h3>
        <p style="margin:0;font-size:.86rem">${n(c.photos.total)} foto's · ${c.photos.withPhotoPct}% van de activiteiten heeft er minstens één · gem. ${c.photos.avgGoals.toLocaleString('nl-BE', { maximumFractionDigits: 1 })} doelen per activiteit</p></div>
    </div>
    <div class="card panel"><h3>Meest gekoppelde doelen
      <button type="button" class="linkish" data-action="never">${state.showNever ? 'Toon meest gekoppelde' : `Toon nooit gekoppelde (${n(c.neverLinked.length)})`}</button></h3>
      ${state.showNever ? goalTable(c.neverLinked, false) : c.topGoals.length ? goalTable(c.topGoals, true) : '<p class="muted">Nog geen doelen gekoppeld.</p>'}</div>`);
}
```

Change the `VIEWS` entries:

```js
const VIEWS = {
  overzicht: overviewView,
  groei: growthView,
  gebruik: usageView,
  inhoud: contentView,
  accounts: () => section('Accounts', ''),
};
```

Add to `ACTIONS`:

```js
const ACTIONS = {
  retry: () => fb && fb.auth.currentUser ? load() : start(),
  period: el => { state.growthPeriod = el.dataset.v; render(); },
  'subj-more': () => { state.subjOpen = !state.subjOpen; render(); },
  never: () => { state.showNever = !state.showNever; render(); },
};
```

Also change the comment above `VIEWS` to `/* Task 8 replaces the accounts entry with the real tab. */`.

- [ ] **Step 2: Check in the browser (demo data)**

Run `python tools/serve.py --port 8000` in the background and open `http://localhost:8000/admin/#groei`:
- **Groei:** clicking 12 weken / 12 maanden / Alles changes the charts and the selected button. Hovering a bar shows a tooltip like "1 sep. 2026: 3 nieuw, totaal 21". The four total tiles are shown.
- **#gebruik:** four tiles; the funnel bars decrease from 100%; the weekly chart is shown.
- **#inhoud:** subject bars use the subject colours. "… N meer" expands the list and "minder" collapses it. The tier labels read exactly "Kleuter", "Lager LJ 1-4" and "Lager LJ 5-6". The photo line uses Dutch decimals ("2,1"). "Toon nooit gekoppelde (N)" switches the table.
- No console errors. At 360px there's no page-level horizontal scroll: the goal tables scroll inside their card.

Stop the server.

- [ ] **Step 3: Commit**

```bash
git add src/admin.html
git commit -m "Admin page: Groei, Gebruik and Inhoud tabs

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 8: Admin page — Accounts

**Files:**
- Modify: `src/admin.html`: add `accountsTable()`, `accountsView()` and `updateTable()` before `const VIEWS`, change the `accounts` entry, add `ACTIONS` entries and an `input` listener.

**Interfaces:**
- Consumes: `S.accountRows`, `S.accountDetail`, `S.relDays`; `state.q`, `state.filter`, `state.sort`, `state.dir`, `state.open`; the helpers `who`, `fmtDate`, `tierName`, `n`, `esc`, `section`, `FOOTNOTE`.

- [ ] **Step 1: Add the Accounts tab**

Insert above the comment `/* Task 8 replaces the accounts entry with the real tab. */`:

```js
const COLS = [['email', 'E-mail', ''], ['signupAt', 'Aangemaakt', ''], ['lastActive', 'Laatst actief', ''], ['children', 'Kinderen', 'r'], ['activities', 'Activiteiten', 'r'], ['photos', "Foto's", 'r']];
const FILTERS = [['all', 'Alle'], ['active', 'Actief'], ['inactive', 'Inactief']];
function accountsTable() {
  const now = Date.now();
  const rows = S.accountRows(state.accounts, { query: state.q, filter: state.filter, sort: state.sort, dir: state.dir }, now);
  const head = COLS.map(([k, label, cls]) => {
    const on = state.sort === k, arrow = on ? (state.dir === 'asc' ? ' ▴' : ' ▾') : '';
    return `<th class="${cls}" aria-sort="${on ? (state.dir === 'asc' ? 'ascending' : 'descending') : 'none'}"><button type="button" data-action="sort" data-v="${k}">${label}${arrow}</button></th>`;
  }).join('');
  const body = rows.map(r => {
    const open = state.open === r.uid;
    const line = `<tr class="${open ? 'open' : ''}">
      <td><button type="button" class="linkish" data-action="row" data-v="${esc(r.uid)}" aria-expanded="${open}">${who(r)}</button></td>
      <td>${r.signupApprox ? '~ ' : ''}${fmtDate(r.signupAt)}</td><td>${esc(S.relDays(r.lastActive, now))}</td>
      <td class="r">${n(r.children)}</td><td class="r">${n(r.activities)}</td><td class="r">${n(r.photos)}</td></tr>`;
    if (!open) return line;
    const d = S.accountDetail(state.accounts.find(a => a.uid === r.uid));
    const kids = d.kids.length
      ? `<table class="t" style="width:auto"><tr><th>Kind</th><th>Niveau</th><th class="r">Activiteiten</th><th class="r">Doelen beheerst</th></tr>${d.kids.map(k =>
        `<tr><td>${esc(k.label)}</td><td>${esc(tierName(k.tier))}</td><td class="r">${n(k.activities)}</td><td class="r">${n(k.mastered)}</td></tr>`).join('')}</table>`
      : '<p class="muted" style="margin:0">Geen kinderen.</p>';
    return line + `<tr class="detail"><td colspan="6">${kids}<p class="mono muted" style="margin:6px 0 0">uid ${esc(d.uid)} · laatste wijziging ${d.lastChange ? `${fmtDate(d.lastChange)} ${timeFmt.format(d.lastChange)}` : '—'}</p></td></tr>`;
  }).join('');
  return `<p class="count-line">${n(rows.length)} van ${n(state.accounts.length)} accounts</p>
    <div class="card panel tbl-wrap"><table class="t"><tr>${head}</tr>${body || '<tr><td colspan="6" class="muted">Geen accounts gevonden.</td></tr>'}</table></div>`;
}
function accountsView() {
  return section('Accounts', `
    <div class="acc-tools"><input class="search" id="acc-q" type="search" placeholder="Zoek op e-mail of uid…" value="${esc(state.q)}" aria-label="Zoek accounts">
      <div class="seg" role="tablist" aria-label="Filter">${FILTERS.map(([k, label]) => `<button type="button" role="tab" aria-selected="${k === state.filter}" data-action="filter" data-v="${k}">${label}</button>`).join('')}</div></div>
    <div id="acc-table">${accountsTable()}</div>
    <p class="count-line">Actief: iets gedaan in de laatste 30 dagen. Inactief: niets in de laatste 90 dagen.</p>${FOOTNOTE}`);
}
/* re-draws only the table, so the search field keeps its focus while typing */
const updateTable = () => { const el = $('acc-table'); if (el) el.innerHTML = accountsTable(); };
```

Change the `accounts` entry in `VIEWS` to `accounts: accountsView,` and remove the now-stale comment above `VIEWS`.

Add to `ACTIONS`:

```js
  filter: el => { state.filter = el.dataset.v; render(); },
  sort: el => {
    const k = el.dataset.v;
    if (state.sort === k) state.dir = state.dir === 'asc' ? 'desc' : 'asc';
    else { state.sort = k; state.dir = k === 'email' ? 'asc' : 'desc'; }
    updateTable();
  },
  row: el => { state.open = state.open === el.dataset.v ? null : el.dataset.v; updateTable(); },
```

After the `submit` listener, add:

```js
document.addEventListener('input', e => { if (e.target.id === 'acc-q') { state.q = e.target.value; updateTable(); } });
```

- [ ] **Step 2: Check in the browser (demo data)**

Run `python tools/serve.py --port 8000` in the background and open `http://localhost:8000/admin/#accounts`:
- Typing "ouder1" in the search field narrows the table while the field keeps focus. The count line updates ("11 van 40 accounts").
- Alle/Actief/Inactief filter the list.
- Clicking each column header sorts it, and clicking again reverses. The arrow moves.
- Clicking an email opens the detail row: "Kind 1, Kind 2…" with tier, activities, goals mastered, uid and last change. Clicking it again closes it. Keyboard: Tab to a row button, Enter toggles it.
- Every fifth account shows a short uid with "geen profiel", and its sign-up date has "~ ".
- No child names appear anywhere: search the DOM for "Voorbeeld" and for `"name"` and find nothing. No console errors. At 360px the table scrolls inside its card.

Stop the server.

- [ ] **Step 3: Commit**

```bash
git add src/admin.html
git commit -m "Admin page: Accounts tab with search, filter, sorting and per-account counts

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 9: Privacy texts (wording approved by the user)

**Files:**
- Modify: `src/doelenboek.html`: the `privacy:` keys around lines 189 (nl) and 287 (en)
- Modify: `tools/public.py`: the NL FAQ "Waar worden mijn gegevens bewaard?" (around line 75), the EN FAQ "Where is my data stored?" (around line 155), and the llms "Privacy:" line (around line 498)

- [ ] **Step 1: Get the wording approved**

Show the user these drafts and ask for approval or changes. Use their exact wording.

- NL sentence: `De beheerder kan opgeslagen gegevens inzien voor statistieken en ondersteuning.`
- EN sentence: `The administrator can view stored data for statistics and support.`
- llms clause: `; the site administrator can view stored data for statistics and support`

Placement: right after the sentence about where the data is stored and who can reach it, in all five places.

- [ ] **Step 2: Apply**

With the approved wording (shown here with the drafts):

`src/doelenboek.html` nl:

```js
    privacy: "Je gegevens (kinderen, activiteiten, foto's) worden bewaard in Google Firebase in de EU en zijn alleen bereikbaar met jouw e-mailadres en wachtwoord. De beheerder kan opgeslagen gegevens inzien voor statistieken en ondersteuning. Je kunt je account en al je gegevens altijd verwijderen via Gegevens.",
```

`src/doelenboek.html` en:

```js
    privacy: 'Your data (children, activities, photos) is stored in Google Firebase in the EU and can only be reached with your email address and password. The administrator can view stored data for statistics and support. You can delete your account and all your data at any time via Data.',
```

`tools/public.py` NL FAQ answer: insert `'De beheerder kan opgeslagen gegevens inzien voor statistieken en ondersteuning. '` as a new string piece directly after the piece ending in `met jouw e-mailadres en wachtwoord. `. The EN FAQ answer gets the same treatment with the EN sentence after `… with your email address and password. ` (read lines 155–158 first for the exact piece boundaries). The llms line becomes:

```
- Privacy: no cookies on the visitor's device; data stored in Google Firebase in the EU; the site administrator can view stored data for statistics and support; users can delete their account and data at any time
```

- [ ] **Step 3: Build and check**

Run: `python tools/build.py src/doelenboek.html index.html firebase-config.json`
Expected: no error. `grep -c "statistieken en ondersteuning" index.html over/index.html` gives at least 1 for each file. `grep "administrator" llms.txt` shows the new clause.

- [ ] **Step 4: Commit**

```bash
git add src/doelenboek.html tools/public.py
git commit -m "Privacy texts: the administrator can view stored data for statistics and support

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 10: Full build, live verification and rollout

**Files:**
- Modify (generated): `index.html`, `admin/index.html`, `robots.txt` and the other build outputs

- [ ] **Step 1: All tests**

Run: `node --test "tests/*.test.mjs"` → PASS, 19 tests.
Run: `python -m unittest discover -s tests` → PASS, 5 tests.

- [ ] **Step 2: Production build**

Run: `python tools/build.py src/doelenboek.html index.html firebase-config.json`
Expected: `wrote index.html`, `wrote admin/index.html`, and the public files. If the user hasn't given a uid yet, the `note: firestore.rules has no admin uid yet` warning appears. Check `robots.txt` contains `Disallow: /admin/`, and `sitemap.xml` doesn't mention `admin`.

- [ ] **Step 3: Rules first (the user does this)**

Ask the user to paste `firestore.rules` into Firebase console → Firestore Database → Rules and click Publish. This must happen before the app change goes live, or profile writes are rejected.

- [ ] **Step 4: Live check locally**

Run `python tools/serve.py --live --port 8000` in the background. The user signs in on `http://localhost:8000/` with a normal test account, then on `http://localhost:8000/admin/`:
- Normal test account at `/admin/`: shows "Geen toegang". Firestore console: `users/{testUid}/profile/main` exists with email, createdAt and lastSeen.
- The owner account at `/admin/`: the dashboard loads with real numbers and the status "Bijgewerkt om HH:MM"; Vernieuwen reloads. All five tabs render without console errors.
- A failing query shows the notice with the error code and the "regels" hint. To try it, temporarily sign in as the owner before the rules are published.
- Deleting the test account (Gegevens → delete account) removes its `profile/main` document.

Stop the server.

- [ ] **Step 5: Commit the build outputs**

```bash
git status --short   # only build outputs should be listed; .superpowers/ is ignored
git add -A
git commit -m "Rebuild the app, /admin/ and the public pages

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

- [ ] **Step 6: Hand over**

Report to the user: the tests passed, what was verified live, that the rules are published, and that the branch is ready to merge with `superpowers:finishing-a-development-branch`. Don't merge or push without their go-ahead.
