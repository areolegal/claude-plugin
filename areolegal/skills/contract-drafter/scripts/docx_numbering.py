# -*- coding: utf-8 -*-
# Copyright (c) Areo. All rights reserved. Licensed under the terms at https://areo.co.il/legal/terms
import re
from docx.oxml.ns import qn
HEB_LETTERS='אבגדהוזחטיכלמנסעפצקרשת'
LITERAL_RX=re.compile('^\\s*(\\d+\\.(?:\\d+\\.?)*|\\d+(?:\\.\\d+)+\\.?)(?=\\s|\\)|$)')
def _roman(n):
	C=[(1000,'m'),(900,'cm'),(500,'d'),(400,'cd'),(100,'c'),(90,'xc'),(50,'l'),(40,'xl'),(10,'x'),(9,'ix'),(5,'v'),(4,'iv'),(1,'i')];A=''
	for(B,D)in C:
		while n>=B:A+=D;n-=B
	return A
def _fmt(n,num_fmt):
	B=num_fmt
	if B in('lowerLetter','upperLetter'):
		A=''
		while n>0:n,C=divmod(n-1,26);A=chr(97+C)+A
		return A.upper()if B=='upperLetter'else A
	if B in('lowerRoman','upperRoman'):A=_roman(n);return A.upper()if B=='upperRoman'else A
	if B in('hebrew1','hebrew2'):return HEB_LETTERS[(n-1)%len(HEB_LETTERS)]
	return str(n)
class Numbering:
	def __init__(A,doc):
		A.abstract={};A.num={};A.style_num={};C=doc.part
		try:B=C.numbering_part.element
		except(KeyError,NotImplementedError,AttributeError):B=None
		if B is not None:A._read_numbering(B)
		A._read_styles(doc);A.counters={};A.started=set()
	def _read_numbering(C,root):
		E=root;H={}
		for B in E.findall(qn('w:abstractNum')):
			A=B.get(qn('w:abstractNumId'));I={}
			for D in B.findall(qn('w:lvl')):J=int(D.get(qn('w:ilvl')));K=D.find(qn('w:start'));L=D.find(qn('w:numFmt'));M=D.find(qn('w:lvlText'));T=D.find(qn('w:isLgl'));I[J]={'start':int(K.get(qn('w:val')))if K is not None else 1,'fmt':L.get(qn('w:val'))if L is not None else'decimal','text':M.get(qn('w:val'))if M is not None else'%d.'%(J+1),'lgl':T is not None}
			N=B.find(qn('w:numStyleLink'))
			if N is not None:H[A]=N.get(qn('w:val'))
			C.abstract[A]=I
		for F in E.findall(qn('w:num')):
			U=F.get(qn('w:numId'));A=F.find(qn('w:abstractNumId')).get(qn('w:val'));O={}
			for P in F.findall(qn('w:lvlOverride')):
				Q=P.find(qn('w:startOverride'))
				if Q is not None:O[int(P.get(qn('w:ilvl')))]=int(Q.get(qn('w:val')))
			C.num[U]=A,O
		G={}
		for B in E.findall(qn('w:abstractNum')):
			R=B.find(qn('w:styleLink'))
			if R is not None:G[R.get(qn('w:val'))]=B.get(qn('w:abstractNumId'))
		for(A,S)in H.items():
			if S in G:C.abstract[A]=C.abstract.get(G[S],C.abstract[A])
	def _read_styles(K,doc):
		E={}
		for F in doc.styles.element.findall(qn('w:style')):C=F.get(qn('w:styleId'));D=F.find(qn('w:basedOn'));G=F.find(qn('w:pPr'));A=G.find(qn('w:numPr'))if G is not None else None;E[C]=D.get(qn('w:val'))if D is not None else None,A
		for C in E:
			H,B=set(),C
			while B and B not in H:
				H.add(B);D,A=E.get(B,(None,None))
				if A is not None:
					I=A.find(qn('w:numId'));J=A.find(qn('w:ilvl'))
					if I is not None:K.style_num[C]=I.get(qn('w:val')),int(J.get(qn('w:val')))if J is not None else 0
					break
				B=D
	def _num_of(B,p):
		C=p.find(qn('w:pPr'));A,D=None,0
		if C is not None:
			E=C.find(qn('w:pStyle'))
			if E is not None and E.get(qn('w:val'))in B.style_num:A,D=B.style_num[E.get(qn('w:val'))]
			F=C.find(qn('w:numPr'))
			if F is not None:
				G=F.find(qn('w:numId'));H=F.find(qn('w:ilvl'))
				if G is not None:A=G.get(qn('w:val'))
				if H is not None:D=int(H.get(qn('w:val')))
		if not A or A=='0'or A not in B.num:return
		return A,D
	def label(C,p):
		G=C._num_of(p)
		if G is None:return None,None
		E,A=G;H,I=C.num[E];J=C.abstract.get(H,{});D=J.get(A)
		if D is None or D['fmt']in('bullet','none'):return None,None
		K=H;B=C.counters.setdefault(K,{})
		if(E,A)not in C.started and A in I:
			B[A]=I[A]-1
			for F in[B for B in B if B>A]:del B[F]
		C.started.add((E,A));B[A]=B.get(A,D['start']-1)+1
		for F in[B for B in B if B>A]:del B[F]
		def L(m):A=int(m.group(1))-1;C=J.get(A,{'start':1,'fmt':'decimal'});E=B.get(A,C['start']);F='decimal'if D.get('lgl')else C['fmt'];return _fmt(E,F)
		M=re.sub('%(\\d)',L,D['text']);return M.strip(),A
def para_text(p):
	A=[]
	for B in p.iter():
		if B.tag==qn('w:t'):A.append(B.text or'')
		elif B.tag==qn('w:tab'):A.append('\t')
	return''.join(A)
def labelled_paragraphs(doc):
	H=Numbering(doc);C=[]
	for B in doc.element.body.iter(qn('w:p')):
		D=para_text(B);A,E=H.label(B);F='auto'if A else None
		if not A:
			G=LITERAL_RX.match(D)
			if G:A,F=G.group(1),'literal';E=norm_label(A).count('.')
		C.append({'p':B,'label':A,'key':norm_label(A),'level':E,'kind':F,'text':D})
	return C
def norm_label(lab):
	if not lab:return
	return lab.strip().strip('().').strip()
REF_HEAD=re.compile('(?:(?:ב|ל|מ|ש|ו|וב|ול|שב|כאמור\\s+ב)?(?:סעיפים|סעיף(?:\\s+קטן)?|ס\\"ק|ס״ק|תת[\\s-]סעיף)|\\b(?:[Ss]ections?|[Cc]lauses?|[Pp]aragraphs?))\\s*')
REF_TOKEN=re.compile('\\d+(?:\\.\\d+)*(?:\\([א-תa-z0-9]{1,3}\\))?')
REF_JOIN=re.compile('\\s*(?:,|או|ו-|ו־|ו|-|–|עד|and|or|to)\\s*')
EXTERNAL_TAIL=re.compile("^[א-ת']{0,2}\\s*(?:\\([^)]{0,12}\\)\\s*)*(?:ל|ב|של\\s+)?(?:חוק|תקנות|פקודת|צו|אמנת|הוראות\\s+החוק|Act\\b|Law\\b|Regulations?\\b|Code\\b|Ordinance\\b)|^\\s*(?:\\([^)]{0,12}\\)\\s*)*of\\s+(?:the\\s+)?(?:[A-Z][\\w'-]*\\s+){0,6}(?:Act|Law|Regulations?|Code|Ordinance)\\b")
LAW_STYLE_TOKEN=re.compile("^\\d+[א-ת]'?")
def find_refs(text):
	A=text;F=[]
	for G in REF_HEAD.finditer(A):
		D,B=G.end(),[]
		while True:
			C=REF_TOKEN.match(A,D)
			if not C:break
			B.append((C.start(),C.end(),C.group(0)));D=C.end();E=REF_JOIN.match(A,D)
			if not E or not REF_TOKEN.match(A,E.end()):break
			D=E.end()
		if not B:continue
		H=A[B[-1][1]:B[-1][1]+40]
		if EXTERNAL_TAIL.match(H)or any(LAW_STYLE_TOKEN.match(A[B:B+6])for(B,C,C)in B):continue
		F.extend(B)
	return F
def _first_num(key):A=re.match('(\\d+)',key or'');return int(A.group(1))if A else None
def assign_segments(rows):
	B,C=0,None
	for A in rows:
		if A['label']and A['level']==0:
			D=_first_num(A['key'])
			if D is not None:
				if C is not None and D<=C:B+=1
				C=D
		A['segment']=B
	return B+1
def body_segment(rows):
	A={}
	for B in rows:
		if B['label']:A[B['segment']]=A.get(B['segment'],0)+1
	return max(A,key=lambda k:(A[k],-k))if A else 0
def segment_summary(rows):
	B={}
	for A in rows:
		if A['label']and A['level']==0:C=B.setdefault(A['segment'],{'segment':A['segment'],'top_clauses':0,'first':A['text'].strip()[:40]});C['top_clauses']+=1
	return[B[A]for A in sorted(B)]
XML_SPACE='{http://www.w3.org/XML/1998/namespace}space'
def _deleted(node,p):
	A=node.getparent()
	while A is not None and A is not p:
		if A.tag in(qn('w:del'),qn('w:moveFrom')):return True
		A=A.getparent()
	return False
def text_nodes(p):return[A for A in p.iter(qn('w:t'))if not _deleted(A,p)]
def replace_spans(p,spans):
	H=spans;A,B,F=[],[],0
	for D in p.iter():
		if D.tag==qn('w:t'):
			I=len(D.text or'')
			if not _deleted(D,p):A.append(D);B.append((F,F+I))
			F+=I
		elif D.tag==qn('w:tab'):F+=1
	if not A or not H:return 0
	def J(off,is_end):
		G=is_end;D=off
		for(C,(E,F))in enumerate(B):
			if E<=D<F or G and E<D<=F:return C,D-E
		if G:
			for C in range(len(B)-1,-1,-1):
				if B[C][1]<=D:return C,B[C][1]-B[C][0]
			return 0,0
		for(C,(E,F))in enumerate(B):
			if E>=D:return C,0
		return len(A)-1,B[-1][1]-B[-1][0]
	K=0
	for(P,Q,L)in sorted(H,key=lambda x:-x[0]):
		C,M=J(P,False);E,N=J(Q,True)
		if C==E:O=A[C].text or'';A[C].text=O[:M]+L+O[N:]
		else:
			A[C].text=(A[C].text or'')[:M]+L
			for G in range(C+1,E):A[G].text=''
			A[E].text=(A[E].text or'')[N:]
		for G in range(C,E+1):A[G].set(XML_SPACE,'preserve')
		K+=1
	return K
