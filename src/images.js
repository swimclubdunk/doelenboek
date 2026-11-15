/* Doelenboek: image compression shared by the app (activity photos) and the admin page (message images).
   Decode, downscale and JPEG-encode in the browser; steps down until the base64 data fits maxB64.
   tools/build.py inlines this file into both pages. */
const Images = (() => {
'use strict';
async function process(file, maxB64) {
  let src, cleanup = () => {};
  try { src = await createImageBitmap(file, { imageOrientation: 'from-image' }); cleanup = () => src.close && src.close(); }
  catch (e) {
    const url = URL.createObjectURL(file), img = new Image();
    img.src = url;
    try { await img.decode(); } catch (er) { URL.revokeObjectURL(url); throw er; }
    src = img; cleanup = () => URL.revokeObjectURL(url);
  }
  try {
    const W = src.naturalWidth || src.width, H = src.naturalHeight || src.height;
    if (!W || !H) throw new Error('empty image');
    const steps = [[1600, .82], [1280, .78], [1024, .74], [800, .7], [640, .65]];
    for (let i = 0; i < steps.length; i++) {
      const [max, q] = steps[i], s = Math.min(1, max / Math.max(W, H));
      const w = Math.max(1, Math.round(W * s)), h = Math.max(1, Math.round(H * s));
      const c = document.createElement('canvas'); c.width = w; c.height = h;
      const g = c.getContext('2d'); g.fillStyle = '#fff'; g.fillRect(0, 0, w, h); g.drawImage(src, 0, 0, w, h);
      const url = c.toDataURL('image/jpeg', q), data = url.slice(url.indexOf(',') + 1);
      if (data.length <= maxB64 || i === steps.length - 1) return { mime: 'image/jpeg', w, h, data };
    }
  } finally { cleanup(); }
}
return { process };
})();
if (typeof module !== 'undefined') module.exports = Images;
