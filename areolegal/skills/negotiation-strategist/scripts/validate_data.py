# -*- coding: utf-8 -*-
# Copyright (c) Areo. All rights reserved. Licensed under the terms at https://areo.co.il/legal/terms
import argparse,io,json,re,sys
for _s in(sys.stdout,sys.stderr):
	try:_s.reconfigure(encoding='utf-8',errors='replace')
	except(AttributeError,ValueError):pass
ISO=re.compile('^\\d{4}-\\d{2}-\\d{2}$')
ENUMS={'risk.severity':{'critical','high','medium','low'},'node.side':{'us','them'},'node.level':{'green','yellow','red'},'bridge.source':{'their_wording','playbook','system_proposal'},'dialogue.who':{'us','them'},'docAccess.mode':{'local','connector','base','none'},'meta.deliverable_language':{'he','en','both'},'meta.display_language':{'he','en'},'meta.agreement_language':{'he','en'},'meta.paper_type':{'negotiable','tender_pre_bid','tender_awarded','standard_form_online'}}
TOP_LEVEL=['meta','counters','clauses','risks','plan','companion','footnotes']
LINES='red','yellow','bridge'
FIELDS={'':{'meta':'o','counters':'o','changed':'l','timeline':'l','plan':'o','clauses':'l','risks':'l','companion':'o','footnotes':'l','outbound':'o','proposal':'o','practice':'o'},'meta':{'company':'s','counterparty':'s','agreement':'s','transaction_id':'s','generated_at':'s','last_updated':'s','round_number':'i','sharing':'s','publishTarget':'s','deliverable_language':'s','display_language':'s','agreement_language':'s','lang':'s','docAccess':'o','status':'o','health':'o','power':'o','branding':'o','paper_type':'s'},'meta.docAccess':{'mode':'s','baseUrl':'s'},'meta.status':{'text':'s','source':'s','date':'s','ref':'s'},'meta.health':{'label':'s','note':'s'},'meta.power':{'label':'s','regime':'s','rationale':'s','leverage':'s','constraint':'s'},'meta.branding':{'logo':'s','theme':'o'},'meta.branding.theme':{'primary_light':'s','secondary_light':'s','soft_light':'s','on_light':'s','primary_dark':'s','secondary_dark':'s','soft_dark':'s','on_dark':'s'},'counters':{'aligned':'i','disputed':'i','redline':'i'},'changed[]':{'what':'s','note':'s'},'timeline[]':{'date':'s','event':'s','source':'s'},'plan':{'next_move':'o','order':'l','give':'l','ask':'l'},'plan.next_move':{'title':'s','why':'s'},'plan.order[]':{'step':'s','why':'s'},'plan.give[]':{'what':'s','why':'s'},'plan.ask[]':{'what':'s','why':'s'},'clauses[]':{'id':'s','title':'s','segment':'s','playbook':'o','lines':'o','bargain':'o','tree':'l','dialogue':'l','refs':'n'},'clauses[].playbook':{'position':'s','why':'s'},'clauses[].lines':{'red':'o','yellow':'o','bridge':'o'},'clauses[].lines.red':{'what':'s','why':'s'},'clauses[].lines.yellow':{'what':'s','conditions':'s'},'clauses[].lines.bridge':{'wording':'s','why':'s','source':'s'},'clauses[].bargain':{'their_open':'s','our_counter':'s','their_refusal':'s','midpoints':'l'},'clauses[].bargain.midpoints[]':{'point':'s','criterion':'s','in_return':'s'},'clauses[].tree[]':{'level':'s','side':'s','text':'s','emotion':'s','risk':'s','refs':'n'},'clauses[].dialogue[]':{'who':'s','text':'s','note':'s'},'risks[]':{'id':'s','title':'s','severity':'s','mitigation':'s','clause_id':'s','refs':'n'},'companion':{'pocket':'ls','redlines':'ls','donot':'ls','briefing':'ls','pause_line':'s','mail_subject':'s','mail_items':'l'},'companion.mail_items[]':{'text':'s','share_safe':'b','clause_id':'s'},'outbound':{'subject':'s','items':'l'},'outbound.items[]':{'text':'s','approved':'b','approved_by':'s','derived_from':'ls'},'proposal':{'base':'o','changes':'l','status':'s'},'proposal.base':{'round_number':'i','state_updated':'s','version':'s'},'proposal.changes[]':{'id':'s','clause_id':'s','issue':'s','what':'s','kind':'s','depends_on':'ls'},'practice':{'space':'s','writes_state':'b','base_round':'i','sessions':'l'},'practice.sessions[]':{'id':'s','clause_id':'s','base_round':'i','concessions':'l','note':'s'},'practice.sessions[].concessions[]':{'what':'s','simulated':'b'},'footnotes[]':{'n':'i','clause':'s','quote':'s','doc':'s','date':'s','page':'s','file':'s','webUrl':'s','urlSource':'s'}}
INTERNAL=re.compile('^[\\s\u200e\u200f\u202a-\u202e\u2066-\u2069]*\\[\\s*(פנימי|internal)\\s*\\]',re.I)
HEB=re.compile('[\u0590-\u05ff]')
LATIN=re.compile('[A-Za-z]')
def text_lang(s):
	s=s or''
	if HEB.search(s):return'he'
	return'en'if LATIN.search(s)else None
def type_ok(kind,v):
	A=kind
	if A=='s':return isinstance(v,(str,int,float))and not isinstance(v,bool)
	if A=='i':return isinstance(v,int)and not isinstance(v,bool)
	if A in('l','ls','n'):
		if not isinstance(v,list):return False
		if A=='ls':return all(isinstance(A,str)for A in v)
		if A=='n':return all(isinstance(A,int)and not isinstance(A,bool)for A in v)
		return True
	if A=='o':return isinstance(v,dict)
	if A=='b':return isinstance(v,bool)
	return True
KIND_NAME={'s':'טקסט','i':'מספר שלם','l':'מערך','ls':'מערך מחרוזות','n':'מערך מספרי הערות שוליים','o':'אובייקט','b':'true או false'}
def check_shape(r,data):
	def E(obj,key,where):
		G=where;F=key;H=FIELDS.get(F)
		if H is None or not isinstance(obj,dict):return
		for(A,B)in obj.items():
			C='%s.%s'%(G,A)if G else A
			if A not in H:r.warn(G or'שורש הקובץ','השדה %r אינו בסכמה, והתבנית אינה מציגה אותו. שם שדה ששונה? (strategist-main.md, סכמת strategy-data.json)'%A);continue
			if B is None:continue
			D=H[A]
			if not type_ok(D,B):r.err(C,'חייב להיות %s, ולא %s'%(KIND_NAME[D],type(B).__name__));continue
			I='%s.%s'%(F,A)if F else A
			if D=='o':E(B,I,C)
			elif D=='l'and I+'[]'in FIELDS:
				for(K,J)in enumerate(B):
					if not isinstance(J,dict):r.err('%s[%d]'%(C,K),'חייב להיות אובייקט, ולא %s'%type(J).__name__);continue
					E(J,I+'[]','%s[%d]'%(C,K))
	E(data,'','')
class Report:
	def __init__(A):A.errors,A.warns=[],[]
	def err(A,w,m):A.errors.append((w,m))
	def warn(A,w,m):A.warns.append((w,m))
def check_enum(r,where,field,value,key,required=True):
	C=field;B=where;A=value
	if A in(None,''):
		if required:r.err(B,'השדה %s ריק, והוא שדה חובה'%C)
		return
	if A not in ENUMS[key]:r.err(B,'הערך %r בשדה %s אינו מוכר לתבנית. הערכים המותרים: %s'%(A,C,', '.join(sorted(ENUMS[key]))))
def check_date(r,where,field,value,required=False):
	C=field;B=where;A=value
	if A in(None,''):
		if required:r.err(B,'השדה %s ריק, ונדרש תאריך'%C)
		return
	if not ISO.match(str(A)):r.err(B,'השדה %s בערך %r אינו בפורמט ISO של YYYY-MM-DD'%(C,A))
def validate(data):
	F=data;A=Report()
	for C in TOP_LEVEL:
		if C not in F:A.err('שורש הקובץ','המפתח %r חסר. התבנית קוראת אותו, והיעדרו מרוקן מסך'%C)
	D=F.get('meta')or{}
	for L in('company','counterparty','transaction_id'):
		if not D.get(L):A.err('meta','meta.%s חסר. הוא נדרש לכותרת ולשמירת הסימונים בדפדפן'%L)
	check_date(A,'meta','generated_at',D.get('generated_at'),required=True);check_date(A,'meta','last_updated',D.get('last_updated'))
	if not isinstance(D.get('round_number'),int):A.warn('meta','round_number אינו מספר שלם. מספר הסבב לא יוצג נכון')
	Y=D.get('status')or{}
	if not Y.get('text'):A.err('meta.status','text חסר. מסך תמונת המצב יציג שטרם נמסר סטטוס')
	if Y.get('text')and not Y.get('source'):A.err('meta.status','נמסר סטטוס בלי source. כל קביעה נושאת את מקורה, למשל דיווח משתמש או מייל')
	check_date(A,'meta.status','date',Y.get('date'));s=D.get('health')or{}
	if not s.get('label'):A.warn('meta.health','label ריק. מדד בריאות העסקה יוצג כלא נקבע')
	check_shape(A,F)
	for L in('deliverable_language','display_language','agreement_language','paper_type'):check_enum(A,'meta',L,D.get(L),'meta.'+L,required=False)
	if D.get('paper_type')in('tender_pre_bid','tender_awarded','standard_form_online'):
		if(F.get('plan')or{}).get('give'):A.warn('plan.give','סוג הנייר %s: אין ויתורים בנייר שאינו פתוח למשא ומתן. ההכנה היא לבירורים ולהחלטה לפני חתימה'%D.get('paper_type'))
		if any((A.get('bargain')or{}).get('midpoints')for A in F.get('clauses')or[]):A.warn('clauses','סוג הנייר %s: אין נקודות פשרה בנייר שאינו פתוח למשא ומתן'%D.get('paper_type'))
	M=D.get('deliverable_language');H=D.get('agreement_language')
	if M=='both':
		if not H:A.err('meta','deliverable_language הוא both בלי agreement_language. בלעדיו אין לדעת באיזו שפה נכתבים מייל הסיכום והמשפטים שנאמרים לצד השני')
		if not D.get('display_language'):A.warn('meta','deliverable_language הוא both בלי display_language. המרכז ייבנה בעברית')
	elif not H:A.warn('meta','agreement_language חסר. מייל הסיכום ייכתב בשפת המרכז, ולא בשפת ההסכם')
	Z=D.get('docAccess')or{}
	if Z:
		check_enum(A,'meta.docAccess','mode',Z.get('mode'),'docAccess.mode',required=False)
		if Z.get('mode')=='base'and not Z.get('baseUrl'):A.warn('meta.docAccess','mode הוא base בלי baseUrl. לא ייגזרו קישורים למסמכים')
	n=D.get('power')or{}
	if n and not n.get('label'):A.warn('meta.power','label ריק. כרטיס מאזן הכוחות אינו מוצג כלל')
	for(E,T)in enumerate(F.get('changed')or[]):
		if isinstance(T,dict)and not T.get('what'):A.err('changed[%d]'%E,'what חסר. השורה תוצג ריקה')
	i=set()
	for(E,L)in enumerate(F.get('footnotes')or[]):
		B='footnotes[%d]'%E;G=L.get('n')
		if not isinstance(G,int):A.err(B,'n חייב להיות מספר שלם, ולא %r'%G)
		if G in i:A.err(B,'מספר הערת שוליים %r חוזר'%G)
		i.add(G)
		if not L.get('quote'):A.err(B,'quote חסר. הערת השוליים תיפתח ריקה')
		check_date(A,B,'date',L.get('date'))
	def j(where,refs):
		for B in refs or[]:
			if B not in i:A.err(where,'הפניה להערת שוליים %r שאינה קיימת. הסימון בממשק יוביל לחלון ריק'%B)
	t=F.get('counters')or{}
	for C in('aligned','disputed','redline'):
		if not isinstance(t.get(C),int):A.err('counters','המונה %r חסר או אינו מספר שלם. הכרטיס יוצג ריק'%C)
	U=set()
	for(E,I)in enumerate(F.get('clauses')or[]):
		B='clauses[%d] (%s)'%(E,I.get('title','ללא כותרת'));J=I.get('id')
		if not J:A.err(B,'id חסר')
		if J in U:A.err(B,'מזהה הסעיף %r חוזר'%J)
		U.add(J)
		if not I.get('title'):A.err(B,'title חסר. כרטיס הסעיף יוצג בלי שם')
		u=I.get('playbook')or{}
		if not u.get('position'):A.err(B,'playbook.position חסר. לא יהיה ברור מה עמדת המדיניות')
		v=I.get('lines')or{}
		for N in LINES:
			Q=v.get(N)
			if not isinstance(Q,dict):A.err(B,'lines.%s חסר. שלושת הקווים חובה בכל סעיף במחלוקת'%N);continue
			a='wording'if N=='bridge'else'what'
			if not Q.get(a):A.err('%s.lines.%s'%(B,N),'%s ריק. תא הקו יוצג ריק'%a)
			if N=='bridge':
				if Q.get('source')in(None,''):A.warn('%s.lines.bridge'%B,'source חסר. לכל גשר נרשם מקור: their_wording, playbook או system_proposal')
				else:check_enum(A,'%s.lines.bridge'%B,'source',Q.get('source'),'bridge.source')
		j(B,I.get('refs'))
		for(O,G)in enumerate(I.get('tree')or[]):
			b='%s.tree[%d]'%(B,O);check_enum(A,b,'side',G.get('side'),'node.side');check_enum(A,b,'level',G.get('level'),'node.level',required=False)
			if not G.get('text'):A.err(b,'text חסר')
			j(b,G.get('refs'))
		c=I.get('dialogue')or[];d=[]
		for(O,e)in enumerate(c):
			o='%s.dialogue[%d]'%(B,O);check_enum(A,o,'who',e.get('who'),'dialogue.who')
			if not e.get('text'):A.err(o,'text חסר. הבועה תוצג ריקה')
			elif M=='both'and H and e.get('who')=='us'and text_lang(str(e.get('text')))not in(None,H):d.append(O)
		if d:A.warn('%s.dialogue'%B,'deliverable_language הוא both, ו-%d משפטים שלנו אינם בשפת ההסכם (%s): dialogue %s. משפט שנאמר לצד השני נכתב בשפת ההסכם'%(len(d),H,', '.join(str(A)for A in d)))
		if c and len(c)<8:A.warn(B,'התסריט מכיל %d חילופי דברים. המפרט דורש 8 עד 12, אחרת הוא קורא כתקציר ולא כאימון'%len(c))
		V=I.get('bargain')or{}
		if(V.get('our_counter')or V.get('their_refusal'))and not V.get('their_open')and not V.get('midpoints'):A.warn('%s.bargain'%B,'their_open חסר. בלעדיו ובלי midpoints, סימולציית המיקוח אינה מוצגת כלל')
		for(O,P)in enumerate(V.get('midpoints')or[]):
			if not P.get('point'):A.err('%s.bargain.midpoints[%d]'%(B,O),'point חסר')
			if not P.get('criterion'):A.err('%s.bargain.midpoints[%d]'%(B,O),'criterion חסר. נקודת אמצע בלי קריטריון אינה ניתנת להגנה בשיחה')
	for(E,C)in enumerate(F.get('risks')or[]):
		B='risks[%d] (%s)'%(E,C.get('title','ללא כותרת'));check_enum(A,B,'severity',C.get('severity'),'risk.severity')
		if not C.get('title'):A.err(B,'title חסר')
		if not C.get('mitigation'):A.err(B,'mitigation ריק. סיכון בלי המלצת צמצום אינו מוסר החלטה')
		J=C.get('clause_id')
		if J and J not in U:A.err(B,'clause_id %r אינו קיים ברשימת הסעיפים'%J)
		j(B,C.get('refs'))
	W=F.get('plan')or{};k=W.get('next_move')or{}
	if not k.get('title'):A.err('plan.next_move','title חסר. מסך ההכנה יציג שלא הוגדר מהלך הבא')
	if k.get('title')and not k.get('why'):A.err('plan.next_move','why חסר. מהלך בלי נימוק אינו ניתן להערכה')
	p=W.get('order')or[]
	if not p:A.err('plan.order','לא הוגדר סדר שיחה')
	for(E,q)in enumerate(p):
		if not q.get('step'):A.err('plan.order[%d]'%E,'step חסר')
		if not q.get('why'):A.err('plan.order[%d]'%E,'why חסר. כל שלב בסדר השיחה נושא נימוק של שורה')
	for l in('give','ask'):
		for(E,T)in enumerate(W.get(l)or[]):
			if not T.get('what'):A.err('plan.%s[%d]'%(l,E),'what חסר')
			if not T.get('why'):A.err('plan.%s[%d]'%(l,E),'why חסר')
	if W.get('give')and not W.get('ask'):A.err('plan','הוגדר מה נותנים בלי מה מבקשים בתמורה. ויתור בלי תמורה אינו חבילה אלא ויתור')
	K=F.get('companion')or{}
	if not(K.get('pocket')or[]):A.err('companion.pocket','כרטיס הכיס ריק. זהו התוצר שנלקח לשיחה עצמה')
	if not(K.get('donot')or[]):A.warn('companion.donot','רשימת מה לא אומרים ריקה')
	if not K.get('pause_line'):A.warn('companion','לא הוגדר משפט הפסקה')
	for C in('pocket','redlines','donot','briefing'):
		R=K.get(C)
		if R is not None and not isinstance(R,list):A.err('companion.%s'%C,'חייב להיות מערך מחרוזות, ולא %s'%type(R).__name__)
	if M=='both'and H and K.get('pause_line')and text_lang(K['pause_line'])not in(None,H)and not(H=='en'and LATIN.search(K['pause_line'])):A.warn('companion.pause_line','deliverable_language הוא both, ומשפט ההפסקה אינו בשפת ההסכם (%s)'%H)
	X=set()
	for C in('pocket','redlines','donot','briefing'):X.update(A.strip()for A in K.get(C)or[]if isinstance(A,str))
	if isinstance(K.get('pause_line'),str):X.add(K['pause_line'].strip())
	for I in F.get('clauses')or[]:
		N=I.get('lines')or{}
		for(Q,a)in(('red','what'),('red','why'),('yellow','what'),('yellow','conditions')):
			R=(N.get(Q)or{}).get(a)
			if isinstance(R,str):X.add(R.strip())
		for G in I.get('tree')or[]:
			if isinstance(G.get('text'),str):X.add(G['text'].strip())
	f=H or(D.get('display_language')if M=='both'else M)or'he';r=K.get('mail_items')or[]
	if not r:A.warn('companion.mail_items','אין פריטים לצד השני. בסיס מייל הסיכום יצא עם מקום להשלמה בלבד')
	for(E,P)in enumerate(r):
		S='companion.mail_items[%d]'%E
		if not isinstance(P,dict):continue
		g=str(P.get('text')or'').strip()
		if not g:A.err(S,'text חסר');continue
		if P.get('share_safe')is not True:A.err(S,'share_safe אינו true. פריט למייל הסיכום מסומן במפורש share_safe: true, ובלעדיו התבנית אינה מכניסה אותו למייל')
		if INTERNAL.match(g):A.err(S,'הפריט מסומן פנימי ([פנימי] או [internal]). שורה פנימית לעולם אינה נכנסת למייל לצד השני')
		if g in X:A.err(S,'הפריט זהה לשורה פנימית (כרטיס הכיס, קו אדום, מדרגת נסיגה, תדריך או עץ התגובות). מייל לצד השני נכתב מחדש, ואינו מעתיק שורה פנימית')
		if text_lang(g)not in(None,f):A.warn(S,'הפריט אינו בשפת ההסכם (%s). מייל הסיכום נכתב בשפת ההסכם'%f)
		J=P.get('clause_id')
		if J and J not in U:A.err(S,'clause_id %r אינו קיים ברשימת הסעיפים'%J)
	h=K.get('mail_subject')
	if isinstance(h,str)and h.strip():
		if INTERNAL.match(h):A.err('companion.mail_subject','הנושא מסומן פנימי, ולא ייכנס למייל')
		elif text_lang(h)not in(None,f):A.warn('companion.mail_subject','הנושא אינו בשפת ההסכם (%s)'%f)
	elif H and H!=(D.get('display_language')if M=='both'else M or'he'):A.warn('companion.mail_subject','mail_subject חסר, ושפת ההסכם שונה משפת המרכז. נושא המייל ייצא עם מקום להשלמה')
	for(E,m)in enumerate(F.get('timeline')or[]):
		B='timeline[%d]'%E;check_date(A,B,'date',m.get('date'),required=True)
		if not m.get('event'):A.err(B,'event חסר')
		if not m.get('source'):A.err(B,'source חסר. אירוע בציר הזמן נושא תמיד את מקורו')
	if not(F.get('clauses')or[]):A.warn('clauses','אין סעיפים במחלוקת. הלשונית תוצג עם הודעת ריק מכוונת')
	check_sections(A,F,U);return A
EXTERNAL_META='company','counterparty','agreement','agreement_language','generated_at'
MIN_MARKER=12
MIN_FRAGMENT=20
WORDLIST=re.compile('BATNA|walk[- ]?away|red[- ]?line|fallback|bottom line|קו אדום|מדרגת נסיגה|נקודת נסיגה|אלטרנטיבה הטובה|גבול פנימי|תקרה פנימית|\\[\\s*(?:פנימי|internal)\\s*\\]',re.I)
FORBIDDEN_PRACTICE_KEYS={'round_number','counters','status','negotiation_state','agreement','playbook','plan','clauses','state','round'}
def _norm(s):return' '.join(str(s).split())
def external_view(data):
	E=data;H=E.get('meta')or{};D=E.get('outbound');F,C=[],''
	if isinstance(D,dict):
		C=D.get('subject')if isinstance(D.get('subject'),str)else''
		for A in D.get('items')or[]:
			B=_norm(A.get('text'))if isinstance(A,dict)and isinstance(A.get('text'),str)else''
			if B and A.get('approved')is True and not INTERNAL.match(B):F.append({'text':B})
	else:
		G=E.get('companion')or{};C=G.get('mail_subject')if isinstance(G.get('mail_subject'),str)else''
		for A in G.get('mail_items')or[]:
			B=_norm(A.get('text'))if isinstance(A,dict)and isinstance(A.get('text'),str)else''
			if B and A.get('share_safe')is True and not INTERNAL.match(B):F.append({'text':B})
	if INTERNAL.match(C or''):C=''
	return{'meta':{A:H[A]for A in EXTERNAL_META if isinstance(H.get(A),str)},'outbound':{'subject':_norm(C),'items':F}}
def _leaves(obj,path=''):
	B=path;A=obj
	if isinstance(A,str):yield(B,A)
	elif isinstance(A,dict):
		for(E,C)in A.items():
			for D in _leaves(C,'%s.%s'%(B,E)if B else E):yield D
	elif isinstance(A,list):
		for(F,C)in enumerate(A):
			for D in _leaves(C,'%s[%d]'%(B,F)):yield D
def internal_markers(data):
	G=external_view(data);C=set(_norm(A)for(B,A)in _leaves(G));F={}
	for(A,B)in _leaves(data):
		H=A.split('[')[0].split('.')[0]
		if H=='outbound'and not A.endswith('.derived_from')and'.derived_from['not in A:
			if _norm(B)in C or A.endswith(('.approved_by','.subject')):continue
		if B.startswith('data:')and len(B)>500:continue
		D=_norm(B)
		if D in C:continue
		if len(D)>=MIN_MARKER:F.setdefault(D,A)
		if len(D)>=2*MIN_FRAGMENT:
			for I in re.split('[.!?;:\\n,]+',B):
				E=_norm(I)
				if len(E)>=MIN_FRAGMENT and E not in C and not any(E in A for A in C):F.setdefault(E,A)
	return F
def _variants(s):
	B=set()
	for A in(s,s.replace('—',', ').replace('–','-')):C=A.replace('&','&amp;').replace('<','&lt;').replace('>','&gt;');B.update((A,C,C.replace('"','&quot;'),json.dumps(A,ensure_ascii=False)[1:-1].replace('</','<\\/'),json.dumps(A,ensure_ascii=True)[1:-1].replace('</','<\\/')))
	return B
def leak_check(built,data):
	A=built;B=A.decode('utf-8','replace')if isinstance(A,(bytes,bytearray))else A;D=_norm(B);C=[]
	for(E,F)in internal_markers(data).items():
		if any(A in B or A in D for A in _variants(E)):C.append(F)
	return C
def check_sections(r,data,clause_ids):
	O=clause_ids;D=data;R=D.get('meta')or{};E=R.get('round_number')if isinstance(R.get('round_number'),int)else None;S=internal_markers(D);M=D.get('outbound');a=D.get('companion')or{};T=[A for A in a.get('mail_items')or[]if isinstance(A,dict)]
	if isinstance(M,dict):
		if T:r.warn('companion.mail_items','יש גם outbound וגם mail_items ישן. הצד השני נבנה מ-outbound בלבד, ו-mail_items אינו יוצא')
		for(H,I)in enumerate(M.get('items')or[]):
			A='outbound.items[%d]'%H
			if not isinstance(I,dict):continue
			F=_norm(I.get('text')or'')
			if not F:r.err(A,'text חסר');continue
			if not isinstance(I.get('approved'),bool):r.err(A,'approved חסר או אינו true/false. רק נוסח שאושר במפורש (true) לצד השני נכלל בעותק החיצוני')
			elif I.get('approved')is False:r.warn(A,'נוסח שטרם אושר (approved: false) אינו נכלל בעותק החיצוני')
			if INTERNAL.match(F):r.err(A,'הפריט מסומן פנימי. שורה פנימית לעולם אינה נכנסת לנוסח לצד השני')
			for(U,V)in S.items():
				if not V.startswith('outbound')and(U in F or F in U and len(F)>=MIN_MARKER):r.err(A,'הנוסח מעתיק תוכן פנימי מ-%s. נוסח לצד השני נכתב מחדש ממה שאושר, ולא מתוך נימוק פנימי'%V);break
			if WORDLIST.search(F):r.warn(A,'בנוסח מונח של משא ומתן פנימי (בדיקת רשימת מילים משלימה). בדוק שאינו חושף עמדה')
			for W in I.get('derived_from')or[]:
				if W not in O:r.err(A,'derived_from %r אינו קיים ברשימת הסעיפים'%W)
		N=M.get('subject')
		if isinstance(N,str)and N.strip():
			if INTERNAL.match(N):r.err('outbound.subject','הנושא מסומן פנימי')
			elif any(not B.startswith('outbound')and A in N for(A,B)in S.items()):r.err('outbound.subject','הנושא מעתיק תוכן פנימי')
		if not(M.get('items')or[]):r.warn('outbound.items','אין פריטים מאושרים לצד השני. העותק החיצוני יצא ריק')
	elif T:r.warn('companion.mail_items','קובץ במבנה ישן: הצד השני נבנה מפריטי share_safe: true בלבד, בסינון נתונים. מומלץ לעבור ל-outbound.items עם approved: true')
	G=D.get('proposal')
	if isinstance(G,dict):
		X=G.get('base')if isinstance(G.get('base'),dict)else{};J=X.get('round_number')
		if not isinstance(J,int)or isinstance(J,bool):r.err('proposal.base','round_number חסר. הצעת שינוי נקשרת לגרסת בסיס של קובץ המצב')
		if not X.get('state_updated'):r.err('proposal.base','state_updated חסר (last_updated של קובץ המצב בעת הקריאה). בלי גרסת בסיס אי אפשר לדעת אם ההצעה התיישנה')
		if E is not None and isinstance(J,int)and J!=E:r.err('proposal.base','ההצעה נשענת על סבב %s והמרכז על סבב %s. הסבב השתנה בזמן ההכנה: חובה לרענן (קריאה מחדש של קובץ המצב ובניית ההצעה מחדש)'%(J,E))
		b=set(A['id']for A in G.get('changes')or[]if isinstance(A,dict)and A.get('id'))
		for(H,B)in enumerate(G.get('changes')or[]):
			A='proposal.changes[%d]'%H
			if not isinstance(B,dict):continue
			for Y in('id','clause_id','what'):
				if not B.get(Y):r.err(A,'%s חסר. שינוי מוצע נושא מזהה, סעיף ותוכן'%Y)
			if B.get('clause_id')and B['clause_id']not in O:r.err(A,'clause_id %r אינו קיים ברשימת הסעיפים'%B['clause_id'])
			for P in B.get('depends_on')or[]:
				if P==B.get('id'):r.err(A,'שינוי תלוי בעצמו')
				elif P not in b:r.err(A,'depends_on %r אינו שינוי בהצעה'%P)
		if G.get('status')not in(None,'','proposed'):r.err('proposal.status','הצעה היא תמיד proposed. קבלתה נעשית בנושא ונותן ובאישור המשתמש, לא כאן')
	K=D.get('practice')
	if isinstance(K,dict):
		if K.get('writes_state')not in(None,False):r.err('practice.writes_state','סימולציה אינה כותבת מצב. חייב להיות false או חסר')
		if K.get('space')not in(None,'','simulation'):r.err('practice.space','מרחב התרגול הוא simulation בלבד')
		for L in K:
			if L in FORBIDDEN_PRACTICE_KEYS:r.err('practice.%s'%L,'שדה של מצב אמיתי בתוך מרחב התרגול. תרגול אינו נושא סבב, מוני התאמה, סטטוס, פלייבוק או נוסח הסכם')
		for(H,C)in enumerate(K.get('sessions')or[]):
			if not isinstance(C,dict):continue
			A='practice.sessions[%d]'%H
			for L in C:
				if L in FORBIDDEN_PRACTICE_KEYS:r.err(A,'שדה %r אסור בתרגול (מצב אמיתי)'%L)
			if C.get('clause_id')and C['clause_id']not in O:r.err(A,'clause_id %r אינו קיים ברשימת הסעיפים'%C['clause_id'])
			for(c,Z)in enumerate(C.get('concessions')or[]):
				if isinstance(Z,dict)and Z.get('simulated')is not True:r.err('%s.concessions[%d]'%(A,c),'ויתור בסימולציה חייב לשאת simulated: true. הוא אינו משנה הסכם, פלייבוק או מצב אמיתי')
			Q=C.get('base_round')
			if E is not None and isinstance(Q,int)and Q!=E:r.warn(A,'התרגול נעשה בסבב %s והמרכז בסבב %s. הסבב השתנה: התרגול התיישן וצריך רענון'%(Q,E))
def main():
	B=argparse.ArgumentParser();B.add_argument('--data',required=True);B.add_argument('--strict',action='store_true');E=B.parse_args()
	try:F=json.load(io.open(E.data,encoding='utf-8'))
	except ValueError as G:print('שגיאה: הקובץ אינו JSON תקין. %s'%G);sys.exit(1)
	A=validate(F)
	if A.errors:
		print('נמצאו %d שגיאות חוסמות. אין להזריק לתבנית לפני תיקונן:'%len(A.errors))
		for(C,D)in A.errors:print('  [%s] %s'%(C,D))
	if A.warns:
		print('%d אזהרות:'%len(A.warns))
		for(C,D)in A.warns:print('  [%s] %s'%(C,D))
	if not A.errors and not A.warns:print('בדיקת הסכמה עברה במלואה. הנתונים תואמים את מה שהתבנית יודעת להציג.')
	elif not A.errors:print('אין שגיאות חוסמות. ניתן להזריק.')
	sys.exit(1 if A.errors or E.strict and A.warns else 0)
if __name__=='__main__':main()
