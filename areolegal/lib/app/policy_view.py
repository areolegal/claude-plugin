# -*- coding: utf-8 -*-
# Copyright (c) Areo. All rights reserved. Licensed under the terms at https://areo.co.il/legal/terms
import io,json,os,re,sys
from pathlib import Path
from typing import Optional
_LIB=Path(__file__).resolve().parents[1]
if str(_LIB)not in sys.path:sys.path.insert(0,str(_LIB))
from playbook import status as S
TRACKS='green','yellow','red'
MARKER='/*__AREO_POLICY__*/null'
TEMPLATE=_LIB.parent/'ui'/'app'/'policy.html'
PROFILE_NAME='פרופיל-לקוח.json'
AREO_BASES='areo_proposal','market_standard'
IMPORTANCE='critical','high','medium','low'
DRAFT_ROLES='draft',
SIGNED_ROLES='signed','agreement','amendment'
TEMPLATE_ROLES='template','form'
def _warn(msg):sys.stderr.write('policy_view: %s\n'%msg)
def _read_json(path):
	try:
		with io.open(str(path),encoding='utf-8')as A:return json.load(A)
	except(OSError,ValueError)as B:_warn('לא נקרא %s (%s)'%(path,B));return
def _pick(d,*B):
	if not isinstance(d,dict):return
	for C in B:
		A=d.get(C)
		if A not in(None,'',[],{}):return A
def _s(v):return v.strip()if isinstance(v,str)else''if v is None else str(v)
def _strs(v):
	if isinstance(v,list):return[_s(A)for A in v if _s(A)]
	if isinstance(v,str)and v.strip():return[v.strip()]
	return[]
def _clause(pc):
	if isinstance(pc,dict):return _s(pc.get('he'))or _s(pc.get('en'))
	return _s(pc)
def _scrubber(model):
	A=_LIB.parent/'skills'/'contract-playbook-builder'/'scripts'
	try:
		if str(A)not in sys.path:sys.path.append(str(A))
		import voice_scrub as B;C=B.Scrubber(model,'he');return C.text
	except Exception:return lambda t:t
def find_models(data_dir):
	A=data_dir;A=Path(A);G,H=[],set()
	def C(entry,mp):
		try:A=os.path.normcase(str(Path(mp).resolve()))
		except OSError:A=str(mp)
		if A in H or not Path(mp).is_file():return
		H.add(A);G.append((entry or{},Path(mp)))
	I=A/'playbooks'/'index.json'
	if I.is_file():
		D=_read_json(I);L=D.get('playbooks')if isinstance(D,dict)else D
		for B in L or[]:
			if not isinstance(B,dict):continue
			E=_pick(B,'core_path','model_path','path')
			if not E:continue
			J=A/os.path.dirname(str(E).replace('\\','/'))/'playbook-model.json'
			if not J.is_file():_warn('לרשומה %s באינדקס אין playbook-model.json'%(B.get('family_id')or E))
			C(B,J)
	K=A/'playbooks'
	if K.is_dir():
		for F in sorted(K.iterdir(),key=lambda p:p.name):
			if F.is_dir():C({'family_id':F.name},F/'playbook-model.json')
	C({'legacy':True},A/'playbook-model.json');return G
def _cells(model,model_path):
	D=model;A={}
	try:A=S.record_cells_for(D,str(model_path))or{}
	except Exception:A={}
	if A:return A
	for B in D.get('rules')or[]:
		if not isinstance(B,dict)or not B.get('rule_id'):continue
		E=B.get('traffic_light')or{}
		for C in TRACKS:
			F=(E.get(C)or{}).get('ingest_result')if isinstance(E.get(C),dict)else None
			if isinstance(F,dict):A[S.cell_key(B['rule_id'],C)]=F
	return A
def _legal_open(rule,track):
	C=track;D=rule.get('legal_review_required');B=[]
	if D is True:return[{'q':'','refs':[]}]
	for A in D if isinstance(D,list)else[]:
		if isinstance(A,str)and A==C:B.append({'q':'','refs':[]});continue
		if not isinstance(A,dict)or A.get('checked_by'):continue
		E=set(_strs(A.get('tracks')))|({A['track']}if A.get('track')else set())
		if E and C not in E:continue
		B.append({'q':_s(A.get('concern')),'refs':_strs(A.get('clause_refs'))})
	if not B and C in _strs(rule.get('legal_review_tracks')):B.append({'q':'','refs':[]})
	return B
def _src_id(ref):return _s(ref).split('#')[0]
def _plain_name(f):A=re.sub('\\.(pdf|docx?|rtf|txt|eml|msg)$','',os.path.basename(_s(f).replace('\\','/')),flags=re.I);return re.sub('^\\d{1,3}[\\s._-]+','',A).strip()
def _sources(model):
	C,D={},0
	for A in model.get('source_log')or[]:
		if not isinstance(A,dict)or A.get('included')is False:continue
		D+=1;E=_s(A.get('source_id'))or'F%d'%D;B=_s(A.get('doc_role'));F='signed'if B in SIGNED_ROLES else'draft'if B in DRAFT_ROLES else'template'if B in TEMPLATE_ROLES else B or'';G=A.get('paper')if A.get('paper')in('ours','theirs')else'';C[E]={'name':_s(_pick(A,'title'))or _plain_name(A.get('file'))or E,'cp':_s(_pick(A,'short_name','counterparty')),'date':_s(_pick(A,'signed_at','date')),'paper':G,'role':_s(A.get('company_role_in_source')),'kind':F}
	return C
def _commercial(model,src):
	B=model.get('commercial')or{};F=[{'key':_s(A.get('key')),'label':_s(A.get('label'))or _s(A.get('key'))}for A in B.get('fields')or[]if isinstance(A,dict)and A.get('key')];C=[]
	for A in B.get('rows')or[]:
		if not isinstance(A,dict)or A.get('found')is False:continue
		D,E=_src_id(_pick(A,'src','source_id')),_s(_pick(A,'he','value','norm'))
		if D in src and E:C.append({'s':D,'f':_s(_pick(A,'field','key')),'v':E})
	return{'fields':F,'rows':C}
def _evidence(rule,track):
	B=[]
	for A in rule.get('evidence')or[]:
		if not isinstance(A,dict)or _s(A.get('track'))!=track:continue
		C=_s(_pick(A,'quote','text'));D=_src_id(_pick(A,'source_ref','source_id'))
		if not C or not D:continue
		B.append({'s':D,'c':_s(_pick(A,'clause_ref','ref')),'q':C,'sd':_s(A.get('side')),'tag':_s(A.get('tag')),'note':_s(A.get('note'))})
	return B
def _steps(obj):
	B=[]
	for A in obj.get('steps')or obj.get('fallback_steps')or[]:
		if isinstance(A,dict)and _pick(A,'text','t','position'):B.append({'t':_s(_pick(A,'text','t','position')),'g':_s(_pick(A,'gives_up','g'))})
		elif isinstance(A,str)and A.strip():B.append({'t':A.strip(),'g':''})
	return B
def _effect(obj):
	A=obj;B=_pick(A,'company_effect')
	if B:return _s(B)
	C=A.get('role_effects')
	if isinstance(C,dict):
		D=[_s(A)for A in C.values()if _s(A)]
		if D:return' '.join(D)
	return _s(_pick(A,'as_discloser_effect','as_recipient_effect'))
def _lane(rule,track,st,cells,rat,sc):
	D=rule;C=sc;B=track;A=(D.get('traffic_light')or{}).get(B)
	if not isinstance(A,dict):return{}
	G=_s(_pick(A,'position','pos','text'))
	if not G:return{}
	H=S.cell_key(D['rule_id'],B);E=H in set(st.get('approved_keys')or());I=cells.get(H)or{};F=_legal_open(D,B);J=A.get('match_criteria')or A.get('crit')or[];return{'p':C(G),'cl':_clause(A.get('proposed_clause')),'fx':C(_effect(A)),'areo':_s(A.get('basis'))in AREO_BASES,'ok':E,'ev':_evidence(D,B),'legal':bool(F),'crit':[C(A)for A in _strs(J)],'why':C(_s(_pick(rat,'%s_boundary_rationale'%B))or _s(A.get('basis_note'))),'signer':_s(I.get('signer'))if E else'','at':_s(I.get('approved_at'))[:10]if E else'','steps':_steps(A)if B=='yellow'else[],'lr':[{'q':C(A['q']),'refs':A['refs']}for A in F if A['q']or A['refs']],'st':'approved'if E else'pending_legal_review'if F else'pending'}
def _rule(r,ids,st,cells,sc):
	A=sc;D=r['rule_id'];E=r.get('policy_rationale')if isinstance(r.get('policy_rationale'),dict)else{};I=r.get('company_perspective')if isinstance(r.get('company_perspective'),dict)else{};J=_s(_pick(r,'topic_name','topic'))or _s(r.get('clause_issue'))or D;G=_s(r.get('clause_issue'));K=_s(r.get('importance')).lower();H=r.get('presence_rule');L=[]
	for B in r.get('related_clause_impacts')or r.get('related_clauses')or[]:
		if not isinstance(B,dict):continue
		F=_s(_pick(B,'related_rule_id','rule_id','ref'));M=_s(_pick(B,'impact','relation','effect'))
		if not F or F==D or F not in ids or not M:continue
		C=[A for A in B.get('evidence')or[]if isinstance(A,dict)and _s(A.get('quote'))];N=_s(B.get('direction'));O={'id':F,'dir':N if N in('affects','affected_by','mutual')else'mutual','basis':'areo'if B.get('basis')=='areo_proposal'or not C else'corpus','why':A(M),'act':A(_s(B.get('action')))}
		if C:O['q']={'c':_s(C[0].get('clause_ref')),'n':int(C[0].get('count')or 1),'t':_s(C[0].get('quote'))}
		L.append(O)
	return{'id':D,'t':J,'sub':G if G and G!=J else'','imp':K if K in IMPORTANCE else'','kind':_s(r.get('clause_kind')),'req':_s(H.get('requirement'))if isinstance(H,dict)else _s(H),'why':A(_s(r.get('why_address_topic'))),'cp':A(_s(r.get('counterparty_objective'))),'rat':A(_s(E.get('executive_policy_rationale'))),'legal':A(_s(_pick(E,'legal_risk_and_legal_framework'))or _s(I.get('legal_analysis'))),'biz':A(_s(_pick(E,'business_operational_impact'))or _s(I.get('business_analysis'))),'rel':[A for A in _strs(r.get('related_rule_ids'))if A!=D and A in ids],'relx':L,'L':{B:_lane(r,B,st,cells,E,A)for B in TRACKS}}
def _segments(model,ids,st,sc):
	G=model;I=G.get('segmentation_model')or{};H,D=[],{}
	for B in I.get('segments')or[]:
		if not isinstance(B,dict):continue
		C=_s(_pick(B,'segment_id','id'))
		if not C:continue
		J=_s(_pick(B,'origin','defined_by')).lower();E={'id':C,'name':_s(_pick(B,'segment_name','label','name'))or C,'how':sc(_s(_pick(B,'criteria','criterion','applies_when'))),'origin':'user'if J in('user','client','lawyer')else'areo','key':'','topics':[]};H.append(E);D[C]=E
		for A in B.get('variants')or[]:
			if isinstance(A,dict):_seg_topic(E,_s(A.get('rule_id')),A,ids,st,sc)
	for F in G.get('rules')or[]:
		if not isinstance(F,dict):continue
		for A in F.get('segment_variants')or[]:
			if isinstance(A,dict)and _s(A.get('segment_id'))in D:_seg_topic(D[_s(A['segment_id'])],_s(F.get('rule_id')),A,ids,st,sc)
	return H
def _seg_topic(g,rid,v,ids,st,sc):
	A=rid
	if A not in ids or any(B['rid']==A for B in g['topics']):return
	B=v.get('traffic_light')or{};C={}
	for D in('green','red'):
		E=_s(_pick(B.get(D)or{},'position','pos'))
		if E:C[D]={'p':sc(E)}
	F=[S.cell_key(A,C,g['id'])for C in TRACKS if isinstance(B.get(C),dict)];G=bool(F)and all(A in set(st.get('approved_keys')or())for A in F);g['topics'].append({'rid':A,'note':sc(_s(_pick(v,'applies_when','segmentation_rationale'))),'L':C or None,'ok':G})
def _company(model,profile):A=model;B=A.get('company');return _s(_pick(A,'company_name')or(B if isinstance(B,str)else _pick(B or{},'name'))or _pick(A.get('meta')or{},'company_name','company')or _pick(profile or{},'organization_name'))
def _approver(profile,st):
	A=(profile or{}).get('branding')or{}
	for B in A.get('signatories')or[]:
		if isinstance(B,dict)and _s(B.get('name')):return{'name':_s(B.get('name')),'role':_s(B.get('role'))}
	if _s(A.get('lawyer_name')):return{'name':_s(A.get('lawyer_name')),'role':_s(A.get('lawyer_role'))}
	C=_s(st.get('approved_by')).split(';')[0]
	if C:D=[A.strip()for A in C.split(',')];return{'name':D[0],'role':', '.join(D[1:])}
def _questions(model,sc):
	B=[]
	for A in model.get('validation_queue')or[]:
		if not isinstance(A,dict)or A.get('answered')or _s(A.get('status')).lower()=='closed':continue
		C,D=_s(_pick(A,'topic','issue')),_s(A.get('question'))
		if C or D:B.append({'t':sc(C),'q':sc(D),'rec':sc(_s(_pick(A,'recommendation','rec')))})
	return B
def _cov(model):B=model.get('coverage')or{};A=lambda k:B.get(k)if isinstance(B.get(k),int)else 0;return{'units':A('units'),'topic':A('topic_units'),'tech':A('technical_units'),'by':[]}
def book_data(model,model_path,profile=None):E=profile;A=model;C=_scrubber(A);F=[A for A in A.get('rules')or[]if isinstance(A,dict)and A.get('rule_id')];G={A['rule_id']for A in F};H=_cells(A,model_path);B=S.derive_status(A,H,lang='he');D=A.get('scope_summary')or{};I=(D.get('contract_families')or[{}])[0]or{};M=D.get('corpus_basis')or A.get('corpus_basis')or{};J=_s(M.get('band'));K=_sources(A);L=A.get('segmentation_model')or{};return{'company':_company(A,E),'family':_s(_pick(I,'contract_family_name','label')),'side':_s(_pick(I,'company_role')),'docs':S.company_agreements_counted(A),'date':_s(_pick(A,'last_updated','generated_at'))[:10],'approver':_approver(E,B),'deal':C(_s(D.get('deal_description')))if isinstance(D.get('deal_description'),str)else'','suff':'thin'if J in('below7','below20','none')else'ok'if J else'','limits':[C(A)for A in _strs(D.get('limitations'))],'notObserved':[C(A)for A in _strs((A.get('applicability')or{}).get('not_covered'))],'seg':{'status':_s(L.get('status')),'checked':[C(A)for A in _strs(L.get('dimensions'))]},'segs':_segments(A,G,B,C),'qs':_questions(A,C),'cov':_cov(A),'status':{'label':B['label'],'approved':B['approved_count'],'total':B['positions_count'],'open_questions':list(B.get('open_questions')or[])},'src':K,'com':_commercial(A,K),'rules':[_rule(A,G,B,H,C)for A in F]},B
def _type_of(key,entry,model):
	A=_pick(entry or{},'family_type','contract_type','type')or _pick(model,'contract_type','family_type')
	if A:return _s(A)
	B=re.match('^fam_(.+)_[^_]+$',key);return B.group(1)if B else key
def page_data(data_dir):
	E=data_dir;E=Path(E);I=_read_json(E/PROFILE_NAME)if(E/PROFILE_NAME).is_file()else None;C,J=[],set()
	for(F,G)in find_models(E):
		A=_read_json(G)
		if not isinstance(A,dict)or not isinstance(A.get('rules'),list):_warn('%s אינו מודל פלייבוק, ולא נכלל'%G);continue
		L=((A.get('scope_summary')or{}).get('contract_families')or[{}])[0]or{};B=_s(_pick(A,'family_id')or _pick(F,'family_id')or _pick(L,'contract_family_id')or _pick(A,'playbook_id'))or G.parent.name or'playbook';M,H=B,2
		while B in J:B,H='%s_%d'%(M,H),H+1
		J.add(B);D,K=book_data(A,G,I);C.append({'key':B,'type':_type_of(B,F,A),'label':D['family']or _s(_pick(F,'family_name','label'))or B,'family':D['family'],'side':D['side']or _s(_pick(F,'company_role')),'status':K['playbook_status'],'status_label':K['label'],'updated':D['date'],'rules':len(D['rules']),'legacy':bool(F.get('legacy')),'built':True,'data':D})
	N=max(C,key=lambda b:b['updated'])['key']if C else None;return{'company':C[0]['data']['company']if C else _s(_pick(I or{},'organization_name')),'current':N,'books':C}
def to_js(obj):A=json.dumps(obj,ensure_ascii=False,separators=(',',':'));return A.replace('</','<\\/').replace('<!--','<\\!--').replace('\u2028','\\u2028').replace('\u2029','\\u2029')
def render_data(data,out_html,template=None):
	B=template;A=out_html;C=Path(B)if B else TEMPLATE;D=C.read_text(encoding='utf-8')
	if D.count(MARKER)!=1:raise ValueError('התבנית %s אינה מכילה את %s פעם אחת'%(C,MARKER))
	A=Path(A);A.parent.mkdir(parents=True,exist_ok=True);A.write_text(D.replace(MARKER,to_js(data)),encoding='utf-8');return A
def render(data_dir,out_html,template=None):return render_data(page_data(Path(data_dir)),out_html,template)
def main(argv=None):
	import argparse as F;sys.dont_write_bytecode=True;A=F.ArgumentParser(description='מסך המדיניות של Areo, מכל הפלייבוקים שבתיקיית Areo-נתונים');A.add_argument('--data-dir',required=True,help='תיקיית Areo-נתונים');A.add_argument('--out',required=True,help='קובץ ה-HTML שנכתב');A.add_argument('--template',help='תבנית אחרת (ברירת מחדל: ui/app/policy.html)');B=A.parse_args(argv);C,D=Path(B.data_dir),Path(B.out)
	if not C.is_dir():sys.stderr.write('אין תיקייה %s\n'%C);return 2
	if D.suffix.lower()not in('.html','.htm'):sys.stderr.write('--out צריך להיות קובץ .html\n');return 2
	from common.cli import guard_out as G,OutputRefused as H
	try:G(str(D),inputs=[str(A)for(B,A)in find_models(C)])
	except H as I:sys.stderr.write('refused: %s\n'%I);return 2
	E=page_data(C);render_data(E,D,Path(B.template)if B.template else None);print('נכתב %s: %d פלייבוקים%s'%(D,len(E['books']),''.join('\n  %s%s (%d נושאים)'%('* 'if A['key']==E['current']else'  ',A['label'],A['rules'])for A in E['books'])));return 0
if __name__=='__main__':sys.exit(main())
