#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (c) Areo. All rights reserved. Licensed under the terms at https://areo.co.il/legal/terms
'בדיקת הקבלה של ה-Word של הפלייבוק, לפני מסירה.'
import datetime as _dt,json,os,re,shutil,subprocess,sys,zipfile
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
import areo_lib
from common import rtl
from common.cli import OutputRefused,guard_out,load_docx_or_explain,no_bytecode,parser
from lxml import etree
from playbook import status as S,surfaces_render as R
W='{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
REL='{http://schemas.openxmlformats.org/officeDocument/2006/relationships}'
PKG_REL='{http://schemas.openxmlformats.org/package/2006/relationships}'
PLACEHOLDERS='טרם נכתב','יושלם במעבר','יושלם בהמשך','TBD','TODO','[●]','XXX'
PLACEHOLDER_RX=re.compile('\\[\\s*להשלים\\s*\\]|(?:^|:\\s*)להשלים\\s*[.]?\\s*$|\\[\\s*to complete\\s*\\]',re.M|re.I)
AS_DATA=re.compile('\\{\\s*[\'\\"]he[\'\\"]'),re.compile('\\{\\s*[\'\\"]en[\'\\"]'),re.compile('\\bdict\\('),re.compile('(?:^|[:=,\\[(]\\s*)None(?=\\s*(?:$|[,\\]}).;]))',re.M),re.compile('\\[\\s*\\{\\s*[\'\\"]')
AREO_TAG='הצעת Areo (לא מבוסס על מסמכי הלקוח)'
SOURCES_HEAD='המקורות שעליהם נשען הפלייבוק'
BRIEF_HEAD='העמדות בקצרה'
TRACKS='ירוק','צהוב','אדום'
W_ID=re.compile('\\bW-\\d+\\b')
NAMES={'he':{'sources':SOURCES_HEAD,'brief':BRIEF_HEAD,'tracks':TRACKS,'approved':re.compile('מאושר')},'en':{'sources':'Sources the playbook relies on','brief':'Positions at a glance','tracks':('Green','Yellow','Red'),'approved':re.compile('\\bapproved\\b',re.I)}}
_APPR_HE='(?:[והשכלמב]{0,3})(?:מאושר(?:ת|ים|ות)?|אושר(?:ה|ו)?)'
_SUBJ_HE='(?:[והשכלמב]{0,3})(?:פלייבוק|מדיניות|עמד(?:ה|ת|ות)|מסלול(?:ים)?|כרטיס(?:ים)?|מעמד|סטטוס)'
_APPR_EN='approved'
_SUBJ_EN='(?:playbooks?|polic(?:y|ies)|positions?|tracks?|cards?|status)'
_GAP='(?:[^\\w\\n]+\\w+){0,2}[^\\w\\n]+'
STATUS_CLAIM={A:re.compile('^\\W*%(a)s\\W*$|(?<!\\w)%(s)s%(g)s%(a)s(?!\\w)|(?<!\\w)%(a)s%(g)s%(s)s(?!\\w)'%{'a':B,'s':C,'g':_GAP},re.I)for(A,B,C)in(('he',_APPR_HE,_SUBJ_HE),('en',_APPR_EN,_SUBJ_EN))}
INLINE_QUOTE=re.compile('(?:(?<=^)|(?<=[\\s(\\[:]))(?:"[^"\\n]+"|“[^”\\n]+”|„[^“”\\n]+[“”]|«[^»\\n]+»)(?=$|[\\s.,;:)\\]])')
DASHES=re.compile('[–—]')
MODEL_CODES={'he':('green','yellow','red','Draft','PartiallyApproved','Approved','Superseded','Invalid'),'en':('PartiallyApproved','AgreeWithComments','NotApproved','own_plus_market','market_built','areo_proposal','market_standard','NotResearched','NotAssessed')}
NOT_RUN=None,'','not_run','skipped','NotPerformed','not_performed','NotRun','none'
class Result:
	def __init__(A):A.checks=[]
	def add(A,num,name,failures,skipped=None):A.checks.append({'check':num,'name':name,'failures':list(failures or()),'skipped':skipped})
	@property
	def failed(self):return[A for A in self.checks if A['failures']]
	@property
	def skipped(self):return[A for A in self.checks if A['skipped']]
	def to_dict(A):return{'passed':not A.failed,'checks':A.checks}
def doc_parts(path):
	with zipfile.ZipFile(path)as A:B=A.namelist();return{B:A.read(B)for B in B}
def text_of(parts):
	A=parts;B=[]
	for D in['word/document.xml']+sorted(A for A in A if re.match('word/(header|footer)\\d*\\.xml$',A)):
		E=etree.fromstring(A[D])
		for F in E.iter(W+'p'):
			C=''.join(A.text or''for A in F.iter(W+'t'))
			if C.strip():B.append(C)
	return B
def doc_lang(parts):
	B=parts;D=(B.get('docProps/core.xml')or b'').decode('utf-8','replace');A=re.search('<dc:language>([^<]*)</dc:language>',D)
	if A and A.group(1).strip():return'en'if A.group(1).strip().lower().startswith('en')else'he'
	E=etree.fromstring(B['word/document.xml']);C=next(E.iter(W+'sectPr'),None);return'he'if C is not None and C.find(W+'bidi')is not None else'en'
HEB=re.compile('[\u0590-\u05ff]')
HEBREW_SHARE_LIMIT=.2
LANG_NOTE_EN='written in Hebrew'
def audit_ltr(path,run_date=None):
	A=[A for A in rtl.audit_docx(path,run_date=run_date,require_hebrew=False)if A.startswith(('מאפייני הקובץ','מספור','אין sectPr'))];D=H=0;I=False
	with zipfile.ZipFile(path)as M:
		for B in['word/document.xml']+sorted(A for A in M.namelist()if re.match('word/(header|footer)\\d*\\.xml$|word/comments\\.xml$|word/styles\\.xml$',A)):
			J=etree.fromstring(M.read(B));E=K=0
			for L in J.iter(W+'p'):
				N=L.find(W+'pPr');O=N is not None and N.find(W+'bidi')is not None;C=''.join(A.text or''for A in L.iter(W+'t'));F=bool(HEB.search(C));U=F and len(HEB.findall(C))>=len(re.findall('[A-Za-z]',C))
				if B=='word/document.xml'and C.strip():D+=1;H+=F;I=I or LANG_NOTE_EN in C
				if O and not F:A.append('%s: פסקה עם bidi במסמך באנגלית: %s'%(B,C[:40]))
				if U and not O:
					E+=1
					if E<=3:A.append('%s: פסקה בעברית בלי bidi במסמך באנגלית: %s'%(B,C[:40]))
				for P in L.iter(W+'r'):
					G=''.join(A.text or''for A in P.iter(W+'t'));Q=P.find(W+'rPr');R=Q.find(W+'rtl')if Q is not None else None;S=R is not None and R.get(W+'val')not in('0','false')
					if HEB.search(G)and not S:K+=1
					elif S and not HEB.search(G):
						if not F and G.strip():A.append('%s: ריצה לטינית עם rtl במסמך באנגלית: %s'%(B,G[:30]))
			if E>3:A.append('%s: עוד %d פסקאות בעברית בלי bidi'%(B,E-3))
			if K:A.append('%s: %d ריצות בעברית בלי rtl במסמך באנגלית'%(B,K))
			for V in J.iter(W+'bidiVisual'):A.append('%s: טבלה עם bidiVisual במסמך באנגלית'%B);break
			for T in J.iter(W+'sectPr'):
				if T.find(W+'bidi')is not None or T.find(W+'rtlGutter')is not None:A.append('%s: מקטע עם bidi או rtlGutter במסמך באנגלית'%B)
	if D and H/D>HEBREW_SHARE_LIMIT and not I:A.append('מסמך באנגלית ש-%d%% מפסקאותיו בעברית, בלי הודעה ללקוח שהטקסט בעברית'%round(100*H/D))
	return A
def _qkey(text):return re.sub('[\\W_]+','',text or'')
def model_quotes(model):
	E=set()
	def B(v,parent=''):
		C=parent
		if isinstance(v,dict):
			for(D,A)in v.items():
				if isinstance(A,str)and(D in('quote','verbatim','quote_text')or D=='text'and C in('evidence','citations')):
					F=_qkey(A)
					if len(F)>=4:E.add(F)
				else:B(A,D if isinstance(A,list)else C)
		elif isinstance(v,list):
			for A in v:B(A,C)
	B(model);return E
def _is_quote_line(line,quotes,blob=None):
	B=quotes;A=_qkey(line)
	if not A or not B:return False
	if A in B:return True
	return len(A)>=20 and blob is not None and A in blob
def written_text(lines,quotes):A=quotes;C='\x00'.join(A);return[INLINE_QUOTE.sub(' ',B)for B in lines if not _is_quote_line(B,A,C)]
def check_content(lines,model,lang='he',quotes=None):
	D=lines;B=quotes;A=[];K='\n'.join(D);B=model_quotes(model)if B is None else B;E=written_text(D,B);C='\n'.join(E)
	for F in E:
		if DASHES.search(F):A.append('מקף ארוך או קצר בטקסט שאינו ציטוט: %s'%F.strip()[:70])
	for G in PLACEHOLDERS:
		if G in C:A.append('מחזיק מקום במסמך: "%s"'%G)
	if PLACEHOLDER_RX.search(C):A.append('מחזיק מקום במסמך: "להשלים"')
	for L in AS_DATA:
		H=L.search(C)
		if H:A.append('נוסח שהודפס כמבנה נתונים: %s'%H.group(0))
	for I in MODEL_CODES[lang]:
		if re.search('(?<![\\w-])%s(?![\\w-])'%I,C):A.append('ערך באנגלית מהמודל בטקסט: "%s"'%I)
	for J in NAMES[lang]['tracks']:
		if J not in K:A.append('אין במסמך את המסלול "%s"'%J)
	return A
def check_sources_and_label(parts,lines,model,st,docx=None,lang='he',quotes=None):
	H=lang;G=model;C=quotes;B=lines;D=list(R.check_surfaces(st,word_path=docx,model=G)or());L='\n'.join(B);E=NAMES[H]['sources'];J=G.get('market_research')or{}
	if J and J.get('status')not in NOT_RUN:
		if E not in L:D.append('רץ מחקר שוק ואין פרק "%s"'%E)
	I=set();F=False
	for A in B:
		if E in A:F=True;continue
		if F and A.strip().startswith('##'):F=False
		if F:I|=set(W_ID.findall(A))
	for A in B:
		if E in A:break
		for K in W_ID.findall(A):
			if I and K not in I:D.append('מזהה %s בשורת מקור ואינו בפרק המקורות'%K)
	C=model_quotes(G)if C is None else C
	for A in written_text([A for A in B if not _is_status_line(A,st)],C):
		if STATUS_CLAIM[H].search(A):D.append('המילה "%s" כטענת מעמד בשורה שאינה שורת המעמד: %s'%('approved'if H=='en'else'מאושר',A.strip()[:70]))
	return D
def _is_status_line(line,st):
	A=st.get('label')or'';B=line.strip()
	if B.startswith(R.SUMMARY_PREFIXES+R.CELL_PREFIXES):return True
	return bool(A)and(A in line or B in(A,A+'.'))
def _rule_keys(model):
	B=[]
	for A in model.get('rules')or[]:
		C=str(A.get('topic_name')or A.get('topic')or A.get('rule_id')or'').strip()
		if C:B.append(C)
	return B
def check_brief(lines,model,lang='he'):
	B=_rule_keys(model)
	if not B:return[],'אין כללים במודל'
	C='\n'.join(lines);A=NAMES[lang]['brief']
	if A not in C:return['אין פרק "%s"'%A],None
	E=C.split(A,1)[1];D=[A for A in B if A not in E];return['אין שורה ב"%s" לכללים: %s'%(A,', '.join(D[:8]))]if D else[],None
RED_TITLE={'he':'אדום: לא מתקבל','en':'Red: not acceptable'}
def _green_keys(model):
	B=set()
	for E in model.get('rules')or[]:
		A=((E.get('traffic_light')or{}).get('green')or{}).get('proposed_clause')
		for C in A.values()if isinstance(A,dict)else[A]:
			D=_qkey(C)if isinstance(C,str)else''
			if len(D)>=12:B.add(D)
	return B
def check_red(lines,model,lang='he'):
	B=lines;E,F,C=RED_TITLE[lang],_green_keys(model),[]
	for(D,G)in enumerate(B):
		if not G.strip().startswith(E):continue
		for A in B[D+1:D+5]:
			if A.strip()in RED_TITLE.values()or re.match('^\\d+\\.\\s',A.strip()):break
			if _qkey(A)in F:C.append('נוסח הירוק מודפס מתחת לכותרת האדום: %s'%A.strip()[:70]);break
	return C
def check_numbering(lines,model):A=_rule_keys(model);B='\n'.join(lines);return['נושא שאינו במסמך: %s'%A for A in A if A not in B]
def check_links(parts,model):
	L=model;C=parts;A=[];M='word/_rels/document.xml.rels'
	if M not in C:return['אין קובץ יחסים למסמך']
	D={}
	for E in etree.fromstring(C[M]).iter(PKG_REL+'Relationship'):D[E.get('Id')]=E.get('Target'),E.get('TargetMode')or'Internal'
	B=etree.fromstring(C['word/document.xml']);Q={A.get(W+'name')for A in B.iter(W+'bookmarkStart')};F=set()
	for N in _iter_sources(L):
		if N.get('url'):F.add(N['url'].rstrip('/'))
	for G in B.iter(W+'hyperlink'):
		H,I=G.get(REL+'id'),G.get(W+'anchor');J=''.join(A.text or''for A in G.iter(W+'t'))
		if I:
			if I not in Q:A.append('קישור פנימי בלי יעד: "%s" -> %s'%(J[:40],I))
			continue
		if not H or H not in D:A.append('קישור בלי יחס: "%s"'%J[:40]);continue
		O,R=D[H]
		if R!='External':A.append('קישור חיצוני בלי יחס חיצוני: "%s"'%J[:40])
		elif F and O.rstrip('/')not in F:A.append('יעד הקישור אינו ברשומה: %s'%O[:70])
	S={''.join(A.text or''for A in A.iter(W+'t'))for A in B.iter(W+'hyperlink')};T=_verbatim_texts(L)
	for U in B.iter(W+'p'):
		P=''.join(A.text or''for A in U.iter(W+'t'))
		for K in re.finditer('https?://\\S+',P):
			if not any(K.group(0)in A for A in S)and not _in_quote(P,K,T):A.append('כתובת שמודפסת כטקסט בלבד: %s'%K.group(0)[:60])
	return A
def _norm(text):return' '.join(DASHES.sub(lambda d:', 'if ord(d.group(0))==8212 else'-',str(text or'')).split())
def _verbatim_texts(model):
	B=model;G=[]
	def A(v):
		if isinstance(v,dict):
			for B in('he','en','text'):A(v.get(B))
		elif isinstance(v,str)and'http'in v:G.append(_norm(v))
	for D in B.get('citations')or():
		if isinstance(D,dict):A(D.get('quote')),A(D.get('text'))
	for C in B.get('rules')or():
		if not isinstance(C,dict):continue
		for E in C.get('evidence')or():
			if isinstance(E,dict):A(E.get('quote')),A(E.get('text'))
		for J in[C.get('traffic_light')or{}]+[A.get('traffic_light')or{}for A in C.get('segment_variants')or()if isinstance(A,dict)]:
			for F in J.values():
				if isinstance(F,dict):A(F.get('proposed_clause')),A(F.get('fallback_wording'))
	K=B.get('coverage')or{}
	for H in K.get('unique_clauses')or():
		if isinstance(H,dict):A(H.get('quote'))
	for I in(B.get('commercial')or{}).get('rows')or():
		if isinstance(I,dict):A(I.get('quote'))
	return G
def _in_quote(par,m,quotes):
	B=m.group(0).rstrip('.,;)"\'');E=_norm(par)
	for C in quotes:
		A=C.find(B)
		if A<0:continue
		D=C[max(0,A-40):A].strip()or C[A+len(B):A+len(B)+40].strip()
		if not D or D in E:return True
	return False
def _iter_sources(model):
	B=model;D=B.get('market_research')or{}
	for E in('sources','external_sources','findings','source_refs'):
		for A in D.get(E)or():
			if isinstance(A,dict):
				yield A
				if A.get('final_url'):yield{'url':A['final_url']}
	for A in(B.get('regulatory_research')or{}).get('sources')or():
		if isinstance(A,dict):yield A
	for A in B.get('external_sources')or():
		if isinstance(A,dict):yield A
	for C in B.get('external_sources_table')or():
		if isinstance(C,dict):yield C
def check_parity(lines,artifact):
	E=artifact
	if not E:return[],'לא נמסר --artifact'
	try:
		with open(E,encoding='utf-8')as G:H=G.read()
	except OSError as B:return['לא ניתן לקרוא את הארטיפקט: %s'%B],None
	try:C=R._find_payload(H)[0]
	except Exception as B:return[],'אין בארטיפקט נתונים מוזרקים (%s)'%type(B).__name__
	if not isinstance(C,dict):return[],'מטען הנתונים בארטיפקט אינו אובייקט'
	I='\n'.join(lines);F=[];J=C.get('rules')or(C.get('model')or{}).get('rules')or[]
	for A in J:
		D=A.get('topic_name')or A.get('topic')or A.get('rule_id')or A.get('id')
		if D and D not in I:F.append('נושא בארטיפקט ואין לו כרטיס ב-Word: %s'%D)
	return F,None
def check_visual(path,run_date):
	B=path;C=shutil.which('soffice')or shutil.which('libreoffice')
	if not C:return[],'אין בסביבה כלי המרה ל-PDF (soffice/libreoffice)'
	A=os.path.join(os.path.dirname(os.path.abspath(B)),'.pdf-check')
	try:
		os.makedirs(A,exist_ok=True);E=subprocess.run([C,'--headless','--convert-to','pdf','--outdir',A,B],capture_output=True,timeout=180);D=os.path.join(A,os.path.splitext(os.path.basename(B))[0]+'.pdf')
		if E.returncode!=0 or not os.path.exists(D):return['ההמרה ל-PDF נכשלה'],None
		if os.path.getsize(D)<2048:return['ה-PDF שנוצר ריק כמעט לגמרי'],None
		return[],None
	except(OSError,subprocess.SubprocessError)as F:return[],'ההמרה ל-PDF לא רצה: %s'%F
	finally:shutil.rmtree(A,ignore_errors=True)
def check_properties(parts,model,company=''):
	C=model;A=company;D=parts.get('docProps/core.xml')
	if D is None:return['אין docProps/core.xml'],None
	F=D.decode('utf-8','replace');E=re.search('<dc:creator[^>]*>([^<]*)</dc:creator>',F);B=(E.group(1)if E else'').strip();A=(A or C.get('company_name')or C.get('organization_name')or(C.get('company')or{}).get('name')or'').strip()
	if not B:return[],None
	if not A:return[],'המחבר בקובץ "%s", ואין במודל שם חברה להשוות אליו'%B
	if B!=A:return['המחבר בקובץ "%s", ולא שם החברה "%s" ולא ריק'%(B,A)],None
	return[],None
def main(argv=None):
	no_bytecode();F=parser(__doc__.split('\n')[0],out_required=False,out_help='אופציונלי: נתיב לדוח הקבלה כ-JSON. בלעדיו: הדפסה בלבד');F.add_argument('--docx',required=True,help='ה-Word שנבנה');F.add_argument('--model',required=True,help='playbook-model.json');F.add_argument('--artifact',help='סביבת העבודה, לבדיקת השוויון');F.add_argument('--run-date',help='יום ההפקה (YYYY-MM-DD). ברירת מחדל: היום');F.add_argument('--profile',help='פרופיל-לקוח.json: שם החברה, להשוואה למחבר הקובץ');F.add_argument('--lang',choices=('he','en'),help='שפת המסמך. בלעדיו: מהמסמך עצמו (language במאפייני הקובץ, או bidi במקטע)');A=F.parse_args(argv)
	for(O,R)in((A.docx,'ה-Word'),(A.model,'המודל')):
		if not os.path.exists(O):print('%s אינו קיים: %s'%(R,O));return 2
	T,U,V=load_docx_or_explain(A.docx,loader=False)
	if T is None:print(U);return V
	with open(A.model,encoding='utf-8')as J:D=json.load(J)
	try:M=_dt.date.fromisoformat(A.run_date)if A.run_date else _dt.date.today()
	except ValueError:print('--run-date אינו תאריך: %s'%A.run_date);return 2
	K=doc_parts(A.docx);H=text_of(K);E=A.lang or doc_lang(K);W=S.gate_status(D,A.model,lang=E);print('שפת המסמך: %s (%s)'%(E,'LTR'if E=='en'else'RTL'));B=Result();P=model_quotes(D);B.add(1,'כיווניות',audit_ltr(A.docx,M)if E=='en'else rtl.audit_docx(A.docx,run_date=M));B.add(2,'תוכן',check_content(H,D,E,P)+check_red(H,D,E));X,G=check_parity(H,A.artifact);B.add(3,'שוויון מול הארטיפקט',X,G);Y,G=check_visual(A.docx,M);B.add(4,'בדיקה חזותית',Y,G);B.add(5,'מקורות ותווית',check_sources_and_label(K,H,D,W,A.docx,E,P));B.add(6,'מספור והפניות',check_numbering(H,D));B.add(7,'קישורים חיצוניים',check_links(K,D));Z,G=check_brief(H,D,E);B.add(8,'תווית ומעמד',Z,G);I=''
	if A.profile:
		try:
			with open(A.profile,encoding='utf-8')as J:Q=json.load(J)
			I=(E=='en'and str(Q.get('organization_name_en')or'').strip()or Q.get('organization_name')or'').strip()
		except(OSError,ValueError):pass
		for N in(', ח.פ',' ח.פ'):
			if N in I and'['in I.split(N,1)[1][:20]:I=I.split(N,1)[0].strip(' ,')
	a,G=check_properties(K,D,I);B.add(9,'מאפייני הקובץ',a,G)
	for C in B.checks:
		if C['failures']:
			print('%d. %s: נכשל'%(C['check'],C['name']))
			for b in C['failures']:print('     %s'%b)
		elif C['skipped']:print('%d. %s: דולגה (%s)'%(C['check'],C['name'],C['skipped']))
		else:print('%d. %s: עבר'%(C['check'],C['name']))
	c=[A['name']for A in B.checks if not A['skipped']];print('\nנבדק: %s.'%', '.join(c))
	if B.skipped:print('לא נבדק: %s. אמור זאת בהודעת המסירה.'%', '.join('%s (%s)'%(A['name'],A['skipped'])for A in B.skipped))
	if A.out:
		try:L=guard_out(A.out,inputs=[A.docx,A.model,A.artifact])
		except OutputRefused as d:print('הדוח לא נכתב. סירוב: %s'%d)
		else:
			if os.path.dirname(L):os.makedirs(os.path.dirname(L),exist_ok=True)
			with open(L,'w',encoding='utf-8')as J:json.dump(B.to_dict(),J,ensure_ascii=False,indent=2)
			print('נכתב %s'%L)
	if B.failed:print('המסמך אינו נמסר: נכשל ב-%d בדיקות.'%len(B.failed));return 3
	return 0
if __name__=='__main__':sys.exit(main())
