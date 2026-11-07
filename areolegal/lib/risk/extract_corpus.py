# -*- coding: utf-8 -*-
# Copyright (c) Areo. All rights reserved. Licensed under the terms at https://areo.co.il/legal/terms
import hashlib,io,json,os,re,sys,zipfile
if __name__=='__main__':
	sys.dont_write_bytecode=True
	for _s in(sys.stdout,sys.stderr):
		try:_s.reconfigure(encoding='utf-8',errors='replace')
		except(AttributeError,ValueError):pass
from lxml import etree
try:from.page_text import PdfTextUnavailable,is_pdf,pdf_text
except ImportError:sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)));from page_text import PdfTextUnavailable,is_pdf,pdf_text
try:from common.cli import DOCX_BAD_EXIT,OutputRefused,docx_problem,guard_out,parser,run,utf8_stdio;from common.paths import long_path
except ImportError:sys.path.insert(0,os.path.dirname(os.path.dirname(os.path.abspath(__file__))));from common.cli import DOCX_BAD_EXIT,OutputRefused,docx_problem,guard_out,parser,run,utf8_stdio;from common.paths import long_path
W='http://schemas.openxmlformats.org/wordprocessingml/2006/main'
NS={'w':W}
def q(tag):return'{%s}%s'%(W,tag)
STRICT_NS=(b'http://purl.oclc.org/ooxml/wordprocessingml/main',W.encode()),(b'http://purl.oclc.org/ooxml/officeDocument/relationships',b'http://schemas.openxmlformats.org/officeDocument/2006/relationships'),(b'http://purl.oclc.org/ooxml/officeDocument/math',b'http://schemas.openxmlformats.org/officeDocument/2006/math'),(b'http://purl.oclc.org/ooxml/drawingml/wordprocessingDrawing',b'http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing'),(b'http://purl.oclc.org/ooxml/drawingml/main',b'http://schemas.openxmlformats.org/drawingml/2006/main')
def is_strict(data):return STRICT_NS[0][0]in data
def normalize_strict(data):
	A=data
	if not is_strict(A):return A
	for(B,C)in STRICT_NS:A=A.replace(B,C)
	return A
class OoxmlZip:
	def __init__(A,z):
		A.z,A.strict=z,False;global _NUMBERING
		try:_NUMBERING=Numbering(A)
		except Exception:_NUMBERING=None
	def namelist(A):return A.z.namelist()
	def read(B,name):
		A=B.z.read(name)
		if name.endswith('.xml')and is_strict(A):B.strict=True;return normalize_strict(A)
		return A
_NUMBERING=None
HEB_UNITS='אבגדהוזחט'
HEB_TENS='יכלמנסעפצ'
HEB_HUNDREDS='ק','ר','ש','ת','תק','תר','תש','תת','תתק'
HEB_ALPHABET='אבגדהוזחטיכלמנסעפצקרשת'
def _hebrew1(n):
	if n<=0:return str(n)
	A=''
	if n>=100:A+=HEB_HUNDREDS[min(n//100,9)-1];n%=100
	if n in(15,16):return A+('טו'if n==15 else'טז')
	if n>=10:A+=HEB_TENS[n//10-1];n%=10
	if n:A+=HEB_UNITS[n-1]
	return A
def _hebrew2(n):
	if n<=0:return str(n)
	A,B=divmod(n-1,22);return HEB_ALPHABET[B]*(A+1)
def _roman(n):
	C=(1000,'M'),(900,'CM'),(500,'D'),(400,'CD'),(100,'C'),(90,'XC'),(50,'L'),(40,'XL'),(10,'X'),(9,'IX'),(5,'V'),(4,'IV'),(1,'I');A=''
	for(B,D)in C:
		while n>=B:A,n=A+D,n-B
	return A or str(n)
def _letters(n):
	A=''
	while n>0:n,B=divmod(n-1,26);A=chr(65+B)+A
	return A
def fmt_number(n,fmt):
	A=fmt or'decimal'
	if A in('decimal','decimalEnclosedParen','decimalEnclosedFullstop','decimalHalfWidth','decimalFullWidth'):return str(n)
	if A=='decimalZero':return'%02d'%n
	if A=='lowerLetter':return _letters(n).lower()
	if A=='upperLetter':return _letters(n)
	if A=='lowerRoman':return _roman(n).lower()
	if A=='upperRoman':return _roman(n)
	if A=='hebrew1':return _hebrew1(n)
	if A=='hebrew2':return _hebrew2(n)
	if A in('none','bullet'):return''
	return str(n)
class Numbering:
	def __init__(A,z):
		A.abstract,A.nums,A.styles={},{},{};A.counters,A.done={},{};E=z.namelist()
		if'word/numbering.xml'in E:
			F=etree.fromstring(z.read('word/numbering.xml'))
			for G in F.findall('w:abstractNum',NS):A.abstract[G.get(q('abstractNumId'))]=A._levels(G)
			for B in F.findall('w:num',NS):
				H=B.find('w:abstractNumId',NS);I={}
				for C in B.findall('w:lvlOverride',NS):N=int(C.get(q('ilvl'))or 0);J=C.find('w:startOverride',NS);K=C.find('w:lvl',NS);I[N]={'start':int(J.get(q('val')))if J is not None else None,'lvl':A._level(K)if K is not None else None}
				A.nums[B.get(q('numId'))]=H.get(q('val'))if H is not None else None,I
		if'word/styles.xml'in E:
			O=etree.fromstring(z.read('word/styles.xml'))
			for D in O.findall('w:style',NS):P=D.get(q('styleId'));L=D.find('w:basedOn',NS);M=D.find('w:pPr/w:numPr',NS);A.styles[P]=L.get(q('val'))if L is not None else None,A._numpr(M)if M is not None else None
	@staticmethod
	def _level(lv):
		def A(tag,default=None):A=lv.find('w:'+tag,NS);return A.get(q('val'))if A is not None and A.get(q('val'))is not None else default
		C=A('start','1');B=A('lvlRestart');return{'start':int(C)if str(C).lstrip('-').isdigit()else 1,'fmt':A('numFmt','decimal'),'text':A('lvlText',''),'lgl':lv.find('w:isLgl',NS)is not None,'restart':int(B)if B is not None and str(B).isdigit()else None}
	def _levels(B,an):return{int(A.get(q('ilvl'))or 0):B._level(A)for A in an.findall('w:lvl',NS)}
	@staticmethod
	def _numpr(np_):A,B=np_.find('w:ilvl',NS),np_.find('w:numId',NS);return B.get(q('val'))if B is not None else None,int(A.get(q('val')))if A is not None else None
	def _style_numpr(D,sid,seen=None):
		B=seen;A=sid;B=B or set()
		while A and A not in B:
			B.add(A);E,C=D.styles.get(A,(None,None))
			if C and C[0]:return C
			A=E
	def _resolve(C,p):
		D=p.find('w:pPr',NS);A,B=None,None
		if D is not None:
			F=D.find('w:numPr',NS)
			if F is not None:A,B=C._numpr(F)
			G=D.find('w:pStyle',NS)
			if G is not None and(A is None or B is None):
				E=C._style_numpr(G.get(q('val')))
				if E:A=A if A is not None else E[0];B=B if B is not None else E[1]
		if not A or A=='0'or A not in C.nums:return
		return A,B or 0
	def _lvl(B,num_id,il):
		D,E=B.nums[num_id];A=E.get(il)or{};C=dict(A.get('lvl')or(B.abstract.get(D)or{}).get(il)or{'start':1,'fmt':'decimal','text':'%%%d.'%(il+1),'lgl':False,'restart':None})
		if A.get('start')is not None:C['start']=A['start']
		return C
	def label(A,p):
		D=id(p)
		if D in A.done:return A.done[D][1]
		H=A._resolve(p)
		if H is None:A.done[D]=p,'';return''
		E,B=H;C=A.counters.setdefault(E,{});F=A._lvl(E,B);C[B]=C[B]+1 if B in C else F['start']
		for I in[A for A in C if A>B]:
			G=A._lvl(E,I).get('restart')
			if G is None or G!=0 and B+1<=G:del C[I]
		if F['fmt']in('bullet','none'):A.done[D]=p,'';return''
		def K(m):
			D=int(m.group(1))-1
			if D>B:return''
			G=C.get(D,A._lvl(E,D)['start']);return fmt_number(G,'decimal'if F['lgl']else A._lvl(E,D)['fmt'])
		J=re.sub('%([1-9])',K,F['text']or'').strip();A.done[D]=p,J;return J
PARTS_RE=re.compile('^word/(document|header\\d*|footer\\d*|footnotes|endnotes)\\.xml$')
INS_TAGS=q('ins'),q('moveTo')
DEL_TAGS=q('del'),q('moveFrom')
TEXT_TAGS=q('t'),q('delText'),q('instrText')
def _is_near_white(val):
	A=val;A=(A or'').strip().upper()
	if A in('','AUTO'):return False
	if not re.match('^[0-9A-F]{6}$',A):return False
	B,C,D=int(A[0:2],16),int(A[2:4],16),int(A[4:6],16);return min(B,C,D)>=240
def run_hidden(run):
	A=run.find('w:rPr',NS)
	if A is None:return
	for B in('vanish','specVanish','webHidden'):
		C=A.find('w:'+B,NS)
		if C is not None and C.get(q('val'),'true')not in('0','false','off'):return B
	D=A.find('w:color',NS)
	if D is not None and _is_near_white(D.get(q('val'))):return'color'
	for B in('sz','szCs'):
		E=A.find('w:'+B,NS)
		if E is not None:
			try:
				if int(E.get(q('val')))<8:return'font_size'
			except(TypeError,ValueError):pass
def _own_paragraph(el,p):
	A=el.getparent()
	while A is not None and A is not p:
		if A.tag==q('p'):return False
		A=A.getparent()
	return True
def _flags(el,p):
	B=C=False;A=el.getparent()
	while A is not None and A is not p:
		if A.tag in INS_TAGS:B=True
		elif A.tag in DEL_TAGS:C=True
		A=A.getparent()
	return B,C
def para_texts(p):
	D,E,J=[],[],[]
	for F in p.iter():
		A=F.tag
		if A not in TEXT_TAGS and A not in(q('tab'),q('br'),q('cr'),q('noBreakHyphen')):continue
		if not _own_paragraph(F,p):continue
		if A==q('instrText'):continue
		if A in TEXT_TAGS:B=F.text or''
		elif A==q('tab'):B=' '
		elif A==q('noBreakHyphen'):B='-'
		else:B='\n'
		N,K=_flags(F,p)
		if A==q('delText'):K=True
		if not K:D.append(B)
		if not N:E.append(B)
		C=F.getparent()
		while C is not None and C.tag!=q('r'):C=C.getparent()
		if C is not None and B.strip():
			L=run_hidden(C)
			if L:J.append({'how':L,'text':B})
	M=lambda parts:re.sub('[ \\t\xa0]+',' ',''.join(parts)).strip();H=_NUMBERING.label(p)if _NUMBERING is not None and p.tag==q('p')else''
	if H:
		if''.join(D).strip():D=[H+' ']+D
		if''.join(E).strip():E=[H+' ']+E
	G=[]
	for I in J:
		if G and G[-1]['how']==I['how']:G[-1]['text']+=I['text']
		else:G.append(dict(I))
	return M(D),M(E),G
def para_changes(p):
	C=[]
	for D in p.iter():
		A=D.tag
		if A not in TEXT_TAGS and A not in(q('tab'),q('br'),q('cr'),q('noBreakHyphen')):continue
		if not _own_paragraph(D,p)or A==q('instrText'):continue
		J,F=_flags(D,p)
		if A==q('delText'):F=True
		if not(J or F):continue
		G=D.text or''if A in TEXT_TAGS else' 'if A==q('tab')else'-'if A==q('noBreakHyphen')else'\n';H='del'if F else'ins';E='';B=D.getparent()
		while B is not None and B is not p:
			if B.tag in INS_TAGS or B.tag in DEL_TAGS:E=B.get(q('author'))or'';break
			B=B.getparent()
		if C and C[-1]['kind']==H and C[-1].get('author','')==E:C[-1]['text']+=G
		else:
			I={'kind':H,'text':G}
			if E:I['author']=E
			C.append(I)
	return[A for A in C if A['text'].strip()]
def comments_of(z):
	B={}
	if'word/comments.xml'not in z.namelist():return B
	D=etree.fromstring(z.read('word/comments.xml'))
	for A in D.findall('w:comment',NS):C=A.get(q('id'));E=' '.join(''.join(A.text or''for A in A.iter(q('t')))for A in A.findall('.//w:p',NS)).strip();B[C]={'id':C,'author':A.get(q('author')),'date':A.get(q('date')),'text':E,'anchored_text':'','part':None}
	return B
def anchored_ranges(x):
	D,B={},{}
	for A in x.iter():
		if A.tag==q('commentRangeStart'):B[A.get(q('id'))]=[]
		elif A.tag==q('commentRangeEnd'):
			C=A.get(q('id'))
			if C in B:D[C]=re.sub('\\s+',' ',''.join(B.pop(C))).strip()
		elif A.tag==q('t'):
			for E in B.values():E.append(A.text or'')
	return D
PDF_CLAUSE_START=re.compile('^\\s*(?:\\(?\\d{1,3}(?:\\.\\d{1,3})*\\)?[.)]?(?=\\s|$)|\\(?\\d{1,3}(?:\\.\\d{1,3})+\\)?|\\([א-תa-zA-Z]{1,4}\\)|[א-ת][.)](?=\\s)|(?i:section|clause|article)\\s+\\d|[•●▪◦\\-]\\s)')
PDF_CLAUSE_ONLY=re.compile('^\\s*\\(?(?:\\d+(?:\\.\\d+)*|[א-ת]|[a-zA-Z]|[ivxIVX]{1,6})\\)?[.)]?\\s*$')
PDF_SENTENCE_END=re.compile('[.:;!?״"”)]\\s*$')
def _pdf_rows(page):
	D=[]
	for H in page.get_text('dict').get('blocks',[]):
		if H.get('type')!=0:continue
		A=None
		for I in H.get('lines',[]):
			E=''.join(A.get('text','')for A in I.get('spans',[]));F,B,G,C=I['bbox']
			if A and min(C,A[4])-max(B,A[2])>.5*min(C-B,A[4]-A[2]):J=max(F,A[1])-min(G,A[3]);K=max(1.,C-B);L=' 'if J>.25*K and E[:1].strip()and A[0][-1:].strip()else'';A=[A[0]+L+E,min(F,A[1]),min(B,A[2]),max(G,A[3]),max(C,A[4])]
			else:
				if A:D.append(A)
				A=[E,F,B,G,C]
		if A:D.append(A)
	return[(re.sub('[ \\t\xa0]+',' ',A[0]).strip(),)+tuple(A[1:])for A in D if A[0].strip()]
def _pdf_paragraphs(rows):
	D=rows
	if not D:return[]
	P,Q=min(A[1]for A in D),max(A[3]for A in D);R=max(1.,Q-P);E=sorted(A[2]-B[4]for(B,A)in zip(D,D[1:])if 0<=A[2]-B[4]<2*(A[4]-A[2]));S=E[len(E)//4]if E else .0;F,B,A=[],None,None
	for G in D:
		C,W,L,X,T=G
		if B is None:B,A=[C],G;continue
		H=max(1.,min(T-L,A[4]-A[2]));I=L-A[4];M=max(.5*H,S+.35*H);U=PDF_CLAUSE_ONLY.match(A[0])and len(B)==1 and I<=M
		if U:J=False
		elif I>M or I<-.5*H or PDF_CLAUSE_START.match(C):J=True
		else:V=A[3]-A[1]<.8*R;J=bool(V and PDF_SENTENCE_END.search(A[0]))
		if J:F.append(B);B=[C]
		else:B.append(C)
		A=G
	F.append(B);N=[]
	for O in F:
		K=O[0]
		for C in O[1:]:K+=C if re.search('[A-Za-z]-$',K)else' '+C
		N.append(re.sub('[ \\t\xa0]+',' ',K).strip())
	return N
def _pdf_pages(raw):
	try:
		try:import pymupdf as A
		except ImportError:import fitz as A
		B=A.open(stream=raw,filetype='pdf');C=[_pdf_paragraphs(_pdf_rows(A))for A in B];B.close()
		if any(C):return C
	except ImportError:pass
	return[[A for A in(re.sub('[ \\t\xa0]+',' ',A).strip()for A in pdf_text(raw).splitlines())if A]]
def extract_pdf(path,raw):
	A={'file':os.path.basename(path),'sha256':hashlib.sha256(raw).hexdigest(),'parts':{},'tracked':{'ins':0,'del':0,'moveFrom':0,'moveTo':0},'format':'pdf','track_revisions_on':False,'comments':[],'hidden_total':0}
	try:F=_pdf_pages(raw)
	except PdfTextUnavailable as D:
		if str(D).startswith('אין ספרייה'):A['unreadable_reason']=str(D)
		else:A['no_text_layer']=True
		return A
	B=0
	for(G,H)in enumerate(F,1):
		E=[]
		for C in H:
			if C:E.append({'i':B,'style':'','text_accept_all':C,'text_reject_all':C,'hidden':[]});B+=1
		A['parts']['pdf/page-%d'%G]=E
	if not B:A['no_text_layer']=True
	return A
def extract(path):
	F=path
	with open(long_path(F),'rb')as R:D=R.read()
	if is_pdf(D):return extract_pdf(F,D)
	C=OoxmlZip(zipfile.ZipFile(io.BytesIO(D)));N=C.namelist();S=sorted((A for A in N if PARTS_RE.match(A)),key=lambda n:(n!='word/document.xml',n));A={'file':os.path.basename(F),'sha256':hashlib.sha256(D).hexdigest(),'parts':{},'tracked':{'ins':0,'del':0,'moveFrom':0,'moveTo':0}};E=comments_of(C)
	for G in S:
		H=etree.fromstring(C.read(G))
		for B in A['tracked']:A['tracked'][B]+=len(H.findall('.//w:'+B,NS))
		O=[]
		for(T,I)in enumerate(H.iter(q('p'))):
			J,K,P=para_texts(I)
			if not J and not K and not P:continue
			L=I.find('w:pPr',NS);Q=''
			if L is not None and L.find('w:pStyle',NS)is not None:Q=L.find('w:pStyle',NS).get(q('val'))or''
			U=any(A.tag==q('txbxContent')for A in I.iterancestors());M={'i':T,'style':Q,'text_accept_all':J,'text_reject_all':K,'hidden':P}
			if U:M['in_textbox']=True
			if J!=K:M['changed']=True
			O.append(M)
		for(B,V)in anchored_ranges(H).items():
			if B in E:E[B]['anchored_text']=V;E[B]['part']=G
		A['parts'][G]=O
	W=C.read('word/settings.xml').decode('utf-8','replace')if'word/settings.xml'in N else'';A['track_revisions_on']='<w:trackRevisions'in W;A['comments']=list(E.values());A['hidden_total']=sum(len(B['hidden'])for A in A['parts'].values()for B in A)
	if C.strict:A['ooxml_strict']=True
	if not any(A['parts'].values()):A['no_text_layer']=True
	return A
def body_text(doc,view='accept'):A='text_accept_all'if view=='accept'else'text_reject_all';return' '.join(B[A]for C in doc['parts'].values()for B in C if B[A])
def reject_all_equals(doc_response,doc_received):
	A=[A['text_reject_all']for A in doc_response['parts'].get('word/document.xml',[])if A['text_reject_all']];B=[A['text_accept_all']for A in doc_received['parts'].get('word/document.xml',[])if A['text_accept_all']];D=lambda s:re.sub('\\s+',' ',s).strip();C=[A for(A,(B,C))in enumerate(zip(A,B))if D(B)!=D(C)]
	if len(A)!=len(B):C.append(min(len(A),len(B)))
	return not C,C
def main(argv=None):
	F=parser('חילוץ Word ו-PDF לקובץ ביניים (JSON)',out_required=True);F.add_argument('inputs',nargs='+',help='מסמכי Word או PDF לחילוץ (קריאה בלבד)');A=F.parse_args(argv)
	if not A.out.lower().endswith('.json'):raise OutputRefused('--out חייב להסתיים ב-.json: %s'%A.out)
	K=guard_out(A.out,A.inputs);G=[A for A in A.inputs if not os.path.isfile(long_path(A))]
	if G:
		sys.stdout.reconfigure(encoding='utf-8')
		for B in G:print('לא נמצא: %s (נתיב של %d תווים)'%(B,len(os.path.abspath(B))))
		return 1
	D=[]
	for B in A.inputs:
		with open(long_path(B),'rb')as E:L=is_pdf(E.read(1024))
		H=None if L else docx_problem(B,strict_ok=True)
		if H:D.append(H[1])
	if D:utf8_stdio();print('\n'.join(D));return DOCX_BAD_EXIT
	I=[extract(A)for A in A.inputs]
	with open(K,'w',encoding='utf-8')as E:json.dump(I,E,ensure_ascii=False,indent=1)
	sys.stdout.reconfigure(encoding='utf-8')
	for C in I:J=C['tracked'];print('%s ins=%d del=%d comments=%d hidden=%d parts=%d'%(C['file'],J['ins'],J['del'],len(C['comments']),C['hidden_total'],len(C['parts'])))
	return 0
if __name__=='__main__':sys.exit(run(main))
