# -*- coding: utf-8 -*-
# Copyright (c) Areo. All rights reserved. Licensed under the terms at https://areo.co.il/legal/terms
import argparse,datetime as dt,json,os,sys
sys.dont_write_bytecode=True
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from clm import assemble,build,doc_kind,fingerprint
from clm.validate import check_data
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
def _load(path,default=None):
	if not os.path.exists(path):return default
	with open(path,encoding='utf-8-sig')as A:return json.load(A)
def _dump(obj,path):
	os.makedirs(os.path.dirname(path),exist_ok=True)
	with open(path,'w',encoding='utf-8')as A:json.dump(obj,A,ensure_ascii=False,indent=1)
def cmd_scan(a):
	E=os.path.join(a.data_dir,'ingest');K=_load(os.path.join(E,'state.json'),{});C={};B=fingerprint.scan(a.folders,previous=K,excluded=tuple(a.exclude or()),work_dir=E,report=C)
	if C['missing']:
		for L in C['missing']:print('לא נמצא: %s. בדקו את הנתיב (תיקייה או קובץ), וחברו אותו שוב'%L)
		print('הסריקה לא נשמרה, כי נתיב אחד או יותר לא נמצא.');return 2
	for A in B:
		if A['status']=='unsupported':A['suggested_kind'],A['reasons']=None,['סוג קובץ שאינו נקרא; נפתח פריט באימות הנתונים'];continue
		M=doc_kind.docx_signals(A['abs'])if A['abs']and A['abs'].lower().endswith('.docx')else{};A['suggested_kind'],A['reasons']=doc_kind.suggest(A['path'],M)
		if A.get('attachments'):A['suggested_kind'],A['reasons']='non_agreement',['מייל: ההסכם בקבצים המצורפים, שנסרקו כרשומות נפרדות']
		if A.get('scanned'):A['reasons'].append('PDF סרוק בלי שכבת טקסט; '+('זיהוי טקסט ב-text_path'if A.get('ocr')=='done'else'אין זיהוי טקסט: לקרוא מתמונות העמודים'))
	_dump({'generated_at':dt.datetime.now().isoformat(timespec='minutes'),'folders':a.folders,'files':B,'skipped':{'system':C['system'],'data_dirs':C['data_dirs']}},os.path.join(E,'scan.json'));N={'new':'חדשים','changed':'השתנו','same':'ללא שינוי','duplicate':'כפולים','removed':'הוסרו','unreadable':'נעולים','unsupported':'בסוג שאינו נקרא'};F={}
	for A in B:F[A['status']]=F.get(A['status'],0)+1
	if not B:print('לא נמצאו קבצים בנתיבים: %s'%', '.join(a.folders))
	else:print('נסרקו %d קבצים: %s'%(len(B),', '.join('%s %d'%(N.get(A,A),B)for(A,B)in sorted(F.items()))))
	print('לחילוץ: %d'%sum(1 for A in B if A['status']in('new','changed')));H=[A['path']for A in B if A['status']=='unreadable']
	if H:print('לא נקראו (נעולים או לא זמינים), החילוץ הקודם נשמר: %s'%', '.join(H))
	I=[A['path']for A in B if A['status']=='unsupported']
	if I:print('לא נקראו, סוג קובץ שאינו נתמך (פריט באימות הנתונים): %s'%', '.join(I))
	for A in B:
		if A.get('attachments')is not None:print('מייל: %s, %d קבצים מצורפים נסרקו כרשומות נפרדות'%(A['path'],len(A['attachments'])))
		if A.get('reason')=='eml_unreadable':print('מייל שלא ניתן לפרק: %s. לקרוא אותו ישירות'%A['path'])
	D=fingerprint.dependencies();J=[A['path']for A in B if A.get('pdf_check')=='unavailable']
	if J:print('לא נבדק אם המסמכים האלה סרוקים, כי חסרה במחשב ספריית PDF (pip install pymupdf): %s'%', '.join(J))
	G=[A for A in B if A.get('scanned')]
	if G and not(D['tesseract']and D['pymupdf']):print('זיהוי טקסט אינו זמין: %s. המסמכים הסרוקים נקראים מתמונות העמודים.'%' ו'.join(A for(A,B)in(('חסר tesseract (התקנה: https://github.com/tesseract-ocr/tesseract, עם heb ו-eng)',D['tesseract']),('חסרה הספרייה pymupdf (pip install pymupdf)',D['pymupdf']))if not B))
	if G:print('PDF סרוק בלי שכבת טקסט: %s'%', '.join('%s (%s)'%(A['path'],'זוהה טקסט'if A.get('ocr')=='done'else'זיהוי הטקסט נכשל'if A.get('ocr')=='failed'else'אין במחשב כלי לזיהוי טקסט')for A in G))
	if C['system']:print('קובצי מערכת ונעילה שלא נסרקו: %d (%s)'%(len(C['system']),', '.join(C['system'][:5])))
	for O in C['data_dirs']:print('תיקיית הנתונים של Areo לא נסרקה: %s'%O)
	return 0
def _profiles(data_dir):
	A=os.path.abspath(data_dir)
	for C in(A,os.path.join(os.path.dirname(A),'Areo-נתונים')):
		try:B=_load(os.path.join(C,'פרופיל-לקוח.json'))
		except(ValueError,UnicodeDecodeError,OSError):continue
		if isinstance(B,dict):yield B
def _company_aliases(data_dir):
	for B in _profiles(data_dir):
		A=B.get('organization_name_en')
		if isinstance(A,str)and A.strip():return A.strip(),
	return()
COUNTRY_NAMES={'IL':('ישראל','Israel'),'GB':('בריטניה','United Kingdom'),'US':('ארצות הברית','United States'),'DE':('גרמניה','Germany'),'FR':('צרפת','France'),'NL':('הולנד','Netherlands'),'IE':('אירלנד','Ireland'),'CY':('קפריסין','Cyprus')}
def _profile_home_law(data_dir,lang):
	for B in _profiles(data_dir):
		C=str(B.get('incorporation_country')or'').strip().upper()
		if C in COUNTRY_NAMES:return COUNTRY_NAMES[C][1 if lang=='en'else 0]
		A=B.get('incorporation_country_name')
		if isinstance(A,str)and A.strip():return A.strip()
def _profile_lang(data_dir):
	for B in _profiles(data_dir):
		for C in('deliverable_language','display_language'):
			A=B.get(C)
			if isinstance(A,str)and A.strip():return A.strip()
def cmd_assemble(a):
	C=os.path.join(a.data_dir,'ingest');D=_load(os.path.join(C,'scan.json'))
	if not D:print('לא נמצאה סריקה. יש להריץ scan תחילה.');return 1
	F,M=assemble.load_extracts(os.path.join(C,'extract'));N,G=assemble.load_playbooks(a.playbooks or os.path.join(a.data_dir,'playbooks','index.json'))
	if G:print('אזהרה: '+G)
	H=os.path.join(a.data_dir,'clm-data.json');O=_company_aliases(a.data_dir);I=_load(H);J=assemble.resolve_lang(a.lang or _profile_lang(a.data_dir),I);B=assemble.assemble(D,F,a.company,dt.date.fromisoformat(a.today),previous=I,default_owner=a.default_owner,bad_extracts=M,playbooks=N,home_law=a.home_law or _profile_home_law(a.data_dir,J),home_law_source='flag'if a.home_law else'profile',company_aliases=O,lang=J,as_of=dt.datetime.now().strftime('%Y-%m-%dT%H:%M')if a.today==dt.date.today().isoformat()else None);_dump(B,H);K=os.path.join(C,'state.json');L=_load(K,{})or{};E={}
	for A in D['files']:
		if A['status']in('removed','duplicate'):continue
		if A.get('sha256')and A['sha256']in F:E[A['path']]=A['sha256']
		elif A['path']in L:E[A['path']]=L[A['path']]
	_dump(E,K);print('הסכמים %d, מועדים %d, ציטוטים %d, לאימות %d'%(len(B['agreements']),len(B['events']),len(B['footnotes']),len(B['review_queue'])));return 0
def cmd_validate(a):
	try:C=_load(a.data,{})
	except ValueError:print('קובץ הנתונים אינו JSON תקין');return 1
	A,B=check_data(C)
	for D in A:print('שגיאה: '+D)
	for E in B:print('אזהרה: '+E)
	print('%d שגיאות, %d אזהרות'%(len(A),len(B)));return 1 if A else 0
def cmd_build(a):
	try:build.build(a.data,a.template,a.out,audience=a.audience,hide_ids=a.hide_id,hide_types=a.hide_type)
	except build.AudienceError as A:print('שגיאה: %s'%A);return 1
	print('נשמר: '+a.out);return 0
def cmd_acceptance(a):
	from clm import acceptance as B
	if not os.path.exists(a.data):print('לא נמצא קובץ הנתונים: %s. יש להריץ assemble תחילה.'%a.data);return 1
	try:A=_load(a.data)
	except ValueError:print('קובץ הנתונים אינו JSON תקין');return 1
	if not isinstance(A,dict)or any(B not in A for B in('documents','agreements','events')):print('קובץ הנתונים אינו במבנה clm-data.json. יש להריץ validate');return 1
	C,D=B.report(A);print('\n'.join(D));return 0 if C else 1
def main(argv=None):
	if hasattr(sys.stdout,'reconfigure'):sys.stdout.reconfigure(encoding='utf-8')
	C=argparse.ArgumentParser(prog='clm_cli');B=C.add_subparsers(dest='cmd',required=True);A=B.add_parser('scan');A.add_argument('--folders',nargs='+',required=True);A.add_argument('--data-dir',required=True);A.add_argument('--exclude',nargs='*');A=B.add_parser('assemble');A.add_argument('--data-dir',required=True);A.add_argument('--company',required=True);A.add_argument('--today',default=dt.date.today().isoformat());A.add_argument('--default-owner',default='me');A.add_argument('--playbooks',help='אינדקס הפלייבוקים; ברירת מחדל <data-dir>/playbooks/index.json');A.add_argument('--home-law',default=None,help='הדין שנחשב דין מקומי בסיווג הדין החל; ברירת מחדל: מדינת ההתאגדות מהפרופיל, ואחריה ההרצה הקודמת');A.add_argument('--lang',choices=('he','en'),default=None,help='שפת הנתונים (meta.lang). ברירת מחדל: deliverable_language או display_language מהפרופיל, אחריהם השפה של ההרצה הקודמת, ואז he');A=B.add_parser('validate');A.add_argument('--data',required=True);A=B.add_parser('build');A.add_argument('--data',required=True);A.add_argument('--out',required=True);A.add_argument('--template',default=os.path.join(ROOT,'assets','workspace-template.html'));A.add_argument('--audience',choices=('full','restricted'),default='full',help='full: העותק המלא המקומי. restricted: עותק לקהל מצומצם, ההסכמים המוסתרים מוסרים מהנתונים לפני ההטמעה');A.add_argument('--hide-id',action='append',default=[],help='מזהה הסכם להסרה מהעותק המצומצם (אפשר כמה פעמים)');A.add_argument('--hide-type',action='append',default=[],help='קוד סוג הסכם להסרה מהעותק המצומצם (אפשר כמה פעמים)');A=B.add_parser('acceptance');A.add_argument('--data',required=True);D=C.parse_args(argv);return{'scan':cmd_scan,'assemble':cmd_assemble,'validate':cmd_validate,'build':cmd_build,'acceptance':cmd_acceptance}[D.cmd](D)
if __name__=='__main__':sys.exit(main())
