#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (c) Areo. All rights reserved. Licensed under the terms at https://areo.co.il/legal/terms
'סעיפים קשורים מוטפסים, בקוד (הערות ענבל, 12.11.2026, v12 פרק 10, "לפי סקיל" 7.1).'
import argparse,io,json,os,re,sys
HERE=os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0,HERE)
import evidence_kind as EK
PAIRS=os.path.normpath(os.path.join(HERE,'..','..','contract-negotiation-orchestrator','scripts','interaction_pairs.json'))
DEF_RX=[re.compile('["“”״]([^"“”״]{2,40})["“”״]\\s*(?:פירושו|פירושה|משמעו|משמעה|יהיה פירושו|-\\s*פירושו)'),re.compile('"([^"]{2,40})"\\s+(?:means|shall mean)',re.I)]
LEARN_MIN=3
def text_of(v):
	if isinstance(v,dict):
		for A in('he','text','en'):
			if isinstance(v.get(A),str)and v[A].strip():return v[A]
		return''
	return v if isinstance(v,str)else''
def load_pairs(path=PAIRS):
	try:
		with io.open(path,encoding='utf-8')as B:A=json.load(B)
	except(OSError,ValueError):return{},[],{}
	return A.get('families')or{},[tuple(A[:3])for A in A.get('pairs')or()if len(A)>=3],A.get('pair_meta')or{}
def rule_text(r):
	C=r.get('traffic_light')or{};B=[r.get('topic_name'),r.get('clause_issue')]
	for D in('green','yellow','red'):
		A=C.get(D)or{}
		if isinstance(A,dict):B+=[A.get('position'),text_of(A.get('proposed_clause'))]
	return' '.join(str(A or'')for A in B)
def families_of(r,fams):
	A=' '.join(str(r.get(A)or'')for A in('topic_name','clause_issue')).lower();B=set()
	for(D,C)in fams.items():
		if any(he_word(B).search(A)for B in C.get('he')or()if B.strip())or any(re.search('\\b'+re.escape(B.strip().lower()),A)for B in C.get('en')or()if B.strip()):B.add(D)
	return B
def he_word(w):return re.compile('(?<![א-ת])[ובלמהשכ]{0,2}'+re.escape(w.strip()))
def defined_terms(r):A=text_of(((r.get('traffic_light')or{}).get('green')or{}).get('proposed_clause'));return{C.group(1).strip()for B in DEF_RX for C in B.finditer(A or'')}
def derive(model,extract=None,pairs=None):
	Q=extract;E=model;a,b,R=pairs or load_pairs();B=[A for A in E.get('rules')or()if isinstance(A,dict)and A.get('rule_id')];S=E.get('related_decisions')or{};G={A['rule_id']:[]for A in B}
	def H(a,b,**A):
		B='%s|%s'%(a,b)
		if any(B['related_rule_id']==b and B['kind']==A['kind']for B in G[a]):return
		if A['origin']!='mechanical':
			if S.get(B)is False:return
			A['approved']=True if S.get(B)is True else None
		else:A['approved']=True
		G[a].append(dict(related_rule_id=b,**A))
	for C in B:
		for T in defined_terms(C):
			for A in B:
				if A is not C and T in rule_text(A):H(C['rule_id'],A['rule_id'],direction='affects',kind='defined_term',origin='mechanical',severity='attention',doc_count=None,impact='המונח "%s" מוגדר בנושא הזה ומשמש בנושא "%s": שינוי בהגדרה חל גם שם.'%(T,A.get('topic_name')or A['rule_id']),action='כשההגדרה משתנה, בודקים את הנושא התלוי באותו סבב.')
	U={A['rule_id']:families_of(A,a)for A in B}
	for(I,J,c)in b:
		K=R.get('%s|%s'%(I,J))or R.get('%s|%s'%(J,I))or{}
		for C in B:
			if I not in U[C['rule_id']]:continue
			for A in B:
				if A is C or J not in U[A['rule_id']]:continue
				H(C['rule_id'],A['rule_id'],direction='affects',kind=K.get('kind')or'remedy_integrity',origin='catalog',severity=K.get('severity')or'attention',doc_count=None,impact=c+'.',action=K.get('action')or'כשאחד משתנה, בודקים את השני באותו סבב.')
	V={str(A.get('source_id')):A for A in E.get('source_log')or()if isinstance(A,dict)};W=EK.doc_index(Q)if Q else{};L={}
	for D in B:
		X=set()
		for M in D.get('evidence')or():
			if not isinstance(M,dict):continue
			N=str(M.get('source_ref')or'').split('#',1)[0];d=EK.ev_kind(M,V.get(N),EK.doc_for_source(V.get(N),W)if W else None)
			if d in('company_added','company_deleted'):X.add(N)
		L[D['rule_id']]=X
	for(e,C)in enumerate(B):
		for A in B[e+1:]:
			O=L[C['rule_id']]&L[A['rule_id']]
			if len(O)>=LEARN_MIN:H(C['rule_id'],A['rule_id'],direction='mutual',kind='give_take',origin='learned',severity='attention',doc_count=len(O),impact='בהסכמים של החברה שני הנושאים זזו יחד ב-%d מסמכים.'%len(O),action='ויתור באחד נשקל מול השני, כחבילה.')
	Y=[]
	for D in B:
		D['related_links']=G[D['rule_id']]
		for F in D['related_links']:
			if not(F.get('kind')and F.get('direction')and F.get('action')):Y.append(('LINK_INCOMPLETE','%s→%s: קישור בלי סוג, כיוון או כלל פעולה'%(D['rule_id'],F.get('related_rule_id'))))
	Z=sum(1 for A in B for B in A['related_links']if B.get('approved')is None);P=E.setdefault('validation_queue',[]);P[:]=[A for A in P if not(isinstance(A,dict)and A.get('kind')=='related_confirm'and A.get('status')!='closed')]
	if Z:P.append({'id':'Q-RELATED','kind':'related_confirm','scope':'playbook','rule_id':'GLOBAL','topic':'סעיפים קשורים','severity':'בינונית','question':'Areo מציעה %d קישורים בין נושאים מהקטלוג המשפטי או מההסכמים שלכם. לאשר?'%Z,'why':'קישור שאושר מחייב את הנושא ונותן לטפל בשני הנושאים יחד. קישור שגוי מייצר התראות מיותרות, ולכן כל הצעה מחכה לאישור שלכם פעם אחת.','recommendation':'לעבור על הקישורים בלשונית המדיניות, בכל נושא תחת "סעיפים קשורים", ולאשר או לדחות.','answered':False})
	return E,Y
def main(argv=None):
	sys.stdout.reconfigure(encoding='utf-8');C=argparse.ArgumentParser(description=__doc__.split('\n')[0]);C.add_argument('--model',required=True);C.add_argument('--extract');C.add_argument('--dry-run',action='store_true');A=C.parse_args(argv)
	if not os.path.isfile(A.model):print('המודל אינו קיים: %s'%A.model);return 2
	with io.open(A.model,encoding='utf-8')as D:B=json.load(D)
	B,F=derive(B,EK.find_extract(B,A.model,A.extract))
	if not A.dry_run:
		with io.open(A.model,'w',encoding='utf-8')as D:json.dump(B,D,ensure_ascii=False,indent=1)
	E={A:sum(1 for B in B.get('rules')or()if isinstance(B,dict)for C in B.get('related_links')or()if C.get('origin')==A)for A in('mechanical','catalog','learned')}
	for(G,H)in F:print('%s %s'%(G,H))
	print('סעיפים קשורים: %d מכניים, %d מהקטלוג, %d נלמדו'%(E['mechanical'],E['catalog'],E['learned']));return 3 if F else 0
if __name__=='__main__':sys.exit(main())
