# -*- coding: utf-8 -*-
# Copyright (c) Areo. All rights reserved. Licensed under the terms at https://areo.co.il/legal/terms
import datetime as dt,re
from clm import catalog,dates
from clm.i18n import t
RESTRICTION_CODES='exclusivity','non_compete','mfn'
COC_CODES='change_of_control','assignment'
BOUND='contracting','both'
NOT_RELEVANT_TERMS='indefinite','until_event','project','none'
LEGAL_FORMS={'בעמ','ltd','inc','llc','gmbh','bv','sa','limited'}
OPTION_NOTE='הסיום נשאר עד אישור מימוש או תיקון חתום'
OPTION_NOTE_EN='The end stands until an exercise is confirmed or an amendment is signed'
add_months=dates.add_months
def norm_entity(s):return' '.join(str(s or'').replace('״','"').replace('׳',"'").split()).casefold()
def count(n,he_one,he_many,en_one,en_many):
	if n==1:return t(he_one,'1 '+en_one)
	return t('%d %s'%(n,he_many),'%d %s'%(n,en_many))
def _by(clause):A=clause;return t(' לפי %s',' under %s')%A if A else''
def _posint(v):return isinstance(v,int)and not isinstance(v,bool)and v>0
def _names(x):return[x]if isinstance(x,str)else[A for A in x or[]if isinstance(A,str)]
def _tokens(s):s=re.sub('\\([^)]*\\)',' ',norm_entity(s));s=re.sub('[.\\"\'`]','',s);return[A for A in re.sub('[^\\w]+',' ',s).split()if A not in LEGAL_FORMS]
def _run_in(short,long):A=short;return any(long[B:B+len(A)]==A for B in range(len(long)-len(A)+1))
def _same(a,b):
	a,b=_tokens(a),_tokens(b)
	if a and a==b:return len(' '.join(a))>=3
	A,B=(a,b)if len(a)<=len(b)else(b,a)
	if not A or len(A)==1 and len(A[0])<4:return False
	return _run_in(A,B)
def resolve_party(raw,name,company,counterparty,role_confirmed):
	A=raw
	if A=='both':return'both',True
	B=any(_same(name,A)for A in _names(company));C=_same(name,counterparty)
	if B!=C:return('contracting',True)if B else('counterparty',True)
	if B and C:return'unknown',False
	if A in('contracting','counterparty'):return A,bool(role_confirmed)
	return'unknown',False
def computed_end(term,start):
	B=start;A=term
	if not A or A.get('kind')!='fixed'or not _posint(A.get('initial_months'))or not B:return None,None
	C=dates.parse(B);D=dates.term_end_after(C,A['initial_months']);return D.isoformat(),t('מחושב: תחילה %s ועוד %d חודשים, פחות יום%s','Computed: start %s plus %d months, less one day%s')%(dates.fmt(C),A['initial_months'],_by(A.get('clause')))
def start_for(term,dts):A=(term or{}).get('starts_on')or'start';return dts.get(A)if A in('start','signed')else None
def roll(end_iso,renewal,today):
	F=today;E=end_iso;B=renewal
	if not E or not B or B.get('kind')!='auto'or not _posint(B.get('period_months')):return None,0,None
	D,G,H=dates.parse(E),B['period_months'],B.get('max_count');C,A=D,0
	while C<F and(H is None or A<H):A+=1;C=dates.add_months_eom(D,G*A)
	if not A:return None,0,None
	I=t('מחושב: %s ועוד %s של %s%s','Computed: %s plus %s of %s%s')%(dates.fmt(D),count(A,'חידוש אחד','חידושים','renewal','renewals'),count(G,'חודש אחד','חודשים','month','months'),_by(B.get('clause')))
	if C<F:return C.isoformat(),A,I+t('; הגיע למספר החידושים המרבי (%d); לאמת את מצב ההסכם',"; reached the maximum number of renewals (%d); confirm the agreement's status")%A
	return C.isoformat(),A,I+t('; לאמת שההסכם התחדש','; confirm that the agreement renewed')
def current_end(end_iso,term,renewal,today,signed=True):
	B=renewal;A=end_iso
	if signed:
		C,E,D=roll(A,B,today)
		if C:return C,{'kind':'auto_renewal','note':D},D
	if(term or{}).get('kind')=='indefinite'and not A:return None,{'kind':'indefinite','note':t('ללא הגבלת זמן','No end date')},None
	if(B or{}).get('kind')in('option','mutual')and A:return A,{'kind':'option_pending','note':t(OPTION_NOTE,OPTION_NOTE_EN)},None
	return None,None,None
def max_end(term,renewal,end_iso,head_events):
	C=end_iso;B=term
	if(B or{}).get('max_end'):return B['max_end'],'extracted',t('לפי %s','Under %s')%B['clause']if B.get('clause')else''
	A=renewal or{}
	if C and A.get('kind')in('auto','option')and _posint(A.get('period_months'))and _posint(A.get('max_count')):F=dates.add_months_eom(dates.parse(C),A['period_months']*A['max_count']);return F.isoformat(),'derived',t('מחושב: %s ועוד %s של %s','Computed: %s plus %s of %s')%(dates.fmt(dates.parse(C)),count(A['max_count'],'תקופה אחת','תקופות','period','periods'),count(A['period_months'],'חודש אחד','חודשים','month','months'))
	D=[A for A in head_events if A['event_code']=='term_end'and A.get('term_role')=='max_end'and not A.get('relative')and A.get('contract_date_original')and A.get('occurrence')!='passed']
	if D:E=max(D,key=lambda x:x['contract_date_original']);return E['contract_date_original'],'deadline',t('לפי המועד: ','From the date: ')+E['label']
	return None,None,None
def survival_end(events):
	A=[A for A in events if A['event_code']=='post_term'and not A.get('relative')and A.get('contract_date_original')and A.get('occurrence')!='passed']
	if not A:return None,None
	B=max(A,key=lambda x:x['contract_date_original']);return B['contract_date_original'],B['label']
def signatories(rows,company,counterparty,role_confirmed):
	B=[]
	for A in rows or[]:C,D=resolve_party(A.get('party'),A.get('party_name'),company,counterparty,role_confirmed);B.append({'party':C,'party_certain':D,'party_name':A.get('party_name'),'name':A.get('name'),'role':A.get('role'),'date':A.get('date'),'status':A.get('status')})
	return B
def _party_of(x,field,name_field,company,counterparty,confirmed):
	A=x.get(field)
	if A=='none':return'none',True
	B,C=resolve_party(A,x.get(name_field),company,counterparty,confirmed);return None if A is None and B=='unknown'else B,C
def agreement_fields(ext,rf,company,counterparty,confirmed):
	J=confirmed;I=counterparty;H=company
	def C(x):return rf(x.get('clause'),x.get('quote'))
	B={'term':None,'renewal':None,'exit':None,'jurisdiction':None,'payment_terms':None};D,A,E,G,F=(ext.get(A)for A in('term','renewal','exit','jurisdiction','payment_terms'))
	if D:B['term']={'kind':D.get('kind'),'initial_months':D.get('initial_months'),'starts_on':D.get('starts_on'),'trigger':D.get('trigger'),'refs':C(D)}
	if A:M,K=_party_of(A,'holder','holder_name',H,I,J);B['renewal']={'kind':A.get('kind'),'period_months':A.get('period_months'),'max_count':A.get('max_count'),'holder':M,'holder_certain':K,'holder_name':A.get('holder_name'),'notice_days':A.get('notice_days'),'clause':A.get('clause'),'refs':C(A)}
	if E:N,K=_party_of(E,'who','who_name',H,I,J);B['exit']={'who':N,'who_certain':K,'who_name':E.get('who_name'),'notice_days':E.get('notice_days'),'min_commitment_months':E.get('min_commitment_months'),'refs':C(E)}
	if G:B['jurisdiction']={'court':G.get('court'),'exclusive':G.get('exclusive'),'refs':C(G)}
	if F:B['payment_terms']={'days':F.get('days'),'basis':F.get('basis'),'text':F.get('text'),'refs':C(F)}
	L=ext.get('signatories')or[];B['signatories']=signatories(L,H,I,J)
	for(O,P)in zip(B['signatories'],L):O['refs']=C(P)
	return B
def facts(sources,rf):return[{'code':A.get('code'),'label':A.get('label'),'value':A.get('value'),'file':B,'refs':rf(A.get('clause'),A.get('quote'),B)}for(B,C)in sources for A in C.get('facts')or[]]
def term_passed(state,dts,current,today):
	B=current;A=state;C=B if B is not None else dts.get('end')
	if A=='in_force'and C and dates.parse(C)<today:return'term_passed_unverified'
	return A
def missing_party_sides(sigs):
	if not sigs:return[]
	A={A.get('party')for A in sigs if A.get('party_certain')};return[B for(B,C)in((t('חותמים לצד שכנגד','Signatories for the other side'),'counterparty'),(t('חותמים לחברה','Signatories for the company'),'contracting'))if C not in A]
def key_clause_fields(row,company,counterparty,confirmed,today):A=row;D,E=resolve_party(A.get('bound_party'),A.get('bound_party_name'),company,counterparty,confirmed);B=A.get('norm')if isinstance(A.get('norm'),dict)else None;C=B.get('until')if B and isinstance(B.get('until'),str)and B.get('until')else None;return{'bound_party':D,'bound_party_certain':E,'bound_party_raw':A.get('bound_party'),'bound_party_name':A.get('bound_party_name'),'stance':A.get('stance')or'set','norm':B,'active_until':C,'active':C is None or C>=today.isoformat()}
def _requires(norm):
	A=norm
	if not isinstance(A,dict):return
	B,C=A.get('requires'),A.get('consent_required')
	if B in('consent','notice')or C is True:return True
	if B in('none','termination_right')or C is False:return False
def _until(row):
	B=row;A=B.get('active_until')
	if A is None and isinstance(B.get('norm'),dict):A=B['norm'].get('until')
	return A if isinstance(A,str)and A else None
def _active(row,today):A=_until(row);return A is None or A>=today.isoformat()
def _order(row,party,today):A=party;B=_until(row);return 0 if A=='contracting'else 1 if A=='both'else 2,not _active(row,today),B is None,B or''
def registers(agreements,key_clauses,checked_ids,today):
	L=checked_ids;G=today;S='restrictions','restrictions_review','change_of_control','change_of_control_review'
	if not L:return dict({A:None for A in S},restriction_details=None)
	T=catalog.load_key_clauses();U={A['id']for A in agreements if A.get('signature')!='signed_unverified'};I={}
	for A in key_clauses:
		if A.get('agreementId')in L and A.get('agreementId')not in U and(A.get('stance')or'set')=='set':I.setdefault(A['agreementId'],[]).append(A)
	B={'restrictions':{},'change_of_control':{}};E={'restrictions':set(),'change_of_control':set()}
	for(D,J)in I.items():
		for A in J:
			H,K=A.get('bound_party')or'unknown',bool(A.get('bound_party_certain'));M=H in BOUND and K
			if A.get('clause_code')in RESTRICTION_CODES:
				if not _active(A,G):continue
				C='restrictions';F='count'if M else'skip'if H=='counterparty'and K else'review'
			elif A.get('clause_code')in COC_CODES:
				C='change_of_control';N=_requires(A.get('norm'))
				if N is False or H=='counterparty'and K:F='skip'
				elif N is True and M:F='count'
				else:F='review'
			else:continue
			if F=='count':O=_order(A,H,G);B[C][D]=min(B[C].get(D,O),O)
			elif F=='review':E[C].add(D)
	for C in B:E[C]-=set(B[C])
	P={}
	for D in sorted(set(B['restrictions'])|E['restrictions']):J=[A for A in I.get(D,[])if A.get('clause_code')in RESTRICTION_CODES];Q=[{'code':A['clause_code'],'label':T.get(A['clause_code'],A['clause_code']),'bound_party':A.get('bound_party')or'unknown','bound_party_certain':bool(A.get('bound_party_certain')),'active_until':A.get('active_until'),'active':_active(A,G),'summary':A.get('summary'),'refs':list(A.get('refs')or[])}for A in J];Q.sort(key=lambda d:(_order(d,d['bound_party'],G),d['code'],str(d['summary']or'')));P[D]=Q
	def R(grp):return sorted(B[grp],key=lambda aid:(B[grp][aid],aid))
	return{'restrictions':R('restrictions'),'restrictions_review':sorted(E['restrictions']),'change_of_control':R('change_of_control'),'change_of_control_review':sorted(E['change_of_control']),'restriction_details':P}
SIDE_WORDS={'provider':{'ספק','ספקית','נותן','נותנת','מעבד','מעבדת','מחזיק','מחזיקה','קבלן','קבלנית','יועץ','יועצת','משכיר','משכירה','מחכיר','מחכירה','מוכר','מוכרת','מעניק','מעניקה','מלווה','מבטח','מבטחת','עובד','עובדת','provider','supplier','vendor','processor','subprocessor','sub-processor','contractor','consultant','licensor','lessor','landlord','seller','lender','insurer','franchisor','employee','manufacturer'},'customer':{'לקוח','לקוחה','מזמין','מזמינה','שוכר','שוכרת','חוכר','חוכרת','קונה','רוכש','רוכשת','לווה','מבוטח','מבוטחת','זכיין','זכיינית','מעסיק','מעסיקה','customer','client','buyer','purchaser','licensee','lessee','tenant','borrower','insured','franchisee','employer','controller','subscriber'}}
SIDE_PHRASES={'customer':('בעל המאגר','בעל השליטה','מקבל השירות','מקבלת השירות'),'provider':('נותן השירות','נותנת השירות','service provider')}
def role_side(text):
	B=text
	if not isinstance(B,str)or not B.strip():return
	D=B.replace('״','"').lower();C={A for(A,B)in SIDE_PHRASES.items()if any(A in D for A in B)}
	for A in re.findall('[\\w\\-]+',D):
		for E in(A,A[1:]if A[:1]in'הו'and len(A)>3 else A,A[2:]if A[:2]=='וה'else A):
			for(F,G)in SIDE_WORDS.items():
				if E in G:C.add(F)
	return C.pop()if len(C)==1 else None
def side_conflict(pb_role,ext):
	C=ext;A=pb_role;B=role_side(A)
	if not B:return''
	F=C.get('counterparty')or{};G,D=F.get('role'),C.get('contracting_role')
	if role_side(G)==B:return t('בהסכם, %s מוגדר כ"%s", וזה הצד שהפלייבוק מייחס לחברה: %s','In the agreement, %s is named "%s", which is the side the playbook gives the company: %s')%(F.get('name')or t('הצד שכנגד','the other side'),G,A)
	if role_side(D)and role_side(D)!=B:return t('בהסכם, החברה מוגדרת כ"%s", והפלייבוק מייחס לה צד אחר: %s','In the agreement, the company is named "%s", and the playbook gives it another side: %s')%(D,A)
	E=C.get('our_role')or{}
	if E.get('source')in('suggested','none')and role_side(E.get('value'))not in(None,B):return t('ההשערה מהחילוץ (%s) שונה מצד החברה בפלייבוק (%s)',"Our reading of the agreement (%s) differs from the company's side in the playbook (%s)")%(E['value'],A)
	return''
