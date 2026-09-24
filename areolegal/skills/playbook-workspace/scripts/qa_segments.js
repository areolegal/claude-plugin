const {JSDOM,VirtualConsole}=require(process.env.JSDOM_PATH); const fs=require('fs');
const vc=new VirtualConsole(); vc.on('jsdomError',()=>{}); vc.on('error',()=>{});
const dom=new JSDOM(fs.readFileSync('dash.html','utf8'),{runScripts:'dangerously',pretendToBeVisual:true,virtualConsole:vc,url:'https://x/',
 beforeParse(w){Object.defineProperty(w,'Chart',{configurable:true,get:()=>function(){return{destroy(){}}},set:()=>{}});}});
const w=dom.window,d=w.document,ev=x=>w.eval(x);
setTimeout(()=>{
  const out=[];
  w.go('segpolicy');
  const t=d.getElementById('wrap').textContent;
  out.push(['כותרת חריגים לפי סגמנט', t.indexOf('חריגים לפי סגמנט')>=0]);
  out.push(['שורת סגמנטים עם מונים', /בנקים \(\d\)/.test(t), (t.match(/בנקים \(\d\)/)||[''])[0]]);
  const rows=d.querySelectorAll('.tbl tbody tr');
  out.push(['טבלת חריגים', rows.length===ev('allExceptions().length') && rows.length>0, rows.length+' שורות']);
  out.push(['השורה מראה מה משתנה', /←/.test(rows[0].textContent)]);
  w.eval("S.segSel='SEG-GOV'"); w.render();
  const rows2=d.querySelectorAll('.tbl tbody tr');
  out.push(['סינון לפי סגמנט', rows2.length===ev("allExceptions().filter(x=>x.seg==='SEG-GOV').length"), rows2.length+' שורות']);
  w.eval("S.segSel=''"); w.render();
  /* בתוך הסעיף */
  const rid=ev("allExceptions()[0].r.id");
  w.openSegEx(rid);
  setTimeout(()=>{
    const card=d.getElementById('rc-'+rid);
    const h=card.innerHTML;
    out.push(['בלוק חריג בתוך הסעיף', h.indexOf('segex')>=0]);
    out.push(['מוצג הכלל הכללי מול הסגמנט', h.indexOf('בכלל הכללי')>=0 && h.indexOf('בסגמנט')>=0]);
    out.push(['אין שכפול של עמדה זהה', ev("varDiff(byId('"+rid+"'), allExceptions()[0].seg).length")<3]);
    const before=ev("Object.keys(S.varEdits||{}).length");
    w.setVarEdit(rid, ev("allExceptions()[0].seg"), 'green','pos','נוסח סגמנט חדש');
    out.push(['עריכת חריג נשמרת', ev("Object.keys(S.varEdits||{}).length")>before]);
    w.render();
    out.push(['עריכה מסומנת', d.getElementById('rc-'+rid).innerHTML.indexOf('נערך ידנית')>=0]);
    w.clearVarEdit(rid, ev("allExceptions()[0].seg"));
    out.push(['שחזור לנוסח הכללי', ev("Object.keys(S.varEdits||{}).length")===0]);
    /* הוספת חריג לסעיף אחר */
    const free=ev("rulesOf().find(r=>!(r.variants||[]).length).id");
    w.addUserVariant(free,'SEG-MALL');
    out.push(['הוספת חריג לסעיף', ev("!!S.userVariants['"+free+"|SEG-MALL']")]);
    let bad=0; out.forEach(([n,ok,note])=>{ if(!ok)bad++; console.log((ok?'✓':'✗')+' '+n+(note?'  ['+note+']':'')); });
    console.log(bad?('כשלים: '+bad):'כל בדיקות הסגמנטים עברו'); process.exit(bad?1:0);
  },150);
},400);
