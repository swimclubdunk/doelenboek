# 📒 Doelenboek

**https://doelenboek.be**

Doelenboek is for parents who homeschool in Flanders. Log what you do with your children, with photos, link it to the Flemish *minimumdoelen*, and see per child and per subject which goals have been covered and which are still open. It is free, in Dutch and English, and works on any device with an email-and-password account.

## Development

Build the site after a change:

```
python tools/build.py src/doelenboek.html index.html firebase-config.json
```

Preview locally with `python tools/serve.py`. The built-in goals are in `doelen/`, and the design files are in `src/design/` (see its [README](src/design/README.md)).
