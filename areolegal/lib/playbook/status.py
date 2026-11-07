# -*- coding: utf-8 -*-
# Copyright (c) Areo. All rights reserved. Licensed under the terms at https://areo.co.il/legal/terms
import datetime as _dt,io,json,os
TRACKS='green','yellow','red'
APPROVED='approved','approved_modified'
APPROVED_PREFIX='מדיניות מאושרת'
PARTIAL_FMT='{base}; {n} מתוך {m} עמדות מאושרות'
LABEL_MARKET='טיוטת מדיניות ממחקר שוק, מחכה לאישור שלכם'
LABEL_MIXED='טיוטת מדיניות מההסכמים שלכם וממחקר שוק, מחכה לאישור שלכם'
LABEL_OWN='טיוטת מדיניות מההסכמים שלכם, מחכה לאישור שלכם'
LABELS={'he':{'market':LABEL_MARKET,'mixed':LABEL_MIXED,'own':LABEL_OWN,'approved':APPROVED_PREFIX,'partial':PARTIAL_FMT,'by':', בידי %s'},'en':{'market':'Draft policy from market research, awaiting your approval','mixed':'Draft policy from your agreements and market research, awaiting your approval','own':'Draft policy from your agreements, awaiting your approval','approved':'Approved policy','partial':'{base}; {n} of {m} positions approved','by':', by %s'}}
CORPUS_STATUSES='signed','mostly_drafts','company_forms','third_party_forms','unknown'
CORPUS_SUFFIX={'signed':'','mostly_drafts':'_drafts','company_forms':'_forms','third_party_forms':'_other','unknown':'_other'}
LABELS['he'].update({'own_drafts':'טיוטת מדיניות מהמסמכים שלכם (רובם טיוטות), מחכה לאישור שלכם','mixed_drafts':'טיוטת מדיניות מהמסמכים שלכם (רובם טיוטות) וממחקר שוק, מחכה לאישור שלכם','own_forms':'טיוטת מדיניות מהנוסחים שאתם מציגים לצד השני, מחכה לאישור שלכם','mixed_forms':'טיוטת מדיניות מהנוסחים שאתם מציגים לצד השני וממחקר שוק, מחכה לאישור שלכם','own_other':'טיוטת מדיניות מנוסחים שאינם הסכמים חתומים שלכם, מחכה לאישור שלכם','mixed_other':'טיוטת מדיניות מנוסחים שאינם הסכמים חתומים שלכם וממחקר שוק, מחכה לאישור שלכם'})
LABELS['en'].update({'own_drafts':'Draft policy from your documents (most of them drafts), awaiting your approval','mixed_drafts':'Draft policy from your documents (most of them drafts) and market research, awaiting your approval','own_forms':'Draft policy from the forms you present to counterparties, awaiting your approval','mixed_forms':'Draft policy from the forms you present to counterparties and market research, awaiting your approval','own_other':'Draft policy from forms that are not your signed agreements, awaiting your approval','mixed_other':'Draft policy from forms that are not your signed agreements and market research, awaiting your approval'})
LABELS['he'].update({'areo':'טיוטת מדיניות בהמלצת Areo, בלי דוגמה מההסכמים שלכם, מחכה לאישור שלכם','own_theirs':'טיוטת מדיניות מנוסחים של הצד השני שחתמתם עליהם, מחכה לאישור שלכם','mixed_theirs':'טיוטת מדיניות מנוסחים של הצד השני שחתמתם עליהם וממחקר שוק, מחכה לאישור שלכם'})
LABELS['en'].update({'areo':'Draft policy recommended by Areo, with no example from your agreements, awaiting your approval','own_theirs':'Draft policy from counterparty paper you signed, awaiting your approval','mixed_theirs':'Draft policy from counterparty paper you signed and market research, awaiting your approval'})
BASE_CODES=('market','mixed','own','areo')+tuple(A+B for A in('own','mixed')for B in('_drafts','_forms','_other','_theirs'))
OLD_LABELS={'he':{'market':'פלייבוק מוצע, מבוסס מחקר שוק, טעון אישור','mixed':'פלייבוק מוצע, מבוסס הסכמים ומחקר שוק, טעון אישור','own':'פלייבוק מוצע, מבוסס הסכמי החברה, טעון אישור','own_drafts':'פלייבוק מוצע, מבוסס מסמכי החברה שרובם טיוטות, טעון אישור','mixed_drafts':'פלייבוק מוצע, מבוסס מסמכי החברה שרובם טיוטות ומחקר שוק, טעון אישור','own_forms':'פלייבוק מוצע, מבוסס נוסחים שהחברה מציגה לצד שכנגד, טעון אישור','mixed_forms':'פלייבוק מוצע, מבוסס נוסחים שהחברה מציגה לצד שכנגד ומחקר שוק, טעון אישור','own_other':'פלייבוק מוצע, מבוסס נוסחים שאינם הסכמים חתומים של החברה, טעון אישור','mixed_other':'פלייבוק מוצע, מבוסס נוסחים שאינם הסכמים חתומים של החברה ומחקר שוק, טעון אישור','areo':'פלייבוק מוצע, הצעת Areo, לא מבוסס על הסכמי החברה, טעון אישור','own_theirs':'פלייבוק מוצע, מבוסס נוסחים של הצד שכנגד, טעון אישור','mixed_theirs':'פלייבוק מוצע, מבוסס נוסחים של הצד שכנגד ומחקר שוק, טעון אישור'},'en':{'market':'Proposed playbook, based on market research, subject to approval','mixed':'Proposed playbook, based on agreements and market research, subject to approval','own':"Proposed playbook, based on the company's agreements, subject to approval",'own_drafts':"Proposed playbook, based on the company's documents, most of them drafts, subject to approval",'mixed_drafts':"Proposed playbook, based on the company's documents, most of them drafts, and market research, subject to approval",'own_forms':'Proposed playbook, based on forms the company presents to its counterparties, subject to approval','mixed_forms':'Proposed playbook, based on forms the company presents to its counterparties and market research, subject to approval','own_other':'Proposed playbook, based on forms that are not signed agreements of the company, subject to approval','mixed_other':'Proposed playbook, based on forms that are not signed agreements of the company and market research, subject to approval','areo':"Proposed playbook, an Areo proposal, not based on the company's agreements, subject to approval",'own_theirs':'Proposed playbook, based on counterparty paper, subject to approval','mixed_theirs':'Proposed playbook, based on counterparty paper and market research, subject to approval'}}
LEGACY_BASE_LABELS=tuple(OLD_LABELS[A][B]for A in('he','en')for B in BASE_CODES)+('פלייבוק מוצע, מבוסס נוסחים שהחברה מציגה ללקוחותיה, טעון אישור','פלייבוק מוצע, מבוסס נוסחים שהחברה מציגה ללקוחותיה ומחקר שוק, טעון אישור','Proposed playbook, based on forms the company presents to its customers, subject to approval','Proposed playbook, based on forms the company presents to its customers and market research, subject to approval')
CURRENT_BASE_LABELS=tuple(LABELS[A][B]for A in('he','en')for B in BASE_CODES)
BASE_LABELS=CURRENT_BASE_LABELS+LEGACY_BASE_LABELS
APPROVED_PREFIXES=LABELS['he']['approved'],LABELS['en']['approved']
LABEL_FIELD='status_label'
DUAL_FIELDS='presentation_label',
HIGH_SEVERITY='high','critical','גבוהה','קריטית'
COMPANY_BASES='company_agreement','company_template','agreement','template','established','company_policy','signed_deviation'
MARKET_ORIGINS='own_plus_market','market_built'
STATUS_DRAFT,STATUS_PARTIAL,STATUS_APPROVED='Draft','PartiallyApproved','Approved'
REUPLOAD_NOTICE='רשומת האישור נקלטה בגרסה קודמת, בלי ראיה להעלאת הגיליון החתום. העמדות שבה אינן נספרות כמאושרות. יש להעלות שוב את גיליון העמדות החתום.'
def norm_lang(v):
	v=str(v or'').strip().lower()
	if v.startswith('en'):return'en'
	if v.startswith('he')or v in('iw','עב','עברית'):return'he'
def deliverable_lang(model=None,profile=None,lang=None):
	A=model;A,B=A or{},profile or{}
	for D in(lang,B.get('deliverable_language'),(A.get('scope_summary')or{}).get('deliverable_language'),A.get('deliverable_language'),B.get('display_language')):
		C=norm_lang(D)
		if C:return C
	return'he'
def model_lang(model):return deliverable_lang(model)
def is_legacy_record(record):
	A=record
	if not A:return False
	B=A.get('evidence')or{};C=B.get('received_via')or A.get('received_via');D=B.get('upload_ref')or A.get('upload_ref');return not(C and D)
def effective_cells(record,cells=None):
	B=record;A=cells;A=A if A is not None else(B or{}).get('cells')or{}
	if not is_legacy_record(B):return A
	return{A:dict(B,legacy=True,policy_claim=False,simulated=True)for(A,B)in A.items()}
def _latest_record(model):A=[A for A in(model or{}).get('approval_records')or[]if not A.get('superseded_by')];return A[-1]if A else None
def cell_key(rule_id,track,segment=None):return'%s|%s|%s'%(rule_id,segment or'-',track)
def iter_cell_keys(model):
	for B in model.get('rules')or[]:
		for A in TRACKS:yield cell_key(B['rule_id'],A)
		for C in B.get('segment_variants')or[]:
			for A in TRACKS:
				if(C.get('traffic_light')or{}).get(A)and C.get('segment_id'):yield cell_key(B['rule_id'],A,C['segment_id'])
def agreements_counted(model):
	A=model;B=A.get('corpus_basis')or{}
	for C in('agreements_counted','agreement_units','counted'):
		if isinstance(B.get(C),int):return B[C]
	D=A.get('scope_summary')or{}
	if isinstance(D.get('total_document_count'),int):return D['total_document_count']
	return 0
PUBLIC_KINDS='public_body','government_company','university'
def _base(p):return os.path.basename(str(p or'').replace(chr(92),'/'))
def is_counterparty_form(row,listed=()):
	A=row
	if str(A.get('doc_role')or'')!='form':return False
	return A.get('paper')=='theirs'or A.get('counterparty_kind')in PUBLIC_KINDS or _base(A.get('file'))in listed
NON_AGREEMENT_ROLES='template','guidance','policy','table','correspondence'
def is_agreement_row(row):
	A=row
	if not isinstance(A,dict)or A.get('included')is False or A.get('exclusion_reason')=='not_agreement':return False
	if A.get('is_agreement')is False or A.get('doc_kind')in('guidance','policy','table'):return False
	return str(A.get('doc_role')or'')not in NON_AGREEMENT_ROLES
def company_agreements_counted(model):
	A=model;B=agreements_counted(A);C=[A for A in A.get('source_log')or[]if isinstance(A,dict)and A.get('included',True)]
	if not C:return B
	D=((A.get('scope_summary')or{}).get('corpus_basis')or{}).get('needs_review')or{};E={_base(A)for A in D.get('counterparty_forms')or[]};F=sum(1 for A in C if is_agreement_row(A)and not is_counterparty_form(A,E));return min(B,F)
NON_COMPANY_BASES='market_standard','areo_proposal'
def company_backed_tracks(model):
	A=0
	for C in model.get('rules')or[]:
		for D in TRACKS:
			B=((C.get('traffic_light')or{}).get(D)or{}).get('basis')
			if B and B not in NON_COMPANY_BASES:A+=1
	return A
def corpus_origin(model):A=model;return A.get('corpus_origin')or(A.get('scope_summary')or{}).get('corpus_origin')
def corpus_read(model):
	A=model
	if corpus_origin(A)=='market_built':return False
	return company_agreements_counted(A)>0
def no_company_position(model):
	A=model
	if not corpus_read(A)or company_backed_tracks(A):return False
	return any(((A.get('traffic_light')or{}).get(B)or{}).get('basis')for A in A.get('rules')or[]if isinstance(A,dict)for B in TRACKS)
def uses_market(model):
	A=model
	if corpus_origin(A)in MARKET_ORIGINS:return True
	B=A.get('market_research')or{};return any(A.get('client_choice')=='include'for A in B.get('findings')or[])
def mostly_drafts(model):A=[A for A in model.get('source_log')or[]if isinstance(A,dict)and A.get('included')];return bool(A)and sum(1 for A in A if A.get('doc_role')=='draft')*2>len(A)
def corpus_status(model):
	A=model;B=(A.get('scope_summary')or{}).get('corpus_status')
	if B in CORPUS_STATUSES:return B
	return'mostly_drafts'if mostly_drafts(A)else'signed'
def theirs_paper(model):A=[A for A in model.get('source_log')or[]if isinstance(A,dict)and A.get('included',True)];return bool(A)and sum(1 for A in A if A.get('paper')=='theirs')*2>len(A)
def base_code(model):
	A=model;B=corpus_read(A);C=corpus_status(A);D='_theirs'if C=='signed'and theirs_paper(A)else CORPUS_SUFFIX[C]
	if uses_market(A):return'mixed'+D if B else'market'
	return'own'+D if B else'areo'
def base_label(model,lang=None):A=model;return LABELS[norm_lang(lang)or model_lang(A)][base_code(A)]
def code_of_label(text):
	C=str(text or'').split(';')[0].strip()
	for(D,E)in((False,LABELS),(True,OLD_LABELS)):
		for A in('he','en'):
			for B in BASE_CODES:
				if E[A].get(B)==C:return B,A,D
	return None,None,False
def label_findings(model,core=None,index_entry=None):
	A=model;C=[];I=base_code(A);J=[('model',A),('core',core),('index',index_entry)]
	if isinstance(A.get('handoff'),dict):J.append(('handoff',A['handoff']))
	F={}
	for(D,E)in J:
		if not isinstance(E,dict)or not E.get(LABEL_FIELD):continue
		B=str(E.get(LABEL_FIELD));G=E.get('playbook_status')or STATUS_DRAFT;F[D]=B;H,M,K=code_of_label(B);L=B.startswith(APPROVED_PREFIXES)
		if L:
			if G!=STATUS_APPROVED:C.append(('LABEL_MISMATCH','%s.status_label="%s" אומר "מדיניות מאושרת", והמעמד %s.'%(D,B,G)))
			continue
		if H is None:C.append(('LABEL_MISMATCH','%s.status_label="%s" אינו תווית שנגזרת ב-status.py. הנגזרת: "%s".'%(D,B,base_label(A))));continue
		if G==STATUS_APPROVED:C.append(('LABEL_MISMATCH','%s.status_label="%s", והמעמד Approved.'%(D,B)))
		if H!=I:C.append(('LABEL_MISMATCH','%s.status_label="%s" (%s), ולפי corpus_origin=%s, %d הסכמים שנספרו, corpus_status=%s ומחקר השוק התווית היא "%s" (%s).'%(D,B,H,corpus_origin(A),agreements_counted(A),corpus_status(A),base_label(A),I)))
		elif K:C.append(('LABEL_OLD_WORDING','%s.status_label בניסוח הקודם ("%s"). התווית בקול של Areo: "%s".'%(D,B,base_label(A))))
	if len(set(F.values()))>1:C.append(('LABEL_DRIFT','התווית שונה בין השכבות: %s.'%'; '.join('%s="%s"'%(A,B)for(A,B)in sorted(F.items()))))
	return C
def label_for(st,lang=None):
	B=lang;A=st;B=norm_lang(B)or A.get('lang')or'he';C=LABELS[B];D=C[A.get('base_code')or'own']
	if A['playbook_status']==STATUS_APPROVED:return'%s, %s'%(C['approved'],fmt_date(A.get('approved_on')or _dt.date.today().isoformat(),B))+(C['by']%A['approved_by']if A.get('approved_by')else'')
	if A['playbook_status']==STATUS_PARTIAL:return C['partial'].format(base=D,n=A['approved_count'],m=A['positions_count'])
	return D
PROGRESS={'he':'אושרו {n} מתוך {m} עמדות.','en':'{n} of {m} positions approved.'}
def progress_line(st,lang=None):B=lang;A=st;B=norm_lang(B)or A.get('lang')or'he';return PROGRESS[B].format(t=A.get('approved_topics',0),tm=A.get('topics_count',0),n=A.get('approved_count',0),m=A.get('positions_count',0))
def in_lang(st,lang):
	A=lang;A=norm_lang(A)
	if not A or A==st.get('lang'):return st
	B=dict(st,lang=A);B['label']=label_for(B,A);B['base_label']=LABELS[A][B.get('base_code')or'own'];return B
EN_MONTHS='January','February','March','April','May','June','July','August','September','October','November','December'
def fmt_date(iso,lang='he'):
	A=_dt.date.fromisoformat(str(iso)[:10])
	if norm_lang(lang)=='en':return'%d %s %d'%(A.day,EN_MONTHS[A.month-1],A.year)
	return'%d.%d.%d'%(A.day,A.month,A.year)
def _he_date(iso):return fmt_date(iso,'he')
def open_decisive(model):
	B=[]
	for A in model.get('validation_queue')or[]:
		C=A.get('status')or('closed'if A.get('answered')else'open')
		if C=='open'and not A.get('answered')and str(A.get('severity')or'').lower()in HIGH_SEVERITY:B.append(A)
	return B
def _rule_of(key):return key.split('|')[0]
def cell_counts(cell):
	A=cell
	if not A or A.get('status')not in APPROVED:return False
	if not A.get('policy_claim')or A.get('simulated')or A.get('needs_amendment')or A.get('legacy'):return False
	if A.get('legal_review_required')and not(A.get('legal_review_done_by')and A.get('legal_review_done_at',True)):return False
	return True
def _signed_by(cells,keys):
	A=[]
	for D in keys:
		C=cells.get(D)or{};B=', '.join(A for A in(C.get('signer'),C.get('role'))if A)
		if B and B not in A:A.append(B)
	return'; '.join(A)
def derive_status(model,cells=None,record=None,lang=None):
	M=record;C=lang;B=model;A=cells;N=M if M is not None else _latest_record(B);F=is_legacy_record(N);A=effective_cells(N,A or{})if F else A or{};E=list(iter_cell_keys(B));G=open_decisive(B);O={A.get('rule_id')for A in G if A.get('rule_id')and A.get('rule_id')!='GLOBAL'};U=[A.get('id')for A in G if not A.get('rule_id')or A.get('rule_id')=='GLOBAL'];D=[B for B in E if cell_counts(A.get(B))and _rule_of(B)not in O];V=sorted(B for B in E if(A.get(B)or{}).get('status')in('pending_choice','pending_legal_review','open')or cell_counts(A.get(B))and _rule_of(B)in O);C=norm_lang(C)or model_lang(B);P=base_code(B);H,I=len(D),len(E);Q=R=None
	if I and H==I and not U:S=sorted(str(A[B].get('approved_at')or'')[:10]for B in D if A[B].get('approved_at'));Q=S[-1]if S else _dt.date.today().isoformat();R=_signed_by(A,D);J=STATUS_APPROVED
	elif H:J=STATUS_PARTIAL
	else:J=STATUS_DRAFT
	K={}
	for T in E:K.setdefault(_rule_of(T),[]).append(T)
	W=set(D);X=sum(1 for A in K.values()if all(A in W for A in A));L={'playbook_status':J,'base_code':P,'lang':C,'approved_on':Q,'approved_by':R,'base_label':LABELS[C][P],'approved_count':H,'positions_count':I,'approved_topics':X,'topics_count':len(K),'approved_keys':D,'blocked_keys':V,'open_questions':[A.get('id')for A in G],'agreements_counted':agreements_counted(B),'legacy_record':F,'notices':[REUPLOAD_NOTICE]if F else[]};L['label']=label_for(L,C);return L
def policy_claim(model,cells,rule_id,track,segment=None,wording_fp=None):
	J=wording_fp;I=segment;H=track;G=rule_id;C=cells;A=cell_key(G,H,I)
	if I and A not in(C or{}):A=cell_key(G,H)
	D=(C or{}).get(A);E=derive_status(model,C);B=A in E['approved_keys'];F=None
	if not B:F='open_decisive_question'if cell_counts(D)else'not_approved'
	if B and J and D.get('approved_fp')and J!=D['approved_fp']:B,F=False,'wording_differs_from_approved'
	return{'policy_claim':B,'key':A,'reason':F,'status_label':E['label'],'playbook_status':E['playbook_status']}
def cell_result(cell,record_id=None):
	C=record_id;A=cell
	if not A:return
	B={B:A.get(B)for B in('status','policy_claim','simulated','legal_review_done_by','legal_review_done_at','approved_at','signer')};B['counts_as_approved']=cell_counts(A)
	if C:B['record_id']=C
	return B
def _rule_policy_status(rule,cells,st):
	A=rule;B=[cell_key(A['rule_id'],B)for B in TRACKS]
	if all(A in st['approved_keys']for A in B):return'Confirmed'
	return A.get('policy_status_from_evidence')or A.get('policy_status')or'Inferred'
def stamp(model,core,index_entry,cells=None,record_id=None):
	F=core;E=cells;A=model;C=derive_status(A,E);I=[A,F,index_entry]
	if A is not None and isinstance(A.get('handoff'),dict):I.append(A['handoff'])
	for D in I:
		if D is None:continue
		for M in DUAL_FIELDS:D.pop(M,None)
		D['playbook_status']=C['playbook_status'];D[LABEL_FIELD]=C['label'];D['approved_count']=C['approved_count'];D['positions_count']=C['positions_count']
	if A is not None and E is not None:
		for B in A.get('rules')or[]:
			if'policy_status_from_evidence'not in B:B['policy_status_from_evidence']=B.get('policy_status')or'Inferred'
			for J in TRACKS:
				G=(B.get('traffic_light')or{}).get(J)
				if isinstance(G,dict):
					K=cell_result(E.get(cell_key(B['rule_id'],J)),record_id)
					if K is None:G.pop('ingest_result',None)
					else:G['ingest_result']=K
			B['policy_status']=_rule_policy_status(B,E,C)
		if F is not None:
			N={A['rule_id']:A for A in A.get('rules')or[]}
			for H in F.get('clauses')or[]:
				L=N.get(H.get('id')or H.get('rule_id'))
				if L is not None:H['policy_status']=L['policy_status']
	return C
def surfaces(st):A=st;return{'word_header':A['label'],'workspace':{'label_now':A['label'],'approved_count':A['approved_count'],'positions_count':A['positions_count']},'chat_first_line':A['label'],'gate':A['label'],'model':A['label']}
def record_cells_for(model,model_path=None):
	C=model_path;B=_latest_record(model)
	if not B or not B.get('record'):return{}
	A=B['record']
	if not os.path.isabs(A):
		if not C:return{}
		A=os.path.join(os.path.dirname(os.path.abspath(C)),A)
	if not os.path.exists(A):return{}
	from playbook import ingest_approval as D
	with io.open(A,encoding='utf-8')as E:return D.record_cells(json.load(E))
def gate_status(model,model_path=None,lang=None):A=model;return derive_status(A,record_cells_for(A,model_path),lang=lang)
def label_gap(model,model_path=None,core=None,index_entry=None):
	D=model;A=gate_status(D,model_path);B={}
	for(E,C)in(('model',D),('core',core),('index',index_entry)):
		if isinstance(C,dict)and C.get(LABEL_FIELD):B[E]=C.get(LABEL_FIELD)
	return{'label':A['label'],'playbook_status':A['playbook_status'],'stored':B,'mismatch':sorted(B for(B,C)in B.items()if C!=A['label'])}
def check_consistency(model,core=None,index_entry=None,cells=None,word_path=None,workspace_path=None):
	L=workspace_path;K=word_path;E=cells;A=model;F=derive_status(A,E);B=[];M=[('model',A),('core',core),('index',index_entry)]
	if isinstance(A.get('handoff'),dict):M.append(('handoff',A['handoff']))
	for(N,G)in M:
		if G is None:continue
		for O in DUAL_FIELDS:
			if O in G:B.append('%s.%s: שדה תווית כפול. התווית היחידה היא status_label'%(N,O))
		for(H,C)in(('playbook_status',F['playbook_status']),(LABEL_FIELD,F['label'])):
			if H in G and G.get(H)!=C:B.append('%s.%s="%s", המחושב: "%s"'%(N,H,G.get(H),C))
	if E is not None:
		for D in A.get('rules')or[]:
			for P in TRACKS:
				S=(D.get('traffic_light')or{}).get(P)or{};Q=cell_key(D['rule_id'],P);I,C=S.get('ingest_result'),E.get(Q)
				if C is None:continue
				if not I or I.get('status')!=C.get('status')or bool(I.get('policy_claim'))!=bool(C.get('policy_claim'))or bool(I.get('simulated'))!=bool(C.get('simulated')):B.append('%s: ingest_result במודל אינו התא שברשומה הנוכחית'%Q)
			if D.get('policy_status')!=_rule_policy_status(D,E,F):B.append('%s.policy_status="%s", המחושב: "%s"'%(D['rule_id'],D.get('policy_status'),_rule_policy_status(D,E,F)))
	for R in open_decisive(A):
		J=R.get('rule_id')
		if J and any(cell_counts((E or{}).get(cell_key(J,A)))for A in TRACKS):B.append('%s: שאלה מכריעה פתוחה (%s) בכלל שתאיו נחתמו. הבחירה בגיליון לא נרשמה'%(J,R.get('id')))
	if K or L:from playbook import surfaces_render as T;B+=T.check_surfaces(F,word_path=K,workspace_path=L,model=A)
	return B
