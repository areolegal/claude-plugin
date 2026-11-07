#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (c) Areo. All rights reserved. Licensed under the terms at https://areo.co.il/legal/terms
import argparse,copy,hashlib,io,json,os,re,sys,zipfile
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
for _s in(sys.stdout,sys.stderr):
	try:_s.reconfigure(encoding='utf-8',errors='replace')
	except(AttributeError,ValueError):pass
from lxml import etree
W_NS='http://schemas.openxmlformats.org/wordprocessingml/2006/main'
W='{%s}'%W_NS
XML_SPACE='{http://www.w3.org/XML/1998/namespace}space'
FONT_HE='David'
STAMP_STYLE='AreoStamp'
PARTS=re.compile('^word/(document|header\\d*|footer\\d*|footnotes|endnotes|comments)\\.xml$')
MANIFEST_SCHEMA='areo-translation-manifest/1'
LATIN_ONLY=re.compile('^[\\sA-Za-z0-9.,;:()\\[\\]/%&@\'\\"\\-+*=#$€£₪]*$')
RTL_LANGS='he','ar'
PDF_LOST='The source is a PDF. The translation keeps its text and the order of its paragraphs; the layout, tables, images, headers and footers and page numbers of the PDF are not kept.\nהמקור הוא PDF. התרגום שומר את הטקסט ואת סדר הפסקאות; העימוד, הטבלאות, התמונות, הכותרות העליונות והתחתונות ומספרי העמודים של ה-PDF אינם נשמרים.'
def sniff(path):
	try:
		with open(path,'rb')as B:A=B.read(8)
	except OSError:return'missing'
	if A.startswith(b'%PDF'):return'pdf'
	if A.startswith(b'\xd0\xcf\x11\xe0'):return'doc'
	if A.startswith(b'PK'):
		try:
			with zipfile.ZipFile(path)as C:return'docx'if'word/document.xml'in C.namelist()else'zip'
		except zipfile.BadZipFile:return'damaged'
	return'text'
KIND_MSG={'doc':'%s is an old Word file (.doc) or an encrypted file. Save it as .docx and try again.\n%s הוא קובץ Word ישן (.doc) או קובץ מוצפן. שמרו אותו כ-docx ונסו שוב.','zip':'%s is a ZIP file, not a Word document.\n%s הוא קובץ ZIP ולא מסמך Word.','damaged':'%s is damaged: it starts like a Word file but cannot be opened. Save it again from Word.\n%s פגום: הוא נפתח כמו קובץ Word אבל אינו נקרא. שמרו אותו שוב מ-Word.','missing':'%s was not found.\n%s לא נמצא.'}
def pdf_paragraphs(path):
	A=''
	try:
		try:import pymupdf as C
		except ImportError:import fitz as C
		with C.open(path)as E:
			D=[]
			for F in E:D+=[A[4]for A in F.get_text('blocks')if str(A[4]).strip()]
		B=[re.sub('\\s+',' ',A).strip()for A in D];return[A for A in B if A],None
	except ImportError:pass
	except Exception as G:return[],'the PDF could not be opened (%s)'%type(G).__name__
	try:from pypdf import PdfReader as H;A='\n'.join(A.extract_text()or''for A in H(path).pages)
	except Exception:return[],'no PDF reader is available (pymupdf)'
	if re.search('[\\u0590-\\u05FF]',A):return[],'a Hebrew PDF needs pymupdf; without it the text comes out reversed'
	B=[re.sub('\\s+',' ',A).strip()for A in re.split('\\n\\s*\\n',A)];return[A for A in B if A],None
def parts_of(path):
	with zipfile.ZipFile(path)as A:return{B:A.read(B)for B in A.namelist()},[A.filename for A in A.infolist()]
def text_parts(parts):A=sorted((A for A in parts if PARTS.match(A)),key=lambda n:(0 if'document'in n else 1,n));return A
def para_text(p):
	B=[]
	for A in p.iter(W+'t',W+'tab',W+'br'):
		if A.getparent()is not None and A.getparent().tag==W+'r':
			if A.tag==W+'t':B.append(A.text or'')
			elif A.tag==W+'tab':B.append('\t')
			else:B.append('\n')
	return''.join(B)
def paragraphs(root):return[A for A in root.iter(W+'p')if not any(A.tag.endswith('}Fallback')for A in A.iterancestors())]
def part_kind(name):
	B=name.rsplit('/',1)[-1]
	for A in('footnotes','endnotes','comments','header','footer'):
		if B.startswith(A):return{'footnotes':'footnote','endnotes':'endnote','comments':'comment'}.get(A,A)
	return'body'
ANNEX_HEAD=re.compile('^\\s*(annex|annexure|schedule|appendix|exhibit|attachment|\\u05e0\\u05e1\\u05e4\\u05d7|\\u05ea\\u05d5\\u05e1\\u05e4\\u05ea|\\u05e0\\u05e1\\u05e4\\u05d7\\u05d9\\u05dd)\\b',re.I)
def seg_hash(text):return hashlib.sha256(re.sub('\\s+',' ',text).strip().encode('utf-8')).hexdigest()[:16]
def para_features(p):
	def A(*A):return sum(len(p.findall('.//'+W+A))for A in A)
	F=len([A for A in p.iter(W+'fldChar')if A.get(W+'fldCharType')=='begin'])+A('fldSimple');C=0;D=0
	for E in p.iter(W+'r'):
		if E.find(W+'t')is None:continue
		D+=1;B=E.find(W+'rPr')
		if B is not None and any(B.find(W+A)is not None and B.find(W+A).get(W+'val')not in('0','false','none')for A in('b','i','u')):C+=1
	return{'fields':F,'bookmarks':A('bookmarkStart'),'hyperlinks':A('hyperlink'),'note_refs':A('footnoteReference','endnoteReference'),'comment_refs':A('commentReference'),'drawings':A('drawing','pict'),'emphasis_runs':C,'text_runs':D}
def collect(src):
	I=src
	if sniff(I)=='pdf':
		R,L=pdf_paragraphs(I)
		if L:raise ValueError(L)
		B=[{'id':'pdf:%d'%A,'part':'pdf','index':A,'kind':'body','source':B}for(A,B)in enumerate(R)];return B,{'parts':{'pdf':{'kind':'body','segments':len(B)}},'tracked_changes':{'insertions':0,'deletions':0,'moves':0,'layer':'not_applicable_pdf'}}
	M,T=parts_of(I);B,F=[],{'parts':{},'tracked_changes':{'insertions':0,'deletions':0,'moves':0}}
	for C in text_parts(M):
		D=etree.fromstring(M[C]);A=F['tracked_changes'];A['insertions']+=len(D.findall('.//'+W+'ins'));A['deletions']+=len(D.findall('.//'+W+'del'));A['moves']+=len(D.findall('.//'+W+'moveFrom'))+len(D.findall('.//'+W+'moveTo'));J,K,N=part_kind(C),False,0
		for(O,G)in enumerate(paragraphs(D)):
			H=para_text(G).strip()
			if not H:continue
			E=J
			if J=='body':
				P=G.find(W+'pPr/'+W+'pStyle');S=(P.get(W+'val')if P is not None else'')or''
				if ANNEX_HEAD.match(H)and len(H)<90:K,E=True,'annex'
				elif re.search('head|title|\\u05db\\u05d5\\u05ea\\u05e8\\u05ea',S,re.I):E='heading'
				elif any(A.tag==W+'tc'for A in G.iterancestors()):E='table'
				elif K:E='annex'
			Q={'id':'%s:%d'%(re.sub('^word/|\\.xml$','',C),O),'part':C,'index':O,'kind':E,'source':H,'features':para_features(G)}
			if K:Q['in_annex']=True
			B.append(Q);N+=1
		F['parts'][C]={'kind':J,'segments':N}
	A=F['tracked_changes'];A['layer']='insertions_shown_deletions_omitted'if A['insertions']or A['deletions']or A['moves']else'none_in_source';return B,F
def extract(src,out,glossary_version=None,allow_scanned=False):
	A=src;F=hashlib.sha256(open(A,'rb').read()).hexdigest();D=False;B,E=collect(A)
	if sniff(A)=='pdf'and not B:
		if not allow_scanned:raise ValueError('the PDF has no text layer (a scanned PDF): it needs text recognition first')
		D=True
	for C in B:C['source_hash']=seg_hash(C['source']);C['target']='';C['not_translated_reason']=''
	G={'manifest_schema':MANIFEST_SCHEMA,'source_file':os.path.basename(A),'source_sha256':F,'source_kind':sniff(A),'glossary_version':glossary_version or'','parts':E['parts'],'tracked_changes':E['tracked_changes'],'scanned_text_unread':D,'segments':B};io.open(out,'w',encoding='utf-8').write(json.dumps(G,ensure_ascii=False,indent=1));return B
def _set(parent,tag,before=None,**C):
	B=parent;A=B.find(W+tag)
	if A is None:A=etree.SubElement(B,W+tag)
	for(D,E)in C.items():A.set(W+D,E)
	return A
def _drop(parent,tag):
	A=parent
	for B in A.findall(W+tag):A.remove(B)
def replace_text(p,target):
	C=[A for A in p.iter(W+'r')if A.find(W+'t')is not None]
	if not C:A=etree.SubElement(p,W+'r');C=[A];etree.SubElement(A,W+'t')
	D=True
	for A in C:
		for B in A.findall(W+'t')+A.findall(W+'tab'):
			if D and B.tag==W+'t':B.text=target;B.set(XML_SPACE,'preserve');D=False
			else:A.remove(B)
def direct_paragraph(p,rtl):
	B=p.find(W+'pPr')
	if B is None:B=etree.Element(W+'pPr');p.insert(0,B)
	if rtl:
		if B.find(W+'bidi')is None:
			H=etree.Element(W+'bidi');C=None
			for I in('pStyle','keepNext','keepLines','pageBreakBefore','framePr','widowControl','numPr','suppressLineNumbers','pBdr','shd','tabs','suppressAutoHyphens','kinsoku','wordWrap','overflowPunct','topLinePunct','autoSpaceDE','autoSpaceDN'):
				if B.find(W+I)is not None:C=B.find(W+I)
			C.addnext(H)if C is not None else B.insert(0,H)
		D=B.find(W+'jc')
		if D is not None and D.get(W+'val')in('left','start'):D.set(W+'val','right')
	else:
		_drop(B,'bidi');D=B.find(W+'jc')
		if D is not None and D.get(W+'val')in('right','end'):D.set(W+'val','left')
	for F in p.iter(W+'r'):
		A=F.find(W+'rPr')
		if A is None:A=etree.Element(W+'rPr');F.insert(0,A)
		G=''.join(A.text or''for A in F.findall(W+'t'))
		if rtl:
			E=A.find(W+'rFonts')
			if E is None:E=etree.Element(W+'rFonts');J=A.find(W+'rStyle');J.addnext(E)if J is not None else A.insert(0,E)
			E.set(W+'cs',FONT_HE)
			if G and LATIN_ONLY.match(G)and re.search('[A-Za-z]',G):_drop(A,'rtl')
			elif A.find(W+'rtl')is None:
				K=etree.Element(W+'rtl');C=None
				for L in A:
					if L.tag.split('}')[-1]in('rStyle','rFonts','b','bCs','i','iCs','caps','smallCaps','strike','dstrike','outline','shadow','emboss','imprint','noProof','snapToGrid','vanish','webHidden','color','spacing','w','kern','position','sz','szCs','highlight','u','effect','bdr','shd','fitText','vertAlign'):C=L
				C.addnext(K)if C is not None else A.insert(0,K)
		else:_drop(A,'rtl')
def direct_part(root,rtl):
	D=rtl;C=root
	for G in paragraphs(C):direct_paragraph(G,D)
	for B in C.iter(W+'tblPr'):
		if D:
			if B.find(W+'bidiVisual')is None:B.insert(1 if B.find(W+'tblStyle')is not None else 0,etree.Element(W+'bidiVisual'))
		else:_drop(B,'bidiVisual')
	for A in C.iter(W+'sectPr'):
		if D:
			for(E,H)in(('bidi',('rtlGutter','docGrid','printerSettings','sectPrChange')),('rtlGutter',('docGrid','printerSettings','sectPrChange'))):
				if A.find(W+E)is None:F=next((A.find(W+B)for B in H if A.find(W+B)is not None),None);F.addprevious(etree.Element(W+E))if F is not None else A.append(etree.Element(W+E))
		else:_drop(A,'rtlGutter');_drop(A,'bidi')
def add_header_lines(parts,lines,rtl):
	D=lines;B=parts;C=[A for A in B if re.match('^word/header\\d*\\.xml$',A)]
	if not C or not D:return bool(C)
	for E in C:
		F=etree.fromstring(B[E])
		for(I,J)in enumerate(D):A=etree.Element(W+'p');K=etree.SubElement(A,W+'pPr');etree.SubElement(K,W+'pStyle').set(W+'val',STAMP_STYLE);G=etree.SubElement(A,W+'r');etree.SubElement(G,W+'rPr');H=etree.SubElement(G,W+'t');H.text=J;H.set(XML_SPACE,'preserve');direct_paragraph(A,rtl);F.insert(I,A)
		B[E]=etree.tostring(F,xml_declaration=True,encoding='UTF-8',standalone=True)
	return True
def build_from_pdf(segs,lang,out,stamp,legend):
	A=out;from docx import Document as I;J=str(lang)[:2].lower()in RTL_LANGS;D=I()
	for K in segs:D.add_paragraph(K['target'])
	B=D.sections[0].header;B.is_linked_to_previous=False;E=True
	for L in[A for A in(stamp,legend)if A]:M=B.paragraphs[0]if E and B.paragraphs else B.add_paragraph();M.text=L;E=False
	D.save(A);C,N=parts_of(A)
	for F in text_parts(C):G=etree.fromstring(C[F]);direct_part(G,J);C[F]=etree.tostring(G,xml_declaration=True,encoding='UTF-8',standalone=True)
	with zipfile.ZipFile(A+'.tmp','w',zipfile.ZIP_DEFLATED)as O:
		for H in N:O.writestr(H,C[H])
	os.replace(A+'.tmp',A)
def ensure_header(out,lines,rtl):
	A=out;from docx import Document as I;D=I(A)
	for J in D.sections:
		B=J.header;B.is_linked_to_previous=False;E=True
		for K in lines:L=B.paragraphs[0]if E and B.paragraphs and not B.paragraphs[0].text else B.add_paragraph();L.text=K;E=False
	D.save(A);C,M=parts_of(A)
	for F in[A for A in text_parts(C)if'header'in A]:G=etree.fromstring(C[F]);direct_part(G,rtl);C[F]=etree.tostring(G,xml_declaration=True,encoding='UTF-8',standalone=True)
	with zipfile.ZipFile(A+'.tmp','w',zipfile.ZIP_DEFLATED)as N:
		for H in M:N.writestr(H,C[H])
	os.replace(A+'.tmp',A)
def build(src,segs_path,lang,out,stamp=None,legend=None):
	N=legend;M=stamp;E=out;G=json.load(io.open(segs_path,encoding='utf-8'));B=G.get('segments')if isinstance(G,dict)else G;H=[A for A in B if not str(A.get('target')or'').strip()and not str(A.get('not_translated_reason')or'').strip()];O=[A for A in B if str(A.get('target')or'').strip()and str(A.get('not_translated_reason')or'').strip()]
	if O:return 1,['%s #%d: has both a target and a not_translated_reason'%(A['part'],A['index'])for A in O[:10]]
	C=[A for A in B if str(A.get('not_translated_reason')or'').strip()]
	if not H:
		for A in C:A['target']=A['source']
	if H:return 1,['%s #%d: %s'%(A['part'],A['index'],A['source'][:60])for A in H[:10]]
	if sniff(src)=='pdf':build_from_pdf(B,lang,E,M,N);return 0,['%d segments were left in the source language for a stated reason; the translation is NOT complete'%len(C)]if C else[]
	D,U=parts_of(src);P={}
	for A in B:P.setdefault(A['part'],{})[int(A['index'])]=A['target']
	I=str(lang)[:2].lower()in RTL_LANGS
	for J in text_parts(D):
		K=etree.fromstring(D[J]);Q=paragraphs(K)
		for(R,V)in P.get(J,{}).items():
			if R<len(Q):replace_text(Q[R],V)
		direct_part(K,I);D[J]=etree.tostring(K,xml_declaration=True,encoding='UTF-8',standalone=True)
	L=[];F=[A for A in(M,N)if A];W=add_header_lines(D,F,I)if F else True;S=E+'.tmp'
	with zipfile.ZipFile(S,'w',zipfile.ZIP_DEFLATED)as X:
		for T in U:X.writestr(T,D[T])
	os.replace(S,E)
	if F and not W:ensure_header(E,F,I);L.append('the source had no header: one was created for the stamp and the legend')
	if C:L.append('%d segments were left in the source language for a stated reason; the translation is NOT complete until they are translated (the integrity check lists them as gaps)'%len(C))
	return 0,L
def main():
	H=argparse.ArgumentParser(description="Builds the translated Word file from the source Word file, keeping its structure and applying the target language's direction");I=H.add_subparsers(dest='cmd',required=True);D=I.add_parser('extract',help='segments to translate, from the body, tables, headers and footers');D.add_argument('--source',required=True);D.add_argument('--out',required=True);D.add_argument('--glossary-version',help='the glossary id/version used; recorded in the manifest');D.add_argument('--allow-scanned',action='store_true',help='a PDF with no text layer: write a manifest that records the unread scanned text as a gap');B=I.add_parser('build',help='the translated file from the source and the filled segments');B.add_argument('--source',required=True);B.add_argument('--segments',required=True);B.add_argument('--lang',required=True,help='target language: he, en, ar ...');B.add_argument('--out',required=True);B.add_argument('--stamp',help='the production stamp, e.g. "Produced on 3 April 2027" / "הופק בתאריך 3.4.2027"');B.add_argument('--legend',help='the status legend, e.g. the binding-version line');B.add_argument('--force',action='store_true',help='overwrite an existing output');A=H.parse_args();E=sniff(A.source)
	if E not in('docx','pdf'):J=os.path.basename(A.source);print(KIND_MSG.get(E,'%s is not a Word or PDF file.\n%s אינו קובץ Word או PDF.')%(J,J));sys.exit(2)
	if E=='pdf'and not A.source.lower().endswith('.pdf'):print('note: %s is a PDF, though its name says otherwise; it is read as a PDF.'%os.path.basename(A.source))
	C=A.out
	if os.path.normcase(os.path.realpath(C))==os.path.normcase(os.path.realpath(A.source)):print('refused: --out is the source file');sys.exit(2)
	if A.cmd=='extract':
		try:L=extract(A.source,C,A.glossary_version,A.allow_scanned)
		except ValueError as D:print('Not extracted: %s'%D);sys.exit(2)
		print('segments: %d (body, tables, headers and footers): %s'%(len(L),C));return
	if os.path.exists(C)and not A.force:print('refused: %s exists; add --force to overwrite'%C);sys.exit(2)
	K,F=build(A.source,A.segments,A.lang,C,A.stamp,A.legend)
	if K:
		print('Not built: %d segments have no translation:'%len(F))
		for G in F:print('  '+G)
		sys.exit(K)
	print('translated file: %s (%s)'%(C,'RTL'if str(A.lang)[:2].lower()in RTL_LANGS else'LTR'))
	if sniff(A.source)=='pdf':print(PDF_LOST)
	for G in F:print('note: '+G)
if __name__=='__main__':main()
