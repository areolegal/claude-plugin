/* הבחירה חלה על כל המסכים, לא רק על הסעיפים */
const {JSDOM,VirtualConsole}=require(process.env.JSDOM_PATH); const fs=require('fs');
const vc=new VirtualConsole(); vc.on('jsdomError',()=>{}); vc.on('error',()=>{});
const dom=new JSDOM(fs.readFileSync('dash.html','utf8'),{runScripts:'dangerously',pretendToBeVisual:true,virtualConsole:vc,url:'https://x/',
 beforeParse(w){Object.defineProperty(w,'Chart',{configurable:true,get:()=>function(){return{destroy(){}}},set:()=>{}});}});
const w=dom.window,d=w.document,ev=x=>w.eval(x);
setTimeout(()=>{
  const out=[];
  const views=['rules','compare','segpolicy','findings','decisions','export'];
  let everywhere=true, missing='';
  views.forEach(v=>{ w.go(v); if(!d.querySelector('#pbbar .pbbar')){ everywhere=false; missing+=v+' '; } });
  out.push(['פס הבחירה בכל המסכים הפנימיים', everywhere, missing]);
  w.go('overview');
  out.push(['אין פס בתמונת מצב', !d.querySelector('#pbbar .pbbar')]);
  out.push(['החלפת סוג הסכם קיימת בכרטיס שבתמונת מצב',
    d.getElementById('wrap').textContent.indexOf('מעבר לסוג הסכם אחר')>=0]);
  w.go('segpolicy');
  const a=ev('allExceptions().length');
  w.setPb(ev("D.playbooks[2].id"));
  const b=ev('allExceptions().length');
  out.push(['מסך החריגים מסונן לפי הבחירה', a!==b, a+' ← '+b]);
  w.go('overview');
  const kpi=d.querySelectorAll('#kpirow .statn')[1].textContent.trim();
  out.push(['מספרי תמונת מצב לפי הבחירה', kpi===String(ev('rulesOf().length')), kpi]);
  w.setPb(ev("(D.playbooks.find(p=>p.current)||{}).id"));
  let bad=0; out.forEach(([n,ok,note])=>{ if(!ok)bad++; console.log((ok?'✓':'✗')+' '+n+(note?'  ['+note+']':'')); });
  console.log(bad?('כשלים: '+bad):'הבחירה חלה בכל המסכים'); process.exit(bad?1:0);
},500);
