/* סקיל בגרסה ישנה שולח משפחות בלי מספר הסכמים. הטופס אינו מציג אפס,
   אינו חוסם, ושולח "לא צוין". */
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
const FAMS=[{n:"משפחה א", p:"צד א", s:"מקור: תיקייה א"},
            {n:"משפחה ב", p:"צד ב"}];
let html=fs.readFileSync(process.argv[2],'utf8')
  .replace('__FAMILIES__',JSON.stringify(FAMS)).replace('__FOLDERS__','[]')
  .replace('"__DRAFTS__"','"0"').replace('"__MODE__"','"scan"');
const vc=new VirtualConsole(); const errs=[]; vc.on('jsdomError',e=>errs.push(String(e.message||e)));
const dom=new JSDOM('<!doctype html><body>'+html+'</body>',{runScripts:'dangerously',virtualConsole:vc,url:'https://x/'});
const w=dom.window,d=w.document; w.sendPrompt=t=>{w.__sent=t;};
const out=[], vis=id=>{const e=d.getElementById(id);return !!e&&!e.hidden;};
out.push(['אפס שגיאות ריצה', errs.length===0, errs[0]||'']);
const chips=[...d.querySelectorAll('#type .chip')];
out.push(['הכפתור אינו מציג "0 הסכמים"', chips[0].textContent.indexOf('0 הסכמים')<0, chips[0].textContent]);
chips[0].onclick();
out.push(['אין רצועה כשהמספר אינו ידוע', !vis('band-mid')&&!vis('band-low')&&!vis('band-zero')]);
out.push(['אין הודעת מחקר קבוע', !vis('reg-fixed')]);
/* שאלת "כל ההסכמים" הוסרה מהטופס (הכרעת ניל, 18.10.2026), ולכן נבדקת רק שאלת התבנית */
out.push(['שאלת התבנית כן מוצגת', vis('q-tpl')]);
[...d.querySelectorAll('#pos .chip')][0].onclick();
[...d.querySelectorAll('#dep .chip')][0].onclick();
[...d.querySelectorAll('#cmp .chip')][1].onclick();
[...d.querySelectorAll('#tpl .chip')][2].onclick();
d.getElementById('go').onclick();
const sent=w.__sent||'';
out.push(['הטופס אינו חוסם', !!sent, d.getElementById('err').textContent]);
out.push(['המספר נשלח כ"לא צוין"', sent.indexOf('הסכמים: לא צוין')>0, sent.slice(0,130)]);
out.push(['המסלול נשלח כלא צוין', sent.indexOf('אופן הבנייה: לא צוין')>0]);
let bad=0; out.forEach(([n,ok,note])=>{ if(!ok)bad++;
  console.log((ok?'✓':'✗')+' '+n+(note?'  ['+String(note).slice(0,110)+']':'')); });
console.log(bad?('כשלים: '+bad):'הטופס סובל סקיל בגרסה ישנה'); process.exit(bad?1:0);
