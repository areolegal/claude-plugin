# -*- coding: utf-8 -*-
# Copyright (c) Areo. All rights reserved. Licensed under the terms at https://areo.co.il/legal/terms
import argparse,io,json,os,re,sys
from collections import Counter,OrderedDict
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from build_template_registry import docx_text,docx_paragraphs,guard_out
from client_text_gate import CODE_RX,HOLD_RX,NO_SOURCE_NOTE,NO_SOURCE_NOTE_EN
from derive_deal_defaults import CUR
try:sys.stdout.reconfigure(encoding='utf-8')
except(AttributeError,ValueError):pass
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from areo_rt import ensure_lib
ensure_lib()
try:from common.case_law import case_law_mentions as _lib_case_law_hits
except ImportError:_lib_case_law_hits=None
_CITE_RX=()
def case_law_hits(text):
	A=[B.group(0).strip()for A in _CITE_RX for B in A.finditer(text or'')]
	for B in _lib_case_law_hits(text)if _lib_case_law_hits else[]:
		if not any(B in A or A in B for A in A):A.append(B)
	return A
_VTOK=re.compile('[\\w\\u0590-\\u05FF]+',re.U)
def _vtoks(t):return[A.lower()for A in _VTOK.findall(t or'')if not A.isdigit()]
def _coverage(needle,hay):
	A=needle;import difflib as B
	if not A:return 1.
	C=B.SequenceMatcher(None,A,hay,autojunk=False);return sum(A.size for A in C.get_matching_blocks())/float(len(A))
INCLUDE_ANS='include','לכלול','yes','כן','כן, להוסיף','yes, add it','include it'
EXCLUDE_ANS='exclude','לא לכלול','no','לא','לא, בלי הסעיף','no, leave it out','leave it out'
def check_variance(text,draft_json,vmap,rep):
	H=vmap;G=draft_json;I=(G or{}).get('variance')or{};F,S=I.get('answers')or{},I.get('overrides')or{};J=set(I.get('defaults')or[]);P=_vtoks(text);Q=set()
	def K(cs):
		for A in cs or[]:
			B=str(A.get('variance_id')or'')
			if B:Q.add(B.split(':')[0])
			K(A.get('children')or A.get('subclauses'))
	K((G or{}).get('clauses'))
	for C in(G or{}).get('annexes')or[]:K(C.get('clauses'))
	D=[]
	for B in H.get('optional_clauses')or[]:
		A=B['id']
		if B.get('askable')is False:continue
		L=str(F.get(A,'')).lower();M=A in Q or _coverage(_vtoks(B.get('wording')),P)>=.9;R=bool(B.get('core'))and A not in F and A not in J
		if R:L='include'
		if A not in F and A not in J and not R:
			if M:D.append('%s (%s): בטיוטה, בלי תשובה ובלי ברירת מחדל'%(A,B.get('heading')))
			else:D.append('%s (%s): לא נשאל ולא נקבע בברירת מחדל'%(A,B.get('heading')))
		elif L in INCLUDE_ANS and not M:D.append('%s (%s): התשובה לכלול, והסעיף אינו בטיוטה'%(A,B.get('heading')))
		elif L in EXCLUDE_ANS and M:D.append('%s (%s): התשובה לא לכלול, והסעיף בטיוטה'%(A,B.get('heading')))
	for C in H.get('alternative_wordings')or[]:
		if C.get('askable')is False:continue
		if C['id']not in F and C['id']not in J:D.append('%s (%s): נוסח חלופי בלי תשובה ובלי ברירת מחדל'%(C['id'],C.get('heading')))
	if D:rep.add('חוסם','מפת השונות','סעיף אופציונלי או נוסח חלופי שאינו נשען על תשובה של הלקוח או על ברירת מחדל',D[:10])
	N=[]
	for E in H.get('constants')or[]:
		if E['id']in S:continue
		T=re.sub('\\{\\{F\\d+\\}\\}',' ',E.get('text_template')or E.get('text')or'');O=_coverage(_vtoks(T),P)
		if O<.97:N.append('%s (%s): %s (%.0f%% מהנוסח נמצא)'%(E['id'],E.get('heading'),'נשמט'if O<.6 else'שונה',O*100))
	if N:rep.add('חוסם','מפת השונות','סעיף קבוע, שזהה בכל ההסכמים של הלקוח, שונה או נשמט בשקט. שינוי במכוון נרשם ב-variance.overrides עם הסיבה',N[:10])
def check_case_law(sources,rep,connector=False):
	if connector:return
	A=[]
	for(B,C)in sources:
		for D in case_law_hits(C):A.append('%s: %s'%(B,D))
	if A:rep.add('חוסם','פסיקה','אזכור פסיקה בלי מחבר פסיקה סגור (כלל 1.1). פסיקה אינה נכתבת מהזיכרון או מהרשת: הסר את האזכור, וסמן את הסעיף "טעון בדיקה משפטית"',A[:10])
def _src_ids(v):
	if isinstance(v,str):return[A.strip()for A in v.split(',')if A.strip()]
	return[str(A).strip()for A in v or[]if str(A).strip()]
def _leaf_sources(clauses,inherited,out):
	B=out
	for A in clauses or[]:
		if not isinstance(A,dict):continue
		D=_src_ids(A.get('source'));C=D or inherited
		if(A.get('text')or'').strip():B.append((str(A.get('number')or A.get('heading')or'?'),C))
		_leaf_sources(A.get('children'),C,B)
	return B
def draft_clause_sources(dj):
	A=_leaf_sources(dj.get('clauses'),[],[])
	for B in dj.get('annexes')or[]:A+=_leaf_sources((B or{}).get('clauses'),[],[])
	return A
def is_outside_draft(dj):
	A=dj.get('meta')or{}
	if dj.get('sources')or any(B.upper().startswith(('REG-','MAND-','AGR-'))for(C,A)in draft_clause_sources(dj)for B in A):return True
	return bool(A.get('notice'))and A.get('source_mode')!='third_party_paper'
def check_hold_and_codes(sources,rep,cover_names):
	D=cover_names;B=rep
	try:from common.voice_check import check_text as E
	except ImportError:E=None
	for(A,C)in sources:
		F=sorted({A.group(0)for A in CODE_RX.finditer(C)})
		if F:B.add('חוסם','קודים פנימיים','%s: %d קודים פנימיים בטקסט שהלקוח רואה. מנסחים בשם ההסכם ובמספר הסעיף'%(A,len(F)),F[:10])
		G=sorted({A.group(0)for A in HOLD_RX.finditer(C)})if A in D else[]
		if G:B.add('חוסם','שער אישור','%s: נוסח של עצירה או של אישור עורך דין. הטיוטה נמסרת נקייה, בלי המתנה לאישור'%A,G[:6])
		if A not in D:
			H=[A for A in(NO_SOURCE_NOTE,NO_SOURCE_NOTE_EN)if A.lower()in C.lower()]
			if H:B.add('חוסם','דליפת נוסח פנימי','%s: השורה הפנימית של Areo בגוף ההסכם, שעלול להגיע לצד השני. בגוף ההסכם רק "[להשלמה]"; השורה המלאה בדף הליווי'%A,H)
		if E and A in D:
			I=[A['term']for A in E(C,'document')if not re.match('^[A-Z]-\\d{1,2}$',A['term'])]
			if I:B.add('חוסם','ניסוח ללקוח','%s: מילים של המערכת בטקסט שהלקוח רואה (voice_check, מצב document)'%A,sorted(set(I))[:10])
def check_sources_shown(dj,cover_text,rep):
	G=cover_text;A=rep;H=dj.get('cover')or{};B={}
	for C in H.get('documents')or[]:
		if isinstance(C,dict)and C.get('no')is not None:B[str(C.get('no'))]=(C.get('title')or'').strip()
	P=((H.get('playbook')or{}).get('name')or'').strip();L=draft_clause_sources(dj);M,I,D={},[],[]
	for(J,N)in L:
		if not N:D.append(J)
		for Q in N:
			K=Q.upper()
			if K.startswith('DOC-'):M.setdefault(K[4:],[]).append(J)
			elif K.startswith('PB-'):I.append(J)
	for(E,F)in sorted(M.items()):
		if not B.get(E):A.add('חוסם','מקור גלוי','סעיפים %s נשענים על נוסח %s, ואין לו שם ב-cover.documents. דף הליווי חייב לומר על איזה הסכם הסעיף נשען'%(', '.join(F[:6]),E),F[:10])
		elif G is not None and B[E]not in G:A.add('חוסם','מקור גלוי','שם ההסכם "%s" אינו מופיע בדף הליווי, והסעיפים %s נשענים עליו'%(B[E],', '.join(F[:6])),F[:10])
	if I and not P:A.add('חוסם','מקור גלוי','סעיפים נשענים על הפלייבוק, ואין cover.playbook.name. דף הליווי חייב לומר על איזה פלייבוק',I[:10])
	if D and any(A for(B,A)in L):
		R=' '.join(str(A)for A in H.get('notes')or[]);O=(G or'')+' '+R
		if NO_SOURCE_NOTE not in O and NO_SOURCE_NOTE_EN not in O:A.add('אזהרה','מקור גלוי','לסעיפים %s אין מקור. סעיף כזה נשען על מקור, או שדף הליווי אומר "%s" ומציע צעד הבא אחד; לא ממלאים מהזיכרון'%(', '.join(D[:8]),NO_SOURCE_NOTE),D[:12])
def check_outside_basis(dj,cover_text,rep):
	D=cover_text;A=rep
	if not is_outside_draft(dj):return
	B=dj.get('meta')or{};E=B.get('outside_basis')or{};C=[A for A in('no_playbook','no_client_agreements','client_asked')if E.get(A)is not True]
	if C:A.add('חוסם','ניסוח מבחוץ','טיוטה שנבנתה מהסכמים ברשת ומפרקטיקת שוק מותרת רק כשאין ללקוח פלייבוק, אין הסכמים, והוא ביקש זאת במפורש. חסר ב-meta.outside_basis: %s'%', '.join(C),C)
	if not(B.get('notice')or'').strip():A.add('חוסם','ניסוח מבחוץ','הטיוטה נבנתה מבחוץ, ואין meta.notice שאומר זאת בדף הליווי בבירור')
	elif D is not None and(B.get('notice')or'').strip()[:25]not in D:A.add('אזהרה','ניסוח מבחוץ','ה-notice שאומר שהטיוטה נבנתה מבחוץ אינו מופיע בדף הליווי')
_NUM_RX=re.compile('\\d[\\d,./-]*\\d|\\d')
def _norm_num(s):return re.sub('[,\\s]','',s)
def _text_norm(text):return re.sub('[,\\s]+',' ',(text or'').lower())
def deal_card_facts(path):
	try:A=json.load(io.open(path,encoding='utf-8-sig'))
	except(OSError,ValueError):return
	C=[]
	def F(v):
		if isinstance(v,str)and v.strip():C.append(v.strip())
		elif isinstance(v,dict):
			A=v.get('fact')or v.get('text')or v.get('value')
			if isinstance(A,str)and A.strip():C.append(A.strip())
	def D(o,depth=0):
		E=depth
		if E>6:return
		if isinstance(o,dict):
			for(G,B)in o.items():
				if G=='facts'and isinstance(B,list):
					for A in B:F(A)
				elif G=='parties'and isinstance(B,list):
					for A in B:
						if isinstance(A,dict)and(A.get('name')or'').strip():C.append(A['name'].strip())
				else:D(B,E+1)
		elif isinstance(o,list):
			for A in o:D(A,E+1)
	if isinstance(A,list):
		for B in A:F(B)
	else:D(A)
	return list(OrderedDict.fromkeys(C))
def fact_in_text(fact,text):
	B=fact;C=_text_norm(text);D=B.split(':',1)[1]if':'in B else B;A=[_norm_num(A)for A in _NUM_RX.findall(D)];A=[A for A in A if len(A)>=2 or not A.isdigit()]
	if A:F=_norm_num(C);return all(A.lower()in F for A in A)
	E=_vtoks(D);return not E or _coverage(E,_vtoks(C))>=.6
def check_deal_card(path,text,rep):
	B=rep;A=deal_card_facts(path)
	if A is None:B.add('חוסם','עובדות העסקה','כרטיס העסקה לא נקרא: %s'%os.path.basename(path));return
	if not A:B.add('מידע','עובדות העסקה','בכרטיס העסקה אין עובדות (facts) לבדיקה');return
	C=[A for A in A if not fact_in_text(A,text)]
	if C:B.add('חוסם','עובדות העסקה','%d מתוך %d עובדות העסקה אינן מופיעות בטיוטה. עובדה מהכרטיס נכנסת לסעיף, או מסומנת [להשלים] במקומה'%(len(C),len(A)),C[:12])
	else:B.add('מידע','עובדות העסקה','כל %d עובדות העסקה מופיעות בטיוטה'%len(A))
def core_required(core):
	B=[]
	for A in(core or{}).get('clauses')or[]:
		if not isinstance(A,dict):continue
		C=((A.get('presence')or{}).get('requirement')or'').strip().lower()
		if C=='required':B.append((str(A.get('id')or A.get('policy_ref')or''),(A.get('title')or A.get('clause_issue')or'').strip(),(A.get('preferred_wording')or(A.get('green')or{}).get('preferred_wording')or'').strip()))
	return B
def check_core(core_path,text,dj,sources,rep):
	H=core_path;B=rep
	try:I=json.load(io.open(H,encoding='utf-8-sig'))
	except(OSError,ValueError):B.add('חוסם','סעיפי ליבה','גרעין הפלייבוק לא נקרא: %s'%os.path.basename(H));return
	J=set()
	if isinstance(dj,dict):
		for(R,F)in draft_clause_sources(dj):
			for K in F:
				if K.upper().startswith('PB-'):J.add(K[3:].strip().lower())
	L=_vtoks(text);O=(text or'').lower();C=core_required(I);D=[]
	for(G,E,M)in C:
		A=G.lower()in J
		if not A and E:A=E.lower()in O or _coverage(_vtoks(E),L)>=.6
		if not A and M:A=_coverage(_vtoks(M)[:40],L)>=.5
		if not A:D.append('%s%s'%(E or'(בלי כותרת)',' [%s]'%G if G else''))
	if D:B.add('חוסם','סעיפי ליבה','%d מתוך %d סעיפי הליבה של הפלייבוק (Required) אינם בטיוטה. סעיף ליבה נכלל תמיד, עם source: PB-<הכלל>'%(len(D),len(C)),D[:12])
	elif C:B.add('מידע','סעיפי ליבה','כל %d סעיפי הליבה של הפלייבוק מכוסים'%len(C))
	F=[str(A.get('id'))for A in I.get('clauses')or[]if isinstance(A,dict)and A.get('id')]
	for(P,Q)in sources:
		N=sorted({A for A in F if re.search('(?<![\\w-])%s(?![\\w-])'%re.escape(A),Q)})
		if N:B.add('חוסם','קודים פנימיים','%s: מזהי כללים מהפלייבוק בטקסט שהלקוח רואה. כותבים את שם הנושא'%P,N[:10])
DEF_RX=[re.compile('\\(\\s*להלן\\s*:?\\s*[""״"]([^""״"]{2,60})[""״"]\\s*\\)'),re.compile('[""״"]([^""״"]{2,60})[""״"]\\s*[-–—]\\s*(?=[א-תA-Za-z])'),re.compile('\\(\\s*hereinafter[:,]?\\s+(?:the\\s+)?["“]([^"”]{2,60})["”]\\s*\\)',re.I),re.compile('\\(\\s*the\\s+["“]([^"”]{2,60})["”]\\s*\\)',re.I)]
XREF_RX=re.compile("(?:סעיף|סעיפים|ס['׳]|clause|section)\\s+(\\d+(?:\\.\\d+)*)",re.I)
ANNEX_REF_RX=re.compile("נספח\\s+([אבגדהוזחט](?:['׳](?![א-ת])|(?![א-ת]))|\\d+)|(?:Exhibit|Schedule|Annex)\\s+([A-H](?![A-Za-z])|\\d+)")
ANNEX_HEAD_RX=re.compile("^\\s*(?:נספח\\s+([אבגדהוזחט](?:['׳](?![א-ת])|(?![א-ת]))|\\d+)|(?:Exhibit|Schedule|Annex)\\s+([A-H]|\\d+))\\s*[:\\-–]?\\s*(.{0,60})$",re.I)
CLAUSE_NUM_RX=re.compile('^(?:סעיף\\s+)?(\\d+(?:\\.\\d+)*)\\s*[:\\.\\)]\\s|^(?:סעיף\\s+)?(\\d+(?:\\.\\d+)+)\\s')
DEF_SCOPE_RX=re.compile('לרבות\\s+במבוא|ובמבוא\\s+לו|including\\s+(?:in\\s+)?the\\s+recitals',re.I)
def clause_num(p):A=CLAUSE_NUM_RX.match(p.strip());return A.group(1)or A.group(2)if A else None
PLACEHOLDER_RX=re.compile('\\[(?:להשלים|to\\s+complete)[^\\[\\]\\n]*\\]|\\[[^\\[\\]\\n]{0,80}\\]|_{3,}|X{3,}|\\bTBD\\b|\\bLorem ipsum\\b|<[^>\\n]{0,30}>',re.I)
NON_GAP_LABELS='טעון בדיקה משפטית','needs legal review','להשלמה','to be completed',NO_SOURCE_NOTE.lower(),NO_SOURCE_NOTE_EN.lower(),'לא אותר','not found','not used','reserved','intentionally left blank','intentionally omitted','deleted','בוטל','נמחק','שמור'
MONEY_RX=re.compile(CUR+'\\s*([\\d,]+(?:\\.\\d+)?)|([\\d,]{4,}(?:\\.\\d+)?)\\s*'+CUR)
DATE_RX=re.compile('\\b(\\d{1,2})[./](\\d{1,2})[./](\\d{2,4})\\b')
EMDASH_RX=re.compile('[—–]')
STALE_RX=re.compile('(?:להסכם|הסכם)\\s+[א-ת]{2,}\\s+מיום\\s+\\d{1,2}\\.\\d{1,2}\\.\\d{4}')
class Report:
	def __init__(A):A.items=[]
	def add(A,level,area,msg,detail=None):A.items.append({'level':level,'area':area,'message':msg,'detail':detail or[]})
	def blocking(A):return[A for A in A.items if A['level']=='חוסם']
	def warnings(A):return[A for A in A.items if A['level']=='אזהרה']
def collect_definitions(text):
	A=OrderedDict()
	for D in DEF_RX:
		for C in D.finditer(text):
			B=C.group(1).strip()
			if 2<=len(B)<=60 and B not in A:A[B]=C.start()
	return A
def check_definitions(text,rep):
	B=rep;A=text;E=collect_definitions(A)
	if not E:B.add('אזהרה','מונחים מוגדרים','לא אותרו מונחים מוגדרים במסמך. אם זה מסמך קצר זה תקין, אחרת יש לבדוק.');return E
	F,G,H=[],[],[];C=DEF_SCOPE_RX.search(A)
	if C:J=[A.start()for A in DEF_RX[1].finditer(A,C.start())];K=C.start(),(max(J)if J else C.end())+200
	for(D,I)in E.items():
		L=[A.start()for A in re.finditer(re.escape(D),A)];O=[A for A in L if A>I+len(D)];M=[A for A in L if A<I-80]
		if not O:F.append(D)
		if M and C and K[0]<I<=K[1]:H.append(D)
		elif M:G.append(D)
	if F:B.add('אזהרה','מונחים מוגדרים','%d מונחים הוגדרו ואינם משמשים בהמשך'%len(F),F[:20])
	if G:B.add('אזהרה','מונחים מוגדרים','%d מונחים משמשים לפני שהוגדרו'%len(G),G[:20])
	if H:B.add('מידע','מונחים מוגדרים','%d מונחים משמשים לפני הגדרתם, במבוא או ברשימת ההגדרות, והפתיח של פרק ההגדרות חל גם על המבוא'%len(H),H[:20])
	N=[A for(A,B)in Counter([C.group(1).strip()for B in DEF_RX for C in B.finditer(A)]).items()if B>1]
	if N:B.add('חוסם','מונחים מוגדרים','מונח מוגדר יותר מפעם אחת. הגדרה כפולה יוצרת סתירה פרשנית',N[:20])
	return E
def check_crossrefs(paras,text,rep):
	E=paras;A=rep;B=set()
	for J in E:
		F=clause_num(J)
		if F:B.add(F)
	if not B:A.add('אזהרה','הפניות פנימיות','לא אותר מספור סעיפים בטקסט. אם המספור אוטומטי ב-Word, יש לאמת את ההפניות ידנית.');return
	G=Counter(A.group(1)for A in XREF_RX.finditer(text));D=sorted([A for A in G if A not in B],key=lambda x:[int(A)for A in x.split('.')])
	if D:A.add('חוסם','הפניות פנימיות','%d הפניות לסעיפים שאינם קיימים במסמך'%len(D),['סעיף %s (מוזכר %d פעמים)'%(A,G[A])for A in D[:20]])
	H=[A for(A,B)in Counter([clause_num(A)for A in E if clause_num(A)]).items()if B>1]
	if H:A.add('חוסם','מספור','מספר סעיף מופיע יותר מפעם אחת',sorted(H)[:20])
	C=sorted({int(A.split('.')[0])for A in B});I=[A for A in range(C[0],C[-1]+1)if A not in C]if C else[]
	if I:A.add('אזהרה','מספור','פערים ברצף הסעיפים הראשיים',['חסר סעיף %d'%A for A in I[:20]])
def check_annexes(paras,text,rep):
	D=rep;E=set()
	for A in ANNEX_REF_RX.finditer(text):E.add((A.group(1)or A.group(2)or'').strip("'׳"))
	B=set()
	for G in paras:
		A=ANNEX_HEAD_RX.match(G.strip())
		if A:B.add((A.group(1)or A.group(2)or'').strip("'׳"))
	C=sorted(E-B);F=sorted(B-E)
	if C and B:D.add('אזהרה','נספחים',DECIDE+'נספחים מוזכרים בגוף ההסכם ואינם במסמך, אף שנספחים אחרים מצורפים בו. יש לצרף אותם, או לקבוע במפורש שהם מסמך נפרד',['נספח %s'%A for A in C[:20]])
	elif C:D.add('אזהרה','נספחים','נספחים מוזכרים בגוף ההסכם ואין להם כותרת במסמך. אם הם קבצים נפרדים, יש לוודא שהם מצורפים למשלוח ושהשמות תואמים',['נספח %s'%A for A in C[:20]])
	if F:D.add('אזהרה','נספחים','נספחים שמצורפים ואינם מוזכרים בגוף ההסכם',['נספח %s'%A for A in F[:20]])
SIGBLOCK_RX=re.compile('ולראיה|על\\s+החתום|חתימה|חותמת|שם\\s*:|תפקיד\\s*:|IN\\s+WITNESS|signature|title\\s*:|name\\s*:',re.I)
def placeholder_matches(text):
	C=[]
	for A in PLACEHOLDER_RX.finditer(text):
		B=A.group(0)
		if B.startswith('_'):
			E=text[max(0,A.start()-90):A.start()+90]
			if SIGBLOCK_RX.search(E):continue
		if B.startswith('['):
			D=B[1:-1].strip()
			if D.isdigit()or D.lower()in NON_GAP_LABELS:continue
		C.append(A)
	return C
def count_placeholders(text):return len(placeholder_matches(text))
def check_placeholders(text,rep):
	A=placeholder_matches(text);C,D=[],-999
	for B in A:
		if B.start()-D<100:continue
		D=B.start();C.append(re.sub('\\s+',' ',text[max(0,B.start()-50):B.start()+60]).strip())
	if A:rep.add('אזהרה','מצייני חוסר','%d פרטים להשלים נותרו בטיוטה, מסומנים בצהוב. הם של הלקוח: נרשמים בדף הליווי ובהודעת המסירה, ואינם עוצרים את המסירה'%len(A),C[:15])
	return len(A)
VAGUE_TIME_RX=re.compile('(?:ללא|בלי|ובלי|וללא)\\s+(?:כל\\s+)?(?:דיחוי|שיהוי|עיכוב)|בהקדם(?:\\s+האפשרי)?|(?:ב|תוך|בתוך)\\s*זמן\\s+סביר|מוקדם\\s+ככל\\s+(?:ה)?(?:אפשר|ניתן)|בתוך\\s+(?:פרק\\s+)?זמן\\s+(?:קצר|מתאים)|\\bwithout\\s+(?:undue\\s+|unreasonable\\s+|any\\s+)?delay\\b|\\bpromptly\\b|\\bas\\s+soon\\s+as\\s+(?:reasonably\\s+)?(?:practicable|possible)\\b|\\bwithin\\s+a\\s+reasonable\\s+(?:time|period)\\b|\\bin\\s+a\\s+timely\\s+manner\\b|\\bexpeditiously\\b|\\bforthwith\\b',re.I)
_HE_NUM='(?:אחד|אחת|שני|שתי|שניים|שתיים|שלוש|שלושה|ארבע|ארבעה|חמש|חמישה|שש|שישה|שבע|שבעה|שמונה|תשע|תשעה|עשר|עשרה|(?:[א-ת]+\\s+)?עשרה?|עשרים|שלושים|ארבעים|חמישים|שישים|שבעים|שמונים|תשעים|מאה)'
_EN_NUM='(?:one|two|three|four|five|six|seven|eight|nine|ten|twelve|fourteen|fifteen|twenty|thirty|forty|forty-five|sixty|ninety)'
TIME_BOUND_RX=re.compile('(?:\\d+|'+_HE_NUM+')\\s*(?:\\([^)]{1,12}\\)\\s*)?(?:ימים|ימי\\s+עסקים|ימי\\s+עבודה|יום|שעות|שעה|חודשים|חודש|שבועות|שבוע|שנים|שנה)\\b|\\b(?:\\d+|'+_EN_NUM+')\\s*(?:\\([^)]{1,12}\\)\\s*)?(?:calendar\\s+|business\\s+|working\\s+)?(?:days?|hours?|months?|weeks?|years?)\\b|\\b\\d{1,2}[./]\\d{1,2}[./]\\d{2,4}\\b|עד\\s+(?:ה)?יום\\s|\\bby\\s+\\d|\\bno\\s+later\\s+than\\b|לא\\s+יאוחר\\s+מ',re.I)
def check_time_bounds(paras,rep,template_paras=None):
	D=template_paras;E=approved_matchers(D)if D else[];B,C=[],[]
	for A in paras or[]:
		if not VAGUE_TIME_RX.search(A)or TIME_BOUND_RX.search(A)or placeholder_matches(A)or'[להשלמה]'in A:continue
		F=re.sub('\\s+',' ',A).strip()[:110];(C if any(B.match(A)for B in E)else B).append(F)
	if B:rep.add('חוסם','מועדים','%d סעיפים קובעים חובה בלשון זמן עמומה (ללא דיחוי, בהקדם, בזמן סביר) בלי מספר ימים או שעות. מועד שהמקור לא קבע אינו נשמט בשקט: שאלה אחת ללקוח, או [להשלים: המועד] בגוף ושורה בדף הליווי'%len(B),B[:10])
	if C:rep.add('אזהרה','מועדים','נדרשת הכרעתך: %d סעיפים מהנוסח המאושר של התבנית קובעים חובה בלשון זמן עמומה בלי מועד במספר. הנוסח לא שונה; לקבוע מועד או להשאיר'%len(C),C[:10])
	return len(B)
COUNT_CLAIM_RX=re.compile('(\\d+)\\s+מצייני(?:\\s+(?:חוסר|\\[להשלים\\]))?|(\\d+)\\s+(?:פרטים|פריטים|שדות|מקומות)\\s+(?:\\[להשלים\\]|להשלמה|חסרים)|(\\d+)\\s+(?:open\\s+)?placeholders?\\b|(\\d+)\\s+(?:items|fields|details|markers)\\s+(?:\\[to complete\\]|to complete|missing)|(?:מצייני\\s+חוסר|placeholders)[^:\\n\\d]{0,20}:\\s*(\\d+)',re.I)
def check_cover_counts(paths,n,rep):
	B=[]
	for A in paths or[]:
		if not os.path.isfile(A):B.append('%s: הקובץ לא נמצא'%os.path.basename(A));continue
		D=docx_text(A,limit=400000)[0]if A.lower().endswith('.docx')else io.open(A,encoding='utf-8',errors='ignore').read()
		for C in COUNT_CLAIM_RX.finditer(D):
			E=int(next(A for A in C.groups()if A))
			if E!=n:B.append('%s: "%s" (בטיוטה %d)'%(os.path.basename(A),C.group(0).strip(),n))
	if B:rep.add('חוסם','מצייני חוסר','ספירת מצייני החוסר בדף הליווי או בסיכום שונה מהספירה בטיוטה. המספר נלקח רק מ-placeholders בדוח הזה',B[:10])
TEMPLATE_TAG_RX=re.compile('\\{\\{\\s*([^{}]{1,60}?)\\s*\\}\\}')
def check_template_tags(text,rep):
	A=sorted(set(A.group(1)for A in TEMPLATE_TAG_RX.finditer(text)))
	if A:rep.add('חוסם','תגיות תבנית','%d משתני תבנית נותרו בלי ערך. יש להשלים אותם בקובץ הערכים ולהריץ את המילוי שוב'%len(A),['{{%s}}'%A for A in A[:20]])
DECIDE='נדרשת הכרעתך: '
RATE_REF_RX=re.compile('(?:לפי|על\\s+פי|בהתאם\\s+ל|כמפורט\\s+ב|כקבוע\\s+ב)\\s*(?:ה)?(?:תערי(?:ף|פ\\w*)|מחירו(?:ן|נ\\w*))|(?:ה)?(?:תעריפים|תעריף|מחירון|מחירונים)\\s+(?:ש(?:ב|נקבע|נקבעו)\\w*|הקבוע\\w*|המפורט\\w*|המצור(?:ף|פ\\w*))|\\b(?:in\\s+accordance\\s+with|according\\s+to|per|at)\\s+the\\s+(?:applicable\\s+)?(?:rates?|price\\s+list|fee\\s+schedule|rate\\s+card)\\b',re.I)
RATE_WORD_RX=re.compile('תערי[פף]|מחירו[ןנ]|\\brates?\\b|price\\s+list|fee\\s+schedule|rate\\s+card',re.I)
RATE_DEF_RX=re.compile('["“”״](?:ה)?(?:תערי(?:ף|פ\\w*)|מחירו(?:ן|נ\\w*)|Rates?|Price\\s+List|Fee\\s+Schedule)["“”״]',re.I)
RATE_HEAD_RX=re.compile('^\\s*(?:נספח|Annex|Schedule|Exhibit)\\b[^\\n]{0,80}(?:תערי[פף]|מחירו[ןנ]|rate|price|fee)',re.I)
PER_UNIT_RX=re.compile('לשעה|לשעת\\s+עבודה|ליום\\s+עבודה|לחודש\\s+עבודה|per\\s+(?:hour|day|man[\\s-]?day)|hourly',re.I)
SCOPE_BASE_RX=re.compile('(?:\\d+(?:\\.\\d+)?\\s*%|אחוז\\w*)\\s*(?:מתוך\\s+|מ)?(?:ה)?(?:היקף\\s+ההתקשרות|ערך\\s+(?:ה)?הסכם|ערך\\s+ההתקשרות|שווי\\s+ההתקשרות)|(?:\\d+(?:\\.\\d+)?\\s*%|percent)\\s+of\\s+the\\s+(?:total\\s+)?contract\\s+(?:value|price|sum)',re.I)
SCOPE_DEF_RX=re.compile('["“”״](?:היקף\\s+ההתקשרות|ערך\\s+(?:ה)?הסכם|ערך\\s+ההתקשרות|שווי\\s+ההתקשרות|Contract\\s+(?:Value|Price|Sum))["“”״]',re.I)
SCOPE_TERM_RX=re.compile('היקף\\s+ההתקשרות|ערך\\s+(?:ה)?הסכם|ערך\\s+ההתקשרות|שווי\\s+ההתקשרות|contract\\s+(?:value|price|sum)',re.I)
ALL_IN_RX=re.compile('(?:כל|כלל)\\s+(?:ה)?(?:מטלה|מטלות|שירות|שירותים|עבודה|עבודות)\\s+(?:ה)?(?:אחרת|אחרים|אחרות|נוספת|נוספים|נוספות)[^.]{0,200}?(?:בתמורה\\s+הקבועה|ללא\\s+(?:כל\\s+)?תמורה\\s+נוספת|בלי\\s+(?:כל\\s+)?תמורה\\s+נוספת|ללא\\s+תוספת\\s+(?:תשלום|תמורה)|בלי\\s+תוספת\\s+(?:תשלום|תמורה)|כלול\\w*\\s+בתמורה)|any\\s+(?:other|additional|further)\\s+(?:tasks?|services|work)[^.]{0,200}?(?:at\\s+no\\s+(?:additional|extra)\\s+(?:cost|charge|fee)|(?:for|within)\\s+the\\s+fixed\\s+(?:fee|price))',re.I)
EXTRA_PAY_RX=re.compile('(?:ה)?(?:תמורה|תשלום)\\s+(?:בגין|עבור|בעד)\\s+(?:ה)?(?:שינוי|הגדלה|תוספת|שירותים\\s+נוספים|עבוד(?:ה|ות)\\s+נוספ(?:ת|ות)|מטל(?:ה|ות)\\s+נוספ(?:ת|ות))|(?:תמורה|תשלום)\\s+(?:נוסף|נוספת|נוספים)\\s+(?:בגין|עבור)|תחושב\\s+לפי\\s+(?:ה)?תערי[פף]|(?:additional|extra)\\s+(?:fees?|compensation|charges?|payment)\\s+(?:for|in\\s+respect\\s+of)\\s+(?:any\\s+)?(?:changes?|variations?|additional\\s+services)',re.I)
RECONCILE_RX=re.compile('למעט|בכפוף\\s+ל|except|subject\\s+to|other\\s+than',re.I)
FIXED_FEE_RX=re.compile('סכום\\s+קבוע|תמורה\\s+קבועה|(?:ה)?תמורה\\s+הקבועה|מחיר\\s+קבוע|fixed\\s+(?:fee|price|sum)|lump[\\s-]sum',re.I)
EXTENSION_RX=re.compile('(?:להאריך|הארכת|יוארך|יוארכו|תוארך)\\s[^.]{0,120}?(?:תקופ|חודש|שנ)|(?:extend|renew)\\w*\\s[^.]{0,80}?(?:term|period)',re.I)
EXT_PRICE_RX=re.compile('(?:בתקופ(?:ת|ות)\\s+(?:ה)?(?:הארכה|נוספות|ההארכה)|בכל\\s+הארכה|לתקופ(?:ת|ות)\\s+(?:ה)?הארכה|בהארכה)[^.]{0,200}?(?:תמורה|תעריף|מחיר|הצמד|ישולם|תשולם)|(?:תמורה|תעריף|מחיר)[^.]{0,200}?(?:בתקופ(?:ת|ות)\\s+(?:ה)?(?:הארכה|נוספות|ההארכה)|לתקופ(?:ת|ות)\\s+(?:ה)?הארכה|בהארכה)|(?:renewal|extension|extended)\\s+(?:term|period)[^.]{0,200}?(?:fees?|price|rates?|compensation)|(?:fees?|price|rates?|compensation)[^.]{0,200}?(?:renewal|extension|extended)\\s+(?:term|period)',re.I)
CONVENIENCE_RX=re.compile('(?:רשאית|רשאי|זכאית|זכאי)\\s+(?:ל)?(?:סיים|לבטל|להביא\\s+לסיום)[^.]{0,80}?(?:בכל\\s+עת|לפי\\s+שיקול\\s+דעת|מכל\\s+סיבה)|terminat\\w*[^.]{0,80}?(?:for\\s+convenience|at\\s+any\\s+time|without\\s+cause)',re.I)
MILESTONE_RX=re.compile('אב(?:ן|ני)\\s+(?:ה)?דרך|milestones?',re.I)
PRORATA_RX=re.compile('(?:באופן|חלק|בחלק|תמורה|תשלום|סכום)\\s+יחסי\\w*|יחסית\\s+ל|לפי\\s+החלק\\s+(?:היחסי|שבוצע|שהושלם)|בשיעור\\s+(?:ההתקדמות|הביצוע)|pro[\\s-]?rata|proportion\\w*',re.I)
LD_RX=re.compile('פיצוי(?:ים)?\\s+מוסכ(?:ם|מ\\w*)|liquidated\\s+damages',re.I)
LD_OPERATIVE_RX=re.compile('ישלם|ישולם|תשלם|יחויב|ישולמו|\\d|%|shall\\s+pay|will\\s+pay|payable',re.I)
CAP_RX=re.compile('תקר|לא\\s+(?:י|ת)על(?:ה|ו)\\s+על|לא\\s+יותר\\s+מ|עד\\s+(?:ל)?(?:סך|סכום|שיעור)|בסך\\s+(?:ה)?כול\\s+לא|shall\\s+not\\s+exceed|\\bcap(?:ped)?\\b|maximum\\s+aggregate|in\\s+(?:the\\s+)?aggregate',re.I)
PROPOSAL_RX=re.compile("הצע(?:ת|תו)\\s+(?:ה)?(?:יועץ|ספק|קבלן|נותן\\s+השירות\\w*|מציע|היועץ|הספק|הקבלן)?[^.]{0,80}?(?:מצורפת|כנספח|חלק\\s+בלתי\\s+נפרד)|(?:ה)?הצעה[^.]{0,60}?(?:מצורפת|כנספח|חלק\\s+בלתי\\s+נפרד)|(?:supplier|consultant|contractor|vendor|provider)['’]?s?\\s+proposal[^.]{0,80}?(?:attached|schedule|annex|exhibit|integral)",re.I)
PROPOSAL_WORD_RX=re.compile('הצע(?:ה|ת|תו)\\b|proposal',re.I)
PROPOSAL_EXCL_RX=re.compile('לא\\s+יחול\\w*|אינ(?:ם|ו|ן|ה)\\s+חלק|לא\\s+יהי(?:ו|ה)\\s+חלק|לא\\s+יחייב\\w*|(?:היקף|לוח\\s+(?:ה)?זמנים|אנשי\\s+(?:ה)?צוות)[^.]{0,160}?בלבד|shall\\s+not\\s+apply|do(?:es)?\\s+not\\s+form\\s+part|(?:is|are)\\s+excluded|shall\\s+have\\s+no\\s+effect|solely\\s+(?:for|as\\s+to)',re.I)
BODY_PREVAILS_RX=re.compile('יגבר\\s+(?:ה)?(?:אמור|נוסח)\\s+ב(?:גוף\\s+)?ההסכם|גוף\\s+ההסכם\\s+יגבר|הוראות\\s+ההסכם\\s+יגברו|(?:this\\s+agreement|the\\s+body\\s+of\\s+this\\s+agreement)\\s+shall\\s+(?:prevail|govern)',re.I)
def where(p):A=clause_num(p);B=re.sub('\\s+',' ',p).strip();return'סעיף %s: %s'%(A,B[len(A):].lstrip('. ')[:100])if A else B[:110]
def check_mechanisms(paras,text,rep,role=None):
	C=text;B=rep;A=paras;G=[A for A in A if RATE_REF_RX.search(A)];P=bool(RATE_DEF_RX.search(C))or any(RATE_HEAD_RX.match(A)for A in A)or any(RATE_WORD_RX.search(A)and(MONEY_RX.search(A)or PER_UNIT_RX.search(A))for A in A)
	if G and not P:B.add('חוסם','עיגון מנגנונים','הפניה לתעריפים או למחירון שאינם קיימים בהסכם: אין הגדרה, נספח או סעיף שקובעים אותם. יש לקבוע את התעריפים (בגוף ההסכם או בנספח) או לנסח מנגנון אחר',[where(A)for A in G[:8]])
	H=[A for A in A if SCOPE_BASE_RX.search(A)];Q=bool(SCOPE_DEF_RX.search(C))or any(SCOPE_TERM_RX.search(A)and MONEY_RX.search(A)and not SCOPE_BASE_RX.search(A)for A in A)
	if H and not Q:B.add('אזהרה','עיגון מנגנונים',DECIDE+'סכום שמחושב כאחוז מ"היקף ההתקשרות" או מערך ההסכם, והמונח אינו מוגדר. עם הארכות ושינויי היקף הסכום אינו ניתן לקביעה. יש להגדיר את הבסיס (למשל סך התמורה לתקופה הראשונה)',[where(A)for A in H[:8]])
	D=[A for A in A if ALL_IN_RX.search(A)and not RECONCILE_RX.search(A)];I=[A for A in A if EXTRA_PAY_RX.search(A)]
	if D and[A for A in I if A not in D]:B.add('חוסם','סתירה בין מנגנוני התמורה','סעיף אחד קובע שכל מטלה אחרת או נוספת כלולה בתמורה הקבועה, וסעיף אחר מזכה בתמורה בגין שינוי או תוספת. יש להכריע ולנסח מנגנון אחד: מה כלול בתמורה, ומה מתומחר ולפי מה',[where(A)for A in(D+[A for A in I if A not in D])[:8]])
	R=bool(FIXED_FEE_RX.search(C));J=[A for A in A if EXTENSION_RX.search(A)]
	if R and J and not any(EXT_PRICE_RX.search(A)for A in A):B.add('אזהרה','עיגון מנגנונים',DECIDE+'ההסכם מאפשר הארכה, והתמורה קבועה לתקופה הראשונה, בלי מחיר או מנגנון מחיר לתקופת ההארכה. יש לקבוע את התמורה בהארכה, או שההארכה מותנית בהסכמה בכתב על התמורה',[where(A)for A in J[:6]])
	K=[A for A in A if CONVENIENCE_RX.search(A)]
	if K and MILESTONE_RX.search(C)and not PRORATA_RX.search(C):B.add('אזהרה','עיגון מנגנונים',DECIDE+'סיום לפי שיקול דעת בלי מנגנון לחישוב יחסי של התמורה באמצע אבן דרך. יש לקבוע כיצד משולמת אבן דרך שבביצוע (לפי החלק שהושלם ונמסר, או לא כלל)',[where(A)for A in K[:6]])
	for F in A:
		E=re.sub('^\\s*(?:סעיף\\s+)?\\d+(?:\\.\\d+)*\\s*[.:)]?\\s*','',F);L=placeholder_matches(E)
		if not LD_RX.search(E)or CAP_RX.search(E)or not(L or LD_OPERATIVE_RX.search(E)):continue
		if L:B.add('חוסם','פיצוי מוסכם','פיצוי מוסכם בלי סכום ובלי תקרה. כשהסכום לא נמסר: ציין מקום עם סכום מוצע ותקרה מוצעת, והערה בדף הליווי: הוראת הדין החל על פיצוי מוסכם נבדקת במחקר העומק, מרשימת המקורות המאושרים',[where(F)])
		else:B.add('אזהרה','פיצוי מוסכם',DECIDE+'פיצוי מוסכם בלי תקרה מצטברת',[where(F)])
	M=[A for A in A if PROPOSAL_RX.search(A)]
	if M and not company_gives(role):
		N=any(PROPOSAL_WORD_RX.search(A)and PROPOSAL_EXCL_RX.search(A)for A in A);O=bool(BODY_PREVAILS_RX.search(C))
		if not(N and O):S=([]if N else['אין החרגה של התנאים הכלליים, ההסתייגויות והגבלת האחריות שבהצעה'])+([]if O else['אין הוראה שבסתירה גוף ההסכם גובר על ההצעה']);B.add('אזהרה','הצעת הצד השני כנספח',DECIDE+'הצעה משולבת בהסכם. כשהיא של הצד השני, ממנה חלים רק ההיקף, הצוות ולוח הזמנים: '+'; '.join(S),[where(A)for A in M[:6]])
PUBLIC_BODY_FORMS={'חברה ממשלתית','גוף ציבורי או משרד ממשלתי','רשות מקומית','תאגיד סטטוטורי','מוסד להשכלה גבוהה או אוניברסיטה','גוף ציבורי (משרד ממשלתי, רשות מקומית, תאגיד סטטוטורי)','Government company','Public body or government ministry','Local authority (municipality or local council)','Statutory corporation','University or higher education institution','Public body (government ministry, local authority, statutory corporation)'}
PUBLIC_STRONG=(re.compile('הצהרה\\s+לפי[^.\\n]{0,60}גופים\\s+ציבוריים|declaration\\s+(?:under|pursuant\\s+to)[^.\\n]{0,60}(?:public\\s+bod|public\\s+procurement|government\\s+contract)',re.I),'הצהרה לפי כללי העסקאות של גופים ציבוריים'),(re.compile('ועדת\\s+(?:ה)?מכרזים|ועדת\\s+רכש|מסמכי\\s+(?:ה)?מכרז|tender\\s+committee|procurement\\s+committee|tender\\s+documents',re.I),'הוראות של הליך תחרותי ציבורי'),(re.compile('נוהלי\\s+רכש\\s+(?:ממשלתי|ציבורי)|(?:government|public)\\s+procurement\\s+(?:circular|directive|manual|rules)',re.I),'נוהלי רכש של גוף ציבורי')
PUBLIC_SOFT=(re.compile('ערבות\\s+(?:בנקאית|ביצוע|אוטונומית|מכרז)|(?:bank|performance)\\s+guarantee',re.I),'ערבות בנקאית או ערבות ביצוע, לצד סימנים של טופס ציבורי'),
COMPANY_PUBLIC_ROLES={'contracting_authority'}
COUNTERPARTY_PUBLIC_ROLES={'bidder','מציע'}
GIVING_ROLES={'bidder','מציע','proposer','submitting_party'}
def _role(role):return str(role or'').strip().lower()
def company_gives(role):return _role(role)in GIVING_ROLES
def is_public_body(profile):
	A=profile or{}
	if A.get('public_body')is True:return True
	return str(A.get('organization_type')or'').strip()in PUBLIC_BODY_FORMS
def public_party(profile,counterparty_public=None,role=None):A=_role(role);return bool(is_public_body(profile)or A in COMPANY_PUBLIC_ROLES or counterparty_public or A in COUNTERPARTY_PUBLIC_ROLES)
def draft_facts(path):
	try:A=json.load(io.open(path,encoding='utf-8-sig'))
	except(OSError,ValueError):return None,None
	if not isinstance(A,dict):return None,None
	B=A.get('meta')if isinstance(A.get('meta'),dict)else{};D=B.get('counterparty_public_body',A.get('counterparty_public_body'));C=B.get('company_role_code',A.get('company_role_code'));return bool(D),str(C).strip()if C else None
def check_public_form(paras,rep,profile=None,keep=False,counterparty_public=None,role=None):
	F=counterparty_public;E=paras;C=profile;B=rep
	if public_party(C,F,role):return
	A=[(C,where(A))for A in E for(B,C)in PUBLIC_STRONG if B.search(A)];G=[(C,where(A))for A in E for(B,C)in PUBLIC_SOFT if B.search(A)]if A else[]
	if keep:
		if A:B.add('מידע','שאריות טופס ציבורי','סעיפים שמקורם בטופס של גוף ציבורי, ונשארו לבקשת המשתמש',['%s (%s)'%(B,A)for(A,B)in(A+G)[:10]])
		return
	if not A:return
	D=['%s (%s)'%(B,A)for(A,B)in(A+G)[:10]]
	if C is None:B.add('אזהרה','שאריות טופס ציבורי',DECIDE+'סעיפים שחלים רק כשאחד הצדדים גוף ציבורי. בלי --profile לא נבדק אם החברה גוף ציבורי; אם אף צד אינו גוף ציבורי, הסעיפים אינם נכנסים ומוצעים כאפשרות בדף הליווי',D)
	elif F is None:B.add('אזהרה','שאריות טופס ציבורי',DECIDE+'סעיפים שחלים רק כשאחד הצדדים גוף ציבורי. החברה אינה גוף ציבורי לפי הפרופיל (%s), ולא נמסר אם הצד שכנגד גוף ציבורי (--draft-json או --counterparty-public-body). אם הוא גוף ציבורי, הסעיפים במקומם; אם לא, הם אינם נכנסים ומוצעים כאפשרות בדף הליווי'%(C.get('organization_type')or'לא צוין'),D)
	else:B.add('חוסם','שאריות טופס ציבורי','סעיפים שמקורם בטופס של גוף ציבורי, או בדרישה שחלה רק על גוף ציבורי, ואף אחד מהצדדים אינו גוף ציבורי: החברה לפי הפרופיל (%s), והצד שכנגד לפי הטיוטה. הסעיף אינו נכנס: מוצע כאפשרות בדף הליווי, או נשאר רק לבקשת המשתמש'%(C.get('organization_type')or'לא צוין'),D)
def check_amounts_dates(text,rep):
	D=[A.group(1)or A.group(2)for A in MONEY_RX.finditer(text)];E=[A.replace(',','')for A in D if A];C=[A for(A,B)in Counter(E).items()if B>1]
	if C:rep.add('מידע','סכומים','סכומים החוזרים יותר מפעם אחת. יש לוודא שהחזרה מכוונת ואינה סתירה',[A for A in C[:12]])
	B=[]
	for A in DATE_RX.finditer(text):
		F,G,H=int(A.group(1)),int(A.group(2)),A.group(3)
		if G>12 or F>31:B.append(A.group(0))
		elif len(H)==2:B.append(A.group(0)+' (שנה דו ספרתית)')
	if B:rep.add('אזהרה','תאריכים','תאריכים בעייתיים או לא חד משמעיים',B[:15])
def approved_matchers(template_paras):
	A=[]
	for B in template_paras:
		if not EMDASH_RX.search(B):continue
		C=TEMPLATE_TAG_RX.split(B);D=[re.escape(B)for(A,B)in enumerate(C)if A%2==0];A.append(re.compile('\\A'+'.*?'.join(D)+'\\Z',re.S))
	return A
def check_style(text,rep,hebrew,paras=None,template_paras=None):
	G=template_paras;F=paras;A=rep
	if hebrew:
		C=len(EMDASH_RX.findall(text))
		if C and G is not None and F is not None:
			J=approved_matchers(G);D,B=0,[]
			for E in F:
				H=len(EMDASH_RX.findall(E))
				if not H:continue
				if any(A.match(E)for A in J):D+=H
				else:B.append(E)
			if B:A.add('חוסם','סגנון','%d מקפים ארוכים בטקסט שנכתב לטיוטה ואינו מהתבנית. יש להחליף בפסיק, בנקודה או בנקודתיים'%sum(len(EMDASH_RX.findall(A))for A in B),[A[:90]for A in B[:8]])
			if D:A.add('אזהרה','סגנון','%d מקפים ארוכים בנוסח המאושר של התבנית. לא שונו, כי נוסח מאושר אינו משתנה; להסרתם יש לעדכן את התבנית עצמה'%D)
		elif C:A.add('חוסם','סגנון','%d מקפים ארוכים במסמך עברי. יש להחליף בפסיק, בנקודה או בנקודתיים'%C)
	I=[A.group(0)for A in STALE_RX.finditer(text)]
	if I:A.add('מידע','שמות תקדים','הפניות להסכמים אחרים בגוף המסמך. יש לוודא שאינן שריד מתבנית',list(dict.fromkeys(I))[:12])
def main():
	D=argparse.ArgumentParser();D.add_argument('draft');D.add_argument('--json');D.add_argument('--strict',action='store_true',help='אזהרה נחשבת ממצא חוסם');D.add_argument('--template',help='master.docx שממנו מולאה הטיוטה: מקף ארוך בנוסח המאושר הוא אזהרה ולא חוסם');D.add_argument('--profile',help='פרופיל-לקוח.json: האם החברה גוף ציבורי (שאריות של טופס ציבורי)');D.add_argument('--draft-json',help='draft.json של הטיוטה (או קובץ הערכים של התבנית): meta.counterparty_public_body ו-meta.company_role_code');D.add_argument('--counterparty-public-body',action='store_true',help='הצד שכנגד גוף ציבורי (כשאין draft.json, למשל בטיוטה שמולאה מתבנית)');D.add_argument('--role',help='company_role_code של החברה מהפלייבוק (bidder, contracting_authority, service_provider ...)');D.add_argument('--cover',nargs='+',help='דף הליווי והסיכום (docx, md, txt): הספירה שבהם מול הטיוטה');D.add_argument('--keep-public-form',action='store_true',help='המשתמש ביקש במפורש סעיף מטופס של גוף ציבורי: הממצא יורד לרמת מידע');D.add_argument('--variance-map',help='variance-map.json של המשפחה: עקיבות של סעיפים אופציונליים, נוסחים חלופיים וקבועים (דורש --draft-json)');D.add_argument('--deal-card',help='כרטיס העסקה: קובץ הטיוטה (cover.facts, meta.parties), negotiation_state.json של העסקה, או {"facts": [...]}: כל עובדה בו חייבת להופיע בטיוטה');D.add_argument('--core',help='playbook-core.json שבשימוש: כל כלל Required מכוסה בטיוטה, ואף מזהה כלל אינו בטקסט שהלקוח רואה');D.add_argument('--case-law-connector',action='store_true',help='מחבר פסיקה סגור שהלקוח חיבר זמין בהרצה (כלל 1.1). בלעדיו, אזכור פסיקה בטיוטה או בדף הליווי הוא ממצא חוסם');A=D.parse_args()
	if A.json:guard_out(A.json,[A.draft,A.template,A.profile,A.draft_json,A.deal_card,A.core]+list(A.cover or[]))
	O=None
	if A.profile:
		try:O=json.load(io.open(A.profile,encoding='utf-8-sig'))
		except(OSError,ValueError):print('הפרופיל לא נקרא: %s'%A.profile);sys.exit(2)
	I,J=None,A.role
	if A.draft_json:
		I,R=draft_facts(A.draft_json)
		if I is None:print('קובץ הטיוטה לא נקרא: %s'%A.draft_json);sys.exit(2)
		J=J or R
	if A.counterparty_public_body:I=True
	if not os.path.isfile(A.draft):print('הקובץ לא נמצא: %s'%A.draft);sys.exit(2)
	if A.draft.lower().endswith('.docx'):C=docx_text(A.draft,limit=400000)[0];E=docx_paragraphs(A.draft,limit=20000)
	else:C=io.open(A.draft,encoding='utf-8',errors='ignore').read();E=C.split('\n')
	if not C.strip():print('לא הופק טקסט מהמסמך.');sys.exit(2)
	P=len(re.findall('[א-ת]',C))>len(re.findall('[A-Za-z]',C));B=Report();check_definitions(C,B);check_crossrefs(E,C,B);check_annexes(E,C,B);L=check_placeholders(C,B)
	if A.cover:check_cover_counts(A.cover,L,B)
	check_template_tags(C,B);check_mechanisms(E,C,B,J);check_public_form(E,B,O,A.keep_public_form,I,J);check_amounts_dates(C,B);G=[(os.path.basename(A.draft),C)]
	for H in A.cover or[]:
		if os.path.isfile(H):G.append((os.path.basename(H),docx_text(H,limit=400000)[0]if H.lower().endswith('.docx')else io.open(H,encoding='utf-8',errors='ignore').read()))
	check_case_law(G,B,A.case_law_connector);M={os.path.basename(A)for A in A.cover or[]};check_hold_and_codes(G,B,M);F=None
	if A.draft_json and os.path.isfile(A.draft_json):
		try:F=json.load(io.open(A.draft_json,encoding='utf-8-sig'))
		except(OSError,ValueError):F=None
	if isinstance(F,dict)and F.get('clauses'):Q=' '.join(B for(A,B)in G if A in M)if M else None;check_sources_shown(F,Q,B);check_outside_basis(F,Q,B)
	if A.deal_card:check_deal_card(A.deal_card,C,B)
	if A.core:check_core(A.core,C,F,G,B)
	if A.variance_map:
		try:S=json.load(io.open(A.variance_map,encoding='utf-8'));T=json.load(io.open(A.draft_json,encoding='utf-8'))if A.draft_json else{}
		except(OSError,ValueError):print('מפת השונות או קובץ הטיוטה לא נקראו: %s'%A.variance_map);sys.exit(2)
		check_variance(C,T,S,B)
	N=None
	if A.template:
		if not os.path.isfile(A.template):print('התבנית לא נמצאה: %s'%A.template);sys.exit(2)
		N=docx_paragraphs(A.template,limit=20000)
	check_time_bounds(E,B,N);check_style(C,B,P,E,N);print('בדיקת שלמות: %s'%os.path.basename(A.draft));U={'חוסם':0,'אזהרה':1,'מידע':2}
	for K in sorted(B.items,key=lambda x:U.get(x['level'],3)):
		print('  [%s] %s: %s'%(K['level'],K['area'],K['message']))
		for V in K['detail'][:8]:print('        %s'%V)
	if not B.items:print('  לא נמצאו ממצאים.')
	print('סיכום: %d חוסמים, %d אזהרות, %d מצייני חוסר'%(len(B.blocking()),len(B.warnings()),L))
	if A.json:io.open(A.json,'w',encoding='utf-8').write(json.dumps({'file':os.path.basename(A.draft),'hebrew':P,'findings':B.items,'placeholders':L,'blocking':len(B.blocking()),'warnings':len(B.warnings())},ensure_ascii=False,indent=2))
	W=len(B.blocking())or A.strict and len(B.warnings());sys.exit(1 if W else 0)
if __name__=='__main__':main()
