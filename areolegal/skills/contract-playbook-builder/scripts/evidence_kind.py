#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (c) Areo. All rights reserved. Licensed under the terms at https://areo.co.il/legal/terms
import json,re
from pathlib import Path
EV_KINDS='company_added','company_deleted','footnote','counterparty_unchanged','unknown'
NON_AGREEMENT_ROLES='template','guidance','policy','table','correspondence'
LAYER_WEIGHT={'signed':3,'agreement':3,'amendment':3,'guidance':2,'policy':2,'table':2,'draft':1,'form':1,'template':1,'correspondence':0}
_HEB=re.compile('[\u0590-\u05ff]')
_LATIN=re.compile('[A-Za-z]')
LAW_RX=re.compile('((?<![\\u0590-\\u05ff])(?:[וש]?(?:[בלכ]|ה|מה|[בלכ]ה)?)חוק\\s+(?!(?:את|אותו|אותה|אותם|אותן|כל)\\b)[\u0590-\u05ff\\"\'״׳]|תקנות\\s+[\u0590-\u05ff]|תקנה\\s+\\d+|פקודת\\s+[\u0590-\u05ff]|צו\\s+[\u0590-\u05ff]+\\s+[\u0590-\u05ff]|הרשות\\s+ל|רשות\\s+(?:ה|ל)[\u0590-\u05ff]+|מפר(?:ה|ים|ת)?\\s+את\\s+(?:ה)?דין|דיני\\s+ה[\u0590-\u05ff]+|בניגוד\\s+לדין|אסור\\s+(?:על\\s+פי|לפי)\\s+(?:ה)?(?:דין|חוק)|\\bGDPR\\b|\\bDirective\\b|\\bRegulation\\s+\\(|\\b[A-Z][a-z]+\\s+(?:Law|Act)\\b|\\bAct\\s+\\d{4}|\\bunlawful\\b|\\billegal\\b|\\bprohibited\\s+by\\s+law\\b|\\bviolates?\\s+(?:the\\s+)?law\\b)',re.I)
def norm(s):s=str(s or'');s=s.replace('\u200e','').replace('\u200f','').replace('\xa0',' ');s=re.sub("[‘’‚‛׳']","'",s);s=re.sub('[“”„״\\"]','"',s);s=re.sub('[‐-―]','-',s);return re.sub('\\s+',' ',s).strip().lower()
def find_extract(model,model_path=None,explicit=None):
	C=model_path;A=[explicit];E=(model or{}).get('coverage')or{};A.append(E.get('extract_ref'));A+=['../../corpus-extract.json','../corpus-extract.json','corpus-extract.json','../../Areo-נתונים/corpus-extract.json'];F=Path(C).resolve().parent if C else Path('.')
	for B in A:
		if not B:continue
		for D in(Path(B),F/B):
			try:
				if D.is_file():return json.loads(D.read_text(encoding='utf-8'))
			except(OSError,ValueError):continue
def doc_index(extract):
	B={}
	for A in(extract or{}).get('documents')or[]:
		if not isinstance(A,dict):continue
		if A.get('doc_id'):B[A['doc_id']]=A
		C=str(A.get('path')or'').replace('\\','/').rsplit('/',1)[-1]
		if C:B[norm(C)]=A
	return B
def doc_for_source(row,idx):
	B=idx;A=row
	if not A or not B:return
	C=B.get(A.get('doc_id'))
	if C:return C
	D=str(A.get('file')or A.get('agreement_name')or'').replace('\\','/').rsplit('/',1)[-1];return B.get(norm(D))
def _segments(quote):A=quote;B=re.split('\\s*(?:\\[\\s*\\.{3}\\s*\\]|\\[…\\]|…|\\.{3})\\s*',str(A or''));return[norm(A)for A in B if len(norm(A))>=12]or[norm(A)]
def _para_of(doc,ref,quote):
	B=doc.get('paragraphs')or[];D=re.search('#p(\\d+)',str(ref or''))
	if D:
		C=int(D.group(1))
		for A in B:
			if isinstance(A,dict)and A.get('i')==C:return A
		if 0<=C<len(B)and isinstance(B[C],dict):return B[C]
	E=_segments(quote)
	for A in B:
		if not isinstance(A,dict):continue
		F=norm(A.get('text',''))+' '+norm(A.get('text_reject_all',''))
		if all(A in F for A in E):return A
def ev_kind(ev,row,doc):
	A=ev;E=str((A or{}).get('ev_kind')or(A or{}).get('evidence_kind')or'').strip()
	if E in EV_KINDS:return E
	if not doc or not row:return'unknown'
	F=(A or{}).get('quote')or(A or{}).get('text')or'';C=_para_of(doc,(A or{}).get('source_ref')or(A or{}).get('source_id'),F)
	if C is None:return'unknown'
	if C.get('kind')=='footnote':return'footnote'
	B=_segments(F);G=row.get('paper');D=C.get('changes')or[];J=norm(' '.join(A.get('text','')for A in D if A.get('kind')=='ins'));K=norm(' '.join(A.get('text','')for A in D if A.get('kind')=='del'));L=[norm(A.get('text',''))for A in D if A.get('kind')=='ins'];M=[norm(A.get('text',''))for A in D if A.get('kind')=='del'];H=any(A in J for A in B)or any(len(A)>=4 and any(A in B for B in B)for A in L);I=any(A in K for A in B)or any(len(A)>=4 and any(A in B for B in B)for A in M)
	if H or I:
		if G=='theirs':return'company_deleted'if I and not H else'company_added'
		return'unknown'
	N=norm(C.get('text',''))
	if all(A in N for A in B):
		if G=='theirs':return'counterparty_unchanged'
		return'unknown'
	return'unknown'
def is_agreement(row):
	A=row
	if not isinstance(A,dict):return False
	if A.get('included')is False or A.get('exclusion_reason')=='not_agreement':return False
	if A.get('is_agreement')is False or A.get('doc_kind')in('guidance','policy','table'):return False
	return str(A.get('doc_role')or'')not in NON_AGREEMENT_ROLES
def layer_of(row):
	A=row;B=str((A or{}).get('doc_role')or'')
	if B in('guidance','policy','table')or(A or{}).get('doc_kind')in('guidance','policy','table'):return'guidance'
	if B=='template':return'template'
	return'agreement'if is_agreement(A)else'other'
def has_tracked(row):
	A=row
	for C in('has_tracked_changes','tracked_changes','negotiated'):
		if A.get(C)is True:return True
	B=A.get('tracked_counts')
	if isinstance(B,dict)and any(isinstance(A,int)and A>0 for A in B.values()):return True
	return str(A.get('doc_role')or'')=='draft'
def derived_counts(rule,source_log):
	H={A.get('source_id'):A for A in source_log or[]if isinstance(A,dict)};D,E,F=set(),set(),set()
	for B in rule.get('evidence')or[]:
		if not isinstance(B,dict)or B.get('track')not in('green','yellow','red'):continue
		C=str(B.get('source_ref')or B.get('source_id')or'').split('#')[0];A=H.get(C)
		if not A or not is_agreement(A):continue
		F.add(C);I=str(A.get('doc_role')or'')
		if I in('signed','agreement','amendment')or has_tracked(A):
			G=A.get('negotiation_id')or C;D.add(G)
			if A.get('paper')=='ours':E.add(G)
	return{'independent_negotiations':len(D),'on_company_paper':len(E),'documents_addressing':len(F)}
RATIONALE_CORE='protected_interest_and_clause_purpose','legal_risk_and_legal_framework','tradeoff_statement','green_boundary_rationale','yellow_boundary_rationale','red_boundary_rationale'
def _positions(rule):
	A=[]
	for D in('green','yellow','red'):
		B=(rule.get('traffic_light')or{}).get(D)or{}
		for C in('position','meaning'):
			if B.get(C):A.append(norm(B[C]))
	return[A for A in A if A]
def repeats_position(text,positions,topic=''):
	C=topic;A=norm(text)
	if not A:return True
	for B in positions+([norm(C)]if C else[]):
		if B and len(B)>=8:A=A.replace(B,' ')
	A=re.sub('(בנושא|הירוק הוא|הצהוב הוא|האדום הוא|the green is|the yellow is|the red is|in the topic|is|הוא|היא)\\b',' ',A);return len(re.sub('[\\s:.,;\\"\'()\\-]+','',A))<40
def rationale_complete(rule):
	C=rule;B=C.get('policy_rationale')or{};A=[]
	if not isinstance(B,dict)or not B:return False,['no_rationale']
	F=_positions(C);G=C.get('topic_name')or''
	for D in RATIONALE_CORE:
		E=B.get(D)
		if not str(E or'').strip():A.append('empty:'+D)
		elif repeats_position(E,F,G):A.append('repeats_position:'+D)
	if B.get('pass_b_pending'):A.append('pass_b_pending')
	return not A,A
def red_response(red):
	A=red
	if not isinstance(A,dict):return None,''
	for E in('response_wording','proposed_clause'):
		B=A.get(E);C=B if isinstance(B,str)else' '.join(str(B.get(A)or'')for A in('he','en'))if isinstance(B,dict)else''
		if C.strip():return'wording',C.strip()
	D=str(A.get('fallback_pointer')or A.get('response_pointer')or'').strip().lower()
	if D in('yellow','green'):return'pointer',D
	return None,''
def party_names(model):
	B=model;C=set();D=B.get('scope_summary')or{}
	for A in[B.get('company_name'),(D.get('contracting_entity')or{}).get('name')]+list(D.get('legal_entities')or[])+[A.get('counterparty')for A in B.get('source_log')or[]]:
		if isinstance(A,dict):A=A.get('name')
		A=str(A or'').strip()
		if len(A)>=3 and not A.isdigit():C.add(A)
	return sorted(C,key=len,reverse=True)
def _name_variants(name):
	A=re.sub('\\s*(בע\\"מ|בע״מ|בעמ|ltd\\.?|inc\\.?|llc|gmbh|limited|corp\\.?|corporation|co\\.)\\s*$','',name,flags=re.I).strip();B={name}
	if len(A)>=3:B.add(A)
	return B
def name_hits(text,names,company_name=''):
	C=company_name;D=[];E=str(text or'')
	for F in names:
		for A in _name_variants(F):
			if A and re.search('(?<![\\w\u0590-\u05ff])'+re.escape(A)+'(?![\\w\u0590-\u05ff])',E):
				B='החברה'if C and A in _name_variants(C)else'הצד שכנגד'
				if _LATIN.search(A)and not _HEB.search(E):B='the Company'if B=='החברה'else'the Counterparty'
				D.append({'name':A,'generic':B});break
	return D
def generic_text(text,hits):
	A=str(text or'')
	for B in hits:A=re.sub('(?<![\\w\u0590-\u05ff])'+re.escape(B['name'])+'(?![\\w\u0590-\u05ff])',B['generic'],A)
	return A
def detect_lang(text):
	A=str(text or'');B,C=len(_HEB.findall(A)),len(_LATIN.findall(A))
	if not(B or C):return''
	return'he'if B>=C else'en'
def legal_claim(text):return bool(LAW_RX.search(str(text or'')))
def integrity_flags(text):
	B=re.sub('\\s+',' ',str(text or'')).strip();A=[]
	if not B:return A
	F=B.split(' ');E=[norm(A)for A in F]
	for D in(3,4,5):
		for C in range(len(E)-2*D+1):
			if E[C:C+D]==E[C+D:C+2*D]and any(len(A)>2 for A in E[C:C+D]):A.append('repeated_phrase');break
		if'repeated_phrase'in A:break
	if re.search('[a-z]{2,}[A-Z][a-z]{2,}',B)or any(len(A)>28 and not re.search('[/\\\\:@]',A)for A in F):A.append('stuck_words')
	if re.match('^[,;:)\\]}]|^[a-z]|^(and|or|but|which|that|whereas)\\b|^(ו|או|אבל|אשר|שבו|כאשר)\\s',B):A.append('starts_midway')
	for(G,H)in(('(',')'),('[',']')):
		if B.count(G)!=B.count(H):A.append('unbalanced');break
	if'unbalanced'not in A and B.count('"')%2==1 and not re.search('\\b\\w\\"\\w\\b',B):A.append('unbalanced')
	return A
