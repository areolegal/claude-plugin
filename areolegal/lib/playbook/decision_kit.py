# -*- coding: utf-8 -*-
# Copyright (c) Areo. All rights reserved. Licensed under the terms at https://areo.co.il/legal/terms
import re
ANATOMY='obligor','beneficiary','trigger','subject','conditions','duration','exceptions','consequence'
ANATOMY_HE={'obligor':'מי חב','beneficiary':'מי מוגן','trigger':'האירוע המפעיל','subject':'על מה','conditions':'תנאים','duration':'משך ושרידות','exceptions':'חריגים','consequence':'התוצאה'}
ANATOMY_EN={'obligor':'Who is bound','beneficiary':'Who is protected','trigger':'Trigger','subject':'Subject','conditions':'Conditions','duration':'Duration and survival','exceptions':'Exceptions','consequence':'Consequence'}
TRACKS='green','yellow','red'
SAME={'כמו בירוק','same','same as green','=','as green'}
DIRECTIONS='higher_better','lower_better','binary'
NEAREST='green','yellow','red'
IF_SILENT_LABELS='contract_mechanism','legal_review_required','areo_anchor','statute_text'
MIN_GREEN_COMPONENTS=5
KIT_WORD_BUDGET=200
STRICT_FROM=3,4
SUBSTANTIAL='critical','high'
VAGUE='סביר','סבירה','מקובל','מקובלת','בהקדם','בהקדם האפשרי','בזמן סביר','ככל הניתן','reasonable','reasonably','promptly','customary','as soon as possible','without undue delay','in a timely manner'
FORBIDDEN_EXTERNAL='מדיניות','פלייבוק','קו אדום','קווים אדומים','נסיגה','רצפה','מדרגה','policy','playbook','red line','fallback','floor','walk away','walk-away'
MARKET_WORDS='מקובל בשוק','מקובלת בשוק','נהוג בשוק','market standard','market practice'
def _s(v):return v.strip()if isinstance(v,str)else''
def _version(model):B=model or{};C=B.get('schema_version')or(B.get('produced_with')or{}).get('skill_version')or'';A=re.match('\\s*(\\d+)\\.(\\d+)',str(C));return(int(A.group(1)),int(A.group(2)))if A else(0,0)
def strict_for(model):return _version(model)>=STRICT_FROM
def substantial(rule):return(rule or{}).get('importance')in SUBSTANTIAL
def anatomy_of(rule,track):
	B=track;C=(rule or{}).get('clause_anatomy')or{};E=C.get('green')if isinstance(C.get('green'),dict)else{};G=C.get(B)if isinstance(C.get(B),dict)else{};F={}
	for D in ANATOMY:
		A=G.get(D)if B!='green'else E.get(D)
		if B!='green'and(A is None or _s(A).lower()in SAME):A=E.get(D)
		if _s(A):F[D]=_s(A)
	return F
def _same_marker(v):return _s(v).lower()in SAME
def _param_ids(rule):return{A.get('id')for A in(rule or{}).get('parameters')or()if isinstance(A,dict)and A.get('id')}
def _ref_ok(ref,rule):
	A=_s(ref)
	if not A:return False
	if A.startswith('anatomy.'):A=A[len('anatomy.'):]
	if A in ANATOMY:return True
	if A.startswith('param:'):A=A[len('param:'):]
	return A in _param_ids(rule)
def _items(v):return[A for A in v or()if A]
def _text(x):
	if isinstance(x,dict):return' '.join(_s(x.get(A))for A in('test','text','signal','op','value')if x.get(A)is not None)
	return _s(x)if isinstance(x,str)else str(x)
def _vague(text):B=' '+text.lower()+' ';return[A for A in VAGUE if' '+A+' 'in B or' '+A+','in B or' '+A+'.'in B]
def forbidden_external(text,market_ran=False):
	A=_s(text).lower();B=[B for B in FORBIDDEN_EXTERNAL if B in A]
	if not market_ran:B+=[B for B in MARKET_WORDS if B in A]
	return B
def _interest_lines(model):
	A=((model or{}).get('scope_summary')or{}).get('business_interest_brief')
	if isinstance(A,list):return[A for A in A if A]
	if isinstance(A,str):return[A for A in A.splitlines()if A.strip()]
	return[]
def param_track(param,value):
	D=value;A=param
	if not isinstance(A,dict):return'undecided',None
	E=A.get('direction');B=A.get('green')
	if E=='binary':
		if D is None:return'undecided',None
		return('green',None)if bool(D)==bool(B)else('red',None)
	try:F,B=float(D),float(B)
	except(TypeError,ValueError):return'undecided',None
	C=(lambda a,b:a>=b)if E=='higher_better'else(lambda a,b:a<=b)if E=='lower_better'else None
	if C is None:return'undecided',None
	if C(F,B):return'green',None
	for(H,I)in enumerate(A.get('yellow_steps')or(),1):
		try:
			if C(F,float(I)):return'yellow',H
		except(TypeError,ValueError):continue
	G=A.get('floor')
	try:
		if G is not None and C(F,float(G)):return'yellow',len(A.get('yellow_steps')or())or 1
	except(TypeError,ValueError):pass
	return'red',None
def kit_findings(rule,model=None,strict=None):
	X=strict;I=model;B=rule;B=B or{}
	if X is None:X=strict_for(I)
	v=X and substantial(B);F='error'if v else'warning';w=B.get('rule_id')or B.get('id')or'?';Y=[]
	def A(level,code,msg):Y.append((level,code,'%s: %s'%(w,msg)))
	J=B.get('clause_anatomy');x=any(B.get(A)for A in('clause_anatomy','parameters','match_tests','red_signals','purpose_for_company','external_rationale'))
	if not x:
		if substantial(B):A(F,'missing','no decision kit (clause_anatomy, parameters, match_tests, purpose_for_company)')
		return Y
	R=anatomy_of(B,'green')
	if substantial(B)and len(R)<MIN_GREEN_COMPONENTS:A(F,'anatomy_thin','green clause_anatomy has %d of %d components (at least %d in a critical or high rule)'%(len(R),len(ANATOMY),MIN_GREEN_COMPONENTS))
	S=[A for A in B.get('parameters')or()if isinstance(A,dict)]
	if isinstance(J,dict):
		for C in('yellow','red'):
			T=J.get(C)if isinstance(J.get(C),dict)else{};L=any(_s(T.get(A))and not _same_marker(T.get(A))and _s(T.get(A))!=R.get(A)for A in ANATOMY)
			if C=='yellow':L=L or any(A.get('yellow_steps')for A in S)
			else:L=L or any(A.get('red_beyond')not in(None,'')for A in S)
			if T and not L:A(F,'track_same_as_green','the %s track differs from green in no component and no parameter'%C)
	e=set()
	for D in S:
		E=D.get('id')or'?'
		if E in e:A('error','param_duplicate','parameter %s appears twice'%E)
		e.add(E)
		if D.get('direction')not in DIRECTIONS:A('error','param_direction','parameter %s direction must be one of %s'%(E,', '.join(DIRECTIONS)))
		if D.get('direction')!='binary'and not _s(D.get('unit')):A('error','param_unit','parameter %s has no unit'%E)
		if D.get('green')in(None,''):A('error','param_green','parameter %s has no green value'%E)
		if not _s(D.get('source')):A(F,'param_source','parameter %s has no source (quotation, client answer, market, Areo proposal)'%E)
		f=D.get('yellow_steps')or[]
		if D.get('direction')in('higher_better','lower_better')and f:
			try:
				g=[float(D['green'])]+[float(A)for A in f];y=all(A>=B if D['direction']=='higher_better'else A<=B for(A,B)in zip(g,g[1:]))
				if not y:A('error','param_steps_order','parameter %s yellow_steps do not move away from green in order'%E)
			except(TypeError,ValueError):A('error','param_steps_value','parameter %s has a non-numeric step'%E)
	H=B.get('match_tests')or{};h=B.get('traffic_light')or{}
	if substantial(B)and not(isinstance(H,dict)and any(H.get(A)for A in TRACKS)):A(F,'match_tests_missing','no match_tests')
	for C in TRACKS:
		i=H.get(C)if isinstance(H,dict)and isinstance(H.get(C),dict)else{};j=_s((h.get(C)or{}).get('position'))if isinstance(h.get(C),dict)else''
		for Z in('required','forbidden'):
			for M in _items(i.get(Z)):
				N=M.get('ref')if isinstance(M,dict)else None
				if not _ref_ok(N,B):A('error','test_unanchored','match_tests.%s.%s item points to no component or parameter'%(C,Z))
				K=_text(M);k=_vague(K)
				if k and not(isinstance(M,dict)and _s(M.get('param'))):A('error','test_vague','match_tests.%s.%s uses %s without a parameter that defines it'%(C,Z,', '.join(k)))
				if j and _s(K)==j:A('error','test_repeats_position','match_tests.%s repeats the position wording'%C)
		for l in _items(i.get('parameter_conditions')):
			if not(isinstance(l,dict)and _s(l.get('param'))in _param_ids(B)):A('error','test_param_unknown','match_tests.%s.parameter_conditions names an unknown parameter'%C)
	O=B.get('undecided_zone')
	if(isinstance(H,dict)and any(H.get(A)for A in TRACKS))and not(_s(O)or isinstance(O,dict)and _s(O.get('when'))):A(F,'undecided_zone_missing','match_tests without an undecided_zone (when a partial match goes to the lawyer)')
	if isinstance(O,dict)and O.get('nearest_track')not in(None,'')+NEAREST:A('error','undecided_zone_track','undecided_zone.nearest_track must be green, yellow or red')
	m=[A for A in B.get('red_signals')or()if isinstance(A,dict)];n=set()
	for P in m:
		if not _ref_ok(P.get('ref'),B):A('error','signal_unanchored','red signal %s points to no component or parameter'%(P.get('id')or'?'))
		else:n.add(_s(P.get('ref')).replace('anatomy.','').replace('param:',''))
		if not _s(P.get('remedy')):A('error','signal_no_remedy','red signal %s has no remedy wording'%(P.get('id')or'?'))
	if isinstance(J,dict)and isinstance(J.get('red'),dict)and m:
		for G in ANATOMY:
			a=J['red'].get(G)
			if _s(a)and not _same_marker(a)and _s(a)!=R.get(G)and G not in n:A('warning','red_component_uncovered','the red track changes %s and no red signal covers it'%G)
	Q=B.get('purpose_for_company')if isinstance(B.get('purpose_for_company'),dict)else{}
	if substantial(B):
		for G in('interest_ref','protected_asset','failure_scenario'):
			if not _s(Q.get(G)):A(F,'purpose_'+G,'purpose_for_company.%s is empty'%G)
	N=_s(Q.get('interest_ref'));o=_interest_lines(I)
	if N:
		p=re.fullmatch('I([1-9])',N)
		if not p:A('error','interest_ref_form','purpose_for_company.interest_ref must be I1 to I5')
		elif o and int(p.group(1))>len(o):A('error','interest_ref_unknown','purpose_for_company.interest_ref %s has no line in business_interest_brief'%N)
	q=_s(Q.get('why_this_side'));U=[B for A in((I or{}).get('scope_summary')or{}).get('company_roles')or()for B in([A]if isinstance(A,str)else[A.get('label'),A.get('role')]if isinstance(A,dict)else[])if isinstance(B,str)and B];U+=[A[1:]if A.startswith('ה')and len(A)>2 else A for A in(A.split()[-1]for A in U if len(A.split())>1)];r=_s(((I or{}).get('scope_summary')or{}).get('company_role'))or _s((I or{}).get('company_role'))
	if q and(U or r):
		if not any(A and A in q for A in U+[r]):A('warning','reverse_test',"why_this_side does not name the company's role: it may be just as true for the other side")
	b=Q.get('if_silent')
	if substantial(B)and not b:A('warning','if_silent_missing','purpose_for_company.if_silent is empty (at least the contract mechanism)')
	if isinstance(b,dict)and b.get('label')not in(None,'')+IF_SILENT_LABELS:A('error','if_silent_label','if_silent.label must be one of %s'%', '.join(IF_SILENT_LABELS))
	z=bool(((I or{}).get('market_research')or{}).get('findings'));V=B.get('external_rationale')if isinstance(B.get('external_rationale'),dict)else{};c=[('external_rationale.green',V.get('green')),('external_rationale.red',V.get('red'))];W=V.get('yellow');c+=[('external_rationale.yellow[%d]'%A,B)for(A,B)in enumerate(W if isinstance(W,list)else[W]if W else[])]
	for(A0,s)in enumerate(Q.get('typical_moves')or()):
		if isinstance(s,dict):c.append(('typical_moves[%d].our_reply_external'%A0,s.get('our_reply_external')))
	A1={str(A.get('floor'))for A in S if A.get('floor')not in(None,'')}
	for(d,K)in c:
		t=forbidden_external(K,z)
		if t:A('error','external_words','%s uses %s, which may not reach the other side'%(d,', '.join(t)))
		if d.startswith(('external_rationale.green','external_rationale.yellow'))and _s(K):
			for u in A1:
				if re.search('(?<![\\d.])%s(?![\\d.])'%re.escape(u),_s(K)):A('error','external_leaks_floor','%s mentions the floor value %s'%(d,u))
	if substantial(B)and not _s(V.get('green')):A('warning','external_rationale_missing','external_rationale.green is empty')
	if substantial(B)and not B.get('post_checks'):A(F,'post_checks_missing','a critical or high rule without post_checks')
	return Y
def core_kit(rule):
	A=rule;A=A or{};C=A.get('purpose_for_company')if isinstance(A.get('purpose_for_company'),dict)else{};B={};F={B:anatomy_of(A,B)for B in TRACKS};G={'green':F['green']}
	for H in('yellow','red'):
		I={A:B for(A,B)in F[H].items()if B!=F['green'].get(A)}
		if I:G[H]=I
	if any(G.values()):B['anatomy']=G
	J=[{B:A.get(B)for B in('id','name','unit','direction','green','yellow_steps','floor','red_beyond','source')if A.get(B)not in(None,'',[])}for A in A.get('parameters')or()if isinstance(A,dict)and A.get('id')]
	if J:B['parameters']=J
	D=A.get('match_tests')
	if isinstance(D,dict)and any(D.get(A)for A in TRACKS):B['match_tests']={A:D[A]for A in TRACKS if D.get(A)}
	if A.get('undecided_zone'):B['undecided_zone']=A['undecided_zone']
	K=[{B:A.get(B)for B in('id','signal','ref','remedy')if A.get(B)}for A in A.get('red_signals')or()if isinstance(A,dict)]
	if K:B['red_signals']=K
	L={A:_s(C.get(A))for A in('interest_ref','protected_asset','failure_scenario','why_this_side')if _s(C.get(A))}
	if L:B['purpose']=L
	if _s(C.get('counterparty_interest')):B['counterparty_interest']=_s(C['counterparty_interest'])
	M=[{B:A.get(B)for B in('their_move','their_argument','our_reply_external','internal_allowance')if _s(A.get(B))}for A in C.get('typical_moves')or()if isinstance(A,dict)]
	if M:B['typical_moves']=M
	if C.get('if_silent'):B['if_silent']=C['if_silent']
	E=A.get('external_rationale')
	if isinstance(E,dict)and any(E.get(A)for A in TRACKS):B['external_rationale']={A:E[A]for A in TRACKS if E.get(A)}
	N=[A for A in A.get('sub_issues')or()if isinstance(A,dict)]
	if N:B['sub_issues']=N
	return B
def core_anatomy(kit,track):
	A=track;B=(kit or{}).get('anatomy')or{};C=dict(B.get('green')or{})
	if A!='green':C.update(B.get(A)or{})
	return C
def _words(v):
	if isinstance(v,str):return len(v.split())
	if isinstance(v,dict):return sum(_words(A)for A in v.values())
	if isinstance(v,(list,tuple)):return sum(_words(A)for A in v)
	return 0
def kit_words(kit):return _words(kit)
CORE_KIT_SCHEMA={'anatomy':{'type':'object','keys':TRACKS,'values':{'type':'object','keys':ANATOMY}},'parameters':{'type':'array','item_keys':('id','name','unit','direction','green','yellow_steps','floor','red_beyond','source'),'required':('id','direction','green')},'match_tests':{'type':'object','keys':TRACKS,'values':{'type':'object','keys':('required','forbidden','parameter_conditions')}},'undecided_zone':{'type':'string|object'},'red_signals':{'type':'array','item_keys':('id','signal','ref','remedy'),'required':('signal','ref','remedy')},'purpose':{'type':'object','keys':('interest_ref','protected_asset','failure_scenario','why_this_side')},'counterparty_interest':{'type':'string'},'typical_moves':{'type':'array','item_keys':('their_move','their_argument','our_reply_external','internal_allowance')},'if_silent':{'type':'string|object'},'external_rationale':{'type':'object','keys':TRACKS},'sub_issues':{'type':'array'}}
def check_core_kit(kit):
	G=kit;A=[]
	if G in(None,{}):return A
	if not isinstance(G,dict):return['decision_kit must be an object']
	for(B,E)in G.items():
		C=CORE_KIT_SCHEMA.get(B)
		if C is None:A.append('decision_kit.%s is not a known field'%B);continue
		F=C['type']
		if F=='object'and not isinstance(E,dict):A.append('decision_kit.%s must be an object'%B);continue
		if F=='array'and not isinstance(E,list):A.append('decision_kit.%s must be a list'%B);continue
		if F=='string'and not isinstance(E,str):A.append('decision_kit.%s must be text'%B);continue
		if'keys'in C and isinstance(E,dict):
			for(D,J)in E.items():
				if D not in C['keys']:A.append('decision_kit.%s.%s is not a known field'%(B,D))
				elif'values'in C and isinstance(J,dict):
					for K in J:
						if K not in C['values']['keys']:A.append('decision_kit.%s.%s.%s is not a known field'%(B,D,K))
		if F=='array':
			for(H,I)in enumerate(E):
				if'item_keys'in C:
					if not isinstance(I,dict):A.append('decision_kit.%s[%d] must be an object'%(B,H));continue
					for D in I:
						if D not in C['item_keys']:A.append('decision_kit.%s[%d].%s is not a known field'%(B,H,D))
					for D in C.get('required',()):
						if I.get(D)in(None,''):A.append('decision_kit.%s[%d] is missing %s'%(B,H,D))
	return A
