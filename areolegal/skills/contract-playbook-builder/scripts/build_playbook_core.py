#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (c) Areo. All rights reserved. Licensed under the terms at https://areo.co.il/legal/terms
'בונה את גרעין ההפעלה (playbook-core.json) מהמודל, בקוד.'
import argparse,datetime as _dt,hashlib,io,json,os,sys
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
try:import areo_lib;from playbook import status as S
except ImportError:S=None
try:from playbook import validate_model as VM
except ImportError:VM=None
try:from common.cli import OutputRefused,guard_out
except ImportError:
	class OutputRefused(Exception):0
	def guard_out(out,inputs=()):
		A=out;B=os.path.normcase(os.path.realpath(A))
		if any(A and os.path.normcase(os.path.realpath(A))==B for A in inputs):raise OutputRefused('--out הוא קובץ קלט: %s'%A)
		return os.path.abspath(A)
TRACKS='green','yellow','red'
TECHNICAL_TOPICS=('signature_block','בלוק חתימה'),('party_identification','זיהוי הצדדים'),('notice_addresses','כתובות להודעות'),('counterparts_esignature','עותקים וחתימה אלקטרונית'),('headings','כותרות לנוחות'),('interpretation_grammar','כללי לשון'),('recitals_descriptive','מבוא תיאורי'),('neutral_definition','הגדרה שאינה משנה היקף'),('bank_details','פרטי חשבון בנק'),('delivery_points_list','רשימת נקודות אספקה'),('admin_form_fields','שדות מנהליים בטופס'),('statutory_admin_restatement','חזרה על חובה מנהלית שבחוק')
MARKET_OR_AREO='market_standard','areo_proposal'
CORE_SCHEMA='2.0'
def text_of(v):
	if isinstance(v,dict):
		for A in('he','text','en'):
			if isinstance(v.get(A),str)and v[A].strip():return v[A]
		return''
	return v if isinstance(v,str)else''
def fallback_source(yellow):
	A=yellow;C=A.get('fallback_wording');B=C.get('source')if isinstance(C,dict)else None
	if B in MARKET_OR_AREO:return B
	D=[A for A in A.get('basis_refs')or()if isinstance(A,str)and A.strip()]
	if D:return D[0]
	if A.get('basis')in MARKET_OR_AREO:return A['basis']
	return B or'areo_proposal'
def block(track,cell,sources=None):
	D=sources;C=track;A=cell;B={'position':A.get('position')or'','basis':A.get('basis')or'','label':A.get('label')or''}
	if A.get('basis_refs'):B['basis_refs']=[str(A)for A in A['basis_refs']if str(A).strip()]
	if D:B['sources']=[{A:B for(A,B)in A.items()if A in('agreement','clause','evidence_id')}for A in D]
	if A.get('source_label'):B['source_label']=A['source_label']
	if A.get('market_source_ids'):B['source_ids']=list(A['market_source_ids'])
	if C=='green':B['preferred_wording']=text_of(A.get('proposed_clause'))
	elif C=='yellow':
		B['fallback_wording']=text_of(A.get('fallback_wording'))or text_of(A.get('proposed_clause'));B['fallback_source']=fallback_source(A);B['fallback_steps']=[text_of(A)for A in A.get('fallback_steps')or()if text_of(A)]
		if A.get('fallback_steps_note'):B['fallback_steps_note']=A['fallback_steps_note']
	else:
		B['red_line']=A.get('position')or''
		if text_of(A.get('proposed_clause')):B['remedy_wording']=text_of(A.get('proposed_clause'))
	return B
def legal_review(rule):
	A=rule.get('legal_review_required')
	if isinstance(A,list):B=[A for A in A if not(isinstance(A,dict)and A.get('checked_by'))];C=sorted({B for A in B if isinstance(A,dict)for B in([A['track']]if isinstance(A.get('track'),str)and A['track']else[])+list(A.get('tracks')or())});return bool(B),C
	return bool(A),[]
def track_sources(rule,model,cell):
	A=model
	if VM is None or not isinstance(A,dict)or not isinstance(cell,dict):return[]
	try:return VM.position_sources(rule,A,cell)
	except Exception:return[]
def open_legal_point(rule,model):
	A=model
	if VM is None or not isinstance(A,dict):return False
	try:return any(A==rule.get('rule_id')for(A,B,C)in VM.no_source_notes(A))
	except Exception:return False
def clause(rule,model=None):
	H=model;A=rule;G=A.get('traffic_light')or{};E={B:block(B,G.get(B)or{},track_sources(A,H,G.get(B)or{}))for B in TRACKS};J,K=legal_review(A);B={'id':A.get('rule_id'),'title':A.get('topic_name')or A.get('topic')or'','clause_issue':A.get('clause_issue')or'','topic_ids':A.get('topic_ids')or[],'topic_origin':A.get('topic_origin')or'catalog','clause_kind':A.get('clause_kind')or'','policy_ref':A.get('policy_ref')or A.get('rule_id'),'importance':A.get('importance')or'','activation_conditions':A.get('activation_conditions')or[],'post_checks':A.get('post_checks')or[],'green':E['green'],'yellow':E['yellow'],'red':E['red'],'red_line':E['red']['red_line'],'preferred_wording':E['green']['preferred_wording'],'fallback_wording':E['yellow']['fallback_wording'],'fallback_source':E['yellow']['fallback_source'],'fallback_steps':E['yellow']['fallback_steps'],'round1_posture':A.get('round1_posture')or'hold_green','round1_posture_source':A.get('round1_posture_source')or'importance','statutory_override':A.get('statutory_override')or[],'evidence_count':A.get('evidence_count')if A.get('evidence_count')is not None else 0,'policy_status':A.get('policy_status')or'Inferred','confidence':A.get('confidence')or'','presence':A.get('presence_rule')or{},'walk_away':bool(A.get('walk_away')),'legal_review_required':J,'legal_review_tracks':K,'segment_overrides':[],'model_ref':'rules[id=%s]'%A.get('rule_id')}
	if open_legal_point(A,H):B['no_approved_source']=True;B['no_source_note']=VM.no_source_text(H.get('output_language')or'he')if VM else''
	for D in TRACKS:
		if isinstance(G.get(D),dict)and isinstance(G[D].get('values'),dict):B[D]['values']=G[D]['values']
	if A.get('walk_away')and A.get('walk_away_source'):B['walk_away_source']=A['walk_away_source']
	for F in A.get('segment_variants')or():
		if not isinstance(F,dict)or not F.get('segment_id'):continue
		I=F.get('traffic_light')or{};C={'segment_id':F['segment_id'],'negotiation_mode':F.get('negotiation_mode')or'negotiated','round1_posture':F.get('round1_posture')or B['round1_posture'],'evidence_count':F.get('evidence_count')if F.get('evidence_count')is not None else 0}
		for D in TRACKS:
			if I.get(D):C[D]=block(D,I[D],track_sources(A,H,I[D]))
		C['red_line']=(C.get('red')or{}).get('red_line',B['red_line']);C['preferred_wording']=(C.get('green')or{}).get('preferred_wording',B['preferred_wording']);C['fallback_wording']=(C.get('yellow')or{}).get('fallback_wording',B['fallback_wording']);C['fallback_source']=(C.get('yellow')or{}).get('fallback_source',B['fallback_source']);C['fallback_steps']=(C.get('yellow')or{}).get('fallback_steps',B['fallback_steps']);B['segment_overrides'].append(C)
	return B
def market_sources(model):
	C=model.get('market_research')or{};D={}
	for A in C.get('ranges')or():
		if not isinstance(A,dict):continue
		for E in('ours','middle','theirs'):
			F=A.get(E)
			for H in(F if isinstance(F,dict)else{}).get('source_ids')or():D.setdefault(H,[]).append({'rule_id':A.get('rule_id')or A.get('topic'),'range_point':E})
	G=[]
	for B in C.get('source_refs')or():
		if not isinstance(B,dict)or B.get('read_status')in('located_not_read','excluded','blocked'):continue
		G.append({A:B.get(A,'')for A in('source_id','issuing_body','document','doc_date','drafter_role','drafted_by','url','retrieved_at')}|{'supports':D.get(B.get('source_id'),[])})
	return G
def coverage_summary(model):B=model;C=B.get('coverage')or{};A=lambda a,b:C.get(a)if isinstance(C.get(a),int)else C.get(b);return{'units':A('units','units_total'),'topic_units':A('topic_units','units_mapped'),'technical_units':A('technical_units','units_technical'),'unique_units':A('unique_units','units_unique')or 0,'unmapped_units':A('unmapped_units','units_unmapped'),'ledger':VM.coverage_ledger(B)if VM is not None else None,'topics':len([A for A in B.get('rules')or()if isinstance(A,dict)]),'topics_new':sum(1 for A in B.get('rules')or()if isinstance(A,dict)and A.get('topic_origin')=='corpus_derived')}
def gate_label(model,model_path):
	A=model
	if S is not None:B=S.gate_status(A,model_path);return B['playbook_status'],B['label']
	return A.get('playbook_status')or'Draft',A.get('status_label')or''
def build(model,model_path):
	B=model_path;A=model;C=A.get('scope_summary')or{};E,F=gate_label(A,B);D=[A for A in C.get('contract_families')or()if isinstance(A,dict)]
	with open(B,'rb')as G:H=hashlib.sha256(G.read()).hexdigest()
	I=A.get('company_role_code')or next((A.get('company_role_code')for A in D if A.get('company_role_code')),'');return{'schema_version':CORE_SCHEMA,'playbook_id':A.get('playbook_id')or'','family_id':A.get('family_id')or'','family_code':A.get('family_code')or A.get('family_id')or'','company_role_code':I,'corpus_origin':A.get('corpus_origin')or C.get('corpus_origin')or'own','market_research_date':(A.get('market_research')or{}).get('research_date')or'','market_sources':market_sources(A),'playbook_status':E,'status_label':F,'produced_with':A.get('produced_with')or{},'playbook_version':str(A.get('version')or''),'core_version':A.get('core_version')or'','generated_at':_dt.date.today().isoformat(),'source_model':os.path.basename(B),'source_model_updated':(A.get('last_updated')or A.get('generated_at')or'')[:10],'source_model_sha256':H,'company_role':C.get('company_role')or next((A.get('company_role')for A in D if A.get('company_role')),''),'output_language':A.get('output_language')or'he','applicability':A.get('applicability')or{},'home_countries':home_of(A),'contract_families':[{A:B.get(A)for A in('contract_family_name','family_aliases','company_role','company_role_code')if B.get(A)is not None}for B in D],'clauses':[clause(B,A)for B in A.get('rules')or()if isinstance(B,dict)],'technical_topics':[{'code':A,'label':B}for(A,B)in TECHNICAL_TOPICS],'unique_clauses':[{B:A.get(B)for B in('ref','kind','queue_id')if A.get(B)}for A in(A.get('coverage')or{}).get('unique_clauses')or()if isinstance(A,dict)],'coverage':coverage_summary(A),'segments':[{B:A.get(B)for B in('segment_id','label','criteria','negotiation_mode')}for A in(A.get('segmentation_model')or{}).get('segments')or()if isinstance(A,dict)],'validity':validity_of(A)}
def stamp_model_label(model,model_path):
	A=model
	if S is None or A.get('approval_records'):return
	B=A.get('playbook_status'),A.get('status_label'),(A.get('handoff')or{}).get('status_label')if isinstance(A.get('handoff'),dict)else None;C=S.stamp(A,None,None);D=A.get('playbook_status'),A.get('status_label'),(A.get('handoff')or{}).get('status_label')if isinstance(A.get('handoff'),dict)else None
	if B==D:return
	with io.open(model_path,'w',encoding='utf-8')as E:json.dump(A,E,ensure_ascii=False,indent=1)
	return C['label']
def home_of(model):
	try:from playbook import validate_model as A;return A.home_countries(model)
	except Exception:return[]
def validity_of(model):
	try:from playbook import validity as A
	except ImportError:return{}
	return A.validity_summary(model)
def main(argv=None):
	sys.stdout.reconfigure(encoding='utf-8');D=argparse.ArgumentParser(description=__doc__.split('\n')[0]);D.add_argument('--model',required=True,help='playbook-model.json');D.add_argument('--out',help='ברירת המחדל: playbook-core.json לצד המודל');A=D.parse_args(argv)
	if not os.path.exists(A.model):print('המודל אינו קיים: %s'%A.model);return 2
	with io.open(A.model,encoding='utf-8')as E:F=json.load(E)
	C=A.out or os.path.join(os.path.dirname(os.path.abspath(A.model)),'playbook-core.json')
	try:C=guard_out(C,inputs=[A.model])
	except OutputRefused as I:print('refused: %s'%I,file=sys.stderr);return 2
	G=stamp_model_label(F,A.model)
	if G:print('המודל: התווית נכתבה מהגזירה האחת (status.base_code): %s'%G)
	B=build(F,A.model)
	with io.open(C,'w',encoding='utf-8')as E:json.dump(B,E,ensure_ascii=False,indent=1)
	H=[A['id']for A in B['clauses']if not A['preferred_wording']or not A['fallback_wording']];print('נכתב %s: %d סעיפים'%(C,len(B['clauses'])))
	if(B.get('validity')or{}).get('status')=='invalid':
		from playbook import validity as J;print('הפלייבוק אינו עובר את הבדיקות של עצמו: %s'%', '.join('%s x%d'%(A,B)for(A,B)in B['validity']['codes'].items()))
		for K in J.playbook_warnings(core=B,lang=B.get('output_language')or'he'):print('ללקוח: %s'%K)
	if H:print('לסעיפים האלה אין נוסח ירוק או נוסח נסיגה במודל, והנושא ונותן לא יוכל להחיל אותם: %s'%', '.join(str(A)for A in H))
	return 0
if __name__=='__main__':sys.exit(main())
