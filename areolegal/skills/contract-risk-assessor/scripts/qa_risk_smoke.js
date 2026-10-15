/* בדיקת עשן לתבנית דוח הסיכונים.

   הרתמה אינה מכוילת לנתוני לקוח: היא רצה על מרשם לדוגמה בסכמה 3.6
   (קוד הייחוס, tests/fixtures/risk/c2_register.json), ובודקת שהדוח נטען בלי
   שגיאות ריצה, שכל מסך בתפריט מרונדר, ושאין בו שום טעינה מהרשת, גם לא
   גופן. הבדיקה המלאה, בדפדפן אמיתי, היא risk/render_check.py.

   בלי הבדיקה הזאת שינוי בתבנית נבדק רק בעין, וכך נשברו בעבר וידג'ט
   הקליטה ותבנית הסיכונים: שורת פרוזה בתוך <script> שוברת את כל הדף.

   בנייה והרצה:
     python3 build_risk_report.py --data <תיקיית עסקה>/risk-register.json --template <תבנית>
     JSDOM_PATH=<נתיב ל-jsdom> node qa_risk_smoke.js "<תיקיית עסקה>/Areo Workspace - סיכונים.html"  */
const {JSDOM, VirtualConsole} = require(process.env.JSDOM_PATH);
const fs = require('fs');
const errs = [];
const vc = new VirtualConsole();
vc.on('jsdomError', e => {
  /* שורת "טיוטה, טעונה אישור" בכותרת כל עמוד מודפס נכתבת בתיבות השוליים של
     @page (@top-center, @bottom-center). Chrome תומך בהן; המפרש של jsdom
     אינו מכיר @page מקונן, ונכשל דווקא עליהן. רק השגיאה הזאת, ורק כשזה
     תוכנה, אינה נספרת. כל שגיאת CSS אחרת עדיין נכשלת */
  const detail = String(e.detail || '');
  if (/Could not parse CSS stylesheet/.test(e.message)
      && /^\s*@page\s*\{\s*@(top|bottom)-(left|center|right)\s*\{/.test(detail)) return;
  errs.push(e.message);
});
vc.on('error', (...a) => errs.push(String(a[0])));
const dom = new JSDOM(fs.readFileSync(process.argv[2], 'utf8'),
  {runScripts: 'dangerously', pretendToBeVisual: true, virtualConsole: vc, url: 'https://x/',
   beforeParse(w) {
     Object.defineProperty(w, 'Chart', {configurable: true,
       get: () => function () { return {destroy() {}}; }, set: () => {}});
     w.scrollTo = () => {};
     w.matchMedia = w.matchMedia || (() => ({matches: false, addListener(){}, addEventListener(){}}));
   }});
const w = dom.window, d = w.document;
setTimeout(() => {
  const out = [];
  out.push(['אפס שגיאות ריצה', errs.length === 0, errs.slice(0, 2).join(' | ')]);
  /* התפריט נבנה עם data-v, ולא עם onclick */
  const views = [...new Set([...d.querySelectorAll('[data-v]')]
    .map(b => b.getAttribute('data-v')).filter(Boolean))];
  out.push(['יש מסכים בתפריט', views.length > 0, views.join(', ')]);
  let bad = [];
  views.forEach(v => {
    try { w.go(v); } catch (e) { bad.push(v + ': ' + e.message.slice(0, 60)); return; }
    const wrap = d.getElementById('wrap') || d.querySelector('main');
    if (!wrap || wrap.innerHTML.length < 30) bad.push(v + ': ריק');
  });
  out.push(['כל מסך מרונדר', bad.length === 0, bad.join(' | ')]);
  /* שום דבר מהרשת: לא סקריפט, לא תמונה ולא גופן */
  const ext = [...d.querySelectorAll('script[src],img[src],link[href]')]
    .map(e => e.getAttribute('src') || e.getAttribute('href') || '')
    .filter(u => /^https?:/i.test(u));
  out.push(['אין טעינה מהרשת', ext.length === 0, ext.slice(0, 2).join(' | ')]);
  let n = 0;
  out.forEach(([t, ok, note]) => {
    if (!ok) n++;
    console.log((ok ? '✓' : '✗') + ' ' + t + (note ? '  [' + note + ']' : ''));
  });
  console.log(n ? ('כשלים: ' + n) : 'תבנית הסיכונים עוברת בדיקת עשן');
  process.exit(n ? 1 : 0);
}, 700);
