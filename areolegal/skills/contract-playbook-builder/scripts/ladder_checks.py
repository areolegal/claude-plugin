#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (c) Areo. All rights reserved. Licensed under the terms at https://areo.co.il/legal/terms
'מדרגות הנסיגה, הספים ומרשם החריגים, בקוד (הערות ענבל, 12.11.2026, "לפי סקיל" 4.3-4.6 ו-5.1).'
import argparse,io,json,os,re,sys
HERE=os.path.dirname(os.path.abspath(__file__))
DEFAULTS=os.path.normpath(os.path.join(HERE,'..','assets','playbook-thresholds.json'))
MATERIAL='critical','high'
SIGNED='signed','agreement','amendment'
RED_SOURCES='declared','law','behavioral'
PCT=re.compile('(\\d+(?:\\.\\d+)?\\s*%|\\d+\\s*אחוז(?:ים)?)\\s*(?:מ|of\\s+)?(?:ה|the\\s+)?(?:הסכמים|מסמכים|agreements|documents|deals|עסקאות)',re.I)
def load_thresholds(model_path,explicit=None):
	B=model_path;C={}
	for A in(DEFAULTS,os.path.join(os.path.dirname(os.path.abspath(B)),'..','..','playbook-thresholds.json'),os.path.join(os.path.dirname(os.path.abspath(B)),'..','playbook-thresholds.json'),explicit):
		if A and os.path.isfile(A):
			try:
				with io.open(A,encoding='utf-8')as D:C.update({A:B for(A,B)in json.load(D).items()if A!='about'})
			except(OSError,ValueError):pass
	return C
def text_of(v):
	if isinstance(v,dict):
		for A in('he','text','en'):
			if isinstance(v.get(A),str)and v[A].strip():return v[A]
		return''
	return v if isinstance(v,str)else''
def _norm(s):return re.sub('\\s+',' ',str(s or'')).strip()
CONCESSION={('important','low'):'נושא חשוב שבו ההסכמים עקביים: מחזיקים בו.',('minor','high'):'נושא פחות חשוב שזז הרבה במשא ומתן: זה הוויתור שמציעים ראשון, כדי לקנות נושא חשוב.',('any','zero_unfavorable'):'תמיד ויתרתם בו: להפסיק לבקש, או להפוך אותו לקרב מנומק.',('any','zero_favorable'):'תמיד התקבל: או תקן שוק, או שמעולם לא נבחן. לא מוותרים עליו בלי סיבה.',('important','high'):'נושא חשוב שזז הרבה: יורדים בו מדרגה אחת בכל פעם, ורק בתמורה.',('minor','low'):'נושא פחות חשוב ועקבי: אפשר לוותר בו אם זה קונה משהו.'}
def concession(importance,variance):
	A=variance
	if A in('zero_unfavorable','zero_favorable'):return CONCESSION['any',A]
	if A not in('low','high'):return''
	return CONCESSION['important'if importance in MATERIAL else'minor',A]
def signed_count(rule,model):
	E={str(A.get('source_id')):A for A in model.get('source_log')or()if isinstance(A,dict)};C=set()
	def B(o):
		if isinstance(o,dict):
			for(F,A)in o.items():
				if F in('source_ref','source_id')and isinstance(A,str):
					D=A.split('#',1)[0]
					if E.get(D,{}).get('doc_role')in SIGNED:C.add(D)
				B(A)
		elif isinstance(o,list):
			for A in o:B(A)
	B(rule.get('traffic_light')or{});B(rule.get('evidence')or[]);return len(C)
def check_rule(rule,model,th):
	O=model;F=th;B=rule;D=B.get('rule_id')or'?';E=[];I=B.get('traffic_light')or{};H=I.get('yellow')if isinstance(I.get('yellow'),dict)else{};J=I.get('red')if isinstance(I.get('red'),dict)else{};A=[A if isinstance(A,dict)else{'text':A}for A in H.get('fallback_steps')or[]if A];G=text_of(H.get('fallback_wording'));K=lambda a,b:re.sub('[\\W_]+','',_norm(a))==re.sub('[\\W_]+','',_norm(b));L=[A for(A,B)in enumerate(A)if G and K(text_of(B.get('text')),G)]
	if L and L[0]>0:A.insert(0,A.pop(L[0]))
	M=[]
	for C in A:
		if not any(K(text_of(C.get('text')),text_of(A.get('text')))for A in M):M.append(C)
	A=M
	if G and A and not K(text_of(A[0].get('text')),G):A.insert(0,{'text':G,'source':(H.get('fallback_wording')or{}).get('source')if isinstance(H.get('fallback_wording'),dict)else None})
	if G and not A:A=[{'text':G}]
	for(N,C)in enumerate(A):
		C.setdefault('origin','derived'if C.get('source')in('areo_proposal','market_standard')or C.get('derived')else'observed');C.pop('floor',None)
		if not _norm(text_of(C.get('text'))):E.append(('STEP_NO_WORDING','%s: מדרגה %d בלי נוסח להחלה'%(D,N+1)))
		if C.get('special_approval'):E.append(('STEP_FROM_EXCEPTION','%s: מדרגה %d נשענת על ערך שדרש אישור חריג: מקומו במרשם החריגים'%(D,N+1)))
		P=C.get('counterparties')
		if C['origin']=='observed'and isinstance(P,int)and P<int(F.get('step_min_counterparties',2)):E.append(('STEP_SINGLE_COUNTERPARTY','%s: מדרגה %d נצפתה מול צד שכנגד אחד בלבד: מקומה במרשם החריגים'%(D,N+1)))
	if A:A[-1]['floor']=True;H['fallback_steps']=A;B['floor_wording']=text_of(A[-1].get('text'))
	if len(A)>int(F.get('max_steps',3)):E.append(('TOO_MANY_STEPS','%s: %d מדרגות, והמקסימום %s'%(D,len(A),F.get('max_steps',3))))
	if B.get('importance')in MATERIAL and len(A)<int(F.get('material_min_steps',2))and not H.get('fallback_steps_note'):E.append(('LADDER_TOO_SHORT','%s: נושא מהותי עם %d מדרגות, בלי רישום שחסרות נקודות'%(D,len(A))))
	Q=J.get('red_source')
	if Q=='absence':E.append(('RED_FROM_ABSENCE','%s: קו אדום שמקורו היעדר. מקורות מותרים: מוצהר, דין שנבדק, או התנהגותי'%D))
	elif Q=='behavioral':
		if int(J.get('rejected_in_deals')or 0)<int(F.get('behavioral_red_min_deals',3))or int(J.get('signed_with')or 0)>0:E.append(('RED_BEHAVIORAL_THIN','%s: קו אדום התנהגותי שלא נדחה בשלוש עסקאות, או שהופיע בהסכם חתום'%D))
	if signed_count(B,O)<int(F.get('percent_min_signed',5)):
		S=' '.join(_norm(text_of(A.get(B)))for A in[B]+[I.get(A)or{}for A in('green','yellow','red')]if isinstance(A,dict)for B in('rationale','position','notes','why','green_pref'))
		if PCT.search(S):E.append(('PERCENT_SMALL_SAMPLE','%s: הצהרה באחוזים על ההסכמים, כשמאחורי הנושא פחות מ-%s חתומים'%(D,F.get('percent_min_signed',5))))
	if B.get('variants_tie')and not any(isinstance(A,dict)and A.get('kind')=='variants_tie'and A.get('rule_id')==D for A in O.get('validation_queue')or[]):E.append(('TIE_UNRESOLVED','%s: שני נוסחים נפוצים במידה דומה הוכרעו בלי פריט בתור ההכרעות'%D))
	R=concession(B.get('importance'),B.get('variance'))
	if R and not B.get('concession_note'):B['concession_note']=R
	return E
def apply(model,th):
	A=model;B=[]
	for C in A.get('rules')or[]:
		if isinstance(C,dict):B+=check_rule(C,A,th)
	A['ladder_findings']=[{'code':A,'text':B}for(A,B)in B];return A,B
def main(argv=None):
	sys.stdout.reconfigure(encoding='utf-8');B=argparse.ArgumentParser(description=__doc__.split('\n')[0]);B.add_argument('--model',required=True);B.add_argument('--thresholds');B.add_argument('--dry-run',action='store_true');A=B.parse_args(argv)
	if not os.path.isfile(A.model):print('המודל אינו קיים: %s'%A.model);return 2
	with io.open(A.model,encoding='utf-8')as D:E=json.load(D)
	E,C=apply(E,load_thresholds(A.model,A.thresholds))
	if not A.dry_run:
		with io.open(A.model,'w',encoding='utf-8')as D:json.dump(E,D,ensure_ascii=False,indent=1)
	for(F,G)in C:print('%s %s'%(F,G))
	print('מדרגות וספים: %s'%('עבר'if not C else'%d ממצאים'%len(C)));return 3 if C else 0
if __name__=='__main__':sys.exit(main())
