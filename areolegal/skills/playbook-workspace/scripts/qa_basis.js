/* פס הבסיס ופאנל הכיסוי: בכל מסך, חמשת הנוסחים, ובמסלול השוק בלי שני המסכים הפנימיים.
   הרצה: JSDOM_PATH=<path> node scripts/qa_basis.js <dashboard.html> */
const {JSDOM,VirtualConsole}=require(process.env.JSDOM_PATH); const fs=require('fs');
function load(file){
  const vc=new VirtualConsole(); vc.on('jsdomError',()=>{}); vc.on('error',()=>{});
  return new JSDOM(fs.readFileSync(file,'utf8'),{runScripts:'dangerously',pretendToBeVisual:true,
    virtualConsole:vc,url:'https://x/',
    beforeParse(w){Object.defineProperty(w,'Chart',{configurable:true,get:()=>function(){return{destroy(){}}},set:()=>{}});}});
}
const dom=load(process.argv[2]); const w=dom.window, d=w.document;
setTimeout(()=>{
  const out=[];
  const views=['overview','rules','compare','findings','decisions','export'];
  let all=true, miss='';
  views.forEach(v=>{ w.go(v); const b=d.querySelector('#pbbar .basisbar');
    if(!b||!b.textContent.trim()){ all=false; miss+=v+' '; } });
  out.push(['פס הבסיס בכל מסך', all, miss]);
  w.go('overview');
  const txt=(d.querySelector('#pbbar .basisbar')||{}).textContent||'';
  out.push(['הנוסח לפי מספר ההסכמים', /נבנה מ-\d+ הסכמים של החברה/.test(txt), txt.slice(0,60)]);
  const cov=d.getElementById('wrap').textContent;
  out.push(['פאנל הכיסוי מוצג', cov.indexOf('כיסוי הסעיפים')>=0]);
  out.push(['סעיף טכני מוצג עם נימוק',
    cov.indexOf('כותרות לנוחות')>=0 || cov.indexOf('בלוק חתימה')>=0]);
  /* מסלול השוק: אפס הסכמים */
  w.eval("D.meta.build_path={n:0,path:'market_built'}; render();");
  const nav=d.getElementById('nav').textContent;
  out.push(['במסלול השוק אין השוואת סעיפים', nav.indexOf('השוואת סעיפים')<0]);
  out.push(['במסלול השוק אין תנאים מסחריים', nav.indexOf('תנאים מסחריים')<0]);
  const t2=(d.querySelector('#pbbar .basisbar')||{}).textContent||'';
  out.push(['נוסח מסלול השוק', t2.indexOf('נבנה לפי השוק')===0, t2.slice(0,40)]);
  /* 1 עד 6, רק ההסכמים שלנו */
  w.eval("D.meta.build_path={n:4,path:'own'}; render();");
  const t3=(d.querySelector('#pbbar .basisbar')||{}).textContent||'';
  out.push(['נוסח 1 עד 6 בלי שוק', t3.indexOf('בלבד')>0 && t3.indexOf('בחרה שלא לשלב')>0, t3.slice(0,50)]);
  w.eval("D.meta.build_path={n:4,path:'own_plus_market'}; render();");
  const t4=(d.querySelector('#pbbar .basisbar')||{}).textContent||'';
  out.push(['נוסח 1 עד 6 בשילוב שוק', t4.indexOf('בשילוב מחקר שוק')>0, t4.slice(0,50)]);
  w.eval("delete D.meta.build_path; render();");
  out.push(['בלי השדה אין פס ואין המצאה', !d.querySelector('#pbbar .basisbar')]);
  let bad=0; out.forEach(([n,ok,note])=>{ if(!ok)bad++; console.log((ok?'✓':'✗')+' '+n+(note?'  ['+note+']':'')); });
  console.log(bad?('כשלים: '+bad):'פס הבסיס ופאנל הכיסוי עוברים'); process.exit(bad?1:0);
},600);
