# -*- coding: utf-8 -*-
# Copyright (c) Areo. All rights reserved. Licensed under the terms at https://areo.co.il/legal/terms
import argparse,datetime as _dt,json,os,sys
from pathlib import Path
LIB=Path(__file__).resolve().parents[1]
if str(LIB)not in sys.path:sys.path.insert(0,str(LIB))
from app import clm_view,nego_view,policy_view
MARKER='/*__AREO_SHELL__*/null'
TEMPLATE=LIB.parent/'ui'/'app'/'index.html'
PLAYBOOK_PAGE=LIB.parent/'skills'/'contract-setup-diagnostician'/'assets'/'setup-page.html'
PLAYBOOK_MARKER='/*__AREO_INIT__*/null'
PROFILE='פרופיל-לקוח.json'
TEMPLATES_DIR='תבניות'
CLM='areo-clm'
BASE='areolegal'
PAGE_LIMIT=16777216
TOTAL_LIMIT=67108864
MCP_SERVERS=[{'server':'Gmail','tools':['search_threads','get_message','send_message']},{'server':'Microsoft 365','tools':['outlook_email_search']},{'server':'host:plugin_areolegal_areolegal','tools':['open_mail_draft']}]
LANGS={'he':'עברית','עברית':'עברית','hebrew':'עברית','en':'English','english':'English','אנגלית':'English'}
def _json(path):
	try:return json.loads(Path(path).read_text(encoding='utf-8'))
	except(OSError,ValueError):return
def _s(v):return v.strip()if isinstance(v,str)else''
def _strs(v):
	if isinstance(v,str):v=[v]
	return[_s(A)for A in v or[]if _s(A)]if isinstance(v,list)else[]
def _uniq(xs):
	A=[]
	for B in xs:
		if B and B not in A:A.append(B)
	return A
def _people(profile):
	B=profile;D=B.get('branding')if isinstance(B.get('branding'),dict)else{};E,F=[],set()
	def C(name,role):
		A=name;A=_s(A)
		if A and A not in F:F.add(A);E.append({'name':A,'role':_s(role)})
	C(D.get('lawyer_name'),D.get('lawyer_role')or'עורך הדין');C(B.get('lawyer_name'),B.get('lawyer_role')or'עורך הדין')
	for A in D.get('signatories')or[]:
		if isinstance(A,dict):C(A.get('name'),A.get('role')or'מורשה חתימה')
		elif isinstance(A,str):C(A,'מורשה חתימה')
	return E
def _org(profile):
	A=profile;B=A.get('sector')
	if isinstance(B,dict):D=_strs(B.get('sectors'))or _strs(B.get('all'))or _strs(B.get('primary'))
	else:D=_strs(B)
	E=[]
	for C in A.get('regulatory_footprint_primary')or[]:
		F=_s(C.get('regulator_name'))if isinstance(C,dict)else _s(C)
		if F:E.append(F)
	G=A.get('connections')if isinstance(A.get('connections'),dict)else{};H=_s(G.get('email'));I=_s(A.get('display_language'));return{'registration':_s(A.get('registration_number')),'sectors':D,'markets':_strs(A.get('material_operating_jurisdictions')),'regulators':_uniq(E),'language':LANGS.get(I.lower(),I),'email':''if H.lower()in('','none','no','false')else H,'calendar':bool(G.get('calendar'))}
def _lang(profile):A=_s(profile.get('display_language')).lower();return'en'if A in('en','english','אנגלית')else'he'
def find_templates(data_dir):
	C=data_dir;C=Path(C);F,G=[],set()
	def D(name,typ):
		A=name;A=_s(A)
		if A and A.lower()not in G:G.add(A.lower());F.append({'name':A,'type':_s(typ)})
	H=C/TEMPLATES_DIR
	if H.is_dir():
		for A in sorted(H.iterdir(),key=lambda p:p.name):
			if A.is_dir():
				E=_json(A/'skeleton.json')
				if isinstance(E,dict):D(E.get('source_file')or A.name,E.get('family')or A.name)
				elif(A/'master.docx').is_file():D(A.name,A.name)
			elif A.suffix.lower()in('.docx','.dotx')and not A.name.startswith('~$'):D(A.name,'')
	I=_json(C/'template-registry.json')
	for B in(I.get('documents')if isinstance(I,dict)else None)or[]:
		if isinstance(B,dict)and B.get('approved_current')and _s(B.get('doc_class'))in('template',''):D(os.path.basename(_s(B.get('file')).replace('\\','/')),B.get('family'))
	return F
def _folders(data_dir,profile,templates):
	G=templates;F=profile;A=data_dir;A=Path(A);B,C=[],{}
	if(A/'clm-data.json').is_file():
		try:D=clm_view.page_data(A)
		except Exception:D={}
		for M in(D.get('meta')or{}).get('folders')or[]:C.setdefault(M,0)
		for H in D.get('agreements')or[]:
			if H.get('parent'):continue
			I=_s(((H.get('docs')or[{}])[0]or{}).get('path')).replace('\\','/');E=I.split('/')[0]if'/'in I else''
			if E:C[E]=C.get(E,0)+1
	N=F.get('connections')if isinstance(F.get('connections'),dict)else{}
	for J in _strs(N.get('folders')):
		K=os.path.basename(J.replace('\\','/').rstrip('/'))or J
		if K not in C:B.append({'name':K,'kind':'agreements','count':None})
	B=[{'name':A,'kind':'agreements','count':B}for(A,B)in C.items()]+B
	if G or(A/TEMPLATES_DIR).is_dir():B.append({'name':TEMPLATES_DIR,'kind':'templates','count':len(G)})
	L=A/'transactions';O=sum(1 for A in L.iterdir()if A.is_dir())if L.is_dir()else 0;B.append({'name':A.name,'kind':'workspace','count':O});return B
def shell_data(data_dir,products=(BASE,),today=None,start=None):
	C=products;B=data_dir;B=Path(B);A=_json(B/PROFILE);A=A if isinstance(A,dict)else{};C=_uniq([_s(A).lower()for A in C if _s(A)])or[BASE]
	if BASE not in C:C.insert(0,BASE)
	E=find_templates(B);D=_s(A.get('organization_name'))or _s(A.get('organization_name_en'))
	if not D:F=(_json(B/'clm-data.json')or{}).get('meta')or{};D=_s(F.get('company'))if isinstance(F,dict)else''
	return{'company':D,'lang':_lang(A),'today':_s(today)or _dt.date.today().isoformat(),'products':C,'folders':_folders(B,A,E),'templates':E,'people':_people(A),'org':_org(A),'start':_s(start)or'','built_at':_dt.datetime.now().replace(microsecond=0).isoformat(timespec='minutes')}
def inject(html,data):
	A=json.dumps(data,ensure_ascii=False,separators=(',',':'));A=A.replace('</','<\\/').replace('<!--','<\\!--').replace('\u2028','\\u2028').replace('\u2029','\\u2029')
	if html.count(MARKER)!=1:raise ValueError('התבנית אינה מכילה את הסמן %s פעם אחת בדיוק'%MARKER)
	return html.replace(MARKER,A)
def capabilities(has_clm=True,with_mail=False):
	A={'db':{},'sample':{},'downloads':True,'room':{}}
	if with_mail:A['mcp']={'servers':[dict(A)for A in MCP_SERVERS]}
	return A
def _write(path,text):A=path;A=Path(A);A.parent.mkdir(parents=True,exist_ok=True);B=A.with_name(A.name+'.tmp');B.write_text(text,encoding='utf-8');os.replace(str(B),str(A))
def features():
	try:A=json.loads((Path(__file__).resolve().parents[1]/'config.json').read_text(encoding='utf-8'))
	except(OSError,ValueError):A={}
	B=A.get('features')if isinstance(A.get('features'),dict)else{};return{'playbook_market_research':bool(B.get('playbook_market_research',False))}
def render_playbook(company,out,mode='playbook',has_clm=False):
	B=company;C=PLAYBOOK_PAGE.read_text(encoding='utf-8')
	if C.count(PLAYBOOK_MARKER)!=1:raise ValueError('בעמוד ההקמה אין את הסמן %s פעם אחת בדיוק'%PLAYBOOK_MARKER)
	A={'mode':mode,'embedded':True,'run':_dt.datetime.now().strftime('%Y%m%d%H%M%S')}
	if B:A['org_name']=B
	A['has_profile']=bool(B);A['has_clm']=bool(has_clm);A['features']=features();D=json.dumps(A,ensure_ascii=False).replace('</','<\\/');E='<!doctype html><html lang="he" dir="rtl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head><body>';_write(out,E+C.replace(PLAYBOOK_MARKER,D)+'</body></html>')
DEFAULT_TITLE='Areo'
def page_title(title=None):A=' '.join(str(title or'').replace('<','').replace('>','').replace('&','ו').split())[:80];return A or DEFAULT_TITLE
def build(data_dir,out_dir,products=(BASE,),today=None,template=None,start=None,title=None):
	M=title;L=template;E=out_dir;B=data_dir;B,E=Path(B),Path(E)
	if not B.is_dir():raise FileNotFoundError('אין תיקייה %s'%B)
	D=shell_data(B,products,today,start);H=CLM in D['products'];A=E/'apps';A.mkdir(parents=True,exist_ok=True);C={};policy_view.render(B,A/'policy.html');C['apps/policy.html']=str(A/'policy.html');render_playbook(D['company'],A/'playbook.html');C['apps/playbook.html']=str(A/'playbook.html');render_playbook(D['company'],A/'setup.html',mode='setup',has_clm=H);C['apps/setup.html']=str(A/'setup.html');nego_view.render(B,A/'nego.html');C['apps/nego.html']=str(A/'nego.html');N=[];F=A/'clm.html'
	if H:clm_view.render(B,F);C['apps/clm.html']=str(F)
	else:
		if F.exists():F.unlink()
		N.append('apps/clm.html')
	P=Path(L)if L else TEMPLATE;I=E/'index.html';J=inject(P.read_text(encoding='utf-8'),D);J=J.replace('<title>%s</title>'%DEFAULT_TITLE,'<title>%s</title>'%page_title(M),1);_write(I,J);G={'index.html':I.stat().st_size};G.update({A:Path(B).stat().st_size for(A,B)in C.items()});K=sum(G.values());O=[A for(A,B)in G.items()if B>PAGE_LIMIT]
	if O or K>TOTAL_LIMIT:raise ValueError('האפליקציה גדולה מדי לפרסום: %s (סך הכול %d בתים)'%(', '.join(O)or'סך הכול',K))
	return{'index':str(I),'title':page_title(M),'files':C,'capabilities':capabilities(H),'remove':N,'products':D['products'],'sizes':G,'total_bytes':K}
def publish_spec(result):
	A=result;B={'file_path':A['index'],'title':A.get('title')or DEFAULT_TITLE,'files':A['files'],'capabilities':A['capabilities'],'sizes':A['sizes'],'total_bytes':A['total_bytes']}
	if A['remove']:B['remove_on_update']=A['remove']
	return B
def main(argv=None):
	B=argparse.ArgumentParser(description='אפליקציית Areo מהנתונים שב-Areo-נתונים');B.add_argument('--data-dir',required=True,help='תיקיית Areo-נתונים');B.add_argument('--out',required=True,help='תיקיית הפלט, למשל Areo-נתונים/Areo');B.add_argument('--products',default=BASE,help='המוצרים של הלקוח, מופרדים בפסיק (areolegal,areo-clm)');B.add_argument('--today',default=None,help='YYYY-MM-DD (ברירת מחדל: היום)');B.add_argument('--title',default=None,help='רק למערכת נוספת לצד מערכת משותפת: "Areo · <שם>". בלי הדגל: השם הרגיל');B.add_argument('--start',default=None,choices=['setup','playbook','draft','nego'],help='המערכת נפתחת ישר על המשימה שהלקוח ביקש: playbook בניית פלייבוק, draft הסכם חדש, nego טיוטה שקיבלו');A=B.parse_args(argv);sys.dont_write_bytecode=True
	for C in(sys.stdout,sys.stderr):
		try:C.reconfigure(encoding='utf-8',errors='replace')
		except(AttributeError,ValueError):pass
	if not Path(A.data_dir).is_dir():sys.stderr.write('התיקייה אינה קיימת: %s\n'%A.data_dir);return 2
	D=build(Path(A.data_dir),Path(A.out),[A for A in A.products.split(',')],A.today,start=A.start,title=A.title);print(json.dumps(publish_spec(D),ensure_ascii=False));return 0
if __name__=='__main__':sys.exit(main())
