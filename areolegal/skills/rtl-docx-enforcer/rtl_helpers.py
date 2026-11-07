# -*- coding: utf-8 -*-
# Copyright (c) Areo. All rights reserved. Licensed under the terms at https://areo.co.il/legal/terms
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
from docx.shared import Pt
RTL_STYLES=['Normal','Heading 1','Heading 2','Heading 3','Heading 4','Heading 5','Heading 6','Heading 7','Heading 8','Heading 9','List Paragraph','List Number','List Bullet','Title','Subtitle']
_ORDER_PPR='pStyle','keepNext','keepLines','pageBreakBefore','framePr','widowControl','numPr','suppressLineNumbers','pBdr','shd','tabs','suppressAutoHyphens','kinsoku','wordWrap','overflowPunct','topLinePunct','autoSpaceDE','autoSpaceDN','bidi','adjustRightInd','snapToGrid','spacing','ind','contextualSpacing','mirrorIndents','suppressOverlap','jc','textDirection','textAlignment','textboxTightWrap','outlineLvl','divId','cnfStyle','rPr','sectPr','pPrChange'
_ORDER_RPR='rStyle','rFonts','b','bCs','i','iCs','caps','smallCaps','strike','dstrike','outline','shadow','emboss','imprint','noProof','snapToGrid','vanish','webHidden','color','spacing','w','kern','position','sz','szCs','highlight','u','effect','bdr','shd','fitText','vertAlign','rtl','cs','em','lang','eastAsianLayout','specVanish','oMath','rPrChange'
_ORDER_TBLPR='tblStyle','tblpPr','tblOverlap','bidiVisual','tblStyleRowBandSize','tblStyleColBandSize','tblW','jc','tblCellSpacing','tblInd','tblBorders','shd','tblLayout','tblCellMar','tblLook','tblCaption','tblDescription','tblPrChange'
_ORDER_SECTPR='footnotePr','endnotePr','type','pgSz','pgMar','paperSrc','pgBorders','lnNumType','pgNumType','cols','formProt','vAlign','noEndnote','titlePg','textDirection','bidi','rtlGutter','docGrid','printerSettings','sectPrChange'
def _ensure(parent,tag,order):
	D=order;C=tag;A=parent;E=A.find(qn(C))
	if E is not None:return E
	G=C.split(':',1)[1];H=D.index(G);B=OxmlElement(C)
	for(I,J)in enumerate(A):
		F=J.tag.split('}')[-1]
		if F in D and D.index(F)>H:A.insert(I,B);return B
	A.append(B);return B
def _pPr(p):
	A=p._p.find(qn('w:pPr'))
	if A is None:A=OxmlElement('w:pPr');p._p.insert(0,A)
	return A
def _rPr(run):
	A=run._r.find(qn('w:rPr'))
	if A is None:A=OxmlElement('w:rPr');run._r.insert(0,A)
	return A
def set_paragraph_rtl(p):
	A=_pPr(p)
	if A.find(qn('w:bidi'))is None:_ensure(A,'w:bidi',_ORDER_PPR)
	for B in A.findall(qn('w:jc')):
		if B.get(qn('w:val'))in('right','left'):A.remove(B)
	for C in p.runs:
		if not _is_run_explicit_ltr(C):set_run_rtl(C)
	return p
def set_run_rtl(run):A=_rPr(run);_ensure(A,'w:rtl',_ORDER_RPR);return run
def _is_run_explicit_ltr(run):
	A=run._r.find(qn('w:rPr'))
	if A is None:return False
	B=A.find(qn('w:rtl'));return B is not None and B.get(qn('w:val'))in('0','false')
def set_run_ltr_explicit(run):
	A=_rPr(run)
	for B in A.findall(qn('w:rtl')):A.remove(B)
	_ensure(A,'w:rtl',_ORDER_RPR).set(qn('w:val'),'0');return run
def set_font(run,name='David',size=11,cs_name=None):B=name;A=run;A.font.name=B;A.font.size=Pt(size);D=_rPr(A);C=_ensure(D,'w:rFonts',_ORDER_RPR);C.set(qn('w:ascii'),B);C.set(qn('w:hAnsi'),B);C.set(qn('w:cs'),cs_name or B);_ensure(D,'w:szCs',_ORDER_RPR).set(qn('w:val'),str(int(size*2)));return A
def set_document_rtl(doc):
	E=doc
	for G in E.sections:F=G._sectPr;_ensure(F,'w:bidi',_ORDER_SECTPR);_ensure(F,'w:rtlGutter',_ORDER_SECTPR)
	for H in RTL_STYLES:
		try:C=E.styles[H]
		except KeyError:continue
		A=C.element.find(qn('w:pPr'))
		if A is None:A=OxmlElement('w:pPr');C.element.append(A)
		_ensure(A,'w:bidi',_ORDER_PPR)
		for I in A.findall(qn('w:jc')):A.remove(I)
		B=C.element.find(qn('w:rPr'))
		if B is None:B=OxmlElement('w:rPr');C.element.append(B)
		D=B.find(qn('w:rFonts'))
		if D is None:D=OxmlElement('w:rFonts');B.insert(0,D)
		D.set(qn('w:cs'),'David');_ensure(B,'w:rtl',_ORDER_RPR)
	return E
def add_rtl_paragraph(doc,text='',style=None,size=11,bold=False,container=None):
	C=container;D=C if C is not None else doc;A=D.add_paragraph(style=style)
	if text:B=A.add_run(text);B.bold=bold;set_font(B,size=size);set_run_rtl(B)
	set_paragraph_rtl(A);return A
def add_rtl_heading(doc,text,level=1):B=level;A=doc.add_heading('',level=B);C=A.add_run(text);set_font(C,size={0:18,1:15,2:13,3:12}.get(B,11));set_run_rtl(C);set_paragraph_rtl(A);return A
def add_mixed_rtl_paragraph(doc,parts,size=11,style=None,container=None):
	C=container;D=C if C is not None else doc;A=D.add_paragraph(style=style)
	for(E,F)in parts:
		B=A.add_run(E);set_font(B,size=size)
		if F=='ltr':set_run_ltr_explicit(B)
		else:set_run_rtl(B)
	set_paragraph_rtl(A);return A
def add_rtl_numbered_list(doc,items,size=11):
	C=[]
	for(G,H)in enumerate(items,1):
		A=doc.add_paragraph();D=A.add_run(f"{G}. ");set_font(D,size=size);set_run_ltr_explicit(D);E=A.add_run(H);set_font(E,size=size);set_run_rtl(E);set_paragraph_rtl(A);F=_pPr(A);B=F.find(qn('w:ind'))
		if B is None:B=OxmlElement('w:ind');F.append(B)
		B.set(qn('w:right'),'360');C.append(A)
	return C
def add_rtl_bullet_list(doc,items,size=11):
	C=[]
	for F in items:
		A=doc.add_paragraph(style='List Bullet');D=A.add_run(F);set_font(D,size=size);set_run_rtl(D);set_paragraph_rtl(A);E=_pPr(A);B=E.find(qn('w:ind'))
		if B is None:B=OxmlElement('w:ind');E.append(B)
		B.set(qn('w:right'),'360');C.append(A)
	return C
def set_table_rtl(table):
	B=table;A=B._tbl.find(qn('w:tblPr'))
	if A is None:A=OxmlElement('w:tblPr');B._tbl.insert(0,A)
	_ensure(A,'w:bidiVisual',_ORDER_TBLPR);E=_ensure(A,'w:tblLayout',_ORDER_TBLPR);E.set(qn('w:type'),'fixed')
	for F in B.rows:
		for G in F.cells:
			for C in G.paragraphs:
				set_paragraph_rtl(C)
				for D in C.runs:
					if not _is_run_explicit_ltr(D):set_font(D,size=10)
	return B
def final_rtl_audit(doc,verbose=True):
	D=doc;B={'paragraphs':0,'tables':0,'sections':0,'styles':0};F=D.element.body
	for G in F.iter(qn('w:p')):
		A=G.find(qn('w:pPr'))
		if A is None:A=OxmlElement('w:pPr');G.insert(0,A)
		if A.find(qn('w:bidi'))is None:_ensure(A,'w:bidi',_ORDER_PPR);B['paragraphs']+=1
	for H in F.iter(qn('w:tbl')):
		C=H.find(qn('w:tblPr'))
		if C is None:C=OxmlElement('w:tblPr');H.insert(0,C)
		if C.find(qn('w:bidiVisual'))is None:_ensure(C,'w:bidiVisual',_ORDER_TBLPR);B['tables']+=1
	for J in D.sections:
		E=J._sectPr
		if E.find(qn('w:bidi'))is None:_ensure(E,'w:bidi',_ORDER_SECTPR);B['sections']+=1
		_ensure(E,'w:rtlGutter',_ORDER_SECTPR)
	for K in RTL_STYLES[:4]:
		try:I=D.styles[K]
		except KeyError:continue
		A=I.element.find(qn('w:pPr'))
		if A is None:A=OxmlElement('w:pPr');I.element.insert(0,A)
		if A.find(qn('w:bidi'))is None:_ensure(A,'w:bidi',_ORDER_PPR);B['styles']+=1
	if verbose:print('RTL audit:',B)
	return D
def audit_schema_order(doc):
	A=0
	for(D,B)in(('w:pPr',_ORDER_PPR),('w:rPr',_ORDER_RPR),('w:tblPr',_ORDER_TBLPR),('w:sectPr',_ORDER_SECTPR)):
		for E in doc.element.body.iter(qn(D)):
			C=[B.index(A.tag.split('}')[-1])for A in E if A.tag.split('}')[-1]in B]
			if C!=sorted(C):A+=1
	return A
