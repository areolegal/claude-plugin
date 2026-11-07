# -*- coding: utf-8 -*-
# Copyright (c) Areo. All rights reserved. Licensed under the terms at https://areo.co.il/legal/terms
import re
LETTER='[^\\W\\d_]'
HE_PREFIX='(?:[ובכלמשה]{1,3})?'
HE_SUFFIX='(?:ה|ים|ות)?'
EN_SUFFIX='(?:s|es)?'
_HE=re.compile('[\\u05d0-\\u05ea]')
def _wrap(term,is_regex=False):
	C=is_regex;B=term;F=B if C else re.escape(B);A=B if not C else re.sub('\\\\.|[\\[\\](){}?*+|^$]','',B);G=bool(_HE.search(A));D=A[:1];H=(A.split()or[''])[-1];I='(?<!%s)'%LETTER if re.match(LETTER,D or'0')or C else'';J=HE_PREFIX if G and _HE.match(D or'')else'';E=''
	if A and re.match(LETTER,A[-1])and len(H)>1:E=(HE_SUFFIX if _HE.match(A[-1])else EN_SUFFIX)+'(?!%s)'%LETTER
	return I+J+'(?:'+F+')'+E
def terms_re(terms,flags=re.I,regex_terms=()):A=[_wrap(A)for A in terms if A]+[_wrap(A,True)for A in regex_terms if A];return re.compile('|'.join(A),flags)
def find_term(text,rx):A=rx.search(text or'');return A.group(0)if A else None
def find_all(text,terms,flags=re.I):return[A for A in terms if terms_re([A],flags).search(text or'')]
