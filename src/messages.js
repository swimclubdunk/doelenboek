/* Doelenboek admin messages: the formatting codes and the rules for which message a user sees.
   Pure functions only (no DOM, no Firebase), so tests/messages.test.mjs runs them in Node.
   tools/build.py inlines this file into both the app (index.html) and the admin page (admin/index.html),
   so the admin's preview and the user's popup render a message with the same code. */
const Messages = (() => {
'use strict';
const ZOOMS = ['click', 'hover', 'none'];
const IMG_LINE = /^!\[([^\]]*)\]\(img:([A-Za-z0-9]{1,20})\s+([a-z]+)\)\s*$/;
const IMG_ANY = /!\[[^\]]*\]\(img:([A-Za-z0-9]{1,20})\s+[a-z]+\)/g;
const LINK = /\[([^\]]+)\]\(([^)\s]+)\)/g;
const SAFE_URL = /^(https?:\/\/|mailto:)/i;

const esc = s => String(s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
/* bold and italic, on text that is already escaped (escaping leaves * alone) */
const emph = s => s.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>').replace(/\*(.+?)\*/g, '<em>$1</em>');
/* one line of text: links with a safe scheme become <a>, everything else is escaped, then bold/italic */
function inline(raw) {
  let out = '', last = 0;
  for (const m of raw.matchAll(LINK)) {
    out += emph(esc(raw.slice(last, m.index)));
    out += SAFE_URL.test(m[2]) ? `<a href="${esc(m[2])}" target="_blank" rel="noopener noreferrer">${emph(esc(m[1]))}</a>` : emph(esc(m[0]));
    last = m.index + m[0].length;
  }
  return out + emph(esc(raw.slice(last)));
}
/* plain text of one line: block markers, links, images and bold/italic codes removed */
const plain = line => line.trim()
  .replace(/^(#{1,2}\s+|-\s+|\d+\.\s+)/, '')
  .replace(/!\[([^\]]*)\]\([^)]*\)/g, '$1')
  .replace(LINK, '$1')
  .replace(/\*\*(.+?)\*\*/g, '$1').replace(/\*(.+?)\*/g, '$1')
  .trim();
const linesOf = text => String(text || '').replace(/\r\n?/g, '\n').split('\n');

/* Message text in formatting codes -> { title, html }. A '# ' heading on the first non-empty line is the
   title (plain, escaped) and is left out of html. imageIds: the ids of the images this message holds. */
function render(text, imageIds) {
  const lines = linesOf(text);
  let title = '';
  const first = lines.findIndex(l => l.trim() !== '');
  if (first >= 0 && /^#\s+\S/.test(lines[first])) { title = esc(plain(lines[first])); lines.splice(first, 1); }
  const out = [];
  let para = [], list = null;   // list: { tag, items }
  const flush = () => {
    if (para.length) { out.push(`<p>${para.join('<br>')}</p>`); para = []; }
    if (list) { out.push(`<${list.tag}>${list.items.map(i => `<li>${i}</li>`).join('')}</${list.tag}>`); list = null; }
  };
  const item = (tag, html) => {
    if (para.length || (list && list.tag !== tag)) flush();
    if (!list) list = { tag, items: [] };
    list.items.push(html);
  };
  for (const line of lines) {
    let m;
    if (line.trim() === '') { flush(); continue; }
    if ((m = IMG_LINE.exec(line.trim()))) {
      flush();
      const [, alt, id, zoom] = m;
      if (imageIds && imageIds.has(id) && ZOOMS.includes(zoom))
        out.push(`<figure class="msg-fig"><img class="msg-img" data-img="${id}" data-zoom="${zoom}" alt="${esc(alt)}"></figure>`);
      continue;
    }
    if ((m = /^##\s+(.*)$/.exec(line))) { flush(); out.push(`<h4>${inline(m[1].trim())}</h4>`); continue; }
    if ((m = /^#\s+(.*)$/.exec(line))) { flush(); out.push(`<h3>${inline(m[1].trim())}</h3>`); continue; }
    if ((m = /^-\s+(.*)$/.exec(line))) { item('ul', inline(m[1].trim())); continue; }
    if ((m = /^\d+\.\s+(.*)$/.exec(line))) { item('ol', inline(m[1].trim())); continue; }
    if (list) flush();
    para.push(inline(line.trim()));
  }
  flush();
  return { title, html: out.join('') };
}

/* The image ids a text refers to, in order of first appearance. */
const imageRefs = text => [...new Set([...String(text || '').matchAll(IMG_ANY)].map(m => m[1]))];

/* The first non-empty line as plain text, at most 80 characters: the message's name in the admin list. */
function firstLine(text) {
  const line = linesOf(text).find(l => plain(l) !== '');
  return line ? plain(line).slice(0, 80) : '';
}

return { ZOOMS, render, imageRefs, firstLine };
})();
if (typeof module !== 'undefined') module.exports = Messages;
