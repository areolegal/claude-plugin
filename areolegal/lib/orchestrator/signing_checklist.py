# -*- coding: utf-8 -*-
# Copyright (c) Areo. All rights reserved. Licensed under the terms at https://areo.co.il/legal/terms
LEGAL_NAME={'he':'השם הרשום של הלקוחה, כפי שהוא ברשם החברות','en':"The client's registered name, as it appears in the companies register"}
LEGAL_NAME_EN={'he':'השם הרשום של הלקוחה באנגלית (organization_name_en), להסכם באנגלית','en':"The client's registered English name (organization_name_en), for an English agreement"}
MANUAL_CHECKS='entity_names','registration_numbers','signatories_authority','dates','annexes','no_leftovers','cross_references'
ITEM_LABELS={'he':{'signing_blank':'שדה ריק לשלב החתימה','their_placeholder':'מציין מקום של הצד שכנגד','registered_legal_name':'השם הרשום של הלקוחה','annex':'נספח שלא צורף','legal_review':'בדיקה משפטית פתוחה','manual_check':'בדיקה בקריאה שנכשלה','silent_change':'שינוי שלא סומן, בלי הכרעה','open_clause':'סעיף שלא הוסכם','talking_point':'נקודה לשיחה שלא נסגרה'},'en':{'signing_blank':'Field left blank for signing','their_placeholder':"Counterparty's placeholder",'registered_legal_name':"Client's registered name",'annex':'Annex not attached','legal_review':'Open legal review','manual_check':'Check by reading that failed','silent_change':'Unmarked change without a decision','open_clause':'Clause not agreed','talking_point':'Talking point not closed'}}
STATUS={'he':{'open':'פתוח','closed':'סגור','passed':'עובר: כן','failed':'עובר: לא. העותק לחתימה אינו מופק'},'en':{'open':'Open','closed':'Closed','passed':'Passed: yes','failed':'Passed: no. The signing copy is not produced'}}
def _lang(lang):return'en'if str(lang or'').lower()[:2]=='en'else'he'
def parse_manual(values):
	C=[]
	for B in values or():
		if isinstance(B,dict):A,D=B.get('check'),B.get('detail')or''
		else:A,E,D=str(B).partition('=')
		A=(A or'').strip()
		if A not in MANUAL_CHECKS:raise ValueError('בדיקה לא מוכרת: %r (אחת מ: %s)'%(A,', '.join(MANUAL_CHECKS)))
		C.append({'check':A,'detail':D.strip()})
	return C
def build_signing_checklist(gate_info,state=None,profile=None,register=None,decisions=None,lang='he',manual=None):
	G=gate_info;D=lang;B,L=state or{},profile or{};D=_lang(D);O=_lang((G or{}).get('lang')or(B.get('meta')or{}).get('lang'));A=[];M=(G or{}).get('placeholders',{}).get('signing_blanks',[])
	for(P,Q)in(B.get('entity_details')or{}).items():
		if(Q or{}).get('status')=='signing_blank':A.append({'item':'signing_blank','detail':P,'status':'open'})
	if M and not any(A['item']=='signing_blank'for A in A):A.append({'item':'signing_blank','detail':'unknown','count':len(M),'status':'open'})
	for F in(G or{}).get('placeholders',{}).get('theirs',[]):A.append({'item':'their_placeholder','text':F.get('text'),'status':'open'})
	if not str(L.get('organization_name')or'').strip():A.append({'item':'registered_legal_name','status':'open','text':LEGAL_NAME[D]})
	elif O=='en'and not str(L.get('organization_name_en')or'').strip():A.append({'item':'registered_legal_name','status':'open','text':LEGAL_NAME_EN[D]})
	for H in B.get('open_items',[]):
		if H.get('kind')=='annex'and H.get('status')!='done':A.append({'item':'annex','text':H.get('item'),'status':'open'})
	from orchestrator.state_builder import unresolved_silent_changes as R,open_point_clauses as S
	for F in R(B,None)if B.get('meta')else():A.append({'item':'silent_change','detail':F.get('clause')or F.get('id'),'status':'open'})
	for E in B.get('clauses',[]):
		if E.get('status')in('STUCK','WALK-AWAY','OPENED'):A.append({'item':'open_clause','clause_id':E.get('clause_id'),'detail':'%s (%s)'%(E.get('contract_ref')or E.get('clause_id'),E['status']),'status':'open'})
	T=S(B);U={A.get('clause_id')for A in B.get('clauses',[])if A.get('status')=='CLOSED'}
	for C in B.get('talking_points')or():
		if not isinstance(C,dict)or C.get('status')in('closed_in_call','closed'):continue
		N=str(C.get('id')or'');I=list(C.get('clause_ids')or())or([N.split(':',2)[2].split('#')[0]]if N.startswith('auto:')else[])
		if I and any(A in T and A not in U for A in I)or not I and C.get('source')!='auto':A.append({'item':'talking_point','detail':C.get('topic')or C.get('text')or C.get('id'),'status':'open'})
	for J in parse_manual(manual):A.append({'item':'manual_check','check':J['check'],'detail':J['detail']or J['check'],'status':'open'})
	for K in A:K['label']=ITEM_LABELS[D].get(K['item'],K['item'])
	return{'checks':A,'passed':not any(A['status']=='open'for A in A)}
def render_lines(res,lang=None):
	B=lang;B=_lang(B);C=STATUS[B];D=[]
	for A in res.get('checks')or[]:E=A.get('detail')or A.get('text')or A.get('clause_id')or'';F=A.get('label')or ITEM_LABELS[B].get(A.get('item'),A.get('item'));D.append('  [%s] %s%s'%(C['open']if A.get('status')=='open'else C['closed'],F,': %s'%E if E else''))
	D.append(C['passed']if res.get('passed')else C['failed']);return D
