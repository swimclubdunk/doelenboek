/* Doelenboek admin: turns the raw Firestore records into the numbers the admin tabs show.
   Pure functions only (no DOM, no Firebase), so tests/admin-stats.test.mjs runs them in Node.
   tools/build.py inlines this file into admin/index.html.
   Names, titles and notes are dropped while cleaning: the admin page only ever holds counts. */
const AdminStats = (() => {
'use strict';
const DAY = 86400000;
const MAX_PHOTOS = 24;   // per activity, as in the app
const ID_RE = /^[A-Za-z0-9_\-~:@+.]{1,120}$/;
/* A timestamp a user's own records could hold: anything outside 2020–2100 (huge, negative, in seconds) counts as unknown. */
const T_MIN = Date.UTC(2020, 0, 1), T_MAX = Date.UTC(2100, 0, 1);
const num = v => typeof v === 'number' && v >= T_MIN && v < T_MAX ? v : 0;
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

const pct = (n, d) => d ? Math.round(100 * n / d) : 0;
const sum = (arr, f) => arr.reduce((s, x) => s + f(x), 0);

/* ---------- time: weeks start on Monday, everything in local time ---------- */
function weekStart(ts) {
  const d = new Date(ts);
  d.setHours(0, 0, 0, 0);
  d.setDate(d.getDate() - (d.getDay() + 6) % 7);
  return d.getTime();
}
function monthStart(ts) { const d = new Date(ts); return new Date(d.getFullYear(), d.getMonth(), 1).getTime(); }
function periodStarts(period, now, earliest = 0) {
  const out = [];
  if (period === 'weeks') {
    const w = new Date(weekStart(now));
    for (let i = 11; i >= 0; i--) out.push(new Date(w.getFullYear(), w.getMonth(), w.getDate() - 7 * i).getTime());
    return out;
  }
  const n = new Date(now);
  if (period === 'months') {
    for (let i = 11; i >= 0; i--) out.push(new Date(n.getFullYear(), n.getMonth() - i, 1).getTime());
    return out;
  }
  const e = new Date(monthStart(earliest && earliest < now ? earliest : now));
  for (let d = e; d.getTime() <= now; d = new Date(d.getFullYear(), d.getMonth() + 1, 1)) out.push(d.getTime());
  return out;
}
/* index of the period ts falls in; -1 before the first; anything after now counts in the last */
function bucketOf(starts, ts) {
  if (!ts || ts < starts[0]) return -1;
  let i = starts.length - 1;
  while (starts[i] > ts) i--;
  return i;
}

/* ---------- activity ---------- */
const isActive = (a, now, days) => a.lastActive > 0 && now - a.lastActive <= days * DAY;
const isInactive = (a, now) => !a.lastActive || now - a.lastActive > 90 * DAY;

/* An account is active in a week when it created or changed a record that week, or opened the app (lastSeen). */
function activeWeekly(accounts, now) {
  const starts = periodStarts('weeks', now);
  const counts = starts.map(() => 0);
  for (const a of accounts) {
    const weeks = new Set([...stamps(a), a.lastSeen].map(ts => bucketOf(starts, ts)).filter(i => i >= 0));
    for (const i of weeks) counts[i]++;
  }
  return starts.map((start, i) => ({ start, count: counts[i] }));
}

/* ---------- tabs ---------- */
function overview(accounts, now) {
  const ms = monthStart(now);
  const kids = accounts.flatMap(a => a.children), acts = accounts.flatMap(a => a.activities);
  const active30 = accounts.filter(a => isActive(a, now, 30)).length;
  return {
    accounts: accounts.length, accountsThisMonth: accounts.filter(a => a.signupAt >= ms).length,
    active30, active30Pct: pct(active30, accounts.length),
    children: kids.length, childrenThisMonth: kids.filter(c => c.createdAt >= ms).length,
    activities: acts.length, activitiesThisMonth: acts.filter(x => x.createdAt >= ms).length,
    activeWeekly: activeWeekly(accounts, now),
    recent: accounts.filter(a => a.lastActive).sort((x, y) => y.lastActive - x.lastActive).slice(0, 8)
      .map(a => ({ uid: a.uid, email: a.email, lastActive: a.lastActive })),
  };
}

function growth(accounts, period, now) {
  const kids = accounts.flatMap(a => a.children), acts = accounts.flatMap(a => a.activities);
  const firsts = [...accounts.map(a => a.signupAt), ...kids.map(c => c.createdAt), ...acts.map(x => x.createdAt)].filter(Boolean);
  const starts = periodStarts(period, now, firsts.length ? firsts.reduce((m, v) => v < m ? v : m) : 0);
  const rows = starts.map(start => ({ start, accounts: 0, children: 0, activities: 0, total: 0 }));
  let before = 0;
  for (const a of accounts) { const i = bucketOf(starts, a.signupAt); if (i >= 0) rows[i].accounts++; else if (a.signupAt) before++; }
  for (const c of kids) { const i = bucketOf(starts, c.createdAt); if (i >= 0) rows[i].children++; }
  for (const x of acts) { const i = bucketOf(starts, x.createdAt); if (i >= 0) rows[i].activities++; }
  let total = before;
  for (const r of rows) { total += r.accounts; r.total = total; }
  return { totals: { accounts: accounts.length, children: kids.length, activities: acts.length, photos: sum(acts, x => x.photos) }, rows };
}

function usage(accounts, now) {
  const all = accounts.length;
  const step = (key, count) => ({ key, count, pct: pct(count, all) });
  return {
    active7: accounts.filter(a => isActive(a, now, 7)).length,
    active30: accounts.filter(a => isActive(a, now, 30)).length,
    inactive90: accounts.filter(a => isInactive(a, now)).length,
    neverLogged: accounts.filter(a => !a.activities.length).length,
    funnel: [step('account', all), step('child', accounts.filter(a => a.children.length).length),
      step('activity', accounts.filter(a => a.activities.length).length), step('ten', accounts.filter(a => a.activities.length >= 10).length)],
    activeWeekly: activeWeekly(accounts, now),
  };
}

const goalRow = g => ({ id: g.id, subject: g.subject, tier: g.tier, code: g.code, description: g.description });

function content(accounts, goals, subjectKeys, tierKeys) {
  const byId = new Map(goals.map(g => [g.id, g]));
  const kids = accounts.flatMap(a => a.children), acts = accounts.flatMap(a => a.activities);
  const subj = new Map(subjectKeys.map(k => [k, 0]));
  const actsPerGoal = new Map(), masteredPerGoal = new Map();
  let links = 0, unknown = 0;
  for (const x of acts) for (const id of x.goalIds) {
    links++;
    const g = byId.get(id);
    if (g && subj.has(g.subject)) subj.set(g.subject, subj.get(g.subject) + 1); else unknown++;
    actsPerGoal.set(id, (actsPerGoal.get(id) || 0) + 1);
  }
  for (const c of kids) for (const id of c.mastered) masteredPerGoal.set(id, (masteredPerGoal.get(id) || 0) + 1);
  const bySubject = [...subj].filter(([, n]) => n).sort((x, y) => y[1] - x[1]).map(([key, count]) => ({ key, count, pct: pct(count, links) }));
  if (unknown) bySubject.push({ key: '?', count: unknown, pct: pct(unknown, links) });
  return {
    bySubject,
    byTier: tierKeys.map(key => { const count = kids.filter(c => c.tier === key).length; return { key, count, pct: pct(count, kids.length) }; }),
    photos: { total: sum(acts, x => x.photos), withPhotoPct: pct(acts.filter(x => x.photos).length, acts.length), avgGoals: acts.length ? links / acts.length : 0 },
    topGoals: [...actsPerGoal].filter(([id]) => byId.has(id)).sort((x, y) => y[1] - x[1] || (x[0] < y[0] ? -1 : 1)).slice(0, 10)
      .map(([id, n]) => ({ ...goalRow(byId.get(id)), activities: n, mastered: masteredPerGoal.get(id) || 0 })),
    neverLinked: goals.filter(g => !actsPerGoal.has(g.id)).map(goalRow),
  };
}

function accountRows(accounts, { query = '', filter = 'all', sort = 'lastActive', dir = 'desc' } = {}, now) {
  const q = query.trim().toLowerCase();
  const rows = accounts
    .filter(a => filter === 'active' ? isActive(a, now, 30) : filter === 'inactive' ? isInactive(a, now) : true)
    .filter(a => !q || a.email.toLowerCase().includes(q) || a.uid.toLowerCase().includes(q))
    .map(a => ({ uid: a.uid, email: a.email, hasProfile: a.hasProfile, signupAt: a.signupAt, signupApprox: a.signupApprox, lastActive: a.lastActive,
      children: a.children.length, activities: a.activities.length, photos: sum(a.activities, x => x.photos) }));
  const sign = dir === 'asc' ? 1 : -1;
  const key = sort === 'email' ? (x, y) => (x.email || x.uid).localeCompare(y.email || y.uid, 'nl', { sensitivity: 'base', numeric: true }) : (x, y) => x[sort] - y[sort];
  return rows.sort((x, y) => sign * key(x, y) || (x.uid < y.uid ? -1 : x.uid > y.uid ? 1 : 0));
}

function accountDetail(a) {
  return {
    uid: a.uid,
    lastChange: maxOf(stamps(a)),
    kids: a.children.map((c, i) => ({ label: `Kind ${i + 1}`, tier: c.tier, activities: a.activities.filter(x => x.childIds.includes(c.id)).length, mastered: c.mastered.length })),
  };
}

function relDays(ts, now) {
  if (!ts) return '—';
  const midnight = t => { const d = new Date(t); return new Date(d.getFullYear(), d.getMonth(), d.getDate()).getTime(); };
  const d = Math.max(0, Math.round((midnight(now) - midnight(ts)) / DAY));
  if (d === 0) return 'vandaag';
  if (d === 1) return 'gisteren';
  if (d < 31) return `${d} d geleden`;
  if (d < 365) return `${Math.floor(d / 30)} mnd geleden`;
  return `${Math.floor(d / 365)} j geleden`;
}

return { DAY, pct, buildDataset, weekStart, monthStart, periodStarts, isActive, isInactive, activeWeekly, overview, growth, usage, content, accountRows, accountDetail, relDays };
})();
if (typeof module !== 'undefined') module.exports = AdminStats;
