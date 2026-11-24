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

return { TEXTS, COLORS, PHOTOS_PER_ACTIVITY, PHOTO_WARN, PERIODS, periodRange, inRange, selectActivities, photoIdsFor };
})();
if (typeof module !== 'undefined') module.exports = Report;
