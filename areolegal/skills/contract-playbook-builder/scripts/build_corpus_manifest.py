#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (c) Areo. All rights reserved. Licensed under the terms at https://areo.co.il/legal/terms
import argparse,hashlib,json,os,re,sys,zipfile
from pathlib import Path
from xml.etree import ElementTree as ET
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
import areo_lib
from common.cli import OutputRefused,docx_problem,guard_out
W='{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
STRICT_W=b'http://purl.oclc.org/ooxml/wordprocessingml/main'
NO_TEXT='אין שכבת טקסט (סרוק?)'
DOCX_REASON={'ole':'DOC ישן או קובץ מוצפן בסיסמה; שמרו כ-docx בלי סיסמה','not_zip':'קובץ פגום: אינו ZIP תקין','no_document':'אין בו word/document.xml: אינו מסמך Word'}
TEXT_EXT={'.txt','.md','.csv','.json'}
TEMPLATE_NAME=re.compile('תבנית|נוסח סטנדרטי|נוסח אחיד|template|master form|standard form',re.I)
PLACEHOLDER=re.compile('_{4,}|\\.{6,}|\\[[^\\]]{0,40}(שם|תאריך|סכום|להשלים|insert|name|date|amount)[^\\]]{0,40}\\]|<<[^>]{1,40}>>|\\{\\{[^}]{1,40}\\}\\}',re.I)
SIGNED=re.compile('IN\\s+WITNESS\\s+WHEREOF|ולראי{1,2}ה\\s+(?:באו|באנו|חתמו|חתמנו)|ובאו\\s+הצדדים\\s+על\\s+החתום|חתימת\\s+הצדדים|(?m:^)[ \\t]*(?-i:Signed|SIGNED|Executed|EXECUTED)\\s+(?:by|for\\s+and\\s+on\\s+behalf)\\b|\\b(?:have|has)\\s+(?:duly\\s+)?executed\\s+this\\b|(?<![\\w/])/s/|signature\\s+of\\s+the\\s+parties|(?:נחתם|תאריך\\s+החתימה|Signed\\s+on|Date\\s+of\\s+signature)\\s*[:\\-]?\\s*\\d',re.I)
LINE_RUN=re.compile('_{4,}|\\.{6,}')
SIGN_TAIL=300
PROCEDURE_SIGN=re.compile('הליך תחרותי|המציע|\\bcompetitive\\s+procedure\\b|\\bbidders?\\b|\\bRFP\\b|request\\s+for\\s+proposals?|invitation\\s+to\\s+(?:bid|tender)',re.I)
PUBLIC_BODY=re.compile('משרד\\s+ה[א-ת]+|עיריית|המועצה\\s+(?:האזורית|המקומית)|חברה\\s+ממשלתית|תאגיד\\s+סטטוטורי|Ministry\\s+of|Municipality\\s+of|Government\\s+of|government\\s+company|statutory\\s+corporation|(?:City|County|Borough)\\s+(?:of|Council)',re.I)
PUBLIC_HEAD=1500
BLANK_PARTY=re.compile('(?:_{4,}|\\.{6,}|\\[[^\\]]{0,40}\\]|<<[^>]{1,40}>>|\\{\\{[^}]{1,40}\\}\\})[^"״“()\\n]{0,60}[()]\\s*(?:להלן\\s*[:\\-]?\\s*|hereinafter(?:\\s+(?:referred\\s+to\\s+as|called))?\\s*[:,]?\\s*(?:the\\s+)?|the\\s+)?["״“]([^"״”()]{2,40})["״”]',re.I)
AMENDMENT=re.compile("תיקון\\s*(?:מס(?:פר|['׳])?\\.?\\s*)?\\d*\\s*ל(?!חוק|תקנות|פקודת|פקודה|צו\\b)|נספח\\s+תיקון|תוספת\\s+להסכם|הסכם\\s+תיקון|\\bamendment\\s*(?:no\\.?\\s*\\d+\\s*)?to\\b|^\\s*(?:(?:first|second|third|\\d+(?:st|nd|rd|th)?)\\s+)?addendum\\b\\s*(?:(?:no\\.?|number|#)\\s*\\d+\\s*)?to\\b",re.I)
RENEWAL_TOKENS={'חידוש','מחודש','הארכה','הארכת','renewal','renewed','extension','extended','new'}
BANDS=[(20,None,'full'),(7,19,'below20'),(1,6,'below7'),(0,0,'none')]
DEFINED_PARTY=re.compile('[()]\\s*(?:להלן\\s*[:\\-\\u2013\\u2014]?\\s*|hereinafter(?:\\s+(?:referred\\s+to\\s+as|called|named|defined\\s+as))?\\s*[:,]?\\s*(?:the\\s+)?|the\\s+)?["״“]([^"״”()]{2,40})["״”](?:\\s*(?:או|or)\\s*(?:the\\s+)?["״“]([^"״”()]{2,40})["״”])?\\s*[()]',re.I)
NOT_A_ROLE=re.compile('^(?:ההסכם|הסכם|החוזה|חוזה|המוצר|השירותים|השירות|המידע|הנכס|הצדדים|הצד|ההצעה|הנספח|נספח|Agreement|Services|Product|Effective Date|Term|Confidential Information|Purpose|Parties|Party|Addendum|Clauses|Schedule|Annex|Exhibit|Proposal|החוק|התקנות|העובדים|המשתמשים|המשתמשים הסופיים|החברות הקשורות|הנציגים|Employees|Personnel|Users|End Users|Affiliates|Representatives)$',re.I)
def _alias(g):g=re.sub('\\s+',' ',re.sub('_{2,}|\\.{3,}',' ',g or'')).strip(' .,:;');return re.sub('^([הוכלבמש]) (?=[א-ת])','\\1',g)
def parties_hint(text):
	D=(text or'')[:2500];B,C=[],[]
	for E in DEFINED_PARTY.finditer(D):
		for A in E.groups():
			A=_alias(A)
			if not A or NOT_A_ROLE.match(A)or len(A.split())>3 or A in B+C or re.search('\\b[A-Z]{2,8}\\b',A)or re.search('\\d',A)or re.match('(?:חוק|תקנות|פקודת)\\s|.*\\b(?:Act|Law|Regulations?)$',A,re.I):continue
			(B if _role_like(A)else C).append(A)
	return(B+C)[:4]
ISSUER_ROLES={'contracting_authority','issuer','inviting_party','מזמין','הגוף המזמין'}
PUBLIC_ORG=re.compile('ממשלתי|ממשלתית|גוף\\s+ציבורי|רשות\\s+מקומית|תאגיד\\s+סטטוטורי|השכלה\\s+גבוהה|אוניברסיט|Government|Public\\s+body|Local\\s+authority|Statutory\\s+corporation|Universit|higher\\s+education',re.I)
LEGAL_SUFFIX=re.compile('\\b(?:בע[\\"״\']?מ|\\(?ע[\\"״\']?ר\\)?|חל[\\"״\']?צ|Ltd\\.?|Limited|Inc\\.?|LLC|L\\.L\\.C\\.|plc|GmbH|B\\.V\\.)(?=\\s|$|[,.)])',re.I)
NO_COMPANY={'names':[],'public':False}
def _name_key(t):return re.sub('\\s+',' ',re.sub('[\\"״\'׳`.,()\\-]',' ',t or'')).strip().lower()
def company_identity(profile_path):
	A=profile_path
	if not A:return dict(NO_COMPANY)
	try:D=json.loads(Path(A).read_text(encoding='utf-8-sig'))
	except(OSError,ValueError):print('אזהרה: הפרופיל לא נקרא (%s). הזיהוי ממשיך בלי שם החברה'%A,file=sys.stderr);return dict(NO_COMPANY)
	B=[]
	for E in('organization_name','organization_name_en'):
		C=_name_key(LEGAL_SUFFIX.sub(' ',str(D.get(E)or'')))
		if len(C)>=4 and C not in B:B.append(C)
	return{'names':B,'public':bool(PUBLIC_ORG.search(str(D.get('organization_type')or'')))}
def company_issues(role_code,own):A=str(role_code or'').strip().lower();return A in ISSUER_ROLES or bool((own or{}).get('public'))and A!='bidder'
def role_terms(role_code):
	A=str(role_code or'').strip()
	if not A or A.lower()in('other','mutual'):return[],[]
	return[A,'ה'+A],[]
def _norm_role(g):return re.sub('^the\\s+','',(g or'').strip().lower())
def _role_like(g):
	if re.search('[א-ת]',g):return g.startswith('ה')
	return bool(re.search('(?:or|er|ee|ant|ent|ist|ary|ier)$',g.split()[-1],re.I))
def family_roles(rows,role_code):
	C,D,E,F={},{},[],[]
	for G in rows:
		if G['doc_role']not in('agreement','form','template'):continue
		F.append(G['path'])
		for A in G.get('parties_hint')or[]:
			if _role_like(A):C[A]=C.get(A,0)+1;D.setdefault(A,len(D))
			elif len(F)<=2 and A not in E and _role_like(A):E.append(A)
	B=sorted(C,key=lambda g:(-C[g],D[g]))[:4]
	if len(B)<2:B+=[A for A in E if A not in B][:4-len(B)]
	H=[];return B,F,H
def third_party_signs(name,text,own=None):
	C=text;B=name;D=[];A=PROCEDURE_SIGN.search(Path(B).stem)or PROCEDURE_SIGN.search(C or'')
	if A:D.append('procedure: %s'%A.group(0))
	A=PUBLIC_BODY.search(Path(B).stem)or PUBLIC_BODY.search((C or'')[:PUBLIC_HEAD])
	if A:
		E=_name_key(Path(B).stem+' '+(C or'')[:PUBLIC_HEAD])
		if not any(A in E for A in(own or NO_COMPANY)['names']):D.append('public body: %s'%re.sub('\\s+',' ',A.group(0)))
	return D
def blank_parties(text):
	B=[]
	for C in BLANK_PARTY.finditer((text or'')[:2500]):
		A=_alias(C.group(1))
		if A and not NOT_A_ROLE.match(A)and A not in B:B.append(A)
	return B
def whose_template(row,role_code):
	D,E=role_terms(role_code);A={_norm_role(A)for A in row.get('blank_parties')or()};B=A&{_norm_role(A)for A in D};C=A&{_norm_role(A)for A in E}
	if B and not C:return'counterparty'
	if C and not B:return'company'
def decide_owner(row,role_code,own=None):
	F=role_code;D=own;A=row;G=A.get('third_party_signs')or();E=any(A.startswith('procedure')for A in G);B=company_issues(F,D)
	if A['doc_role']not in('template','form'):
		if E and B and A.get('paper_hint')=='theirs':A=dict(A);A.pop('paper_hint',None)
		elif E and not B and(D or{}).get('public')and not A.get('paper_hint'):A=dict(A,paper_hint='theirs')
		return A
	H=whose_template(A,F);C=bool(A.get('counterparty_template'))
	if H=='counterparty':return A if C else as_counterparty_form(A,['blank party: company role'])
	if A['doc_role']=='form'and not C:return A
	if H=='company':return as_company_template(A,'blank party: counterparty role')
	if C and B:return as_company_template(A,'company issues the procedure'if E else'company is the public body')
	if not C and A['doc_role']=='template'and G and(D or{}).get('public')and not B:return as_counterparty_form(A,['company is the bidder'])
	return A
def as_counterparty_form(row,why):
	A=row;A=dict(A)
	if A['doc_role']in('template','form'):A['doc_role']='form';A['form_signs']=['counterparty template']+list(A.get('template_signs')or A.get('form_signs')or[])+list(why);A['counterparty_template']=True
	A['paper_hint']='theirs';return A
def as_company_template(row,why='client: company template'):
	A=row;A=dict(A)
	if A['doc_role']!='amendment':A['doc_role']='template';A['template_signs']=[A for A in A.get('template_signs')or[]if A!=why]+[why]
	for B in('counterparty_template','paper_hint','form_signs'):A.pop(B,None)
	return A
def band_of(units):A=units;return next(D for(C,B,D)in BANDS if A>=C and(B is None or A<=B))
def sha256_bytes(path):
	A=hashlib.sha256()
	with open(path,'rb')as B:
		for C in iter(lambda:B.read(1048576),b''):A.update(C)
	return A.hexdigest()
def pdf_text(path):
	B=path
	try:
		try:import pymupdf as D
		except ImportError:import fitz as D
		with D.open(str(B))as E:A='\n'.join(A.get_text()for A in E)
		return(A,None)if A.strip()else(None,'PDF סרוק, בלי שכבת טקסט')
	except ImportError:pass
	except Exception as C:return None,'PDF לא נקרא: %s'%type(C).__name__
	try:
		try:
			import pdfplumber as F
			with F.open(str(B))as G:A='\n'.join(A.extract_text()or''for A in G.pages)
		except ImportError:import pypdf;A='\n'.join(A.extract_text()or''for A in pypdf.PdfReader(str(B)).pages)
	except ImportError:return None,'אין ספרייה לקריאת PDF. התקנה: pip install pymupdf'
	except Exception as C:return None,'PDF לא נקרא: %s'%type(C).__name__
	if not A.strip():return None,'PDF סרוק, בלי שכבת טקסט'
	if re.search('[א-ת]',A):return None,'PDF בעברית, ואין pymupdf: הטקסט יוצא בסדר הפוך. התקנה: pip install pymupdf'
	return A,None
def read_text(path):
	A=path
	try:
		if A.suffix.lower()=='.docx':
			B=docx_problem(A,strict_ok=True)
			if B and B[0]in DOCX_REASON:return None,DOCX_REASON[B[0]]
			with zipfile.ZipFile(A)as D:E=D.read('word/document.xml').replace(STRICT_W,W[1:-1].encode())
			F=ET.fromstring(E);C='\n'.join(''.join(A.text or''for A in A.iter(W+'t'))for A in F.iter(W+'p'));return(C,None)if C.strip()else(None,NO_TEXT)
		if A.suffix.lower()=='.pdf':return pdf_text(A)
		if A.suffix.lower()in TEXT_EXT:return A.read_text(encoding='utf-8',errors='ignore'),None
	except Exception as G:return None,'הקובץ לא נקרא: %s'%type(G).__name__
	return None,None
def normalize(text):A=re.sub('[\u200e\u200f\u202a-\u202e]','',text or'');A=re.sub('\\b\\d{1,2}[./-]\\d{1,2}[./-]\\d{2,4}\\b',' ',A);return re.sub('\\s+',' ',A).strip().lower()
def title_hint(text,name):
	if not text:return Path(name).stem
	A=[A.strip()for A in text.splitlines()if A.strip()]
	if not A:return Path(name).stem
	B=3
	while B<min(len(A),12)and len(' '.join(A[:B]))<80:B+=1
	return' / '.join(A[:B])[:300]
def head_lines(text,n=3):return[A.strip()[:200]for A in(text or'').splitlines()if A.strip()][:n]
def is_amendment(name,text):
	if AMENDMENT.search(Path(name).stem):return True
	return any(AMENDMENT.search(A)for A in head_lines(text))
def placeholder_count(text):B=len(text)-SIGN_TAIL;return sum(1 for A in PLACEHOLDER.finditer(text)if not(A.start()>=B and LINE_RUN.fullmatch(A.group(0))))
def shingles(text,size=9,step=1):A=text.split();return{hashlib.md5(' '.join(A[B:B+size]).encode('utf-8')).digest()[:8]for B in range(0,max(1,len(A)-size+1),step)}
def similarity(a,b):return len(a&b)/float(len(a|b))if a and b else .0
def normalized_stem(name):A=Path(name).stem.lower();A=re.sub('\\b(v|ver|version|rev|draft|final|signed)[-_ ]?\\d*[a-z]?\\b',' ',A);A=re.sub('\\b20\\d{2}[-_. ]\\d{1,2}[-_. ]\\d{1,2}\\b',' ',A);A=re.sub('\\b(copy|עותק)\\b',' ',A);A=re.sub('[^a-z0-9\u0590-\u05ff]+',' ',A);return' '.join(A.split())
def same_negotiation(a,b):
	A,B=a.split(),b.split()
	if not A or not B:return False
	if A[:len(B)]==B:C=A[len(B):]
	elif B[:len(A)]==A:C=B[len(A):]
	else:return False
	return not set(C)&RENEWAL_TOKENS
def looks_like_template(name,text):
	B=text;A=[]
	if TEMPLATE_NAME.search(name):A.append('file name')
	if B:
		if placeholder_count(B)>=3:A.append('placeholders')
		if not SIGNED.search(B):A.append('no signature block')
	return'file name'in A or len(A)>=2,A
def looks_like_blank_form(text):
	A=text
	if not A or not SIGNED.search(A):return False,[]
	B=placeholder_count(A);return B>=3,['signature block','%d placeholders'%B]if B>=3 else[]
AREO_DIRS='Areo-נתונים','Areo-data'
def _skipped(rel):return any(A in AREO_DIRS or A.startswith('.')for A in rel.parts[:-1])
def scan(root,own=None):
	F=root;D=own;D=D or NO_COMPANY;I=[]
	for B in sorted(F.rglob('*')):
		if not B.is_file()or B.name.startswith(('~$','.'))or _skipped(B.relative_to(F)):continue
		C,J=read_text(B);E=normalize(C)if C else None;A={'path':str(B.relative_to(F)),'size':B.stat().st_size,'extension':B.suffix.lower(),'sha256':sha256_bytes(B),'normalized_stem':normalized_stem(B.name),'text_read':C is not None,'text_sha256':hashlib.sha256(E.encode('utf-8')).hexdigest()if E else None,'title_hint':title_hint(C,B.name),'parties_hint':parties_hint(C),'doc_role':'agreement'}
		if J:A['unreadable_reason']=J
		L,G=looks_like_template(B.name,C)
		if L:A['doc_role'],A['template_signs']='template',G
		else:
			M,G=looks_like_blank_form(C)
			if M:A['doc_role'],A['form_signs']='form',G
		K=blank_parties(C)
		if K:A['blank_parties']=K
		H=third_party_signs(B.name,C,D)
		if H:
			A['third_party_signs']=H
			if D['public']:0
			elif A['doc_role']=='template':A=as_counterparty_form(A,[])
			elif any(A.startswith('procedure')for A in H):A['paper_hint']='theirs'
		if is_amendment(B.name,C):A['doc_role']='amendment'
		A['_shingles']=shingles(E)if E else None;I.append(A)
	return I
def count(rows,near_threshold):
	G=rows;J,K,L,M=[],[],[],[];N=[]
	for A in G:
		if A['doc_role']=='template':M.append({'path':A['path'],'signs':A.get('template_signs',[])})
		else:N.append(A)
	H,B={},[]
	for A in sorted(N,key=lambda x:(len(x['path']),x['path'])):
		I=A['text_sha256']or A['sha256']
		if I in H:J.append({'kept':H[I],'removed':A['path'],'same':'text'if A['text_sha256']else'bytes'})
		else:H[I]=A['path'];B.append(A)
	B.sort(key=lambda x:x['path']);E={}
	for(S,D)in enumerate(B):
		if D['path']in E or not D['_shingles']:continue
		for C in B[S+1:]:
			if C['path']in E or not C['_shingles']:continue
			if not same_negotiation(D['normalized_stem'],C['normalized_stem']):continue
			O=similarity(D['_shingles'],C['_shingles'])
			if O>=near_threshold:E[C['path']]=True;K.append({'kept':D['path'],'merged':C['path'],'similarity':round(O,3)})
	B=[A for A in B if A['path']not in E];T=[A for A in B if A['doc_role']in('agreement','form')and A['normalized_stem']];F,P=[],[]
	for A in B:
		if A['doc_role']!='amendment':F.append(A['path']);continue
		Q=[B for B in T if B['normalized_stem']==A['normalized_stem']or B['normalized_stem']in A['normalized_stem']]
		if Q:U=max(Q,key=lambda x:len(x['normalized_stem']));L.append({'path':A['path'],'amends':U['path']})
		else:P.append(A['path']);F.append(A['path'])
	R=len(F);return{'files':len(G),'agreement_units':R,'band':band_of(R),'counted_agreements':F,'removed_duplicates':J,'merged_versions':K,'amendments_attached':L,'excluded_templates':M,'needs_review':{'unreadable':[A['path']for A in G if not A['text_read']],'amendments_without_base':P,'unsigned_forms':[A['path']for A in B if A['doc_role']=='form'and not A.get('counterparty_template')],'counterparty_forms':[A['path']for A in B if A.get('counterparty_template')]}}
def main():
	G=argparse.ArgumentParser();G.add_argument('root');G.add_argument('--out',default='corpus-manifest.json',help='ברירת המחדל: corpus-manifest.json. לעולם לא אחד מקובצי הקורפוס (common/cli.guard_out)');G.add_argument('--families',help='קובץ סיווג לסוגים, אחרי שלב 2א');G.add_argument('--near',type=float,default=.92,help='סף דמיון לאיחוד גרסאות');G.add_argument('--profile',help='פרופיל-לקוח.json של הישות (רשות): שם החברה, והאם היא גוף ציבורי. גוף ציבורי שהוא החברה עצמה אינו סימן לנייר של צד שכנגד');B=G.parse_args();H=Path(B.root).resolve()
	if not H.is_dir():sys.exit('אין תיקייה כזאת: %s'%H)
	N=company_identity(B.profile);D=scan(H,N)
	if not D:sys.exit('התיקייה ריקה: %s'%H)
	try:S=guard_out(B.out,inputs=[str(H/A['path'])for A in D]+[B.families])
	except OutputRefused as T:print('refused: %s'%T,file=sys.stderr);return 2
	C={'root':str(H),'file_count':len(D),'corpus_basis_all_files':count(D,B.near)}
	if B.families:
		U=json.loads(Path(B.families).read_text(encoding='utf-8'));E,O={A['path']:A for A in D},[];P=set()
		for A in U.get('families',[]):
			L,K=[],[]
			for F in A.get('paths',[]):(L if F in E else K).append(F);P.add(F)
			I={B:A.get(B)for B in('contract_family_id','label','company_role_code')};V=set(A.get('counterparty_templates')or[]);W=set(A.get('company_templates')or[]);X=A.get('company_role_code');M=[as_counterparty_form(E[A],['client: counterparty template'])if A in V else as_company_template(E[A])if A in W else decide_owner(E[A],X,N)for A in L];I['corpus_basis']=count(M,B.near)if L else None
			for(F,J)in zip(L,M):
				if J['doc_role']=='agreement'and J.get('paper_hint')!=E[F].get('paper_hint'):
					E[F]['paper_hint']=J.get('paper_hint')
					if not J.get('paper_hint'):E[F].pop('paper_hint',None)
			Y,Z,Q=family_roles(M,A.get('company_role_code'));I['roles_hint']=Y;I['roles_read_from']=Z
			if Q:I['roles_from_vocabulary']=Q
			if K:I['paths_not_found']=K;print('אזהרה: בסוג %s יש %d נתיבים שאינם בתיקייה: %s'%(A.get('label')or A.get('contract_family_id'),len(K),', '.join(K[:4])))
			O.append(I)
		C['by_family']=O;C['unclassified']=[A['path']for A in D if A['path']not in P]
	for J in D:J.pop('_shingles',None)
	C['files']=D;Path(S).write_text(json.dumps(C,ensure_ascii=False,indent=2),encoding='utf-8')
	def R(name,b):
		print('%s: %d קבצים, %d הסכמים, רצועה %s'%(name,b['files'],b['agreement_units'],b['band']));print('   נוכו: %d כפילויות, %d גרסאות, %d תיקונים, %d תבניות'%(len(b['removed_duplicates']),len(b['merged_versions']),len(b['amendments_attached']),len(b['excluded_templates'])))
		for(B,C)in(('unreadable','לא נקרא טקסט'),('amendments_without_base','תיקון בלי הסכם בסיס'),('unsigned_forms','טופס לא חתום (בלוק חתימה ומצייני מקום ריקים): מעמד המאגר נשאל בטופס'),('counterparty_forms','תבנית של צד שכנגד (פרטי הצד של החברה ריקים, הליך תחרותי או גוף ציבורי): נספרה כמסמך על הנייר שלו; אשרו לפי הכותרת, או רשמו ב-families.json')):
			A=b['needs_review'].get(B)
			if not A:continue
			D=[A if isinstance(A,str)else' ו-'.join(A['files'])for A in A[:3]];print('   דורש בדיקה, %s: %s'%(C,'; '.join(D)))
	print('נכתב %s'%B.out)
	if'by_family'in C:
		for A in C['by_family']:
			if A['corpus_basis']:R(A.get('label')or A.get('contract_family_id')or'סוג',A['corpus_basis'])
		if C['unclassified']:print('לא סווגו לסוג: %d קבצים'%len(C['unclassified']))
	else:R('כל הקבצים',C['corpus_basis_all_files']);print('הסיווג לסוגים נעשה לפי title_hint, ואז מריצים שוב עם --families')
if __name__=='__main__':sys.exit(main())
