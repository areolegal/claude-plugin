#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (c) Areo. All rights reserved. Licensed under the terms at https://areo.co.il/legal/terms
import argparse,json,os,re,sys
from pathlib import Path
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
for _s in(sys.stdout,sys.stderr):
	try:_s.reconfigure(encoding='utf-8',errors='replace')
	except(AttributeError,ValueError):pass
VALID_STATUS={'Confirmed','Inferred','Unclear'}
VALID_CONF={'High','Medium','Low'}
VALID_PB_STATUS={'Draft','PartiallyApproved','Approved','Superseded','Invalid'}
VALID_POSTURE_SOURCE={'importance','tradeoff_statement','client_answer'}
VALID_POSTURE={'hold_green','offer_yellow','not_applicable'}
WALK_AWAY_MAX=5
VALID_REG_STATUS={'NotResearched','NoSpecificSourceIdentified','ApplicableSourcesFound'}
VALID_PRESENCE={'Required','Optional','Conditional','Prohibited'}
LEGACY_PRESENCE={'Recommended'}
VALID_MISSING_COLOR={'Green','Yellow','Red','NotApplicable'}
VALID_EVIDENCE_TRACK={'green','yellow','red','context'}
VALID_QUEUE_SCOPE={'rule','segment','rules','playbook'}
VALID_CORPUS_STATUS={'signed','mostly_drafts','company_forms','third_party_forms','unknown'}
VALID_TEMPLATE_STATUS={'found','attached','none','unknown','not_asked'}
VALID_TOPIC_ORIGIN={'catalog','corpus_derived'}
VALID_RESEARCH_STATUS={'Performed','Partial','NotPerformed','NotRequested','Declined','Completed'}
RESEARCH_DONE={'Performed','Completed','Partial'}
LEGACY_NOT_PERFORMED={'not_run','skipped','NotRequested','Declined'}
VALID_NOT_PERFORMED_REASON={'route','no_web_access','not_answered','client_declined'}
VALID_QA_STATUS={'NotRun','Partial','Completed'}
VALID_SEG_STATUS={'NotDetected','Candidate','Confirmed'}
VALID_RATIONALE_STATUS={'Draft','Confirmed'}
VALID_OUTPUT_LANGUAGE={'he','en'}
VALID_MARKET_BASIS={'ExternalResearch','ExpertAssessment','InternalTrendOnly','NotAssessed'}
VALID_CORPUS_ORIGIN={'own','own_plus_market','market_built'}
CORPUS_BANDS=[(20,None,'full'),(7,19,'below20'),(1,6,'below7'),(0,0,'none')]
BAND_CHOICES={'full':{'own','own_plus_market','market_built'},'below20':{'own','own_plus_market','market_built'},'below7':{'own','own_plus_market','market_built'},'none':{'market_built'}}
BAND_CHOICE_FIELD={'full':{'not_asked','combine','own_only','market'},'below20':{'not_asked','combine','own_only','market'},'below7':{'combine','own_only','not_asked','market'},'none':{'market'}}
CHOICE_ORIGIN={'own_only':'own','combine':'own_plus_market','market':'market_built'}
VALID_TRACK_BASIS={'own_evidence','own_paper_repeated','documents_majority','template','company_request','client_answer','established','single','offered_unexecuted','company_source','struck','rejected_comment','never_accepted','bid_condition','market_standard','areo_proposal'}
FALLBACK_SOURCE_WORDS={'market_standard','areo_proposal'}
LEGACY_FALLBACK_SOURCE={'signed_compromise','single_compromise','offered_not_signed','client_answer'}
VALID_ACCEPTANCE_MODE={'negotiated','imposed','unnegotiated','unknown'}
VALID_PAPER={'ours','theirs','third_party','unknown'}
LEGACY_PAPER=set()
VALID_DOC_ROLE={'signed','agreement','draft','amendment','template','form','correspondence','guidance','policy','table'}
NOT_NEGOTIATION_ROLES={'form','template','correspondence','guidance','policy','table'}
VALID_BASELINE={'template','own_paper_majority','documents_majority','none','market'}
NON_SIGNED_STATUSES={'company_forms','third_party_forms','unknown'}
CONF_CAP_ORDER={'Low':0,'Medium':1,'High':2}
FORBIDDEN_YELLOW='לפי שיקול דעת הצד','ללא הגבלה','כפי שיידרש','unlimited','sole discretion'
LEGACY_RULE_KEYS={'fallbacks','fallback_1','fallback_2','red_line','escalation'}
COLOR_SPEC={'green':'Approved','yellow':'AgreeWithComments','red':'NotApproved'}
RATIONALE_MIN={'executive_policy_rationale':120,'protected_interest_and_clause_purpose':60,'legal_risk_and_legal_framework':80,'contractual_risk_allocation_mechanism':60,'company_role_and_policy_fit':60,'business_operational_impact':60,'internal_evidence_rationale':60,'market_practice_assessment':40,'green_boundary_rationale':50,'yellow_boundary_rationale':50,'red_boundary_rationale':50,'tradeoff_statement':40,'related_clause_rationale':30,'uncertainties_and_limitations':20}
SEG_RATIONALE_MIN={'executive_segment_rationale':70,'segment_characteristic_and_risk_change':50,'legal_basis':40,'business_basis':40,'internal_evidence_basis':40,'market_practice_assessment':25,'green_boundary_rationale':35,'yellow_boundary_rationale':35,'red_boundary_rationale':35,'tradeoff':30,'related_clause_effect':20,'uncertainties_and_limitations':15}
def corpus_status_of(data):
	try:import areo_lib;from playbook import status as A;return A.corpus_status(data)
	except ImportError:return(data.get('scope_summary')or{}).get('corpus_status')or'signed'
def nonempty(value):return value not in(None,'',[],{})
def text_len(value):
	A=value
	if not isinstance(A,str):return 0
	return len(' '.join(A.split()))
def add(errors,msg):errors.append(msg)
def require_obj(errors,obj,key,prefix):
	A=obj.get(key)
	if not isinstance(A,dict)or not A:add(errors,f"{prefix} missing/non-object {key}");return
	return A
def validate_previous(errors,items,prefix,segment_ids):
	F=prefix;D=items;A=errors
	if D is None:return
	if not isinstance(D,list):add(A,f"{F}.previous_agreements_where_language_accepted must be list");return
	for(H,B)in enumerate(D):
		C=f"{F}.previous_agreements_where_language_accepted[{H}]"
		if not isinstance(B,dict):add(A,f"{C} must be object");continue
		for G in['agreement_id','agreement_label','agreement_status','company_role','date','clause_ref','similarity','source_ref']:
			if not nonempty(B.get(G)):add(A,f"{C} missing {G}")
		if B.get('similarity')not in{'Exact','SubstantiallySimilar'}:add(A,f"{C} invalid similarity")
		E=B.get('segment_id')
		if E and E not in segment_ids:add(A,f"{C} references unknown segment_id {E}")
def fallback_source_ok(src,citation_ids=None):
	B=citation_ids;A=src
	if not isinstance(A,str)or not A.strip():return False
	if A in FALLBACK_SOURCE_WORDS or A in LEGACY_FALLBACK_SOURCE or A.startswith('answer:'):return True
	return A in B if B else True
def validate_traffic_light(errors,light,prefix,segment_ids,citation_ids=None):
	H=prefix;G=light;A=errors
	if not isinstance(G,dict)or not G:add(A,f"{H} missing/non-object traffic_light");return
	for(F,I)in COLOR_SPEC.items():
		B=G.get(F);C=f"{H}.traffic_light.{F}"
		if not isinstance(B,dict)or not B:add(A,f"{C} missing/non-object");continue
		if B.get('meaning')!=I:add(A,f"{C} meaning must be {I}")
		for J in['position','match_criteria','proposed_clause']:
			if not nonempty(B.get(J)):add(A,f"{C} missing {J}")
		if not isinstance(B.get('match_criteria'),list)or not B.get('match_criteria'):add(A,f"{C}.match_criteria must be a non-empty list")
		if F=='yellow'and not nonempty(B.get('comments')):add(A,f"{C} requires comments")
		E=B.get('basis')
		if E not in VALID_TRACK_BASIS:add(A,f"{C} missing/invalid basis")
		elif E!='areo_proposal'and not nonempty(B.get('basis_refs')):add(A,f"{C} basis {E} requires basis_refs")
		if E in{'market_standard','areo_proposal'}and not nonempty(B.get('label')):add(A,f"{C} requires a label when the source is not the company")
		if E=='market_standard':
			K=B.get('basis_refs')
			if not isinstance(K,list)or len(K)<3:add(A,f"{C} market_standard requires three counted sources")
		if F=='yellow':
			D=B.get('fallback_wording')
			if not isinstance(D,dict)or not nonempty(D.get('text')):add(A,f"{C} requires fallback_wording.text")
			elif not fallback_source_ok(D.get('source'),citation_ids):add(A,f"{C}.fallback_wording invalid source {D.get('source')!r}: a citation id, answer:<id>, market_standard or areo_proposal")
			elif D.get('source')=='signed_compromise'and len(D.get('negotiation_refs')or[])<2:add(A,f"{C} established yellow requires two different negotiations")
			if B.get('offer_yellow')and(D or{}).get('source')!='signed_compromise'and E!='established':add(A,f"{C} offer_yellow is allowed only when the yellow is established")
			M=' '.join(str(A)for A in[B.get('proposed_clause'),(D or{}).get('text')]if A)
			for L in FORBIDDEN_YELLOW:
				if L in M:add(A,f"{C} yellow wording contains an unconditional concession: {L}")
		validate_previous(A,B.get('previous_agreements_where_language_accepted',[]),C,segment_ids)
PASS_A_FIELDS='executive_policy_rationale','green_boundary_rationale','yellow_boundary_rationale','red_boundary_rationale','internal_evidence_rationale'
ENTITY_KIND_CODES={'company','corporate','individual','person','public_body','public','government','municipality','university','academic','non_profit','npo','nonprofit','non-profit','charity','government_company','foreign','large_enterprise','large','enterprise','sme','small','consumer','group','partnership'}
LEGACY_COUNTERPARTY_KIND={'local','foreign','large','small','any'}
VALID_COUNTERPARTY_KIND=ENTITY_KIND_CODES|LEGACY_COUNTERPARTY_KIND
NOT_OBSERVED_LABELS={'לא נצפה בקורפוס','not observed in the corpus'}
EXCLUSION_WORDS=re.compile('מוחרג|לא חל|לא מכוסה|מחוץ לתחולה|exclud|not applicable|not covered|out of scope',re.I)
VALID_POST_SCOPE={'whole_agreement','definitions','annexes'}
VALID_POST_ON_FAIL={'block','warn'}
def bad_kinds(value):A=value;B=A if isinstance(A,(list,tuple))else str(A).split(',');return[A for A in B if str(A).strip().lower()not in VALID_COUNTERPARTY_KIND]
def validate_applicability(errors,warnings,app):
	I=warnings;E=app;A=errors
	if E is None:return
	if not isinstance(E,dict):add(A,'applicability must be an object {counterparty_kinds[], deal_kinds[], value_range, not_observed[], not_covered[]}');return
	F=E.get('counterparty_kinds')
	if F is not None and not isinstance(F,list):add(A,'applicability.counterparty_kinds must be a list')
	elif F:
		J=bad_kinds(F)
		if J:I.append(f"applicability.counterparty_kinds has values outside the vocabulary {J}: {', '.join(sorted(ENTITY_KIND_CODES))}")
	G=E.get('not_observed')
	if G is None:return
	if not isinstance(G,list):add(A,'applicability.not_observed must be a list of {kind, label, recommendation}');return
	for(K,B)in enumerate(G):
		D=f"applicability.not_observed[{K}]";H=B.get('kind')if isinstance(B,dict)else B
		if not isinstance(B,(dict,str))or not nonempty(H):add(A,f"{D} needs kind (a counterparty type)");continue
		if bad_kinds(H):add(A,f"{D}.kind {H!r} is not a counterparty type ({', '.join(sorted(ENTITY_KIND_CODES))}); a deal type goes in not_covered[]")
		if not isinstance(B,dict):continue
		C=B.get('label')
		if nonempty(C)and EXCLUSION_WORDS.search(str(C)):add(A,f'{D}.label {C!r}: a type not observed is never excluded; the label is "לא נצפה בקורפוס" (EN: "not observed in the corpus")')
		elif nonempty(C)and str(C).strip()not in NOT_OBSERVED_LABELS:add(A,f'{D}.label {C!r} must be "לא נצפה בקורפוס" (EN: "not observed in the corpus")')
		if not nonempty(B.get('recommendation')):I.append(f'{D} has no recommendation: what to check when the playbook is applied to this type (clause-catalog.md, "Considerations by counterparty type")')
def validate_activation_and_post_checks(errors,rule,prefix):
	E=prefix;A=errors
	for(F,G)in enumerate(rule.get('activation_conditions')or[]):
		if not isinstance(G,dict):continue
		for H in('counterparty_kind','counterparty_entity'):
			if G.get(H)not in(None,'',[])and bad_kinds(G[H]):add(A,f"{E}.activation_conditions[{F}].{H} invalid ({', '.join(sorted(VALID_COUNTERPARTY_KIND))})")
	I=rule.get('post_checks')
	if I is None:return
	if not isinstance(I,list):add(A,f"{E}.post_checks must be a list");return
	for(F,B)in enumerate(I):
		C=f"{E}.post_checks[{F}]"
		if not isinstance(B,dict):add(A,f"{C} must be an object");continue
		if not nonempty(B.get('id'))or not nonempty(B.get('intent')):add(A,f"{C} missing id or intent")
		D=B.get('pass_when')
		if isinstance(D,dict):
			J=list(D.get('absent')or[])+list(D.get('present')or[])
			if not J:add(A,f"{C}.pass_when needs absent[] or present[]")
			for K in J:
				try:re.compile(K)
				except(re.error,TypeError):add(A,f"{C}.pass_when has an invalid pattern: {K!r}")
		elif not nonempty(D):add(A,f"{C}.pass_when missing (text for a manual check, or {{absent, present}})")
		if B.get('scope')not in(None,'')and B['scope']not in VALID_POST_SCOPE:add(A,f"{C}.scope invalid ({', '.join(sorted(VALID_POST_SCOPE))})")
		if B.get('on_fail')not in(None,'')and B['on_fail']not in VALID_POST_ON_FAIL:add(A,f"{C}.on_fail invalid (block, warn)")
PERSPECTIVE_FIELDS='legal_analysis','business_analysis','internal_corpus_findings','internal_contracting_trend','external_market_trend'
def validate_perspective(errors,rule,prefix):
	E=prefix;D=errors;B=rule;F=B.get('policy_rationale')if isinstance(B.get('policy_rationale'),dict)else{};C=F.get('rationale_status')=='Draft';G=set(F.get('pass_b_pending')or());H=B.get('company_perspective')
	if not isinstance(H,dict):
		if C and all('company_perspective.%s'%A in G for A in PERSPECTIVE_FIELDS):return
		add(D,f"{E} missing/non-object company_perspective");return
	for A in PERSPECTIVE_FIELDS:
		if not nonempty(H.get(A))and not(C and'company_perspective.%s'%A in G):add(D,f"{E}.company_perspective missing {A}"+(' (in pass A, list it in pass_b_pending as company_perspective.%s)'%A if C else''))
def validate_rationale(errors,rationale,prefix,min_spec,applicability_min=2):
	F=applicability_min;E=min_spec;D=prefix;C=errors;B=rationale
	if not isinstance(B,dict)or not B:add(C,f"{D} missing/non-object rationale");return
	if B.get('rationale_status')=='Draft'and E is RATIONALE_MIN:
		I=set(B.get('pass_b_pending')or())
		for A in PASS_A_FIELDS:
			if not nonempty(B.get(A)):add(C,f"{D} missing {A} (pass A)")
		for A in E:
			if A not in PASS_A_FIELDS and not nonempty(B.get(A))and A not in I:add(C,f"{D}.{A} is empty and not listed in pass_b_pending")
		if B.get('rationale_status')not in VALID_RATIONALE_STATUS:add(C,f"{D} invalid rationale_status")
		return
	for(A,G)in E.items():
		if not nonempty(B.get(A)):add(C,f"{D} missing {A}")
		elif text_len(B.get(A))<G:add(C,f"{D}.{A} too thin ({text_len(B.get(A))} chars; minimum {G})"+(': pass B writes this pass A field in full (policy-rationale.md, sections 1, 8 and 10)'if E is RATIONALE_MIN and A in PASS_A_FIELDS else''))
	H=B.get('applicability_scenarios')
	if not isinstance(H,list)or len([A for A in H if nonempty(A)])<F:add(C,f"{D}.applicability_scenarios requires at least {F} substantive scenarios")
	if B.get('rationale_status')not in VALID_RATIONALE_STATUS:add(C,f"{D} invalid rationale_status")
	if B.get('market_practice_basis')not in VALID_MARKET_BASIS:add(C,f"{D} invalid market_practice_basis")
def _guard(out,inputs):
	from common.cli import OutputRefused as A,guard_out as B
	try:return B(out,inputs=inputs)
	except A as C:print('refused: %s'%C);return
def validate_qa_summary(errors,data):
	I=data;A=errors;B=I.get('qa_summary')
	if not isinstance(B,dict):add(A,'qa_summary must be object');return
	J=B.get('status')
	if J not in VALID_QA_STATUS:add(A,'qa_summary invalid status')
	if I.get('playbook_status')=='Approved'and J!='Completed':add(A,'Approved playbook requires completed QA back-test')
	if J!='Completed':return
	C='or record qa_summary.status Partial with untested_rule_ids (playbook-qa.md, "qa_summary")';K=[A for A in I.get('rules')or[]if isinstance(A,dict)];D=B.get('tested_rule_count')
	if not isinstance(D,int)or isinstance(D,bool):add(A,f"qa_summary status Completed requires tested_rule_count, {C}")
	elif D!=len(K):add(A,f"qa_summary status Completed requires tested_rule_count equal to the number of rules ({D} != {len(K)}), {C}")
	L=B.get('tested_source_count')
	if not isinstance(L,int)or isinstance(L,bool)or L<0:add(A,f"qa_summary status Completed requires tested_source_count, {C}")
	if not nonempty(B.get('checked_at')):add(A,'qa_summary status Completed requires checked_at')
	M=B.get('track_coherence')
	if not isinstance(M,list)or not M:add(A,f"qa_summary status Completed requires track_coherence[], one entry per rule and per segment variant {{rule_id, segment_id}}, {C}");return
	N=set()
	for E in M:
		if isinstance(E,dict)and nonempty(E.get('rule_id')):N.add((E['rule_id'],E.get('segment_id')or None))
	F=[]
	for O in K:
		G=O.get('rule_id')
		if(G,None)not in N:F.append(str(G))
		for H in O.get('segment_variants')or[]:
			if isinstance(H,dict)and nonempty(H.get('segment_id'))and(G,H['segment_id'])not in N:F.append(f"{G}/{H['segment_id']}")
	if F:add(A,f"qa_summary status Completed requires a track_coherence entry for every rule and segment variant; missing: {', '.join(F)}, {C}")
def main(path,core=None,index_entry=None,word=None,workspace=None,inventory=None,extract=None,coverage_out=None,skeleton_out=None,inputs=()):
	A3=coverage_out;u=skeleton_out;f=inventory;a=extract;U=path
	if u and not Path(U).exists():D={}
	else:
		try:D=json.loads(Path(U).read_text(encoding='utf-8'))
		except Exception as k:print('INVALID');print('- cannot parse JSON:',k);return 1
	if f is None:f=_find_beside(U,((D.get('coverage')or{}).get('inventory_ref'),'clause-inventory.json'))
	if a is None:a=_find_beside(U,((D.get('coverage')or{}).get('extract_ref'),'../../corpus-extract.json'))
	if u:
		try:import areo_lib;from playbook.validate_model import inventory_skeleton as Ac
		except ImportError as k:print('the shared library is not importable: %s'%k);return 1
		if not a:print('no corpus extract: pass --extract');return 2
		l=_guard(u,[U]+list(inputs))
		if not l:return 2
		AI=Ac(D,a);Path(l).write_text(json.dumps(AI,ensure_ascii=False,indent=1),encoding='utf-8');print('inventory skeleton written to %s: %d units to map (rule_id, technical, unique or unmapped_reason in each)'%(u,len(AI['units'])));return 0
	if A3:
		try:import areo_lib;from playbook.validate_model import coverage_from_inventory as Ad
		except ImportError as k:print('the shared library is not importable: %s'%k);return 1
		if not f:print('no clause inventory: pass --inventory');return 2
		l=_guard(A3,[U]+list(inputs))
		if not l:return 2
		V=Ad(D,f,a);V['inventory_ref']=f.get('ref')or(D.get('coverage')or{}).get('inventory_ref')or'';Path(l).write_text(json.dumps({A:B for(A,B)in V.items()if not A.startswith('_')},ensure_ascii=False,indent=1),encoding='utf-8');print('coverage block written to %s (units %d: mapped %d, technical %d, unique %d, unmapped %d, unassigned %d)'%(A3,V['units'],V['topic_units'],V['technical_units'],V['unique_units'],V['unmapped_units'],V['unassigned_units']))
	A=[];H=[];Ae=['schema_version','core_version','playbook_id','profile_id','version','playbook_status','output_language','scope_summary','segmentation_model','rules','regulatory_research','qa_summary']
	for E in Ae:
		if not nonempty(D.get(E)):add(A,f"missing {E}")
	W=D.get('playbook_status');AJ=D.get('approval_records');Af=isinstance(AJ,list)and bool(AJ)
	if W not in VALID_PB_STATUS:add(A,'invalid playbook_status')
	elif W in('PartiallyApproved','Approved')and not Af:add(A,f"playbook_status is {W} with no approval_records[]: the builder writes Draft, and the status is derived only after a positions sheet is ingested")
	elif W not in('Draft','PartiallyApproved','Approved'):add(A,f"playbook_status must be Draft on build, got {W}")
	if not nonempty(D.get('status_label')):add(A,"missing status_label: it is the only field that states the playbook's status, and every component prints it as it is")
	if'presentation_label'in json.dumps(D,ensure_ascii=False):add(A,'presentation_label must not appear anywhere: status_label is the only label field (two labels in one record is a defect)')
	if not nonempty(D.get('produced_with')):add(A,'missing produced_with: the skill version, the notes version and refs_sha256 of the run that produced this model')
	for E in['approved_by','approved_at','confirmed_by','approved_version']:
		if nonempty(D.get(E)):add(A,f"{E} must not be written: who approved is recorded in approval_records[], not in a field of its own")
	if D.get('output_language')not in VALID_OUTPUT_LANGUAGE:add(A,'invalid output_language')
	M=D.get('scope_summary')
	if not isinstance(M,dict):add(A,'scope_summary must be object')
	else:
		A4=M.get('contract_families')
		if not isinstance(A4,list)or not A4:add(A,'scope_summary requires contract_families[]')
		else:
			for(I,AK)in enumerate(A4):
				AL=f"scope_summary.contract_families[{I}]"
				if not isinstance(AK,dict):add(A,f"{AL} must be object");continue
				for E in['contract_family_id','contract_family_name','company_role','document_count']:
					if not nonempty(AK.get(E)):add(A,f"{AL} missing {E}")
		if not nonempty(M.get('total_document_count')):add(A,'scope_summary missing total_document_count')
		N=M.get('corpus_origin')
		if N not in VALID_CORPUS_ORIGIN:add(A,'scope_summary missing/invalid corpus_origin')
		elif D.get('corpus_origin')not in(None,N):add(A,f"corpus_origin at the root ({D.get('corpus_origin')}) differs from scope_summary.corpus_origin ({N})")
		J=M.get('corpus_basis')
		if not isinstance(J,dict):add(A,'scope_summary requires corpus_basis{}')
		else:
			b=J.get('agreement_units');O=J.get('band')if J.get('band')in BAND_CHOICES else None
			if not isinstance(b,int):add(A,'corpus_basis.agreement_units must be a number counted in code')
			else:
				O=next((C for(B,A,C)in CORPUS_BANDS if b>=B and(A is None or b<=A)),None)
				if J.get('band')!=O:add(A,f"corpus_basis.band must be {O} for {b} agreements")
				if N and O and N not in BAND_CHOICES.get(O,set()):add(A,f"corpus_origin {N} does not match band {O}")
			A5=['removed_duplicates','merged_versions','amendments_attached','excluded_templates']
			for E in A5:
				if not isinstance(J.get(E),list):add(A,f"corpus_basis missing {E}[] (counted in code)")
			if not isinstance(J.get('files'),int):add(A,'corpus_basis missing files (counted in code)')
			elif all(isinstance(J.get(A),list)for A in A5)and isinstance(b,int):
				AM=sum(len(J[A])for A in A5)
				if b+AM!=J['files']:add(A,f"corpus_basis does not add up: {J['files']} files but {b} counted plus {AM} deducted")
			m=J.get('choice')
			if O and m not in BAND_CHOICE_FIELD.get(O,set()):add(A,f"corpus_basis.choice {m} is not allowed in band {O}")
			elif m in CHOICE_ORIGIN and N and N!=CHOICE_ORIGIN[m]:add(A,f"corpus_origin {N} does not match choice {m}")
		A6=M.get('corpus_status')
		if A6 is None:H.append('scope_summary.corpus_status is missing (signed, mostly_drafts, company_forms, third_party_forms, unknown): the basis line falls back to source_log')
		elif A6 not in VALID_CORPUS_STATUS:add(A,f"scope_summary.corpus_status invalid {A6!r} ({', '.join(sorted(VALID_CORPUS_STATUS))})")
		A7=M.get('template_status')
		if A7 is not None and A7 not in VALID_TEMPLATE_STATUS:add(A,f"scope_summary.template_status invalid {A7!r} ({', '.join(sorted(VALID_TEMPLATE_STATUS))})")
		if M.get('contracting_entity_differs')and not nonempty(M.get('contracting_entity')):add(A,'scope_summary requires contracting_entity when the signer is not the profile company')
	validate_applicability(A,H,D.get('applicability'));n=D.get('segmentation_model');g=set();AN={}
	if not isinstance(n,dict):add(A,'segmentation_model must be object');n={}
	if n.get('status')not in VALID_SEG_STATUS:add(A,'segmentation_model invalid status')
	v=n.get('segments',[])
	if not isinstance(v,list):add(A,'segmentation_model.segments must be list');v=[]
	if n.get('status')=='Confirmed'and not v:add(A,'Confirmed segmentation_model requires segments[]')
	for(I,h)in enumerate(v):
		K=f"segmentation_model.segments[{I}]"
		if not isinstance(h,dict):add(A,f"{K} must be object");continue
		for E in['segment_id','label','criteria','policy_status','confidence','evidence']:
			if not nonempty(h.get(E)):add(A,f"{K} missing {E}")
		F=h.get('segment_id')
		if F in g:add(A,f"duplicate segment_id {F}")
		if F:g.add(F);AN[F]=h.get('policy_status')
		if h.get('policy_status')not in VALID_STATUS:add(A,f"{K} invalid policy_status")
		if h.get('confidence')not in VALID_CONF:add(A,f"{K} invalid confidence")
	X=D.get('regulatory_research')
	if not isinstance(X,dict):add(A,'regulatory_research must be object')
	else:
		W=X.get('status')
		if W not in VALID_RESEARCH_STATUS:add(A,'regulatory_research invalid status')
		if W in RESEARCH_DONE:
			if X.get('trigger')not in('client_chose','band_below7','band_none')and X.get('requested_by_user')is not True:add(A,'regulatory research Performed/Partial requires trigger client_chose (the client chose deep research: corpus_basis.choice combine or market)')
			AO=((D.get('scope_summary')or{}).get('corpus_basis')or{}).get('choice')
			if AO in('own_only','not_asked'):add(A,'regulatory research was recorded Performed/Partial, but corpus_basis.choice is %s: outside research only when the client chose it (rr1-gate-sources-verification.md)'%AO)
			if not nonempty(X.get('checked_at')):add(A,'completed/partial regulatory research requires checked_at')
	if isinstance(X,dict)and X.get('status')=='NotPerformed'and X.get('not_performed_reason')not in VALID_NOT_PERFORMED_REASON:add(A,'regulatory_research NotPerformed requires not_performed_reason (%s)'%', '.join(sorted(VALID_NOT_PERFORMED_REASON)))
	A8=D.get('market_research')
	if not isinstance(A8,dict):add(A,'missing market_research{} (status Performed, Partial or NotPerformed)')
	else:
		o=A8.get('status')
		if o in LEGACY_NOT_PERFORMED:H.append(f"market_research.status {o} is a legacy name for NotPerformed")
		elif o not in('Performed','Partial','NotPerformed','Completed'):add(A,f"market_research invalid status {o!r} (Performed, Partial, NotPerformed)")
		elif o=='NotPerformed'and A8.get('not_performed_reason')not in VALID_NOT_PERFORMED_REASON:add(A,'market_research NotPerformed requires not_performed_reason (%s)'%', '.join(sorted(VALID_NOT_PERFORMED_REASON)))
	validate_qa_summary(A,D);i=D.get('rules')
	if not isinstance(i,list)or not i:add(A,'rules must be a non-empty list');i=[]
	w=set()
	for(I,G)in enumerate(D.get('source_log')or[]):
		K=f"source_log[{I}]"
		if not isinstance(G,dict):add(A,f"{K} must be object");continue
		F=G.get('source_id')
		if not nonempty(F):add(A,f"{K} missing source_id")
		elif F in w:add(A,f"duplicate source_id {F}")
		else:w.add(F)
		if G.get('doc_role')not in(None,'')and G['doc_role']not in VALID_DOC_ROLE:add(A,f"{K} invalid doc_role {G['doc_role']!r} ({', '.join(sorted(VALID_DOC_ROLE))})")
		if G.get('doc_role')in('template','correspondence'):continue
		if G.get('paper')in LEGACY_PAPER:H.append(f"{K} paper {G['paper']!r} is a legacy value: leave it empty when it cannot be determined (playbook-schema.md)")
		elif G.get('paper')not in VALID_PAPER and G.get('paper')not in(None,''):add(A,f"{K} invalid paper {G.get('paper')!r} (ours, theirs, third_party or unknown)")
		if not nonempty(G.get('channel')):add(A,f"{K} missing channel")
		if G.get('acceptance_mode')not in VALID_ACCEPTANCE_MODE:add(A,f"{K} missing/invalid acceptance_mode")
	p=corpus_status_of(D);A9=[A for A in D.get('source_log')or[]if isinstance(A,dict)and A.get('included')is not False]
	if p=='unknown':AA=0
	else:AA=len({A.get('negotiation_id')or A.get('source_id')for A in A9 if A.get('doc_role')not in NOT_NEGOTIATION_ROLES and A.get('status')!='company_form'})
	if p=='company_forms'and A9 and not any(A.get('doc_role')=='form'or A.get('status')=='company_form'for A in A9):H.append('scope_summary.corpus_status is company_forms, and no source_log row is doc_role form: record each form as doc_role form (workflow.md, step 2ח)')
	x={A.get('citation_id')for A in D.get('citations')or[]if isinstance(A,dict)};j=set();AP=0;y=[];AQ=set()
	for(I,B)in enumerate(i):
		C=f"rules[{I}]"
		if not isinstance(B,dict):add(A,f"{C} must be object");continue
		validate_activation_and_post_checks(A,B,C)
		for AR in sorted(LEGACY_RULE_KEYS):
			if AR in B:add(A,f"{C} contains prohibited legacy field {AR}")
		Ag=isinstance(B.get('evidence'),list)and all(((B.get('traffic_light')or{}).get(A)or{}).get('basis')in('client_answer','areo_proposal','market_standard')for A in('green','yellow','red'))
		for E in['rule_id','topic_name','clause_issue','why_address_topic','policy_status','confidence','evidence','presence_rule','policy_rationale','traffic_light']:
			if E=='evidence'and Ag:continue
			if not nonempty(B.get(E)):add(A,f"{C} missing {E}")
		q=B.get('rule_id')
		if q in j:add(A,f"duplicate rule_id {q}")
		if q:j.add(q)
		if B.get('policy_status')not in VALID_STATUS:add(A,f"{C} invalid policy_status")
		if B.get('confidence')not in VALID_CONF:add(A,f"{C} invalid confidence")
		validate_perspective(A,B,C)
		if B.get('topic_origin')not in(None,'')and B['topic_origin']not in VALID_TOPIC_ORIGIN:add(A,f"{C} invalid topic_origin {B['topic_origin']!r} (catalog, corpus_derived)")
		validate_rationale(A,B.get('policy_rationale'),f"{C}.policy_rationale",RATIONALE_MIN,2);AB=B.get('round1_posture')
		if AB is None:add(A,f"{C} missing round1_posture")
		elif AB not in VALID_POSTURE:add(A,f"{C} invalid round1_posture: {AB}")
		G=B.get('round1_posture_source')
		if G is None:add(A,f"{C} missing round1_posture_source")
		elif G=='default':add(A,f"{C} round1_posture_source is 'default': the value was renamed to 'importance', because the default follows importance")
		elif G not in VALID_POSTURE_SOURCE:add(A,f"{C} invalid round1_posture_source: {G}")
		AS=B.get('walk_away')
		if not isinstance(AS,bool):add(A,f"{C} walk_away must be true or false on every rule")
		elif AS:
			y.append(q)
			if not nonempty(B.get('walk_away_source')):add(A,f"{C} walk_away is true without walk_away_source: a deal breaker needs a recorded source (statute, a company document, or the client's answer)")
		if D.get('playbook_status')=='Approved'and isinstance(B.get('policy_rationale'),dict):
			if B['policy_rationale'].get('rationale_status')!='Confirmed':add(A,f"Approved playbook requires confirmed rationale for {C}")
		z=B.get('presence_rule')
		if not isinstance(z,dict):add(A,f"{C}.presence_rule must be object")
		else:
			r=z.get('requirement')
			if r in LEGACY_PRESENCE:H.append(f"{C}.presence_rule.requirement {r} is a legacy value; use one of {', '.join(sorted(VALID_PRESENCE))}")
			elif r not in VALID_PRESENCE:add(A,f"{C}.presence_rule invalid requirement {r!r} ({', '.join(sorted(VALID_PRESENCE))})")
			elif r=='Conditional'and not nonempty(z.get('condition'))and not nonempty(B.get('activation_conditions')):add(A,f"{C}.presence_rule Conditional requires condition (or activation_conditions[])")
			if z.get('missing_clause_color')not in VALID_MISSING_COLOR:add(A,f"{C}.presence_rule invalid missing_clause_color")
		AT=B.get('regulatory_status')
		if AT not in VALID_REG_STATUS:add(A,f"{C} invalid/missing regulatory_status")
		if AT=='ApplicableSourcesFound'and not nonempty(B.get('regulatory_sources')):add(A,f"{C} ApplicableSourcesFound requires regulatory_sources")
		AU=set()
		for E in('agreement_exceptions','observed_alternatives','statutory_override'):
			for AC in B.get(E)or[]:
				c=AC.get('source_ref')if isinstance(AC,dict)else AC
				if c:AU.add(c)
		AD=0
		for(Ah,d)in enumerate(B.get('evidence')or[]):
			Y=f"{C}.evidence[{Ah}]"
			if not isinstance(d,dict):add(A,f"{Y} must be object");continue
			AD+=1
			if d.get('same_family')is None:add(A,f"{Y} missing same_family")
			if not nonempty(d.get('company_role_in_source')):add(A,f"{Y} missing company_role_in_source")
			s=d.get('track')
			if s not in(None,'')and s not in VALID_EVIDENCE_TRACK:add(A,f"{Y} invalid track {s!r} (green, yellow, red, context)")
			if d.get('same_family')is False and s!='context':add(A,f"{Y} evidence from another contract family may only be context")
			c=d.get('source_ref')
			if c and w and c.split('#')[0]not in w:add(A,f"{Y} source_ref {c} is not in source_log")
			AE=d.get('citation_id')
			if AE and x and AE not in x:add(A,f"{Y} citation_id {AE} is not in citations[]")
			if s in{'green','yellow'}and c in AU:add(A,f"{Y} a green/yellow track cannot rest on an exception, a replaced wording or a statutory override")
		L=B.get('evidence_count')
		if isinstance(L,bool)or L is not None and not isinstance(L,(int,dict)):add(A,f"{C}.evidence_count must be {{independent_negotiations, on_company_paper}}")
		elif isinstance(L,int)and L!=AD:add(A,f"{C}.evidence_count says {L} but {AD} entries were found")
		elif isinstance(L,dict):
			P,AV=L.get('independent_negotiations'),L.get('on_company_paper')
			if not isinstance(P,int)or not isinstance(AV,int)or AV>P:add(A,f"{C}.evidence_count needs integers independent_negotiations >= on_company_paper")
			A0=L.get('documents_addressing')
			if A0 is not None and(isinstance(A0,bool)or not isinstance(A0,int)or A0<0):add(A,f"{C}.evidence_count.documents_addressing must be a count of documents")
			for A1 in('forms_addressing_topic','forms_addressing','documents_addressing_topic'):
				if A1 in L and A1 not in AQ:AQ.add(A1);H.append(f"{C}.evidence_count.{A1} (and in other rules) is a legacy name: documents_addressing")
			if isinstance(P,int)and p in NON_SIGNED_STATUSES and P>AA:add(A,f"{C}.evidence_count.independent_negotiations is {P}, but the corpus ({p}) has {AA} negotiations: a form is not a negotiation. Count the documents in documents_addressing")
			if isinstance(P,int)and B.get('confidence')in CONF_CAP_ORDER:
				AW='Low'if P<=1 else'Medium'if P==2 else'High'
				if p in NON_SIGNED_STATUSES and CONF_CAP_ORDER[B['confidence']]>CONF_CAP_ORDER[AW]:add(A,f"{C}.confidence {B['confidence']} is above the cap for {P} negotiations ({AW})")
		A2=B.get('fallback_origin')
		if isinstance(A2,dict)and A2.get('baseline')not in(None,'')and A2['baseline']not in VALID_BASELINE:H.append(f"{C}.fallback_origin.baseline {A2['baseline']!r} is not in the schema ({', '.join(sorted(VALID_BASELINE))})")
		validate_traffic_light(A,B.get('traffic_light'),C,g,x);AF=B.get('segment_variants',[])
		if not isinstance(AF,list):add(A,f"{C}.segment_variants must be list");AF=[]
		AX=set()
		for(Ai,Q)in enumerate(AF):
			R=f"{C}.segment_variants[{Ai}]"
			if not isinstance(Q,dict):add(A,f"{R} must be object");continue
			for E in['segment_id','applies_when','segmentation_rationale','traffic_light','policy_status','confidence','evidence']:
				if not nonempty(Q.get(E)):add(A,f"{R} missing {E}")
			F=Q.get('segment_id')
			if F not in g:add(A,f"{R} references unknown segment_id {F}")
			if F in AX:add(A,f"{C} duplicate segment variant for {F}")
			AX.add(F)
			if Q.get('policy_status')not in VALID_STATUS:add(A,f"{R} invalid policy_status")
			if Q.get('confidence')not in VALID_CONF:add(A,f"{R} invalid confidence")
			validate_rationale(A,Q.get('segmentation_rationale'),f"{R}.segmentation_rationale",SEG_RATIONALE_MIN,1);validate_traffic_light(A,Q.get('traffic_light'),R,g,x)
			if Q.get('policy_status')=='Confirmed':
				AP+=1
				if AN.get(F)!='Confirmed':add(A,f"{R} Confirmed policy cannot rely on unconfirmed segment {F}")
				AY=Q.get('segmentation_rationale')
				if isinstance(AY,dict)and AY.get('rationale_status')!='Confirmed':add(A,f"{R} Confirmed segment policy requires confirmed segmentation rationale")
		AG=B.get('company_process_reference')
		if nonempty(AG):
			if not isinstance(AG,dict)or not nonempty(AG.get('source_refs')):add(A,f"{C}.company_process_reference requires source_refs")
	for(I,B)in enumerate(i):
		if not isinstance(B,dict):continue
		for AZ in B.get('related_rule_ids',[]):
			if AZ not in j:add(A,f"rules[{I}] related_rule_id {AZ} does not exist")
	if D.get('playbook_status')=='Approved'and AP:
		if not isinstance(qa,dict)or not nonempty(qa.get('tested_segment_count')):add(A,'Approved playbook with confirmed segment variants requires qa_summary.tested_segment_count')
	t=D.get('validation_queue',[])
	if not isinstance(t,list):add(A,'validation_queue must be list');t=[]
	Aa={A.get('rule_id')for A in t if isinstance(A,dict)};Aa|={B for A in t if isinstance(A,dict)and A.get('scope')=='rules'for B in A.get('rule_ids')or[]}
	for(I,e)in enumerate(t):
		if not isinstance(e,dict):add(A,f"validation_queue[{I}] must be object");continue
		S='validation_queue[%d] (%s)'%(I,e.get('id'));T,Z=e.get('scope'),e.get('rule_id')
		for E in('id','topic','question','why','severity','recommendation'):
			if not nonempty(e.get(E)):add(A,f"{S} missing {E}")
		if T is None:H.append(f"{S} has no scope (rule, segment, rules, playbook)")
		elif T not in VALID_QUEUE_SCOPE:add(A,f"{S} invalid scope {T!r}")
		if T in('rule','segment')and Z not in j:add(A,f"{S} scope {T} requires a rule_id that exists in rules[] (got {Z!r})")
		if T=='playbook'and Z!='GLOBAL':
			if Z in(None,''):H.append(f"{S} scope playbook: rule_id should be GLOBAL")
			else:add(A,f"{S} scope playbook takes rule_id GLOBAL (got {Z!r})")
		if T=='segment'and e.get('segment_id')not in g:add(A,f"{S} scope segment requires a known segment_id")
		if T=='rules':
			Ab=e.get('rule_ids')or[]
			if len(Ab)<2 or any(A not in j for A in Ab):add(A,f"{S} scope rules requires rule_ids[] of two or more existing rules")
		if T is None and Z not in(None,'','GLOBAL')and Z not in j:add(A,f"{S} rule_id {Z} does not exist")
	for(I,B)in enumerate(i):
		if isinstance(B,dict)and B.get('policy_status')=='Unclear':
			if B.get('rule_id')not in Aa and not nonempty(B.get('validation_question')):add(A,f"rules[{I}] Unclear rule lacks validation queue item/question")
	if len(y)>WALK_AWAY_MAX:add(A,'%d rules have walk_away: true, the limit is %d (%s)'%(len(y),WALK_AWAY_MAX,', '.join(str(A)for A in y[:8])))
	Aj=content_findings(D,A,H,core=core,index_entry=index_entry,word=word,workspace=workspace,inventory=f,extract=a,model_path=U);handoff_findings(D,A);enforce_findings(D,A,H,a,U)
	if A:
		print('INVALID')
		for Ak in A:print('-',Ak)
		for AH in H:print('! warning:',AH)
		client_lines(D,core);return 1
	print('VALID')
	for AH in H:print('! warning:',AH)
	if Aj:print('(content checks from the shared library ran: %d findings, none blocking)'%len(H))
	return 0
def enforce_findings(data,errors,warnings,extract=None,model_path=None):
	C=extract;B=errors
	try:sys.path.insert(0,str(Path(__file__).resolve().parent));import enforce_playbook_checks as D,evidence_kind as E
	except ImportError as A:add(B,'enforce_playbook_checks is not importable, so the enforcement checks did not run: %s'%A);return
	try:F=C if C is not None else E.find_extract(data,model_path);G,H=D.run_checks(data,F)
	except Exception as A:add(B,'enforcement checks raised %s: %s'%(type(A).__name__,A));return
	for I in G:add(B,'enforce: '+I)
	for J in H:warnings.append('enforce: '+J)
def handoff_findings(data,errors):
	D=data;A=errors;H=(D.get('meta')or{}).get('build_request')or{}
	if H.get('requested_by')in(None,'','user'):return
	E=D.get('handoff')
	if not isinstance(E,dict):add(A,'handoff: a build for another component returns a handoff record');return
	B=H.get('route_answer')
	if B and E.get('route_answer')!=B:add(A,'handoff.route_answer: the route question was answered in the builder (meta.build_request.route_answer) and must be returned as is')
	for I in('asked_in','answer_verbatim','choice'):
		if B and I not in B:add(A,'meta.build_request.route_answer.%s is required'%I)
	C=E.get('decisions_now')
	if C is None:add(A,'handoff.decisions_now[] is required (up to three decisions, each with a recommendation)')
	elif len(C)>3:add(A,'handoff.decisions_now has %d items; at most three'%len(C))
	else:
		for(K,J)in enumerate(C):
			if not(isinstance(J,dict)and J.get('recommendation')):add(A,'handoff.decisions_now[%d]: every decision carries a recommendation'%K)
	if B:
		for F in D.get('validation_queue')or[]:
			G='%s %s'%(F.get('question')or'',F.get('why')or'')
			if'לאשר את הבחירה'in G or'לאשר?'in G and'בחירה'in G:add(A,'validation_queue %s: asks to confirm a choice the client already made in this session (route_answer)'%F.get('id'))
def client_lines(data,core=None):
	C=data
	try:import areo_lib;from playbook import validity as B
	except ImportError:return
	A='en'if str(C.get('output_language')or'').startswith('en')else'he';D=B.playbook_warnings(C,core,lang=A)
	if B.validity_summary(C,core)['status']=='valid':D.insert(0,B.TEXT[A]['other']['some'])
	print('client (%s): %s'%(A,B.TEXT[A]['head']))
	for E in D:print('client (%s): %s'%(A,E))
def _find_beside(model_path,candidates):
	B=Path(model_path).resolve().parent
	for A in candidates:
		if not A:continue
		for C in(Path(A),B/A,B/Path(str(A).replace('\\','/')).name):
			try:
				if C.is_file():return json.loads(C.read_text(encoding='utf-8'))
			except(OSError,ValueError):continue
def _scripts_closed(s):
	A=s.lower();B=0
	while True:
		C=A.find('<script',B)
		if C<0:return True
		D=A.find('</script>',C)
		if D<0:return False
		B=D+len('</script>')
def workspace_file_problems(workspace):
	C=workspace;import os
	if not os.path.isfile(C):return['Workspace: הקובץ %s לא קיים'%C]
	A=open(C,encoding='utf-8',errors='replace').read();B=[]
	if not A.lstrip().lower().startswith('<!doctype html'):B.append('Workspace: הקובץ אינו מסמך HTML שלם (חסר doctype)')
	if'</html>'not in A or not _scripts_closed(A):B.append('Workspace: הקובץ נחתך או לא נסגר (חסר </html> או תג script לא סגור)')
	if'/*__DATA__*/null'in A:B.append('Workspace: הנתונים לא הוזרקו לדף (נקודת ההזרקה נשארה ריקה)')
	return B
def workspace_findings(st,workspace,model,S,MC):
	A=st;from playbook.surfaces_render import read_workspace_status as G;C=[];B=(G(workspace)or{}).get('meta')or{};A=S.in_lang(A,B.get('lang'))
	for E in S.DUAL_FIELDS:
		if E in B:C.append('Workspace: meta.%s: שדה תווית כפול'%E)
	F=B.get('label_now')if B.get('label_now')is not None else B.get('status_label')
	if F!=A['label']:C.append('Workspace: label_now="%s", המחושב: "%s"'%(F,A['label']))
	D=B.get('approved_count')
	if D is None and A['approved_count']==0:D=0
	if D!=A['approved_count']:C.append('Workspace: approved_count=%s, המחושב: %d'%(D,A['approved_count']))
	C+=['Workspace: '+A for A in MC.count_claims(B.get('evidence_disclaimer')or'',model)];return C
def content_findings(data,errors,warnings,core=None,index_entry=None,word=None,workspace=None,inventory=None,extract=None,model_path=None):
	H=index_entry;E=workspace;C=errors;B=data
	try:import areo_lib;from playbook.status import check_consistency as L;from playbook.validate_model import validate as M
	except ImportError as A:add(C,'the shared library (areolegal/lib) is not importable, so the content checks did not run: %s'%A);return False
	try:N=M(B,core=core,index_entry=H,inventory=inventory,extract=extract)
	except Exception as A:add(C,'content checks raised %s: %s'%(type(A).__name__,A));return False
	for D in N:
		I=' '.join(str(D.get(A))for A in('rule_id','track')if D.get(A));J='%s%s: %s'%(D.get('code','?'),' (%s)'%I if I else'',D.get('message',''))
		if D.get('severity')=='error':add(C,J)
		else:warnings.append(J)
	try:
		from playbook import status as G;K=G.record_cells_for(B,model_path)if B.get('approval_records')else None;F=L(B,core,H,cells=K,word_path=word,workspace_path=None)
		if word and not E:F.append('Workspace: לא נמסרה סביבת עבודה לצד ה-Word. פלייבוק נמסר תמיד בשני התוצרים, יחד')
		if E:F+=workspace_file_problems(E);from playbook import market_counts as O;F+=workspace_findings(G.derive_status(B,K),E,B,G,O)
	except Exception as A:add(C,'the cross-layer status check raised %s: %s'%(type(A).__name__,A));return True
	for P in F:add(C,'status drift: %s'%P)
	return True
def _load(path,label):
	try:return json.loads(Path(path).read_text(encoding='utf-8'))
	except Exception as A:print('INVALID');print('- cannot read %s (%s): %s'%(label,path,A));raise SystemExit(1)
if __name__=='__main__':
	ap=argparse.ArgumentParser(description='Validates playbook-model.json: the schema here, and the mechanisms in the shared library (areolegal/lib).');ap.add_argument('model');ap.add_argument('--core',help='playbook-core.json, compared against the model');ap.add_argument('--index',help="the playbook's entry in playbooks/index.json");ap.add_argument('--word',help='the playbook .docx, checked for a stale status');ap.add_argument('--workspace',help='the workspace file, checked for a stale status');ap.add_argument('--inventory',help='clause-inventory.json; default: coverage.inventory_ref, or the file beside the model');ap.add_argument('--extract',help='corpus-extract.json; default: coverage.extract_ref, or Areo-נתונים/corpus-extract.json');ap.add_argument('--coverage-out',help='writes the coverage block computed from the inventory (and the extract) to this path, for the builder to copy into the model');ap.add_argument('--inventory-skeleton',help='writes the clause-unit skeleton built from the extract (one unit per clause, no mapping) to this path, and exits');ap.add_argument('--approved-sources',help='מקורות-מאושרים.json saved to disk: legal and regulatory source URLs are checked against it (default: AREO_APPROVED_SOURCES, else the copy bundled in the plugin, lib/מקורות-מאושרים.json)');a=ap.parse_args()
	if a.approved_sources:
		if not os.path.isfile(a.approved_sources):print('INVALID');print('- the approved-sources file does not exist: %s'%a.approved_sources);raise SystemExit(2)
		os.environ['AREO_APPROVED_SOURCES']=a.approved_sources
	if a.word:
		try:import areo_lib;from common.cli import load_docx_or_explain
		except ImportError:load_docx_or_explain=None
		if load_docx_or_explain:
			ok,msg,code=load_docx_or_explain(a.word,loader=False)
			if ok is None:print('INVALID');print(msg);raise SystemExit(code)
	raise SystemExit(main(a.model,core=_load(a.core,'the core')if a.core else None,index_entry=_load(a.index,'the index entry')if a.index else None,word=a.word,workspace=a.workspace,inventory=_load(a.inventory,'the clause inventory')if a.inventory else None,extract=_load(a.extract,'the corpus extract')if a.extract else None,coverage_out=a.coverage_out,skeleton_out=a.inventory_skeleton,inputs=[a.core,a.index,a.word,a.workspace,a.inventory,a.extract]))
