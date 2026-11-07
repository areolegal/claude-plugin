# -*- coding: utf-8 -*-
# Copyright (c) Areo. All rights reserved. Licensed under the terms at https://areo.co.il/legal/terms
import copy,json,os
FULL,RESTRICTED='full','restricted'
BY_AGREEMENT='events','commercials','guarantees','key_clauses','footnotes','timeline','review_queue'
class AudienceError(ValueError):0
def _hidden_ids(data,hide_ids,hide_types):
	B,D=set(hide_ids or()),set(hide_types or());A={A['id']for A in data.get('agreements')or[]if A.get('id')in B or A.get('type_code')in D and A.get('type_code')};C=B-{A.get('id')for A in data.get('agreements')or[]}
	if C:raise AudienceError('מזהי הסכם להסתרה שאינם בנתונים: '+', '.join(sorted(C)))
	if not A:raise AudienceError('עותק מצומצם בלי אף הסכם להסתרה אינו מצומצם. יש לציין --hide-id או --hide-type שמתאימים להסכם')
	return A
def _scrub(x,hidden,hidden_events):
	C=hidden;B=hidden_events
	if isinstance(x,dict):return{A:_scrub(D,C,B)for(A,D)in x.items()if A not in C and A not in B}
	if isinstance(x,list):
		D=[]
		for A in x:
			if isinstance(A,str)and(A in C or A in B):continue
			if isinstance(A,dict)and(A.get('agreementId')in C or A.get('eventId')in B or A.get('id')in B):continue
			D.append(_scrub(A,C,B))
		return D
	return x
def restrict(data,hide_ids=(),hide_types=()):
	C=data;from clm import money;C=copy.deepcopy(C);D=_hidden_ids(C,hide_ids,hide_types);H=[A for A in C['agreements']if A['id']in D];G=[A for A in C['agreements']if A['id']not in D];N={A['id']for A in C.get('events')or[]if A.get('agreementId')in D and A.get('id')};I={B for A in H for B in A.get('doc_ids')or[]};R={A.get('file')for A in H if A.get('file')};J={B for A in G for B in A.get('doc_ids')or[]};B={}
	for(A,E)in C.items():
		if A=='agreements':B[A]=G
		elif A=='documents':B[A]=[A for A in E if A.get('id')not in I or A.get('id')in J]
		elif A in BY_AGREEMENT:B[A]=[A for A in E if A.get('agreementId')not in D and A.get('id')not in N]
		elif A=='counterparties':
			O=[]
			for P in E:
				K=[A for A in P.get('agreements')or[]if A not in D]
				if not K:continue
				L={}
				for M in G:
					if M['id']in K and(M.get('value')or{}).get('in_portfolio'):
						for(Q,S)in((M.get('value')or{}).get('annual_by_currency')or{}).items():L[Q]=L.get(Q,0)+S
				O.append(dict(P,agreements=K,annual_by_currency=money.tidy(L)))
			B[A]=O
		elif A in('catalog','key_clause_labels','meta'):B[A]=E
		else:B[A]=_scrub(E,D,N)
	F=dict(B.get('meta')or{});F['audience']=RESTRICTED
	if isinstance(F.get('files_scanned'),int):F['files_scanned']=max(0,F['files_scanned']-len(I-J))
	B['meta']=F;_assert_clean(B,H,G,I-J,R);return B
def _assert_clean(out,gone,keep,docs,files):
	C=keep;F=json.dumps(out,ensure_ascii=False);G={A.get('title')for A in C};H={A.get('counterparty')for A in C};D={A.get('file')for A in C};A=set()
	for B in gone:
		A|={B.get('id'),B.get('number')}
		if B.get('file')not in D:A.add(B.get('file'))
		if B.get('title')not in G:A.add(B.get('title'))
		if B.get('counterparty')not in H:A.add(B.get('counterparty'))
	A|=set(docs)|set(files)-D;A.discard(None);A.discard('');E=sorted(A for A in A if isinstance(A,str)and A in F)
	if E:raise AudienceError('נשאר זכר להסכם מוסתר בנתונים המוטמעים (%d ערכים). הבנייה נעצרה'%len(E))
def build(data_path,template_path,out_path,audience=FULL,hide_ids=(),hide_types=()):
	F=hide_types;E=hide_ids;D=out_path;B=audience;H=os.path.dirname(os.path.abspath(D));os.makedirs(H,exist_ok=True)
	with open(data_path,encoding='utf-8-sig')as A:C=json.load(A)
	if B==RESTRICTED:C=restrict(C,E,F)
	elif B!=FULL:raise AudienceError('קהל לא מוכר: %r'%(B,))
	elif E or F:raise AudienceError('הסתרת הסכמים מחייבת --audience restricted')
	with open(template_path,encoding='utf-8')as A:G=A.read()
	if'__DATA__'not in G:raise ValueError('המציין __DATA__ לא נמצא בתבנית')
	I=json.dumps(C,ensure_ascii=False).replace('</','<\\/')
	with open(D,'w',encoding='utf-8')as A:A.write(G.replace('__DATA__',I))
