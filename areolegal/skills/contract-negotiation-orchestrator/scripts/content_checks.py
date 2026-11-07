#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (c) Areo. All rights reserved. Licensed under the terms at https://areo.co.il/legal/terms
'בדיקות התוכן של הסבב: מה שהשער בודק בנוסח שמתקבל אחרי כל התיקונים, ובהכרעות.'
import argparse,io,json,os,re,sys,zipfile
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
import areo_lib
from lxml import etree
import common.docx_tracked as dt,playbook_map as PM
W=dt.W
HERE=os.path.dirname(os.path.abspath(__file__))
HEB=re.compile('[\u0590-\u05ff]')
LAT=re.compile('[A-Za-z]')
NEUTRALIZERS=['יגברו','מכריעים','כמי שוויתר','תתיישן','לחלט','לקזז','שלטענתה','זנח','לא יושעו','לאלתר','ללא ספירה','הסעד היחיד','incorporated by reference','conclusive','sole and exclusive remedy','deemed to have waived','shall prevail']
TBA=re.compile('יוסכ(?:ם|מו)(?![א-ת])|to be agreed|\\bTBA\\b|to be determined',re.I)
REPRESENT=re.compile('\\b(?:represents?|warrants?|certif(?:y|ies)|confirms?)(?:\\s+and\\s+\\w+)?\\s+that\\b|\\bhereby\\s+(?:represents?|warrants?|confirms?|certif(?:y|ies))\\b|\\bshall\\s+comply\\s+with\\b|מצהיר(?:ה|ים)?\\s+(?:כי|ש|בזאת)|מאשר(?:ת|ים)?\\s+בזאת|מתחייב(?:ת|ים)?\\s+לעמוד',re.I)
REPRESENT_BUBBLE=re.compile('\\bwe\\s+(?:represent|warrant|confirm|certify)\\b|אנו\\s+(?:מצהירים|מאשרים)|החברה\\s+(?:מצהירה|מאשרת)',re.I)
CONFLICT_REP=re.compile('אין הסכם סותר|לא קיים הסכם (?:ה)?סותר|החברה גילתה|גילתה לצד|no conflicting agreement|has disclosed|is not (?:a )?party to any (?:other )?agreement',re.I)
EXHAUST=re.compile('מצה(?:ה|ים) את|מבטל(?:ים)? כל הסכם|כל ההסכמות|entire agreement|supersedes? (?:all|any) prior',re.I)
PREVAILS=[re.compile('(?:הנספח|נספח|ההזמנה|הזמנת|הנוהל|נוהל|המדיניות|מדיניות|תנאי(?:ם)? (?:ה)?כללי|מסמך)[^.;]{0,70}(?:יגבר|יגברו|תגבר|תגברנה|יכריע|יכריעו)(?![^.;]{0,25}הסכם זה)'),re.compile('(?:annex|schedule|exhibit|appendix|order|statement of work|sow|policy|terms and conditions|purchase order)[^.;]{0,90}shall (?:prevail|govern|control)(?![^.;]{0,25}(?:this|the) agreement shall prevail)',re.I)]
INCOTERMS=re.compile('\\b(EXW|FCA|FAS|FOB|CFR|CIF|CPT|CIP|DAP|DPU|DDP)\\b')
CURRENCY=re.compile('ש\\"ח|ש״ח|₪|\\bNIS\\b|\\bILS\\b|\\bUSD\\b|\\$|€|\\bEUR\\b|דולר|יורו|הצמדה|צמוד|מדד|indexation|\\bCPI\\b',re.I)
PRICE=re.compile('מחיר|מחירון|תעריף|תמורה|price|pricing|fee|tariff|rate card',re.I)
CONFORMING_ONLY=re.compile('^\\s*(?:conforming change|תיקון עקבי|שינוי עקבי|התאמה)\\s*[.]?\\s*$',re.I)
COMPLIANCE=re.compile('bribery|corruption|FCPA|anti-?bribery|sanction|boycott|export control|money laundering|AML\\b|שוחד|שחיתות|סנקציה|סנקציות|חרם|פיקוח על יצוא|יצוא בטחוני|הלבנת הון',re.I)
INTERNAL_HINT=re.compile("\\b(internal|our client|client wants|between us|do not share|don'?t share|we can accept|fallback|walk.?away|bottom line|can live with)\\b|פנימי|בינינו|הלקוח שלנו|הלקוח מוכן|אפשר לוותר|נוכל לוותר|מוכנים לוותר|עמדת נסיגה|לא להעביר|לא לשתף|נסתפק",re.I)
PARTY_LABELS=()
def party_labels(core):
	B=core;B=B if isinstance(B,dict)else{};E=[B.get('company_role_code')]+list(B.get('party_labels')or[])
	for C in B.get('contract_families')or[]:
		if isinstance(C,dict):E+=[C.get('company_role_code')]+list(C.get('party_labels')or[])
	D=[]
	for A in E:
		A=str(A or'').strip()
		if A and A.lower()not in('other','mutual')and A not in D:D+=[A]+(['ה'+A]if re.match('[א-ת]',A)else[])
	return D
EXT_REF_EN=re.compile("^(?:\\([^)]*\\))*(?:\\s*(?:,|and|or|to)\\s*\\d+(?:\\.\\d+)*(?:\\([^)]*\\))*)*\\s*(?:of|under|in)\\s+(?:the\\s+)?(?:[A-Z][\\w'’-]*\\s+){0,8}?(?:Act|Regulations?|Law|Directive|Code|Order|Ordinance|Rules|Statute|Convention|Agreement|Contract)\\b")
EXT_REF_HE=re.compile('^(?:\\([^)]*\\))*(?:\\s*(?:,|ו|או|עד)\\s*\\d+(?:\\.\\d+)*(?:\\([^)]*\\))*)*\\s*(?:ל|של\\s+|ב)?(?:חוק|תקנות|פקודת|פקודה|צו|כללי|הסכם ה(?!זה))')
REF_HE=re.compile('(?<![א-ת])(?:ב|ל|מ|ו|ש)?סעי(?:ף|פים)\\s+(\\d+(?:\\.\\d+){0,4})')
REF_EN=re.compile('\\b(?:Section|Clause|section|clause)s?\\s+(\\d+(?:\\.\\d+){0,4})')
ANNEX_HE=re.compile("(?<![א-ת])(?:ב|ל|מ|ו|ש)?נספח\\s+([א-ת]['׳]?|\\d+)(?![א-ת])")
ANNEX_EN=re.compile('\\b(?:Annex|Schedule|Exhibit|Appendix)\\s+([A-Z]|\\d+)\\b')
DEF_PATTERNS=[re.compile('\\(\\s*(?:להלן:?\\s*|the\\s+|hereinafter\\s+)?[\\"״“]([^\\"״”]{2,50})[\\"״”](?:\\s*(?:או|or)\\s*[\\"״“]([^\\"״”]{2,50})[\\"״”])?\\s*\\)'),re.compile('\\(להלן:?\\s*[\\"״“]([^\\"״”]{2,50})[\\"״”]'),re.compile('[\\"״“]([^\\"״”]{2,50})[\\"״”]\\s*(?:-|פירושו|פירושה|משמעו|משמעה|יהיה פירושו)'),re.compile('[\\"“]([A-Z][^\\"”]{1,50})[\\"”]\\s+(?:means|shall mean|has the meaning)'),re.compile('\\((?:the|hereinafter)?\\s*[\\"“]([A-Z][^\\"”]{1,50})[\\"”]\\)')]
def finding(out,code,message,where='',blocking=False):out.append({'code':code,'message':message,'where':where,'blocking':bool(blocking)})
def load(path):
	A=path
	if not A or not os.path.exists(A):return
	with io.open(A,encoding='utf-8')as B:return json.load(B)
def _roman(n):
	C=(10,'x'),(9,'ix'),(5,'v'),(4,'iv'),(1,'i');A=''
	for(B,D)in C:
		while n>=B:A,n=A+D,n-B
	return A
def _num_levels(path):
	try:
		with zipfile.ZipFile(path)as L:F=etree.fromstring(L.read('word/numbering.xml'))
	except(KeyError,OSError,zipfile.BadZipFile,etree.XMLSyntaxError):return{}
	G={}
	for B in F.iter(W+'abstractNum'):
		A={}
		for H in B.iter(W+'lvl'):
			def D(tag,dflt):A=H.find(W+tag);return A.get(W+'val')if A is not None and A.get(W+'val')is not None else dflt
			A[int(H.get(W+'ilvl')or 0)]=D('lvlText',''),D('numFmt','decimal'),int(D('start','1')or 1)
		G[B.get(W+'abstractNumId')]=A
	I={}
	for E in F.iter(W+'num'):
		B=E.find(W+'abstractNumId');A=dict(G.get(B.get(W+'val')if B is not None else None)or{})
		for J in E.iter(W+'lvlOverride'):
			K=J.find(W+'startOverride');C=int(J.get(W+'ilvl')or 0)
			if K is not None and C in A:A[C]=A[C][0],A[C][1],int(K.get(W+'val')or 1)
		I[E.get(W+'numId')]=A
	return I
HE_LETTERS='אבגדהוזחטיכלמנסעפצקרשת'
INTERNAL_AUTHORS=tuple(A for A in(dt.INTERNAL_AUTHOR,getattr(dt,'INTERNAL_AUTHOR_EN',None),'Internal, delete before sending')if A)
def _hebrew_numeral(n):
	A=''
	while n>=400:A,n=A+'ת',n-400
	for(B,C)in((300,'ש'),(200,'ר'),(100,'ק'),(90,'צ'),(80,'פ'),(70,'ע'),(60,'ס'),(50,'נ'),(40,'מ'),(30,'ל'),(20,'כ'),(10,'י')):
		if n>=B:A,n=A+C,n-B
	if n in(15,16):return A+('טו'if n==15 else'טז')
	if A.endswith('י')and n in(5,6):return A[:-1]+('טו'if n==5 else'טז')
	return A+(''if not n else HE_LETTERS[n-1])
def _fmt_num(n,fmt):
	A=fmt
	if A=='hebrew1'and n>0:return _hebrew_numeral(n)
	if A=='hebrew2'and n>0:return HE_LETTERS[(n-1)%22]*((n-1)//22+1)
	if A in('lowerLetter','upperLetter')and 0<n<=26:B=chr(96+n);return B.upper()if A=='upperLetter'else B
	if A in('lowerRoman','upperRoman'):C=_roman(n);return C.upper()if A=='upperRoman'else C
	return str(n)
def numbered_labels(path):
	h=dt.document_root(path);X=dt.body_paragraphs(h);Y=[dt.para_text(A).strip()for A in X];R,Z,D={},{},[];B,I,N,O=None,None,False,False;K={};i=re.compile('^(?:i|ii|iii|iv|v|vi|vii|viii|ix|x|xi|xii)$');j=_num_levels(path);a=re.compile('^\\(([a-z]{1,4})\\)\\s');k=re.compile('^(?:\\(([א-ת]{1,2})\\)|([א-ת]{1,2})[.)])\\s')
	def l(i):
		for B in Y[i+1:i+4]:
			A=a.match(B)
			if A:return A.group(1)
	for(b,m)in enumerate(X):
		S=Y[b];T=re.match('^(\\d+(?:\\.\\d+){0,4})[.)]?\\s',S)
		if T:D.append(T.group(1));B,I,N,O=T.group(1),None,False,True;R={A:B for(A,B)in R.items()if not A.startswith('under:')};K={};continue
		U=k.match(S)
		if U and B:D.append('%s(%s)'%(B,U.group(1)or U.group(2)));continue
		c=a.match(S)
		if c and B:
			L=c.group(1);d=bool(i.match(L))and not(L=='i'and I=='h'and l(b)!='ii')
			if d and I and not N:D.append('%s(%s)(%s)'%(B,I,L))
			else:I,N=L,d;D.append('%s(%s)'%(B,L))
			continue
		P=m.find(W+'pPr/'+W+'numPr');F=P.find(W+'numId')if P is not None else None;F=F.get(W+'val')if F is not None else None
		if P is not None and F not in(None,'0'):
			A=P.find(W+'ilvl');A=int(A.get(W+'val'))if A is not None else 0;V='under:%s:%s'%(B,F)if O and B else F;C=R.setdefault(V,[0]*9);M=j.get(F)or{};G=(M.get(A)or('','decimal',1))[0]
			for E in range(A):
				if C[E]==0 and(not G or'%%%d'%(E+1)in G):C[E]=(M.get(E)or('','decimal',1))[2]
			C[A]=C[A]+1 if C[A]else(M.get(A)or('','decimal',1))[2]
			for E in range(A+1,9):C[E]=0
			H=Z.setdefault(V,A)
			if A<H:H=Z[V]=A
			e=A-H
			if O and B and e<=1:Q,f=C[H],C[H+1]if H+1<9 else 0;g=(M.get(H)or('','decimal',1))[1];n='%s(%s)'%(B,_fmt_num(Q,g)if g not in('decimal','')else chr(96+Q)if 0<Q<=26 else Q);D.append(n+('(%s)'%_roman(f)if e==1 and f else''))
			else:
				if G and re.search('%\\d',G):J=re.sub('%(\\d)',lambda m:_fmt_num(C[int(m.group(1))-1],(M.get(int(m.group(1))-1)or('','decimal'))[1]),G).strip().rstrip('.)').lstrip('(')
				else:J='.'.join(str(A)for A in C[:A+1]if A)
				if A>0 and B and G and not any('%%%d'%(A+1)in G for A in range(A)):o=next((K[A]for A in range(A-1,-1,-1)if K.get(A)),B);J='%s(%s)'%(o,J)
				D.append(J);K[A]=J
				for E in range(A+1,9):K.pop(E,None)
				if A==0:B,I,N,O=J,None,False,False
		else:D.append(None)
	return D
PARTY_DEF=re.compile('\\(\\s*(?:להלן|ולהלן|hereinafter|the|הלן)?:?\\s*(?:referred to as\\s*)?(?:the\\s+)?[\\"״“\']([^\\"״”\']{2,40})[\\"״”\']\\s*\\)',re.I)
def document_sides(path,our_names=(),their_names=(),role_side=None):
	I=role_side;C=[A.strip()for A in dt.received_paragraphs(path)]
	try:E=next((A for(A,B)in enumerate(numbered_labels(path))if B),None)
	except Exception:E=None
	C=C[:max(E or 0,3)if E is not None else 15][:40];A=lambda s:re.sub('[\\s\\"״\'”“׳.,]+',' ',str(s or'')).strip().lower();P=[A(B)for B in our_names if B and len(A(B))>=3];Q=[A(B)for B in their_names if B and len(A(B))>=3];B=[]
	for(J,K)in enumerate(C):
		for L in PARTY_DEF.finditer(K):
			M=L.group(1).strip();F=I(M)if I else None
			if F=='mutual':F=None
			G=K[:L.start()];R=G if len(G.strip())>=3 else' '.join(C[max(0,J-2):J])+' '+G;B.append({'term':M,'side':F,'block':A(R)[-300:]})
	if not B:return{'ours':None,'basis':'no_party_definitions'}
	def N(d):
		if any(A in d['block']for A in P):return'ours'
		if any(A in d['block']for A in Q):return'theirs'
	S=[A for A in B if A['side']];D=next((A for A in B if N(A)=='ours'),None);O=next((A for A in B if N(A)=='theirs'),None)
	if D and D['side']:return{'ours':D['side'],'our_term':D['term'],'basis':'our_name'}
	if O:
		H=[A for A in S if A['term']!=O['term']]
		if len({A['side']for A in H})==1:return{'ours':H[0]['side'],'our_term':H[0]['term'],'basis':'other_party'}
	return{'ours':None,'basis':'names_not_found'}
PLACE_WORDS={'he':{'pre':'המבוא','after':'אחרי סעיף %s','in':'%s','sign':'החתימות'},'en':{'pre':'Preamble','after':'After clause %s','in':'%s','sign':'Signatures'}}
SIGN_RX=re.compile('ולראיה|על החתום|in witness whereof|signature',re.I)
def place_labels(path,lang='he',labels=None):
	D=labels;E=PLACE_WORDS['en'if str(lang or'').lower()[:2]=='en'else'he'];K=dt.document_root(path);L=[dt.para_text(A).strip()for A in dt.body_paragraphs(K)];D=D if D is not None else numbered_labels(path);B,C,G,F,H=[],None,False,None,False
	for(A,I)in zip(L,D):
		if I:C=I;B.append(None);H=0<len((A or'').strip())<=80 and not re.search('[.;:,]\\s*$',(A or'').strip())and not re.search('[.;:]\\s',(A or'').strip());continue
		if H and C and(A or'').strip()and not SIGN_RX.search(A or''):B.append(E['in']%C);continue
		H=False
		if C and SIGN_RX.search(A or''):G,F=True,None
		elif G and F is None and 8<=len(A or'')<=90 and'\t'not in A and not A.endswith(('.',':',','))and not re.search('_{3,}|\\.{3,}|…',A):J=A.split(' - ')[-1].strip();F=J if len(J)>=6 else A
		if C is None:B.append(E['pre'])
		elif G:B.append(F or E['sign'])
		else:B.append(E['after']%C)
	return B
SCHEDULE_HEAD=re.compile('^(Schedule|SCHEDULE|Annex|ANNEX|Appendix|APPENDIX|Exhibit|EXHIBIT|Attachment|ATTACHMENT)\\s+([A-Z]|\\d+(?:\\.\\d+)*|[IVX]+)\\b'),re.compile("^(תוספת|נספח)\\s+([א-ת]['׳]?|\\d+(?:\\.\\d+)*)(?![א-ת])")
def _body_restart(paras,labels):
	G=paras;A=labels
	if not A:return
	D=next((A for(A,B)in enumerate(G)if _schedule_head((B or'').strip())),None)
	if D is None or any(A[B]for B in range(min(D,len(A)))):return
	H,E=None,0;B=D
	while B<len(A):
		if A[B]=='1':
			F,C=0,B
			while C<len(A)and not _schedule_head((G[C]or'').strip()):
				if A[C]and re.match('^\\d+$',str(A[C])):F+=1
				C+=1
			if F>E:H,E=B,F
			B=C
		else:B+=1
	return H if E>=3 else None
def _schedule_head(s):
	if len(s)<=80 and not s.endswith('.')and not re.search('(\\t|\\.{3,}|…)\\s*\\d+$',s):return SCHEDULE_HEAD[0].match(s)or SCHEDULE_HEAD[1].match(s)
def schedule_of_paragraphs(paras,labels=None):
	C=paras;D,B=[],None;E=_body_restart(C,labels)
	for(F,G)in enumerate(C):
		H=(G or'').strip()
		if E is not None and F==E:B=None
		A=_schedule_head(H)
		if A:B=A.group(1)[:1].upper()+A.group(1)[1:].lower()if A.group(1)[0].isascii()else A.group(1),A.group(2).replace('׳',"'")
		D.append(B)
	return D
def annex_names(paras):
	A=set()
	for D in paras:
		B=D.strip();C=re.match("^נספח\\s+([א-ת]['׳]?|\\d+)(?![א-ת])",B)or re.match('^(?:Annex|Schedule|Exhibit|Appendix)\\s+([A-Z]|\\d+)\\b',B)
		if C:A.add(C.group(1).replace('׳',"'"))
	return A
def hidden_scan(path):
	E=[]
	with zipfile.ZipFile(path)as F:
		H=F.namelist()
		for A in H:
			if not re.match('^word/(document|header\\d*|footer\\d*|footnotes|endnotes|comments)\\.xml$',A):continue
			N=etree.fromstring(F.read(A))
			for(O,P)in enumerate(N.iter(W+'p')):
				for I in P.iter(W+'r'):
					C=I.find(W+'rPr')
					if C is None:continue
					J=''.join(A.text or''for A in I.iter(W+'t',W+'delText'))
					if not J.strip():continue
					B=[]
					for K in('vanish','specVanish','webHidden'):
						L=C.find(W+K)
						if L is not None and L.get(W+'val')not in('0','false'):B.append(K)
					M=C.find(W+'color')
					if M is not None and str(M.get(W+'val','')).upper()in('FFFFFF','FEFEFE','FDFDFD','FCFCFC'):B.append('color')
					G=C.find(W+'sz')
					if G is not None and str(G.get(W+'val','99')).isdigit()and int(G.get(W+'val'))<=2:B.append('font_size')
					if B:E.append({'part':A,'paragraph':O,'text':J,'how':','.join(B)})
		for A in H:
			if A.startswith('customXml/item')and A.endswith('.xml')or A=='docProps/custom.xml':
				D=re.sub('<[^>]+>',' ',F.read(A).decode('utf-8','ignore'));D=re.sub('\\s+',' ',D).strip()
				if len(D)>20:E.append({'part':A,'paragraph':None,'text':D[:300],'how':'properties'})
	return E
def comment_info(path):
	with zipfile.ZipFile(path)as D:
		G=D.namelist()
		if'word/comments.xml'not in G:return[]
		K=etree.fromstring(D.read('word/comments.xml'));H=etree.fromstring(D.read('word/commentsExtended.xml'))if'word/commentsExtended.xml'in G else None
	L='{http://schemas.microsoft.com/office/word/2010/wordml}';C='{http://schemas.microsoft.com/office/word/2012/wordml}';I={}
	if H is not None:
		for E in H.iter(C+'commentEx'):
			if E.get(C+'paraIdParent'):I[E.get(C+'paraId')]=E.get(C+'paraIdParent')
	B=[]
	for A in K.iter(W+'comment'):F=list(A.iter(W+'p'));J=F[-1].get(L+'paraId')if F else None;B.append({'id':A.get(W+'id'),'author':A.get(W+'author')or'','paraId':J,'date':A.get(W+'date'),'text':' '.join(''.join(A.text or''for A in A.iter(W+'t'))for A in F).strip(),'parent':I.get(J)})
	M={A['parent']for A in B if A.get('parent')}
	for(N,A)in enumerate(B):A['has_reply']=A['paraId']in M or bool(A.get('parent'))and any(B.get('parent')==A['parent']and B['author']!=A['author']and(C>N or B.get('date')and A.get('date')and B['date']>A['date'])for(C,B)in enumerate(B))
	return B
def our_texts(decisions):
	B=[]
	for A in decisions or():
		for C in('new_text','new','text'):
			if A.get(C):B.append((A,A[C]))
	return B
def run_checks(work,received,decisions,state=None,core=None,manifest=None,profile=None,mode=None):
	l=work;Q=received;O=core;L=mode;D=state;C=decisions;B=[];D=D or{};U=D.get('meta')or{};C=C or[];F=dt.accept_all(l);E=dt.received_paragraphs(Q);m='\n'.join(F);AL=numbered_labels(l);A1={A for A in AL if A};AM=annex_names(F);n={A.get('para')for A in C if A.get('para')is not None}|{A.get('after_para')for A in C if A.get('after_para')is not None};c={}
	for A in C:
		if A.get('para')is not None:c.setdefault(A['para'],[]).append(A)
	for(G,J)in enumerate(F):
		for(P,d)in((REF_HE,'sec'),(REF_EN,'sec'),(ANNEX_HE,'annex'),(ANNEX_EN,'annex')):
			for M in P.finditer(J):
				o=M.group(1).replace('׳',"'");A2=J[M.end():]+' '+(F[G+1]if G+1<len(F)else'')
				if d=='sec'and(EXT_REF_EN.match(A2)or EXT_REF_HE.match(A2)):continue
				e=o in A1 if d=='sec'else o in AM
				if d=='sec'and not A1:e=True
				if not e:AN=any(M.group(0)in A for(B,A)in our_texts(C));finding(B,'CON_REF_MISSING','הפניה ל%s %s, ואין לה יעד בנוסח המתקבל'%('סעיף'if d=='sec'else'נספח',o),'פסקה %d'%G,blocking=AN)
	A3={}
	for(G,J)in enumerate(F):
		for P in DEF_PATTERNS:
			for M in P.finditer(J):
				for A4 in M.groups():
					if A4:A3.setdefault(A4.strip(),G)
	for(R,p)in A3.items():
		A5=R[1:]if R.startswith('ה')and len(R)>3 else R
		if A5!=R:q=re.compile('(?<![א-ת])[ולבכמש]{0,2}ה?'+re.escape(A5)+'(?![א-ת])')
		else:q=re.compile(re.escape(R))
		f=[A for(A,B)in enumerate(F)if q.search(B)]
		if f and f[0]<p:finding(B,'CON_TERM_BEFORE_DEF','המונח "%s" משמש לפני שהוגדר'%R,'פסקה %d'%f[0])
		if len([A for A in f if A!=p])==0 and len(q.findall(m))<=1:finding(B,'CON_TERM_UNUSED','המונח "%s" מוגדר ואינו בשימוש'%R,'פסקה %d'%p)
	for(A,H)in our_texts(C):
		if TBA.search(H):finding(B,'CON_TBA','בנוסח שהכנסנו נשאר "%s": אין הסכמה על עניין שנשאר להסכמה'%TBA.search(H).group(0),A.get('id'),blocking=True)
	Y=next((A for(A,B)in enumerate(F)if re.match('^\\s*(?:נספח|Annex|Schedule|Exhibit|Appendix)\\s',B)),None)
	if Y is not None:
		for A in C:
			K=A.get('para')
			if K is None or K>=Y or K>=len(F):continue
			AO=set(re.findall('[\\"״“]([^\\"״”]{2,40})[\\"״”]',F[K]))|set(re.findall('\\d+(?:\\.\\d+)+',F[K]))
			for r in range(Y,len(F)):
				if r not in n and any(A in F[r]for A in AO):finding(B,'CON_ANNEX_SHARED','פסקה בנספח חולקת מונח או מספר עם הכרעה %s: לבדוק שהיא עקבית'%A.get('id'),'פסקה %d'%r)
	for N in D.get('client_answers')or[]:
		if not N.get('status')or N.get('status')=='applied'and not N.get('clause_ids'):finding(B,'CON_CLIENT_ANSWER','רשומה ב-client_answers בלי status, או תשובה שיושמה בנוסח בלי clause_ids',N.get('question',''),blocking=True)
		elif N.get('status')=='applied'and N.get('value')and str(N['value'])not in m:finding(B,'CON_CLIENT_ANSWER','התשובה "%s" יושמה, אבל אינה בנוסח המתקבל'%N['value'],', '.join(N['clause_ids']),blocking=True)
	for(G,J)in enumerate(F):
		for P in PREVAILS:
			M=P.search(J)
			if M:finding(B,'PREC_ANNEX_PREVAILS','נשאר סעיף שקובע שמסמך אחר גובר על ההסכם: "%s"'%M.group(0)[:80],'פסקה %d'%G,blocking=True)
	for I in(U.get('deal_documents')or D.get('deal_documents')or{}).get('conflicts')or[]:
		if not I.get('decision'):finding(B,'DEAL_DOCS_CONFLICT','סתירה בין מסמכי העסקה בלי הכרעה: %s'%I.get('conflict',''),', '.join(I.get('documents')or[]),blocking=True)
	for(G,J)in enumerate(F):
		if G in n or G>=len(E)or J!=E[G]:continue
		for A6 in NEUTRALIZERS:
			if A6.lower()in J.lower():finding(B,'NEUTRALIZER','ביטוי מנטרל בנוסח שלא שונה: "%s". להכריע בו'%A6,'פסקה %d'%G)
	A7={A.get('clause_id'):A for A in D.get('company_representations')or[]}
	for(A,H,P)in[(A,B,REPRESENT)for(A,B)in our_texts(C)]+[(A,A.get('external_comment')or'',REPRESENT_BUBBLE)for A in C]:
		M=next((A for A in P.finditer(H or'')if not(P is REPRESENT and _rep_by_them(H,A.start(),D))),None)
		if not M:continue
		A8=A7.get(A.get('clause_id'))or A7.get(A.get('id'));AP=bool(re.search('\\[[^\\]]*'+re.escape(M.group(0))+'[^\\]]*\\]',H))
		if not AP and not(A8 and A8.get('status')in('confirmed','approved')):finding(B,'REP_UNAPPROVED','מצג או התחייבות ("%s") בנוסח שלנו בלי רשומה מאושרת ב-company_representations, ולא בסוגריים מרובעים'%M.group(0),A.get('id'),blocking=True)
	s=U.get('deal_context')or{};AQ='existing_agreements_with_counterparty'in s or bool((s.get('conflict_check')or{}).get('done'))
	for(A,H)in our_texts(C):
		if CONFLICT_REP.search(H)and not AQ:finding(B,'CONFLICT_CHECK','מצג "%s" בלי בדיקת התנגשות רשומה (conflict_check)'%CONFLICT_REP.search(H).group(0),A.get('id'),blocking=True)
	if EXHAUST.search(m):
		for g in s.get('existing_agreements_with_counterparty')or D.get('existing_agreements_with_counterparty')or[]:
			if g.get('in_force',True)and not g.get('effect_of_new_agreement'):finding(B,'EXISTING_AGREEMENT','יש סעיף מיצוי או ביטול הסכמים קודמים, וההסכם הקיים "%s" בלי השפעה רשומה'%(g.get('name')or g.get('file')or''),'')
	A9=set()
	for AR in(manifest or{}).get('documents')or[]:
		for AS in('counterparty','parties'):
			t=AR.get(AS)
			for S in t if isinstance(t,list)else[t]:
				if S and len(str(S))>=3:A9.add(str(S))
	u=str(U.get('counterparty_name')or'')
	for A in C:
		AT=A.get('external_comment')or''
		for S in A9:
			if S in AT and not(u and(S in u or u in S)):finding(B,'OTHER_PARTY_NAME','בבועה החיצונית שם של צד מהסכם אחר: "%s"'%S,A.get('id'),blocking=True)
	AA={A for(A,B)in enumerate(F)if Y is not None and A>=Y and PRICE.search(B)}
	for(A,H)in our_texts(C):
		if(INCOTERMS.search(H)or CURRENCY.search(H))and AA and not n&AA:finding(B,'PRICE_TERMS','התיקון משנה תנאי מסירה, מטבע או הצמדה, ונספח המחירים לא שונה',A.get('id'))
		if CONFORMING_ONLY.match(A.get('external_comment')or'x')and(PRICE.search(H)or CURRENCY.search(H)):finding(B,'PRICE_CONFORMING','בועה "תיקון עקבי" בלבד על שינוי שנוגע במחיר',A.get('id'),blocking=True)
	for(G,J)in enumerate(E):
		if not COMPLIANCE.search(J):continue
		AU=c.get(G)or[];e=any((A.get('user_decision')or{}).get('answer_kind')=='explicit'or(A.get('decision_required')or{}).get('required')or _explicit_on(A,D or{})for A in AU)
		if not e:finding(B,'COMPLIANCE','סעיף ציות ("%s") בלי הכרעה מפורשת של המשתמש'%COMPLIANCE.search(J).group(0),'פסקה %d'%G,blocking=True)
	h=U.get('bilingual')or{};i=sum(1 for A in E if len(HEB.findall(A))>len(LAT.findall(A))and len(A)>30);j=sum(1 for A in E if len(LAT.findall(A))>len(HEB.findall(A))and len(A)>30);AV=i>=5 and j>=5 and min(i,j)>=.3*max(i,j)
	if AV and not h.get('is_bilingual'):finding(B,'BILINGUAL_UNDECLARED','ההסכם נראה דו-לשוני (%d פסקאות בעברית, %d באנגלית), ו-meta.bilingual אינו מסמן זאת'%(i,j),'',blocking=True)
	if h.get('is_bilingual'):
		Z={int(A):int(B)for(A,B)in(h.get('map')or{}).items()};Z.update({B:A for(A,B)in list(Z.items())})
		for A in C:
			K=A.get('para')
			if K is None or A.get('op')in('accept','comment_only'):continue
			AB=Z.get(K)
			if AB is None or not c.get(AB):finding(B,'BILINGUAL_ONE_SIDE','הכרעה שמשנה נוסח בגרסה אחת בלבד',A.get('id'),blocking=True)
		for v in h.get('mismatches')or[]:
			if not v.get('decision'):finding(B,'BILINGUAL_MISMATCH','סתירה בין הגרסאות בלי הכרעה: %s'%v.get('difference',''),v.get('clause_ref_a',''),blocking=True)
	AW=D.get('playbook_resolution')or{};AC=AW.get('playbook_match')or U.get('playbook_match')
	if AC in('side_mismatch','family_mismatch','mutuality_mismatch'):finding(B,'POSITION_MISMATCH','הפלייבוק שהוחל אינו מתאים להסכם (%s)'%AC,'',blocking=True)
	AX='\n'.join(E)
	for(A,H)in our_texts(C):
		for w in list(PARTY_LABELS)+party_labels(O):
			P="(?<![\\w\u0590-\u05ff'])"+re.escape(w)+"(?![\\w\u0590-\u05ff])(?!\\s+[A-Z])(?!'s)"
			if re.search(P,H)and w not in AX:finding(B,'PARTY_LABEL','בנוסח שלנו הכינוי "%s", שאינו בהסכם: הנוסח לא עבר את מפת המונחים'%w,A.get('id'),blocking=True)
	AD={}
	for A in C:
		for AY in A.get('rule_ids')or[]:AD.setdefault(AY,set()).update({A.get('para'),A.get('after_para')})
	for a in(O or{}).get('clauses')or(O or{}).get('rules')or[]:
		AE=a.get('id')or a.get('rule_id');AF=(a.get('traffic_light')or{}).get('red')or a.get('red')or{};AZ=list(a.get('red_flags')or[])+list(AF.get('red_flags')or[])+[A for A in AF.get('match_criteria')or[]if isinstance(A,str)]
		for b in AZ:
			b=str(b).strip()
			if len(b)<4:continue
			for(G,J)in enumerate(F):
				if b in J and G not in(AD.get(AE)or set()):finding(B,'RED_MARKER','סימן אדום של הכלל %s ("%s") בנוסח המתקבל, בלי הכרעה לאותו כלל'%(AE,b),'פסקה %d'%G,blocking=True)
	for T in hidden_scan(Q):
		if T['part']=='word/document.xml'and T['paragraph']is not None:
			AG=dt.document_root(Q);Aa=dt.body_paragraphs(AG);Ab=list(AG.iter(W+'p'))
			try:k=Aa.index(Ab[T['paragraph']])
			except(ValueError,IndexError):k=None
			if k is not None and not c.get(k):finding(B,'HIDDEN_TEXT','טקסט מוסתר (%s) בטיוטה שלהם, בלי הכרעה: "%s"'%(T['how'],T['text'][:80]),'פסקה %d'%k,blocking=True)
		elif T['how']=='properties':finding(B,'HIDDEN_TEXT','טקסט במאפייני הקובץ (%s): לבדוק שאינו הוראה'%T['part'],T['part'])
	Ac={str(A).strip()for A in(profile or{}).get('lawyer_names')or[]if A};Ad={(A.get('quote')or'')[:40]for A in U.get('exposed_comments')or D.get('exposed_comments')or[]};Ae={A.get('reply_to_comment')for A in C if A.get('reply_to_comment')}
	for I in comment_info(Q):
		if I['author']in Ac or I['author']in INTERNAL_AUTHORS:continue
		if INTERNAL_HINT.search(I['text'])and I['text'][:40]not in Ad:finding(B,'THEIR_INTERNAL_COMMENT','בועה של %s נראית פנימית, ואינה רשומה ב-exposed_comments: "%s"'%(I['author'],I['text'][:100]),'בועה %s'%I['id'],blocking=True)
		if not I['has_reply']and I['id']not in Ae:finding(B,'THEIR_COMMENT_UNANSWERED','לבועה של %s אין מענה: "%s"'%(I['author'],I['text'][:80]),'בועה %s'%I['id'])
	Af=load(os.path.join(HERE,'combos.json'))or[];Ag={tuple(sorted(A.get('decisions')or[]))for A in U.get('combo_checks')or D.get('combo_checks')or[]};AH={A.get('id'):' '.join(str(A.get(B)or'')for B in('new_text','new','text'))for A in C}
	for x in Af:
		N=sorted(B for(B,A)in AH.items()if A.strip()and re.search(x['a'],A,re.I));AI=sorted(B for(B,A)in AH.items()if A.strip()and re.search(x['b'],A,re.I));Z={tuple(sorted((A,B)))for A in N for B in AI if A!=B};Ah=sorted(A for A in Z if A not in Ag)
		if Ah:finding(B,'COMBO','צירוף "%s": %s מול %s. לבדוק אותם יחד, ולרשום ב-meta.combo_checks'%(x['name'],', '.join(N),', '.join(AI)),'')
	Ai={A.get('para'):A for A in C if A.get('op')=='delete_paragraph'}
	for A in C:
		if A.get('op')!='insert_paragraph'or not isinstance(A.get('after_para'),int):continue
		for K in(A['after_para'],A['after_para']+1):
			AJ=Ai.get(K)
			if AJ is None or K>=len(E):continue
			V=re.findall('\\w+',E[K]);y=set(re.findall('\\w+',A.get('text')or''))
			if V and sum(1 for A in V if A in y)/len(V)>=.4:finding(B,'PARAGRAPH_REPLACED','הפסקה נמחקה ונכתבה מחדש (%s ו-%s), ורוב המילים נשארו: לסמן ב-replace_span רק את מה שמשתנה'%(AJ.get('id'),A.get('id')),'פסקה %d'%K,blocking=True)
	for A in C:
		if A.get('op')=='replace'and isinstance(A.get('para'),int)and A['para']<len(E):
			z,A0=E[A['para']],A.get('new_text')or'';AK=dt.char_ops(z,A0);Aj=sum(A[2]-A[1]for A in AK if A[0]=='delete')+sum(len(A[3])for A in AK if A[0]=='insert');V=re.findall('\\w+',z);y=set(re.findall('\\w+',A0));Ak=sum(1 for A in V if A in y)/len(V)if V else .0
			if Aj>=.8*(len(z)+len(A0))and Ak>=.4:finding(B,'REPLACE_COLLAPSED','ההכרעה מסמנת את רוב הפסקה אף שרוב המילים נשארו: לסמן ב-replace_span רק את מה שמשתנה',A.get('id'),blocking=True)
	for A in C:
		if A.get('op')in('replace','replace_span','insert_paragraph')and not(A.get('plain_effect')and A.get('position_effect')):finding(B,'EFFECT_FIELDS','הכרעה שמכניסה נוסח בלי plain_effect ו-position_effect',A.get('id'))
	review_2210(B,E,C,D,O,Q);review_containment(B,E,C,D,O,L)
	try:X=numbered_labels(Q)
	except(OSError,KeyError,zipfile.BadZipFile,etree.XMLSyntaxError):X=None
	review_related(B,E,C,D,O,X);review_post_edit(B,E,C,D,L,X);review_high_risk(B,E,C,D,O,L,X);review_law_coverage(B,C,D,O,L);B.extend(PM.check_map(((D or{}).get('meta')or{}).get('playbook_map'),O,'work'if L=='work'else'send'));review_definitions(B,E,C,D,L,X);review_definition_changes(B,E,F,C,X);review_areo(B,C,D,L);review_s1c(B,E,C,D,Q,l,L);review_interactions(B,F,E,C,D,L);review_overclaim(B,C,L);review_numbers(B,E,C,D,O,L);review_consistency(B,F,E,C,D,Q,L,lawyer_names=(profile or{}).get('lawyer_names'));return B
CLAIM=re.compile('\\b(?:as|where|which|what)\\b[^.;]{0,60}?\\b(?:was|were|has been|have been|had been)\\s+(?:already\\s+)?(?:agreed|negotiated|settled|fixed|discussed|confirmed|approved)\\b|\\bthat is where\\b|\\bas (?:already |previously )?(?:agreed|discussed|confirmed)\\b|\\b(?:is|are) (?:already )?(?:set|fixed|agreed|priced|settled) (?:in|under|by) the\\b|\\bas you (?:have )?(?:confirmed|agreed|said|told us)\\b|כפי ש(?:סוכם|הוסכם|נקבע|אישרתם|ציינתם|נאמר)|שם (?:סוכם|הוסכם|נקבע)|(?:סוכם|הוסכם|נקבע) (?:ב|בין)|(?:קבוע|קבועים|נקבעו|מוסדרים) ב(?:הסכם|חוזה)',re.I)
DOC_NAME=re.compile('\\b((?:[A-Z][\\w-]*\\s+){1,4}(?:Agreement|Contract|Order Form|Order|Form|Statement of Work|Terms|Proposal|Quotation|Letter))\\b|(?<![א-ת])(?:ב|ל|מ|ש)?(הסכם ה[א-ת]+|חוזה ה[א-ת]+|הזמנת ה[א-ת]+)')
NOT_RECEIVED='referenced_not_received','not_received','missing','requested','to_request'
THEIR_NOTE=re.compile('Staff Only|Note to (?:read|draft|user)|drafting note|guidance note|for internal use|internal use only|הערה לצוות|לשימוש פנימי|הערת ניסוח|הנחיות למילוי',re.I)
GUIDE_FOOTNOTE=re.compile('^\\s*(?:Consider|Amend|Add|Include|Insert|Delete|Remove|Check|Please|Below is|This (?:should|must)|יש ל|להשלים|לשקול|למחוק|נא )|amend as necessary|consult with',re.I)
def _docs_received(state):
	C=state;E=C.get('meta')or{};A=E.get('deal_documents')or C.get('deal_documents')or{};F=A.get('files')if isinstance(A,dict)else A;D=[]
	for B in F or[]:
		if isinstance(B,dict):G=' '.join(str(B.get(A)or'')for A in('file','name','title'));D.append((G.lower(),str(B.get('status')or'received')))
	return D
def review_s1c(out,theirs,decisions,state,received,work,mode=None):
	J=state;I=decisions;S=J.get('meta')or{};T=_docs_received(J);U=' '.join(str((A or{}).get('fact')or'')for A in(S.get('deal_context')or{}).get('facts')or[]if isinstance(A,dict)).lower()
	for C in I:
		V=C.get('external_comment')or''
		for K in re.split('(?<=[.;?!])\\s+',V):
			D=CLAIM.search(K)
			if not D:continue
			L=[A for B in DOC_NAME.findall(K)for A in B if A and not A.lower().startswith('this ')]
			if L:E=[A for A in L if A.lower()not in U and not any(A.lower()in B and C not in NOT_RECEIVED for(B,C)in T)]
			else:E=[]if C.get('fact_source')in('user_answer','agreement')else[D.group(0)]
			if E:finding(out,'BUB_UNSOURCED_FACT','הבועה טוענת עובדה על מסמך או על אירוע שלא נמסרו ("%s", %s): אין לה מקור ב-deal_documents שהתקבלו, ב-deal_context.facts או ב-fact_source. לנמק בנוסח שלפנינו, או לרשום את המקור'%(D.group(0),', '.join(E)),C.get('id'),blocking=mode!='work');break
	M=[A for(A,B)in enumerate(theirs)if THEIR_NOTE.search(B or'')];N={A.get('para')for A in I if A.get('op')=='delete_paragraph'};F=[A for A in M if A in N];G=[A for A in M if A not in N];A=[]
	try:
		with zipfile.ZipFile(received)as O:
			if'word/footnotes.xml'in O.namelist():
				X=etree.fromstring(O.read('word/footnotes.xml'))
				for P in X.iter(W+'footnote'):
					Q=''.join(A.text or''for A in P.iter(W+'t'))
					if Q.strip()and GUIDE_FOOTNOTE.search(Q):A.append(P.get(W+'id'))
	except(OSError,zipfile.BadZipFile,etree.XMLSyntaxError):A=[]
	B=[]
	if A:
		Y=dt.document_root(work)
		for H in Y.iter(W+'footnoteReference'):
			if H.get(W+'id')in A and not any(dt.local(A.tag)=='del'for A in H.iterancestors()):B.append(H.get(W+'id'))
	R=[A for A in A if A not in B]
	if(F or R)and(G or B):finding(out,'THEIR_NOTES_PARTIAL','הערות לצוות של הצד שכנגד טופלו חלקית: נמחקו %s, ונשארו %s. כולן נמחקות עם בועה אחת, או כולן נשארות עם בועה (n4-redlining.md, שלב א)'%('פסקאות %s'%F if F else'הערות שוליים %s'%R,', '.join(A for A in['פסקאות %s'%G if G else'','הערות שוליים %s'%B if B else'']if A)),'')
EMAIL=re.compile('\\be-?mail\\b|\\belectronic mail\\b|דוא[\\"״\']ל|דואר אלקטרוני|אי-?מייל',re.I)
NOTICE_WORD=re.compile('\\bnoti(?:ce|fy|fied|fication)s?\\b|\\bsent\\b|\\bserved?\\b|\\bdelivered\\b|הודע|יישלח|תישלח|תימסר|יימסר|שליחה|מסירה',re.I)
EMAIL_EXCLUDED=re.compile('writing shall not include e-?mail|(?:e-?mail|electronic mail)[^.;]{0,40}(?:shall|does|will) not (?:constitute|be (?:deemed|treated as|considered|valid)|count as|be a valid)|\\b(?:not|excluding|other than|except) (?:by |via )?(?:e-?mail|electronic mail)\\b|(?:דוא[\\"״\']ל|דואר אלקטרוני)[^.;]{0,40}(?:לא ייחשב|לא תיחשב|אינו|אינה|לא יהווה|לא תהווה)|(?:למעט|ולא|שלא) (?:ב|באמצעות )(?:דוא[\\"״\']ל|דואר אלקטרוני)',re.I)
IN_WRITING=re.compile('\\bin writing\\b|\\bwritten notice\\b|(?<![א-ת])בכתב(?![א-ת])',re.I)
OVERRIDE=re.compile('\\bnotwithstanding\\b|\\bdespite\\b|\\bby way of exception to\\b|על אף|למרות',re.I)
STALE_MARKERS=(re.compile('\\bsubject to (?:Royal Assent|enactment|ratification)\\b|\\bnot yet in force\\b|טרם נכנס(?:ה)? לתוקף',re.I),'הפניה לחקיקה שבזמן הניסוח עוד לא נחקקה או לא נכנסה לתוקף'),
UNREASONABLY=re.compile('\\bnot\\s+(?:to\\s+)?be\\s+unreasonably\\s+(?:withheld|refused|delayed|conditioned)|\\bnot\\s+unreasonably\\s+(?:withhold|refuse|delay|condition)|(?:לא|שלא)\\s+(?:תסורב|יסורב|תימנע|יימנע|יעוכב|תעוכב|יסרב|תסרב)[^.;]{0,25}(?:בלתי\\s+סביר|שלא\\s+(?:מטעמים|באופן)\\s+סביר|מטעמים\\s+(?:בלתי\\s+)?סבירים)',re.I)
INCREASE=re.compile('\\b(?:increase|extend|expand|enlarge|add to)\\w*\\b[^.;]{0,60}?\\b(?:obligations?|costs?|liabilit(?:y|ies)|responsibilit(?:y|ies)|exposure)\\b|(?:יגדיל|יגדילו|תגדיל|להגדיל|הגדלת|ירחיב|ירחיבו|להרחיב|הרחבת)[^.;]{0,60}?(?:התחייבויות|חובות|עלויות|אחריות|חבות)',re.I)
MONEY_CUR={'£':'GBP','gbp':'GBP','ליש"ט':'GBP','ליש״ט':'GBP','$':'USD','usd':'USD','דולר':'USD','€':'EUR','eur':'EUR','אירו':'EUR','יורו':'EUR','₪':'ILS','nis':'ILS','ils':'ILS','ש"ח':'ILS','ש״ח':'ILS'}
_CUR_RX='|'.join(sorted((re.escape(A)for A in MONEY_CUR),key=len,reverse=True))
_MULT={'million':1e6,'m':1e6,'mm':1e6,'מיליון':1e6,'k':1e3,'thousand':1e3,'אלף':1e3}
MONEY_BEFORE=re.compile('(?<![\\w])(%s)\\s?(\\d[\\d,]*(?:\\.\\d+)?)(?:\\s*(million|mm|m|k|thousand|מיליון|אלף)(?![\\w]))?'%_CUR_RX,re.I)
MONEY_AFTER=re.compile('(?<![\\d.,])(\\d[\\d,]*(?:\\.\\d+)?)\\s*(million|thousand|מיליון|אלף)?\\s*(%s)(?![\\w])'%_CUR_RX,re.I)
INSURANCE=re.compile('\\binsurance\\b|\\binsured\\b|\\binsurer\\b|ביטוח|פוליס',re.I)
CAP_WORD=re.compile('shall not exceed|will not exceed|limited to|capped at|\\bcap\\b|maximum (?:aggregate )?liability|לא תעלה|לא יעלה|לא יעלו|תקרת|תוגבל|מוגבלת ל',re.I)
LIAB_WORD=re.compile('liabilit|אחריות|חבות',re.I)
SUPER_CAP=re.compile('\\b(?:save that|except that|provided that|save for|other than)\\b(?:[^.]|\\.(?=\\d)){0,250}?\\b(?:shall|will) not exceed\\b|(?:ואולם|למעט|אלא ש|ובלבד ש|פרט ל)(?:[^.]|\\.(?=\\d)){0,250}?(?:לא תעלה|לא יעלה|לא יעלו)',re.I)
CAP_RELATION=re.compile('in addition to|inclusive of|included in|count(?:s|ed)? towards|not in addition|separate from|instead of|in substitution|within (?:that|the|such) (?:cap|limit|amount)|בנוסף ל|נוסף על|כלול|במסגרת (?:התקרה|הסכום)|מעבר לתקרה',re.I)
AGGREGATION=re.compile('(?:calculated|counted|aggregated|taken together|combined)\\s+(?:in the aggregate\\s+)?with|in (?:the )?aggregate with|together with (?:its|their|any|the) (?:liabilit(?:y|ies)|exposure) under|single (?:aggregate )?cap (?:for|across|under)|במצטבר עם|יחד עם (?:האחריות|החבות)|תקרה (?:אחת|משותפת)|ייכלל(?:ו)? בתקרה',re.I)
OFFER_ATTR=re.compile('\\bas (?:you|the [A-Z][\\w-]+) (?:have |has |had )?(?:offered|proposed|suggested)\\b|\\b(?:in line with|per|following) your (?:offer|proposal|suggestion)\\b|\\byour (?:offer|proposal|suggestion) (?:of|to|that)\\b|\\byou (?:have )?(?:offered|proposed|suggested)\\b|כפי שהצעתם|כהצעתכם|בהתאם להצעתכם|לפי הצעתכם|הצעתכם ל|שהצעתם|כפי שהציעו',re.I)
OFFER_STOP={'which','their','there','these','those','about','after','before','would','could','should','shall','under','where','while','keep','agree','accept','offered','proposed','suggested','additional','together'}
def _money(text):
	C=[]
	for A in MONEY_BEFORE.finditer(text or''):
		B,D,E=A.group(1),A.group(2),A.group(3)
		try:F=float(D.replace(',',''))*_MULT.get((E or'').lower(),1)
		except ValueError:continue
		C.append((MONEY_CUR.get(B.lower(),MONEY_CUR.get(B,B)),F))
	for A in MONEY_AFTER.finditer(text or''):
		D,E,B=A.group(1),A.group(2),A.group(3)
		try:F=float(D.replace(',',''))*_MULT.get((E or'').lower(),1)
		except ValueError:continue
		C.append((MONEY_CUR.get(B.lower(),MONEY_CUR.get(B,B)),F))
	return C
def _norm_ws(s):return re.sub('\\s+',' ',(s or'').replace('’',"'").replace('‘',"'")).strip()
def _ours_in(text,decisions):B=_norm_ws(text);return any(len(_norm_ws(A))>=12 and _norm_ws(A)in B for(C,A)in our_texts(decisions))
def _sentence_span(text,pos):
	C=pos;B=text;D=0
	for A in re.finditer('[.;?!](?:\\s+|$)',B):
		if A.end()>C:break
		D=A.end()
	A=re.search('[.;?!](?=\\s|$)',B[C:]);return D,C+A.end()if A else len(B)
def _sentence_of(text,pos):A,B=_sentence_span(text,pos);return text[A:B]
def _our_labels(state):
	C=((state or{}).get('meta')or{}).get('position')or{};B=[]
	for A in C.get('defined_terms_map')or[]:
		if isinstance(A,dict)and A.get('means')=='us'and A.get('term'):B.append(re.sub('^(?:the|ה)\\s*','',str(A['term']).strip(),flags=re.I))
	return[A for A in B if len(A)>=2]
def _their_labels(state):
	C=((state or{}).get('meta')or{}).get('position')or{};B=[]
	for A in C.get('defined_terms_map')or[]:
		if isinstance(A,dict)and A.get('means')=='them'and A.get('term'):B.append(re.sub('^(?:the|ה)\\s*','',str(A['term']).strip(),flags=re.I))
	return[A for A in B if len(A)>=2]
def _rep_by_them(txt,start,state):
	B=state;A=start;E,G=_sentence_span(txt,A);F=txt[max(E,A-80):A]
	def C(labels):
		A=-1
		for B in labels:
			for C in re.finditer('(?<![א-ת\\w])[ולבכמש]{0,2}ה?'+re.escape(B)+'(?![א-ת\\w])',F,re.I):A=max(A,C.start())
		return A
	D=C(_their_labels(B));return D>=0 and D>C(_our_labels(B))
def _their_sources(received,ours):
	A=received;B=[A['text']for A in comment_info(A)if A['author']not in ours and A['author']not in INTERNAL_AUTHORS]
	try:
		D=dt.document_root(A)
		for C in D.iter(W+'ins'):
			if C.get(W+'author')not in ours:B.append(''.join(A.text or''for A in C.iter(W+'t')))
	except(OSError,KeyError,zipfile.BadZipFile,etree.XMLSyntaxError):pass
	return'\n'.join(B)
def review_consistency(out,accepted,theirs,decisions,state,received,mode=None,lawyer_names=()):
	P=received;O=theirs;L=decisions;I=accepted;F=out;E=state;E=E or{};X=our_texts(L);f=[(B,A.group(0))for(B,C)in enumerate(I)for A in[EMAIL_EXCLUDED.search(C)]if A]
	if f:
		for(A,p)in X:
			for H in re.split('(?<=[.;])\\s+',p):
				C=EMAIL.search(H)
				if not(C and NOTICE_WORD.search(H))or EMAIL_EXCLUDED.search(H)or OVERRIDE.search(H):continue
				M=A.get('para')if isinstance(A.get('para'),int)else A.get('after_para')
				if _reviewed(E,'NOTICE_EMAIL_CONFLICT',M):break
				Q=[]
				if isinstance(M,int):Q=[A for A in range(max(0,M-3),min(len(O),M+4))if A!=M and IN_WRITING.search(O[A])and NOTICE_WORD.search(O[A])]
				q,r=f[0];finding(F,'NOTICE_EMAIL_CONFLICT','הנוסח שלנו קובע הודעה בדוא"ל ("%s"), וסעיף ההודעות (פסקה %d: "%s") מוציא דוא"ל מ"בכתב"%s. המלצה: לקבוע בנוסח שלנו שההודעה לפי סעיף זה יכולה להישלח בדוא"ל על אף סעיף ההודעות, או לתקן את סעיף ההודעות, או לוותר על הדוא"ל'%(H.strip()[:90],q,r,'; ובפסקה %s הסמוכה נדרשת הודעה בכתב ("%s"), כך שהשתיים סותרות'%(Q[0],O[Q[0]].strip()[:70])if Q else''),A.get('id'));break
	for(D,B)in enumerate(I):
		Y=[C for(A,C)in STALE_MARKERS if A.search(B)]
		if not Y or _reviewed(E,'DEF_OUTDATED',D):continue
		R=sorted(_terms_in(B))
		if R:g=sorted({str(A.get('id'))for(A,B)in X for C in R if _term_rx(C).search(B)});h=sum(1 for(A,B)in enumerate(I)if A!=D and any(_term_rx(A).search(B)for A in R));finding(F,'DEF_OUTDATED','ההגדרה "%s" (פסקה %d) מפנה לחוק או למועד שהוחלפו: %s. %s המלצה: להציע עדכון של ההגדרה לדין שחל היום, או לרשום ב-checks_reviewed שהוחלט להשאיר אותה'%(', '.join(R),D,'; '.join(Y),'ההכרעות %s נשענות עליה, ו-%d פסקאות משתמשות בה.'%(', '.join(g),h)if g else'%d פסקאות משתמשות בה.'%h),'פסקה %d'%D)
		elif _ours_in(B,L):finding(F,'DEF_OUTDATED','בנוסח שלנו הפניה לחוק או למועד שהוחלפו: %s. המלצה: להפנות לדין שחל היום'%'; '.join(Y),'פסקה %d'%D)
	Z=_our_labels(E)
	for(D,B)in enumerate(I):
		C=UNREASONABLY.search(B)
		if not C or _reviewed(E,'CONSENT_REASONABLE_OURS',D):continue
		H=_sentence_of(B,C.start());i=INCREASE.search(H)
		if not i:continue
		a=[A for A in Z if re.search('(?<![\\w\u0590-\u05ff])'+re.escape(A)+'(?![\\w\u0590-\u05ff])',H,re.I)]
		if Z and not a:continue
		finding(F,'CONSENT_REASONABLE_OURS','"%s" חל על הסכמה להגדלת החובות, העלויות או האחריות%s ("%s")%s. המלצה: הסכמה כזו בשיקול דעתנו המוחלט: למחוק את הסייג, או לכתוב "in its sole discretion". אחרת הצד שכנגד יטען שסירוב לשאת בחובה או בעלות נוספת אינו סביר'%(C.group(0),' של %s'%a[0]if a else'',i.group(0)[:70],' בנוסח שלנו'if _ours_in(B,L)else''if Z else'. לא נמצאה מפת מונחים: הממצא חל רק כשזה הצד שלנו'),'פסקה %d'%D)
	for(D,B)in enumerate(I):
		C=SUPER_CAP.search(B)
		if not C or CAP_RELATION.search(B)or len(_money(B))<2 or _reviewed(E,'CAP_SUPER_UNCLEAR',D):continue
		finding(F,'CAP_SUPER_UNCLEAR','ניסוח: תקרה נוספת ("%s...")%s בלי "in addition to" או "inclusive of". לא ברור אם הסכום שלה נוסף על התקרה הכללית או כלול בה. המלצה: לכתוב במפורש "inclusive of, and not in addition to" (או "in addition to"), לפי העמדה'%(C.group(0)[:60],' בנוסח שלנו'if _ours_in(B,L)else''),'פסקה %d'%D)
	s={B for(C,A)in X for B in _money(A)};S,T={},{}
	for(D,B)in enumerate(I):
		j=_money(B)
		if not j:continue
		t=CAP_WORD.search(B)and LIAB_WORD.search(B);k=T if t else S if INSURANCE.search(B)else None
		if k is None:continue
		for(G,u)in j:k.setdefault(G,[]).append((u,D))
	for G in sorted(set(S)&set(T)):
		J,v=max(S[G]);K,b=max(T[G])
		if not(J and K)or max(J,K)/min(J,K)<2:continue
		if not{(G,A)for(A,B)in S[G]+T[G]}&s:continue
		if _reviewed(E,'CAP_INSURANCE_GAP',b):continue
		finding(F,'CAP_INSURANCE_GAP','הביטוח הנדרש (פסקה %d: %s %s) והתקרה (פסקה %d: %s %s) רחוקים זה מזה פי %.1f. %s המלצה: ליישר את התקרה לסכום הביטוח או את הביטוח לתקרה, או לנמק את הפער בבועה ולרשום אותו בהכרעה'%(v,G,'{:,.0f}'.format(J),b,G,'{:,.0f}'.format(K),max(J,K)/min(J,K),'תקרה נמוכה בהרבה מהביטוח מזמינה את הטענה שהכיסוי קיים ולכן התקרה צריכה לעלות.'if J>K else'ביטוח נמוך בהרבה מהתקרה משאיר חשיפה שאינה מבוטחת.'),'פסקה %d'%b)
	if not any(AGGREGATION.search(A)and LIAB_WORD.search(A)for A in I):
		try:l,c=dt.reject_all(P),dt.accept_all(P)
		except(OSError,KeyError,zipfile.BadZipFile,etree.XMLSyntaxError):l,c=[],[]
		m=[(B,AGGREGATION.search(A).group(0),A)for(B,A)in enumerate(l+c)if AGGREGATION.search(A)and LIAB_WORD.search(A)]
		if m and not _reviewed(E,'CAP_AGGREGATION_REMOVED',None):A6,w,B=m[0];x=not any(AGGREGATION.search(A)and LIAB_WORD.search(A)for A in c);finding(F,'CAP_AGGREGATION_REMOVED','נמחק מנגנון נגד צבירה של תקרות בין מסמכים ("%s")%s. בלעדיו התקרה בהסכם הזה עלולה להיספר בנוסף לתקרה בהסכם האחר, ולא יחד איתה. המלצה: להחזיר את המנגנון (למשל "calculated in the aggregate with its liability under the [other agreement]"), או לוודא שההסכם האחר קובע תקרה משותפת'%(w,': הצד שכנגד מחק אותו, וההכרעה לא החזירה אותו'if x else': המחיקה בהכרעה שלנו'),'')
	y={str(A).strip()for A in lawyer_names or()if A};N=None
	for A in L:
		U=A.get('external_comment')or'';C=OFFER_ATTR.search(U)
		if not C or A.get('offer_source')or A.get('fact_source')=='user_answer':continue
		if N is None:N=_their_sources(P,y)if P else''
		z,A0=_sentence_span(U,C.start());n=U[z:C.start()]+' '+U[C.end():A0];A1=set(re.findall('\\d+',n));d={A.lower()for A in re.findall('[A-Za-z]{5,}|[א-ת]{4,}',n)}-OFFER_STOP;A2=set(re.findall('\\d+',N));A3=N.lower();e=sorted(A1-A2);A4=[A for A in d if A in A3]
		if e or not N.strip()or d and len(A4)<.5*len(d):finding(F,'BUB_OFFER_UNSOURCED','הבועה מייחסת לצד שכנגד הצעה ("%s") שאין לה מקור בבועות או בסימונים שלו%s. המלצה: לנסח כהצעה שלנו, או לרשום את המקור ב-offer_source (מזהה הבועה שלהם, their_markup, או user_answer כשההצעה נמסרה בשיחה)'%(C.group(0),' (%s לא מופיעים אצלם)'%', '.join(e)if e else''),A.get('id'))
	o=set()
	for V in E.get('user_decisions')or[]:
		if isinstance(V,dict)and V.get('answer_kind')=='explicit'and this_round(E,V):o|={str(A)for A in V.get('applies_to')or[]}
	for A in L:
		A5=A.get('requires_explicit')or(A.get('decision_required')or{}).get('requires_explicit')
		if A5 is not True:continue
		W=(A.get('user_decision')or{}).get('answer_kind')
		if W=='explicit'or str(A.get('id'))in o:continue
		if A.get('coverage')=='for_call'and A.get('op')in(None,'','comment_only'):continue
		finding(F,'EXPLICIT_ANSWER_MISSING','ההכרעה מסומנת requires_explicit, והתשובה של המשתמש %s. נדרשת תשובה מפורשת לפני משלוח: negotiation_state.py decide --id <השאלה> --answer-kind explicit --applies-to %s'%('הואצלה (delegated)'if W=='delegated'else'אינה מפורשת (%s)'%W if W else'חסרה',A.get('id')),A.get('id'),blocking=mode!='work')
PROVISO_REF=re.compile('הסייג (?:האמור|ה?נ[\\"״]ל|שלעיל|שלהלן|הבא|דלעיל)|בכפוף לסייג|the (?:foregoing|above|following|said|preceding) proviso|subject to the proviso',re.I)
PROVISO_MARK=re.compile('ובלבד ש|בתנאי ש|ואולם|אלא אם|provided(?:,)? (?:however,? )?that|provided always that|except that',re.I)
BACKREF=re.compile('^\\s*(?:\\(?[א-תa-z0-9]{1,3}[.)]\\s*)?(?:כאמור לעיל|האמור לעיל|על אף האמור לעיל|בנוסף לאמור לעיל|מבלי לגרוע מהאמור לעיל|The foregoing|Notwithstanding the foregoing|In addition to the foregoing|Without limiting the foregoing)',re.I)
LEAD_IN=re.compile('(?::|שלהלן|כדלקמן|as follows|the following)\\s*:?\\s*$',re.I)
LIST_ITEM=re.compile("^\\s*(?:\\(?[א-י]\\)|\\(?[a-z]\\)|\\(?\\d{1,2}\\)|[א-י]['׳]?[.)]|[a-z][.)]|\\(?[ivx]{1,4}\\))\\s",re.I)
DANGLING_END=re.compile('(?:,|;|\\s)(?:או|וכן|or|and)\\s*[;:]?\\s*$',re.I)
DANGLING_MID=re.compile('(?:,|\\s)(?:או|or|and)\\s*[.;](?:\\s|$)',re.I)
TAIL_CONJ=re.compile('[;,]\\s*(?:או|וכן|or|and)\\s*$',re.I)
OBLIGATION=re.compile('\\bshall\\b|\\bmust\\b|יתחייב|מתחייב|תתחייב|מחויב|חייב(?:ת|ים)?\\s|אסור|לא יהיה רשאי|לא תהיה רשאית',re.I)
REF_BUBBLE=re.compile("רא(?:ו|ה) (?:את )?הערת(?:נו|י)|כאמור בהערת(?:נו|י)|כמפורט בהערת(?:נו|י)|ר' הערת|see (?:our )?(?:comment|note)|as per our (?:comment|note)|as noted above|part of the same change|same as (?:above|our comment)",re.I)
FACT_THEM=re.compile('מאחר ש(?:אתם|אתן|הנכם|החברה שלכם)|הואיל ואתם|בהיותכם|כפי שידוע(?: לנו)? ש|אתם (?:פועלים|נסחרים|מעסיקים|מפוקחים|רשומים|מתחרים)|לקוחותיכם|עובדיכם|מתחריכם|המתחרים שלכם|הרגולטור (?:שלכם|החל עליכם)|given that you|since you (?:are|operate|have)|as you (?:are|operate)|you operate|you employ|you are (?:a |an )?(?:public|listed|regulated|subject to)|your (?:customers|clients|employees|competitors|regulator)',re.I)
FACT_US=re.compile('(?:החברה|אנו|אנחנו) (?:היא )?(?:חברה ציבורית|נסחרת|נסחרים|פועלת ב(?!התאם|אופן|מסגרת|הקשר)|פועלים ב(?!התאם|אופן|מסגרת|הקשר)|מעסיקה|מעסיקים|מפוקחת|מפוקחים|כפופה לפיקוח|רשומה ב)|כחברה (?:ציבורית|נסחרת|בורסאית|זרה|מפוקחת)|we are (?:a )?(?:public|listed|regulated)|we operate in|we employ|as a (?:public|listed|regulated) (?:company|entity)|our (?:customers|employees|regulator)',re.I)
FACT_SOURCES='profile','user_answer','agreement'
WEAKNESS=re.compile('אין לנו ברירה|אין לנו חלופה|אין בידינו חלופה|קשה לנו לגבות|יקשה עלינו לגבות|קשה לגבות|אנו תלויים|אנחנו תלויים|תלויים בכם|לחץ זמנים|לוח הזמנים שלנו לחוץ|תזרים|we have no (?:choice|alternative)|we (?:depend|rely) (?:heavily )?on you|we are under (?:time )?pressure|cash ?flow|difficult (?:for us )?to collect|we cannot afford',re.I)
_HE_PRE='(?<![א-ת])(?:[ובלמשכ]{0,2}ה?)'
CP_TOPIC=re.compile(_HE_PRE+'(?:דין|שיפוט|פורום|בוררות|שפה|מטבע|מס|מסים|מיסים|מיסוי|ניכוי במקור)(?![א-ת])|(?<![א-ת])[ובלמשכ]{0,2}סמכות(?![א-ת])|\\b(?:governing law|jurisdictions?|forums?|arbitration|languages?|currenc(?:y|ies)|tax(?:es|ation)?|withholding)\\b',re.I)
LAW_TOPIC=re.compile(_HE_PRE+'(?:דין|דיני|שיפוט|פורום|בוררות|שפה|מטבע|מס|מסים|מיסים|מיסוי|ניכוי במקור|פרטיות|מידע אישי|ניירות ערך)(?![א-ת])|(?<![א-ת])[ובלמשכ]{0,2}סמכות(?![א-ת])|רגולצ|\\b(?:governing law|jurisdictions?|forums?|arbitration|languages?|currenc(?:y|ies)|tax(?:es|ation)?|withholding|privacy|data protection|securities)\\b|\\bregulat',re.I)
HE_MONTHS={'ינואר':1,'פברואר':2,'מרץ':3,'מרס':3,'אפריל':4,'מאי':5,'יוני':6,'יולי':7,'אוגוסט':8,'ספטמבר':9,'אוקטובר':10,'נובמבר':11,'דצמבר':12}
EN_MONTHS={B:A+1 for(A,B)in enumerate(('january','february','march','april','may','june','july','august','september','october','november','december'))}
ANCHOR_CTX=re.compile('תחילת|תחולת|יחול|ייכנס לתוקף|ייכנסו לתוקף|נכנס לתוקף|מועד התחילה|מועד התחולה|מועד הקובע|תקופת ההסכם|יתחיל|תתחיל|החל מיום|החל מתאריך|effective|commenc|start date|as of|term (?:of this agreement )?(?:shall )?(?:begin|start)',re.I)
DATE_RX=[(re.compile('(?<!\\d)(\\d{1,2})[./](\\d{1,2})[./](\\d{4})(?!\\d)'),'dmy'),(re.compile('(?<!\\d)(\\d{4})-(\\d{2})-(\\d{2})(?!\\d)'),'ymd'),(re.compile('(?<!\\d)(\\d{1,2})\\s+ב?(%s),?\\s+(\\d{4})'%'|'.join(HE_MONTHS)),'d_he_y'),(re.compile('(?<!\\d)(\\d{1,2})(?:st|nd|rd|th)?\\s+(%s),?\\s+(\\d{4})'%'|'.join(EN_MONTHS),re.I),'d_en_y'),(re.compile('\\b(%s)\\s+(\\d{1,2}),?\\s+(\\d{4})'%'|'.join(EN_MONTHS),re.I),'en_d_y')]
EMPTY_ANCHOR=re.compile('(?:מיום|מתאריך|החל מיום|ביום|effective(?: as of)?|dated|as of|commencing on)\\s*(?:_{2,}|\\[\\s*[•·.\\s]*\\]|\\.{3,}|__\\s*/\\s*__)',re.I)
def result_view(theirs,decisions):
	C=list(theirs);F=set();G=set();I={}
	for A in decisions:
		B,E=A.get('para'),A.get('op')
		if E=='insert_paragraph'and isinstance(A.get('after_para'),int):I.setdefault(A['after_para'],[]).append(A.get('text')or'')
		if not isinstance(B,int)or not 0<=B<len(C):continue
		if E=='replace'and A.get('new_text')is not None:C[B]=A['new_text'];F.add(B)
		elif E=='replace_span'and A.get('old')and A['old']in C[B]:C[B]=C[B].replace(A['old'],A.get('new')or'',1);F.add(B)
		elif E=='delete_paragraph':G.add(B)
	H=[]
	for(D,J)in enumerate(C):
		if D not in G:H.append((D,J,D in F))
		for K in I.get(D,[]):H.append((('ins',D),K,True))
	return H,G
def _dates(text):
	import datetime as B
	for(F,D)in DATE_RX:
		for E in F.finditer(text):
			A=E.groups()
			try:
				if D=='dmy':C=B.date(int(A[2]),int(A[1]),int(A[0]))
				elif D=='ymd':C=B.date(int(A[0]),int(A[1]),int(A[2]))
				elif D=='d_he_y':C=B.date(int(A[2]),HE_MONTHS[A[1]],int(A[0]))
				elif D=='d_en_y':C=B.date(int(A[2]),EN_MONTHS[A[1].lower()],int(A[0]))
				else:C=B.date(int(A[2]),EN_MONTHS[A[0].lower()],int(A[1]))
			except(ValueError,KeyError):continue
			yield(E,C)
def time_anchors(theirs,today=None):
	C=today;import datetime as G;C=C or G.date.today();D=[]
	for(E,B)in enumerate(theirs):
		for A in EMPTY_ANCHOR.finditer(B):D.append({'para':E,'text':A.group(0),'issue':'empty','date':None})
		for(A,F)in _dates(B):
			H=B[max(0,A.start()-60):A.start()]
			if F<C and ANCHOR_CTX.search(H):D.append({'para':E,'text':B[max(0,A.start()-40):A.end()].strip(),'issue':'past','date':F.isoformat()})
	return D
def _terms_in(text):
	A=set()
	for B in DEF_PATTERNS:
		for C in B.finditer(text or''):A.update(A.strip()for A in C.groups()if A)
	return A
def _term_rx(term):
	A=term;B=A[1:]if A.startswith('ה')and len(A)>3 else A
	if B!=A:return re.compile('(?<![א-ת])[ולבכמש]{0,2}ה?'+re.escape(B)+'(?![א-ת])')
	return re.compile(re.escape(A))
def dependents_of(d,theirs,labels):
	D=labels;B=theirs;A=d.get('para')
	if not isinstance(A,int)or not 0<=A<len(B):return[]
	E=d.get('regime');H=_terms_in(B[A])
	if E in(None,'','none'):return[]
	C=set();F=D[A]if A<len(D)else None
	if F:
		for(G,I)in enumerate(B):
			if G==A:continue
			for J in(REF_HE,REF_EN):
				if any(A.group(1)==F for A in J.finditer(I)):C.add(G)
	if E=='definition':
		for K in H:L=_term_rx(K);C.update(B for(B,C)in enumerate(B)if B!=A and L.search(C))
	C.update(B for B in d.get('same_topic')or[]if isinstance(B,int)and B!=A);return sorted(C)
def _rule_index(core):return{A.get('id')or A.get('rule_id'):A for A in(core or{}).get('clauses')or(core or{}).get('rules')or[]}
def _kinds(meta):A=(meta.get('deal_context')or{}).get('counterparty_kind');return set(A if isinstance(A,list)else[A]if A else[])
CONTAIN_TOPICS={'אחריות ושיפוי':('הגבלת (?:ה)?אחריות|תקר[הת]|מוגבלת ל|נזק (?:עקיף|תוצאתי)|אחריות(?:ו)? (?:ו)?שיפוי|ישפה|שיפוי|limitation of liability|liabilit[^.\\n]{0,40}(?:limited|cap|exceed)|indirect|consequential|indemnif','האחראי(?:ת)? הבלעדי|אחריות (?:מלאה|בלעדית|מוחלטת|בלתי מוגבלת)|(?:ב)?יחד ולחוד|בגין כל נזק|לכל נזק|נזקים? (?:כבדים|עקיפים|תוצאתיים)|לרבות נזק (?:עקיף|תוצאתי)|ישפה[^.\\n]{0,60}כל|sole(?:ly)? (?:responsib|liab)|jointly and severally|unlimited liability|any and all (?:loss|damage|claim)|including (?:indirect|consequential)'),'קבלני משנה, הסבה וגילוי לצד שלישי':('קבלני? משנה|מעבד(?:י)? משנה|להסב|הסבה|להמחות|subcontract|sub-?processor|\\bassign','(?:לא|אין)[^.\\n]{0,30}(?:י?מסור|יגלה|לגלות|יעביר|להעביר|ישתף|יסב|להסב|ימחה)[^.\\n]{0,60}(?:צד (?:שלישי|ג)|לכל (?:אדם|גורם)|לאחר)|לא (?:יעסיק|ייעזר|יתקשר)[^.\\n]{0,40}(?:קבלני? משנה|מעבד)|סודיות (?:מלאה|מוחלטת)|shall not (?:disclose|transfer|subcontract|assign|share)[^.\\n]{0,60}(?:third part|any person|any other)'),'החזרה והשמדה בסיום':('יחזיר|השבה|ימחק|מחיק|השמד|\\breturn|delet|destroy','(?:מיד|לאלתר|מיידית|immediately)[^.\\n]{0,40}(?:יחזיר|ישיב|מחק|ימחק|מחיק|השמד|return|delet|destroy)|(?:יחזיר|ישיב|מחק|ימחק|מחיק|השמד|return|delet|destroy)[^.\\n]{0,40}(?:מיד|לאלתר|מיידית|immediately)'),'הפרה וסיום':('הפרה יסודית|תקופת תיקון|לתקן את ההפרה|שימוע|material breach|cure period','הפרה יסודית|תנאי (?:מהותי|עיקרי)|fundamental breach|material term|of the essence'),'ביקורת':('ביקורת|audit|inspect','במתקני|באתרי|בחצרי|בחצרות|on-?site|premises|ללא הודעה|without notice')}
CONTAIN_CONTEXT={'אחריות ושיפוי':'(?<![א-ת])[ובלמהש]{0,2}(?:אחריות|אחראי|אחראית|ישפה|תשפה|לשפות|שיפוי|יפצה|תפצה|לפצות|פיצוי|חבות|חב)(?![א-ת])|liab|indemn|compensat|reimburs'}
KEEPS_THEIRS='accept',
def _rule_titles(core):
	B={}
	for C in('clauses','rules'):
		for A in(core or{}).get(C)or():
			if isinstance(A,dict)and(A.get('id')or A.get('rule_id')):B[A.get('id')or A.get('rule_id')]=A
	return B
def _explicit_on(d,state):
	C=state
	if(d.get('user_decision')or{}).get('answer_kind')=='explicit':return True
	D=str(d.get('id'))
	for A in C.get('user_decisions')or():
		if isinstance(A,dict)and A.get('answer_kind')=='explicit'and D in{str(A)for A in A.get('applies_to')or()}:return True
	for B in C.get('deliberate_concessions')or():
		if isinstance(B,dict)and str(B.get('clause_ref'))==D and(B.get('user_decision')or{}).get('answer_kind')=='explicit':return True
	return False
def review_containment(out,theirs,decisions,state,core,mode=None):
	G=decisions;F=theirs;B=state;B=B or{};H=_rule_titles(core);S=_related_map(core);I=mode!='work';J=[A for A in G if A.get('op')in KEEPS_THEIRS and isinstance(A.get('para'),int)and A.get('para')<len(F)]
	for C in G:
		if C.get('op')!='insert_paragraph':continue
		K=' '.join(str(C.get(A)or'')for A in('text','new_text','new'));K+=' '+' '.join(str((H.get(A)or{}).get('title')or'')for A in C.get('rule_ids')or());T=[A for(A,(B,C))in CONTAIN_TOPICS.items()if re.search(B,K,re.I)];L=set(C.get('rule_ids')or())
		for A in J:
			if _reviewed(B,'CONTAIN_TOPIC_NOT_EDITED',A.get('para'))or _explicit_on(A,B):continue
			M=F[A['para']];D=None;N=L&set(A.get('rule_ids')or());O={B for A in L for B in S.get(A)or()}&set(A.get('rule_ids')or())
			if N:D='אותו כלל (%s)'%', '.join(sorted(N))
			elif O and A.get('their_track')in('red','yellow'):D='כלל קשור בפלייבוק (%s), והנוסח שלהם בו אינו בירוק'%', '.join(sorted(O))
			for E in T:
				P=CONTAIN_CONTEXT.get(E)
				if P and not re.search(P,M,re.I):continue
				Q=re.search(CONTAIN_TOPICS[E][1],M,re.I)
				if Q:D='נוסח שסותר את הסעיף החדש בנושא %s: "%s"'%(E,Q.group(0));break
			if D:finding(out,'CONTAIN_TOPIC_NOT_EDITED','הסעיף החדש %s מחיל עמדה, והפסקה %s, שעוסקת באותו נושא (%s), התקבלה כמו שהיא. להחיל את העמדה בתיקון כירורגי של הפסקה הקיימת, או לתקן גם אותה; ויתור על הפסקה אינו חי לצד סעיף חדש שלנו באותו נושא, וסעיף חדש מוסיפים רק לנושא שאף הוראה בנייר שלהם אינה עוסקת בו'%(C.get('id'),A.get('id'),D),A.get('id'),blocking=I)
	for A in J:
		R=A.get('tier')=='deliberate_concession';U=[H.get(A)or{}for A in A.get('rule_ids')or()];V=any(str(A.get('importance')or'').lower()=='critical'or A.get('walk_away')is True for A in U)
		if not(R and V or A.get('their_track')=='red'):continue
		if _explicit_on(A,B)or _reviewed(B,'CONTAIN_CONCESSION_UNDECIDED',A.get('para')):continue
		finding(out,'CONTAIN_CONCESSION_UNDECIDED','הנוסח שלהם התקבל כמו שהוא (%s) בכלל %s, %s, בלי הכרעה מפורשת של המשתמש. ויתור על קו אדום אינו נעשה בשקט, גם לא בתגובה ממוקדת: תיקון כירורגי, נקודה לשיחה, או "נדרשת הכרעתך" בהכרעה מפורשת'%('ויתור מכוון'if R else'קבלה',', '.join(A.get('rule_ids')or())or'?','שהנוסח שלהם בו אדום'if A.get('their_track')=='red'else'שהוא קו אדום (חשיבות קריטית או walk_away)'),A.get('id'),blocking=I)
RELATED_OPS='replace','replace_span','delete_paragraph','insert_paragraph'
RELATED_STOP=set('של את על עם או כל לא אם כי גם זה זו אשר יהיה תהיה יהיו לפי בין עד כן אלה אותו אותה הוא היא הם\nלרבות ככל וכן מכל כלשהו כלשהי בכל הספק המזמין הלקוח החברה הצד הצדדים ההסכם הסכם נספח בנספח זה ידי the and of to in or\na an any all shall be by for with this that such as is are any other its their\nיובהר מובהר יודגש לעיל להלן כמפורט בהתאם לצורך במסגרת אין'.split())
_HE_PREFIX=re.compile('^[והבלמשכ](?=[א-ת]{4,})')
def _norm_token(w):w=_HE_PREFIX.sub('',w.lower().strip('"\'׳״,.;:()'));return re.sub('[התםן]$','',w)if re.match('[א-ת]',w)and len(w)>4 else w
def _title_tokens(core,rule_ids,stop):
	A=_rule_titles(core);B=set()
	for C in rule_ids or():D=(A.get(C)or{}).get('title')or(A.get(C)or{}).get('topic_name')or'';B|={_norm_token(A)for A in re.findall('[א-ת\\w]{4,}',D)if A.lower()not in stop}
	return{A for A in B if len(A)>=3}
RELATED_BACKREF=re.compile('^\\s*(?:במקרה כאמור|כאמור לעיל|כאמור|בנסיבות אלה|לצורך כך|in such (?:case|event)|as aforesaid)',re.I)
def attach_related(core,core_path):
	B=core_path;A=core
	if not isinstance(A,dict)or not B or A.get('_related'):return A
	C=os.path.join(os.path.dirname(os.path.abspath(B)),'playbook-model.json');D=load(C)if os.path.exists(C)else None
	if isinstance(D,dict):A['_related']={A.get('rule_id')or A.get('id'):list(A.get('related_rule_ids')or[])for A in D.get('rules')or()if isinstance(A,dict)}
	return A
def _related_map(core):
	B=dict((core or{}).get('_related')or{})
	for C in('clauses','rules'):
		for A in(core or{}).get(C)or():
			if isinstance(A,dict)and A.get('related_rule_ids'):B[A.get('id')or A.get('rule_id')]=list(A['related_rule_ids'])
	return B
def _key_phrases(text,stop=RELATED_STOP):
	C=re.findall('[^\\s,.;:()\u200e\u200f]+',text or'');B=lambda w:len(w)>=3 and w.lower()not in stop and w[1:]not in stop;D=[]
	for E in range(len(C)-2):
		A=C[E:E+3]
		if sum(1 for A in A if B(A))>=2 and(B(A[0])or B(A[2])):D.append(' '.join(A))
	return D
def deal_only_mode(state):A=(state or{}).get('positions_source');return isinstance(A,dict)and A.get('mode')=='deal_only'
def review_areo(out,decisions,state,mode=None):
	B=state
	for A in decisions:
		if A.get('op')not in RELATED_OPS+('comment_only',)or A.get('rule_ids')or A.get('structural')or A.get('conforming')or A.get('silent_change')or A.get('reply_to_comment'):continue
		if A.get('source_label')in('areo_proposal','הצעת Areo','Areo proposal')or A.get('areo_clause')is True:continue
		if deal_only_mode(B)and str(A.get('source_label')or'').strip():continue
		C=str(A.get('source_label')or'')
		if A.get('decision_basis')not in('Law','CompanyPractice','ExpertJudgment')and not C.startswith(('שיקול מקצועי','דין','הסכם קודם','Professional judgment','Law','Prior')):continue
		if _reviewed(B or{},'AREO_LABEL_MISSING',A.get('para')):continue
		finding(out,'AREO_LABEL_MISSING','להכרעה %s אין כלל בפלייבוק, והיא אינה מסומנת כסעיף AREO (source_label: areo_proposal). כך עורך הדין אינו רואה שהיא הצעת Areo. / Decision %s has no playbook rule and is not marked as an Areo clause (source_label: areo_proposal)'%(A.get('id'),A.get('id')),A.get('id'),blocking=mode!='work')
def review_related(out,theirs,decisions,state,core,labels=None):
	J=state;I=decisions;E=labels;C=theirs;J=J or{};Y=_related_map(core);Z=(J.get('meta')or{}).get('position')or{};a=[re.sub('^(?:the|ה)\\s*','',str(A.get('term')or''),flags=re.I)for A in Z.get('defined_terms_map')or()if isinstance(A,dict)and A.get('term')];Q=RELATED_STOP|{B for A in a for B in re.findall('[א-ת\\w]{3,}',A)};b={A.get('para')for A in I if A.get('tier')=='deliberate_concession'};M={}
	for G in C:
		for R in{_norm_token(A)for A in re.findall('[א-ת\\w]{3,}',G or'')}:M[R]=M.get(R,0)+1
	c={A.get('para')for A in I if isinstance(A.get('para'),int)and(A.get('op')in RELATED_OPS+('comment_only',)or A.get('op')=='accept'and(A.get('internal_comment')or A.get('reason')))};S={}
	for B in I:
		if isinstance(B.get('para'),int):S.setdefault(B['para'],[]).append(B)
	T=set()
	for B in I:
		if B.get('op')not in RELATED_OPS or B.get('structural')or B.get('conforming'):continue
		D=B.get('para');d={A.get('para')for A in B.get('dependents')or()if isinstance(A,dict)and(A.get('decision')or A.get('keep')and A.get('reason'))};F={};e=B.get('old')or(C[D]if B.get('op')in('replace','delete_paragraph')and isinstance(D,int)and D<len(C)else'');H=lambda i:i!=D and i not in c and i not in b and len((C[i]or'').split())>=8
		for U in _key_phrases(e,Q):
			N=[A for(A,B)in enumerate(C)if A!=D and U in B]
			if not N or len(N)>4:continue
			for A in N:
				if H(A):F.setdefault(A,'אותו נוסח: "%s"'%U)
		K=_title_tokens(core,B.get('rule_ids'),Q);K={A for A in K if M.get(A,0)<=max(2,len(C)//5)}
		if len(K)>=2:
			for(A,G)in enumerate(C):
				if not H(A):continue
				V=K&{_norm_token(A)for A in re.findall('[א-ת\\w]{3,}',G)}
				if len(V)>=2:F.setdefault(A,'אותו נושא בפלייבוק (%s)'%', '.join(sorted(V)))
		if isinstance(D,int):
			for A in range(D+1,min(D+4,len(C))):
				if H(A)and RELATED_BACKREF.search(C[A]or''):F.setdefault(A,'מפנה לסעיף שתוקן ("%s")'%RELATED_BACKREF.search(C[A]).group(0).strip())
		O=(E or[None]*(len(C)+1))[D]if isinstance(D,int)and E and D<len(E)else None
		if O:
			f=re.compile('(?:סעיף|סעיפים|בסעיף|לסעיף|section|clause)\\s*'+re.escape(O)+'(?![\\d.]*\\d)',re.I)
			for(A,G)in enumerate(C):
				if H(A)and f.search(G):F.setdefault(A,'הפניה לסעיף %s'%O)
		P={B for A in B.get('rule_ids')or()for B in Y.get(A)or()}
		if P:
			for(A,g)in S.items():
				if not H(A):continue
				for L in g:
					if L.get('op')=='accept'and P&set(L.get('rule_ids')or())and L.get('their_track')in('red','yellow'):F.setdefault(A,'כלל קשור בפלייבוק (%s)'%', '.join(sorted(P&set(L.get('rule_ids')))))
		W=B.get('cluster_id')or B.get('id')
		for(A,h)in sorted(F.items()):
			if A in d or(W,A)in T or _reviewed(J,'RELATED_UNHANDLED',A):continue
			T.add((W,A));X=E[A]if E and A<len(E)and E[A]else'פסקה %d'%A;finding(out,'RELATED_UNHANDLED','ההכרעה %s שינתה סעיף, והסעיף הקשור %s (%s) נשאר בלי הכרעה. להחיל עליו את אותה תכלית בנוסח דומה, או לרשום ב-dependents של ההכרעה שהוא הושאר בכוונה, עם reason. / Decision %s changed a clause; the related clause %s was not handled: apply the same purpose there, or record it in dependents as deliberately unchanged, with a reason'%(B.get('id'),X,h,B.get('id'),X),B.get('id'),blocking=True)
POST_EDIT_PAIRS=('נוסח קפוא של מסמך או מדיניות','version in (?:effect|force) (?:on|at|as at)|as (?:in force|in effect) (?:on|at) the (?:date|effective)|shall not (?:be )?(?:amend|chang|modif)\\w* (?:unilaterally|without)|בנוסח(?:ו|ה|ם)? (?:התקף|שבתוקף|שהיה בתוקף) (?:במועד|ביום)|לא (?:ישונה|ישונו|יעודכן|יעודכנו) (?:באופן חד.?צדדי|ללא|בלי)',None,'as (?:amended|updated|modified|revised) (?:from time to time|periodically)|as updated periodically|then[- ]current|from time to time (?:amend|updat|modif|revis)|כפי (?:שי|שת)(?:עודכן|עודכנו|שונה|שונו) מעת לעת|כפי שיהיה בתוקף מעת לעת|בנוסח(?:ו|ה)? העדכני|כפי שיתעדכן'),('הגבלת היקף או תדירות של ביקורת','(?:not|no) more (?:often )?than once (?:in|per|every|a)|once (?:per|a|in any|every) (?:year|calendar|twelve|12)|by way of (?:written )?(?:reports?|questionnaires?)|לא יותר מפעם(?: אחת)? ב|פעם(?: אחת)? (?:בשנה|ב-?12 חודשים)|בדרך של (?:בקשת )?(?:דוחות|דו\\"חות|שאלון)','audit|inspect|ביקורת|בדיקה|לבדוק','at any time|without (?:prior )?notice|on (?:any )?suspicion|(?:if|where) (?:it|there) (?:is|has) (?:a )?(?:suspicion|concern)|in its (?:sole|absolute) discretion|בכל עת|ללא הודעה|בלי הודעה|בעקבות חשש|בשל חשש|לפי שיקול דעת(?:ו|ה)?(?: הבלעדי)?|(?:החלטת|קביעת)[^.;]{0,40}(?:תהיה )?(?:מכרעת|סופית)|כחלופה'),('חריג של בלאי, אשם או פגם',"fair wear and tear|reasonable wear|(?:caused by|due to|arising from) (?:its|their|the \\w+'s) (?:act|omission|fault|negligence)|בלאי סביר|בלאי רגיל|עקב מעשה או מחדל של(?:ו|ה|הם)|למעט[^.;]{0,40}(?:פגם|בלאי)",'repair|damage|maintenance|restor|תיקון|תיקונים|נזק|נזקים|אחזקה|החזקה|לתקן','(?:all|any(?: and all)?) (?:repairs?|damages?|costs? of repair|loss)|כל (?:ה)?(?:נזקים|תיקונים|הוצאות|הקלקולים)|את כל (?:ה)?(?:נזקים|תיקונים|הוצאות)|הנובעים מ(?:ה)?(?:שימוש|השכרת)'),('איסור לצמצם שירות או תכונה','(?:will|shall) not (?:remove|reduce|degrade|materially reduce|discontinue)|לא (?:יסיר|יפחית|יצמצם|יפסיק)',None,'discontinu|withdraw (?:the|a|any) (?:service|feature)|end[- ]of[- ]life|deprecat|(?:רשאי|זכאי)[^.;]{0,30}(?:להפסיק|לצמצם|להסיר)')
def review_post_edit(out,theirs,decisions,state,mode=None,labels=None):
	I=state;H=decisions;D=labels;C=theirs;I=I or{};O=mode!='work';P={A.get('para')for A in H if A.get('op')in RELATED_OPS and isinstance(A.get('para'),int)};Q,R=result_view(C,H);S={}
	for(T,E,U)in Q:
		if U:S.setdefault(T,[]).append(E)
	K=set()
	for B in H:
		if B.get('op')not in RELATED_OPS or B.get('structural'):continue
		F=B.get('para')if B.get('op')!='insert_paragraph'else('ins',B.get('after_para'));V=' '.join(str(B.get(A)or'')for A in('new','new_text','text'));W=C[F]if isinstance(F,int)and F<len(C)else'';X={A.get('para')for A in B.get('dependents')or()if isinstance(A,dict)and(A.get('decision')or A.get('keep')and A.get('reason'))}
		for(G,L,M,Y)in POST_EDIT_PAIRS:
			if not re.search(L,V,re.I)or re.search(L,W,re.I):continue
			for(A,E)in enumerate(C):
				if A==F or A in P or A in R or A in X or(G,A)in K:continue
				if M and not re.search(M,E or'',re.I):continue
				J=re.search(Y,E or'',re.I)
				if not J or _reviewed(I,'POST_EDIT_CONTRADICTION',A):continue
				K.add((G,A));N=D[A]if D and A<len(D)and D[A]else'פסקה %d'%A;finding(out,'POST_EDIT_CONTRADICTION','ההכרעה %s קבעה %s, והסעיף %s נשאר עם נוסח שסותר אותה: "%s". לתקן אותו כסעיף קשור (הכרעה משלו), או לרשום ב-dependents של ההכרעה keep עם reason ולהסביר בבועה. / Decision %s set a rule (%s); clause %s still contradicts it ("%s"): fix it as a related clause, or record it in dependents with keep and a reason, and explain it in the comment'%(B.get('id'),G,N,J.group(0),B.get('id'),G,N,J.group(0)),B.get('id'),blocking=O)
HIGH_RISK=('דין או פורום','governing law|governed by|exclusive jurisdiction|courts? of|arbitrat|venue|הדין החל|יחול(?:ו)? (?:ה)?דין|דיני מדינת|סמכות (?:ה)?שיפוט|בוררות'),('חידוש אוטומטי או העלאת מחיר','auto(?:matic(?:ally)?)?[- ]?renew|renew(?:s|ed|al)? automatically|(?:increase|uplift|adjust)\\w*[^.;]{0,50}\\d+(?:\\.\\d+)?\\s?%|\\bCPI\\b|indexation|יתחדש(?:ו)? (?:באופן )?אוטומטי|חידוש אוטומטי|(?:יעודכנו|יעלו|יועלו|תוספת)[^.;]{0,40}\\d+\\s?%|הצמדה למדד'),('העברת נטל מס','withholding|gross[- ]?up|taxes?[^.;]{0,40}(?:borne|paid|payable) by|ניכוי (?:מס )?במקור|גילום|המס(?:ים)? (?:יחול|יחולו|ישולם|ישולמו) על'),('אחריות או שיפוי בלי תקרה','(?:indemnif|liab)\\w*[^.;]{0,90}(?:unlimited|without (?:any )?(?:limit|cap)|not (?:be )?subject to (?:the|any) (?:cap|limit))|uncapped|unlimited liability|(?:אחריות|שיפוי|ישפה)[^.;]{0,60}(?:ללא הגבלה|ללא תקרה|בלתי מוגבל)|לא (?:תחול|יחולו)[^.;]{0,30}(?:הגבלת|תקרת) (?:ה)?אחריות'),('מידע מסוג מיוחד','special categor|sensitive (?:personal )?(?:data|information)|health (?:data|information)|protected health|biometric|genetic|criminal (?:record|offen)|מידע (?:רגיש|רפואי|בריאותי|ביומטרי|גנטי)|בעל רגישות מיוחדת')
SECTOR_LAW=re.compile('\\b(?:[A-Z][\\w\'’&.\\-]*\\s+){1,6}(?:Act|Law|Regulations?|Directive|Code|Rules)\\b(?:\\s+(?:of\\s+)?\\(?\\d{4}\\)?|\\s+No\\.?\\s*\\d+)|\\bRegulation\\s*\\((?:EU|EC)\\)\\s*\\d{2,4}/\\d+|\\b(?:compl(?:y|iance|ies)\\s+with|subject\\s+to|governed\\s+by|pursuant\\s+to|in\\s+accordance\\s+with)\\s+(?:the\\s+)?[A-Z]{3,8}\\b|(?:חוק|תקנות|צו)\\s+[^\\n.;,]{2,50}?,?\\s*(?:ה?ת[א-ת\\"״\']{1,6}[-–]\\d{4}|\\d{4})')
CHANGING_OPS='replace','replace_span','delete_paragraph'
HIGH_RISK_EN={'דין או פורום':'governing law or forum','חידוש אוטומטי או העלאת מחיר':'automatic renewal or price increase','העברת נטל מס':'tax withholding or gross-up','אחריות או שיפוי בלי תקרה':'uncapped liability or indemnity','מידע מסוג מיוחד':'sensitive data','הפניה לחקיקה':'reference to legislation'}
def review_high_risk(out,theirs,decisions,state,core,mode=None,labels=None):
	G=state;D=labels;G=G or{};H={}
	for E in decisions:
		if isinstance(E.get('para'),int):H.setdefault(E['para'],[]).append(E)
	K=json.dumps(core or{},ensure_ascii=False)
	for(B,I)in enumerate(theirs):
		F=H.get(B,[])
		if any(A.get('op')in CHANGING_OPS or A.get('rule_ids')for A in F):continue
		J=D[B]if D and B<len(D)and D[B]else'פסקה %d'%B;A=None
		for(L,M)in HIGH_RISK:
			C=re.search(M,I or'',re.I)
			if C:A=L,C.group(0)[:40];break
		if not A:
			for C in SECTOR_LAW.finditer(I or''):
				if C.group(0).lower()not in K.lower():A='הפניה לחקיקה',C.group(0)[:40]
				break
		if A:finding(out,'NO_APPROVED_SOURCE','AREO לא מצאה מקור מורשה לנקודה זו: %s (%s, "%s"). הצעד הבא: להוסיף לתיקיית ההסכמים של החברה הסכם שמסדיר אותה, או לאשר עמדה בפלייבוק. / AREO did not find an approved source for this point: %s (%s). Next step: add to the company\'s agreements folder an agreement that covers it, or confirm a position in the playbook'%(A[0],J,A[1],HIGH_RISK_EN.get(A[0],A[0]),J),F[0].get('id')if F else'para %d'%B,blocking=False)
def review_law_coverage(out,decisions,state,core,mode=None):
	B=core;B=B if isinstance(B,dict)else{}
	for A in B.get('clauses')or B.get('rules')or[]:
		if not isinstance(A,dict):continue
		D=A.get('id')or A.get('rule_id')or'?';C=A.get('no_source_note');F=bool(A.get('no_approved_source'))or any(isinstance(A,dict)and A.get('no_approved_source')for A in A.get('statutory_override')or[])
		if not F:continue
		if not isinstance(C,str)or not C.strip():C=next((A.get('no_source_note')for A in A.get('statutory_override')or[]if isinstance(A,dict)and A.get('no_source_note')),'')
		E=A.get('title')or A.get('topic_name')or D;finding(out,'NO_APPROVED_SOURCE','AREO לא מצאה מקור מורשה לנקודה זו: %s. %sהצעד הבא: להוסיף לפלייבוק את המקור המאושר, או לאשר עמדה בפלייבוק. / AREO did not find an approved source for this point: %s'%(E,C.strip()+' 'if C else'',E),D,blocking=False)
def review_definitions(out,theirs,decisions,state,mode=None,labels=None):
	H=decisions;E=state;D=labels;C=theirs;E=E or{};L=mode!='work'
	for A in H:
		B=A.get('para')
		if A.get('op')not in('replace','replace_span')or not isinstance(B,int)or B>=len(C):continue
		F=_terms_in(C[B])
		if not F:continue
		if A.get('regime')=='none':continue
		if A.get('op')=='replace_span'and A.get('old')and not any(_term_rx(D).search(A['old'])or A['old']in C[B][max(0,C[B].find(D)-10):C[B].find(D)+len(D)+200]for D in F if D in C[B]):continue
		M={A.get('para')for A in A.get('dependents')or()if isinstance(A,dict)and(A.get('decision')or A.get('keep')and A.get('reason'))};N={B.get('para')for B in H if isinstance(B.get('para'),int)and B is not A and B.get('op')in RELATED_OPS}
		for G in sorted(F):
			O=_term_rx(G);I=[A for(A,C)in enumerate(C)if A!=B and O.search(C or'')]
			if len(I)>40:continue
			J=[A for A in I if A not in M and A not in N and not _reviewed(E,'DEF_USES_UNTRACED',A)]
			if J:K=', '.join('%d%s'%(A,' (%s)'%D[A]if D and A<len(D)and D[A]else'')for A in J[:12]);finding(out,'DEF_USES_UNTRACED','ההכרעה %s משנה את ההגדרה "%s". השימושים במונח (פסקאות %s) לא נבדקו: לכל שימוש הכרעה, או רישום ב-dependents עם keep ו-reason, כולל ההשפעה על הגנות שלנו שנשענות על המונח, וההשפעה מוסברת בבועה. / Decision %s changes the definition of "%s"; its uses (%s) were not traced'%(A.get('id'),G,K,A.get('id'),G,K),A.get('id'),blocking=L)
def this_round(state,x):A=x.get('round')if isinstance(x,dict)else None;return A is None or str(A)==str((state.get('meta')or{}).get('round_number'))
def _reviewed(state,code,para):B=state;return any(isinstance(A,dict)and A.get('code')==code and A.get('para')==para and A.get('reason')and this_round(B,A)for A in B.get('checks_reviewed')or[])
def review_2210(out,theirs,decisions,state,core,received):
	J=state;D=decisions;C=theirs;B=out;b=J.get('meta')or{};j={}
	for A in D:
		if isinstance(A.get('para'),int):j.setdefault(A['para'],[]).append(A)
	k,c=result_view(C,D);H=[B for(A,B,A)in k]
	for(R,(M,S,l))in enumerate(k):
		if PROVISO_REF.search(S):
			A0=' '.join(H[max(0,R-1):R+2])
			if not PROVISO_MARK.search(A0):T=M if isinstance(M,int)else M[1];A1=' '.join(C[max(0,T-1):T+2]);A2=(bool(PROVISO_MARK.search(A1))or l)and not _reviewed(J,'STRUCT_ORPHAN_PROVISO',T);finding(B,'STRUCT_ORPHAN_PROVISO','הפניה לסייג ("%s") בלי סייג שהיא מפנה אליו בנוסח המתקבל'%PROVISO_REF.search(S).group(0),'פסקה %s'%(T,),blocking=A2)
		A3=H[R+1]if R+1<len(H)else''
		if l and(DANGLING_MID.search(S)or DANGLING_END.search(S)and not LIST_ITEM.search(A3)):finding(B,'STRUCT_DANGLING_CONJ','בנוסח שלנו נשארה מילת חיבור ("או", "and") בלי פריט אחריה','פסקה %s'%(M if isinstance(M,int)else M[1],),blocking=True)
	m=[A for A in range(len(C))if A not in c]
	for E in sorted(c):
		N=next((A for A in m if A>E),None);K=next((A for A in reversed(m)if A<E),None)
		if N is not None and BACKREF.search(C[N])and not _reviewed(J,'STRUCT_BACKREF',N):finding(B,'STRUCT_BACKREF','הפסקה שאחרי הפסקה שמחקנו מפנה "לעיל", ומה שהיא הפנתה אליו נמחק','פסקה %d'%N,blocking=True)
		A4=N is None or not LIST_ITEM.search(C[N])
		if K is not None and A4 and LIST_ITEM.search(C[E]):
			if LEAD_IN.search(C[K])and all(A in c for A in range(K+1,E+1)):finding(B,'STRUCT_LIST_EMPTY','כל פריטי הרשימה נמחקו, ונשאר משפט הפתיחה שלה ("%s")'%C[K][-40:],'פסקה %d'%K,blocking=True)
			elif TAIL_CONJ.search(C[K]):finding(B,'STRUCT_DANGLING_CONJ','מחקנו את הפריט האחרון ברשימה, ו"או" או "and" נשארו לפני פריט שכבר אינו קיים','פסקה %d'%K,blocking=True)
	for A in D:
		U=(A.get('text')if A.get('op')=='insert_paragraph'else A.get('new'))or''
		if PROVISO_MARK.match(U.strip())and OBLIGATION.search(U):finding(B,'STRUCT_PROVISO_ROLE','נוסח שהכנסנו כסייג כולל התחייבות או איסור. התחייבות מקבלת פסקה משלה, וסייג צריך לסייג',A.get('id'))
	A5=numbered_labels(received)
	for A in D:
		E=A.get('para')
		if A.get('regime')in(None,'')and A.get('op')in('replace','replace_span','delete_paragraph')and isinstance(E,int)and 0<=E<len(C):
			n=[B.span()for A in DEF_PATTERNS for B in A.finditer(C[E])];d=C[E].find(A.get('old')or'\x00')if A.get('op')=='replace_span'else-1;A6=n and(A.get('op')!='replace_span'or d>=0 and any(B<d+len(A['old'])and d<C for(B,C)in n))
			if A6:finding(B,'REGIME_UNDECLARED','ההכרעה נוגעת בהגדרה: לקבוע regime (definition, או none כשהמשמעות אינה משתנה), כדי שהסעיפים התלויים ייבדקו',A.get('id'))
		o=dependents_of(A,C,A5)
		if not o:continue
		p,V=set(),[]
		for I in A.get('dependents')or[]:
			if not isinstance(I,dict)or not isinstance(I.get('para'),int):continue
			if I.get('decision')or I.get('keep')and I.get('reason'):p.add(I['para'])
			elif I.get('keep'):V.append(I['para'])
		W=[B for B in o if B not in p and not any(B is not A for B in j.get(B,[]))];W=[A for A in W if A not in V]
		if V:finding(B,'DEPENDENT_KEEP_NO_REASON','סעיף תלוי שהוחלט להשאיר בלי נימוק: פסקאות %s'%', '.join(map(str,V)),A.get('id'),blocking=True)
		if W:finding(B,'DEPENDENT_UNDECIDED','ההכרעה משנה משטר (%s), ויש סעיפים תלויים בלי הכרעה: פסקאות %s'%(A.get('regime')or'definition',', '.join(map(str,W))),A.get('id'),blocking=True)
	e=_rule_index(core);A7={B for A in D for B in A.get('rule_ids')or[]};A8={(A.get('rule_id'),A.get('id')):A for A in J.get('post_checks_done')or[]if isinstance(A,dict)and this_round(J,A)};A9=next((A for(A,B)in enumerate(H)if re.match('^\\s*(?:נספח|Annex|Schedule|Exhibit|Appendix)\\s',B)),len(H))
	for G in sorted(A7):
		O=e.get(G)or{}
		for F in O.get('post_checks')or[]:
			if not isinstance(F,dict):continue
			q=F.get('on_fail')=='block'or F.get('on_fail')is None and str(O.get('importance','')).lower()=='critical';r=F.get('scope')or'whole_agreement'
			if r=='definitions':X='\n'.join(A for A in H if _terms_in(A))
			elif r=='annexes':X='\n'.join(H[A9:])
			else:X='\n'.join(H)
			Y=F.get('pass_when');f='%s/%s'%(G,F.get('id','?'))
			if isinstance(Y,dict):
				g=[A for A in Y.get('absent')or[]if re.search(A,X,re.I)];h=[A for A in Y.get('present')or[]if not re.search(A,X,re.I)]
				if g or h:finding(B,'POST_CHECK_FAILED','בדיקת התוצאה של הכלל נכשלה (%s)%s%s'%(F.get('intent')or'',': נמצא %s'%', '.join(g)if g else'',': חסר %s'%', '.join(h)if h else''),f,blocking=q)
			else:
				s=A8.get((G,F.get('id')))
				if s is None:finding(B,'POST_CHECK_MANUAL','בדיקת תוצאה שאינה אוטומטית, ולא נרשמה ב-post_checks_done: %s'%(F.get('intent')or Y or''),f)
				elif s.get('result')=='fail':finding(B,'POST_CHECK_FAILED','בדיקת התוצאה נרשמה כנכשלת: %s'%(F.get('intent')or''),f,blocking=q)
	AA={(A.get('para'),A.get('issue'))for A in J.get('time_anchors')or[]if isinstance(A,dict)and A.get('status')in('answered','accepted','fixed')and this_round(J,A)}
	for P in time_anchors(C):
		if(P['para'],P['issue'])not in AA:finding(B,'TIME_ANCHOR','עוגן זמן %s בנייר שלהם ("%s"): שאלה לפני ההכרעה, ורישום ב-time_anchors'%('שכבר עבר'if P['issue']=='past'else'ריק',P['text'][:80]),'פסקה %d'%P['para'],blocking=True)
	from common import vague_terms as AB
	for(A,U)in our_texts(D):
		for AC in AB.undefined(U):finding(B,'VAGUE_TERM','מונח עמום בנוסח שלנו ("%s") בלי מבחן מוגדר: תקן, הוראות בכתב, רף מספרי או נספח'%AC['term'],A.get('id'))
	t=b.get('entity_check')or{};u=t.get('match')in('related','none')and not t.get('facts_confirmed')
	for A in D:
		L=A.get('external_comment')or'';Q=FACT_THEM.search(L)or FACT_US.search(L)
		if Q and A.get('fact_source')not in FACT_SOURCES:finding(B,'FACT_WITHOUT_SOURCE','הבועה נשענת על עובדה על אחד הצדדים ("%s") בלי מקור ב-fact_source (profile, user_answer או agreement)'%Q.group(0),A.get('id'),blocking=True)
		if u and A.get('fact_source')=='profile':finding(B,'ENTITY_PROFILE_FACT','הישות בנייר אינה הישות שבפרופיל, והמשתמש לא אישר שהעובדות חלות עליה: אין להשתמש בעובדה מהפרופיל',A.get('id'),blocking=True)
		if u and not(A.get('decision_required')or{}).get('required'):
			for G in A.get('rule_ids')or[]:
				v=(e.get(G)or{}).get('title')or''
				if LAW_TOPIC.search(v):finding(B,'ENTITY_RULE_UNCONFIRMED','כלל שתלוי במקום, בדין, ברגולציה או ברישום (%s), כשהישות בנייר לא אושרה: נדרשת הכרעתך'%(v or G),A.get('id'),blocking=True)
	w={}
	for A in D:
		L=A.get('external_comment')or''
		if L and REF_BUBBLE.search(L):finding(B,'REF_BUBBLE','בועת הפניה ("%s"). כל השינויים של אותו כלל באותו סעיף מקבלים בועה אחת (cluster_id)'%REF_BUBBLE.search(L).group(0),A.get('id'),blocking=True)
		if L and isinstance(A.get('para'),int)and A.get('rule_ids')and not A.get('cluster_id'):w.setdefault((A['para'],tuple(sorted(A['rule_ids']))),[]).append(A.get('id'))
	for((E,AG),x)in sorted(w.items(),key=lambda kv:str(kv[0])):
		if len(x)>1:finding(B,'BUBBLE_SAME_TOPIC','כמה בועות לאותו כלל באותו סעיף (%s): אשכול אחד עם בועה אחת'%', '.join(x),'פסקה %d'%E,blocking=True)
	for A in D:
		Q=WEAKNESS.search(A.get('external_comment')or'')
		if Q:finding(B,'WEAKNESS_IN_BUBBLE','הנימוק בבועה חושף חולשה שלנו ("%s"). לנסח כאינטרס של העסקה או כהגינות, והחשש נשאר בשכבה הפנימית'%Q.group(0),A.get('id'))
	for A in D:
		i=A.get('op')in('replace','replace_span','delete_paragraph')
		if A.get('their_track')=='green'and i and not A.get('mandatory'):finding(B,'THEIR_GREEN_MARKED','הנוסח שלהם כבר בירוק, ובכל זאת סומן. נוסח בירוק אינו מסומן',A.get('id'),blocking=True)
		elif A.get('their_track')=='yellow'and A.get('decision_code')in('R1','R2')and i and not(A.get('tier')=='tradeable'and A.get('fallback')=='their_wording'):finding(B,'THEIR_YELLOW_NOT_CHIP','הנוסח שלהם בצהוב וביקשנו יותר: ההכרעה היא מטבע חליפין (tier: tradeable), ועמדת הנסיגה היא הנוסח שלהם (fallback: their_wording)',A.get('id'))
		elif i and A.get('rule_ids')and not A.get('their_track'):finding(B,'THEIR_TRACK_MISSING','הכרעה לפי כלל בלי סיווג של הנוסח שלהם (their_track)',A.get('id'))
	from orchestrator import proportionality as AD;y=(b.get('deal_context')or{}).get('proportionality')or{};Z=AD.count_asks(D)['asks'];a=y.get('fight_list_size')
	if isinstance(a,int)and Z>a and y.get('user_choice')in(None,'','unanswered'):finding(B,'PROPORTIONALITY_UNASKED','%d בקשות מול רשימת מאבק של %d, והמשתמש לא נשאל לפני הסימון (מצב 4, עם שלושה ויתורים מוצעים)'%(Z,a),'',blocking=True)
	elif not isinstance(a,int)and Z>7:finding(B,'FIGHT_LIST_MISSING','%d בקשות, ולא נרשם גודל רשימת המאבק (deal_context.proportionality.fight_list_size)'%Z,'')
	if'foreign'in _kinds(b):
		for A in D:
			if(A.get('decision_required')or{}).get('required')or(A.get('user_decision')or{}).get('answer_kind')=='explicit':continue
			for G in A.get('rule_ids')or[]:
				O=e.get(G)or{};AE=[A for A in O.get('activation_conditions')or[]if isinstance(A,dict)];z={A.get('counterparty_kind')for A in AE if A.get('counterparty_kind')};AF=bool(z)or bool(CP_TOPIC.search(O.get('title')or''))
				if AF and not z&{'foreign','any'}:finding(B,'COUNTERPARTY_KIND_UNDECIDED','הכלל %s תלוי בזהות הצד שכנגד, ואין לו תנאי הפעלה לצד זר: נדרשת הכרעתך'%(O.get('title')or G),A.get('id'),blocking=True)
DEF_USAGES_MARK='DEF_CHANGED_USAGES'
def definition_changes(theirs,accepted,decisions,labels=None):
	F=theirs;E=labels;D=accepted;G=[];H={}
	for A in decisions or[]:
		if A.get('op')in('replace','replace_span')and isinstance(A.get('para'),int):H.setdefault(A['para'],A)
	M=min(len(F),len(D))
	for B in range(M):
		I,J=F[B]or'',D[B]or''
		if _norm_ws(I)==_norm_ws(J):continue
		K=_terms_in(I)|_terms_in(J)
		if not K:continue
		A=H.get(B)
		if A is not None and A.get('regime')=='none':continue
		for L in sorted(K):
			N=_term_rx(L);C=[A for(A,C)in enumerate(D)if A!=B and N.search(C or'')]
			if not C or len(C)>40:continue
			G.append({'decision':A.get('id')if A else None,'para':B,'term':L,'usages':[{'para':A,'label':E[A]if E and A<len(E)else None}for A in C],'usage_count':len(C)})
	return G
def usages_line(ch,lang='he'):
	B=lang;A=ch;D=', '.join(('סעיף %s'if B!='en'else'clause %s')%A['label']if A['label']else('פסקה %d'if B!='en'else'paragraph %d')%A['para']for A in A['usages'][:15]);C=A['usage_count']-min(A['usage_count'],15);E=(' ועוד %d'%C if B!='en'else' and %d more'%C)if C>0 else''
	if B=='en':return'%s: the definition of "%s" changed; the term also appears in %d places: %s%s. Each use was checked against the new definition.'%(DEF_USAGES_MARK,A['term'],A['usage_count'],D,E)
	return'%s: ההגדרה "%s" שונתה; המונח מופיע גם ב-%d מקומות: %s%s. כל שימוש נבדק מול ההגדרה החדשה.'%(DEF_USAGES_MARK,A['term'],A['usage_count'],D,E)
def annotate_definition_changes(decisions,theirs,accepted,labels=None,lang='he'):
	D=decisions;E=0;F={A.get('id'):A for A in D or[]}
	for B in definition_changes(theirs,accepted,D,labels):
		C=F.get(B['decision'])
		if C is None:continue
		G=usages_line(B,lang);A=C.get('internal_comment')or''
		if'%s: '%DEF_USAGES_MARK in A and'"%s"'%B['term']in A:continue
		C['internal_comment']=(A+('\n'if A else'')+G).strip();E+=1
	return E
def review_definition_changes(out,theirs,accepted,decisions,labels=None):
	B=decisions
	for A in definition_changes(theirs,accepted,B,labels):
		D=next((B for B in B if B.get('id')==A['decision']),None);C=(D or{}).get('internal_comment')or''
		if'%s: '%DEF_USAGES_MARK in C and'"%s"'%A['term']in C:continue
		finding(out,DEF_USAGES_MARK,'ההגדרה "%s" שונתה (פסקה %d), והמונח מופיע ב-%d מקומות נוספים. רשימת המופעים נכנסת לבועה הפנימית (content_checks.py --annotate-definitions) / The definition of "%s" changed; its %d uses are listed in the internal comment'%(A['term'],A['para'],A['usage_count'],A['term'],A['usage_count']),A['decision']or'פסקה %d'%A['para'])
_RULE_CODE='(?:R|V|Q|SEG|DS|LG|PB|OS|EMP)-?\\d+[a-z]?'
SCRUB_RULE=re.compile('(?<![\\w-])(?:כלל\\s+|rule\\s+)?('+_RULE_CODE+')(?![\\w-])',re.I)
SCRUB_CODES=re.compile('\\s*\\((?:\\s*(?:[ARKNQ]|REG-?|APR-?|DOC-?|AGR-?|S)\\d+[a-z]?\\s*,?)+\\)|(?<![\\w-])(?:קוד\\s+)?(?:[ARKNQ]\\d{1,3}[a-z]?|REG-\\d+|APR-\\d+|DOC-\\d+|AGR-\\d+|S\\d{1,3})(?![\\w-])')
ROUND_WORDS={'he':{1:'ראשון',2:'שני',3:'שלישי',4:'רביעי'},'en':{1:'first',2:'second',3:'third',4:'fourth'}}
def scrub_client_text(text,core=None,lang='he'):
	C=core;A=str(text or'');D={}
	if isinstance(C,dict):
		for B in C.get('clauses')or C.get('rules')or[]:
			if isinstance(B,dict)and(B.get('id')or B.get('rule_id')):D[str(B.get('id')or B.get('rule_id')).upper()]=B.get('title')or B.get('topic_name')or''
		for(E,F)in C.items():
			if isinstance(F,str)and re.fullmatch(_RULE_CODE,str(E),re.I):D[str(E).upper()]=F
	def G(m):return D.get(m.group(1).upper().replace('-',''))or D.get(m.group(1).upper())or''
	A=SCRUB_RULE.sub(G,A);A=SCRUB_CODES.sub('',A)
	def H(m):B=int(m.group(2));A=ROUND_WORDS['en'if m.group(1).lower()=='round'else'he'].get(B);return m.group(1)+' '+A if A else m.group(0)
	A=re.sub('(סבב|Round|round)\\s+(\\d+)',H,A);A=re.sub('\\s+([,.;:)])','\\1',A);A=re.sub('\\(\\s*\\)','',A);return re.sub('\\s{2,}',' ',A).strip()
TEMPLATE_BLANK=re.compile('_{3,}|\\[\\s*●\\s*\\]|\\[[^\\]\\n]{0,40}\\]|<[^>\\n]{2,40}>')
def paper_owner(received,our_names=(),their_names=(),lawyer_names=(),sent_shas=()):
	D=received;A,B=[],{'ours':0,'theirs':0,'template':0};C=lambda s:re.sub('[\\s\\"״\'”“׳.,]+',' ',str(s or'')).strip().lower();K=[C(A)for A in our_names if A and len(C(A))>=3];L=[C(A)for A in their_names if A and len(C(A))>=3];R={str(A).strip()for A in lawyer_names if A}|set(INTERNAL_AUTHORS)
	try:
		import hashlib as S;T=S.sha256(open(D,'rb').read()).hexdigest()
		if T in set(sent_shas or()):A.append('sha_of_sent_document');return{'owner':'ours','confident':True,'signals':A}
	except OSError:pass
	H=dt.read_package(D);U=etree.fromstring(H['word/document.xml']);M={A.get(W+'author')for A in U.iter(W+'ins',W+'del')}|{A['author']for A in dt.read_comments(H)};M.discard(None)
	if M&R:A.append('our_markup_present');B['ours']+=2
	N=H.get('docProps/core.xml')
	if N:
		O=C(re.sub('<[^>]+>',' ',N.decode('utf-8','ignore')))
		if any(A in O for A in K):A.append('properties_ours');B['ours']+=1
		elif any(A in O for A in L):A.append('properties_theirs');B['theirs']+=1
	P=[A.strip()for A in dt.received_paragraphs(D)]
	try:I=next((A for(A,B)in enumerate(numbered_labels(D))if B),None)
	except Exception:I=None
	Q=(P[:I]if I else P[:15])[:40];E=C(' '.join(Q));J=min([E.find(A)for A in K if A in E]or[-1]);F=min([E.find(A)for A in L if A in E]or[-1])
	if J>=0 and(F<0 or J<F):A.append('our_name_first_party');B['ours']+=1
	elif F>=0:A.append('their_name_first_party');B['theirs']+=1
	V=sum(len(TEMPLATE_BLANK.findall(A))for A in Q)
	if J<0 and F<0 and V>=2:A.append('party_block_blank');B['template']+=2
	if not A:return{'owner':None,'confident':False,'signals':A}
	G=max(B,key=B.get);X=[B for(A,B)in B.items()if A!=G];Y=B[G]>=2 and max(X)==0;return{'owner':G if B[G]else None,'confident':Y,'signals':A}
def unit_counts(decisions,para_count=None,playbook_map=None):
	C=para_count;A=[A for A in decisions or[]if isinstance(A,dict)];D={A.get('para')for A in A if isinstance(A.get('para'),int)};E={A.get('para')for A in A if A.get('op')in('replace','replace_span','delete_paragraph')and isinstance(A.get('para'),int)};F={A.get('para')for A in A if A.get('op')=='comment_only'and isinstance(A.get('para'),int)}-E;I=D-E-F;J=sum(1 for A in A if A.get('op')=='insert_paragraph');G={'unit':'paragraph','paragraphs':C,'decided':len(D),'changed':len(E),'accepted':len(I),'comment_only':len(F),'added':J,'open':max(C-len(D),0)if isinstance(C,int)else None};H=playbook_map or{};B=H.get('counts')or{}
	if H:G.update(playbook_rules=B.get('rules'),applied=B.get('applied'),no_matching_clause=B.get('no_matching_clause'),rules_no_outcome=B.get('no_outcome'))
	return G
def counts_line(c,lang='he'):
	B=c.get('paragraphs')
	if lang=='en':
		A='%d paragraphs changed, %d accepted as they are'%(c['changed'],c['accepted'])
		if c.get('added'):A+=', %d added'%c['added']
		if isinstance(B,int):A+=', out of %d paragraphs in their draft'%B
		if c.get('playbook_rules')is not None:A+='; playbook: %s of %s positions applied, %s with no matching clause'%(c.get('applied'),c.get('playbook_rules'),c.get('no_matching_clause'))
		return A+'.'
	A='%d פסקאות תוקנו, %d התקבלו כמו שהן'%(c['changed'],c['accepted'])
	if c.get('added'):A+=', %d נוספו'%c['added']
	if isinstance(B,int):A+=', מתוך %d פסקאות בטיוטה שלהם'%B
	if c.get('playbook_rules')is not None:A+='; הפלייבוק: %s מתוך %s עמדות הוחלו, %s בלי סעיף מתאים'%(c.get('applied'),c.get('playbook_rules'),c.get('no_matching_clause'))
	return A+'.'
_PAIRS_CACHE={}
BODY_DELETE_OPS='delete','delete_paragraph','delete_span'
NUM_UNIT='(?P<unit>ימים|יום|שבועות|שבוע|חודשים|חודש|שנים|שנה|days?|weeks?|months?|years?)'
NUM_RX=[('pct',re.compile('(?P<n>\\d+(?:[.,]\\d+)?)\\s*(?:%|אחוז|percent\\b|per cent\\b)',re.I)),('dur',re.compile('(?P<n>\\d+)\\s*(?:\\(\\s*\\w+\\s*\\)\\s*)?-?\\s*'+NUM_UNIT,re.I)),('amt',re.compile('(?:[$€₪]\\s*(?P<n>\\d[\\d,]*(?:\\.\\d+)?)|(?P<n2>\\d[\\d,]*(?:\\.\\d+)?)\\s*(?:ש\\"ח|ש״ח|₪|NIS\\b|ILS\\b|USD\\b|EUR\\b|דולר|אירו|יורו))',re.I))]
UNIT_CLASS={'יום':'d','ימים':'d','day':'d','days':'d','שבוע':'w','שבועות':'w','week':'w','weeks':'w','חודש':'m','חודשים':'m','month':'m','months':'m','שנה':'y','שנים':'y','year':'y','years':'y'}
def interaction_map(path=None):
	A=path;A=A or os.path.join(HERE,'interaction_pairs.json')
	if A in _PAIRS_CACHE:return _PAIRS_CACHE[A]
	B=None
	try:
		with io.open(A,encoding='utf-8')as E:C=json.load(E)
		def D(v):B=tuple(A.lower()for A in v.get('he')or());A=v.get('en')or();C=re.compile('|'.join(('(?<![A-Za-z])'if A[:1].isalnum()else'')+re.escape(A)for A in A),re.I)if A else None;return B,C
		B={'raw':C,'fam':{A:D(B)for(A,B)in(C.get('families')or{}).items()},'dup':{A:D(B)for(A,B)in(C.get('duplicate_mechanisms')or{}).items()},'pairs':[tuple(A)for A in C.get('pairs')or[]]}
	except(OSError,ValueError):B=None
	_PAIRS_CACHE[A]=B;return B
def _hits(text,comp):
	C,A=comp;D=(text or'').lower();B=sum(1 for A in C if A in D)
	if A:B+=len({A.group(0).lower()for A in A.finditer(text or'')})
	return B
def _decision_text(d,theirs):
	A=theirs;D=A[d['para']]if isinstance(d.get('para'),int)and 0<=d['para']<len(A)else'';B=''
	for C in('new_text','new','text'):
		if d.get(C):B=d[C];break
	return B,D
def _changes_body(d,theirs):A,B=_decision_text(d,theirs);return bool(A)or d.get('op')in BODY_DELETE_OPS
def _locate(accepted,d,new):
	B=accepted;C=_norm_ws(new)[:50]if new else''
	if C:
		for(D,E)in enumerate(B):
			if C in _norm_ws(E):return D
	A=d.get('para')if isinstance(d.get('para'),int)else d.get('after_para');return A if isinstance(A,int)and 0<=A<len(B)else None
def _entry_covers(e,idx):
	if not isinstance(e,dict):return False
	if e.get('para')==idx:return True
	A=e.get('paras');return isinstance(A,(list,tuple))and idx in A
def _open_item_listed(state,d):
	C=state;D=list((C or{}).get('open_items')or[])+list(((C or{}).get('meta')or{}).get('open_items')or[]);A=d.get('id')
	for B in D:
		if isinstance(B,dict)and A and(B.get('decision_id')==A or B.get('interaction_of')==A or str(A)in str(B.get('item',''))):return True
	return False
def review_interactions(out,accepted,theirs,decisions,state,mode=None,imap=None,cap=8):
	N=theirs;I=accepted;F=decisions;C=out;A=imap;A=A or interaction_map();J=mode!='work'
	if not A:finding(C,'INTERACTION_MAP_MISSING','interaction_pairs.json חסר או פגום: בדיקת העקיפות לא רצה','');return
	F=[A for A in F if isinstance(A,dict)];a={A.get('id')for A in F if A.get('id')}
	for B in F:
		if not _changes_body(B,N):continue
		D,b=_decision_text(B,N);c=D+'\n'+b;T={A for(A,B)in A['fam'].items()if _hits(c,B)}
		if not T:continue
		K=_locate(I,B,D);E={}
		for(U,V,f)in A['pairs']:
			for(d,O)in((U,V),(V,U)):
				if d not in T or O not in A['fam']:continue
				e=sorted(((_hits(C,A['fam'][O]),B)for(B,C)in enumerate(I)if B!=K),key=lambda r:(-r[0],r[1]))
				for(W,P)in[A for A in e if A[0]>0][:4]:
					if P not in E or E[P][1]<W:E[P]=O,W
		E=dict(sorted(E.items(),key=lambda kv:(-kv[1][1],kv[0]))[:cap]);L=B.get('interactions');L=L if isinstance(L,list)else[]
		for(Q,(G,g))in sorted(E.items()):
			X=[A for A in L if _entry_covers(A,Q)];M='%s, פסקה %d'%(B.get('id'),Q);R=A['raw']['families'][G].get('label',G)
			if not X:finding(C,'INTERACTION_UNCHECKED','ההכרעה משנה נוסח, ופסקה %d נוגעת ב"%s" ויכולה לצמצם או לעקוף אותה, ואין ב-interactions[] ערך שמכסה אותה (para, bypass, answer)'%(Q,R),M,J);continue
			Y=X[0];H=str(Y.get('bypass',''))
			if not(H in('no','open')or H.startswith('fixed:')and H[6:]in a):finding(C,'INTERACTION_UNCHECKED','bypass חייב להיות no, open או fixed:<מזהה הכרעה קיימת>; נמצא %r'%H,M,J)
			elif not str(Y.get('answer')or'').strip():finding(C,'INTERACTION_UNCHECKED','חסרה התשובה לשאלה: האם הצד השני עדיין יכול להגיע לתוצאה שהפלייבוק מבקש למנוע באמצעות הוראה אחרת (answer)',M,J)
			elif H=='open'and not _open_item_listed(state,B):finding(C,'INTERACTION_OPEN_UNLISTED','עקיפה פתוחה שאינה ברשימת הפריטים הפתוחים (open_items עם decision_id)',M,J)
	for B in F:
		D,h=_decision_text(B,N)
		if not D:continue
		K=_locate(I,B,D)
		for(G,Z)in A['dup'].items():
			if not _hits(D,Z):continue
			S=[A for(A,B)in enumerate(I)if _hits(B,Z)and(K is None or abs(A-K)>2)]
			if S:R=A['raw']['duplicate_mechanisms'][G].get('label',G);finding(C,'DUPLICATE_MECHANISM','ההכרעה מוסיפה מנגנון (%s) ובפסקה %d יש מנגנון נוסף מאותו סוג: לאחד, להפנות או לוודא שהם אינם מתנגשים'%(R,S[0]),'%s, פסקה %d'%(B.get('id'),S[0]))
def _claims(rx_list,text):
	for B in rx_list or():
		A=re.search(B,text,re.I)
		if A:return A.group(0)
def _eq_values(d):
	B=d.get('equivalence')
	if not isinstance(B,dict):return
	C={}
	for(D,A)in B.items():
		if isinstance(A,dict):A=A.get('value')or A.get('result')
		C[D]=str(A or'').lower()
	return C
def review_overclaim(out,decisions,mode=None,imap=None):
	E=imap;E=E or interaction_map();A=((E or{}).get('raw')or{}).get('overclaim')or{}
	if not A:return
	I=mode!='work'
	for B in decisions:
		if not isinstance(B,dict):continue
		F=B.get('external_comment')or''
		if not F:continue
		G,M=_decision_text(B,[]);J=_eq_values(B);C=[A for(A,B)in(J or{}).items()if B=='narrower'];K=bool(C)or str(B.get('coverage')or'').lower()=='partial';D=_claims(A.get('mutual',{}).get('he',[])+A.get('mutual',{}).get('en',[]),F);H=_claims(A.get('total',{}).get('he',[])+A.get('total',{}).get('en',[])+A.get('none',{}).get('he',[])+A.get('none',{}).get('en',[]),F);L=_claims(A.get('symmetric_markers',{}).get('he',[])+A.get('symmetric_markers',{}).get('en',[]),G)
		if D and G and(not L or C):finding(out,'BUBBLE_OVERCLAIM','הבועה טוענת "%s" (הדדיות), והנוסח שהוכנס אינו סימטרי או שהשקילות צרה יותר (%s): לתאר רק את מה שתוקן'%(D,', '.join(C)or'אין ניסוח הדדי'),B.get('id'),I)
		elif(D or H)and K:finding(out,'BUBBLE_OVERCLAIM','הבועה טוענת טענה מוחלטת ("%s") והשינוי חלקי%s: לתאר במדויק מה תוקן ומה לא'%(D or H,' (צר יותר ב: %s)'%', '.join(C)if C else''),B.get('id'))
def _numbers(text):
	C=set()
	for(D,E)in NUM_RX:
		for F in E.finditer(text or''):
			B=F.groupdict();A=(B.get('n')or B.get('n2')or'').replace(',','');G=UNIT_CLASS.get((B.get('unit')or'').lower(),'')if D=='dur'else''
			if A:
				try:A=str(float(A)).rstrip('0').rstrip('.')
				except ValueError:pass
				C.add((D,A,G))
	return C
def review_numbers(out,theirs,decisions,state,core,mode=None):
	A=state;I=mode!='work';A=A or{};D=A.get('meta')or{};E=[json.dumps(core or{},ensure_ascii=False),'\n'.join(theirs),json.dumps(A.get('client_answers')or[],ensure_ascii=False),json.dumps(A.get('user_decisions')or[],ensure_ascii=False),json.dumps(D.get('deal_card')or A.get('deal_card')or D.get('deal_context')or{},ensure_ascii=False)];F=set()
	for B in E:F|=_numbers(B)
	G=set()
	for B in E[2:]:G|=set(re.findall('(?<![\\d.,])\\d+(?![\\d])',B))
	for(H,J)in our_texts(decisions):
		if str(H.get('number_source')or'').strip():continue
		for(K,C,L)in sorted(_numbers(J)):
			if(K,C,L)not in F and C not in G:finding(out,'NUMBER_UNSOURCED','בנוסח שהכנסנו מספר (%s) שאינו בגרעין, בתשובות הלקוח, בכרטיס העסקה או בהסכם שהתקבל: לכתוב [להשלים] ולפתוח פריט פתוח, ולא להמציא'%C,H.get('id'),I);break
VERIFY_CHECKS='contradiction_after_accept','bubble_vs_change','reasoning_vs_position','syntax_break','bubble_exploitable','scope_vs_paper_type','legal_review_scope','definition_uses','bypass_remaining','protection_incomplete','survival_numbering_refs','external_documents','rule_coverage_vs_text'
VERIFY_SEVERITIES='open','note'
def validate_verify_findings(data):
	E=data;A=[]
	if not isinstance(E,dict):return['הקובץ אינו אובייקט JSON']
	if E.get('verifier')!='n9':A.append('verifier חייב להיות n9')
	if not isinstance(E.get('findings'),list):A.append('findings חייב להיות רשימה');return A
	for(F,B)in enumerate(E['findings']):
		D='findings[%d]'%F
		if not isinstance(B,dict):A.append('%s אינו אובייקט'%D);continue
		if B.get('check')not in VERIFY_CHECKS:A.append('%s: check לא מוכר: %r (אחד מ: %s)'%(D,B.get('check'),', '.join(VERIFY_CHECKS)))
		if B.get('severity')not in VERIFY_SEVERITIES:A.append('%s: severity חייב להיות open או note'%D)
		for C in('where','quote','issue'):
			if not isinstance(B.get(C),str)or not B.get(C).strip():A.append('%s: חסר %s (ממצא בלי ציטוט ומיקום אינו ממצא)'%(D,C))
		for C in('decision','new_text','replace_with','op','decision_code'):
			if C in B:A.append('%s: המאמת אינו מכריע ואינו מנסח: השדה %s אסור'%(D,C))
	return A
def main(argv=None):
	sys.dont_write_bytecode=True;sys.stdout.reconfigure(encoding='utf-8',errors='replace');from common.cli import load_docx_or_explain as N;B=argparse.ArgumentParser(description=__doc__.split('\n')[0]);B.add_argument('--work',help='קובץ העבודה (לא נדרש עם --hidden-only)');B.add_argument('--received',required=True);B.add_argument('--decisions',help='קובץ ההכרעות (לא נדרש עם --hidden-only)');B.add_argument('--state');B.add_argument('--core');B.add_argument('--manifest',help='corpus-manifest.json: שמות הצדדים בהסכמים החתומים');B.add_argument('--hidden-only',action='store_true',help='רק סריקת הטקסט המוסתר בטיוטה שהתקבלה');B.add_argument('--mode',choices=('work','send'),default='send',help='work: ממצא שחוסם רק משלוח (BUB_UNSOURCED_FACT) הוא לבדיקה. ברירת מחדל: send');B.add_argument('--anchors',action='store_true',help='בקליטה: עוגני הזמן בנייר שלהם שכבר עברו או ריקים (כלל 4). כל ממצא הוא שאלה במנת השאלות');B.add_argument('--profile',help='פרופיל-לקוח.json: השמות שלנו, כדי שבועה שלנו לא תיחשב מקור של הצד שכנגד');B.add_argument('--definition-changes',action='store_true',help='JSON: כל הגדרה שתוקנה בקובץ העבודה, וכל המופעים של המונח בנוסח המתקבל (DEF_CHANGED_USAGES)');B.add_argument('--annotate-definitions',action='store_true',help='מוסיף לקובץ ההכרעות (--decisions, נכתב במקומו) את שורת DEF_CHANGED_USAGES בבועה הפנימית של כל הכרעה שמשנה הגדרה, לפני apply_redlines.py');B.add_argument('--validate-findings',help='קובץ הממצאים של המאמת העצמאי (n9-verify.md): בדיקת מבנה בלבד');B.add_argument('--lang',choices=('he','en'),default='he',help='שפת שורת DEF_CHANGED_USAGES בבועה הפנימית');A=B.parse_args(argv)
	if A.validate_findings:
		F=load(A.validate_findings);G=validate_verify_findings(F)if F is not None else['הקובץ חסר או אינו JSON']
		for T in G:print('  [VERIFY_SCHEMA] %s'%T)
		if not G:U=sum(1 for A in F['findings']if A.get('severity')=='open');print('תקין: %d ממצאים, %d פתוחים'%(len(F['findings']),U))
		return 3 if G else 0
	if A.anchors:
		if not A.received or not os.path.exists(A.received):print('אינו קיים או חסר: %s'%A.received);return 2
		H,I,J=N(A.received,loader=False)
		if H is None:print(I);return J
		print(json.dumps(time_anchors(dt.received_paragraphs(A.received)),ensure_ascii=False,indent=1));return 0
	V=(A.received,)if A.hidden_only else(A.work,A.received,A.decisions)
	for D in V:
		if not D or not os.path.exists(D):print('אינו קיים או חסר: %s'%D);return 2
	for D in(A.received,)if A.hidden_only else(A.work,A.received):
		H,I,J=N(D,loader=False)
		if H is None:print(I);return J
	if A.hidden_only:print(json.dumps(hidden_scan(A.received),ensure_ascii=False,indent=1));return 0
	C=load(A.decisions)
	if A.definition_changes or A.annotate_definitions:
		O=C.get('decisions',[])if isinstance(C,dict)else C;P=dt.received_paragraphs(A.received);Q=dt.accept_all(A.work)
		try:K=numbered_labels(A.received)
		except Exception:K=None
		if A.annotate_definitions:
			W=annotate_definition_changes(O,P,Q,K,A.lang)
			with open(A.decisions,'w',encoding='utf-8')as X:json.dump(C,X,ensure_ascii=False,indent=1)
			print('עודכנו %d הכרעות בשורת %s'%(W,DEF_USAGES_MARK));return 0
		print(json.dumps(definition_changes(P,Q,O,K),ensure_ascii=False,indent=1));return 0
	R=[C.get('author')]if isinstance(C,dict)else[]
	if A.profile:from lawyer import lawyer_view as Y;L=Y(load(A.profile)or{});R+=[L.get('lawyer_name'),L.get('lawyer_name_en')]+list(L.get('lawyer_aliases')or[])
	M=run_checks(A.work,A.received,C.get('decisions',[])if isinstance(C,dict)else C,load(A.state),attach_related(load(A.core),A.core),load(A.manifest),mode=A.mode,profile={'lawyer_names':[A for A in R if A]})
	for E in M:print('%s [%s] %s%s'%('חוסם'if E['blocking']else'לבדיקה',E['code'],E['message'],'  (%s)'%E['where']if E['where']else''))
	S=[A for A in M if A['blocking']];print('ממצאים: %d, חוסמים: %d'%(len(M),len(S)));return 3 if S else 0
if __name__=='__main__':sys.exit(main())
