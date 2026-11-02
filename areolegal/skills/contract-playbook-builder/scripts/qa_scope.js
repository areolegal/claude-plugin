/* הבחירה חלה על כל המסכים, לא רק על הסעיפים. דורש דף של כמה פלייבוקים.
   הרצה: JSDOM_PATH=<path> node qa_scope.js <dashboard.html> */
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
const vc=new VirtualConsole(); vc.on('jsdomError',()=>{}); vc.on('error',()=>{});
const dom=new JSDOM(fs.readFileSync(process.argv[2]||'dash.html','utf8'),{runScripts:'dangerously',pretendToBeVisual:true,virtualConsole:vc,url:'https://x/',
 beforeParse(w){Object.defineProperty(w,'Chart',{configurable:true,get:()=>function(){return{destroy(){}}},set:()=>{}});}});
const w=dom.window,d=w.document,ev=x=>w.eval(x);
setTimeout(()=>{
  const out=[];
  /* דף של פלייבוק אחד: אין בחירה לבדוק. הודעה ברורה במקום TypeError */
  if(ev("!Array.isArray(D.playbooks) || D.playbooks.length<2")){
    console.log('בדף הזה פלייבוק אחד, ולכן אין בחירה לבדוק. להרצה אמיתית דרוש דף של כמה פלייבוקים (build_workspace_payload.py --data).');
    process.exit(0);
  }
  /* רק מסכים שהדף מציג: מסך הסגמנטים מוסתר כשאין סגמנטים, ומעבר אליו
     מחזיר לתמונת מצב, שבה אין פס בכוונה */
  const views=['rules','compare','segpolicy','findings','decisions','export']
    .filter(v=>ev('viewShown(VIEWS.find(x=>x.id==='+JSON.stringify(v)+'))'));
  let everywhere=true, missing='';
  views.forEach(v=>{ w.go(v); if(!d.querySelector('#pbbar .pbbar')){ everywhere=false; missing+=v+' '; } });
  out.push(['פס הבחירה בכל המסכים הפנימיים', everywhere, missing]);
  w.go('overview');
  out.push(['אין פס בתמונת מצב', !d.querySelector('#pbbar .pbbar')]);
  out.push(['החלפת סוג הסכם קיימת בכרטיס שבתמונת מצב',
    d.getElementById('wrap').textContent.indexOf('מעבר לסוג הסכם אחר')>=0]);
  w.go('segpolicy');
  const a=ev('allExceptions().length');
  /* סוג הסכם אחר מזה שנבחר, ולא מיקום קבוע ברשימה */
  w.setPb(ev("(D.playbooks.find(p=>p.id!==S.pb)||{}).id"));
  const b=ev('allExceptions().length');
  /* כששני הסוגים בלי חריגים, השוואת המספרים אינה אומרת דבר */
  out.push(['מסך החריגים מסונן לפי הבחירה', a!==b || (a===0&&b===0), a+' ← '+b]);
  w.go('overview');
  const kpi=d.querySelectorAll('#kpirow .statn')[1].textContent.trim();
  out.push(['מספרי תמונת מצב לפי הבחירה', kpi===String(ev('rulesOf().length')), kpi]);
  w.setPb(ev("(D.playbooks.find(p=>p.current)||{}).id"));
  let bad=0; out.forEach(([n,ok,note])=>{ if(!ok)bad++; console.log((ok?'✓':'✗')+' '+n+(note?'  ['+note+']':'')); });
  console.log(bad?('כשלים: '+bad):'הבחירה חלה בכל המסכים'); process.exit(bad?1:0);
},500);
