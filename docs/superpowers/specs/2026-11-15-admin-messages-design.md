# Admin messages — design

Date: 2026-11-15 · Branch: `feature/admin-messages`

## Goal

The admin writes a message on `/admin/` and every user sees it once, in a popup, the next time they open the app. A message has a start and a lifetime, so a Christmas greeting never shows up in February.

Terms used in this document:

- **Admin:** the one account that `isAdmin()` in `firestore.rules` names.
- **User:** any signed-in account, the admin included.
- **Message:** one announcement the admin creates. It has one or two language versions.
- **Live:** a message whose start has passed and whose end has not.
- **Seen:** a user has had the message on screen and moved past it (see *Seen*).

## Decided with the user

- The admin writes each message in one language, or in both Dutch and English. There is no automatic translation.
- A one-language message shows to every user in that language, without a language toggle.
- A two-language message opens in the user's app language. An NL | EN toggle in the top right corner of the popup switches the message only, not the rest of the app.
- Writing a two-language message shows the Dutch and English text boxes side by side, each with a live preview of exactly what users will see.
- Formatting: bold, italic, headings, bulleted and numbered lists, links, and images.
- Each image has one enlarge setting: *enlarge on click*, *enlarge on hover*, or *never enlarge*.
- A message either starts the moment the admin sends it, or at a date and time the admin schedules.
- Each message has a lifetime. The end is its start plus the lifetime.
- A **Replace** toggle per message (see *Replace*).
- An **Also show to new accounts** checkbox per message, off by default (see *Who sees a message*).
- A user sees each message at most once, across all their devices.
- The admin page lists sent messages with their status and how many accounts have seen each one. The admin can withdraw a live message. A live message can't be edited: to fix it, the admin withdraws it and sends it again.
- A scheduled message can be edited or deleted until it starts.

## Approaches considered

**Translation** (the user first asked for automatic translation, then dropped it):
- Chrome's built-in translator: free and on-device, but works only in desktop Chrome.
- The Claude API: best quality, works everywhere, needs an API key with billing.
- **Chosen:** neither. The user found both too dependent on outside services and writes both versions by hand.

**Text editor:**
- **Chosen: a plain text box with formatting codes,** with toolbar buttons that insert the codes and a live preview under each box. Little code, no library, pasted text arrives as plain text, and the preview removes the downside of seeing codes while typing.
- Rejected: an editor that shows formatting while typing. It needs a library or a lot of fiddly code, pasted text brings hidden formatting, and the preview would repeat it.

## User side (the app)

### When the popup appears

After `enterAccount()` in `src/doelenboek.html`, the app loads the live messages once per app open. If one or more are pending for this user (see *Who sees a message*), the message popup opens. If another dialog is open (`dlg`, `dlg2`, the lightbox or the thank-you popup), the popup waits until that dialog closes, the way `scheduleThanks()` waits. The thank-you popup waits for the message popup in the same way.

A failed load is logged to the console and never shown to the user. The next app open tries again.

### Who sees a message

A message is pending for a user when all of these hold:

1. The message is live.
2. The message id is not in the user's `seen` list.
3. The account was created at or before the message's start, or the message has **Also show to new accounts** on. The account's creation time is `user.metadata.creationTime`.

### The popup

```
┌─────────────────────────────────────────────┐
│ Vrolijk kerstfeest!            NL | EN   ✕  │
│                                             │
│ [ image ]                                   │
│ Fijne feestdagen, en bedankt dat jullie     │
│ Doelenboek gebruiken. …                     │
│                                             │
│                           1 / 2  [Volgende] │
└─────────────────────────────────────────────┘
```

- Pending messages show one at a time, oldest start first.
- With more than one pending message, a counter ("1 / 2") and a **Next** button show. On the last message the button reads **Close**.
- When the message text starts with a `#` heading, that heading is the popup's title, in the header next to the toggle and ✕. Otherwise the header shows only the toggle and ✕.
- The NL | EN toggle shows only for a two-language message. It starts on the user's app language. A one-language message shows in its own language whatever the app language is.
- The popup follows the app's dialog style, light and dark theme, and works at phone width without horizontal scrolling.

### Seen

- A message counts as seen when the user presses **Next** or **Close** on it, or closes the popup on it (✕, Escape, or a click outside the popup).
- Closing the popup on message 1 of 3 marks only message 1 as seen. Messages 2 and 3 show at the next app open.
- The app adds the id to the `seen` list in `users/{uid}/profile/main`. When the profile record doesn't exist yet, the same write also sets `email`, `createdAt` and `lastSeen`, because the rules require them. A failed write is logged and ignored. The message then shows again at the next app open.

### Images

- **Enlarge on click:** clicking the image opens it full size in an overlay that closes on click, ✕ or Escape. The builder may reuse the app's lightbox or make a small overlay.
- **Enlarge on hover:** while the mouse pointer is over the image, a larger version shows. It disappears when the pointer leaves. On devices without hover (`@media (hover: none)`), the image behaves as **Enlarge on click**.
- **Never enlarge:** the image is shown at its size in the message and does nothing.

Images in the popup are at most the popup's width.

## Admin side (`/admin/`)

A sixth tab, **Berichten** / **Messages** (hash `#berichten`), with labels in Dutch and English like the other tabs.

```
┌ New message ──────────────────────────────────────────────┐
│ Language: (•) NL + EN   ( ) NL only   ( ) EN only          │
│                                                            │
│ ┌ NL ───────────────────────┐ ┌ EN ───────────────────────┐│
│ │ [B][I][H][•][1.][link][img]│ │ [B][I][H][•][1.][link][img]││
│ │ your text                 │ │ your text                 ││
│ ├ preview ──────────────────┤ ├ preview ──────────────────┤│
│ │ exactly as users see it   │ │ exactly as users see it   ││
│ └───────────────────────────┘ └───────────────────────────┘│
│ Start: (•) Now  ( ) Scheduled [24-12-2026 08:00]           │
│ Lifetime: [30] days  → visible until 23 Jan 2027 08:00     │
│ [ ] Replace older messages that haven't been seen          │
│ [ ] Also show to new accounts                              │
│                                              [ Send ]      │
├ Messages ──────────────────────────────────────────────────┤
│ Vrolijk kerstfeest! · NL+EN · scheduled 24 Dec · until 23 Jan
│                                       [Edit] [Delete]      │
│ Nieuw: kindniveaus · NL · live until 4 Dec · seen by 41    │
│                                       [Withdraw]           │
└────────────────────────────────────────────────────────────┘
```

### Writing

- **Language** picks two text boxes side by side, or one. On a phone the two columns stack.
- Each text box has its own toolbar and a live preview directly under it. The preview uses the same rendering code as the app (see *Formatting codes*), so it shows exactly what users see.
- **Image button:** the admin picks an image file and an enlarge setting. The page compresses the image with the app's `processImage()` steps (longest side 1600 px down to 640 px, JPEG, at most `PHOTO_MAX_B64` = 240,000 base64 characters) and inserts an image code at the cursor. In a two-language message, an image inserted in one box can be used in the other box by copying its code. The image is stored once.
- **Lifetime:** a whole number of days, at least 1 and at most 365, default 30. The page shows the resulting end date and time.
- **Scheduled start:** a date and time in the admin's local time, at least 1 minute in the future.
- **Send** is disabled while a chosen language's text box is empty. Before sending, the page asks for confirmation inside the page (no browser `confirm()`), showing the start, end and the two toggles.
- An unsent draft lives only in the page. Leaving or reloading the page with an unsent draft asks for confirmation (`beforeunload`).

### The message list

Newest start first. Each row shows the first line of the message text (Dutch if present), its languages, its status and, once started, "seen by N", where N is the number of profiles whose `seen` list holds the message id.

| Status | Shown as | Actions |
|---|---|---|
| Scheduled | starts *date*, until *date* | **Edit** (loads it into the form; **Send** becomes **Save**), **Delete** |
| Live | live until *date* | **Withdraw** |
| Ended | ended *date*, or "replaced by *first line*" | **Delete** |

Withdraw and Delete both remove the message record and its images, after an in-page confirmation. Users who already saw the message are not affected.

## Replace

When a message R with **Replace** on starts, every message with an earlier start that is still live ends at R's start. Users who already saw such a message are not affected; everyone else never sees it.

Example: message M runs 1 December to 28 February. Message R with **Replace** starts 24 December. M ends on 24 December, so a user who hasn't opened the app since 30 November sees only R.

Messages with a later start than R are not affected, also when they were scheduled before R was sent.

How it's stored: each message that a later message replaced holds `replacedBy` (the replacing message's id) and `replacedAt` (its start). A message's effective end is the earlier of its `endAt` and its `replacedAt`. The admin page recomputes these two fields for all messages after every send, save and delete. For example: a message scheduled after R was sent, but starting before R, gets the fields too. Fields already set by a message that has started stay as they are, also when that message is withdrawn.

## Formatting codes

One shared file, `src/messages.js`, turns message text into HTML and holds the pure function that picks a user's pending messages (*Who sees a message*, *Replace*). `tools/build.py` inlines it into both the app and the admin page, the way it inlines `src/admin-stats.js` into the admin page. It has no DOM or Firebase code.

| Code | Result |
|---|---|
| `**text**` | bold |
| `*text*` | italic |
| `# text` at the start of a line | heading |
| `## text` at the start of a line | subheading |
| `- text` at the start of a line | bulleted list item |
| `1. text` at the start of a line | numbered list item |
| `[text](https://…)` | link, opens in a new tab |
| `![alt text](img:ID click)` on its own line | image; the last word is `click`, `hover` or `none` |
| empty line | new paragraph |
| single line break | line break |

Rules for the renderer:
- It must escape all other text. Raw HTML in a message is shown as text, never rendered.
- Links must use `https:`, `http:` or `mailto:`. Any other link is shown as plain text.
- An image code whose ID does not belong to the message is dropped.
- [Builder's call: the exact syntax may change, as long as the toolbar inserts it and the preview shows it.]

## Data

### `messages/{messageId}`

| Field | Type | Meaning |
|---|---|---|
| `langs` | list: `['nl']`, `['en']` or `['nl', 'en']` | the languages written |
| `body` | map: `{ nl: text, en: text }` | the message text in formatting codes, one entry per language in `langs` |
| `startAt` | number, ms | start |
| `endAt` | number, ms | start + lifetime |
| `replace` | boolean | the **Replace** toggle |
| `newAccounts` | boolean | the **Also show to new accounts** checkbox |
| `replacedBy`, `replacedAt` | string, number (ms) | set only on a message a later message replaced |
| `createdAt` | number, ms | when the admin first saved it |

### `messages/{messageId}/images/{imageId}`

`data` (base64 JPEG), `w`, `h`, and a copy of the message's `startAt`, so the rules can check the start without reading the message record.

### `users/{uid}/profile/main`

Gains one field, `seen`: a list of message ids. The daily `writeProfile()` write must keep `seen` (merge, or include it). A list grows by one id per message; at a few messages a month it stays far below the 1 MB record limit, so it is never pruned.

### Loading in the app

One query per app open: messages with `startAt` ≤ now and `endAt` > now. The app drops messages with `replacedAt` ≤ now, then applies *Who sees a message*. It then loads the images of the messages it will show.

## Access (`firestore.rules`)

- `messages` and its `images`: the admin may read and write everything. A signed-in user may read only records whose `startAt` has passed (`resource.data.startAt <= request.time.toMillis()`). Nobody else has access.
- `profile`: the allowed keys become `email`, `createdAt`, `lastSeen` and `seen`. `seen` must be a list of at most 1,000 entries. `email`, `createdAt` and `lastSeen` stay required.
- Risk for the builder to check in the Firebase emulator: Firestore only allows a list query that the rules can prove safe for every result. The app's query must therefore filter on `startAt`, and a device clock running ahead of the server can make the query fail. If the rule can't be made to work reliably, the fallback is to let signed-in users read all messages, scheduled ones included, while the app still shows only live ones. The builder tells the user before taking the fallback, because the user was told scheduled messages are unreadable until they start.

**Rollout order:** before deploying the app and admin changes, the user publishes the new rules and creates the composite index on `messages` (`startAt`, `endAt`) that the app's query needs, both in the Firebase console. The builder gives the exact index settings. Without them, the message query and the `seen` writes are rejected (harmless: no popup appears).

## Testing

- `node --test "tests/*.test.mjs"`: `messages.js`. The renderer: every code, escaping of HTML, rejected link types, unknown image ids, empty text. The pending-message function: live window edges, `seen`, new accounts, replaced messages, order.
- `python -m unittest discover -s tests`: both built pages contain the inlined `messages.js` and still parse.
- In the Firebase emulator or on staging: send now, schedule, edit and delete a scheduled message, withdraw a live one, replace, the new-account checkbox, one- and two-language messages, all three image settings (also at phone width, where hover becomes click), seen on one device not showing on a second, and light and dark theme.
- A scheduled message can't be read by a normal account before its start (see the risk under *Access*).

## Calls made in writing this design

The user did not decide these. Claude proposed them; the user may change any of them.

- Closing the popup marks only the message on screen as seen (see *Seen*).
- Lifetime: whole days, 1 to 365, default 30.
- A scheduled start must be at least 1 minute in the future.
- The `seen` list is never pruned; the rules cap it at 1,000 ids.
- **Replace** is stored on the replaced messages (`replacedBy`, `replacedAt`), so it still holds after the replacing message has ended.
- Withdraw deletes the message record and its images; there is no archive.
- Unsent drafts are not saved anywhere.
- No separate title field: a `#` heading on the first line becomes the popup title.
- The message list shows the first line of the text, Dutch if present.
- No change to the privacy texts: the only new personal data is the list of seen message ids, and it is deleted with the account's profile.

## Out of scope

Automatic translation, sending to selected users only, email or push notifications, editing a live message, a draft store, and statistics beyond "seen by N".
