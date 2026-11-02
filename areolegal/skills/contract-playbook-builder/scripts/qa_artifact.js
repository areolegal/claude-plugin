/* בדיקת קבלה גנרית, אינה תלויה בקורפוס. בודקת את שני התוצרים:
   הצגת כל המסכים, הטמעת ספריית הגרפים, גישה למסמכי המקור, וניטרול ההורדות בעמוד משותף.
   הרצה: JSDOM_PATH=<path> node scripts/qa_artifact.js <local.html> <artifact.html> */
const fs=require('fs');
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
const {JSDOM,VirtualConsole}=loadJsdom();
const VIEWS=['overview','rules','compare','findings','additions','segpolicy','precedents','sources','decisions','export'];
let fails=0;
const ok=(c,m)=>{ console.log(c?'PASS':'FAIL',m); if(!c) fails++; };

function boot(file){
  const errs=[], downloads=[], toasts=[], charts=[];
  const vc=new VirtualConsole();
  vc.on('jsdomError',e=>{ if(!/scroll|print|navigation|resource|opaque|canvas/i.test(e.message)) errs.push(e.message.slice(0,150)); });
  vc.on('error',()=>{});
  const dom=new JSDOM(fs.readFileSync(file,'utf8'),{runScripts:'dangerously',pretendToBeVisual:true,virtualConsole:vc,url:'https://localhost/',
    beforeParse(window){
      const stub=function(el,cfg){ charts.push(cfg&&cfg.type); return {destroy(){}}; };
      Object.defineProperty(window,'Chart',{configurable:true,get:()=>stub,set:()=>{}});
      window.print=()=>{}; window.confirm=()=>true;
      window.URL.createObjectURL=()=>'blob:x'; window.URL.revokeObjectURL=()=>{};
    }});
  const w=dom.window;
  w.HTMLAnchorElement.prototype.click=function(){ if(this.download) downloads.push(this.download); };
  w.Element.prototype.scrollIntoView=function(){};
  Object.defineProperty(w.navigator,'clipboard',{value:{writeText:()=>Promise.resolve()},configurable:true});
  return {w, d:w.document, errs, downloads, charts};
}

function run(file, label, published){
  console.log('\n== '+label);
  const {w,d,errs,downloads,charts}=boot(file);
  ok(errs.length===0,'  אפס שגיאות ריצה'+(errs[0]?': '+errs[0]:''));
  ok(typeof w.Chart!=='undefined','  ספריית הגרפים זמינה');
  ok(fs.readFileSync(file,'utf8').indexOf('cdn.jsdelivr.net')<0,'  אין טעינה מרשת חיצונית');
  VIEWS.forEach(v=>{
    let threw=null;
    try{ w.go(v); }catch(e){ threw=e.message.slice(0,80); }
    const html=d.getElementById('wrap').innerHTML;
    ok(!threw && html.length>50,'  מסך '+v+(threw?': '+threw:''));
  });
  w.go('sources');
  /* הבדיקה נגזרת מהנתונים: תוצר שבו אין לאף מקור כתובת https אינו אמור
     להציג קישורים, והדרישה היא שכל קישור שכן מוצג ייפתח בכרטיסייה חדשה.
     הגרסה הקודמת דרשה קישור תמיד, ולכן נכשלה על מטען בלי מקורות רשת. */
  const withUrl=w.eval("[].concat(Object.values(D.sources||{}),D.market||[],D.external_sources||[])"
    + ".filter(s=>s&&typeof s.url==='string'&&/^https:\\/\\//i.test(s.url)).length");
  const links=[...d.querySelectorAll('#wrap a[href^="https://"]')];
  if(withUrl){
    ok(links.length>0,'  קישורים למקורות: '+links.length+' (מתוך '+withUrl+' מקורות עם כתובת)');
    ok(links.every(a=>a.target==='_blank'&&/noopener/.test(a.rel||'')),
      '  כל קישור נפתח בכרטיסייה חדשה');
  } else {
    ok(links.length===0,'  אין מקור עם כתובת https, ולכן אין קישורים');
  }
  /* ההורדה היחידה שנשארה בדף היא ההערות וההצעות: אין ייצוא Office,
     אין חבילת סוכן ואין יומן החלטות (`dashboard_spec.md`, "מה אסור") */
  const gone=['dl','agentPack','showOut','officeBlob','decide','approveAll']
    .filter(n=>typeof w[n]==='function');
  ok(gone.length===0,'  אין בדף פעולות אישור וייצוא'+(gone.length?': '+gone.join(', '):''));
  /* הערות נכתבות רק באשף: בדף אין תיבת הערה, אין מצב עריכה ואין כפתור הורדת הערות */
  w.go('decisions');
  const html=w.document.documentElement.outerHTML;
  ok(!html.includes('class="noteta"') && !w.document.getElementById('editChip') && !html.includes('onclick="dlComments()"'),
     '  אין בדף תיבת הערה, מצב עריכה או הורדת הערות');
  return fails;
}

run(process.argv[2]||'local.html','קובץ HTML מקומי',false);
run(process.argv[3]||'artifact.html','תוכן לעמוד משותף',true);
console.log(fails?('\nFAILURES: '+fails):'\nALL PASSED');
process.exit(fails?1:0);
