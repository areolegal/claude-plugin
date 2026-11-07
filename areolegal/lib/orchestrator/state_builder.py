# -*- coding: utf-8 -*-
# Copyright (c) Areo. All rights reserved. Licensed under the terms at https://areo.co.il/legal/terms
import copy,datetime as _dt,hashlib,os,re
SCHEMA_VERSION='4.9'
REFS_VERSION='4.9'
ROUND_STAGES='opening','response','closing'
CLAUSE_STATUSES='CLOSED','ACCEPTED_PENDING','MOVING','STUCK','WALK-AWAY','OPENED'
CLOSED_BASES='counterparty_unchanged','counterparty_accepted'
SILENT_DECISIONS='revert','accept_with_comment','accept_with_condition'
REVERT_OPS='replace','replace_span','insert_paragraph','delete_paragraph'
THEIR_CHANGE='their_silent','their_tracked','their_rejected_our_insert','our_rejected','our_accepted_partial'
THEIR_REJECTION='our_rejected','their_rejected_our_insert'
THEIR_MOVEMENT='their_tracked','our_accepted_partial'
FINAL_POSITION=re.compile('final position|final offer|non[- ]?negotiable|not negotiable|not (?:open to|subject to|up for) (?:negotiation|discussion)|will not (?:agree|accept) (?:to )?any (?:change|amendment)|עמדה סופית|עמדתנו הסופית|אינ[והםן] נתונ[הים]* למשא ומתן|לא נתונ[הים]* למשא ומתן|אין מקום למשא ומתן',re.I)
OPEN_POINT_KINDS='for_call','escalation'
CLOSING_REPLY=re.compile('^\\s*(?:agreed|accepted|noted|thank you|thanks|ok|מוסכם|מקובל|תודה)[.!]?\\s*$',re.I)
REQUEST=re.compile('\\bplease\\b|\\bkindly\\b|\\bwe (?:would )?(?:ask|request)\\b|\\bcould you\\b|\\bcan you\\b|\\bwould you\\b|\\bprovide\\b|\\bsend us\\b|\\bconfirm\\b|\\bclarify\\b|\\blet us know\\b|\\?|\\bcannot (?:accept|agree|execute|sign)\\b|נא\\s|אבקש|נבקש|מבקשים|בבקשה|יש להשלים|להשלים|לספק|לשלוח|האם|הבהרה|לא נוכל',re.I)
SITUATIONS=range(1,10)
CONFIDENTIAL_EN='Privileged and confidential: prepared for the purpose of obtaining legal advice'
ANSWER_KINDS='explicit','delegated'
ISO=re.compile('^\\d{4}-\\d\\d-\\d\\dT\\d\\d:\\d\\d:\\d\\d([+-]\\d\\d:\\d\\d|Z)$')
NEW_CLAUSE_ID=re.compile('^N-?\\d+[a-z]?$',re.I)
COVERAGE_DECISION={'accept':'accept_as_is','comment_only':'comment_only','replace':'tracked_change','replace_span':'tracked_change','insert_paragraph':'tracked_change','delete_paragraph':'tracked_change'}
COVERAGE_DECISIONS='accept_as_is','tracked_change','comment_only','for_call'
RULE_ID=re.compile('^(R|V|Q|SEG|DS|LG|PB|OS|EMP)-?\\d+$|^mandatory_list:',re.I)
FORBIDDEN_KEYS='approval','required_by','required_approver','authority_table','approval_required','approved_by','approved_at','approval_status','escalation_approver','approval_table','approved_by_user_in_chat','awaiting_approval'
TOP_KEYS='meta','playbook_source','positions_source','profile_gap','playbook_status','strategy_summary','case_law','exception_log','clarification_questions','posture_confirmation','lawyer_overrides','clauses','coverage_index','sources_log','client_answers','company_representations','open_items','talking_points','commitments','packages','signing_checklist','deliberate_concessions','numbering_map','text_status','entity_details','decisions_file','quality_gate','summary','user_decisions','question_batches','review_table','internal_summary','produced_documents','policy_claim_allowed','pre_send_fixes','playbook_resolution','time_anchors','post_checks_done','checks_reviewed','clause_map','silent_changes'
ROOT_ONLY='time_anchors','post_checks_done','checks_reviewed'
TIME_ANCHOR_ISSUES='past','empty'
TIME_ANCHOR_STATUS='answered','accepted','fixed'
TEXT_STATUS='counterparty_draft','their_draft','our_unsent_response','our_sent_response','our_draft','agreed'
TEXT_STATUS_SYNONYMS={'their_draft':'counterparty_draft'}
def canonical_text_status(v):return TEXT_STATUS_SYNONYMS.get(v,v)
MR_ASKED_AT='negotiator_batch','negotiator_round_end'
MR_ANSWERS='yes','no','not_now'
STANCES='playbook','stricter','lenient'
def stance_of(state):A=(((state or{}).get('meta')or{}).get('deal_context')or{}).get('stance');return A.get('value')if isinstance(A,dict)else None
def record_stance(state,value,round_number,answer_kind):
	D=answer_kind;A=value
	if A not in STANCES:raise ValueError('stance הוא playbook, stricter או lenient: %r'%(A,))
	if D not in ANSWER_KINDS:raise ValueError('answer_kind הוא explicit או delegated')
	B=state.setdefault('meta',{}).setdefault('deal_context',{});C=B.get('stance')if isinstance(B.get('stance'),dict)else None;E=list((C or{}).get('history')or[])
	if C:E.append({A:C.get(A)for A in('value','round','answer_kind','recorded_at')})
	F={'value':A,'round':int(round_number or 1),'answer_kind':D,'recorded_at':now_iso(),'history':E};B['stance']=F;return F
def current_round(state):
	C=(state or{}).get('meta')or{}
	def D(key):return[int(A['round'])for A in C.get(key)or()if isinstance(A,dict)and str(A.get('round','')).isdigit()]
	A=max([int(C.get('round_number')or 0)]+D('received_documents'));B=D('sent_documents')
	if A and B and max(B)>=A:A=max(B)+1
	return A or 1
def stage_for_round(round_number):A=int(round_number or 1);return'opening'if A<=1 else'response'if A==2 else'closing'
def now_iso():return _dt.datetime.now().astimezone().replace(microsecond=0).isoformat()
def sha256_file(path):
	A=hashlib.sha256()
	with open(path,'rb')as B:
		for C in iter(lambda:B.read(1<<16),b''):A.update(C)
	return A.hexdigest()
SEND_COPY_STATUSES='produced_pending_send','sent'
def send_copy_pending(rec):A={A:rec.get(A)for A in('path','sha256','recorded_at')if rec.get(A)};A['status']='produced_pending_send';return A
def produced_document(path,deal_dir,kind):A=path;B=os.path.relpath(os.path.abspath(A),os.path.abspath(deal_dir));return{'kind':kind,'path':B.replace('\\','/'),'sha256':sha256_file(A)if os.path.exists(A)else'','produced_at':now_iso()}
EN_MONTHS='January','February','March','April','May','June','July','August','September','October','November','December'
def display_date(d=None,lang='he'):
	if d is None:d=_dt.date.today()
	elif isinstance(d,str):d=_dt.date.fromisoformat(d[:10])
	if str(lang or'he').lower()[:2]=='en':return'%d %s %d'%(d.day,EN_MONTHS[d.month-1],d.year)
	return'%d.%d.%d'%(d.day,d.month,d.year)
def skeleton():return{'meta':{'transaction_id':'','schema_version':SCHEMA_VERSION,'refs_version':REFS_VERSION,'confidential':'חסוי: הוכן לצורך קבלת ייעוץ משפטי','client_name':'','counterparty_name':'','position':{},'contract_type':'','our_role':'','paper_type':'','governing_law':'','round_number':1,'round_stage':'opening','generated_at':'','last_updated':'','lang':'he','sent_documents':[],'received_documents':[],'deal_context':{'facts':[]}},'playbook_source':'','positions_source':{},'profile_gap':{},'playbook_status':{},'strategy_summary':'','case_law':{'connector':'','rulings':[]},'exception_log':[],'clarification_questions':[],'posture_confirmation':{},'lawyer_overrides':[],'clauses':[],'coverage_index':[],'sources_log':[],'client_answers':[],'company_representations':[],'open_items':[],'talking_points':[],'commitments':[],'packages':[],'signing_checklist':{'checks':[],'passed':False},'deliberate_concessions':[],'numbering_map':{},'text_status':'our_unsent_response','entity_details':{},'decisions_file':'','quality_gate':{'work':{},'send':{},'send_copy':None},'summary':{'closed':0,'accepted_pending':0,'moving':0,'stuck':0,'walk_away':0,'opened':0,'red_line_conflicts':[]},'user_decisions':[],'question_batches':[],'review_table':[],'internal_summary':'','produced_documents':[],'playbook_resolution':{},'time_anchors':[],'post_checks_done':[],'checks_reviewed':[],'silent_changes':[]}
HELD_REQUIRES_EXPLICIT='held_requires_explicit'
def record_user_decision(state,question_id,situation,answer,answer_kind,applies_to=(),recommendation=None,requires_explicit=False):
	H=answer;G=question_id;F=state;D=requires_explicit;C=situation;B=answer_kind
	if C is not None and C not in SITUATIONS:raise ValueError('אין מצב עשירי ל"נדרשת הכרעתך": %r'%(C,))
	if B not in ANSWER_KINDS:raise ValueError('answer_kind הוא explicit או delegated')
	I=bool(D)and B!='explicit';A={'id':G,'situation':C,'answer':H,'answer_kind':B,'applies_to':list(applies_to),'recommendation':recommendation,'outcome':HELD_REQUIRES_EXPLICIT if I else'user_decided'if B=='explicit'else'applied_recommendation','recorded_at':now_iso()}
	if D:A['requires_explicit']=True
	F.setdefault('user_decisions',[]).append(A)
	for E in F.get('clauses',[]):
		if E.get('clause_id')in A['applies_to']:
			E['user_decision']={'question_id':G,'answer':H,'answer_kind':B,'recorded_at':A['recorded_at']}
			if D:E['user_decision'].update(requires_explicit=True,outcome=A['outcome'])
	return A
def held_for_explicit(state):
	B={}
	for A in(state or{}).get('user_decisions')or():
		if not isinstance(A,dict)or not A.get('id'):continue
		if A.get('outcome')==HELD_REQUIRES_EXPLICIT:B[A['id']]=A
		elif A.get('answer_kind')=='explicit':B.pop(A['id'],None)
	return set(B)
def _sent_rounds(state):return sorted({int(A.get('round'))for A in((state or{}).get('meta')or{}).get('sent_documents')or()if isinstance(A,dict)and str(A.get('round','')).lstrip('-').isdigit()})
def premature_closed(state,c):
	if c.get('status')!='CLOSED':return
	if c.get('closed_basis')not in CLOSED_BASES:return'אין closed_basis: counterparty_unchanged או counterparty_accepted'
	if not isinstance(c.get('closed_in_round'),int):return'אין closed_in_round'
	if not any(A<c['closed_in_round']for A in _sent_rounds(state)):return'אין ב-sent_documents מסמך שנשלח לפני סבב %s'%c['closed_in_round']
def open_point_clauses(state):
	F=state;D=set()
	for A in(F or{}).get('talking_points')or():
		if not isinstance(A,dict)or A.get('status')in('closed_in_call','closed','superseded'):continue
		B=str(A.get('id')or'')
		if B.startswith('auto:')and(A.get('kind')or B.split(':')[1])not in OPEN_POINT_KINDS:continue
		E=list(A.get('clause_ids')or())
		if not E and B.startswith('auto:'):E=[B.split(':',2)[2].split('#')[0]]
		D.update(E)
	for C in(F or{}).get('deliberate_concessions')or():
		if isinstance(C,dict)and C.get('for_call')and C.get('clause_ref'):D.add(C['clause_ref'])
	return D
def delivered(state,round_number):return int(round_number or 0)in _sent_rounds(state)
def normalize_statuses(state,log=None):
	C=log;B=state;C=C if C is not None else[];F=int(((B or{}).get('meta')or{}).get('round_number')or 1);E=open_point_clauses(B);D=[]
	for A in(B or{}).get('clauses')or():
		if A.get('status')!='CLOSED'or not(premature_closed(B,A)or A.get('clause_id')in E):continue
		A['status']='ACCEPTED_PENDING';A['accepted_in_round']=A.pop('closed_in_round',None)or A.get('decided_in_round')or F
		if A.get('agreed_text'):A['pending_text']=A.pop('agreed_text')
		A.pop('closed_basis',None)
		if A.get('clause_id')in E:A['held_for']='talking_point'
		D.append(A.get('clause_id'))
	if D:C.append('CLOSED -> ACCEPTED_PENDING (%d): הצד השני עוד לא הגיב, או שיש נקודה פתוחה לשיחה'%len(D))
	return D
def summarize(state):
	C=state;A=C.setdefault('summary',{});B={'CLOSED':'closed','ACCEPTED_PENDING':'accepted_pending','MOVING':'moving','STUCK':'stuck','WALK-AWAY':'walk_away','OPENED':'opened'}
	for E in B.values():A[E]=0
	for D in C.get('clauses')or():
		if D.get('status')in B:A[B[D['status']]]+=1
	A.setdefault('red_line_conflicts',[]);return A
def in_fight_list(c):return c.get('tier')=='deal_breaker'or bool(c.get('fight_list'))
def _norm(s):return re.sub('\\s+',' ',re.sub('[\u200e\u200f\u202a-\u202e]','',s or'')).strip()
def apply_compare(state,compare,round_number):
	O=compare;H=state;B=int(round_number);F=B-1;R=(O or{}).get('clauses')or[];S=H.get('clause_map')or{};T=open_point_clauses(H);I=[]
	def a(c):
		G=c.get('clause_id');B=S.get(G)or{};D={_norm(c.get(A))for A in('pending_text','agreed_text','current_text')if c.get(A)};E=int(c.get('decided_in_round')or F)==F;C=[]
		for A in R:
			if E and isinstance(B.get('para'),int)and A.get('base_para')==B['para']:C.append(A)
			elif E and isinstance(B.get('after_para'),int)and A.get('base_para')is None and A.get('after_base_para')==B['after_para']:C.append(A)
			elif D and _norm(A.get('we_sent'))in D:C.append(A)
		return C
	U={};V=(O or{}).get('threads')or[];b={A.get('received_para'):A.get('base_para')for A in(O or{}).get('para_map')or()if isinstance(A,dict)and isinstance(A.get('base_para'),int)};W=their_requests(V)
	for A in H.get('clauses')or():
		D,L=A.get('clause_id'),A.get('status');E=a(A)
		for c in E:U.setdefault(id(c),D)
		X={A.get('received_para')for A in E if A.get('received_para')is not None};Y=S.get(D)or{}
		if isinstance(Y.get('para'),int)and int(A.get('decided_in_round')or F)==F:X|={A for(A,B)in b.items()if B==Y['para']}
		M=next((W[A]for A in sorted(X)if A in W),None);G=sorted({A['classification']for A in E})
		if G:A['last_round_changes']=G;A['current_text']=next((A.get('now')for A in reversed(E)if A.get('now')),A.get('current_text'))
		J=[A for A in G if A in THEIR_CHANGE]
		if J:A['their_change_round']=B
		if L=='CLOSED':
			if J:A['reopened_by_counterparty']={'round':B,'classification':J};I.append('%s: סעיף מוסכם שהצד השני שינה (%s)'%(D,', '.join(J)))
			continue
		if J:
			if any(A in THEIR_REJECTION for A in G):
				Z=A.setdefault('rejections',[])
				if not any(isinstance(A,dict)and A.get('round')==B and A.get('by')=='them'for A in Z):Z.append({'round':B,'by':'them','moved':any(A in THEIR_MOVEMENT for A in G)})
			A['status']='MOVING';A.pop('held_for',None);N=stuck_reason(A,B,final_position_said(E,V))
			if N:A['status']='STUCK';A['escalation']={'round':B,'proposed':'call','basis':N[0],'why':N[1]};I.append('%s: STUCK בסבב %d (%s), מוצעת שיחה'%(D,B,N[0]))
			continue
		if M and L in('MOVING','ACCEPTED_PENDING','OPENED'):A['status']='MOVING';A['their_request']={'round':B,'thread':M.get('root_id'),'text':M.get('text','')[:300]};A.pop('held_for',None);I.append('%s: בקשה חדשה של הצד השני (בועה %s): נשאר פתוח'%(D,M.get('root_id')));continue
		if G==['our_accepted']and L in('MOVING','ACCEPTED_PENDING','OPENED'):
			if D in T:A['status'],A['held_for']='ACCEPTED_PENDING','talking_point';A.setdefault('accepted_in_round',B);continue
			A.update(status='CLOSED',closed_in_round=B,closed_basis='counterparty_accepted',agreed_text=next((A.get('now')or A.get('we_sent')for A in E),A.get('pending_text')or''));A.pop('held_for',None);continue
		if L=='ACCEPTED_PENDING'and not E and int(A.get('accepted_in_round')or F)<=F:
			if D in T:A['held_for']='talking_point';continue
			A.update(status='CLOSED',closed_in_round=B,closed_basis='counterparty_unchanged')
			if A.get('pending_text'):A['agreed_text']=A.pop('pending_text')
			A.pop('held_for',None)
	P={A.get('id'):A for A in H.setdefault('silent_changes',[])}
	for C in R:
		if C.get('classification')!='their_silent':continue
		K='S%d-%s'%(B,C.get('received_para')if C.get('received_para')is not None else's%s'%C.get('sent_para'));Q=P.get(K)or{'id':K,'round':B,'decision':None,'decision_ref':None};Q.update(clause=C.get('clause'),clause_id=U.get(id(C)),sent_para=C.get('sent_para'),received_para=C.get('received_para'),we_sent=C.get('we_sent')or'',they_opened_with=C.get('they_opened_with')or'',reopens_closed=C.get('reopens_closed'))
		if K not in P:H['silent_changes'].append(Q);P[K]=Q
		I.append('שינוי שלא סומן: %s (סעיף %s)'%(K,C.get('clause')or'?'))
	return I
def their_requests(threads):
	C={}
	for A in threads or():
		if A.get('done')or not isinstance(A.get('para'),int):continue
		D=[A for A in A.get('entries')or()if A.get('new')and not A.get('ours')]
		if not D or not(A.get('their_new_thread')or A.get('their_reply_to_ours')):continue
		B=D[-1].get('text')or''
		if CLOSING_REPLY.match(B)or not REQUEST.search(B):continue
		C.setdefault(A['para'],{'root_id':A.get('root_id'),'text':B})
	return C
def final_position_said(hits,threads):
	D={B for A in hits for B in A.get('threads')or()};E={A.get('received_para')for A in hits if A.get('received_para')is not None}
	for A in threads or():
		if A.get('root_id')not in D and A.get('para')not in E:continue
		for B in A.get('entries')or():
			if B.get('ours')or not B.get('new'):continue
			C=FINAL_POSITION.search(B.get('text')or'')
			if C:return C.group(0)
	return''
def stuck_reason(c,round_number,final_said=''):
	B=final_said
	if B:return'final_position','הצד השני כתב שהעמדה סופית ("%s"): הסלמה מוקדמת, שיחה לפני סבב נוסף'%B
	A=sorted({int(A.get('round')or 0)for A in c.get('rejections')or()if isinstance(A,dict)and A.get('by')=='them'and not A.get('moved')})
	if len(A)>=2 and A[-1]==int(round_number):return'rejected_twice','ההצעה שלנו, או המדרגה שאחריה, נדחתה בשני סבבים (%s) בלי תזוזה שלהם: שיחה לפני סבב נוסף'%', '.join(map(str,A[-2:]))
def link_silent_decisions(state,decisions):
	D=state;C=decisions;F={A.get('id'):A for A in D.get('silent_changes')or()};G=(C or{}).get('decisions',[])if isinstance(C,dict)else C or[];E={A.get('clause_id'):A for A in D.get('clauses')or()}
	for B in G:
		A=F.get(B.get('silent_change'))
		if A is None:continue
		if B.get('op')in REVERT_OPS and B.get('kind')=='accept_with_condition':A['decision']='accept_with_condition'
		elif B.get('op')in REVERT_OPS:
			A['decision']='revert';H=E.get(B.get('id'))or E.get(A.get('clause_id'))or{}
			if B.get('kind')=='restore_agreed'or(H.get('restore_agreed')or{}).get('silent_change')==A['id']:A['kind']='restore_agreed'
		elif B.get('op')=='comment_only'and B.get('external_comment'):A['decision']='accept_with_comment'
		else:A['decision']=None
		A['decision_ref']=B.get('id')if A['decision']else None
def unresolved_silent_changes(state,round_number=None):A=state;B=int(round_number or((A or{}).get('meta')or{}).get('round_number')or 0);return[A for A in(A or{}).get('silent_changes')or()if int(A.get('round')or 0)==B and(A.get('decision')not in SILENT_DECISIONS or not A.get('decision_ref'))]
OPEN_ITEM_DONE='closed','done','superseded'
LEGAL_ITEM=re.compile('בדיקה משפטית|legal review|"נבדק"|"Reviewed"',re.I)
def _clause_text(c,decision=None):A=decision or{};return' '.join(str(A or'')for A in(A.get('new'),A.get('new_text'),A.get('text'),c.get('current_text'),c.get('agreed_text'),c.get('pending_text'),c.get('sent_text')))
def refresh_open_items(state,round_number=None,decisions=None):
	H=decisions;F=state or{};B=int(round_number or current_round(F));M={A.get('clause_id'):A for A in F.get('clauses')or()if isinstance(A,dict)};L=(H or{}).get('decisions',[])if isinstance(H,dict)else list(H or[]);N={A.get('id'):A for A in L if isinstance(A,dict)};O=[(str(B),A)for A in L if isinstance(A,dict)for B in A.get('resolves_open_items')or()if B];P=((F.get('quality_gate')or{}).get('send')or{}).get('passed')is True;I=[]
	for A in F.get('open_items')or():
		if not isinstance(A,dict)or A.get('status')in OPEN_ITEM_DONE:continue
		J=[A for A in A.get('clause_ids')or()if A];E=[M.get(A)or{}for A in J];G=str(A.get('item')or'');C=None;D=next((C for(B,C)in O if B==A.get('source')or G.startswith(B)),None)
		if D is not None:C='נסגר בהכרעה %s בסבב %d%s'%(D.get('id'),B,': %s'%(D.get('reason')or D.get('summary'))[:160]if D.get('reason')or D.get('summary')else'')
		elif E and all(A.get('status')=='CLOSED'for A in E):C='כל הסעיפים שלו הוסכמו (CLOSED)'
		elif A.get('depends_on')and E and not any(_norm(A['depends_on']).lower()in _norm(_clause_text(C,N.get(B))).lower()for(B,C)in zip(J,E)):C='הנוסח הנוכחי של הסעיף אינו כולל עוד את "%s"'%A['depends_on']
		elif A.get('kind')=='legal_review'or LEGAL_ITEM.search(G):
			A['blocks_sending']=False
			if P:C='בדיקה משפטית אינה מעכבת משלוח, והשער עבר במצב משלוח בסבב %d'%B
		if C:A['status']='closed';A['closed']={'round':B,'why':C};I.append('open_items: נסגר "%s": %s'%(G[:60],C));continue
		Q=int(A.get('from_round')or A.get('round')or 0);K=[C for(C,A)in zip(J,E)if Q<B and(int(A.get('their_change_round')or 0)==B or int(A.get('decided_in_round')or 0)==B and A.get('op')in REVERT_OPS)]
		if K:A['recheck']={'round':B,'clause_ids':K};I.append('open_items: לבדוק "%s": הסעיף השתנה בסבב %d (%s)'%(G[:60],B,', '.join(K)))
	return I
def open_items_to_recheck(state,round_number=None):A=state;B=int(round_number or current_round(A));return[A for A in(A or{}).get('open_items')or()if isinstance(A,dict)and A.get('status')not in OPEN_ITEM_DONE and int((A.get('recheck')or{}).get('round')or 0)==B]
PLAYBOOK_UPDATE_TRIGGER='עדכון פלייבוק מעסקה'
PLAYBOOK_UPDATE_LINE={'he':'בעסקה הזו הוכרעו %d עמדות שונות מהפלייבוק. לעדכון הפלייבוק כתבו "'+PLAYBOOK_UPDATE_TRIGGER+'".','en':'In this deal, %d positions were decided differently from the playbook. To update the playbook, write "'+PLAYBOOK_UPDATE_TRIGGER+'" (update playbook from deal).'}
def playbook_deviations(state,round_number=None):
	C=state or{};D=int(round_number or current_round(C));K={A.get('clause_id'):A for A in C.get('clauses')or()if isinstance(A,dict)};I,J=[],[]
	def F(x,recent):
		if not x:return
		if x not in I:I.append(x)
		if recent and x not in J:J.append(x)
	for A in C.get('lawyer_overrides')or():
		if isinstance(A,dict):F(A.get('clause_id')or A.get('clause')or'override:%s'%(A.get('para')if A.get('para')is not None else A.get('after_para')),int(A.get('round')or 0)in(D,D-1))
	for B in C.get('exception_log')or():
		if isinstance(B,dict):F(B.get('clause_id')or B.get('clause_ref')or B.get('id')or B.get('topic'),int(B.get('round')or 0)==D)
	for E in C.get('user_decisions')or():
		if isinstance(E,dict)and E.get('situation')==2 and E.get('answer_kind')=='explicit':
			for G in E.get('applies_to')or[E.get('id')]:F(G,int((K.get(G)or{}).get('decided_in_round')or 0)==D)
	for(G,L)in K.items():
		for H in L.get('concession_history')or():
			if isinstance(H,dict)and H.get('kind')=='counter_tighter'and(H.get('user_decision')or{}).get('answer_kind')=='explicit':F(G,int(H.get('round')or 0)==D)
	return I,J
AREO_CLAUSES_LINE={'he':'סעיפי AREO, שאין להם עמדה בפלייבוק והוכרעו כהצעת Areo: %d (%s).','en':'Areo clauses, with no position in the playbook, decided as Areo proposals: %d (%s).'}
AREO_UPDATE_TAIL={'he':' לעדכון הפלייבוק כתבו "'+PLAYBOOK_UPDATE_TRIGGER+'".','en':' To update the playbook, write "'+PLAYBOOK_UPDATE_TRIGGER+'" (update playbook from deal).'}
def areo_clauses_line(state,round_number=None,lang='he',with_trigger=True):
	A=state or{};D=int(round_number or current_round(A));E=A.get('numbering_map')or{};B=[A.get('clause_id')for A in A.get('clauses')or()if isinstance(A,dict)and(A.get('source_label')in('areo_proposal','הצעת Areo','Areo proposal')or A.get('areo_clause')is True)and A.get('op')!='accept'and int(A.get('decided_in_round')or 0)==D]
	if not B:return
	C='en'if str(lang or'').lower()[:2]=='en'else'he';F=', '.join(E.get(A)or A for A in B);return AREO_CLAUSES_LINE[C]%(len(B),F)+(AREO_UPDATE_TAIL[C]if with_trigger else'')
def playbook_update_line(state,round_number=None,lang='he'):
	A,B=playbook_deviations(state,round_number)
	if not B:return
	return PLAYBOOK_UPDATE_LINE['en'if str(lang or'').lower()[:2]=='en'else'he']%len(A)
CRITICAL_OPEN='MOVING','STUCK','WALK-AWAY','OPENED'
def critical_open_clauses(state):
	C=state or{};G=C.get('numbering_map')or{};H={}
	for D in C.get('user_decisions')or():
		for B in(D or{}).get('applies_to')or():
			if D.get('recommendation'):H[B]=D['recommendation']
	E=[]
	for A in C.get('clauses')or():
		if not isinstance(A,dict)or A.get('status')not in CRITICAL_OPEN:continue
		if A.get('tier')!='deal_breaker'and str(A.get('importance')or'').upper()!='CRITICAL':continue
		B=A.get('clause_id');I=H.get(B)or(A.get('escalation')or{}).get('why')or'';J=G.get(B)or A.get('contract_ref')or B;F=next((A for A in E if A['ref']==J),None)
		if F is not None:F['recommendation']=F['recommendation']or I;continue
		E.append({'clause_id':B,'ref':G.get(B)or A.get('contract_ref')or B,'status':A.get('status'),'recommendation':I})
	return E
def record_reopen(state,clause_id,instruction,reason='',round_number=None):
	F=reason;D=clause_id;C=state;B=instruction;B=(B or'').strip()
	if not B:raise ValueError('פתיחה מחדש דורשת את ההוראה של עורך הדין, במילים שלו')
	E=int(round_number or current_round(C));A=next((A for A in C.get('clauses')or()if A.get('clause_id')==D),None)
	if A is None:raise ValueError('אין בקובץ המצב סעיף %s'%D)
	G=now_iso();H={'round':E,'instruction':B,'reason':F or'','previous_status':A.get('status'),'recorded_at':G};A.setdefault('reopen_log',[]).append(H);A.setdefault('concession_history',[]).append({'round':E,'who':'us','kind':'reopen','what':'פתיחה מחדש בהוראת עורך הדין: %s'%B,'in_exchange_for':F or'','user_decision':{'answer_kind':'explicit','recorded_at':G}});A['status']='MOVING';A.pop('held_for',None)
	for I in C.get('deliberate_concessions')or():
		if I.get('clause_ref')==D:I['reopened_in_round']=E
	return H
def build_coverage(decisions,para_count=None):
	H=para_count;C,F={},[]
	for A in(decisions or{}).get('decisions',[]):
		G='for_call'if A.get('coverage')=='for_call'else COVERAGE_DECISION.get(A.get('op'));I={'clause_id':A['id'],'decision':G,'reason':A.get('reason')or A.get('internal_comment')or'','rule_ids':list(A.get('rule_ids',[]))}
		if A.get('op')=='insert_paragraph':F.append(dict(I,element_id='N-%s'%A['id'],element_type='missing_topic',after_para=A.get('after_para')))
		elif'para'in A:
			D=C.get(A['para'])
			if D is None:C[A['para']]=dict(I,element_id='E-%03d'%(A['para']+1),para=A['para'],clause_ids=[A['id']])
			else:
				D['clause_ids'].append(A['id'])
				if D['decision']!='tracked_change'and G=='tracked_change':D['decision']=G
	J=range(H)if H is not None else sorted(C);B=[]
	for E in J:B.append(C.get(E)or{'element_id':'E-%03d'%(E+1),'para':E,'decision':None,'clause_id':None,'clause_ids':[],'reason':'','rule_ids':[]});B+=[A for A in F if A.get('after_para')==E]
	B+=[A for A in F if A not in B];return B
def coverage_gaps(coverage):return[A for A in coverage or[]if A.get('decision')not in COVERAGE_DECISIONS]
def clause_map_entry(d,clause_numbers=None):
	B=clause_numbers;C={'clause_label':d.get('clause_label')or''}
	if d.get('op')=='insert_paragraph'or not isinstance(d.get('para'),int):C.update(after_para=d.get('after_para')if isinstance(d.get('after_para'),int)else None,element_id='N-%s'%d['id'],clause_number=None)
	else:A=d['para'];C.update(para=A,element_id='E-%03d'%(A+1),clause_number=B[A]if B and A<len(B)else None)
	return C
def fill_clause_map(state):
	C=state;D=C.setdefault('clause_map',{});E={}
	for A in C.get('coverage_index')or():
		for B in list(A.get('clause_ids')or())+[A.get('clause_id')]:
			if B and B not in E:E[B]=A
	F=[]
	for G in C.get('clauses')or():
		B=G.get('clause_id')
		if not B or B in D:continue
		A=E.get(B)
		if A and isinstance(A.get('para'),int):D[B]={'para':A['para'],'element_id':A.get('element_id'),'clause_number':None,'clause_label':(C.get('numbering_map')or{}).get(B,'')}
		elif A and isinstance(A.get('after_para'),int):D[B]={'after_para':A['after_para'],'element_id':A.get('element_id'),'clause_number':None,'clause_label':(C.get('numbering_map')or{}).get(B,'')}
		else:F.append(B)
	return F
def initial_status(d):
	A=d.get('status')
	if A in CLAUSE_STATUSES and A not in('CLOSED','ACCEPTED_PENDING'):return A
	if d.get('coverage')=='for_call':return'MOVING'
	if d.get('decision_code')=='A1'or d.get('op')=='accept':return'ACCEPTED_PENDING'
	return'MOVING'
def counter_tighter_concession(d,round_number):
	if d.get('kind')!='counter_tighter':return
	if not(d.get('op')=='accept'or str(d.get('decision_code')or'').startswith('A')or d.get('their_changes')=='accept'or d.get('offered_now')=='their_wording'):return
	D=d.get('concession')if isinstance(d.get('concession'),dict)else{};B=d.get('user_decision')if isinstance(d.get('user_decision'),dict)else{};E=d.get('decision_required')if isinstance(d.get('decision_required'),dict)else{};A={'round':int(round_number),'who':'us','kind':'counter_tighter','decision_id':d.get('id'),'what':D.get('what')or d.get('summary')or d.get('plain_effect')or'קבלת הצעה נגדית שלהם, הדוקה מהנסיגה','in_exchange_for':D.get('in_exchange_for')or d.get('in_exchange_for')or''};C=B.get('answer_kind')or E.get('answer_kind')
	if C in ANSWER_KINDS:
		A['user_decision']={'answer_kind':C}
		if B.get('recorded_at'):A['user_decision']['recorded_at']=B['recorded_at']
	if C!='explicit':A['status']=HELD_REQUIRES_EXPLICIT
	return A
SCHEDULE_WORD_HE={'Schedule':'תוספת','Annex':'נספח','Appendix':'נספח','Exhibit':'נספח','Attachment':'נספח'}
def schedule_label(schedules,para,number,lang='he'):
	C=number;B=para;A=schedules
	if not A or not isinstance(B,int)or B>=len(A)or not A[B]or not C:return
	D,E=A[B][0],A[B][1]
	if str(lang or'').lower()[:2]=='en':return'%s %s, paragraph %s'%(D,E,C)
	return'%s %s, פסקה %s'%(SCHEDULE_WORD_HE.get(D,D),E,C)
def build_state(transaction_id,round_number,profile=None,decisions=None,deal_dir=None,produced=(),resolution=None,gate=None,concessions=(),entity_details=None,lang='he',text_status=None,counterparty_name='',contract_type='',clause_labels=None,para_count=None,clause_numbers=None,received_texts=None,clause_schedules=None):
	P=text_status;O=entity_details;N=deal_dir;J=received_texts;I=resolution;H=lang;G=decisions;E=gate;D=round_number;B=skeleton();Q=B['meta'];Q.update(transaction_id=transaction_id,round_number=int(D),round_stage=stage_for_round(D),generated_at=now_iso(),last_updated=now_iso(),lang=H,client_name=(profile or{}).get('organization_name',''),counterparty_name=counterparty_name,contract_type=contract_type)
	if str(H or'').lower()[:2]=='en':Q['confidential']=CONFIDENTIAL_EN
	if P:B['text_status']=P
	S=clause_labels or{}
	for A in(G or{}).get('decisions',[]):
		C={'clause_id':A['id'],'decision_code':A.get('decision_code'),'op':A.get('op'),'rule_ids':list(A.get('rule_ids',[])),'policy_gate':_as_list(A.get('policy_gate')),'structural':bool(A.get('structural')),'conforming':bool(A.get('conforming'))}
		for K in('safe_wording','legal_review_required','legal_review','user_decision','tier','importance','fight_list','silent_change','dependents','conforms_to','carried_from','source_label','areo_clause'):
			if K in A:C[K]=copy.deepcopy(A[K])
		if A.get('kind')in('restore_agreed','accept_with_condition'):C['decision_kind']=A['kind']
		C['status']=initial_status(A);C['decided_in_round']=int(D)
		if C.get('legal_review_required'):C['legal_review_round']=int(D)
		if C['status']=='STUCK'and not A.get('escalation'):C['escalation']={'round':int(D),'proposed':'call','basis':A.get('escalation_basis')or'user_instruction'}
		if C['status']=='ACCEPTED_PENDING':
			C['accepted_in_round']=int(D);L=A.get('para')
			if J and isinstance(L,int)and L<len(J):C['pending_text']=J[L]
		if str(A.get('decision_code')or'').startswith('R'):C['rejections']=[{'round':int(D),'by':'us'}]
		R=counter_tighter_concession(A,D)
		if R:C['concession_history']=[R]
		B['clauses'].append(C);F=clause_map_entry(A,clause_numbers);B.setdefault('clause_map',{})[A['id']]=F;B['numbering_map'][A['id']]=S.get(A['id'])or(schedule_label(clause_schedules,F.get('para'),F['clause_number'],H)or('Clause %s'if str(H or'').lower()[:2]=='en'else'סעיף %s')%F['clause_number']if F.get('clause_number')else F['clause_label'])
	if G is not None:B['coverage_index']=build_coverage(G,para_count)
	if N:
		B['produced_documents']=[produced_document(B,N,A)for(A,B)in produced]
		if G is not None:B['decisions_file']='decisions_round_%d.json'%int(D)
	if I:B['playbook_resolution']={A:B for(A,B)in I.items()if A!='candidates'};B['playbook_source']=I.get('chosen','')
	if E:
		B['quality_gate'][E.get('mode','work')]={'passed':E.get('passed'),'codes':sorted({A['code']for A in E.get('failures',[])})};M=E.get('send_copy_record')
		if E.get('passed')and isinstance(M,dict)and M.get('path'):B['quality_gate']['send_copy']=send_copy_pending(M)
	B['deliberate_concessions']=[copy.deepcopy(A)for A in concessions]
	if O:B['entity_details']=copy.deepcopy(O)
	return B
def _as_list(x):
	if x is None:return[]
	return list(x)if isinstance(x,list)else[x]
def _walk_keys(o,path=''):
	A=path
	if isinstance(o,dict):
		for(B,C)in o.items():yield(B,A+'/'+str(B),C);yield from _walk_keys(C,A+'/'+str(B))
	elif isinstance(o,list):
		for(D,E)in enumerate(o):yield from _walk_keys(E,'%s[%d]'%(A,D))
def validate_state(state):
	X=[]
	def A(code,msg,where=None):X.append({'code':code,'message':msg,'where':where})
	B=state or{};F=B.get('meta',{})
	for D in B:
		if D not in TOP_KEYS:A('STATE_UNKNOWN_KEY','מפתח עליון שאינו במבנה: %s'%D,D)
	for D in ROOT_ONLY:
		if D in F:A('STATE_MISPLACED_KEY','%s יושב בשורש קובץ המצב, ולא ב-meta (n8-state-schema.md). השער אינו קורא אותו מ-meta; להעביר לשורש (negotiation_state.py migrate)'%D,'meta/'+D)
	for(U,E)in enumerate(B.get('time_anchors')or[]):
		if not isinstance(E,dict)or not isinstance(E.get('para'),int)or E.get('issue')not in TIME_ANCHOR_ISSUES or E.get('status')not in TIME_ANCHOR_STATUS:A('STATE_TIME_ANCHOR','עוגן זמן: {"para": <מספר>, "issue": "past|empty", "status": "answered|accepted|fixed", "answer"}','time_anchors[%d]'%U)
	L=F.get('round_stage')
	if L not in ROUND_STAGES:A('STATE_ROUND_STAGE','round_stage חייב להיות opening, response או closing: %r'%L,'meta/round_stage')
	elif F.get('round_number')and L!=stage_for_round(F['round_number']):A('STATE_ROUND_STAGE','round_stage %s אינו תואם לסבב %s'%(L,F['round_number']),'meta/round_stage')
	if str(F.get('schema_version',''))!=SCHEMA_VERSION:A('STATE_SCHEMA_VERSION','schema_version %r (נדרש %s; להמיר ב-state_migrate)'%(F.get('schema_version'),SCHEMA_VERSION))
	if B.get('text_status')and B['text_status']not in TEXT_STATUS:A('STATE_TEXT_STATUS','text_status לא מוכר: %r'%B['text_status'])
	for(D,Y,M)in _walk_keys(B):
		if D in FORBIDDEN_KEYS:A('STATE_APPROVAL_FIELD','שדה של שרשרת אישורים: %s (החלטת מוצר 1: אין שרשרת אישורים)'%D,Y)
		if D in('generated_at','last_updated','produced_at','received_at','sent_at','checked_at','recorded_at')and isinstance(M,str)and M and not ISO.match(M):A('STATE_TIMESTAMP','חותמת זמן שאינה ISO 8601 עם היסט: %s=%s'%(D,M),Y)
	N={A.get('clause_id')for A in B.get('clauses',[])}
	for C in B.get('clauses',[]):
		if'policy_gate'in C and not isinstance(C['policy_gate'],list):A('STATE_POLICY_GATE_TYPE','policy_gate חייב להיות רשימה',C.get('clause_id'))
		I=C.get('user_decision')
		if I and I.get('answer_kind')not in ANSWER_KINDS:A('STATE_USER_DECISION','answer_kind לא מוכר',C.get('clause_id'))
	d=open_point_clauses(B)
	for C in B.get('clauses',[]):
		G,J=C.get('clause_id'),C.get('status')
		if J is not None and J not in CLAUSE_STATUSES:A('STATE_CLAUSE_STATUS','status חייב להיות אחד מ: %s: %r'%(', '.join(CLAUSE_STATUSES),J),G)
		Z=premature_closed(B,C)
		if Z:A('STATE_PREMATURE_CLOSED','CLOSED רק כשהנוסח הוסכם על ידי שני הצדדים (%s). עד אז ACCEPTED_PENDING (negotiation_state.py migrate ממיר)'%Z,G)
		elif J=='CLOSED'and G in d:A('STATE_CLOSED_OPEN_POINT','סעיף CLOSED שיש עליו נקודה פתוחה לשיחה: הוא נשאר ACCEPTED_PENDING עד שהנקודה נסגרה בשיחה (closed_in_call)',G)
		e=C.get('conforming')and C.get('conforms_to')and int(C.get('decided_in_round')or 0)>=int(C.get('closed_in_round')or 0);f=int((C.get('restore_agreed')or{}).get('round')or 0)>=int(C.get('closed_in_round')or 0)>0
		if isinstance(C.get('closed_in_round'),int)and J!='CLOSED'and not e and not f and not any(isinstance(A,dict)and A.get('recorded_at')and int(A.get('round')or 0)>=C['closed_in_round']for A in C.get('reopen_log')or()):A('STATE_REOPEN_WITHOUT_INSTRUCTION','סעיף מוסכם (closed_in_round %s) שאינו CLOSED בלי הוראה רשומה של עורך הדין (negotiation_state.py reopen)'%C['closed_in_round'],G)
	if'clause_map'in B:
		g=B.get('clause_map')or{}
		for G in sorted(A for A in N if A):
			V=g.get(G)
			if not isinstance(V,dict)or not(isinstance(V.get('para'),int)or isinstance(V.get('after_para'),int)):A('STATE_CLAUSE_UNMAPPED','מזהה הכרעה בלי מיפוי לפסקה ב-clause_map: %s. כל מזהה ממופה לפסקה (para) או למקום שאחריו נכנס סעיף חדש (after_para)'%G,G)
	for D in B.get('numbering_map')or{}:
		if N and D not in N and not NEW_CLAUSE_ID.match(D):A('STATE_NUMBERING_MAP_KEY','מפתח ב-numbering_map שאינו clause_id: %s'%D,D)
	a=N|set(B.get('numbering_map')or{})
	for C in coverage_gaps(B.get('coverage_index')):A('STATE_COVERAGE_GAP','רכיב בלי הכרעה מפורשת במפתח הכיסוי: %s'%C.get('element_id'),C.get('element_id'))
	for H in B.get('deliberate_concessions',[]):
		O=H.get('clause_ref')or''
		if not O or RULE_ID.match(O)or a and O not in a:A('STATE_CLAUSE_REF','clause_ref של ויתור חייב להיות clause_id של סעיף בקובץ המצב, ולא מזהה כלל: %r'%O,H.get('topic'))
		I=H.get('user_decision')or{}
		if I.get('answer_kind')not in ANSWER_KINDS:A('STATE_USER_DECISION','ויתור בלי הכרעת משתמש (user_decision.answer_kind)',H.get('topic'))
		if H.get('crosses_red_line')and I.get('answer_kind')!='explicit'and not H.get('cure_applied'):A('STATE_RED_LINE_WITHOUT_USER_DECISION','חציית קו אדום בלי הכרעה מפורשת של המשתמש (מצב 2)',H.get('topic'))
	for P in B.get('user_decisions',[]):
		if P.get('situation')is not None and P['situation']not in SITUATIONS:A('STATE_SITUATION','מצב שאינו אחד מתשעת המצבים: %r'%P['situation'],P.get('id'))
	K=(F.get('deal_context')or{}).get('stance')if isinstance(F.get('deal_context'),dict)else None
	if K is not None:
		if not isinstance(K,dict)or K.get('value')not in STANCES or not isinstance(K.get('round'),int)or K.get('answer_kind')not in ANSWER_KINDS:A('STATE_STANCE','meta.deal_context.stance: {"value": "playbook|stricter|lenient", "round": <מספר>, "answer_kind": "explicit|delegated", "recorded_at", "history": []}','meta/deal_context/stance')
	h=B.get('positions_source')if isinstance(B.get('positions_source'),dict)else{};b=set()
	for(U,E)in enumerate(h.get('market_research_asks')or[]):
		Q='positions_source/market_research_asks[%d]'%U
		if E.get('asked_at')not in MR_ASKED_AT:A('STATE_MR_ASK','asked_at חייב להיות negotiator_batch או negotiator_round_end: %r'%E.get('asked_at'),Q)
		if E.get('answer')not in MR_ANSWERS:A('STATE_MR_ASK','answer חייב להיות yes, no או not_now (תשובה שאינה בוחרת היא not_now): %r'%E.get('answer'),Q)
		W=E.get('topics')or[]
		if not W:A('STATE_MR_ASK','הפניה לבונה בלי רשימת נושאים',Q)
		for c in W:
			if c in b:A('STATE_MR_ASK_REPEATED','הנושא כבר נשאל בעסקה הזו, ואינו נשאל שוב: %s'%c,Q)
		b.update(W)
	for R in B.get('produced_documents',[]):
		S=R.get('path','')
		if os.path.isabs(S)or re.match('^[A-Za-z]:',S)or S.startswith('\\\\'):A('STATE_PRODUCED_PATH','נתיב תוצר חייב להיות יחסי לתיקיית העסקה: %s'%S,R.get('kind'))
		if not re.fullmatch('[0-9a-f]{64}',R.get('sha256')or''):A('STATE_PRODUCED_SHA','תוצר בלי sha256',R.get('kind'))
	T=(B.get('quality_gate')or{}).get('send_copy')
	if isinstance(T,dict)and T.get('status')is not None and T['status']not in SEND_COPY_STATUSES:A('STATE_SEND_COPY_STATUS','quality_gate.send_copy.status: produced_pending_send או sent: %r'%T['status'],'quality_gate/send_copy')
	return X
