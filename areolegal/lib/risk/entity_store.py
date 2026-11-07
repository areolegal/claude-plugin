# -*- coding: utf-8 -*-
# Copyright (c) Areo. All rights reserved. Licensed under the terms at https://areo.co.il/legal/terms
import csv,hashlib,io,json,os,re,sys,unicodedata
if __name__=='__main__':sys.dont_write_bytecode=True
from datetime import datetime,timezone
from urllib.parse import parse_qsl,urlencode,urlsplit,urlunsplit
from xml.etree import ElementTree as ET
try:from.page_text import PdfTextUnavailable,is_pdf,page_text,norm as _norm
except ImportError:from page_text import PdfTextUnavailable,is_pdf,page_text;from page_text import norm as _norm
try:from common.cli import guard_out,parser,run,write_json;from common.paths import long_path
except ImportError:import sys as _sys;_sys.path.insert(0,os.path.dirname(os.path.dirname(os.path.abspath(__file__))));from common.cli import guard_out,parser,run,write_json;from common.paths import long_path
def now_iso():return datetime.now(timezone.utc).astimezone().isoformat(timespec='seconds')
EXTRACT_CAP=204800
DEAL_CAP=2097152
DEFAULT_CAP=DEAL_CAP
PAGE_CAP=EXTRACT_CAP
MAX_ROWS=25
NEAR_ROWS=5
SOURCES_DIR='sources'
LEGACY_DIRS='raw',
SECRET_TOKENS=frozenset(('token','secret','sig','signature','key','apikey','password','passwd','pwd','auth','authorization','session','sessionid','sid','jsessionid','phpsessid','credential','credentials','otp','ticket'))
SECRET_PREFIXES='x-amz-','x-goog-'
SAS_PARAMS=frozenset(('sv','ss','srt','sp','se','st','spr','si','sr','sip','skoid','sktid','skt','ske','sks','skv','sdd'))
OAUTH_PARAMS=frozenset(('code','state','session_state'))
SIGNED_URL_PARAMS=frozenset(('expires','policy'))
def _secret_name(name,names):
	B=names;A=name.lower()
	if A.startswith(SECRET_PREFIXES):return True
	if any(A in SECRET_TOKENS for A in re.split('[-_.]',A)if A):return True
	if A in SAS_PARAMS and'sig'in B:return True
	if A in OAUTH_PARAMS and B&{'client_id','redirect_uri','scope'}:return True
	if A in SIGNED_URL_PARAMS and B&{'signature','key-pair-id'}:return True
	return False
class StoreError(Exception):0
def strip_secrets(url):
	E=url
	if not E:return E,[]
	A=urlsplit(E);B=[];G=[];H=parse_qsl(A.query,keep_blank_values=True);I={A.lower()for(A,B)in H}
	for(F,J)in H:
		if _secret_name(F,I):B.append(F)
		else:G.append((F,J))
	C=A.netloc
	if'@'in C:B.append('userinfo');C=C.split('@',1)[1]
	D=A.fragment
	if D and re.search('(token|key|sig)=',D,re.I):B.append('fragment');D=''
	K=urlunsplit((A.scheme,C,A.path,urlencode(G,doseq=True),D));return K,B
def has_secret(url):return bool(strip_secrets(url)[1])
LEGAL_SUFFIX=re.compile('\\b(l\\.?l\\.?c|inc|incorporated|ltd|limited|corp|corporation|co|company|plc|gmbh|ag|s\\.?a|b\\.?v|n\\.?v|llp|lp|pte|pty|srl|spa|oy|ab|as)\\.?$',re.I)
HE_SUFFIX=re.compile('\\s*(בע"מ|בעמ|בע״מ|שותפות מוגבלת|שותפות רשומה|ש"מ|ש״מ|אגודה שיתופית בע"מ|\\(ישראל\\)|ישראל)\\s*$')
PUNCT=re.compile('[^\\w\\s]',re.U)
def normalize_name(name):
	A=unicodedata.normalize('NFKC',str(name or''));A=re.sub('[֑-ׇ\u200e\u200f\u202a-\u202e]','',A);A=A.replace('״','"').replace('׳',"'");A=HE_SUFFIX.sub('',A.strip());A=A.casefold().replace('.','');A=PUNCT.sub(' ',A);A=re.sub('\\s+',' ',A).strip();B=None
	while B!=A:B=A;A=LEGAL_SUFFIX.sub('',A).strip()
	return A
def entity_kind_compatible(query_type,record_type):
	A=(query_type or'').lower();B=(record_type or'').lower()
	if not A or not B:return True
	C='individual','person','אדם','יחיד';D=any(B in A for B in C);E=any(A in B for A in C);return D==E
def match_name(query_name,record_name,aliases=(),query_type='entity',record_type=''):
	C=aliases;A=normalize_name(query_name)
	if not A:return'none','שם ריק'
	D=normalize_name(record_name);E=entity_kind_compatible(query_type,record_type)
	if D==A:return('exact','השם זהה אחרי נרמול')if E else('near','השם זהה אבל סוג הישות שונה (אדם מול תאגיד)')
	for B in C or():
		if normalize_name(B)==A:return('alias','כינוי רשמי זהה אחרי נרמול')if E else('near','כינוי זהה אבל סוג הישות שונה')
	F=set(A.split());G=set(D.split())
	for B in C or():G|=set(normalize_name(B).split())
	if F and F<=G:return'near','כל מילות השם מופיעות, אבל השם אינו זהה'
	return'none',''
def scan_rows(rows,query_name,name_field,alias_fields=(),type_field=None,note_fields=(),query_type='entity'):
	G=type_field;F=query_name;H,B=[],[];C=normalize_name(F)
	for(D,A)in enumerate(rows):
		I=[]
		for L in alias_fields:
			J=A.get(L)
			if J:I+=[A.strip()for A in re.split('[;|]',str(J))if A.strip()]
		E,K=match_name(F,A.get(name_field,''),I,query_type,A.get(G,'')if G else'')
		if E in('exact','alias'):H.append({'row_no':D,'match':E,'why':K,'row':A})
		elif E=='near':B.append({'row_no':D,'match':'near','why':K,'row':A})
		elif C and any(C and C in normalize_name(A.get(B,''))for B in note_fields):B.append({'row_no':D,'match':'near','why':'השם מופיע רק בשדה הערות, לא בשדה השם','row':A})
	return H,B
OFAC_SDN_FIELDS=['ent_num','SDN_Name','SDN_Type','Program','Title','Call_Sign','Vess_type','Tonnage','GRT','Vess_flag','Vess_owner','Remarks']
OFAC_ALT_FIELDS=['ent_num','alt_num','alt_type','alt_name','alt_remarks']
def rows_from_csv_bytes(data,encoding='utf-8-sig',delimiter=None,fieldnames=None,header_startswith=None):
	C=header_startswith;A=delimiter;E=data.decode(encoding,'replace');B=E.splitlines(True)
	if C:
		for(F,G)in enumerate(B):
			if G.lstrip('\ufeff"').startswith(C):B=B[F:];break
	D=''.join(B)
	if A is None:
		H=D[:20000]
		try:A=csv.Sniffer().sniff(H,delimiters=',;\t').delimiter
		except csv.Error:A=','
	I=list(csv.DictReader(io.StringIO(D),fieldnames=fieldnames,delimiter=A));return[{(B or'').strip():A.strip()if isinstance(A,str)else A for(B,A)in A.items()}for A in I]
def rows_from_un_xml(data):
	D=ET.fromstring(data);B=[]
	for(E,C)in(('individual','INDIVIDUAL'),('entity','ENTITY')):
		for A in D.iter(C):F=[(A.findtext(B)or'').strip()for B in('FIRST_NAME','SECOND_NAME','THIRD_NAME','FOURTH_NAME')];G=[(A.findtext('ALIAS_NAME')or'').strip()for A in A.iter(C+'_ALIAS')];B.append({'name':' '.join(A for A in F if A),'type':E,'aliases':';'.join(A for A in G if A),'reference':(A.findtext('REFERENCE_NUMBER')or'').strip(),'comments':(A.findtext('COMMENTS1')or'').strip()})
	return B
def sha256_bytes(b):return hashlib.sha256(b).hexdigest()
def sha256_file(path,chunk=1<<20):
	A=hashlib.sha256()
	with open(long_path(path),'rb')as B:
		for C in iter(lambda:B.read(chunk),b''):A.update(C)
	return A.hexdigest()
class EntityStore:
	def __init__(A,deal_dir,cap_bytes=DEAL_CAP,max_rows=MAX_ROWS,extract_cap=EXTRACT_CAP):B=deal_dir;A.deal_dir=B;A.raw_dir=os.path.join(B,SOURCES_DIR);A.cap=cap_bytes;A.extract_cap=extract_cap;A.max_rows=max_rows;A.records=[]
	def used_bytes(A):
		if not os.path.isdir(A.raw_dir):return 0
		return sum(os.path.getsize(os.path.join(A.raw_dir,B))for B in os.listdir(A.raw_dir))
	def _write(A,name,data):
		C=data;B=name
		if not re.match('^[A-Za-z0-9_\\-]+\\.[a-z0-9]{2,5}$',B):raise StoreError('שם קובץ לא חוקי: %r (המבנה: <source_id>.<ext>)'%B)
		if len(C)>A.extract_cap:raise StoreError('קטע של %d בתים, מעל %d לכל קטע שנשמר: %s'%(len(C),A.extract_cap,B))
		if A.used_bytes()+len(C)>A.cap:raise StoreError('חריגה מתקרת תיקיית המחקר של העסקה (%d בתים): %s'%(A.cap,B))
		os.makedirs(A.raw_dir,exist_ok=True);D=os.path.join(A.raw_dir,B)
		with open(D,'wb')as E:E.write(C)
		return D
	def store_list_result(C,source_id,source,url,query,full_bytes=None,full_path=None,rows=None,name_field='name',alias_fields=(),type_field=None,note_fields=(),file_date=None,query_type='entity',looked_up_at=None):
		K=query_type;J=query;E=full_path;D=source_id;B=full_bytes;A=rows
		if B is None and E is not None:
			F=os.path.getsize(long_path(E));G=sha256_file(E)
			if A is None:
				with open(long_path(E),'rb')as O:A=rows_from_csv_bytes(O.read())
		else:
			B=B or b'';F=len(B);G=sha256_bytes(B)
			if A is None:A=rows_from_csv_bytes(B)
		H,L=scan_rows(A,J,name_field,alias_fields,type_field,note_fields,K);P=L[:NEAR_ROWS]
		if len(H)>C.max_rows:raise StoreError('יותר מ-%d התאמות לשם אחד: השאילתה רחבה מדי, אין שמירה של רשימה'%C.max_rows)
		M,Q=strip_secrets(url);R=list(A[0].keys())if A else[];I={'source_id':D,'source':source,'url':M,'url_params_removed':Q,'query':J,'query_type':K,'looked_up_at':looked_up_at or now_iso(),'file_date':file_date,'full_size_bytes':F,'full_sha256':G,'rows_total':len(A),'header':R,'result':'match'if H else'no_match','matches':H,'near':P,'near_total':len(L),'stored':'match_window'};N=json.dumps(I,ensure_ascii=False,indent=1).encode('utf-8');S=C._write(D+'.json',N);T={'source_id':D,'final_url':M,'file':SOURCES_DIR+'/'+D+'.json','stored':'match_window','full_size_bytes':F,'full_sha256':G,'sha256':sha256_bytes(N),'result':I['result']};C.records.append(T);return I,S
	def store_page(C,source_id,url,content,ext='htm',excerpt=None,window=4000,title=None):
		L=title;K=window;J=excerpt;D=source_id;B=ext;A=content
		if isinstance(A,str):A=A.encode('utf-8')
		O,P=strip_secrets(url);Q,E=sha256_bytes(A),len(A);M='page';F=A
		if is_pdf(A)and B in('htm','html'):B='pdf'
		if E>PAGE_CAP:
			if not J:raise StoreError('דף של %d בתים בלי קטע מילולי: לא נשמר (מעל %d)'%(E,PAGE_CAP))
			try:R=page_text(A)
			except PdfTextUnavailable as S:raise StoreError('אין שכבת טקסט ל-PDF הגדול (%s): לא נשמר'%S)
			G,N=_norm(R),_norm(J);H=G.find(N)
			if H<0:raise StoreError('הקטע המילולי לא נמצא בדף; אין שמירה')
			T,U=max(0,H-K),min(len(G),H+len(N)+K);F=G[T:U].encode('utf-8');M='excerpt_window';B='txt'
		V=C._write('%s.%s'%(D,B),F);I={'source_id':D,'final_url':O,'url_params_removed':P,'file':'%s/%s.%s'%(os.path.basename(C.raw_dir),D,B),'stored':M,'full_size_bytes':E,'full_sha256':Q,'sha256':sha256_bytes(F),'saved_at':now_iso()}
		if L:I['title']=L
		C.records.append(I);return I,V
SANCTIONS_NAME=re.compile('(sdn|consolidated|sanction|ofsi|fsf|ent-0[3-7])',re.I)
def audit_deal_dir(deal_dir,cap_bytes=DEAL_CAP,report_json=None):
	G=cap_bytes;F=deal_dir;B=[];C=0
	for H in(SOURCES_DIR,)+LEGACY_DIRS:
		D=os.path.join(F,H)
		if not os.path.isdir(D):continue
		for A in sorted(os.listdir(D)):
			L=os.path.join(D,A);E=os.path.getsize(L);C+=E
			if E>EXTRACT_CAP:B.append('קובץ מעל 200 קילובייט ב-%s (נראה כרשימה או דף מלא): %s, %d בתים'%(H,A,E))
	if C>G:B.append('תיקיית העותקים בתיקיית העסקה: %d בתים, מעל התקרה %d'%(C,G))
	I=report_json or os.path.join(F,'entity-report.json')
	if os.path.exists(long_path(I)):
		with open(long_path(I),encoding='utf-8')as M:N=json.load(M)
		for J in('raw_copies','sources','lookups'):
			for(O,K)in enumerate(N.get(J)or[]):
				for A in('url','typed_url','final_url'):
					if K.get(A)and has_secret(K[A]):B.append('%s[%d].%s: כתובת עם טוקן או חתימה'%(J,O,A))
	return B
def main(argv=None):
	C=parser('בדיקת תיקיית העותקים של עסקה',out_required=False);C.add_argument('command',choices=['audit']);C.add_argument('--deal',required=True,help='תיקיית העסקה (קריאה בלבד)');A=C.parse_args(argv);B=audit_deal_dir(A.deal)
	if A.out:D=os.path.join(A.deal,'entity-report.json');write_json(A.out,{'problems':B},inputs=[D]+[os.path.join(A.deal,SOURCES_DIR,B)for B in(os.listdir(os.path.join(A.deal,SOURCES_DIR))if os.path.isdir(os.path.join(A.deal,SOURCES_DIR))else[])])
	sys.stdout.reconfigure(encoding='utf-8')
	for E in B:print('ERR',E)
	print('problems:',len(B));return 1 if B else 0
if __name__=='__main__':sys.exit(run(main))
