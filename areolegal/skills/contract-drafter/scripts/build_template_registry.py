# -*- coding: utf-8 -*-
# Copyright (c) Areo. All rights reserved. Licensed under the terms at https://areo.co.il/legal/terms
import argparse,hashlib,io,json,os,re,sys,zipfile
from datetime import datetime
try:sys.stdout.reconfigure(encoding='utf-8')
except(AttributeError,ValueError):pass
PROTECTED_EXT='.docx','.doc','.docm','.dotx','.pdf','.xlsx','.pptx'
def _path_key(p):return os.path.normcase(os.path.realpath(os.path.abspath(p)))
def out_problem(out,inputs=(),force=False):
	A=out
	if not A or not str(A).strip():return'חסר נתיב פלט'
	B=_path_key(A)
	for C in inputs or():
		if C and _path_key(C)==B:return'נתיב הפלט הוא קובץ קלט (%s). פלט לעולם אינו נכתב על קובץ קלט'%C
	if not force and os.path.isfile(B)and os.path.splitext(B)[1].lower()in PROTECTED_EXT:return'נתיב הפלט הוא מסמך קיים (%s). לדריסה מכוונת, הוסיפו --force'%A
def guard_out(out,inputs=(),force=False):
	A=out_problem(out,inputs,force)
	if A:print('הפלט לא נכתב: '+A);sys.exit(2)
	return out
PLACEHOLDER=re.compile('\\[\\s*להשלים\\s*(?::[^\\]\\n]{0,120})?\\]|\\[\\s*(?i:to\\s+complete)\\s*(?::[^\\]\\n]{0,120})?\\]|_{4,}|\\bXXX+\\b|\\[\\s{2,}\\]|\\[●\\]|\\[\\*+\\]')
SIGN_DATE=re.compile('IN\\s+WITNESS\\s+WHEREOF|ולראי{1,2}ה\\s+(?:באו|באנו|חתמו|חתמנו)|ובאו\\s+הצדדים\\s+על\\s+החתום|חתימת\\s+הצדדים|(?m:^)[ \\t]*(?-i:Signed|SIGNED|Executed|EXECUTED)\\s+(?:by|for\\s+and\\s+on\\s+behalf)\\b|\\b(?:have|has)\\s+(?:duly\\s+)?executed\\s+this\\b|(?<![\\w/])/s/|signature\\s+of\\s+the\\s+parties|(?:נחתם|תאריך\\s+החתימה|Signed\\s+on|Date\\s+of\\s+signature)\\s*[:\\-]?\\s*\\d',re.I)
LINE_RUN=re.compile('_{4,}|\\.{6,}')
SIGN_TAIL=300
BLANK_PARTY=re.compile('(?:_{4,}|\\.{6,}|\\[[^\\]]{0,40}\\]|<<[^>]{1,40}>>|\\{\\{[^}]{1,40}\\}\\})[^"״“()\\n]{0,60}[()]\\s*(?:להלן\\s*[:\\-]?\\s*|hereinafter(?:\\s+(?:referred\\s+to\\s+as|called))?\\s*[:,]?\\s*(?:the\\s+)?|the\\s+)?["״“]([^"״”()]{2,40})["״”]',re.I)
PROCEDURE_SIGN=re.compile('המציע|הליך תחרותי|\\bcompetitive\\s+procedure\\b|\\bbidders?\\b|\\bRFP\\b|request\\s+for\\s+proposals?|invitation\\s+to\\s+(?:bid|tender)',re.I)
def placeholder_count(text):B=len(text)-SIGN_TAIL;return sum(1 for A in PLACEHOLDER.finditer(text)if not(A.start()>=B and LINE_RUN.fullmatch(A.group(0))))
MARKERS_HE=['בין','לבין','הצדדים','הואיל','מוסכם','התחייבות','סעיף','בתוקף','תקופת ההסכם','הפרה','שיפוי','סודיות','ולראיה','נספח','הודעה מוקדמת','אחריות','תמורה']
MARKERS_EN=['whereas','the parties','agreement','hereby','shall','termination','in witness','governing law','confidential','indemnif','liability','warrant','herein','thereof','effective date','exhibit','schedule','written notice','breach','assignment','entire agreement','force majeure']
NON_CONTRACT_TITLES=re.compile('נוהל|מדריך|הצעת\\s*מחיר|מצגת|סיכום\\s*פגישה|פרוטוקול|דוח|טיוטת\\s*מייל|readme|פלייבוק|playbook|מערכת\\s*התרעות|מתווה|לוח\\s*מועדים|דשבורד|workspace|guide|manual|proposal|quote|presentation|minutes|report|skill',re.I)
CONTRACT_TITLE=re.compile('הסכם|חוזה|תוספת|נספח|agreement|contract|addendum|amendment|\\bagr\\b|\\bmou\\b|\\bloi\\b|license',re.I)
def is_contract(text,name,ext):
	if ext in('.md',):return False,'קובץ Markdown, אינו מסמך חוזי'
	if NON_CONTRACT_TITLES.search(name):return False,'שם הקובץ מעיד על מסמך שאינו חוזי'
	if len(text)<1200:return False,'המסמך קצר מדי מכדי להיות הסכם'
	C=text.lower();D=sum(1 for A in MARKERS_HE if A in C);E=sum(1 for A in MARKERS_EN if A in C)
	if D>=E:A,F,B=D,len(MARKERS_HE),'עברית'
	else:A,F,B=E,len(MARKERS_EN),'אנגלית'
	G=bool(CONTRACT_TITLE.search(name));H=3 if G else 5
	if A<H:return False,'לא אותרו סימני מסמך חוזי ב%s (%d מתוך %d)'%(A and B or B,A,F)
	return True,''
AMEND=re.compile("תיקון\\s*(?:מס(?:פר|['׳])?\\.?\\s*)?\\d*\\s*ל(?!חוק|תקנות|פקודת|פקודה|צו\\b)|נספח\\s+תיקון|תוספת\\s+להסכם|הסכם\\s+תיקון|\\bamendment\\s*(?:no\\.?\\s*\\d+\\s*)?to\\b|^\\s*(?:(?:first|second|third|\\d+(?:st|nd|rd|th)?)\\s+)?addendum\\b\\s*(?:(?:no\\.?|number|#)\\s*\\d+\\s*)?to\\b",re.I)
HE=re.compile('[\u0590-\u05ff]')
LAT=re.compile('[A-Za-z]')
ISSUER_WORDS={'issuer','contracting_authority','inviting_party','מזמין','הגוף המזמין'}
MUTUAL=re.compile('(?<![\\w\u0590-\u05ff])(?:mutual|bilateral|reciprocal|הדדי|הדדית|דו[\\s\\-]?צדדי(?:ת)?)(?![\\w\u0590-\u05ff])(?!\\s+(?:covenants|promises|obligations|consent|understanding))',re.I)
ONE_WAY=re.compile('(?<![\\w\u0590-\u05ff])(?:one[\\s\\-]way|unilateral|חד[\\s\\-]?צדדי(?:ת)?)(?![\\w\u0590-\u05ff])',re.I)
def _word_re(w,suffix):
	A=w.lower()
	if re.search('[a-z]',A):B='(?<![a-z0-9])'+re.escape(A)+'(?![a-z0-9])'
	else:B='(?<![\u0590-\u05ff])[ובלמהשכ]{0,2}'+re.escape(A)+(''if suffix else'(?![\u0590-\u05ff])')
	return re.compile(B)
_WORD_CACHE={}
def word_count(w,low,suffix=True):
	A=suffix
	if(w,A)not in _WORD_CACHE:_WORD_CACHE[w,A]=_word_re(w,A)
	return len(_WORD_CACHE[w,A].findall(low))
FAMILIES=[]
def docx_text(path,limit=200000):
	E=limit
	try:
		with zipfile.ZipFile(path)as B:
			G=[A for A in B.namelist()if A.startswith('word/')and A.endswith('.xml')];C=[]
			for F in['word/document.xml']+[A for A in G if A!='word/document.xml']:
				if F not in B.namelist():continue
				A=B.read(F).decode('utf-8','ignore');C.append(A)
				if sum(len(A)for A in C)>E*3:break
			A=''.join(C);H='<w:ins 'in A or'<w:del 'in A;I='word/comments.xml'in B.namelist();D=re.sub('<[^>]+>',' ',A);D=re.sub('\\s+',' ',D);return D[:E],H,I
	except Exception as J:return'',False,False
def docx_paragraphs(path,limit=4000,mode='final'):
	C=[]
	try:
		with zipfile.ZipFile(path)as D:
			if'word/document.xml'not in D.namelist():return C
			E=D.read('word/document.xml').decode('utf-8','ignore')
		for A in E.split('</w:p>')[:limit]:
			if mode=='final':A=re.sub('<w:del\\b[^>]*>.*?</w:del>','',A,flags=re.S)
			elif mode=='base':A=re.sub('<w:ins\\b[^>]*>.*?</w:ins>','',A,flags=re.S);A=re.sub('<w:delText([^>]*)>','<w:t\\1>',A);A=re.sub('</w:delText>','</w:t>',A)
			B=re.sub('<[^>]+>','',''.join(re.findall('<w:t[^>]*>(.*?)</w:t>',A,re.S)));B=re.sub('\\s+',' ',B).strip()
			if B:C.append(B)
	except Exception:pass
	return C
def docx_num_formats(path):
	try:
		with zipfile.ZipFile(path)as A:
			if'word/numbering.xml'not in A.namelist():return[]
			B=A.read('word/numbering.xml').decode('utf-8','ignore')
		C=re.findall('<w:numFmt\\s+w:val="([^"]+)"',B);D=re.findall('<w:lvlText\\s+w:val="([^"]*)"',B);return list(zip(C[:9],D[:9]))
	except Exception:return[]
def docx_revisions(path):
	A={'authors_ins':{},'authors_del':{},'n_ins':0,'n_del':0,'base_text':'','final_text':''}
	try:
		with zipfile.ZipFile(path)as D:
			if'word/document.xml'not in D.namelist():return A
			B=D.read('word/document.xml').decode('utf-8','ignore')
	except Exception:return A
	for(H,E)in(('ins','authors_ins'),('del','authors_del')):
		for F in re.findall('<w:%s [^>]*w:author="([^"]+)"'%H,B):A[E][F]=A[E].get(F,0)+1
	A['n_ins']=sum(A['authors_ins'].values());A['n_del']=sum(A['authors_del'].values())
	def G(blob,drop_tag,keep_tag):C=drop_tag;A=blob;A=re.sub('<w:%s\\b[^>]*>.*?</w:%s>'%(C,C),'',A,flags=re.S);B=' '.join(re.findall('<w:t[^>]*>(.*?)</w:t>',A,re.S));B=re.sub('<[^>]+>','',B);return re.sub('\\s+',' ',B).strip()
	C=re.sub('<w:delText([^>]*)>','<w:t\\1>',B);C=re.sub('</w:delText>','</w:t>',C);A['base_text']=G(C,'ins','del')[:200000];A['final_text']=G(B,'del','ins')[:200000];return A
def pdf_text(path):
	try:
		try:import pymupdf as A
		except ImportError:import fitz as A
		with A.open(path)as C:return'\n'.join(A.get_text()for A in C)[:200000],''
	except ImportError:pass
	except Exception:return'','לא ניתן היה לפתוח את ה-PDF'
	try:from pypdf import PdfReader as D;B='\n'.join(A.extract_text()or''for A in D(path).pages)[:200000]
	except Exception:return'','אין בסביבה ספרייה לקריאת PDF (pymupdf)'
	if HE.search(B):return'','PDF בעברית, ואין pymupdf: הטקסט יוצא בסדר הפוך'
	return B,''
READ_EXT='.docx','.txt','.md','.pdf'
AREO_DIRS='Areo-נתונים',
AREO_OUTPUT=re.compile('דף ליווי|cover note|עמדות[\\s_-]*לאישור|positions[\\s_-]*for[\\s_-]*approval|areo workspace|מרכז היערכות|prep cent(?:er|re)|דוח שלמות|completeness report|translation-integrity|integrity-|risk-register|תזכיר פנימי|internal memo|\\.report\\.json$',re.I)
COUNTERPARTY_DIR=re.compile('מהצד[\\s_-]*שכנגד|הצד[\\s_-]*השני|מהצד[\\s_-]*השני|counterparty|from[\\s_-]*them|their[\\s_-]*paper',re.I)
def eml_parts(path):
	import email;from email import policy as G
	with open(path,'rb')as H:C=email.message_from_binary_file(H,policy=G.default)
	B=''
	try:
		A=C.get_body(preferencelist=('plain','html'))
		if A is not None:
			B=A.get_content()
			if A.get_content_type()=='text/html':B=re.sub('<[^>]+>',' ',B)
	except Exception:B=''
	D=[]
	for A in C.iter_attachments():
		E=A.get_filename()or''
		try:F=A.get_payload(decode=True)or b''
		except Exception:F=b''
		if E:D.append((os.path.basename(E),F))
	return re.sub('\\s+',' ',B or'').strip(),D
def eml_attachment_dir(path):import tempfile as B;C=hashlib.sha256(os.path.abspath(path).encode('utf-8','ignore')).hexdigest()[:12];A=os.path.join(B.gettempdir(),'areo-eml',C);os.makedirs(A,exist_ok=True);return A
def scan_items(folder,queue):
	G=folder;C=queue
	for(B,H,O)in os.walk(G):
		for P in[A for A in H if A in AREO_DIRS]:C.append({'file':P+'/','folder':B,'why':'תיקיית הנתונים של Areo אינה מקור','excluded':True})
		H[:]=sorted(A for A in H if A not in AREO_DIRS and not A.startswith('.'));Q=bool(COUNTERPARTY_DIR.search(os.path.relpath(B,G)))if B!=G else False
		for A in sorted(O):
			if A.startswith('~$')or A.startswith('.'):continue
			E=os.path.join(B,A);I=os.path.splitext(A)[1].lower()
			if AREO_OUTPUT.search(A):C.append({'file':A,'folder':B,'why':'תוצר של Areo, אינו מקור','excluded':True});continue
			K={'paper':'counterparty','paper_basis':'folder'}if Q else{}
			if I=='.eml':
				try:R,L=eml_parts(E)
				except Exception as S:C.append({'file':A,'folder':B,'why':'לא ניתן היה לקרוא את המייל (%s)'%type(S).__name__});continue
				F=[(A,B)for(A,B)in L if os.path.splitext(A)[1].lower()in READ_EXT]
				for(D,J)in L:
					if(D,J)not in F:C.append({'file':'%s / %s'%(A,D),'folder':B,'why':'צרופה מסוג שאינו נקרא (%s)'%(os.path.splitext(D)[1]or'בלי סיומת')})
				if not F:C.append({'file':A,'folder':B,'why':'מייל בלי צרופה שאפשר לקרוא; הגוף אינו הסכם'if R else'מייל בלי גוף ובלי צרופה שאפשר לקרוא'})
				M=eml_attachment_dir(E)if F else None
				for(D,J)in F:
					N=os.path.join(M,D)
					with open(N,'wb')as T:T.write(J)
					yield(D,M,N,dict(K,source_email=E))
				continue
			if I not in READ_EXT:C.append({'file':A,'folder':B,'why':'סוג קובץ שאינו נקרא (%s)'%(I or'בלי סיומת')});continue
			yield(A,B,E,K)
def read_text(path):
	A=path;B=os.path.splitext(A)[1].lower()
	if B=='.docx':return docx_text(A)
	if B=='.pdf':return pdf_text(A)[0],False,False
	if B in('.txt','.md'):
		try:return io.open(A,encoding='utf-8',errors='ignore').read()[:200000],False,False
		except Exception:return'',False,False
	return'',False,False
AGR_WORD=re.compile('(?:הסכם|חוזה|agreement|contract)\\s*',re.I)
NOISE=re.compile('redline|final|draft|signed|v\\d|\\d{1,2}[-.]\\d{1,2}[-.]\\d{2,4}|טיוטה|חתום|סופי|מעודכן|עותק|\\(\\d+\\)',re.I)
HE_INITIAL_NOUN=re.compile('^(?:הת[א-ת]{2,}|ה[א-ת]{2,4}ה|ה[א-ת]{2,3}ת)$')
def strip_article(word):
	A=word
	if A.startswith('הה'):return A[1:]
	if A.startswith('ה')and len(A)>3 and not HE_INITIAL_NOUN.match(A):return A[1:]
	return A
def derive_family_name(fname):
	A=os.path.splitext(fname)[0];A=NOISE.sub(' ',A);C=re.split('\\s+[-\\u2013\\u2014]\\s+',A,maxsplit=1)
	if len(C)==2:
		E=AGR_WORD.search(C[0])
		if E and(C[0][E.end():].strip()or C[0][:E.start()].strip()):A=C[0]
	A=re.sub('[_\\-]+',' ',A);B=AGR_WORD.search(A)
	if B and not A[B.end():].strip()and A[:B.start()].strip():A,B=A[:B.start()],None
	elif B:A=A[B.end():]
	G={'for','of','the','and','with','between','to','by','on','בין','עם','של','על','לבין','מול'};D=[A for A in re.split('\\s+',A.strip())if len(A)>1 and A.lower()not in G]
	if B and D:D[0]=strip_article(D[0])
	F=' '.join(D[:2]).strip(' ,.-');return F if 2<=len(F)<=40 else None
def pick_family(name,head,body):
	for(B,C)in((name,'נגזר משם הקובץ, טעון אישור המשתמש'),((head or'').strip().splitlines()[0]if(head or'').strip()else'','נגזר מכותרת המסמך, טעון אישור המשתמש')):
		A=derive_family_name(B)if B else None
		if A:return A,[A],C
	return None,[],'לא זוהתה משפחה'
def pick_role(text):return[]
def normalize_role(value):
	A=(value or'').strip()
	if not A or A.lower()=='other':return
	return A
def playbook_roles(path):
	D=[]
	try:E=json.load(io.open(path,encoding='utf-8'))
	except Exception:return D
	C=[E]
	while C:
		B=C.pop()
		if isinstance(B,dict):
			for A in B.get('contract_families')or[]:
				if isinstance(A,dict)and normalize_role(A.get('company_role_code')):F=[A.get('contract_family_name'),A.get('contract_family_id')]+list(A.get('family_aliases')or[]);D.append(([A for A in F if A],normalize_role(A.get('company_role_code'))))
			C.extend(A for A in B.values()if isinstance(A,(dict,list)))
		elif isinstance(B,list):C.extend(B)
	return D
def family_matches(family,names):
	C=family
	if not C:return False
	D=lambda s:re.sub('^(?:הסכמי|הסכם)\\s+|\\s+agreements?$|_',' ',s.lower()).strip();B=D(C)
	for A in names:
		A=D(str(A))
		if B and A and(B==A or word_count(B,A)or word_count(A,B)):return True
	return False
def parse_roles(values):
	B=[]
	for D in values or[]:
		C,E,A=D.rpartition('=');A=normalize_role(A)
		if A:B.append(([C.strip()]if C.strip()else None,A))
	return sorted(B,key=lambda x:x[0]is None)
def resolve_role(family,body,role_arg,pb_roles):
	C=family;D=pick_role(body)
	for(B,A)in role_arg:
		if B is None or family_matches(C,B):return A,'המשתמש (--role)',[A]+[B for B in D if B!=A]
	for(B,A)in pb_roles:
		if family_matches(C,B):return A,'company_role_code בפלייבוק',[A]+[B for B in D if B!=A]
	return None,'תפקיד לא ידוע, שאלה למשתמש',[]
def _alias_key(g):g=re.sub('\\s+',' ',re.sub('_{2,}|\\.{3,}',' ',g or'')).strip(' .,:;').lower();return re.sub('^the\\s+','',g)
def blank_parties(text):
	A=[]
	for C in BLANK_PARTY.finditer((text or'')[:2500]):
		B=re.sub('\\s+',' ',C.group(1)).strip()
		if B and B not in A:A.append(B)
	return A
DEFINED_ALIAS=re.compile('(?:להלן\\s*[:\\-]?\\s*|hereinafter(?:\\s+(?:referred\\s+to\\s+as|called))?\\s*[:,]?\\s*(?:the\\s+)?|the\\s+)?["״“]([^"״”()]{2,40})["״”]',re.I)
def whose_template(blanks,role,body=''):
	if not role:return
	A=_alias_key(role);B={A,'ה'+A};C={_alias_key(A)for A in blanks or()};D={_alias_key(A.group(1))for A in DEFINED_ALIAS.finditer((body or'')[:2500])}
	if C&B:return'counterparty'
	if C and D&B:return'company'
def paper_owner(name,body,blanks,role,role_basis):
	B=role;D=B and not str(role_basis or'').startswith('תפקיד לא ידוע');A=whose_template(blanks,B,body)if D else None
	if A=='counterparty':return A,'הצד שפרטיו ריקים בפתיח הוא הצד של החברה'
	if A=='company':return A,'הצד שפרטיו ריקים בפתיח הוא הצד שכנגד'
	C=PROCEDURE_SIGN.search(os.path.splitext(name)[0])or PROCEDURE_SIGN.search(body or'')
	if C and(B or'').strip().lower()not in ISSUER_WORDS:return'counterparty','נוסח של הליך תחרותי (%s), והחברה אינה הגוף המזמין'%C.group(0)
	return None,None
def mutuality(name,head):
	A=name+'\n'+head
	if ONE_WAY.search(A):return'one_way'
	if MUTUAL.search(A):return'mutual'
def language(text):
	A=len(HE.findall(text));B=len(LAT.findall(text))
	if A and B and min(A,B)/max(A,B)>.25:return'bilingual'
	return'he'if A>=B else'en'
CORP_SUFFIX=re.compile('\\s*\\(?(?:בע[\\"\'״׳]?מ|ע[\\"\'״׳]ר|חל[\\"\'״׳]?צ|ltd\\.?|limited|inc\\.?|llc|plc|gmbh|cio|cic|corp(?:oration)?\\.?|co\\.)\\)?\\s*$',re.I)
RECITALS=re.compile('הואיל|whereas|recitals|מבוא',re.I)
def _norm_name(v):v=re.sub('[\\"\'״׳`]','',str(v or'').lower());return re.sub('\\s+',' ',v).strip()
def company_markers(profile_path,extra):
	B=profile_path;A={}
	if B and os.path.exists(B):
		try:A=json.load(io.open(B,encoding='utf-8'))
		except Exception:A={}
	C,D=[],[]
	for G in[A.get('organization_name'),A.get('organization_name_en')]+list(extra or[]):
		E=_norm_name(CORP_SUFFIX.sub('',str(G or'').strip()))
		if len(E)>=3 and E not in C:C.append(E)
	for H in(A.get('registration_number'),A.get('organization_id')):
		F=re.sub('\\D','',str(H or''))
		if len(F)>=6 and F not in D:D.append(F)
	return C,D
def on_company_paper(body,names,regs):
	B=names
	if not B and not regs:return
	A=body[:3000];C=RECITALS.search(A,100)
	if C:A=A[:C.start()]
	D=_norm_name(A)
	if any(A in D for A in B):return True
	E=re.sub('\\D','',A);return any(A in E for A in regs)
def classify(text,tracked,comments,name):
	A=text;C=[];E=[A.strip()[:200]for A in A.splitlines()if A.strip()][:3]
	if AMEND.search(os.path.splitext(name)[0])or any(AMEND.search(A)for A in E):return'amendment',['הכותרת או שם הקובץ מזהים תיקון להסכם']
	if tracked:return'internal_draft',['המסמך מכיל שינויים במעקב']
	if comments:return'internal_draft',['המסמך מכיל הערות']
	B=placeholder_count(A);D=bool(SIGN_DATE.search(A))
	if D and B<=2:return'signed',['אותר תאריך חתימה ואין שדות ריקים מהותיים']
	if B>=3:return'template',['אותרו %d שדות למילוי'%B]
	if D:return'signed',['אותר תאריך חתימה']
	C.append('לא אותרו שדות למילוי ולא אותר תאריך חתימה');return'unclassified',C
def main():
	G=argparse.ArgumentParser();G.add_argument('--folders',nargs='+',required=True);G.add_argument('--out',required=True);G.add_argument('--playbook',help='playbook-model.json: company_role_code של המשפחה שלו קובע את התפקיד');G.add_argument('--role',nargs='+',help='הצד שבו עומדת החברה, כפי שמסר המשתמש: קוד (customer, receiving, processor ...) או תווית (לקוח, מקבל, מעבד ...), לכל המסמכים, או משפחה=תפקיד למשפחה אחת. גובר על הפלייבוק ועל ספירת מילים');G.add_argument('--profile',help='פרופיל-לקוח.json: שם החברה ומספר הרישום, לבדיקה שהמסמך על נייר החברה');G.add_argument('--company',nargs='+',help='שמות נוספים של החברה (שם באנגלית, שם קודם)');G.add_argument('--approved',nargs='+',help='שמות קבצים שהמשתמש אישר כתבנית, גם כשאינם על נייר החברה');C=G.parse_args();guard_out(C.out,[C.playbook,C.profile]);W,X=company_markers(C.profile,C.company);q={os.path.basename(A)for A in C.approved or[]};r=parse_roles(C.role);s=playbook_roles(C.playbook)if C.playbook and os.path.exists(C.playbook)else[];A,F,Y=[],[],{}
	for t in C.folders:
		for(D,Q,J,h)in scan_items(t,F):
			if True:
				try:u=os.path.getsize(J)
				except OSError:continue
				R=D.lower().endswith('.pdf')
				if R:(E,i),Z,j=pdf_text(J),False,False
				else:(E,Z,j),i=read_text(J),''
				if not E.strip():F.append({'file':D,'folder':Q,'why':i or('PDF סרוק, בלי שכבת טקסט'if R else'לא ניתן היה לקרוא טקסט מהמסמך')});continue
				a=hashlib.sha256(E[:20000].encode('utf-8','ignore')).hexdigest()[:16]
				if a in Y:A[Y[a]].setdefault('duplicates',[]).append(D);continue
				v,w=is_contract(E,D,os.path.splitext(D)[1].lower())
				if not v:F.append({'file':D,'folder':Q,'why':w,'excluded':True});continue
				L=E
				if J.lower().endswith('.docx'):L='\n'.join(docx_paragraphs(J))or E
				b,k=classify(L,Z,j,D);O,x,S=pick_family(D,E[:800],E[:20000]);T,l,y=resolve_role(O,E[:20000],r,s);H={'file':D,'folder':Q,'bytes':u,'doc_class':b,'class_reason':k,'family':O,'family_candidates':x,'family_basis':S,'company_role_candidates':y,'company_role':T,'company_role_basis':l,'mutuality':mutuality(D,'\n'.join(L.splitlines()[:3])),'language':language(E),'doc_date':datetime.fromtimestamp(os.path.getmtime(J)).strftime('%Y-%m-%d'),'approved_current':False,'format':'pdf'if R else os.path.splitext(D)[1].lower().lstrip('.'),'company_paper':on_company_paper(L,W,X)and h.get('paper')!='counterparty','user_approved':D in q};H.update(h)
				if b=='template':
					c=blank_parties(L)
					if c:H['blank_parties']=c
					m,z=paper_owner(D,L,c,T,l)
					if m:H['paper_owner'],H['paper_owner_basis']=m,z
				if R:H['selectable_as_template']=False;H['format_note']='PDF: נקרא לסיווג ולמבנה, ואינו נבחר כתבנית. לתבנית יש לשמור אותו כ-docx'
				if Z:P=docx_revisions(J);H['revisions']={'authors':sorted(set(list(P['authors_ins'])+list(P['authors_del']))),'insertions':P['n_ins'],'deletions':P['n_del'],'base_text_chars':len(P['base_text']),'markup_side':'לא ידוע, טעון שאלה למשתמש','note':'מי שסימן את השינויים הוא מי שמנסח את עמדתו. אם המחברים הם אנשי החברה, המרקאפ הוא העמדה שלנו והנוסח שאחרי קבלת השינויים הוא לשון הבית; טקסט הבסיס הוא אז הנייר של הצד שכנגד ואינו התבנית שלנו. אם המחברים הם הצד שכנגד, ההפך. אין להסיק מהשמות: יש לשאול את המשתמש.','house_text_is':'לא ידוע עד שתיקבע זהות המחברים'}
				if b=='unclassified'or not O or S.endswith('טעון אישור'):F.append({'file':D,'folder':Q,'why':'; '.join(k+([]if O else['לא זוהתה משפחת הסכם'])+([S]if O and S.endswith('טעון אישור')else[]))})
				Y[a]=len(A);A.append(H)
	n={}
	for(U,B)in enumerate(A):
		if not B['family']:continue
		T=(B['company_role_candidates']or['לא צוין'])[0];M=B['family'],T,B['language'],B.get('mutuality');n.setdefault(M,[]).append(U)
	def d(i):B=A[i];return B['format']!='pdf'and(B['user_approved']or B['company_paper']is True and B.get('paper_owner')!='counterparty')
	V=[]
	for(M,I)in n.items():
		for U in I:
			B=A[U]
			if B['doc_class']in('template','signed')and not d(U):
				B['not_approved_reason']='PDF'if B['format']=='pdf'else'טופס של הצד שכנגד: '+B['paper_owner_basis']if B.get('paper_owner')=='counterparty'else'לא נמסר שם החברה (--profile), ולכן לא נבדק שהמסמך על נייר החברה'if B['company_paper']is None else'שם החברה אינו בבלוק הצדדים: נייר של צד שלישי'
				if B.get('paper_owner')=='company':B['not_approved_reason']+='; הצד שפרטיו ריקים בפתיח הוא הצד שכנגד, ולכן ייתכן שזו תבנית של החברה'
				if B['doc_class']=='template'and B['format']!='pdf':F.append({'file':B['file'],'folder':B['folder'],'why':'טופס עם שדות למילוי שלא נבחר כתבנית מאושרת: '+B['not_approved_reason']+'. אם המשתמש מאשר אותו כתבנית, הרץ שוב עם --approved'})
		if not any(d(A)for A in I):V.append({'family':M[0],'role':M[1],'language':M[2],'mutuality':M[3],'documents':[A[B]['file']for B in I]})
		I=[A for A in I if d(A)];e=[B for B in I if A[B]['doc_class']=='template'];N=e or[B for B in I if A[B]['doc_class']=='signed'];f='template'if e else'signed'if N else None
		if not N:N=[B for B in I if A[B].get('revisions')];f='redline_base'if N else None
		if not N:continue
		K=max(N,key=lambda i:A[i]['doc_date']);A[K]['approved_current_basis']=f;A[K]['approved_by']='company_paper'if A[K]['company_paper']else'user'
		if f=='redline_base':A[K]['approved_current_note']='אין בתיקייה תבנית נקייה ואין הסכם חתום, והבסיס נגזר ממסמך redline. **אין להשתמש בו כלשון בית לפני שנקבע מי סימן את השינויים.** אם אנשי החברה סימנו, לשון הבית היא הנוסח שאחרי קבלת השינויים, וטקסט הבסיס הוא נייר הצד שכנגד. אם הצד שכנגד סימן, ההפך. שאל את המשתמש שאלה אחת: מי הם מחברי השינויים שבמסמך, אנשי החברה או הצד שכנגד.';A[K]['requires_user_answer']='מי סימן את השינויים במסמך'
		A[K]['approved_current']=True
		if not e:A[K]['derived_from_signed']=True
	A0={'meta':{'generated_at':datetime.now().strftime('%Y-%m-%d'),'last_updated':datetime.now().strftime('%Y-%m-%d'),'folders':list(C.folders),'playbook_used':bool(C.playbook and os.path.exists(C.playbook)),'company_paper_checked':bool(W or X),'third_party_paper_only':V,'note':'מרשם נגזר. הרכיב מציג אותו למשתמש ומבקש אישור לפני הסתמכות.'},'documents':A,'review_queue':F};os.makedirs(os.path.dirname(os.path.abspath(C.out)),exist_ok=True);io.open(C.out,'w',encoding='utf-8').write(json.dumps(A0,ensure_ascii=False,indent=1));g={}
	for B in A:g[B['doc_class']]=g.get(B['doc_class'],0)+1
	print('נסרקו %d מסמכים ייחודיים'%len(A))
	for(A1,A2)in sorted(g.items(),key=lambda x:-x[1]):print('  %-20s %d'%(A1,A2))
	print('תבניות מאושרות שנקבעו: %d'%sum(1 for A in A if A['approved_current']));o=sum(1 for A in A if A['format']=='pdf')
	if o:print('PDF שנקראו ונרשמו: %d (אינם נבחרים כתבנית)'%o)
	if not(W or X):print('שים לב: לא נמסר שם החברה (--profile), ולכן אף מסמך לא נבחר כתבנית מאושרת')
	elif V:print('צירופים בלי אף מסמך על נייר החברה: %d'%len(V))
	A3=sum(1 for A in F if A.get('excluded'));print('בתור בדיקה: %d, מתוכם %d הוצאו (לא חוזי, תוצר של Areo או תיקיית הנתונים)'%(len(F),A3));A4=[A for A in F if not A.get('excluded')]
	for p in A4[:20]:print('  לא נקרא: %s (%s)'%(p['file'],p['why']))
if __name__=='__main__':main()
