#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (c) Areo. All rights reserved. Licensed under the terms at https://areo.co.il/legal/terms
'מיפוי הפלייבוק להסכם, ויומן הסבבים: כללי היסוד 9, 11, 12 ו-15 של Areo בקוד.'
import argparse,json,os,re,sys
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
import areo_lib
OUTCOMES='applied','accepted_as_is','no_matching_clause'
CHANGING_OPS='replace','replace_span','insert_paragraph','delete_paragraph','comment_only'
TRACKS='green','yellow','red'
LIVE='negotiation_state.json'
NOTICE={'he':'אין סעיף בפלייבוק לנושא הזה. התשובה ניתנת על בסיס שיקול הדעת המקצועי של AREO, בלי פסיקה ובלי מקורות שלא אושרו.','en':'The playbook has no clause on this topic. AREO answered on its own professional judgment, with no case law and no unapproved sources.'}
NO_SOURCE={'he':'AREO לא מצאה מקור מורשה לנקודה זו. הצעד הבא: להוסיף לתיקיית הסכמים של החברה הסכם שמסדיר אותה, או לאשר את העמדה בפלייבוק.','en':"AREO did not find an approved source for this point. Next step: add to the company's agreements folder an agreement that covers it, or confirm the position in the playbook."}
SOURCE_PREFIX={'he':'מקור: ','en':'Source: '}
ROUND_NAMES={1:('first','סבב ראשון','Round 1 (first)'),2:('second','סבב שני','Round 2 (second)'),3:('third','סבב שלישי','Round 3 (third)'),4:('fourth','סבב רביעי','Round 4 (fourth)')}
ROUND_RULE={'first':('סבב ראשון: הפלייבוק מוחל במלואו על ההסכם. כל הנקודות פתוחות.','First round: the whole playbook is applied to the agreement. Every point is open.'),'other':('סבב המשך: מטפלים רק בנקודות הפתוחות. מה שהוסכם אינו נפתח מחדש.','Follow-up round: only the open points are handled. Agreed points are not reopened.')}
def _text(v):
	if isinstance(v,dict):
		for A in('he','text','en'):
			if isinstance(v.get(A),str)and v[A].strip():return v[A].strip()
		return''
	return v.strip()if isinstance(v,str)else''
def rules_of(playbook):
	B=playbook;C=B if isinstance(B,dict)else{};D=[]
	for A in C.get('clauses')or C.get('rules')or[]:
		if isinstance(A,dict)and(A.get('id')or A.get('rule_id')):D.append(A)
	return D
def rule_id(r):return r.get('id')or r.get('rule_id')
def rule_topic(r):return _text(r.get('title')or r.get('topic_name')or r.get('topic'))or str(rule_id(r))
def rule_position(r,track=None):
	B=track;C=r.get('traffic_light')if isinstance(r.get('traffic_light'),dict)else{}
	for A in([B]if B in TRACKS else[])+list(TRACKS):
		D=C.get(A)if isinstance(C.get(A),dict)else r.get(A)if isinstance(r.get(A),dict)else{};E=_text(D.get('position'))or(_text(D.get('red_line'))if A=='red'else'')
		if E:return A,E
	return None,''
def _source_titles(playbook):
	B={}
	for A in(playbook or{}).get('source_log')or[]:
		if isinstance(A,dict)and A.get('source_id'):B[A['source_id']]=_text(A.get('short_name')or A.get('title')or A.get('file'))
	return B
def rule_sources(r,playbook=None):
	I=_source_titles(playbook);B,C=[],set()
	for A in r.get('evidence')or[]:
		if not isinstance(A,dict):continue
		G=A.get('source_id')or A.get('source_ref');K=_text(A.get('source_ref'));D=I.get(G)or I.get(K.split('#')[0])or _text(A.get('agreement')or A.get('source_title'))or G;H=_text(A.get('clause_ref')or A.get('clause'))
		if D and(D,H)not in C:C.add((D,H));B.append({'agreement':D,'clause':H,'source_id':G or''})
	J=r.get('traffic_light')if isinstance(r.get('traffic_light'),dict)else{}
	for E in TRACKS:
		L=J.get(E)if isinstance(J.get(E),dict)else r.get(E)if isinstance(r.get(E),dict)else{};F=_text(L.get('source_label'))or _text(r.get('source_label'))
		if F and('label',F)not in C:C.add(('label',F));B.append({'agreement':'','clause':'','label':F})
	if r.get('policy_status')in('market_standard','areo_proposal')or r.get('basis')in('market_standard','areo_proposal'):B.append({'agreement':'','clause':'','label':r.get('basis')or r.get('policy_status')})
	return B
def source_text(sources,lang='he'):
	C='en'if lang=='en'else'he';B=[]
	for A in sources or[]:
		if A.get('agreement'):B.append('%s, %s'%(A['agreement'],A['clause'])if A.get('clause')else A['agreement'])
		elif A.get('label'):B.append(A['label'])
	return SOURCE_PREFIX[C]+'; '.join(B)if B else NO_SOURCE[C]
def _agreement_clauses(paras,labels,structural):
	C=labels;D=[]
	for(A,B)in enumerate(paras or[]):
		B=(B or'').strip()
		if not B or A in structural:continue
		E=C[A]if C and A<len(C)else None
		if E or len(B.split())>=8:D.append((A,E or None))
	return D
def build_map(playbook,decisions,round_number=1,deal_id='',paras=None,labels=None,declared=None,lang='he',coverage=None):
	V=coverage;U=round_number;T=playbook;L=labels;J=declared;G='en'if lang=='en'else'he';O=[A for A in decisions or[]if isinstance(A,dict)];J={A.get('rule_id'):A for A in J or[]if isinstance(A,dict)and A.get('rule_id')}
	def P(i):A=L[i]if L and isinstance(i,int)and 0<=i<len(L)else None;return A or('פסקה %s'%i if G=='he'else'paragraph %s'%i)
	H=coverage_results_view(V)if V else{};I,Q=[],set()
	for M in rules_of(T):
		D=rule_id(M);C=[A for A in O if D in(A.get('rule_ids')or[])];B=J.get(D);A={'rule_id':D,'topic':rule_topic(M),'outcome':None,'agreement_clauses':[],'decision_ids':[],'reason':''};E,W=[],[]
		for N in C:
			if N.get('op')=='insert_paragraph':
				if isinstance(N.get('after_para'),int):W.append(N['after_para'])
				continue
			F=N.get('para')
			if isinstance(F,int)and F not in E:E.append(F)
		if C:
			A['decision_ids']=[A.get('id')for A in C];R=next((A.get('offered_track')or A.get('track')for A in C if A.get('offered_track')or A.get('track')),None)
			if all(A.get('op')=='insert_paragraph'for A in C):A['outcome']='no_matching_clause';A['added_by']=A['decision_ids'];A['reason']='אין בהסכם סעיף לנושא; נוסף סעיף'if G=='he'else'No clause on this topic in the agreement; a clause was added'
			elif any(A.get('op')in CHANGING_OPS for A in C):A['outcome']='applied'
			else:A['outcome']='accepted_as_is';A['reason']=next((A.get('reason')for A in C if A.get('reason')),'')
		else:R=None
		if B and C and B.get('round')and int(B['round'])<int(U or 1):B=None;J.pop(D,None)
		if B:
			if C and B.get('outcome')!=A['outcome']:A['conflict']={'decisions':A['outcome'],'declared':B.get('outcome')}
			elif not C:A['outcome']=B.get('outcome')if B.get('outcome')in OUTCOMES else None;A['reason']=B.get('reason')or'';R=B.get('track')
			for F in B.get('agreement_paras')or[]:
				if isinstance(F,int)and F not in E:E.append(F)
		if D in H:
			A['result']=H[D]
			if not A['outcome']and H[D]in EXTRA_OUTCOMES:A['outcome']=H[D]
			elif not A['outcome']and H[D]in('applied_full','applied_partial'):A['outcome']='applied'
		A['agreement_clauses']=[P(A)for A in E]+[('נוסף אחרי %s'if G=='he'else'added after %s')%P(A)for A in W];A['paras']=E
		if A['outcome']!='no_matching_clause':Q.update(E)
		else:Q.update(E)
		X,Y=rule_position(M,R);A['track']=X;A['position']=Y;A['sources']=rule_sources(M,T);A['source_text']=source_text(A['sources'],G);A['source_found']=bool(A['sources']);I.append(A)
	Z={A.get('para')for A in O if A.get('structural')and isinstance(A.get('para'),int)};S=[]
	for(K,a)in _agreement_clauses(paras,L,Z):
		if K in Q:continue
		b=[A.get('id')for A in O if A.get('para')==K or A.get('after_para')==K];S.append({'para':K,'clause':a or P(K),'decision_ids':b,'answered_on':'areo_judgment','notice':NOTICE[G]})
	return{'round':int(U or 1),'deal_id':deal_id or'','lang':G,'rules':I,'unmatched_agreement_clauses':S,'declared':list(J.values()),'counts':{'rules':len(I),**{A:sum(1 for B in I if B['outcome']==A)for A in OUTCOMES},'no_outcome':sum(1 for A in I if not A['outcome']),**({A:sum(1 for B in I if B.get('result')==A)for A in RESULTS}if H else{}),'unmatched_agreement_clauses':len(S)}}
def _f(code,message,where='',blocking=False):return{'code':code,'message':message,'where':where,'blocking':bool(blocking)}
def check_map(pm,playbook,mode='send'):
	D=mode!='work';B=[];H=rules_of(playbook)
	if not H:return B
	if not isinstance(pm,dict)or not pm.get('rules'):B.append(_f('PLAYBOOK_MAP_MISSING','לא נבנה מיפוי של הפלייבוק להסכם: אין תוצאה רשומה לאף סעיף בפלייבוק. להריץ playbook_map.py build','',D));return B
	I={}
	for C in pm['rules']:I.setdefault(C.get('rule_id'),[]).append(C)
	for E in H:
		A=rule_id(E);F=I.get(A)or[]
		if not F:B.append(_f('PLAYBOOK_RULE_NO_OUTCOME','סעיף בפלייבוק בלי תוצאה רשומה: %s (%s)'%(A,rule_topic(E)),A,D));continue
		if len(F)>1 or F[0].get('conflict'):B.append(_f('PLAYBOOK_RULE_TWO_OUTCOMES','לסעיף %s יותר מתוצאה אחת: צריכה להיות אחת בדיוק'%A,A,D))
		C=F[0]
		if C.get('outcome')not in OUTCOMES+EXTRA_OUTCOMES:B.append(_f('PLAYBOOK_RULE_NO_OUTCOME','סעיף בפלייבוק בלי תוצאה רשומה: %s (%s)'%(A,rule_topic(E)),A,D));continue
		if C['outcome']in('applied','accepted_as_is')and not(C.get('position')or'').strip():B.append(_f('PLAYBOOK_OUTCOME_NO_POSITION','הסעיף %s נרשם %s בלי העמדה שהוחלה'%(A,C['outcome']),A,D))
		if C['outcome']in('applied','accepted_as_is')and not C.get('agreement_clauses'):B.append(_f('PLAYBOOK_OUTCOME_NO_CLAUSE','הסעיף %s נרשם %s בלי הסעיף בהסכם'%(A,C['outcome']),A,D))
		if not C.get('sources'):B.append(_f('NO_APPROVED_SOURCE','%s (%s)'%(NO_SOURCE['he'],rule_topic(E)),A,False))
	for G in pm.get('unmatched_agreement_clauses')or[]:
		if not(G.get('notice')or'').strip():B.append(_f('UNMATCHED_CLAUSE_NO_NOTICE','סעיף בהסכם בלי סעיף מקביל בפלייבוק ובלי ההודעה ללקוח: %s'%G.get('clause'),str(G.get('clause')),D))
	return B
def check_sources_shown(decisions,pm,lang='he'):
	C=[];D={A['rule_id']:A for A in(pm or{}).get('rules')or[]};E=SOURCE_PREFIX['en'if lang=='en'else'he']
	for A in decisions or[]:
		if not isinstance(A,dict)or A.get('op')=='accept'or not A.get('rule_ids'):continue
		B=A.get('internal_comment')or''
		if E.strip()not in B and NO_SOURCE['he'][:25]not in B and NO_SOURCE['en'][:25]not in B:F=[D[A]for A in A['rule_ids']if A in D];C.append(_f('SOURCE_NOT_SHOWN','ההכרעה %s נשענת על כלל בפלייבוק, ובבועה הפנימית שלה אין מקור (הסכם וסעיף)%s. להריץ playbook_map.py annotate'%(A.get('id'),''if F else' ומפה'),A.get('id'),False))
	return C
def annotate(decisions,pm,lang='he'):
	A={A['rule_id']:A for A in(pm or{}).get('rules')or[]};F=SOURCE_PREFIX['en'if lang=='en'else'he'];D=0
	for B in decisions or[]:
		if not isinstance(B,dict)or B.get('op')=='accept':continue
		E=[B for B in B.get('rule_ids')or[]if B in A]
		if not E:continue
		C=B.get('internal_comment')or''
		if F.strip()in C or NO_SOURCE['he'][:25]in C or NO_SOURCE['en'][:25]in C:continue
		G=['%s (%s)'%(A[B]['source_text'],A[B].get('topic')or'')if A[B].get('topic')else A[B]['source_text']for B in E];B['internal_comment']=(C+'\n'if C else'')+'\n'.join(G);D+=1
	return D
def round_info(n):n=int(n or 1);B,C,D=ROUND_NAMES.get(n,('later','סבב %d'%n,'Round %d'%n));A=ROUND_RULE['first'if n==1 else'other'];return{'n':n,'kind':B,'label':C,'label_en':D,'rule':A[0],'rule_en':A[1],'ordinal_distinguished':n in ROUND_NAMES}
def round_view(state,compare=None):
	D=state or{};Q=D.get('meta')or{}
	try:from orchestrator import state_builder as S;B=S.current_round(D)
	except Exception:B=int(Q.get('round_number')or 1)
	H=round_info(B);K,E,F,G,L=[],[],[],[],[];I=set()
	for C in D.get('clauses')or[]:
		if not isinstance(C,dict):continue
		A=C.get('clause_id');T=C.get('contract_ref')or(D.get('numbering_map')or{}).get(A)or A;M={'clause_id':A,'clause':T,'status':C.get('status')};R=C.get('status');O=C.get('reopened_by_counterparty')or{}
		if O and int(O.get('round')or 0)==B:G.append(dict(M,round=B,how=O.get('classification')or'reopened_by_counterparty'));I.add(A)
		if R=='CLOSED':K.append(dict(M,closed_in_round=C.get('closed_in_round')))
		elif R=='ACCEPTED_PENDING':E.append(M)
		else:F.append(M)
	for J in D.get('silent_changes')or[]:
		if isinstance(J,dict)and J.get('restore_agreed')or isinstance(J,dict)and J.get('kind')=='restore_agreed':
			A=J.get('clause_id')
			if A and A not in I:I.add(A);G.append({'clause_id':A,'clause':(D.get('numbering_map')or{}).get(A)or A,'status':'CLOSED','round':B,'how':'silent_change'})
	for N in(compare or{}).get('clauses')or[]:
		A=N.get('reopens_closed')if isinstance(N,dict)else None
		if A and A not in I:I.add(A);G.append({'clause_id':A,'clause':N.get('clause')or A,'status':'CLOSED','round':B,'how':N.get('classification')or'compare'})
	if B==1:F=F+[A for A in E];E=[]
	L=[]
	for P in F+G:
		if P.get('clause_id')and P['clause_id']not in L:L.append(P['clause_id'])
	return{'round':B,'kind':H['kind'],'label':H['label'],'label_en':H['label_en'],'rule':H['rule'],'rule_en':H['rule_en'],'deal_id':Q.get('transaction_id')or'','agreed':K,'awaiting_confirmation':E,'open':F,'changed_back_by_counterparty':G,'handle_only':L,'must_not_touch':[A['clause_id']for A in K+E if A.get('clause_id')],'counts':{'agreed':len(K),'awaiting_confirmation':len(E),'open':len(F),'changed_back':len(G)}}
def check_round_discipline(view,decisions):
	B=[];D=set(view.get('must_not_touch')or[])-set(view.get('handle_only')or[])
	for A in decisions or[]:
		C=A.get('clause_id')
		if C in D and A.get('op')in('replace','replace_span','delete_paragraph','insert_paragraph')and not(A.get('reopen')or A.get('conforming')):B.append(_f('ROUND_AGREED_POINT_TOUCHED','ההכרעה %s משנה את %s, שהוסכם. סעיף מוסכם אינו נפתח מחדש בלי הוראה רשומה'%(A.get('id'),C),A.get('id'),True))
	return B
def update_ledger(state,view):A=state.setdefault('meta',{});B=[A for A in A.get('round_ledger')or[]if isinstance(A,dict)and A.get('round')!=view['round']];B.append(view);A['round_ledger']=sorted(B,key=lambda x:x.get('round')or 0);return A['round_ledger']
COVERAGE_FILE='rule-coverage.json'
RESULTS='applied_full','applied_partial','not_applied','not_applicable'
ACTIONS='amend','keep','clarify'
EQ_KEYS='protected_party','event','subject','conditions','duration','exceptions'
EQ_VALUES='same','broader','narrower','n/a'
BASES='approved_policy','proposed_unapproved','new_recommendation'
BODY_OPS='replace','replace_span','insert_paragraph','delete_paragraph'
EXTRA_OUTCOMES='not_applied','not_applicable'
CODE_BLOCKING_COVERAGE='RULE_COVERAGE_PLAN_MISSING','RULE_COVERAGE_PLAN_INCOMPLETE','RULE_PLANNED_NOT_RESOLVED','RULE_APPLIED_BY_COMMENT_ONLY','RULE_PARTIAL_MARKED_FULL','EQUIVALENCE_MISSING','OPENING_DEPARTURE_UNEXPLAINED','POSITION_BASIS_MISSING','BASIS_APPROVAL_UNSUPPORTED'
def coverage_path(deal):return os.path.join(deal,COVERAGE_FILE)
def _now_iso():import datetime as A;return A.datetime.now(A.timezone.utc).isoformat()
def _dlist(decisions):A=decisions;B=A.get('decisions')if isinstance(A,dict)else A;return[A for A in B or[]if isinstance(A,dict)]
def rule_approved(rule,track='green'):
	B=track;A=rule
	if not isinstance(A,dict):return False
	C=A.get('traffic_light')if isinstance(A.get('traffic_light'),dict)else{};D=C.get(B)if isinstance(C.get(B),dict)else A.get(B)if isinstance(A.get(B),dict)else{};E=D.get('ingest_result')if isinstance(D.get('ingest_result'),dict)else None
	if E is not None:return E.get('counts_as_approved')is True
	return A.get('policy_status')=='Confirmed'
def _offered_track(d):
	A=str(d.get('offered')or d.get('offered_now')or d.get('offered_track')or'').strip().lower()
	if A in('','green','opening'):return'green',False
	if A.startswith('fallback')or A=='yellow':return'yellow',True
	return'red'if A=='red'else'yellow',True
def plan_skeleton(playbook,pm=None,deal_id='',playbook_name=''):
	H={A.get('rule_id'):A for A in(pm or{}).get('rules')or[]};C=[]
	for A in rules_of(playbook):
		D=rule_id(A);I,J=rule_position(A,'green');E=[]
		for B in('yellow',):
			F=A.get('traffic_light')if isinstance(A.get('traffic_light'),dict)else{};K=F.get(B)if isinstance(F.get(B),dict)else A.get(B)if isinstance(A.get(B),dict)else{};G=_text(K.get('position'))
			if G:E.append(G)
		C.append({'rule_id':D,'topic':rule_topic(A),'applies':None,'applies_reason':'','locations':list((H.get(D)or{}).get('agreement_clauses')or[]),'opening':J if I=='green'else'','allowed_fallbacks':E,'action':'','result':'','result_reason':'','result_decision_ids':[]})
	return{'version':1,'created_at':_now_iso(),'deal_id':deal_id,'playbook':playbook_name,'rules':C}
def check_plan(plan,playbook):
	D=plan;E=[]
	if not isinstance(D,dict)or not isinstance(D.get('rules'),list):return[{'code':'RULE_COVERAGE_PLAN_INCOMPLETE','message':'תוכנית הכיסוי אינה במבנה: חסר rules','where':''}]
	G={}
	for A in D['rules']:
		if isinstance(A,dict)and A.get('rule_id'):G.setdefault(A['rule_id'],A)
	for F in rules_of(playbook):
		C=rule_id(F);A=G.get(C)
		if not A:E.append({'code':'RULE_COVERAGE_PLAN_INCOMPLETE','message':'כלל בפלייבוק שאינו בתוכנית הכיסוי: %s (%s)'%(C,rule_topic(F)),'where':C});continue
		B=[]
		if not isinstance(A.get('applies'),bool):B.append('applies (true/false)')
		if not str(A.get('applies_reason')or'').strip()and A.get('applies')is False:B.append('applies_reason (חובה כשהכלל אינו חל)')
		if A.get('applies')is True:
			if not str(A.get('applies_reason')or'').strip():B.append('applies_reason')
			if not A.get('locations')and not A.get('missing_clause'):B.append('locations (או missing_clause:true כשאין בהסכם סעיף)')
			if not str(A.get('opening')or'').strip():B.append('opening')
			if not isinstance(A.get('allowed_fallbacks'),list):B.append('allowed_fallbacks (רשימה, אפשר ריקה)')
			if A.get('action')not in ACTIONS:B.append('action (%s)'%'|'.join(ACTIONS))
		if A.get('result')and A['result']not in RESULTS:B.append('result חייב להיות אחד מ: %s'%', '.join(RESULTS))
		if B:E.append({'code':'RULE_COVERAGE_PLAN_INCOMPLETE','message':'בתוכנית הכיסוי של %s (%s) חסר: %s'%(C,rule_topic(F),'; '.join(B)),'where':C})
	return E
def _plan_before_work(plan,work):
	import datetime as A
	try:
		B=A.datetime.fromisoformat(str(plan.get('created_at')))
		if B.tzinfo is None:B=B.replace(tzinfo=A.timezone.utc)
		C=A.datetime.fromtimestamp(os.path.getctime(work),tz=A.timezone.utc)
	except(TypeError,ValueError,OSError):return True
	return B<=C+A.timedelta(seconds=2)
def equivalence_problem(d):
	A=d.get('equivalence')
	if not isinstance(A,dict):return'חסר equivalence'
	B=[B for B in EQ_KEYS if A.get(B)not in EQ_VALUES]
	if B:return'equivalence חסר או לא תקין ב: %s (ערכים: %s)'%(', '.join(B),' | '.join(EQ_VALUES))
def has_open_entry(d,state=None,doc=None):
	A=doc;C=d.get('decision_required')
	if isinstance(C,dict)and C.get('required'):return True
	E={A for A in(d.get('id'),d.get('clause_id'))if A};D=[(state or{}).get('open_items')]
	if isinstance(A,dict):D+=[A.get('open_items'),A.get('open_decisions')]
	for F in D:
		for B in F or[]:
			if isinstance(B,dict)and E&(set(B.get('decision_ids')or[])|set(B.get('clause_ids')or[])):return True
	return False
def check_coverage(plan,playbook,decisions,state=None,mode='send',work=None):
	P=decisions;O=playbook;I=plan;X=mode!='work';F=[]
	def B(code,msg,where=''):F.append(_f(code,msg,where,X and code in CODE_BLOCKING_COVERAGE))
	K={rule_id(A):A for A in rules_of(O)}
	if not K:return F
	if I is None:B('RULE_COVERAGE_PLAN_MISSING','אין תוכנית כיסוי לכללי הפלייבוק (rule-coverage.json). להריץ: playbook_map.py plan, למלא, ו-check-plan, לפני העריכה');return F
	if work and not _plan_before_work(I,work):B('RULE_COVERAGE_PLAN_MISSING','תוכנית הכיסוי נוצרה אחרי קובץ העבודה: התוכנית באה לפני העריכה, ולא אחריה')
	for L in check_plan(I,O):B(L['code'],L['message'],L['where'])
	Q=_dlist(P);R={A['rule_id']:A for A in I.get('rules')or[]if isinstance(A,dict)and A.get('rule_id')}
	for(C,E)in R.items():
		M=[A for A in Q if C in(A.get('rule_ids')or[])];G=[A for A in M if A.get('op')in BODY_OPS];H=E.get('result')
		if E.get('applies')is False:
			if G:F.append(_f('RULE_NOT_APPLICABLE_BUT_EDITED','הכלל %s סומן כלא חל (%s), ויש הכרעות שמשנות נוסח: %s'%(C,E.get('applies_reason')or'-',', '.join(str(A.get('id'))for A in G)),C,False))
			continue
		if E.get('applies')is not True:continue
		if H not in RESULTS:B('RULE_PLANNED_NOT_RESOLVED','הכלל %s (%s) תוכנן כחל וללא תוצאה רשומה (applied_full | applied_partial | not_applied | not_applicable). לרשום: playbook_map.py result'%(C,E.get('topic')or C),C);continue
		if H in('applied_full','applied_partial'):
			Y=any(A.get('op')=='comment_only'for A in M)
			if not G and(E.get('action')!='keep'or Y):B('RULE_APPLIED_BY_COMMENT_ONLY','הכלל %s סומן %s, אבל ההכרעות שלו אינן משנות את גוף ההסכם (הערה בלבד). הערה אינה יישום: או תיקון בגוף, או not_applied'%(C,H),C)
			if H=='applied_full':
				S=[A for A in M if isinstance(A.get('equivalence'),dict)and'narrower'in A['equivalence'].values()]
				if S:B('RULE_PARTIAL_MARKED_FULL','הכלל %s סומן applied_full, אבל בהכרעה %s יש רכיב שקילות צר יותר מהפלייבוק (narrower). התוצאה היא applied_partial'%(C,', '.join(str(A.get('id'))for A in S)),C)
		elif H=='not_applied'and G:B('RULE_PARTIAL_MARKED_FULL','הכלל %s סומן not_applied, אבל יש לו הכרעות שמשנות נוסח (%s)'%(C,', '.join(str(A.get('id'))for A in G)),C)
	T=set()
	for A in Q:
		U=[A for A in A.get('rule_ids')or[]if A in R]
		if not U or A.get('op')=='accept':continue
		D=A.get('id')
		if A.get('op')in BODY_OPS:
			V=equivalence_problem(A)
			if V and D not in T:T.add(D);B('EQUIVALENCE_MISSING','ההכרעה %s משנה נוסח לפי כלל בפלייבוק, ו%s (שישה רכיבים: %s)'%(D,V,', '.join(EQ_KEYS)),str(D))
		J=A.get('position_basis')
		if J not in BASES:B('POSITION_BASIS_MISSING','בהכרעה %s חסר position_basis (%s)'%(D,' | '.join(BASES)),str(D))
		else:
			N,W=_offered_track(A)
			if J=='approved_policy'and not all(rule_approved(K.get(A),N)for A in U if A in K):B('BASIS_APPROVAL_UNSUPPORTED','ההכרעה %s רשומה approved_policy, והפלייבוק אינו מסמן את העמדה (מסלול %s) כמאושרת (ingest_result.counts_as_approved או policy_status=Confirmed). אין להסיק אישור מתווית ירוק'%(D,N),str(D))
			if J in('proposed_unapproved','new_recommendation')and not has_open_entry(A,state,P):B('APPROVAL_OPEN_MISSING','ההכרעה %s נשענת על עמדה שלא אושרה (%s) ואין לה רשומת הכרעה פתוחה (open_items). העבודה אינה נעצרת; ההכרעה נשארת פתוחה ללקוח'%(D,J),str(D))
		N,W=_offered_track(A)
		if W and not(str(A.get('departure_reason')or'').strip()or A.get('earlier_rejection')or A.get('user_instruction')):B('OPENING_DEPARTURE_UNEXPLAINED','ההכרעה %s מציעה עמדה שאינה עמדת הפתיחה (%s) בלי departure_reason (ובלי דחייה קודמת מתועדת או הנחיה). להסביר בדוח הפנימי'%(D,A.get('offered')or A.get('offered_now')or A.get('offered_track')),str(D))
	return F
def coverage_results_view(plan,pm_rules=None):
	B={}
	for A in(plan or{}).get('rules')or[]:
		if not isinstance(A,dict)or not A.get('rule_id'):continue
		if A.get('applies')is False and A.get('applies_reason'):B[A['rule_id']]=A.get('result')if A.get('result')in RESULTS else'not_applicable'
		elif A.get('result')in RESULTS:B[A['rule_id']]=A['result']
	return B
def _load(path,what,required=True):
	A=path
	if not A or not os.path.exists(A):
		if required:print('%s אינו קיים: %s'%(what,A));raise SystemExit(2)
		return
	with open(A,encoding='utf-8')as B:return json.load(B)
def _state_path(deal):return os.path.join(deal,LIVE)
def _state_or_skeleton(deal):
	B=deal;C=_state_path(B)
	if os.path.exists(C):return _load(C,'קובץ המצב')
	from orchestrator import state_builder as A;os.makedirs(B,exist_ok=True);D=A.skeleton();D['meta'].update(transaction_id=os.path.basename(os.path.abspath(B)),round_number=1,round_stage=A.stage_for_round(1),generated_at=A.now_iso(),last_updated=A.now_iso());print('אין עדיין קובץ מצב בעסקה: נוצר שלד לסבב 1, והמיפוי נרשם בו');return D
def _save_state(deal,state):import negotiation_state as A;return A.write_checked(deal,state)
def _decisions(path):A=_load(path,'קובץ ההכרעות');return A,(A.get('decisions')if isinstance(A,dict)else A)or[]
def _agreement(received):
	A=received
	if not A:return None,None
	import content_checks as C,common.docx_tracked as D;E=D.received_paragraphs(A)
	try:B=C.numbered_labels(A)
	except Exception:B=None
	return E,B
def cmd_build(a):
	H=_load(a.playbook,'הפלייבוק');E,K=_decisions(a.decisions);A=_state_or_skeleton(a.deal)if a.deal else{};F=(A or{}).get('meta')or{};I=F.get('playbook_map')or{};G=(E.get('round')if isinstance(E,dict)else None)or F.get('round_number')or 1;L=[dict(A,round=A.get('round')or I.get('round')or G)for A in I.get('declared')or[]if isinstance(A,dict)];M,N=_agreement(a.received);O=_load(coverage_path(a.deal),'תוכנית הכיסוי',required=False)if a.deal else None;B=build_map(H,K,G,F.get('transaction_id')or(E.get('transaction_id')if isinstance(E,dict)else''),M,N,L,a.lang,coverage=O);C=B['counts'];print('מיפוי הפלייבוק להסכם, סבב %s: %d סעיפים בפלייבוק. הוחלו: %d, התקבלו כמו שהם: %d, אין סעיף מתאים בהסכם: %d, בלי תוצאה: %d. סעיפים בהסכם בלי סעיף בפלייבוק: %d'%(B['round'],C['rules'],C['applied'],C['accepted_as_is'],C['no_matching_clause'],C['no_outcome'],C['unmatched_agreement_clauses']))
	for D in B['rules']:
		if not D['outcome']:print('  בלי תוצאה: %s (%s). לרשום: playbook_map.py declare --rule %s --outcome accepted_as_is|no_matching_clause'%(D['rule_id'],D['topic'],D['rule_id']))
		if not D['source_found']:print('  %s (%s)'%(NO_SOURCE[a.lang],D['topic']))
	for J in B['unmatched_agreement_clauses']:print('  %s: %s'%(J['clause'],J['notice']))
	P=check_map(B,H,a.mode)
	if a.deal and A:
		A.setdefault('meta',{})['playbook_map']=B
		if not any(isinstance(A,dict)and A.get('round')==int(G)for A in A['meta'].get('round_ledger')or[]):update_ledger(A,round_view(A))
		if _save_state(a.deal,A):return 3
	return 3 if any(A['blocking']for A in P)else 0
def cmd_declare(a):
	D=_state_or_skeleton(a.deal);C=D.setdefault('meta',{});B=C.setdefault('playbook_map',{'round':C.get('round_number')or 1,'rules':[],'declared':[],'unmatched_agreement_clauses':[]});E=[A for A in B.get('declared')or[]if A.get('rule_id')!=a.rule];E.append({'rule_id':a.rule,'outcome':a.outcome,'reason':a.reason or'','agreement_paras':a.para or[],'track':a.track,'round':int(B.get('round')or C.get('round_number')or 1)});B['declared']=E
	for A in B.get('rules')or[]:
		if A.get('rule_id')==a.rule and not A.get('decision_ids'):A['outcome'],A['reason']=a.outcome,a.reason or'';A['paras']=list(a.para or[]);A['agreement_clauses']=['פסקה %s'%A for A in a.para or[]];A.pop('conflict',None)
	print('נרשם: %s -> %s'%(a.rule,a.outcome));return _save_state(a.deal,D)
def cmd_check(a):
	D=_load(a.playbook,'הפלייבוק');E=_load(_state_path(a.deal),'קובץ המצב');F=(E.get('meta')or{}).get('playbook_map');B=check_map(F,D,a.mode)
	if getattr(a,'decisions',None):G,I=_decisions(a.decisions);H=_load(coverage_path(a.deal),'תוכנית הכיסוי',required=False);B=B+check_coverage(H,D,G,E,a.mode,getattr(a,'work',None))
	for A in B:print('  %s [%s] %s%s'%('כשל'if A['blocking']else'אזהרה',A['code'],A['message'],'  (%s)'%A['where']if A['where']else''))
	C=[A for A in B if A['blocking']];print('תוצאה: %s'%('נכשל: %d'%len(C)if C else'עבר'));return 3 if C else 0
def cmd_plan(a):
	C=_load(a.playbook,'הפלייבוק');A=coverage_path(a.deal)
	if os.path.exists(A)and not a.force:print('תוכנית כיסוי כבר קיימת (%s). לא נדרסת: זמן יצירתה הוא ההוכחה שנכתבה לפני העריכה. --force מחליף'%A);return 2
	D=_load(_state_path(a.deal),'קובץ המצב',required=False);E=((D or{}).get('meta')or{}).get('playbook_map');B=plan_skeleton(C,E,os.path.basename(os.path.abspath(a.deal)),os.path.basename(a.playbook));os.makedirs(a.deal,exist_ok=True)
	with open(A,'w',encoding='utf-8')as F:json.dump(B,F,ensure_ascii=False,indent=1)
	print('נכתב שלד תוכנית כיסוי ל-%d כללים: %s. למלא applies, applies_reason, locations, action; אחר כך check-plan'%(len(B['rules']),A));return 0
def cmd_check_plan(a):
	C=_load(a.playbook,'הפלייבוק');D=_load(coverage_path(a.deal),'תוכנית הכיסוי');A=check_plan(D,C)
	for B in A:print('  כשל [%s] %s'%(B['code'],B['message']))
	print('תוצאה: %s'%('נכשל: %d'%len(A)if A else'עבר'));return 3 if A else 0
def cmd_result(a):
	B=coverage_path(a.deal);C=_load(B,'תוכנית הכיסוי')
	for A in C.get('rules')or[]:
		if A.get('rule_id')==a.rule:A['result'],A['result_reason']=a.result,a.reason or'';A['result_decision_ids']=list(a.decision or[]);break
	else:print('הכלל %s אינו בתוכנית הכיסוי'%a.rule);return 2
	with open(B,'w',encoding='utf-8')as D:json.dump(C,D,ensure_ascii=False,indent=1)
	print('נרשם: %s -> %s'%(a.rule,a.result));return 0
def cmd_annotate(a):
	C=_load(a.playbook,'הפלייבוק');D,A=_decisions(a.decisions);E=_load(_state_path(a.deal),'קובץ המצב',required=False)if a.deal else None;F=((E or{}).get('meta')or{}).get('playbook_map')or build_map(C,A,lang=a.lang);G=annotate(A,F,a.lang);B=a.out or a.decisions
	with open(B,'w',encoding='utf-8')as H:json.dump(D,H,ensure_ascii=False,indent=1)
	print('שורת מקור נוספה ל-%d הכרעות (%s)'%(G,B));return 0
def cmd_rounds(a):
	C=_load(_state_path(a.deal),'קובץ המצב');A=round_view(C,_load(a.compare,'השוואת הסבב',required=False));print('%s (עסקה %s). %s'%(A['label'],A['deal_id']or'-',A['rule']));B=A['counts'];print('הוסכמו: %d. ממתינים לאישור הצד השני: %d. פתוחים: %d. הוחזרו לאחור בידי הצד השני: %d'%(B['agreed'],B['awaiting_confirmation'],B['open'],B['changed_back']))
	for D in A['changed_back_by_counterparty']:print('  סעיף מוסכם שהצד השני החזיר לאחור: %s (%s)'%(D['clause'],D['how']))
	print('מטפלים רק ב: %s'%(', '.join(A['handle_only'])or'-'));update_ledger(C,A);return _save_state(a.deal,C)
def main(argv=None):
	sys.dont_write_bytecode=True;G=argparse.ArgumentParser(description=__doc__.split('\n')[0]);B=G.add_subparsers(dest='cmd',required=True)
	for E in('build','check','annotate'):
		A=B.add_parser(E);A.add_argument('--playbook',required=True,help='playbook-core.json או playbook-model.json');A.add_argument('--lang',choices=('he','en'),default='he');A.add_argument('--deal',help='תיקיית העסקה')
		if E!='check':A.add_argument('--decisions',required=True)
		else:A.add_argument('--decisions',help='קובץ ההכרעות: מפעיל גם את בדיקות הכיסוי');A.add_argument('--work',help='קובץ העבודה: לבדיקה שהתוכנית נוצרה לפניו')
		if E=='build':A.add_argument('--received',help='הטיוטה שהתקבלה (docx): לזיהוי סעיפים בהסכם בלי סעיף בפלייבוק')
		if E!='annotate':A.add_argument('--mode',choices=('work','send'),default='send')
		else:A.add_argument('--out')
	F=B.add_parser('plan');F.add_argument('--playbook',required=True);F.add_argument('--deal',required=True);F.add_argument('--force',action='store_true');H=B.add_parser('check-plan');H.add_argument('--playbook',required=True);H.add_argument('--deal',required=True);D=B.add_parser('result');D.add_argument('--deal',required=True);D.add_argument('--rule',required=True);D.add_argument('--result',required=True,choices=RESULTS);D.add_argument('--reason');D.add_argument('--decision',action='append');C=B.add_parser('declare');C.add_argument('--deal',required=True);C.add_argument('--rule',required=True);C.add_argument('--outcome',required=True,choices=OUTCOMES);C.add_argument('--reason');C.add_argument('--para',type=int,action='append',help='פסקה בהסכם שהסעיף חל עליה (אפשר כמה)');C.add_argument('--track',choices=TRACKS);I=B.add_parser('rounds');I.add_argument('--deal',required=True);I.add_argument('--compare');J=G.parse_args(argv);return{'build':cmd_build,'declare':cmd_declare,'check':cmd_check,'annotate':cmd_annotate,'rounds':cmd_rounds,'plan':cmd_plan,'check-plan':cmd_check_plan,'result':cmd_result}[J.cmd](J)
if __name__=='__main__':sys.exit(main())
