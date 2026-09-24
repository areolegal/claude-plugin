/* רתמת בדיקה לשכבת המאגר המשותף שבסביבת העבודה.

   מריצה את התוצר בתוך jsdom מול מאגר מדומה, ובודקת שההכרעה נכתבת למאגר עם שם
   המכריע, שהכרעה של משתמש אחר מופיעה בדף חיה, ושביטול הכרעה מוחק אותה.
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
  const rid=ev('D.rules[1].id');
  w.decide(rid,'accept'); await wait(700);
  const doc=store.get(rid);
  out.push(['הכרעה נכתבה למאגר', !!doc && doc.status==='approved', JSON.stringify(doc&&doc.status)]);
  out.push(['שם המכריע נרשם', !!doc && doc.by==='ענבל', JSON.stringify(doc&&doc.by)]);
  const other=ev('D.rules[2].id');
  store.set(other,{rule_id:other,status:'approved_with_change',note:'מבנק',by:'ניל',
    at:new Date().toISOString(),wording:{yellow:{clause:'נוסח חדש'}},applied:false});
  cb(snap()); await wait(300);
  out.push(['הכרעה של משתמש אחר נקלטה בדף', ev('S.decisions')[other]==='edit', JSON.stringify(ev('S.decisions')[other])]);
  out.push(['הערה של משתמש אחר נקלטה', ev('S.notes')[other]==='מבנק', JSON.stringify(ev('S.notes')[other])]);
  out.push(['נוסח של משתמש אחר נקלט', (((ev('S.ruleEdits')[other]||{}).yellow||{}).clause)==='נוסח חדש', '']);
  out.push(['מי הכריע מוצג', w.decidedBy(other).indexOf('ניל')===0, w.decidedBy(other)]);
  w.decide(rid,'accept'); await wait(700);           /* לחיצה חוזרת מבטלת */
  out.push(['ביטול הכרעה מוחק מהמאגר', !store.has(rid), 'still='+store.has(rid)]);
  let bad=0;
  out.forEach(([n,ok,note])=>{ if(!ok) bad++; console.log((ok?'✓':'✗')+' '+n+(note?'  ['+note+']':'')); });
  console.log(bad?('כשלים: '+bad):'כל הבדיקות עברו');
  process.exit(bad?1:0);
})();
