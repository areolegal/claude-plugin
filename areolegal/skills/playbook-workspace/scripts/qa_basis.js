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
  /* התווית, המונה ותאריך המחקר. הדף מציג מה שהמודל כתב, ואינו גוזר תווית */
  w.eval("D.meta.build_path={n:22,path:'own'}; D.meta.status_label='פלייבוק מוצע, מבוסס הסכמים ומחקר שוק, טעון אישור';"
       + "D.meta.market_research_date='12.10.2026'; D.meta.approved_count=4; D.meta.positions_count=9; render();");
  const t5=(d.querySelector('#pbbar .basisbar')||{}).textContent||'';
  out.push(['התווית מוצגת מילה במילה', t5.indexOf('פלייבוק מוצע, מבוסס הסכמים ומחקר שוק, טעון אישור')>=0]);
  out.push(['המונה כשרק חלק מהעמדות מאושרות', t5.indexOf('4 מתוך 9 עמדות מאושרות')>=0]);
  out.push(['תאריך המחקר בפס', t5.indexOf('12.10.2026')>=0]);
  w.eval("D.meta.approved_count=9; render();");
  out.push(['כשכל העמדות מאושרות אין מונה',
    ((d.querySelector('#pbbar .basisbar')||{}).textContent||'').indexOf('מתוך')<0]);
  w.eval("delete D.meta.status_label; delete D.meta.label_now; render();");
  out.push(['בלי תווית במודל אין תווית בדף',
    ((d.querySelector('#pbbar .basisbar')||{}).textContent||'').indexOf('טעון אישור')<0]);

  /* כפתור "המקורות" ומסך המקורות */
  out.push(['בלי מקורות חיצוניים אין כפתור "המקורות"',
    ((d.querySelector('#pbbar .basisbar')||{}).textContent||'').indexOf('המקורות')<0]);
  w.eval("D.market=[{id:'W1',body:'מינהל הרכש הממשלתי',title:'טיוטת הסכם שירותים',"
       + "url:'https://mr.gov.il/doc1',date:'2025-02-03',retrieved_at:'12.10.2026',"
       + "drafter_role:'המזמין',drafted_by:'לטובתם',supports:['הגבלת אחריות']}];"
       + "D.external_sources=[{ref:'W1',body:'מינהל הרכש הממשלתי',title:'טיוטת הסכם שירותים',"
       + "url:'https://mr.gov.il/doc1',retrieved_at:'12.10.2026',taken:[{fact:'תקרת אחריות 12 חודשי תשלום',"
       + "verification:'verified',corroborated_by:[{ref:'W5',url:'https://sec.gov/a'},{ref:'W7',url:'https://sec.gov/b'}]},"
       + "{fact:'התיישנות מקוצרת',verification:'not_verified',sources_found:1,reason:'נמצא מקור אחד'}]}]; render();");
  const bar2=(d.querySelector('#pbbar .basisbar')||{}).textContent||'';
  out.push(['עם מקורות חיצוניים יש כפתור "המקורות"', bar2.indexOf('המקורות')>=0]);
  out.push(['המסך בתפריט', d.getElementById('nav').textContent.indexOf('המקורות')>=0]);
  w.go('sources');
  const sv=d.getElementById('wrap');
  out.push(['מקורות השוק במסך', sv.textContent.indexOf('מקורות השוק')>=0]);
  out.push(['מי ניסח ולטובת מי', sv.textContent.indexOf('המזמין')>=0]);
  out.push(['טבלת המקורות', sv.textContent.indexOf('מה נלקח ממנו')>=0]);
  out.push(['"מה לא אומת" מופרד', sv.textContent.indexOf('מה לא אומת')>=0
    && sv.textContent.indexOf('נמצא מקור אחד')>=0]);
  const links=[...sv.querySelectorAll('a[href^="https://"]')];
  out.push(['כל קישור נפתח בכרטיסייה חדשה',
    links.length>0 && links.every(a=>a.target==='_blank' && /noopener/.test(a.rel||'')),
    links.length+' קישורים']);
  w.eval("D.market[0].url='http://mr.gov.il/doc1'; D.external_sources[0].url='http://mr.gov.il/doc1'; render();");
  out.push(['כתובת שאינה https אינה הופכת לקישור',
    d.getElementById('wrap').querySelectorAll('a[href^="http://"]').length===0]);

  /* מה המסלול מטיל על החברה, לפי התפקידים שבפלייבוק */
  const rid=w.eval("(rulesOf()[0]||{}).id");
  w.eval("const r=byId("+JSON.stringify(rid)+"); r.tl.green.role_effects={buyer:'אנחנו נושאים בעלות',seller:'אנחנו מוגנים'};"
       + "D.meta.company_roles=[{role:'buyer',label:'הקונה'},{role:'seller',label:'המוכרת'}];"
       + "D.market=[]; D.external_sources=[]; S.view='rules'; render(); openRule("+JSON.stringify(rid)+");");
  const card=()=>(d.getElementById('rc-'+rid)||{textContent:''}).textContent;
  out.push(['שורה לכל תפקיד כשיש כמה', card().indexOf('כשהחברה הקונה')>=0 && card().indexOf('כשהחברה המוכרת')>=0]);
  w.eval("D.meta.company_roles=[{role:'buyer',label:'הקונה'}]; byId("+JSON.stringify(rid)+").tl.green.company_effect='אנחנו נושאים בעלות'; render(); openRule("+JSON.stringify(rid)+");");
  out.push(['תפקיד אחד: שורה אחת בלי שם תפקיד',
    card().indexOf('מה זה מטיל על החברה')>=0 && card().indexOf('כשהחברה הקונה')<0]);
  w.eval("delete D.meta.company_roles; const r=byId("+JSON.stringify(rid)+"); delete r.tl.green.role_effects; delete r.tl.green.company_effect; render(); openRule("+JSON.stringify(rid)+");");
  out.push(['בלי נתון אין שורת השפעה', card().indexOf('מה זה מטיל על החברה')<0]);

  /* התגית "הצעת Areo", המסנן, ומקורות השוק בתוך הסעיף */
  w.eval("D.market=[{id:'W2',body:'גוף א',title:'נוסח א',url:'https://a.example/1'},"
       + "{id:'W5',body:'גוף ב',title:'נוסח ב',url:'https://b.example/2'},"
       + "{id:'W7',body:'גוף ג',title:'נוסח ג',url:'https://c.example/3'}];"
       + "const r=byId("+JSON.stringify(rid)+"); r.tl.yellow.label='הצעת Areo (לא מבוסס על מסמכי הלקוח)';"
       + "r.tl.yellow.market_source_ids=['W2','W5','W7'];"
       + "S.view='rules'; S.filter='all'; S.xf='all'; render();");
  /* המונה בתגית נגזר מהנתונים: בהדגמה הצהוב והאדום הם הצעות Areo */
  const nAreo=w.eval("areoTracks(byId("+JSON.stringify(rid)+")).length");
  out.push(['התגית בשורה המקופלת, עם מונה העמדות',
    (d.getElementById('rc-'+rid)||{textContent:''}).textContent.indexOf('הצעת Areo ('+nAreo+')')>=0,
    nAreo+' עמדות']);
  w.eval("S.xf='areo'; renderList();");
  const want=w.eval("rulesOf().filter(r=>areoTracks(r).length).map(r=>'rc-'+r.id)");
  const shown=[...d.querySelectorAll('#rlist .rulecard')].map(x=>x.id);
  out.push(['מסנן "רק הצעות Areo"', shown.join()===want.join(),
    shown.length+' מוצגים, '+want.length+' עם הצעה']);
  /* כלל שאין בו הצעת Areo יוצא מהמסנן */
  w.eval("const r=byId("+JSON.stringify(rid)+"); r._bk={y:r.tl.yellow.label,r:r.tl.red.label};"
       + "delete r.tl.yellow.label; delete r.tl.red.label; renderList();");
  out.push(['כלל בלי הצעה יוצא מהמסנן',
    [...d.querySelectorAll('#rlist .rulecard')].map(x=>x.id).indexOf('rc-'+rid)<0]);
  w.eval("const r=byId("+JSON.stringify(rid)+"); r.tl.yellow.label=r._bk.y; r.tl.red.label=r._bk.r;"
       + "delete r._bk; S.xf='all'; renderList();");
  w.eval("S.xf='all'; renderList(); openRule("+JSON.stringify(rid)+");");
  const cc=(d.getElementById('rc-'+rid)||{innerHTML:''}).innerHTML;
  out.push(['מקורות השוק בתוך הסעיף',
    cc.indexOf('מקורות השוק')>=0 && /W2[\s\S]*W5[\s\S]*W7/.test(cc)]);
  const mchips=[...(d.getElementById('rc-'+rid)||d.body).querySelectorAll('a.fn[href^="https://"]')];
  out.push(['כל מקור שוק הוא קישור בכרטיסייה חדשה',
    mchips.length===3 && mchips.every(a=>a.target==='_blank'), mchips.length+' קישורים']);
  w.eval("const r=byId("+JSON.stringify(rid)+"); delete r.tl.yellow.label; delete r.tl.yellow.market_source_ids; D.market=[];");

  w.go('overview');
  w.eval("delete D.meta.build_path; render();");
  out.push(['בלי השדה אין פס ואין המצאה', !d.querySelector('#pbbar .basisbar')]);
  let bad=0; out.forEach(([n,ok,note])=>{ if(!ok)bad++; console.log((ok?'✓':'✗')+' '+n+(note?'  ['+note+']':'')); });
  console.log(bad?('כשלים: '+bad):'פס הבסיס ופאנל הכיסוי עוברים'); process.exit(bad?1:0);
},600);
