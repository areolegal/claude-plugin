# -*- coding: utf-8 -*-
# Copyright (c) Areo. All rights reserved. Licensed under the terms at https://areo.co.il/legal/terms
import re
from clm.i18n import t as tr
VERSIONABLE={'signed','draft','negotiation_version'}
CHILD={'amendment','schedule','order'}
CO_SUFFIX=re.compile('(בע\\"?מ|בעמ|\\bltd\\b\\.?|\\blimited\\b|\\binc\\b\\.?|\\bllc\\b|\\bgmbh\\b)',re.I)
NOISE=re.compile('\\b(redline|edits|tgrnedits|tracked|final|clean|v\\d+)\\b',re.I)
HEB_NOISE=re.compile('(עקוב אחר שינויים|טיוטה נגדית|טיוטה|נוסח סופי|נקי|מלא\\d*|רגיש)')
def basename(path):return re.sub('\\.(docx|pdf|doc|txt|md|eml)$','',path.split('/')[-1],flags=re.I)
def folder(path):return path.rsplit('/',1)[0]if'/'in path else''
def norm_cp(name):A=(name or'').replace('״','"').replace('׳',"'");A=CO_SUFFIX.sub(' ',A);A=re.sub('[^\\w\\s]',' ',A);return re.sub('\\s+',' ',A).strip().lower()
def topic_key(path):A=basename(path);A=re.sub('\\(.*?\\)|\\[.*?\\]',' ',A);A=re.sub('\\d{1,2}[.\\-]\\d{1,2}[.\\-]\\d{2,4}',' ',A);A=A.replace('_',' ');A=re.split('\\s+-\\s+|,\\s*',A)[0];A=NOISE.sub(' ',A);A=HEB_NOISE.sub(' ',A);return re.sub('\\s+',' ',A).strip().lower()
def _key(d):return norm_cp(d['counterparty']),topic_key(d['file']),folder(d['file'])
def _by_date(d):return d['date']or'0000'
def _hint(d):return re.sub('\\s+',' ',(d.get('relation')or{}).get('parent_hint')or'').strip().lower()
HINT_FILLER={'הסכם','ההסכם','חוזה','מיום','בין','לבין','ובין','מתאריך','תאריך','תיקון','התיקון','נספח','בע','בעמ','agreement','contract','nda','cda','amendment','addendum','to','the','of','and','dated','between','no','number','first','second','third'}
NAME_STOP={'חברת','קבוצת','the','company'}
DATE_IN_HINT=re.compile('(?<![\\d.])(\\d{1,2})[./](\\d{1,2})[./](\\d{4})(?![\\d])')
PREFIXES='ולהבמש'
def _date_tuple(iso):A=re.match('(\\d{4})-(\\d{1,2})-(\\d{1,2})$',iso or'');return(int(A.group(3)),int(A.group(2)),int(A.group(1)))if A else None
def _parent_dates(parent):A=parent;B=A.get('signed_date')or(A.get('date')if A.get('doc_kind')=='signed'else None);return{A for A in(_date_tuple(B),_date_tuple(A.get('start_date')))if A}
def _variants(t):return{t,t[1:]}if len(t)>2 and t[0]in PREFIXES else{t}
def _words(text):return re.findall('\\w+',(text or'').replace('״','"').replace('׳',"'").lower())
def _filler(t):return bool(_variants(t)&HINT_FILLER)
def _phrase_at(phrase,words,i):B=words;A=phrase;return i+len(A)<=len(B)and all(C in _variants(B[i+A])for(A,C)in enumerate(A))
def _has_phrase(phrase,words):B=words;A=phrase;return bool(A)and any(_phrase_at(A,B,C)for C in range(len(B)))
def _name_phrases(name):A=[_words(norm_cp(A))for A in(name or'').split()];B=next((A for A in A if A and not all(_filler(A)or A in NAME_STOP for A in A)),[]);return[A for A in(_words(norm_cp(name)),B)if A]
def _name_noise(*A):return[(B,C)for A in A for(B,C)in zip(('full','first'),_name_phrases(A))]
def _strip(words,names):
	B,C=list(words),[]
	for(E,D)in sorted(names,key=lambda x:x[0]!='full'):
		A=0
		while A<len(B):
			if _phrase_at(D,B,A):del B[A:A+len(D)];C.append(E)
			else:A+=1
	return B,C
def _content_of(words):return[A for A in words if len(A)>=2 and not A.isdigit()and not _filler(A)]
def _topic_content(tk,names=()):return _content_of(_strip(_words(tk),names)[0])
def _hint_info(child,company,hint=None):B=child;A=hint;A=_hint(B)if A is None else A;E=_date_tuple(B.get('signed_date'));C=_name_noise(company,B.get('counterparty'));D,F=_strip(_words(DATE_IN_HINT.sub(' ',A)),C);return{'dates':{(int(A),int(B),int(C))for(A,B,C)in DATE_IN_HINT.findall(A)}-{E},'names':C,'rest':D,'stripped':F,'content':_content_of(D)}
def _rank(parent,info):
	C=parent;A=info;D=A['dates']&_parent_dates(C)
	if A['dates']and not D:return-1
	G=set().union(*[_variants(A)for A in A['content']])
	for H in(topic_key(C['file']),C.get('title')or'',basename(C['file'])):
		E=_strip(_words(H),A['names'])[0];B=_content_of(E);F=_has_phrase(E,A['rest'])
		if len(B)==1 and F and all(B[0]in _variants(A)for A in A['content']):return 2
		if len(B)>=2 and(F or sum(1 for A in B if A in G)>=.8*len(B)):return 2
	if D and not A['content']and A['stripped']!=['first']:return 1
	return 0
def _coverage(parent,info):
	C=info;B=parent;E=set().union(*[_variants(A)for A in C['content']]);D=.0,0
	for F in(topic_key(B['file']),B.get('title')or'',basename(B['file'])):
		A=_content_of(_strip(_words(F),C['names'])[0])
		if not A:continue
		G=set().union(*[_variants(A)for A in A]);H=sum(1 for A in C['content']if _variants(A)&G);D=max(D,(sum(1 for A in A if A in E)/len(A),H))
	return D
def _best_strong(idxs,frameworks,by_id,info):
	B=idxs
	if len(B)==1:return B[0]
	A=sorted(((_coverage(by_id[frameworks[A]['head_id']],info),A)for A in B),reverse=True);return A[0][1]if A and A[0][0]>A[1][0]else None
def _template_matches(t,buckets):C,D,B=topic_key(t['file']),folder(t['file']),norm_cp(t['counterparty']);return[A for(A,E)in buckets.items()if A[1]==C and A[2]==D and(not B or B==A[0])and any(A['doc_kind']=='negotiation_version'for A in E)]
def _parent_for(child,frameworks,by_id,company=''):
	J=company;D=by_id;C=frameworks;A=child;H=norm_cp(A['counterparty']);B=_hint(A);K=[norm_cp(D[A['head_id']]['counterparty'])for A in C];E=[A for(A,B)in enumerate(K)if H and B==H];L=[A for(A,B)in enumerate(K)if A not in E and(not H or not B)]
	if not B and len(E)==1:return E[0]
	if not B:
		B=re.sub('\\s+',' ',A.get('title')or'').strip().lower()
		if not B:return
	F=_hint_info(A,J)if B==_hint(A)else _hint_info(A,J,B);M={A:_rank(D[C[A]['head_id']],F)for A in E};G=max(M.values(),default=0);I=[A for(A,B)in M.items()if B==G]
	if G>0 and len(I)==1:return I[0]
	if G==2:return _best_strong(I,C,D,F)
	if G<=0 and L:N=[A for A in L if _rank(D[C[A]['head_id']],F)==2];return _best_strong(N,C,D,F)if N else None
def group(docs,company=''):
	M=company;E=docs;F,B,G=[],[],{};N={A['id']:A for A in E}
	for A in E:
		if A['doc_kind']in VERSIONABLE:G.setdefault(_key(A),[]).append(A)
	for C in E:
		if C['doc_kind']!='template':continue
		J=_template_matches(C,G)
		if len(J)==1:C['base_version']=True;G[J[0]].insert(0,C)
		elif len(J)>1:F.append({'kind':'ambiguous_template','group':tr('קיבוץ לבדיקה','Grouping to check'),'text':tr('תבנית בסיס %s תואמת כמה עסקאות. לא צורפה','The base template %s matches several deals, so it was not attached')%basename(C['file'])})
	for(T,H)in G.items():
		D=[A for A in H if A['doc_kind']=='signed']
		if len(D)>1:
			for O in D:B.append({'doc_ids':[O['id']],'head_id':O['id']})
			F.append({'kind':'ambiguous_group','group':tr('קיבוץ לבדיקה','Grouping to check'),'text':tr('%d הסכמים חתומים באותו נושא מול אותו צד (%s). לא קובצו','%d signed agreements on the same subject with the same party (%s). They were kept apart')%(len(D),T[1])});K=sorted([A for A in H if A['doc_kind']!='signed'],key=_by_date)
			if K:B.append({'doc_ids':[A['id']for A in K],'head_id':K[-1]['id']})
			continue
		U=[A for A in H if A.get('base_version')];V=sorted([A for A in H if not A.get('base_version')],key=_by_date);P=U+V;W=D[0]if D else P[-1];B.append({'doc_ids':[A['id']for A in P],'head_id':W['id']})
	L=list(B);Q={};X=sorted((A for A in E if A['doc_kind']in CHILD),key=lambda d:d['doc_kind']=='amendment')
	for A in X:
		I=_parent_for(A,L,N,M)
		if I is None and A['doc_kind']=='amendment'and len(B)>len(L):R=list(range(len(L),len(B)));S=_parent_for(A,[B[A]for A in R],N,M);I=R[S]if S is not None else None
		if I is not None:Q[A['id']]=I
		else:B.append({'doc_ids':[A['id']],'head_id':A['id']});F.append({'kind':'orphan','group':tr('מסמך יתום','Unlinked document'),'text':tr('לא נמצא הסכם מסגרת יחיד עבור %s. נקלט כהסכם עצמאי עד לשיוך','No single framework agreement was found for %s. It was added as a separate agreement until it is linked')%basename(A['file'])})
	return{'groups':B,'children':Q,'review':F}
