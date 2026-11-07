# -*- coding: utf-8 -*-
# Copyright (c) Areo. All rights reserved. Licensed under the terms at https://areo.co.il/legal/terms
import base64,json,os,re,shutil,socket,struct,subprocess,sys,tempfile,time,urllib.request,zlib
from pathlib import Path
if __name__=='__main__':sys.dont_write_bytecode=True
try:from common.cli import guard_out,parser,run,write_json;from common.paths import long_path
except ImportError:sys.path.insert(0,os.path.dirname(os.path.dirname(os.path.abspath(__file__))));from common.cli import guard_out,parser,run,write_json;from common.paths import long_path
BODY_PAGE_LIMIT=8
A4=595,842
DEFAULT_MARKERS=['Areo Workspace','התמונה במבט אחד','השורה התחתונה']
ENTITY_MARKERS=['Areo Workspace','חקר ישות','ממצאים שעוצרים את העסקה']
ENTITY_PLACEHOLDER='__ENTITY_DATA__'
ENTITY_BODY_LIMIT=2
KINDS={'risk':{'placeholder':'__RISK_DATA__','markers':None,'body_limit':BODY_PAGE_LIMIT,'name':'סיכונים'},'entity':{'placeholder':ENTITY_PLACEHOLDER,'markers':ENTITY_MARKERS,'body_limit':ENTITY_BODY_LIMIT,'name':'חקר ישות'}}
RESOURCES=os.path.join(os.path.dirname(os.path.abspath(__file__)),'resources')
APPENDIX_TITLES=['נספח: ציטוטים מילוליים','Appendix: verbatim quotes']
HEADINGS=['התמונה במבט אחד','השורה התחתונה','העדשות','מועדים קריטיים','התמונה הכספית','הסיכונים','סתירות בין ההסכם לנספחים','צירופים ושרשראות','הסיכונים הקריטיים בפירוט','מה לא נבדק ומה חסר','נספח: ציטוטים מילוליים','נספחים שלא נמסרו','הנחות שהלקוח צריך לאשר','מספר','עדשה','הסיכון בשורה אחת','סעיף','חומרה','כיוון טיפול','נושא','מה גובר','התיקון','מסמך וסעיף','הנוסח המילולי']
HE_DRAFT='טיוטה, טעונה אישור'
HE_PRIV='חסוי: מסמך עבודה של המחלקה המשפטית, הוכן לבקשת עו״ד {counsel} לצורך מתן ייעוץ משפטי ל{company}'
HE_PRIV_NONE='לא צוין עורך דין שהדוח הוכן עבורו; קיים ספק אם יחול חיסיון'
EN_DRAFT='Draft, pending approval'
EN_PRIV='Privileged: legal department working document, prepared at the request of {counsel} for the purpose of legal advice to {company}'
EN_PRIV_NONE='No counsel named for this report; privilege may not apply'
EN_MARKERS=['Areo Workspace','At a glance','Bottom line']
EN_ENTITY_MARKERS=['Areo Workspace','Entity check','Findings that stop the deal']
EN_HEADINGS=['At a glance','Bottom line','The lenses','Critical dates','The money picture','1. Risks','2. Agreement vs annexes','3. Combinations and chains','4. Critical risks in detail','Not checked and missing','Appendix: verbatim quotes','Annexes not provided','Assumptions the client should confirm','Lens','The risk in one line','Clause','Severity','Treatment direction','Topic','What prevails','The fix','Document and clause','Verbatim text']
TITLES={('risk','he'):'Areo Workspace | סיכונים',('risk','en'):'Areo Workspace | Risks',('entity','he'):'Areo Workspace | חקר ישות',('entity','en'):'Areo Workspace | Entity check'}
BAND_PAD=3.
OVERLAP_MIN=1.
def build_report(template_text,register,placeholder='__RISK_DATA__'):
	C=register;B=template_text;A=placeholder;D=B.count(A)
	if D!=1:raise ValueError('מציין ההזרקה %s צריך להופיע פעם אחת בדיוק (נמצא %d)'%(A,D))
	E=json.dumps(C,ensure_ascii=False).replace('</','<\\/');return localize_shell(B,lang_of(C)).replace(A,E)
def lang_of(register):A=(register or{}).get('meta')or{};B=str(A.get('deliverable_language')or A.get('display_language')or'he').strip().lower();return'en'if B[:2]=='en'or B in('english','אנגלית')else'he'
def localize_shell(html_text,lang):
	A=html_text
	if lang!='en':return A
	A=A.replace('<html lang="he" dir="rtl">','<html lang="en" dir="ltr">',1)
	for B in('risk','entity'):A=A.replace('<title>%s</title>'%TITLES[B,'he'],'<title>%s</title>'%TITLES[B,'en'],1)
	return A
def static_checks(html_text):
	A=html_text;B=[]
	if A.count('<!--')!=A.count('-->'):B.append('הערה שאינה נסגרת')
	if re.search('<link\\b',A,re.I):B.append('<link> בתבנית')
	if re.search('@import',A):B.append('@import בתבנית')
	for C in re.finditer('\\b(?:src|href)\\s*=\\s*["\\\'](https?:)?//',A,re.I):B.append('טעינה חיצונית: %s'%A[C.start():C.start()+60])
	if re.search('url\\(\\s*["\\\']?https?:',A,re.I):B.append('url() חיצוני ב-CSS')
	return B
COUNSEL_TITLE_RE=re.compile('^\\s*(?:עו(?:"|״|\\\'\\\'|”)ד|עוה(?:"|״)ד|עורך הדין|עורכת הדין|Adv\\.?|Advocate)\\s+',re.I)
def counsel_name(name,role=None):
	A=COUNSEL_TITLE_RE.sub('',str(name or'').strip()).strip();B=str(role or'').strip()
	if B and A.endswith(B)and A!=B:A=A[:-len(B)].rstrip(' ,;-').strip()
	return A
def band_text_from_register(register,lang=None):
	B=register;C=B.get('meta')or{};D=(lang or lang_of(B))=='en';F,G,H=(EN_DRAFT,EN_PRIV,EN_PRIV_NONE)if D else(HE_DRAFT,HE_PRIV,HE_PRIV_NONE);E=counsel_name(C.get('prepared_for_counsel'));A=str(C.get('company')or'').strip()
	if not D and A and not'\u0590'<=A[0]<='\u05ff':A='-'+A
	I=G.replace('{counsel}',E).replace('{company}',A)if E else H;return F+' · '+I
def markers_for(kind,lang):
	if kind=='entity':return EN_ENTITY_MARKERS if lang=='en'else ENTITY_MARKERS
	return EN_MARKERS if lang=='en'else DEFAULT_MARKERS
def find_browser():
	C=os.environ.get('AREO_BROWSER');A=[C]if C else[];F=[os.environ.get(A)for A in('PROGRAMFILES','PROGRAMFILES(X86)','LOCALAPPDATA')]
	for D in[A for A in F if A]:A+=[os.path.join(D,'Google','Chrome','Application','chrome.exe'),os.path.join(D,'Microsoft','Edge','Application','msedge.exe')]
	A+=['C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe','C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe']
	for G in('google-chrome','chromium','chromium-browser','microsoft-edge','msedge','chrome'):
		E=shutil.which(G)
		if E:A.append(E)
	A+=['/Applications/Google Chrome.app/Contents/MacOS/Google Chrome','/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge']
	for B in A:
		if B and os.path.isfile(B):return B
class WS:
	def __init__(A,url,timeout=60):
		B=re.match('ws://([^/:]+):(\\d+)(/.*)',url);D,E,H=B.group(1),int(B.group(2)),B.group(3);A.sock=socket.create_connection((D,E),timeout=timeout);I=base64.b64encode(os.urandom(16)).decode();J='GET %s HTTP/1.1\r\nHost: %s:%d\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Key: %s\r\nSec-WebSocket-Version: 13\r\n\r\n'%(H,D,E,I);A.sock.sendall(J.encode());C=b''
		while b'\r\n\r\n'not in C:
			F=A.sock.recv(4096)
			if not F:raise ConnectionError('handshake failed')
			C+=F
		G,A.rest=C.split(b'\r\n\r\n',1)
		if b' 101 'not in G.split(b'\r\n')[0]:raise ConnectionError(G.decode('latin-1'))
	def _recv_exact(B,n):
		A=B.rest[:n];B.rest=B.rest[n:]
		while len(A)<n:
			C=B.sock.recv(max(65536,n-len(A)))
			if not C:raise ConnectionError('socket closed')
			A+=C
		if len(A)>n:B.rest=A[n:]+B.rest;A=A[:n]
		return A
	def send(E,text):
		C=text.encode('utf-8');A=bytearray([129]);B=len(C)
		if B<126:A.append(128|B)
		elif B<65536:A.append(254);A+=struct.pack('>H',B)
		else:A.append(255);A+=struct.pack('>Q',B)
		D=os.urandom(4);E.sock.sendall(bytes(A)+D+bytes(B^D[A%4]for(A,B)in enumerate(C)))
	def recv(A):
		D=b''
		while True:
			E,F=A._recv_exact(2);G,B=E&15,F&127
			if B==126:B=struct.unpack('>H',A._recv_exact(2))[0]
			elif B==127:B=struct.unpack('>Q',A._recv_exact(8))[0]
			H=A._recv_exact(4)if F&128 else None;C=A._recv_exact(B)
			if H:C=bytes(B^H[A%4]for(A,B)in enumerate(C))
			if G==9:continue
			if G==8:raise ConnectionError('closed by browser')
			D+=C
			if E&128:return D.decode('utf-8')
	def close(A):
		try:A.sock.close()
		except OSError:pass
class Browser:
	def __init__(A,exe,profile_dir):
		B=profile_dir;A.profile=B;E=[exe,'--headless=new','--remote-debugging-port=0','--user-data-dir='+B,'--no-first-run','--no-default-browser-check','--disable-extensions','--disable-gpu','--allow-file-access-from-files','about:blank'];A.proc=subprocess.Popen(E,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL);C=os.path.join(B,'DevToolsActivePort')
		for F in range(150):
			if os.path.exists(C)and os.path.getsize(C)>0:break
			time.sleep(.1)
		G=int(open(C).read().split()[0]);D=None
		for F in range(100):
			try:
				with urllib.request.urlopen('http://127.0.0.1:%d/json/list'%G,timeout=5)as H:I=json.loads(H.read().decode())
				D=next((A for A in I if A.get('type')=='page'),None)
				if D:break
			except OSError:pass
			time.sleep(.1)
		A.ws=WS(D['webSocketDebuggerUrl']);A.id=0;A.events=[]
	def call(A,method,params=None,timeout=90):
		C=method;A.id+=1;D=A.id;A.ws.send(json.dumps({'id':D,'method':C,'params':params or{}}));E=time.time()
		while time.time()-E<timeout:
			B=json.loads(A.ws.recv())
			if B.get('id')==D:
				if'error'in B:raise RuntimeError('%s: %s'%(C,B['error']))
				return B.get('result')or{}
			A.events.append(B)
		raise TimeoutError(C)
	def wait_event(A,name,timeout=30):
		B=time.time()
		while time.time()-B<timeout:
			if any(A.get('method')==name for A in A.events):return True
			A.ws.sock.settimeout(1)
			try:A.events.append(json.loads(A.ws.recv()))
			except(socket.timeout,TimeoutError):pass
			finally:A.ws.sock.settimeout(60)
		return False
	def drain(A,seconds):
		B=time.time();A.ws.sock.settimeout(.3)
		while time.time()-B<seconds:
			try:A.events.append(json.loads(A.ws.recv()))
			except(socket.timeout,TimeoutError):pass
		A.ws.sock.settimeout(60)
	def evaluate(A,expr):B=A.call('Runtime.evaluate',{'expression':expr,'returnByValue':True});return(B.get('result')or{}).get('value')
	def close(A):
		try:A.call('Browser.close',timeout=5)
		except Exception:pass
		A.ws.close()
		try:A.proc.wait(timeout=10)
		except subprocess.TimeoutExpired:A.proc.kill()
WS_BYTES=b' \t\r\n\x0c\x00'
DELIM=b'()<>[]{}/%'
class Ref(tuple):0
class Name(str):0
class Op(str):0
class Lexer:
	def __init__(A,data,pos=0):A.d=data;A.p=pos
	def skip_ws(A):
		B=A.d
		while A.p<len(B):
			C=B[A.p:A.p+1]
			if C in(b' ',b'\t',b'\r',b'\n',b'\x0c',b'\x00'):A.p+=1
			elif C==b'%':
				while A.p<len(B)and B[A.p:A.p+1]not in(b'\r',b'\n'):A.p+=1
			else:break
	def token(A):
		A.skip_ws();B=A.d
		if A.p>=len(B):return
		C=B[A.p:A.p+1]
		if C==b'<'and B[A.p:A.p+2]==b'<<':A.p+=2;return'<<'
		if C==b'>'and B[A.p:A.p+2]==b'>>':A.p+=2;return'>>'
		if C in(b'[',b']',b'{',b'}'):A.p+=1;return C.decode()
		if C==b'/':
			D=A.p+1;A.p=D
			while A.p<len(B)and B[A.p:A.p+1]not in WS_BYTES and B[A.p:A.p+1]not in DELIM:A.p+=1
			E=B[D:A.p];E=re.sub(b'#([0-9A-Fa-f]{2})',lambda m:bytes([int(m.group(1),16)]),E);return Name(E.decode('latin-1'))
		if C==b'(':return A._literal()
		if C==b'<':
			H=B.index(b'>',A.p);F=re.sub(b'\\s',b'',B[A.p+1:H])
			if len(F)%2:F+=b'0'
			A.p=H+1;return bytes.fromhex(F.decode())
		D=A.p
		while A.p<len(B)and B[A.p:A.p+1]not in WS_BYTES and B[A.p:A.p+1]not in DELIM:A.p+=1
		if A.p==D:A.p+=1;return Op(B[D:A.p].decode('latin-1'))
		G=B[D:A.p]
		try:return int(G)
		except ValueError:
			try:return float(G)
			except ValueError:return Op(G.decode('latin-1'))
	def _literal(A):
		D=A.d;A.p+=1;B=bytearray();F=1;G={b'n':10,b'r':13,b't':9,b'b':8,b'f':12,b'(':40,b')':41,b'\\':92}
		while A.p<len(D):
			C=D[A.p:A.p+1]
			if C==b'\\':
				E=D[A.p+1:A.p+2]
				if E in G:B.append(G[E]);A.p+=2
				elif E in(b'\r',b'\n'):
					A.p+=2
					if E==b'\r'and D[A.p:A.p+1]==b'\n':A.p+=1
				elif re.match(b'[0-7]',E):H=re.match(b'[0-7]{1,3}',D[A.p+1:A.p+4]);B.append(int(H.group(0),8)&255);A.p+=1+len(H.group(0))
				else:A.p+=1
			elif C==b'(':F+=1;B+=C;A.p+=1
			elif C==b')':
				F-=1;A.p+=1
				if F==0:break
				B+=C
			else:B+=C;A.p+=1
		return bytes(B)
	def obj(A,tok=None):
		C=A.token()if tok is None else tok
		if C=='<<':
			D={}
			while True:
				B=A.token()
				if B=='>>'or B is None:return D
				D[B]=A.obj()
		if C=='[':
			E=[]
			while True:
				B=A.token()
				if B==']'or B is None:return E
				E.append(A.obj(B))
		if isinstance(C,int):
			G=A.p;F=A.token()
			if isinstance(F,int):
				H=A.token()
				if H=='R':return Ref((C,F))
			A.p=G
		return C
class PDF:
	def __init__(A,data):
		A.d=data;A.offsets={}
		for B in re.finditer(b'(?<![0-9])(\\d+)\\s+(\\d+)\\s+obj\\b',data):A.offsets[int(B.group(1))]=B.end()
		A.cache={}
	def get(A,ref):
		F=ref
		if isinstance(F,Ref):
			E=F[0]
			if E not in A.cache:
				D=Lexer(A.d,A.offsets[E]);C=D.obj()
				if isinstance(C,dict):
					D.skip_ws()
					if A.d[D.p:D.p+6]==b'stream':
						B=D.p+6
						if A.d[B:B+2]==b'\r\n':B+=2
						elif A.d[B:B+1]in(b'\n',b'\r'):B+=1
						G=A.get(C.get('Length'));H=A.d[B:B+G]if isinstance(G,int)else A.d[B:A.d.index(b'endstream',B)];C=dict(C);C['__stream__']=H
				A.cache[E]=C
			return A.cache[E]
		return F
	def stream(C,o):
		o=C.get(o);B=o.get('__stream__',b'');A=C.get(o.get('Filter'));D=A if isinstance(A,list)else[A]if A else[]
		for E in D:
			if E=='FlateDecode':B=zlib.decompress(B)
		return B
	def pages(A):
		B=next(A.get(Ref((B,0)))for B in A.offsets if isinstance(A.get(Ref((B,0))),dict)and A.get(Ref((B,0))).get('Type')=='Catalog');C=[]
		def D(node,inherited):
			E=inherited;B=node;B=A.get(B);F=B.get('Resources',E.get('Resources'));G=B.get('MediaBox',E.get('MediaBox'))
			if B.get('Type')=='Pages':
				for H in A.get(B.get('Kids'))or[]:D(H,{'Resources':F,'MediaBox':G})
			else:C.append({'node':B,'Resources':A.get(F)or{},'MediaBox':[A.get(B)for B in A.get(G)]})
		D(B.get('Pages'),{});return C
def _cmap(data):
	B={};H=data.decode('latin-1')
	for C in re.findall('beginbfchar(.*?)endbfchar',H,re.S):
		for(D,E)in re.findall('<([0-9A-Fa-f]+)>\\s*<([0-9A-Fa-f]+)>',C):B[int(D,16)]=bytes.fromhex(E).decode('utf-16-be','replace')
	for C in re.findall('beginbfrange(.*?)endbfrange',H,re.S):
		for(D,E,F)in re.findall('<([0-9A-Fa-f]+)>\\s*<([0-9A-Fa-f]+)>\\s*(<[0-9A-Fa-f]+>|\\[[^\\]]*\\])',C):
			G,J=int(D,16),int(E,16)
			if F.startswith('['):
				K=re.findall('<([0-9A-Fa-f]+)>',F)
				for(A,L)in enumerate(K):B[G+A]=bytes.fromhex(L).decode('utf-16-be','replace')
			else:
				I=int(F[1:-1],16)
				for A in range(J-G+1):B[G+A]=chr(I+A)if I+A<1114112 else''
	return B
class Font:
	def __init__(A,pdf,fd):
		C=fd;B=pdf;C=B.get(C)or{};A.two_byte=C.get('Subtype')=='Type0';M=C.get('ToUnicode');A.cmap=_cmap(B.stream(M))if M else{};A.widths={};A.dw=1e3;A.scale=.001;A.asc,A.desc=.9,-.22;E=None
		if A.two_byte:
			I=B.get((B.get(C.get('DescendantFonts'))or[{}])[0]);A.dw=float(I.get('DW',1000));F=B.get(I.get('W'))or[];D=0
			while D<len(F):
				N=B.get(F[D]);J=B.get(F[D+1])if D+1<len(F)else None
				if isinstance(J,list):
					for(G,H)in enumerate(J):A.widths[N+G]=float(B.get(H))
					D+=2
				else:
					P,H=J,B.get(F[D+2])
					for G in range(N,P+1):A.widths[G]=float(H)
					D+=3
			E=B.get(I.get('FontDescriptor'))
		else:
			Q=C.get('FirstChar',0)
			for(G,H)in enumerate(B.get(C.get('Widths'))or[]):A.widths[Q+G]=float(B.get(H))
			O=B.get(C.get('FontMatrix'))
			if O:A.scale=float(B.get(O[0]))
			E=B.get(C.get('FontDescriptor'))
		if isinstance(E,dict):
			K,L=E.get('Ascent'),E.get('Descent')
			if isinstance(K,(int,float))and K:A.asc=K/1e3
			if isinstance(L,(int,float))and L:A.desc=L/1e3
	def codes(A,b):
		if A.two_byte:return[b[A]<<8|b[A+1]for A in range(0,len(b)-1,2)]
		return list(b)
	def text(A,code):
		B=code
		if B in A.cmap:return A.cmap[B]
		return''if A.two_byte else chr(B)
	def width(A,code):return A.widths.get(code,A.dw if A.two_byte else 5e2)*A.scale
def _mul(m1,m2):E,F,G,H,I,J=m1;A,B,C,D,K,L=m2;return E*A+F*C,E*B+F*D,G*A+H*C,G*B+H*D,I*A+J*C+K,I*B+J*D+L
def _pt(m,x,y):return m[0]*x+m[2]*y+m[4],m[1]*x+m[3]*y+m[5]
def page_runs(pdf,page):
	A=page;C=pdf;R=float(A['MediaBox'][3])-float(A['MediaBox'][1]);B=C.get(A['node'].get('Contents'));E=B if isinstance(B,list)else[B];F=b'\n'.join(C.stream(A)for A in E if A is not None);Z=[];D={}
	def l(res,name):
		A=id(res),name
		if A not in D:B=(C.get(res.get('Font'))or{}).get(name);D[A]=Font(C,B)if B else None
		return D[A]
	def a(data,res,ctm0):
		T=res;S=data;J=Lexer(S);K,r=[],[];G={'ctm':ctm0};U=[];D=E=1,0,0,1,0,0;F,I,b,c,V,L,W=None,1.,.0,.0,1.,.0,.0;M=[]
		while True:
			H=J.token()
			if H is None:break
			if H in('<<','['):K.append(J.obj(H));continue
			if not isinstance(H,Op)or H in('true','false','null'):K.append(H);continue
			A=str(H);B=K;K=[]
			if A=='q':U.append(dict(G))
			elif A=='Q':G=U.pop()if U else G
			elif A=='cm':G['ctm']=_mul(tuple(float(A)for A in B[-6:]),G['ctm'])
			elif A=='BT':D=E=1,0,0,1,0,0
			elif A=='Tf':F,I=l(T,B[-2]),float(B[-1])
			elif A=='Tm':D=E=tuple(float(A)for A in B[-6:])
			elif A in('Td','TD'):
				m,d=float(B[-2]),float(B[-1])
				if A=='TD':L=-d
				D=E=_mul((1,0,0,1,m,d),E)
			elif A=='T*':D=E=_mul((1,0,0,1,0,-L),E)
			elif A=='TL':L=float(B[-1])
			elif A=='Tc':b=float(B[-1])
			elif A=='Tw':c=float(B[-1])
			elif A=='Tz':V=float(B[-1])/1e2
			elif A=='Ts':W=float(B[-1])
			elif A in('BMC','BDC'):n=B[0]if B else'';M.append(n)
			elif A=='EMC':
				if M:M.pop()
			elif A=='Do'and B:
				X=(C.get(T.get('XObject'))or{}).get(B[-1]);N=C.get(X)if X else None
				if isinstance(N,dict)and N.get('Subtype')=='Form':o=tuple(float(C.get(A))for A in C.get(N.get('Matrix'))or[1,0,0,1,0,0]);a(C.stream(X),C.get(N.get('Resources'))or T,_mul(o,G['ctm']))
			elif A in('Tj','TJ',"'",'"'):
				if A in("'",'"'):D=E=_mul((1,0,0,1,0,-L),E)
				e=B[-1]if A=='TJ'else[B[-1]]
				if F is None or not isinstance(e,list):continue
				f,O=[],.0
				for P in e:
					if isinstance(P,(int,float)):O-=P/1e3*I*V
					elif isinstance(P,bytes):
						for Y in F.codes(P):
							f.append(F.text(Y));g=F.width(Y)*I+b
							if not F.two_byte and Y==32:g+=c
							O+=g*V
				Q=''.join(f)
				if'ReversedChars'in M:Q=Q[::-1]
				p=_mul(D,G['ctm']);q=W+F.desc*I,W+F.asc*I;h=[_pt(p,A,B)for A in(0,O)for B in q];i=[A[0]for A in h];j=[A[1]for A in h]
				if Q.strip():Z.append({'text':Q,'x0':min(i),'x1':max(i),'top':R-max(j),'bottom':R-min(j)})
				D=_mul((1,0,0,1,O,0),D)
			elif A=='BI':k=S.find(b'EI',J.p);J.p=k+2 if k>=0 else len(S)
	a(F,A['Resources'],(1,0,0,1,0,0));return Z,R
def pdf_layout(pdf_bytes):
	B=PDF(pdf_bytes);C=[]
	for D in B.pages():E,F=page_runs(B,D);A=[float(A)for A in D['MediaBox']];C.append({'size':(round(A[2]-A[0]),round(A[3]-A[1])),'runs':E})
	return C
def _ns(s):s=re.sub('[\\s\\u200e\\u200f\\u202a-\\u202e\\u2066-\\u2069]','',s or'');return s.replace('"','״').replace('״','״').replace("'",'׳')
def lines_of(runs,tol=2.):
	C=[]
	for B in sorted(runs,key=lambda r:(r['bottom'],-r['x1'])):
		for A in C:
			if abs(A['bottom']-B['bottom'])<=tol:A['runs'].append(B);A['top']=min(A['top'],B['top']);break
		else:C.append({'bottom':B['bottom'],'top':B['top'],'runs':[B]})
	for A in C:D=sorted(A['runs'],key=lambda r:-r['x1']);A['rtl']=''.join(A['text']for A in D);A['ltr']=''.join(A['text']for A in reversed(D));A['x0']=min(A['x0']for A in A['runs']);A['x1']=max(A['x1']for A in A['runs'])
	return C
_LTR_RUN=re.compile('[A-Za-z0-9]+')
def is_band_line(ln,marker_ns):
	B=marker_ns;D=_LTR_RUN.sub(lambda m:m.group(0)[::-1],ln['rtl'])
	for E in(ln['rtl'],ln['ltr'],D):
		C=_ns(E)
		if len(C)>=12 and C in B:return True
	A=[_ns(A['text'])for A in ln['runs']if len(_ns(A['text']))>=2];return bool(A)and sum(map(len,A))>=20 and all(A in B for A in A)
def analyse(layout,marker,headings=HEADINGS+EN_HEADINGS,appendix_titles=APPENDIX_TITLES):
	G=layout;J=_ns(marker);U={_ns(A):A for A in headings};V=[_ns(A)for A in appendix_titles];A={'pages':len(G),'page_sizes':sorted({tuple(A['size'])for A in G}),'appendix_page':None,'band_lines':0,'overlaps':[],'heading_overlaps':[],'first_page_runs':len(G[0]['runs'])if G else 0,'band_on_pages':0}
	for(L,W)in enumerate(G,1):
		K=lines_of(W['runs'])
		if A['appendix_page']is None and any(B in _ns(A['rtl'])or B in _ns(A['ltr'])for A in K for B in V):A['appendix_page']=L
		C=[]
		for B in K:
			H=[A for A in B['runs']if _ns(A['text'])and _ns(A['text'])in J]
			if not any(len(_ns(A['text']))>=2 for A in H):continue
			O=sorted(H,key=lambda r:-r['x1']);M={'runs':H,'rtl':''.join(A['text']for A in O),'ltr':''.join(A['text']for A in reversed(O)),'top':min(A['top']for A in H),'bottom':max(A['bottom']for A in H)}
			if is_band_line(M,J):M['runs']=[A for A in B['runs']if _ns(A['text'])in J];C.append(M)
		N=True
		while N and C:
			N=False;X={id(B)for A in C for B in A['runs']}
			for B in K:
				E=[A for A in B['runs']if _ns(A['text'])]
				if not E or any(id(A)in X for A in E):continue
				if not all(_ns(A['text'])in J for A in E)or sum(len(_ns(A['text']))for A in E)<4:continue
				P,Q=min(A['top']for A in E),max(A['bottom']for A in E)
				if any(P-A['bottom']<=6 and A['top']-Q<=6 for A in C):C.append({'runs':E,'rtl':B['rtl'],'ltr':B['ltr'],'top':P,'bottom':Q});N=True
		A['band_lines']+=len(C)
		if C:A['band_on_pages']+=1
		D=[]
		for B in sorted(C,key=lambda x:x['top']):
			if D and B['top']-D[-1][1]<=6:D[-1][1]=max(D[-1][1],B['bottom'])
			else:D.append([B['top'],B['bottom']])
		D=[(A-BAND_PAD,B+BAND_PAD)for(A,B)in D];Y={id(B)for A in C for B in A['runs']}
		for B in K:
			for F in B['runs']:
				if id(F)in Y:continue
				for(R,S)in D:
					Z=min(F['bottom'],S)-max(F['top'],R)
					if Z>=OVERLAP_MIN:
						a={'page':L,'text':F['text'][:60],'top':round(F['top'],1),'bottom':round(F['bottom'],1),'band':[round(R,1),round(S,1)]};A['overlaps'].append(a);T=_ns(B['rtl'])
						for(I,b)in U.items():
							if I and(I==T or I==_ns(F['text'])or len(I)>6 and I in T):A['heading_overlaps'].append({'page':L,'heading':b});break
						break
	A['body_pages']=A['appendix_page']-1 if A['appendix_page']else A['pages'];A['appendix_pages']=A['pages']-A['body_pages'];return A
JS_INFO="(function(){\n const c=document.body?document.body.cloneNode(true):null;\n if(c) c.querySelectorAll('script,style,template').forEach(x=>x.remove());\n const full=c?c.textContent.replace(/\\s+/g,' ').trim():'';\n return JSON.stringify({title:document.title, dom_text_chars:full.length,\n   visible_text_chars:(document.body&&document.body.innerText||'').length, text:full.slice(0,200000)});\n})()"
def run_check(html_path,out_dir,marker,browser=None,markers=None,twice=False,body_limit=BODY_PAGE_LIMIT):
	J=markers;I=marker;H=out_dir;D=body_limit;E=browser or find_browser()
	if not E:return{'verdict':'NO_BROWSER','exit':3}
	os.makedirs(H,exist_ok=True);K=tempfile.mkdtemp(prefix='areo_rc_');L=Path(os.path.abspath(html_path)).as_uri();A={'browser':os.path.basename(E),'url_scheme':L[:7]};C=None
	try:
		C=Browser(E,K)
		for R in('Network.enable','Runtime.enable','Page.enable','Log.enable'):C.call(R)
		C.call('Page.navigate',{'url':L});C.wait_event('Page.loadEventFired',30);C.drain(1.5);M=json.loads(C.evaluate(JS_INFO)or'{}');S=M.pop('text','');A.update(M);T=J if J is not None else DEFAULT_MARKERS;A['markers_missing']=[A for A in T if A not in S];N=[A['params']['request']['url']for A in C.events if A.get('method')=='Network.requestWillBeSent'];A['requests_total']=len(N);A['external_requests']=[A[:120]for A in N if not re.match('^(file|data|blob|about|chrome|devtools):',A)];A['js_exceptions']=[((A['params'].get('exceptionDetails')or{}).get('exception')or{}).get('description')or(A['params'].get('exceptionDetails')or{}).get('text')for A in C.events if A.get('method')=='Runtime.exceptionThrown'];O=base64.b64decode(C.call('Page.printToPDF',{'preferCSSPageSize':True,'printBackground':True,'displayHeaderFooter':False},timeout=120)['data']);P=os.path.join(H,'render_check.pdf')
		with open(P,'wb')as U:U.write(O)
		A['pdf']=P;V=analyse(pdf_layout(O),I);A.update(V)
		if twice:C.call('Page.reload',{'ignoreCache':False});C.drain(2.5);W=base64.b64decode(C.call('Page.printToPDF',{'preferCSSPageSize':True,'printBackground':True},timeout=120)['data']);F=analyse(pdf_layout(W),I);A['second_print']={'pages':F['pages'],'body_pages':F['body_pages'],'first_page_runs':F['first_page_runs']}
	finally:
		if C:C.close()
		shutil.rmtree(K,ignore_errors=True)
	B=[]
	if A.get('dom_text_chars',0)<500:B.append('blank')
	if not str(A.get('title')or'').startswith('Areo Workspace'):B.append('title')
	if A.get('markers_missing'):B.append('markers')
	if A.get('js_exceptions'):B.append('js_exceptions')
	if A.get('external_requests'):B.append('external_requests')
	if A.get('page_sizes')and any(abs(A-A4[0])>2 or abs(B-A4[1])>2 for(A,B)in A['page_sizes']):B.append('not_a4')
	if not A.get('first_page_runs'):B.append('first_page_blank')
	if A.get('band_lines',0)==0:B.append('no_band')
	if A.get('overlaps'):B.append('band_overlap')
	G=A.get('second_print')
	if G and(G['pages']!=A['pages']or not G['first_page_runs']):B.append('second_print_differs')
	Q=A.get('body_pages',0)>D
	if Q:B.append('body_pages>%d'%D)
	A['fails']=B;A['verdict']='PASS'if not B else'FAIL';A['exit']=0 if not B else 2 if Q and B==['body_pages>%d'%D]else 1;return A
def main(argv=None):
	B=parser('Areo risk report render check',out_required=True,out_help='תיקיית הפלט (העמוד, render_check.json). לעולם לא תיקיית מקור של הלקוח');B.add_argument('--template');B.add_argument('--register');B.add_argument('--html');B.add_argument('--browser');B.add_argument('--marker',help='טקסט הסימון; ברירת מחדל: נגזר מהמרשם');B.add_argument('--twice',action='store_true');B.add_argument('--kind',choices=sorted(KINDS),help='risk (ברירת מחדל) או entity: מציין, סמנים וגבול עמודים');B.add_argument('--body-limit',type=int);B.add_argument('--placeholder',help='בדוח חקר ישות: __ENTITY_DATA__ (או --kind entity)');B.add_argument('--markers',help='מחרוזות חובה מופרדות בפסיק');A=B.parse_args(argv);sys.stdout.reconfigure(encoding='utf-8');J=A.kind or('entity'if A.placeholder==ENTITY_PLACEHOLDER else'risk');G=KINDS[J];A.placeholder=A.placeholder or G['placeholder'];A.body_limit=A.body_limit if A.body_limit is not None else G['body_limit'];F=[A.strip()for A in A.markers.split(',')]if A.markers else G['markers'];K=[A for A in(A.template,A.register,A.html)if A];guard_out(A.out,K)
	if A.template and A.register:
		with open(long_path(A.template),encoding='utf-8')as D:O=D.read()
		with open(long_path(A.register),encoding='utf-8')as D:E=json.load(D)
		L=static_checks(O);H=build_report(O,E,A.placeholder);os.makedirs(A.out,exist_ok=True);I=guard_out(os.path.join(A.out,'Areo Workspace - %s.html'%G['name']),K)
		with open(I,'w',encoding='utf-8')as D:D.write(H)
		P=A.marker or band_text_from_register(E);F=F if A.markers else markers_for(J,lang_of(E))
	elif A.html:
		I=A.html
		with open(long_path(I),encoding='utf-8')as D:H=D.read()
		L=static_checks(H);M=re.search('const DATA = (\\{.*?\\});\\n',H,re.S);E=json.loads(M.group(1).replace('<\\/','</'))if M else{};P=A.marker or(band_text_from_register(E)if M else HE_DRAFT);F=F if A.markers else markers_for(J,lang_of(E))
	else:B.error('--template ו---register, או --html')
	C=run_check(I,A.out,P,browser=A.browser,markers=F,twice=A.twice,body_limit=A.body_limit);C['static_problems']=L
	if L and C.get('verdict')=='PASS':C['verdict'],C['exit']='FAIL',1;C['fails']=C.get('fails',[])+['static']
	N={A:B for(A,B)in C.items()if A not in('overlaps',)};N['overlaps_count']=len(C.get('overlaps')or[]);N['overlaps_sample']=(C.get('overlaps')or[])[:8];print(json.dumps(N,ensure_ascii=False,indent=1))
	with open(guard_out(os.path.join(A.out,'render_check.json'),K),'w',encoding='utf-8')as D:json.dump(C,D,ensure_ascii=False,indent=1)
	return C['exit']
if __name__=='__main__':sys.exit(run(main))
