// Tests for src/messages.js. Run: node --test "tests/*.test.mjs"
import test from 'node:test';
import assert from 'node:assert/strict';
import M from '../src/messages.js';

/* ---------- formatting codes ---------- */
test('heading on the first line becomes the title', () => {
  const r = M.render('# Vrolijk **kerst**\nTekst', new Set());
  assert.equal(r.title, 'Vrolijk kerst');
  assert.equal(r.html, '<p>Tekst</p>');
});
test('no leading heading: empty title', () => assert.equal(M.render('Tekst\n# Kop', new Set()).title, ''));
test('a later heading is a heading in the text', () => assert.equal(M.render('Tekst\n# Kop', new Set()).html, '<p>Tekst</p><h3>Kop</h3>'));
test('inline codes', () => assert.equal(M.render('**b** en *i*', new Set()).html, '<p><strong>b</strong> en <em>i</em></p>'));
test('paragraphs and line breaks', () => assert.equal(M.render('a\nb\n\nc', new Set()).html, '<p>a<br>b</p><p>c</p>'));
test('lists', () => {
  assert.equal(M.render('- a\n- b', new Set()).html, '<ul><li>a</li><li>b</li></ul>');
  assert.equal(M.render('1. a\n2. b', new Set()).html, '<ol><li>a</li><li>b</li></ol>');
});
test('subheading', () => assert.equal(M.render('x\n## Sub', new Set()).html, '<p>x</p><h4>Sub</h4>'));
test('raw HTML is shown as text', () => assert.equal(M.render('<img src=x onerror=alert(1)>', new Set()).html, '<p>&lt;img src=x onerror=alert(1)&gt;</p>'));
test('allowed links', () => assert.match(M.render('[site](https://doelenboek.be/?a=1&b=2)', new Set()).html, /<a href="https:\/\/doelenboek\.be\/\?a=1&amp;b=2" target="_blank" rel="noopener noreferrer">site<\/a>/));
test('mailto link', () => assert.match(M.render('[mail](mailto:a@b.be)', new Set()).html, /<a href="mailto:a@b\.be"/));
test('javascript: link stays text', () => assert.doesNotMatch(M.render('[x](javascript:alert(1))', new Set()).html, /<a /));
test('a quote in a link cannot break out of the attribute', () => assert.doesNotMatch(M.render('[x](https://a.be/"onmouseover="alert(1))', new Set()).html, /" onmouseover|"onmouseover="/));
test('known image', () => assert.equal(M.render('![Boom](img:ab12 hover)', new Set(['ab12'])).html,
  '<figure class="msg-fig"><img class="msg-img" data-img="ab12" data-zoom="hover" alt="Boom" style="width:100%"></figure>'));
test('unknown image id or zoom is dropped', () => {
  assert.equal(M.render('![x](img:zz99 click)', new Set(['ab12'])).html, '');
  assert.equal(M.render('![x](img:ab12 big)', new Set(['ab12'])).html, '');
});
test('imageRefs', () => assert.deepEqual(M.imageRefs('![a](img:x1 click)\n![b](img:y2 none)\n![c](img:x1 hover)'), ['x1', 'y2']));
test('firstLine strips codes and cuts at 80', () => {
  assert.equal(M.firstLine('\n# **Hallo** [daar](https://a.be)\nmeer'), 'Hallo daar');
  assert.equal(M.firstLine('x'.repeat(100)).length, 80);
});
test('empty text', () => assert.deepEqual(M.render('', new Set()), { title: '', html: '' }));

/* ---------- message rules ---------- */
// Months are 0-based (11 = December).
const day = (m, d, h = 12, y = 2026) => new Date(y, m, d, h).getTime();
const msg = (id, over = {}) => ({ langs: ['nl'], body: { nl: 'x' }, startAt: day(11, 1), endAt: day(11, 31), replace: false, newAccounts: false, createdAt: day(10, 30), ...over });

test('clean rejects bad records', () => {
  assert.equal(M.clean('a', msg('a', { langs: ['de'] })), null);
  assert.equal(M.clean('a', msg('a', { langs: ['nl', 'en'], body: { nl: 'x', en: '  ' } })), null);
  assert.equal(M.clean('a', msg('a', { endAt: day(11, 1) })), null);
  assert.equal(M.clean('a', msg('a', { startAt: 'soon' })), null);
  assert.equal(M.clean('a', null), null);
});
test('clean keeps a valid record', () => {
  const m = M.clean('a', msg('a', { langs: ['nl', 'en'], body: { nl: 'x', en: 'y' }, replace: true }));
  assert.deepEqual(m, { id: 'a', langs: ['nl', 'en'], body: { nl: 'x', en: 'y' }, startAt: day(11, 1), endAt: day(11, 31), replace: true, newAccounts: false, replacedBy: null, replacedAt: null, createdAt: day(10, 30) });
});
test('clean drops body of unlisted language', () => assert.deepEqual(M.clean('a', msg('a', { body: { nl: 'x', en: 'y' } })).body, { nl: 'x' }));
test('endFrom keeps the clock time', () => {
  assert.equal(M.endFrom(day(11, 24, 8), 30), day(0, 23, 8, 2027));
  assert.equal(M.endFrom(day(2, 20, 8, 2027), 30), day(3, 19, 8, 2027));   // across the 28 March 2027 DST change
});
test('status edges', () => {
  const m = M.clean('a', msg('a'));
  assert.equal(M.status(m, day(11, 1) - 1), 'scheduled');
  assert.equal(M.status(m, day(11, 1)), 'live');
  assert.equal(M.status(m, day(11, 31) - 1), 'live');
  assert.equal(M.status(m, day(11, 31)), 'ended');
  assert.equal(M.status({ ...m, replacedAt: day(11, 10) }, day(11, 10)), 'ended');
  assert.equal(M.effectiveEnd({ ...m, replacedAt: day(11, 10) }), day(11, 10));
});
test('pending: seen, new accounts, order', () => {
  const a = M.clean('a', msg('a', { startAt: day(11, 5) }));
  const b = M.clean('b', msg('b', { startAt: day(11, 2) }));
  const c = M.clean('c', msg('c', { startAt: day(11, 3), newAccounts: true }));
  const now = day(11, 10);
  assert.deepEqual(M.pending([a, b, c], { seen: [], createdAt: day(0, 1), now }).map(m => m.id), ['b', 'c', 'a']);
  assert.deepEqual(M.pending([a, b, c], { seen: ['b'], createdAt: day(0, 1), now }).map(m => m.id), ['c', 'a']);
  // account created 4 Dec: b (2 Dec) is hidden, c shows because newAccounts is on, a (5 Dec) started after the account
  assert.deepEqual(M.pending([a, b, c], { seen: [], createdAt: day(11, 4), now }).map(m => m.id), ['c', 'a']);
  assert.deepEqual(M.pending([a, b, c], { seen: [], createdAt: day(0, 1), now: day(11, 31) }), []);   // all ended
});
test('pending: not before the start, not after a replacement', () => {
  const a = M.clean('a', msg('a', { startAt: day(11, 5) }));
  const r = M.clean('r', msg('r', { startAt: day(11, 2), replacedBy: 'x', replacedAt: day(11, 4) }));
  assert.deepEqual(M.pending([a, r], { seen: [], createdAt: day(0, 1), now: day(11, 4) }), []);
});
test('replacements: earliest later replacing message wins', () => {
  const m = M.clean('m', msg('m', { startAt: day(11, 1), endAt: day(1, 28, 12, 2027) }));
  const r1 = M.clean('r1', msg('r1', { startAt: day(11, 24), replace: true }));
  const r2 = M.clean('r2', msg('r2', { startAt: day(11, 20), replace: true }));
  const later = M.clean('l', msg('l', { startAt: day(11, 26) }));
  const out = M.replacements([m, r1, r2, later], day(11, 1));
  assert.deepEqual(out.get('m'), { replacedBy: 'r2', replacedAt: day(11, 20) });
  assert.deepEqual(out.get('r2'), { replacedBy: 'r1', replacedAt: day(11, 24) });
  assert.equal(out.get('l'), null);   // starts after r1 and r2
  assert.equal(out.get('r1'), null);
});
test('replacements: no effect on a message that ended before R starts', () => {
  const m = M.clean('m', msg('m', { startAt: day(11, 1), endAt: day(11, 5) }));
  const r = M.clean('r', msg('r', { startAt: day(11, 6), replace: true }));
  assert.equal(M.replacements([m, r], day(11, 1)).get('m'), null);
});
test('replacements: an effective replacement stays after R is withdrawn', () => {
  const m = M.clean('m', msg('m', { replacedBy: 'gone', replacedAt: day(11, 3) }));
  assert.deepEqual(M.replacements([m], day(11, 10)).get('m'), { replacedBy: 'gone', replacedAt: day(11, 3) });
});
test('replacements: a scheduled replacement is recomputed', () => {
  const m = M.clean('m', msg('m', { replacedBy: 'gone', replacedAt: day(11, 20) }));
  assert.equal(M.replacements([m], day(11, 10)).get('m'), null);
});
test('seenCounts', () => {
  const c = M.seenCounts([{ data: { seen: ['a', 'b', 'a', 3] } }, { data: { seen: ['a'] } }, { data: null }, { data: {} }]);
  assert.equal(c.get('a'), 2); assert.equal(c.get('b'), 1); assert.equal(c.size, 2);
});

/* ---------- image codes without an image ---------- */
test('unknownImages lists codes whose image is missing', () => {
  assert.deepEqual(M.unknownImages('![a](img:x1 click)\n![b](img:y2 none)\n![c](img:y2 hover)', new Set(['x1'])), ['y2']);
  assert.deepEqual(M.unknownImages('no images', new Set()), []);
});

/* ---------- centring and image size ---------- */
test('a centred paragraph', () => assert.equal(M.render('-> Hallo **jij** <-', new Set()).html, '<p class="msg-c">Hallo <strong>jij</strong></p>'));
test('centred and plain lines become separate paragraphs', () => assert.equal(M.render('a\n-> b <-\n-> c <-\nd', new Set()).html, '<p>a</p><p class="msg-c">b<br>c</p><p>d</p>'));
test('a centred heading', () => assert.equal(M.render('x\n-> ## Sub <-', new Set()).html, '<p>x</p><h4 class="msg-c">Sub</h4>'));
test('centre markers on a list item are ignored', () => assert.equal(M.render('-> - a <-\n- b', new Set()).html, '<ul><li>a</li><li>b</li></ul>'));
test('a centred first-line heading is still the title', () => {
  const r = M.render('-> # Titel <-\nTekst', new Set());
  assert.equal(r.title, 'Titel'); assert.equal(r.html, '<p>Tekst</p>');
});
test('image size and centre', () => assert.equal(M.render('![a](img:ab12 click 50% center)', new Set(['ab12'])).html,
  '<figure class="msg-fig msg-c"><img class="msg-img" data-img="ab12" data-zoom="click" alt="a" style="width:50%"></figure>'));
test('an image between centre markers is centred', () => assert.equal(M.render('-> ![a](img:ab12 none 25%) <-', new Set(['ab12'])).html,
  '<figure class="msg-fig msg-c"><img class="msg-img" data-img="ab12" data-zoom="none" alt="a" style="width:25%"></figure>'));
test('a size outside 10-100% drops the image', () => {
  assert.equal(M.render('![a](img:ab12 click 5%)', new Set(['ab12'])).html, '');
  assert.equal(M.render('![a](img:ab12 click 150%)', new Set(['ab12'])).html, '');
});
test('imageRefs and firstLine read the new syntax', () => {
  assert.deepEqual(M.imageRefs('![a](img:x1 click 50% center)\n-> ![b](img:y2 none) <-'), ['x1', 'y2']);
  assert.equal(M.firstLine('-> **Hallo** <-'), 'Hallo');
});
test('parseImage and imageCode round trip', () => {
  assert.deepEqual(M.parseImage('-> ![Boom](img:ab12 hover 40%) <-'), { alt: 'Boom', id: 'ab12', zoom: 'hover', size: 40, center: true });
  assert.deepEqual(M.parseImage('![Boom](img:ab12 click)'), { alt: 'Boom', id: 'ab12', zoom: 'click', size: 100, center: false });
  assert.equal(M.parseImage('gewone tekst'), null);
  assert.equal(M.imageCode({ alt: 'Boom', id: 'ab12', zoom: 'click', size: 100, center: false }), '![Boom](img:ab12 click)');
  assert.equal(M.imageCode({ alt: 'Boom', id: 'ab12', zoom: 'none', size: 55, center: true }), '![Boom](img:ab12 none 55% center)');
});
