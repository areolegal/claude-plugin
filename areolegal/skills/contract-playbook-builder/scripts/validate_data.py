# -*- coding: utf-8 -*-
# Copyright (c) Areo. All rights reserved. Licensed under the terms at https://areo.co.il/legal/terms
import argparse,io,json,re,sys
for _s in(sys.stdout,sys.stderr):
	try:_s.reconfigure(encoding='utf-8',errors='replace')
	except(AttributeError,ValueError):pass
ISO=re.compile('^\\d{4}-\\d{2}-\\d{2}$')
ENUMS={'rule.conf':{'High','Medium','Low'},'rule.reg':{'Researched','NotResearched','NotApplicable','ApplicableSourcesFound','NoApplicableSources','NoSpecificSourceIdentified'},'presence.requirement':{'Required','Optional','Conditional','Prohibited'},'presence.missing_clause_color':{'Green','Yellow','Red','NotApplicable'},'ev.weight':{'High','Medium','Low'},'cite.side':{'pro','con','neutral'},'cite.track':{'green','yellow','red','context'},'source.kind':{'internal','external'},'source.paper':{'ours','theirs'},'rule.kind':{'משפטי','מסחרי'},'precedent.direction':{'stricter','easier','neutral'},'finding.severity':{'high','medium','low'},'meta.status':{'Draft','PartiallyApproved','Approved','Superseded'},'rat.rationale_status':{'Draft','Confirmed'},'reg.status':{'Performed','Completed','Partial','NotPerformed','Declined'},'build_path.path':{'own','own_plus_market','market_built'},'technical_code':{'signature_block','party_identification','notice_addresses','counterparts_esignature','headings','interpretation_grammar','recitals_descriptive','neutral_definition','bank_details','delivery_points_list','admin_form_fields','statutory_admin_restatement'}}
LIGHTS='green','yellow','red'
TOP_LEVEL=['meta','scope','sources','cites','rules','segments','precedents','templateFindings','queue']
class Report:
	def __init__(A):A.errors=[];A.warns=[]
	def err(A,where,msg):A.errors.append((where,msg))
	def warn(A,where,msg):A.warns.append((where,msg))
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
COMMERCIAL_ROW=['src','field','found','norm','he','ref','quote']
def check_commercial(r,data,sources):
	H=sources;D=data.get('commercial')
	if D is None:return
	if not isinstance(D,dict):r.err('commercial','commercial חייב להיות אובייקט עם fields ו-rows');return
	F=D.get('fields');I=D.get('rows')
	if not isinstance(F,list)or not F:r.err('commercial.fields','חסר מערך fields, ובלעדיו אין כותרות לטבלה');return
	if not isinstance(I,list):r.err('commercial.rows','rows חייב להיות מערך');return
	G=set()
	for(E,C)in enumerate(F):
		if not isinstance(C,dict)or not C.get('key')or not C.get('label'):r.err('commercial.fields[%d]'%E,'לכל תנאי נדרשים key ו-label')
		else:
			if C['key']in G:r.err('commercial.fields[%d]'%E,'מפתח כפול: %s'%C['key'])
			G.add(C['key'])
	for(E,A)in enumerate(I):
		B='commercial.rows[%d]'%E
		if not isinstance(A,dict):r.err(B,'שורה חייבת להיות אובייקט');continue
		for J in COMMERCIAL_ROW:
			if J not in A:r.err(B,'חסר שדה %s'%J)
		if A.get('field')and A['field']not in G:r.err(B,'field=%s אינו מופיע ב-fields'%A['field'])
		if A.get('src')and H and str(A['src']).split('#')[0]not in H:r.err(B,'src=%s אינו מופיע ב-sources'%A['src'])
		elif A.get('src')and'#'in str(A['src']):r.warn(B,'src=%s כולל עוגן פסקה. התבנית מחפשת את המקור לפי source_id בלבד'%A['src'])
		if A.get('found')and not str(A.get('quote')or'').strip():r.warn(B,'סומן found בלי ציטוט; המגירה תיפתח ריקה')
		if A.get('found')and not str(A.get('ref')or'').strip():r.warn(B,'סומן found בלי מספר סעיף')
def validate(data):
	C=data;A=Report()
	for k in TOP_LEVEL:
		if k not in C:A.err('שורש הקובץ','המפתח %r חסר. התבנית קוראת אותו, והיעדרו מרוקן לשונית'%k)
	N=C.get('meta')or{}
	for E in('id','slug','ls_key','company','title','version'):
		if not N.get(E):A.err('meta','meta.%s חסר. הוא נדרש לזיהוי הפלייבוק ולשמירת סימונים בדפדפן'%E)
	check_enum(A,'meta','status',N.get('status'),'meta.status');check_date(A,'meta','created',N.get('created'));check_date(A,'meta','updated',N.get('updated'))
	if N.get('ls_key')and not re.match('^[A-Za-z0-9_]+$',str(N['ls_key'])):A.err('meta','ls_key מכיל תווים שאינם אותיות לטיניות, ספרות או קו תחתון. מפתח כזה שובר את שמירת הסימונים בדפדפן')
	O=N.get('build_path')
	if not isinstance(O,dict):A.warn('meta','meta.build_path חסר. פס הבסיס לא יוצג, והדף לא יאמר על כמה הסכמים הפלייבוק נשען')
	else:
		if not isinstance(O.get('n'),int):A.err('meta.build_path','n חסר או אינו מספר. הוא מספר ההסכמים אחרי ניקוי כפילויות, ואינו מספר הקבצים בתיקייה')
		check_enum(A,'meta.build_path','path',O.get('path'),'build_path.path')
		if isinstance(O.get('n'),int)and O.get('path'):
			Z,y=O['n'],O['path']
			if Z==0 and y!='market_built':A.err('meta.build_path','אין הסכמים, ולכן המסלול חייב להיות market_built')
	a=C.get('coverage')
	if not isinstance(a,dict):A.warn('coverage','coverage חסר. פאנל כיסוי הסעיפים לא יוצג')
	else:
		for E in('units','topic_units','technical_units'):
			if not isinstance(a.get(E),int):A.warn('coverage','coverage.%s חסר או אינו מספר, והמספר יוצג כמקף'%E)
		l=a.get('technical_items')
		if not isinstance(l,list):A.warn('coverage','technical_items חסר. רשימת הסעיפים הטכניים לא תוצג')
		else:
			for(F,b)in enumerate(l):
				c='coverage.technical_items[%d]'%F
				if not isinstance(b,dict):A.err(c,'אינו אובייקט');continue
				check_enum(A,c,'code',b.get('code'),'technical_code')
				if not(b.get('reason')or'').strip():A.warn(c,'אין נימוק. הסעיף יוצג בלי הסבר למה אין לו משמעות')
	z=C.get('scope')or{};m=z.get('contract_families')or[]
	if not m:A.err('scope','לא הוגדרה אף משפחת הסכמים. הכותרת ותיאור התחולה יוצגו ריקים')
	for(F,E)in enumerate(m):
		if not E.get('contract_family_name'):A.err('scope.contract_families[%d]'%F,'contract_family_name חסר')
		if not E.get('company_role'):A.warn('scope.contract_families[%d]'%F,'company_role ריק. עמדת החברה במשפחה אינה מוצגת')
	n=C.get('reg')
	if isinstance(n,dict):check_enum(A,'reg','status',n.get('status'),'reg.status',required=False)
	K=C.get('sources')or{}
	if isinstance(K,list):A.err('sources','sources הוא מערך, אך התבנית מצפה לאובייקט שממפה מזהה מקור לפרטיו');K={}
	for(L,I)in K.items():
		B='sources[%s]'%L;check_enum(A,B,'kind',(I or{}).get('kind'),'source.kind')
		if not(I or{}).get('label'):A.err(B,'label חסר. המקור יוצג כקוד פנימי במקום בשם ידידותי')
		if(I or{}).get('kind')=='internal':
			check_enum(A,B,'paper',(I or{}).get('paper'),'source.paper',required=False);A0=(C.get('meta')or{}).get('corpus_status')or(C.get('scope')or{}).get('corpus_status');A1=A0=='unknown'or(I or{}).get('doc_role')in('form','template')
			if not(I or{}).get('paper')and not A1:A.warn(B,'paper חסר. לא יוצג אם ההסכם על הנייר שלנו או של הצד שכנגד')
	V=set();P=set(A.get('id')for A in C.get('rules')or[])
	for(F,G)in enumerate(C.get('cites')or[]):
		B='cites[%d]'%F;J=G.get('id')
		if not J:A.err(B,'id חסר')
		if J in V:A.err(B,'מזהה הציטוט %r חוזר'%J)
		V.add(J)
		if not G.get('text'):A.err(B,'text חסר. הערת השוליים תיפתח ריקה')
		T=str(G.get('src')or'').split('#')[0]
		if T and T not in K:A.err(B,'src %r אינו קיים ב-sources. הציטוט לא ישויך לאף מקור'%G['src'])
		elif T and T!=G['src']:A.warn(B,'src %r כולל עוגן פסקה. התבנית מחפשת את המקור לפי %r בלבד: העוגן נשמר ב-para (build_workspace_payload.py)'%(G['src'],T))
		check_enum(A,B,'side',G.get('side'),'cite.side',required=False);check_enum(A,B,'track',G.get('track'),'cite.track',required=False)
		if not G.get('track'):A.warn(B,'track חסר. הציטוט לא ישויך לעמדה, ולא ייכנס לספירת ההסכמים ולאחוז שמוצגים בה. ראיה הקשרית מסומנת context')
		for D in G.get('rules')or[]:
			if D not in P:A.err(B,'מפנה לכלל %r שאינו קיים'%D)
	A2=set(A.get('segment_id')for A in C.get('segments')or[])
	for(F,I)in enumerate(C.get('segments')or[]):
		B='segments[%d]'%F
		if not I.get('segment_id'):A.err(B,'segment_id חסר')
		if not I.get('label'):A.err(B,'label חסר. הסגמנט יוצג כקוד פנימי')
		if not I.get('criteria'):A.warn(B,'criteria ריק. לא יהיה ברור מתי הסגמנט חל')
	U=[A for A in C.get('playbooks')or[]if A.get('id')]
	if len(C.get('playbooks')or[])>1 and not U:A.err('playbooks','יש יותר מפלייבוק אחד ואין להם id. בלי מזהה אי אפשר לשייך סעיפים ואי אפשר לבורר לעבוד')
	if len(U)>1:
		o=set(A['id']for A in U);p=[A.get('id')for A in C.get('rules')or[]if not A.get('pb')]
		if p:A.err('rules','יש %d פלייבוקים, ו-%d סעיפים בלי שדה pb. סעיף בלי שיוך יוצג בכל משפחה, ומדיניות ממשפחה אחת תיראה כאילו היא של אחרת'%(len(U),len(p)))
		for W in C.get('rules')or[]:
			if W.get('pb')and W['pb']not in o:A.err('rules[%s]'%W.get('id'),'pb %r אינו קיים ב-playbooks'%W['pb'])
		d=C.get('books')or{}
		for e in U:
			A3=(d.get(e['id'])or{}).get('rules')if d else C.get('rules')
			if not any(A.get('pb')==e['id']for A in A3 or[]):A.warn('playbooks[%s]'%e['id'],'אין בקובץ אף סעיף של הפלייבוק הזה. הבורר יציג מסך ריק מוסבר')
		for q in d:
			if q not in o:A.err('books[%s]'%q,'ספר שאין לו שורה ב-playbooks, ולכן אין אליו מעבר בבורר')
	r=set()
	for G in C.get('cites')or[]:
		if G.get('track'):
			for D in G.get('rules')or[]:r.add((D,G['track']))
	s=set()
	for(F,H)in enumerate(C.get('rules')or[]):
		D=H.get('id')or'?';B='rules[%d] (%s)'%(F,D)
		if D in s:A.err(B,'מזהה הכלל %r חוזר'%D)
		s.add(D);check_enum(A,B,'kind',H.get('kind'),'rule.kind',required=False)
		if not H.get('they'):A.warn(B,"they חסר. הכרטיס 'מה הצד שכנגד ירצה' לא יוצג, ועורך הדין יראה רק את הצד שלנו")
		for(Q,Z)in enumerate(H.get('norms')or[]):
			for E in('law','ref','meaning'):
				if not Z.get(E):A.err('%s norms[%d]'%(B,Q),'%s חסר. שורת המקור הנורמטיבי תוצג חלקית'%E)
		if not H.get('kind'):A.warn(B,'kind חסר. הסעיף לא ישויך למשפטי או למסחרי, והסינון לפי סוג הסעיף לא יראה אותו')
		for f in LIGHTS:
			R=(H.get('tl')or{}).get(f)or{}
			if(D,f)in r or R.get('basis')or R.get('label'):continue
			A.warn(B,'אין ציטוט משויך לעמדה ה%s ואין לה מקור מוצהר. היא תוצג כהנחה של המערכת ולא כראיה מהתיקייה'%{'green':'ירוקה','yellow':'צהובה','red':'אדומה'}[f])
		for E in('id','topic','issue'):
			if not H.get(E):A.err(B,'השדה %r חסר, והוא שדה חובה בכרטיס הכלל'%E)
		g=H.get('presence')or{}
		if g.get('requirement')=='Recommended':A.warn(B+'.presence','requirement Recommended הוא ערך ישן, והסינון לפי נחיצות הסעיף לא יראה אותו. הערכים: Required, Optional, Conditional, Prohibited')
		else:check_enum(A,B+'.presence','requirement',g.get('requirement'),'presence.requirement')
		check_enum(A,B+'.presence','missing_clause_color',g.get('missing_clause_color'),'presence.missing_clause_color');A4=H.get('tl')or{}
		for M in LIGHTS:
			R=A4.get(M)
			if not isinstance(R,dict):A.err(B,'הרמזור חסר את המצב %r. שלושת המצבים חובה בכל כלל'%M);continue
			if not R.get('pos'):A.err('%s.tl.%s'%(B,M),'pos ריק. תא הרמזור יוצג ריק')
			h=R.get('crit')
			if h is None:A.err('%s.tl.%s'%(B,M),'crit חסר. התבנית מצפה למערך קריטריונים')
			elif not isinstance(h,list):A.err('%s.tl.%s'%(B,M),'crit חייב להיות מערך, ולא %s'%type(h).__name__)
		check_enum(A,B,'conf',H.get('conf'),'rule.conf',required=False);A5=H.get('rat')or{};t=A5.get('rationale_status')
		if t is None:A.warn(B,'אין rationale_status. הנושא יוצג כטיוטה בסביבת העבודה')
		else:check_enum(A,B+'.rat','rationale_status',t,'rat.rationale_status',required=False)
		check_enum(A,B,'reg',H.get('reg'),'rule.reg',required=False)
		for(Q,X)in enumerate(H.get('ev')or[]):
			u='%s.ev[%d]'%(B,Q)
			if X.get('source_id')and X['source_id']not in K:A.err(u,'source_id %r אינו קיים ב-sources'%X['source_id'])
			check_enum(A,u,'weight',X.get('weight'),'ev.weight',required=False)
		for v in H.get('rel')or[]:
			if v not in P:A.err(B,'rel מפנה לכלל %r שאינו קיים'%v)
		for(Q,i)in enumerate(H.get('impacts')or[]):
			if i.get('related_rule_id')and i['related_rule_id']not in P:A.err('%s.impacts[%d]'%(B,Q),'related_rule_id %r אינו קיים'%i['related_rule_id'])
		for(Q,Y)in enumerate(H.get('variants')or[]):
			w='%s.variants[%d]'%(B,Q)
			if Y.get('seg')and Y['seg']not in A2:A.err(w,'seg %r אינו קיים ברשימת הסגמנטים'%Y['seg'])
			A6=Y.get('tl')or{}
			for M in A6:
				if M not in LIGHTS:A.err(w,'מצב רמזור %r אינו מוכר. המצבים הם green, yellow, red'%M)
	for(F,j)in enumerate(C.get('precedents')or[]):
		B='precedents[%d]'%F;check_enum(A,B,'direction',j.get('direction'),'precedent.direction')
		for D in j.get('rules')or[]:
			if D not in P:A.err(B,'מפנה לכלל %r שאינו קיים'%D)
		for J in j.get('cites')or[]:
			if J not in V:A.err(B,'מפנה לציטוט %r שאינו קיים'%J)
	for(F,E)in enumerate(C.get('templateFindings')or[]):
		B='templateFindings[%d]'%F;check_enum(A,B,'severity',E.get('severity'),'finding.severity')
		if not E.get('title'):A.err(B,'title חסר')
		for J in E.get('cites')or[]:
			if J not in V:A.err(B,'מפנה לציטוט %r שאינו קיים'%J)
	for(F,S)in enumerate(C.get('queue')or[]):
		B='queue[%d]'%F
		if not S.get('question'):A.err(B,'question חסר. פריט בלי שאלה אינו ניתן להכרעה')
		if S.get('rule_id')and S['rule_id']!='GLOBAL'and S['rule_id']not in P:A.err(B,'rule_id %r אינו קיים'%S['rule_id'])
		for D in S.get('rule_ids')or[]:
			if D not in P:A.err(B,'rule_ids מפנה לכלל %r שאינו קיים'%D)
	for(F,G)in enumerate(C.get('cross')or[]):
		B='cross[%d]'%F
		for D in G.get('rules')or[]:
			if D not in P:A.err(B,'צירוף מפנה לכלל %r שאינו קיים'%D)
	x=C.get('friendly')or{}
	for L in x:
		if L not in K:A.warn('friendly','השם הידידותי מוגדר למקור %r שאינו קיים ב-sources'%L)
	for L in K:
		if L not in x and L not in(C.get('shortx')or{}):A.warn('sources','למקור %r אין שם ידידותי, והוא יוצג כקוד פנימי'%L)
	if not(C.get('rules')or[]):A.err('rules','אין אף כלל מדיניות. ה-Workspace יוצג ריק')
	check_commercial(A,C,K);return A
def main():
	B=argparse.ArgumentParser();B.add_argument('--data',required=True);B.add_argument('--strict',action='store_true');G=B.parse_args()
	try:C=json.load(io.open(G.data,encoding='utf-8'))
	except ValueError as J:print('שגיאה: הקובץ אינו JSON תקין. %s'%J);sys.exit(1)
	A=validate(C)
	for(H,K)in sorted((C.get('books')or{}).items()):D=dict(K);D['playbooks']=C.get('playbooks')or[];D.pop('books',None);I=validate(D);A.errors+=[('books[%s].%s'%(H,A),B)for(A,B)in I.errors];A.warns+=[('books[%s].%s'%(H,A),B)for(A,B)in I.warns if not A.startswith('playbooks[')]
	if A.errors:
		print('נמצאו %d שגיאות חוסמות. אין להזריק לתבנית לפני תיקונן:'%len(A.errors))
		for(E,F)in A.errors:print('  [%s] %s'%(E,F))
	if A.warns:
		print('%d אזהרות:'%len(A.warns))
		for(E,F)in A.warns:print('  [%s] %s'%(E,F))
	if not A.errors and not A.warns:print('בדיקת הסכמה עברה במלואה. הנתונים תואמים את מה שהתבנית יודעת להציג.')
	elif not A.errors:print('אין שגיאות חוסמות. ניתן להזריק.')
	sys.exit(1 if A.errors or G.strict and A.warns else 0)
if __name__=='__main__':main()
