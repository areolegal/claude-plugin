# -*- coding: utf-8 -*-
# Copyright (c) Areo. All rights reserved. Licensed under the terms at https://areo.co.il/legal/terms
import re
_NOUN='(הסכמים|גופים|משפחות(?:\\s+תבנית)?|מסמכים)'
_CLAIM=re.compile('(?:מ-)?(\\d+)[^\\S\\n]+'+_NOUN+'(?=(?P<tail>[^.;:()\\d\\n]{0,40}))')
_VERB=re.compile('(נמצאו|נפתחו|נקראו|נספרו)[^\\S\\n]+(\\d+)')
_OWN='שלכם','של החברה'
_VERB_KEY={'נמצאו':'found','נפתחו':'opened','נקראו':'read','נספרו':'counted'}
_ONE=re.compile('(משפחת(?:\\s+תבנית)?|הסכם|גוף|מסמך)\\s+(?:אחת|אחד)(?=(?P<tail>[^.;:()\\d\\n]{0,40}))')
_NOUN_EN='(agreements|bodies|(?:template\\s+)?families|documents)'
_CLAIM_EN=re.compile('(?<![\\w.])(\\d+)[^\\S\\n]+'+_NOUN_EN+'(?=(?P<tail>[^.;:()\\d\\n]{0,40}))',re.I)
_VERB_EN=re.compile('\\b(found|opened|read|counted)[^\\S\\n]+(\\d+)\\b',re.I)
_OWN_EN='of the company','your',"company's"
_ONE_EN=re.compile('\\bone\\s+(template\\s+family|family|agreement|body|document)\\b(?=(?P<tail>[^.;:()\\d\\n]{0,40}))',re.I)
def counts(model):B=(model.get('market_research')or{}).get('counts')or{};return{A:B.get(A)for A in('found','opened','read','counted')if isinstance(B.get(A),int)}
def _families(n):
	if n==1:return'משפחת תבנית אחת של הסכמים שפורסמו ברשת ונספרה'
	return'%d משפחות תבנית של הסכמים שפורסמו ברשת ונספרו'%n
def _docs_read(n):return'מתוך מסמך אחד שנקרא'if n==1 else'מתוך %d מסמכים שנקראו'%n
def _legal(n):return'עובדת דין אחת ממקור רשמי'if n==1 else'%d עובדות דין ממקור רשמי'%n
def _families_en(n):
	if n==1:return'one template family of agreements published online, which was counted'
	return'%d template families of agreements published online, which were counted'%n
def _docs_read_en(n):return'out of one document read'if n==1 else'out of %d documents read'%n
def _legal_en(n):return'one legal fact from an official source'if n==1 else'%d legal facts from official sources'%n
def basis_sentence(model,legal_sources=None,lang='he'):
	C=legal_sources;A=counts(model)
	if'counted'not in A:return''
	if lang=='en':
		B='The playbook was built from %s'%_families_en(A['counted'])
		if A.get('read')is not None and A['read']!=A['counted']:B+=' (%s)'%_docs_read_en(A['read'])
		if C:B+=', and from %s'%_legal_en(C)
		return B+'.'
	B='הפלייבוק נבנה לפי %s'%_families(A['counted'])
	if A.get('read')is not None and A['read']!=A['counted']:B+=' (%s)'%_docs_read(A['read'])
	if C:B+=', ולפי %s'%_legal(C)
	return B+'.'
def _expected(tail,c):
	for(A,B)in(('נקראו','read'),('נמצאו','found'),('נפתחו','opened')):
		if A in tail:return B
	return'counted'
def count_claims(text,model):
	E=text;D=counts(model)
	if not E or'counted'not in D:return[]
	F=[]
	for A in _CLAIM.finditer(E):
		if any(B in A.group('tail')[:12]for B in _OWN):continue
		C=_expected(A.group('tail'),D);B=D.get(C)
		if B is not None and int(A.group(1))!=B:F.append('"%s": %s, ובספירה %s=%d'%(A.group(0).strip()[:60],A.group(1),C,B))
	for A in _ONE.finditer(E):
		if any(B in A.group('tail')[:12]for B in _OWN):continue
		C='read'if A.group(1)=='מסמך'and'שנקרא'in A.group('tail')else _expected(A.group('tail'),D);B=D.get(C)
		if B is not None and B!=1:F.append('"%s": 1, ובספירה %s=%d'%(A.group(0).strip()[:60],C,B))
	for A in _VERB.finditer(E):
		C=_VERB_KEY[A.group(1)];B=D.get(C)
		if B is not None and int(A.group(2))!=B:F.append('"%s": בספירה %s=%d'%(A.group(0),C,B))
	F+=_count_claims_en(E,D);return F
def _expected_en(tail):
	A=tail.lower()
	for(B,C)in(('read','read'),('found','found'),('opened','opened')):
		if re.search('\\b%s\\b'%B,A):return C
	return'counted'
def _count_claims_en(text,c):
	D=text;E=[]
	for A in _CLAIM_EN.finditer(D):
		F=A.group('tail')[:16].lower();G=D[max(0,A.start()-12):A.start()].lower()
		if any(A in F for A in _OWN_EN)or'company'in G:continue
		C=_expected_en(A.group('tail'));B=c.get(C)
		if B is not None and int(A.group(1))!=B:E.append('"%s": %s, ובספירה %s=%d'%(A.group(0).strip()[:60],A.group(1),C,B))
	for A in _ONE_EN.finditer(D):
		F=A.group('tail')[:16].lower()
		if any(A in F for A in _OWN_EN):continue
		C='read'if A.group(1).lower()=='document'and'read'in F else _expected_en(A.group('tail'));B=c.get(C)
		if B is not None and B!=1:E.append('"%s": 1, ובספירה %s=%d'%(A.group(0).strip()[:60],C,B))
	for A in _VERB_EN.finditer(D):
		C=A.group(1).lower();B=c.get(C)
		if B is not None and int(A.group(2))!=B:E.append('"%s": בספירה %s=%d'%(A.group(0),C,B))
	return E
