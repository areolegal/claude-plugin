# -*- coding: utf-8 -*-
# Copyright (c) Areo. All rights reserved. Licensed under the terms at https://areo.co.il/legal/terms
import hashlib,ipaddress,json,os,posixpath,re,socket,sys,time,urllib.error,urllib.request
from datetime import datetime,timezone
from urllib.parse import parse_qsl,quote,unquote,urlencode,urlsplit,urlunsplit
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
def _version():
	try:
		with open(os.path.join(ROOT,'VERSION'),encoding='utf-8')as A:return A.read().strip()or'1.2.0'
	except OSError:return'1.2.0'
VERSION=_version()
ORG='AreoLegal'
UA_PREFIX='AreoLegal-research/'
UA_FORMAT=UA_PREFIX+'%s ('+ORG+' automated legal research; contact: %s)'
BROWSER_UA=re.compile('Mozilla/|Chrome/|Safari/|Firefox/|Edg/|Gecko',re.I)
UA_CONTACT=re.compile('contact: [A-Za-z0-9._%+\\-]+@[A-Za-z0-9.\\-]+\\.[A-Za-z]{2,}\\)$')
CONTACT_ENV='AREO_CONTACT_EMAIL'
CONFIG_PATH=os.path.join(ROOT,'config.json')
_EMAIL=re.compile('^[A-Za-z0-9._%+\\-]+@[A-Za-z0-9\\-]+(?:\\.[A-Za-z0-9\\-]+)*\\.[A-Za-z]{2,}$')
MIN_INTERVAL=2.
MAX_PER_HOST=30
MAX_BYTES=104857600
TIMEOUT=30
BLOCK_CODES={401,403,407,429,451}
OK_2XX={200,201,203,204,206}
HOST_POLICY={'nevo.co.il':{'paths':('/law_html/','/HakikaSearch.aspx'),'post_paths':('/HakikaSearch.aspx',),'min_interval':1e1,'max_requests':10}}
CHALLENGE=re.compile('cf-chl|challenge-platform|cf_chl_opt|Attention Required! \\| Cloudflare|<title>\\s*Just a moment|_Incapsula_Resource|Incapsula incident|Request unsuccessful\\. Incapsula|g-recaptcha|h-captcha|hcaptcha\\.com|<title>[^<]*(?:captcha|access denied|are you a robot)[^<]*</title>|perimeterx|px-captcha|datadome|verify (?:that )?you(?: a|\\\')re (?:a )?human|are you a human|confirm you are human|i\\\'m not a robot|(?:id|name|class)=["\\\'][^"\\\']*captcha|anomaly-modal|anomaly\\.js|bots use DuckDuckGo too|אנא אמת(?:ו)? שאינך רובוט|אימות אנושי',re.I)
BLOCKS_FILE='net-blocks.json'
MULTI_SUFFIX={'co.il','org.il','gov.il','ac.il','net.il','muni.il','idf.il','k12.il','co.uk','org.uk','gov.uk','ac.uk','ltd.uk','plc.uk','net.uk','sch.uk','nhs.uk','police.uk','com.au','gov.au','org.au','net.au','edu.au','co.nz','govt.nz','co.jp','go.jp','or.jp','com.br','gov.br','co.in','gov.in','co.za','gov.za','com.cn','gov.cn','com.sg','gov.sg','com.hk','gov.hk','europa.eu'}
_last={}
_count={}
_blocked={}
_run={'dir':None}
_contact={'email':None}
_clock=time.monotonic
_sleep=time.sleep
USER_AGENT=None
def _set_contact(email):A=email;global USER_AGENT;A=(A or'').strip();_contact['email']=A if _EMAIL.match(A)else None;USER_AGENT=UA_FORMAT%(VERSION,_contact['email'])if _contact['email']else None;return USER_AGENT
def configure(contact_email=None,config_path=None):
	A=contact_email or os.environ.get(CONTACT_ENV)
	if not A:
		try:
			with open(config_path or CONFIG_PATH,encoding='utf-8')as C:B=json.load(C)
			A=B.get('contact_email')or(B.get('net')or{}).get('contact_email')
		except(OSError,ValueError,AttributeError):A=None
	return _set_contact(A)
def user_agent():return USER_AGENT
configure()
def registrable_domain(host):
	A=host;A=(A or'').lower().strip('.')
	try:ipaddress.ip_address(A);return A
	except ValueError:pass
	B=A.split('.')
	if len(B)<=2:return A
	C=3 if'.'.join(B[-2:])in MULTI_SUFFIX else 2;return'.'.join(B[-C:])
def _blocks_path(run_dir):return os.path.join(run_dir,BLOCKS_FILE)
def _load_blocks(run_dir):
	B=run_dir
	if not B:return
	try:
		with open(_blocks_path(B),encoding='utf-8')as C:D=json.load(C)
	except(OSError,ValueError):return
	for(E,A)in(D.get('blocked')or{}).items():_blocked.setdefault(E,A.get('why')if isinstance(A,dict)else str(A))
def _save_blocks(run_dir):
	A=run_dir
	if not A:return
	os.makedirs(A,exist_ok=True);B=_blocks_path(A);C=B+'.tmp'
	with open(C,'w',encoding='utf-8')as D:json.dump({'blocked':{A:{'why':B}for(A,B)in sorted(_blocked.items())},'updated_at':now_iso()},D,ensure_ascii=False,indent=1)
	os.replace(C,B)
def start_run(run_dir=None):A=run_dir;reset_session();_run['dir']=A;_load_blocks(A)
def reset_session():_last.clear();_count.clear();_blocked.clear();_run['dir']=None
def now_iso():return datetime.now(timezone.utc).astimezone().isoformat(timespec='seconds')
try:from risk.entity_store import strip_secrets;from common.case_law import case_law_url
except ImportError:sys.path.insert(0,ROOT);from risk.entity_store import strip_secrets;from common.case_law import case_law_url
def to_uri(url):
	try:A=urlsplit(url);D=A.hostname.encode('idna').decode('ascii')if A.hostname else''
	except(UnicodeError,ValueError):return url
	B=D+(':%d'%A.port if A.port else'')
	if A.username:B=A.username+(':'+A.password if A.password else'')+'@'+B
	C="/%:@!$&'()*+,;=-._~";return urlunsplit((A.scheme,B,quote(A.path,safe=C),quote(A.query,safe=C+'?'),quote(A.fragment,safe=C)))
def _host(url):return(urlsplit(url).hostname or'').lower()
def _policy(host):
	for(A,B)in HOST_POLICY.items():
		if host==A or host.endswith('.'+A):return B
	return{}
def norm_path(path):A=unquote(path or'/').replace(chr(92),'/');A=posixpath.normpath('/'+A.lstrip('/'));A=re.sub('/+','/',A);return('/'if A in('.','')else A).lower()
def _path_under(path,prefix,bounded=True):
	B=path;A=prefix;A=norm_path(A).rstrip('/')or'/'
	if A=='/':return True
	if not bounded:return B.startswith(A)
	return B==A or B.startswith(A+'/')
def rule_matches(url,rule):
	A=rule;A=(A or'').strip();E=A.startswith('!')
	if E:A=A[1:]
	F=A.startswith('=')
	if F:A=A[1:]
	if A.startswith('*.'):A=A[2:]
	A,I,G=A.partition('?');B,I,H=A.partition('/');B=B.lower().strip('.')
	if B.startswith('www.'):B=B[4:]
	try:D=urlsplit(url or'');C=(D.hostname or'').lower().rstrip('.')
	except ValueError:return False
	if not C or not B:return False
	if F:
		if C not in(B,'www.'+B):return False
	elif not(C==B or C.endswith('.'+B)):return False
	if H and not _path_under(norm_path(D.path),'/'+H,bounded=not E):return False
	if G:
		J={(A.lower(),B.lower())for(A,B)in parse_qsl(D.query,keep_blank_values=True)}
		for(K,L)in parse_qsl(G,keep_blank_values=True):
			if(K.lower(),L.lower())not in J:return False
	return True
def url_allowed(url,rules):
	B=url;A=rules
	if case_law_url(B):return False
	A=[A for A in tuple(A or())+tuple(getattr(A,'refuse',()))if A]
	if any(A.startswith('!')and rule_matches(B,A)for A in A):return False
	return any(not A.startswith('!')and rule_matches(B,A)for A in A)
def _url_problem(url,allowed_domains,pol,dom,after_redirect=False):
	D=allowed_domains;B=pol;A=url;C='אחרי הפניה: 'if after_redirect else'';E=case_law_url(A)
	if E:return'refused: %s%s'%(C,E)
	if D is not None and not url_allowed(A,D):return'refused: %sכתובת שאינה ברשימה המורשית, בדומיין או בנתיב (%s)'%(C,_host(A))
	if B.get('paths')and not any(_path_under(norm_path(urlsplit(A).path),B)for B in B['paths']):return'refused: %sב-%s רק הנתיבים %s'%(C,dom,', '.join(B['paths']))
	return''
def _decode(b,ctype):
	A=re.search('charset=([A-Za-z0-9_\\-]+)',ctype or'',re.I);B=re.search(b'charset=["\\\']?([A-Za-z0-9_\\-]+)',b[:4096]);C=['utf-8']+([A.group(1)]if A else[])+([B.group(1).decode('ascii','ignore')]if B else[])+['cp1255']
	for D in C:
		try:return b.decode(D)
		except(LookupError,UnicodeDecodeError):continue
	return b.decode('utf-8','replace')
def _lawyer_task(host,purpose,why,url):return{'item':'%s: %s'%(host,purpose),'why':why,'task':'עורך הדין','url':url}
OFFICIAL_ID=re.compile('\\b[1-9CE]\\d{4}[A-Z]{1,2}\\d{3,4}\\b|(?:lawitemid|lawid|law_id|celex|docid|billid)\\s*[=:]?\\s*\\d+|\\d+\\s*U\\.?S\\.?C\\.?(?:\\s*§*\\s*\\d+)?|\\d+\\s*C\\.?F\\.?R\\.?(?:\\s*(?:Part\\s*)?\\d+)?|Pub(?:lic)?\\.?\\s*L(?:aw)?\\.?\\s*(?:No\\.?\\s*)?\\d+[-–]\\d+',re.I)
OFFICIAL_CONTEXT=re.compile('(?:חוק|תקנות|תקנה|צו|פקודת|פקודה|הצעת חוק|ס"ח|ס״ח|ק"ת|ק״ת|י"פ|י״פ|ה"ח|ה״ח|רשומות|קובץ התקנות|ספר החוקים|statute|regulation|directive|act|law|section|§)[^\\d]{0,25}$',re.I)
PHONE=re.compile('(?<!\\d)(?:\\+972[-\\s]?|0)(?:[23489]|5\\d|7\\d)[-\\s]?\\d{3}[-\\s]?\\d{4}(?!\\d)')
def _id_check_digit(num):
	if not re.fullmatch('\\d{9}',num):return False
	B=0
	for(C,D)in enumerate(num):A=int(D)*(1 if C%2==0 else 2);B+=A if A<10 else A-9
	return B%10==0
def client_detail_in_query(query,company_names=()):
	C=str(query or'');F=' '.join(C.split()).casefold()
	for G in company_names or():
		D=' '.join(str(G or'').split())
		if D and D.casefold()in F:return D
	A=PHONE.search(C)
	if A:return A.group(0)
	E=OFFICIAL_ID.sub(lambda x:' '*len(x.group(0)),C)
	for A in re.finditer('\\d{5,}',E):
		B=A.group(0)
		if len(B)==9 and _id_check_digit(B):return B
		if OFFICIAL_CONTEXT.search(E[:A.start()]):continue
		return B
	return''
def _block(dom,why):_blocked[dom]=why;_save_blocks(_run['dir'])
def fetch(url,purpose,allowed_domains=None,store=None,source_id=None,excerpt=None,timeout=TIMEOUT,accept='text/html,application/pdf,application/json,text/csv,application/xml;q=0.9,*/*;q=0.5',max_bytes=MAX_BYTES,form=None,run_dir=None,_opener=None):
	W=source_id;V=store;U=allowed_domains;Q=max_bytes;N=run_dir;L=form;J=purpose;G=url
	if N and N!=_run['dir']:_run['dir']=N;_load_blocks(N)
	G=to_uri(G);K,f=strip_secrets(G);R=_host(G);B=registrable_domain(R);O=_policy(R);S='POST'if L is not None else'GET';X=strip_secrets('http://x/?'+urlencode(L,doseq=True))[0].split('?',1)[-1]if L else'';A={'status':None,'text':None,'blocked':False,'reason':'','content':None,'content_type':'','url':K,'final_url':K,'url_params_removed':f,'sha256':None,'bytes':0,'lawyer_task':None,'stored':None,'method':S}
	def D():
		A['log']={'at':now_iso(),'url':A['url'],'final_url':A['final_url'],'purpose':J,'method':S,'status':A['status'],'blocked':A['blocked'],'reason':A['reason'],'user_agent':USER_AGENT,'bytes':A['bytes'],'sha256':A['sha256'],'via':'common.net'}
		if X:A['log']['form']=X
		return A
	if not USER_AGENT:A['reason']='refused: אין כתובת קשר במזהה. לקבוע contact_email בתצורה (configure, %s או config.json)'%CONTACT_ENV;return D()
	if not J or not str(J).strip():A['reason']='refused: חסרה מטרה (purpose)';return D()
	if urlsplit(G).scheme not in('http','https')or not R:A['reason']='refused: כתובת שאינה http או https';return D()
	M=_url_problem(G,U,O,B)
	if M:A['reason']=M;return D()
	g=norm_path(urlsplit(G).path)
	if L is not None and not any(_path_under(g,A)for A in O.get('post_paths',())):A['reason']='refused: POST רק לטופס חיפוש רשמי שברשימה (HOST_POLICY post_paths)';return D()
	if B in _blocked:A['blocked']=True;A['reason']='blocked earlier in this run: %s (אין ניסיון חוזר)'%_blocked[B];A['lawyer_task']=_lawyer_task(B,J,'נחסם: '+_blocked[B],K);return D()
	if _count.get(B,0)>=O.get('max_requests',MAX_PER_HOST):A['reason']='refused: תקרת הבקשות ל-%s בהרצה הזו'%B;return D()
	Y=O.get('min_interval',MIN_INTERVAL)
	if B in _last:
		Z=_last[B]+Y-_clock()
		if Z>0:_sleep(Z)
	a={'User-Agent':USER_AGENT,'Accept':accept};b=None
	if L is not None:b=urlencode(L,doseq=True).encode('utf-8');a['Content-Type']='application/x-www-form-urlencoded; charset=utf-8'
	h=urllib.request.Request(G,data=b,headers=a,method=S);i=_opener or urllib.request.build_opener();C,E,H,I=None,None,'',G
	for j in(1,2):
		_last[B]=_clock();_count[B]=_count.get(B,0)+1
		try:
			with i.open(h,timeout=timeout)as P:E=P.getcode();H=P.headers.get('Content-Type','');I=P.geturl()or G;C=P.read(Q+1)
			break
		except urllib.error.HTTPError as F:
			E=F.code;H=F.headers.get('Content-Type','')if F.headers else''
			try:C=F.read(200000)
			except Exception:C=b''
			I=getattr(F,'filename',None)or G;c=F.headers.get('Retry-After')if F.headers else None
			if E in BLOCK_CODES:T='%d%s'%(E,', Retry-After %s'%c if c else'');_block(B,T);A.update(status=E,blocked=True,reason='blocked: HTTP %s'%T,lawyer_task=_lawyer_task(B,J,'נחסם (%s)'%T,K));A['final_url']=strip_secrets(I)[0];return D()
			A.update(status=E,reason='http_error: %d'%E);A['final_url']=strip_secrets(I)[0];return D()
		except(urllib.error.URLError,socket.timeout,ConnectionError,OSError)as F:
			if j==2:A['reason']='network_error: %s'%(getattr(F,'reason',None)or F);return D()
			_sleep(Y)
	A['status']=E;A['content_type']=H;A['final_url']=strip_secrets(I)[0];M=_url_problem(I,U,_policy(_host(I)),registrable_domain(_host(I)),after_redirect=True)
	if M:A['reason']=M;return D()
	if C is not None and len(C)>Q:A['reason']='refused: מעל %d בתים'%Q;return D()
	C=C or b''
	if E is not None and 200<=E<300 and E not in OK_2XX:_block(B,'challenge %d'%E);A.update(blocked=True,reason='blocked: דף אתגר בקוד %d (קוד 2xx חריג)'%E,lawyer_task=_lawyer_task(B,J,'נחסם (CAPTCHA, קוד %d)'%E,K));return D()
	d=C[:300000].decode('utf-8','ignore')if not C[:5]==b'%PDF-'else''
	if d and CHALLENGE.search(d):_block(B,'CAPTCHA');A.update(blocked=True,reason='blocked: דף אתגר (CAPTCHA או הגנת בוטים)',lawyer_task=_lawyer_task(B,J,'נחסם (CAPTCHA)',K));return D()
	A['content']=C;A['bytes']=len(C);A['sha256']=hashlib.sha256(C).hexdigest()
	if C[:5]==b'%PDF-'or'pdf'in(H or'').lower():A['reason']='ok: PDF (הטקסט דרך risk.page_text.page_text)'
	else:A['text']=_decode(C,H);A['reason']='ok'
	if V is not None and W:
		k='pdf'if C[:5]==b'%PDF-'else'json'if'json'in H else'txt'if'text/plain'in H else'csv'if'csv'in H else'htm'
		try:e,l=V.store_page(W,A['final_url'],C,ext=k,excerpt=excerpt);e['typed_url']=K;A['stored']=e
		except Exception as F:A['reason']='ok, not stored: %s'%F
	return D()
def assert_honest_headers(headers):
	A={A.lower():B for(A,B)in headers.items()}.get('user-agent','')
	if not A.startswith(UA_PREFIX)or BROWSER_UA.search(A):raise AssertionError('user-agent שאינו המזהה של Areo: %r'%A)
	if ORG not in A or not UA_CONTACT.search(A):raise AssertionError('user-agent בלי שם הארגון וכתובת קשר: %r'%A)
	return True
