# -*- coding: utf-8 -*-
# Copyright (c) Areo. All rights reserved. Licensed under the terms at https://areo.co.il/legal/terms
import datetime as _dt,re,zipfile
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Pt
from lxml import etree
W_NS='http://schemas.openxmlformats.org/wordprocessingml/2006/main'
HEBREW_FONT='David'
_ORDER_PPR='pStyle','keepNext','keepLines','pageBreakBefore','framePr','widowControl','numPr','suppressLineNumbers','pBdr','shd','tabs','suppressAutoHyphens','kinsoku','wordWrap','overflowPunct','topLinePunct','autoSpaceDE','autoSpaceDN','bidi','adjustRightInd','snapToGrid','spacing','ind','contextualSpacing','mirrorIndents','suppressOverlap','jc','textDirection','textAlignment','textboxTightWrap','outlineLvl','divId','cnfStyle','rPr','sectPr','pPrChange'
_ORDER_RPR='rStyle','rFonts','b','bCs','i','iCs','caps','smallCaps','strike','dstrike','outline','shadow','emboss','imprint','noProof','snapToGrid','vanish','webHidden','color','spacing','w','kern','position','sz','szCs','highlight','u','effect','bdr','shd','fitText','vertAlign','rtl','cs','em','lang','eastAsianLayout','specVanish','oMath','rPrChange'
_ORDER_TBLPR='tblStyle','tblpPr','tblOverlap','bidiVisual','tblStyleRowBandSize','tblStyleColBandSize','tblW','jc','tblCellSpacing','tblInd','tblBorders','shd','tblLayout','tblCellMar','tblLook','tblCaption','tblDescription','tblPrChange'
_ORDER_SECTPR='footnotePr','endnotePr','type','pgSz','pgMar','paperSrc','pgBorders','lnNumType','pgNumType','cols','formProt','vAlign','noEndnote','titlePg','textDirection','bidi','rtlGutter','docGrid','printerSettings','sectPrChange'
_ORDER_LVL='start','numFmt','lvlRestart','pStyle','isLgl','suff','lvlText','lvlPicBulletId','legacy','lvlJc','pPr','rPr'
RTL_STYLES='Normal','Heading 1','Heading 2','Heading 3','Title','Subtitle','List Paragraph','List Number','List Bullet','Table Grid'
_HEB=re.compile('[\u0590-\u05ff]')
def _ensure(parent,tag,order):
	D=order;C=tag;A=parent;E=A.find(qn(C))
	if E is not None:return E
	G=C.split(':',1)[1];H=D.index(G);B=OxmlElement(C)
	for(I,J)in enumerate(A):
		F=J.tag.split('}')[-1]
		if F in D and D.index(F)>H:A.insert(I,B);return B
	A.append(B);return B
def _child(parent,tag,first=True):
	B=parent;A=B.find(qn(tag))
	if A is None:
		A=OxmlElement(tag)
		if first:B.insert(0,A)
		else:B.append(A)
	return A
def _ppr_rtl(p_el):
	A=_child(p_el,'w:pPr');_ensure(A,'w:bidi',_ORDER_PPR)
	for B in A.findall(qn('w:jc')):
		if B.get(qn('w:val'))in('left','right'):A.remove(B)
	return A
def _is_explicit_ltr(r_el):
	A=r_el.find(qn('w:rPr'))
	if A is None:return False
	B=A.find(qn('w:rtl'));return B is not None and B.get(qn('w:val'))in('0','false')
def _rpr_rtl(r_el,font=HEBREW_FONT):
	if _is_explicit_ltr(r_el):return
	A=_child(r_el,'w:rPr');B=_ensure(A,'w:rFonts',_ORDER_RPR);B.set(qn('w:cs'),font);_ensure(A,'w:rtl',_ORDER_RPR)
def set_run_rtl(run,font=HEBREW_FONT,size=None):
	B=size;A=run
	if B:A.font.size=Pt(B);C=_child(A._r,'w:rPr');_ensure(C,'w:szCs',_ORDER_RPR).set(qn('w:val'),str(int(B*2)))
	D=_ensure(_child(A._r,'w:rPr'),'w:rFonts',_ORDER_RPR)
	for E in('w:ascii','w:hAnsi'):D.set(qn(E),font)
	_rpr_rtl(A._r,font);return A
def set_run_ltr(run):
	A=_child(run._r,'w:rPr')
	for B in A.findall(qn('w:rtl')):A.remove(B)
	_ensure(A,'w:rtl',_ORDER_RPR).set(qn('w:val'),'0');return run
def set_paragraph_rtl(paragraph,font=HEBREW_FONT):
	A=paragraph;_ppr_rtl(A._p)
	for B in A._p.iter(qn('w:r')):_rpr_rtl(B,font)
	return A
def add_paragraph(container,text='',bold=False,size=11,ltr_parts=None):
	B=container.add_paragraph();D=ltr_parts or[(text,False)]
	for(C,E)in D:
		if not C:continue
		A=B.add_run(C);A.bold=bold
		if E:A.font.size=Pt(size);set_run_ltr(A)
		else:set_run_rtl(A,size=size)
	set_paragraph_rtl(B);return B
def set_table_rtl(table):
	A=table;B=A._tbl;D=_child(B,'w:tblPr');_ensure(D,'w:bidiVisual',_ORDER_TBLPR)
	for C in B.iter(qn('w:p')):
		_ppr_rtl(C)
		for E in C.iter(qn('w:r')):_rpr_rtl(E)
	return A
def set_section_rtl(section):A=section;B=A._sectPr;_ensure(B,'w:bidi',_ORDER_SECTPR);_ensure(B,'w:rtlGutter',_ORDER_SECTPR);return A
def set_styles_rtl(doc):
	for D in RTL_STYLES:
		try:B=doc.styles[D]
		except KeyError:continue
		C=B.element.find(qn('w:pPr'))
		if C is None:C=OxmlElement('w:pPr');B.element.append(C)
		_ensure(C,'w:bidi',_ORDER_PPR);A=B.element.find(qn('w:rPr'))
		if A is None:A=OxmlElement('w:rPr');B.element.append(A)
		_ensure(A,'w:rFonts',_ORDER_RPR).set(qn('w:cs'),HEBREW_FONT);_ensure(A,'w:rtl',_ORDER_RPR)
def add_numbered_list(doc,items,size=11):
	A=doc.part.numbering_part.element;O=[int(A.get(qn('w:abstractNumId')))for A in A.findall(qn('w:abstractNum'))];P=[int(A.get(qn('w:numId')))for A in A.findall(qn('w:num'))];G=max(O+[0])+1;H=max(P+[0])+1;B=OxmlElement('w:abstractNum');B.set(qn('w:abstractNumId'),str(G));C=OxmlElement('w:lvl');C.set(qn('w:ilvl'),'0')
	for(Q,R)in(('w:start','1'),('w:numFmt','decimal'),('w:lvlText','%1.'),('w:lvlJc','left')):S=_ensure(C,Q,_ORDER_LVL);S.set(qn('w:val'),R)
	I=_ensure(C,'w:pPr',_ORDER_LVL);_ensure(I,'w:bidi',_ORDER_PPR);J=_ensure(I,'w:ind',_ORDER_PPR);J.set(qn('w:right'),'360');J.set(qn('w:hanging'),'360');B.append(C);K=A.find(qn('w:num'))
	if K is not None:K.addprevious(B)
	else:A.append(B)
	E=OxmlElement('w:num');E.set(qn('w:numId'),str(H));L=OxmlElement('w:abstractNumId');L.set(qn('w:val'),str(G));E.append(L);A.append(E);M=[]
	for T in items:
		N=add_paragraph(doc,T,size=size);U=_child(N._p,'w:pPr');F=_ensure(U,'w:numPr',_ORDER_PPR);_child(F,'w:ilvl').set(qn('w:val'),'0');D=F.find(qn('w:numId'))
		if D is None:D=OxmlElement('w:numId');F.append(D)
		D.set(qn('w:val'),str(H));M.append(N)
	return M
def utc_naive(when=None):
	A=when
	if A is None:A=_dt.datetime.now(_dt.timezone.utc)
	elif A.tzinfo is None:A=A.astimezone()
	return A.astimezone(_dt.timezone.utc).replace(tzinfo=None,microsecond=0)
def clean_metadata(doc,author='',title=None,when=None):
	D=title;C=author;B=when;B=utc_naive(B);A=doc.core_properties;A.author=C or'';A.last_modified_by=C or'';A.comments='';A.keywords='';A.subject=''
	if D is not None:A.title=D
	A.revision=1;A.created=B;A.modified=B;A.last_printed=B;return doc
def enforce_document(doc,author='',title=None):
	A=doc
	for C in A.sections:
		set_section_rtl(C)
		for F in(C.header,C.footer):
			for B in F._element.iter(qn('w:p')):
				_ppr_rtl(B)
				for D in B.iter(qn('w:r')):_rpr_rtl(D)
	set_styles_rtl(A);E=A.element.body
	for G in E.iter(qn('w:tbl')):_ensure(_child(G,'w:tblPr'),'w:bidiVisual',_ORDER_TBLPR)
	for B in E.iter(qn('w:p')):
		_ppr_rtl(B)
		for D in B.iter(qn('w:r')):_rpr_rtl(D)
	clean_metadata(A,author=author,title=title);return A
def _q(tag):return'{%s}%s'%(W_NS,tag)
def _text(el):return''.join(A.text or''for A in el.iter(_q('t')))
def audit_docx(path,run_date=None,require_hebrew=True):
	L=run_date;B=[]
	with zipfile.ZipFile(path)as D:
		E=D.namelist();Z=['word/document.xml']+sorted(A for A in E if re.match('word/(header|footer)\\d*\\.xml$|word/comments\\.xml$',A));F=False
		for C in Z:
			G=etree.fromstring(D.read(C))
			for M in G.iter(_q('p')):
				A=_text(M)
				if not A.strip():continue
				F=F or bool(_HEB.search(A));H=M.find(_q('pPr'))
				if H is None or H.find(_q('bidi'))is None:B.append('%s: פסקה בלי bidi: %s'%(C,A[:40]))
				elif any(A.get(_q('val'))in('left','right')for A in H.findall(_q('jc'))):B.append('%s: יישור מפורש left/right בפסקה RTL: %s'%(C,A[:40]))
			for N in G.iter(_q('r')):
				A=_text(N)
				if not A.strip():continue
				O=N.find(_q('rPr'));I=O.find(_q('rtl'))if O is not None else None
				if I is None and not _HEB.search(A):continue
				if I is None:B.append('%s: ריצה בלי rtl: %s'%(C,A[:40]))
				elif I.get(_q('val'))in('0','false')and _HEB.search(A):B.append('%s: ריצה עברית שסומנה LTR: %s'%(C,A[:40]))
			for a in G.iter(_q('tbl')):
				P=a.find(_q('tblPr'))
				if P is None or P.find(_q('bidiVisual'))is None:B.append('%s: טבלה בלי bidiVisual (סדר העמודות לא הפוך)'%C)
		b=etree.fromstring(D.read('word/document.xml'));Q=list(b.iter(_q('sectPr')))
		if not Q:B.append('אין sectPr במסמך')
		for R in Q:
			if R.find(_q('bidi'))is None:B.append('מקטע בלי bidi')
			if R.find(_q('rtlGutter'))is None:B.append('מקטע בלי rtlGutter')
		if'word/numbering.xml'in E:
			c=etree.fromstring(D.read('word/numbering.xml'))
			for S in c.iter(_q('lvl')):
				T=S.find(_q('numFmt'));U=S.find(_q('lvlText'));J=U.get(_q('val'))if U is not None else''
				if T is not None and T.get(_q('val'))=='bullet':continue
				if J and re.match('^\\.\\s*%\\d',J):B.append('מספור עם נקודה לפני המספר: %s'%J)
		if'docProps/core.xml'in E:
			V=D.read('docProps/core.xml').decode('utf-8','replace')
			if'python-docx'in V:B.append('מאפייני הקובץ: "python-docx" ב-core.xml')
			if L:
				for W in('created','modified'):
					X=re.search('<dcterms:%s[^>]*>([^<]+)<'%W,V)
					if not X:continue
					Y=X.group(1).strip()
					try:import datetime as d;A=d.datetime.fromisoformat(Y.replace('Z','+00:00'));K=(A.astimezone()if A.tzinfo else A).date().isoformat()
					except ValueError:K=Y[:10]
					if K<L.isoformat():B.append('מאפייני הקובץ: %s=%s מוקדם מיום ההפקה'%(W,K))
		if require_hebrew and not F:B.append('אין טקסט עברי במסמך: הבדיקה חלה על מסמכים בעברית')
	return B
LATIN_FONT='Calibri'
def is_en(lang):A=str(lang or'').strip().lower();return A[:2]=='en'or A in('english','אנגלית')
def lang_of(*B,default='he'):
	for A in B:
		if A not in(None,''):return'en'if is_en(A)else'he'
	return default
def _strip(parent,*B):
	A=parent
	if A is None:return
	for C in B:
		for D in A.findall(qn(C)):A.remove(D)
def _ind_left(ind):
	A=ind
	if A is not None and A.get(qn('w:right'))and not A.get(qn('w:left')):A.set(qn('w:left'),A.get(qn('w:right')));del A.attrib[qn('w:right')]
def _ppr_ltr(p_el):
	A=_child(p_el,'w:pPr');_strip(A,'w:bidi');B=A.find(qn('w:jc'))
	if B is None:_ensure(A,'w:jc',_ORDER_PPR).set(qn('w:val'),'left')
	elif B.get(qn('w:val'))in('right','end'):B.set(qn('w:val'),'left')
	_ind_left(A.find(qn('w:ind')));return A
def _rpr_ltr(r_el,font=LATIN_FONT):
	A=r_el.find(qn('w:rPr'))
	if A is None:return
	_strip(A,'w:rtl');B=A.find(qn('w:rFonts'))
	if B is not None:
		for C in('w:ascii','w:hAnsi','w:cs'):
			if B.get(qn(C))in(None,HEBREW_FONT):B.set(qn(C),font)
def enforce_document_ltr(doc,author='',title=None,font=LATIN_FONT):
	C=font;A=doc
	for D in A.sections:
		_strip(D._sectPr,'w:bidi','w:rtlGutter')
		for M in(D.header,D.footer):
			for B in M._element.iter(qn('w:p')):
				_ppr_ltr(B)
				for E in B.iter(qn('w:r')):_rpr_ltr(E,C)
	for N in RTL_STYLES:
		try:J=A.styles[N]
		except KeyError:continue
		_strip(J.element.find(qn('w:pPr')),'w:bidi');F=J.element.find(qn('w:rPr'));_strip(F,'w:rtl');G=F.find(qn('w:rFonts'))if F is not None else None
		if G is not None:
			for K in('w:ascii','w:hAnsi','w:cs'):
				if G.get(qn(K))==HEBREW_FONT:G.set(qn(K),C)
	try:H=A.part.numbering_part.element
	except Exception:H=None
	if H is not None:
		for O in H.iter(qn('w:lvl')):I=O.find(qn('w:pPr'));_strip(I,'w:bidi');_ind_left(I.find(qn('w:ind'))if I is not None else None)
	L=A.element.body
	for P in L.iter(qn('w:tbl')):_strip(P.find(qn('w:tblPr')),'w:bidiVisual')
	for B in L.iter(qn('w:p')):
		_ppr_ltr(B)
		for E in B.iter(qn('w:r')):_rpr_ltr(E,C)
	clean_metadata(A,author=author,title=title);return A
def hebrew_dominant(text):A=len(_HEB.findall(text));return A>0 and A>=len(re.findall('[A-Za-z]',text))
def keep_hebrew_rtl(doc):
	B=[doc.element.body]
	for C in doc.sections:
		for D in(C.header,C.footer):
			if not D.is_linked_to_previous:B.append(D._element)
	E=0
	for H in B:
		for A in H.iter(qn('w:p')):
			F=''.join(A.text or''for A in A.iter(qn('w:t')))
			if not _HEB.search(F):continue
			E+=1
			if hebrew_dominant(F):_ppr_rtl(A)
			for G in A.iter(qn('w:r')):
				if _HEB.search(''.join(A.text or''for A in G.iter(qn('w:t')))):_rpr_rtl(G)
	return E
def enforce(doc,lang,author='',title=None,keep_hebrew=False):
	C=title;B=author;A=doc
	if is_en(lang):
		enforce_document_ltr(A,author=B,title=C)
		if keep_hebrew:keep_hebrew_rtl(A)
		return A
	return enforce_document(A,author=B,title=C)
def audit_docx_ltr(path,run_date=None):
	A=[]
	with zipfile.ZipFile(path)as B:
		G=B.namelist();R=['word/document.xml']+sorted(A for A in G if re.match('word/(header|footer)\\d*\\.xml$|word/comments\\.xml$',A))
		for C in R:
			H=etree.fromstring(B.read(C))
			for J in H.iter(_q('p')):
				D=_text(J)
				if not D.strip():continue
				E=J.find(_q('pPr'))
				if E is not None and E.find(_q('bidi'))is not None and not _HEB.search(D):A.append('%s: bidi in an English paragraph: %s'%(C,D[:40]))
				if E is not None and any(A.get(_q('val'))in('right','end')for A in E.findall(_q('jc'))):A.append('%s: right-aligned paragraph: %s'%(C,D[:40]))
			for F in H.iter(_q('r')):
				K=F.find(_q('rPr'));L=K.find(_q('rtl'))if K is not None else None
				if L is not None and L.get(_q('val'))not in('0','false')and _text(F).strip()and not _HEB.search(_text(F)):A.append('%s: rtl run in an English document: %s'%(C,_text(F)[:40]))
			for S in H.iter(_q('tbl')):
				M=S.find(_q('tblPr'))
				if M is not None and M.find(_q('bidiVisual'))is not None:A.append('%s: table with bidiVisual (reversed columns)'%C)
		T=etree.fromstring(B.read('word/document.xml'))
		for N in T.iter(_q('sectPr')):
			if N.find(_q('bidi'))is not None or N.find(_q('rtlGutter'))is not None:A.append('section with bidi or rtlGutter')
		if'word/numbering.xml'in G:
			U=etree.fromstring(B.read('word/numbering.xml'))
			for O in U.iter(_q('lvl')):
				P=O.find(_q('lvlText'));I=P.get(_q('val'))if P is not None else''
				if I and re.match('^\\.\\s*%\\d',I):A.append('numbering with the dot before the number: %s'%I)
				Q=O.find(_q('pPr'))
				if Q is not None and Q.find(_q('bidi'))is not None:A.append('numbering level with bidi')
		if'docProps/core.xml'in G:
			V=B.read('docProps/core.xml').decode('utf-8','replace')
			if'python-docx'in V:A.append('file properties: "python-docx" in core.xml')
	return A
def audit(path,lang,run_date=None):
	A=run_date
	if is_en(lang):return audit_docx_ltr(path,run_date=A)
	return audit_docx(path,run_date=A)
