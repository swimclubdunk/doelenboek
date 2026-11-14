// Tests for src/admin-stats.js. Run: node --test "tests/*.test.mjs"
import test from 'node:test';
import assert from 'node:assert/strict';
import S from '../src/admin-stats.js';

// "now" is Saturday 14 Nov 2026, 12:00 local time. Months are 0-based (10 = November).
export const NOW = new Date(2026, 10, 14, 12).getTime();
export const day = (m, d, h = 12, y = 2026) => new Date(y, m, d, h).getTime();

export const RAW = {
  profiles: [
    { uid: 'u1', id: 'main', data: { email: 'An@Example.be', createdAt: day(2, 12), lastSeen: day(10, 14, 9) } },
    { uid: 'u4', id: 'main', data: { email: 'x@y.be', createdAt: day(10, 10), lastSeen: day(10, 10) } },
    { uid: 'u9', id: 'main', data: null },
  ],
  children: [
    { uid: 'u1', id: 'c2', data: { name: 'Bo', tier: 'L4', createdAt: day(3, 1), updatedAt: day(10, 1), mastered: { 'b-NL-1.1.2': '2026-10-01', 'bad id!': 'x' } } },
    { uid: 'u1', id: 'c1', data: { name: 'Ada', tier: 'XX', createdAt: day(2, 20), updatedAt: 0 } },
    { uid: 'u1', id: 'cx', data: { name: 'Voorbeeld', example: true, createdAt: day(2, 12) } },
    { uid: 'u2', id: 'k1', data: { name: '  ', createdAt: day(5, 1) } },
    { uid: 'u2', id: 'k2', data: { name: 'Cas', tier: 'L6', createdAt: day(5, 2), updatedAt: day(7, 3) } },
  ],
  activities: [
    { uid: 'u1', id: 'a1', data: { title: 'Lezen', createdAt: day(9, 1), updatedAt: day(9, 2), childIds: ['c1', 'c2', 'c1'], goalIds: ['b-NL-1.1.2', 'b-??', 'zz'], photoIds: ['p1', 'p2'] } },
    { uid: 'u2', id: 'a2', data: { title: '', createdAt: day(6, 1) } },
    { uid: 'u2', id: 'a3', data: { title: 'Tellen', createdAt: 'gisteren', updatedAt: day(7, 1), goalIds: 'nope', photoIds: Array.from({ length: 30 }, (_, i) => 'p' + i) } },
    { uid: 'u3', id: 'a4', data: { title: 'Voorbeeld', example: true, createdAt: day(1, 1) } },
  ],
};
export const accounts = () => S.buildDataset(RAW);

test('buildDataset: one account per uid with real data or a profile; example-only uids are left out', () => {
  assert.deepEqual(accounts().map(a => a.uid), ['u1', 'u4', 'u2']);
});

test('buildDataset: profile fields, children sorted by createdAt, invalid tier falls back to KO, names dropped', () => {
  const u1 = accounts()[0];
  assert.equal(u1.email, 'An@Example.be');
  assert.equal(u1.hasProfile, true);
  assert.equal(u1.signupAt, day(2, 12));
  assert.equal(u1.signupApprox, false);
  assert.deepEqual(u1.children.map(c => [c.id, c.tier]), [['c1', 'KO'], ['c2', 'L4']]);
  assert.deepEqual(u1.children[1].mastered, ['b-NL-1.1.2']);
  assert.equal('name' in u1.children[0], false);
  assert.equal(u1.lastActive, day(10, 14, 9));
});

test('buildDataset: activities are de-duplicated and cleaned, photos capped at 24, titles dropped', () => {
  const [u1, , u2] = accounts();
  const a1 = u1.activities[0];
  assert.deepEqual(a1.childIds, ['c1', 'c2']);
  assert.deepEqual(a1.goalIds, ['b-NL-1.1.2', 'zz']);
  assert.equal(a1.photos, 2);
  assert.equal('title' in a1, false);
  assert.deepEqual(u2.activities.map(a => a.id), ['a3']);
  assert.equal(u2.activities[0].createdAt, 0);
  assert.deepEqual(u2.activities[0].goalIds, []);
  assert.equal(u2.activities[0].photos, 24);
});

test('buildDataset: an account without a profile gets an approximate sign-up date and last-active from its records', () => {
  const u2 = accounts()[2];
  assert.equal(u2.hasProfile, false);
  assert.equal(u2.email, '');
  assert.deepEqual(u2.children.map(c => c.id), ['k2']);
  assert.equal(u2.signupAt, day(5, 2));
  assert.equal(u2.signupApprox, true);
  assert.equal(u2.lastActive, day(7, 3));
});

test('buildDataset: profile-only account has no children or activities; last active is its last visit', () => {
  const u4 = accounts()[1];
  assert.equal(u4.children.length, 0);
  assert.equal(u4.activities.length, 0);
  assert.equal(u4.lastActive, day(10, 10));
});

test('buildDataset: empty or missing input gives no accounts', () => {
  assert.deepEqual(S.buildDataset({}), []);
  assert.deepEqual(S.buildDataset({ profiles: [], children: [], activities: [] }), []);
});
