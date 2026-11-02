/* פס הבסיס ופאנל הכיסוי: בכל מסך, חמשת הנוסחים, ובמסלול השוק בלי שני המסכים הפנימיים.
   הרצה: JSDOM_PATH=<path> node scripts/qa_basis.js <dashboard.html> */
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
function load(file){
  const vc=new VirtualConsole(); vc.on('jsdomError',()=>{}); vc.on('error',()=>{});
  return new JSDOM(fs.readFileSync(file,'utf8'),{runScripts:'dangerously',pretendToBeVisual:true,
    virtualConsole:vc,url:'https://x/',
    beforeParse(w){Object.defineProperty(w,'Chart',{configurable:true,get:()=>function(){return{destroy(){}}},set:()=>{}});}});
}
const dom=load(process.argv[2]); const w=dom.window, d=w.document;
setTimeout(()=>{
  const out=[];
  /* דף באנגלית (meta.lang = en): אותן בדיקות מול הנוסח האנגלי */
  const EN=d.documentElement.getAttribute('lang')==='en', L=(he,en)=>EN?en:he;
  const views=['overview','rules','compare','findings','decisions','export'];
  let all=true, miss='';
  views.forEach(v=>{ w.go(v); const b=d.querySelector('#pbbar .basisbar');
    if(!b||!b.textContent.trim()){ all=false; miss+=v+' '; } });
  out.push(['פס הבסיס בכל מסך', all, miss]);
  w.go('overview');
  const txt=(d.querySelector('#pbbar .basisbar')||{}).textContent||'';
  /* איך המסמכים נקראים תלוי במעמד המאגר (corpus_status): "הסכמים של החברה" רק כשהם חתומים */
  const docs=w.eval('T(BASIS_DOCS[corpusStatus()])'), pre=EN?'Built from ':'נבנה מ-';
  const nm=txt.slice(txt.indexOf(pre)+pre.length).match(/^\d+/);
  out.push(['הנוסח לפי מספר ההסכמים', !!nm && txt.indexOf(pre+nm[0]+' '+docs)>=0, txt.slice(0,60)]);
  const cov=d.getElementById('wrap').textContent;
  out.push(['פאנל הכיסוי מוצג', cov.indexOf(L('כיסוי הסעיפים','Clause coverage'))>=0]);
  out.push(['סעיף טכני מוצג עם נימוק',
    cov.indexOf(L('כותרות לנוחות','Headings for convenience'))>=0 || cov.indexOf(L('בלוק חתימה','Signature block'))>=0]);
  /* מסלול השוק: אפס הסכמים */
  w.eval("D.meta.build_path={n:0,path:'market_built'}; render();");
  const nav=d.getElementById('nav').textContent;
  out.push(['במסלול השוק אין השוואת סעיפים', nav.indexOf(L('השוואת סעיפים','Clause comparison'))<0]);
  out.push(['במסלול השוק אין תנאים מסחריים', nav.indexOf(L('תנאים מסחריים','Commercial terms'))<0]);
  const t2=(d.querySelector('#pbbar .basisbar')||{}).textContent||'';
  out.push(['נוסח מסלול השוק', t2.indexOf(L('נבנה לפי השוק','Built from the market'))===0, t2.slice(0,40)]);
  /* 1 עד 6, רק ההסכמים שלנו */
  w.eval("D.meta.build_path={n:4,path:'own'}; render();");
  const t3=(d.querySelector('#pbbar .basisbar')||{}).textContent||'';
  out.push(['נוסח 1 עד 6 בלי שוק', t3.indexOf(L('בלבד','only'))>0 && t3.indexOf(L('בחרה שלא לשלב','chose not to add'))>0, t3.slice(0,50)]);
  w.eval("D.meta.build_path={n:4,path:'own_plus_market'}; render();");
  const t4=(d.querySelector('#pbbar .basisbar')||{}).textContent||'';
  out.push(['נוסח 1 עד 6 בשילוב שוק', t4.indexOf(L('בשילוב מחקר שוק','combined with market research'))>0, t4.slice(0,50)]);
  /* התווית, המונה ותאריך המחקר. הדף מציג מה שהמודל כתב, ואינו גוזר תווית */
  w.eval("D.meta.build_path={n:22,path:'own'}; D.meta.status_label='פלייבוק מוצע, מבוסס הסכמים ומחקר שוק, טעון אישור';"
       + "D.meta.market_research_date='12.10.2026'; D.meta.approved_count=4; D.meta.positions_count=9; render();");
  const t5=(d.querySelector('#pbbar .basisbar')||{}).textContent||'';
  out.push(['התווית מוצגת מילה במילה', t5.indexOf('פלייבוק מוצע, מבוסס הסכמים ומחקר שוק, טעון אישור')>=0]);
  out.push(['המונה כשרק חלק מהעמדות מאושרות', t5.indexOf(L('4 מתוך 9 עמדות מאושרות','4 of 9 positions approved'))>=0]);
  out.push(['תאריך המחקר בפס', t5.indexOf('12.10.2026')>=0]);
  w.eval("D.meta.approved_count=9; render();");
  out.push(['כשכל העמדות מאושרות אין מונה',
    ((d.querySelector('#pbbar .basisbar')||{}).textContent||'').indexOf(L('מתוך',' of 9'))<0]);
  w.eval("delete D.meta.status_label; delete D.meta.label_now; render();");
  out.push(['בלי תווית במודל אין תווית בדף',
    ((d.querySelector('#pbbar .basisbar')||{}).textContent||'').indexOf('טעון אישור')<0]);

  /* כפתור "המקורות" ומסך המקורות */
  /* תוצר אמיתי כבר נושא מקורות שוק; הבדיקה מנקה אותם קודם, ולא מניחה שהנתונים ריקים */
  w.eval("D.market=[]; D.external_sources=[]; D.external_sources_table=''; render();");
  out.push(['בלי מקורות חיצוניים אין כפתור "המקורות"',
    ((d.querySelector('#pbbar .basisbar')||{}).textContent||'').indexOf(L('המקורות','Sources'))<0]);
  w.eval("D.market=[{id:'W1',body:'גוף ציבורי א',title:'טיוטת הסכם א',"
       + "url:'https://mr.gov.il/doc1',date:'2025-02-03',retrieved_at:'12.10.2026',"
       + "drafter_role:'המזמין',drafted_by:'לטובתם',supports:['הגבלת אחריות']}];"
       + "D.external_sources=[{ref:'W1',body:'גוף ציבורי א',title:'טיוטת הסכם א',"
       + "url:'https://mr.gov.il/doc1',retrieved_at:'12.10.2026',taken:[{fact:'תקרת אחריות 12 חודשי תשלום',"
       + "verification:'verified',corroborated_by:[{ref:'W5',url:'https://sec.gov/a'},{ref:'W7',url:'https://sec.gov/b'}]},"
       + "{fact:'התיישנות מקוצרת',verification:'not_verified',sources_found:1,reason:'נמצא מקור אחד'}]}]; render();");
  const bar2=(d.querySelector('#pbbar .basisbar')||{}).textContent||'';
  out.push(['עם מקורות חיצוניים יש כפתור "המקורות"', bar2.indexOf(L('המקורות','Sources'))>=0]);
  out.push(['המסך בתפריט', d.getElementById('nav').textContent.indexOf(L('המקורות','Sources'))>=0]);
  w.go('sources');
  const sv=d.getElementById('wrap');
  out.push(['מקורות השוק במסך', sv.textContent.indexOf(L('מקורות השוק','Market sources'))>=0]);
  out.push(['מי ניסח ולטובת מי', sv.textContent.indexOf('המזמין')>=0]);
  out.push(['טבלת המקורות', sv.textContent.indexOf(L('מה נלקח ממנו','What was taken from it'))>=0]);
  out.push(['"מה לא אומת" מופרד', sv.textContent.indexOf(L('מה לא אומת','What was not verified'))>=0
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
  out.push(['שורה לכל תפקיד כשיש כמה', card().indexOf(L('כשהחברה הקונה','When the company acts as הקונה'))>=0 && card().indexOf(L('כשהחברה המוכרת','When the company acts as המוכרת'))>=0]);
  w.eval("D.meta.company_roles=[{role:'buyer',label:'הקונה'}]; byId("+JSON.stringify(rid)+").tl.green.company_effect='אנחנו נושאים בעלות'; render(); openRule("+JSON.stringify(rid)+");");
  out.push(['תפקיד אחד: שורה אחת בלי שם תפקיד',
    card().indexOf(L('מה זה מטיל על החברה','What this imposes on the company'))>=0 && card().indexOf(L('כשהחברה הקונה','When the company acts as הקונה'))<0]);
  /* בלי נתון בשום מסלול: המודל כותב company_effect גם בצהוב ובאדום, ולכן מוחקים בשלושתם */
  w.eval("delete D.meta.company_roles; const r=byId("+JSON.stringify(rid)+"); ['green','yellow','red'].forEach(k=>{ const t=r.tl[k]||{}; delete t.role_effects; delete t.company_effect; Object.keys(t).filter(x=>/^as_.*_effect$/.test(x)).forEach(x=>delete t[x]); }); render(); openRule("+JSON.stringify(rid)+");");
  out.push(['בלי נתון אין שורת השפעה', card().indexOf(L('מה זה מטיל על החברה','What this imposes on the company'))<0]);

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
    (d.getElementById('rc-'+rid)||{textContent:''}).textContent.indexOf(L('הצעת Areo (','Areo proposal (')+nAreo+')')>=0,
    nAreo+' עמדות']);
  w.eval("S.xf='areo'; renderList();");
  const want=w.eval("rulesOf().filter(r=>areoTracks(r).length).map(r=>'rc-'+r.id)");
  const shown=[...d.querySelectorAll('#rlist .rulecard')].map(x=>x.id);
  out.push(['מסנן "רק הצעות Areo"', shown.join()===want.join(),
    shown.length+' מוצגים, '+want.length+' עם הצעה']);
  /* כלל שאין בו הצעת Areo יוצא מהמסנן */
  /* בכל שלושת המסלולים: בתוצר אמיתי גם הירוק יכול להיות הצעת Areo */
  w.eval("const r=byId("+JSON.stringify(rid)+"); r._bk={}; ['green','yellow','red'].forEach(k=>{ if(r.tl[k]){"
       + "r._bk[k]=r.tl[k].label; delete r.tl[k].label; } }); renderList();");
  out.push(['כלל בלי הצעה יוצא מהמסנן',
    [...d.querySelectorAll('#rlist .rulecard')].map(x=>x.id).indexOf('rc-'+rid)<0]);
  w.eval("const r=byId("+JSON.stringify(rid)+"); Object.keys(r._bk).forEach(k=>{ if(r._bk[k]!==undefined) r.tl[k].label=r._bk[k]; });"
       + "delete r._bk; S.xf='all'; renderList();");
  w.eval("S.xf='all'; renderList(); openRule("+JSON.stringify(rid)+");");
  const cc=(d.getElementById('rc-'+rid)||{innerHTML:''}).innerHTML;
  out.push(['מקורות השוק בתוך הסעיף',
    cc.indexOf(L('מקורות השוק','Market sources'))>=0 && /W2[\s\S]*W5[\s\S]*W7/.test(cc)]);
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
