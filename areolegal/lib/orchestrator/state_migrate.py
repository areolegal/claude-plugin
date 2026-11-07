# -*- coding: utf-8 -*-
# Copyright (c) Areo. All rights reserved. Licensed under the terms at https://areo.co.il/legal/terms
import copy,datetime as _dt,os,re
SCHEMA_VERSION='4.9'
REFS_VERSION='4.9'
ISO=re.compile('^\\d{4}-\\d\\d-\\d\\dT\\d\\d:\\d\\d:\\d\\d([+-]\\d\\d:\\d\\d|Z)$')
TIME_KEYS='generated_at','last_updated','produced_at','received_at','sent_at','checked_at','recorded_at'
LEGACY_STAGE={'awaiting_proposed_playbook|awaiting_playbook_builder|awaiting_builder|ממתין לרכיב הפלייבוק':'awaiting_builder'}
ROUND_STAGES='opening','response','closing'
APPROVAL_KEYS='required_by','required_approver','approval_required','approved_by','approved_at','approval_status','escalation_approver','awaiting_approval'
def _stage_for_round(n):n=int(n or 1);return'opening'if n<=1 else'response'if n==2 else'closing'
def _user_decision_from(old,fallback_kind=None):
	B=fallback_kind;A=old
	if isinstance(A,dict):C=A.get('status');D='explicit'if C in('approved','changed','rejected')else'delegated';return{'answer_kind':B or D,'answer':A.get('by')or'','recorded_at':A.get('at')or''}
	if A in('approved',True):return{'answer_kind':B or'explicit','answer':''}
	return{'answer_kind':B or'delegated','answer':''}
def _strip_approval_chain(st,log):
	D=log;B=st
	for A in B.get('clauses',[])+B.get('exception_log',[]):
		if'approval'in A:A.setdefault('user_decision',_user_decision_from(A.pop('approval')));D.append('approval -> user_decision (%s)'%A.get('clause_id',A.get('id','')))
		if'approved_by_user_in_chat'in A:F=A.pop('approved_by_user_in_chat');A.setdefault('user_decision',{'answer_kind':'explicit'if F else'delegated','answer':''});D.append('approved_by_user_in_chat -> user_decision')
	for C in B.get('deliberate_concessions',[]):
		if'approval'in C or'answer_kind'in C:C.setdefault('user_decision',_user_decision_from(C.pop('approval',None),C.pop('answer_kind',None)));D.append('ויתור: approval/answer_kind -> user_decision (%s)'%C.get('topic'))
	def E(o):
		if isinstance(o,dict):
			for A in list(o):
				if A in APPROVAL_KEYS or A=='authority_table'or A=='approval_table':o.pop(A);D.append('נמחק שדה של שרשרת אישורים: %s'%A)
				else:E(o[A])
		elif isinstance(o,list):
			for B in o:E(B)
	E(B)
	if'deliverables'in B:B.setdefault('produced_documents',[]).extend(A if isinstance(A,dict)else{'kind':'','path':A,'sha256':''}for A in B.pop('deliverables'));D.append('deliverables -> produced_documents')
def _iso(value):
	A=value
	if not A or ISO.match(str(A)):return A
	B=str(A)
	for C in('%d.%m.%Y','%Y-%m-%d','%Y-%m-%dT%H:%M:%S','%d.%m.%Y %H:%M','%d %B %Y','%B %d, %Y'):
		try:D=_dt.datetime.strptime(B,C);return D.astimezone().isoformat(timespec='seconds')
		except ValueError:continue
	return A
def migrate_state(old):
	A=copy.deepcopy(old);E=[];M=str(A.get('meta',{}).get('schema_version')or'legacy');B=A.setdefault('meta',{});G=str(B.get('round_stage',''));H=A.setdefault('positions_source',{}).setdefault('proposed_playbook',{})
	for(N,J)in LEGACY_STAGE.items():
		if re.search(N,G)and not H.get('build_state'):H['build_state']=J;E.append('build_state=%s מתוך round_stage "%s"'%(J,G))
	if H.get('build_state')=='awaiting_builder':
		for F in A.get('coverage_index',[]):
			if not F.get('decision'):F['decision']='awaiting_playbook';E.append('coverage %s: awaiting_playbook'%F.get('element_id'))
	if G not in ROUND_STAGES:B['round_stage']=_stage_for_round(B.get('round_number',1));E.append('round_stage "%s" -> %s (לפי מספר הסבב)'%(G,B['round_stage']))
	_strip_approval_chain(A,E)
	for D in('time_anchors','post_checks_done','checks_reviewed'):
		if D in B:O=B.pop(D)or[];K=A.setdefault(D,[]);K+=[A for A in O if A not in K];E.append('%s: מ-meta לשורש'%D)
	for C in A.get('meta',{}).get('received_documents',[])+A.get('meta',{}).get('sent_documents',[]):
		if'file'in C and'file_name'in C:
			if C['file']==C['file_name']or not C['file_name']:C['file_name']=C.pop('file')or C['file_name']
			else:C.pop('file')
			E.append('מפתח כפול file/file_name אוחד')
		if'received'in C:C.setdefault('received_at',C['received']);C.pop('received');E.append('מפתח כפול received/received_at אוחד')
	def I(o):
		if isinstance(o,dict):
			for(B,A)in list(o.items()):
				if B in TIME_KEYS and isinstance(A,str):
					C=_iso(A)
					if C!=A:o[B]=C;E.append('%s -> ISO'%B)
				else:I(A)
		elif isinstance(o,list):
			for D in o:I(D)
	I(A)
	for D in('last_updated','updated_by','date'):
		if D in A:
			L=A.pop(D)
			if not B.get(D)or D=='last_updated'and str(L)>str(B.get(D)):B[D]=L
			E.append('%s: מהשורש ל-meta'%D)
	from orchestrator import state_builder as P
	for F in A.get('clauses',[]):
		F.setdefault('decided_in_round',int(B.get('round_number')or 1))
		if str(F.get('decision_code')or'').startswith('R')and'rejections'not in F:F['rejections']=[{'round':F['decided_in_round'],'by':'us'}]
	P.normalize_statuses(A,E);B['schema_version']=SCHEMA_VERSION;B['refs_version']=REFS_VERSION;B['migrated_from']=M;return A,E
def history_path(transaction_dir,old_state,when=None):A=when;A=A or _dt.datetime.now().astimezone();B=str(old_state.get('meta',{}).get('schema_version')or'legacy');return os.path.join(transaction_dir,'history','negotiation_state.%s.v%s.json'%(A.strftime('%Y%m%dT%H%M%S'),B))
def non_iso_timestamps(state):
	C=[]
	def B(o):
		if isinstance(o,dict):
			for(D,A)in o.items():
				if D in TIME_KEYS and isinstance(A,str)and A and not ISO.match(A):C.append((D,A))
				else:B(A)
		elif isinstance(o,list):
			for E in o:B(E)
	B(state);return C
