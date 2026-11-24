/* Doelenboek reports: the texts, the period and selection rules and the PDF document description (pdfmake).
   Pure functions only (no DOM, no Firebase, no pdfmake), so tests/report.test.mjs runs them in Node.
   tools/build.py inlines this file into the app; src/report-run.js turns the description into a PDF. */
const Report = (() => {
'use strict';
const PHOTOS_PER_ACTIVITY = 4;
const PHOTO_WARN = 300;
const PERIODS = ['school', '6m', 'all', 'custom'];
/* the light subject colours of src/design/tokens.css, by the keys the dashboard gives children (DASH_COLORS) */
const COLORS = { wk: '#2773B0', ge: '#A5631E', nl: '#0BB9BB', mv: '#8F4E88', wt: '#0A8257', lo: '#E98D90', at: '#A297E9', ak: '#9DA244' };

const TEXTS = {
  nl: {
    rep_type: 'Soort rapport', rep_global: 'Globaal rapport', rep_child: 'Rapport per kind',
    rep_children: 'Kinderen', rep_pick_child: 'Kind', rep_no_kids: 'Voeg eerst een kind toe om een rapport te maken.',
    rep_period: 'Periode', rep_p_school: 'Dit schooljaar', rep_p_6m: 'Laatste 6 maanden', rep_p_all: 'Alles', rep_p_custom: 'Eigen data',
    rep_from: 'Van', rep_until: 'Tot', rep_photos: "Met foto's", rep_download: 'Download',
    rep_need_child: 'Kies minstens één kind.', rep_need_dates: 'Vul beide data in.',
    rep_prog_photos: (n, tot) => `Foto's verkleinen: ${n} van ${tot}…`, rep_prog_pdf: 'PDF maken…',
    rep_err_offline: 'Kon het rapport niet maken: geen verbinding. Probeer opnieuw.',
    rep_err: m => `Kon het rapport niet maken: ${m}`,
    rep_warn_h: "Veel foto's", rep_warn_p: n => `Dit rapport heeft ${n} foto's en kan traag zijn. Toch doorgaan?`, rep_warn_go: 'Toch doorgaan',
    rep_title: 'Rapport', rep_summary: 'Gezinsoverzicht',
    rep_made: d => `aangemaakt op ${d}`, rep_page: (p, n) => `pagina ${p} van ${n}`,
    rep_range: (a, b) => `${a} – ${b}`, rep_range_all: b => `alle gegevens tot ${b}`,
    rep_col_child: 'Kind', rep_col_level: 'Niveau', rep_col_new: 'Beheerst in periode', rep_col_total: 'Beheerst totaal', rep_col_acts: 'Activiteiten',
    rep_start: 'Begindatum', rep_end: 'Einddatum',
    rep_totals: (n, tot, k) => `${n} van ${tot} doelen beheerst, waarvan ${k} in deze periode`,
    rep_chart: 'Beheerste doelen, per maand',
    rep_goals: 'Doelen', rep_col_code: 'Code', rep_col_goal: 'Doel', rep_col_status: 'Status', rep_col_n: 'Act.',
    rep_done: d => `beheerst ${d}`, rep_open: 'open',
    rep_acts: 'Activiteiten', rep_no_acts: 'Geen activiteiten in deze periode.',
    rep_missing: n => n === 1 ? '1 foto kon niet geladen worden' : `${n} foto's konden niet geladen worden`,
    rep_file: 'rapport',
  },
  en: {
    rep_type: 'Kind of report', rep_global: 'Global report', rep_child: 'Report per child',
    rep_children: 'Children', rep_pick_child: 'Child', rep_no_kids: 'Add a child first to make a report.',
    rep_period: 'Period', rep_p_school: 'This school year', rep_p_6m: 'Last 6 months', rep_p_all: 'Everything', rep_p_custom: 'Own dates',
    rep_from: 'From', rep_until: 'Until', rep_photos: 'With photos', rep_download: 'Download',
    rep_need_child: 'Choose at least one child.', rep_need_dates: 'Fill in both dates.',
    rep_prog_photos: (n, tot) => `Shrinking photos: ${n} of ${tot}…`, rep_prog_pdf: 'Making the PDF…',
    rep_err_offline: 'Could not make the report: no connection. Please try again.',
    rep_err: m => `Could not make the report: ${m}`,
    rep_warn_h: 'Many photos', rep_warn_p: n => `This report has ${n} photos and may be slow. Continue anyway?`, rep_warn_go: 'Continue anyway',
    rep_title: 'Report', rep_summary: 'Family overview',
    rep_made: d => `made on ${d}`, rep_page: (p, n) => `page ${p} of ${n}`,
    rep_range: (a, b) => `${a} – ${b}`, rep_range_all: b => `everything up to ${b}`,
    rep_col_child: 'Child', rep_col_level: 'Level', rep_col_new: 'Mastered in period', rep_col_total: 'Mastered in total', rep_col_acts: 'Activities',
    rep_start: 'Start date', rep_end: 'End date',
    rep_totals: (n, tot, k) => `${n} of ${tot} goals mastered, ${k} of them in this period`,
    rep_chart: 'Goals mastered, per month',
    rep_goals: 'Goals', rep_col_code: 'Code', rep_col_goal: 'Goal', rep_col_status: 'Status', rep_col_n: 'Act.',
    rep_done: d => `mastered ${d}`, rep_open: 'open',
    rep_acts: 'Activities', rep_no_acts: 'No activities in this period.',
    rep_missing: n => n === 1 ? '1 photo could not be loaded' : `${n} photos could not be loaded`,
    rep_file: 'report',
  },
};

/* ---------- dates (ISO yyyy-mm-dd strings, calendar arithmetic in UTC so time zones never shift a day) ---------- */
const ISO = /^\d{4}-\d{2}-\d{2}$/;
const isoOf = d => d.toISOString().slice(0, 10);
const validIso = s => typeof s === 'string' && ISO.test(s) && isoOf(new Date(s + 'T00:00:00Z')) === s;
/* the same day n months earlier; a day that month lacks becomes its last day (31 Aug -> 28 Feb) */
function monthsBack(day, n) {
  const [y, m, d] = day.split('-').map(Number);
  const last = new Date(Date.UTC(y, m - 1 - n + 1, 0)).getUTCDate();
  return isoOf(new Date(Date.UTC(y, m - 1 - n, Math.min(d, last))));
}
/* The period of a report: from (null: from the beginning) and until, both included. null: own dates missing or invalid. */
function periodRange(choice, today, from, until) {
  if (choice === '6m') return { from: monthsBack(today, 6), until: today };
  if (choice === 'all') return { from: null, until: today };
  if (choice === 'custom') {
    if (!validIso(from) || !validIso(until)) return null;
    return from <= until ? { from, until } : { from: until, until: from };
  }
  const y = Number(today.slice(0, 4)) - (Number(today.slice(5, 7)) < 9 ? 1 : 0);   // the school year runs 1 Sept - 31 Aug
  return { from: `${y}-09-01`, until: `${y + 1}-08-31` };
}
const inRange = (date, r) => (!r.from || date >= r.from) && date <= r.until;
const newestFirst = (a, b) => b.date.localeCompare(a.date) || ((b.createdAt || 0) - (a.createdAt || 0));
const selectActivities = (acts, childId, r) => acts.filter(a => a.childIds.includes(childId) && inRange(a.date, r)).sort(newestFirst);
/* the photos a report shows: the first few of each activity, each photo once */
function photoIdsFor(acts, limit = PHOTOS_PER_ACTIVITY) {
  const ids = new Set();
  for (const a of acts) for (const id of a.photoIds.slice(0, limit)) ids.add(id);
  return [...ids];
}

/* ---------- the document ---------- */
const BROWN = '#725C4E', FG = '#3B2F27', MUTED = '#665244', LINE = '#D9CDBF', GREEN = '#0A8257';
const STYLES = {
  h1: { fontSize: 20, bold: true, margin: [0, 0, 0, 4] },
  h2: { fontSize: 14, bold: true, color: BROWN, margin: [0, 14, 0, 6] },
  h3: { fontSize: 11, bold: true, margin: [0, 6, 0, 4] },
  th: { fontSize: 9, bold: true, color: MUTED },
  muted: { color: MUTED },
  code: { fontSize: 8.5 },
};
/* tables: a line under the header and thin lines between rows, none at the sides */
const TABLE = {
  hLineWidth: (i, node) => (i === 0 || i === node.table.body.length ? 0 : i === 1 ? 1 : 0.5),
  vLineWidth: () => 0, hLineColor: () => LINE,
  paddingLeft: i => (i ? 6 : 0), paddingRight: () => 6, paddingTop: () => 3, paddingBottom: () => 3,
};
const xml = s => String(s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const periodText = (r, t, fmt) => (r.from ? t('rep_range', fmt.date(r.from), fmt.date(r.until)) : t('rep_range_all', fmt.date(r.until)));
/* a goal's state at the end of the period: its mastered date, or null (also when it was mastered later) */
const doneAt = (c, gid, r) => { const d = c.mastered[gid]; return d && d <= r.until ? d : null; };
function childFacts(c, r, acts) {
  let total = 0, fresh = 0;
  for (const g of c.goals) { const d = doneAt(c, g.id, r); if (d) { total++; if (inRange(d, r)) fresh++; } }
  return { total, fresh, goals: c.goals.length, acts: acts.length };
}

/* yyyy-mm months from a to b, both included (at most 20 years) */
function monthList(a, b) {
  const out = []; let [y, m] = a.split('-').map(Number); const [y2, m2] = b.split('-').map(Number);
  while ((y < y2 || (y === y2 && m <= m2)) && out.length < 240) { out.push(`${y}-${String(m).padStart(2, '0')}`); if (++m > 12) { m = 1; y++; } }
  return out;
}
/* The chart: per month the number of goals mastered by its end, from the start of the period (everything: the first
   mastered goal) up to the end of the period or today, whichever comes first. */
function chartData(c, r, today) {
  const end = r.until < today ? r.until : today;
  const dates = c.goals.map(g => c.mastered[g.id]).filter(d => d && d <= end).sort();
  let start = r.from || dates[0] || end;
  if (start > end) start = end;
  const months = monthList(start.slice(0, 7), end.slice(0, 7));
  return { months, values: months.map(ym => dates.filter(d => d.slice(0, 7) <= ym).length) };
}
const niceTop = v => { const p = 10 ** Math.floor(Math.log10(v)); for (const k of [1, 2, 5, 10]) if (k * p >= v) return k * p; return v; };
function chartSvg({ months, values }, color, fmt) {
  const W = 500, H = 170, L = 34, R = 10, T = 10, B = 26, pw = W - L - R, ph = H - T - B, n = values.length;
  const top = niceTop(Math.max(1, ...values));
  const x = i => L + (n > 1 ? pw * i / (n - 1) : pw / 2), y = v => T + ph - ph * v / top;
  const grid = [0, top / 2, top].map(v => `<line x1="${L}" x2="${W - R}" y1="${y(v)}" y2="${y(v)}" stroke="${LINE}" stroke-width="1"/>`
    + `<text x="${L - 6}" y="${y(v) + 3}" font-size="9" text-anchor="end" fill="${MUTED}">${Number.isInteger(v) ? v : v.toFixed(1)}</text>`).join('');
  const step = Math.ceil(n / 6);   // at most about seven month names
  const anchor = i => (n < 2 ? 'middle' : i === 0 ? 'start' : i === n - 1 ? 'end' : 'middle');   // the outer names stay inside the picture
  const axis = months.map((m, i) => ((n - 1 - i) % step ? '' : `<text x="${x(i)}" y="${H - 8}" font-size="9" text-anchor="${anchor(i)}" fill="${MUTED}">${xml(fmt.month(m))}</text>`)).join('');
  const path = values.map((v, i) => `${i ? 'L' : 'M'}${x(i).toFixed(1)},${y(v).toFixed(1)}`).join(' ');
  return `<svg width="${W}" height="${H}" viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">${grid}`
    + `<path d="${path}" fill="none" stroke="${color}" stroke-width="2"/><circle cx="${x(n - 1)}" cy="${y(values[n - 1])}" r="3" fill="${color}"/>${axis}</svg>`;
}

function summaryBlock({ t, fmt, range }, parts) {
  return [
    { text: t('rep_summary'), style: 'h1' },
    { text: periodText(range, t, fmt), style: 'muted', margin: [0, 0, 0, 12] },
    { table: { headerRows: 1, widths: ['*', 'auto', 'auto', 'auto', 'auto'], body: [
      ['rep_col_child', 'rep_col_level', 'rep_col_new', 'rep_col_total', 'rep_col_acts'].map(k => ({ text: t(k), style: 'th' })),
      ...parts.map(({ c, f }) => [{ text: c.name, bold: true }, c.level, String(f.fresh), `${f.total} / ${f.goals}`, String(f.acts)]),
    ] }, layout: TABLE },
  ];
}
function childCover({ t, fmt, range }, c, f) {
  const dates = [c.startDate && `${t('rep_start')}: ${fmt.date(c.startDate)}`, c.endDate && `${t('rep_end')}: ${fmt.date(c.endDate)}`].filter(Boolean);
  return [
    { text: c.name, style: 'h1', color: c.color },
    { text: [c.level, ...dates].join(' · '), style: 'muted' },
    { text: periodText(range, t, fmt), style: 'muted' },
    { text: t('rep_totals', f.total, f.goals, f.fresh), bold: true, margin: [0, 6, 0, 0] },
  ];
}
function childChart(input, c) {
  return [{ text: input.t('rep_chart'), style: 'h2' }, { svg: chartSvg(chartData(c, input.range, input.today), c.color, input.fmt), width: 500 }];
}
function goalsTable({ t, fmt, range }, c, acts) {
  const n = new Map();
  for (const a of acts) for (const gid of a.goalIds) n.set(gid, (n.get(gid) || 0) + 1);
  const out = [{ text: t('rep_goals'), style: 'h2' }];
  let subject = null, rows = null;
  const flush = () => { if (rows) out.push({ table: { headerRows: 1, dontBreakRows: true, widths: [62, '*', 84, 24], body: rows }, layout: TABLE, margin: [0, 0, 0, 8] }); };
  for (const g of c.goals) {
    if (g.subject !== subject) {
      flush(); subject = g.subject;
      out.push({ text: subject, style: 'h3' });
      rows = [['rep_col_code', 'rep_col_goal', 'rep_col_status', 'rep_col_n'].map(k => ({ text: t(k), style: 'th' }))];
    }
    const d = doneAt(c, g.id, range);
    rows.push([{ text: g.code, style: 'code' }, g.text, d ? { text: t('rep_done', fmt.date(d)), color: GREEN } : { text: t('rep_open'), color: MUTED },
      { text: String(n.get(g.id) || ''), alignment: 'right' }]);
  }
  flush();
  return out;
}
const shownPhotos = (input, a) => (input.withPhotos ? a.photoIds.slice(0, PHOTOS_PER_ACTIVITY).filter(id => input.images[id]) : []);
function activityList(input, c, acts) {
  const { t, fmt } = input, codes = new Map(c.goals.map(g => [g.id, g.code]));
  const out = [{ text: t('rep_acts'), style: 'h2' }];
  if (!acts.length) return [...out, { text: t('rep_no_acts'), style: 'muted' }];
  for (const a of acts) {
    const cs = a.goalIds.map(id => codes.get(id)).filter(Boolean), pics = shownPhotos(input, a);
    out.push({ stack: [
      { text: [{ text: fmt.date(a.date) + '   ', color: MUTED }, { text: a.title, bold: true }] },
      ...(cs.length ? [{ text: cs.join(' · '), style: 'code', color: MUTED }] : []),
      ...(a.notes ? [{ text: a.notes, margin: [0, 2, 0, 0] }] : []),
      ...(pics.length ? [{ columns: pics.map(id => ({ image: 'p_' + id, fit: [118, 88], width: 'auto' })), columnGap: 6, margin: [0, 4, 0, 0] }] : []),
    ], margin: [0, 0, 0, 10] });
  }
  return out;
}
function missingBlock({ t, fmt, missing }) {
  if (!missing.length) return [];
  return [{ text: t('rep_missing', missing.length), style: 'h2', pageBreak: 'before' },
    { ul: missing.map(m => [m.date && fmt.date(m.date), m.title].filter(Boolean).join(' · ') || '—') }];
}

/* The whole report: the family overview (global only), then per child its cover, chart, goals and activities,
   each child on a new page; the photos that could not be loaded at the end. */
function buildReport(input) {
  const { kind, range, t, fmt, today } = input;
  const parts = input.children.map(c => { const acts = selectActivities(input.activities, c.id, range); return { c, acts, f: childFacts(c, range, acts) }; });
  const content = kind === 'global' ? summaryBlock(input, parts) : [];
  for (const { c, acts, f } of parts) {
    const part = [...childCover(input, c, f), ...childChart(input, c), ...goalsTable(input, c, acts), ...activityList(input, c, acts)];
    if (content.length) part[0] = { ...part[0], pageBreak: 'before' };
    content.push(...part);
  }
  content.push(...missingBlock(input));
  const images = {};
  if (input.logo) images.logo = input.logo;
  for (const { acts } of parts) for (const a of acts) for (const id of shownPhotos(input, a)) images['p_' + id] = input.images[id];   // a shared photo once
  return {
    pageSize: 'A4', pageMargins: [40, 56, 40, 48],
    info: { title: `Doelenboek – ${t('rep_title')}`, creator: 'Doelenboek.be', producer: 'Doelenboek.be' },
    header: input.logo
      ? { margin: [40, 18, 40, 0], columns: [{ image: 'logo', width: 20 }, { text: 'Doelenboek.be', bold: true, color: BROWN, margin: [6, 4, 0, 0] }] }
      : { margin: [40, 22, 40, 0], text: 'Doelenboek.be', bold: true, color: BROWN },
    footer: (page, pages) => ({ margin: [40, 14, 40, 0], fontSize: 8, color: MUTED,
      columns: [{ text: `Doelenboek.be · ${t('rep_made', fmt.date(today))}` }, { text: t('rep_page', page, pages), alignment: 'right' }] }),
    content, images, styles: STYLES, defaultStyle: { fontSize: 10, color: FG, lineHeight: 1.2 },
  };
}
/* doelenboek-rapport[-child]-date.pdf; letters (any alphabet) and digits stay, everything else becomes a dash */
function fileName(kind, name, today, t) {
  const safe = String(name).normalize('NFC').replace(/[^\p{L}\p{N}]+/gu, '-').replace(/^-+|-+$/g, '').slice(0, 60) || 'kind';
  return `doelenboek-${t('rep_file')}${kind === 'child' ? '-' + safe : ''}-${today}.pdf`;
}

return { TEXTS, COLORS, PHOTOS_PER_ACTIVITY, PHOTO_WARN, PERIODS, periodRange, inRange, selectActivities, photoIdsFor, chartData, buildReport, fileName };
})();
if (typeof module !== 'undefined') module.exports = Report;
