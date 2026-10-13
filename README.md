# 📒 Doelenboek

**Track which Flemish *minimumdoelen* your homeschooled kids have covered, one activity at a time.**
*Houd per kind bij welke minimumdoelen al aan bod kwamen.*

**▶ Open the app: https://swimclubdunk.github.io/doelenboek/**

Create an account with your email and a password, then use it on any device.

## What it does

- **Children:** each child gets a card with an animal avatar and a progress bar per subject.
- **Activities:** log a lesson, outing or project, choose who took part, and tag the minimum goals it covered. Hover a goal code to see what the goal is.
- **Photos:** attach up to 24 photos per activity. They show as thumbnails; hover to preview, click to view full size. Photos are resized in your browser before they're saved.
- **Coverage:** calculated from your activities, so it's always correct. Delete an activity and only the goals nothing else covers reopen.
- **32 built-in goals:** kindergarten goals for Nederlands and Muzische vorming. You can add your own goals or import more from Excel or CSV.
- **Report:** a CSV per child (goal, covered or open, and the activities that covered it). Handy as evidence for the exam board.
- **NL / EN:** switch the whole interface between Dutch and English.

## 🔐 Accounts and your data

- **Email + password, nothing else.** Your email address is your username. There are no codes or confirmation emails. The only email the app can send is a *Forgot password?* link.
- **Every device, in sync.** Log in anywhere and you see the same data; changes appear on your other devices within seconds.
- **Private by design.** Data is stored in Google Firebase (Cloud Firestore). The database rules in [`firestore.rules`](firestore.rules) only let each account read and write its own data.
- **Logging out** also removes the offline copy from that browser, so the next person on a shared computer finds nothing.
- **Delete your account** under **Gegevens**. It permanently removes the login and all its data.

Used Doelenboek before accounts existed? Log in at the same address. The app offers to move the data stored in that browser into your account.

## For developers

Plain HTML, CSS and JavaScript in a single file. There are no dependencies except the Firebase SDK and Google Fonts, both loaded from a CDN.

```
src/doelenboek.html     the app (source)
doelen/*.json           the built-in goals, one file per subject
firebase-config.json    Firebase web config (public by design; the rules protect the data)
firestore.rules         Firestore security rules: paste into the Firebase console → Firestore → Rules
tools/build.py          builds index.html from the source, the goals and the config
```

### Editing the built-in goals

Each subject has its own file in [`doelen/`](doelen), for example `doelen/nederlands.json`. Add a goal by copying an existing entry inside the `"doelen": [ ... ]` list:

```json
{
  "code": "1.1.1",
  "category": "Lezen",
  "categoryEn": "Reading",
  "description": "De kleuters kunnen rijm herkennen, ...",
  "descriptionEn": "Preschoolers can recognise rhyme, ..."
}
```

- `code` and `description` are required. The other fields are optional.
- Separate entries with a comma, but don't put a comma after the last one.
- Use `\n` for a line break inside a text, and `\"` for a double quote.
- **Don't change the `code` of an existing goal.** Activities link to goals by subject and code, so a renamed code shows up as a new goal that nothing has covered yet. Fixing typos in the texts is safe.
- Leave `subject` at the top of the file as it is. It's the subject key the app uses (`NL`, `WK`, `WT`, `GE`, `AK`, `MV`, `LO` or `AT`).

Then rebuild. The build checks the files and names the file and goal if something is wrong.

Rebuild after editing the source:

```
python tools/build.py src/doelenboek.html index.html firebase-config.json
```

Without the config argument, the build stores data only in the browser.
