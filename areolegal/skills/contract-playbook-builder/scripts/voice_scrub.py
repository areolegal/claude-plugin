# -*- coding: utf-8 -*-
# Copyright (c) Areo. All rights reserved. Licensed under the terms at https://areo.co.il/legal/terms
import os,re
RULE_RE=re.compile('(?<![\\w/\\.#])R(\\d{1,3})(?![\\w-])')
SRC_RE=re.compile('(?<![\\w/\\.#])S(\\d{2,3})(?:#[A-Za-z]{0,2}\\d+)?(?![\\w-])')
CITE_RE=re.compile('(?<![\\w/\\.#])C\\d{4}(?![\\w-])')
GENERIC={'he':('נושא אחר בפלייבוק','אחד המסמכים'),'en':('another topic in the playbook','one of the documents')}
def _short_name(f):A=os.path.splitext(os.path.basename(str(f or'').replace(chr(92),'/')))[0];return re.sub('^\\s*\\d+\\s*[-.)]*\\s*','',A).strip()or A
class Scrubber:
	def __init__(B,model,lang='he'):
		C=model;B.lang='en'if str(lang or'').lower().startswith('en')else'he';C=C if isinstance(C,dict)else{};B.rules={}
		for A in C.get('rules')or[]:
			if isinstance(A,dict)and A.get('rule_id'):D=A.get('topic_name')or A.get('topic')or A.get('clause_issue')or'';B.rules[str(A['rule_id'])]=str(D).strip()
		B.sources={}
		for A in C.get('source_log')or[]:
			if isinstance(A,dict)and A.get('source_id'):B.sources[str(A['source_id'])]=_short_name(A.get('file'))
	def _rule(A,m):B=A.rules.get('R'+m.group(1))or A.rules.get('R%02d'%int(m.group(1)));return'"%s"'%B if B else GENERIC[A.lang][0]
	def _src(A,m):B=A.sources.get('S'+m.group(1))or A.sources.get('S%02d'%int(m.group(1)));return B or GENERIC[A.lang][1]
	def text(C,value):
		B=value
		if not isinstance(B,str)or not B:return B
		A=RULE_RE.sub(C._rule,B);A=SRC_RE.sub(C._src,A);A=CITE_RE.sub('',A);A=re.sub('\\(\\s*[,;]?\\s*\\)','',A);return re.sub('[ \\t]{2,}',' ',A).strip()if A!=B else B
	def deep(B,obj,skip_keys=()):
		C=skip_keys;A=obj
		if isinstance(A,dict):return{A:D if A in C else B.deep(D,C)for(A,D)in A.items()}
		if isinstance(A,list):return[B.deep(A,C)for A in A]
		return B.text(A)if isinstance(A,str)else A
