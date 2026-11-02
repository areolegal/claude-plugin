/* וידג'ט הקליטה: בחירה יחידה של סוג, הרצועה לפי מספר ההסכמים,
   חסימה בלי בחירת מסלול, והשורה שנשלחת לצ'אט.
   הרצה: JSDOM_PATH=<path> node qa_intake.js <widget.html> */
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
const {JSDOM,VirtualConsole}=loadJsdom(); const fs=require('fs');
const FAMS=[
 {n:"משפחה א", p:"הצד המזמין / הרוכש", u:24, d:"2 כפילויות"},
 {n:"משפחה ב", p:"צד ב", u:9, r:["צד א","צד ב"]},
 {n:"משפחה ג", p:"צד א", u:4},
 {n:"משפחה ד", p:"צד ב", u:0}];
function load(){
  let html=fs.readFileSync(process.argv[2],'utf8')
    .replace('__FAMILIES__',JSON.stringify(FAMS))
    .replace('__FOLDERS__','[]')
    .replace('"__DRAFTS__"','"0"').replace('"__MODE__"','"scan"');
  const vc=new VirtualConsole(); const errs=[];
  vc.on('jsdomError',e=>errs.push(String(e.message||e)));
  const dom=new JSDOM('<!doctype html><body>'+html+'</body>',
    {runScripts:'dangerously',virtualConsole:vc,url:'https://x/'});
  dom.window.sendPrompt=t=>{dom.window.__sent=t;};
  return {dom, errs};
}
const {dom,errs}=load(); const w=dom.window, d=w.document;
const out=[];
const vis=id=>{const e=d.getElementById(id);return !!e&&!e.hidden;};
out.push(['אפס שגיאות ריצה', errs.length===0, errs[0]||'']);
const chips=[...d.querySelectorAll('#type .chip')];
out.push(['כפתור לכל סוג, ועוד "סוג אחר"', chips.length===5, chips.length+' כפתורים']);
out.push(['המספר והניכוי בכפתור', chips[0].textContent.indexOf('24 הסכמים')>0 &&
  chips[0].textContent.indexOf('2 כפילויות')>0, chips[0].textContent]);
/* 24 הסכמים: לא מוצגת שום רצועה */
chips[0].onclick();
out.push(['ב-24 הסכמים אין רצועה', !vis('band-mid')&&!vis('band-low')&&!vis('band-zero')]);
out.push(['ב-24 הסכמים אין הודעה שהמחקר החיצוני הוא חלק מהבנייה', !vis('reg-fixed')]);
out.push(['ב-24 הסכמים נשאלת בחירת מחקר השוק', vis('band-res')&&d.querySelectorAll('#res .chip').length===3]);
out.push(['ברירת המחדל במחקר השוק: רק ההסכמים שלנו, בלי מחקר חיצוני', (()=>{const on=[...d.querySelectorAll('#res .chip')].filter(b=>b.getAttribute('aria-pressed')==='true');
  return on.length===1&&on[0].textContent.indexOf('המסמכים המשפטיים שלי')>=0;})()]);
out.push(['ב-24 הסכמים אין הערת 15', !vis('band-under15')]);
out.push(['אין שאלת "כל ההסכמים"', !d.getElementById('all') && !d.getElementById('q-all')]);
out.push(['שאלת הפוזיציה נבנתה לסוג שנבחר', !!d.getElementById('pos')]);
out.push(['הנחת הפוזיציה סומנה', [...d.querySelectorAll('#pos .chip')]
  .some(b=>b.getAttribute('aria-pressed')==='true')]);
/* 9 הסכמים: רצועת האמצע, עם המספר בתוכה */
chips[1].onclick();
out.push(['ב-9 הסכמים מוצגת רצועת האמצע', vis('band-mid')&&!vis('band-low')]);
out.push(['המספר נכתב ברצועה', d.querySelector('#band-mid .n').textContent==='9']);
out.push(['ב-9 הסכמים מוצגת הערת 20 הסכמים וטיוטות', vis('band-under15') &&
  d.querySelector('#band-under15 .help').textContent.indexOf('20 הסכמים וטיוטות')>0]);
/* הצדדים של הסוג נקראו משני הסכמים: הכפתורים הם הם, ועוד הדדי ו"לא מופיע ברשימה" */
const roleChips=[...d.querySelectorAll('#pos .chip')].map(b=>b.textContent);
out.push(['כפתורי הצד הם הצדדים שנקראו מההסכמים', roleChips[0]==='צד א' && roleChips[1]==='צד ב' &&
  roleChips.length===4, roleChips.join(' | ')]);
out.push(['בסוג בלי צדדים שנקראו, שלוש התוויות הכלליות', (()=>{chips[0].onclick();
  const c=[...d.querySelectorAll('#pos .chip')].map(b=>b.textContent); chips[1].onclick();
  return c.length===4 && c[0]==='הצד המזמין / הרוכש';})()]);
out.push(['בחירה יחידה: הסוג הקודם כבר אינו מסומן',
  chips[0].getAttribute('aria-pressed')==='false']);
/* 4 הסכמים: בחירת מסלול, והיא חוסמת */
chips[2].onclick();
out.push(['ב-4 הסכמים מוצגת בחירת הבסיס, ורצועת המדגם הקטן', vis('band-low')&&vis('band-res')&&!!d.querySelector('#res .chip')]);
out.push(['ב-4 הסכמים אין הודעה שהמחקר החיצוני הוא חלק מהבנייה', !vis('reg-fixed')]);
out.push(['ב-4 הסכמים ברירת המחדל: רק ההסכמים שלנו', (()=>{const on=[...d.querySelectorAll('#res .chip')].filter(b=>b.getAttribute('aria-pressed')==='true');
  return on.length===1&&on[0].textContent.indexOf('המסמכים המשפטיים שלי')>=0;})()]);
out.push(['ב-4 הסכמים שלושה כפתורים: מסמכים, שוק, גם וגם', [...d.querySelectorAll('#res .chip')].length===3]);
out.push(['שאלת הבסיס אחת לכל מספר הסכמים (ב-4 מוצגת אותה רצועה)', (()=>{const a=d.querySelector('#band-res .ask').textContent; return a==='על פי מה לגזור את הפלייבוק?' && vis('band-res');})()]);
/* הפוזיציה כבר מסומנת מההנחה; בוחרים אחרת, ולא מכבים את הקיימת */
[...d.querySelectorAll('#pos .chip')][0].onclick();
[...d.querySelectorAll('#dep .chip')][0].onclick();
[...d.querySelectorAll('#cmp .chip')][1].onclick();
[...d.querySelectorAll('#tpl .chip')][2].onclick();
/* מכבים את הבחירה (לחיצה שנייה על הכפתור המסומן): בלי בחירה לא נשלח דבר */
[...d.querySelectorAll('#res .chip')].filter(b=>b.getAttribute('aria-pressed')==='true')[0].onclick();
d.getElementById('go').onclick();
out.push(['בלי בחירת מסלול לא נשלח דבר', !w.__sent &&
  d.getElementById('err').textContent.indexOf('על פי מה')>=0, d.getElementById('err').textContent]);
[...d.querySelectorAll('#res .chip')].filter(b=>b.textContent.indexOf('גם וגם')===0)[0].onclick();
d.getElementById('go').onclick();
const sent=w.__sent||'';
out.push(['אחרי הבחירה נשלחה שורה', !!sent]);
out.push(['המסלול שנבחר נשלח', sent.indexOf('אופן הבנייה: שילוב עם מחקר שוק')>0, sent.slice(0,150)]);
out.push(['אין שאלת פורמט: שני התוצרים תמיד', !d.getElementById('fmt') && sent.indexOf('פורמטים')<0]);
out.push(['מספר ההסכמים נשלח', sent.indexOf('הסכמים: 4')>0]);
out.push(['"כל ההסכמים" אינו נשלח', sent.indexOf('כל ההסכמים')<0]);
out.push(['ב-4 הסכמים מוצגת הערת 20 הסכמים וטיוטות', vis('band-under15')]);
out.push(['המחקר החיצוני נרשם לפי בחירת הלקוח (שילוב: כן)', sent.indexOf('מחקר רגולטורי: כן, חלק מהבנייה לפי בחירתכם')>0]);
/* ברירת המחדל ב-24 הסכמים: בלי מחקר חיצוני. ובשילוב: כן */
(()=>{ const x=load(); const dd=x.dom.window.document, ww=x.dom.window; const cs=[...dd.querySelectorAll('#type .chip')];
  cs[0].onclick(); [...dd.querySelectorAll('#pos .chip')].filter(b=>b.getAttribute('aria-pressed')==='true').length||[...dd.querySelectorAll('#pos .chip')][0].onclick();
  [...dd.querySelectorAll('#dep .chip')][0].onclick(); [...dd.querySelectorAll('#cmp .chip')][1].onclick(); [...dd.querySelectorAll('#tpl .chip')][2].onclick();
  dd.getElementById('go').onclick(); const s1=ww.__sent||'';
  out.push(['ב-24 הסכמים בברירת מחדל נשלח: מחקר חיצוני לא', s1.indexOf('מחקר רגולטורי: לא, בלי מחקר מחוץ לתיקייה')>0 && s1.indexOf('אופן הבנייה: רק ההסכמים שלנו')>0, s1.slice(0,200)]);
  [...dd.querySelectorAll('#res .chip')].filter(b=>b.textContent.indexOf('גם וגם')===0)[0].onclick();
  out.push(['בבחירת שילוב ב-24 הסכמים שאלת ההשוואה נעלמת', dd.getElementById('q-cmp').hidden===true]);
  ww.__sent=''; dd.getElementById('go').onclick(); const s2=ww.__sent||'';
  out.push(['ב-24 הסכמים בשילוב נשלח: מחקר כן', s2.indexOf('אופן הבנייה: שילוב עם מחקר שוק')>0 && s2.indexOf('מחקר רגולטורי: כן, חלק מהבנייה לפי בחירתכם')>0, s2.slice(0,220)]); })();
/* אנגלית: אותה בחירה, אותה הודעה */
(()=>{ let html=fs.readFileSync(process.argv[2],'utf8').replace('__FAMILIES__',JSON.stringify(FAMS)).replace('__FOLDERS__','[]')
    .replace('"__DRAFTS__"','"0"').replace('"__MODE__"','"scan"').replace('"__LANG__"','"en"');
  const vc=new VirtualConsole(); const er=[]; vc.on('jsdomError',e=>er.push(String(e.message||e)));
  const dm=new JSDOM('<!doctype html><body>'+html+'</body>',{runScripts:'dangerously',virtualConsole:vc,url:'https://x/'});
  dm.window.sendPrompt=t=>{dm.window.__sent=t;}; const dd=dm.window.document;
  [...dd.querySelectorAll('#type .chip')][0].onclick(); [...dd.querySelectorAll('#pos .chip')][0].onclick();
  [...dd.querySelectorAll('#dep .chip')][0].onclick(); [...dd.querySelectorAll('#cmp .chip')][1].onclick(); [...dd.querySelectorAll('#tpl .chip')][2].onclick();
  dd.getElementById('go').onclick(); const s=dm.window.__sent||'';
  const ui=[...dd.querySelectorAll('#af *')].filter(e=>e.children.length===0&&!e.closest('#type')&&!e.closest('.foot-he')&&!e.closest('#pos')&&!e.closest('#dep')).map(e=>e.textContent).join(' ');
  out.push(['אנגלית: אפס שגיאות, וההודעה בבחירת המחקר', er.length===0 && s.indexOf('Regulatory research: No, nothing outside the folder')>0, er[0]||s.slice(0,220)]);
  out.push(['אנגלית: אין עברית בתוויות הטופס', !/[֐-׿]/.test(ui), (ui.match(/[֐-׿]+/)||[''])[0]]); })();
/* אפס הסכמים: המסלול השני */
chips[3].onclick();
out.push(['באפס הסכמים מוצגת בחירת השוק', vis('band-zero')&&!!d.querySelector('#path0 .chip')]);
out.push(['באפס הסכמים אין שאלת תבנית', !vis('q-tpl')]);
let bad=0; out.forEach(([n,ok,note])=>{ if(!ok)bad++;
  console.log((ok?'✓':'✗')+' '+n+(note?'  ['+String(note).slice(0,120)+']':'')); });
console.log(bad?('כשלים: '+bad):'וידג\'ט הקליטה עובר'); process.exit(bad?1:0);
