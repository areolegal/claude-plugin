# -*- coding: utf-8 -*-
# Copyright (c) Areo. All rights reserved. Licensed under the terms at https://areo.co.il/legal/terms
import glob,json,os,re,zipfile
from lxml import etree
W='{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
try:from common.case_law import case_law_mentions
except ImportError:case_law_mentions=lambda text:[]
DERIVATION=re.compile('(נבנה|נבנתה|נגזר|נגזרה|מבוסס|מבוססת|על בסיס|מתוך|derived from|based on)[^.\\n]{0,260}',re.I)
MUTUAL_WORDS=re.compile('הדדי(ת)?|mutual|bilateral|reciprocal|^both$',re.I)
PERSPECTIVE=re.compile('(?:מנקודת המבט של|מבט של|בצד|פלייבוק (?:של )?)\\s*(?:ה)?([\u0590-\u05ff\\"״\']{2,20}(?: [\u0590-\u05ff\\"״\']{2,20})?)|\\b([A-Za-z][A-Za-z\\- ]{2,24}?)(?:\'s)?[\\s\\-](?:perspective|side|view|playbook)\\b|from the ([A-Za-z][A-Za-z\\- ]{2,24}?)(?:\'s)? (?:perspective|side|view)',re.I)
CLEAR_SIDES='mutual',
def _role_key(text):
	A=re.sub('[\\s_\\-]+',' ',str(text or'').strip().lower()).strip(' .,:;"\'״')
	if A.startswith('ה')and len(A)>3:A=A[1:]
	return A.replace(' ','_')
def role_code(text):
	A=text
	if not A or not str(A).strip():return
	if MUTUAL_WORDS.search(str(A)):return'mutual'
	return _role_key(A)or None
def role_side(role):A=role;return role_code(A)if A else A
def same_role(a,b):return role_side(a)==role_side(b)
def _script(key):return'he'if re.search('[\u0590-\u05ff]',key or'')else'en'
def side_status(cand_side,role):
	A,B=role_side(role),role_side(cand_side)
	if A in CLEAR_SIDES or B in CLEAR_SIDES:
		if A==B:return'same'
		if A and B:return'mutuality_mismatch'
		return'unclear'
	if A and B and A==B and A!='other':return'same'
	return'unclear'
def _norm_name(s):return re.sub('\\s+',' ',re.sub('[\\W_]+',' ',str(s or'').lower())).strip()
_NAME_STOP={'הסכם','הסכמי','חוזה','נספח','agreement','agreements','contract','the','of','and','for','a'}
def family_keys(*C):
	A=set()
	for D in C:
		B=_norm_name(D)
		if B:A.add(B)
	return A,set()
def family_match(requested,cand_names):
	C,D=requested;E,F=family_keys(*cand_names)
	if C&E:return'exact'
	if D&F:return'family'
	if not D:
		A={B for A in C for B in A.split()}-_NAME_STOP
		for G in E:
			B=set(G.split())-_NAME_STOP
			if A and B and(A<=B or B<=A):return'partial'
NOT_A_POLICY=re.compile('^\\s*(דוח|דו"ח|סקירת|סקירה|review|report)',re.I)
RENDERING=re.compile('Workspace|דשבורד|dashboard',re.I)
BUILDER_VOLUME=re.compile('כרך הנימוקים|הכרך התפעולי|כרך תפעולי')
POLICY_NAME=re.compile('מדיניות|פלייבוק|playbook|policy',re.I)
def _docx_text(path):
	try:A=etree.fromstring(zipfile.ZipFile(path).read('word/document.xml'))
	except(zipfile.BadZipFile,KeyError,etree.XMLSyntaxError):return''
	return'\n'.join(''.join(A.text or''for A in A.iter(W+'t'))for A in A.iter(W+'p'))
def read_text(path):
	A=path;B=os.path.splitext(A)[1].lower()
	if B=='.docx':return _docx_text(A)
	if B in('.md','.txt','.json','.html','.htm'):C=open(A,encoding='utf-8',errors='replace').read();return re.sub('<[^>]+>',' ',C)if B.startswith('.htm')else C
	if B=='.pdf':
		try:
			from risk.page_text import pdf_text as D
			with open(A,'rb')as E:return D(E.read())
		except Exception:return''
	if B in('.xlsx','.xlsm'):
		try:import openpyxl as F;G=F.load_workbook(A,read_only=True,data_only=True);H=[' | '.join(str(A)for A in B if A is not None)for A in G.worksheets for B in A.iter_rows(values_only=True)];return'\n'.join(A for A in H if A)
		except Exception:return''
	return''
def title_of(text):
	for A in(text or'').split(chr(10)):
		if A.strip():return _norm_name(A)[:60]or'unknown'
	return'unknown'
def family_of(text):return title_of(text)
def derivation_families(text):
	B=set()
	for C in DERIVATION.finditer(text):
		A=re.split(',|;| ו(?=[\u0590-\u05ff])|\\band\\b',C.group(0));A=[_norm_name(A)for A in A if re.search('הסכם|נספח|agreement|addendum|contract',A,re.I)]
		if len(A)>=3:B.update(A)
	return B
def side_of(text):
	A=(text or'')[:1500];B=PERSPECTIVE.search(A[:300])or PERSPECTIVE.search(A)
	if B:return role_code(next(A for A in B.groups()if A))
	return role_code('mutual')if MUTUAL_WORDS.search(A[:300])else None
def classify_document(text):A=text;B=derivation_families(A);C=re.findall('\\b(\\d{1,2})\\.(\\d{1,2})\\.(20\\d\\d)\\b',A)+[(C,B,A)for(A,B,C)in re.findall('\\b(20\\d\\d)-(\\d\\d)-(\\d\\d)\\b',A[:600])];D=max(('%s-%02d-%02d'%(C,int(B),int(A))for(A,B,C)in C),default='');E=[A for A in A.split('\n')if A.strip()][:3];return{'family':family_of(A[:3000]),'derived_from':sorted(B),'mixed_family':len(B)>=2,'cites_case_law':bool(case_law_mentions(A)),'side':side_of(A),'date':D,'not_a_policy':any(NOT_A_POLICY.search(A)for A in E)}
def _same_family(a,b):A,B=set(_norm_name(a).split())-_NAME_STOP,set(_norm_name(b).split())-_NAME_STOP;return bool(A and B and(A<=B or B<=A))
def _conditions_text(conds):
	A=conds
	if not A:return''
	if isinstance(A,str):return A
	if isinstance(A,dict):A=[A]
	B=[]
	for C in A:
		if isinstance(C,dict):B.extend(str(A)for A in C.values()if isinstance(A,(str,int,float)))
		else:B.append(str(C))
	return' '.join(B)
def _activation_share(model,counterparty_kind):
	C=counterparty_kind;A=(model or{}).get('rules',[])
	if not A:return .0
	B=0
	for E in A:
		D=_conditions_text(E.get('activation_conditions'))
		if C=='company'and re.search('יחיד|individual|sole',D):B+=1
		elif C=='individual'and re.search('תאגיד|חברה בע"מ|corporate',D):B+=1
	return B/len(A)
ENTITY_KINDS={'company':'company','corporate':'company','individual':'individual','person':'individual','public_body':'public_body','public':'public_body','government':'public_body','municipality':'public_body','university':'university','academic':'university','non_profit':'non_profit','npo':'non_profit','nonprofit':'non_profit','non-profit':'non_profit','charity':'non_profit','government_company':'government_company','foreign':'foreign','large_enterprise':'large_enterprise','large':'large_enterprise','enterprise':'large_enterprise','sme':'sme','small':'sme','consumer':'consumer','group':'group','partnership':'partnership'}
KIND_ATTRIBUTES={'foreign','large_enterprise','sme'}
KIND_PARENTS={'university':{'public_body'},'government_company':{'company','public_body'},'group':{'company'},'large_enterprise':{'company'},'sme':{'company'},'consumer':{'individual'}}
NOT_COVERED_BY_KIND={'public_body':re.compile('ציבורי|ממשלת|רשות מקומית|מוסד|public|government|authorit|institution|municipal',re.I),'university':re.compile('אוניברסיט|מוסד להשכלה|אקדמ|universit|academic|higher education',re.I),'individual':re.compile('אדם יחיד|יחידים|individual|natural person',re.I),'consumer':re.compile('צרכנ|consumer',re.I),'non_profit':re.compile('עמות|מלכ"ר|חל"צ|הקדש|ללא כוונת רווח|non-?profit|charit',re.I),'government_company':re.compile('חברה ממשלתית|government compan',re.I),'foreign':re.compile('צד זר|חברה זרה|foreign',re.I),'large_enterprise':re.compile('תאגיד גדול|large enterprise',re.I),'sme':re.compile('עסק קטן|קטן או בינוני|\\bSMEs?\\b',re.I)}
OPEN_POSITION_Q=re.compile('עמד[הת]|פער כיסוי|סגמנט|position|coverage gap|segment',re.I)
KIND_NAMES={'he':{'company':'חברות','individual':'אנשים יחידים','public_body':'גופים ציבוריים','university':'אוניברסיטאות','non_profit':'עמותות','government_company':'חברות ממשלתיות','foreign':'צדדים זרים','large_enterprise':'תאגידים גדולים','sme':'עסקים קטנים ובינוניים','consumer':'צרכנים','group':'חברות בקבוצה','partnership':'שותפויות'},'en':{'company':'companies','individual':'individuals','public_body':'public bodies','university':'universities','non_profit':'non-profits','government_company':'government companies','foreign':'foreign parties','large_enterprise':'large enterprises','sme':'SMEs','consumer':'consumers','group':'group companies','partnership':'partnerships'}}
def _entity_kinds(counterparty_kind):A=counterparty_kind;B=A if isinstance(A,(list,tuple))else str(A or'').split(',');return{ENTITY_KINDS[A.strip().lower()]for A in B if A and A.strip().lower()in ENTITY_KINDS}
def _with_parents(kinds):
	A=kinds;B=set(A)
	for C in A:B|=KIND_PARENTS.get(C,set())
	return B
def _entry_kinds(x):
	if isinstance(x,dict):A=str(x.get('kind')or'').strip().lower();B=' '.join(str(x.get(A)or'')for A in('kind','label'))
	else:A,B=str(x).strip().lower(),str(x)
	if A in ENTITY_KINDS:return{ENTITY_KINDS[A]}
	return{A for(A,C)in NOT_COVERED_BY_KIND.items()if C.search(B)}
def activation_check(core,model,counterparty_kind):
	M=counterparty_kind;F=model;G=(core or{}).get('applicability')or(F or{}).get('applicability')or{};H=_entity_kinds(M);C=[];D={ENTITY_KINDS.get(str(A).lower(),str(A).lower())for A in G.get('counterparty_kinds')or()};R=_with_parents(D);S={A for A in H if A not in KIND_ATTRIBUTES or D&KIND_ATTRIBUTES};I={A for A in S if not _with_parents({A})&R}
	if H and D and not{'any','all'}&D and I:N=lambda ks:', '.join(KIND_NAMES['he'].get(A,A)for A in sorted(ks));O=lambda ks:', '.join(KIND_NAMES['en'].get(A,A)for A in sorted(ks));C.append({'code':'counterparty_kind_not_covered','text':'הפלייבוק נבנה מול %s, והצד שכנגד מסוג %s'%(N(D),N(I)),'text_en':'the playbook was built for %s, and the counterparty is %s'%(O(D),O(I)),'recommendation':''})
	T=list(G.get('not_observed')or())+[A for A in G.get('not_covered')or()if _entry_kinds(A)];P=_with_parents(H)
	for E in T:
		B=_entry_kinds(E)&P
		if B:U=(E.get('label')if isinstance(E,dict)else'')or'לא נצפה בקורפוס';J=', '.join(KIND_NAMES['he'].get(A,A)for A in sorted(B));K=', '.join(KIND_NAMES['en'].get(A,A)for A in sorted(B));C.append({'code':'not_observed','kinds':sorted(B),'text':'%s: %s'%(J,U),'text_en':'%s: not observed in the corpus'%K,'recommendation':E.get('recommendation')or''if isinstance(E,dict)else''})
	for A in(F or{}).get('validation_queue')or(core or{}).get('validation_queue')or():
		if not isinstance(A,dict)or A.get('answered')or A.get('status')=='closed':continue
		if A.get('scope')!='playbook':continue
		Q='%s %s'%(A.get('topic')or'',A.get('question')or'')
		if not OPEN_POSITION_Q.search(Q):continue
		B={A for(A,B)in NOT_COVERED_BY_KIND.items()if B.search(Q)}&P
		if B:J=', '.join(KIND_NAMES['he'].get(A,A)for A in sorted(B));K=', '.join(KIND_NAMES['en'].get(A,A)for A in sorted(B));C.append({'code':'open_question','kinds':sorted(B),'question_id':A.get('id'),'question':A.get('question')or'','text':'בפלייבוק פתוחה שאלה על %s: %s'%(J,str(A.get('question')or A.get('topic')).rstrip('?. ')),'text_en':'an open question in the playbook about %s (%s)'%(K,A.get('id')or''),'recommendation':A.get('recommendation')or''})
	L=_activation_share(F,M)
	if L>=.5:C.append({'code':'rule_conditions','text':'תנאי ההפעלה של %d%% מהכללים אינם מתקיימים בצד שכנגד הזה'%int(round(L*100)),'text_en':'the activation conditions of %d%% of the rules are not met for this counterparty'%int(round(L*100)),'recommendation':''})
	return not C,C
def _version_tuple(v):return tuple(int(A)for A in re.findall('\\d+',str(v or'0')))
def _builder_candidate(core_path,data_dir,family,role,counterparty_kind,entry=None,legacy=False,min_skill_version=None,agreement_family_label=None):
	L=agreement_family_label;K=min_skill_version;J=counterparty_kind;G=core_path;B=entry;A=json.load(open(G,encoding='utf-8'));H=os.path.join(os.path.dirname(G),'playbook-model.json');C=json.load(open(H,encoding='utf-8'))if os.path.exists(H)else A;B=B or{};M=C.get('scope_summary')or{};N=[A for A in list(M.get('contract_families')or[])+list(A.get('contract_families')or[])if isinstance(A,dict)];O=(C.get('meta')or{}).get('build_request')or{};D=[B.get('family_name',''),str(A.get('family_name','')),O.get('family_label')or''];D+=list(B.get('family_aliases')or[])+list(O.get('family_aliases')or[])
	for P in N:D+=[P.get('contract_family_name','')]+list(P.get('family_aliases')or[])
	U=[A.get('family_code'),B.get('family_code'),A.get('family_id'),B.get('family_id'),C.get('family_code'),C.get('family_id')];E=A.get('family_code')or B.get('family_code')or family_of(' '.join(A for A in D if A))
	if E=='unknown':E=A.get('family_id')or B.get('family_id')or E
	Q=B.get('company_role_code')or A.get('company_role_code')or next((A.get('company_role_code')for A in N if A.get('company_role_code')),None)or side_of(str(M.get('company_role','')));V=B.get('language')or A.get('output_language')or C.get('output_language');F=[];R=family_match(family,[A for A in D+U if A])
	if not R:F.append('other_family')
	I=side_status(Q,role)
	if I in('opposite','mutuality_mismatch'):F.append('mutuality_mismatch'if I=='mutuality_mismatch'else'opposite_side')
	S=[A.get('kind')or A.get('label')or str(A)if isinstance(A,dict)else str(A)for A in(A.get('applicability')or{}).get('not_covered',[])if not _entry_kinds(A)]
	if L and any(L in A for A in S):F.append('not_covered')
	W=_activation_share(C,J);X,Y=activation_check(A,C,J);T=[];Z=A.get('produced_with')or{}
	if K and _version_tuple(Z.get('skill_version'))<_version_tuple(K):T.append('built_with_older_version')
	a=C.get('validation_queue',[])or A.get('validation_queue',[]);return{'path':os.path.relpath(G,data_dir),'form':'builder_json','legacy_root':legacy,'family':E,'side':Q,'language':V,'family_match':R,'side_unclear':I=='unclear','date':B.get('last_updated')or A.get('last_updated')or C.get('last_updated',''),'status':A.get('playbook_status'),'activation_ok':X,'activation_share':W,'activation_reasons':Y,'not_covered':S,'excluded_because':F,'warnings':T,'validation_queue':a,**_status_fields(C,H if C is not A else None,A,B)}
def _status_fields(model,model_path,core,entry):
	B=model
	try:from playbook import status as C;A=C.label_gap(B,model_path,core=core,index_entry=entry or None)
	except Exception:return{}
	D,E=basis_guard(core,A['label'],list(A['mismatch']or[]));return{'status_label':D,'label_mismatch':E,'stored_labels':A['stored'],'proposed_notice':proposed_notice(B)if is_proposed_status(A['playbook_status'])else None}
COMPANY_BASIS_CODES='own','mixed'
NON_COMPANY_TRACK_BASES='market_standard','areo_proposal'
def company_backed_rules(core):
	B=C=0
	for A in(core or{}).get('clauses')or(core or{}).get('rules')or[]:
		if not isinstance(A,dict):continue
		C+=1;D=A.get('traffic_light')if isinstance(A.get('traffic_light'),dict)else A;E=[(D.get(A)or{}).get('basis')if isinstance(D.get(A),dict)else None for A in('green','yellow','red')]
		if any(A and A not in NON_COMPANY_TRACK_BASES for A in E):B+=1
	return B,C
def basis_guard(core,label,mismatch):
	B=mismatch;A=label
	if not A or not core:return A,B
	try:from playbook import status as D;C,F,I=D.code_of_label(A)
	except Exception:return A,B
	if not C or not any(C.startswith(A)for A in COMPANY_BASIS_CODES):return A,B
	G,E=company_backed_rules(core)
	if E==0 or G>0:return A,B
	H=D.LABELS[F]['market'if C.startswith('mixed')else'areo'];return H,list(B)+['basis_vs_tracks:0/%d company-backed rules'%E]
NOTICE_DOCS={'he':{'signed':'ההסכמים של החברה','mostly_drafts':'מסמכים של החברה (רובם טיוטות ולא הסכמים חתומים)','company_forms':'נוסחים שהחברה מציגה לצד שכנגד (לא הסכמים חתומים)','third_party_forms':'נוסחים שאינם הסכמים חתומים של החברה','unknown':'נוסחים שאינם הסכמים חתומים של החברה'},'en':{'signed':"the company's agreements",'mostly_drafts':'company documents (most of them drafts, not signed agreements)','company_forms':'forms the company presents to its counterparties (not signed agreements)','third_party_forms':'forms that are not signed agreements of the company','unknown':'forms that are not signed agreements of the company'}}
NOTICE_TXT={'he':{'lead':'העמדות בעסקה הזו באות מטיוטת מדיניות שסוכן הפלייבוק הכין מ%s%s. ','market_only':'מחקר שוק בלבד, בלי הסכמים של החברה מהסוג הזה','performed':' וממחקר שוק','partial':' וממחקר שוק חלקי','declined':', בלי מחקר שוק (החברה בחרה שלא לשלב אותו)','none':', בלי מחקר שוק','tail':'היא מחכה לאישור שלכם. המקורות שלה מפורטים ברשימת המקורות: %s.','where':'<המיקום>'},'en':{'lead':'The positions in this deal come from a draft policy that the playbook agent prepared from %s%s. ','market_only':'market research only, without company agreements of this type','performed':' and market research','partial':' and partial market research','declined':', without market research (the company chose not to include it)','none':', without market research','tail':'It awaits your approval. Its sources are listed in the source list: %s.','where':'<location>'}}
def research_state(model):
	C=model;from playbook import status as D;B=C.get('market_research')or{};A=str(B.get('status')or'')
	if A in('Performed','Completed'):return'performed'
	if A=='Partial':return'partial'
	if not A and D.uses_market(C):return'performed'
	if A=='Declined'or'declin'in str(B.get('not_performed_reason')or'')or any(isinstance(A,dict)and A.get('answer')=='no'for A in B.get('asks')or()):return'declined'
	return'none'
def proposed_notice(model,location=None):
	D=location;C=model;from playbook import status as E;F,G=E.corpus_status(C),research_state(C);H=E.base_code(C)=='market';I={'corpus_status':F,'research':'market_only'if H else G}
	for B in('he','en'):
		A=NOTICE_TXT[B]
		if H:J,K=A['market_only'],''
		else:J,K=NOTICE_DOCS[B].get(F)or NOTICE_DOCS[B]['signed'],A[G]
		L=A['tail']%D if D else A['tail'].split(':')[0]+'.';I[B]=A['lead']%(J,K)+L
	return I
CLIENT_DOC_EXT='.docx','.md','.txt','.html','.htm','.pdf','.xlsx','.xlsm'
TOOL_READ='scripts/read_playbook_doc.py'
def _client_documents(folder,uploaded):
	B=uploaded;A,D=[],set()
	for(F,E,G)in os.walk(folder):
		E[:]=[A for A in E if A!='Areo-נתונים'and not A.startswith('.')]
		for C in G:
			if POLICY_NAME.search(C)and os.path.splitext(C)[1].lower()in CLIENT_DOC_EXT:A.append(os.path.join(F,C));D.add(os.path.normcase(os.path.abspath(A[-1])))
	if B and os.path.normcase(os.path.abspath(B))not in D:A.append(B)
	return A
def _describe(c):return'%s (משפחה %s, צד %s%s)'%(c['path'],c.get('family')or'לא ידועה',c.get('side')or'לא ידוע',', עדכון %s'%c['date']if c.get('date')else'')
def resolve(data_dir,folder,family,role,agreement_language,counterparty_kind='company',uploaded=None,min_skill_version=None,agreement_family_label=None):
	e=min_skill_version;d=folder;Y=uploaded;X=counterparty_kind;W=agreement_language;V=family;O=agreement_family_label;N=role;J=data_dir;H=family_keys(V)
	if not H[1]and O:H=H[0],family_keys(O)[1]
	F,Z=[],set();f=os.path.join(J,'playbooks','index.json')
	if os.path.exists(f):
		for P in json.load(open(f,encoding='utf-8')).get('playbooks',[]):
			K=P.get('core_path')or P.get('path')
			if not K:continue
			D=os.path.join(J,K)
			if os.path.isdir(D):D=os.path.join(D,'playbook-core.json')
			if os.path.exists(D):Z.add(os.path.normcase(os.path.abspath(D)));F.append(_builder_candidate(D,J,H,N,X,P,bool(P.get('legacy')),e,O))
	for D in glob.glob(os.path.join(J,'playbooks','*','playbook-core.json'))+[os.path.join(J,'playbook-core.json')]:
		g=os.path.normcase(os.path.abspath(D))
		if g in Z or not os.path.exists(D):continue
		Z.add(g);F.append(_builder_candidate(D,J,H,N,X,legacy=True,min_skill_version=e,agreement_family_label=O))
	Q=[]
	for G in _client_documents(d,Y):
		M=read_text(G);p=os.path.splitext(G)[1].lower();K=os.path.basename(G)if G==Y else os.path.relpath(G,d)
		if not M.strip():
			if p not in('.pdf','.xlsx','.xlsm','.docx')and G!=Y:continue
			q=_norm_name(os.path.splitext(os.path.basename(G))[0]);E={'path':K,'form':'client_document','family':'unknown','side':None,'language':None,'date':'','unread':True,'read_with':TOOL_READ,'family_hint':q,'activation_ok':True,'excluded_because':[],'warnings':['unread_client_document'],'validation_queue':[]};F.append(E);continue
		A=classify_document(M);E={'path':K,'form':'client_document','family':A['family'],'side':A['side'],'language':'he'if re.search('[\u0590-\u05ff]',M)else'en','date':A['date'],'mixed_family':A['mixed_family'],'derived_from':A['derived_from'],'activation_ok':True,'cites_case_law':A['cites_case_law'],'read_with':TOOL_READ,'excluded_because':[],'warnings':[],'validation_queue':[]};r={B['date']for B in F if B['form']=='builder_json'and _same_family(B['family'],A['family'])}
		if RENDERING.search(os.path.basename(G))or BUILDER_VOLUME.search(M[:1500])or A['date']and A['date']in r:E['excluded_because'].append('rendering_only')
		elif A['not_a_policy']or NOT_A_POLICY.search(os.path.basename(G)):E['excluded_because'].append('not_a_policy')
		elif A['mixed_family']or A['cites_case_law']:L='mixed_family_background'if A['mixed_family']else'case_law_background';E['excluded_because'].append(L);Q.append({'path':K,'reason':L,'date':A['date'],'derived_from':A['derived_from'],'cites_case_law':A['cites_case_law']})
		a=None
		if any(len(A)>=4 and A in _norm_name(M[:1500])for A in H[0]):a='partial'
		E['family_match']=a
		if not a:E['excluded_because'].append('other_family')
		b=side_status(A['side'],N)
		if b in('opposite','mutuality_mismatch'):E['excluded_because'].append('mutuality_mismatch'if b=='mutuality_mismatch'else'opposite_side')
		E['side_unclear']=b=='unclear';F.append(E)
	h=[A for A in F if not A['excluded_because']];C=[A for A in h if A.get('family_match')in('exact','family')and not A.get('side_unclear')and not A.get('unread')];I=[A for A in h if A not in C];i={_norm_name(A['family'])for A in C if A['form']=='builder_json'and A.get('family_match')=='exact'}
	if i:
		for A in C:
			if A['form']=='builder_json'and _norm_name(A['family'])not in i:A['excluded_because'].append('other_family')
		C=[A for A in C if not A['excluded_because']]
	j=lambda c:(c['activation_ok'],c['language']==W,c['date']or'');C.sort(key=j,reverse=True);I.sort(key=j,reverse=True);s={_norm_name(A['family'])for A in C if A['form']=='builder_json'};B,R,S=None,[],''
	if len(s)>=2:R=C;S='נמצאו כמה פלייבוקים שמתאימים ל"%s" ולצד הזה: %s. איזה מהם חל על ההסכם? המלצה: %s.'%(V,'; '.join(_describe(A)for A in C),C[0]['path'])
	elif C:
		B=C[0]
		for A in C[1:]:
			if not A['activation_ok']and B['activation_ok']:A['excluded_because'].append('activation_mismatch')
			elif A['language']!=W:A['excluded_because'].append('other_language')
			else:A['excluded_because'].append('older')
		for A in I:A['excluded_because'].append('unread'if A.get('unread')else'side_unclear'if A.get('side_unclear')else'family_uncertain')
	elif I:
		R=I;T=[];k=[A for A in I if A.get('unread')];l=[A for A in I if not A.get('unread')and A.get('side_unclear')];m=[A for A in I if not A.get('unread')and not A.get('side_unclear')]
		if l:T.append('הצד של החברה בהסכם ("%s"), או הצד שהפלייבוק נכתב בשבילו, אינו מזוהה, ולכן אין התאמה אוטומטית: %s. מה הצד של החברה בהסכם הזה, והאם הפלייבוק נכתב לאותו צד?'%(N,'; '.join(_describe(A)for A in l)))
		if m:T.append('ההתאמה בין "%s" לבין שם הפלייבוק אינה ודאית: %s. האם זה אותו סוג הסכם?'%(V,'; '.join(_describe(A)for A in m)))
		if k:T.append('המסמך %s לא נקרא (למשל PDF סרוק, או Excel בלי openpyxl). קראו אותו ב-%s, וקבעו את המשפחה והצד שלו.'%(', '.join(A['path']for A in k),TOOL_READ))
		S=' '.join(T)
	n=[]
	for A in F:
		A['chosen']=A is B;o=A.pop('validation_queue',[])
		if A is B:continue
		A['open_items_on_rejection']=[A.get('id')for A in o]
		for U in o:
			if re.search('חוק|דין|תקנות|\\blaw\\b',json.dumps(U,ensure_ascii=False)):n.append({'from':A['path'],'id':U.get('id'),'question':U.get('question'),'rule_id':U.get('rule_id')})
	t=sorted({B for A in F for B in A.get('warnings',[])})
	if B:c='match';L='נבחר לפי משפחה, צד, תחולה, שפה ותאריך: %s'%B['path']
	elif R:c='choose';L='לבחירה: '+S
	else:c='no_match';L='אין פלייבוק להסכם הזה ולצד הזה. '+('מסמכי מדיניות כלליים של הלקוחה משמשים רקע בלבד: %s'%', '.join(A['path']for A in Q)if Q else'אין מסמך רקע.')
	return{'result':c,'chosen':B['path']if B else'','reason':L,'activation_question':bool(B and not B['activation_ok']),'activation_ok':bool(B['activation_ok'])if B else None,'activation_reason':'; '.join(A['text']for A in B.get('activation_reasons')or())if B else'','activation_reasons':list(B.get('activation_reasons')or())if B else[],'counterparty_kind':X,'playbook_status':B.get('status')if B else None,'status_label':B.get('status_label')if B else None,'label_mismatch':B.get('label_mismatch')or[]if B else[],'proposed_notice':B.get('proposed_notice')if B else None,'choices':[A['path']for A in R],'question':S,'requested_family':{'names':sorted(H[0]),'families':sorted(H[1])},'agreement_language':W,'candidates':F,'background_documents':Q,'law_items_carried':n,'warnings':t}
PROPOSED_STATUSES='draft','inferred','proposed','provisional','suggested','partiallyapproved'
APPROVED_STATUSES='approved','approved_modified'
APPROVED_LABEL_PREFIXES='מדיניות מאושרת','approved policy'
PAPER_TENDER=re.compile("מכרז(?: פומבי| סגור)? (?:מס'|מס׳|מספר)|הזמנה להציע הצעות|ועדת (?:ה)?מכרזים|(?<![א-ת])ה?מציע(?:ים)?(?![א-ת])|שאלות (?:ה)?הבהרה|מועד אחרון להגשת|הגשת (?:ה)?הצעות|עורך המכרז|מסמכי המכרז|invitation to tender|\\bITT\\b|request for (?:proposals?|quotations?|tenders?)|\\bRF[PQ]\\b|\\btenderers?\\b|\\bbidders?\\b|clarification (?:questions|requests)|deadline for (?:the )?(?:receipt|submission) of (?:tenders|bids|proposals)|contracting authority|procurement procedure|tender documents",re.I)
PAPER_AWARD=re.compile('זכ(?:ה|תה|ו) במכרז|הזוכה במכרז|הצע(?:ת|תו|תה) (?:ה)?זוכה|הודעת (?:ה)?זכייה|זכתה ואושרה|זכה ואושר|מסמכי המכרז (?:יגברו|הם חלק|מהווים חלק)|successful (?:tenderer|bidder)|notice of award|awarded (?:the|this) (?:contract|tender)|following the award|(?:the )?tender documents (?:shall prevail|form part)',re.I)
PAPER_PUBLIC=re.compile('משרד (?:ה)?[א-ת]+|(?<![א-ת])ה?רשות (?:ה)?[א-ת]+|עיריי?ת|מועצה (?:מקומית|אזורית)|חברה ממשלתית|ministry|municipal|county council|city council|public (?:body|authority|sector)|government|federal|state agency|contracting authority',re.I)
PAPER_ONLINE=re.compile('by clicking|click(?:ing)? (?:on )?\\W?(?:I )?(?:accept|agree)|clickwrap|click-wrap|by (?:accessing|using) the (?:service|website|platform)[^.]{0,40}you agree|בלחיצה על|בסימון התיבה|בעצם השימוש באתר',re.I)
PAPER_SIGNED=re.compile('in witness whereof|signature|signed by|duly authori[sz]ed|ולראיה באו הצדדים|חתימת|\\bby:\\s|name:\\s|title:\\s',re.I)
def detect_paper_type(paragraphs):
	C='\n'.join(A or''for A in paragraphs);A={A:sorted({A.group(0).strip()for A in B.finditer(C)})[:6]for(A,B)in(('tender',PAPER_TENDER),('award',PAPER_AWARD),('public',PAPER_PUBLIC),('online',PAPER_ONLINE))}
	if A['award']and(A['tender']or A['public']):B='tender_awarded'
	elif len(A['tender'])>=2:B='tender_pre_bid'
	elif A['online']and not A['tender']and not PAPER_SIGNED.search(C):B='standard_form_online'
	else:B='negotiable'
	D=B=='negotiable'and not any(A[B]for B in('tender','award','online'))or B=='tender_awarded'and len(A['award'])+len(A['tender'])>=2 or B=='tender_pre_bid'and len(A['tender'])>=3 or B=='standard_form_online'and len(A['online'])>=2;return{'suggested':B,'signals':A,'confident':D,'recommended':B if D else None}
_QTY_UNITS=('area','מ"ר|מ״ר|מטר(?:ים)? רבוע(?:ים)?|m2|m²|sq\\.? ?m|square met(?:re|er)s?|sq\\.? ?ft|square feet',1),('months','חודשים|חודש|months?',1),('months','שנים|שנה|years?',12),('units','יחידות|משתמשים|רישיונות|units|users|licen[cs]es|seats',1)
_QTY_RX=[(A,re.compile('(\\d[\\d,]*(?:\\.\\d+)?)\\s*(?:-|\\s)?\\s*(?:'+B+')(?![א-תA-Za-z])',re.I),C)for(A,B,C)in _QTY_UNITS]
def quantities(text):
	A=[]
	for(B,C,D)in _QTY_RX:
		for E in C.finditer(text or''):
			try:A.append((B,float(E.group(1).replace(',',''))*D))
			except ValueError:pass
	return A
def facts_mismatch(facts,paragraphs):
	E={}
	for(A,B)in quantities('\n'.join(A or''for A in paragraphs)):E.setdefault(A,set()).add(B)
	F=[]
	for C in facts or():
		G=C.get('fact')if isinstance(C,dict)else str(C)
		for(A,B)in quantities(G or''):
			D=E.get(A)
			if D and B not in D:F.append({'fact':G,'unit':A,'fact_value':B,'draft_values':sorted(D)[:6]})
	return F
def is_approved_status(status):A=str(status or'').strip();return A.lower()in APPROVED_STATUSES or A.lower().startswith(APPROVED_LABEL_PREFIXES)
def is_proposed_status(status):
	A=status
	if isinstance(A,dict):
		B=A.get('rules_by_status')or{}
		if B and any(not is_approved_status(A)for A in B):return True
		return any(is_proposed_status(A.get(B))for B in('playbook','status','code','status_label')if A.get(B))
	C=str(A or'').strip();return bool(C)and not is_approved_status(C)
LABELS={'he':{'pb':'מהמדיניות שלכם','proposed':'מטיוטת המדיניות','other':'שיקול מקצועי, בהשראת פלייבוק של סוג אחר','choose':'טרם נבחר פלייבוק: ממתין לבחירת המשתמש','background':'ממסמך מדיניות שמעמדו לא נבדק (%s), רקע בלבד','no_date':'בלי תאריך','prof':'שיקול מקצועי','activation':', שלא נבנה מול צד שכנגד מסוג זה: כל סטייה מסומנת'},'en':{'pb':'From your policy','proposed':'From the draft policy','activation':', which was not built for this type of counterparty: every deviation is flagged','other':'Professional judgment, inspired by a playbook of another type','choose':'No playbook chosen yet: awaiting your choice','background':'From a policy document whose status was not checked (%s), background only','no_date':'undated','prof':'Professional judgment'}}
def source_label(resolution,activation_answer_kind=None,lang='he',playbook_status=None):
	B=resolution;A=LABELS['en'if str(lang or'').lower()[:2]=='en'else'he']
	if B['result']=='match':
		C=next((A for A in B.get('candidates')or[]if A.get('chosen')),{});D=A['proposed']if is_proposed_status(playbook_status)or is_proposed_status(C.get('status'))or is_proposed_status(B.get('playbook_status'))else A['pb']
		if B.get('activation_question')and activation_answer_kind!='explicit':
			if C and(C.get('family_match')in(None,False,'')or C.get('side_unclear')):return A['other']
			return D+A['activation']
		return D
	if B['result']=='choose':return A['choose']
	if B['background_documents']:E=B['background_documents'][0];return A['background']%(E.get('date')or A['no_date'])
	return A['prof']
