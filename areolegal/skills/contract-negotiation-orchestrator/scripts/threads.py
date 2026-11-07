# -*- coding: utf-8 -*-
# Copyright (c) Areo. All rights reserved. Licensed under the terms at https://areo.co.il/legal/terms
import os,re,secrets,sys
from lxml import etree
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
import areo_lib,common.docx_tracked as dt
W=dt.W
W14='http://schemas.microsoft.com/office/word/2010/wordml'
W15='http://schemas.microsoft.com/office/word/2012/wordml'
MC='http://schemas.openxmlformats.org/markup-compatibility/2006'
EXT_PART='word/commentsExtended.xml'
EXT_TYPE='application/vnd.openxmlformats-officedocument.wordprocessingml.commentsExtended+xml'
EXT_REL='http://schemas.microsoft.com/office/2011/relationships/commentsExtended'
def _norm(s):return re.sub('\\s+',' ',s or'').strip()
def _text(c):return _norm(' '.join(''.join(A.text or''for A in A.iter(W+'t'))for A in c.iter(W+'p')))
def _para_id(c,create=True):
	B=list(c.iter(W+'p'))
	if not B:return
	C=B[-1];A=C.get('{%s}paraId'%W14)
	if not A and create:A='%08X'%secrets.randbits(31);C.set('{%s}paraId'%W14,A)
	return A
def _root_para(pid,have):
	B=have;A=pid;C=set()
	while A in B and B[A].get('{%s}paraIdParent'%W15)and A not in C:C.add(A);A=B[A].get('{%s}paraIdParent'%W15)
	return A
def _ext_root(parts):
	A=parts
	if EXT_PART in A:return etree.fromstring(A[EXT_PART])
	B=etree.Element('{%s}commentsEx'%W15,nsmap={'w15':W15,'mc':MC});B.set('{%s}Ignorable'%MC,'w15');return B
def _write_ext(parts,root,ext):
	A=parts;A['word/comments.xml']=etree.tostring(root,xml_declaration=True,encoding='UTF-8',standalone=True);A[EXT_PART]=etree.tostring(ext,xml_declaration=True,encoding='UTF-8',standalone=True);B=A['word/_rels/document.xml.rels'].decode('utf-8')
	if EXT_REL not in B:D={int(A)for A in re.findall('Id="rId(\\d+)"',B)};E='rId%d'%(max(D or{0})+1);B=B.replace('</Relationships>','<Relationship Id="%s" Type="%s" Target="commentsExtended.xml"/></Relationships>'%(E,EXT_REL));A['word/_rels/document.xml.rels']=B.encode('utf-8')
	C=A['[Content_Types].xml'].decode('utf-8')
	if'/word/commentsExtended.xml'not in C:C=C.replace('</Types>','<Override PartName="/word/commentsExtended.xml" ContentType="%s"/></Types>'%EXT_TYPE);A['[Content_Types].xml']=C.encode('utf-8')
def apply_threads(path,replies,author):
	F=replies
	if not F:return[]
	B=dt.read_package(path);N=list(B)
	if'word/comments.xml'not in B:return[(A,'אין בועות בקובץ')for(A,B)in F]
	K=etree.fromstring(B['word/comments.xml']);L=list(K.iter(W+'comment'));O={A.get(W+'id'):A for A in L};D=_ext_root(B);C={A.get('{%s}paraId'%W15):A for A in D.iter('{%s}commentEx'%W15)};G=[]
	for(H,P)in F:
		I=O.get(str(H));M=next((A for A in L if A.get(W+'author')==author and _text(A)==_norm(P)),None)
		if I is None or M is None:G.append((H,'לא נמצאה %s'%('הבועה שלהם'if I is None else'התשובה שלנו')));continue
		E,J=_root_para(_para_id(I),C),_para_id(M)
		if E not in C:A=etree.SubElement(D,'{%s}commentEx'%W15);A.set('{%s}paraId'%W15,E);A.set('{%s}done'%W15,'0');C[E]=A
		A=C.get(J)
		if A is None:A=etree.SubElement(D,'{%s}commentEx'%W15)
		A.set('{%s}paraId'%W15,J);A.set('{%s}paraIdParent'%W15,E);A.set('{%s}done'%W15,'0');C[J]=A;G.append((H,'נענתה בשרשור'))
	_write_ext(B,K,D)
	with open(path,'wb')as Q:Q.write(dt.write_package(B,N))
	return G
def read_threads(path_or_parts):
	G=path_or_parts;D=G if isinstance(G,dict)else dt.read_package(G)
	if'word/comments.xml'not in D:return[]
	O=etree.fromstring(D['word/comments.xml']);K=etree.fromstring(D[EXT_PART])if EXT_PART in D else None;H={}
	if K is not None:
		for I in K.iter('{%s}commentEx'%W15):H[I.get('{%s}paraId'%W15)]=I.get('{%s}paraIdParent'%W15),I.get('{%s}done'%W15)=='1'
	P=dt.comment_paragraphs(etree.fromstring(D['word/document.xml']))if'word/document.xml'in D else{};B,J=[],{}
	for C in O.findall(W+'comment'):
		F=_para_id(C,create=False);A={'id':C.get(W+'id'),'author':C.get(W+'author'),'initials':C.get(W+'initials'),'date':C.get(W+'date'),'text':_text(C),'para_id':F,'done':bool(H.get(F,(None,False))[1]),'para':P.get(C.get(W+'id'))};B.append(A)
		if F:J[F]=A
	for A in B:L=H.get(A['para_id'],(None,False))[0];A['parent_id']=J[L]['id']if L in J else None
	M={A['id']:A for A in B}
	for A in B:
		E,N=A,set()
		while E.get('parent_id')in M and E['id']not in N:N.add(E['id']);E=M[E['parent_id']]
		A['root_id']=E['id']
	for A in B:
		if A['para']is None:A['para']=next((B['para']for B in B if B['id']==A['root_id']),None)
	return B
def mark_done(path,root_ids,out_path=None):
	G={str(A)for A in root_ids or()}
	if not G:return[]
	A=dt.read_package(path);K=list(A)
	if'word/comments.xml'not in A:return[]
	H=etree.fromstring(A['word/comments.xml']);D=_ext_root(A);I={A.get('{%s}paraId'%W15):A for A in D.iter('{%s}commentEx'%W15)};E=[]
	for F in read_threads(A):
		if F['root_id']not in G:continue
		J=next((A for A in H.findall(W+'comment')if A.get(W+'id')==F['id']),None);C=_para_id(J)if J is not None else None
		if not C:continue
		B=I.get(C)
		if B is None:B=etree.SubElement(D,'{%s}commentEx'%W15);B.set('{%s}paraId'%W15,C);I[C]=B
		B.set('{%s}done'%W15,'1');E.append(F['id'])
	if E:
		_write_ext(A,H,D)
		with open(out_path or path,'wb')as L:L.write(dt.write_package(A,K))
	return E
