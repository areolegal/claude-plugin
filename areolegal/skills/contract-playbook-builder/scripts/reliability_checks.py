#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (c) Areo. All rights reserved. Licensed under the terms at https://areo.co.il/legal/terms
'אמינות הפלייבוק, בקוד (הערות ענבל, 12.11.2026, "לפי סקיל" 6.1-6.10).'
import argparse,io,json,os,re,sys
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
import evidence_kind as EK
try:import areo_lib;from playbook import status as S
except ImportError:S=None
NON_DOC='areo_proposal','market_standard','client_answer',''
SIGNED='signed','agreement','amendment'
def _norm(s):return re.sub('\\s+',' ',str(s or'')).strip()
def _sid(v):return str(v).split('#',1)[0].strip()if isinstance(v,str)else''
def quote_found(doc,ref,quote):
	A=quote;D=EK._segments(A);E=[A for A in doc.get('paragraphs')or()if isinstance(A,dict)];B=EK._para_of(doc,ref,A)
	for C in([B]if B else[])+E:
		F=EK.norm(C.get('text',''))+' '+EK.norm(C.get('text_reject_all',''))
		if all(A in F for A in D):return True
	return False
def corpus_count(model):
	B=model;A=0
	if S is not None:
		try:A=int(S.company_agreements_counted(B))
		except Exception:A=0
	return A or sum(1 for A in B.get('source_log')or()if isinstance(A,dict)and A.get('included')is not False and A.get('doc_role')in SIGNED)
def find_inventory(model_path,explicit=None):
	G=explicit;F=model_path;A=[G]if G else[];H=os.path.dirname(os.path.abspath(F));A.append(os.path.join(H,'clause-inventory.json'))
	try:
		with io.open(F,encoding='utf-8')as B:C=(json.load(B).get('coverage')or{}).get('inventory_ref')or''
	except(OSError,ValueError):C=''
	if C:
		D=H
		for I in range(4):A.append(os.path.join(D,C));D=os.path.dirname(D)
	for E in A:
		if E and os.path.isfile(E):
			try:
				with io.open(E,encoding='utf-8')as B:return json.load(B)
			except(OSError,ValueError):return
def addressed_by(inventory):
	B=inventory;C={};D=(B or{}).get('units')if isinstance(B,dict)else B
	for A in D or():
		if isinstance(A,dict)and A.get('rule_id'):C.setdefault(str(A['rule_id']),set()).add(_sid(A.get('source_ref')or A.get('source_id')))
	return C
def apply(model,extract=None,inventory=None):
	T=extract;A=model;D,M=[],[];b=addressed_by(inventory);J={str(A.get('source_id')):A for A in A.get('source_log')or()if isinstance(A,dict)};U=EK.doc_index(T)if T else{};N=corpus_count(A);A['corpus_count']=N;c=set((A.get('backtest')or{}).get('holdout_ids')or());O=0
	for B in A.get('rules')or[]:
		if not isinstance(B,dict):continue
		F=B.get('rule_id')or'?';K=[A for A in B.get('evidence')or()if isinstance(A,dict)]
		for G in K:
			C,H=G.get('quote'),_sid(G.get('source_ref')or G.get('source_id'))
			if not C or not H:continue
			V=EK.doc_for_source(J.get(H),U)if U else None
			if V is None:O+=1;continue
			W=quote_found(V,G.get('source_ref'),C);G['quote_verified']=W
			if not W:D.append(('CITATION_NOT_FOUND','%s: הציטוט %s לא נמצא מילה במילה בהסכם %s'%(F,G.get('evidence_id')or'',H)))
			if H in c:D.append(('BACKTEST_LEAK','%s: מצטט את %s, שהוחזק בצד לבדיקה החוזרת'%(F,H)))
		P={_sid(A.get('source_ref')or A.get('source_id'))for A in K if A.get('track')in('green','yellow','red')and A.get('quote_verified')is not False};P={A for A in P if A in J};d=({_sid(A.get('source_ref')or A.get('source_id'))for A in K}|b.get(str(F),set()))&set(J);B['evidence_count_computed']={'n':len(P),'total':N,'absent':max(N-len(d),0)};X=[];e=B.get('traffic_light')or{}
		for Q in('green','yellow','red'):
			E=e.get(Q)
			if not isinstance(E,dict)or not(E.get('position')or E.get('proposed_clause')):continue
			Y=any(A.get('track')==Q and _sid(A.get('source_ref')or A.get('source_id'))in J and A.get('quote_verified')is not False for A in K)or bool(E.get('basis_refs'))
			if str(E.get('basis')or'')not in NON_DOC and not Y:D.append(('BASIS_NOT_DERIVED','%s/%s: מסומן כנשען על המסמכים, ואין לו ציטוט או מקור'%(F,Q)))
			E['basis_label']='own'if Y else'areo_proposal';X.append(E['basis_label'])
		B['mixed_basis']=len(set(X))>1;Z=_norm(B.get('policy_ref'))
		if not Z or Z==F:
			a=_norm(B.get('topic_name')or B.get('clause_issue'))
			if a:B['policy_ref']=a
			else:D.append(('POLICY_REF_MISSING','%s: אין שם נושא להפניית המדיניות'%F))
	R={}
	for C in A.get('validation_queue')or[]:
		if not isinstance(C,dict)or C.get('status')=='closed':continue
		I=_norm(C.get('why'))
		if not I or not C.get('severity'):D.append(('QUEUE_INCOMPLETE','%s: פריט בתור בלי נימוק או בלי חומרה'%(C.get('id')or'?')))
		if I:
			if I in R:D.append(('QUEUE_GENERIC_REASON','%s ו-%s: אותו נימוק מילה במילה'%(R[I],C.get('id')or'?')))
			else:R[I]=C.get('id')or'?'
	L=A.get('backtest')
	if isinstance(L,dict)and L.get('results'):S=[A for A in L['results']if isinstance(A,dict)];L['red_rate']=round(sum(1 for A in S if A.get('track')=='red')/len(S),3)if S else None
	if O:M.append('%d ציטוטים לא נבדקו מילה במילה: אין להם מסמך בקובץ החילוץ'%O)
	A['reliability_findings']=[{'code':A,'text':B}for(A,B)in D];A['reliability_notes']=M;return A,D,M
def main(argv=None):
	sys.stdout.reconfigure(encoding='utf-8');B=argparse.ArgumentParser(description=__doc__.split('\n')[0]);B.add_argument('--model',required=True);B.add_argument('--extract');B.add_argument('--inventory');B.add_argument('--dry-run',action='store_true');A=B.parse_args(argv)
	if not os.path.isfile(A.model):print('המודל אינו קיים: %s'%A.model);return 2
	with io.open(A.model,encoding='utf-8')as E:C=json.load(E)
	F=EK.find_extract(C,A.model,A.extract);C,D,G=apply(C,F,find_inventory(A.model,A.inventory))
	if not A.dry_run:
		with io.open(A.model,'w',encoding='utf-8')as E:json.dump(C,E,ensure_ascii=False,indent=1)
	for(H,I)in D:print('%s %s'%(H,I))
	for J in G:print('הערה: %s'%J)
	print('אמינות: %s · מאגר קנוני: %d'%('עבר'if not D else'%d ממצאים'%len(D),C['corpus_count']));return 3 if D else 0
if __name__=='__main__':sys.exit(main())
