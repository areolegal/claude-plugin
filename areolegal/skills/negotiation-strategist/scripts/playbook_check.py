# -*- coding: utf-8 -*-
# Copyright (c) Areo. All rights reserved. Licensed under the terms at https://areo.co.il/legal/terms
import argparse,io,json,os,re,sys
try:sys.stdout.reconfigure(encoding='utf-8')
except(AttributeError,ValueError):pass
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from areo_rt import ensure_lib
ensure_lib()
PLACEHOLDER=re.compile('\\[[^\\[\\]\\n]{1,60}\\]')
TXT={'he':{'no_clauses':'בפלייבוק אין עמדות.','no_family':'בפלייבוק לא נרשם סוג ההסכם.','no_role':'בפלייבוק לא נרשם הצד של החברה בהסכם.','no_position':'לנושא "%s" אין עמדה.','dup':'אותו נושא מופיע פעמיים: %s.','placeholder':'בנוסח המועדף של "%s" נשאר מקום ריק להשלמה: %s.','kind':'הפלייבוק נבנה מהסכמים עם צד מסוג אחר (%s), ולא עם %s. כדאי לבדוק כל עמדה לפני שמחילים אותה.','draft':'הפלייבוק הוא עדיין טיוטת מדיניות, שמחכה לאישור שלכם.','invalid':'הפלייבוק לא עבר את הבדיקות שלו. כדאי שעורך דין יעבור עליו לפני שמסתמכים עליו.','head':'בדיקת הפלייבוק: %d הערות.','ok':'בדיקת הפלייבוק: אין הערות.','side':'הצד לא ברור: לפי הפלייבוק החברה היא %s, ובמסמך היא מוגדרת "%s". הצד נשאר פתוח עד שתאשרו מה הצד שלכם בהסכם הזה.','gives':'הצד שנותן את השירות, הנכס או המידע','gets':'הצד שמקבל את השירות, הנכס או המידע','one':'בדיקת הפלייבוק: הערה אחת.'},'en':{'no_clauses':'The playbook has no positions.','no_family':'The playbook does not record the agreement type.','no_role':"The playbook does not record the company's side.",'no_position':'The topic "%s" has no position.','dup':'The same topic appears twice: %s.','placeholder':'The preferred wording of "%s" still has a blank to fill in: %s.','kind':'The playbook was built from agreements with a different kind of counterparty (%s), not %s. Check each position before applying it.','draft':'The playbook is still a draft policy, awaiting your approval.','invalid':'The playbook did not pass its own checks. A lawyer should review it before you rely on it.','head':'Playbook check: %d notes.','ok':'Playbook check: no notes.','side':'Your side is unclear: the playbook makes the company %s, but the document defines it as "%s". Your side stays open until you confirm it for this agreement.','gives':'the side that provides the service, asset or information','gets':'the side that receives the service, asset or information','one':'Playbook check: 1 note.'}}
def _s(v):return str(v or'').strip()
def local_problems(core,counterparty_kind=None,lang='he'):
	E=counterparty_kind;C=core;D=TXT['en'if str(lang)[:2]=='en'else'he'];B=[];I=C.get('clauses')or C.get('rules')or[]
	if not I:B.append(('warn',D['no_clauses']))
	if not(_s(C.get('family_id'))or C.get('contract_families')):B.append(('warn',D['no_family']))
	if not(_s(C.get('company_role_code'))or _s(C.get('company_role'))):B.append(('warn',D['no_role']))
	F={}
	for A in I:
		if not isinstance(A,dict):continue
		J=_s(A.get('title')or A.get('clause_issue')or A.get('id'));G=_s(A.get('id'))
		if G:F[G]=F.get(G,0)+1
		K=A.get('green')or{};N=_s(K.get('position'))or _s(A.get('preferred_wording'))or _s((A.get('yellow')or{}).get('position'))or _s((A.get('red')or{}).get('position'))or _s(A.get('red_line'))
		if not N:B.append(('warn',D['no_position']%J))
		O=_s(K.get('preferred_wording'))or _s(A.get('preferred_wording'));L=PLACEHOLDER.search(O)
		if L:B.append(('warn',D['placeholder']%(J,L.group(0))))
	M=[A for(A,B)in F.items()if B>1]
	if M:B.append(('warn',D['dup']%', '.join(M[:5])))
	H=[_s(A)for A in(C.get('applicability')or{}).get('counterparty_kinds')or[]if _s(A)]
	if E and H and _s(E)not in H:B.append(('warn',D['kind']%(', '.join(H),E)))
	if _s(C.get('playbook_status')).lower()in('draft','partiallyapproved'):B.append(('info',D['draft']))
	return B
DEFINED=re.compile('\\(\\s*(?:להלן\\s*[:\\-]?\\s*|hereinafter\\s*(?:referred\\s+to\\s+as\\s*)?|the\\s+)?["“״\\\']([^"”״\\\'\\)]{2,40})["”״\\\']\\s*\\)',re.I)
def doc_text(path):
	A=path;D=(A or'').lower()
	try:
		with open(A,'rb')as E:B=E.read(5)
	except OSError:return''
	if B.startswith(b'%PDF'):
		try:
			try:import pymupdf as C
			except ImportError:import fitz as C
			with C.open(A)as F:return'\n'.join(A.get_text()for A in F)
		except Exception:return''
	if B.startswith(b'PK'):
		import zipfile as G
		try:
			with G.ZipFile(A)as H:I=H.read('word/document.xml').decode('utf-8','ignore')
		except Exception:return''
		return re.sub('\\s+',' ',re.sub('<[^>]+>',' ',I.replace('</w:p>','\n')))
	if D.endswith(('.txt','.md')):return io.open(A,encoding='utf-8',errors='ignore').read()
	return''
def _key(v):
	A=re.sub('[\\s_\\-]+',' ',_s(v).strip().lower()).strip(' .,:;"\'״')
	if A.startswith('ה')and len(A)>3:A=A[1:]
	return A
def side_of_role(code):return _key(code)or None
def side_in_document(text,names):
	A=(text or'')[:6000]
	for E in[A for A in names if A and len(A)>2]:
		for B in re.finditer(re.escape(E),A,re.I):
			F=A[B.end():B.end()+260];C=DEFINED.search(F)
			if C:D=C.group(1).strip();return _key(D),D
	return None,None
def side_problem(core,text,names,lang='he'):
	E=TXT['en'if str(lang)[:2]=='en'else'he'];C=_s(core.get('company_role_code'))or next((_s(A.get('company_role_code'))for A in core.get('contract_families')or[]if isinstance(A,dict)),'');A=side_of_role(C);B,F=side_in_document(text,names);D=lambda v:bool(re.search('[\u0590-\u05ff]',v or''))
	if A and B and A!=B and D(A)==D(B)and'mutual'not in(A,B):return E['side']%('"%s"'%C,F)
def validity_lines(core,lang='he'):
	A=core
	try:from playbook.validity import playbook_warnings as C;return[_s(A)for A in C(core=A,lang=lang)if _s(A)]
	except Exception:
		B=A.get('validity')if isinstance(A,dict)else None
		if isinstance(B,dict)and _s(B.get('status')).lower()=='invalid':return[TXT['en'if str(lang)[:2]=='en'else'he']['invalid']]
		return[]
def problems(core,counterparty_kind=None,lang='he'):
	D=counterparty_kind;C=lang;B=core;A=None
	try:
		from playbook.check_core import core_problems as F;E=F(B,counterparty_kind=D,lang=C)
		if isinstance(E,list):A=[(A[0],A[1])if isinstance(A,(list,tuple))else('warn',_s(A))for A in E]
	except Exception:A=None
	if A is None:A=local_problems(B,D,C)
	G={A for(B,A)in A};A+=[('warn',A)for A in validity_lines(B,C)if A not in G];return A
def main():
	B=argparse.ArgumentParser(description='בדיקה קצרה של playbook-core.json לפני שמנסחים או מכינים שיחה לפיו');B.add_argument('--core',required=True,help='playbook-core.json');B.add_argument('--counterparty-kind',help='סוג הצד שכנגד בעסקה (למשל גוף ציבורי, חברה זרה)');B.add_argument('--lang',choices=('he','en'),default='he');B.add_argument('--document',help='ההסכם שעל השולחן (Word, PDF או טקסט): בדיקת הצד שלנו מול הצדדים במסמך');B.add_argument('--profile',help='פרופיל-לקוח.json: שם החברה (בעברית ובאנגלית) לאיתור שלה בבלוק הצדדים');A=B.parse_args()
	try:I=json.load(io.open(A.core,encoding='utf-8-sig'))
	except(OSError,ValueError)as K:print(('The playbook could not be read (%s).'if A.lang=='en'else'לא הצלחנו לקרוא את הפלייבוק (%s).')%type(K).__name__);sys.exit(2)
	D=problems(I,A.counterparty_kind,A.lang);C=None
	if A.document:
		E=[]
		if A.profile:
			try:F=json.load(io.open(A.profile,encoding='utf-8-sig'));E=[F.get('organization_name'),F.get('organization_name_en')]+list(F.get('organization_aliases')or[])
			except(OSError,ValueError):E=[]
		J=doc_text(A.document)
		if not J.strip():print(('The document could not be read: %s'if A.lang=='en'else'לא הצלחנו לקרוא את המסמך: %s')%os.path.basename(A.document));sys.exit(2)
		C=side_problem(I,J,[str(A)for A in E if A],A.lang)
		if C:D.insert(0,('side',C))
	G=TXT[A.lang];H=[B for(A,B)in D if A in('warn','side')];print((G['one']if len(H)==1 else G['head']%len(H))if H else G['ok'])
	for(M,L)in D:print('  '+L)
	sys.exit(3 if C else 0)
if __name__=='__main__':main()
