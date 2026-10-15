/* שורת הבסיס מופיעה בשני תוצרים: בשער ה-Word ובפס הבסיס בארטיפקט, והנוסח
   חייב להיות זהה. ב-Word הוא נגזר ב-basis_line.py, ובדף ב-basisText() שבתבנית,
   ושתי המימושים יכולים להיסחף. הבדיקה מריצה את שניהם על חמשת המצבים ומשווה.
   הרצה: JSDOM_PATH=<path> node scripts/qa_basis_line.js <dashboard.html> <basis_line.py> */
const {JSDOM,VirtualConsole}=require(process.env.JSDOM_PATH);
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

const page=process.argv[2];
const py=process.argv[3]||path.join(__dirname,'..','..','contract-playbook-builder','scripts','basis_line.py');

/* הצד של הדף */
const vc=new VirtualConsole(); vc.on('jsdomError',()=>{}); vc.on('error',()=>{});
const dom=new JSDOM(fs.readFileSync(page,'utf8'),{runScripts:'dangerously',pretendToBeVisual:true,
  virtualConsole:vc,url:'https://x/',
  beforeParse(w){Object.defineProperty(w,'Chart',{configurable:true,get:()=>function(){return{destroy(){}}},set:()=>{}});}});

setTimeout(()=>{
  const w=dom.window;
  const fromPage=CASES.map(c=>{
    w.eval('D.meta.build_path='+JSON.stringify(c)+';');
    return w.eval('basisText()');
  });
  /* הצד של ה-Word */
  const script=
    'import json,sys\n'+
    'sys.path.insert(0,'+JSON.stringify(path.dirname(py))+')\n'+
    'from basis_line import basis_line\n'+
    'cases=json.loads(sys.argv[1])\n'+
    'print(json.dumps([basis_line(c["n"],c["path"]) for c in cases],ensure_ascii=False))\n';
  const out=execFileSync('python3',['-c',script,JSON.stringify(CASES)],{encoding:'utf8'});
  const fromWord=JSON.parse(out);

  let bad=0;
  CASES.forEach((c,i)=>{
    const a=fromPage[i], b=fromWord[i];
    const same=a===b;
    if(!same)bad++;
    console.log((same?'✓':'✗')+' '+c.n+' הסכמים, '+c.path);
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
