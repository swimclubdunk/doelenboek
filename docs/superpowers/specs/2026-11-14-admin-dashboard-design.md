# Admin dashboard — design

Date: 2026-11-14 · Branch: `feature/admin-dashboard`

## Goal

A private page at `doelenboek.be/admin/` where the site owner sees platform data: growth, engagement, content usage, and a per-account lookup. Only the owner's account can open it, from any device.

Decided with the user:
- Admin page on the site (not a local script).
- Layout: tabs per topic (*Overzicht, Groei, Gebruik, Inhoud, Accounts*), so features stay grouped and new ones can be added per tab.
- Per-account lookup shows **counts only**: no child names, activity titles/notes or photos.
- Labels in Dutch, like the app.
- The per-tab content in the 2026-11-14 mockups is a first draft; it may be refined after the first version.

## Architecture

### Files

| File | Purpose |
|---|---|
| `src/admin.html` | The admin page source: header, tabs, rendering, Firebase sign-in and loading. |
| `src/admin-stats.js` | Pure functions that turn raw records into the numbers each tab shows. No DOM, no Firebase. |
| `tests/admin-stats.test.mjs` | `node --test` tests for `admin-stats.js` against small fixture datasets. |
| `tools/build.py` | Gains a second target: builds `admin/index.html` next to `index.html`. |
| `tools/serve.py` | Serves `/admin/` (rebuilt on each load, like the app). |
| `tools/public.py` | `robots.txt` gets `Disallow: /admin/`; privacy texts get one admin sentence. |
| `firestore.rules` | Admin read access and the new `profile` collection. |
| `src/doelenboek.html` | Writes the profile record; deletes it on "delete account". |

### Build

`build.py` builds `src/admin.html` the same way as the app: inline the stylesheets (`design/tokens.css`, `design/app.css`, `core.css`), the favicon and the Firebase config. It also inlines `src/admin-stats.js` and fills in:
- `BUILTIN_GOALS`: the same goal list the app gets, needed to map goal ids to subjects, tiers, codes and descriptions.
- `SUBJECTS` and `TIERS`: copied as text from `src/doelenboek.html`, so the subject names, colours and tier labels ("Lager LJ 1-4") have one source.

The admin page gets `<meta name="robots" content="noindex, nofollow">`, isn't linked from anywhere, and isn't listed in `sitemap.xml`.

### Access (Firestore rules)

```
function isAdmin() { return request.auth != null && request.auth.uid == '<OWNER_UID>'; }

match /{path=**}/children/{id}   { allow read: if isAdmin(); }
match /{path=**}/activities/{id} { allow read: if isAdmin(); }
match /{path=**}/profile/{id}    { allow read: if isAdmin(); }
```

- The existing owner rules stay as they are. `profile` is added to the owner's read/delete list and to the create/update list, with only the fields `email`, `createdAt` and `lastSeen` allowed.
- The admin can read but never write other accounts' data. `photos` and the legacy `goals` stay closed to the admin.
- The owner's uid is filled in from the Firebase console. The user pastes and publishes the rules, as before.
- On the page itself, the "geen toegang" (no access) screen is only for convenience. The rules are what actually protect the data.

### The profile record

Path: `users/{uid}/profile/main` with fields:
- `email`
- `createdAt`: ms timestamp from `user.metadata.creationTime`
- `lastSeen`: ms timestamp

The app writes it after sign-in, but only when there's no profile yet, the email has changed, or `lastSeen` is from an earlier day. That keeps it to at most one write per account per day. A failed write is ignored and never shown to the user. "Delete account" also deletes `profile`.

**Rollout order:** publish the new rules before deploying the app change. Otherwise profile writes are rejected (harmless, just lost).

### Loading

After admin sign-in, the page runs three collection-group queries: `children`, `activities` and `profile`. The uid of each record is its parent path (`users/{uid}/…`). Records go through the same validation as in the app. Records with `example: true` are dropped. Name, title and notes fields are thrown away while loading and never reach the rendering code.

All data is loaded once per page load; the *Vernieuwen* button reloads it. At the current scale (thousands of activities) one load costs about the number of documents read, well within the free 50k reads per day. A nightly summary (Cloud Functions, paid plan) is the later option if it grows. Out of scope now.

## Definitions (computed in `admin-stats.js`)

- **Account:** every uid that has a profile, a child or an activity. Accounts with no data and no profile can't be seen (stated in a footnote on the page).
- **Sign-up date:** `profile.createdAt`. Without a profile, the earliest `createdAt` of the account's records, shown with a "~" prefix.
- **Last active:** the latest of `profile.lastSeen` and any record's `updatedAt`/`createdAt`.
- **Active in the last N days:** last active within N days of now.
- **Active in week W** (chart): at least one record created or updated in that week, plus `lastSeen` in that week for the current week only (`lastSeen` has no history).
- **Inactive:** last active more than 90 days ago.
- **Never logged anything:** account with zero activities.
- **Photos:** the sum of `photoIds.length` over activities. Photo files are never read.
- **Subject of a goal link:** from `BUILTIN_GOALS` by goal id. Unknown ids count as "Onbekend".
- Weeks start on Monday, local time. Numbers use Dutch formatting (`6.840`).

## Tabs

**Overzicht**
- Four tiles: Accounts (+ this month), Actief 30 d (% of all), Kinderen (+ this month), Activiteiten (+ this month).
- A chart of active accounts per week for the last 12 weeks.
- A "Recent actief" list of the 8 most recently active emails.

**Groei**
- A period switch: 12 weken / 12 maanden / Alles.
- Totals: accounts, children, activities, photos.
- A chart of new accounts per period, with the running total.
- Small charts for new children and new activities per period.

**Gebruik**
- Tiles: actief 7 d, actief 30 d, inactief > 90 d, nooit iets gelogd.
- A funnel: account → first child → first activity → 10+ activities, with count and % of all accounts.
- A chart of active accounts per week for the last 12 weeks.

**Inhoud**
- Linked goals per subject (bars in the subject colours, top 5, then "… N meer" which expands).
- Children per tier.
- Photo totals, % of activities with at least one photo, and average goals per activity.
- A table of the most linked goals (top 10): code, description, activities, children who mastered it.
- A toggle to show built-in goals that are never linked.

**Accounts**
- Search by email or uid, an Alle / Actief / Inactief filter, and sortable columns.
- Columns: e-mail (or a short uid with a "geen profiel" tag), aangemaakt, laatst gezien, kinderen, activiteiten, foto's.
- Clicking a row opens: per child "Kind 1, 2…" (ordered by `createdAt`), its tier, number of activities and goals mastered. Also the full uid and the last change. No names.

Charts are simple bars made with the app's CSS (`.bars`, plain flex bars). No chart library. The selected tab is in the URL hash (`#groei`), like the app.

## States and errors

- **Not signed in:** the app's sign-in form, with email and password.
- **Signed in but not the admin:** the "Geen toegang" screen and a sign-out button. No queries are run.
- **Loading:** "Gegevens laden…".
- **Query fails** (e.g. rules not published yet): a notice with the Firebase error code and a hint to publish `firestore.rules`.
- **Empty data:** tiles show 0 and charts show the empty state, without errors.

## Privacy

- The rule gives the owner's account read access to all children and activities. "Counts only" is enforced by the page, which drops names and notes while loading. It isn't enforced by Firebase.
- The privacy texts in `tools/public.py` (NL and EN) get one sentence along the lines of: *De beheerder kan opgeslagen gegevens inzien voor statistieken en ondersteuning.* The user approves the exact wording before it's added.

## Testing

- `node --test tests/` covers `admin-stats.js` against fixtures: account union, profile fallbacks, active and inactive edges, week boundaries, example records excluded, funnel, subject mapping, unknown goals, and empty data.
- `python tools/build.py …` must build both pages without errors.
- Local demo: `python tools/serve.py --port 8000`, then `/admin/`. Check the "Geen toegang" screen with a normal account, and the full dashboard with the owner account once the rules are published. Check at phone width (no horizontal scroll) and in light and dark themes.
- The app still works for a normal user: the profile is written once, and delete account removes it.

## Out of scope

Server-side aggregation, exports, email to users, editing or deleting other accounts, a storage size in bytes, and English UI for the admin page.
