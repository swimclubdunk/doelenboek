/* Doelenboek admin: turns the raw Firestore records into the numbers the admin tabs show.
   Pure functions only (no DOM, no Firebase), so tests/admin-stats.test.mjs runs them in Node.
   tools/build.py inlines this file into admin/index.html.
   Names, titles and notes are dropped while cleaning: the admin page only ever holds counts. */
const AdminStats = (() => {
'use strict';
const DAY = 86400000;
const MAX_PHOTOS = 24;   // per activity, as in the app
const ID_RE = /^[A-Za-z0-9_\-~:@+.]{1,120}$/;
const num = v => typeof v === 'number' && isFinite(v) ? v : 0;
const ids = v => Array.isArray(v) ? [...new Set(v.filter(x => typeof x === 'string' && ID_RE.test(x)))] : [];
const named = v => typeof v === 'string' && v.trim() !== '';
const maxOf = arr => arr.reduce((m, v) => v > m ? v : m, 0);

/* The same rules as clean() in doelenboek.html: a child needs a name, an activity a title. */
function cleanChild(b, tierKeys) {
  if (!b || typeof b !== 'object' || b.example === true || !named(b.name)) return null;
  const m = b.mastered && typeof b.mastered === 'object' && !Array.isArray(b.mastered) ? Object.keys(b.mastered).filter(k => ID_RE.test(k)) : [];
  return { createdAt: num(b.createdAt), updatedAt: num(b.updatedAt), tier: tierKeys.includes(b.tier) ? b.tier : tierKeys[0], mastered: m };
}
function cleanActivity(b) {
  if (!b || typeof b !== 'object' || b.example === true || !named(b.title)) return null;
  return { createdAt: num(b.createdAt), updatedAt: num(b.updatedAt), childIds: ids(b.childIds), goalIds: ids(b.goalIds), photos: Math.min(ids(b.photoIds).length, MAX_PHOTOS) };
}
function cleanProfile(b) {
  if (!b || typeof b !== 'object') return null;
  return { email: typeof b.email === 'string' ? b.email.slice(0, 320) : '', createdAt: num(b.createdAt), lastSeen: num(b.lastSeen) };
}
const stamps = a => [...a.children, ...a.activities].flatMap(r => [r.createdAt, r.updatedAt]);

/* raw: { profiles, children, activities }, each a list of { uid, id, data } */
function buildDataset(raw, tierKeys = ['KO', 'L4', 'L6']) {
  const map = new Map();
  const acc = uid => {
    if (!map.has(uid)) map.set(uid, { uid, email: '', hasProfile: false, signupAt: 0, signupApprox: false, lastSeen: 0, lastActive: 0, children: [], activities: [] });
    return map.get(uid);
  };
  for (const r of raw.profiles || []) {
    const p = cleanProfile(r.data);
    if (!p) continue;
    Object.assign(acc(r.uid), { hasProfile: true, email: p.email, signupAt: p.createdAt, lastSeen: p.lastSeen });
  }
  for (const r of raw.children || []) { const c = cleanChild(r.data, tierKeys); if (c) acc(r.uid).children.push({ id: r.id, ...c }); }
  for (const r of raw.activities || []) { const x = cleanActivity(r.data); if (x) acc(r.uid).activities.push({ id: r.id, ...x }); }
  for (const a of map.values()) {
    a.children.sort((x, y) => x.createdAt - y.createdAt || (x.id < y.id ? -1 : 1));
    a.lastActive = Math.max(a.lastSeen, maxOf(stamps(a)));
    if (!a.signupAt) {
      const created = [...a.children, ...a.activities].map(r => r.createdAt).filter(Boolean);
      if (created.length) { a.signupAt = created.reduce((m, v) => v < m ? v : m); a.signupApprox = true; }
    }
  }
  return [...map.values()];
}

return { DAY, buildDataset };
})();
if (typeof module !== 'undefined') module.exports = AdminStats;
