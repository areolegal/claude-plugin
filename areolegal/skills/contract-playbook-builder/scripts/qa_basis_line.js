/* שורת הבסיס מופיעה בשני תוצרים: בשער ה-Word ובפס הבסיס בארטיפקט, והנוסח
   חייב להיות זהה. ב-Word הוא נגזר ב-basis_line.py, ובדף ב-basisText() שבתבנית,
   ושתי המימושים יכולים להיסחף. הבדיקה מריצה את שניהם על חמשת המצבים ומשווה.
   בדף באנגלית (meta.lang = en) הצד של ה-Word הוא basis_line_en שב-build_playbook_docx.py, שבונה את השער
   של ה-Word באנגלית, ואותם חמשת המצבים מושווים לנוסח האנגלי של basisText().
   מעמד המאגר (corpus_status: signed, mostly_drafts, company_forms, third_party_forms, unknown) משנה איך
   המסמכים נקראים בשורה, ולכן כל מצב נבדק גם בכל מעמד. מקרה בלי status הוא המודל הישן, שנקרא כ-signed.
   הרצה: JSDOM_PATH=<path> node scripts/qa_basis_line.js <dashboard.html> <basis_line.py> */
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
const fs=require('fs'), {execFileSync}=require('child_process'), path=require('path');

const CASES=[
  {n:24, path:'own'},
  {n:20, path:'own'},
  {n:19, path:'own'},
  {n:7,  path:'own'},
  {n:6,  path:'own'},
  {n:1,  path:'own'},
  {n:6,  path:'own_plus_market'},
  {n:1,  path:'own_plus_market'},
  {n:0,  path:'market_built'},
];
['signed','mostly_drafts','company_forms','third_party_forms','unknown'].forEach(st=>{
  [{n:24,path:'own'},{n:12,path:'own'},{n:4,path:'own'},{n:4,path:'own_plus_market'},{n:0,path:'market_built'}]
    .forEach(c=>CASES.push(Object.assign({status:st},c)));
});

const page=process.argv[2];
const py=process.argv[3]||path.join(__dirname,'basis_line.py');  /* basis_line.py יושב ליד הבדיקה, בחבילת זמן הריצה */

/* הצד של הדף */
const vc=new VirtualConsole(); vc.on('jsdomError',()=>{}); vc.on('error',()=>{});
const dom=new JSDOM(fs.readFileSync(page,'utf8'),{runScripts:'dangerously',pretendToBeVisual:true,
  virtualConsole:vc,url:'https://x/',
  beforeParse(w){Object.defineProperty(w,'Chart',{configurable:true,get:()=>function(){return{destroy(){}}},set:()=>{}});}});

setTimeout(()=>{
  const w=dom.window;
  const fromPage=CASES.map(c=>{
    w.eval('D.meta.build_path='+JSON.stringify({n:c.n,path:c.path})+';'+
      'if(D.scope)delete D.scope.corpus_status;'+
      (c.status?'D.meta.corpus_status='+JSON.stringify(c.status)+';':'delete D.meta.corpus_status;'));
    return w.eval('basisText()');
  });
  /* הצד של ה-Word */
  const EN=w.document.documentElement.getAttribute('lang')==='en';
  const script=
    'import json,sys\n'+
    'sys.path.insert(0,'+JSON.stringify(path.dirname(py))+')\n'+
    (EN?'from build_playbook_docx import basis_line_en as basis_line\n':'from basis_line import basis_line\n')+
    'cases=json.loads(sys.argv[1])\n'+
    'print(json.dumps([basis_line(c["n"],c["path"],c.get("status")) for c in cases],ensure_ascii=False))\n';
  /* ב-Windows הפקודה היא python, וב-macOS ו-Linux לרוב python3 */
  let out=null;
  for(const exe of (process.platform==='win32'?['python','python3']:['python3','python'])){
    try{ out=execFileSync(exe,['-c',script,JSON.stringify(CASES)],{encoding:'utf8',stdio:['ignore','pipe','pipe']}); break; }
    catch(e){ if(e.status!==null&&e.status!==9009&&!/not found/i.test(String(e.stderr||''))) throw e; }
  }
  if(out===null){ console.error('python לא נמצא / python was not found'); process.exit(1); }
  const fromWord=JSON.parse(out);

  let bad=0;
  CASES.forEach((c,i)=>{
    const a=fromPage[i], b=fromWord[i];
    const same=a===b;
    if(!same)bad++;
    console.log((same?'✓':'✗')+' '+c.n+' הסכמים, '+c.path+(c.status?', '+c.status:''));
    if(!same){ console.log('   בדף:  '+a); console.log('   ב-Word: '+b); }
  });
  /* בלי השדה אין שורה, בשני הצדדים */
  w.eval('delete D.meta.build_path;');
  const none=w.eval('basisText()');
  const ok=!none;
  if(!ok)bad++;
  console.log((ok?'✓':'✗')+' בלי הספירה אין שורה ואין המצאה');
  console.log(bad?('הפרשים: '+bad):'הנוסח זהה בשער ה-Word ובפס הבסיס');
  process.exit(bad?1:0);
},600);
