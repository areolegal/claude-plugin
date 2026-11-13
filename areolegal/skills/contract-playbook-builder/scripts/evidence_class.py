#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (c) Areo. All rights reserved. Licensed under the terms at https://areo.co.il/legal/terms
'מחלקת הראיה ורמת הביטחון, בקוד (הערות ענבל, 12.11.2026, סעיפים 3.2, 3.3 ו-4.1 במסמך "לפי סקיל").'
import argparse,io,json,os,sys
PAPERS='ours','theirs','third_party','unknown'
SIGNED='signed','agreement','amendment'
DRAFT='draft',
ORDER='A1','A2','B','C','D'
REF_KEYS='source_ref','source_id','src','source'
def _sid(v):return str(v).split('#',1)[0].strip()if isinstance(v,(str,int))and str(v).strip()else''
def rows(model):
	C={}
	for(D,A)in enumerate(model.get('source_log')or[]):
		if not isinstance(A,dict)or A.get('included')is False:continue
		E=_sid(A.get('source_id'))or'F%d'%(D+1);B=A.get('paper')
		if B not in PAPERS:B='unknown'
		C[E]=dict(A,paper=B)
	return C
def cited(obj,known,acc=None):
	D=known;B=obj;A=acc;A=set()if A is None else A
	if isinstance(B,dict):
		for(F,C)in B.items():
			if F in REF_KEYS:
				E=_sid(C)
				if E in D:A.add(E)
			cited(C,D,A)
	elif isinstance(B,list):
		for C in B:cited(C,D,A)
	return A
def klass(srcs):
	A=srcs
	if not A:return
	B={}
	for C in A:B.setdefault(C.get('negotiation_id')or C.get('_sid'),[]).append(C)
	F=lambda g:{A.get('doc_role')for A in g}
	for D in B.values():
		if F(D)&set(DRAFT)and F(D)&set(SIGNED)and any(A['paper']=='ours'for A in D):return'A1'
	if any(A.get('doc_role')in DRAFT and A['paper']=='theirs'for A in A):return'A2'
	if any(len(A)>=2 for A in B.values()):return'B'
	E=[A for A in A if A.get('doc_role')in SIGNED or A.get('doc_role')in('template','form')];G=[A for A in E if A['paper']in('ours','theirs')]
	if E and len(G)*2>=len(E):return'C'
	return'D'
def confidence(srcs):
	if not srcs:return'low','הצעה של Areo: אין מקור בהסכמים'
	B=[A for A in srcs if A.get('doc_role')in SIGNED]
	if not B:return'low','נשען על טיוטות בלבד'
	D={A.get('counterparty')or A.get('negotiation_id')or A.get('_sid')for A in B};A,C=len(B),len(D)
	if A>=10 and C>=3:return'high','%d הסכמים חתומים, מול %d צדדים שונים'%(A,C)
	if A>=5:return'medium','%d הסכמים חתומים'%A+(''if C>=3 else', מול פחות משלושה צדדים שונים')
	return'low','%d הסכמים חתומים בלבד'%A
def apply(model):
	C=model
	for(G,B)in enumerate(C.get('source_log')or[]):
		if isinstance(B,dict)and not _sid(B.get('source_id')):B['source_id']='F%d'%(G+1)
	A=rows(C)
	for(K,B)in A.items():B['_sid']=K
	F=[]
	for(G,B)in enumerate(C.get('source_log')or[]):
		if isinstance(B,dict)and B.get('included')is not False and B.get('paper')not in PAPERS:B['paper']='unknown'
	L={B:sum(1 for A in A.values()if A['paper']==B)for B in PAPERS};M=C.setdefault('scope_summary',{});M['paper_counts']=L;C['evidence_class']=klass(list(A.values()))or'D'
	for D in C.get('rules')or[]:
		if not isinstance(D,dict):continue
		H=[A[B]for B in sorted(cited(D.get('traffic_light')or{},A)|cited(D.get('evidence')or[],A))];D['evidence_class']=klass(H);N,O=confidence(H);D['confidence_computed']=N;D['confidence_basis']=O;I=cited((D.get('traffic_light')or{}).get('green')or{},A)
		if I and all(A[B]['paper']in('theirs','unknown','third_party')for B in I):F.append('%s: העמדה המועדפת נשענת רק על מסמכים שאינם על הנייר של החברה'%D.get('rule_id'))
	E=sorted(A for(A,B)in A.items()if B['paper']=='unknown');J=C.setdefault('validation_queue',[])
	if E and len(E)*2<max(1,len(A))and not any(isinstance(A,dict)and A.get('kind')=='paper_confirm'and A.get('status')!='closed'for A in J):P=[str(A[B].get('title')or os.path.basename(str(A[B].get('file')or B)))for B in E][:12];J.append({'id':'Q-PAPER','kind':'paper_confirm','scope':'playbook','rule_id':'GLOBAL','topic':'על הנייר של מי','severity':'בינונית','question':'על הנייר של מי נוסחו ההסכמים האלה? %s'%', '.join(P),'why':'לא ידוע מי ניסח אותם, ולכן הם לא נכנסו לפלייבוק. הסכם על הנייר שלכם מלמד מה אתם מבקשים, והסכם על הנייר של הצד השני מלמד על מה הסכמתם.','recommendation':'לסמן לכל הסכם אם הוא על הנייר שלכם או של הצד השני, כדי שייכנס לפלייבוק.','source_ids':E,'answered':False})
	if E and len(E)*2>=max(1,len(A)):F.append('ברוב ההסכמים לא ידוע של מי הנייר: מחלקה D, בלי עמדה מועדפת מהקורפוס')
	C['evidence_warnings']=F;return C,F
def main(argv=None):
	sys.stdout.reconfigure(encoding='utf-8');C=argparse.ArgumentParser(description=__doc__.split('\n')[0]);C.add_argument('--model',required=True);C.add_argument('--dry-run',action='store_true');D=C.parse_args(argv)
	with io.open(D.model,encoding='utf-8')as E:A=json.load(E)
	A,F=apply(A)
	if not D.dry_run:
		with io.open(D.model,'w',encoding='utf-8')as E:json.dump(A,E,ensure_ascii=False,indent=1)
	B=A['scope_summary']['paper_counts'];print('מחלקת ראיה: %s · על הנייר שלכם %d, של הצד השני %d, צד שלישי %d, לא ידוע %d'%(A['evidence_class'],B['ours'],B['theirs'],B['third_party'],B['unknown']))
	for G in F:print('אזהרה: %s'%G)
	return 0
if __name__=='__main__':sys.exit(main())
