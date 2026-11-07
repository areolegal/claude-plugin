#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (c) Areo. All rights reserved. Licensed under the terms at https://areo.co.il/legal/terms
'מחקר השוק של בונה הפלייבוק, בקוד ולא בשיקול דעת: הטווח, הבדיקות, הקישורים, ההודעה והרשת.'
import argparse,datetime as _dt,io,json,os,re,sys,tempfile
from collections import Counter
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
import areo_lib
from playbook import market_counts as MC
from playbook import status as S
LEVELS=2,1,0,-1,-2
OURS_POOL='same_side','negotiated','neutral_model'
MIDDLE_POOL='negotiated','neutral_model'
THEIRS_POOL='other_side','negotiated','neutral_model'
BALANCED='negotiated','neutral_model'
NOT_READ='located_not_read','excluded','blocked'
MIN_SOURCES=3
OLD_YEARS=7
CERTAINTY={'high':'ודאות גבוהה','medium':'ודאות בינונית','low':'ודאות נמוכה','expert':'הערכת מומחה'}
NOT_MEASURED='לא נמדד: אין מקור מהצד השני'
ALL_AREO='כל עמדה בו היא הצעה של Areo'
TEMPLATE_BASIS='own_paper_repeated','template'
MARKET_BASIS='market_standard',
STOP_REASONS='client_stop','switch_component','cannot_continue','build_request'
SOURCE_TYPES='tender','public_filing','vendor_terms','model_agreement'
MODEL_UNLISTED='לא נבדק: המקור אינו ברשימת המקורות המאושרים'
NO_POSITION='AREO לא מצאה מקור מורשה לנקודה זו'
SOURCE_TYPE_NUM={'tender':1,'public_filing':2,'vendor_terms':3,'model_agreement':4}
DRAFTED_HE={'same_side':'הצד שלנו','other_side':'הצד שכנגד','negotiated':'נוהל עליו משא ומתן','neutral_model':'מודל מאוזן','unknown':'לא ידוע'}
DRAFTER_HE={'public_body':'גוף ציבורי','model_body':'גוף שמפרסם הסכם מודל','negotiated':'נוהל עליו משא ומתן','unknown':'לא ידוע','same_side':'צד באותה פוזיציה כמו החברה','other_side':'הצד שכנגד','supplier':'הספק','customer':'הלקוח'}
SOURCE_TYPE_HE={'tender':'הליך תחרותי ציבורי','public_filing':'דיווח פומבי','vendor_terms':'תנאים שצד מפרסם','model_agreement':'הסכם מודל'}
DENIED_DOMAINS='lawinsider.com','wikipedia.org','rocketlawyer.com','legalzoom.com','pandadoc.com','templatelab.com','docracy.com','lawdepot.com','jdsupra.com','lexology.com','law.com','ynet.co.il','globes.co.il','calcalist.co.il','themarker.com','reuters.com'
QUERY_LOG='query-log.jsonl'
QUERY_LOG_OLD='query-log.json'
SESSION_FILE='research-session.json'
SESSION_HOURS=6
def load(path,what):
	A=path
	if not A or not os.path.exists(A):print('%s אינו קיים: %s'%(what,A));raise SystemExit(2)
	with io.open(A,encoding='utf-8')as B:return json.load(B)
ENTITIES_FILE='ישויות.json'
def load_profile(path):
	C=load(path,'הפרופיל');A=os.path.dirname(os.path.abspath(path))
	for H in range(4):
		D=os.path.join(A,ENTITIES_FILE)
		if os.path.isfile(D):
			try:
				with io.open(D,encoding='utf-8')as F:B=json.load(F)
			except(OSError,ValueError):break
			G=B.get('entities')if isinstance(B,dict)else B;C['_entity_names']=[A.get('name')for A in G or()if isinstance(A,dict)and A.get('name')];break
		E=os.path.dirname(A)
		if E==A:break
		A=E
	return C
GENERIC_NAME_WORDS={A.casefold()for A in('limited','ltd','inc','incorporated','llc','llp','corp','corporation','company','holdings','holding','group','gmbh','plc','the','and','services','service','systems','system','solutions','technologies','technology','tech','software','international','global','industries','industry','enterprises','partners','partnership','capital','management','consulting','trading','investments','properties','property','networks','digital','data','cloud','medical','health','healthcare','energy','finance','financial','insurance','bank','media','logistics','development','foundation','association','university','college','institute','trust','fund','agency','authority','ministry','council','municipality','state','government','national','israel','israeli','europe','america','american','british','project','product','platform','programme','program','solution','agreement','party','parties','online','labs','works','pharma','biotech','foods','retail','estate','realty','telecom','communications','security','analytics','ventures','equity','advisors','associates','consultants','engineering','construction','manufacturing','supply','supplies','products','resources','operations','united','general','standard','public','private','terms','rollout','renewal','phase','deal','תקשורת','הנדסה','בנייה','אבטחה','מזון','נדלן','נדל"ן','פיתוח','ייזום','מוצרים','משאבים','בעמ','בע"מ','בע״מ','חברה','חברת','החברה','מערכות','שירותים','שירותי','אחזקות','החזקות','טכנולוגיות','תעשיות','השקעות','נכסים','ניהול','ייעוץ','פתרונות','קבוצת','קבוצה','ישראל','בינלאומי','בינלאומית','גלובל','דיגיטל','מדינת','המדינה','משרד','רשות','הרשות','עיריית','העירייה','מועצה','עמותת','עמותה','אגודת','אגודה','שותפות','קרן','אוניברסיטת','מכללת','פרויקט','הפרויקט','מוצר','המוצר','מערכת','המערכת','בין','לבין','ובין','להלן')}
LEGAL_SUFFIX_EN='(?:Ltd\\.?|Limited|Inc\\.?|Incorporated|L\\.?L\\.?C\\.?|L\\.?L\\.?P\\.?|plc|PLC|Corp\\.?|Corporation|GmbH|AG|S\\.A\\.?|SAS|S\\.p\\.A\\.?|B\\.V\\.?|N\\.V\\.?|Pty|Co\\.|Holdings)'
ENTITY_EN=re.compile("\\b((?:[A-Z][\\w&'\\-]*\\.?\\s+){0,4}[A-Z][\\w&'\\-]*),?\\s+"+LEGAL_SUFFIX_EN+'(?!\\w)')
ENTITY_HE=re.compile('((?:[א-ת][א-ת\\"״\'׳\\-]*\\s+){0,4}[א-ת][א-ת\\"״\'׳\\-]*)\\s+(?:בע[\\"״]?מ|\\(ע[\\"״]?ר\\)|\\(חל[\\"״]?צ\\)|\\(שותפות מוגבלת\\))')
PROJECT_EN=re.compile('\\b(?:Project|Programme|Program|Product|Platform)\\s+([A-Z][\\w\\-]{2,})|\\b([A-Z][\\w\\-]{2,})\\s+(?:Project|Programme|Platform)\\b')
PROJECT_HE=re.compile('(?:פרויקט|מיזם|תוכנית|מוצר|מערכת|פלטפורמת)\\s+[\\"״“]([^\\"״”]{2,30})[\\"״”]')
QUOTED_ALIAS=re.compile('[(]\\s*(?:להלן\\s*:?\\s*|hereinafter(?:\\s+(?:referred\\s+to\\s+as|called))?\\s*[:,]?\\s*)?(?:the\\s+)?[\\"״“]([^\\"״”()]{2,40})[\\"״”]\\s*[)]',re.I)
_HE_PREFIX='והבכלמש'
def _role_words():
	try:import build_corpus_manifest as A;return A._role_like,A.NOT_A_ROLE
	except Exception:return lambda _n:False,None
def distinctive_tokens(name):
	B=[]
	for A in re.findall("[^\\W\\d_][\\w'\\-]*",str(name or'')):
		A=A.strip("'-")
		if len(re.sub('\\W','',A))>=4 and A.casefold()not in GENERIC_NAME_WORDS:B.append(A)
	return B
def corpus_names(corpus=None,manifest=None,deal=None):
	F=corpus;E=manifest;A=deal;R,L=_role_words();G=[]
	def C(n):
		n=re.sub('\\s+',' ',str(n or'')).strip(' ,.;:()"\'״“”');n=re.split('(?:^|\\s)(?:ו?ל?בין|עם|between|and|by)\\s+',n,flags=re.I)[-1].strip()
		if len(n)<3 or re.search('\\d',n):return
		A=re.sub('^the ','',n.casefold())
		if R(n)or A in GENERIC_NAME_WORDS or L is not None and L.match(n):return
		if re.match('(?:חוק|תקנות|פקודת|צו)\\s|.*\\b(?:Act|Law|Regulations?|Directive)$',n,re.I):return
		G.append(n)
	S=F.get('documents')if isinstance(F,dict)else F
	for H in S or():
		if not isinstance(H,dict):continue
		T=H.get('paragraphs')or[B for A in(H.get('parts')or{}).values()for B in A];I=' '.join(A.get('text')or A.get('text_accept_all')or''for A in T if isinstance(A,dict));M=I[:3000]
		for U in(ENTITY_EN,ENTITY_HE):
			for B in U.finditer(M):C(B.group(1))
		for B in QUOTED_ALIAS.finditer(M):
			D=B.group(1).strip()
			if not re.search('\\b[A-Z]{2,8}\\b',D)and len(D.split())<=3:C(D)
		for B in PROJECT_EN.finditer(I):C(B.group(1)or B.group(2))
		for B in PROJECT_HE.finditer(I):C(B.group(1))
	N=E.get('files')or E.get('documents')or[]if isinstance(E,dict)else E
	for O in N if isinstance(N,list)else():
		for D in O.get('parties_hint')or[]if isinstance(O,dict)else():C(D)
	if isinstance(A,dict):
		J=A.get('counterparty')
		for P in(A.get('counterparty_name'),A.get('counterparty_name_en'),A.get('deal_name'),A.get('project_name'),A.get('product_name'),J.get('name')if isinstance(J,dict)else J):
			if isinstance(P,str):C(P)
		for K in A.get('parties')or():C(K.get('name')if isinstance(K,dict)else K)
		for Q in('meta','deal','deal_context'):
			if isinstance(A.get(Q),dict):G+=corpus_names(deal=A[Q])
	return list(dict.fromkeys(G))
def client_names(profile,corpus=None,manifest=None,deal=None):
	E=manifest;D=corpus;A=profile;C=[]
	if A:
		C+=[A.get('organization_name'),A.get('organization_name_en')];C+=list(A.get('_entity_names')or());I=A.get('branding')if isinstance(A.get('branding'),dict)else{};F=re.sub('^www\\.','',_host(I.get('website')or''))
		if F:C.append(F)
	if D or E or deal:C+=corpus_names(D,E,deal)
	G,H=set(),[]
	for B in C:
		B=str(B or'').strip()
		if B and B.lower()not in G:G.add(B.lower());H.append(B)
	return H
def name_tokens(names):
	B=[]
	for A in names:
		if re.fullmatch('[\\w\\-]+(\\.[\\w\\-]+)+',A):A=A.split('.')[0]
		B+=distinctive_tokens(A)
	return list(dict.fromkeys(B))
def token_in(text,tokens):
	B=' '.join(str(text or'').split())
	for A in tokens:
		C='(?:[%s]{1,2})?'%_HE_PREFIX if re.match('[א-ת]',A)else''
		if re.search('(?<!\\w)%s%s(?!\\w)'%(C,re.escape(A)),B,re.I):return A
	return''
def save(path,data):
	with io.open(path,'w',encoding='utf-8')as A:json.dump(data,A,ensure_ascii=False,indent=1)
def now_iso():return _dt.datetime.now().astimezone().isoformat(timespec='seconds')
EN_MONTHS='January','February','March','April','May','June','July','August','September','October','November','December'
def he_date(iso,lang='he'):
	try:A=_dt.date.fromisoformat(str(iso)[:10])
	except ValueError:return str(iso or'')
	if lang=='en':return'%d %s %d'%(A.day,EN_MONTHS[A.month-1],A.year)
	return'%d.%d.%d'%(A.day,A.month,A.year)
def year_of(d):A=re.match('(\\d{4})',str(d or''));return int(A.group(1))if A else None
def _host(url):return re.sub('^[a-z]+://','',url or'',flags=re.I).split('/')[0].split(':')[0].lower()
def _approved_rules(path=None):
	try:from risk.validate_register import approved_domains as A;return A(path)[0]
	except Exception:return()
def model_body_unlisted(ref):
	A=ref
	if not(A.get('source_type')in(4,'4')or A.get('drafter_role')=='model_body'or A.get('drafted_by')=='neutral_model'):return False
	B=A.get('final_url')or A.get('url')
	if not _host(B):return True
	try:from risk.validate_register import domain_ok as C
	except Exception:return True
	return not C(B,_approved_rules())
def counted_ref(ref):
	A=ref
	if not A or A.get('read_status')in NOT_READ or not A.get('doc_date'):return False
	if model_body_unlisted(A):return False
	if A.get('located_via')=='aggregator'and not A.get('verified_against_original'):return False
	return A.get('drafted_by')not in(None,'unknown')
def level_of(c,silence_rank):
	if c.get('special')=='silent'or c.get('level')=='silence':return'silence'if silence_rank is not None else None
	A=c.get('level');return A if A in LEVELS else None
def rank(level,silence_rank):A=level;return silence_rank if A=='silence'else A
def pick(sources,refs):
	B,C,D=set(),set(),[]
	for A in sorted(sources):
		E=refs[A];F=(E.get('issuing_body')or A).strip().lower();G=(E.get('template_family')or A).strip().lower()
		if F in B or G in C:continue
		B.add(F);C.add(G);D.append(A)
	return D
def topic_points(topic,coding,refs,silence_rank=None):
	B,C={},[]
	for A in coding:
		if A.get('topic')!=topic:continue
		E=refs.get(A.get('source_id'))
		if not counted_ref(E)or A.get('special')in('redacted','not_relevant'):continue
		if A.get('status')=='uncertain':C.append(A['source_id']);continue
		if A.get('status')not in('agreed','resolved'):continue
		D=level_of(A,silence_rank)
		if D is None:continue
		B.setdefault(D,[]).append(A['source_id'])
	return B,C
def point_for(by_level,refs,pool,order,silence_rank,mode=False):
	D=silence_rank;A=[]
	for(B,C)in by_level.items():
		E=pick([A for A in C if refs[A].get('drafted_by')in pool],refs)
		if len(E)>=MIN_SOURCES:A.append((B,E))
	if not A:return
	if mode:A.sort(key=lambda x:(-len(x[1]),abs(rank(x[0],D)or 0)))
	else:A.sort(key=lambda x:rank(x[0],D)*(1 if order=='max'else-1),reverse=True)
	B,C=A[0];return{'level':B,'source_ids':C}
def certainty(point,refs,question,research_year,uncertain,by_level,silence_rank):
	E=silence_rank;D=research_year;B=point
	if not B or uncertain:return CERTAINTY['expert']
	C=[refs[A]for A in B['source_ids']];A=0
	if len({A.get('source_type')for A in C})<2:A+=1
	F=(question or{}).get('jurisdiction')
	if F and any(A.get('jurisdiction')and A.get('jurisdiction')!=F for A in C):A+=1
	if D and any((year_of(A.get('doc_date'))or D)<D-OLD_YEARS for A in C):A+=1
	G=rank(B['level'],E)
	if any(A!=B['level']and abs((rank(A,E)or 0)-G)==1 for A in by_level):A+=1
	H=any(A.get('drafted_by')in BALANCED for A in C)
	if A==0 and H:return CERTAINTY['high']
	if A<=1:return CERTAINTY['medium']
	return CERTAINTY['low']
def accepted_ok(point,refs,question):
	C=question;B=point
	if not B:return False
	A=[refs[A]for A in B['source_ids']];D={(C or{}).get('agreement_type_he'),(C or{}).get('agreement_type_en')}-{None};E=all(not D or A.get('agreement_type')in D for A in A);return len(A)>=MIN_SOURCES and E and any(A.get('drafted_by')in BALANCED for A in A)
def compute_ranges(model):
	C=model.setdefault('market_research',{});A={A['source_id']:A for A in C.get('source_refs')or[]if A.get('source_id')};K=C.get('coding')or[];P=C.get('question')or{};X=year_of(C.get('research_date'));Y={A.get('topic'):A for A in C.get('coding_sheets')or[]};Q={A.get('topic'):A for A in C.get('ranges')or[]};L=[]
	for M in K:
		if M.get('topic')and M['topic']not in L:L.append(M['topic'])
	N=[]
	for I in L:
		B=(Y.get(I)or{}).get('silence_level');B=B if B in LEVELS else None;D,R=topic_points(I,K,A,B);E=point_for(D,A,OURS_POOL,'max',B);F=point_for(D,A,MIDDLE_POOL,None,B,mode=True);S=any(A[C].get('drafted_by')=='other_side'for B in D.values()for C in B);G=point_for(D,A,THEIRS_POOL if S else BALANCED,'min',B);O=None
		if not S:
			T=F or E
			if G is None or T and rank(G['level'],B)>rank(T['level'],B):G,O=None,NOT_MEASURED
		if E and F and E['level']==F['level']:U='theirs'if G and rank(G['level'],B)==rank(E['level'],B)-1 else'areo_compromise'
		else:U='middle'if F else'areo_compromise'
		J={'topic':I,'distribution':{str(A):sorted(B)for(A,B)in sorted(D.items(),key=lambda x:str(x[0]))},'uncertain':sorted(R),'yellow_from':U}
		for(V,H)in(('ours',E),('middle',F),('theirs',G)):
			if H:H=dict(H,position=V,certainty=certainty(H,A,P,X,R,D,B),accepted_ok=accepted_ok(H,A,P))
			J[V]=H
		if O:J['theirs_note']=O
		if not E and not F:J['certainty']=CERTAINTY['expert']
		if(Q.get(I)or{}).get('periods'):J['periods']=Q[I]['periods']
		N.append(J)
	C['ranges']=N;W={B['source_id']for B in K if B.get('source_id')in A and counted_ref(A[B['source_id']])};C['counts']={'found':len(A),'opened':sum(1 for A in A.values()if A.get('read_status')not in('located_not_read',)),'read':sum(1 for A in A.values()if A.get('read_status')not in NOT_READ),'counted':len({(A[B].get('template_family')or B).strip().lower()for B in W}),'excluded':sum(1 for A in A.values()if A.get('read_status')in NOT_READ),'bodies':len({(A[B].get('issuing_body')or'').strip().lower()for B in W}-{''})};return N
def iter_tracks(model):
	for A in model.get('rules')or[]:
		for B in('green','yellow','red'):
			C=(A.get('traffic_light')or{}).get(B)
			if isinstance(C,dict):yield(A,B,C)
def text_of(tl):return' '.join(str(tl.get(A)or'')for A in('source_label','rationale','note','proposed_clause','position','summary'))
def range_for(model,rule):
	A=rule;C=A.get('market_topic')or A.get('topic')or A.get('title')
	for B in(model.get('market_research')or{}).get('ranges')or[]:
		if B.get('topic')==C:return B
def uses_market(model):A=model;return any(B.get('basis')in MARKET_BASIS for(A,A,B)in iter_tracks(A))or A.get('corpus_origin')in('own_plus_market','market_built')
def docx_created(path):
	import zipfile as A
	try:
		with A.ZipFile(path)as C:D=C.read('docProps/core.xml').decode('utf-8','ignore')
	except(OSError,KeyError,A.BadZipFile):return
	B=re.search('<dcterms:(?:modified|created)[^>]*>([^<]+)<',D);return B.group(1)if B else None
def _ts(s):
	try:A=_dt.datetime.fromisoformat(str(s).replace('Z','+00:00'));return A if A.tzinfo else A.replace(tzinfo=_dt.timezone.utc)
	except ValueError:return
def check_model(model,word=None,final=False):
	C=model;B=[];E=C.get('market_research')or{}
	for(I,F,G)in iter_tracks(C):
		J='%s/%s'%(I.get('rule_id'),F);D=range_for(C,I);K=(D or{}).get(G.get('range_point')or{'green':'ours','yellow':'middle','red':'theirs'}[F])
		if'מקובל'in text_of(G)and not(K and K.get('accepted_ok')):B.append('MARKET_ACCEPTED_UNSUPPORTED %s: "מקובל" בלי נקודה של שלושה מקורות נספרים, מגופים ומתבניות שונים, מאותו סוג הסכם ועם מקור מנוהל או מאוזן'%J)
		if F=='red'and G.get('basis')in MARKET_BASIS and D and not D.get('theirs'):B.append('RED_THEIRS_NOT_MEASURED %s: אדום בבסיס שוק, ו"לטובתם" לא נמדדה (%s)'%(J,D.get('theirs_note')or'פחות משלושה מקורות'))
	for A in E.get('source_refs')or[]:
		if A.get('read_status')not in NOT_READ and model_body_unlisted(A):B.append('MODEL_BODY_NOT_LISTED %s: הסכם מודל מגוף שאינו ברשימה הסגורה (%s) אינו מקור, גם בהצהרה או באישור של הלקוח. הוצא אותו מ-source_refs ומהקידוד, ורשום אותו ב-counts.screened_out[] בסיבה "%s"'%(A.get('source_id'),_host(A.get('final_url')or A.get('url'))or'אין כתובת',MODEL_UNLISTED))
		if A.get('source_type')in(3,'3')and A.get('drafted_by')in BALANCED:B.append('VENDOR_TERMS_AS_BALANCED %s: תנאים שספק מפרסם הם העמדה של אותו ספק, ואינם נספרים לנקודת המפגש (drafted_by=%s)'%(A.get('source_id'),A.get('drafted_by')))
	if uses_market(C):
		L=E.get('disclosure')or{}
		if not(C.get('status_label')or C.get('presentation_label')):B.append('MARKET_NO_LABEL: הפלייבוק נשען על מחקר שוק, ואין תווית')
		if not L.get('chat_message'):B.append('MARKET_NO_DISCLOSURE: הפלייבוק נשען על מחקר שוק, ואין הודעת שקיפות (market_research.disclosure)')
		Q=any(A=='green'and B.get('basis')in TEMPLATE_BASIS+('documents_majority',)for(C,A,B)in iter_tracks(C))
		for H in('fixed_sentence','chat_message'):
			M=L.get(H)or''
			if Q and ALL_AREO in M:B.append('ALL_AREO_WITH_TEMPLATE: "%s" ב-%s, ויש ירוק מתבנית של החברה'%(ALL_AREO,H))
			for R in MC.count_claims(M,C):B.append('MARKET_COUNT_MISMATCH %s: %s'%(H,R))
	if word:
		N=_ts(docx_created(word))
		for A in E.get('source_refs')or[]:
			O=_ts(A.get('link_checked_at'))
			if A.get('read_status')in NOT_READ:continue
			if A.get('url')and N and(not O or O<N):B.append('LINK_CHECK_BEFORE_WORD %s: הקישור נבדק לפני שה-Word נבנה (או לא נבדק)'%A.get('source_id'))
	if final:
		P=[A.get('rule_id')for A in C.get('rules')or[]if(A.get('rationale')or{}).get('rationale_status',A.get('rationale_status'))=='Draft'];S=(C.get('qa_summary')or{}).get('pass_b_stop_reason')
		if P and S not in STOP_REASONS:B.append('PASS_B_STOP_REASON: מסירה סופית עם %d כללים שהנימוק שלהם בטיוטה, בלי pass_b_stop_reason (%s)'%(len(P),' | '.join(STOP_REASONS)))
	return B
def own_agreements(model):
	try:return S.agreements_counted(model)or 0
	except Exception:return 0
def legal_facts(model):return sum(1 for A in model.get('external_sources')or[]if str(A.get('ref','')).startswith('L')and not str(A.get('verification')or'').startswith('לא אומת'))
def fixed_sentence(model):
	A=model;G=MC.counts(A);J,K=G.get('counted',0),G.get('read',0);H=legal_facts(A);B,C=MC._families(J),MC._docs_read(K);F=', ולפי %s'%MC._legal(H)if H else'';D=A.get('corpus_origin');E=own_agreements(A);L=sum(1 for(A,A,B)in iter_tracks(A)if B.get('basis')in('market_standard','areo_proposal'));I=[A for(C,B,A)in iter_tracks(A)if B=='green'and A.get('basis')in TEMPLATE_BASIS];M=A.get('company_role_code')or(A.get('meta')or{}).get('company_role_code')or'';N=((A.get('meta')or{}).get('build_request')or{}).get('requested_by')not in(None,'','user')
	if N and E:return'זו טיוטת מדיניות, שנבנתה לפי %d הסכמים שלכם ולפי %s (%s). העמדות שמקורן בשוק הן הצעה של Areo, ועוד לא אישרתם אותן.'%(E,B,C)
	if D=='own_plus_market':return'הפלייבוק נבנה מ-%d הסכמים שלכם. בנושאים שאין עליהם ראיה בהסכמים, הוא נבנה לפי %s (%s). %d עמדות הן הצעה של Areo, ואינן מבוססות על ההסכמים שלכם.'%(E,B,C,L)
	if D=='market_built'and I:return'הירוק נלקח מ-%d התבניות שלכם. הצהוב והאדום נבנו לפי %s (%s)%s. הם הצעה של Areo, ואינם מבוססים על ההסכמים שלכם, כי אין הסכם חתום מהסוג הזה.'%(len(I),B,C,F)
	if D=='market_built'and M=='mutual':return'אין לכם הסכם הדדי מהסוג הזה, ולכן הפלייבוק נבנה כולו לפי %s (%s)%s. התבניות החד-צדדיות שלכם סווגו לפי הכותרת והפתיח בלבד, ולא שימשו מקור לעמדות. %s.'%(B.replace('הסכמים','הסכמים הדדיים',1),C,F,ALL_AREO)
	if D=='market_built':return'הפלייבוק נבנה לפי %s (%s)%s. %s, ואינה מבוססת על ההסכמים שלכם.'%(B,C,F,ALL_AREO)
	O=sum(1 for A in(A.get('market_research')or{}).get('findings')or[]if A.get('client_choice'));return'המדיניות נגזרה מ-%d ההסכמים שלכם, והושוותה ל-%s (%s). %d ממצאים שבחרתם נכנסו לפלייבוק, מסומנים כהצעה של Areo.'%(E,B,C,O)
POS_HE={'ours':'לטובתנו','middle':'באמצע','theirs':'לטובתם'}
def build_message(model):
	C=model;E=C.get('market_research')or{};K=E.get('source_refs')or[];F=E.get('counts')or{}
	try:G=S.derive_status(C)['label']
	except Exception:G=C.get('status_label')or''
	H=fixed_sentence(C);B=[G,H,'']if G else[H,''];P=((C.get('meta')or{}).get('build_request')or{}).get('requested_by')not in(None,'','user')
	if P:
		Q=C.get('handoff')or{};B+=['מה נבנה: %d כללים, %d עמדות.'%(len(C.get('rules')or[]),sum(1 for A in iter_tracks(C)))]
		for I in(Q.get('decisions_now')or[])[:3]:B.append('- %s (המלצה: %s)'%(I.get('question')or I.get('text')or'',I.get('recommendation')or''))
		B.append('')
	L={}
	for A in E.get('ranges')or[]:
		for D in('ours','middle','theirs'):
			for R in(A.get(D)or{}).get('source_ids')or():L.setdefault(R,[]).append('%s: %s'%(A['topic'],POS_HE[D]))
	B.append('המקורות שעליהם נשענות העמדות (%d מסמכים שנקראו, מ-%d גופים; נמצאו %d, נקראו %d, נספרו %d; תאריך המחקר %s):'%(F.get('read',0),F.get('bodies',0),F.get('found',0),F.get('read',0),F.get('counted',0),he_date(E.get('research_date'))));B.append('| # | גוף | מסמך | תאריך | ניסח / לטובת מי | קישור | נושאים ועמדות שהוא תומך בהם |');B.append('|---|---|---|---|---|---|---|')
	for A in K:
		if A.get('read_status')in NOT_READ:continue
		B.append('| %s | %s | %s | %s | %s / %s | [פתיחה](%s) | %s |'%(A.get('source_id'),A.get('issuing_body')or'',A.get('document')or'',he_date(A.get('doc_date')),DRAFTER_HE.get(A.get('drafter_role'),A.get('drafter_role')or''),DRAFTED_HE.get(A.get('drafted_by'),A.get('drafted_by')or''),A.get('url')or'','; '.join(L.get(A.get('source_id'),[]))or'לא נספר לנקודה'))
	B+=['','הטווח לכל נושא:']
	for A in E.get('ranges')or[]:
		T=next((A[B]['certainty']for B in('middle','ours','theirs')if A.get(B)),A.get('certainty')or CERTAINTY['expert']);B.append('**%s** (%s)'%(A['topic'],T))
		for D in('ours','middle','theirs'):
			J=A.get(D)
			if J:B.append('- %s: דרגה %s. מקורות: %s.'%(POS_HE[D],J['level'],', '.join(J['source_ids'])))
			elif D=='theirs'and A.get('theirs_note'):B.append('- %s: %s.'%(POS_HE[D],A['theirs_note']))
			else:B.append('- %s: ממצא לא מאומת, פחות משלושה מקורות.'%POS_HE[D])
	M=[A for A in K if A.get('read_status')in NOT_READ]
	if M:B+=['','מה לא נמצא:'];B+=['- %s: אותר, לא נקרא (%s), %s.'%(A.get('document')or A.get('source_id'),A.get('read_reason')or A.get('read_status'),A.get('url')or'')for A in M]
	N=E.get('unverified_findings')or[]
	if N:B+=['','מה לא אומת:'];B+=['- %s'%(A.get('text')or A.get('label')or json.dumps(A,ensure_ascii=False))for A in N]
	O=E.get('limitations')or[]
	if O:B+=['','מגבלות:']+['- %s'%A for A in O]
	if C.get('external_sources_table'):B+=['',C['external_sources_table']]
	return H,'\n'.join(B).strip()+'\n'
def agreement_phrases(corpus,n=4):
	A=corpus;B,C=set(),set();I=A.get('documents')if isinstance(A,dict)else A
	for D in I or():
		J=D.get('paragraphs')or[B for A in(D.get('parts')or{}).values()for B in A]
		for E in J:
			F=E.get('text')or E.get('text_accept_all')or'';G=re.findall('\\w+',F)
			for H in range(len(G)-n+1):B.add(' '.join(G[H:H+n]).lower())
			C|={A for A in re.findall('\\d[\\d,.]*\\d|\\d',F)if len(A.replace(',','').replace('.',''))>=2}
	return B,C
def query_problem(query,purpose,corpus,profile,statute_names=(),manifest=None,deal=None):
	E=corpus;from common import net;A=query or'';B=''
	if purpose=='legal':
		for C in sorted(statute_names or(),key=len,reverse=True):
			C=' '.join(str(C or'').split())
			if C and C in' '.join(A.split()):A=' '.join(A.split()).replace(C,' ');B=B or C
	H=client_names(profile,E,manifest,deal);I=net.client_detail_in_query(A,[A for A in H if A])
	if I:return'פרט של הלקוח או של צד בשאילתה (%s)'%I,B
	J=token_in(A,name_tokens(H))
	if J:return'שם של הלקוח, של צד, של פרויקט או של מוצר בשאילתה (%s)'%J,B
	if E:
		K,L=agreement_phrases(E);F=re.findall('\\w+',A.lower())
		for D in range(len(F)-3):
			if' '.join(F[D:D+4])in K:return'רצף מילים מההסכמים בשאילתה (%s)'%' '.join(F[D:D+4]),B
		for G in re.findall('\\d[\\d,.]*\\d|\\d',A):
			if G in L and len(G.replace(',','').replace('.',''))>=2:return'מספר מההסכמים בשאילתה (%s)'%G,B
	return None,B
def url_problem(url,corpus,profile,manifest=None,deal=None):
	B=corpus;from urllib.parse import unquote as G;from common import net;C=G(url or'');H=client_names(profile,B,manifest,deal)
	for D in H:
		if D and D.lower()in C.lower():return'פרט של הלקוח בכתובת (%s)'%D
	E=re.search('(?<!\\d)\\d{9}(?!\\d)',C)
	if E and net._id_check_digit(E.group(0)):return'מספר חברה או זהות בכתובת (%s)'%E.group(0)
	if B:
		I,J=agreement_phrases(B);F=re.findall('[^\\W\\d_]+',C.lower())
		for A in range(len(F)-3):
			if' '.join(F[A:A+4])in I:return'רצף מילים מההסכמים בכתובת (%s)'%' '.join(F[A:A+4])
def case_law_reason(url):
	try:from common.case_law import case_law_url as B
	except ImportError:A=_host(url);return'%s הוא אתר בית משפט או מאגר פסיקה'%A if re.search('(^|\\.)(courts?|judiciary)\\.',A+'.')else None
	return B(url)
def source_type_problem(url,source_type,vendor=None,approved_path=None):
	D=source_type;B=url;from risk.validate_register import domain_ok as F;A=_host(B)
	if not A:return'אין כתובת',None
	E=case_law_reason(B)
	if E:return E,None
	if any(A==B or A.endswith('.'+B)for B in DENIED_DOMAINS):return'%s אינו מקור למחקר שוק (מאגר מצרף, אתר תבניות, אנציקלופדיה או חדשות). מסמך שאותר במאגר נקרא במקור המקורי שלו'%A,None
	if D not in SOURCE_TYPES:return'סוג המקור חסר או אינו אחד מארבעת הסוגים (%s)'%' | '.join(SOURCE_TYPES),None
	C=_approved_rules(approved_path)
	if not C or not F(B,C):return'%s אינו ברשימת המקורות המאושרים: המסמך אינו נקרא ואינו נספר. %s'%(A,NO_POSITION),None
	if D=='vendor_terms'and not(vendor or'').strip():return'תנאים שצד מפרסם: חסר שם הצד המפרסם (--vendor). הם נספרים רק כעמדה של אותו צד',None
	return None,C
def reading_dir():return os.path.join(tempfile.gettempdir(),'areo-research','reading')
def write_copy(source_id,res):
	C=source_id;A=res;from risk.page_text import PdfTextUnavailable as H,page_text as I;D=A.get('content')or b''
	try:J=I(D)
	except H:return
	B=reading_dir();os.makedirs(B,exist_ok=True);F='pdf'if D[:5]==b'%PDF-'else'htm'
	with open(os.path.join(B,'%s.%s'%(C,F)),'wb')as E:E.write(D)
	K={'url':A.get('url'),'final_url':A.get('final_url'),'status':A.get('status'),'ext':F,'log':A.get('log')};save(os.path.join(B,'%s.json'%C),K);G=os.path.join(B,'%s.txt'%C)
	with io.open(G,'w',encoding='utf-8')as E:E.write(J)
	return G
def read_copy(source_id,url):
	C=source_id;from common import net;D=reading_dir()
	try:
		with io.open(os.path.join(D,'%s.json'%C),encoding='utf-8')as A:B=json.load(A)
		with open(os.path.join(D,'%s.%s'%(C,B['ext'])),'rb')as A:E=A.read()
	except(OSError,ValueError,KeyError):return
	if B.get('url')!=net.strip_secrets(net.to_uri(url))[0]:return
	return dict(B,content=E)
def session_path():return os.path.join(tempfile.gettempdir(),'areo-research',SESSION_FILE)
def load_session(now=None):
	A=now
	try:
		with io.open(session_path(),encoding='utf-8')as C:B=json.load(C)
	except(OSError,ValueError):return
	A=A or _dt.datetime.now(_dt.timezone.utc)
	try:
		if _dt.datetime.fromisoformat(B.get('expires_at'))<A:return
	except(TypeError,ValueError):return
	return B
def _log_path(family_dir):return os.path.join(family_dir,'market-research',QUERY_LOG)
def read_query_log(family_dir):
	C=family_dir;A=[];D=os.path.join(C,'market-research',QUERY_LOG_OLD)
	try:
		with io.open(D,encoding='utf-8')as B:A+=json.load(B)
	except(OSError,ValueError):pass
	try:
		with io.open(_log_path(C),encoding='utf-8')as B:
			for E in B:
				try:A.append(json.loads(E))
				except ValueError:continue
	except OSError:pass
	return A
def log_query(family_dir,entry):
	A=family_dir;os.makedirs(os.path.dirname(_log_path(A)),exist_ok=True);C=json.dumps(dict(entry,at=now_iso()),ensure_ascii=False)+'\n';B=os.open(_log_path(A),os.O_WRONLY|os.O_CREAT|os.O_APPEND,420)
	try:os.write(B,C.encode('utf-8'))
	finally:os.close(B)
def query_passed(family_dir,query):B=' '.join((query or'').split());return any(A.get('precheck')in('passed','passed_statute_name')and' '.join((A.get('query')or'').split())==B for A in read_query_log(family_dir))
def check_query(query,purpose,family_dir,corpus=None,profile=None,statutes=(),via='query',manifest=None,deal=None):
	E=purpose;D=query;A,B=query_problem(D,E,corpus,profile,statutes,manifest,deal);C={'query':D,'purpose':E,'via':via,'precheck':'failed'if A else'passed_statute_name'if B else'passed'}
	if A:C['reason']=A
	if B:C['statute_name']=B
	log_query(family_dir,C);return A
def cmd_start(a):
	for(A,C)in((a.corpus,'החילוץ'),(a.profile,'הפרופיל'),(a.manifest,'המניפסט'),(a.deal,'העסקה')):
		if A and not os.path.exists(A):print('%s אינו קיים: %s'%(C,A));return 2
	B=_dt.datetime.now(_dt.timezone.utc)+_dt.timedelta(hours=SESSION_HOURS);D={'family_dir':os.path.abspath(a.family_dir),'corpus':os.path.abspath(a.corpus)if a.corpus else None,'profile':os.path.abspath(a.profile)if a.profile else None,'manifest':os.path.abspath(a.manifest)if a.manifest else None,'deal':os.path.abspath(a.deal)if a.deal else None,'statutes':a.statute or[],'started_at':now_iso(),'expires_at':B.isoformat()};os.makedirs(os.path.dirname(session_path()),exist_ok=True);save(session_path(),D);print('מושב מחקר נפתח עד %s. הרץ query על כל שאילתה לפני החיפוש, וחפש רק בנוסח שעבר; קריאה רק דרך fetch. בסוף המחקר: stop.'%B.astimezone().strftime('%H:%M'));return 0
def cmd_stop(a):
	import shutil as A
	try:os.remove(session_path())
	except OSError:pass
	A.rmtree(reading_dir(),ignore_errors=True);print('מושב המחקר נסגר.');return 0
def _opt(path,what):return load(path,what)if path else None
def cmd_query(a):
	A=load_session()or{};B=a.family_dir or A.get('family_dir')
	if not B:print('אין מושב מחקר פעיל ולא נמסר --family-dir. התחל ב-start.');return 2
	D=load(a.corpus or A.get('corpus'),'החילוץ')if a.corpus or A.get('corpus')else None;E=load_profile(a.profile or A.get('profile'))if a.profile or A.get('profile')else None;F=_opt(a.manifest or A.get('manifest'),'המניפסט');G=_opt(a.deal or A.get('deal'),'העסקה');C=check_query(a.query,a.purpose,B,D,E,a.statute or A.get('statutes')or(),manifest=F,deal=G)
	if C:print('השאילתה נעצרה ולא תישלח: %s'%C);return 3
	print('מותר לחפש, בדיוק בנוסח הזה: %s'%a.query);return 0
def cmd_ranges(a):
	B=load(a.model,'המודל');C=compute_ranges(B);save(a.model,B)
	for A in C:D=', '.join('%s %s'%(POS_HE[B],A[B]['level'])for B in('ours','middle','theirs')if A.get(B));print('%s: %s%s; צהוב מ-%s'%(A['topic'],D or'אין נקודה עם שלושה מקורות','; לטובתם: '+A['theirs_note']if A.get('theirs_note')else'',A['yellow_from']))
	print('ספירה: %s'%json.dumps(B['market_research']['counts'],ensure_ascii=False));return 0
def cmd_check(a):
	B=load(a.model,'המודל');A=check_model(B,word=a.word,final=a.final)
	for C in A:print('שגיאה: %s'%C)
	print('שגיאות: %d'%len(A));return 3 if A else 0
SOURCE_TYPE_KEY={B:A for(A,B)in SOURCE_TYPE_NUM.items()}
def ref_problem(r):
	A=r.get('source_type');C=SOURCE_TYPE_KEY.get(int(A))if str(A or'').isdigit()else A;B,D=source_type_problem(r.get('final_url')or r.get('url'),C,r.get('vendor')or r.get('issuing_body'))
	if not B and r.get('final_url')and r.get('final_url')!=r.get('url'):B,D=source_type_problem(r['url'],C,r.get('vendor')or r.get('issuing_body'))
	return B
def legal_problem(url,rules):
	A=url;from risk.validate_register import domain_ok as C;B=case_law_reason(A)
	if B:return B
	if not C(A,rules):return'דומיין או נתיב שאינו ברשימת המקורות המאושרים (%s)'%_host(A)
def cmd_links(a):
	from common import net;from risk.validate_register import approved_domains as L;F=load(a.model,'המודל');I=F.get('market_research')or{};D=[]
	if a.approved_sources and not os.path.isfile(a.approved_sources):print('קובץ המקורות המאושרים אינו קיים: %s'%a.approved_sources);return 2
	J=L(a.approved_sources)[0];H=os.path.join(tempfile.gettempdir(),'areo-net','links-'+os.path.basename(os.path.normpath(a.family_dir)));os.makedirs(H,exist_ok=True)
	for A in I.get('source_refs')or[]:
		if not A.get('url')or A.get('read_status')in NOT_READ:continue
		E=ref_problem(A);A['link_checked_at']=now_iso()
		if E:A['read_status']='excluded';A['read_reason']='לא נבדק שוב: %s'%E;D.append(A.get('source_id'));continue
		P,M=source_type_problem(A.get('url'),SOURCE_TYPE_KEY.get(int(A['source_type']))if str(A.get('source_type')or'').isdigit()else A.get('source_type'),A.get('vendor')or A.get('issuing_body'));B=net.fetch(A['url'],'בדיקת קישור לפני המסירה',allowed_domains=M,run_dir=H);G=B.get('status')and 200<=B['status']<300 and not B.get('blocked');N=bool(A.get('file_sha256')and B.get('sha256')==A['file_sha256'])
		if G and not N and A.get('document')and B.get('text'):
			K=re.search('<title[^>]*>(.*?)</title>',B['text'],re.S|re.I);O=((K.group(1)if K else'')+' '+re.sub('<[^>]+>',' ',B['text'])[:20000]).lower()
			if not any(A.lower()in O for A in re.findall('\\w{4,}',A['document'])[:3]):G,B['reason']=False,'שם המסמך אינו מופיע בדף'
		if G and A.get('file_sha256')and B.get('sha256')and B['sha256']!=A['file_sha256']:A['file_sha256_new']=B['sha256'];A.setdefault('notes',[]).append('המסמך השתנה מאז ההורדה (%s)'%he_date(A['link_checked_at']))
		if not G:A['read_status']='located_not_read';A['read_reason']='הקישור לא נפתח ב-%s (%s)'%(he_date(A['link_checked_at']),B.get('reason'));D.append(A['source_id'])
	for C in F.get('external_sources')or[]:
		if C.get('url')and str(C.get('ref','')).startswith(('L','X')):
			C['link_checked_at']=now_iso();E=legal_problem(C['url'],J)
			if E:C['verification']='לא אומת: %s'%E;D.append(C.get('ref'));continue
			B=net.fetch(C['url'],'בדיקת קישור לפני המסירה',run_dir=H,allowed_domains=J)
			if not(B.get('status')and 200<=B['status']<300 and not B.get('blocked')):C['verification']='לא אומת: הקישור לא נפתח ב-%s'%he_date(C['link_checked_at']);D.append(C.get('ref'))
	if D:compute_ranges(F)
	I.setdefault('refresh',{})['last_link_check']=now_iso();save(a.model,F);print('נבדקו הקישורים. נכשלו: %s'%(', '.join(str(A)for A in D)if D else'אף אחד'))
	if D:print('הטווח חושב מחדש בלי המקורות שנכשלו. הרץ שוב message לפני המסירה.')
	return 3 if D else 0
def cmd_message(a):
	B=None
	if a.out:
		from common.cli import OutputRefused as F,guard_out as G
		try:B=G(a.out,inputs=[a.model])
		except F as H:print('refused: %s'%H,file=sys.stderr);return 2
	A=load(a.model,'המודל');I,C=build_message(A);D=A.setdefault('market_research',{});D['disclosure']={'fixed_sentence':I,'chat_message':C,'shown_at':now_iso(),'word_chapter':True}
	if isinstance(A.get('handoff'),dict):A['handoff']['counted_sources']=(D.get('counts')or{}).get('counted')
	save(a.model,A);E=[A for A in check_model(A)if A.startswith(('MARKET_COUNT_MISMATCH','ALL_AREO'))]
	if B:
		with io.open(B,'w',encoding='utf-8')as J:J.write(C)
	print(C)
	for K in E:print('שגיאה: %s'%K)
	return 3 if E else 0
def cmd_fetch(a):
	from common import net;from risk.entity_store import EntityStore as U;E=load_session()or{};H,I=a.corpus or E.get('corpus'),a.profile or E.get('profile');J=load(H,'החילוץ')if H else None;K=load_profile(I)if I else None;L=_opt(a.manifest or E.get('manifest'),'המניפסט');M=_opt(a.deal or E.get('deal'),'העסקה')
	def F(reason,precheck='failed'):print(json.dumps({'sent':False,'precheck':precheck,'reason':reason,'query':a.query},ensure_ascii=False,indent=1));return 3
	if not query_passed(a.family_dir,a.query):return F('השאילתה לא נבדקה לפני החיפוש. הרץ query על השאילתה לפני החיפוש, וחפש בדיוק בנוסח שעבר','not_prechecked')
	C,G=query_problem(a.query,a.purpose,J,K,a.statute or E.get('statutes')or(),L,M);C=C or url_problem(a.url,J,K,L,M)
	if C:return F(C)
	N=case_law_reason(a.url)
	if N:return F(N,'case_law')
	if a.purpose=='legal':
		from urllib.parse import urlsplit as V;from risk.validate_register import approved_domains as W,domain_ok as X
		if a.approved_sources and not os.path.isfile(a.approved_sources):print('קובץ המקורות המאושרים אינו קיים: %s'%a.approved_sources);return 2
		O=W(a.approved_sources)[0]
		if not X(a.url,O):return F('דומיין או נתיב שאינו ברשימת המקורות המאושרים (%s)'%V(a.url).hostname,'approved_sources')
		P=O
	else:
		C,P=source_type_problem(a.url,a.source_type,a.vendor,a.approved_sources)
		if C:return F(C,'source_type')
	Q=U(os.path.join(a.family_dir,'market-research'));D=read_copy(a.source_id,a.url)if a.excerpt else None
	if D:
		A={'status':D['status'],'blocked':False,'lawyer_task':None,'log':D['log']}
		try:A['stored'],Z=Q.store_page(a.source_id,D['final_url'],D['content'],ext=D['ext'],excerpt=a.excerpt);A['reason']='ok: נשמר חלון סביב הקטע, מעותק הקריאה (בלי בקשה נוספת)'
		except Exception as Y:A['stored'],A['reason']=None,'ok, not stored: %s'%Y
	else:R=os.path.join(tempfile.gettempdir(),'areo-net',os.path.basename(os.path.normpath(a.family_dir)));os.makedirs(R,exist_ok=True);A=net.fetch(a.url,a.topic or a.purpose,allowed_domains=P,store=Q,source_id=a.source_id,excerpt=a.excerpt,run_dir=R)
	S=dict(A['log'],query=a.query,purpose=a.purpose,topic=a.topic,precheck='passed_statute_name'if G else'passed')
	if G:S['statute_name']=G
	B={'sent':True,'status':A.get('status'),'blocked':A.get('blocked'),'reason':A.get('reason'),'lawyer_task':A.get('lawyer_task'),'stored':A.get('stored'),'search_log':S}
	if a.purpose=='market':
		B['source_type']=SOURCE_TYPE_NUM[a.source_type]
		if a.vendor:B['vendor']=a.vendor
	if A.get('blocked'):B['read_status']='located_not_read';B['read_reason']='אותר, לא נקרא: נחסם'
	elif not A.get('stored')and A.get('content')and not a.excerpt:
		T=write_copy(a.source_id,A)
		if T:B['reading_copy']=T;B['next']='המסמך גדול מכדי להישמר כולו. קרא את reading_copy, ובחר את הקטע המילולי של הנושא. אחר כך הרץ שוב fetch עם אותם פרטים ועם --excerpt "<הקטע>": החלון סביבו נשמר, בלי בקשה נוספת לאתר. עותק הקריאה נמחק ב-stop.'
	print(json.dumps(B,ensure_ascii=False,indent=1));return 0 if A.get('stored')or B.get('reading_copy')else 3
def cmd_lookup(a):from common.approved_sources import lookup as B;A=B(a.url,a.approved_sources);print(json.dumps(A,ensure_ascii=False,indent=1));return 0 if A['status']=='approved'else 2 if A['status']=='no_list'else 1
def main(argv=None):
	sys.dont_write_bytecode=True;sys.stdout.reconfigure(encoding='utf-8');F=argparse.ArgumentParser(description=__doc__.split('\n')[0]);B=F.add_subparsers(dest='cmd',required=True);K=B.add_parser('ranges',help='הטווח לכל נושא');K.add_argument('--model',required=True);G=B.add_parser('check',help='הבדיקות של מחקר השוק');G.add_argument('--model',required=True);G.add_argument('--word',help='ה-Word שנבנה: הקישורים חייבים להיבדק אחריו');G.add_argument('--final',action='store_true',help='מסירה סופית: pass_b_stop_reason');H=B.add_parser('links',help='בדיקת הקישורים לפני המסירה');H.add_argument('--model',required=True);H.add_argument('--family-dir',required=True);H.add_argument('--approved-sources',help='מקורות-מאושרים.json, לבדיקת המקורות המשפטיים (L, X) לפני הקריאה (ברירת מחדל: AREO_APPROVED_SOURCES, ואחריו העותק שבתוסף)');I=B.add_parser('message',help='הודעת המסירה');I.add_argument('--model',required=True);I.add_argument('--out');A=B.add_parser('fetch',help='בקשה אחת לרשת');A.add_argument('--family-dir',required=True,help='playbooks/<family_id>: העותק נשמר ב-market-research/sources/');A.add_argument('--source-id',required=True);A.add_argument('--url',required=True);A.add_argument('--query',required=True,help='השאילתה, מילה במילה, כפי שתירשם ביומן');A.add_argument('--purpose',required=True,choices=('market','legal'));A.add_argument('--topic',help='הנושא שלשמו נשלחה');A.add_argument('--excerpt');A.add_argument('--corpus',help='החילוץ של ההסכמים: הבדיקה שאין בשאילתה רצף או מספר מהם');A.add_argument('--profile');A.add_argument('--manifest',help='מניפסט הקורפוס: כינויי הצדדים (parties_hint) נבדקים בשאילתה');A.add_argument('--deal',help='קובץ העסקה (negotiation_state.json), כשהבנייה לבקשת הנושא ונותן: שם הצד שכנגד');A.add_argument('--statute',action='append',help='שם חוק או רגולטור מהרשימה הסגורה (רק ב-legal)');A.add_argument('--source-type',choices=sorted(SOURCE_TYPES),help='חובה במחקר שוק: tender | public_filing | vendor_terms | model_agreement');A.add_argument('--vendor','--publisher',dest='vendor',help='שם הצד שמפרסם את התנאים באתר שלו (vendor_terms)');A.add_argument('--approved-sources',help='מקורות-מאושרים.json, לקריאה רגולטורית (ברירת מחדל: AREO_APPROVED_SOURCES, ואחריו העותק שבתוסף, lib/מקורות-מאושרים.json; אין רשימת נפילה בקוד)');D=B.add_parser('start',help='פותח מושב מחקר: מכאן כל חיפוש ברשת נבדק לפני שהוא נשלח');D.add_argument('--family-dir',required=True);D.add_argument('--corpus');D.add_argument('--profile');D.add_argument('--manifest');D.add_argument('--deal');D.add_argument('--statute',action='append');B.add_parser('stop',help='סוגר את מושב המחקר');J=B.add_parser('lookup',help='הרשומה של כתובת אחת ברשימת המקורות המאושרים, בלי לקרוא את הרשימה');J.add_argument('--url',required=True);J.add_argument('--approved-sources',help='מקורות-מאושרים.json (ברירת מחדל: AREO_APPROVED_SOURCES, ואחריו העותק שבתוסף, lib/מקורות-מאושרים.json)');C=B.add_parser('query',help='בודק שאילתה לפני החיפוש, ורושם אותה ביומן');C.add_argument('--query',required=True);C.add_argument('--purpose',required=True,choices=('market','legal'));C.add_argument('--family-dir',help='ברירת המחדל: של המושב הפעיל');C.add_argument('--corpus');C.add_argument('--profile');C.add_argument('--manifest');C.add_argument('--deal');C.add_argument('--statute',action='append');E=F.parse_args(argv)
	if E.cmd=='fetch'and E.purpose=='market'and not E.source_type:F.error('במחקר שוק חובה --source-type (ארבעת סוגי המקורות של market-research.md)')
	return{'ranges':cmd_ranges,'check':cmd_check,'links':cmd_links,'message':cmd_message,'fetch':cmd_fetch,'start':cmd_start,'stop':cmd_stop,'query':cmd_query,'lookup':cmd_lookup}[E.cmd](E)
if __name__=='__main__':sys.exit(main())
