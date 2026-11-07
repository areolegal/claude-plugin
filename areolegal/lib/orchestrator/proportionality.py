# -*- coding: utf-8 -*-
# Copyright (c) Areo. All rights reserved. Licensed under the terms at https://areo.co.il/legal/terms
REJECTION_CODES='R1','R2','R3'
USER_CHOICES='send_as_is','concede_three','focused','full_response','unanswered'
ADDITION_CODE='N1'
IMPORTANCE_RANK={'critical':0,'CRITICAL':0,'high':1,'HIGH':1,'medium':2,'MEDIUM':2,'low':3,'LOW':3}
FRICTION_RANK={'high':0,'medium':1,'low':2}
LAW_FORUM_LANGUAGE='governing_law','forum','language'
PRIORITY_KINDS='critical_asset','client_data'
TXT={'he':{'summary':'%d דרישות על הנוסח שלהם, ו-%d נושאים שהוספנו (מהם %d נושאי חובה): %d בקשות בסך הכול, מול התקשרות של %s.','summary_no_value':'%d דרישות על הנוסח שלהם, ו-%d נושאים שהוספנו (מהם %d נושאי חובה): %d בקשות בסך הכול. שווי ההתקשרות לא נמסר.','options':['לשלוח כפי שהיא','לוותר מראש על שלושת הפריטים המוצעים','תגובה ממוקדת'],'cure':'ריפוי: %s','row':'מקבלים כמות שהוא את: %s. [לאשר] [להוסיף לתגובה]','yellow_kept':'הצהוב נשמר לסבב הבא'},'en':{'summary':'%d requests on their wording, and %d topics we added (%d of them mandatory): %d requests in total, against an engagement of %s.','summary_no_value':'%d requests on their wording, and %d topics we added (%d of them mandatory): %d requests in total. The value of the engagement was not provided.','options':['Send as is','Concede the three proposed items up front','A focused response'],'cure':'Cure: %s','row':'Accepting as is: %s. [Approve] [Add to the response]','yellow_kept':'The yellow position is kept for the next round'}}
def _t(lang):return TXT['en'if str(lang or'').lower()[:2]=='en'else'he']
COMMERCIAL_TOPICS={'termination_without_cause':'סיום (?:מיידי|בהודעה|בלי עילה|ללא עילה|מטעמי נוחות)|זכות סיום מיידית|terminat\\w*\\s+(?:for convenience|without cause|at any time|immediately|on notice)|for convenience|without cause','term_mismatch':'\\bתקופ[הת] (?:ה?הסכם|ההתקשרות)|תקופה וחידוש|חידוש אוטומטי|\\bterm (?:of|and renewal)\\b|\\bduration\\b|automatic(?:ally)? renew','refund':'החזר (?:יחסי|חלק יחסי|כספי)|החזר (?:ה)?(?:תשלומים|תשלום|דמי|תמורה)[^.]{0,40}(?:מראש|ששולמ|שולמ)|שולמו? מראש|\\brefund|prepaid|paid in advance','change_of_control':'שינוי (?:ב)?שליטה|change of control','cap_vs_insurance':'(?:ביטוח|insurance|insured)[^.]{0,80}(?:תקרה|cap|liabilit|אחריות|תשלומים|payment)|(?:תקרה|cap|liabilit|אחריות)[^.]{0,80}(?:ביטוח|insurance)'}
COMMERCIAL_LABELS={'he':{'termination_without_cause':'סיום בלי עילה','term_mismatch':'תקופה מול שווי העסקה או ההסכם הראשי, כשיש','refund':'החזר תשלום ששולם מראש','change_of_control':'שינוי שליטה','cap_vs_insurance':'תקרה מול ביטוח'},'en':{'termination_without_cause':'termination without cause','term_mismatch':'term against the deal value or the main agreement, if any','refund':'refund of prepaid amounts','change_of_control':'change of control','cap_vs_insurance':'cap against insurance'}}
def commercial_topic(item):
	A=item;import re
	if isinstance(A,dict):
		if A.get('commercial_topic')in COMMERCIAL_TOPICS:return A['commercial_topic']
		B=' '.join(str(A.get(B)or'')for B in('topic','summary','reason','title','clause_label'))
	else:B=str(A or'')
	return next((A for(A,C)in COMMERCIAL_TOPICS.items()if re.search(C,B,re.I)),None)
def commercial_concession_violations(concessions):return[{'code':'commercial_topic_conceded_without_separate_question','topic':A.get('topic'),'clause_ref':A.get('clause_ref'),'commercial_topic':commercial_topic(A)}for A in concessions or()if isinstance(A,dict)and commercial_topic(A)and not _explicit(A)]
def _for_call(d):return d.get('coverage')=='for_call'or d.get('held_for')=='talking_point'
def _counted(d):return not d.get('structural')and not d.get('conforming')and not _for_call(d)
def ask_key(d):return('c',d['cluster_id'])if d.get('cluster_id')else('d',d.get('id'))
def _unique_asks(decisions,codes):
	B,C=[],set()
	for A in decisions:
		if A.get('decision_code')in codes and _counted(A)and ask_key(A)not in C:C.add(ask_key(A));B.append(A)
	return B
def count_asks(decisions):C=decisions;A=_unique_asks(C,REJECTION_CODES);D={ask_key(A)for A in A};B=[A for A in _unique_asks(C,(ADDITION_CODE,))if ask_key(A)not in D];return{'rejections':len(A),'additions':len(B),'mandatory_additions':sum(1 for A in B if A.get('mandatory')),'asks':len(A)+len(B)}
NO_VALUE='','<שווי>','<value>','לא ידוע','unknown'
def summary_line(counts,value_text,lang='he'):
	B=value_text;A=counts;C=A['rejections'],A['additions'],A['mandatory_additions'],A['asks']
	if str(B or'').strip()in NO_VALUE:return _t(lang)['summary_no_value']%C
	return _t(lang)['summary']%(C+(B,))
def _concession_candidates(decisions,context=None):A=[A for A in _unique_asks(decisions,REJECTION_CODES+(ADDITION_CODE,))if not A.get('mandatory')and A.get('tier')!='deal_breaker'and not A.get('client_priority')and not A.get('never_concede')and not commercial_topic(A)and(A.get('user_decision')or{}).get('answer_kind')!='explicit'];return sorted(A,key=lambda d:(0 if d.get('their_track')=='yellow'else 1,-IMPORTANCE_RANK.get(d.get('importance','medium'),2),FRICTION_RANK.get(d.get('expected_friction','medium'),1),d.get('id','')))
def assess(decisions,fight_list_size,value_band='לא ידוע',value_text=None,user_choice=None,answer_kind=None,context=None,lang='he'):
	E=decisions;B=user_choice;C=count_asks(E);D=C['asks']>fight_list_size;A={'counts':C,'summary_line':summary_line(C,value_text,lang),'alert':D,'question_required':False,'proposed_concessions':[],'violations':[]}
	if D and B is None:A['question_required']=True;A['proposed_concessions']=[A.get('id')for A in _concession_candidates(E,context)[:3]];A['options']=list(_t(lang)['options'])
	if B=='full_response'and answer_kind!='explicit':A['violations'].append('full_response_without_explicit_answer')
	if D and B=='unanswered'and value_band in('קטנה','small'):A['violations'].append('small_deal_alert_without_question')
	return A
def _explicit(item):return(item.get('user_decision')or{}).get('answer_kind')=='explicit'
def _cure_item(it,lang='he'):A=it;return{'id':'%s-cure'%A.get('id'),'topic':_t(lang)['cure']%A.get('topic',A.get('id')),'kind':'cure','cure_of':A.get('id'),'cure_wording':A['cure_wording'],'mandatory':True,'importance':A.get('importance','high')}
def focus_round1(items,client_confirmed_law=False,max_asks=None,lang='he'):
	H=client_confirmed_law;F=lang;E=max_asks;B,C,G,D=[],[],[],[]
	for A in items:
		I=A.get('kind','other');L=A.get('playbook_red')and IMPORTANCE_RANK.get(A.get('importance','medium'),2)==0
		if A.get('chosen_option_wording'):B.append(A)
		elif I in LAW_FORUM_LANGUAGE:
			if A.get('playbook_red')and(H or _explicit(A)and A['user_decision'].get('ask')):B.append(A)
			else:
				C.append(A)
				if A.get('playbook_red')and A.get('cure_wording'):B.append(_cure_item(A,F))
				elif A.get('playbook_red')and not _explicit(A):G.append(A)
		elif I in PRIORITY_KINDS or L or A.get('client_priority')or A.get('mandatory'):B.append(A)
		elif commercial_topic(A)and not _explicit(A):G.append(A)
		elif A.get('playbook_red')and A.get('cure_wording'):C.append(A);B.append(_cure_item(A,F))
		elif(A.get('playbook_red')or _heavy(A))and not _explicit(A):D.append(A)
		else:C.append(A)
	D.sort(key=lambda i:IMPORTANCE_RANK.get(i.get('importance','medium'),2));J=len(D)if not E else max(0,E-len([A for A in B if not A.get('structural')]));B.extend(D[:J]);M=D[J:];K=''
	if C:K=_t(F)['row']%', '.join(A.get('topic',A.get('id'))for A in C)
	N=[A for A in B if not A.get('structural')];return{'asks':B,'accepted_as_is':C,'decisions_required':G,'for_call':M,'decision_row':K,'alert':bool(E)and len(N)>E,'violations':check_round1_focus(B,C,H)}
def _heavy(it):return IMPORTANCE_RANK.get(it.get('importance','medium'),2)==0 or bool(it.get('walk_away'))or it.get('red_line')is True
def check_round1_focus(asks,accepted,client_confirmed_law=False,route=None,concessions=()):
	E=asks;D=concessions;C=accepted;B=[]
	if route=='side_letter':B.append('side_letter_route')
	F=[A for A in E if not A.get('client_priority')and A.get('kind','other')=='other'and IMPORTANCE_RANK.get(A.get('importance','medium'),2)>=2 and not A.get('mandatory')];G=[A for A in C if A.get('client_priority')or A.get('kind')in PRIORITY_KINDS]
	if G and F:B.append('priority_waived_while_low_value_asked')
	for A in E:
		if A.get('kind')in LAW_FORUM_LANGUAGE and not(A.get('playbook_red')and(client_confirmed_law or _explicit(A))):B.append('law_forum_language_without_red_and_confirmation');break
	H={A.get('cure_of')for A in E if A.get('kind')=='cure'}
	for A in list(C)+list(D):
		if A.get('playbook_red')and A.get('cure_wording')and A.get('id')not in H:B.append('red_line_waived_although_cure_exists');break
	for A in list(C)+list(D):
		if A.get('chosen_option_wording'):B.append('sheet_choice_with_wording_treated_as_waiver');break
	for A in list(D):
		if A.get('playbook_red')and not A.get('cure_wording')and not _explicit(A):B.append('red_line_crossed_without_user_decision');break
	for A in list(C)+list(D):
		if A.get('kind','other')not in LAW_FORUM_LANGUAGE and _heavy(A)and not A.get('cure_wording')and not _explicit(A):B.append('critical_position_conceded_without_user_decision');break
	if commercial_concession_violations(list(C)+list(D)):B.append('commercial_topic_conceded_without_separate_question')
	return B
def round1_opening(green_feasible,yellow_is_last_fallback,intermediate=None,lang='he'):
	A=intermediate
	if green_feasible:return{'open_at':'green','question_required':False}
	if yellow_is_last_fallback:return{'open_at':'intermediate','intermediate':A,'question_required':A is None,'note':_t(lang)['yellow_kept']}
	return{'open_at':'yellow','question_required':False}
def waiver_handoff(state):
	C=[]
	for A in(state or{}).get('deliberate_concessions',[]):
		B=A.get('user_decision')or({'answer_kind':A['answer_kind']}if A.get('answer_kind')else{})
		if not A.get('reason')or B.get('answer_kind')not in('explicit','delegated')or A.get('reopened_in_round'):continue
		C.append({'topic':A.get('topic'),'clause_ref':A.get('clause_ref'),'rule_ids':A.get('rule_ids',[]),'reason':A['reason'],'user_decision':{'answer_kind':B['answer_kind'],'answer':B.get('answer'),'recorded_at':B.get('recorded_at')or A.get('recorded_at')},'crosses_red_line':bool(A.get('crosses_red_line')),'gap_codes':A.get('gap_codes',[]),'recorded_at':A.get('recorded_at'),'report_as':'accepted_risk'})
	return C
