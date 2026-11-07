# -*- coding: utf-8 -*-
# Copyright (c) Areo. All rights reserved. Licensed under the terms at https://areo.co.il/legal/terms
import copy,datetime as _dt,difflib,io,re,secrets,zipfile
from lxml import etree
W_NS='http://schemas.openxmlformats.org/wordprocessingml/2006/main'
R_NS='http://schemas.openxmlformats.org/officeDocument/2006/relationships'
MC_NS='http://schemas.openxmlformats.org/markup-compatibility/2006'
W16DU_NS='http://schemas.microsoft.com/office/word/2023/wordml/word16du'
W14_NS='http://schemas.microsoft.com/office/word/2010/wordml'
PKG_REL_NS='http://schemas.openxmlformats.org/package/2006/relationships'
CT_NS='http://schemas.openxmlformats.org/package/2006/content-types'
W='{%s}'%W_NS
XML_SPACE='{http://www.w3.org/XML/1998/namespace}space'
DATE_UTC_ATTR='{%s}dateUtc'%W16DU_NS
MC_IGNORABLE='{%s}Ignorable'%MC_NS
INTERNAL_AUTHOR='פנימי, למחיקה לפני המשלוח'
INTERNAL_AUTHOR_EN='Internal, delete before sending'
INTERNAL_AUTHORS=INTERNAL_AUTHOR,INTERNAL_AUTHOR_EN
INTERNAL_INITIALS='פנ'
INTERNAL_INITIALS_EN='Int'
INTERNAL_HEADER_TEXT='טיוטת עבודה פנימית, לא למשלוח'
INTERNAL_HEADER_TEXT_EN='Internal working draft, not for sending'
def internal_author(lang='he'):
	if str(lang or'he').lower().startswith('en'):return INTERNAL_AUTHOR_EN,INTERNAL_INITIALS_EN,INTERNAL_HEADER_TEXT_EN
	return INTERNAL_AUTHOR,INTERNAL_INITIALS,INTERNAL_HEADER_TEXT
INTERNAL_HEADER_PART='word/headerInternal.xml'
INTERNAL_REL_PREFIX='rIdInt'
AREO_LABEL={'he':'סעיף AREO: אין לסעיף הזה עמדה בפלייבוק, וההכרעה היא הצעת Areo מנקודת המבט של %s%s.','en':"Areo clause: the playbook has no position on this clause; the decision is Areo's proposal from %s's position%s."}
AREO_LABEL_PREFIXES='סעיף AREO','Areo clause'
AREO_HIGHLIGHT='yellow'
def areo_label(company,role=None,lang='he'):A=str(lang or'').lower()[:2]=='en';B=(' as %s'if A else' כ%s')%role if role else'';return AREO_LABEL['en'if A else'he']%(company or('the company'if A else'החברה'),B)
AREO_SOURCE_LABELS='areo_proposal','הצעת Areo','Areo proposal'
def is_areo_decision(d):return(d or{}).get('source_label')in AREO_SOURCE_LABELS or(d or{}).get('areo_clause')is True
def _areo_comment_ids(comments_root):
	C=comments_root;A=set()
	if C is None:return A
	for B in C.findall(W+'comment'):
		D=''.join(A.text or''for A in B.iter(W+'t')).strip()
		if B.get(W+'author')in INTERNAL_AUTHORS and D.startswith(AREO_LABEL_PREFIXES):A.add(B.get(W+'id'))
	return A
def areo_paragraphs(doc_root,ids):
	A=ids
	if not A:return[]
	D,B=[],set()
	for C in body_paragraphs(doc_root):
		E={A.get(W+'id')for A in C.iter(W+'commentRangeStart')}&A;F={A.get(W+'id')for A in C.iter(W+'commentRangeEnd')}&A;B|=E
		if B:D.append(C)
		B-=F
	return D
def _revision_runs(p,author=None):
	B=author;C,D=[],[]
	for A in p.iter(W+'ins',W+'del'):
		if A.getparent()is not None and local(A.getparent().tag)=='rPr':continue
		if B and A.get(W+'author')!=B:continue
		(C if local(A.tag)=='ins'else D).extend(A for A in A.iter(W+'r')if A.find(W+'commentReference')is None)
	return C,D
COMMENTS_PART='word/comments.xml'
REL_TYPE='http://schemas.openxmlformats.org/officeDocument/2006/relationships/'
CT_COMMENTS='application/vnd.openxmlformats-officedocument.wordprocessingml.comments+xml'
CT_HEADER='application/vnd.openxmlformats-officedocument.wordprocessingml.header+xml'
DATE_FMT='%Y-%m-%dT%H:%M:%SZ'
DATE_FMT_LOCAL='%Y-%m-%dT%H:%M:%S'
class UnsupportedEdit(Exception):0
ORDER_PPR='pStyle','keepNext','keepLines','pageBreakBefore','framePr','widowControl','numPr','suppressLineNumbers','pBdr','shd','tabs','suppressAutoHyphens','kinsoku','wordWrap','overflowPunct','topLinePunct','autoSpaceDE','autoSpaceDN','bidi','adjustRightInd','snapToGrid','spacing','ind','contextualSpacing','mirrorIndents','suppressOverlap','jc','textDirection','textAlignment','textboxTightWrap','outlineLvl','divId','cnfStyle','rPr','sectPr','pPrChange'
ORDER_RPR='ins','del','moveFrom','moveTo','rStyle','rFonts','b','bCs','i','iCs','caps','smallCaps','strike','dstrike','outline','shadow','emboss','imprint','noProof','snapToGrid','vanish','webHidden','color','spacing','w','kern','position','sz','szCs','highlight','u','effect','bdr','shd','fitText','vertAlign','rtl','cs','em','lang','eastAsianLayout','specVanish','oMath','rPrChange'
ORDER_SECTPR='headerReference','footerReference','footnotePr','endnotePr','type','pgSz','pgMar','paperSrc','pgBorders','lnNumType','pgNumType','cols','formProt','vAlign','noEndnote','titlePg','textDirection','bidi','rtlGutter','docGrid','printerSettings','sectPrChange'
ORDER_TBLPR='tblStyle','tblpPr','tblOverlap','bidiVisual','tblStyleRowBandSize','tblStyleColBandSize','tblW','jc','tblCellSpacing','tblInd','tblBorders','shd','tblLayout','tblCellMar','tblLook','tblCaption','tblDescription','tblPrChange'
ORDERS={'pPr':ORDER_PPR,'rPr':ORDER_RPR,'sectPr':ORDER_SECTPR,'tblPr':ORDER_TBLPR}
SETTINGS_BEFORE_TRACK='writeProtection','view','zoom','removePersonalInformation','removeDateAndTime','doNotDisplayPageBoundaries','displayBackgroundShape','printPostScriptOverText','printFractionalCharacterWidth','printFormsData','embedTrueTypeFonts','embedSystemFonts','saveSubsetFonts','saveFormsData','mirrorMargins','alignBordersAndEdges','bordersDoNotSurroundHeader','bordersDoNotSurroundFooter','gutterAtTop','hideSpellingErrors','hideGrammaticalErrors','activeWritingStyle','proofState','formsDesign','attachedTemplate','linkStyles','stylePaneFormatFilter','stylePaneSortMethod','documentType','mailMerge','revisionView'
def local(tag):return tag.split('}')[-1]if isinstance(tag,str)else''
def fix_schema_order(root):
	E=0
	for(H,A)in ORDERS.items():
		for B in root.iter(W+H):
			C=list(B);F=[B for B in C if local(B.tag)in A];G=[A.index(local(B.tag))for B in F]
			if G!=sorted(G):
				I=[B for B in C if local(B.tag)not in A]
				for D in C:B.remove(D)
				for D in sorted(F,key=lambda k:A.index(local(k.tag)))+I:B.append(D)
				E+=1
	return E
def audit_schema_order(root):
	A=0
	for(D,B)in ORDERS.items():
		for E in root.iter(W+D):
			C=[B.index(local(A.tag))for A in E if local(A.tag)in B]
			if C!=sorted(C):A+=1
	return A
class RevisionClock:
	def __init__(B,now=None,steps=0):
		A=now;A=A or _dt.datetime.now().astimezone()
		if A.tzinfo is None:A=A.astimezone()
		B.t=(A-_dt.timedelta(seconds=steps)).replace(microsecond=0)
	def stamp(A):B=A.t.replace(tzinfo=None).strftime(DATE_FMT_LOCAL);C=A.t.astimezone(_dt.timezone.utc).strftime(DATE_FMT);return B,C
	def tick(A):A.t+=_dt.timedelta(seconds=1)
TOK=re.compile('\\[[^\\]\\n]*\\]|\\d[\\d,./]*\\d|\\d|[A-Za-z]+|[\u0590-\u05ff"\\\'׳״\\-]+|\\s+|.',re.S)
def tokens(s):return TOK.findall(s)
def char_ops(a,b):
	B,C=tokens(a),tokens(b);J,K=[0],[0]
	for O in B:J.append(J[-1]+len(O))
	for O in C:K.append(K[-1]+len(O))
	F=[];A=0
	while A<min(len(B),len(C))and B[A]==C[A]:A+=1
	E=0
	while E<min(len(B),len(C))-A and B[-1-E]==C[-1-E]:E+=1
	L=difflib.SequenceMatcher(_diff_junk,B[A:len(B)-E],C[A:len(C)-E],autojunk=False);P=[(B,C+A,D+A,E+A,F+A)for(B,C,D,E,F)in L.get_opcodes()]
	if A:P.insert(0,('equal',0,A,0,A))
	if E:P.append(('equal',len(B)-E,len(B),len(C)-E,len(C)))
	for(S,I,T,M,U)in P:
		D,G,V,W=J[I],J[T],K[M],K[U]
		if S=='equal':F.append(('equal',D,G,a[D:G]));continue
		if S=='replace'and T-I==1 and U-M==1 and not re.match('[\\d\\[]',B[I])and not re.match('[\\d\\[]',C[M])and not B[I].isspace():
			Q,R=B[I],C[M];L=difflib.SequenceMatcher(None,Q,R,autojunk=False);Z=sum(A.size for A in L.get_matching_blocks())
			if Z*2>max(len(Q),len(R)):
				for(c,N,H,X,Y)in L.get_opcodes():
					if c=='equal':F.append(('equal',D+N,D+H,Q[N:H]))
					else:
						if H>N:F.append(('delete',D+N,D+H,''))
						if Y>X:F.append(('insert',D+H,D+H,R[X:Y]))
				continue
		if G>D:F.append(('delete',D,G,''))
		if W>V:F.append(('insert',G,G,b[V:W]))
	return cleanup_ops(F)
CONTENT_WORD=re.compile('[A-Za-z]{4,}|\\b[A-Z]{2,}\\b|\\d|[א-ת]{3,}')
def _diff_junk(tok):return not CONTENT_WORD.search(tok)
def cleanup_ops(ops,min_side=10,max_equal=14):
	J=min_side
	def K(o):return o[2]-o[1]if o[0]=='delete'else len(o[3])if o[0]=='insert'else 0
	A=[]
	for E in ops:
		if E[0]=='equal':A.append(['equal',E])
		elif A and A[-1][0]=='chg':A[-1][1].append(E)
		else:A.append(['chg',[E]])
	G=True
	while G:
		G=False
		for B in range(1,len(A)-1):
			D=A[B]
			if D[0]!='equal'or A[B-1][0]!='chg'or A[B+1][0]!='chg':continue
			C=D[1]
			if CONTENT_WORD.search(C[3]):continue
			N=''.join(A[3]for A in A[B-1][1]+A[B+1][1]if A[0]=='insert');O=C[2]-C[1]<=max_equal and sum(K(A)for A in A[B-1][1])>=J and sum(K(A)for A in A[B+1][1])>=J;P=len(C[3].split())<=1 and len(C[3])<=7 and not re.search('[\\d\\[]',N+C[3])
			if O or P:Q=A[B-1][1]+[('delete',C[1],C[2],''),('insert',C[2],C[2],C[3])]+A[B+1][1];A[B-1:B+2]=[['chg',Q]];G=True;break
	F=[]
	for D in A:
		if D[0]=='equal':F.append(D[1]);continue
		H=[A for A in D[1]if A[0]=='delete'];L=''.join(A[3]for A in D[1]if A[0]=='insert')
		if H:R,M=min(A[1]for A in H),max(A[2]for A in H);F.append(('delete',R,M,''));I=M
		else:I=D[1][0][1]
		if L:F.append(('insert',I,I,L))
	return F
def span_ops(orig,spans):
	A=orig;D=[]
	for(E,F,I)in spans:
		if not E or A.count(E)!=1:raise UnsupportedEdit('הטווח "%s" אינו מופיע פעם אחת בדיוק בפסקה'%(E or'')[:40])
		J=A.index(E);D.append((J,J+len(E),F,I))
	D.sort()
	for K in range(1,len(D)):
		if D[K][0]<D[K-1][1]:raise UnsupportedEdit('שני טווחים חופפים באותה פסקה')
	G,B,H=[],0,''
	for(C,L,F,I)in D:
		if C>B:G.append(('equal',B,C,A[B:C],None));H+=A[B:C]
		for(M,N,O,P)in char_ops(A[C:L],F):G.append((M,C+N,C+O,P,None if M=='equal'else I))
		H+=F;B=L
	if B<len(A):G.append(('equal',B,len(A),A[B:],None));H+=A[B:]
	return G,H
QUOTE_FOLD=str.maketrans({'“':'"','”':'"','‘':"'",'’':"'"})
def quote_style(texts):A=''.join(texts);B=A.count('“')+A.count('”')>A.count('"');C=A.count('‘')+A.count('’')>A.count("'");return B,C
def match_quotes(text,style):
	A=text;F,G=style
	if not(F or G)or not A:return A
	H=[]
	for(C,B)in enumerate(A):
		D=A[C-1]if C else'';E=A[C+1]if C+1<len(A)else''
		if B in'"\''and not(HEB_CHAR.match(D or' ')or HEB_CHAR.match(E or' ')):
			I=not D or D.isspace()or D in'([{/'
			if B=='"'and F:B='“'if I else'”'
			elif B=="'"and G:B='‘'if I and E and not E.isspace()else'’'
		H.append(B)
	return''.join(H)
LATIN=re.compile('[A-Za-z][A-Za-z0-9/&.\\-]*(?:[ ][A-Za-z0-9/&.\\-]+)*')
HEB_SEG=re.compile('[\u0590-\u05ff](?:[\u0590-\u05ff"\'׳״\\- ]*[\u0590-\u05ff])?')
HEB_CHAR=re.compile('[\u0590-\u05ff]')
def script_split(text,rtl_para=True):
	D=text
	if not rtl_para:
		B,A=[],0
		for C in HEB_SEG.finditer(D):
			if C.start()>A:B.append((D[A:C.start()],True))
			B.append((C.group(),False));A=C.end()
		if A<len(D):B.append((D[A:],True))
		return[A for A in B if A[0]]
	B,A=[],0
	for C in LATIN.finditer(D):
		if C.start()>A:B.append((D[A:C.start()],False))
		B.append((C.group(),True));A=C.end()
	if A<len(D):B.append((D[A:],False))
	return[A for A in B if A[0]]
_SKIP={W+'txbxContent','{%s}Fallback'%MC_NS}
def body_paragraphs(root):
	A=root.find(W+'body');B=[]
	def C(el):
		for A in el:
			if A.tag in _SKIP:continue
			if A.tag==W+'p':B.append(A)
			else:C(A)
	C(A);return B
def _text_nodes(p):
	def D(el,anc):
		B=anc
		for A in el:
			if A.tag in _SKIP or A.tag==W+'p':continue
			C=local(A.tag)
			if C in('pPr','rPr'):continue
			if C in('t','delText','tab','br','cr'):
				if B and B[-1]=='r':yield(A,B)
			else:yield from D(A,B+(C,))
	yield from D(p,()if p.tag==W+'p'else(local(p.tag),))
def _node_text(node):
	A=local(node.tag)
	if A in('t','delText'):return node.text or''
	if A=='tab':return'\t'
	return'\n'
def para_text(p):return''.join(_node_text(A)for(A,B)in _text_nodes(p)if local(A.tag)!='delText'and'del'not in B)
def _mark(p):
	A=p.find(W+'pPr/'+W+'rPr')
	if A is None:return
	if A.find(W+'del')is not None and A.find(W+'ins')is not None:return'both'
	if A.find(W+'del')is not None:return'del'
	if A.find(W+'ins')is not None:return'ins'
def _revision_of(node,p):
	B=[]
	for A in node.iterancestors():
		if A is p:break
		if A.tag in(W+'ins',W+'del'):B.append((local(A.tag),A.get(W+'author')))
	return B
def received_reject_text(p,keep=()):
	A=''
	for(B,C)in _text_nodes(p):
		if all((A=='del')!=(B in keep)for(A,B)in _revision_of(B,p)):A+=_node_text(B)
	return A
def revision_key(e):return local(e.tag),e.get(W+'author'),e.get(W+'date')
def prior_revisions(root,authors):B={A for A in authors if A};return{revision_key(A)for A in root.iter(W+'ins',W+'del')if A.get(W+'author')in B}
def set_aside_prior(root,prior,label='%s (סבב קודם)'):
	B=set()
	for A in root.iter(W+'ins',W+'del'):
		if revision_key(A)in prior:A.set(W+'author',label%A.get(W+'author'));B.add(A.get(W+'author'))
	return B
def prior_edit_exists(p,old,new,prior):
	B=new;A=old
	if not A:return
	E,C=[],''
	for(H,N)in _text_nodes(p):
		D=[]
		for I in H.iterancestors():
			if I is p:break
			if I.tag==W+'del':D.append(I)
		J=_node_text(H)
		if not D and local(H.tag)!='delText':E+=[(B,None,len(C)+A)for(A,B)in enumerate(J)];C+=J
		elif D and all(revision_key(A)in prior for A in D):E+=[(A,D[-1],len(C))for A in J]
	L=''.join(A for(A,B,B)in E)
	if L.count(A)!=1:return
	M=L.index(A);K=E[M:M+len(A)];F=[A for(B,A,B)in K if A is not None]
	if not F:return
	if len(F)<len(K):raise UnsupportedEdit('חלק מ-"%s" כבר נמחק בסימון פתוח שלנו מסבב קודם. כתבו את old מול הנוסח הגלוי, אחרי קבלת הסימונים הפתוחים מהסבב הקודם'%A[:40])
	G=K[-1][2]
	if B and C[G:G+len(B)]!=B and C[max(0,G-len(B)):G]!=B:raise UnsupportedEdit('"%s" כבר נמחק בסימון פתוח שלנו מסבב קודם, והנוסח שבא במקומו אינו "%s". כתבו את old מול הנוסח הגלוי, אחרי קבלת הסימונים הפתוחים מהסבב הקודם'%(A[:40],B[:40]))
	return F[0],F[-1]
def reject_ours_view(root,author,prior=()):
	B=prior;B=B or()
	def D(e):return e is not None and e.get(W+'author')==author and revision_key(e)not in B
	C,A=[],''
	for E in body_paragraphs(root):
		G=_reject_ours_para(E,D);F=E.find(W+'pPr/'+W+'rPr');H=F.find(W+'ins')if F is not None else None;A+=G
		if D(H):continue
		C.append(A);A=''
	if A:C.append(A)
	return C
def _reject_ours_para(p,now_ours):
	D=''
	for(B,H)in _text_nodes(p):
		C=[]
		for A in B.iterancestors():
			if A is p:break
			if A.tag in(W+'ins',W+'del'):C.append((local(A.tag),now_ours(A)))
		E=[A for(A,B)in C if B];G=[A for(A,B)in C if not B]
		if E:F=E[0]=='del'
		else:F='del'not in G and local(B.tag)!='delText'
		if F:D+=_node_text(B)
	return D
DUP_WORDS=12
def duplicated_insertions(p,now_ours,k=DUP_WORDS):
	H=now_ours;I,C=[],[]
	for(D,N)in _text_nodes(p):
		if local(D.tag)=='delText'or'del'in N:continue
		E=False
		for F in D.iterancestors():
			if F is p:break
			E=E or F.tag==W+'ins'and H(F)
		J=_node_text(D);I.append(J);C+=[E]*len(J)
	if not any(C):return[]
	O=''.join(I);B=[(A.start(),A.end(),A.group(0).lower())for A in re.finditer('\\w+',O)];K=[A.lower()for A in re.findall('\\w+',_reject_ours_para(p,H))];G={}
	for A in range(len(K)-k+1):L=tuple(K[A:A+k]);G[L]=G.get(L,0)+1
	M={}
	for A in range(len(B)-k+1):M.setdefault(tuple(B for(A,A,B)in B[A:A+k]),[]).append((B[A][0],B[A+k-1][1]))
	return[' '.join(B)for(B,A)in M.items()if len(A)>1 and len(A)>G.get(B,0)and any(any(C[A:B])for(A,B)in A)]
def paragraph_views(root,mode):
	B=mode;C,A=[],''
	for G in body_paragraphs(root):
		H=''
		for(I,J)in _text_nodes(G):
			K=local(I.tag);L,M='ins'in J,'del'in J or K=='delText'
			if B=='accept':D=not M
			elif B=='reject':D=not L
			else:D=True
			if D:H+=_node_text(I)
		E=_mark(G)
		if B=='accept':F=E in('del','both')
		elif B=='reject':F=E in('ins','both')
		else:F=E=='both'
		A+=H
		if F:continue
		C.append(A);A=''
	if A:C.append(A)
	return C
def read_package(path_or_bytes):A=path_or_bytes;C=A if isinstance(A,(bytes,bytearray))else open(A,'rb').read();B=zipfile.ZipFile(io.BytesIO(C));return{A:B.read(A)for A in B.namelist()}
def document_root(path_or_bytes):return etree.fromstring(read_package(path_or_bytes)['word/document.xml'])
def accept_all(path):return paragraph_views(document_root(path),'accept')
def reject_all(path):return paragraph_views(document_root(path),'reject')
def received_paragraphs(path):return[para_text(A)for A in body_paragraphs(document_root(path))]
def read_comments(path_or_parts):
	B=path_or_parts;C=B if isinstance(B,dict)else read_package(B)
	if COMMENTS_PART not in C:return[]
	E=etree.fromstring(C[COMMENTS_PART]);D=[]
	for A in E.findall(W+'comment'):F='\n'.join(''.join(A.text or''for A in A.iter(W+'t'))for A in A.findall(W+'p'));D.append({'id':A.get(W+'id'),'author':A.get(W+'author'),'initials':A.get(W+'initials'),'date':A.get(W+'date'),'text':F})
	return D
def future_dated(path_or_parts,exclude_authors=(),today=None):
	C=path_or_parts;D=C if isinstance(C,dict)else read_package(C);F=(today or _dt.date.today()).isoformat();G={A for A in exclude_authors or()if A};E=[]
	for A in read_comments(D):
		if A.get('author')not in G and(A.get('date')or'')[:10]>F:E.append({'kind':'comment','author':A.get('author'),'date':A.get('date')})
	if'word/document.xml'in D:
		for B in etree.fromstring(D['word/document.xml']).iter(W+'ins',W+'del'):
			H=B.get(W+'date')or''
			if B.get(W+'author')not in G and H[:10]>F:E.append({'kind':local(B.tag),'author':B.get(W+'author'),'date':H})
	return E
def comment_paragraphs(root):
	A={}
	for(B,C)in enumerate(body_paragraphs(root)):
		for D in C.iter(W+'commentRangeStart'):A.setdefault(D.get(W+'id'),B)
	return A
def comment_paragraph_spans(root):
	A,B={},{}
	for(C,D)in enumerate(body_paragraphs(root)):
		for E in D.iter(W+'commentRangeStart'):A.setdefault(E.get(W+'id'),C)
		for F in D.iter(W+'commentRangeEnd'):B[F.get(W+'id')]=C
	return{C:(A,max(A,B.get(C,A)))for(C,A)in A.items()}
def revision_text(p,kind,author=None):
	B=author;C=[]
	for A in p.iter(W+kind):
		if A.getparent()is not None and local(A.getparent().tag)=='rPr':continue
		if B and A.get(W+'author')!=B:continue
		for D in A.iter(W+('t'if kind=='ins'else'delText')):C.append(D.text or'')
	return''.join(C)
_EDITABLE_RUN_CHILDREN={'rPr','t','tab','br','lastRenderedPageBreak','softHyphen'}
_LOCKED_CONTAINERS={'sdt','fldSimple','smartTag','customXml','oMath','oMathPara'}
_REVISION_CONTAINERS={'ins','del','moveFrom','moveTo'}
_FIELD_RUN_CHILDREN=_EDITABLE_RUN_CHILDREN|{'fldChar','instrText'}
class _Unit:
	__slots__='el','text','editable','s','e','deleted','field'
	def __init__(A,el,text,editable,deleted=False,field=False):A.el,A.text,A.editable,A.deleted=el,text,editable,deleted;A.field=field;A.s=A.e=0
class TrackedDocx:
	def __init__(A,src,author,initials=None,clock=None,prior_authors=(),prior_keys=(),lang='he'):C=prior_authors;B=author;A.parts=read_package(src);A.internal_author,A.internal_initials,A.internal_header_text=internal_author(lang);A.order=list(A.parts);A.root=etree.fromstring(A.parts['word/document.xml']);A.body=A.root.find(W+'body');A.paras=body_paragraphs(A.root);A.orig_texts=[para_text(A)for A in A.paras];A.received_texts=list(A.orig_texts);A.resolved={};A.author=B;A.our_names={B}|{A for A in C or()if A};D={tuple(A)for A in prior_keys or()};A.prior=prior_revisions(A.root,[B]+list(C or()))|{revision_key(A)for A in A.root.iter(W+'ins',W+'del')if revision_key(A)in D};A.existing=[];A.initials=initials or''.join(A[0]for A in B.split()[:2]);A.clock=clock or RevisionClock();A.targets={};A.inserted={};A.comments=[];A.decision_log=[];A.highlight_in=len(list(A.root.iter(W+'highlight')));A._base_comments=A.parts.get(COMMENTS_PART);A._next_id=A._max_id()+1;A._edited=set();A._finalized=False;A.rtl_default=A._styles_rtl_default();A.quotes=quote_style(A.orig_texts)
	def _max_id(B):
		A=0
		for C in('word/document.xml',COMMENTS_PART):
			if C in B.parts:
				for D in re.finditer(b'w:id="(\\d+)"',B.parts[C]):A=max(A,int(D.group(1)))
		return max(A,100)
	def _id(A):A._next_id+=1;return str(A._next_id)
	def _rev(B,tag):A=etree.Element(W+tag);C,D=B.clock.stamp();A.set(W+'id',B._id());A.set(W+'author',B.author);A.set(W+'date',C);A.set(DATE_UTC_ATTR,D);return A
	def _styles_rtl_default(E):
		C=E.parts.get('word/styles.xml')
		if not C:return False
		D=etree.fromstring(C)
		for F in D.iter(W+'pPrDefault'):
			A=F.find('.//'+W+'bidi')
			if A is not None and A.get(W+'val')not in('0','false'):return True
		for B in D.findall(W+'style'):
			if B.get(W+'default')=='1'and B.get(W+'type')=='paragraph':
				A=B.find(W+'pPr/'+W+'bidi')
				if A is not None and A.get(W+'val')not in('0','false'):return True
		return False
	def _para_rtl(C,p):
		A=p.find(W+'pPr/'+W+'bidi')
		if A is not None:return A.get(W+'val')not in('0','false')
		if C.rtl_default:return True
		B=para_text(p);return len(HEB_CHAR.findall(B))>=len(re.findall('[A-Za-z]',B))
	@staticmethod
	def _clean_rpr(rpr,latin):
		A=copy.deepcopy(rpr)if rpr is not None else etree.Element(W+'rPr');A.tag=W+'rPr'
		for C in('highlight','ins','del','rPrChange','vanish','webHidden'):
			for B in A.findall(W+C):A.remove(B)
		for B in A.findall(W+'rtl'):A.remove(B)
		if latin:
			for B in A.findall(W+'cs'):A.remove(B)
		else:etree.SubElement(A,W+'rtl')
		fix_schema_order(A);return A
	@staticmethod
	def _content(r,text,deleted):
		for(C,A)in enumerate(re.split('(\\t|\\n)',text)):
			if A=='\t':etree.SubElement(r,W+'tab')
			elif A=='\n':etree.SubElement(r,W+'br')
			elif A:B=etree.SubElement(r,W+('delText'if deleted else't'));B.set(XML_SPACE,'preserve');B.text=A
	def _orig_run(B,rpr,text,deleted=False):
		A=etree.Element(W+'r')
		if rpr is not None:A.append(copy.deepcopy(rpr))
		B._content(A,text,deleted);return A
	def _ins_el(A,rpr,text,rtl_para=True):
		B=A._rev('ins')
		for(D,E)in script_split(text,rtl_para):C=etree.SubElement(B,W+'r');C.append(A._clean_rpr(rpr,E));A._content(C,D,False)
		return B
	def _units(F,p):
		A=[];B=[0]
		def G(r,locked,deleted):
			C=deleted;D={local(A.tag)for A in r};I=''if C else''.join(_node_text(A)for(A,B)in _text_nodes(r));E=B[0]>0;F=False
			for J in r.iter(W+'fldChar'):
				F=True;G=J.get(W+'fldCharType')
				if G=='begin':B[0]+=1
				elif G=='end'and B[0]:B[0]-=1
			H=not locked and not C and r.tag==W+'r';A.append(_Unit(r,I,H and not E and D<=_EDITABLE_RUN_CHILDREN,C,field=H and(E or F)and D<=_FIELD_RUN_CHILDREN))
		def D(el,locked,deleted):
			E=deleted;C=locked
			for A in el:
				if A.tag in _SKIP:continue
				B=local(A.tag)
				if B in('pPr','rPr','sdtPr','sdtEndPr'):continue
				if B=='r':G(A,C,E)
				elif B in('ins','del')and revision_key(A)in F.prior:D(A,C,E or B=='del')
				elif B in _REVISION_CONTAINERS:raise UnsupportedEdit('בפסקה יש %s'%F._whose(A))
				else:D(A,C or B in _LOCKED_CONTAINERS,E)
		D(p,False,False);C=0
		for E in A:E.s,C=C,C+len(E.text);E.e=C
		if''.join(A.text for A in A)!=para_text(p):raise UnsupportedEdit('מבנה הפסקה אינו נתמך (טקסט מחוץ לריצות)')
		return A
	def _their(A,el):return el.get(W+'author')not in A.our_names and revision_key(el)not in A.prior
	def _now_ours(A,el):return el is not None and el.get(W+'author')==A.author and revision_key(el)not in A.prior
	def _whose(C,el):
		A={'ins':'הוספה','del':'מחיקה','moveFrom':'העברה','moveTo':'העברה'}.get(local(el.tag),'סימון');B='%s, %s'%(el.get(W+'author')or'?',el.get(W+'date')or'?')
		if not C._their(el):return'%s פתוחה שלנו מסבב קודם (%s), שהמנוע אינו עורך בתוכה: לסמן ידנית'%(A,B)
		return'%s פתוחה של הצד שכנגד (%s): להכריע אותה (their_changes) לפני הסימון'%(A,B)
	def has_their_revisions(A,idx):B=A.paras[idx];return any(A._their(B)for B in B.iter(W+'ins',W+'del',W+'moveFrom',W+'moveTo'))
	def snapshot_para(A,idx):B=idx;import copy;return copy.deepcopy(A.paras[B]),A.orig_texts[B],A.resolved.get(B)
	def restore_para(A,idx,snap):
		B=idx;C,F,D=snap;E=A.paras[B];E.getparent().replace(E,C);A.paras[B]=C;A.orig_texts[B]=F
		if D is None:A.resolved.pop(B,None)
		else:A.resolved[B]=D
	def resolve_theirs(B,idx,mode):
		F=mode;E=idx
		if F not in('accept','reject'):raise UnsupportedEdit('their_changes: %r אינו accept או reject'%(F,))
		C=B.paras[E];G=C.find(W+'pPr/'+W+'rPr')
		if G is not None and any(A is not None and B._their(A)for A in(G.find(W+'ins'),G.find(W+'del'))):raise UnsupportedEdit('הצד שכנגד פיצל או איחד כאן פסקאות: לסמן ידנית')
		if any(B._their(A)for A in C.iter(W+'moveFrom',W+'moveTo')):raise UnsupportedEdit('הצד שכנגד העביר כאן טקסט ממקום למקום: לסמן ידנית')
		K=W+'commentRangeStart',W+'commentRangeEnd',W+'bookmarkStart',W+'bookmarkEnd'
		for A in list(C.iter(W+'ins',W+'del')):
			D=A.getparent()
			if D is None or D.tag==W+'rPr'or not B._their(A):continue
			L=(A.tag==W+'ins')==(F=='accept');I=D.index(A)
			if L:
				if A.tag==W+'del':
					for H in A.iter(W+'delText'):H.tag=W+'t'
					for H in A.iter(W+'delInstrText'):H.tag=W+'instrText'
				J=list(A)
			else:J=[A for A in A.iter()if A.tag in K]+[A for A in A.iter(W+'r')if A.find(W+'commentReference')is not None]
			for M in J:D.insert(I,M);I+=1
			D.remove(A)
		for A in list(C.iter(W+'ins',W+'del')):
			if A.getparent()is not None and A.getparent().tag!=W+'rPr'and not len(A)and not B._their(A):A.getparent().remove(A)
		B.orig_texts[E]=para_text(C);B.resolved[E]=F;return B.orig_texts[E]
	def _check_idx(B,idx):
		A=idx
		if not 0<=A<len(B.paras):raise UnsupportedEdit('אין פסקה %s בטיוטה'%A)
		if A in B._edited:raise UnsupportedEdit('פסקה %d כבר סומנה. מאחדים את ההכרעות לפני הסימון'%A)
	def set_text(B,idx,target,external=None,internal=None):
		C=idx;A=target;B._check_idx(C);D=B.orig_texts[C];A=match_quotes(A,B.quotes)
		if A==D:raise UnsupportedEdit('נוסח היעד זהה לנוסח שהתקבל')
		E=[(A[0],A[1],A[2],A[3],'all')for A in char_ops(D,A)];B._apply_ops(C,E,{'all':(external,internal)});B.targets[C]=A;return A
	def replace_span(A,idx,old,new,external=None,internal=None):return A.edit_spans(idx,[(old,new,external,internal)])
	def edit_spans(A,idx,spans,dry_run=False):
		D=spans;B=idx;A._check_idx(B);F=[(A._absorb_prior_ins(B,E,match_quotes(C,A.quotes)),match_quotes(C,A.quotes),'s%d'%D)for(D,(E,C,F,F))in enumerate(D)];E,C=span_ops(A.orig_texts[B],F)
		if dry_run:A._check_ops(B,E);return C
		G={'s%d'%A:(C,D)for(A,(B,B,C,D))in enumerate(D)};A._apply_ops(B,E,G);A.targets[B]=C;return C
	def _prior_ins_ranges(D,idx):
		A,B=[],0
		for(E,H)in _text_nodes(D.paras[idx]):
			if local(E.tag)=='delText'or'del'in H:continue
			C=_node_text(E);F=False
			for G in E.iterancestors():
				if G is D.paras[idx]:break
				F=F or G.tag==W+'ins'and revision_key(G)in D.prior
			if F and C:
				if A and A[-1][1]==B:A[-1][1]=B+len(C)
				else:A.append([B,B+len(C)])
			B+=len(C)
		return[tuple(A)for A in A]
	def _absorb_prior_ins(K,idx,old,new):
		C=old;A=K.orig_texts[idx]
		if not C or not new or A.count(C)!=1:return C
		B=A.index(C);D=B+len(C);G,H=B,D
		for(E,F)in K._prior_ins_ranges(idx):
			if E<D and F>B:continue
			if E>=D and not A[D:E].strip():I=B,F
			elif F<=B and not A[F:B].strip():I=E,D
			else:continue
			J,L=re.findall('\\w+',A[E:F].lower()),re.findall('\\w+',new.lower())
			if len(J)<4:continue
			M=sum(A.size for A in difflib.SequenceMatcher(None,J,L,autojunk=False).get_matching_blocks())
			if M>=max(6,.5*min(len(J),len(L))):G,H=min(G,I[0]),max(H,I[1])
		return A[G:H]
	def _check_ops(C,idx,ops):
		D=idx;G=C._units(C.paras[D]);I,B=[],None
		for A in G:
			if A.editable:B=None
			elif B is None:B=[A.s,A.e,[A]];I.append(B)
			else:B[1]=A.e;B[2].append(A)
		C._field_del={}
		for(J,H,K,N,M)in ops:
			for(E,F,L)in I:
				if F<=E:continue
				if J=='delete'and H<F and K>E:
					if H<=E and K>=F and all(A.field for A in L):
						for A in L:C._field_del[id(A)]=M
						continue
					raise UnsupportedEdit('השינוי נוגע בשדה או באובייקט נעול בפסקה %d'%D)
				if J=='insert'and E<H<F:raise UnsupportedEdit('הוספה בתוך שדה נעול בפסקה %d'%D)
		if not any(A.editable for A in G):raise UnsupportedEdit('אין בפסקה %d ריצה שאפשר לערוך'%D)
		return G
	def _apply_ops(B,idx,ops,bubbles):
		N=idx;I=ops;Z=B.paras[N];Q=B._check_ops(N,I);J=[A for A in Q if A.editable]
		def a(pos):
			for A in J:
				if A.s<pos<=A.e:return A
			for A in J:
				if A.s>=pos:return A
			return J[-1]
		R,S={},{}
		for(D,O)in enumerate(I):
			if O[0]=='insert':
				R[D]=a(O[1]);E=I[D-1]if D else None
				if E is not None and E[0]=='delete'and E[2]==O[1]:
					G=next((A for A in J if A.s<E[2]and A.e>E[1]and A.text[max(E[1],A.s)-A.s:min(E[2],A.e)-A.s].strip()),None)
					if G is not None:S[D]=G
		K={};b=B._para_rtl(Z)
		for A in Q:
			if id(A)in B._field_del:
				F=B._rev('del');A.el.addprevious(F)
				for L in A.el.findall(W+'t'):L.tag=W+'delText';L.set(XML_SPACE,'preserve')
				for L in A.el.findall(W+'instrText'):L.tag=W+'delInstrText'
				F.append(A.el);K.setdefault(B._field_del[id(A)],[]).append(F);continue
			if not A.editable or A.e==A.s:continue
			P=A.el.find(W+'rPr');H=[]
			for(D,(T,c,d,e,M))in enumerate(I):
				if T=='insert':
					if R[D]is A:G=S.get(D);C=B._ins_el(G.el.find(W+'rPr')if G is not None else P,e,b);H.append(C);K.setdefault(M,[]).append(C)
					continue
				U,V=max(c,A.s),min(d,A.e)
				if U>=V:continue
				X=A.text[U-A.s:V-A.s]
				if T=='equal':H.append(B._orig_run(P,X))
				else:F=B._rev('del');F.append(B._orig_run(P,X,deleted=True));H.append(F);K.setdefault(M,[]).append(F)
			for C in H:A.el.addprevious(C)
			A.el.getparent().remove(A.el)
			for C in H:
				if C.tag==W+'ins'and C.getparent().tag==W+'ins':B._split_prior_ins(C)
		for(M,Y)in K.items():f,g=bubbles.get(M,(None,None));B._anchor(Y[0],Y[-1],f,g,ref_wrap=None)
		B._edited.add(N);B.clock.tick()
	def _split_prior_ins(D,el):
		A=el.getparent();C=list(el.itersiblings())
		if C:
			B=etree.Element(A.tag,attrib=dict(A.attrib));B.set(W+'id',D._id())
			for E in C:B.append(E)
			A.addnext(B)
		A.addnext(el)
		if not len(A):A.getparent().remove(A)
	def delete_paragraph(A,idx,external=None,internal=None):
		H=internal;G=external;C=idx;A._check_idx(C);D=A.paras[C];I=A._units(D)
		if any(A.el.tag!=W+'r'and A.text for A in I):raise UnsupportedEdit('פסקה %d כוללת נוסחה, ואינה נמחקת בשלמותה'%C)
		for M in list(D.iter(W+'fldSimple')):A._expand_fld_simple(M)
		I=A._units(D);E=[]
		for K in I:
			B=K.el;L=[local(A.tag)for A in B if local(A.tag)!='rPr']
			if not L or L==['commentReference']or K.deleted:continue
			J=A._rev('del');B.addprevious(J);B.getparent().remove(B)
			for F in B.findall(W+'t'):F.tag=W+'delText';F.set(XML_SPACE,'preserve')
			for F in B.findall(W+'instrText'):F.tag=W+'delInstrText'
			J.append(B);E.append(J)
		A._mark_para(D,'del')
		if E:A._anchor(E[0],E[-1],G,H,ref_wrap='del')
		elif G or H:A.comment_only(C,G,H)
		A.targets[C]=None;A._edited.add(C);A.clock.tick()
	@staticmethod
	def _expand_fld_simple(fs):
		A=fs;E=[A for A in A if A.tag==W+'r'];F=E[0].find(W+'rPr')if E else None
		def C(kind=None,instr=None):
			B=instr;A=etree.Element(W+'r')
			if F is not None:A.append(copy.deepcopy(F))
			if B is not None:C=etree.SubElement(A,W+'instrText');C.set(XML_SPACE,'preserve');C.text=B
			else:D=etree.SubElement(A,W+'fldChar');D.set(W+'fldCharType',kind)
			return A
		G=C('begin');H=G.find(W+'fldChar')
		for B in('fldLock','dirty'):
			if A.get(W+B)is not None:H.set(W+B,A.get(W+B))
		D=A.find(W+'fldData')
		if D is not None:A.remove(D);H.append(D)
		J=[G,C(instr=A.get(W+'instr')or''),C('separate')]+list(A)+[C('end')];I,K=A.getparent(),A.getparent().index(A);I.remove(A)
		for(B,L)in enumerate(J):I.insert(K+B,L)
	def insert_paragraph(A,after_idx,text,number=None,template_idx=None,external=None,internal=None):
		M=template_idx;H=number;E=after_idx;B=text
		if not 0<=E<len(A.paras):raise UnsupportedEdit('אין פסקת עוגן %s'%E)
		if not B or not B.strip():raise UnsupportedEdit('אין מוסיפים פסקה ריקה')
		B=match_quotes(B,A.quotes);I=A.paras[E if M is None else M];D=etree.Element(W+'p');N=I.find(W+'pPr');C=copy.deepcopy(N)if N is not None else etree.Element(W+'pPr')
		for O in('rPr','sectPr','pPrChange'):
			for P in C.findall(W+O):C.remove(P)
		D.append(C);A._mark_para(D,'ins');F=[A for A in I.iter(W+'r')if A.find(W+'t')is not None];Q=F[-1].find(W+'rPr')if F else None;R=F[0].find(W+'rPr')if F else None;J=A._para_rtl(I)
		if len(HEB_CHAR.findall(B))>=len(re.findall('[A-Za-z]',B))and HEB_CHAR.search(B):
			J=True;K=C.find(W+'bidi')
			if K is None:etree.SubElement(C,W+'bidi')
			elif K.get(W+'val')in('0','false'):K.attrib.pop(W+'val')
			L=C.find(W+'jc')
			if L is not None and L.get(W+'val')in('left','start'):L.set(W+'val','right')
			fix_schema_order(C)
		G=A._ins_el(Q,B,J)
		if H:
			S=A._ins_el(R,H,J)
			for T in list(S)[::-1]:G.insert(0,T)
		D.append(G);A._anchor(G,G,external,internal,ref_wrap='ins');A.inserted.setdefault(E,[]).append((D,(H or'')+B));A.clock.tick();return D
	def comment_only(B,idx,external=None,internal=None):
		C=B.paras[idx];A=[A for A in C if local(A.tag)!='pPr']
		if not A:D=etree.SubElement(C,W+'r');A=[D]
		B._anchor(A[0],A[-1],external,internal,ref_wrap=None);B.clock.tick()
	def _anchor(A,first,last,external,internal,ref_wrap):
		E=ref_wrap
		for(I,J,F)in((A.author,A.initials,external),(A.internal_author,A.internal_initials,internal)):
			if not F:continue
			C=A._id();K,N=A.clock.stamp();A.comments.append((C,I,J,F,K));G=etree.Element(W+'commentRangeStart');G.set(W+'id',C);B=etree.Element(W+'commentRangeEnd');B.set(W+'id',C);first.addprevious(G);last.addnext(B);D=etree.Element(W+'r');L=etree.SubElement(D,W+'rPr');etree.SubElement(L,W+'rtl');M=etree.SubElement(D,W+'commentReference');M.set(W+'id',C)
			if E:H=A._rev(E);H.append(D);B.addnext(H)
			else:B.addnext(D)
			last=B if not E else B.getnext()
	def _mark_para(C,p,tag):
		A=p.find(W+'pPr')
		if A is None:A=etree.Element(W+'pPr');p.insert(0,A)
		B=A.find(W+'rPr')
		if B is None:B=etree.SubElement(A,W+'rPr')
		if B.find(W+tag)is None:B.insert(0,C._rev(tag))
		fix_schema_order(B);fix_schema_order(A)
	@staticmethod
	def _unmark_para(p,tag):
		A=p.find(W+'pPr/'+W+'rPr')
		if A is not None:
			for B in A.findall(W+tag):A.remove(B)
	def _final_body_paragraph(B):A=[A for A in B.body if A.tag==W+'p'];return A[-1]if A else None
	def finalize(A):
		if A._finalized:return
		E=len(A.paras)-1;C=A.paras[E];H=C.getparent()is A.body and A._final_body_paragraph()is C
		for I in sorted(A.inserted,reverse=True):
			J=A.paras[I]
			for(F,L)in A.inserted[I]:J.addnext(F);J=F
		D=[A for(A,B)in A.inserted.get(E,[])]
		if H and D and A._final_body_paragraph()is D[-1]:
			if A.targets.get(E,'')is None:
				G=D[-1]
				for F in D[:-1]:C.addprevious(F)
				A._unmark_para(C,'del')
				for K in[A for A in G if local(A.tag)!='pPr']:C.append(K)
				G.getparent().remove(G)
			else:A._mark_para(C,'ins');A._unmark_para(D[-1],'ins')
		elif H and A.targets.get(E,'')is None:
			B=C.getprevious()
			while B is not None and(B.tag!=W+'p'or _mark(B)=='del'):B=B.getprevious()
			if B is None:raise UnsupportedEdit('אין פסקה לפני הפסקה האחרונה שנמחקה')
			if _mark(B)=='ins':raise UnsupportedEdit('לפני הפסקה האחרונה שנמחקה יש פסקה שהוספנו: מוסיפים אחרי הפסקה האחרונה')
			A._mark_para(B,'del')
		A._finalized=True
	def expected_accept(B):
		C,A=[],''
		for(D,G)in enumerate(B.orig_texts):
			E=B.targets.get(D,G);F=[(E,B._their_mark_deleted(D))]if E is not None else[];F+=[(A,False)for(B,A)in B.inserted.get(D,[])]
			for(H,I)in F:
				A+=H
				if not I:C.append(A);A=''
		if A:C.append(A)
		return C
	def _their_mark_deleted(A,idx):B=A.paras[idx].find(W+'pPr/'+W+'rPr');C=B.find(W+'del')if B is not None else None;return C is not None and not A._now_ours(C)
	def verify_roundtrip(A):
		A.finalize();C=[]
		for(F,D)in(('accept',A.expected_accept()),('reject',A.orig_texts)):
			E=paragraph_views(A.root,F)if F=='accept'else reject_ours_view(A.root,A.author,A.prior)
			if E!=D:
				for B in range(max(len(E),len(D))):
					G=E[B]if B<len(E)else None;H=D[B]if B<len(D)else None
					if G!=H:C.append((F,B,H,G));break
		for B in sorted(A._edited):
			I=duplicated_insertions(A.paras[B],A._now_ours)
			if I:C.append(('duplicate',B,'',I[0]))
		J=[C for B in A.root.iter(W+'ins')if B.get(W+'author')==A.author for C in B.iter(W+'highlight')]
		if J:C.append(('highlight',None,0,len(J)))
		return C
	def _used_para_ids(C):
		B=set()
		for A in C.parts.values():
			if isinstance(A,(bytes,bytearray))and b'paraId'in A:B.update(A.upper()for A in re.findall(b'paraId="([0-9A-Fa-f]{8})"',A))
		return B
	def _comments_xml(E):
		if E._base_comments:A=etree.fromstring(E._base_comments)
		else:A=etree.Element(W+'comments',nsmap={'w':W_NS})
		if W14_NS not in A.nsmap.values():
			F=dict(A.nsmap);F['w14']=W14_NS;F.setdefault('mc',MC_NS);G=etree.Element(A.tag,nsmap=F)
			for(H,N)in A.attrib.items():G.set(H,N)
			for O in list(A):G.append(O)
			A=G
		K=(A.get(MC_IGNORABLE)or'').split()
		if'w14'not in K:A.set(MC_IGNORABLE,' '.join(K+['w14']))
		L=E._used_para_ids()
		def P():
			while True:
				A=('%08X'%secrets.randbits(31)).encode()
				if A not in L and A!=b'00000000':L.add(A);return A.decode()
		for(Q,R,S,I,T)in E.comments:
			B=etree.SubElement(A,W+'comment');B.set(W+'id',Q);B.set(W+'author',R);B.set(W+'date',T);B.set(W+'initials',S);J=len(HEB_CHAR.findall(I))>=len(re.findall('[A-Za-z]',I))
			for(H,U)in enumerate(I.split('\n')):
				C=etree.SubElement(B,W+'p');C.set('{%s}paraId'%W14_NS,P());C.set('{%s}textId'%W14_NS,'77777777');V=etree.SubElement(C,W+'pPr')
				if J:etree.SubElement(V,W+'bidi')
				if H==0:
					D=etree.SubElement(C,W+'r')
					if J:etree.SubElement(etree.SubElement(D,W+'rPr'),W+'rtl')
					etree.SubElement(D,W+'annotationRef')
				for(X,Y)in script_split(U,J):
					D=etree.SubElement(C,W+'r')
					if not Y:etree.SubElement(etree.SubElement(D,W+'rPr'),W+'rtl')
					M=etree.SubElement(D,W+'t');M.set(XML_SPACE,'preserve');M.text=X
		return etree.tostring(A,xml_declaration=True,encoding='UTF-8',standalone=True)
	def _next_rid(A):B=[int(A)for A in re.findall(b'Id="rId(\\d+)"',A.parts['word/_rels/document.xml.rels'])];return'rId%d'%(max(B or[0])+1)
	def _add_rel(D,rid,rtype,target):
		E=target;A=rid;B=etree.fromstring(D.parts['word/_rels/document.xml.rels'])
		for F in B:
			if F.get('Target')==E:return F.get('Id')
		G={A.get('Id')for A in B}
		while A in G:A+='x'
		C=etree.SubElement(B,'{%s}Relationship'%PKG_REL_NS);C.set('Id',A);C.set('Type',REL_TYPE+rtype);C.set('Target',E);D.parts['word/_rels/document.xml.rels']=etree.tostring(B,xml_declaration=True,encoding='UTF-8',standalone=True);return A
	def _add_override(B,part,ctype):
		A=etree.fromstring(B.parts['[Content_Types].xml'])
		if any(A.get('PartName')=='/'+part for A in A):return
		C=etree.SubElement(A,'{%s}Override'%CT_NS);C.set('PartName','/'+part);C.set('ContentType',ctype);B.parts['[Content_Types].xml']=etree.tostring(A,xml_declaration=True,encoding='UTF-8',standalone=True)
	def _add_internal_header(A):
		E=etree.Element(W+'hdr',nsmap={'w':W_NS});F=etree.SubElement(E,W+'p');G=etree.SubElement(F,W+'pPr');etree.SubElement(G,W+'bidi');K=etree.SubElement(G,W+'jc');K.set(W+'val','center');H=etree.SubElement(F,W+'r');I=etree.SubElement(H,W+'rPr');etree.SubElement(I,W+'b')
		if A.internal_author==INTERNAL_AUTHOR:etree.SubElement(I,W+'rtl')
		L=etree.SubElement(H,W+'t');L.text=A.internal_header_text;A.parts[INTERNAL_HEADER_PART]=etree.tostring(E,xml_declaration=True,encoding='UTF-8',standalone=True);A._add_override(INTERNAL_HEADER_PART,CT_HEADER)
		for J in A.root.iter(W+'sectPr'):
			B=[A for A in J.findall(W+'headerReference')if A.get(W+'type','default')=='default']
			if B:M=B[0].get('{%s}id'%R_NS);C=A._add_rel('%s_%s'%(INTERNAL_REL_PREFIX,M),'header','headerInternal.xml');B[0].set('{%s}id'%R_NS,C)
			else:C=A._add_rel(INTERNAL_REL_PREFIX,'header','headerInternal.xml');D=etree.Element(W+'headerReference');D.set(W+'type','default');D.set('{%s}id'%R_NS,C);J.insert(0,D)
	def _enable_track_revisions(C):
		A=etree.fromstring(C.parts['word/settings.xml'])
		for F in A.findall(W+'trackChanges'):A.remove(F)
		if A.find(W+'trackRevisions')is None:
			D=etree.Element(W+'trackRevisions');B=None
			for E in A:
				if local(E.tag)in SETTINGS_BEFORE_TRACK:B=E
			if B is not None:B.addnext(D)
			else:A.insert(0,D)
		C.parts['word/settings.xml']=etree.tostring(A,xml_declaration=True,encoding='UTF-8',standalone=True)
	def _clean_metadata(A):
		F=A.clock.t.astimezone(_dt.timezone.utc).strftime(DATE_FMT);G=esc(A.author);I='<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" xmlns:dcmitype="http://purl.org/dc/dcmitype/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"><dc:creator>%s</dc:creator><cp:lastModifiedBy>%s</cp:lastModifiedBy><cp:revision>1</cp:revision><dcterms:created xsi:type="dcterms:W3CDTF">%s</dcterms:created><dcterms:modified xsi:type="dcterms:W3CDTF">%s</dcterms:modified></cp:coreProperties>'%(G,G,F,F);A.parts['docProps/core.xml']=I.encode('utf-8')
		if'docProps/app.xml'in A.parts:
			C=A.parts['docProps/app.xml'].decode('utf-8')
			for B in('Template','TotalTime','Company','Manager','Pages','Lines'):C=re.sub('\\s*<%s>[^<]*</%s>'%(B,B),'',C);C=re.sub('\\s*<%s/>'%B,'',C)
			for B in('HeadingPairs','TitlesOfParts'):C=re.sub('\\s*<%s>.*?</%s>'%(B,B),'',C,flags=re.S);C=re.sub('\\s*<%s/>'%B,'',C)
			H=paragraph_views(A.root,'accept');D='\n'.join(H);J={'Words':len(D.split()),'Characters':len(re.sub('\\s','',D)),'CharactersWithSpaces':len(D.replace('\n','')),'Paragraphs':sum(1 for A in H if A.strip())}
			for(B,E)in J.items():C=re.sub('<%s>[^<]*</%s>'%(B,B),'<%s>%d</%s>'%(B,E,B),C)
			A.parts['docProps/app.xml']=C.encode('utf-8')
		if'docProps/thumbnail.jpeg'in A.parts:del A.parts['docProps/thumbnail.jpeg'];A.parts['_rels/.rels']=re.sub(b'<Relationship [^>]*thumbnail[^>]*/>',b'',A.parts['_rels/.rels']);A.parts['[Content_Types].xml']=re.sub(b'<Override PartName="/docProps/thumbnail\\.jpeg"[^>]*/>',b'',A.parts['[Content_Types].xml'])
		if b'dataBinding'not in etree.tostring(A.root):
			for E in[A for A in A.parts if A.startswith('customXml/')]:del A.parts[E]
			A.parts['word/_rels/document.xml.rels']=re.sub(b'<Relationship [^>]*customXml[^>]*/>',b'',A.parts['word/_rels/document.xml.rels']);A.parts['[Content_Types].xml']=re.sub(b'<Override PartName="/customXml/[^"]*"[^>]*/>',b'',A.parts['[Content_Types].xml'])
	def _serialize_document(A):
		C=dict(A.root.nsmap);C.setdefault('mc',MC_NS);C['w16du']=W16DU_NS;B=etree.Element(A.root.tag,nsmap=C)
		for(E,F)in A.root.attrib.items():B.set(E,F)
		D=B.get(MC_IGNORABLE,'').split()
		if'w16du'not in D:D.append('w16du')
		B.set(MC_IGNORABLE,' '.join(D))
		for G in list(A.root):B.append(G)
		A.root=B;A.body=B.find(W+'body');fix_schema_order(A.root);A.parts['word/document.xml']=etree.tostring(B,xml_declaration=True,encoding='UTF-8',standalone=True)
	def _highlight_areo(B):
		D={A[0]for A in B.comments if A[1]in INTERNAL_AUTHORS and str(A[3]or'').strip().startswith(AREO_LABEL_PREFIXES)}
		for E in areo_paragraphs(B.root,D):
			F,G=_revision_runs(E,B.author)
			for C in F or G:
				A=C.find(W+'rPr')
				if A is None:A=etree.Element(W+'rPr');C.insert(0,A)
				if A.find(W+'highlight')is None:H=etree.SubElement(A,W+'highlight');H.set(W+'val',AREO_HIGHLIGHT);fix_schema_order(A)
	def to_bytes(A,internal_header=True):
		A.finalize();A._highlight_areo()
		if A.comments:A.parts[COMMENTS_PART]=A._comments_xml();A._add_rel(A._next_rid(),'comments','comments.xml');A._add_override(COMMENTS_PART,CT_COMMENTS)
		if internal_header and INTERNAL_HEADER_PART not in A.parts:A._add_internal_header()
		A._enable_track_revisions();A._clean_metadata();A._serialize_document();return write_package(A.parts,A.order)
	def save(B,out_path,internal_header=True):
		A=out_path;C=B.to_bytes(internal_header)
		with open(A,'wb')as D:D.write(C)
		return A
def esc(s):return(s or'').replace('&','&amp;').replace('<','&lt;').replace('>','&gt;').replace('"','&quot;')
def write_package(parts,order=()):
	A=parts;B=['[Content_Types].xml']+[B for B in order if B in A and B!='[Content_Types].xml'];B+=[A for A in A if A not in B];C=io.BytesIO()
	with zipfile.ZipFile(C,'w',zipfile.ZIP_DEFLATED)as E:
		for D in B:E.writestr(D,A[D])
	return C.getvalue()
def strip_internal(src,dst=None):
	A=read_package(src);Q=list(A);G=set();C=etree.fromstring(A['word/document.xml'])
	if COMMENTS_PART in A:
		E=etree.fromstring(A[COMMENTS_PART])
		for R in areo_paragraphs(C,_areo_comment_ids(E)):
			S,T=_revision_runs(R)
			for U in S+T:
				H=U.find(W+'rPr')
				for B in list(H.findall(W+'highlight'))if H is not None else():
					if B.get(W+'val')==AREO_HIGHLIGHT:H.remove(B)
		for I in E.findall(W+'comment'):
			if I.get(W+'author')in INTERNAL_AUTHORS:G.add(I.get(W+'id'));E.remove(I)
		A[COMMENTS_PART]=etree.tostring(E,xml_declaration=True,encoding='UTF-8',standalone=True)
	for V in('commentRangeStart','commentRangeEnd'):
		for J in list(C.iter(W+V)):
			if J.get(W+'id')in G:J.getparent().remove(J)
	for L in list(C.iter(W+'commentReference')):
		if L.get(W+'id')in G:
			M=L.getparent();D=M.getparent();D.remove(M)
			if local(D.tag)in('ins','del')and len(D)==0:D.getparent().remove(D)
	K=etree.fromstring(A['word/_rels/document.xml.rels'])
	for N in list(K):
		F=N.get('Id','')
		if F.startswith(INTERNAL_REL_PREFIX):
			O=F[len(INTERNAL_REL_PREFIX)+1:]if F.startswith(INTERNAL_REL_PREFIX+'_')else None
			for B in list(C.iter(W+'headerReference')):
				if B.get('{%s}id'%R_NS)==F:
					if O:B.set('{%s}id'%R_NS,O)
					else:B.getparent().remove(B)
			K.remove(N)
	A['word/_rels/document.xml.rels']=etree.tostring(K,xml_declaration=True,encoding='UTF-8',standalone=True);A.pop(INTERNAL_HEADER_PART,None);A['[Content_Types].xml']=re.sub(b'<Override PartName="/word/headerInternal\\.xml"[^>]*/>',b'',A['[Content_Types].xml']);A['word/document.xml']=etree.tostring(C,xml_declaration=True,encoding='UTF-8',standalone=True);P=write_package(A,Q)
	if dst:
		with open(dst,'wb')as X:X.write(P)
	return P
DECISION_OPS='replace','replace_span','insert_paragraph','delete_paragraph','comment_only','accept'
ACCEPT_CODES='A1','A2','A3'
DECISIONS_SCHEMA={'$schema':'https://json-schema.org/draft/2020-12/schema','title':'decisions_round_<n>.json','type':'object','required':['transaction_id','round','received_sha256','decisions'],'properties':{'transaction_id':{'type':'string'},'lang':{'enum':['he','en'],'description':'שפת הנייר המחייב (4.9, שינוי 86). בלי השדה: לפי רוב האותיות'},'round':{'type':'integer','minimum':1},'received_sha256':{'type':'string'},'decisions':{'type':'array','items':{'type':'object','required':['id','op','decision_code'],'properties':{'id':{'type':'string'},'op':{'enum':list(DECISION_OPS)},'para':{'type':'integer','description':'אינדקס הפסקה בטיוטה שהתקבלה'},'new_text':{'type':'string','description':'replace: נוסח יעד מלא לפסקה'},'old':{'type':'string','description':'replace_span: הטווח, פעם אחת בדיוק בפסקה'},'new':{'type':'string'},'after_para':{'type':'integer','description':'insert_paragraph: פסקת העוגן'},'text':{'type':'string'},'number':{'type':'string','description':'מספר מוקלד בנייר עם מספור מוקלד (60א, 77)'},'external_comment':{'type':'string'},'internal_comment':{'type':'string'},'conforming':{'type':'boolean','description':'שינוי טכני או עקבי. גם הוא מקבל בועה חיצונית קצרה (4.9, שינוי 84)'},'conforms_to':{'type':'string','description':'עם conforming: ההכרעה (או הסעיף הפתוח) שהתיקון העקבי נובע ממנה. אינו פתיחה מחדש של סעיף מוסכם (S1d-R2)'},'their_rejected':{'type':'array','description':'סבב המשך: הרכיבים שהצד השני דחה במפורש, כל אחד מחרוזת או {component, terms, red_line}. מדרגת ביניים מוותרת על מה שאינו בקו האדום (S1d-R2)'},'carried_from':{'type':'object','description':'הכרעה מהסבב הקודם שהועברה לפסקה שלא השתנתה (round_tools.py carry): {round, id, para, op}'},'structural':{'type':'boolean','description':'כותרת פרק או מבנה. אינו נספר בבקשות (4.9, שינוי 89), ומקבל בועה קצרה'},'decision_code':{'enum':['A1','A2','A3','R1','R2','R3','N1']},'their_changes':{'enum':['reject','accept','keep'],'description':'פסקה עם שינויים פתוחים של הצד שכנגד: לדחות אותם ולסמן את שלנו מול הנוסח שלפניהם, לקבל אותם ולסמן מעליהם, או להשאיר אותם פתוחים (בועה בלבד). בלי השדה: קבלה ב-A1 עד A3, keep ב-comment_only, ודחייה בשאר. ב-reject, old ו-new_text נכתבים מול הנוסח שלפני השינויים שלהם'},'rule_ids':{'type':'array','items':{'type':'string'}},'cluster_id':{'type':'string','description':'כלל 8: כל השינויים של אותו כלל באותו סעיף הם אשכול אחד, עם בועה אחת שמעוגנת על כל הקטע. רק הכרעה אחת באשכול נושאת external_comment'},'regime':{'enum':['mutuality','cost','period','definition','cap_or_exception','law_or_forum','none'],'description':'כלל 2: ההכרעה משנה משטר, ולכן כל סעיף שתלוי בה מוכרע באותו סבב. none: נגיעה שאינה משנה משמעות (כתיב, כינוי, מספר הליך)'},'dependents':{'type':'array','items':{'type':'object'},'description':'כלל 2: {para, decision} (מזהה ההכרעה שמטפלת בו) או {para, keep: true, reason} לכל סעיף תלוי'},'fact_source':{'enum':['profile','user_answer','agreement'],'description':'כלל 6: המקור לעובדה על אחד הצדדים שהבועה נשענת עליה'},'their_track':{'enum':['green','yellow','red'],'description':'כלל 10: המסלול של הנוסח המקורי שלהם, לפני הסימון'},'fallback':{'enum':['their_wording','playbook'],'description':'כלל 10: עמדת הנסיגה. בנוסח שלהם שבצהוב: their_wording'},'policy_gate':{'type':'object'},'safe_wording':{'type':'object'},'mandatory':{'type':'boolean'},'kind':{'enum':['hidden_text_removal'],'description':'מחיקה של טקסט מוסתר (vanish) בטיוטה שלהם, עם הבועה הניטרלית (external_comments_guide.md, "טקסט מוסתר שהוסר"). השער בודק ש-old מוסתר בטיוטה שהתקבלה, ואינו דורש שהבועה תקרא בשמם מושגים שבטקסט המוסתר'},'silent_change':{'type':'string','description':'מזהה שינוי שקט מ-silent_changes בקובץ המצב, שההכרעה הזו מסמנת (החזרה, או קבלה עם בועה)'}}}}}}
def validate_decisions(dec):
	F=dec;B=[]
	for H in DECISIONS_SCHEMA['required']:
		if H not in F:B.append('חסר %s'%H)
	I=set();G={}
	for A in F.get('decisions',[]):
		if A.get('cluster_id')and A.get('external_comment'):G.setdefault(A['cluster_id'],[]).append(A.get('id','?'))
	for(E,J)in sorted(G.items()):
		if len(J)>1:B.append('אשכול %s: יותר מבועה חיצונית אחת (%s). לאשכול בועה אחת על כל הקטע'%(E,', '.join(J)))
	L={A.get('para')for A in F.get('decisions',[])if A.get('external_comment')and isinstance(A.get('para'),int)}
	for A in F.get('decisions',[]):
		C=A.get('id','?')
		if C in I:B.append('%s: מזהה כפול'%C)
		I.add(C);D=A.get('op')
		if D not in DECISION_OPS:B.append('%s: op לא מוכר: %s'%(C,D));continue
		M={'replace':('para','new_text'),'replace_span':('para','old','new'),'insert_paragraph':('after_para','text'),'delete_paragraph':('para',),'comment_only':('para',),'accept':('para',)}[D]
		for K in M:
			if K not in A:B.append('%s: חסר %s'%(C,K))
		if A.get('decision_code')not in DECISIONS_SCHEMA['properties']['decisions']['items']['properties']['decision_code']['enum']:B.append('%s: decision_code לא מוכר'%C)
		if D=='insert_paragraph'and A.get('decision_code')in('R1','R2','R3'):B.append('%s: נושא חסר שנוסף נרשם N1, ולא R1 עד R3'%C)
		if D!='insert_paragraph'and A.get('decision_code')=='N1':B.append('%s: N1 רק לנושא חסר שנוסף'%C)
		E=A.get('cluster_id')
		if D in('replace','replace_span','insert_paragraph','delete_paragraph')and not A.get('external_comment')and E and E in G:0
		elif D in('replace','replace_span')and not A.get('external_comment')and A.get('conforming')and A.get('para')in L:0
		elif D in('replace','replace_span','insert_paragraph','delete_paragraph')and not A.get('external_comment'):
			if E:B.append('%s: לאשכול %s אין בועה חיצונית באף הכרעה'%(C,E))
			elif A.get('conforming')or A.get('structural'):B.append('%s: שינוי טכני בלי בועה חיצונית קצרה (כל שינוי שהצד שכנגד רואה מקבל בועה)'%C)
			else:B.append('%s: שינוי מהותי בלי בועה חיצונית'%C)
		if D=='accept'and A.get('decision_code')not in ACCEPT_CODES:B.append('%s: accept רק עם decision_code A1, A2 או A3'%C)
		if D=='accept'and(A.get('external_comment')or A.get('internal_comment')):B.append('%s: accept הוא בלי סימון ובלי בועה; לבועה בלבד: comment_only'%C)
		if D=='insert_paragraph'and A.get('structural')and A.get('mandatory'):B.append('%s: כותרת מבנית אינה נושא חובה'%C)
	return B
def their_changes_mode(d):
	if d.get('their_changes'):return d['their_changes']
	if d.get('op')=='comment_only':return'keep'
	if d.get('op')=='accept'or d.get('decision_code')in ACCEPT_CODES:return'accept'
	return'reject'
def mark_decisions(doc,dec):
	H=dec;B=doc;G=[];I={};J={}
	for A in H['decisions']:
		if A['op']=='replace_span':J.setdefault(A['para'],[]).append(A)
	for A in H['decisions']:
		E=None;F=None
		try:
			D=A['op'];C=A.get('para')
			if D=='replace_span':
				F=J.pop(C,None)
				if F is None:continue
			K=None
			if D!='insert_paragraph'and isinstance(C,int)and 0<=C<len(B.paras)and B.has_their_revisions(C):
				L=their_changes_mode(A)
				if L!='keep':K=B.orig_texts[C];E=C,B.snapshot_para(C);B.resolve_theirs(C,L)
			if D=='replace':B.set_text(A['para'],A['new_text'],A.get('external_comment'),A.get('internal_comment'))
			elif D=='replace_span':
				M=_mark_span_group(B,C,F,K);G.extend(M)
				if E is not None and len(M)==len(F):B.restore_para(*E)
			elif D=='insert_paragraph':I[A['id']]=B.insert_paragraph(A['after_para'],A['text'],A.get('number'),A.get('template_para'),A.get('external_comment'),A.get('internal_comment'))
			elif D=='delete_paragraph':B.delete_paragraph(A['para'],A.get('external_comment'),A.get('internal_comment'))
			elif D=='accept':continue
			else:B.comment_only(A['para'],A.get('external_comment'),A.get('internal_comment'))
		except UnsupportedEdit as N:
			if E is not None:B.restore_para(*E)
			for O in F or[A]:G.append({'id':O['id'],'reason':str(N)})
	span_clusters(B,H,I,{A['id']for A in G});return G
def _mark_span_group(doc,idx,group,received=None):
	I=received;C=idx;B=doc;D=B.orig_texts[C]if isinstance(C,int)and 0<=C<len(B.orig_texts)else None;E,F,J=[],[],[]
	for A in group:
		K=A['old'],A['new'],A.get('external_comment'),A.get('internal_comment')
		try:
			if A.get('old')and D is not None and A['old']not in D:
				L=prior_edit_exists(B.paras[C],A['old'],match_quotes(A.get('new')or'',B.quotes),B.prior)
				if L:J.append((A,L));continue
			if I is not None and A.get('old')and D is not None and A['old']not in D and A['old']in I:raise UnsupportedEdit('"%s" הוא מהנוסח של הצד שכנגד, והשינויים שלהם בפסקה נדחו (their_changes: reject). כתבו את old מול הנוסח שלפני השינויים שלהם, או קבעו their_changes: accept'%A['old'][:40])
			B.edit_spans(C,[K],dry_run=True);E.append((A,K))
		except UnsupportedEdit as G:F.append({'id':A['id'],'reason':str(G)})
	if E:
		try:B.edit_spans(C,[A for(B,A)in E])
		except UnsupportedEdit as G:F+=[{'id':A['id'],'reason':str(G)}for(A,B)in E]
	for(A,(H,M))in J:B._anchor(H,M,A.get('external_comment'),A.get('internal_comment'),ref_wrap=None);B.clock.tick();B.existing.append({'id':A['id'],'para':C,'note':'קיימת מסבב קודם: "%s" כבר נמחק בסימון פתוח שלנו (%s, %s), שהצד שכנגד לא קיבל ולא דחה. לא סומנה כפילות'%(A['old'][:40],H.get(W+'author'),H.get(W+'date'))})
	return F
def span_clusters(doc,dec,inserted,skipped=()):
	O=inserted;D=doc;K={}
	for A in dec['decisions']:
		if A.get('cluster_id')and A['id']not in skipped and A['op']!='accept':K.setdefault(A['cluster_id'],[]).append(A)
	if not any(len(A)>1 for A in K.values()):return
	P=set()
	for L in K.values():
		Q=next((A for A in L if A.get('external_comment')),None)
		if Q is None or len(L)<2:continue
		H=next((A[0]for A in D.comments if A[1]==D.author and A[3]==Q['external_comment']and A[0]not in P),None)
		if H is None:continue
		P.add(H);E=[]
		for A in L:
			M=F=None
			if A['op']=='insert_paragraph'and O.get(A['id'])is not None:F=O[A['id']];V=[A for(A,B)in D.inserted.get(A['after_para'],[])];M=A['after_para'],1+next((A for(A,B)in enumerate(V)if B is F),0)
			elif isinstance(A.get('para'),int)and 0<=A['para']<len(D.paras):F,M=D.paras[A['para']],(A['para'],0)
			if F is not None and all(F is not A for(B,A)in E):E.append((M,F))
		E=[A for(B,A)in sorted(E,key=lambda kp:kp[0])]
		if len(E)<2:continue
		N=E[0];I=next((A for A in reversed(E)if _mark(A)!='del'),E[-1]);R=[D.root]+[B for A in D.inserted.values()for(B,C)in A];J=next((A for B in R for A in B.iter(W+'commentRangeStart')if A.get(W+'id')==H),None);G=next((A for B in R for A in B.iter(W+'commentRangeEnd')if A.get(W+'id')==H),None)
		if J is None or G is None:continue
		B=G.getnext();C=B
		if B is not None and local(B.tag)in('ins','del'):C=next((A for A in B if A.find(W+'commentReference')is not None),None)
		if C is None or C.find(W+'commentReference')is None:continue
		J.getparent().remove(J);S=N.find(W+'pPr');N.insert(list(N).index(S)+1 if S is not None else 0,J);G.getparent().remove(G)
		if B is not C:
			B.remove(C)
			if not len(B)and B.getparent()is not None:B.getparent().remove(B)
		elif C.getparent()is not None:C.getparent().remove(C)
		I.append(G);T=_mark(I)
		if T in('ins','del'):U=D._rev(T);U.append(C);I.append(U)
		else:I.append(C)
def apply_decisions(received,dec,out_path=None,author=None,initials=None,now=None,internal_header=True,prior_authors=(),prior_keys=(),lang=None):
	D=out_path;C=author;B=dec;E=validate_decisions(B)
	if E:return{'ok':False,'errors':E}
	C=C or B.get('author');I=RevisionClock(now=now,steps=len(B['decisions']));A=TrackedDocx(received,author=C,initials=initials or B.get('initials'),clock=I,prior_authors=prior_authors,prior_keys=prior_keys,lang=lang or B.get('lang')or'he');F=mark_decisions(A,B);G=A.verify_roundtrip();H=A.to_bytes(internal_header=internal_header)
	if D:
		with open(D,'wb')as J:J.write(H)
	return{'ok':not G and not F,'errors':[],'not_marked':F,'existing':A.existing,'verify':G,'expected_accept':A.expected_accept(),'original':A.orig_texts,'data':H,'doc':A}
def sent_revision_keys(sent_paths,received_paths=()):
	def B(path):
		try:A=document_root(path)
		except Exception:return set()
		return{revision_key(A)for A in A.iter(W+'ins',W+'del')}
	C=set()
	for A in received_paths or():C|=B(A)
	D=set()
	for A in sent_paths or():D|=B(A)-C
	return D
