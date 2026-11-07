# -*- coding: utf-8 -*-
# Copyright (c) Areo. All rights reserved. Licensed under the terms at https://areo.co.il/legal/terms
import copy
EFFECTIVENESS='effective','partial','not_effective'
PROPOSAL_STATUS='pending','sent','rejected'
STATE_LABEL={'current':'נוכחי','proposed':'בקרה מוצעת','agreed':'מוסכם'}
STATE_LABEL_EN={'current':'Current','proposed':'Proposed control','agreed':'Agreed'}
def lvl(score):A=score;return'critical'if A>=16 else'high'if A>=9 else'medium'if A>=4 else'low'
def _score(block):A=(block or{}).get('score');return A if isinstance(A,(int,float))and not isinstance(A,bool)else None
def has_states(r):return isinstance(r.get('states'),dict)
def risk_state(r):
	A=r.get('states')if has_states(r)else None
	if not A:return'current'
	if A.get('agreed'):return'agreed'
	if[A for A in A.get('proposed')or[]if A.get('status')in('pending','sent')]:return'proposed'
	return'current'
def current_score(r):B=r.get('states')or{};A=_score(B.get('current'));return A if A is not None else _score(r.get('inherent'))
def effective_score(r):
	if not has_states(r):B=_score(r.get('residual'));return B if B is not None else _score(r.get('inherent'))
	A=r['states'].get('agreed')or{}
	if A and _score(A)is not None and A.get('acceptance_evidence')and A.get('effectiveness')in EFFECTIVENESS:return _score(A)
	return current_score(r)
def derive_levels(data):
	for A in data.get('risks')or[]:
		if not has_states(A):continue
		B=effective_score(A)
		if B is not None:A['severity_level']=lvl(B)
		A['exposure_state']=risk_state(A)
	return data
def state_counts(data):
	A={'current':0,'proposed':0,'agreed':0}
	for B in data.get('risks')or[]:A[risk_state(B)]+=1
	return A
def identity(r):A=lambda k:' '.join(str(r.get(k)or'').split()).strip().lower();return A('event'),A('impact'),A('control_ref')
def check(data):
	B,M=[],[];F={}
	for C in data.get('risks')or[]:
		A=C.get('id')or C.get('risk_no')
		if C.get('event')or C.get('impact'):
			if not(C.get('event')and C.get('impact')):B.append('%s: צריך גם event וגם impact'%A)
			G=identity(C)
			if G in F:B.append('%s: אותו אירוע, השפעה ובקרה כמו %s; אלה סיכון אחד'%(A,F[G]))
			F[G]=A
		if not has_states(C):
			if any((A or{}).get('basis')=='proposed_text'for A in C.get('controls')or[]):M.append('%s: בקרה מוצעת במרשם בלי states נחשבת נוכחית; יש להעביר ל-states.proposed'%A)
			continue
		H=C['states'];I=H.get('current')
		if not isinstance(I,dict)or _score(I)is None or not I.get('version'):B.append('%s: states.current דורש version ו-score'%A)
		for O in C.get('controls')or[]:
			if(O or{}).get('basis')=='proposed_text':B.append('%s: בקרה מוצעת נרשמת ב-states.proposed ולא ב-controls עם proposed_text'%A)
		J=set()
		for E in H.get('proposed')or[]:
			if not E.get('id')or E['id']in J:B.append('%s: לכל הצעה מזהה ייחודי'%A)
			J.add(E.get('id'))
			if E.get('status')not in PROPOSAL_STATUS:B.append('%s: סטטוס הצעה חייב להיות אחד מ-%s (קבלה נרשמת ב-agreed)'%(A,'/'.join(PROPOSAL_STATUS)))
			if not E.get('control')or not E.get('markup_version'):B.append('%s: הצעה דורשת control ו-markup_version'%A)
		D=H.get('agreed');N=current_score(C)
		if D:
			if not D.get('accepted_version')or not D.get('acceptance_evidence'):B.append('%s: מצב מוסכם דורש accepted_version ו-acceptance_evidence'%A)
			if D.get('effectiveness')not in EFFECTIVENESS:B.append('%s: מצב מוסכם דורש effectiveness (%s)'%(A,'/'.join(EFFECTIVENESS)))
			if _score(D)is None:B.append('%s: מצב מוסכם דורש score שהוערך'%A)
			elif D.get('effectiveness')=='not_effective'and N is not None and _score(D)<N:B.append('%s: בקרה לא אפקטיבית אינה מורידה את הציון'%A)
			if D.get('proposal_id')and D['proposal_id']not in J:B.append('%s: proposal_id אינו מפנה להצעה'%A)
		K=_score(C.get('residual'));L=effective_score(C)
		if K is not None and L is not None and K!=L:B.append('%s: residual.score (%s) שונה מהציון שבתוקף (%s); בקרה מוצעת אינה מורידה'%(A,K,L))
	return B,M
def apply_acceptance(data,accepted_version,evidence_by_risk):
	C=copy.deepcopy(data)
	for B in C.get('risks')or[]:
		A=evidence_by_risk.get(B.get('id'))
		if not A or not has_states(B):continue
		B['states']['agreed']={'accepted_version':accepted_version,'acceptance_evidence':A.get('acceptance_evidence'),'proposal_id':A.get('proposal_id'),'effectiveness':A.get('effectiveness'),'effectiveness_note':A.get('effectiveness_note'),'score':A.get('score')}
		if B.get('residual')is not None and A.get('score')is not None:B['residual']['score']=A['score']
	return C
