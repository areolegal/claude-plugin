#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (c) Areo. All rights reserved. Licensed under the terms at https://areo.co.il/legal/terms
import argparse,io,json,os,re,sys
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
import areo_lib,basis_line,evidence_kind as E,voice_scrub
from common.cli import OutputRefused,guard_out
from playbook import approval_sheet as A
from playbook import status as S
LIGHTS='green','yellow','red'
ORIGIN_TO_PATH={'own':'own','own_plus_market':'own_plus_market','market_built':'market_built'}
STATUS={'Draft':'Draft','PartiallyApproved':'PartiallyApproved','Approved':'Approved','Superseded':'Superseded'}
AREO_LABEL='הצעת Areo (לא מבוסס על מסמכי הלקוח)'
TXT={'he':{'title':'פלייבוק חוזי','areo':AREO_LABEL,'units':'%d הסכמים','files':'מתוך %d קבצים'},'en':{'title':'Contract playbook','areo':"Areo proposal (not based on the client's documents)",'units':'%d agreements','files':'out of %d files'}}
def norm_lang(v):
	v=str(v or'').strip().lower()
	if v.startswith('en'):return'en'
	if v.startswith('he')or v in('iw','עב','עברית'):return'he'
def resolve_lang(m,profile=None,lang=None):
	A=profile or{}
	for C in(lang,A.get('deliverable_language'),(m.get('scope_summary')or{}).get('deliverable_language'),m.get('deliverable_language'),A.get('display_language')):
		B=norm_lang(C)
		if B:return B
	return'he'
def warn(msg):sys.stderr.write('אזהרה: %s\n'%msg)
def ls_key(text):A=re.sub('[^A-Za-z0-9_]+','_',str(text or'')).strip('_');return A or'playbook'
def first_line(text,limit=160):A=re.sub('\\s+',' ',str(text or'')).strip();return A[:limit]
def pick(d,*B):
	for A in B:
		if isinstance(d,dict)and d.get(A)not in(None,'',[],{}):return d[A]
def build_meta(m,lang='he',st=None,profile=None):
	C=lang;B=st;F=m.get('scope_summary')or{};K=F.get('corpus_basis')or{};M=F.get('contract_families')or[];H=M[0]if M else{};H=family_in_lang(H,C);W=pick(H,'contract_family_name','label')or'';N=pick(H,'company_role')or'';L=m.get('company');I=pick(m,'company_name')or(L if isinstance(L,str)else pick(L or{},'name'))or pick(m.get('meta')or{},'company_name','company')or'';X=pick(m,'company_name_en')or pick(m.get('meta')or{},'company_name_en')or pick(profile or{},'organization_name_en')or I;O={'he':I,'en':X};I=O[C];P=pick(m,'playbook_id','family_id')or'playbook';A={'id':P,'slug':ls_key(pick(m,'family_id','playbook_id')),'ls_key':ls_key(P),'company':I,'title':W+(' · '+N if N else'')or TXT[C]['title'],'lang':C,'version':str(pick(m,'version')or'1.0'),'created':pick(m,'generated_at')or'','updated':pick(m,'last_updated','generated_at')or'','status':STATUS.get(pick(m,'playbook_status','status')or'Draft','Draft')};D=K.get('agreement_units')
	if isinstance(D,int)and S is not None:D=S.company_agreements_counted(m)
	Q=F.get('corpus_origin')
	if isinstance(D,int)and Q in ORIGIN_TO_PATH:A['build_path']={'n':D,'path':ORIGIN_TO_PATH[Q]}
	else:warn('אין corpus_basis.agreement_units או corpus_origin במודל, ולכן פס הבסיס לא יוצג')
	R=m.get('policy_gate')or{}
	for E in('status_label','label_now'):
		G=pick(m,E)or pick(R,E)
		if G:A[E]=G
	for E in('approved_count','positions_count'):
		G=R.get(E)
		if isinstance(G,int):A[E]=G
	B=B or S.derive_status(m,lang=C);A['label_now']=B['label'];A['status_label']=B['label'];A['playbook_status']=B['playbook_status'];A['labels']={A:S.label_for(B,A)for A in('he','en')};A['company_by_lang']=O;A['approved_count']=B['approved_count'];A['positions_count']=B['positions_count'];A['corpus_status']=basis_line.docs_status(m);Y=m.get('market_research')or{};T=pick(Y,'research_date','date','performed_at')
	if T:A['market_research_date']=T
	U=[A for A in F.get('company_roles')or[]if isinstance(A,dict)]
	if U:A['company_roles']=[{'role':pick(A,'role')or'','label':pick(A,'label')or''}for A in U]
	V=pick(F,'main_role')
	if V:A['main_role']=V
	J=[]
	if isinstance(D,int):J.append('%d %s'%(D,basis_line.docs(A['corpus_status'],C)))
	if K.get('files'):J.append(TXT[C]['files']%K['files'])
	if J:A['evidence_short']=', '.join(J)+'.'
	return A
_LATIN_ONLY=re.compile("^[A-Za-z0-9 ,.&()/'+\\-]+$")
_PAREN_LATIN=re.compile("\\(([A-Za-z][A-Za-z ,./'\\-]*)\\)")
def family_in_lang(fam,lang):
	A=fam
	if lang!='en'or not isinstance(A,dict):return A
	B=dict(A);C=A.get('contract_family_name_en')or next((A for A in A.get('family_aliases')or[]if isinstance(A,str)and _LATIN_ONLY.match(A.strip())),None)
	if C:B['contract_family_name']=C.strip()
	D=A.get('company_role')or'';E=_PAREN_LATIN.search(D);F=str(A.get('company_role_code')or'').replace('_',' ').strip();G=A.get('company_role_en')or(E.group(1).strip()if E else'')or(F.capitalize()if F else'')
	if G and not _LATIN_ONLY.match(D.strip()or'-'):B['company_role']=G
	return B
def scope_block(m,lang='he'):
	A=m.get('scope_summary')or{};B={'contract_families':[family_in_lang(A,lang)for A in A.get('contract_families')or[]]}
	for(D,E)in(('limitations','limitations'),('date_range','date_range'),('locations','source_locations'),('corpus_status','corpus_status')):
		C=pick(A,E)
		if C is not None:B[D]=C
	return B
def src_id(ref):return str(ref or'').split('#')[0]
def _plain_name(f):import re;A=re.sub('\\.(pdf|docx?|rtf|txt|eml|msg)$','',str(f or'').strip(),flags=re.I);return re.sub('^\\d{1,3}[\\s._-]+','',A).strip()
ORIGIN_LABELS={'he':{'guidance':'הנחיה פנימית של החברה','template':'תבנית של החברה','signed':'הסכם חתום','amendment':'תיקון להסכם','draft_ours':'טיוטה שלכם במשא ומתן','draft_theirs':'טיוטה של הצד שכנגד במשא ומתן','form_ours':'נוסח שאתם מציגים','form_theirs':'נוסח של הצד שכנגד','form_public':'נוסח ציבורי','unknown_paper':'מסמך שמקורו לא נקבע'},'en':{'guidance':'Company internal guidance','template':'Company template','signed':'Signed agreement','amendment':'Amendment','draft_ours':'Your draft in negotiation','draft_theirs':'Counterparty draft in negotiation','form_ours':'Form you present','form_theirs':'Counterparty form','form_public':'Public form','unknown_paper':'Document of undetermined origin'}}
def origin_label_key(row):
	B=row;A,C=str(B.get('doc_role')or''),B.get('paper')
	if E.layer_of(B)=='guidance':return'guidance'if C!='theirs'else'form_theirs'
	if A=='template':return'template'if C!='theirs'else'form_theirs'
	if A in('signed','agreement'):return'signed'
	if A=='amendment':return'amendment'
	if C=='ours':return'draft_ours'if A=='draft'else'form_ours'
	if C=='theirs':
		if B.get('counterparty_kind')in S.PUBLIC_KINDS:return'form_public'
		return'draft_theirs'if A=='draft'else'form_theirs'
	return'unknown_paper'
def origin_label(row):A=origin_label_key(row);return{'key':A,'he':ORIGIN_LABELS['he'][A],'en':ORIGIN_LABELS['en'][A]}
def build_sources(m):
	D,G={},{}
	for A in m.get('source_log')or[]:
		B=pick(A,'source_id')
		if not B:continue
		F=pick(A,'title')or _plain_name(pick(A,'file'))or B;C={'label':F,'name':F,'kind':'internal'};C['title']=F
		for(I,L)in(('paper','paper'),('doc_role','doc_role'),('date','signed_at'),('counterparty','counterparty'),('url','url'),('channel','channel'),('acceptance_mode','acceptance_mode'),('role','company_role_in_source'),('status','status'),('path','path'),('loc','folder')):
			H=pick(A,L)
			if I=='paper'and H not in('ours','theirs'):continue
			if H is not None:C[I]=H
		if A.get('doc_role')=='template':C['kind']='internal'
		C['is_agreement']=E.is_agreement(A);C['layer']=E.layer_of(A);C['weight']=E.LAYER_WEIGHT.get(str(A.get('doc_role')or''),1);J,K=pick(A,'counterparty'),str(pick(A,'signed_at','date')or'')[:4];G[B]=pick(A,'short_name')or(J+(' · '+K if K.isdigit()else'')if J else'')or first_line(F,60);C['short']=G[B];C['origin_label']=origin_label(A);D[B]=C
	for A in((m.get('market_research')or{}).get('sources')or[])+(m.get('market')or[]):
		B=pick(A,'source_id','id')
		if B and B not in D:D[B]={'label':pick(A,'title')or B,'name':pick(A,'title')or B,'kind':'external','url':pick(A,'url')or'','date':pick(A,'checked_at','date')or''}
	return D,G
def build_market(m):
	E=[]
	for A in((m.get('market_research')or{}).get('sources')or[])+(m.get('market')or[]):
		B=pick(A,'source_id','id')
		if not B:continue
		C={'id':B,'title':pick(A,'title')or B,'body':pick(A,'issuer','body')or'','url':pick(A,'url')or'','date':pick(A,'doc_date','checked_at','date')or''}
		for(G,H)in(('retrieved_at','retrieved_at'),('drafter_role','drafter_role'),('drafted_by','drafted_by')):
			F=pick(A,H)
			if F:C[G]=F
		D=A.get('supports')or A.get('topics')
		if isinstance(D,list)and D:C['supports']=D
		E.append(C)
	return E
def light(obj,rule_id,color,lang='he'):
	N=rule_id;K=lang;J=color;B=obj
	if not isinstance(B,dict):return
	C={};O=(pick(B,'position_en','pos_en')if K=='en'else None)or pick(B,'position','pos','text')
	if O:C['pos']=O
	L=B.get('match_criteria')or B.get('crit')or[];C['crit']=[str(A)for A in L]if isinstance(L,list)else[str(L)];C['evidence']=B.get('evidence')or[]
	for(G,P)in(('basis','basis'),('basis_note','basis_note'),('why','meaning'),('notes','notes'),('comments','comments'),('source_label','source_label')):
		D=pick(B,P)
		if D is not None:C[G]=D
	H=B.get('proposed_clause')
	if isinstance(H,dict)or isinstance(H,str)and H:C['clause'],C['clause_lang']=A.clause_text(H,K)
	M=B.get('basis_refs')
	if isinstance(M,list)and M:C['basis_refs']=M
	if B.get('basis')in('areo_proposal','market_standard'):
		C['label']=pick(B,'label')or TXT[K]['areo'];E=B.get('market_source_ids')
		if isinstance(E,list)and E:
			C['market_source_ids']=E
			if B.get('basis')=='market_standard'and len(E)<3:warn('%s %s: market_standard עם %d מקורות, נדרשים שלושה'%(N,J,len(E)))
		elif B.get('basis')=='market_standard':warn('%s %s: market_standard בלי market_source_ids'%(N,J))
	F=B.get('role_effects')
	if isinstance(F,dict):
		F={B:A for(B,A)in F.items()if A}
		if F:C['role_effects']=F
	for G in('as_discloser_effect','as_recipient_effect','company_effect'):
		D=B.get(G)
		if D:C[G]=D
	if J=='yellow':
		I=B.get('fallback_wording')
		if isinstance(I,dict)and I.get('text'):C['fallback_wording']={'text':I['text'],'source':I.get('source')or''}
	return C or None
def build_rules(m,cites,lang='he',extract=None):
	g=extract;R=lang;Q=cites;S,h=[],set();q={A.get('source_id'):A for A in m.get('source_log')or[]if isinstance(A,dict)};r=E.doc_index(g)if g else{};s=E.party_names(m);t=pick(m,'company_name')or'';u={A.get('rule_id')for A in m.get('rules')or[]if isinstance(A,dict)}
	for A in m.get('rules')or[]:
		D=pick(A,'rule_id','id')
		if not D:warn('כלל בלי rule_id נדלג');continue
		if D in h:warn('rule_id כפול: %s'%D)
		h.add(D);T=A.get('policy_rationale')or{};B={'id':D,'topic':(pick(A,'topic_name_en')if R=='en'else None)or pick(A,'topic_name','topic')or D,'issue':(pick(A,'clause_issue_en')if R=='en'else None)or pick(A,'clause_issue')or''}
		for(U,V)in(('num','clause_number'),('kind','clause_kind'),('they','counterparty_objective'),('pb','playbook_id'),('conf','confidence'),('why','why_address_topic'),('reg','regulatory_status'),('policy','policy_status'),('topic_en','topic_name_en')):
			I=pick(A,V)
			if I is not None:B[U]=I
		if A.get('walk_away')is True:B['walk_away']=True
		if A.get('client_concern')is True:B['client_concern']=True
		i,v=E.rationale_complete(A);B['rationale_complete']=i
		if T and i:B['rat']=T
		elif T:B['rat_hidden']=v
		W={};j=A.get('traffic_light')or A.get('tl')or{}
		for J in LIGHTS:
			X=light(j.get(J),D,J,R)
			if X:wording_checks(X,j.get(J)or{},D,J,s,t);W[J]=X
		if W:B['tl']=W
		K=A.get('proposed_clause')or{}
		if K:B['clause']=pick(K,'he','en')or'';B['clause_en']=K.get('en')or'';B['clause_lang']=K.get('source_language')or''
		Y=[]
		for L in A.get('legal_basis_layers')or[]:
			if L.get('statute'):Y.append({'law':L.get('statute')or'','ref':L.get('section')or'','meaning':first_line(pick(L,'meaning','effect')or'',220)})
		if Y:B['norms']=Y
		Z=[]
		for F in A.get('related_clause_impacts')or A.get('related_clauses')or A.get('impacts')or[]:
			M=pick(F,'related_rule_id','rule_id','ref')or''
			if not M or M==A.get('rule_id')or M not in u or not(pick(F,'impact','relation','effect')or'').strip():continue
			C=[A for A in F.get('evidence')or[]if isinstance(A,dict)and(A.get('quote')or'').strip()];k=pick(F,'direction')or'mutual';Z.append({'related_rule_id':M,'direction':k if k in('affects','affected_by','mutual')else'mutual','impact':pick(F,'impact','relation','effect')or'','action':pick(F,'action')or'','basis':'areo_proposal'if F.get('basis')=='areo_proposal'or not C else'corpus','evidence':[{'clause':A.get('clause_ref')or'','quote':first_line(A.get('quote')or'',400),'count':A.get('count')or 1}for A in C[:2]]})
		if Z:B['impacts']=Z
		l=[B for B in A.get('related_rule_ids')or[]if B and B!=A.get('rule_id')]
		if l:B['rel']=l
		G=A.get('presence_rule')or A.get('presence')
		if isinstance(G,dict)and G:B['presence']={'requirement':pick(G,'requirement')or'','missing_clause_color':pick(G,'missing_clause_color')or''}
		elif isinstance(G,str)and G:B['presence']={'requirement':G,'missing_clause_color':''}
		else:warn('%s: אין presence_rule. הסינון לפי נחיצות הסעיף לא יראה אותו'%D)
		a=A.get('activation_conditions')
		if isinstance(a,list)and a:B['trig']={'he':[str(A)for A in a],'en':[]}
		b,n=[],{}
		for c in A.get('evidence')or[]:
			N=src_id(pick(c,'source_ref','source_id'))
			if not N or N in n:continue
			n[N]=True;b.append({'source_id':N,'weight':pick(c,'weight')or'','note':pick(c,'note','tag')or''})
		if b:B['ev']=b
		B['ec']=E.derived_counts(A,m.get('source_log')or[]);O=A.get('fallback_origin')or{}
		if isinstance(O,dict)and O:
			P={A:basis_line.fallback_label(O,m,A)for A in('he','en')}
			if P['he']or P['en']:B['fallback_origin']={'label_he':P['he'],'label_en':P['en'],'baseline':O.get('baseline')or''}
		for C in A.get('evidence')or[]:
			o=pick(C,'evidence_id','id')or'c%d'%(len(Q)+1);d=pick(C,'track')
			if not d:warn('%s: ראיה %s בלי track, לא תיספר באחוז'%(D,o))
			e=pick(C,'source_ref','source_id')or'';H={'id':o,'rules':[D],'src':src_id(e),'text':pick(C,'quote','text')or'','ref':pick(C,'clause_ref','ref')or'','tag':pick(C,'tag')or'','side':pick(C,'side')or'pro'}
			if d:H['track']=d
			if'#'in e:H['para']=e
			for(U,V)in(('weight','weight'),('segment_id','segment_id')):
				I=pick(C,V)
				if I:H[U]=I
			f=q.get(H['src'])or{};H['ev_kind']=E.ev_kind(C,f,E.doc_for_source(f,r));p=pick(C,'paper')or f.get('paper')
			if p in('ours','theirs'):H['paper']=p
			Q.append(H)
		S.append(B)
	prune_constants(S,Q);return S
def wording_checks(one,raw,rid,color,names,company):
	H=company;G=names;D=raw;A=one;C=A.get('clause')or'';I=E.detect_lang(C)
	if I:A['clause_lang']=I
	else:A.pop('clause_lang',None)
	B=E.name_hits(C,G,H)
	for J in E.name_hits(A.get('pos')or'',G,H):
		if J not in B:B.append(J)
	if B:
		A['name_hits']=B
		if C:A['clause_generic']=E.generic_text(C,B)
		if A.get('pos'):A['pos_generic']=E.generic_text(A['pos'],B)
	M=' '.join(str(A.get(B)or'')for B in('pos','clause','why','notes'))
	if E.legal_claim(M):
		A['legal_claim']=True;F=[A for A in D.get('regulatory_refs')or D.get('sources')or[]if A];A['needs_verification']=not F
		if F:A['verify_refs']=F
	K=E.integrity_flags(C)
	if K:A['integrity']=K
	if color=='red':
		L,N=E.red_response(D)
		if L=='pointer':A['response']={'kind':'pointer','to':N}
		elif L=='wording':A['response']={'kind':'wording'}
		else:A['gap']=True;warn('%s red: אין נוסח תגובה ואין הפניה לנוסח החלופי. מוצג כפער'%rid)
CONSTANT_CANDIDATES='conf','reg','policy'
def prune_constants(rules,cites):
	B=cites;A=rules
	if len(A)>1:
		for C in CONSTANT_CANDIDATES:
			D={json.dumps(A.get(C),ensure_ascii=False,sort_keys=True)for A in A}
			if len(D)==1 and C in A[0]:
				for E in A:E.pop(C,None)
				warn('השדה %s זהה בכל הכללים ולכן אינו מוצג'%C)
	if len(B)>1:
		D={A.get('weight')for A in B}
		if len(D)==1 and'weight'in B[0]:
			for F in B:F.pop('weight',None)
			warn('משקל הציטוט זהה בכל הציטוטים ולכן אינו מוצג')
def build_segments(m,rules_by_id,lang='he'):
	H=[]
	for C in(m.get('segmentation_model')or{}).get('segments')or[]:
		B=pick(C,'segment_id','id')
		if not B:continue
		H.append({'segment_id':B,'label':pick(C,'segment_name','label','name')or B,'criteria':pick(C,'criteria','criterion')or'','status':pick(C,'status')or''})
		for A in C.get('variants')or[]:
			I=pick(A,'rule_id');J=rules_by_id.get(I)
			if not J:warn('ווריאנט בסגמנט %s מפנה לכלל %s שאינו בפלייבוק'%(B,I));continue
			D={'seg':B,'mode':pick(A,'negotiation_mode')or''};E={}
			for F in LIGHTS:
				K=light((A.get('traffic_light')or{}).get(F),B,F,lang)
				if K:E[F]=K
			if E:D['tl']=E
			L=A.get('segment_rationale')or A.get('policy_rationale')
			if L:D['rat']=L
			for G in('imposed_regime','clarification_positions','bid_conditions','clarification_record'):
				if A.get(G)not in(None,'',[],{}):D[G]=A[G]
			J.setdefault('variants',[]).append(D)
	return H
def build_queue(m):
	B=[]
	for A in m.get('validation_queue')or[]:B.append({'item_id':pick(A,'id','item_id')or'','issue':pick(A,'topic','issue')or'','question':pick(A,'question')or'','impact':pick(A,'why','impact')or'','scope':pick(A,'scope')or'','rule_id':pick(A,'rule_id')or'','segment_id':pick(A,'segment_id')or'','severity':pick(A,'severity')or'','rec':pick(A,'recommendation')or''})
	return B
URGENCY={'high':'high','critical':'high','urgent':'high','immediate':'high','גבוהה':'high','גבוה':'high','דחוף':'high','דחופה':'high','קריטית':'high','מיידי':'high','medium':'medium','בינונית':'medium','בינוני':'medium','low':'low','נמוכה':'low','נמוך':'low'}
def build_findings(m):
	B=[]
	for A in(m.get('company_findings')or[])+(m.get('template_findings')or[]):
		if not isinstance(A,dict):continue
		C=[URGENCY.get(str(A.get(B)or'').strip().lower())for B in('urgency','severity')];B.append({'title':pick(A,'topic','title','finding')or'','body':pick(A,'required_action','detail','body')or'','severity':next((A for A in C if A),'medium'),'refs':pick(A,'source_refs','clause_refs','refs')or[]})
	return B
def build_departments(m):
	A=[str(A).strip()for A in m.get('responsible_departments')or()if str(A or'').strip()];B=[{'name':A.get('name')or'','quote':A.get('quote')or'','source':A.get('source')or''}for A in m.get('departments_proposed')or()if isinstance(A,dict)and A.get('name')];C=[{'type':A.get('type')or'','department':A.get('department')or'','summary':A.get('summary')or'','source':A.get('source')or'','needs_verification':bool(A.get('needs_verification'))}for A in m.get('obligation_assignments')or()if isinstance(A,dict)and A.get('type')]
	if not(A or B or C):return
	return{'responsible':A,'proposed':B,'assignments':C}
def build_playbooks(m):
	B=[]
	for A in m.get('company_playbooks')or m.get('playbooks')or[]:
		C=pick(A,'playbook_id','id')
		if not C:continue
		B.append({'id':C,'family':pick(A,'family','contract_family_name')or'','role':pick(A,'role','company_role')or'','rules':A.get('rules')or 0,'segments':A.get('segments')or 0,'scanned':A.get('scanned')or A.get('agreement_units')or 0,'updated':pick(A,'updated','last_updated')or'','current':bool(A.get('current'))})
	return B
def approval_flags(m,rules,cells,st):
	F=set(st.get('approved_keys')or());I={pick(A,'rule_id','id'):A for A in m.get('rules')or[]}
	for D in rules:
		J=A.legal_review_tracks(I.get(D['id'])or{})
		for(G,B)in(D.get('tl')or{}).items():
			E=S.cell_key(D['id'],G);B['approved']=E in F;C=(cells or{}).get(E)or{}
			if B['approved']and isinstance(C,dict):
				if C.get('signer'):B['approved_by']=str(C.get('signer'))
				if C.get('approved_at'):B['approved_at']=str(C.get('approved_at'))
			if G in J and E not in F:B['legal_review_open']=True
			H=A.decision_slots('%s %s'%(B.get('pos')or'',B.get('clause')or''))
			if H:B['slots']=H
_GLOSSARY_HE=[(re.compile('(?<![א-ת])(ו?[בלמשכ]?)ה?קורפוס(?![א-ת])'),lambda m:m.group(1)+('הסכמים'if m.group(1)else'ההסכמים')),(re.compile('(?<![א-ת])([ושהכלב]{0,2})נגזר(ה|ת|ים|ות)? מ(ה?)'),lambda m:'%sמבוסס%s על %s'%(m.group(1),{'ה':'ת','ת':'ת'}.get(m.group(2)or'',m.group(2)or''),'ה'if m.group(3)else'')),(re.compile('(?<![א-ת])([ושהכלב]{0,2})נגזר(ה|ת|ים|ות)?(?![א-ת])'),lambda m:'%sמבוסס%s'%(m.group(1),{'ה':'ת','ת':'ת'}.get(m.group(2)or'',m.group(2)or''))),(re.compile('(?<![א-ת])טעונה (אישור|בדיקה)'),lambda m:'ממתינה ל'+m.group(1)),(re.compile('(?<![א-ת])טעונות (אישור|בדיקה)'),lambda m:'ממתינות ל'+m.group(1)),(re.compile('(?<![א-ת])טעונים (אישור|בדיקה)'),lambda m:'ממתינים ל'+m.group(1)),(re.compile('(?<![א-ת])טעון (אישור|בדיקה)'),lambda m:'ממתין ל'+m.group(1)),(re.compile('(?<![א-ת])הטעונים (אישור|בדיקה)'),lambda m:'הממתינים ל'+m.group(1)),(re.compile('(?<![א-ת])הטעונות (אישור|בדיקה)'),lambda m:'הממתינות ל'+m.group(1)),(re.compile('(?<![א-ת])(ה?)מסלולים(?![א-ת])'),lambda m:m.group(1)+'עמדות'),(re.compile('(?<![א-ת])(ו?[בלמשכ]?ה?)מסלול(?![א-ת])'),lambda m:m.group(1)+'עמדה')]
_GLOSSARY_EN=[(re.compile('\x08corpus\x08',re.I),'agreements'),(re.compile('\x08derived from\x08',re.I),'based on'),(re.compile('\x08needs approval\x08',re.I),'awaiting approval')]
_SKIP={'id','rule_id','src','source_id','source_ref','refs','related_rule_id','rules','seg','segment_id','item_id','evidence','ev','quote','text','basis_refs','market_source_ids','supports','pb','source','baseline','clause','clause_en','clause_lang','fallback_wording','slots','url','path','loc','proposed_clause','family_id','playbook_id','ls_key','slug','h'}
def voice_text(s,lang='he'):
	import html as C
	if not isinstance(s,str)or not s:return s
	if'&'in s:s=C.unescape(s)
	if re.search('[א-ת]',s):
		for(A,B)in _GLOSSARY_HE:s=A.sub(B,s)
	if lang=='en':
		for(A,B)in _GLOSSARY_EN:s=A.sub(B,s)
	return s
def _walk_voice(v,lang,key=''):
	A=lang
	if isinstance(v,dict):return{B:C if B in _SKIP else _walk_voice(C,A,B)for(B,C)in v.items()}
	if isinstance(v,list):return[B if key in _SKIP else _walk_voice(B,A,key)for B in v]
	return voice_text(v,A)if isinstance(v,str)else v
def _norm_ws(t):return re.sub('\\s+',' ',str(t or'')).strip()
def finish_payload(payload,lang='he'):
	B=payload
	for G in B.get('rules')or[]:
		E=G.get('tl')or{};A=E.get('red')
		if not A:continue
		for D in('green','yellow'):
			F=E.get(D)or{}
			if _norm_ws(A.get('clause'))and _norm_ws(A.get('clause'))==_norm_ws(F.get('clause')):A.setdefault('clause_dup',D)
			if _norm_ws(A.get('pos'))and _norm_ws(A.get('pos'))==_norm_ws(F.get('pos')):A.setdefault('pos_dup',D)
	for C in('rules','queue','templateFindings','coverage','assumptions','departments','reg','scope','meta'):
		if C in B:B[C]=_walk_voice(B[C],lang,C)
	return B
def build_gaps(m,rules,lang='he'):
	E,C=[],set();J={A['id']:A for A in rules}
	for A in m.get('profile_topics')or[]:
		if isinstance(A,dict)and A.get('evidence_in_corpus')is False and A.get('topic'):
			G=norm_key(A['topic'])
			if G not in C:C.add(G);E.append({'topic':A['topic'],'rule_id':A.get('rule_id')or'','origin':'profile','trigger':A.get('trigger')or''})
	for A in(m.get('scope_summary')or{}).get('core_topics')or[]:
		B=A.get('topic')if isinstance(A,dict)else A;D=(A.get('rule_id')if isinstance(A,dict)else'')or''
		if B and norm_key(B)not in C and(not D or D not in J):C.add(norm_key(B));E.append({'topic':B,'rule_id':D,'origin':(A.get('origin')if isinstance(A,dict)else'')or'client'})
	for F in m.get('rules')or[]:
		D=pick(F,'rule_id','id');H=F.get('traffic_light')or{};I={(H.get(A)or{}).get('basis')for A in LIGHTS if H.get(A)};K=any(A.get('track')in LIGHTS for A in F.get('evidence')or[])
		if I and I<={'areo_proposal','market_standard'}and not K:
			B=pick(F,'topic_name','topic')or D
			if norm_key(B)not in C:C.add(norm_key(B));E.append({'topic':B,'rule_id':D,'origin':'no_evidence'})
	return E
def norm_key(t):return re.sub('\\s+',' ',str(t or'')).strip().lower()
def _old_evidence_as_objects(m):
	for A in m.get('rules')or[]:
		if isinstance(A,dict)and isinstance(A.get('evidence'),list)and any(not isinstance(A,dict)for A in A['evidence']):A['evidence']=[A if isinstance(A,dict)else{'quote':str(A)}for A in A['evidence']if A not in(None,'')]
	return m
def convert(m,lang='he',model_path=None,profile=None,extract=None):
	C=extract;B=model_path;A=lang;m=_old_evidence_as_objects(m);H=[];F,M=build_sources(m)
	if C is None and B:C=E.find_extract(m,B)
	if not C:warn('אין קובץ חילוץ (--extract): סיווג הראיה של הציטוטים (ev_kind) הוא unknown')
	D=build_rules(m,H,A,C);N={A['id']:A for A in D};I=S.record_cells_for(m,B)if B else{};J=S.derive_status(m,I,lang=A);approval_flags(m,D,I,J);G=build_meta(m,A,J,profile);G['gaps']=build_gaps(m,D,A);G['sources_counted']={'agreements':sum(1 for A in F.values()if A.get('is_agreement')),'non_agreements':sum(1 for A in F.values()if A.get('kind')=='internal'and not A.get('is_agreement'))};K={'meta':G,'scope':scope_block(m,A),'sources':F,'friendly':M,'rules':D,'cites':H,'segments':build_segments(m,N,A),'precedents':m.get('previous_agreements_where_language_accepted')or[],'templateFindings':build_findings(m),'queue':build_queue(m)}
	for(O,L)in(('reg',m.get('regulatory_research')),('commercial',m.get('commercial')),('coverage',m.get('coverage')),('market',build_market(m)),('playbooks',build_playbooks(m)),('external_sources',m.get('external_sources')),('external_sources_table',m.get('external_sources_table')),('assumptions',m.get('assumptions')),('departments',build_departments(m)),('cross',m.get('cross_family_links'))):
		if L:K[O]=L
	return finish_payload(_scrub_payload(K,m,A),A)
_KEEP='quote','text','q','clause_text','verbatim','excerpt','id','rid','rule_id','ref','refs'
def _scrub_payload(payload,m,lang):
	B=voice_scrub.Scrubber(m,lang)
	def A(o):
		if isinstance(o,dict):return{B:C if B in _KEEP else A(C)for(B,C)in o.items()}
		if isinstance(o,list):return[A(B)for B in o]
		if isinstance(o,str)and' 'in o.strip():return B.text(o)
		return o
	return A(payload)
def index_models(data_dir):
	F=data_dir;B=os.path.join(F,'playbooks','index.json')
	if not os.path.exists(B):warn('אין %s (הרישום רץ אחרון). הדף נבנה מהמודל שנמסר, או מ-playbooks/*/playbook-model.json'%B);return
	C=json.load(io.open(B,encoding='utf-8'));H=C.get('playbooks')if isinstance(C,dict)else C;G=[]
	for A in H or[]:
		D=A.get('core_path')or A.get('path')
		if not D:warn('רשומה באינדקס בלי core_path: %s'%json.dumps(A,ensure_ascii=False)[:100]);continue
		E=os.path.join(F,os.path.dirname(D),'playbook-model.json')
		if not os.path.exists(E):warn('לרשומה %s אין playbook-model.json (%s), והיא אינה בסביבת העבודה'%(A.get('family_id')or D,E));continue
		G.append((A,E))
	return G
def folder_models(data_dir):
	A=os.path.join(data_dir,'playbooks');B=[]
	for C in sorted(os.listdir(A))if os.path.isdir(A)else[]:
		D=os.path.join(A,C,'playbook-model.json')
		if os.path.isfile(D):B.append(({'family_id':C},D))
	return B
def book_id(m,entry=None):return pick(m,'family_id','playbook_id')or pick(entry or{},'family_id')or'playbook'
def build_book(m,entry=None,lang='he',model_path=None,profile=None,extract=None):
	B=entry;A=convert(m,lang,model_path,profile,extract);C=book_id(m,B);D=(pick(A.get('scope')or{},'contract_families')or[{}])[0]or{};A['pb']={'id':C,'family':pick(D,'contract_family_name','label')or pick(B or{},'family_name')or C,'role':pick(D,'company_role')or pick(B or{},'company_role_code')or''}
	for E in A['rules']:E['pb']=C
	A.pop('playbooks',None);return A
def merge_books(books,current=None,company_key=None):
	A=books;B=current
	if not A:sys.exit('אין אף פלייבוק להציג')
	D=[A['pb']['id']for A in A]
	if B and B not in D:sys.exit('--current %s אינו באינדקס. הקיימים: %s'%(B,', '.join(D)))
	if not B:B=max(A,key=lambda b:str(b['meta'].get('updated')or''))['pb']['id']
	E=next(A for A in A if A['pb']['id']==B);C=json.loads(json.dumps(E));C['books']={A['pb']['id']:A for A in A};C['playbooks']=[{'id':A['pb']['id'],'family':A['pb']['family'],'role':A['pb']['role'],'rules':len(A['rules']),'segments':len(A.get('segments')or[]),'scanned':(A['meta'].get('build_path')or{}).get('n')or 0,'updated':A['meta'].get('updated')or'','status_label':A['meta'].get('status_label')or'','current':A['pb']['id']==B}for A in A];F=C['meta'].get('company')or company_key or'company';C['meta']['page_key']='playbooks_'+ls_key(F);return C
def main():
	C=argparse.ArgumentParser();C.add_argument('model',nargs='?',help='playbook-model.json, לפלייבוק אחד. עם --data: מצטרף לפלייבוקים שבאינדקס, וכשאין אינדקס הוא היחיד בדף');C.add_argument('out');C.add_argument('--data',help='תיקיית Areo-נתונים: כל הפלייבוקים שבאינדקס, בדף אחד');C.add_argument('--current',help='family_id של הפלייבוק שנפתח ראשון. ברירת מחדל: זה שעודכן אחרון');C.add_argument('--meta',help='שדות הצגה שאינם במודל, למשל הודעת הדגמה או docAccess');C.add_argument('--lang',choices=('he','en'),help='שפת הדף. בלעדיו: deliverable_language מהפרופיל או מהמודל, וברירת המחדל עברית');C.add_argument('--profile',help='פרופיל-לקוח.json: deliverable_language ו-display_language');C.add_argument('--extract',help='corpus-extract.json: ממנו נגזר סיווג הראיה של כל ציטוט (ev_kind). בלעדיו: coverage.extract_ref ליד המודל, ואחרת unknown');A=C.parse_intermixed_args();F=json.load(io.open(A.profile,encoding='utf-8'))if A.profile else None;O=json.load(io.open(A.extract,encoding='utf-8'))if A.extract else None
	if not A.model and not A.data:sys.exit('יש לתת מודל אחד, או --data לכל הפלייבוקים')
	try:guard_out(A.out,inputs=[A.model,A.profile,A.meta,A.extract])
	except OutputRefused as T:print('refused: %s'%T,file=sys.stderr);sys.exit(2)
	if A.data:
		E=[];G=index_models(A.data)
		if G is None and not A.model:
			G=folder_models(A.data)
			if not G:sys.exit('אין playbooks/index.json ואין playbook-model.json בתיקיות הסוגים של %s. תן את המודל שנבנה: build_workspace_payload.py <model> --data %s <out>'%(A.data,A.data))
		D=[(B,json.load(io.open(A,encoding='utf-8')),A)for(B,A)in G or[]];K=A.current
		if A.model:P=json.load(io.open(A.model,encoding='utf-8'));L=book_id(P);M=next((A for(A,B,C)in D if book_id(B,A)==L),None);D=[(A,B,C)for(A,B,C)in D if book_id(B,A)!=L]+[(M,P,A.model)];K=K or L
		U=resolve_lang(D[0][1]if D else{},F,A.lang)
		for(M,H,V)in D:E.append(build_book(H,M,U,V,F,O))
		B=merge_books(E,current=K)
	else:H=json.load(io.open(A.model,encoding='utf-8'));B=convert(H,resolve_lang(H,F,A.lang),A.model,F,O)
	if A.meta:
		Q=json.loads(io.open(A.meta,encoding='utf-8').read());R='id','slug','ls_key','title','wizard_href','page_key';E=list((B.get('books')or{}).values())
		for(I,S)in(Q.get('meta')or Q).items():
			if not E or I not in R:B['meta'][I]=S
			for W in E:
				if I not in R:W['meta'][I]=S
	io.open(A.out,'w',encoding='utf-8').write(json.dumps(B,ensure_ascii=False,indent=2));print('נכתב %s: %d סעיפים, %d ציטוטים, %d מקורות, %d סגמנטים'%(A.out,len(B['rules']),len(B['cites']),len(B['sources']),len(B['segments'])))
	if B.get('books'):
		print('פלייבוקים בדף: %d'%len(B['books']))
		for J in B['playbooks']:print('  %s %s · %s (%d סעיפים)'%('*'if J['current']else' ',J['family'],J['role'],J['rules']))
	print('שפת הדף: %s'%B['meta'].get('lang'));N=B['meta'].get('build_path')
	if N:print('פס הבסיס: %d %s, מסלול %s'%(N['n'],basis_line.docs(B['meta'].get('corpus_status')),N['path']))
	print('הבא: python3 validate_data.py --data %s'%A.out)
if __name__=='__main__':main()
