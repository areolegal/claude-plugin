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
IMPORTANCE={'critical':0,'high':1,'medium':2,'low':3}
REQUESTS_DIR='בקשות'
AGREEMENT_CLASSES='signed',
TEMPLATE_EXT='.docx','.dotx','.doc'
def _mdate(path):
	try:return _dt.date.fromtimestamp(Path(path).stat().st_mtime).isoformat()
	except OSError:return''
def _playbook_cores(data_dir):
	B=data_dir;B=Path(B);E,F=[],set();G=_json(B/'playbooks'/'index.json')
	for D in(G.get('playbooks')if isinstance(G,dict)else None)or[]:
		if not isinstance(D,dict):continue
		H=_s(D.get('core_path'));I=_s(D.get('family_id'))or _s(D.get('family_code'));C=B/H if H else B/'playbooks'/I/'playbook-core.json';A=_json(C)
		if isinstance(A,dict):F.add(str(C.resolve()));E.append((I or _s(A.get('family_id')),A,D))
	J=B/'playbooks'
	if J.is_dir():
		for C in sorted(J.glob('*/playbook-core.json')):
			if str(C.resolve())in F:continue
			A=_json(C)
			if isinstance(A,dict):E.append((_s(A.get('family_id'))or C.parent.name,A,{}))
	return E
def _evidence_n(c):
	A=c.get('evidence_count')
	if isinstance(A,dict):A=A.get('documents_addressing')
	try:return int(A)if A is not None and not isinstance(A,bool)else None
	except(TypeError,ValueError):return
def playbook_gaps(core):
	B=[]
	for(G,A)in enumerate((core or{}).get('clauses')or[]):
		if not isinstance(A,dict):continue
		D=_s(A.get('title'))or _s(A.get('policy_ref'))or _s(A.get('clause_issue'))
		if not D:continue
		E=A.get('green')if isinstance(A.get('green'),dict)else{};H=_s(E.get('position'))or _s(E.get('preferred_wording'))or _s(A.get('preferred_wording'));C=_evidence_n(A)
		if not H:F='none'
		elif C is not None and C<=2:F='thin'
		else:continue
		I=_s(A.get('importance')).lower();B.append({'topic':D,'reason':F,'n':C,'importance':I,'_i':G})
	B.sort(key=lambda g:(IMPORTANCE.get(g['importance'],4),g['_i']))
	for J in B:J.pop('_i',None)
	return B
def _yn_options(opts):
	D=[]
	for A in opts or[]:
		if isinstance(A,dict):B,C=_s(str(A.get('value',''))),_s(A.get('label'))or _s(str(A.get('value','')))
		else:B=C=_s(str(A))
		if B or C:D.append({'value':B or C,'label':C or B})
	return D
def _driver_item(d,items,dep):
	C=None;B=d.get('ask_when')
	if isinstance(B,dict)and B:F=next(iter(B));C={'id':_s(F),'value':_s(str(B[F]))}
	D=[]
	for(A,G)in(dep or{}).items():
		if G==d.get('id'):
			E=_s(((items or{}).get(A)or{}).get('heading'))
			if E and E not in D:D.append(E)
	A={'id':_s(d.get('id')),'question':_s(d.get('question')),'kind':_s(d.get('kind'))or'choice','options':_yn_options(d.get('options')),'help':_s(d.get('help')or d.get('note')or d.get('drafter_note')),'affects':D[:6]}
	if C:A['when']=C
	if d.get('threshold')not in(None,''):A['threshold']=d.get('threshold')
	return A
def _variance_items(vmap):
	C=[]
	for A in(vmap or{}).get('questions')or[]:
		if not isinstance(A,dict)or A.get('kind')in('driver',None):continue
		D=_s(A.get('about'))or _s(A.get('id'));E=_s(A.get('text'))
		if not D or not E:continue
		if A.get('kind')=='alternative':I,G=A.get('options')or[],A.get('option_values')or[];B=[{'value':_s(str(G[A]))if A<len(G)else _s(str(B)),'label':_s(str(B))}for(A,B)in enumerate(I)];C.append({'id':D,'question':E,'kind':'choice','options':B,'excerpts':True})
		elif A.get('kind')=='optional':C.append({'id':D,'question':E,'kind':'yes_no','options':_yn_options(A.get('options'))})
		elif A.get('kind')in('data','open'):
			H=A.get('default');B=[_s(str(A))for A in A.get('options')or[]if _s(str(A))];F={'id':D,'question':E,'kind':'text','suggestions':B[:4]}
			if _s(str(H or'')):F['suggestion']=_s(str(H))
			elif B:F['suggestion']=B[0]
			C.append(F)
	return C
def _models(data_dir,role_names):
	H=Path(data_dir)/TEMPLATES_DIR;C=[]
	if not H.is_dir():return C
	for D in sorted(A for A in H.iterdir()if A.is_dir()):
		E=_json(D/'variance-map.json')
		for J in sorted(D.glob('drivers*.json')):
			A=_json(J)
			if not isinstance(A,dict)or not _s(A.get('schema')).startswith('drivers/'):continue
			K,L=A.get('items')or{},A.get('dependent_on')or{};F=[_driver_item(A,K,L)for A in A.get('drivers')or[]if isinstance(A,dict)and A.get('id')];F=[A for A in F if A['question']];B=_s(A.get('role'));I=_variance_items(E)if isinstance(E,dict)and _s(str(E.get('role')or B))==B else[];G=A.get('open_question')if isinstance(A.get('open_question'),dict)else None
			if G and _s(G.get('question')):I.append({'id':'open_question','question':_s(G['question']),'kind':'text'})
			M=A.get('approved')if isinstance(A.get('approved'),dict)else{};N=A.get('built_from')if isinstance(A.get('built_from'),dict)else{};C.append({'family':_s(A.get('family'))or D.name,'role':B,'side':role_names.get(B,B),'set':[os.path.basename(_s(A))for A in N.get('template_set')or[]if _s(A)],'approved':bool(M.get('at')),'questions':F,'data':I})
	return C
def _requests(data_dir):
	C=Path(data_dir)/REQUESTS_DIR;B=[]
	if not C.is_dir():return B
	for D in sorted(C.glob('*.json')):
		A=_json(D)
		if not isinstance(A,dict)or A.get('kind')!='draft_new':continue
		A={A:B for(A,B)in A.items()if A not in('request_text','about')};A['id']=_s(A.get('id'))or'f-'+D.stem;A['from_file']=True;B.append(A)
	return B[-20:]
def drafter_data(data_dir):
	E=data_dir;E=Path(E);O,I,S=[],{},[]
	def K(name,aliases=()):
		A=name;A=_s(A)
		if not A:return
		C=_uniq([A]+[_s(A)for A in aliases if _s(A)]);D={A.lower()for A in C}
		for B in O:
			if D&{A.lower()for A in[B['name']]+B['aliases']}:B['aliases']=_uniq(B['aliases']+[A for A in C if A!=B['name']]);return
		O.append({'name':A,'aliases':[B for B in C if B!=A]})
	for(T,D,P)in _playbook_cores(E):
		F=(D.get('contract_families')or[{}])[0]if isinstance(D.get('contract_families'),list)else{};F=F if isinstance(F,dict)else{};U=_s(F.get('contract_family_name'))or _s(D.get('family_name'))or T;V=_strs(F.get('family_aliases'))or _strs(P.get('family_aliases'));A=_s(F.get('company_role_code'))or _s(D.get('company_role_code'))or _s(P.get('company_role_code'));J=_s(F.get('company_role'))or(D.get('company_role')if isinstance(D.get('company_role'),str)else'');J=_s(J)
		if A and J:I[A]=J
		K(U,V);d=playbook_gaps(D);S.append({'key':T,'family':U,'aliases':V,'role':A,'side':J or A,'status':_s(D.get('playbook_status'))or _s(P.get('playbook_status')),'gaps':d})
	L=_json(E/'template-registry.json');e=(L.get('documents')if isinstance(L,dict)else None)or[];Q,W,X={},[],set()
	def R(file,date,family,role,tset='',approved=False):
		C=family;B=role;A=file;A=os.path.basename(_s(A).replace('\\','/'))
		if not A or A.lower()in X:return
		X.add(A.lower());B=_s(B);W.append({'file':A,'date':_s(date),'family':_s(C),'role':B,'side':I.get(B,B),'set':_s(tset),'approved':bool(approved)});K(C)
	for B in e:
		if not isinstance(B,dict):continue
		Y,M=_s(B.get('doc_class')),_s(B.get('family'));A=_s(B.get('company_role'))or(_strs(B.get('company_role_candidates'))or[''])[0]
		if Y=='template'and _s(B.get('format')).lower()!='pdf'and not B.get('superseded_by'):R(B.get('file'),B.get('doc_date'),M,A,B.get('template_set'),B.get('approved_current'))
		elif Y in AGREEMENT_CLASSES and M:Z=M,A;Q[Z]=Q.get(Z,0)+1;K(M)
	a=E/TEMPLATES_DIR
	if a.is_dir():
		for C in sorted(a.iterdir(),key=lambda p:p.name):
			if C.is_dir():
				G=_json(C/'skeleton.json')
				if isinstance(G,dict)and G.get('kind','template')=='template':f=_s(G.get('source_file'))or C.name;R(f,_s(G.get('doc_date'))or _mdate(C/'skeleton.json'),G.get('family')or C.name,G.get('company_role')or G.get('role'),approved=True)
			elif C.suffix.lower()in TEMPLATE_EXT and not C.name.startswith('~$'):R(C.name,_mdate(C),'','')
	b=[]
	for H in(L.get('template_sets')if isinstance(L,dict)else None)or[]:
		if not isinstance(H,dict):continue
		N=H.get('driver')if isinstance(H.get('driver'),dict)else{};g=N.get('effects')if isinstance(N.get('effects'),dict)else{};h=[{'value':A['value'],'label':A['label'],'template':os.path.basename(_s((g.get(A['value'])or{}).get('template')))}for A in _yn_options(N.get('options'))];A=_s(H.get('role'));b.append({'id':_s(H.get('id')),'family':_s(H.get('family')),'role':A,'side':I.get(A,A),'templates':[os.path.basename(_s(A))for A in H.get('templates')or[]if _s(A)],'question':_s(N.get('question')),'options':h})
	c=_models(E,I)
	for i in c:K(i['family'])
	return{'families':O,'roles':I,'playbooks':S,'agreements':[{'family':B,'role':A,'side':I.get(A,A),'count':C}for((B,A),C)in Q.items()],'templates':W,'sets':b,'models':c,'requests':_requests(E)}
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
def plugin_version():
	try:return _s(json.loads((LIB.parent/'.claude-plugin'/'plugin.json').read_text(encoding='utf-8')).get('version'))
	except(OSError,ValueError,AttributeError):return''
def shell_data(data_dir,products=(BASE,),today=None,start=None):
	C=products;B=data_dir;B=Path(B);A=_json(B/PROFILE);A=A if isinstance(A,dict)else{};C=_uniq([_s(A).lower()for A in C if _s(A)])or[BASE]
	if BASE not in C:C.insert(0,BASE)
	E=find_templates(B);D=_s(A.get('organization_name'))or _s(A.get('organization_name_en'))
	if not D:F=(_json(B/'clm-data.json')or{}).get('meta')or{};D=_s(F.get('company'))if isinstance(F,dict)else''
	try:G=drafter_data(B)
	except Exception:G={}
	return{'company':D,'drafter':G,'lang':_lang(A),'today':_s(today)or _dt.date.today().isoformat(),'products':C,'folders':_folders(B,A,E),'templates':E,'people':_people(A),'org':_org(A),'start':_s(start)or'','built_at':_dt.datetime.now().replace(microsecond=0).isoformat(timespec='minutes'),'built_with':plugin_version()}
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
