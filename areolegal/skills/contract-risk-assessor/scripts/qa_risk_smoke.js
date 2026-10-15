/* בדיקת עשן לתבנית דוח הסיכונים.

   הרתמה אינה מכוילת לנתוני לקוח: היא רצה על מרשם מינימלי
   (risk_smoke_fixture.json), ובודקת שהדוח נטען בלי שגיאות ריצה, שכל
   מסך בתפריט מרונדר, ושאין בו טעינת סקריפט או תמונה מהרשת. הגופן
   מ-Google Fonts מותר בתבנית הזאת.

   בלי הבדיקה הזאת שינוי בתבנית נבדק רק בעין, וכך נשברו בעבר וידג'ט
   הקליטה ותבנית הסיכונים: שורת פרוזה בתוך <script> שוברת את כל הדף.

   בנייה והרצה:
     python3 build_risk_report.py --data risk_smoke_fixture.json \
         --template <תבנית> --out /tmp/risk.html
     JSDOM_PATH=<נתיב ל-jsdom> node qa_risk_smoke.js /tmp/risk.html  */
const {JSDOM, VirtualConsole} = require(process.env.JSDOM_PATH);
const fs = require('fs');
const errs = [];
const vc = new VirtualConsole();
vc.on('jsdomError', e => errs.push(e.message));
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
  /* גופן מ-Google Fonts מותר בתבנית הזאת; סקריפט או תמונה מהרשת אינם */
  const ext = [...d.querySelectorAll('script[src],img[src],link[href]')]
    .map(e => e.getAttribute('src') || e.getAttribute('href') || '')
    .filter(u => /^https?:/i.test(u) && !/^https:\/\/fonts\.(googleapis|gstatic)\.com/.test(u));
  out.push(['אין סקריפט או תמונה מהרשת', ext.length === 0, ext.slice(0, 2).join(' | ')]);
  let n = 0;
  out.forEach(([t, ok, note]) => {
    if (!ok) n++;
    console.log((ok ? '✓' : '✗') + ' ' + t + (note ? '  [' + note + ']' : ''));
  });
  console.log(n ? ('כשלים: ' + n) : 'תבנית הסיכונים עוברת בדיקת עשן');
  process.exit(n ? 1 : 0);
}, 700);
