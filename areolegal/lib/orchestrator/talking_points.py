# -*- coding: utf-8 -*-
# Copyright (c) Areo. All rights reserved. Licensed under the terms at https://areo.co.il/legal/terms
TXT={'he':{'friction':'%s: צפוי ויכוח.%s','fallback':' נסיגה מוכנה: %s.','no_fallback':' אין נסיגה מוכנה: לברר מה חשוב להם לפני שמציעים.','last':'%s: ההצעה כבר בנסיגה האחרונה. ירידה נוספת היא "נדרשת הכרעתך" (מצב 2).','call':'%s: נשאר לשיחה, בלי נוסח מכריע.','conc':'%s: ויתרנו בסבב הזה.%s','raised':' אם הנושא נפתח: %s.','legal':' טעון בדיקה משפטית: אין להציע נסיגה עד שעורך דין יסמן את הנושא "נבדק".','escalation':'%s: תקוע (STUCK). מוצעת שיחה לפני סבב נוסף, עם נימוק חדש ולא חזרה על הקודם.','closed':'הסעיף הוסכם בסבב %s','changed':'הצד השני שינה את הסעיף בסבב %s (סטטוס: %s)','request':'בקשה חדשה של הצד השני בסעיף בסבב %s','waived':'ויתור ביודעין בהכרעה מפורשת (%s)'},'en':{'friction':'%s: expect pushback.%s','fallback':' Prepared fallback: %s.','no_fallback':' No prepared fallback: find out what matters to them before offering anything.','last':'%s: our offer is already at the last fallback. Going lower needs your decision (situation 2).','call':'%s: left for the call, with no deciding wording.','conc':'%s: we conceded this round.%s','raised':' If the topic comes up: %s.','legal':' Requires legal review: offer no fallback until a lawyer marks the topic "Reviewed".','escalation':'%s: stuck (STUCK). Propose a call before another round, with new reasoning rather than repeating the old.','closed':'the clause was agreed in round %s','changed':'the other side changed the clause in round %s (status: %s)','request':'a new request by the other side on the clause in round %s','waived':'knowingly waived by an express decision (%s)'}}
def legal_review_open(d,reviewed=()):return False
def merge_points(existing,generated,clauses=None,round_number=None,lang='he'):
	L=round_number;F=[A for A in existing or()if not isinstance(A,dict)or A.get('source')!='auto'or A.get('status')=='closed_in_call'or A.get('manual')];N={A.get('id')for A in F if isinstance(A,dict)and A.get('id')};H=[A for A in generated if A.get('id')not in N]
	if not L:return F+H
	B=int(L);G=TXT['en'if str(lang or'').lower()[:2]=='en'else'he'];M={A.get('clause_id'):A for A in clauses or()if isinstance(A,dict)}
	for A in H:A.setdefault('round',B)
	import re;I={}
	for(J,C)in M.items():
		K=C.get('user_decision')or{}
		if K.get('answer_kind')=='explicit'and re.search('לוותר|ויתור ביודעין|\\bwaive',str(K.get('answer')or''),re.I):I[J]=K.get('question_id')or''
	for A in F:
		if not isinstance(A,dict)or A.get('status')in('closed_in_call','closed','superseded'):continue
		D=list(A.get('clause_ids')or())+([A['clause_id']]if A.get('clause_id')else[])
		if D and all(A in I for A in D):A['status']='superseded';A['superseded']={'round':B,'why':G['waived']%I[D[0]]}
	for A in F:
		if not isinstance(A,dict)or A.get('status')in('closed_in_call','closed','superseded')or A.get('round')is None or int(A['round'])>=B:continue
		D=list(A.get('clause_ids')or())+([A['clause_id']]if A.get('clause_id')else[])
		if not D and str(A.get('id')or'').startswith('auto:'):D=[str(A['id']).split(':',2)[2].split('#')[0]]
		E=None
		for J in D:
			C=M.get(J)or{}
			if C.get('status')=='CLOSED':E=G['closed']%C.get('closed_in_round')
			elif B in(int(C.get('their_change_round')or 0),int((C.get('reopened_by_counterparty')or{}).get('round')or 0)):E=G['changed']%(B,C.get('status'))
			elif int((C.get('their_request')or{}).get('round')or 0)==B:E=G['request']%B
			if E:break
		if E:A['status']='superseded';A['superseded']={'round':B,'why':E}
	return F+H
def _point(kind,d_or_c,topic,text):B=topic;A=d_or_c;C=A.get('id')or A.get('clause_ref')or B;return{'id':'auto:%s:%s'%(kind,C),'source':'auto','topic':B,'kind':kind,'text':text}
def build_talking_points(decisions,concessions=(),lang='he',reviewed=()):
	D=TXT['en'if str(lang or'').lower()[:2]=='en'else'he'];B=[];H={}
	for A in decisions:
		F=A.get('cluster_id')
		if F and F in H:
			for C in H[F]:
				C.setdefault('clause_ids',[])
				if A.get('id')and A['id']not in C['clause_ids']:C['clause_ids'].append(A['id'])
			continue
		I=len(B);E=A.get('topic')or A.get('clause_label')or A.get('id')
		if A.get('expected_friction')=='high':
			J=A.get('prepared_fallback')
			if legal_review_open(A,reviewed):K=D['legal']
			else:K=D['fallback']%J.rstrip('.')if J else D['no_fallback']
			B.append(_point('friction',A,E,D['friction']%(E,K)))
		if A.get('at_last_fallback'):B.append(_point('last_fallback',A,E,D['last']%E))
		if A.get('coverage')=='for_call':B.append(_point('for_call',A,E,D['call']%E))
		if A.get('escalation')or A.get('stuck_candidate'):B.append(_point('escalation',A,E,D['escalation']%E))
		if F:
			for C in B[I:]:C['clause_ids']=[A.get('id')]if A.get('id')else[]
			H[F]=B[I:]
	for G in concessions:L=G.get('if_raised');B.append(_point('concession',G,G.get('topic'),D['conc']%(G.get('topic'),D['raised']%L.rstrip('.')if L else'')))
	M={}
	for C in B:
		N=M[C['id']]=M.get(C['id'],0)+1
		if N>1:C['id']='%s#%d'%(C['id'],N)
	return B
