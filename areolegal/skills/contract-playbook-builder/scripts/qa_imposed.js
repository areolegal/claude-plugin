/* סגמנט שאין בו משא ומתן מוצג בשלוש השכבות שלו ולא כרמזור, וחריג שקורא
   יוצר מסומן "הצעה, לא מדיניות". אין בשום מסך פעולת אישור על סגמנט.

   **הרתמה אינה מכוילת לפלייבוק מסוים.** היא בודקת את התבנית, ולכן כשבדף אין
   את שני סגמנטי הבדיקה (SEG-BID כפוי ו-SEG-REG רגיל) היא מוסיפה אותם לנתונים
   שבתוך הדף, על שלושת הנושאים הראשונים של סוג ההסכם שנבחר. כך היא רצה על כל
   דף שנבנה, גם על ההדגמה שאין בה סגמנטים, ולא נכשלת על נתונים חסרים.
   הרצה: JSDOM_PATH=<path> node qa_imposed.js <dashboard.html> */
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
const dom=new JSDOM(fs.readFileSync(process.argv[2],'utf8'),{runScripts:'dangerously',
  pretendToBeVisual:true,virtualConsole:vc,url:'https://x/',
  beforeParse(w){Object.defineProperty(w,'Chart',{configurable:true,get:()=>function(){return{destroy(){}}},set:()=>{}});}});
const w=dom.window,d=w.document,ev=x=>w.eval(x);
/* שני סגמנטי הבדיקה, בצורה ש-build_workspace_payload.py כותב לדף: הסגמנט
   ב-D.segments, והווריאנט על הנושא שהוא משנה (r.variants[].seg). הכפוי נושא
   את שלוש השכבות (segmentation.md, §12) ולא רמזור. נוסף רק כשאינו בדף */
const FIXTURE=`(function(){
  const rs=rulesOf(); if(rs.length<3) return 'פחות משלושה נושאים';
  D.segments=D.segments||[];
  const has=id=>D.segments.some(s=>s.segment_id===id);
  if(!has('SEG-BID')){
    D.segments.push({segment_id:'SEG-BID',label:'הליך תחרותי ציבורי',criteria:'התקשרות בהליך שתנאיו נקבעו מראש',status:''});
    (rs[0].variants=rs[0].variants||[]).push({seg:'SEG-BID',mode:'imposed',
      imposed_regime:[{topic:'אחריות בלי תקרה',imposed:'מסמכי ההליך קובעים אחריות מלאה של הצד השני',
        effect:'חשיפה בלתי מוגבלת לנזקי המזמין'}],
      clarification_positions:{green:{pos:'לבקש בשאלות ההבהרה תקרה בגובה התמורה'},
        yellow:{pos:'לבקש תקרה בגובה פי שניים מהתמורה',label:'הצעת Areo (לא מבוסס על מסמכי הלקוח)'}},
      bid_conditions:[{recommendation:'ניגשים רק באישור הנהלה ועם ביטוח מתאים',
        combination:'אחריות בלי תקרה ובלי ביטוח',why:'החשיפה עולה על שווי ההתקשרות'}]});
  }
  if(!has('SEG-REG')){
    D.segments.push({segment_id:'SEG-REG',label:'גוף מפוקח',criteria:'הלקוח הוא גוף מפוקח',status:''});
    (rs[1].variants=rs[1].variants||[]).push({seg:'SEG-REG',mode:'negotiable',
      tl:{green:{pos:'תקרה בגובה התמורה השנתית'},yellow:{pos:'תקרה בגובה פי שניים מהתמורה השנתית'},
        red:{pos:'אחריות בלי תקרה'}}});
  }
  render(); return '';
})()`;
setTimeout(()=>{
  const out=[];
  /* דף באנגלית: הכותרות שבתבנית מתורגמות, והנתונים שהרתמה הוסיפה נשארים בעברית */
  const EN=d.documentElement.getAttribute('lang')==='en', L=(he,en)=>EN?en:he;
  const fx=ev(FIXTURE);
  if(fx){ console.log('אין על מה לבדוק: '+fx); process.exit(1); }
  /* הנושא שעליו יוצרים חריג של קורא: השלישי, שאין לו וריאנט ב-SEG-REG */
  const RID=JSON.stringify(ev("rulesOf()[2].id"));
  w.go('segpolicy');
  const txt=()=>d.getElementById('wrap').textContent.replace(/\s+/g,' ');
  const has=(t,s)=>t.indexOf(s)>=0;
  /* השמות כפי שהם בדף: סגמנט שכבר היה בנתונים נשאר בשם שלו (למשל "מכרז ציבורי"), ולא בשם של הרתמה */
  const segLabel=id=>String(ev("(D.segments.find(s=>s.segment_id==='"+id+"')||{}).label||''"));
  out.push(['שני הסגמנטים מוצגים', ['SEG-REG','SEG-BID'].every(id=>{const l=segLabel(id); return !!l && has(txt(),l);})]);
  /* הסגמנט הכפוי */
  ev("S.segFull='SEG-BID'"); w.render();
  const t=txt();
  const NONEG=L('אין משא ומתן בסגמנט הזה','No negotiation in this segment');
  const IMP=L('משטר כפוי, לא עמדת החברה',"Imposed regime, not the company's position");
  out.push(['הכותרת אומרת שאין משא ומתן', has(t,NONEG)]);
  out.push(['שכבה 1: משטר כפוי', has(t,IMP)]);
  out.push(['שכבה 1 מראה מה נכפה', /אחריות בלי תקרה/.test(t) && /חשיפה בלתי מוגבלת/.test(t)]);
  out.push(['שכבה 2: בקשות לפני החתימה', has(t,L('מה מבקשים לפני החתימה','What we ask before signing'))]);
  out.push(['שכבה 2 מסמנת הצעת Areo', /הצעת Areo \(לא מבוסס על מסמכי הלקוח\)/.test(t)]);
  out.push(['שכבה 3: חותמים או לא', has(t,L('חותמים, חותמים בתנאי, או לא חותמים','Sign, sign with conditions, or do not sign'))]);
  out.push(['שכבה 3 נושאת המלצה', /ניגשים רק באישור הנהלה ועם ביטוח מתאים/.test(t)]);
  out.push(['בסגמנט כפוי אין רמזור ירוק צהוב אדום',
    !(EN?/Green.*Yellow.*Red/:/ירוק.*צהוב.*אדום/).test(t.slice(t.indexOf(IMP)))]);
  /* הסגמנט הרגיל כן מוצג כרמזור */
  ev("S.segFull='SEG-REG'"); w.render();
  const t2=txt();
  out.push(['סגמנט רגיל מוצג כרמזור', /תקרה בגובה התמורה השנתית/.test(t2)]);
  out.push(['בסגמנט רגיל אין תווית "אין משא ומתן"', !has(t2,NONEG)]);
  /* חריג שקורא יוצר הוא הצעה */
  ev("S.editMode=true"); ev("S.segFull=null"); w.render();
  w.addUserVariant(JSON.parse(RID),'SEG-REG');
  ev("S.segFull='SEG-REG'"); w.render();
  out.push(['חריג של קורא מסומן הצעה', has(txt(),L('הצעה, לא מדיניות','Proposal, not policy'))]);
  out.push(['הצעת חריג אינה נכתבת למדיניות',
    ev("JSON.stringify((byId("+RID+").variants||[]).map(v=>v.seg))").indexOf('SEG-REG')<0]);
  /* אין פעולת אישור בשום מסך */
  const bad=['decide','approveAll','approveSeg','confirmSeg'].filter(n=>typeof w[n]==='function');
  out.push(['אין פעולת אישור על סגמנט', bad.length===0, bad.join(', ')]);
  let n=0; out.forEach(([t,ok,note])=>{ if(!ok)n++;
    console.log((ok?'✓':'✗')+' '+t+(note?'  ['+note+']':'')); });
  console.log(n?('כשלים: '+n):'הסגמנט הכפוי וההצעות עוברים'); process.exit(n?1:0);
},600);
