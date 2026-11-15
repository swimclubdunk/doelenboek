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
  '<figure class="msg-fig"><img class="msg-img" data-img="ab12" data-zoom="hover" alt="Boom"></figure>'));
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
