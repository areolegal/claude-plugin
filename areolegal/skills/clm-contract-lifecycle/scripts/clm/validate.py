# -*- coding: utf-8 -*-
# Copyright (c) Areo. All rights reserved. Licensed under the terms at https://areo.co.il/legal/terms
import datetime,re
from clm import catalog,money
from clm.doc_kind import DOC_KINDS
ISO=re.compile('[0-9]{4}-[0-9]{2}-[0-9]{2}')
LONG_DASH=re.compile('[–—]')
ROLE_SOURCES={'playbook','user','suggested','none'}
OBLIGORS={'us','them','both'}
DIRECTIONS={'given','received','policy','unknown'}
VERSION_BY={'us','them','unknown'}
COVERAGE={'found','none_found','not_checked'}
IMPACTS={'critical','material','administrative'}
TERM_KINDS={'fixed','indefinite','until_event','project','none'}
TERM_STARTS={'start','signed','other'}
RENEWAL_KINDS={'auto','option','mutual','none'}
PARTIES={'counterparty','contracting','both','unknown'}
EXIT_WHO=PARTIES|{'none'}
SIGN_PARTIES={'counterparty','contracting','unknown'}
SIGN_STATUS={'signed','blank','unknown'}
PAY_BASIS={'invoice','eom','milestone','other'}
FACT_CODES={'negotiation_stopped','other'}
VALUE_KINDS={'monthly','annual','total','max','unit'}
VALUE_BASIS={'fixed','estimate','usage'}
STANCES={'set','expressly_none'}
COC_REQUIRES={'consent','notice','termination_right','none'}
TERM_ROLES={'initial_end','extension_end','max_end','min_commitment_end'}
REQUIRED='file','sha256','doc_kind','title','counterparty','our_role','dates','events','coverage'
OBJECT_FIELDS='counterparty','our_role','dates'
LIST_FIELDS='events','coverage'
def _strings(x):
	if isinstance(x,str):yield x
	elif isinstance(x,dict):
		for(B,A)in x.items():
			if B!='quote':yield from _strings(A)
	elif isinstance(x,list):
		for A in x:yield from _strings(A)
def _in(value,allowed):A=value;return isinstance(A,str)and A in allowed
def _date(p,where,value):
	B=where;A=value
	if A is None:return
	C=str(A)
	if not ISO.fullmatch(C):p.append('%s: date %r אינו בפורמט YYYY-MM-DD'%(B,A));return
	try:datetime.date.fromisoformat(C)
	except ValueError:p.append('%s: date %r אינו תאריך קיים'%(B,A))
def _items(p,name,seq):
	A=[]
	for(B,C)in enumerate(seq):
		if isinstance(C,dict):A.append((B,C))
		else:p.append('מבנה פגום: %s[%d] אינו אובייקט'%(name,B))
	return A
def _optional_list(p,ext,name):
	A=name;B=ext.get(A)or[]
	if not isinstance(B,list):p.append('מבנה פגום: %s אינו בצורה הנכונה'%A);return[]
	return _items(p,A,B)
def _whole(p,where,v):
	if v is not None and(isinstance(v,bool)or not isinstance(v,int)or v<0):p.append('%s: חייב להיות מספר שלם לא שלילי'%where)
def _str_or_null(p,where,v):
	if v is not None and not isinstance(v,str):p.append('%s: חייב להיות מחרוזת או null'%where)
def _enum(p,where,v,allowed,nullable=True):
	if v is None and nullable:return
	if not _in(v,allowed):p.append('%s %r אינו מותר'%(where,v))
def _obj(p,ext,name):
	A=ext.get(name)
	if A is None:return
	if not isinstance(A,dict):p.append('מבנה פגום: %s אינו אובייקט'%name);return
	return A
def _check_extended(p,ext):
	B=ext;D=_obj(p,B,'term')
	if D is not None:_enum(p,'term.kind',D.get('kind'),TERM_KINDS,False);_whole(p,'term.initial_months',D.get('initial_months'));_enum(p,'term.starts_on',D.get('starts_on'),TERM_STARTS);_date(p,'term.max_end',D.get('max_end'));_str_or_null(p,'term.trigger',D.get('trigger'))
	E=_obj(p,B,'renewal')
	if E is not None:
		_enum(p,'renewal.kind',E.get('kind'),RENEWAL_KINDS,False)
		for C in('period_months','max_count','notice_days'):_whole(p,'renewal.%s'%C,E.get(C))
		_enum(p,'renewal.holder',E.get('holder'),PARTIES);_str_or_null(p,'renewal.holder_name',E.get('holder_name'))
	F=_obj(p,B,'exit')
	if F is not None:
		_enum(p,'exit.who',F.get('who'),EXIT_WHO,False)
		for C in('notice_days','min_commitment_months'):_whole(p,'exit.%s'%C,F.get(C))
		_str_or_null(p,'exit.who_name',F.get('who_name'))
	for(A,G)in _optional_list(p,B,'signatories'):
		H='signatories[%d]'%A;_enum(p,H+'.party',G.get('party'),SIGN_PARTIES,False);_enum(p,H+'.status',G.get('status'),SIGN_STATUS,False);_date(p,H,G.get('date'))
		for C in('party_name','name','role'):_str_or_null(p,'%s.%s'%(H,C),G.get(C))
	I=_obj(p,B,'jurisdiction')
	if I is not None:
		if I.get('exclusive')is not None and not isinstance(I['exclusive'],bool):p.append('jurisdiction.exclusive חייב להיות true, false או null')
		_str_or_null(p,'jurisdiction.court',I.get('court'))
	J=_obj(p,B,'payment_terms')
	if J is not None:_whole(p,'payment_terms.days',J.get('days'));_enum(p,'payment_terms.basis',J.get('basis'),PAY_BASIS);_str_or_null(p,'payment_terms.text',J.get('text'))
	for(A,K)in _optional_list(p,B,'facts'):
		_enum(p,'facts[%d].code'%A,K.get('code'),FACT_CODES,False)
		if not isinstance(K.get('label'),str)or not K['label'].strip():p.append('facts[%d].label: חייב להיות מחרוזת לא ריקה'%A)
		_str_or_null(p,'facts[%d].value'%A,K.get('value'))
	for(A,L)in _optional_list(p,B,'commercials'):
		_enum(p,'commercials[%d].value_kind'%A,L.get('value_kind'),VALUE_KINDS);_enum(p,'commercials[%d].basis'%A,L.get('basis'),VALUE_BASIS);_enum(p,'commercials[%d].operation'%A,L.get('operation'),money.OPERATIONS);M=L.get('effective_date')
		if M is not None and not(isinstance(M,str)and money.ISO_DATE.match(M)):p.append('commercials[%d].effective_date: חייב להיות YYYY-MM-DD או null'%A)
def _check_key_clause_extension(p,i,c):
	A='key_clauses[%d]'%i;_enum(p,A+'.bound_party',c.get('bound_party'),PARTIES);_enum(p,A+'.stance',c.get('stance'),STANCES);_str_or_null(p,A+'.bound_party_name',c.get('bound_party_name'));B=c.get('norm')
	if B is None:return
	if not isinstance(B,dict):p.append('מבנה פגום: %s.norm אינו אובייקט'%A);return
	_date(p,A+'.norm.until',B.get('until'));_enum(p,A+'.norm.requires',B.get('requires'),COC_REQUIRES);_whole(p,A+'.norm.months',B.get('months'))
def _check(ext):
	B=ext;A=[]
	if not isinstance(B,dict):return['מבנה פגום: השורש אינו אובייקט']
	K,L=catalog.load_events(),catalog.load_key_clauses()
	for C in REQUIRED:
		if C not in B:A.append('חסר שדה חובה: %s'%C)
	if A:return A
	for C in OBJECT_FIELDS:
		if not isinstance(B[C],dict):A.append('מבנה פגום: %s אינו בצורה הנכונה'%C)
	for C in LIST_FIELDS:
		if not isinstance(B[C],list):A.append('מבנה פגום: %s אינו בצורה הנכונה'%C)
	if A:return A
	if not _in(B['doc_kind'],DOC_KINDS):A.append('doc_kind %r אינו ברשימה הסגורה'%B['doc_kind'])
	I=B['our_role'].get('source')
	if not _in(I,ROLE_SOURCES):A.append('our_role.source %r אינו מותר'%I)
	if not _in(B.get('version_by','unknown'),VERSION_BY):A.append('version_by %r אינו מותר'%B.get('version_by'))
	if B.get('playbook_family_id')is not None and not isinstance(B['playbook_family_id'],str):A.append('playbook_family_id חייב להיות מחרוזת או null')
	for C in('signed','start','end'):_date(A,'dates.%s'%C,B['dates'].get(C))
	for(G,D)in _items(A,'events',B['events']):
		E='events[%d]'%G
		if not _in(D.get('event_code'),K):A.append('%s: event_code %r אינו בקטלוג'%(E,D.get('event_code')))
		for C in('label','clause'):
			if not D.get(C):A.append('%s: חסר %s'%(E,C))
		if not _in(D.get('consequence'),catalog.CONSEQUENCES):A.append('%s: consequence %r אינו מותר'%(E,D.get('consequence')))
		if not _in(D.get('obligor'),OBLIGORS):A.append('%s: obligor %r אינו מותר'%(E,D.get('obligor')))
		if not _in(D.get('impact'),IMPACTS):A.append('%s: impact %r אינו מותר'%(E,D.get('impact')))
		_date(A,E,D.get('date'))
		if D.get('relative')and not D.get('trigger'):A.append('%s: מועד יחסי חייב trigger'%E)
		if D.get('term_role')is not None:
			if D.get('event_code')!='term_end':A.append('%s: term_role מותר רק בתום תקופה'%E)
			elif not _in(D['term_role'],TERM_ROLES):A.append('%s: term_role %r אינו מותר'%(E,D['term_role']))
	for(G,H)in _optional_list(A,B,'guarantees'):
		if not _in(H.get('direction'),DIRECTIONS):A.append('guarantees[%d]: direction %r אינו מותר'%(G,H.get('direction')))
		_date(A,'guarantees[%d].expiry'%G,H.get('expiry'))
	for(G,F)in _optional_list(A,B,'key_clauses'):
		if not _in(F.get('clause_code'),L):A.append('key_clauses[%d]: clause_code %r אינו בקטלוג'%(G,F.get('clause_code')))
		_check_key_clause_extension(A,G,F)
	_check_extended(A,B);J=_items(A,'coverage',B['coverage']);M={A.get('category')for(B,A)in J if isinstance(A.get('category'),str)}
	if M!=set(catalog.CATEGORIES):A.append('coverage: חייב לכלול בדיוק את שש הקטגוריות')
	for(O,F)in J:
		if not _in(F.get('status'),COVERAGE):A.append('coverage: status %r אינו מותר'%F.get('status'))
		if F.get('status')in('none_found','not_checked')and not F.get('note'):A.append('coverage: %s בלי note'%F.get('category'))
	for(C,N)in(('counterparty.role',(B.get('counterparty')or{}).get('role')),('contracting_role',B.get('contracting_role'))):_str_or_null(A,C,N)
	if any(LONG_DASH.search(A)for A in _strings(B)):A.append('נמצא מקף ארוך בטקסט שאינו ציטוט (בציטוט מותר): להחליף במקף רגיל')
	return A
def check_extraction(ext):
	try:return _check(ext)
	except(TypeError,AttributeError,KeyError)as A:return['מבנה פגום: %s'%type(A).__name__]
from clm import dates as _dates
TOP=['meta','documents','agreements','events','commercials','guarantees','key_clauses','footnotes','timeline','counterparties','registers','review_queue','catalog']
AGREEMENT_STATES={'signed_not_effective','in_force','renewal_window','extended','ended','ended_early','replaced','survival_only','term_passed_unverified','status_unverified'}
END_STATUSES={'extracted','derived','not_expected','missing','not_relevant'}
OVERDUE_BUCKETS={'ours','theirs','role','outcome','old','superseded'}
HANDLING_STAGES={'request','drafting','with_cp','comments','final','internal','signing','frozen','abandoned'}
def _check_data(data):
	E=data;A,I=[],[]
	for F in TOP:
		if F not in E:A.append('חסר מפתח עליון: %s'%F)
	if A:return A,I
	W=catalog.load_events();Q={A['n']for A in E['footnotes']};R={A['id']for A in E['agreements']}
	for(X,Y)in(('מזהה הסכם',[A['id']for A in E['agreements']]),('מספר הסכם',[A['number']for A in E['agreements']]),('מזהה מועד',[A['id']for A in E['events']]),('מזהה פריט אימות',[A['id']for A in E['review_queue']if A.get('id')])):
		S,J=set(),set()
		for T in Y:(J if T in S else S).add(T)
		if J:A.append('%s כפול: %s'%(X,', '.join(sorted(str(A)for A in J))))
	H=E['registers']if isinstance(E['registers'],dict)else{}
	for F in('restrictions','restrictions_review','change_of_control','change_of_control_review'):
		if H.get(F)is not None and not isinstance(H[F],list):A.append('registers/%s: חייב להיות רשימה או null'%F)
	if H.get('restriction_details')is not None and not isinstance(H['restriction_details'],dict):A.append('registers/restriction_details: חייב להיות מילון או null')
	for K in E['documents']:
		if K['doc_kind']not in DOC_KINDS:A.append('documents/%s: doc_kind %r אינו מותר'%(K['id'],K['doc_kind']))
	for C in E['agreements']:
		B='agreements/%s'%C['number']
		if C.get('agreement_state')and C['agreement_state']not in AGREEMENT_STATES:A.append('%s: agreement_state %r אינו מותר'%(B,C['agreement_state']))
		if C.get('handling_stage')and C['handling_stage']not in HANDLING_STAGES:A.append('%s: handling_stage %r אינו מותר'%(B,C['handling_stage']))
		if bool(C.get('agreement_state'))==bool(C.get('handling_stage')):A.append('%s: חייב בדיוק אחד מ-agreement_state ו-handling_stage'%B)
		if{A.get('category')for A in C.get('coverage',[])}!=set(catalog.CATEGORIES):A.append('%s: coverage חייב לכלול את שש הקטגוריות'%B)
		L=(C.get('field_status')or{}).get('end_date')
		if L is not None and L not in END_STATUSES:A.append('%s: field_status.end_date %r אינו מותר'%(B,L))
		for U in(C.get('value')or{}).get('annual_by_currency')or{}:
			if not money.explicit_code(U):A.append('%s: מטבע %r אינו מוכר'%(B,U))
	Z={A['n']:A.get('agreementId')for A in E['footnotes']}
	def M(w,x,aid=None):
		for B in(x.get('refs')if isinstance(x,dict)else None)or[]:
			if B not in Q:A.append('%s: הפניה %s אינה קיימת בציטוטים'%(w,B))
			elif aid is not None and Z[B]!=aid:A.append('%s: הפניה %s שייכת להסכם אחר'%(w,B))
	for C in E['agreements']:
		B='agreements/%s'%C['number']
		for F in('term','renewal','exit','jurisdiction','payment_terms'):M('%s/%s'%(B,F),C.get(F),C['id'])
		for F in('signatories','facts'):
			for(N,O)in enumerate(C.get(F)or[]):M('%s/%s[%d]'%(B,F,N),O,C['id'])
	for(P,a)in(H.get('restriction_details')or{}).items()if isinstance(H.get('restriction_details'),dict)else[]:
		for(N,O)in enumerate(a or[]):M('registers/restriction_details/%s[%d]'%(P,N),O,P if P in R else None)
	for D in E['events']:
		B='events/%s'%D['id']
		if D['agreementId']not in R:A.append('%s: agreementId לא קיים'%B)
		if D['event_code']not in W:A.append('%s: event_code %r אינו בקטלוג'%(B,D['event_code']))
		if D.get('overdue_bucket')is not None and D['overdue_bucket']not in OVERDUE_BUCKETS:A.append('%s: overdue_bucket %r אינו מותר'%(B,D['overdue_bucket']))
		if D['state']not in _dates.STATES:A.append('%s: state %r אינו מותר (realized אסור)'%(B,D['state']))
		for V in D.get('refs',[]):
			if V not in Q:A.append('%s: הפניה %s אינה קיימת בציטוטים'%(B,V))
		if not D.get('refs')and not D.get('verify'):A.append('%s: מועד בלי ציטוט חייב verify'%B)
		if D['state']in('upcoming','needs_action')and not D.get('action'):A.append('%s: חסרה פעולה נדרשת'%B)
		if any(A in(D.get('action')or'')for A in _dates.GENERIC):A.append('%s: פעולה כללית אסורה'%B)
		for F in('date','act_by'):
			if D.get(F)and not ISO.match(D[F]):A.append('%s: %s אינו ISO'%(B,F))
		if not D.get('refs'):I.append('%s: טעון אימות, אין ציטוט'%B)
	if any(LONG_DASH.search(A)for A in _strings({A:E[A]for A in TOP if A!='catalog'})):A.append('נמצא מקף ארוך בנתונים מחוץ לציטוטים')
	for G in E['review_queue']:
		if G.get('kind')=='bad_extract':A.append('קובץ החילוץ של %s נפסל, וההסכם לא נכנס למאגר: %s. לתקן את קובץ החילוץ ולהריץ assemble שוב'%(G.get('source')or G.get('text'),'; '.join(G.get('detail')or[G.get('text')or''])))
		elif G.get('kind')=='not_extracted':I.append('ממתין לחילוץ: %s'%G.get('text'))
		elif G.get('kind')=='unsupported':I.append('קובץ שלא נקרא (סוג שאינו נתמך): %s'%G.get('text'))
	return A,I
def check_data(data):
	if not isinstance(data,dict):return['מבנה פגום: השורש אינו אובייקט'],[]
	try:return _check_data(data)
	except(TypeError,AttributeError,KeyError,ValueError)as A:return['מבנה פגום: %s'%type(A).__name__],[]
