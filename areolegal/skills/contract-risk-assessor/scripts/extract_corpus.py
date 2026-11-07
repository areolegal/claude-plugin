#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (c) Areo. All rights reserved. Licensed under the terms at https://areo.co.il/legal/terms
from __future__ import annotations
import argparse,hashlib,io,json,re,sys,zipfile
from pathlib import Path
import os
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
import areo_lib
from common.cli import DOCX_BAD_EXIT,OutputRefused,docx_problem,guard_out
from common.paths import long_path,plain_path
try:from lxml import etree;from risk.extract_corpus import OoxmlZip,anchored_ranges,comments_of,extract_pdf,para_changes,para_texts,q;from risk.page_text import PdfTextUnavailable,pdf_text
except ImportError as _exc:sys.exit('נדרשת הספרייה lxml (מגיעה עם python-docx): pip install python-docx. בלעדיה החילוץ אינו רץ. (%s)'%_exc)
SKIP_DIRS={'Areo-נתונים','דוגמאות-נראות','__MACOSX','.git','node_modules'}
CLAUSE_RE=re.compile('^\\s*(?:(?i:section|clause|article|sec\\.|art\\.)\\s*(\\d+(?:\\.\\d+)*|[IVX]{1,6}|[A-Z])\\b[.):]?(?=\\s*$|\\s*[\\-:.]|\\s+[A-Z\\"“(\\[]|\\s+[א-ת])|\\(?(\\d+(?:\\.\\d+)+)\\)?[.):]?|\\(?(\\d+)\\)?[.):])(?:\\s+|$)|^\\s*\\(?(?:(טו|טז|[יכלמנסעפצ][אבגדהוזחט]|[אבגדהוזחטיכלמנסעפצקרשת])\\)?[.):]|([ivx]{1,6}|[IVX]{1,6}|[A-Za-z])\\)?[.)])\\s+')
HEBREW=re.compile('[א-ת]')
TRACK_KINDS='ins','del','moveFrom','moveTo'
SIDE_PARTS=re.compile('^word/(footnotes|endnotes|header\\d*|footer\\d*)\\.xml$')
NO_TEXT='אין שכבת טקסט (סרוק?)'
BODY_KINDS='p','cell','textbox'
DOCX_REASON={'ole':'DOC ישן או קובץ מוצפן בסיסמה; שמרו כ-docx בלי סיסמה','not_zip':'קובץ פגום: אינו ZIP תקין','no_document':'אין בו word/document.xml: אינו מסמך Word','unreadable':'הקובץ אינו נפתח'}
UNSUPPORTED_DOC_EXT='.html','.htm','.eml','.msg','.odt','.xls','.xlsx','.ppt','.pptx','.jpg','.jpeg','.png','.tif','.tiff'
def clause_of(text):A=CLAUSE_RE.match(text or'');return next((A for A in A.groups()if A),'')if A else''
def _rec(kind,acc,rej,hidden,**C):
	B=hidden;A={'kind':kind,'text':acc};A.update(C)
	if rej!=acc:A['text_reject_all']=rej
	if B:A['hidden']=B
	return A
def _changes(p):A=para_changes(p);return{'changes':A}if A else{}
def _walk(container,out,tables):
	C=tables;B=out
	for A in container:
		if A.tag==q('p'):
			D,E,J=para_texts(A)
			if D or E:B.append(_rec('p',D,E,J,**_changes(A)))
			for K in A.iter(q('txbxContent')):
				for F in K.iter(q('p')):
					G,H,L=para_texts(F)
					if G or H:B.append(_rec('textbox',G,H,L,**_changes(F)))
		elif A.tag==q('tbl'):_table(A,B,C)
		elif A.tag==q('sdt'):
			I=A.find(q('sdtContent'))
			if I is not None:_walk(I,B,C)
def _kids(el,tag):
	B=tag
	for A in el:
		if A.tag==B:yield A
		elif A.tag==q('sdt'):
			C=A.find(q('sdtContent'))
			if C is not None:yield from _kids(C,B)
		elif A.tag==q('customXml'):yield from _kids(A,B)
def _val(el,default):
	try:return int(el.get(q('val')))
	except(AttributeError,TypeError,ValueError):return default
def _cell_of(el):
	A=el.getparent()
	while A is not None and A.tag!=q('tc'):A=A.getparent()
	return A
def _table(tbl,out,tables,parent=None):
	H=tables;E=parent;H[0]+=1;O=H[0];C={}
	for(P,Q)in enumerate(_kids(tbl,q('tr'))):
		R=Q.find(q('trPr'));A=max(0,_val(R.find(q('gridBefore'))if R is not None else None,0))
		for D in _kids(Q,q('tc')):
			F=D.find(q('tcPr'));I=max(1,_val(F.find(q('gridSpan'))if F is not None else None,1));B=F.find(q('vMerge'))if F is not None else None;B=None if B is None else B.get(q('val'))or'continue';S,T,U,J=[],[],[],[]
			for K in D.iter(q('p')):
				if _cell_of(K)is not D:continue
				W,X,Y=para_texts(K);S.append(W);T.append(X);U+=Y;J+=para_changes(K)
			L=' '.join(A for A in S if A).strip();M=' '.join(A for A in T if A).strip();N=None
			if B=='continue'and not(L or M):
				if C.get(A)is not None:C[A]['row_span']=C[A].get('row_span',1)+1
			else:
				if L or M:
					G={'table':O,'row':P,'col':A}
					if I>1:G['col_span']=I
					if E:G.update(parent_table=E[0],parent_row=E[1],parent_col=E[2])
					if J:G['changes']=J
					N=_rec('cell',L,M,U,**G);out.append(N)
				if B=='restart':C[A]=N
				elif B is None:C.pop(A,None)
			for V in D.iter(q('tbl')):
				if _cell_of(V)is D:_table(V,out,H,parent=(O,P,A))
			A+=I
def read_docx(path):
	with zipfile.ZipFile(path)as O:
		B=OoxmlZip(O);G=B.namelist()
		if'word/document.xml'not in G:raise ValueError('no document.xml')
		D=etree.fromstring(B.read('word/document.xml'));M=D.find(q('body'));H,I=[],[0];_walk(M if M is not None else D,H,I);N={A:len(D.findall('.//'+q(A)))for A in TRACK_KINDS};C=comments_of(B)
		for(A,J)in anchored_ranges(D).items():
			if A in C:C[A]['anchored_text']=J
		for K in sorted(A for A in G if SIDE_PARTS.match(A)):
			E=etree.fromstring(B.read(K))
			for A in TRACK_KINDS:N[A]+=len(E.findall('.//'+q(A)))
			for(A,J)in anchored_ranges(E).items():
				if A in C and not C[A].get('anchored_text'):C[A]['anchored_text']=J
			L=[]
			if'notes'in K:
				for P in E:_walk(P,L,I)
			else:_walk(E,L,I)
			Q='footnote'if'notes'in K else'header_footer'
			for F in L:
				if len(F['text'])>3:
					if F['kind']=='p':F['kind']=Q
					H.append(F)
		R=B.read('word/settings.xml').decode('utf-8','replace')if'word/settings.xml'in G else''
	S={'format':'docx','tracked_counts':N,'ooxml_strict':B.strict,'track_revisions_on':'<w:trackRevisions'in R,'comments':[{'author':A.get('author'),'date':A.get('date'),'text':A.get('text'),'anchored_text':A.get('anchored_text')or''}for A in C.values()]};return H,S
def pdf_engine():
	for A in('pymupdf','fitz'):
		try:__import__(A);return'pymupdf'
		except ImportError:pass
	try:__import__('pypdf');return'pypdf'
	except ImportError:return
def read_pdf(path,engine):
	A=engine;C=path.read_bytes()
	if A is None:raise ValueError('אין בסביבה ספרייה לקריאת PDF. התקנה: pip install pymupdf')
	if A=='pymupdf':
		D=extract_pdf(str(path),C)
		if D.get('no_text_layer'):raise ValueError('PDF סרוק, בלי שכבת טקסט')
		B=[]
		for(F,G)in D['parts'].items():H=int(F.rsplit('-',1)[-1]);B+=[{'kind':'p','text':A['text_accept_all'],'page':H}for A in G]
		return B,{'format':'pdf','pdf_engine':A}
	try:E=pdf_text(C)
	except PdfTextUnavailable as I:raise ValueError(str(I).split(':')[0])
	if HEBREW.search(E):raise ValueError('PDF בעברית, ואין pymupdf: הטקסט יוצא בסדר הפוך. התקנה: pip install pymupdf')
	B=[{'kind':'p','text':re.sub('\\s+',' ',A).strip()}for A in E.splitlines()if A.strip()];return B,{'format':'pdf','pdf_engine':A}
def family_guess(stem):A=re.sub('[_\\-]+',' ',stem);A=re.sub('\\b(v|ver|version|rev|draft|final|signed|חתום|טיוטה)\\s*\\d*\\b',' ',A,flags=re.I);A=re.sub('\\b20\\d{2}[.\\-_ ]?\\d{0,2}[.\\-_ ]?\\d{0,2}\\b',' ',A);return' '.join(A.split())[:80]
def main():
	J=argparse.ArgumentParser();J.add_argument('root');J.add_argument('--out',required=True,help='קובץ הפלט (JSON). חובה ומפורש: ברירת מחדל שקטה כותבת לתיקייה שממנה הריצו');J.add_argument('--max-paragraphs',type=int,default=1200,help='תקרה לכל מסמך; פסקאות מעבר לה נספרות ואינן נשמרות');M=J.parse_args();C=Path(long_path(str(Path(M.root).expanduser()))).resolve()
	if not C.exists():print('לא נמצאו תיקייה או קובץ: %s'%plain_path(C));return 1
	V=C.is_file();b=[C]if V else sorted(C.rglob('*'))
	if C.is_file():C=C.parent
	c=pdf_engine();D,B,N,I,O=[],[],{},[],[]
	for A in b:
		if not A.is_file():
			if not A.is_dir()and not A.name.startswith(('.','~$'))and not any(A in SKIP_DIRS for A in A.parts):I.append('%s (הקובץ לא נמצא או שאינו נגיש; נתיב של %d תווים)'%(str(A.relative_to(C)),len(plain_path(A))))
			continue
		if A.name.startswith(('.','~$')):continue
		if any(A in SKIP_DIRS for A in A.parts):continue
		E=A.suffix.lower()
		if E not in('.docx','.txt','.md','.pdf','.doc','.rtf'):
			if E in UNSUPPORTED_DOC_EXT:B.append('%s (סוג הקובץ %s אינו נתמך; שמרו כ-docx או כ-PDF)'%(str(A.relative_to(C)),E[1:].upper()))
			continue
		H=str(A.relative_to(C))
		if E in('.doc','.rtf'):B.append('%s (פורמט %s אינו נקרא; שמרו כ-docx)'%(H,E[1:].upper()));continue
		try:
			if E=='.docx':
				K=docx_problem(A,strict_ok=True)
				if K:B.append('%s (%s)'%(H,DOCX_REASON.get(K[0],K[0])));O.append(K[1]);continue
				F,G=read_docx(A)
			elif E=='.pdf':F,G=read_pdf(A,c)
			else:F=[{'kind':'p','text':A.strip()}for A in io.open(A,encoding='utf-8',errors='ignore').read().splitlines()if A.strip()];G={'format':E[1:]}
		except ValueError as P:B.append('%s (%s)'%(H,P));continue
		except Exception as P:B.append('%s (%s)'%(H,type(P).__name__));continue
		if not any((A.get('text')or'').strip()or(A.get('text_reject_all')or'').strip()for A in F if A['kind']in BODY_KINDS):B.append('%s (%s)'%(H,NO_TEXT if E in('.docx','.pdf')else'קובץ ריק'));continue
		Q='\n'.join(A['text']for A in F);L=hashlib.sha256(Q.encode('utf-8')).hexdigest()
		if Q.strip()and L in N:D[N[L]]['duplicates'].append(H);continue
		if Q.strip():N[L]=len(D)
		d=G.get('tracked_counts')or{};W=any(d.values());X=bool(G.get('comments'));R=F[:M.max_paragraphs];S={'doc_id':'d%03d'%(len(D)+1),'path':H,'format':G.get('format'),'family_guess':family_guess(A.stem),'paragraph_count':len(F),'truncated':len(F)>len(R),'has_tracked_changes':W,'has_comments':X,'looks_like_draft':W or X,'content_sha256':L[:16],'duplicates':[],'table_count':len({A['table']for A in R if A['kind']=='cell'}),'hidden_total':sum(len(A.get('hidden')or[])for A in F),'paragraphs':[dict(A,i=B,clause=clause_of(A['text'])if A['kind']=='p'else'')for(B,A)in enumerate(R)]}
		for T in('tracked_counts','track_revisions_on','comments','pdf_engine'):
			if T in G:S[T]=G[T]
		if G.get('ooxml_strict'):S['ooxml_strict']=True
		D.append(S)
	Y=sum(1 for A in D if A['looks_like_draft']);Z=[A['path']for A in D if A['hidden_total']];U={'root':plain_path(C),'document_count':len(D),'duplicate_count':sum(len(A['duplicates'])for A in D),'draft_like_count':Y,'pdf_count':sum(1 for A in D if A['format']=='pdf'),'hidden_text_documents':Z,'unreadable':I+B,'documents':D}
	try:a=guard_out(M.out,inputs=[plain_path(A)for A in C.rglob('*')if A.is_file()])
	except OutputRefused as e:print('סירוב: %s'%e);return 1
	io.open(a,'w',encoding='utf-8').write(json.dumps(U,ensure_ascii=False,indent=1));print('נכתב %s'%a);print('  מסמכים ייחודיים : %d (מהם PDF: %d)'%(len(D),U['pdf_count']));print('  כפילויות מדויקות: %d'%U['duplicate_count']);print('  נחזים כטיוטות   : %d'%Y);print('  עם טקסט מוסתר   : %d'%len(Z));B=I+B;print('  לא נקראו כאן    : %d'%len(B))
	for f in B[:10]:print('    - %s'%f)
	if len(B)>10:print('    ועוד %d'%(len(B)-10))
	if B:print('  אלה אינם בקובץ; הטיפול בהם לפי הוראות הרכיב.')
	if I:print('שגיאה: %d קבצים בתיקייה לא נמצאו או אינם נגישים, והחילוץ אינו מלא (קוד יציאה 1).'%len(I));return 1
	if V and O:print(O[0]);return DOCX_BAD_EXIT
	return 0
if __name__=='__main__':sys.exit(main())
