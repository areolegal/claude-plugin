/* חריגי הסגמנטים: הרשימה, הסינון, התצוגה בתוך הסעיף, וההצעות.

   **הרתמה אינה מכוילת לפלייבוק מסוים.** הגרסה הקודמת חיפשה סגמנט בשם
   "בנקים" ומזהים כמו SEG-GOV של לקוח אמיתי, ולכן נכשלה על כל פלייבוק אחר.
   כאן כל מזהה נגזר מהנתונים שבתוצר. מריצים אותה על תוצר שיש בו סגמנטים;
   כשאין, היא אומרת זאת ויוצאת בהצלחה.

   הרצה:  JSDOM_PATH=<נתיב ל-jsdom> node qa_segments.js <dashboard.html>
*/
const {JSDOM, VirtualConsole} = require(process.env.JSDOM_PATH);
const fs = require('fs');
const vc = new VirtualConsole(); vc.on('jsdomError', () => {}); vc.on('error', () => {});
const dom = new JSDOM(fs.readFileSync(process.argv[2] || 'dash.html', 'utf8'),
  {runScripts: 'dangerously', pretendToBeVisual: true, virtualConsole: vc, url: 'https://x/',
   beforeParse(w) {
     Object.defineProperty(w, 'Chart',
       {configurable: true, get: () => function () { return {destroy() {}}; }, set: () => {}});
     w.confirm = () => true;
   }});
const w = dom.window, d = w.document, ev = x => w.eval(x);

setTimeout(() => {
  const out = [];
  const segs = w.effSegs();
  if (!segs.length) {
    console.log('בתוצר הזה אין סגמנטים, ולכן אין מה לבדוק כאן.');
    console.log('להרצה אמיתית דרוש תוצר שיש בו segments ו-rules[].variants.');
    process.exit(0);
  }
  w.go('segpolicy');
  const txt = () => d.getElementById('wrap').textContent;
  out.push(['כותרת חריגים לפי סגמנט', txt().indexOf('חריגים לפי סגמנט') >= 0]);
  /* מונה לכל סגמנט, לפי השם שבנתונים */
  const label = segs[0].label;
  out.push(['שורת סגמנטים עם מונים',
    new RegExp(label.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + ' \\(\\d+\\)').test(txt()),
    label]);
  const rows = () => d.querySelectorAll('.tbl tbody tr');
  const all = ev('allExceptions().length');
  out.push(['טבלת חריגים', rows().length === all && all > 0, rows().length + ' שורות']);
  if (rows().length) {
    out.push(['השורה מראה מה משתנה',
      /←|בכלל הכללי|אין הבדל/.test(rows()[0].textContent)]);
  }
  /* סינון לפי הסגמנט הראשון שיש לו חריגים */
  const withEx = segs.map(s => s.segment_id)
    .find(id => ev("allExceptions().filter(x=>x.seg===" + JSON.stringify(id) + ").length") > 0);
  if (withEx) {
    w.eval("S.segSel=" + JSON.stringify(withEx)); w.render();
    out.push(['סינון לפי סגמנט',
      rows().length === ev("allExceptions().filter(x=>x.seg===" + JSON.stringify(withEx) + ").length"),
      rows().length + ' שורות ב-' + withEx]);
    w.eval("S.segSel=''"); w.render();
  }

  const first = ev('allExceptions()[0]');
  if (!first) {
    console.log('אין חריגים בתוצר הזה; הרשימה והסינון נבדקו, והשאר דורש חריג.');
    report(out);
    return;
  }
  const rid = first.r.id, seg = first.seg;
  w.openSegEx(rid);
  setTimeout(() => {
    const card = () => (d.getElementById('rc-' + rid) || {innerHTML: ''}).innerHTML;
    out.push(['בלוק חריג בתוך הסעיף', card().indexOf('segex') >= 0]);
    out.push(['מוצג הכלל הכללי מול הסגמנט',
      card().indexOf('בכלל הכללי') >= 0 || card().indexOf('אין הבדל') >= 0]);
    /* הצעה לחריג: נשמרת, מסומנת, ואינה משנה את החריג שבמודל */
    /* העמדה כפי שהיא במודל, לפני כל הצעה */
    const vpos = () => {
      const v = ev('effVar(byId(' + JSON.stringify(rid) + '), '
        + JSON.stringify(seg) + ')') || {};
      return (v.green || {}).pos;
    };
    const modelPos = vpos();
    w.setVarEdit(rid, seg, 'green', 'pos', 'עמדה שהוצעה בבדיקת QA');
    out.push(['הצעה לחריג נשמרת',
      ev("Object.keys(S.varEdits||{}).length") > 0]);
    w.render();
    out.push(['ההצעה מסומנת "הצעה, לא מדיניות"',
      card().indexOf('הצעה, לא מדיניות') >= 0]);
    out.push(['ההצעה אינה משנה את החריג שבמודל',
      vpos() === modelPos]);
    w.clearVarEdit(rid, seg);
    out.push(['מחיקת ההצעה', ev("Object.keys(S.varEdits||{}).length") === 0]);
    /* הוספת חריג לסעיף שאין לו, בסגמנט קיים */
    const free = ev("(rulesOf().find(r=>!(r.variants||[]).length)||{}).id");
    if (free) {
      w.addUserVariant(free, seg);
      out.push(['הצעת חריג לסעיף נוסף',
        ev("!!S.userVariants[" + JSON.stringify(free + '|' + seg) + "]")]);
      w.delUserVariant(free, seg);
    }
    report(out);
  }, 120);
}, 600);

function report(out) {
  let bad = 0;
  out.forEach(([n, ok, note]) => {
    if (!ok) bad++;
    console.log((ok ? '✓' : '✗') + ' ' + n + (note ? '  [' + note + ']' : ''));
  });
  console.log(bad ? ('כשלים: ' + bad) : 'כל בדיקות הסגמנטים עברו');
  process.exit(bad ? 1 : 0);
}
