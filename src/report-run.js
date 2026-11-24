/* Doelenboek reports in the browser: loads pdfmake from our own site the first time a report is made, shrinks the
   photos, turns Report's document description into a PDF and offers it as a download. tools/build.py inlines this file. */
const ReportRun = (() => {
'use strict';
const PDFMAKE = ['vendor/pdfmake/pdfmake.min.js', 'vendor/pdfmake/vfs_fonts.js'];   // copied to the site by tools/build.py
const MAX_SIDE = 1000, QUALITY = 0.75, AT_ONCE = 3;
let loading = null;

function loadScript(src) {
  return new Promise((res, rej) => {
    const s = document.createElement('script');
    s.src = src; s.onload = res;
    s.onerror = () => { s.remove(); rej(new Error('offline')); };
    document.head.appendChild(s);
  });
}
/* once per page; a failed load is tried again on the next report */
function loadPdfMake() {
  if (!loading) loading = (async () => { for (const src of PDFMAKE) await loadScript(src); if (!window.pdfMake?.createPdf) throw new Error('offline'); })()
    .catch(e => { loading = null; throw e; });
  return loading;
}
/* A stored photo ({mime, w, h, data}) as a data URL pdfmake can use: JPEG or PNG of at most MAX_SIDE pixels are used as
   they are; larger ones and WebP (which pdfmake cannot read) are drawn again as JPEG. */
async function shrink(rec) {
  if ((rec.mime === 'image/jpeg' || rec.mime === 'image/png') && rec.w && rec.h && Math.max(rec.w, rec.h) <= MAX_SIDE) return `data:${rec.mime};base64,${rec.data}`;
  const bin = atob(rec.data), arr = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) arr[i] = bin.charCodeAt(i);
  const bmp = await createImageBitmap(new Blob([arr], { type: rec.mime }));
  try {
    const s = Math.min(1, MAX_SIDE / Math.max(bmp.width, bmp.height));
    const c = document.createElement('canvas'); c.width = Math.max(1, Math.round(bmp.width * s)); c.height = Math.max(1, Math.round(bmp.height * s));
    const g = c.getContext('2d'); g.fillStyle = '#fff'; g.fillRect(0, 0, c.width, c.height); g.drawImage(bmp, 0, 0, c.width, c.height);
    return c.toDataURL('image/jpeg', QUALITY);
  } finally { bmp.close?.(); }
}
async function pool(items, fn, onDone) {
  let i = 0, done = 0;
  const worker = async () => { while (i < items.length) { const it = items[i++]; await fn(it); onDone(++done); } };
  await Promise.all(Array.from({ length: Math.min(AT_ONCE, items.length) }, worker));
}
async function dataUrl(path) {
  try { const b = await (await fetch(path)).blob(); return await new Promise((res, rej) => { const r = new FileReader(); r.onload = () => res(r.result); r.onerror = rej; r.readAsDataURL(b); }); }
  catch (e) { return null; }   // the report works without its logo
}
function save(blob, name) {
  const url = URL.createObjectURL(blob), a = document.createElement('a');
  a.href = url; a.download = name; document.body.appendChild(a); a.click(); a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 60000);   // iOS opens the PDF in a new view; give it time to read the blob
}

async function run({ photoIds, getPhoto, build, fileName, onProgress }) {
  const pdfReady = loadPdfMake();   // pdfmake downloads while the photos are shrunk
  pdfReady.catch(() => {});
  const logoReady = dataUrl('logo.png');
  const images = {}, failed = [];
  if (photoIds.length) onProgress('photos', 0, photoIds.length);
  await pool(photoIds, async id => {
    try { const rec = await getPhoto(id); if (!rec) throw new Error('missing'); images[id] = await shrink(rec); }
    catch (e) { failed.push(id); }
  }, n => onProgress('photos', n, photoIds.length));
  if (failed.length && navigator.onLine === false) throw new Error('offline');
  onProgress('pdf');
  await pdfReady;
  const doc = build({ images, failed, logo: await logoReady });
  save(await window.pdfMake.createPdf(doc).getBlob(), fileName);
}

return { run };
})();
