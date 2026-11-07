# -*- coding: utf-8 -*-
# Copyright (c) Areo. All rights reserved. Licensed under the terms at https://areo.co.il/legal/terms
import re,unicodedata
from.import dates as D
SCHEMA='areo-obligations/1'
OBLIGORS='us','them','both'
STATUS='open','done','waived','not_applicable'
DOC_KINDS='main','annex','amendment','side_letter','consent'
TYPES='payment','milestone','deliverable','insurance','guarantee','reporting','notice','renewal_notice','term_end','option','audit','consent_approval','data_return_deletion','confidentiality','compliance','price_adjustment','other'
EXEC_BASIS='signed_copy','user_confirmed','negotiation_state'
LABELS={'he':{'type':{'payment':'תשלום','milestone':'אבן דרך','deliverable':'מסירה','insurance':'ביטוח','guarantee':'ערבות','reporting':'דיווח','notice':'הודעה','renewal_notice':'הודעת אי חידוש','term_end':'תום תקופה','option':'אופציה','audit':'ביקורת','consent_approval':'הסכמה או אישור','data_return_deletion':'החזרה ומחיקה של מידע','confidentiality':'סודיות','compliance':'ציות','price_adjustment':'עדכון מחיר','other':'אחר'},'obligor':{'us':'אנחנו','them':'הצד השני','both':'שני הצדדים'},'status':{'open':'פתוחה','done':'בוצעה','waived':'ויתור','not_applicable':'לא רלוונטית'},'date_status':{'computed':'מחושב','to_complete':'[להשלים]','needs_verification':'טעון אימות','needs_legal_review':'טעון בדיקה משפטית','event_driven':'תלוי באירוע','ongoing':'מתמשכת'}},'en':{'type':{'payment':'Payment','milestone':'Milestone','deliverable':'Deliverable','insurance':'Insurance','guarantee':'Guarantee','reporting':'Reporting','notice':'Notice','renewal_notice':'Non-renewal notice','term_end':'End of term','option':'Option','audit':'Audit','consent_approval':'Consent or approval','data_return_deletion':'Data return and deletion','confidentiality':'Confidentiality','compliance':'Compliance','price_adjustment':'Price adjustment','other':'Other'},'obligor':{'us':'Us','them':'Counterparty','both':'Both parties'},'status':{'open':'Open','done':'Done','waived':'Waived','not_applicable':'Not applicable'},'date_status':{'computed':'Computed','to_complete':'[to complete]','needs_verification':'Needs verification','needs_legal_review':'Needs legal review','event_driven':'Event driven','ongoing':'Continuing'}}}
MSG={'SCHEMA':('הקובץ אינו טיוטת מרשם תקינה: %s','Not a valid register draft: %s'),'NOT_EXECUTED':('ההסכם לא סומן כחתום (agreement.executed). המרשם רושם רק הסכם שנחתם; בטיוטה או בהסכם במשא ומתן אין רישום','The agreement is not marked as executed (agreement.executed). Only a signed agreement is registered'),'EXEC_BASIS':('חסר בסיס לקביעה שההסכם חתום (agreement.execution_basis: %s)','Missing basis for treating the agreement as signed (agreement.execution_basis: %s)'),'AGREEMENT_ID':('agreement_id חסר או מכיל תווים שאסורים בשם תיקייה: %r','agreement_id missing or has characters not allowed in a folder name: %r'),'OBL_ID':('מזהה חובה לא תקין או כפול: %r (נדרש obl_ וייחודי)','Invalid or duplicate obligation id: %r (obl_, unique)'),'OBL_ID_EXISTS':('%s: המזהה כבר רשום במרשם, בהסכם %s. מזהה חובה ייחודי בכל המרשם: יש לבחור קיצור הסכם אחר','%s: the id is already registered, in agreement %s. Obligation ids are unique across the register: choose another agreement abbreviation'),'OBLIGOR':('%s: obligor חייב להיות us, them או both','%s: obligor must be us, them or both'),'TYPE':('%s: סוג לא מוכר %r','%s: unknown type %r'),'SOURCE':('%s: חסר עוגן מקור (source.clause ו-source.quote)','%s: missing source anchor (source.clause and source.quote)'),'QUOTE_NOT_FOUND':('%s: הציטוט אינו מופיע מילה במילה בהסכם שחולץ: "%s"','%s: the quote is not verbatim in the extracted agreement: "%s"'),'TIMING':('%s: timing לא תקין: %s','%s: invalid timing: %s'),'HAND_DATE':('%s: תאריך יעד נכתב ביד (%s). המועד מחושב רק מ-timing','%s: due date written by hand (%s). Dates are computed from timing only'),'ANCHOR':('%s: עוגן לא מוכר %r','%s: unknown anchor %r'),'STATUS':('%s: מעמד %r בלי רישום מי ומתי (status_log עם by ו-date)','%s: status %r without a record of who and when (status_log with by and date)'),'DATE':('%s: תאריך לא תקין %r (נדרש YYYY-MM-DD)','%s: invalid date %r (YYYY-MM-DD)'),'W_DEPARTMENT':('%s: אין מחלקה אחראית','%s: no responsible department'),'W_DELIVERY':('%s: הודעה בלי סעיף הודעות, אופן מסירה או כתובת (agreement.notices: %s)','%s: notice without a notices clause, delivery method or address (agreement.notices: %s)'),'W_TRACKED':('במסמך %s יש שינויים במעקב או הערות. ודאו שזה הנוסח החתום','Document %s has tracked changes or comments. Make sure this is the signed version'),'W_NO_CORPUS':('הציטוטים לא אומתו מול ההסכם (לא סופק --corpus)','Quotes were not verified (no --corpus)')}
ANCHORS='signing_date','effective_date','end_date','term_end','renewal_date'
_BAD_ID=re.compile('[<>:"/\\\\|?*\\x00-\\x1f]')
def lang_key(lang):return'en'if str(lang or'').lower().startswith('en')else'he'
def msg(code,lang,*A):B=MSG[code][1 if lang_key(lang)=='en'else 0];return B%A if A else B
def label(kind,value,lang):A=value;return LABELS[lang_key(lang)][kind].get(A,A or'')
def norm(s):s=unicodedata.normalize('NFKC',s or'');s=re.sub('[\u200e\u200f\u202a-\u202e\u2066-\u2069\xad]','',s);s=re.sub('[‘’׳`]',"'",s);s=re.sub('[“”״„]','"',s);s=re.sub('[‐-―−]','-',s);return re.sub('\\s+',' ',s).strip().lower()
def corpus_text(corpus):
	C=corpus;D=[];E=C.get('documents')if isinstance(C,dict)else None
	for F in E if isinstance(E,list)else[]:
		for B in F.get('paragraphs')or[]if isinstance(F,dict)else[]:
			if not isinstance(B,dict):continue
			H=[norm(A.get('text'))for A in B.get('hidden')or[]if isinstance(A,dict)]
			for I in('text','text_reject_all'):
				A=B.get(I)
				if not isinstance(A,str)or not A:continue
				A=norm(A)
				for G in H:
					if G:A=A.replace(G,' ',1)
				D.append(A)
	return norm(' \n '.join(D))
PLACEHOLDERS='[להשלים]','[to complete]'
def delivery_gaps(notices):A=notices;B=A if isinstance(A,dict)else{};return[A for A in('clause','method','to_them')if not str(B.get(A)or'').strip()or str(B.get(A)).strip().lower()in PLACEHOLDERS]
def tracked_docs(corpus):return[A.get('path')for A in(corpus or{}).get('documents',[])if A.get('has_tracked_changes')or A.get('has_comments')]
def _date_ok(v):return v in(None,'')or D.parse(v)is not None
def _check_off(off):A=off;return isinstance(A,dict)and A.get('unit')in D.UNITS and str(A.get('n','')).lstrip('-').isdigit()and A.get('direction','after')in('after','before')
def _check_timing(tm,ids,custom):
	A=tm
	if not isinstance(A,dict)or A.get('kind')not in D.KINDS:return'kind',None
	B=A['kind']
	if A.get('qualifier')and A['qualifier']not in D.QUALIFIERS:return'qualifier',None
	def F(a):
		if a is None:return True
		if D.parse(a):return True
		if a in ANCHORS:return True
		if isinstance(a,str)and a.startswith('custom:'):return a[7:]in custom
		if isinstance(a,str)and a.startswith('obl:'):return a[4:]in ids
		return False
	if B=='fixed'and not D.parse(A.get('date')):return'fixed.date',None
	if B=='relative':
		if not A.get('anchor'):return'relative.anchor',None
		if not _check_off(A.get('offset')):return'relative.offset',None
	if B=='recurring':
		C=A.get('every')
		if not isinstance(C,dict)or C.get('unit')not in D.UNITS or not str(C.get('n','')).isdigit()or int(C['n'])<1 or not A.get('start'):return'recurring.every/start',None
		if A.get('start_offset')and not _check_off(A['start_offset']):return'recurring.start_offset',None
	if B=='event'and not A.get('event'):return'event.event',None
	if B=='event'and A.get('offset')and not _check_off(A['offset']):return'event.offset',None
	if B=='survival'and A.get('period')not in(None,'indefinite')and not(isinstance(A['period'],dict)and A['period'].get('unit')in D.UNITS):return'survival.period',None
	for E in('anchor','start','until'):
		if E in A and not F(A[E]):return None,A[E]
	return None,None
def check_draft(draft,corpus=None,lang='he'):
	M=corpus;L=draft;N,O=[],[];A=lambda code,*A:N.append((code,msg(code,lang,*A)));P=lambda code,*A:O.append((code,msg(code,lang,*A)))
	if not isinstance(L,dict)or L.get('schema')!=SCHEMA:A('SCHEMA','schema != %s'%SCHEMA);return N,O
	E,S=L.get('agreement'),L.get('obligations')
	if not isinstance(E,dict)or not isinstance(S,list):A('SCHEMA','agreement / obligations');return N,O
	F=E.get('agreement_id')
	if not F or not isinstance(F,str)or _BAD_ID.search(F)or F.strip()!=F or F in('.','..'):A('AGREEMENT_ID',F)
	if E.get('executed')is not True:A('NOT_EXECUTED')
	if E.get('execution_basis')not in EXEC_BASIS:A('EXEC_BASIS',E.get('execution_basis'))
	G=E.get('dates')or{}
	for H in('signing_date','effective_date','end_date'):
		if not _date_ok(G.get(H)):A('DATE','agreement.dates.'+H,G.get(H))
	X={}
	for(H,T)in(G.get('anchors')or{}).items():
		U=T.get('date')if isinstance(T,dict)else T
		if not _date_ok(U):A('DATE','anchors.'+H,U)
		X[H]=U
	if G.get('initial_term')and not(isinstance(G['initial_term'],dict)and G['initial_term'].get('unit')in D.UNITS):A('TIMING','agreement','dates.initial_term')
	I=G.get('auto_renewal')
	if I and not(isinstance(I,dict)and isinstance(I.get('period'),dict)and I['period'].get('unit')in D.UNITS and(I.get('notice')is None or _check_off(dict(I['notice'],direction='before')))):A('TIMING','agreement','dates.auto_renewal')
	K=E.get('business_days')
	if K is not None and not(isinstance(K,dict)and isinstance(K.get('weekend',[]),list)and all(str(A).strip().casefold()in D.DAY_NAMES for A in K.get('weekend',[]))and isinstance(K.get('calendars',[]),list)):A('TIMING','agreement','business_days')
	J=E.get('notice_delivery')
	if J is not None:
		Q=J.get('deemed_after')if isinstance(J,dict)else None
		if not isinstance(J,dict)or Q is not None and not(isinstance(Q,dict)and Q.get('unit')in D.UNITS and str(Q.get('n','')).isdigit())or J.get('cutoff_time')and not re.match('^\\d{1,2}:\\d{2}$',str(J['cutoff_time'])):A('TIMING','agreement','notice_delivery')
	for Y in E.get('documents')or[]:
		if Y.get('kind')not in DOC_KINDS:A('SCHEMA','documents.kind %r'%Y.get('kind'))
	Z=corpus_text(M)if M else None
	if M is None:P('W_NO_CORPUS')
	else:
		for f in tracked_docs(M):P('W_TRACKED',f)
	g,a={A.get('id')for A in S if isinstance(A,dict)},set();h=E.get('notices')or{}
	for C in S:
		if not isinstance(C,dict):A('SCHEMA','obligation is not an object');continue
		B=C.get('id')
		if not isinstance(B,str)or not B.startswith('obl_')or B in a:A('OBL_ID',B)
		a.add(B)
		if C.get('obligor')not in OBLIGORS:A('OBLIGOR',B)
		if C.get('type')not in TYPES:A('TYPE',B,C.get('type'))
		b=C.get('source')or{};V=b.get('quote')
		if not b.get('clause')or not V:A('SOURCE',B)
		elif Z is not None and norm(V)not in Z:A('QUOTE_NOT_FOUND',B,V[:90])
		if C.get('due_date'):A('HAND_DATE',B,C.get('due_date'))
		c,d=_check_timing(C.get('timing'),g,X)
		if c:A('TIMING',B,c)
		if d is not None:A('ANCHOR',B,d)
		R=C.get('status','open')
		if R not in STATUS:A('STATUS',B,R)
		elif R!='open':
			W=C.get('status_log')or[]
			if not W or not W[-1].get('by')or not D.parse(W[-1].get('date')):A('STATUS',B,R)
		if not C.get('department'):P('W_DEPARTMENT',B)
		e=delivery_gaps(h)
		if C.get('type')in('notice','renewal_notice')and C.get('obligor')in('us','both')and e:P('W_DELIVERY',B,', '.join(e))
	return N,O
