/* רתמת בדיקות הקבלה של הדשבורד. לפני הרצה על פלייבוק חדש התאם את הליטרלים
   התלויים בקורפוס: מונחי החיפוש, מזהי הסעיפים לדוגמה (R-02, R-03, C24), מספר הסעיפים (14),
   ושמות קובצי ה-JSON הנגזרים מה-slug. הקובץ הנבדק: artifact.html בתיקיית העבודה. */
/* בדיקת איכות מקיפה לדשבורד */
const {JSDOM,VirtualConsole}=require(process.env.JSDOM_PATH||'/tmp/node_modules/jsdom');
const fs=require('fs');
const qa={blobs:[],downloads:[],copied:[],charts:[],printed:0,btnOK:0,btnFail:[],results:[]};
const R=(name,ok,note='')=>{qa.results.push({name,ok,note});};

const vc=new VirtualConsole();
vc.on('jsdomError',e=>{ if(!/scroll|print|navigation|resource|opaque/i.test(e.message)) qa.btnFail.push('JSDOM:'+e.message.slice(0,90)); });
vc.on('error',()=>{});

const html=fs.readFileSync(process.argv[2]||'artifact.html','utf8');
const dom=new JSDOM(html,{runScripts:'dangerously',pretendToBeVisual:true,virtualConsole:vc,
  url:'https://localhost/',
  beforeParse(window){
    /* ספריית הגרפים מוטמעת בתוצר. הבדיקה מחליפה אותה בבדל, כי jsdom אינו מספק קנבס.
       ההשמה של הספרייה נבלעת בלי לזרוק, והבדל נשאר פעיל. */
    const chartStub=function(el,cfg){qa.charts.push(cfg&&cfg.type);return{destroy(){}};};
    Object.defineProperty(window,'Chart',{configurable:true,get:()=>chartStub,set:()=>{}});
    window.confirm=()=>true;
    window.print=()=>{qa.printed++;};
    window.URL.createObjectURL=b=>{qa.blobs.push(b);return 'blob:'+qa.blobs.length;};
    window.URL.revokeObjectURL=()=>{};
  }});
const w=dom.window,d=w.document;
w.HTMLAnchorElement.prototype.click=function(){qa.downloads.push({name:this.download||'(link)',href:(this.href||'').slice(0,20)});};
Object.defineProperty(w.navigator,'clipboard',{value:{writeText:t=>{qa.copied.push(String(t).length);return Promise.resolve();}}});

const VIEWS=['overview','rules','compare','findings','additions','segpolicy','precedents','sources','decisions','export'];

setTimeout(async ()=>{
  // 1. רינדור כל הלשוניות
  for(const v of VIEWS){
    try{ w.go(v); const len=d.getElementById('wrap').innerHTML.length;
      R('לשונית '+v, len>300, len+' תווים'); }
    catch(e){ R('לשונית '+v,false,e.message); }
  }

  // 2. גרפים
  w.go('overview'); await sleep(120);
  R('גרף עוגה נוצר', qa.charts.includes('doughnut'));
  R('גרף עומק הראיות הוסר', !qa.charts.includes('bar') && !html.includes('עומק הראיות'));
  R('אין חיצים בכפתורים', !html.includes('⌄'));

  // 3. לחיצה על כל כפתור בכל לשונית
  for(const v of VIEWS){
    w.go(v); await sleep(30);
    const btns=[...d.getElementById('wrap').querySelectorAll('button')];
    for(const b of btns){ try{ b.click(); qa.btnOK++; }catch(e){ qa.btnFail.push(v+': '+(b.textContent||'').trim().slice(0,25)+' → '+e.message.slice(0,60)); } }
  }
  // כפתורי הסרגל העליון והניווט
  for(const b of [...d.querySelectorAll('.top button, nav .navi')]){
    try{ b.click(); qa.btnOK++; }catch(e){ qa.btnFail.push('topbar: '+(b.textContent||'').trim().slice(0,25)+' → '+e.message.slice(0,60)); }
  }
  R('לחיצה על כל הכפתורים', qa.btnFail.length===0, qa.btnOK+' כפתורים, '+qa.btnFail.length+' כשלים');

  // 4. הורדות: איפוס וריצה מסודרת
  qa.blobs=[]; qa.downloads=[];
  w.docExport(); w.xlsExport(); w.pptExport();
  w.go('export'); await sleep(30); w.dl('agent'); w.dl('dec');
  await sleep(30);
  const names=qa.downloads.map(x=>x.name);
  R('הורדת Word', names.includes('מדיניות_חוזית.doc'));
  R('הורדת Excel', names.includes('מדיניות_חוזית.xls'));
  R('הורדת PowerPoint', names.includes('מתאר_מצגת_מדיניות.doc'));
  R('הורדת חבילת סוכן JSON', names.includes('highlaw-nda-agent-pack.json'));
  R('הורדת יומן החלטות JSON', names.includes('highlaw-nda-decisions.json'));
  if(qa.blobs.length<5){
    console.log('\nעצירה: נוצרו '+qa.blobs.length+' קובצי ייצוא מתוך 5.');
    console.log('הרתמה מכוילת לפלייבוק אחד (slug highlaw-nda, סעיפים R-02/R-03/C24).');
    console.log('היא אינה מיושנת: כשמריצים אותה על פלייבוק אחר יש להתאים תחילה');
    console.log('את השמות ואת מזהי הסעיפים שבראש הקובץ. ראה ההערה בשורה 1.');
    process.exit(2);
  }
  const texts=await Promise.all(qa.blobs.map(b=>b.text()));
  const doc=texts[0]||'',xls=texts[1]||'',ppt=texts[2]||'',agent=texts[3]||'',dec=texts[4]||'';
  const bom=async b=>{const a=new Uint8Array(await b.arrayBuffer());return a[0]===0xEF&&a[1]===0xBB&&a[2]===0xBF;};
  R('Word+Excel: BOM לעברית', (await bom(qa.blobs[0]))&&(await bom(qa.blobs[1])));
  R('Word: תוכן מלא', doc.includes('המדיניות שלנו')||doc.includes('ירוק, מקובל'), Math.round(doc.length/1024)+'KB');
  R('Word: דיסקליימר', doc.includes('אינן חתומות'));
  R('Word: RTL', doc.includes('dir="rtl"'));
  R('Excel: טבלה מלאה', xls.includes('<table')&&xls.split('<tr').length>14, (xls.split('<tr').length-1)+' שורות');
  R('Excel: דיסקליימר', xls.includes('אינן חתומות'));
  R('PPT: מתאר שקופיות', (ppt.match(/<h1>/g)||[]).length>=15, (ppt.match(/<h1>/g)||[]).length+' שקופיות');
  try{ const a=JSON.parse(agent);
    R('חבילת סוכן: JSON תקין', a.rules.length===14 && a.fallback_ladder.status==='NotDefined', a.rules.length+' כללים'); }
  catch(e){ R('חבילת סוכן: JSON תקין',false,e.message); }
  try{ JSON.parse(dec); R('יומן החלטות: JSON תקין',true); }catch(e){ R('יומן החלטות: JSON תקין',false); }

  // 5. זרימת הכרעה
  w.go('rules'); w.renderList(); await sleep(20);
  w.decide('R-02','accept');
  R('אישור סעיף + מד התקדמות', d.getElementById('progChip').textContent.includes('מתוך 14'), d.getElementById('progChip').textContent);
  w.toggleRuleEdit('R-03'); await sleep(20);
  R('עריכה נפתחת רק בלחיצה', d.getElementById('rlist').innerHTML.includes('עריכה ידנית, נשמר מיד'));
  w.setRuleEdit('R-03','green','clause','נוסח בדיקת QA');
  w.renderList();
  R('עריכה מוחלת ומסומנת', d.getElementById('rlist').innerHTML.includes('נוסח בדיקת QA'));
  w.clearRuleEdit('R-03','green'); w.renderList();
  R('שחזור מקור', !d.getElementById('rlist').innerHTML.includes('נוסח בדיקת QA'));
  w.decide('R-02','accept'); // ביטול
  w.approveAll();
  R('אישור כל הפלייבוק', d.getElementById('progChip').textContent.includes('14 מתוך 14'));

  // 6. חיפוש בשלושה סקופים
  const setScope=v=>{const s=d.getElementById('gscope'); s.value=v; s.dispatchEvent(new w.Event('change'));};
  const gq=q=>{const e=d.getElementById('gq'); e.value=q; w.globalSearch(q);};
  setScope('topic'); gq('קניין רוחני');
  const n1=(d.getElementById('rlist').innerHTML.match(/class="card rulecard/g)||[]).length;
  R('חיפוש לפי נושא', n1>=1&&n1<=3, n1+' תוצאות');
  setScope('agreement'); gq('NGM');
  const n2=(d.getElementById('rlist').innerHTML.match(/class="card rulecard/g)||[]).length;
  R('חיפוש לפי הסכם או צד', n2>=3, n2+' סעיפים נתמכים ב-NGM');
  setScope('agreement'); gq('ממשלת בריטניה');
  const n2b=(d.getElementById('rlist').innerHTML.match(/class="card rulecard/g)||[]).length;
  R('חיפוש צד בעברית', n2b>=1, n2b+' תוצאות');
  setScope('all'); gq('');

  // 6א. מסננים משפטיים חדשים
  w.go('rules'); w.renderList(); await sleep(20);
  const nAll=(d.getElementById('rlist').innerHTML.match(/class="card rulecard/g)||[]).length;
  w.eval("S.pf='Required';renderList()");
  const nReq=(d.getElementById('rlist').innerHTML.match(/class="card rulecard/g)||[]).length;
  R('מסנן כלל נוכחות', nReq>0&&nReq<nAll, nAll+'→'+nReq+' חובה');
  w.eval("S.pf='all';S.df='accept';renderList()");
  const nAcc=(d.getElementById('rlist').innerHTML.match(/class="card rulecard/g)||[]).length;
  R('מסנן סטטוס הכרעה', nAcc===nAll, nAcc+' אושרו אחרי אישור הכל');
  w.eval("S.df='all';S.xf='weak';renderList()");
  const nWeak=(d.getElementById('rlist').innerHTML.match(/class="card rulecard/g)||[]).length;
  R('מסנן עוצמת ראיות', nWeak<nAll, nAll+'→'+nWeak+' עם ראיות מועטות');
  w.eval("S.xf='lowconf';renderList()");
  const nLow=(d.getElementById('rlist').innerHTML.match(/class="card rulecard/g)||[]).length;
  R('מסנן רמת ודאות', nLow>0&&nLow<=nAll, nLow+' בוודאות נמוכה');
  w.eval("S.xf='all';renderList()");
  R('צ׳יפ הציטוטים הוסר', !html.includes('ציטוטים מקושרים'));
  w.go('overview'); await sleep(20);
  R('KPI בשורה לרוחב', d.getElementById('kpirow')!==null && d.getElementById('kpirow').classList.contains('statrow'));

  // 6ב1. לשוניות חדשות מדף הבית
  w.go('redmap'); await sleep(20);
  R('מפת קווים אדומים: 14 נושאים', (d.getElementById('wrap').innerHTML.match(/class="rrow"/g)||[]).length===14);
  w.go('findings'); await sleep(20);
  R('ממצאים עיקריים: לשונית עצמאית', d.getElementById('wrap').innerHTML.includes('תובנות רוחביות'));
  w.go('overview'); await sleep(20);
  const ov=d.getElementById('wrap').innerHTML;
  R('דף הבית נקי מהמפה ומהממצאים', !ov.includes('מפת הקווים האדומים')||ov.indexOf('מפת הקווים האדומים')===ov.lastIndexOf('מפת הקווים האדומים'));
  R('דף הבית ללא כרטיס סגמנטים כפול', !ov.includes('<h3>הסגמנטים</h3>'));
  R('כפתור הכנה לשיחה הוסר מהפעולות', !ov.includes('הכנה לשיחה'));

  // 6ב. לשונית השוואה
  w.go('compare'); w.cmpSet('rule',''); w.cmpSet('seg',''); w.cmpSet('scope','all'); await sleep(20);
  R('השוואה: מסך בחירה', d.getElementById('wrap').innerHTML.includes('בחירה מהירה לפי נושא'));
  w.cmpFind('שיפוי'); await sleep(20);
  let ch=d.getElementById('wrap').innerHTML;
  R('השוואה: איתור לפי נושא', ch.includes('מה נקבע בפועל בהסכמים'));
  w.cmpFind('6'); await sleep(20);
  ch=d.getElementById('wrap').innerHTML;
  R('השוואה: איתור לפי מספר סעיף', ch.includes('סעיף 6'));
  const rowsAll=(ch.match(/<tr>/g)||[]).length;
  w.cmpSet('scope','internal'); await sleep(20);
  const rowsInt=((d.getElementById('wrap').innerHTML).match(/<tr>/g)||[]).length;
  R('השוואה: סינון מקור מצמצם', rowsInt<=rowsAll, rowsAll+'→'+rowsInt);
  w.cmpSet('scope','all');
  const segId0=(w.effSegs()[0]||{}).segment_id;
  w.cmpSet('seg',segId0); await sleep(20);
  R('השוואה: בלוק סגמנט מוצג', d.getElementById('wrap').innerHTML.includes('המדיניות בסגמנט'));
  w.cmpSet('seg',''); w.cmpSet('rule','');

  // 7. מגירת ציטוטים
  w.openCite('C24');
  R('מגירת ציטוט נפתחת', d.getElementById('drawer').classList.contains('on') && d.getElementById('drTitle').textContent.length>3, d.getElementById('drTitle').textContent);
  R('ציטוט ללא קודים', !/INT-\d\d/.test(d.getElementById('drTitle').textContent));
  w.closeDrawer();
  R('מגירה נסגרת', !d.getElementById('drawer').classList.contains('on'));

  // 8. סגמנטים ותקדימים
  w.go('segpolicy'); await sleep(20);
  if(!d.getElementById('wrap').innerHTML.includes('סגמנט חדש')){ w.toggleEdit(); w.go('segpolicy'); await sleep(20); }
  R('מצב עריכה מפעיל הוספת סגמנט', d.getElementById('wrap').innerHTML.includes('סגמנט חדש'));
  const segsBefore=(d.getElementById('wrap').innerHTML.match(/מחיקת הסגמנט/g)||[]).length;
  w.segAdd(); await sleep(20);
  const segsAfter=(d.getElementById('wrap').innerHTML.match(/מחיקת הסגמנט/g)||[]).length;
  R('הוספת סגמנט', segsAfter===segsBefore+1, segsBefore+'→'+segsAfter);
  const segId=(w.effSegs()[0]||{}).segment_id;
  w.addUserVariant('R-05',segId); await sleep(20);
  R('וריאנט ידני נוצר', d.getElementById('wrap').innerHTML.includes('וריאנט ידני'), 'בסגמנט '+segId);
  w.delUserVariant('R-05',segId);
  w.go('precedents'); await sleep(20);
  d.getElementById('pCp').value='בדיקת QA בע"מ'; d.getElementById('pDev').value='סטייה לבדיקה';
  w.addPrec(); await sleep(20);
  R('תיעוד תקדים', d.getElementById('wrap').innerHTML.includes('בדיקת QA'));
  w.delPrec(0);

  // 9. התמדה מקומית
  const saved=JSON.parse(w.localStorage.getItem('highlaw_nda_recipient_v1')||'{}');
  R('שמירה ב-localStorage', saved.decisions && Object.keys(saved.decisions).length>=14, Object.keys(saved.decisions||{}).length+' החלטות נשמרו');

  // 10. העתקות, הדפסה, RTL
  R('כפתורי העתקה', qa.copied.length>0, qa.copied.length+' העתקות בוצעו');
  w.toggleDl(); R('תפריט הורדה נפתח', d.getElementById('dlMenu').classList.contains('on'));
  w.hideDl(); R('תפריט הורדה נסגר', !d.getElementById('dlMenu').classList.contains('on'));
  R('RTL מלא', d.documentElement.getAttribute('dir')==='rtl');
  R('אפס מקפים ארוכים', !html.includes('—')&&!html.includes('–'));
  R('אפס קודי SEG/INT/R בטקסט גלוי', (()=>{ w.go('rules'); w.renderList();
    const vis=[...d.querySelectorAll('#wrap b,#wrap h3,#wrap h4,#wrap .mut,#wrap .tag,#wrap p,#wrap li')].map(e=>e.textContent).join(' ');
    return !/\b(R-\d\d|SEG-\d|INT-\d\d)\b/.test(vis); })());

  // סיכום
  const fail=qa.results.filter(r=>!r.ok);
  console.log('====== תוצאות QA ======');
  qa.results.forEach(r=>console.log((r.ok?'PASS':'FAIL')+'  '+r.name+(r.note?('  ['+r.note+']'):'')));
  console.log('======');
  console.log('סה"כ: '+qa.results.length+' בדיקות, '+fail.length+' כשלים');
  if(qa.btnFail.length) console.log('כשלי כפתורים:', qa.btnFail.slice(0,8));
  process.exit(fail.length?1:0);
},600);
function sleep(ms){return new Promise(r=>setTimeout(r,ms));}
