/* Doelenboek: enlarging the images in a message (data-zoom="click" | "hover" | "none", see messages.js).
   Shared by the app's message popup and the admin page's preview, so both behave the same.
   tools/build.py inlines this file into both pages. Styles: .msg-hover and dialog.msgzoom in design/app.css. */
const MessageZoom = (() => {
'use strict';
/* phones and tablets have no hover: there "enlarge on hover" works as "enlarge on click" */
const noHover = () => !!(window.matchMedia && matchMedia('(hover: none)').matches);
let dlg = null;
function zoomDialog() {
  if (dlg) return dlg;
  dlg = document.createElement('dialog');
  dlg.className = 'msgzoom';
  dlg.innerHTML = '<img alt="">';
  document.body.append(dlg);
  dlg.addEventListener('click', () => dlg.close());
  dlg.addEventListener('close', () => dlg.querySelector('img').removeAttribute('src'));
  return dlg;
}
function open(img) {
  const d = zoomDialog(), z = d.querySelector('img');
  z.src = img.src; z.alt = img.alt;
  if (typeof d.showModal === 'function') d.showModal(); else d.setAttribute('open', '');
}
/* the hover copy goes inside root, so it stays above root when root is a modal dialog */
const hide = root => { const h = root.querySelector('.msg-hover'); if (h) h.remove(); };
function attach(root) {
  root.addEventListener('click', e => {
    const img = e.target.closest && e.target.closest('img[data-zoom]');
    if (img && img.src && (img.dataset.zoom === 'click' || (img.dataset.zoom === 'hover' && noHover()))) { hide(root); open(img); }
  });
  root.addEventListener('pointerover', e => {
    const img = e.target.closest && e.target.closest('img[data-zoom="hover"]');
    if (!img || !img.src || e.pointerType !== 'mouse' || noHover() || root.querySelector('.msg-hover')) return;
    const box = document.createElement('div'), big = document.createElement('img');
    box.className = 'msg-hover'; box.setAttribute('aria-hidden', 'true');
    big.src = img.src; big.alt = ''; box.append(big);
    root.append(box);
  });
  root.addEventListener('pointerout', e => { if (e.target.closest && e.target.closest('img[data-zoom="hover"]')) hide(root); });
}
return { attach, hide };
})();
if (typeof module !== 'undefined') module.exports = MessageZoom;
