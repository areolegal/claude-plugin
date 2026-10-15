/* סגמנט שאין בו משא ומתן מוצג בשלוש השכבות שלו ולא כרמזור, וחריג שקורא
   יוצר מסומן "הצעה, לא מדיניות". אין בשום מסך פעולת אישור על סגמנט.
   הרצה: JSDOM_PATH=<path> node qa_imposed.js <dashboard.html> */
const {JSDOM,VirtualConsole}=require(process.env.JSDOM_PATH); const fs=require('fs');
const vc=new VirtualConsole(); vc.on('jsdomError',()=>{}); vc.on('error',()=>{});
const dom=new JSDOM(fs.readFileSync(process.argv[2],'utf8'),{runScripts:'dangerously',
  pretendToBeVisual:true,virtualConsole:vc,url:'https://x/',
  beforeParse(w){Object.defineProperty(w,'Chart',{configurable:true,get:()=>function(){return{destroy(){}}},set:()=>{}});}});
const w=dom.window,d=w.document,ev=x=>w.eval(x);
setTimeout(()=>{
  const out=[];
  w.go('segpolicy');
  const txt=()=>d.getElementById('wrap').textContent.replace(/\s+/g,' ');
  out.push(['שני הסגמנטים מוצגים', /גוף מפוקח/.test(txt()) && /מכרז ציבורי/.test(txt())]);
  /* הסגמנט הכפוי */
  ev("S.segFull='SEG-BID'"); w.render();
  const t=txt();
  out.push(['הכותרת אומרת שאין משא ומתן', /אין משא ומתן בסגמנט הזה/.test(t)]);
  out.push(['שכבה 1: משטר כפוי', /משטר כפוי, לא עמדת החברה/.test(t)]);
  out.push(['שכבה 1 מראה מה נכפה', /אחריות בלי תקרה/.test(t) && /חשיפה בלתי מוגבלת/.test(t)]);
  out.push(['שכבה 2: שאלות ההבהרה', /מה מבקשים בשאלות ההבהרה/.test(t)]);
  out.push(['שכבה 2 מסמנת הצעת Areo', /הצעת Areo \(לא מבוסס על מסמכי הלקוח\)/.test(t)]);
  out.push(['שכבה 3: ניגשים או לא', /ניגשים, ניגשים בתנאי, או לא ניגשים/.test(t)]);
  out.push(['שכבה 3 נושאת המלצה', /ניגשים רק באישור הנהלה ועם ביטוח מתאים/.test(t)]);
  out.push(['בסגמנט כפוי אין רמזור ירוק צהוב אדום',
    !/ירוק.*צהוב.*אדום/.test(t.slice(t.indexOf('משטר כפוי')))]);
  /* הסגמנט הרגיל כן מוצג כרמזור */
  ev("S.segFull='SEG-REG'"); w.render();
  const t2=txt();
  out.push(['סגמנט רגיל מוצג כרמזור', /תקרה בגובה התמורה השנתית/.test(t2)]);
  out.push(['בסגמנט רגיל אין תווית "אין משא ומתן"', !/אין משא ומתן בסגמנט הזה/.test(t2)]);
  /* חריג שקורא יוצר הוא הצעה */
  ev("S.editMode=true"); ev("S.segFull=null"); w.render();
  const rid=ev("D.rules[2].id");
  w.addUserVariant(rid,'SEG-REG');
  ev("S.segFull='SEG-REG'"); w.render();
  out.push(['חריג של קורא מסומן הצעה', /הצעה, לא מדיניות/.test(txt())]);
  out.push(['הצעת חריג אינה נכתבת למדיניות',
    ev("JSON.stringify((D.rules[2].variants||[]).map(v=>v.seg))").indexOf('SEG-REG')<0]);
  /* אין פעולת אישור בשום מסך */
  const bad=['decide','approveAll','approveSeg','confirmSeg'].filter(n=>typeof w[n]==='function');
  out.push(['אין פעולת אישור על סגמנט', bad.length===0, bad.join(', ')]);
  let n=0; out.forEach(([t,ok,note])=>{ if(!ok)n++;
    console.log((ok?'✓':'✗')+' '+t+(note?'  ['+note+']':'')); });
  console.log(n?('כשלים: '+n):'הסגמנט הכפוי וההצעות עוברים'); process.exit(n?1:0);
},600);
