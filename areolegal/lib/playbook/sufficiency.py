# -*- coding: utf-8 -*-
# Copyright (c) Areo. All rights reserved. Licensed under the terms at https://areo.co.il/legal/terms
'playbook/sufficiency.py: האם ההסכמים של הלקוח מספיקים כדי להסיק את קווי הנסיגה שלו (כלל מייסד 13).'
import argparse,io,json,sys
SOLID_AGREEMENTS=7
OPTIMAL_AGREEMENTS=20
MIN_WITH_TRAIL=3
MIN_ANY=3
AREO_FALLBACK_SHARE=.5
SIGNED_ROLES='signed','agreement'
DRAFT_ROLES='draft',
CORRESPONDENCE_ROLES='correspondence',
NOT_AGREEMENT_ROLES=('template','form','amendment')+DRAFT_ROLES+CORRESPONDENCE_ROLES
DOCUMENT_BASES='established','single','offered_unexecuted','client_answer'
AREO_BASES='areo_proposal','market_standard'
LEVELS='sufficient','thin','insufficient'
TEXT={'he':{'thin_head':'החומר שמסרתם מספיק כדי להתחיל, אבל לא כדי לדייק את קווי הנסיגה של החברה.','insufficient_head':'החומר שמסרתם אינו מספיק כדי להסיק איפה החברה מוכנה לוותר.','ok':'החומר מספיק כדי להסיק את קווי הנסיגה של החברה מההסכמים שלה. מ-20 הסכמים ומעלה מאותו סוג הדיוק משתפר עוד.','few':'עוד {k} הסכמים לפחות מאותו סוג ומאותה עמדה של החברה (מול צדדים שונים או בתקופות שונות).','trail':'טיוטות משא ומתן (גרסאות עם שינויים במעקב) והתכתבות עם הצד השני על סעיפים שהתמקחתם עליהם. הן מראות מה ביקשתם, על מה ויתרתם ובמה התעקשתם.','spread':'הסכמים שנחתמו מול צדדים שונים. כשכל ההסכמים כמעט זהים, אי אפשר לדעת איפה יש לכם גמישות.','areo':'ב-{n} מתוך {m} נושאים הצהוב מבוסס על הצעת Areo בלבד, כי אין במסמכים שלכם פשרה בנושא.','ask':'מה שיחדד את התוצאה:','tail':'אפשר להמשיך גם עכשיו. קווי נסיגה שאינם נשענים על החומר שלכם יסומנו "הצעת Areo", ואפשר להשלים חומר ולעדכן את הפלייבוק בכל שלב.'},'en':{'thin_head':"What you gave is enough to start, but not enough to pin down the company's fallback lines.",'insufficient_head':'What you gave is not enough to tell where the company is willing to give ground.','ok':"The material is enough to infer the company's fallback lines from its own agreements. From 20 agreements of the same type the precision improves further.",'few':'At least {k} more agreements of the same type and the same company side (with different counterparties or from different periods).','trail':'Negotiation drafts (versions with tracked changes) and correspondence with the other side on the clauses you bargained over. They show what you asked for, what you gave up and where you held.','spread':'Agreements signed with different counterparties. When all agreements are nearly identical, there is no way to tell where you have flexibility.','areo':'In {n} of {m} topics the fallback rests on an Areo proposal alone, because your documents hold no compromise on the topic.','ask':'What would sharpen the result:','tail':'You can go on now. Fallback lines that do not rest on your material will be marked "Areo proposal", and you can add material and update the playbook at any time.'}}
def _lang(lang):return'en'if str(lang or'').strip().lower().startswith('en')else'he'
def _included(s):return isinstance(s,dict)and s.get('included')is not False
def _role(s):return str(s.get('doc_role')or'').strip().lower()
def _family(s):return str(s.get('family_id')or s.get('contract_family_id')or s.get('family')or'')or'_'
def agreements_per_family(sources):
	B={}
	for A in sources or[]:
		if not _included(A)or A.get('same_family')is False:continue
		C=_role(A)
		if C in NOT_AGREEMENT_ROLES:continue
		if C in SIGNED_ROLES or not C and str(A.get('status')or'').lower()in('signed','executed'):D=_family(A);B[D]=B.get(D,0)+1
	return B
def negotiation_trail(sources):
	C=D=E=0
	for A in sources or[]:
		if not _included(A):continue
		B=_role(A)
		if B in DRAFT_ROLES:C+=1
		elif B in CORRESPONDENCE_ROLES:D+=1
		elif B in SIGNED_ROLES and str(A.get('acceptance_mode')or'')=='negotiated':E+=1
	return{'drafts':C,'correspondence':D,'negotiated_agreements':E}
def _tracks_seen(rule):return{str(A.get('track'))for A in rule.get('evidence')or[]if isinstance(A,dict)and A.get('track')in('green','yellow','red')}
def spread(rules):
	A=[A for A in rules or[]if isinstance(A,dict)]
	if not A:return
	B=C=D=0
	for E in A:
		if len(_tracks_seen(E))>=2:B+=1
		F=((E.get('traffic_light')or{}).get('yellow')or{}).get('basis')
		if F in DOCUMENT_BASES:C+=1
		elif F in AREO_BASES:D+=1
	return{'rules':len(A),'with_spread':B,'yellow_from_documents':C,'yellow_areo_only':D}
def assess(sources,rules=None):
	I=sources;G=agreements_per_family(I);A=min(G.values())if G else 0;H=negotiation_trail(I);E=H['drafts']+H['correspondence']>0;B=spread(rules);F,C=[],[]
	if A>=SOLID_AGREEMENTS:D='sufficient'
	elif A>=MIN_WITH_TRAIL and E:D='sufficient'
	elif A>=MIN_ANY or A>=1 and E:D='thin'
	else:D='insufficient'
	if A<(MIN_WITH_TRAIL if E else SOLID_AGREEMENTS):F.append('FEW_AGREEMENTS');J=MIN_WITH_TRAIL if E else SOLID_AGREEMENTS;C.append({'kind':'more_agreements','need':max(1,J-A)})
	if not E and A<SOLID_AGREEMENTS:F.append('NO_NEGOTIATION_TRAIL');C.append({'kind':'negotiation_trail'})
	if B and B['rules']>=3 and B['with_spread']==0 and A<SOLID_AGREEMENTS:F.append('NO_SPREAD');C.append({'kind':'varied_counterparties'})
	if B and B['rules']and B['yellow_areo_only']/float(B['rules'])>AREO_FALLBACK_SHARE:
		F.append('FALLBACK_FROM_AREO')
		if D=='sufficient':D='thin'
		if not any(A['kind']=='negotiation_trail'for A in C):C.append({'kind':'negotiation_trail'})
	return{'level':D,'agreements':A,'agreements_per_family':G,'negotiation_trail':H,'spread':B,'reasons':F,'requests':C}
def client_message(res,lang='he'):
	B=res;A=TEXT[_lang(lang)]
	if B.get('level')=='sufficient'and not B.get('requests'):return[A['ok']]
	C=[A['insufficient_head']if B.get('level')=='insufficient'else A['thin_head'],A['ask']];E=B.get('spread')or{}
	for F in B.get('requests')or[]:
		D=F.get('kind')
		if D=='more_agreements':C.append('- '+A['few'].format(k=F.get('need',1)))
		elif D=='negotiation_trail':C.append('- '+A['trail'])
		elif D=='varied_counterparties':C.append('- '+A['spread'])
	if'FALLBACK_FROM_AREO'in(B.get('reasons')or[]):C.append(A['areo'].format(n=E.get('yellow_areo_only',0),m=E.get('rules',0)))
	C.append(A['tail']);return C
def record(res,client_response='pending',asked_at=None):A=res;return{'level':A['level'],'agreements':A['agreements'],'reasons':list(A['reasons']),'requests':[dict(A)for A in A['requests']],'asked_at':asked_at or'','client_response':client_response}
def findings(model):
	D=model;B=[]
	if not isinstance(D,dict):return B
	A=assess(D.get('source_log'),D.get('rules'))
	if A['level']=='sufficient'and not A['requests']:return B
	C=D.get('sufficiency')
	if not isinstance(C,dict)or not C.get('requests')or C.get('client_response')not in('pending','provided','declined'):B.append(('SUFFICIENCY_NOT_ASKED','error'if A['level']=='insufficient'else'warning','החומר אינו מספיק להסקת קווי הנסיגה (%s), והמודל אינו נושא sufficiency עם requests ועם תשובת הלקוח. בקשו מהלקוח חומר מסוים, והסבירו מה יחדד את התוצאה.'%(', '.join(A['reasons'])or A['level'])))
	elif C.get('level')!=A['level']:B.append(('SUFFICIENCY_STALE','warning','sufficiency.level במודל הוא %s, ומהמקורות הנוכחיים נגזר %s.'%(C.get('level'),A['level'])))
	return B
def main(argv=None):
	for B in(sys.stdout,sys.stderr):
		try:B.reconfigure(encoding='utf-8',errors='replace')
		except(AttributeError,ValueError):pass
	A=argparse.ArgumentParser(description=__doc__.split('\n')[0]);A.add_argument('--model',help='playbook-model.json (source_log ו-rules)');A.add_argument('--sources',help='קובץ JSON של רשימת מקורות (source_log), לפני שנבנה מודל');A.add_argument('--rules',help='קובץ JSON של הכללים, אופציונלי');A.add_argument('--lang',default='he');A.add_argument('--json',action='store_true',help='הפלט כ-JSON');C=A.parse_args(argv)
	try:return _run(C,A)
	except(OSError,ValueError)as D:print('לא ניתן לקרוא את הקובץ: %s'%D);return 3
def _run(a,ap):
	if a.model:
		with io.open(a.model,encoding='utf-8')as B:E=json.load(B)
		A,C=E.get('source_log'),E.get('rules')
	elif a.sources:
		with io.open(a.sources,encoding='utf-8')as B:A=json.load(B)
		A=A.get('source_log',A)if isinstance(A,dict)else A;C=None
		if a.rules:
			with io.open(a.rules,encoding='utf-8')as B:C=json.load(B)
	else:ap.error('נדרש --model או --sources');return 2
	D=assess(A,C)
	if a.json:print(json.dumps(D,ensure_ascii=False,indent=1))
	else:
		for F in client_message(D,a.lang):print(F)
	return{'sufficient':0,'thin':1,'insufficient':2}[D['level']]
if __name__=='__main__':sys.dont_write_bytecode=True;sys.exit(main())
