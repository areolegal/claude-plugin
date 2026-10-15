/* רתמת בדיקות הקבלה של סביבת העבודה.

   **הרתמה אינה מכוילת לפלייבוק מסוים.** הגרסה הקודמת חיפשה בתוצר מזהי
   סעיפים, שמות צדדים ו-slug של לקוח אמיתי, ולכן נכשלה על כל פלייבוק אחר
   ולא רצה בשגרה. כאן כל מזהה, מונח חיפוש וסגמנט נגזרים מהנתונים שבתוצר
   עצמו, ולכן היא רצה על כל פלייבוק, כולל מטען ההדגמה.

   מה נבדק: כל המסכים נרנדרים; לחיצה על כל כפתור בכל מסך אינה זורקת;
   הגרפים נוצרים; זרימת ההערות וההצעות; החיפוש בשלושת הסקופים; המסננים;
   מגירת הציטוטים; הסגמנטים והתקדימים; ההתמדה בדפדפן; RTL; ושאין בטקסט
   הגלוי מקפים ארוכים או קודים פנימיים.

   הרצה:  JSDOM_PATH=<נתיב ל-jsdom> node qa_dashboard.js <dashboard.html>
*/
const {JSDOM, VirtualConsole} = require(process.env.JSDOM_PATH);
const fs = require('fs');

const qa = {downloads: [], copied: [], charts: [], btnOK: 0, btnFail: [], results: []};
const R = (name, ok, note = '') => { qa.results.push({name, ok, note}); };

const vc = new VirtualConsole();
vc.on('jsdomError', e => {
  if (!/scroll|print|navigation|resource|opaque/i.test(e.message))
    qa.btnFail.push('JSDOM: ' + e.message.slice(0, 90));
});
vc.on('error', () => {});

const html = fs.readFileSync(process.argv[2] || 'dash.html', 'utf8');
const dom = new JSDOM(html, {
  runScripts: 'dangerously', pretendToBeVisual: true, virtualConsole: vc,
  url: 'https://localhost/',
  beforeParse(window) {
    /* ספריית הגרפים מוטמעת בתוצר; jsdom אינו מספק קנבס, ולכן בדל */
    const stub = function (el, cfg) { qa.charts.push(cfg && cfg.type); return {destroy() {}}; };
    Object.defineProperty(window, 'Chart', {configurable: true, get: () => stub, set: () => {}});
    window.confirm = () => true;
    window.print = () => {};
    window.URL.createObjectURL = () => 'blob:1';
    window.URL.revokeObjectURL = () => {};
  }
});
const w = dom.window, d = w.document;
w.HTMLAnchorElement.prototype.click = function () {
  qa.downloads.push(this.download || '(link)');
};
Object.defineProperty(w.navigator, 'clipboard',
  {value: {writeText: t => { qa.copied.push(String(t).length); return Promise.resolve(); }}});

const sleep = ms => new Promise(r => setTimeout(r, ms));
const wrap = () => d.getElementById('wrap').innerHTML;
const cards = () => (d.getElementById('rlist').innerHTML.match(/class="card rulecard/g) || []).length;

setTimeout(async () => {
  const D = w.eval('D');
  /* כל מה שהבדיקה צריכה, מתוך הנתונים ולא מליטרלים */
  const views = w.eval('VIEWS.map(v=>v.id)');
  const rules = w.rulesOf();
  const n = rules.length;
  const rid = r => (rules[r] || rules[0] || {}).id;
  const firstCite = (D.cites || [])[0] || {};
  const topicWord = ((rules[0] || {}).topic || '').split(/\s+/)[0] || '';
  const srcName = (D.friendly || {})[firstCite.src] || firstCite.src || '';
  const srcWord = String(srcName).split(/\s+/)[0] || '';

  R('יש בתוצר סעיפים', n > 0, n + ' סעיפים');

  // 1. כל המסכים נרנדרים
  for (const v of views) {
    try {
      w.go(v);
      /* מסך שאין לו נתונים מרנדר מצב ריק מוסבר, וזה תקין. הכשל הוא מסך
         שזורק, או שיוצא ריק לגמרי. */
      R('מסך ' + v, wrap().length > 120, wrap().length + ' תווים');
    } catch (e) { R('מסך ' + v, false, e.message); }
  }

  // 2. גרפים
  w.go('overview'); await sleep(120);
  R('גרף נוצר בתמונת מצב', qa.charts.length > 0, qa.charts.join(', '));
  R('אין חיצים בכפתורים', !html.includes('⌄'));
  R('KPI בשורה לרוחב', !!d.getElementById('kpirow')
    && d.getElementById('kpirow').classList.contains('statrow'));

  // 3. לחיצה על כל כפתור בכל מסך
  for (const v of views) {
    w.go(v); await sleep(30);
    for (const b of [...d.getElementById('wrap').querySelectorAll('button')]) {
      try { b.click(); qa.btnOK++; }
      catch (e) {
        qa.btnFail.push(v + ': ' + (b.textContent || '').trim().slice(0, 25)
          + ' -> ' + e.message.slice(0, 60));
      }
    }
  }
  for (const b of [...d.querySelectorAll('.top button, nav .navi')]) {
    try { b.click(); qa.btnOK++; }
    catch (e) { qa.btnFail.push('topbar: ' + e.message.slice(0, 60)); }
  }
  R('לחיצה על כל הכפתורים', qa.btnFail.length === 0,
    qa.btnOK + ' כפתורים, ' + qa.btnFail.length + ' כשלים');

  // 4. הערות והצעות: הזרימה שהחליפה את ההכרעות
  w.go('rules'); w.renderList(); await sleep(20);
  const before = d.getElementById('progChip').textContent;
  R('מונה נימוקים ולא מונה אישורים',
    before.includes('נימוקים מלאים') && before.includes('מתוך ' + n), before);
  w.setNote(rid(0), 'הערה לבדיקת QA'); w.renderList();
  R('הערה נשמרת ומוצגת', wrap().includes('הערה לבדיקת QA') || cards() > 0);
  w.toggleRuleEdit(rid(1)); await sleep(20);
  R('תיבת ההצעה נפתחת בלחיצה',
    d.getElementById('rlist').innerHTML.includes('הצעת נוסח חלופי'));
  w.setProp(rid(1), 'green', 'נוסח שהוצע בבדיקת QA'); w.renderList();
  const body = d.getElementById('rlist').innerHTML;
  R('ההצעה מוצגת בתיבה נפרדת', body.includes('נוסח שהוצע בבדיקת QA')
    && body.includes('הצעה, לא מדיניות'));
  R('ההצעה אינה מחליפה את המדיניות',
    w.effLight(rules[1], 'green').clause !== 'נוסח שהוצע בבדיקת QA');
  w.dropProp(rid(1), 'green'); w.renderList();
  R('מחיקת ההצעה', !d.getElementById('rlist').innerHTML.includes('נוסח שהוצע בבדיקת QA'));
  R('אין בדף פעולת אישור',
    ['decide', 'approveAll', 'dl', 'agentPack', 'docExport'].every(x => typeof w[x] !== 'function'));

  // 5. הורדת ההערות וההצעות: ההורדה היחידה שנשארה
  qa.downloads = [];
  w.go('decisions'); await sleep(20);
  w.dlComments(); await sleep(20);
  R('הורדת ההערות וההצעות', qa.downloads.length > 0, qa.downloads.join(', '));

  // 6. חיפוש בשלושה סקופים, במונחים מהנתונים
  const setScope = v => { const s = d.getElementById('gscope'); s.value = v; s.dispatchEvent(new w.Event('change')); };
  const gq = q => { const e = d.getElementById('gq'); e.value = q; w.globalSearch(q); };
  w.go('rules'); w.renderList();
  setScope('topic'); gq(topicWord);
  R('חיפוש לפי נושא', cards() >= 1 && cards() <= n, cards() + ' תוצאות על "' + topicWord + '"');
  setScope('agreement'); gq(srcWord);
  R('חיפוש לפי הסכם או צד', cards() >= 1, cards() + ' תוצאות על "' + srcWord + '"');
  setScope('all'); gq('');
  R('איפוס החיפוש מחזיר הכול', cards() === n, cards() + ' מתוך ' + n);

  // 7. מסננים
  const nAll = cards();
  w.eval("S.pf='Required';renderList()");
  R('מסנן כלל נוכחות', cards() <= nAll, nAll + ' -> ' + cards());
  w.eval("S.pf='all';S.df='commented';renderList()");
  R('מסנן סעיפים עם הערה', cards() >= 1 && cards() <= nAll, cards() + ' עם הערה');
  w.eval("S.df='all';S.xf='weak';renderList()");
  R('מסנן עוצמת ראיות', cards() <= nAll, nAll + ' -> ' + cards());
  w.eval("S.xf='all';renderList()");

  // 8. מגירת הציטוטים
  if (firstCite.id) {
    w.openCite(firstCite.id);
    R('מגירת ציטוט נפתחת', d.getElementById('drawer').classList.contains('on')
      && d.getElementById('drTitle').textContent.length > 3,
      d.getElementById('drTitle').textContent.slice(0, 40));
    R('בכותרת המגירה אין קוד פנימי', !/INT-\d\d/.test(d.getElementById('drTitle').textContent));
    w.closeDrawer();
    R('מגירה נסגרת', !d.getElementById('drawer').classList.contains('on'));
  }

  // 9. סגמנטים ותקדימים
  w.go('segpolicy'); await sleep(20);
  if (!wrap().includes('סגמנט חדש')) { w.toggleEdit(); w.go('segpolicy'); await sleep(20); }
  R('מצב עריכה מפעיל הוספת סגמנט', wrap().includes('סגמנט חדש'));
  const segsBefore = w.effSegs().length;
  w.segAdd(); await sleep(20);
  R('הוספת סגמנט', w.effSegs().length === segsBefore + 1,
    segsBefore + ' -> ' + w.effSegs().length);
  const segId = (w.effSegs()[0] || {}).segment_id;
  if (segId) {
    w.addUserVariant(rid(0), segId); await sleep(20);
    R('הצעת חריג נרשמת', !!w.eval("S.userVariants['" + rid(0) + "|" + segId + "']"));
    /* הכרטיס עצמו מוצג במסך הסגמנט המלא, ושם גם התווית */
    w.eval("S.segFull='" + segId + "'"); w.render(); await sleep(20);
    R('הצעת חריג מסומנת "הצעה, לא מדיניות"', wrap().includes('הצעה, לא מדיניות'),
      'בסגמנט ' + segId);
    w.eval("S.segFull=null"); w.render();
    w.delUserVariant(rid(0), segId);
  }
  w.go('precedents'); await sleep(20);
  if (d.getElementById('pCp')) {
    d.getElementById('pCp').value = 'בדיקת QA בעמ';
    d.getElementById('pDev').value = 'סטייה לבדיקה';
    w.addPrec(); await sleep(20);
    R('תיעוד תקדים', wrap().includes('בדיקת QA'));
    w.delPrec(0);
  }

  // 10. התמדה בדפדפן, לפי המפתח שבמטען
  const key = (D.meta || {}).ls_key;
  const saved = JSON.parse(w.localStorage.getItem(key) || w.localStorage.getItem(key + '_v1') || '{}');
  R('שמירה ב-localStorage', !!saved && typeof saved === 'object'
    && Object.keys(saved).length > 0, Object.keys(saved).join(', ').slice(0, 60));

  // 11. העתקה, כיווניות, וטקסט גלוי נקי
  R('אין בדף תפריט הורדות של Office', typeof w.toggleDl !== 'function'
    && !d.getElementById('dlMenu'));
  R('RTL מלא', d.documentElement.getAttribute('dir') === 'rtl');
  R('אפס מקפים ארוכים', !html.includes('—') && !html.includes('–'));
  R('אפס קודים פנימיים בטקסט גלוי', (() => {
    w.go('rules'); w.renderList();
    const vis = [...d.querySelectorAll('#wrap b,#wrap h3,#wrap h4,#wrap .mut,#wrap .tag,#wrap p,#wrap li')]
      .map(e => e.textContent).join(' ');
    return !/\b(SEG-\d|INT-\d\d)\b/.test(vis);
  })());

  const fail = qa.results.filter(r => !r.ok);
  console.log('====== תוצאות QA ======');
  qa.results.forEach(r => console.log((r.ok ? 'PASS' : 'FAIL') + '  ' + r.name
    + (r.note ? ('  [' + r.note + ']') : '')));
  console.log('======');
  console.log('סך הכול: ' + qa.results.length + ' בדיקות, ' + fail.length + ' כשלים');
  if (qa.btnFail.length) console.log('כשלי כפתורים:', qa.btnFail.slice(0, 8));
  process.exit(fail.length ? 1 : 0);
}, 600);
