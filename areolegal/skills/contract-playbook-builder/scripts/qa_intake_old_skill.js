/* סקיל בגרסה ישנה שולח משפחות בלי מספר הסכמים. הטופס אינו מציג אפס,
   אינו חוסם, ושולח "לא צוין". */
const {JSDOM,VirtualConsole}=require(process.env.JSDOM_PATH); const fs=require('fs');
const FAMS=[{n:"הסכם שירותים", p:"הצד המספק / הנותן", s:"מקור: תיקיית ספקים"},
            {n:"הסכם סודיות", p:"הצד המזמין / הרוכש"}];
let html=fs.readFileSync(process.argv[2],'utf8')
  .replace('__FAMILIES__',JSON.stringify(FAMS)).replace('__FOLDERS__','[]')
  .replace('"__DRAFTS__"','"0"').replace('"__MODE__"','"scan"');
const vc=new VirtualConsole(); const errs=[]; vc.on('jsdomError',e=>errs.push(String(e.message||e)));
const dom=new JSDOM('<!doctype html><body>'+html+'</body>',{runScripts:'dangerously',virtualConsole:vc,url:'https://x/'});
const w=dom.window,d=w.document; w.sendPrompt=t=>{w.__sent=t;};
const out=[], vis=id=>{const e=d.getElementById(id);return !!e&&!e.hidden;};
out.push(['אפס שגיאות ריצה', errs.length===0, errs[0]||'']);
const chips=[...d.querySelectorAll('#type .chip')];
out.push(['הכפתור אינו מציג "0 הסכמים"', chips[0].textContent.indexOf('0 הסכמים')<0, chips[0].textContent]);
chips[0].onclick();
out.push(['אין רצועה כשהמספר אינו ידוע', !vis('band-mid')&&!vis('band-low')&&!vis('band-zero')]);
out.push(['אין הודעת מחקר קבוע', !vis('reg-fixed')]);
out.push(['שאלת התבנית כן מוצגת', vis('q-tpl')&&vis('q-all')]);
[...d.querySelectorAll('#pos .chip')][0].onclick();
[...d.querySelectorAll('#dep .chip')][0].onclick();
[...d.querySelectorAll('#cmp .chip')][1].onclick();
[...d.querySelectorAll('#tpl .chip')][2].onclick();
[...d.querySelectorAll('#all .chip')][0].onclick();
d.getElementById('go').onclick();
const sent=w.__sent||'';
out.push(['הטופס אינו חוסם', !!sent, d.getElementById('err').textContent]);
out.push(['המספר נשלח כ"לא צוין"', sent.indexOf('הסכמים: לא צוין')>0, sent.slice(0,130)]);
out.push(['המסלול נשלח כלא צוין', sent.indexOf('מסלול: לא צוין')>0]);
let bad=0; out.forEach(([n,ok,note])=>{ if(!ok)bad++;
  console.log((ok?'✓':'✗')+' '+n+(note?'  ['+String(note).slice(0,110)+']':'')); });
console.log(bad?('כשלים: '+bad):'הטופס סובל סקיל בגרסה ישנה'); process.exit(bad?1:0);
