/* וידג'ט הקליטה: בחירה יחידה של סוג, הרצועה לפי מספר ההסכמים,
   חסימה בלי בחירת מסלול, והשורה שנשלחת לצ'אט.
   הרצה: JSDOM_PATH=<path> node qa_intake.js <widget.html> */
const {JSDOM,VirtualConsole}=require(process.env.JSDOM_PATH); const fs=require('fs');
const FAMS=[
 {n:"הסכם שירותים", p:"הצד המספק / הנותן", u:24, d:"2 כפילויות"},
 {n:"הסכם סודיות", p:"הצד המזמין / הרוכש", u:9, r:["המשכיר","השוכר"]},
 {n:"הסכם הפצה", p:"הצד המספק / הנותן", u:4},
 {n:"הסכם רישוי", p:"הצד המזמין / הרוכש", u:0}];
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
out.push(['ב-24 הסכמים אין הודעת מחקר קבוע', !vis('reg-fixed')]);
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
out.push(['כפתורי הצד הם הצדדים שנקראו מההסכמים', roleChips[0]==='המשכיר' && roleChips[1]==='השוכר' &&
  roleChips.length===4, roleChips.join(' | ')]);
out.push(['בסוג בלי צדדים שנקראו, שלוש התוויות הכלליות', (()=>{chips[0].onclick();
  const c=[...d.querySelectorAll('#pos .chip')].map(b=>b.textContent); chips[1].onclick();
  return c.length===4 && c[0]==='הצד המזמין / הרוכש';})()]);
out.push(['בחירה יחידה: הסוג הקודם כבר אינו מסומן',
  chips[0].getAttribute('aria-pressed')==='false']);
/* 4 הסכמים: בחירת מסלול, והיא חוסמת */
chips[2].onclick();
out.push(['ב-4 הסכמים מוצגת בחירת המסלול', vis('band-low')&&!!d.querySelector('#path .chip')]);
out.push(['ב-4 הסכמים המחקר הוא חלק מהבנייה', vis('reg-fixed')]);
/* הפוזיציה כבר מסומנת מההנחה; בוחרים אחרת, ולא מכבים את הקיימת */
[...d.querySelectorAll('#pos .chip')][0].onclick();
[...d.querySelectorAll('#dep .chip')][0].onclick();
[...d.querySelectorAll('#cmp .chip')][1].onclick();
[...d.querySelectorAll('#tpl .chip')][2].onclick();
d.getElementById('go').onclick();
out.push(['בלי בחירת מסלול לא נשלח דבר', !w.__sent &&
  d.getElementById('err').textContent.indexOf('כיצד לבנות')>=0, d.getElementById('err').textContent]);
[...d.querySelectorAll('#path .chip')][0].onclick();
d.getElementById('go').onclick();
const sent=w.__sent||'';
out.push(['אחרי הבחירה נשלחה שורה', !!sent]);
out.push(['המסלול שנבחר נשלח', sent.indexOf('מסלול: שילוב עם מחקר שוק')>0, sent.slice(0,150)]);
out.push(['אין שאלת פורמט: שני התוצרים תמיד', !d.getElementById('fmt') && sent.indexOf('פורמטים')<0]);
out.push(['מספר ההסכמים נשלח', sent.indexOf('הסכמים: 4')>0]);
out.push(['"כל ההסכמים" אינו נשלח', sent.indexOf('כל ההסכמים')<0]);
out.push(['ב-4 הסכמים מוצגת הערת 20 הסכמים וטיוטות', vis('band-under15')]);
out.push(['המחקר הרגולטורי נגזר ולא נשאל', sent.indexOf('חלק מהבנייה')>0]);
/* אפס הסכמים: המסלול השני */
chips[3].onclick();
out.push(['באפס הסכמים מוצגת בחירת השוק', vis('band-zero')&&!!d.querySelector('#path0 .chip')]);
out.push(['באפס הסכמים אין שאלת תבנית', !vis('q-tpl')]);
let bad=0; out.forEach(([n,ok,note])=>{ if(!ok)bad++;
  console.log((ok?'✓':'✗')+' '+n+(note?'  ['+String(note).slice(0,120)+']':'')); });
console.log(bad?('כשלים: '+bad):'וידג\'ט הקליטה עובר'); process.exit(bad?1:0);
