# -*- coding: utf-8 -*-
# Copyright (c) Areo. All rights reserved. Licensed under the terms at https://areo.co.il/legal/terms
import io,json,os,posixpath,re,sys
from urllib.parse import parse_qsl,unquote,urlparse
if os.path.dirname(os.path.abspath(__file__))not in sys.path:sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
SCOPES={'agreements':'איסוף הסכמים מייצגים','research':'מחקר רגולטורי בשכבות','both':'איסוף הסכמים ומחקר רגולטורי'}
COURT_HOST_MARKERS='court.gov.il','courts.','curia.europa.eu','supremecourt','judiciary','bailii.org','caselaw.','canlii.org','austlii.edu.au','courtlistener.com','tribunal'
COURT_PATH_MARKERS='psika','verdict','judgment','judgement','/juri','ecli','celex:6','celex%3a6','tribunal-decisions','/cases/','case-law','caselaw'
try:import sys as _sys;_sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)));from areo_rt import ensure_lib;ensure_lib();from common.case_law import case_law_url as _lib_case_law_url
except ImportError:_lib_case_law_url=None
APPROVED_SOURCES_ENV='AREO_APPROVED_SOURCES'
APPROVED_SOURCES_FILE='מקורות-מאושרים.json'
MISSING_SOURCES='רשימת המקורות המאושרים (מקורות-מאושרים.json) לא נטענה. אין מחקר רגולטורי בלעדיה. העותק נארז בתוסף (lib/מקורות-מאושרים.json); כשהוא חסר או שנמסר נתיב אחר שאינו קיים, תקנו את הנתיב ב---approved-sources.\nThe approved sources list (מקורות-מאושרים.json) was not loaded. There is no regulatory research without it.'
def default_sources_path():
	try:from areo_rt import areo_lib as B;A=B()
	except ImportError:A=None
	return os.path.join(A,APPROVED_SOURCES_FILE)if A else None
class ApprovedSourcesMissing(Exception):0
NORM_RANKS={1:'חקיקה ראשית',2:'חקיקת משנה',3:'הוראה מחייבת של רגולטור',4:'הנחיה או מדריך של רגולטור',5:'עמדת סגל או שו"ת',6:'מקור בהליך'}
RANK_STATUS={1:'מחייב',2:'מחייב',3:'מחייב',4:'מנחה',5:'מנחה',6:'בהליך'}
MANDATORY_ALLOWED_RANKS=1,2,3
RECOMMENDED_RANKS=4,5
MIN_AGREEMENTS,TARGET_AGREEMENTS,MAX_AGREEMENTS=10,10,15
AGREEMENT_SOURCE_ORDER='רגולטור','גוף ציבורי','הליך תחרותי ציבורי','דיווח פומבי','אתר המפרסם','אחר'
FORBIDDEN_AGREEMENT_SOURCES='משרד עורכי דין','אתר משפטי','מאגר מסחרי'
COMMERCIAL_REPOSITORY_HOSTS='lawinsider.com','lawdepot.com','rocketlawyer.com','legalzoom.com','docracy.com','legaltemplates.net','contractstandards.com','onecle.com'
VERBATIM_OK='רגולטור','גוף ציבורי'
ORIENTATIONS='לטובת הפוזיציה','מאוזן','נגד הפוזיציה'
NOT_FOUND='[לא אותר]'
def _parts(url):
	try:A=urlparse(url or'');return(A.hostname or'').lower(),A.path or''
	except Exception:return'',''
def _host_matches(host,entry):
	B=host;A=entry
	if A.startswith('.'):return B.endswith(A)
	return B==A or B.endswith('.'+A)
_SOURCES_CACHE={}
try:from risk.validate_register import approved_domains as _lib_approved_domains;from common.net import rule_matches as _lib_rule_matches
except ImportError:_lib_approved_domains=_lib_rule_matches=None
def _norm_dom(d):d=(d or'').strip().lower().split('://',1)[-1].rstrip('/').rstrip('.');return d[4:]if d.startswith('www.')else d
def _src_rules(src):
	A=src;C,I,D=_norm_dom(A.get('domain')).partition('/')
	if A.get('status')!='approved'or not C:return[]
	B=[A for A in A.get('allowed_paths')or[]if(A or'').strip('/')]
	if D:B=B or['/'+D]
	H=any((A.get(B)or'').strip()for B in A if B.startswith('usage_restriction'));E=A.get('restriction_kind')
	if(H or E=='paths')and not B and E!='content':return[]
	F=(''if A.get('include_subdomains')else'=')+C;G=[F+'/'+A.strip().lstrip('/')for A in B]or[F];G+=['='+_norm_dom(A)for A in A.get('include_hosts')or[]if _norm_dom(A)];return G
def _page_rule(pg):
	if pg.get('status')!='approved'or not pg.get('url'):return
	A=urlparse(pg['url']);B=_norm_dom(A.hostname)
	if not B:return
	C=[A for A in A.query.split('&')if re.match('(?i)(officeid|topicid|type)=',A)];return'='+B+(A.path.rstrip('/')or'')+('?'+'&'.join(C)if C else'')
def _case_law_rules(data):
	B=(data or{}).get('case_law_only')
	if isinstance(B,dict):D=list(B.get('sources')or[])+list(B.get('domains')or[])or[B for A in B.get('jurisdictions')or[]for B in A.get('sources')or[]]
	else:D=list(B or[])
	E=[]
	for A in D:
		A={'domain':A}if isinstance(A,str)else A or{};C=_norm_dom(A.get('domain'))
		if C:F=[A for A in A.get('paths')or A.get('allowed_paths')or[]if(A or'').strip('/')];E+=['!'+C+'/'+A.lstrip('/')for A in F]or['!'+C]
	return E
def load_approved_sources(path=None):
	A=path;A=A or os.environ.get(APPROVED_SOURCES_ENV)or default_sources_path()
	if A in _SOURCES_CACHE:return _SOURCES_CACHE[A]
	C=(),None
	if A and os.path.isfile(A):
		if _lib_approved_domains:
			try:B,D=_lib_approved_domains(A);C=(tuple(B)+tuple(getattr(B,'refuse',())),D)if D else((),None)
			except Exception:C=(),None
		else:
			try:
				with io.open(A,encoding='utf-8-sig')as J:E=json.load(J)
				B=[]
				for F in E.get('jurisdictions')or[]:
					for G in F.get('sources')or[]:
						if isinstance(G,dict):B+=_src_rules(G)
					for H in F.get('pages')or[]:
						I=_page_rule(H)if isinstance(H,dict)else None
						if I:B.append(I)
				if B:C=tuple(dict.fromkeys(B+_case_law_rules(E))),A
			except(OSError,ValueError,AttributeError):C=(),None
	_SOURCES_CACHE[A]=C;return C
def require_approved_sources(path=None):
	A,B=load_approved_sources(path)
	if not B:raise ApprovedSourcesMissing(MISSING_SOURCES)
	return A
def _norm_path(path):A=unquote(path or'/').replace(chr(92),'/');A=posixpath.normpath('/'+A.lstrip('/'));A=re.sub('/+','/',A);return('/'if A in('.','')else A).lower()
def _path_under(path,prefix,bounded=True):
	B=path;A=prefix;A=_norm_path(A).rstrip('/')or'/'
	if A=='/':return True
	return B.startswith(A)if not bounded else B==A or B.startswith(A+'/')
def rule_matches(url,rule):
	A=rule
	if _lib_rule_matches:return _lib_rule_matches(url,A)
	A=(A or'').strip();F=A.startswith('!');A=A[1:]if F else A;D=A.startswith('=');A=A[1:]if D else A;A=A[2:]if A.startswith('*.')else A;A,I,G=A.partition('?');B,I,H=A.partition('/');B=B.lower().strip('.');B=B[4:]if B.startswith('www.')else B
	try:E=urlparse(url or'');C=(E.hostname or'').lower().rstrip('.')
	except ValueError:return False
	if not C or not B:return False
	if D and C not in(B,'www.'+B):return False
	if not D and not(C==B or C.endswith('.'+B)):return False
	if H and not _path_under(_norm_path(E.path),'/'+H,bounded=not F):return False
	if G:
		J={(A.lower(),B.lower())for(A,B)in parse_qsl(E.query,keep_blank_values=True)}
		if any((A.lower(),B.lower())not in J for(A,B)in parse_qsl(G,keep_blank_values=True)):return False
	return True
def case_law_source(url):
	A=url
	if _lib_case_law_url:
		C=_lib_case_law_url(A)
		if C:return C
	B,E=_parts(A);D=(A or'').lower().split(B,1)[-1]if B else''
	if any(A in B for A in COURT_HOST_MARKERS)or any(A in D for A in COURT_PATH_MARKERS):return'פסיקה אינה מקור במחקר הזה. פסיקה רק ממחבר פסיקה סגור שהלקוח חיבר (כלל 1.1)'
def law_source_problem(url,jurisdiction=None,approved_sources=None):
	A=url;B,E=_parts(A)
	if not B:return'אין קישור'
	C=case_law_source(A)
	if C:return C
	D=require_approved_sources(approved_sources)
	if any(B.startswith('!')and rule_matches(A,B)for B in D):return'מסומן ברשימה המשותפת כמקור פסיקה בלבד (case_law_only): %s'%B
	if any(not B.startswith('!')and rule_matches(A,B)for B in D):return
	return'אינו ברשימת המקורות המאושרים (מקורות-מאושרים.json), בדומיין, בתת-דומיין או בנתיב: %s'%B
EU_MEMBERS='AT','BE','BG','HR','CY','CZ','DK','EE','FI','FR','DE','GR','HU','IE','IT','LV','LT','LU','MT','NL','PL','PT','RO','SK','SI','ES','SE'
def applies_within(src_law,base_law):
	C=src_law;import governing_law as D;A,B=D.code(C)or str(C or'').strip().upper(),D.code(base_law)
	if not(A and B):return False
	E=B.split('-')[0];return A==B or A==E or A=='EU'and E in EU_MEMBERS
def agreement_source_problem(agreement):
	B=agreement;C=(B.get('source_type')or'').strip()
	if C in FORBIDDEN_AGREEMENT_SOURCES:return'מקור מסוג "%s" אינו מותר גם לנוסח (hard-rules.md המשותף, מקורות לנוסחים)'%C
	A,D=_parts(B.get('url'))
	if A and any(A==B or A.endswith('.'+B)for B in COMMERCIAL_REPOSITORY_HOSTS):return'מאגר מסחרי (%s) משמש לאיתור בלבד; את ההסכם מצטטים מהמקור המקורי'%A
def normalise(research):
	A=dict(research);D='structures'in A
	if'agreements'not in A and A.get('structures'):A['agreements']=[dict(B,no=A+1)for(A,B)in enumerate(A['structures'])]
	if D and not A.get('scope'):B,C=bool(A.get('agreements')),bool(A.get('law'));A['scope']='both'if B and C else'agreements'if B else'research'if C else''
	A.setdefault('approvals',{});return A
def scope_has(research,part):A=research.get('scope');return A=='both'or A==part
def check(research,stage='brief',approved_sources=None,inc_country=None):
	R=approved_sources;import governing_law as S;C=normalise(research);B,G=[],[];J={'law':[],'agreements':[],'mandatory':[]}
	if C.get('scope')not in SCOPES:B.append('לא נבחר היקף העבודה (scope): agreements, research או both.')
	if not C.get('consent_at'):B.append('אין תיעוד לבקשה המפורשת של הלקוח לנסח מבחוץ (consent_at). ניסוח מבחוץ רק כשאין ללקוח פלייבוק ואין הסכמי טיוטה, והוא ביקש זאת במפורש.')
	if not(C.get('company_role')or'').strip():B.append('הפוזיציה של המשתמש (company_role) חסרה. היא נשאלת, ולעולם אינה מוסקת.')
	H=C.get('law')or[]
	if scope_has(C,'research'):
		if not H:B.append('נבחר מחקר רגולטורי, ואין אף מקור דין.')
		require_approved_sources(R)
		if not C.get('jurisdiction'):B.append('הדין החל (jurisdiction) לא נקבע. הוא נקבע לפני המחקר: מהמשתמש, מנייר הבית, או בשאלה אחת עם המלצה לפי מדינת ההתאגדות שבפרופיל, והמחקר נערך בתוכו.')
		T=S.code(C.get('jurisdiction'))or S.code(inc_country);K=0
		for(E,A)in enumerate(H):
			D=[];U=A.get('instrument')or'שורה %d'%(E+1);V=law_source_problem(A.get('url'),A.get('jurisdiction'),R)
			if V:B.append('מקור דין %d (%s): %s'%(E+1,U,V));D.append('מקור אסור')
			L=A.get('rank')
			if L not in NORM_RANKS:B.append('מקור דין %d (%s): חסר דרג במדרג הנורמטיבי (1 עד 6).'%(E+1,U))
			else:
				if L<K:B.append('השורות אינן ממוינות לפי המדרג: מקור %d בדרג %d אחרי דרג %d.'%(E+1,L,K))
				K=max(K,L)
			if not A.get('verified'):D.append('טעון אימות')
			if not(A.get('jurisdiction')or'').strip():D.append('תחום שיפוט לא צוין')
			elif T and not applies_within(A.get('jurisdiction'),T):D.append('דין זר')
			for Z in('published_original','published_last'):
				if A.get(Z)in(None,'',NOT_FOUND):D.append('תאריך לא אותר');break
			J['law'].append(D)
		a={A.get('row',B+1):A for(B,A)in enumerate(H)}
		for M in C.get('mandatory_clauses')or[]:
			D=[];A=a.get(M.get('source_row'));O=M.get('clause_id')or'?'
			if A is None:B.append('סעיף חובה %s: אין שורת מקור %s במחקר.'%(O,M.get('source_row')))
			else:
				if not A.get('verified'):B.append('סעיף חובה %s נשען על מקור שלא אומת (שורה %s).'%(O,M.get('source_row')))
				if A.get('rank')not in MANDATORY_ALLOWED_RANKS:B.append('סעיף חובה %s נשען על מקור בדרג %s. סעיף חובה רק מדרגים 1 עד 3; מדרגים 4 ו-5 נגזר סעיף מומלץ.'%(O,A.get('rank')))
			J['mandatory'].append(D)
		b={A.get('source_row')for A in C.get('mandatory_clauses')or[]}
		for(E,A)in enumerate(H):
			c=A.get('row',E+1)
			if A.get('mandatory')and A.get('verified')and A.get('rank')in MANDATORY_ALLOWED_RANKS and c not in b:B.append('מקור %d (%s) סומן כמחייב סעיף חובה, ולא נגזר ממנו סעיף חובה.'%(E+1,A.get('instrument')or''))
		if C.get('layers_checked'):G.append('שכבות שנבדקו: '+', '.join(C['layers_checked']))
		G.append('המחקר מוגבל למאגר המקורות המאושרים. נקודה שאין לה מקור מורשה מסומנת: AREO לא מצאה מקור מורשה לנקודה זו.')
	elif H:G.append('נבחר איסוף הסכמים בלבד, ולכן מקורות הדין שבקובץ אינם חלק מהתוצר.')
	I=C.get('agreements')or[]
	if scope_has(C,'agreements'):
		if len(I)>MAX_AGREEMENTS:B.append('%d הסכמים. התקרה היא %d.'%(len(I),MAX_AGREEMENTS))
		elif len(I)<MIN_AGREEMENTS:G.append('נמצאו %d הסכמים רלוונטיים, פחות מ-%d.%s'%(len(I),MIN_AGREEMENTS,' הסיבה: '+C['agreements_shortfall_reason']if C.get('agreements_shortfall_reason')else''))
		e=C.get('company_role')or'';W={A.get('clause_id')for A in C.get('mandatory_clauses')or[]}
		for(E,F)in enumerate(I):
			D=[];N=F.get('title')or'הסכם %d'%(E+1);d,f=_parts(F.get('url'))
			if not d:B.append('הסכם %d (%s) בלי קישור.'%(E+1,N))
			P=F.get('orientation')
			if P not in ORIENTATIONS:B.append('הסכם %d (%s): חסר כיוון ביחס לפוזיציה.'%(E+1,N))
			elif P=='נגד הפוזיציה':B.append('הסכם %d (%s) מסווג "נגד הפוזיציה" ואינו נכלל.'%(E+1,N))
			if P in ORIENTATIONS and not(F.get('orientation_reason')or'').strip():D.append('חסר נימוק לכיוון')
			X=agreement_source_problem(F)
			if X:B.append('הסכם %d (%s): %s.'%(E+1,N,X))
			Q=F.get('source_type')or'אחר'
			if Q=='אחר':D.append('מקור לא מסווג: ודאו שאינו אתר משרד עורכי דין או מאגר מסחרי')
			D.append('מותר כלשונו, בציון המקור'if Q in VERBATIM_OK else'מבנה, נושאים ועמדות בלבד')
			if Q=='הליך תחרותי ציבורי':D.append('נכתב לטובת הגוף הציבורי המזמין');D.append('לעיון בלבד, אלא אם החברה היא הגוף המזמין')
			Y=[A for A in F.get('missing_mandatory')or[]if W and A not in W]
			if Y:D.append('סעיפי חובה לא מוכרים: '+', '.join(Y))
			J['agreements'].append(D)
	return B,J,G
def approved_mandatory(research):return[A for A in normalise(research).get('mandatory_clauses')or[]if A.get('status')!='הוסר']
def approved_agreements(research):A=normalise(research);B=set(str(A)for A in(A.get('approvals')or{}).get('removed_agreements')or[]);return[A for A in A.get('agreements')or[]if str(A.get('no'))not in B]
MONTHS_EN='January','February','March','April','May','June','July','August','September','October','November','December'
def display_date(v,lang='he'):
	A=(v or'').strip()
	if len(A)>=10 and A[4]=='-'and A[7]=='-'and A[:4].isdigit()and A[5:7].isdigit()and A[8:10].isdigit():
		C,B,D=A[:4],int(A[5:7]),int(A[8:10])
		if 1<=B<=12:
			if str(lang or'he')[:2].lower()=='en':return'%d %s %s'%(D,MONTHS_EN[B-1],C)
			return'%d.%d.%s'%(D,B,C)
	return A or NOT_FOUND
def lookup_source(url,path=None):
	B=url
	try:from common.approved_sources import lookup as C
	except ImportError:C=None
	if C:return C(B,path)
	D,I=_parts(B);A={'url':B,'host':D};E,H=load_approved_sources(path)
	if not H:A.update(status='no_list',reason=MISSING_SOURCES.split('\n')[0]);return A
	F=case_law_source(B)
	if F or any(A.startswith('!')and rule_matches(B,A)for A in E):A.update(status='case_law_only',reason=F or'case_law_only');return A
	G=next((A for A in E if not A.startswith('!')and rule_matches(B,A)),None)
	if G:A.update(status='approved',entry={'rule':G})
	else:A.update(status='not_on_list',reason='אינו ברשימת המקורות המאושרים: %s'%D)
	return A
def main(argv=None):
	import argparse as E;sys.dont_write_bytecode=True
	try:sys.stdout.reconfigure(encoding='utf-8')
	except(AttributeError,ValueError):pass
	B=E.ArgumentParser(description='כללי המקורות של הניסוח מבחוץ');F=B.add_subparsers(dest='cmd',required=True);C=F.add_parser('lookup',help='הרשומה של כתובת אחת ברשימת המקורות המאושרים, בלי לקרוא את הרשימה');C.add_argument('--url',required=True);C.add_argument('--approved-sources',help='מקורות-מאושרים.json (ברירת מחדל: AREO_APPROVED_SOURCES, ואחריו העותק שבתוסף, lib/מקורות-מאושרים.json)');D=B.parse_args(argv);A=lookup_source(D.url,D.approved_sources);print(json.dumps(A,ensure_ascii=False,indent=1));return 0 if A['status']=='approved'else 2 if A['status']=='no_list'else 1
if __name__=='__main__':sys.exit(main())
