# -*- coding: utf-8 -*-
# Copyright (c) Areo. All rights reserved. Licensed under the terms at https://areo.co.il/legal/terms
import argparse,base64,hashlib,json,os,re,sys
from pathlib import Path
LIB=Path(__file__).resolve().parents[1]
if str(LIB)not in sys.path:sys.path.insert(0,str(LIB))
SCRIPTS=LIB.parent/'skills'/'contract-negotiation-orchestrator'/'scripts'
import common.docx_tracked as dt
TEMPLATE=LIB.parent/'ui'/'app'/'nego.html'
MARKER='/*__AREO_NEGO__*/null'
PROFILE='פרופיל-לקוח.json'
DOCX_EMBED_LIMIT=12582912
DECISIONS_RX=re.compile('^decisions_round_(\\d+)\\.json$')
HEAD_RX=re.compile('^\\d+[.)]?[\\u200e\\u200f]?\\s*\\S')
SUB_RX=re.compile('^\\d+\\.\\d+')
TITLE_STYLE=re.compile('title|כותרת ראשית',re.I)
HEAD_STYLE=re.compile('heading|כותרת',re.I)
def _json(path):
	try:
		with open(str(path),encoding='utf-8')as A:return json.load(A)
	except(OSError,ValueError):return
def _s(v):return v.strip()if isinstance(v,str)else''
def _date(iso):A=_s(iso);return A[:10]if re.match('^\\d{4}-\\d{2}-\\d{2}',A)else''
def _labels(path):
	try:
		if str(SCRIPTS)not in sys.path:sys.path.insert(0,str(SCRIPTS))
		import content_checks as A;return A.numbered_labels(str(path))
	except Exception:return
def _style(p):A=p.find(dt.W+'pPr/'+dt.W+'pStyle');return A.get(dt.W+'val')or''if A is not None else''
def read_paras(path):
	Q=dt.document_root(str(path));K=dt.body_paragraphs(Q);L=_labels(path)or[];M,D=[],False;R=next((A for(A,B)in enumerate(K)if dt.para_text(B).strip()),None)
	for(E,G)in enumerate(K):
		N=dt.para_text(G);A=N.strip();O=_style(G);C=G.find(dt.W+'pPr/'+dt.W+'numPr');H=C is not None and(C.find(dt.W+'numId')is None or C.find(dt.W+'numId').get(dt.W+'val')!='0');P=len(A.split())
		if not A:B='clause'if D else'pre'
		elif E==R and P<=12 and not HEAD_RX.match(A)and not H:B='title'
		elif TITLE_STYLE.search(O)and not D:B='title'
		elif HEAD_STYLE.search(O)or P<=6 and not A.endswith(('.',':',';',','))and not SUB_RX.match(A)and not re.search('\\s{3,}|\\t',A):B='head'
		elif HEAD_RX.match(A)or H or D:B='clause'
		else:B='pre'
		if B in('head','clause'):D=True
		I={'i':E,'t':N,'k':B};J=L[E]if E<len(L)else None
		if J and H and not A.startswith(str(J)):
			I['n']=str(J);F=C.find(dt.W+'ilvl')if C is not None else None
			if F is not None and(F.get(dt.W+'val')or'0').isdigit()and int(F.get(dt.W+'val'))>0:I['lv']=int(F.get(dt.W+'val'))
		M.append(I)
	return M
def _cell(r,track):A=track;B=r.get('traffic_light')if isinstance(r.get('traffic_light'),dict)else{};C=B.get(A)if isinstance(B.get(A),dict)else r.get(A);return C if isinstance(C,dict)else{}
def _wording(v):
	if isinstance(v,dict):return _s(v.get('text')or v.get('he')or v.get('wording'))
	return _s(v)
def rule_view(r):A,B,D=_cell(r,'green'),_cell(r,'yellow'),_cell(r,'red');C=[_wording(A)for A in B.get('fallback_steps')or r.get('fallback_steps')or[]];E=_wording(B.get('fallback_wording')or r.get('fallback_wording'))or _wording((B.get('proposed_clause')or{}).get('he')if isinstance(B.get('proposed_clause'),dict)else'');C=[A for A in([E]if E else[])+C if A];return{'id':r.get('id')or r.get('rule_id'),'title':_s(r.get('title')or r.get('topic_name')or r.get('topic'))or str(r.get('id')or r.get('rule_id')),'issue':_s(r.get('clause_issue')or r.get('issue')),'importance':_s(r.get('importance')),'green':_s(A.get('position')),'green_w':_wording(A.get('preferred_wording')or r.get('preferred_wording'))or _wording((A.get('proposed_clause')or{}).get('he')if isinstance(A.get('proposed_clause'),dict)else''),'yellow':_s(B.get('position')),'yellow_steps':list(dict.fromkeys(C)),'red':_s(D.get('position')or D.get('red_line')or r.get('red_line')),'basis':_s(A.get('label')or r.get('source_label'))}
def _find(rel,data_dir,deal_dir):
	B=rel;B=_s(B)
	if not B:return
	A=Path(B)
	if A.is_absolute():return A if A.is_file()else None
	for C in(data_dir,deal_dir):
		if(C/A).is_file():return C/A
def load_playbook(state,data_dir,deal_dir,notes,tag):
	E=tag;D=notes;B=state;J=B.get('playbook_resolution')if isinstance(B.get('playbook_resolution'),dict)else{};K=B.get('positions_source')if isinstance(B.get('positions_source'),dict)else{};F=B.get('playbook_source')or J.get('chosen')or K.get('document')
	if not _s(F):return[],'',''
	A=_find(F,data_dir,deal_dir)
	if A is None:D.append('%s: הפלייבוק %s לא נמצא, ולכן הדף בלי עמדות המדיניות'%(E,F));return[],'',''
	if A.suffix.lower()!='.json':D.append('%s: הפלייבוק %s אינו קובץ JSON של Areo, ולכן הדף בלי עמדות המדיניות'%(E,A.name));return[],'',''
	C=_json(A.parent/'playbook-core.json')if A.name!='playbook-core.json'else _json(A);H=_json(A.parent/'playbook-model.json')if A.name!='playbook-model.json'else _json(A);G=C if isinstance(C,dict)and(C.get('clauses')or C.get('rules'))else H
	if not isinstance(G,dict):D.append('%s: הפלייבוק %s אינו קריא'%(E,A.name));return[],'',''
	L=[rule_view(A)for A in G.get('clauses')or G.get('rules')or[]if isinstance(A,dict)and(A.get('id')or A.get('rule_id'))];I=[A for A in(C,H)if isinstance(A,dict)];M=next((_s(A.get(B))for A in I for B in('presentation_label','family_label')if _s(A.get(B))),'');N=next((_s(A.get('status_label'))for A in I if _s(A.get('status_label'))),'');return L,M,N
def merge_coverage(rules,cov):
	D={A.get('rule_id'):A for A in(cov or{}).get('rules')or[]if isinstance(A,dict)and A.get('rule_id')};B=[]
	for C in rules:A=D.pop(C['id'],None);B.append(dict(C,**_cov(A))if A else C)
	for(E,A)in D.items():B.append(dict({'id':E,'title':_s(A.get('topic'))or E,'issue':'','importance':'','green':_s(A.get('opening')),'green_w':'','yellow':'','yellow_steps':[_s(A)for A in A.get('allowed_fallbacks')or[]if _s(A)],'red':'','basis':''},**_cov(A)))
	return B
def _cov(e):
	E=[]
	for B in e.get('locations')or[]:
		C=B.get('para')if isinstance(B,dict)else B
		if isinstance(C,int)and not isinstance(C,bool):E.append(C)
	A={'paras':E}
	if isinstance(e.get('applies'),bool):A['applies']=e['applies']
	for D in('action','result'):
		if _s(e.get(D)):A[D]=_s(e[D])
	F=_s(e.get('result_reason')or e.get('applies_reason'))
	if F:A['reason']=F
	return A
def _sha(path):
	A=hashlib.sha256()
	with open(str(path),'rb')as B:
		for C in iter(lambda:B.read(1<<20),b''):A.update(C)
	return A.hexdigest()
def received_file(deal_dir,states,n,want_sha):
	F=deal_dir;D=want_sha;G=[]
	for I in states:
		for A in(I.get('meta')or{}).get('received_documents')or[]:
			if isinstance(A,dict)and A.get('round')==n:
				C=_s(A.get('file_name')or A.get('path')or A.get('file'))
				if C and C not in[A[0]for A in G]:G.append((C,_s(A.get('sha256')),A))
	E=[]
	for(C,H,A)in G:
		B=F/C if not Path(C).is_absolute()else Path(C)
		if not B.is_file():B=F/Path(C).name
		if B.is_file():E.append((B,H,A))
	if D:
		for(B,H,A)in E:
			if H==D or _sha(B)==D:return B,A
	if E:return E[-1][0],E[-1][2]
	if D and re.match('^[0-9a-f]{64}$',D):
		for B in sorted(F.glob('*.docx')):
			if _sha(B)==D:return B,{}
	return None,{}
_DRAFT_WORDS=re.compile('\\b(?:טיוטה|טיוטת|draft|redline|markup|final|v\\d+)\\b|\\d{1,2}[.\\-]\\d{1,2}[.\\-]\\d{2,4}',re.I)
def _name_from_received(meta):
	for B in reversed(meta.get('received_documents')or[]):
		C=_s((B or{}).get('file_name'))if isinstance(B,dict)else''
		if not C:continue
		E=re.sub('\\.[A-Za-z0-9]{2,5}$','',C.replace('\\','/').rsplit('/',1)[-1]);D=[A.strip()for A in re.split('\\s+[-\\u2013\\u2014]\\s+',E)if A.strip()];A=[_DRAFT_WORDS.sub(' ',A).strip(' -_,')for A in D];A=[re.sub('\\s+',' ',A)for A in A if len(A)>=2]
		if len(D)>1 and A:return A[-1]
	return''
def _paper(pos,counterparty):
	B=counterparty;A=_s(pos.get('paper_origin'))
	if A=='theirs':return'הנייר של '+B if B else'הנייר של הצד השני'
	if A=='ours':return'הנייר שלכם'
	if A=='template':return'תבנית'
	return''
def _ask(v):
	if isinstance(v,dict):A=_s(v.get('gap')or v.get('question'));return dict(v,gap=A)if A else None
	return{'gap':_s(v)}if _s(v)else None
def decision_view(x,rules_by_id,conc_by_ref):
	C=rules_by_id;A=dict(x);D=[A for A in A.get('rule_ids')or[]if isinstance(A,str)]
	if not _s(A.get('topic')):A['topic']=next((C[A]['title']for A in D if A in C),'')
	if not _s(A.get('summary')):A['summary']=_s(A.get('plain_effect'))
	A['ask']=_ask(A.get('ask'));B=conc_by_ref.get(A.get('id'))
	if B is not None and not _s(A.get('concession')):A['concession']=_s(B.get('reason')or B.get('topic'))or'ויתור מכוון'
	if'lawyer'not in A:A['lawyer']=bool(A.get('concession'))or A.get('position_basis')=='proposed_unapproved'or A.get('source_label')=='areo_proposal'and not D
	return A
def verify_view(deal_dir,n,doc):
	D=[A for A in doc.get('verify_resolutions')or[]if isinstance(A,dict)];G=_json(deal_dir/'runs'/('round-%d'%n)/'verify.json');C,E=[],set()
	for A in(G or{}).get('findings')or[]:
		if not isinstance(A,dict):continue
		H=str(A.get('check')),_s(A.get('where'));B=next((A for A in D if(str(A.get('check')),_s(A.get('where')))==H),None)
		if B is not None:E.add(id(B))
		F={B:A.get(B)for B in('check','severity','where','quote','issue','suggest')if A.get(B)is not None}
		if B is not None:F.update({'resolution':B.get('resolution')or'','note':B.get('note')or''})
		C.append(F)
	C+=[{B:A.get(B)for B in('check','where','resolution','note')}for A in D if id(A)not in E];return C
def _state_for(states_by_round,live,n):
	A=states_by_round
	if n in A:return A[n]
	if(live.get('meta')or{}).get('round_number')==n:return live
def deal_view(deal_dir,data_dir,profile,notes):
	Z=profile;G=deal_dir;D=notes;C=G.name;H=_json(G/'negotiation_state.json')
	if not isinstance(H,dict):H={}
	L={}
	for R in sorted(G.glob('negotiation_state_round_*.json')):
		B=_json(R)
		if isinstance(B,dict)and isinstance((B.get('meta')or{}).get('round_number'),int):L[B['meta']['round_number']]=B
	E=H.get('meta')if isinstance(H.get('meta'),dict)else{};T=E.get('position')if isinstance(E.get('position'),dict)else{};a=_s(E.get('transaction_id'))or C;b=_s(E.get('counterparty_name'))or _name_from_received(E);S={}
	for R in G.iterdir():
		I=DECISIONS_RX.match(R.name)
		if I:S[int(I.group(1))]=R
	U=set(S)
	for B in[H]+list(L.values()):
		I=B.get('meta')or{}
		if isinstance(I.get('round_number'),int):U.add(I['round_number'])
		for M in I.get('received_documents')or[]:
			if isinstance(M,dict)and isinstance(M.get('round'),int):U.add(M['round'])
	V,h,i=load_playbook(H,data_dir,G,D,C);W=_json(G/'rule-coverage.json');j=[H]+[L[A]for A in sorted(L)];N,X=[],''
	for A in sorted(U):
		if A not in S:D.append('%s: סבב %d בלי קובץ הכרעות (decisions_round_%d.json), ולכן אינו מוצג'%(C,A,A));continue
		J=_json(S[A])
		if not isinstance(J,dict)or not isinstance(J.get('decisions'),list):D.append('%s: קובץ ההכרעות של סבב %d אינו קריא, ולכן הסבב אינו מוצג'%(C,A));continue
		O,M=received_file(G,j,A,_s(J.get('received_sha256')))
		if O is None:D.append('%s: הטיוטה שהתקבלה בסבב %d לא נמצאה בתיקייה, ולכן הסבב אינו מוצג'%(C,A));continue
		try:Y=read_paras(O)
		except Exception as k:D.append('%s: הטיוטה של סבב %d (%s) אינה קריאה: %s'%(C,A,O.name,type(k).__name__));continue
		B=_state_for(L,H,A)or{};c=[A for A in B.get('deliberate_concessions')or[]if isinstance(A,dict)];l={A.get('clause_ref'):A for A in c if A.get('clause_ref')};m={A['id']:A for A in V};d=[decision_view(A,m,l)for A in J['decisions']if isinstance(A,dict)]
		for F in d:
			P=F.get('para')if F.get('op')!='insert_paragraph'else F.get('after_para')
			if not isinstance(P,int)or not 0<=P<len(Y):D.append('%s: סבב %d, הכרעה %s מפנה לפסקה %r שאינה בטיוטה'%(C,A,F.get('id'),P))
			elif F.get('old')and F.get('op')!='insert_paragraph'and F['old']not in Y[P]['t']:D.append('%s: סבב %d, הכרעה %s: הנוסח "%s" אינו בפסקה %d'%(C,A,F.get('id'),F['old'][:40],P))
		Q=B.get('meta')or{};e=Q.get('playbook_map')if isinstance(Q.get('playbook_map'),dict)else{};n=[{'para':A.get('para'),'notice':A.get('notice')or''}for A in e.get('unmatched_agreement_clauses')or[]if isinstance(A,dict)]if e.get('round')in(None,A)else[];f=[B for B in Q.get('sent_documents')or E.get('sent_documents')or[]if isinstance(B,dict)and B.get('round')==A and _s(B.get('sent_at'))];X=_s(J.get('author'))or X;N.append({'n':A,'received':_date(M.get('received_at')),'received_file':O.name,'paper':_paper(Q.get('position')or T if isinstance(Q.get('position')or T,dict)else{},b),'playbook':h,'playbook_status':i,'strategy':_s(B.get('strategy_summary')),'open_items':[A for A in B.get('open_items')or[]if isinstance(A,dict)and _s(A.get('item'))],'concessions':[dict(A,topic=_s(A.get('topic')),reason=_s(A.get('reason')))for A in c],'unmatched':n,'verify':verify_view(G,A,J),'sent_at':_date(f[-1].get('sent_at'))if f else'','paras':Y,'decisions':d,'rules':V,'files':{},'_src':O})
	if not N:D.append('%s: אין סבב עם הכרעות, ולכן העסקה אינה מוצגת'%C);return
	K=N[-1]
	if W and isinstance(W,dict):K['rules']=merge_coverage(V,W)
	g=K['_src'].stat().st_size
	if g<=DOCX_EMBED_LIMIT:K['docx_b64']=base64.b64encode(K['_src'].read_bytes()).decode('ascii')
	else:D.append('%s: הטיוטה של סבב %d גדולה מדי להטמעה (%d MB), והדף בלי תצוגת Word'%(C,K['n'],g>>20))
	for o in N:o.pop('_src',None)
	return{'id':a,'company':_s(E.get('client_name'))or _company(Z),'counterparty':b or a,'type':_s(E.get('contract_type')),'role':_s(T.get('our_side_in_agreement'))or _s(E.get('our_role')),'paper':K['paper'],'author':X or _s((Z or{}).get('lawyer_name')),'rounds':N}
def _company(profile):A=profile or{};return _s(A.get('organization_name')or A.get('organization_name_en')or A.get('company_name'))
def page_data(data_dir):
	A=data_dir;A=Path(A);C=[];B=_json(A/PROFILE);B=B if isinstance(B,dict)else{};D=[];F=A/'transactions'
	if F.is_dir():
		for G in sorted(A for A in F.iterdir()if A.is_dir()):
			try:E=deal_view(G,A,B,C)
			except Exception as H:C.append('%s: לא נקראה (%s)'%(G.name,type(H).__name__));E=None
			if E:D.append(E)
	I=_company(B)or next((A['company']for A in D if A.get('company')),'');return{'company':I,'deals':D,'signed':[],'notes':C}
def inject(html,payload):
	A=json.dumps(payload,ensure_ascii=False,separators=(',',':'));A=A.replace('</','<\\/').replace('<!--','<\\!--').replace('\u2028','\\u2028').replace('\u2029','\\u2029')
	if html.count(MARKER)!=1:raise ValueError('התבנית אינה מכילה את הסימן %s פעם אחת בדיוק'%MARKER)
	return html.replace(MARKER,A)
def render(data_dir,out_html,template=None):B=template;C=page_data(data_dir);E=Path(B)if B else TEMPLATE;F=inject(E.read_text(encoding='utf-8'),{A:B for(A,B)in C.items()if A!='notes'});A=Path(out_html);A.parent.mkdir(parents=True,exist_ok=True);D=A.with_name(A.name+'.tmp');D.write_text(F,encoding='utf-8');os.replace(str(D),str(A));return C
def main(argv=None):
	B=argparse.ArgumentParser(description='דף המשא ומתן מהנתונים שב-Areo-נתונים');B.add_argument('--data-dir',required=True,help='תיקיית Areo-נתונים');B.add_argument('--out',required=True,help='קובץ ה-HTML לכתיבה');B.add_argument('--template',help='תבנית אחרת (ברירת המחדל: ui/app/nego.html)');A=B.parse_args(argv)
	for D in(sys.stdout,sys.stderr):
		try:D.reconfigure(encoding='utf-8',errors='replace')
		except(AttributeError,ValueError):pass
	if not Path(A.data_dir).is_dir():print('התיקייה אינה קיימת: %s'%A.data_dir);return 2
	C=render(Path(A.data_dir),Path(A.out),A.template);print('נכתב %s: %d עסקאות, %d סבבים'%(A.out,len(C['deals']),sum(len(A['rounds'])for A in C['deals'])))
	for E in C['notes']:print('  '+E)
	return 0
if __name__=='__main__':sys.exit(main())
