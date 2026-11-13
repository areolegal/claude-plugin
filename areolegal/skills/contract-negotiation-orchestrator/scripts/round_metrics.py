#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (c) Areo. All rights reserved. Licensed under the terms at https://areo.co.il/legal/terms
BODY_OPS='replace','replace_span','insert_paragraph','delete_paragraph'
CLAUSE_TYPES='clause','sub_clause','definition'
DECIDED='tracked_change','comment_only','for_call'
REJECTED='our_rejected','their_rejected_our_insert'
def _dlist(decisions):A=decisions;B=A.get('decisions')if isinstance(A,dict)else A;return[A for A in B or()if isinstance(A,dict)]
def _ids(v):return[str(A)for A in v or()if isinstance(A,str)and A.strip()]
def entry(state,decisions,rnd,with_outcome=True):
	M=state;B=rnd;N,O=[],set()
	for C in _dlist(decisions):
		if C.get('op')not in BODY_OPS:continue
		F=C.get('ladder_step')if isinstance(C.get('ladder_step'),int)else 0
		for G in _ids(C.get('rule_ids')):
			if(G,F)in O:continue
			O.add((G,F));N.append({'rule_id':G,'step':F,'floor':bool(C.get('ladder_floor'))})
	D={'round':B,'applied':N}
	if with_outcome and B>1:
		E,H,P=set(),set(),set()
		for I in(M or{}).get('clauses')or():
			if not isinstance(I,dict):continue
			J=set(I.get('last_round_changes')or());K=set(_ids(I.get('rule_ids')))
			if J&set(REJECTED):H|=K
			elif'our_accepted_partial'in J:P|=K
			elif'our_accepted'in J:E|=K
		D.update(outcome_of_round=B-1,accepted=sorted(E),rejected=sorted(H-E),partial=sorted(P-E-H))
	L=[]
	for A in(M or{}).get('coverage_index')or():
		if not isinstance(A,dict)or A.get('element_type')not in CLAUSE_TYPES or _ids(A.get('rule_ids')):continue
		if A.get('decision')in DECIDED and int(A.get('round_decided')or B)==B:L.append(str(A.get('location')or A.get('element_id')or''))
	D['no_rule']=len(L);D['no_rule_where']=[A for A in L if A][:20];return D
def update(state,new):
	A=new;C=state.setdefault('meta',{});B=[A for A in C.get('metrics_log')or()if isinstance(A,dict)];D=next((B for B in B if B.get('round')==A['round']),None)
	if D and'outcome_of_round'in D and'outcome_of_round'not in A:
		for E in('outcome_of_round','accepted','rejected','partial'):A[E]=D.get(E)
	B=[B for B in B if B.get('round')!=A['round']]+[A];C['metrics_log']=sorted(B,key=lambda x:x.get('round')or 0);return C['metrics_log']
