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
VERSION_SIM=.9
_SIM_WORD=re.compile('[A-Za-z\u0590-\u05ff]+')
def _sim_words(text,limit=4000):return[A.lower()for A in _SIM_WORD.findall(PLACEHOLDER.sub(' ',text or''))][:limit]
def similarity(a,b):
	import difflib as D;B,C=_sim_words(a),_sim_words(b)
	if not B or not C:return .0
	A=D.SequenceMatcher(None,B,C,autojunk=False)
	if A.real_quick_ratio()<VERSION_SIM or A.quick_ratio()<VERSION_SIM:return A.quick_ratio()
	return A.ratio()
def version_clusters(idxs,bodies):
	C=bodies;A=[]
	for B in idxs:
		for D in A:
			if any(similarity(C.get(B,''),C.get(A,''))>=VERSION_SIM for A in D):D.append(B);break
		else:A.append([B])
	return A
def _short_lines(body):
	B=[]
	for C in(body or'').splitlines():
		A=re.sub('\\s+',' ',PLACEHOLDER.sub(' ',C)).strip(' .:;-');A=re.sub('^\\d+(?:\\.\\d+)*\\.?\\s*','',A)
		if 3<=len(A)<=80 and _SIM_WORD.search(A):B.append(A)
	return B
def distinguishing(members,bodies):
	C=members;B={A:_short_lines(bodies.get(A,''))for A in C};D={}
	for A in C:E={D.lower()for C in C if C!=A for D in B[C]};F=[A for A in B[A]if A.lower()not in E];D[A]={'title':B[A][0]if B[A]else'','unique_headings':list(dict.fromkeys(F))[:5]}
	return D
def template_set_driver(n,members,docs,dist,lang):
	G=members;D=dist;E,H,F=[],{},[]
	for(J,A)in enumerate(G,1):
		B=docs[A];C=D[A]['title']or os.path.splitext(B['file'])[0]
		if[A for A in E if A['label']==C]:C='%s (%s)'%(C,os.path.splitext(B['file'])[0])
		I='t%d'%J;E.append({'value':I,'label':C});H[I]={'template':B['file']};F.append({'doc':B['file'],'title':D[A]['title'],'unique_headings':D[A]['unique_headings']})
	K=all(A['unique_headings']for A in F);return{'id':'TS%d'%n,'question':'Which of these templates fits this deal?'if lang=='en'else'איזו מהתבניות מתאימה לעסקה הזו?','kind':'choice','options':E,'threshold':None,'source':'template','evidence':F,'effects':H,'follow_ups':[],'priority':{'clauses':len(G),'exposure':'high'},'derivable_from':None,'distinguishing_clear':K}
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
	H=argparse.ArgumentParser();H.add_argument('--folders',nargs='+',required=True);H.add_argument('--out',required=True);H.add_argument('--playbook',help='playbook-model.json: company_role_code של המשפחה שלו קובע את התפקיד');H.add_argument('--role',nargs='+',help='הצד שבו עומדת החברה, כפי שמסר המשתמש: קוד (customer, receiving, processor ...) או תווית (לקוח, מקבל, מעבד ...), לכל המסמכים, או משפחה=תפקיד למשפחה אחת. גובר על הפלייבוק ועל ספירת מילים');H.add_argument('--profile',help='פרופיל-לקוח.json: שם החברה ומספר הרישום, לבדיקה שהמסמך על נייר החברה');H.add_argument('--company',nargs='+',help='שמות נוספים של החברה (שם באנגלית, שם קודם)');H.add_argument('--approved',nargs='+',help='שמות קבצים שהמשתמש אישר כתבנית, גם כשאינם על נייר החברה');H.add_argument('--chosen',nargs='+',help='נתיב התאמת התבנית (פרק 7, כלל 0): התבניות שהלקוח בחר או צירף. נחשבות מאושרות על ידו גם כשאינן על נייר החברה, ויחד הן ערכת התבניות של המשפחה והצד (גרסאות כמעט זהות: נשמרת המאוחרת)');C=H.parse_args();guard_out(C.out,[C.playbook,C.profile]);b,c=company_markers(C.profile,C.company);n={os.path.basename(A)for A in C.chosen or[]};A1={os.path.basename(A)for A in C.approved or[]}|n;A2=parse_roles(C.role);A3=playbook_roles(C.playbook)if C.playbook and os.path.exists(C.playbook)else[];A,I,d,e=[],[],{},{}
	for A4 in C.folders:
		for(D,T,L,o)in scan_items(A4,I):
			if True:
				try:A5=os.path.getsize(L)
				except OSError:continue
				U=D.lower().endswith('.pdf')
				if U:(G,p),f,q=pdf_text(L),False,False
				else:(G,f,q),p=read_text(L),''
				if not G.strip():I.append({'file':D,'folder':T,'why':p or('PDF סרוק, בלי שכבת טקסט'if U else'לא ניתן היה לקרוא טקסט מהמסמך')});continue
				g=hashlib.sha256(G[:20000].encode('utf-8','ignore')).hexdigest()[:16]
				if g in d:A[d[g]].setdefault('duplicates',[]).append(D);continue
				A6,A7=is_contract(G,D,os.path.splitext(D)[1].lower())
				if not A6:I.append({'file':D,'folder':T,'why':A7,'excluded':True});continue
				M=G
				if L.lower().endswith('.docx'):M='\n'.join(docx_paragraphs(L))or G
				h,r=classify(M,f,q,D);Q,A8,V=pick_family(D,G[:800],G[:20000]);W,s,A9=resolve_role(Q,G[:20000],A2,A3);J={'file':D,'folder':T,'bytes':A5,'doc_class':h,'class_reason':r,'family':Q,'family_candidates':A8,'family_basis':V,'company_role_candidates':A9,'company_role':W,'company_role_basis':s,'mutuality':mutuality(D,'\n'.join(M.splitlines()[:3])),'language':language(G),'doc_date':datetime.fromtimestamp(os.path.getmtime(L)).strftime('%Y-%m-%d'),'approved_current':False,'format':'pdf'if U else os.path.splitext(D)[1].lower().lstrip('.'),'company_paper':on_company_paper(M,b,c)and o.get('paper')!='counterparty','user_approved':D in A1}
				if D in n:J['client_chosen']=True
				J.update(o)
				if h=='template':
					i=blank_parties(M)
					if i:J['blank_parties']=i
					t,AA=paper_owner(D,M,i,W,s)
					if t:J['paper_owner'],J['paper_owner_basis']=t,AA
				if U:J['selectable_as_template']=False;J['format_note']='PDF: נקרא לסיווג ולמבנה, ואינו נבחר כתבנית. לתבנית יש לשמור אותו כ-docx'
				if f:R=docx_revisions(L);J['revisions']={'authors':sorted(set(list(R['authors_ins'])+list(R['authors_del']))),'insertions':R['n_ins'],'deletions':R['n_del'],'base_text_chars':len(R['base_text']),'markup_side':'לא ידוע, טעון שאלה למשתמש','note':'מי שסימן את השינויים הוא מי שמנסח את עמדתו. אם המחברים הם אנשי החברה, המרקאפ הוא העמדה שלנו והנוסח שאחרי קבלת השינויים הוא לשון הבית; טקסט הבסיס הוא אז הנייר של הצד שכנגד ואינו התבנית שלנו. אם המחברים הם הצד שכנגד, ההפך. אין להסיק מהשמות: יש לשאול את המשתמש.','house_text_is':'לא ידוע עד שתיקבע זהות המחברים'}
				if h=='unclassified'or not Q or V.endswith('טעון אישור'):I.append({'file':D,'folder':T,'why':'; '.join(r+([]if Q else['לא זוהתה משפחת הסכם'])+([V]if Q and V.endswith('טעון אישור')else[]))})
				d[g]=len(A);e[len(A)]=M;A.append(J)
	u={}
	for(E,B)in enumerate(A):
		if not B['family']:continue
		W=(B['company_role_candidates']or['לא צוין'])[0];F=B['family'],W,B['language'],B.get('mutuality');u.setdefault(F,[]).append(E)
	def j(i):B=A[i];return B['format']!='pdf'and(B['user_approved']or B['company_paper']is True and B.get('paper_owner')!='counterparty')
	X,Y=[],[]
	for(F,K)in u.items():
		for E in K:
			B=A[E]
			if B['doc_class']in('template','signed')and not j(E):
				B['not_approved_reason']='PDF'if B['format']=='pdf'else'טופס של הצד שכנגד: '+B['paper_owner_basis']if B.get('paper_owner')=='counterparty'else'לא נמסר שם החברה (--profile), ולכן לא נבדק שהמסמך על נייר החברה'if B['company_paper']is None else'שם החברה אינו בבלוק הצדדים: נייר של צד שלישי'
				if B.get('paper_owner')=='company':B['not_approved_reason']+='; הצד שפרטיו ריקים בפתיח הוא הצד שכנגד, ולכן ייתכן שזו תבנית של החברה'
				if B['doc_class']=='template'and B['format']!='pdf':I.append({'file':B['file'],'folder':B['folder'],'why':'טופס עם שדות למילוי שלא נבחר כתבנית מאושרת: '+B['not_approved_reason']+'. אם המשתמש מאשר אותו כתבנית, הרץ שוב עם --approved'})
		if not any(j(A)for A in K):X.append({'family':F[0],'role':F[1],'language':F[2],'mutuality':F[3],'documents':[A[B]['file']for B in K]})
		K=[A for A in K if j(A)];v=[B for B in K if A[B].get('client_chosen')];S=v or[B for B in K if A[B]['doc_class']=='template'];P=S or[B for B in K if A[B]['doc_class']=='signed'];Z=('client_chosen'if v else'template')if S else'signed'if P else None
		if S:
			AB=version_clusters(S,e);N=[]
			for a in AB:
				a=sorted(a,key=lambda i:(A[i]['doc_date'],A[i]['file']),reverse=True);w=a[0]
				for x in a[1:]:A[x]['superseded_by']=A[w]['file'];A[x]['superseded_reason']='גרסה כמעט זהה של תבנית מאוחרת יותר'
				N.append(w)
			for E in N:A[E]['approved_current']=True;A[E]['approved_current_basis']=Z;A[E]['approved_by']='client_chosen'if A[E].get('client_chosen')else'company_paper'if A[E]['company_paper']else'user'
			if len(N)>1:
				AC=distinguishing(N,e);k=len(Y)+1
				for E in N:A[E]['template_set']='TS%d'%k
				Y.append({'id':'TS%d'%k,'family':F[0],'role':F[1],'language':F[2],'mutuality':F[3],'templates':[A[B]['file']for B in N],'driver':template_set_driver(k,N,A,AC,F[2])})
			continue
		if not P:P=[B for B in K if A[B].get('revisions')];Z='redline_base'if P else None
		if not P:continue
		O=max(P,key=lambda i:A[i]['doc_date']);A[O]['approved_current_basis']=Z;A[O]['approved_by']='company_paper'if A[O]['company_paper']else'user'
		if Z=='redline_base':A[O]['approved_current_note']='אין בתיקייה תבנית נקייה ואין הסכם חתום, והבסיס נגזר ממסמך redline. **אין להשתמש בו כלשון בית לפני שנקבע מי סימן את השינויים.** אם אנשי החברה סימנו, לשון הבית היא הנוסח שאחרי קבלת השינויים, וטקסט הבסיס הוא נייר הצד שכנגד. אם הצד שכנגד סימן, ההפך. שאל את המשתמש שאלה אחת: מי הם מחברי השינויים שבמסמך, אנשי החברה או הצד שכנגד.';A[O]['requires_user_answer']='מי סימן את השינויים במסמך'
		A[O]['approved_current']=True
		if not S:A[O]['derived_from_signed']=True
	AD={'meta':{'generated_at':datetime.now().strftime('%Y-%m-%d'),'last_updated':datetime.now().strftime('%Y-%m-%d'),'folders':list(C.folders),'playbook_used':bool(C.playbook and os.path.exists(C.playbook)),'company_paper_checked':bool(b or c),'third_party_paper_only':X,'note':'מרשם נגזר. הרכיב מציג אותו למשתמש ומבקש אישור לפני הסתמכות.'},'documents':A,'template_sets':Y,'review_queue':I};os.makedirs(os.path.dirname(os.path.abspath(C.out)),exist_ok=True);io.open(C.out,'w',encoding='utf-8').write(json.dumps(AD,ensure_ascii=False,indent=1));l={}
	for B in A:l[B['doc_class']]=l.get(B['doc_class'],0)+1
	print('נסרקו %d מסמכים ייחודיים'%len(A))
	for(AE,AF)in sorted(l.items(),key=lambda x:-x[1]):print('  %-20s %d'%(AE,AF))
	print('תבניות מאושרות שנקבעו: %d'%sum(1 for A in A if A['approved_current']));y=[A for A in A if A.get('superseded_by')]
	if y:print('גרסאות קודמות שהוחלפו בגרסה מאוחרת: %d'%len(y))
	for m in Y:print('ערכת תבניות (%s, %s): %s'%(m['family'],m['role'],', '.join(m['templates'])))
	z=sum(1 for A in A if A['format']=='pdf')
	if z:print('PDF שנקראו ונרשמו: %d (אינם נבחרים כתבנית)'%z)
	if not(b or c):print('שים לב: לא נמסר שם החברה (--profile), ולכן אף מסמך לא נבחר כתבנית מאושרת')
	elif X:print('צירופים בלי אף מסמך על נייר החברה: %d'%len(X))
	AG=sum(1 for A in I if A.get('excluded'));print('בתור בדיקה: %d, מתוכם %d הוצאו (לא חוזי, תוצר של Areo או תיקיית הנתונים)'%(len(I),AG));AH=[A for A in I if not A.get('excluded')]
	for A0 in AH[:20]:print('  לא נקרא: %s (%s)'%(A0['file'],A0['why']))
if __name__=='__main__':main()
