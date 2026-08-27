/* בדיקת קבלה גנרית, אינה תלויה בקורפוס. בודקת את שני התוצרים:
   הצגת כל המסכים, הטמעת ספריית הגרפים, גישה למסמכי המקור, וניטרול ההורדות בעמוד משותף.
   הרצה: JSDOM_PATH=<path> node scripts/qa_artifact.js <local.html> <artifact.html> */
const fs=require('fs');
const {JSDOM,VirtualConsole}=require(process.env.JSDOM_PATH||'/tmp/node_modules/jsdom');
const VIEWS=['overview','rules','compare','findings','additions','segpolicy','precedents','sources','decisions','export'];
let fails=0;
const ok=(c,m)=>{ console.log(c?'PASS':'FAIL',m); if(!c) fails++; };

function boot(file){
  const errs=[], downloads=[], toasts=[], charts=[];
  const vc=new VirtualConsole();
  vc.on('jsdomError',e=>{ if(!/scroll|print|navigation|resource|opaque|canvas/i.test(e.message)) errs.push(e.message.slice(0,150)); });
  vc.on('error',()=>{});
  const dom=new JSDOM(fs.readFileSync(file,'utf8'),{runScripts:'dangerously',pretendToBeVisual:true,virtualConsole:vc,url:'https://localhost/',
    beforeParse(window){
      const stub=function(el,cfg){ charts.push(cfg&&cfg.type); return {destroy(){}}; };
      Object.defineProperty(window,'Chart',{configurable:true,get:()=>stub,set:()=>{}});
      window.print=()=>{}; window.confirm=()=>true;
      window.URL.createObjectURL=()=>'blob:x'; window.URL.revokeObjectURL=()=>{};
    }});
  const w=dom.window;
  w.HTMLAnchorElement.prototype.click=function(){ if(this.download) downloads.push(this.download); };
  w.Element.prototype.scrollIntoView=function(){};
  Object.defineProperty(w.navigator,'clipboard',{value:{writeText:()=>Promise.resolve()},configurable:true});
  return {w, d:w.document, errs, downloads, charts};
}

function run(file, label, published){
  console.log('\n== '+label);
  const {w,d,errs,downloads,charts}=boot(file);
  ok(errs.length===0,'  אפס שגיאות ריצה'+(errs[0]?': '+errs[0]:''));
  ok(typeof w.Chart!=='undefined','  ספריית הגרפים זמינה');
  ok(fs.readFileSync(file,'utf8').indexOf('cdn.jsdelivr.net')<0,'  אין טעינה מרשת חיצונית');
  VIEWS.forEach(v=>{
    let threw=null;
    try{ w.go(v); }catch(e){ threw=e.message.slice(0,80); }
    const html=d.getElementById('wrap').innerHTML;
    ok(!threw && html.length>50,'  מסך '+v+(threw?': '+threw:''));
  });
  w.go('sources');
  const links=[...d.querySelectorAll('#wrap a[href^="http"]')];
  ok(links.length>0,'  קישורים למקורות: '+links.length);
  w.go('export');
  const before=downloads.length;
  try{ w.dl('decisions'); }catch(e){}
  if(published){ ok(downloads.length===before,'  בעמוד משותף לא נפתחה הורדה'); }
  else { ok(downloads.length>before,'  בקובץ המקומי ההורדה פעלה'); }
  return fails;
}

run(process.argv[2]||'local.html','קובץ HTML מקומי',false);
run(process.argv[3]||'artifact.html','תוכן לעמוד משותף',true);
console.log(fails?('\nFAILURES: '+fails):'\nALL PASSED');
process.exit(fails?1:0);
