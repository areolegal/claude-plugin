/* רתמת בדיקה לשכבת המאגר המשותף שבסביבת העבודה.

   בדף אין הכרעות: יש הערות והצעות נוסח (`dashboard_spec.md`, "הערות והצעות:
   איפה הן חיות"). הרתמה מריצה את התוצר בתוך jsdom מול מאגר מדומה, ובודקת
   שהערה נכתבת למאגר עם שם הכותב, שהערה של משתמש אחר מופיעה בדף חיה,
   שמחיקת ההערה מוחקת אותה מהמאגר, ושאין בדף פעולת אישור.
   זו הבדיקה היחידה שמוכיחה שהעמוד המשותף באמת משותף.

   הרצה:  JSDOM_PATH=<נתיב ל-jsdom> node qa_shared_decisions.js [dashboard.html]
*/

const {JSDOM,VirtualConsole}=require(process.env.JSDOM_PATH);
const fs=require('fs');
const store=new Map(); let cb=null, subs=0;
const snap=()=>({docs:[...store.entries()].map(([id,v])=>({id,data:()=>v})),size:store.size,
  metadata:{fromCache:false,hasPendingWrites:false},docChanges:()=>[]});
const db={
  collection:(p)=>({onSnapshot:(n)=>{subs++;cb=n;setTimeout(()=>n(snap()),0);return()=>{};}}),
  doc:(p)=>{const id=p.split('/')[1];return{
    set:async v=>{store.set(id,v);cb&&cb(snap());},
    delete:async ()=>{store.delete(id);cb&&cb(snap());}};}
};
const vc=new VirtualConsole(); vc.on('jsdomError',()=>{}); vc.on('error',()=>{});
const dom=new JSDOM(fs.readFileSync(process.argv[2]||'dash.html','utf8'),{runScripts:'dangerously',pretendToBeVisual:true,
  virtualConsole:vc,url:'https://claude.ai/artifact/test',
  beforeParse(w){
    Object.defineProperty(w,'Chart',{configurable:true,get:()=>function(){return{destroy(){}}},set:()=>{}});
    w.claude={use:async n=>n==='db'?db:(n==='user'?{me:async()=>({name:'ענבל'})}:null)};
  }});
const w=dom.window;
const wait=ms=>new Promise(r=>setTimeout(r,ms));
(async()=>{
  await wait(400);
  const out=[];
  out.push(['מנוי אחד למאגר', subs===1, 'subs='+subs]);
  const ev=x=>w.eval(x);
  out.push(['אין בדף פעולת אישור',
    ['decide','approveAll','dl','agentPack'].every(n=>typeof w[n]!=='function')]);
  const rid=ev('D.rules[1].id');
  /* בדף של כמה פלייבוקים המזהה במאגר הוא <פלייבוק>__<סעיף>, כי R-01 של
     סוג אחד אינו R-01 של סוג אחר. הדף עצמו אומר מה המזהה (dbKey) */
  const key=r=>ev('typeof dbKey==="function"')?ev('dbKey('+JSON.stringify(r)+')'):r;
  w.setNote(rid,'לבדוק מול הביטוח'); await wait(700);
  const doc=store.get(key(rid));
  out.push(['הערה נכתבה למאגר', !!doc && doc.note==='לבדוק מול הביטוח', JSON.stringify(doc&&doc.note)]);
  out.push(['המאגר אינו נושא מצב אישור', !!doc && doc.status===undefined && doc.kind==='proposal',
    JSON.stringify(doc&&(doc.status||doc.kind))]);
  out.push(['שם הכותב נרשם', !!doc && doc.by==='ענבל', JSON.stringify(doc&&doc.by)]);
  w.setProp(rid,'yellow','נוסח שאני מציע'); await wait(700);
  out.push(['הצעת נוסח נכתבה למאגר',
    ((store.get(key(rid))||{}).wording||{}).yellow==='נוסח שאני מציע', '']);
  const other=ev('D.rules[2].id');
  store.set(key(other),{rule_id:other,kind:'proposal',note:'מבנק',by:'ניל',
    at:new Date().toISOString(),wording:{yellow:'נוסח חדש'}});
  cb(snap()); await wait(300);
  out.push(['הערה של משתמש אחר נקלטה', ev('S.notes')[other]==='מבנק', JSON.stringify(ev('S.notes')[other])]);
  out.push(['הצעה של משתמש אחר נקלטה', (ev('S.props')[other]||{}).yellow==='נוסח חדש', '']);
  out.push(['מי כתב מוצג', w.commentBy(other).indexOf('ניל')===0, w.commentBy(other)]);
  out.push(['ההצעה מוצגת כהצעה ולא כמדיניות',
    w.propBox(other,'yellow').indexOf('הצעה, לא מדיניות')>=0 &&
    w.effLight(ev('D.rules[2]'),'yellow').clause!=='נוסח חדש']);
  w.setNote(rid,''); w.setProp(rid,'yellow',''); await wait(700);
  out.push(['מחיקת ההערה מוחקת מהמאגר', !store.has(key(rid)), 'still='+store.has(key(rid))]);
  /* בדף של כמה פלייבוקים: הערה של סוג אחד אינה מופיעה בסוג אחר */
  if(ev('typeof BOOKS!=="undefined" && !!BOOKS')){
    const ids=ev('Object.keys(BOOKS)'), here=ev('S.pb'), there=ids.find(x=>x!==here);
    w.setNote(other,'הערה של הסוג הזה בלבד'); await wait(700);
    w.setPb(there); await wait(100);
    const leaked=(ev('S.notes')||{})[other]==='הערה של הסוג הזה בלבד';
    w.setPb(here); await wait(100);
    const back=(ev('S.notes')||{})[other]==='הערה של הסוג הזה בלבד';
    out.push(['הערה אינה עוברת לסוג הסכם אחר', !leaked && back, 'leaked='+leaked+' back='+back]);
  }
  let bad=0;
  out.forEach(([n,ok,note])=>{ if(!ok) bad++; console.log((ok?'✓':'✗')+' '+n+(note?'  ['+note+']':'')); });
  console.log(bad?('כשלים: '+bad):'כל הבדיקות עברו');
  process.exit(bad?1:0);
})();
