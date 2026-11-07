# -*- coding: utf-8 -*-
# Copyright (c) Areo. All rights reserved. Licensed under the terms at https://areo.co.il/legal/terms
import email,email.policy,hashlib,os,re,shutil,subprocess,tempfile
EXTS='.docx','.pdf','.doc','.txt','.md','.eml'
def sha256_file(path):
	A=hashlib.sha256()
	with open(path,'rb')as B:
		for C in iter(lambda:B.read(65536),b''):A.update(C)
	return A.hexdigest()
def _norm(p):return p.replace('\\','/').lower()
def _prepare(excluded):
	C,D=[],[]
	for B in excluded or():
		if not B or not B.strip():continue
		if os.path.isabs(B):D.append(_norm(os.path.normcase(os.path.abspath(B))).rstrip('/'))
		else:
			A=_norm(B).strip()
			while A.startswith('./'):A=A[2:]
			A=A.strip('/')
			if A:C.append(A)
	return C,D
def _under(path,prefix):A=prefix;return path==A or path.startswith(A+'/')
def _is_excluded(full,rel,key,rules):
	A,B=rules;C,D=_norm(rel),_norm(key)
	if any(_under(C,A)or _under(D,A)for A in A):return True
	E=_norm(os.path.normcase(os.path.abspath(full)));return any(_under(E,A)for A in B)
SYSTEM_FILES={'desktop.ini','thumbs.db','.ds_store'}
DATA_DIRS={'areo-נתונים'}
PAGE_TEXT_MIN=30
OCR_MAX_PAGES=60
def _safe_name(name):A=name;A=re.sub('[\\\\/:*?"<>|\\x00-\\x1f]+','_',A or'').strip(' .');return A or'attachment'
def _pymupdf():
	try:import pymupdf as A;return A
	except ImportError:
		try:import fitz;return fitz
		except ImportError:return
def pdf_signals(path):
	A=B=None;C=_pymupdf()
	try:
		if C is not None:
			with C.open(path)as D:A=len(D);B=sum(len(A.get_text().strip())for A in D)
			E='pymupdf'
		else:from pypdf import PdfReader as G;F=G(path);A=len(F.pages);B=sum(len((A.extract_text()or'').strip())for A in F.pages);E='pypdf'
	except ImportError:return{'readable':None,'method':None}
	except Exception:return{'readable':False,'method':None}
	return{'readable':True,'pages':A,'text_chars':B,'method':E,'scanned':bool(A)and B<PAGE_TEXT_MIN*A}
def dependencies():
	try:import pypdf;A=True
	except ImportError:A=False
	return{'pymupdf':_pymupdf()is not None,'pypdf':A,'tesseract':bool(tesseract())}
def tesseract():
	A=shutil.which('tesseract')
	if not A and os.name=='nt':
		for C in(os.environ.get('ProgramFiles','C:\\Program Files'),os.environ.get('ProgramFiles(x86)','')):
			B=os.path.join(C,'Tesseract-OCR','tesseract.exe')if C else''
			if B and os.path.exists(B):A=B;break
	return A
def _ocr_langs(exe):
	try:A=subprocess.run([exe,'--list-langs'],capture_output=True,text=True,timeout=30).stdout
	except(OSError,subprocess.SubprocessError):return'eng'
	B={A.strip()for A in A.splitlines()};return'+'.join(A for A in('heb','eng')if A in B)or'eng'
def ocr_pdf(path,out_txt):
	C=out_txt;A,D=tesseract(),_pymupdf()
	if not A or D is None:return'unavailable'
	H,E=_ocr_langs(A),[]
	try:
		with tempfile.TemporaryDirectory()as I,D.open(path)as J:
			for(B,K)in enumerate(J):
				if B>=OCR_MAX_PAGES:break
				F=os.path.join(I,'p%d.png'%B);K.get_pixmap(dpi=300).save(F);L=subprocess.run([A,F,'stdout','-l',H],capture_output=True,timeout=180);E.append('--- page %d ---\n%s'%(B+1,L.stdout.decode('utf-8','replace').strip()))
	except(OSError,subprocess.SubprocessError,RuntimeError,ValueError):return'failed'
	G='\n\n'.join(E)
	if not re.sub('--- page \\d+ ---','',G).strip():return'failed'
	os.makedirs(os.path.dirname(C),exist_ok=True)
	with open(C,'w',encoding='utf-8')as M:M.write(G)
	return'done'
COPY_NAME=re.compile('(\\bcopy\\b|עותק|העתק|\\(\\d+\\)(?=\\.[^.]+$))',re.I)
def _copy_last(name):return bool(COPY_NAME.search(name)),name
AREO_SIDECARS='.report.json',
def _areo_sidecar(dirpath,name):
	B=name.lower()
	for A in AREO_SIDECARS:
		if B.endswith(A):C=name[:-len(A)];return any(os.path.isfile(os.path.join(dirpath,C+A))for A in('.docx','.doc','.pdf'))
	return False
def _status(key,sha,previous,seen):
	A=previous
	if sha in seen:return'duplicate'
	if key not in A:return'new'
	return'changed'if A[key]!=sha else'same'
def _eml_parts(raw):
	D=email.message_from_bytes(raw,policy=email.policy.default);E=D.get_body(preferencelist=('plain','html'));B=''
	if E is not None:
		try:B=E.get_content()
		except(LookupError,ValueError):B=''
		if E.get_content_type()=='text/html':B=re.sub('<[^>]+>',' ',B)
	I='\n'.join('%s: %s'%(A,D.get(A,''))for A in('From','To','Date','Subject'));G=[]
	for C in D.iter_attachments():
		F=C.get_filename()
		if C.get_content_type()=='message/rfc822':A=C.get_payload();A=A[0]if isinstance(A,list)and A else A;H=A.as_bytes()if hasattr(A,'as_bytes')else bytes(C.get_payload(decode=True)or b'');F=F or((A.get('Subject')if hasattr(A,'get')else None)or'message')+'.eml'
		else:H=C.get_payload(decode=True)or b''
		G.append((_safe_name(F or'attachment'),H))
	return I+'\n\n'+(B or'').strip(),G
def _add_eml(entry,raw,work_dir,previous,seen,out,depth=0):
	N=depth;M=previous;J=out;G=seen;F=work_dir;C=entry
	try:R,S=_eml_parts(raw)
	except Exception:C['reason']='eml_unreadable';return
	D=os.path.join(F,'attachments',C['sha256'][:16])if F else None
	if D:
		os.makedirs(D,exist_ok=True)
		with open(os.path.join(D,'_message.txt'),'w',encoding='utf-8')as K:K.write(R)
		C['text_path']=os.path.join(D,'_message.txt')
	C['attachments']=[];O=set()
	for(P,L)in S:
		T,U=os.path.splitext(P);B,Q=P,1
		while B.lower()in O:Q+=1;B='%s (%d)%s'%(T,Q,U)
		O.add(B.lower());H=C['path']+'/'+B;I=hashlib.sha256(L).hexdigest();E=os.path.join(D,B)if D else None
		if E:
			with open(E,'wb')as K:K.write(L)
		A={'path':H,'abs':E,'sha256':I,'container':C['path'],'duplicate_of':None};C['attachments'].append(H)
		if not B.lower().endswith(EXTS):A.update(status='unsupported',reason='file_type');J.append(A);continue
		A['status']=_status(H,I,M,G);A['duplicate_of']=G.get(I)if A['status']=='duplicate'else None;G.setdefault(I,H);J.append(A)
		if B.lower().endswith('.eml')and N<2 and A['status']!='duplicate':_add_eml(A,L,F,M,G,J,N+1)
		elif B.lower().endswith('.pdf')and E:_add_pdf(A,E,F)
def _add_pdf(entry,full,work_dir):
	C=work_dir;A=entry;D=pdf_signals(full)
	if D.get('readable')is None:A['pdf_check']='unavailable';return
	if not D.get('scanned'):return
	A['scanned']=True
	if not C or not A.get('sha256'):A['ocr']='unavailable';return
	B=os.path.join(C,'ocr',A['sha256']+'.txt');A['ocr']='done'if os.path.exists(B)else ocr_pdf(full,B)
	if A['ocr']=='done':A['text_path']=B
def scan(folders,previous=None,excluded=(),work_dir=None,report=None):
	N=work_dir;H=previous;D=report;H=H or{};D=D if D is not None else{}
	for S in('missing','system','data_dirs'):D.setdefault(S,[])
	T=_prepare(excluded);I,E={},[]
	for B in folders:
		if not os.path.exists(B):D['missing'].append(B);continue
		if os.path.isfile(B):O=os.path.dirname(os.path.abspath(B));P=[(O,[],[os.path.basename(B)])];B=O
		else:P=os.walk(B)
		U=os.path.basename(os.path.normpath(B))
		for(J,K,V)in P:
			K.sort()
			for Q in[A for A in K if A.lower()in DATA_DIRS]:K.remove(Q);D['data_dirs'].append(os.path.join(J,Q))
			for F in sorted(V,key=_copy_last):
				C=os.path.join(J,F);R=os.path.relpath(C,B).replace('\\','/');A=U+'/'+R
				if F.startswith('~$')or F.lower()in SYSTEM_FILES or _areo_sidecar(J,F):D['system'].append(A);continue
				if _is_excluded(C,R,A,T):continue
				W=F.lower().endswith(EXTS)
				try:G=sha256_file(C)
				except OSError:E.append({'path':A,'abs':C,'sha256':H.get(A),'status':'unreadable','duplicate_of':None});continue
				if not W:E.append({'path':A,'abs':C,'sha256':G,'status':'unsupported','reason':'file_type','duplicate_of':None});continue
				L=_status(A,G,H,I);M={'path':A,'abs':C,'sha256':G,'status':L,'duplicate_of':I.get(G)if L=='duplicate'else None};E.append(M);I.setdefault(G,A)
				if L=='duplicate':continue
				if F.lower().endswith('.eml'):
					with open(C,'rb')as X:_add_eml(M,X.read(),N,H,I,E)
				elif F.lower().endswith('.pdf'):_add_pdf(M,C,N)
	Y={A['path']for A in E}
	for(A,G)in sorted(H.items()):
		if A not in Y:E.append({'path':A,'abs':None,'sha256':G,'status':'removed','duplicate_of':None})
	return E
