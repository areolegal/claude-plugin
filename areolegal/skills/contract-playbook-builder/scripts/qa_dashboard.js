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
/* jsdom: JSDOM_PATH (תיקיית jsdom או הקובץ שלה), ואחריו החיפוש הרגיל של node (node_modules מקומי ו-NODE_PATH),
   node_modules בתיקיית העבודה, ההתקנה הגלובלית של npm והתיקייה הזמנית של המחשב. בלי נתיב Unix קשיח, כדי שהבדיקה
   תרוץ גם ב-Windows. כשלא נמצא: הודעה ברורה ויציאה 1, ולא TypeError */
function loadJsdom(){
  const path=require('path'), os=require('os'), tried=[];
  const attempt=c=>{ if(!c) return null; tried.push(c);
    try{ return require(c); }catch(e){}
    try{ return require(require.resolve(c,{paths:[process.cwd()]})); }catch(e){}
    return null; };
  let m=attempt(process.env.JSDOM_PATH)||attempt('jsdom')
    ||attempt(process.env.APPDATA&&path.join(process.env.APPDATA,'npm','node_modules','jsdom'))
    ||attempt(path.join(os.tmpdir(),'node_modules','jsdom'))||attempt('/tmp/node_modules/jsdom');
  if(!m){ try{ m=attempt(path.join(require('child_process').execSync('npm root -g',
    {stdio:['ignore','pipe','ignore']}).toString().trim(),'jsdom')); }catch(e){} }
  if(m) return m;
  console.error('jsdom לא נמצא, ולכן הבדיקה לא רצה. התקינו אותו (npm install jsdom) או הגדירו JSDOM_PATH לתיקיית jsdom. '
    +'נבדקו: '+tried.join(' | ')+'\njsdom was not found, so the check did not run. Install it (npm install jsdom) '
    +'or set JSDOM_PATH to the jsdom folder.');
  process.exit(1);
}
const {JSDOM, VirtualConsole} = loadJsdom();
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
  /* דף באנגלית (meta.lang = en): אותן בדיקות, והטקסט הקבוע שמחפשים הוא המקביל האנגלי */
  const EN = d.documentElement.getAttribute('lang') === 'en';
  const L = (he, en) => EN ? en : he;

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

  // 3. לחיצה על כל כפתור בכל מסך. בדף של כמה פלייבוקים זה כולל את הבורר,
  // ולכן הסוג שנבחר נשמר, ומוחזר אחרי הלחיצות: הבדיקות שאחריו נמדדות מול
  // הסעיפים של הסוג שממנו התחלנו
  const pb0 = w.eval('S.pb');
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
  if (w.eval('typeof BOOKS!=="undefined" && !!BOOKS') && pb0) w.setPb(pb0);

  // 3א. דף של כמה פלייבוקים: כל סוג מוצג שלם בכל מסך, ומספר הסעיפים
  // שמוצג הוא של הסוג שנבחר, לא של הסוג הקודם
  if (w.eval('typeof BOOKS!=="undefined" && !!BOOKS')) {
    const ids = w.eval('Object.keys(BOOKS)');
    let bad = [];
    for (const id of ids) {
      w.setPb(id);
      const want = w.pbRuleCount(id);
      if (w.rulesOf().length !== want) bad.push(id + ': ' + w.rulesOf().length + '/' + want);
      for (const v of views) {
        try { w.go(v); if (wrap().length <= 120) bad.push(id + '/' + v + ' ריק'); }
        catch (e) { bad.push(id + '/' + v + ': ' + e.message.slice(0, 50)); }
      }
    }
    R('כל סוג הסכם נפתח שלם בכל המסכים', bad.length === 0,
      ids.length + ' סוגים' + (bad.length ? ': ' + bad.slice(0, 3).join('; ') : ''));
    w.setPb(pb0);
  }

  // 4. הערות, אישורים והצעות נוסח: רק באשף. בדף אין תיבת הערה ואין מצב עריכה, ובכל סעיף יש קישור לאשף
  // לחיצה על כל הכפתורים משאירה את העדפות הצופה (לוח/טבלה, מסנן, חיפוש) במצב שרירותי; הבדיקות שלמטה מניחות לוח, מסנן 'הכל' וחיפוש ריק
  w.eval("if(typeof setRulesMode==='function'){S.rulesMode='board';} S.filter='all'; S.q='';");
  w.go('rules'); w.renderList(); await sleep(20);
  const before = d.getElementById('progChip').textContent;
  R('מונה נימוקים ולא מונה אישורים',
    before.includes(L('נימוקים מלאים', 'Full rationales')) && before.includes(L('מתוך ', 'of ') + n), before);
  const body = d.getElementById('rlist').innerHTML;
  R('אין בסעיף תיבת הערה או הצעת נוסח', !body.includes('class="noteta"') && !body.includes('toggleRuleEdit('));
  R('אין בדף מצב עריכה', !d.getElementById('editChip') && !wrap().includes('toggleEdit()'));
  const wiz = w.eval('D.meta.wizard_href||""');
  R('בכל סעיף כפתור להכרעה ולאישור של הסעיף הזה, בלשונית שבסביבת העבודה (כשהאשף נבנה)', !wiz || (body.includes('goApprove(') && body.includes(rid(0))));
  R('לשונית הכרעה ואישור קיימת כשהאשף נבנה', !wiz || !!d.querySelector('#nav [onclick*="approve"]'));
  R('אין בדף פעולת אישור',
    ['decide', 'approveAll', 'dl', 'agentPack', 'docExport'].every(x => typeof w[x] !== 'function'));

  // 5. אין בדף כפתור הורדת הערות: קובץ ההערות יוצא רק מהאשף
  w.go('decisions'); await sleep(20);
  R('אין כפתור הורדת הערות', !wrap().includes('dlComments()'));

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
  w.eval("S.pf='all';S.xf='weak';renderList()");
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
  R('מסך הסגמנטים נפתח בלי מצב עריכה', wrap().length > 120 && !wrap().includes('toggleEdit()'));
  /* אין בדף הוספת סגמנט או הצעת חריג: סגמנט חדש מבקשים בצ'אט, והערה על חריג נכתבת באשף */
  R('אין בדף הוספת סגמנט או הצעת חריג', !wrap().includes('segAdd()') && !wrap().includes('addUserVariant('));
  w.go('precedents'); await sleep(20);
  if (d.getElementById('pCp')) {
    d.getElementById('pCp').value = 'בדיקת QA בעמ';
    d.getElementById('pDev').value = 'סטייה לבדיקה';
    w.addPrec(); await sleep(20);
    R('תיעוד תקדים', wrap().includes('בדיקת QA'));
    w.delPrec(0);
  }

  // 10. התמדה בדפדפן, לפי המפתח שבמטען
  /* מוסכמת המפתחות: areo:<לקוח>:<פלייבוק>:<מה>; הדף חושף את מפתח המצב שלו ב-LS */
  const key = (() => { try { return w.eval('LS'); } catch (e) { return (D.meta || {}).ls_key; } })();
  R('מפתח אחסון לפי המוסכמה areo:לקוח:פלייבוק:מה', /^areo:[^:]+:[^:]+:state$/.test(String(key)), String(key).slice(0, 60));
  const saved = JSON.parse(w.localStorage.getItem(key) || w.localStorage.getItem(key + '_v1') || '{}');
  R('שמירה ב-localStorage', !!saved && typeof saved === 'object'
    && Object.keys(saved).length > 0, Object.keys(saved).join(', ').slice(0, 60));

  // 11. העתקה, כיווניות, וטקסט גלוי נקי
  R('אין בדף תפריט הורדות של Office', typeof w.toggleDl !== 'function'
    && !d.getElementById('dlMenu'));
  if (EN) {
    R('LTR מלא בדף באנגלית', d.documentElement.getAttribute('dir') === 'ltr');
    /* בדף באנגלית אין עברית קבועה: כל רצף עברי גלוי הוא נתון (נושא, עמדה, נוסח מצוטט, שם) */
    const blob = []; (function walk(v) { if (typeof v === 'string') blob.push(v);
      else if (v && typeof v === 'object') Object.values(v).forEach(walk); })([D, w.eval('S')]);  /* נתונים, וגם מה שהבדיקה עצמה כתבה */
    const data = blob.join('\n');
    const leaks = new Set();
    for (const v of views) {
      w.go(v); if (v === 'rules') w.renderList();
      const tw = d.createTreeWalker(d.body, 4);
      for (let t = tw.nextNode(); t; t = tw.nextNode()) {
        if (t.parentElement && t.parentElement.closest('script,style')) continue;
        for (const m of t.nodeValue.matchAll(/[\u0590-\u05FF][\u0590-\u05FF "'.,:;()\-״׳0-9/]*/g)) {
          const s2 = m[0].trim().replace(/[\s"'.,:;()\-]+$/, '');
          if (s2.length < 2 || data.includes(s2)) continue;
          /* רצף שהוא שני נתונים צמודים (שם הסכם ומספר סעיף) הוא עדיין נתון */
          let rest = s2, ok = true;
          while (rest.trim()) { rest = rest.replace(/^[\s,.:;()\-]+/, ''); let k = rest.length;
            while (k > 1 && !data.includes(rest.slice(0, k))) k--;
            if (k <= 1 && /[֐-׿]/.test(rest[0] || '')) { ok = false; break; }
            rest = rest.slice(Math.max(k, 1)); }
          if (!ok) leaks.add(s2);
        }
      }
    }
    R('אין עברית קבועה בדף באנגלית', leaks.size === 0, [...leaks].slice(0, 5).join(' | '));
  } else {
    R('RTL מלא', d.documentElement.getAttribute('dir') === 'rtl');
  }
  // 12. תיקוני הביקורת מ-31.10 (ממשק): מגירה כדיאלוג, פס עליון אטום, מסננים ומוני תוצאות, חיפוש, סימן מותג אחד
  (() => {
    const dr = d.getElementById('drawer');
    R('המגירה היא דיאלוג מודאלי', dr.getAttribute('role') === 'dialog' && dr.getAttribute('aria-modal') === 'true');
    const c0 = (D.cites || [])[0];
    if (c0) {
      w.openCite(c0.id);
      const open1 = dr.classList.contains('on') && d.body.classList.contains('noscroll');
      d.dispatchEvent(new w.KeyboardEvent('keydown', {key: 'Escape', bubbles: true}));
      R('Escape סוגר את המגירה ומשחרר את הגלילה', open1 && !dr.classList.contains('on') && !d.body.classList.contains('noscroll'));
      w.openCite(c0.id); d.getElementById('scrim').click();
      R('לחיצה על הרקע סוגרת את המגירה', !dr.classList.contains('on'));
      R('אין במגירה מילה טכנית כמיקום', !/>\s*corpus\s*</.test(d.getElementById('drBody').innerHTML));
    }
    R('אין console.log שנשאר מהפיתוח', !/console\.log\(/.test(html));
    R('הפס העליון אטום', /--topbg:var\(--page\)/.test(html));
    w.go('rules'); w.renderList();
    const n = w.rulesOf().length, attn = w.attnCount();
    const fb = [...d.querySelectorAll('#wrap .fbtn')].map(b => b.textContent);
    R('מסנן שמתאים לכל הרשומות מוסתר', (attn > 0 && attn < n) ? fb.some(t => /תשומת לב|attention/i.test(t)) : !fb.some(t => /תשומת לב|attention/i.test(t)));
    R('לשדה החיפוש יש כפתור ניקוי', !!d.getElementById('gqx') && typeof w.clearQ === 'function');
    const q = String((w.rulesOf()[0] || {}).topic || '').split(/\s+/)[0];
    if (q && q.length > 1) { w.globalSearch(q);
      R('מילת החיפוש מודגשת בתוצאות', d.querySelectorAll('#rlist mark.hl').length > 0, q);
      R('מונה התוצאות הוא אזור חי', (d.getElementById('cnt') || {}).getAttribute && d.getElementById('cnt').getAttribute('aria-live') === 'polite');
      w.clearQ(); }
    w.setRulesMode('table'); w.renderList();
    const ths = [...d.querySelectorAll('#rlist th')];
    R('טבלה: תגיות עמודה וכיתוב מרחף', ths.length > 0 && ths.every(t => t.getAttribute('scope') === 'col')
      && [...d.querySelectorAll('#rlist td.g,#rlist td.y,#rlist td.r')].every(t => t.hasAttribute('title')));
    w.setRulesMode('board');
    R('סימן המותג מופיע פעם אחת', /\.areo-brand\{display:none\}/.test(html));
    const ask = w.updAsk();
    R('בקשת העדכון שלמה ובלי סוגריים מקוננים', ask.length > 80 && !/\([^()]*\(/.test(ask));
    w.go('ask');
    R('תיבת השאלה בכיוון מפורש, לא auto', (d.getElementById('askq') || {}).getAttribute && d.getElementById('askq').getAttribute('dir') !== 'auto');
    if (!(D.templateFindings || []).length) R('מסך ממצאים ריק מוסתר', !w.viewShown(w.eval('VIEWS').find(v => v.id === 'findings')));
  })();
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
