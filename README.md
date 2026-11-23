# 📒 Doelenboek

**https://doelenboek.be**

Doelenboek is for parents who homeschool in Flanders. Log what you do with your children, with photos, link it to the Flemish *minimumdoelen*, and see per child and per subject which goals have been covered and which are still open. It is free, in Dutch and English, and works on any device with an email-and-password account.

## Folders

- `site/` — everything that is published, and nothing else: the built app, `admin/`, the public pages, fonts and images, plus `CNAME` and `.nojekyll`. `.github/workflows/pages.yml` uploads this folder to GitHub Pages on every push to `main`.
- `src/`, `doelen/`, `doelen-lager/`, `doelen-secundair/`, `tools/`, `tests/` — the sources, build scripts and tests.

## Development

Build the site after a change:

```
python tools/build.py src/doelenboek.html site/index.html firebase-config.json
```

The build also writes the public side of the site next to `site/index.html`: plain HTML pages about Doelenboek and the minimumdoelen per subject (`over/`, `minimumdoelen/`, `en/...`), `robots.txt`, `sitemap.xml`, `llms.txt`, `llms-full.txt` and the share image. These are what search engines and AI assistants read, since the app itself needs JavaScript and a login. Their texts are in `tools/public.py`.

Messages to users are written on the admin page, under `/admin/#berichten`. Each signed-in user sees each message once, in a popup, the next time they open the app. The rules for which message shows and the formatting codes are in `src/messages.js`. To preview the popup locally, open `http://localhost:8000/?messages`.

`firestore.rules` doesn't publish itself: after every change, paste it into the Firebase console (Firestore Database → Rules) and publish it, before deploying the pages that need it.

Preview locally with `python tools/serve.py`. The built-in goals are in `doelen/` (kleuter), `doelen-lager/` and `doelen-secundair/` (see its [README](doelen-secundair/README.md)), and the design files are in `src/design/` (see its [README](src/design/README.md)).
