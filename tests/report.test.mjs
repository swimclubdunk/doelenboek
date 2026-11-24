// Tests for src/report.js. Run: node --test "tests/*.test.mjs"
import test from 'node:test';
import assert from 'node:assert/strict';
import R from '../src/report.js';

const act = (id, date, childIds, over = {}) => ({ id, date, title: 'Act ' + id, notes: '', childIds, goalIds: [], photoIds: [], createdAt: 0, ...over });

/* ---------- texts ---------- */
test('every report text exists in NL and EN, of the same kind', () => {
  const nl = Object.keys(R.TEXTS.nl).sort(), en = Object.keys(R.TEXTS.en).sort();
  assert.deepEqual(en, nl);
  for (const k of nl) assert.equal(typeof R.TEXTS.en[k], typeof R.TEXTS.nl[k], k);
});

/* ---------- periods ---------- */
test('school year: 31 August still belongs to the year that began the September before', () =>
  assert.deepEqual(R.periodRange('school', '2026-08-31'), { from: '2025-09-01', until: '2026-08-31' }));
test('school year: 1 September starts a new one', () =>
  assert.deepEqual(R.periodRange('school', '2026-09-01'), { from: '2026-09-01', until: '2027-08-31' }));
test('last 6 months: the same day six months back, up to today', () =>
  assert.deepEqual(R.periodRange('6m', '2026-11-24'), { from: '2026-05-24', until: '2026-11-24' }));
test('last 6 months: a day the earlier month lacks becomes its last day', () =>
  assert.deepEqual(R.periodRange('6m', '2026-08-31'), { from: '2026-02-28', until: '2026-08-31' }));
test('everything: no start, up to today', () =>
  assert.deepEqual(R.periodRange('all', '2026-11-24'), { from: null, until: '2026-11-24' }));
test('own dates are kept', () =>
  assert.deepEqual(R.periodRange('custom', '2026-11-24', '2026-01-01', '2026-03-31'), { from: '2026-01-01', until: '2026-03-31' }));
test('own dates the wrong way round are swapped', () =>
  assert.deepEqual(R.periodRange('custom', '2026-11-24', '2026-03-31', '2026-01-01'), { from: '2026-01-01', until: '2026-03-31' }));
test('a missing or invalid own date gives null', () => {
  assert.equal(R.periodRange('custom', '2026-11-24', '', '2026-01-01'), null);
  assert.equal(R.periodRange('custom', '2026-11-24', '2026-02-30', '2026-03-01'), null);
});
test('an unknown choice falls back to the school year', () =>
  assert.deepEqual(R.periodRange('bogus', '2026-11-24'), R.periodRange('school', '2026-11-24')));

/* ---------- selection ---------- */
test('activities of one child inside the period, both ends included, newest first', () => {
  const acts = [act('a', '2026-01-01', ['k']), act('b', '2026-03-31', ['k']), act('c', '2026-04-01', ['k']),
    act('d', '2025-12-31', ['k']), act('e', '2026-02-01', ['other']), act('f', '2026-02-01', ['k', 'other'], { createdAt: 5 }),
    act('g', '2026-02-01', ['k'], { createdAt: 9 })];
  const got = R.selectActivities(acts, 'k', { from: '2026-01-01', until: '2026-03-31' }).map(a => a.id);
  assert.deepEqual(got, ['b', 'g', 'f', 'a']);
});
test('no start date means everything up to the end', () => {
  const got = R.selectActivities([act('a', '2001-01-01', ['k']), act('b', '2030-01-01', ['k'])], 'k', { from: null, until: '2026-01-01' });
  assert.deepEqual(got.map(a => a.id), ['a']);
});
test('photo ids: at most 4 per activity, each id once, in order', () => {
  const acts = [act('a', '2026-01-01', ['k'], { photoIds: ['p1', 'p2', 'p3', 'p4', 'p5', 'p6'] }), act('b', '2026-01-02', ['k'], { photoIds: ['p2', 'p7'] })];
  assert.deepEqual(R.photoIdsFor(acts), ['p1', 'p2', 'p3', 'p4', 'p7']);
});

/* ---------- the document ---------- */
import { createRequire } from 'node:module';
const t = (k, ...a) => { const v = R.TEXTS.nl[k]; return typeof v === 'function' ? v(...a) : v; };
const fmt = { date: d => d, month: m => m };
const PNG = 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==';
const child = (id, over = {}) => ({ id, name: 'Kind ' + id, level: 'Kleuter', startDate: null, endDate: null, color: '#2773B0', mastered: {},
  goals: [{ id: 'g1', code: 'Kl 1.1', text: 'Rijmen', subject: 'Nederlands' }, { id: 'g2', code: 'Kl 1.2', text: 'Klanken', subject: 'Nederlands' },
    { id: 'g3', code: 'Kl 2.1', text: 'Tellen', subject: 'Wiskunde' }], ...over });
const input = over => ({ kind: 'global', range: { from: '2026-01-01', until: '2026-06-30' }, today: '2026-06-30', withPhotos: false,
  images: {}, missing: [], logo: null, t, fmt, children: [child('a'), child('b')], activities: [], ...over });
/* all text in a part of the document (images, SVG and functions left out) */
const allText = n => typeof n === 'string' ? n : Array.isArray(n) ? n.map(allText).join(' ')
  : n && typeof n === 'object' ? Object.entries(n).filter(([k]) => !['image', 'svg', 'images', 'layout'].includes(k)).map(([, v]) => allText(v)).join(' ') : '';
const breaks = doc => JSON.stringify(doc.content).split('"pageBreak":"before"').length - 1;

test('global report: the family overview first, every child on a new page', () => {
  const doc = R.buildReport(input());
  assert.equal(doc.content[0].text, t('rep_summary'));
  assert.equal(breaks(doc), 2);
});
test('report per child: no overview, no page break before the child', () => {
  const doc = R.buildReport(input({ kind: 'child', children: [child('a')] }));
  assert.doesNotMatch(allText(doc.content), new RegExp(t('rep_summary')));
  assert.equal(breaks(doc), 0);
});
test('goal status as at the end of the period: mastered later counts as open', () => {
  const c = child('a', { mastered: { g1: '2025-12-01', g2: '2026-03-01', g3: '2026-08-01' } });
  const text = allText(R.buildReport(input({ children: [c] })).content);
  assert.match(text, /beheerst 2025-12-01/);
  assert.match(text, /beheerst 2026-03-01/);
  assert.doesNotMatch(text, /2026-08-01/);
  assert.match(text, new RegExp(t('rep_totals', 2, 3, 1)));
  assert.match(text, /2 \/ 3/);   // summary: mastered in total / goals of the level
});
test('a child without activities in the period gets a line, not an error', () =>
  assert.match(allText(R.buildReport(input()).content), new RegExp(t('rep_no_acts'))));
test('a photo shared by two children is in the file once and shown in both parts', () => {
  const doc = R.buildReport(input({ withPhotos: true, images: { p1: PNG },
    activities: [{ id: 'x', date: '2026-02-01', title: 'Uitstap', notes: '', childIds: ['a', 'b'], goalIds: [], photoIds: ['p1'], createdAt: 0 }] }));
  assert.deepEqual(Object.keys(doc.images), ['p_p1']);
  assert.equal(JSON.stringify(doc.content).split('"image":"p_p1"').length - 1, 2);
});
test('without photos chosen no photo is shown, even when there are some', () => {
  const doc = R.buildReport(input({ images: { p1: PNG },
    activities: [{ id: 'x', date: '2026-02-01', title: 'Uitstap', notes: '', childIds: ['a'], goalIds: [], photoIds: ['p1'], createdAt: 0 }] }));
  assert.deepEqual(Object.keys(doc.images), []);
});
test('at most 4 photos per activity', () => {
  const ids = ['p1', 'p2', 'p3', 'p4', 'p5'];
  const doc = R.buildReport(input({ kind: 'child', children: [child('a')], withPhotos: true, images: Object.fromEntries(ids.map(i => [i, PNG])),
    activities: [{ id: 'x', date: '2026-02-01', title: 'Uitstap', notes: '', childIds: ['a'], goalIds: [], photoIds: ids, createdAt: 0 }] }));
  assert.equal(Object.keys(doc.images).length, 4);
});
test('goals of another level or deleted goals on an activity are left out, without an error', () => {
  const text = allText(R.buildReport(input({ kind: 'child', children: [child('a')],
    activities: [{ id: 'x', date: '2026-02-01', title: 'Uitstap', notes: 'n', childIds: ['a'], goalIds: ['g1', 'zz-other-level'], photoIds: [], createdAt: 0 }] })).content);
  assert.match(text, /Kl 1\.1/);
  assert.doesNotMatch(text, /zz-other-level/);
});
test('photos that could not be loaded are listed at the end', () => {
  const doc = R.buildReport(input({ missing: [{ date: '2026-02-01', title: 'Uitstap' }, { date: '', title: '' }] }));
  const text = allText(doc.content);
  assert.match(text, new RegExp(t('rep_missing', 2)));
  assert.match(text, /Uitstap/);
});
test('the chart counts mastered goals per month and stops at today', () => {
  const c = child('a', { mastered: { g1: '2025-12-01', g2: '2026-02-10', g3: '2026-03-20' } });
  assert.deepEqual(R.chartData(c, { from: '2026-01-01', until: '2026-06-30' }, '2026-03-15'), { months: ['2026-01', '2026-02', '2026-03'], values: [1, 2, 2] });
});
test('the chart over everything starts at the first mastered goal', () => {
  const c = child('a', { mastered: { g1: '2026-04-03' } });
  assert.deepEqual(R.chartData(c, { from: null, until: '2026-05-31' }, '2026-05-31'), { months: ['2026-04', '2026-05'], values: [1, 1] });
});
test('the chart keeps its first and last month names inside the picture', () => {
  const c = child('a', { mastered: { g1: '2026-02-10' } });
  const svg = R.buildReport(input({ kind: 'child', children: [c] })).content.find(n => n.svg).svg;
  assert.match(svg, /text-anchor="start"[^>]*>2026-01</);
  assert.match(svg, /text-anchor="end"[^>]*>2026-06</);
});
test('file names: date always, the child only for a report per child, unsafe characters replaced', () => {
  assert.equal(R.fileName('global', 'x', '2026-06-30', t), 'doelenboek-rapport-2026-06-30.pdf');
  assert.equal(R.fileName('child', 'Jan/Piet "J" 😀', '2026-06-30', t), 'doelenboek-rapport-Jan-Piet-J-2026-06-30.pdf');
  assert.equal(R.fileName('child', 'Aloïske', '2026-06-30', t), 'doelenboek-rapport-Aloïske-2026-06-30.pdf');
  assert.equal(R.fileName('child', '😀', '2026-06-30', t), 'doelenboek-rapport-kind-2026-06-30.pdf');
});
test('pdfmake makes a PDF of the description (vendored build, in Node)', async () => {
  const require = createRequire(import.meta.url);
  const pdfMake = require('../vendor/pdfmake/pdfmake.min.js');
  globalThis.pdfMake = pdfMake; require('../vendor/pdfmake/vfs_fonts.js');
  const c = child('a', { mastered: { g1: '2026-02-01' }, startDate: '2025-09-01', endDate: '2027-06-30' });
  // a JPEG: pdfmake's browser build decodes PNG in a Web Worker, which Node lacks (the PNG logo is checked in the browser)
  const JPG = 'data:image/jpeg;base64,/9j/4AAQSkZJRgABAQEASABIAAD/2wBDAP//////////////////////////////////////////////////////////////////////////////////////wgALCAABAAEBAREA/8QAFBABAAAAAAAAAAAAAAAAAAAAAP/aAAgBAQABPxA=';
  const doc = R.buildReport(input({ children: [c, child('b')], withPhotos: true, images: { p1: JPG }, logo: JPG, missing: [{ date: '2026-02-01', title: 'Weg' }],
    activities: [{ id: 'x', date: '2026-02-01', title: 'Uitstap', notes: 'Naar het bos', childIds: ['a', 'b'], goalIds: ['g1'], photoIds: ['p1'], createdAt: 0 }] }));
  const buf = await pdfMake.createPdf(doc).getBuffer();
  assert.equal(Buffer.from(buf).subarray(0, 5).toString(), '%PDF-');
});
