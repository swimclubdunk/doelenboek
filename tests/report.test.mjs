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
