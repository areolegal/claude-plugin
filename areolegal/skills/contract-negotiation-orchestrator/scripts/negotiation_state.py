#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (c) Areo. All rights reserved. Licensed under the terms at https://areo.co.il/legal/terms
'פנקס העסקה: קובץ המצב של המשא ומתן, נכתב ונבדק בקוד ולא ביד.'
import argparse,copy,hashlib,json,os,re,sys
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
import areo_lib
from orchestrator import state_builder as SB,state_migrate as SM
from common import paths
LIVE='negotiation_state.json'
REJECTED='negotiation_state.rejected.json'
UPDATED_BY='orchestrator'
UNSENT_OURS='','our_unsent_response','our_draft'
CARRY_TOP='playbook_source','positions_source','profile_gap','playbook_status','strategy_summary','case_law','exception_log','clarification_questions','posture_confirmation','lawyer_overrides','sources_log','client_answers','company_representations','open_items','talking_points','commitments','packages','entity_details','question_batches','signing_checklist','playbook_resolution','silent_changes'
APPEND_TOP='deliberate_concessions','user_decisions','produced_documents'
CARRY_META='client_name','counterparty_name','contract_type','position','our_role','paper_type','lang','deal_context','sent_documents','received_documents'
FRESH_META='transaction_id','schema_version','refs_version','round_number','round_stage','generated_at','last_updated','confidential'
SAME_ROUND_TOP='time_anchors','post_checks_done','checks_reviewed','review_table','internal_summary'
EMPTY=None,'',[],{}
def load(path,what,required=True):
	A=path
	if not A:
		if required:print('חסר %s'%what);raise SystemExit(2)
		return
	if not os.path.exists(A):print('%s אינו קיים: %s'%(what,A));raise SystemExit(2)
	with open(A,encoding='utf-8')as B:return json.load(B)
def dump(path,data):
	with open(path,'w',encoding='utf-8')as A:json.dump(data,A,ensure_ascii=False,indent=1)
def sha256(path):
	A=hashlib.sha256()
	with open(path,'rb')as B:
		for C in iter(lambda:B.read(1<<16),b''):A.update(C)
	return A.hexdigest()
def doc_record(path,deal,when_key):A=os.path.relpath(os.path.abspath(path),os.path.abspath(deal)).replace('\\','/');return{'file_name':A,'sha256':sha256(path),when_key:SB.now_iso()}
def report(errors):
	for A in errors:print('  [%s] %s%s'%(A.get('code'),A.get('message'),'  (%s)'%A['where']if A.get('where')else''))
def write_checked(deal,state):
	B=state;A=deal;B.setdefault('meta',{})['updated_by']=UPDATED_BY;C=SB.validate_state(B)
	if C:dump(os.path.join(A,REJECTED),B);print('קובץ המצב אינו תקין, ולא נכתב במקום הקובץ החי (%d שגיאות):'%len(C));report(C);print('הגרסה שנדחתה: %s'%os.path.join(A,REJECTED));return 3
	dump(os.path.join(A,LIVE),B);D=os.path.join(A,REJECTED)
	if os.path.exists(D):os.remove(D)
	print('נכתב %s'%os.path.join(A,LIVE));return 0
KEEP_LISTS='rejections','reopen_log','concession_history'
def _recorded_concession(prev_list,x,key):return key=='concession_history'and isinstance(x,dict)and x.get('kind')=='counter_tighter'and any(isinstance(A,dict)and A.get('round')==x.get('round')and A.get('who')=='us'and A.get('kind')in(None,'counter_tighter')for A in prev_list or())
def merge_clauses(prev,new):
	G={A.get('clause_id'):A for A in new};E=[]
	for A in prev:
		I=A.get('clause_id')
		if I in G:
			B=G.pop(I)
			if A.get('status')=='CLOSED'and(B.get('decision_code')=='A1'or B.get('op')=='accept'):E.append(copy.deepcopy(A));continue
			if restores_agreed(A,B):
				F=copy.deepcopy(A);F['restore_agreed']={'round':B.get('decided_in_round'),'kind':'restore_agreed','silent_change':B.get('silent_change'),'op':B.get('op'),'decision_code':B.get('decision_code')}
				for C in('user_decision',):
					if B.get(C)and not F.get(C):F[C]=copy.deepcopy(B[C])
				E.append(F);continue
			if B.get('carried_from')and B.get('op')=='accept':E.append(copy.deepcopy(A));continue
			D=copy.deepcopy(A);D.update(B)
			for C in KEEP_LISTS:
				if A.get(C)or B.get(C):D[C]=copy.deepcopy(A.get(C)or[])+[B for B in B.get(C)or[]if B not in(A.get(C)or[])and not _recorded_concession(A.get(C),B,C)]
			if A.get('status')=='STUCK'and D.get('status')=='MOVING':D['status']='STUCK'
			H=A.get('legal_review_round')or(A.get('decided_in_round')if A.get('legal_review_required')else None)
			if H and D.get('legal_review_required'):D['legal_review_round']=min(int(H),int(D.get('legal_review_round')or H))
			if A.get('first_round')or A.get('decided_in_round'):D['first_round']=int(A.get('first_round')or A.get('decided_in_round'))
			if A.get('status')=='CLOSED':D['status']='MOVING'
			E.append(D)
		else:E.append(copy.deepcopy(A))
	E+=[A for A in new if A.get('clause_id')in G];return E
def restores_agreed(prev_clause,new_clause):
	B=prev_clause;A=new_clause
	if B.get('status')!='CLOSED'or A.get('decision_kind')=='accept_with_condition':return False
	C=int(A.get('decided_in_round')or 0)
	if any(isinstance(A,dict)and int(A.get('round')or 0)>=C for A in B.get('reopen_log')or()):return False
	return A.get('decision_kind')=='restore_agreed'or bool(A.get('silent_change')and A.get('op')in SB.REVERT_OPS)
def merge_value(old,new,deep=True):
	B=new;A=old
	if B in EMPTY:return copy.deepcopy(A if A is not None else B)
	if A in EMPTY:return copy.deepcopy(B)
	if isinstance(A,dict)and isinstance(B,dict):
		E=copy.deepcopy(A)
		for(D,C)in B.items():E[D]=merge_value(A.get(D),C)if deep else copy.deepcopy(C if C not in EMPTY else A.get(D,C))
		return E
	if isinstance(A,list)and isinstance(B,list):return copy.deepcopy(A)+[copy.deepcopy(B)for B in B if B not in A]
	return copy.deepcopy(B)
def tag_round(value,rnd):
	A=value
	if isinstance(A,list):return[dict(A,round=A.get('round')or rnd)if isinstance(A,dict)else A for A in A]
	return copy.deepcopy(A)
def carry_over(prev,st,same_round=False,gate=None,text_status_given=False):
	G=gate;F=same_round;C=prev;A=st;J=int((C.get('meta')or{}).get('round_number')or 0)
	for(B,K)in(C.get('meta')or{}).items():
		if B in FRESH_META:continue
		A['meta'][B]=merge_value(K,A['meta'].get(B))if B in A['meta']else copy.deepcopy(K)
	for B in CARRY_TOP:A[B]=merge_value(C.get(B),A.get(B),deep=False)
	if not F:
		for H in A.get('talking_points')or():
			if isinstance(H,dict)and H.get('round')is None:H['round']=J
	for B in SAME_ROUND_TOP:N=C.get(B)if F else tag_round(C.get(B),J);A[B]=merge_value(N,A.get(B))
	for B in APPEND_TOP:A[B]=copy.deepcopy(C.get(B)or[])+[A for A in A.get(B)or[]if A not in(C.get(B)or[])]
	A['clauses']=merge_clauses(C.get('clauses')or[],A.get('clauses')or[]);A['clause_map']=dict(C.get('clause_map')or{},**A.get('clause_map')or{});O=C.get('numbering_map')or{};SB.fill_clause_map(dict(A,coverage_index=list(C.get('coverage_index')or[])+list(A.get('coverage_index')or[]),numbering_map=dict(O,**A.get('numbering_map')or{})))
	for D in A.get('user_decisions')or[]:
		for E in A['clauses']:
			if E.get('clause_id')in(D.get('applies_to')or[])and not E.get('user_decision'):
				E['user_decision']={'question_id':D.get('id'),'answer':D.get('answer'),'answer_kind':D.get('answer_kind'),'recorded_at':D.get('recorded_at')}
				if D.get('requires_explicit'):E['user_decision'].update(requires_explicit=True,outcome=D.get('outcome'))
	I=dict(C.get('numbering_map')or{});I.update({A:B for(A,B)in(A.get('numbering_map')or{}).items()if B or A not in I});A['numbering_map']=I;A['meta']['generated_at']=(C.get('meta')or{}).get('generated_at')or A['meta']['generated_at']
	if F:
		P=bool(G)and G.get('mode')=='send'and not G.get('passed');L,M=A.setdefault('quality_gate',{}),C.get('quality_gate')or{}
		for B in('work','send','send_copy'):
			if B=='send_copy'and P:continue
			if not L.get(B)and M.get(B):L[B]=copy.deepcopy(M[B])
		if not text_status_given and C.get('text_status'):A['text_status']=C['text_status']
	return A
def place_labels_of(received,deal,decisions,numbers,lang):
	H=decisions;C=numbers
	if not C or not isinstance(H,dict):return{}
	for A in received or():
		A=A if not A or os.path.isabs(A)else os.path.join(deal,A)
		if A and os.path.exists(A)and A.lower().endswith('.docx'):
			try:import content_checks as K;D=K.place_labels(A,lang,C)
			except Exception:return{}
			G={};I=str(lang or'').lower()[:2]=='en'
			for B in H.get('decisions')or():
				if not isinstance(B,dict)or not B.get('id'):continue
				E=B.get('para')
				if isinstance(E,int)and E<len(D)and D[E]:G[B['id']]=D[E]
				F=B.get('after_para')
				if B.get('op')=='insert_paragraph'and isinstance(F,int)and F<len(C):J=next((C[A]for A in range(F,-1,-1)if C[A]),None);L=('clause %s'if I else'סעיף %s')%J if J else D[F];G[B['id']]=('New clause after %s'if I else'סעיף חדש אחרי %s')%L
			return G
	return{}
def clause_numbers_of(received,deal):
	for A in received or():
		A=A if not A or os.path.isabs(A)else os.path.join(deal,A)
		if A and os.path.exists(A)and A.lower().endswith('.docx'):
			try:import content_checks as B;return B.numbered_labels(A)
			except Exception as C:print('מספרי הסעיפים לא נקראו מהטיוטה (%s). מפת הסעיפים נכתבת בלי clause_number'%C);return
def schedules_of(received,deal,numbers=None):
	A=received_texts_of(received,deal)
	if not A:return
	try:import content_checks as B;return B.schedule_of_paragraphs(A,numbers)
	except Exception:return
def received_texts_of(received,deal):
	for A in received or():
		A=A if not A or os.path.isabs(A)else os.path.join(deal,A)
		if A and os.path.exists(A)and A.lower().endswith('.docx'):
			try:import common.docx_tracked as B;return B.received_paragraphs(A)
			except Exception as C:print('הטקסט של הטיוטה לא נקרא (%s). pending_text לא נרשם'%C);return
def record_sent(st,path,deal,rnd,basis='user_confirmed',edited=False):
	K=edited;H=basis;E=rnd;D=st;A=doc_record(path,deal,'sent_at');A.update(round=E,basis=H,edited_before_sending=bool(K));F=D['meta']['sent_documents'];C=next((B for B in F if isinstance(B,dict)and B.get('sha256')==A['sha256']),None);G=[]
	if C is not None:
		if str(C.get('round'))==str(E):
			if K:C['edited_before_sending']=True
			if H=='user_confirmed'and C.get('basis')!='user_confirmed':C.setdefault('history',[]).append({'basis':C.get('basis'),'until':A['sent_at']});C['basis']=H
		A=C
	else:
		G=[A for A in F if isinstance(A,dict)and str(A.get('round'))==str(E)]
		if G:
			I=[]
			for J in G:I+=J.get('history')or[];I.append(dict({A:B for(A,B)in J.items()if A!='history'},replaced_at=A['sent_at']));F.remove(J)
			A['history']=I
		F.append(A)
	B=(D.get('quality_gate')or{}).get('send_copy')
	if isinstance(B,dict)and B.get('sha256')==A['sha256']:
		if A.get('basis')!='assumed_last_work':B.update(status='sent',sent_at=A['sent_at']);B.pop('sent_instead',None)
	elif isinstance(B,dict)and B.get('sha256')and(any(A.get('sha256')==B['sha256']for A in G)or str(E)==str((D.get('meta')or{}).get('round_number'))):
		if B.get('status')=='sent':B['status']='produced_pending_send';B.pop('sent_at',None)
		B['sent_instead']=A['file_name']
	if str(E)==str((D.get('meta')or{}).get('round_number'))and(D.get('text_status')or'')in UNSENT_OURS:D['text_status']='our_sent_response'
	for L in D.get('deliberate_concessions')or():
		if not L.get('delivered_in_round'):L['delivered_in_round']=E
	return A
def cmd_write(a):
	C=a.deal;os.makedirs(C,exist_ok=True);Y=os.path.join(C,LIVE);B=load(Y,'קובץ המצב')if os.path.exists(Y)else None
	if B is not None and str((B.get('meta')or{}).get('schema_version'))!=SB.SCHEMA_VERSION:print('קובץ המצב הקיים בפורמט ישן (%s). הרץ קודם: negotiation_state.py migrate --deal ...'%(B.get('meta')or{}).get('schema_version'));return 2
	F=int((B or{}).get('meta',{}).get('round_number')or 0);l=bool(a.decisions)and B is not None and os.path.basename(a.decisions)=='decisions_round_%d.json'%F==B.get('decisions_file');m=B is not None and(not B.get('decisions_file')and not(B.get('meta')or{}).get('sent_documents')or l);D=a.round or(F if m else F+1 if B else 1)
	if B is not None and D<F:print('סבב %d קטן מהסבב שבקובץ (%d). קובץ מצב אינו חוזר לאחור'%(D,F));return 2
	Z=a.transaction_id or(B or{}).get('meta',{}).get('transaction_id')or os.path.basename(os.path.abspath(C));M=[]
	for b in a.produced or():
		N,p,G=b.partition('=');H=G if os.path.isabs(G)else os.path.join(C,G)
		if not N or not G or not os.path.exists(H):print('--produced %r: צריך סוג=נתיב לקובץ שקיים'%b);return 2
		M.append((N,H))
	c=load(a.gate,'דוח השער',required=False);d=a.lang or((B or{}).get('meta')or{}).get('lang')or'he';Q=load(a.decisions,'קובץ ההכרעות',required=False);R=clause_numbers_of(a.received,C);e=dict(place_labels_of(a.received,C,Q,R,d));e.update(load(a.clause_labels,'מספרי הסעיפים',required=False)or{});A=SB.build_state(Z,D,profile=load(a.profile,'הפרופיל',required=False),decisions=Q,deal_dir=C,produced=M,resolution=load(a.resolution,'תוצאת האיתור',required=False),gate=c,concessions=load(a.concessions,'הוויתורים',required=False)or(),lang=d,text_status=a.text_status,counterparty_name=a.counterparty or'',contract_type=a.contract_type or'',clause_labels=e or None,para_count=a.para_count,clause_numbers=R,received_texts=received_texts_of(a.received,C),clause_schedules=schedules_of(a.received,C,R));I=load(a.compare,'השוואת הסבב',required=False)
	if B is not None:
		B=copy.deepcopy(B);S=[];SB.normalize_statuses(B,S)
		if I is not None and D>F:
			if not any(int(A.get('round')or 0)==F for A in B['meta'].get('sent_documents')or())and I.get('sent')and os.path.exists(I['sent']):record_sent(B,I['sent'],C,F,'assumed_last_work'if I.get('base')=='assumed'else'compare_base');print('נרשם כקובץ שנשלח בסבב %d: %s (%s)'%(F,os.path.basename(I['sent']),'בסיס משוער'if I.get('base')=='assumed'else'בסיס ההשוואה'))
			S+=SB.apply_compare(B,I,D)
		for K in S:print('  %s'%K)
		A=carry_over(B,A,same_round=D==F,gate=c,text_status_given=bool(a.text_status));T=os.path.join(C,'negotiation_state_round_%d.json'%F)
		if D>F and not os.path.exists(T):dump(T,B);print('הסבב הקודם נשמר: %s'%T)
	O=A.setdefault('quality_gate',{})
	for(N,H)in M:
		if N=='send'and not(O.get('send_copy')or{}).get('path'):E=SB.produced_document(H,C,'send');O['send_copy']=SB.send_copy_pending({'path':E['path'],'sha256':E['sha256'],'recorded_at':E['produced_at']})
	L=next((paths.prefix_from_name(A)for(B,A)in M if B=='work'and paths.prefix_from_name(A)),None);E=A['meta'].get('file_prefix')if isinstance(A['meta'].get('file_prefix'),dict)else{};J=(E['agreement_type'],E.get('company')or'')if E.get('agreement_type')else paths.stored_prefix(B)if B else None
	if J or L:
		f=J or L;E=dict(E,agreement_type=f[0],company=f[1]);E.setdefault('set_in_round',1 if J else D)
		if J and L and tuple(L)!=tuple(J)and paths.prefix_switch_answer(A)=='switch':E.setdefault('history',[]).append({'agreement_type':J[0],'company':J[1],'until_round':D});E.update(agreement_type=L[0],company=L[1],set_in_round=D)
		A['meta']['file_prefix']=E
	g=(O.get('send_copy')or{}).get('sha256')if(O.get('send_copy')or{}).get('status')=='produced_pending_send'else None
	for G in a.sent or():
		H=G if os.path.isabs(G)else os.path.join(C,G)
		if not os.path.exists(H):print('--sent %r אינו קיים'%G);return 2
		if g and sha256(H)==g:print('%s הוא העותק למשלוח של הסבב: נרשם "הופק, ממתין לשליחה", ולא "נשלח". אחרי המשלוח: negotiation_state.py sent --deal <תיקיית העסקה> --file <הקובץ>'%os.path.basename(H));continue
		record_sent(A,H,C,D)
	for G in a.received or():
		H=G if os.path.isabs(G)else os.path.join(C,G)
		if not os.path.exists(H):print('--received %r אינו קיים'%G);return 2
		E=doc_record(H,C,'received_at');E['round']=D
		if E['sha256']not in{A.get('sha256')for A in A['meta']['received_documents']}:A['meta']['received_documents'].append(E)
	SB.link_silent_decisions(A,load(a.decisions,'קובץ ההכרעות',required=False))
	if B is not None and D>F:carry_time_anchors(B,A,C,F,a.received)
	for K in SB.refresh_open_items(A,D,load(a.decisions,'קובץ ההכרעות',required=False)):print('  %s'%K)
	from orchestrator import proportionality as n;U=set()
	for P in A.get('user_decisions')or():
		if isinstance(P,dict)and P.get('answer_kind')=='explicit':
			U.update(str(A)for A in P.get('applies_to')or());V=str(P.get('id')or'').split(':')
			if len(V)>=2 and V[0]in('commercial','held'):U.add(V[1])
	for W in n.commercial_concession_violations(A.get('deliberate_concessions')):
		if str(W.get('clause_ref'))in U:continue
		print('  ויתור על נושא מסחרי מחייב בלי שאלה נפרדת: %s (%s). נשאל במנה הבאה, ואינו נמסר כוויתור עד תשובה מפורשת'%(W.get('topic'),W.get('clause_ref')))
	o=isinstance(A.get('positions_source'),dict)and A['positions_source'].get('mode')=='deal_only';K=None if o else SB.playbook_update_line(A,D,A['meta'].get('lang')or'he')
	if K:print('לשורה בסיכום: %s'%K)
	SB.summarize(A);h=SB.unresolved_silent_changes(A,D)
	if h:print('שינויים שקטים בלי הכרעה מסומנת (חוסמים משלוח): %s. ההכרעה נכנסת לקובץ ההכרעות עם silent_change: <מזהה>, בהחזרה בעקוב אחר שינויים או בקבלה עם בועה'%', '.join(A['id']for A in h))
	print('עסקה: %s   סבב: %d (%s)'%(Z,D,A['meta']['round_stage']));print('סעיפים: %d   ויתורים מכוונים: %d   הכרעות משתמש: %d'%(len(A['clauses']),len(A['deliberate_concessions']),len(A['user_decisions'])));i=SB.coverage_gaps(A.get('coverage_index'))
	if i:print('רכיבים בלי הכרעה במפתח הכיסוי: %d'%len(i))
	infer_paper_type(A,received_texts_of(a.received,C))
	try:import playbook_map as j;j.update_ledger(A,j.round_view(A,I))
	except Exception as X:print('יומן הסבבים לא נרשם (%s). להריץ playbook_map.py rounds'%X)
	try:import round_metrics as k;k.update(A,k.entry(A,Q,D,with_outcome=I is not None and B is not None and D>F))
	except Exception as X:print('נתוני המדידה לא נרשמו (%s)'%X)
	return write_checked(C,A)
def infer_paper_type(st,texts):
	C=texts;A=st.setdefault('meta',{})
	if A.get('paper_type')or not C:return
	try:from orchestrator import resolve_playbook as D;B=D.detect_paper_type(C)
	except Exception:return
	if B.get('suggested')=='negotiable'and B.get('confident'):A['paper_type']='negotiable';A['paper_type_basis']={'answer_kind':'inferred_no_signs','recorded_at':SB.now_iso(),'suggested':'negotiable'};print('סוג הנייר: אין בנוסח סימן להליך תחרותי או לתנאים מקוונים, נרשם negotiable');return'negotiable'
	print('סוג הנייר לא נקבע, ובנוסח יש סימנים (%s): לשאול במנה ולרשום ב-round_tools.py paper-type --set'%', '.join(A for(A,B)in(B.get('signals')or{}).items()if B))
def carry_time_anchors(prev,st,deal,prev_round,received):
	F=deal;D=prev_round;C=st;G=next((A for A in(prev.get('meta')or{}).get('received_documents')or()if isinstance(A,dict)and str(A.get('round'))==str(D)),None);H=received_texts_of(received,F);E=received_texts_of([G.get('file_name')],F)if G else None
	if not E:E=sent_base_texts(prev,F,D)
	if not(H and E):return
	try:import content_checks as I
	except Exception:return
	M={(A['para'],A['issue']):A['text']for A in I.time_anchors(E)};N=I.time_anchors(H);J={(A.get('para'),A.get('issue'))for A in C.get('time_anchors')or()if isinstance(A,dict)and str(A.get('round')or C['meta']['round_number'])==str(C['meta']['round_number'])}
	for A in list(C.get('time_anchors')or()):
		if not isinstance(A,dict)or str(A.get('round'))!=str(D):continue
		K=M.get((A.get('para'),A.get('issue')));B=next((B for B in N if K and B['issue']==A.get('issue')and B['text']==K),None)
		if B and(B['para'],B['issue'])not in J:L={A:B for(A,B)in A.items()if A!='round'};L.update(para=B['para'],carried_from_round=D);C['time_anchors'].append(L);J.add((B['para'],B['issue']));print('  עוגן זמן מסבב %s (פסקה %s): אותו נוסח בפסקה %s, והתשובה עוברת'%(D,A.get('para'),B['para']))
def our_names(deal,profile=None):
	A=profile
	if A is None:E=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(deal))),'פרופיל-לקוח.json');A=load(E,'הפרופיל')if os.path.exists(E)else None
	if not A:return[]
	import lawyer as F;C=F.lawyer_view(A);D=[]
	for B in[C.get('lawyer_name'),C.get('lawyer_name_en')]+list(C.get('lawyer_aliases')or[]):
		if B and str(B).strip()and str(B).strip()not in D:D.append(str(B).strip())
	return D
def sent_base_texts(st,deal,rnd):
	D=rnd;C=deal;A=next((A for A in reversed((st.get('meta')or{}).get('sent_documents')or[])if isinstance(A,dict)and str(A.get('round'))==str(D)),None);B=A and(A['file_name']if os.path.isabs(A['file_name'])else os.path.join(C,A['file_name']))
	if not B or not os.path.exists(B):return
	try:import compare_rounds as E,common.docx_tracked as F;G=our_names(C);return E.base_paragraphs(F.body_paragraphs(F.document_root(B)),G,E.prior_keys(B,G,C,D))[1]
	except Exception as H:print('הפסקאות של הקובץ שנשלח בסבב %s לא נקראו (%s)'%(D,H));return
def produced_for_round(st,deal,rnd):
	if str(rnd)!=str((st.get('meta')or{}).get('round_number')):return
	C=(st.get('quality_gate')or{}).get('send_copy')or{};D=[C.get('path')]+[A.get('path')for A in reversed(st.get('produced_documents')or())if isinstance(A,dict)and A.get('kind')=='work']
	for A in D:
		B=A and(A if os.path.isabs(A)else os.path.join(deal,A))
		if B and os.path.exists(B):return B
def record_lawyer_edits(st,deal,rnd,produced,sent,ours):
	J=produced;D=rnd;import compare_rounds as K;from orchestrator import question_batch as M;N=K.edits_before_sending(J,sent,ours,K.prior_keys(J,ours,deal,D));L=os.path.join(deal,'decisions_round_%d.json'%int(D));C=load(L,'קובץ ההכרעות')if os.path.exists(L)else{};C=C.get('decisions',[])if isinstance(C,dict)else C or[];O={A.get('clause_id'):A for A in st.get('clauses')or()};P=st.get('numbering_map')or{};F=[]
	for A in N:
		G=A.get('para')if isinstance(A.get('para'),int)else None;E=[A for A in C if G is not None and A.get('para')==G]or[B for B in C if G is None and isinstance(A.get('after_para'),int)and B.get('after_para')==A['after_para']];H=next((A for A in E if A.get('op')not in(None,'accept')),None)or(E[0]if E else{});I=H.get('id');B=O.get(I)or{};Q,R=M.diff_window(A.get('produced_text'),A.get('sent_text'),mark=False);F.append({'date':SB.now_iso()[:10],'round':int(D),'para':A.get('para'),'after_para':A.get('after_para'),'sent_para':A.get('sent_para'),'clause_id':I,'clause_ids':[A.get('id')for A in E],'clause':P.get(I)or'','rule_ids':list(H.get('rule_ids')or B.get('rule_ids')or[]),'decision_code':H.get('decision_code')or B.get('decision_code')or'','kind':A['kind'],'before':Q,'after':R,'produced_text':A.get('produced_text')or'','sent_text':A.get('sent_text')or'','source':'edited_before_sending','auto':True,'candidate_for_playbook_update':False})
		if B and A['kind'].startswith('text_')and A.get('sent_text'):
			B['sent_text']=A['sent_text']
			if B.get('pending_text'):B['pending_text']=A['sent_text']
			if B.get('status')=='CLOSED'and B.get('agreed_text')and B['agreed_text']!=A['sent_text']:B.setdefault('agreed_text_history',[]).append({'text':B['agreed_text'],'until_round':int(D),'replaced_by':'edited_before_sending'});B['agreed_text']=A['sent_text']
	st['lawyer_overrides']=[A for A in st.get('lawyer_overrides')or()if not(isinstance(A,dict)and A.get('auto')and A.get('source')=='edited_before_sending'and str(A.get('round'))==str(D))]+F;return F
def cmd_decide(a):
	C=os.path.join(a.deal,LIVE)
	if os.path.exists(C):A=load(C,'קובץ המצב')
	else:os.makedirs(a.deal,exist_ok=True);A=SB.skeleton();A['meta'].update(transaction_id=os.path.basename(os.path.abspath(a.deal)),round_number=1,round_stage=SB.stage_for_round(1),generated_at=SB.now_iso(),last_updated=SB.now_iso());print('אין עדיין קובץ מצב בעסקה: נוצר שלד לסבב 1, וההכרעה נרשמת בו')
	E=bool(a.requires_explicit)or any(a.id in(A.get('requires_explicit')or())for A in A.get('question_batches')or()if isinstance(A,dict))
	try:B=SB.record_user_decision(A,a.id,a.situation,a.answer,a.answer_kind,applies_to=a.applies_to or(),recommendation=a.recommendation,requires_explicit=E)
	except ValueError as F:print('ההכרעה לא נרשמה: %s'%F);return 2
	if a.applies_to_para:B['applies_to_paras']=sorted(set(a.applies_to_para))
	D=[B for B in B['applies_to']if B not in{A.get('clause_id')for A in A.get('clauses',[])}]
	if D:print('אין עדיין בקובץ סעיף בשם %s. ההכרעה נשמרה ב-user_decisions, ותירשם על הסעיף כש-write יכתוב אותו'%', '.join(D))
	A['meta']['last_updated']=SB.now_iso();print('הכרעה %s: %s (%s)'%(B['id'],B['answer'],B['outcome']))
	if B['outcome']==SB.HELD_REQUIRES_EXPLICIT:print('הפריט נשאר פתוח: תשובה כללית אינה מחילה הכרעה מסוג זה (מעבר לפלייבוק, הצעה נגדית הדוקה, סכום, גבול הקו האדום או התחייבות תפעולית). ההמלצה אינה מוחלת, ובהכרעה בקובץ ההכרעות: coverage: for_call, עד תשובה מפורשת. הפריט נשאל שוב במפורש במנה הבאה')
	return write_checked(a.deal,A)
def cmd_stance(a):
	C=os.path.join(a.deal,LIVE)
	if os.path.exists(C):A=load(C,'קובץ המצב')
	else:os.makedirs(a.deal,exist_ok=True);A=SB.skeleton();A['meta'].update(transaction_id=os.path.basename(os.path.abspath(a.deal)),round_number=1,round_stage=SB.stage_for_round(1),generated_at=SB.now_iso(),last_updated=SB.now_iso());print('אין עדיין קובץ מצב בעסקה: נוצר שלד לסבב 1, והגישה נרשמת בו')
	D=a.round or SB.current_round(A)
	try:B=SB.record_stance(A,a.value,D,a.answer_kind)
	except ValueError as E:print('הגישה לא נרשמה: %s'%E);return 2
	A['meta']['last_updated']=SB.now_iso();print('הגישה: %s (סבב %d, %s)'%(B['value'],B['round'],B['answer_kind']));return write_checked(a.deal,A)
def cmd_sent(a):
	J=os.path.join(a.deal,LIVE);A=load(J,'קובץ המצב');E=a.file if os.path.isabs(a.file)else os.path.join(a.deal,a.file)
	if not os.path.exists(E):print('--file %r אינו קיים'%a.file);return 2
	C=a.round or int((A.get('meta')or{}).get('round_number')or 1);F=produced_for_round(A,a.deal,C)if a.basis=='user_confirmed'else None;D=[]
	if F and sha256(F)!=sha256(E):
		try:D=record_lawyer_edits(A,a.deal,C,F,E,our_names(a.deal,load(a.profile,'הפרופיל',required=False)))
		except Exception as K:print('ההבדלים מול העותק שהופק לא נקראו (%s). הקובץ נרשם כנשלח בלי lawyer_overrides'%K)
	G=record_sent(A,E,a.deal,C,a.basis,a.edited or bool(D));A['meta']['last_updated']=SB.now_iso();print('נרשם כקובץ שנשלח בסבב %d: %s (%s)%s'%(C,G['file_name'],a.basis,'. ההשוואה בסבב הבא מסומנת "בסיס משוער"'if a.basis=='assumed_last_work'else''))
	if G.get('history'):print('הרשומה הקודמת של סבב %d (%s) הוחלפה, ונשמרה ב-history'%(C,', '.join(A.get('file_name')or'?'for A in G['history']if A.get('replaced_at'))))
	if D:
		H=[]
		for B in D:
			I=B.get('clause')or B.get('clause_id')or('פסקה %s'%B['para']if isinstance(B.get('para'),int)else'אחרי פסקה %s'%B['after_para']if isinstance(B.get('after_para'),int)else'בועה')
			if I not in H:H.append(I)
		print('לשורה בסיכום: הקובץ שנשלח שונה מהעותק שהופק (%s) ב-%d מקומות: %s. ההבדלים נרשמו ב-lawyer_overrides, וההשוואה בסבב הבא היא מול הקובץ שנשלח'%(os.path.basename(F),len(D),', '.join(H)))
	return write_checked(a.deal,A)
def cmd_reopen(a):
	A=load(os.path.join(a.deal,LIVE),'קובץ המצב')
	try:B=SB.record_reopen(A,a.clause,a.instruction,a.reason or'',a.round or SB.current_round(A))
	except ValueError as C:print('לא נפתח: %s'%C);return 2
	SB.record_user_decision(A,'reopen-%s-%d'%(a.clause,B['round']),None,a.instruction,'explicit',applies_to=[a.clause]);SB.summarize(A);A['meta']['last_updated']=SB.now_iso();print('נפתח מחדש בהוראת עורך הדין: %s (היה %s), %s'%(a.clause,B['previous_status'],B['recorded_at']));return write_checked(a.deal,A)
DECISION_BASES='PolicyDerived','PolicyBenchmark','UserDecided','Law','CompanyPractice','ExpertJudgment'
AREO_BASES='UserDecided','Law','CompanyPractice','ExpertJudgment'
IMPORTANCE='CRITICAL','HIGH','MEDIUM','LOW'
DECISION_CODES='A1','A2','A3','R1','R2','R3','N1'
ROUND_BASIS='state','document','user'
PAPER_TYPES='negotiable','tender_pre_bid','tender_awarded','standard_form_online'
TENDER_TYPES='tender_pre_bid','tender_awarded','standard_form_online'
LAST_ROUND_CHANGES='our_accepted','our_accepted_partial','our_rejected','their_rejected_our_insert','our_open','their_tracked','their_silent'
SILENT_DECISIONS='revert','accept_with_comment','accept_with_condition'
WAYS='existing_playbook','proposed_playbook','none'
POSITIONS_MODES='playbook','market','both','deal_only'
BUILD_STATES='not_requested','awaiting_builder','returned','declined','unavailable'
RESOLUTION_RESULTS='match','choose','no_match'
PLAYBOOK_MATCH='match','side_mismatch','family_mismatch','mutuality_mismatch','asked'
PLAYBOOK_STATUS_READ='policy_gate','unavailable'
UPDATED_BY_VALUES='orchestrator','strategist'
DR_ANSWER_KINDS='explicit','delegated','none'
DR_OUTCOMES='applied_recommendation','unanswered_for_call','held_requires_explicit','applied','applied_other','answered'
ENTITY_STATUS='value','signing_blank','open'
ENTITY_SOURCES='profile','signed_agreement','incorporation_certificate','letterhead','client_answer'
ENTITY_CHECKS='ok','missing','wrong_length','bad_check_digit','not_company'
MUTUAL_RESULTS='both_ways','our_direction_only','deliberate_concession','decision_required'
INVOKERS='us','them','both'
EXPOSED_SIDES='them','us'
CONCESSION_WHO='us','them'
COVERAGE_DECISIONS=tuple(SB.COVERAGE_DECISIONS)+('awaiting_playbook',)
FORBIDDEN_IMPORTANCE='לא נקבע','לא מוגדר','n/a','unknown',''
RULE_ID_RX=re.compile('^(R|V|Q|SEG|DS|LG|PB|OS|EMP)-?\\d+[a-z]?$',re.I)
MAX_TALKING_POINTS=7
def notes_checks(st):
	B=st;i,j=[],[]
	def A(code,msg,where=None):i.append({'code':code,'message':msg,'where':where})
	def H(code,msg,where=None):j.append({'code':code,'message':msg,'where':where})
	def C(val,allowed,code,where,field,when=True):
		C=allowed;B=val
		if when and B is not None and B not in C:A(code,'%s חייב להיות אחד מ: %s (נמצא %r)'%(field,', '.join(C),B),where)
	B=B or{};G=B.get('meta')or{};C(G.get('round_basis'),ROUND_BASIS,'STATE_ROUND_BASIS','meta/round_basis','round_basis');C(G.get('updated_by'),UPDATED_BY_VALUES,'STATE_UPDATED_BY','meta/updated_by','updated_by');V=G.get('paper_type');C(V or None,PAPER_TYPES,'STATE_PAPER_TYPE','meta/paper_type','paper_type')
	if V in(None,''):H('STATE_PAPER_TYPE_MISSING','meta.paper_type ריק: כשאין סימן להליך תחרותי או לתנאים אחידים הערך הוא negotiable (round_tools.py paper-type --set)','meta/paper_type')
	try:k=int(G.get('round_number')or 1)
	except(TypeError,ValueError):k=1
	r={A.get('round')for A in G.get('round_ledger')or[]if isinstance(A,dict)};l=[A for A in range(1,k+1)if A not in r]
	if l:H('STATE_ROUND_LEDGER_MISSING','אין רשומה ביומן הסבבים (meta.round_ledger) לסבב %s: write של סוף הסבב רושם אותה, ו-playbook_map.py rounds מחליף אותה'%', '.join(str(A)for A in l),'meta/round_ledger')
	if B.get('clarification_questions')and V not in TENDER_TYPES:A('STATE_CLARIFICATION_NOT_TENDER','clarification_questions ממולא רק בהליך תחרותי או בתנאים מקוונים (paper_type %r)'%V,'clarification_questions')
	m={}
	for F in B.get('clauses')or[]:
		if not isinstance(F,dict):continue
		D=F.get('clause_id');C(F.get('decision_code'),DECISION_CODES,'STATE_DECISION_CODE',D,'decision_code');Z=F.get('decision_basis');C(Z,DECISION_BASES,'STATE_DECISION_BASIS',D,'decision_basis');s=F.get('user_decision')or{}
		if Z=='UserDecided'and s.get('answer_kind')!='explicit':A('STATE_USER_DECIDED_NOT_EXPLICIT','UserDecided רק עם תשובה מפורשת של המשתמש (user_decision.answer_kind: explicit); תשובה כללית היא delegated והבסיס הוא מקור ההמלצה',D)
		W=F.get('importance')
		if W is not None and(W not in IMPORTANCE or str(W).strip().lower()in FORBIDDEN_IMPORTANCE):A('STATE_IMPORTANCE','importance חייב להיות CRITICAL, HIGH, MEDIUM או LOW; "לא נקבע" ו"לא מוגדר" אינם ערכים (נמצא %r)'%W,D)
		X=F.get('rule_ids')
		if X is not None:
			if not isinstance(X,list):A('STATE_RULE_IDS','rule_ids הוא רשימה של מזהי כללים, ולא מחרוזת אחת (%r)'%X,D)
			else:
				for P in X:
					if str(P)in DECISION_CODES:A('STATE_RULE_IDS','קוד הכרעה (%s) אינו מזהה כלל: rule_ids מקבל מזהי כללים מהפלייבוק בלבד'%P,D)
		if'legal_review'in F:H('STATE_LEGAL_REVIEW_FIELD','אין סימון "נבדק" של עורך דין בעסקה (כלל יסוד 6): legal_review אינו נכתב; legal_review_required הוא מידע בלבד',D)
		I=F.get('decision_required')
		if isinstance(I,dict):
			if I.get('required')is True and not I.get('situation'):A('STATE_DECISION_REQUIRED','decision_required.required: true רק באחד מתשעת המצבים (situation)',D)
			C(I.get('answer_kind'),DR_ANSWER_KINDS,'STATE_DECISION_REQUIRED',D,'decision_required.answer_kind');C(I.get('outcome'),DR_OUTCOMES,'STATE_DECISION_REQUIRED',D,'decision_required.outcome')
			if I.get('answer_kind')=='delegated'and I.get('outcome')not in(None,'applied_recommendation','held_requires_explicit'):A('STATE_DECISION_REQUIRED','תשובה delegated נרשמת outcome: applied_recommendation (או held_requires_explicit כשהפריט דורש תשובה מפורשת)',D)
			if I.get('answer_kind')=='delegated'and Z=='UserDecided':A('STATE_USER_DECIDED_NOT_EXPLICIT','delegated אינו UserDecided: הבסיס הוא מקור ההמלצה',D)
		for a in F.get('last_round_changes')or[]:t=a.get('classification')if isinstance(a,dict)else a;C(t,LAST_ROUND_CHANGES,'STATE_LAST_ROUND_CHANGE',D,'last_round_changes[].classification')
		b=F.get('mutual_check')
		if isinstance(b,dict):C(b.get('result'),MUTUAL_RESULTS,'STATE_MUTUAL_CHECK',D,'mutual_check.result');C(b.get('likely_invoker'),INVOKERS,'STATE_MUTUAL_CHECK',D,'mutual_check.likely_invoker')
		if F.get('status')=='CLOSED':
			Y=[A for A in('agreed_text','closed_in_round','closed_basis')if not F.get(A)]
			if Y:m.setdefault(tuple(Y),[]).append(D)
		if F.get('status')=='ACCEPTED_PENDING'and not F.get('pending_text')and'pending_text'in F:H('STATE_PENDING_FIELDS','סעיף ACCEPTED_PENDING ממלא pending_text ו-accepted_in_round',D)
	for(Y,c)in m.items():H('STATE_CLOSED_FIELDS','%d סעיפים CLOSED בלי %s (סעיף CLOSED ממלא agreed_text, closed_in_round ו-closed_basis)'%(len(c),', '.join(Y)),', '.join(str(A)for A in c[:8])+(' ...'if len(c)>8 else''))
	for J in B.get('concession_history')or[]:
		if isinstance(J,dict):C(J.get('who'),CONCESSION_WHO,'STATE_CONCESSION_WHO',J.get('clause_id')or J.get('topic'),'concession_history[].who')
	for Q in B.get('silent_changes')or[]:
		if isinstance(Q,dict):C(Q.get('decision'),SILENT_DECISIONS,'STATE_SILENT_DECISION',Q.get('id'),'silent_changes[].decision')
	try:
		for Q in SB.unresolved_silent_changes(B):H('SILENT_CHANGE_UNDECIDED','שינוי שקט של הסבב בלי decision ו-decision_ref: חוסם משלוח בשער',Q.get('id'))
	except Exception:pass
	K=B.get('positions_source')if isinstance(B.get('positions_source'),dict)else{};C(K.get('way'),WAYS,'STATE_POSITIONS_WAY','positions_source/way','positions_source.way');C(K.get('mode')or None,POSITIONS_MODES,'STATE_POSITIONS_MODE','positions_source/mode','positions_source.mode')
	if K.get('mode')=='deal_only':
		if K.get('way')not in(None,'','none'):A('STATE_POSITIONS_MODE','ב-deal_only ה-way הוא none (או חסר)','positions_source/way')
		if(K.get('proposed_playbook')or{}).get('build_state')=='awaiting_builder':A('STATE_POSITIONS_MODE','ב-deal_only אין בנייה שממתינה לבונה (build_state: awaiting_builder)','positions_source/proposed_playbook/build_state')
	u=K.get('proposed_playbook')if isinstance(K.get('proposed_playbook'),dict)else{};d=u.get('build_state');C(d,BUILD_STATES,'STATE_BUILD_STATE','positions_source/proposed_playbook/build_state','build_state')
	if d=='awaiting_builder'and K.get('way')not in(None,'proposed_playbook'):A('STATE_BUILD_STATE','כל עוד build_state הוא awaiting_builder, way הוא proposed_playbook','positions_source/way')
	for(E,R)in enumerate(B.get('coverage_index')or[]):
		if not isinstance(R,dict):continue
		C(R.get('decision'),COVERAGE_DECISIONS,'STATE_COVERAGE_DECISION','coverage_index[%d]'%E,'coverage_index[].decision')
		if R.get('decision')=='awaiting_playbook'and d!='awaiting_builder':A('STATE_AWAITING_PLAYBOOK','awaiting_playbook תקין רק כש-build_state הוא awaiting_builder','coverage_index[%d]'%E)
		if R.get('decision')and not R.get('reason'):A('STATE_COVERAGE_REASON','רשומה במפתח הכיסוי בלי reason','coverage_index[%d]'%E)
	S=B.get('playbook_resolution')if isinstance(B.get('playbook_resolution'),dict)else{};e=S.get('result');C(e,RESOLUTION_RESULTS,'STATE_PLAYBOOK_RESOLUTION','playbook_resolution/result','playbook_resolution.result')
	if e in('choose','no_match')and S.get('chosen'):A('STATE_PLAYBOOK_RESOLUTION','chosen ריק בכל מה שאינו match','playbook_resolution/chosen')
	if e=='choose'and not S.get('question'):A('STATE_PLAYBOOK_RESOLUTION','ב-choose השאלה האחת (question) נכנסת למנת השאלות כלשונה','playbook_resolution/question')
	if S and'activation_ok'not in S:H('STATE_ACTIVATION_OK_MISSING','playbook_resolution נושא תמיד activation_ok (true/false, null כשלא נבחר פלייבוק)','playbook_resolution/activation_ok')
	v=B.get('playbook_status')if isinstance(B.get('playbook_status'),dict)else{};C(v.get('read_from'),PLAYBOOK_STATUS_READ,'STATE_PLAYBOOK_STATUS','playbook_status/read_from','playbook_status.read_from');w=G.get('position')if isinstance(G.get('position'),dict)else{};C(w.get('playbook_match'),PLAYBOOK_MATCH,'STATE_POSITION_MATCH','meta/position/playbook_match','position.playbook_match');x=B.get('entity_details')if isinstance(B.get('entity_details'),dict)else{}
	for(L,M)in x.items():
		if isinstance(M,dict):
			C(M.get('status'),ENTITY_STATUS,'STATE_ENTITY_DETAIL','entity_details/%s'%L,'entity_details.status');C(M.get('source'),ENTITY_SOURCES,'STATE_ENTITY_DETAIL','entity_details/%s'%L,'entity_details.source');C(M.get('check'),ENTITY_CHECKS,'STATE_ENTITY_DETAIL','entity_details/%s'%L,'entity_details.check')
			if M.get('status')=='value'and M.get('check')not in(None,'ok'):A('STATE_ENTITY_DETAIL','status: value רק כשהבדיקה עברה (check: ok)','entity_details/%s'%L)
	for(E,J)in enumerate(G.get('exposed_comments')or[]):
		if isinstance(J,dict):
			C(J.get('side'),EXPOSED_SIDES,'STATE_EXPOSED_SIDE','meta/exposed_comments[%d]'%E,'exposed_comments[].side')
			if not J.get('quote'):A('STATE_EXPOSED_QUOTE','exposed_comments שומר את ההערה במלואה (quote)','meta/exposed_comments[%d]'%E)
	f=B.get('case_law')if isinstance(B.get('case_law'),dict)else None
	if f is not None:
		y=f.get('connector')
		if y in(None,'','אין','none')and f.get('rulings'):A('STATE_CASE_LAW','כש-case_law.connector הוא "אין", rulings ריק: אין פסיקה בלי מחבר (כלל יסוד 2)','case_law')
	z=G.get('deal_documents')if isinstance(G.get('deal_documents'),dict)else{}
	for(E,n)in enumerate(z.get('conflicts')or[]):
		if isinstance(n,dict)and not n.get('decision'):A('STATE_DEAL_DOC_CONFLICT','סתירה בין מסמכי העסקה בלי decision באותו סבב','meta/deal_documents/conflicts[%d]'%E)
	A0=G.get('bilingual')if isinstance(G.get('bilingual'),dict)else{}
	for(E,g)in enumerate(A0.get('mismatches')or[]):
		if isinstance(g,dict)and not(g.get('origin')and g.get('decision')):A('STATE_BILINGUAL_MISMATCH','פער בין הגרסאות נרשם עם origin ו-decision','meta/bilingual/mismatches[%d]'%E)
	T=B.get('signing_checklist')if isinstance(B.get('signing_checklist'),dict)else{}
	if T:
		o=[A for A in T.get('checks')or()if isinstance(A,dict)and A.get('status')=='open']
		if T.get('passed')is True and o:A('STATE_SIGNING_PASSED','signing_checklist.passed: true רק כשאין אף פריט פתוח (%d פתוחים)'%len(o),'signing_checklist')
		if T.get('clean_copy_path')and not T.get('passed'):A('STATE_SIGNING_CLEAN_COPY','clean_copy_path נכתב רק אחרי passed: true','signing_checklist')
	p=set()
	for(E,U)in enumerate(G.get('sent_documents')or[]):
		if not isinstance(U,dict):continue
		P=U.get('round')
		if P in p:H('STATE_SENT_DUPLICATE','sent_documents: רשומה אחת לכל סבב; קובץ אחר לאותו סבב מחליף את הקודמת (history)','meta/sent_documents[%d]'%E)
		p.add(P)
		if not(U.get('path')or U.get('file_name')or U.get('file')):A('STATE_SENT_FIELDS','רשומת קובץ שנשלח בלי נתיב','meta/sent_documents[%d]'%E)
	q=[A for A in B.get('talking_points')or()if isinstance(A,dict)and A.get('status')not in('closed_in_call','superseded')]
	if len(q)>MAX_TALKING_POINTS:H('STATE_TALKING_POINTS','talking_points מציג עד %d נקודות לפי priority (%d פתוחות)'%(MAX_TALKING_POINTS,len(q)),'talking_points')
	for(E,h)in enumerate(B.get('talking_points')or[]):
		if isinstance(h,dict)and h.get('source')=='auto'and not str(h.get('id')or'').startswith('auto:'):A('STATE_TALKING_POINT_ID','נקודה של הכלי נושאת id "auto:<kind>:<מזהה הכרעה>"','talking_points[%d]'%E)
	A1=B.get('quality_gate')if isinstance(B.get('quality_gate'),dict)else{}
	for L in('work','send'):
		N=A1.get(L)
		if N and(not isinstance(N,dict)or not isinstance(N.get('passed'),bool)or'codes'in N and N['codes']is not None and not isinstance(N['codes'],list)):A('STATE_QUALITY_GATE','quality_gate.%s: {"passed": bool, "codes": [...]} (ריק עד שהשער רץ)'%L,'quality_gate/%s'%L)
	for(E,O)in enumerate(B.get('lawyer_overrides')or[]):
		if isinstance(O,dict)and not(O.get('clause_id')and('before'in O and'after'in O or'produced_text'in O and'sent_text'in O)):A('STATE_LAWYER_OVERRIDE','רשומת lawyer_overrides: clause_id, והנוסח שהופק מול הנוסח שנשלח (before/after או produced_text/sent_text)','lawyer_overrides[%d]'%E)
	return i,j
def cmd_check(a):
	A=load(os.path.join(a.deal,LIVE),'קובץ המצב');B=SB.validate_state(A);E=SM.non_iso_timestamps(A);F,G=notes_checks(A);B=list(B)+F
	for C in G:print('  אזהרה [%s] %s%s'%(C['code'],C['message'],'  (%s)'%C['where']if C.get('where')else''))
	if not B and not E:D=A.get('meta',{});print('תקין. עסקה %s, סבב %s (%s).'%(D.get('transaction_id'),D.get('round_number'),D.get('round_stage')));return 0
	report(B)
	for(H,I)in E:print('  [STATE_TIMESTAMP] %s=%s'%(H,I))
	return 3
def cmd_migrate(a):
	D=os.path.join(a.deal,LIVE);A=load(D,'קובץ המצב');E=[B for B in SB.ROOT_ONLY if B in(A.get('meta')or{})];F=[B for B in A.get('clauses')or()if SB.premature_closed(A,B)];G=[B for B in('last_updated','updated_by','date')if B in A]
	if str((A.get('meta')or{}).get('schema_version'))==SB.SCHEMA_VERSION and not(E or F or G):print('הקובץ כבר במבנה הנוכחי (%s). אין מה להמיר.'%SB.SCHEMA_VERSION);return 0
	B=SM.history_path(a.deal,A)
	if os.path.exists(B):print('כבר קיים %s. הקובץ הישן אינו נדרס'%B);return 2
	C,H=SM.migrate_state(A);SB.fill_clause_map(C);os.makedirs(os.path.dirname(B),exist_ok=True);dump(B,A);print('הקובץ הישן נשמר כמו שהוא: %s'%B)
	for I in H[:20]:print('  %s'%I)
	return write_checked(a.deal,C)
def main(argv=None):sys.dont_write_bytecode=True;G=argparse.ArgumentParser(description=__doc__.split('\n')[0]);C=G.add_subparsers(dest='cmd',required=True);A=C.add_parser('write',help='קובץ המצב בסוף סבב');A.add_argument('--deal',required=True,help='תיקיית העסקה, Areo-נתונים/transactions/<id>');A.add_argument('--transaction-id',help='בלעדיו: מהקובץ הקיים, או שם התיקייה');A.add_argument('--round',type=int,help='בלעדיו: הסבב שבקובץ ועוד אחד, או 1');A.add_argument('--decisions',help='קובץ ההכרעות של הסבב');A.add_argument('--profile',help='פרופיל-לקוח.json');A.add_argument('--resolution',help='הפלט של resolve_playbook.py');A.add_argument('--gate',help='הדוח של qa_gate.py');A.add_argument('--concessions',help='JSON: רשימת הוויתורים המכוונים של הסבב');A.add_argument('--clause-labels',help='JSON: {"<מזהה הכרעה>": "סעיף 3"}');A.add_argument('--para-count',type=int,help='מספר הפסקאות בטיוטה שהתקבלה, למפתח הכיסוי');A.add_argument('--produced',action='append',help='סוג=נתיב: work, send, as_produced, decisions');A.add_argument('--sent',action='append',help='הקובץ שנשלח לצד שכנגד בסבב הזה');A.add_argument('--received',action='append',help='הקובץ שהתקבל מהצד שכנגד בסבב הזה');A.add_argument('--counterparty',help='שם הצד שכנגד');A.add_argument('--contract-type',help='סוג ההסכם');A.add_argument('--text-status',choices=SB.TEXT_STATUS);A.add_argument('--lang',choices=('he','en'),help='בלעדיו: מהקובץ הקיים, או he');B=C.add_parser('decide',help='הכרעה של המשתמש');B.add_argument('--deal',required=True);B.add_argument('--id',required=True,help='מזהה השאלה');B.add_argument('--situation',type=int,choices=list(SB.SITUATIONS),help='אחד מתשעת המצבים של "נדרשת הכרעתך"');B.add_argument('--answer',required=True,help='התשובה, במילים של המשתמש');B.add_argument('--answer-kind',required=True,choices=SB.ANSWER_KINDS,help='explicit: המשתמש הכריע. delegated: המשתמש אמר להחיל את ההמלצה');B.add_argument('--applies-to',action='append',help='clause_id שההכרעה חלה עליו');B.add_argument('--applies-to-para',action='append',type=int,help='מספר פסקה בטיוטה שהתקבלה (מ-0) שההכרעה חלה עליה, לשאלה שנשאלה לפני ההכרעות (sensitive_topics: הפסקאות שבפריט, paras)');B.add_argument('--recommendation',help='ההמלצה שהוצגה למשתמש');B.add_argument('--requires-explicit',action='store_true',help='הפריט דורש תשובה מפורשת (מצב 2, counter_tighter, סכום, גבול הקו האדום, התחייבות תפעולית): תשובה כללית נרשמת ואינה מחילה את ההמלצה. בלעדיו: לפי question_batches בקובץ המצב');F=C.add_parser('stance',help='הגישה להחלת הפלייבוק בעסקה');F.add_argument('--deal',required=True);F.add_argument('--value',required=True,choices=SB.STANCES,help='playbook: לפי הפלייבוק (ההמלצה); stricter: מחמירה; lenient: מקלה');F.add_argument('--answer-kind',required=True,choices=SB.ANSWER_KINDS,help='explicit: המשתמש בחר; delegated: בלי תשובה או "לפי ההמלצה", ואז playbook');F.add_argument('--round',type=int,help='הסבב שבו נקבעה; בלעדיו: הסבב שבקובץ המצב');A.add_argument('--compare',help='הפלט של compare_rounds.py לסבב הזה: CLOSED, MOVING, STUCK ושינויים שקטים');D=C.add_parser('sent',help='הקובץ שנשלח בפועל בסבב שהסתיים');D.add_argument('--deal',required=True);D.add_argument('--file',required=True,help='הקובץ שנשלח: העותק למשלוח, קובץ העבודה, או קובץ שנערך');D.add_argument('--round',type=int,help='בלעדיו: הסבב שבקובץ המצב');D.add_argument('--basis',choices=('user_confirmed','assumed_last_work'),default='user_confirmed',help='assumed_last_work: לא ידוע מה נשלח, וההשוואה מול קובץ העבודה האחרון (בסיס משוער)');D.add_argument('--edited',action='store_true',help='עורך הדין ערך את הקובץ לפני המשלוח. ההבדלים מול העותק שהופק נרשמים ב-lawyer_overrides גם בלעדיו');D.add_argument('--profile',help='פרופיל-לקוח.json: השמות שלנו. בלעדיו: הפרופיל שמעל תיקיית העסקה');E=C.add_parser('reopen',help='הוראה רשומה של עורך הדין לפתוח מחדש סעיף מוסכם או ויתור שנמסר');E.add_argument('--deal',required=True);E.add_argument('--clause',required=True,help='clause_id');E.add_argument('--instruction',required=True,help='ההוראה, במילים של עורך הדין');E.add_argument('--reason',help='הסיבה, למשל: הוסכם בשיחה מיום ...');E.add_argument('--round',type=int,help='בלעדיו: הסבב שבקובץ המצב');I=C.add_parser('check',help='בדיקת הקובץ מול המבנה');I.add_argument('--deal',required=True);J=C.add_parser('migrate',help='המרת קובץ בפורמט ישן');J.add_argument('--deal',required=True);H=G.parse_args(argv);return{'write':cmd_write,'decide':cmd_decide,'stance':cmd_stance,'check':cmd_check,'migrate':cmd_migrate,'sent':cmd_sent,'reopen':cmd_reopen}[H.cmd](H)
if __name__=='__main__':sys.exit(main())
