#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (c) Areo. All rights reserved. Licensed under the terms at https://areo.co.il/legal/terms
'בונה את Areo Workspace | סיכונים (או את דוח חקר הישות) בתיקיית העסקה, בלי לקרוא את התבנית להקשר.'
import argparse,copy,io,json,os,re,sys,tempfile,urllib.parse
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
import areo_lib
from common.cli import OutputRefused,guard_out
from common.branding import apply_theme
from common.paths import PathTooLong,long_path
from risk import build as B
from risk import logo as LG
from risk import render_check as RC
from risk.render_check import build_report
from risk import validate_register as VR
import risk_states as RS
LONG_DASHES='—','–'
ASSETS=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),'assets')
DEFAULT_TEMPLATES={'risk':os.path.join(ASSETS,'risk-report-template.html'),'entity':os.path.join(ASSETS,'entity-report-template.html')}
def load(path,what):
	A=path
	if not os.path.exists(long_path(A)):print('%s אינו קיים: %s'%(what,A));raise SystemExit(2)
	try:
		with io.open(long_path(A),encoding='utf-8')as B:return json.load(B)
	except ValueError as C:print('%s אינו JSON תקין (%s)'%(what,C));raise SystemExit(2)
def short_dashes(o):
	if isinstance(o,str):return o.replace('—',', ').replace('–','-')
	if isinstance(o,list):return[short_dashes(A)for A in o]
	if isinstance(o,dict):return{A:short_dashes(B)for(A,B)in o.items()}
	return o
def derive_urls(data):
	C=data.setdefault('meta',{});B=C.get('docAccess')or{'mode':'local'};C['docAccess']=B
	if B.get('mode')!='base'or not B.get('baseUrl'):return 0
	F=B['baseUrl'].rstrip('/');D=0
	for A in data.get('documents',[])or[]:
		E=A.get('file')
		if not E or A.get('webUrl')or A.get('urlSource')=='none':continue
		A['webUrl']=F+'/'+urllib.parse.quote(E);A['urlSource']='derived';D+=1
	return D
def inside(path,folder):B=path;A=folder;B,A=os.path.realpath(B),os.path.realpath(A);return os.path.commonpath([B,A])==A
def to_artifact(html,lang='he'):
	A=html;B=re.search('<title>.*?</title>',A,re.S);C=re.search('<body[^>]*>(.*)</body>',A,re.S)
	if not(B and C):raise ValueError('מבנה התבנית אינו כצפוי, לא ניתן להפיק תוכן ל-Artifact')
	D=re.findall('<style>.*?</style>|<script>.*?</script>',A[:A.index('<body')],re.S);E,F=('ltr','en')if lang=='en'else('rtl','he');return B.group(0)+'\n'+'\n'.join(D)+'\n<script>document.documentElement.setAttribute("dir","%s");document.documentElement.setAttribute("lang","%s");</script>\n'%(E,F)+C.group(1).strip()+'\n'
def apply_lang(data,lang_arg,profile_path):
	B=profile_path;C=load(B,'הפרופיל')if B else{};D=data.setdefault('meta',{});A=C.get('deliverable_language')
	if str(A or'').strip().lower()=='both':A=C.get('display_language')
	E=lang_arg or A or D.get('display_language')or'he';F='en'if str(E).strip().lower()[:2]=='en'or str(E).strip().lower()in('english','אנגלית')else'he';D['display_language']=F;return F
def derive_fields(data,profile_path,lang):
	C=profile_path;B=data
	for A in B.get('risks')or[]:
		if not A.get('severity_level'):
			D,G=A.get('residual')or{},A.get('inherent')or{};E=D.get('score')if D.get('score')is not None else G.get('score')
			if E is not None:A['severity_level']=VR.lvl(E)
	RS.derive_levels(B)
	if lang=='en'and C:
		F=(load(C,'הפרופיל').get('organization_name_en')or'').strip()
		if F:B.setdefault('meta',{})['company']=F
def clean_counsel(data,profile_path):
	B=profile_path;A=data.setdefault('meta',{})
	if not A.get('prepared_for_counsel'):return
	C=(load(B,'הפרופיל').get('branding')or{}).get('lawyer_role')if B else None;A['prepared_for_counsel']=RC.counsel_name(A['prepared_for_counsel'],C)or None
def add_logo(data,profile_path):
	C=profile_path;D=load(C,'הפרופיל');A=(D.get('branding')or{}).get('logo_path')or D.get('logo_path')
	if not A:return'אין לוגו בפרופיל'
	if not os.path.isabs(A):B=os.path.dirname(os.path.abspath(C));E=[os.path.join(os.path.dirname(B),A),os.path.join(B,A),os.path.join(B,os.path.basename(A))];A=next((A for A in E if os.path.exists(A)),E[0])
	if not os.path.exists(A):return'הלוגו שבפרופיל אינו נמצא (%s)'%A
	try:data.setdefault('meta',{}).setdefault('branding',{})['logo']=LG.logo_data_uri(A)
	except LG.LogoError as F:return'הדוח נבנה בלי לוגו: %s'%F
	return'הלוגו הוטמע'
def page_check(a,data):
	C=data
	if a.no_page_check or not RC.find_browser():return
	D=RC.KINDS[a.kind]
	with io.open(long_path(a.template),encoding='utf-8')as E:J=E.read()
	G=tempfile.mkdtemp(prefix='areo-render-');H=os.path.join(G,B.names_for(a.kind,RC.lang_of(C))[0])
	with io.open(H,'w',encoding='utf-8')as E:E.write(build_report(J,C,D['placeholder']))
	A=None
	for L in(1,2):
		try:A=RC.run_check(H,G,RC.band_text_from_register(C),markers=RC.markers_for(a.kind,RC.lang_of(C)),body_limit=D['body_limit']);break
		except Exception as I:K='%s: %s'%(type(I).__name__,I)
	if A is None:print('  בדיקת העמודים לא הושלמה: תקלה בדפדפן (%s)'%K[:120]);return
	if A.get('verdict')=='PASS':return'עברה (%s עמודים בגוף, עד %d)'%(A.get('body_pages'),D['body_limit'])
	print('הדוח לא נכתב: בדיקת העמודים נכשלה (%s).'%', '.join(A.get('fails')or['?']))
	if A.get('body_pages'):print('  עמודים בגוף: %s, המותר: %d. קצרו את הנתונים, ולא את התבנית.'%(A['body_pages'],D['body_limit']))
	for F in('external_requests','js_exceptions','markers_missing','heading_overlaps'):
		if A.get(F):print('  %s: %s'%(F,A[F][:5]))
	return False
def main(argv=None):
	sys.dont_write_bytecode=True;sys.stdout.reconfigure(encoding='utf-8');D=argparse.ArgumentParser(description=__doc__.split('\n')[0]);D.add_argument('--data',required=True,help='risk-register.json, או entity-report.json עם --kind entity');D.add_argument('--template',help='התבנית; בלעדיו: העותק שבתוסף לפי --kind (assets/risk-report-template.html או assets/entity-report-template.html)');D.add_argument('--kind',choices=('risk','entity'),default='risk');D.add_argument('--deal',help='תיקיית העסקה; בלעדיו: התיקייה של --data');D.add_argument('--profile',help='פרופיל-לקוח.json: הלוגו ושפת התוצר (deliverable_language)');D.add_argument('--lang',choices=('he','en'),help='שפת הדוח; בלעדיו: deliverable_language בפרופיל, ואחריו meta.display_language');D.add_argument('--artifact',help='תוכן ל-Artifact פרטי בחשבון הלקוח, רק כשהמשתמש ביקש');D.add_argument('--no-page-check',action='store_true',help='לבדיקות בלבד: בלי בדיקת העמודים בדפדפן');A=D.parse_args(argv);C=load(A.data,'קובץ הנתונים');A.template=A.template or DEFAULT_TEMPLATES[A.kind]
	if not os.path.exists(long_path(A.template)):print('התבנית אינה קיימת: %s'%A.template);return 2
	F=A.deal or os.path.dirname(os.path.abspath(A.data))
	if not os.path.isdir(F):print('תיקיית העסקה אינה קיימת: %s'%F);return 2
	if inside(A.template,F):print('עותק התבנית בתוך תיקיית העסקה (%s). בלי --template נקרא העותק שבתוסף (%s), ואין לשמור תבנית בתיקיית הלקוח.'%(A.template,DEFAULT_TEMPLATES[A.kind]));return 1
	H=[];I=apply_lang(C,A.lang,A.profile)
	if A.kind=='risk':derive_fields(C,A.profile,I)
	clean_counsel(C,A.profile)
	if A.profile:
		H.append(add_logo(C,A.profile));M=apply_theme(C,load(A.profile,'הפרופיל'))
		if M:H.append(M)
	C=short_dashes(C);R=derive_urls(C)if A.kind=='risk'else 0;C.setdefault('meta',{})['publishTarget']='local';J=page_check(A,C)
	if J is False:return 3
	K=[]
	try:G,N=B.write_report(F,A.template,C,kind=A.kind,data_path=A.data,archived=K,lang=I)
	except(B.BuildError,PathTooLong,ValueError)as L:print('הדוח לא נבנה: %s'%L);return 3
	with io.open(G,encoding='utf-8')as E:S=E.read()
	if any(A in S for A in LONG_DASHES):print('מקף ארוך זלג לדוח (מהתבנית): %s. יש לתקן את התבנית.'%G);return 3
	print('הדוח: %s'%G);print('  בדיקת העמודים: %s'%(J if J else'לא הושלמה (אין Chrome או Edge, או תקלה בדפדפן)'));print('הנתונים לצדו: %s'%N)
	if K:print('  הגרסה הקודמת של הדוח והמרשם הועברה לתיקייה history של העסקה: %s'%', '.join(os.path.basename(A)for A in K))
	for T in H:print('  %s'%T)
	if A.kind=='risk':O=C.get('documents',[])or[];U=(C['meta'].get('docAccess')or{}).get('mode','local');print('  מצב גישה: %s. מסמכים עם קישור חי: %d מתוך %d. נגזרו כעת: %d'%(U,sum(1 for A in O if A.get('webUrl')),len(O),R))
	if A.artifact:
		try:P=guard_out(A.artifact,inputs=[A.data,A.template,G,N])
		except OutputRefused as L:print('תוכן ה-Artifact לא נכתב. סירוב: %s'%L);return 1
		Q=copy.deepcopy(C);Q['meta']['publishTarget']='artifact';V=B.NAMES[A.kind][2]
		with io.open(long_path(A.template),encoding='utf-8')as E:W=E.read()
		with io.open(P,'w',encoding='utf-8')as E:E.write(to_artifact(build_report(W,Q,V),I))
		print('  תוכן ל-Artifact פרטי: %s'%P)
	return 0
if __name__=='__main__':sys.exit(main())
