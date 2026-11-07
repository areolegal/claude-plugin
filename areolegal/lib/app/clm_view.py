# -*- coding: utf-8 -*-
# Copyright (c) Areo. All rights reserved. Licensed under the terms at https://areo.co.il/legal/terms
import argparse,datetime as _dt,json,os,sys
from pathlib import Path
MARKER='/*__AREO_CLM__*/null'
HERE=Path(__file__).resolve().parent
TEMPLATE=HERE.parent.parent/'ui'/'app'/'clm.html'
PROFILE='פרופיל-לקוח.json'
DOC_KIND={'signed':'חתום','draft':'טיוטה','negotiation_version':'גרסת משא ומתן','template':'תבנית','amendment':'תיקון','schedule':'נספח','order':'הזמנת עבודה','non_agreement':'מסמך שאינו הסכם'}
NSTAGE={'request':'draft','drafting':'draft','with_cp':'with_them','comments':'theirs','final':'sign','internal':'sign','signing':'sign'}
RENEWAL_CODES='term_end','auto_renewal','nonrenewal_notice','option_extend'
FLAGS=[['auto_renewal','חידוש אוטומטי'],['change_of_control','שינוי שליטה'],['restriction','מגבלות על החברה'],['foreign_law','דין זר'],['data_abroad','מידע אישי בחו"ל'],['guarantee','ערבות שנתנו']]
CUR={'ILS':'₪','USD':'$','EUR':'€','GBP':'£'}
PERIOD={'monthly':'לחודש','annual':'לשנה','חודשי':'לחודש','שנתי':'לשנה'}
DIRECTION={'given':'שנתנו','received':'שקיבלנו','policy':'פוליסה של החברה'}
OUTCOME_RENEW=['ההסכם התחדש','נמסרה הודעה, ההסכם הסתיים','לא רלוונטי']
OUTCOME_OPTION=['מומש','פקע','לא רלוונטי']
OPTIONS={'renewal_verify':['ההסכם התחדש','ההסכם הסתיים'],'missing_core':['נבדק ולא נמצא','להשלים מהמקור'],'verify_critical':['המועד אומת מול ההסכם','המועד שגוי'],'amendment_unconfirmed':['התיקון נחתם','התיקון לא נחתם'],'signing_unverified':['נחתם','לא נחתם']}
DEFAULT_OPTIONS=['אושר','לא נכון']
def _load(path):
	try:
		with open(str(path),encoding='utf-8-sig')as A:return json.load(A)
	except(OSError,ValueError,UnicodeDecodeError):return
def _s(v):return str(v).strip()if v is not None else''
def _list(v):return v if isinstance(v,list)else[]
def _dict(v):return v if isinstance(v,dict)else{}
def _fmt_date(iso):
	try:A=_dt.date.fromisoformat(_s(iso)[:10])
	except ValueError:return''
	return'%d.%d.%d'%(A.day,A.month,A.year)
def _money(value,currency):
	B=currency
	try:A=float(value)
	except(TypeError,ValueError):return''
	C='{:,.0f}'.format(A)if A==int(A)else'{:,.2f}'.format(A);D=CUR.get(_s(B).upper(),_s(B));return(C+' '+D).strip()
def _playbooks(data_dir):
	A=data_dir;G=_load(A/'playbooks'/'index.json');H=_list(_dict(G).get('playbooks'));C=[]
	for B in H:
		if not isinstance(B,dict):continue
		D={};E=_s(B.get('core_path'))
		if E:
			for I in(A,A/'playbooks'):
				F=I.joinpath(*E.replace('\\','/').split('/'))
				if F.exists():D=_dict(_load(F));break
		C.append((B,D))
	return C
def _norm(s):return' '.join(_s(s).split()).casefold()
def _pb_for(agr,playbooks):
	C=playbooks;D,E=_s(agr.get('type_code')),_norm(agr.get('type_label'))
	for(A,B)in C:
		if D and D in(_s(A.get('family_code')),_s(A.get('type_code')),_s(B.get('family_code'))):return A,B
	for(A,B)in C:
		F=[A.get('family_name')]+_list(A.get('family_aliases'))
		if E and E in[_norm(A)for A in F if A]:return A,B
def _pb_name(r,core):B=next((A for A in _list(core.get('contract_families'))if isinstance(A,dict)),{});A=_s(r.get('family_name'))or _s(B.get('contract_family_name'))or _s(r.get('family_id'));C=_s(core.get('company_role'))or _s(B.get('company_role'));return'%s (%s)'%(A,C)if A and C else A
def _rule_key(r,rule):return'%s/%s'%(_s(r.get('family_id'))or _s(r.get('family_code')),rule)
def _topics(playbooks):
	C={}
	for(E,D)in playbooks:
		for A in _list(D.get('clauses')or D.get('rules')):
			if not isinstance(A,dict)or not _s(A.get('id')):continue
			B=lambda t:_s(_dict(A.get(t)).get('position'));C[_rule_key(E,_s(A.get('id')))]={'name':_s(A.get('title')or A.get('clause_issue'))or _s(A.get('id')),'g':B('green')or _s(A.get('preferred_wording')),'y':B('yellow')or _s(A.get('fallback_wording')),'r':B('red')or _s(A.get('red_line'))}
	return C
def _value(a):
	A=_dict(a.get('value'));D=[]
	for B in _list(A.get('components')):
		if not isinstance(B,dict):continue
		F=_money(B.get('value'),B.get('currency'))
		if not F:continue
		D.append(('%s: %s %s'%(_s(B.get('component')),F,PERIOD.get(_s(B.get('period')),''))).strip())
	E='; '.join(D);G=_dict(A.get('annual_by_currency'));C=', '.join('%s לשנה'%_money(B,A)for(A,B)in sorted(G.items())if _money(B,A))
	if not C and A.get('total')is not None:C=_money(A.get('total'),A.get('total_currency')or A.get('currency'));E=E or('סכום כולל: '+C if C else'')
	return E,C or(D[0].split(': ',1)[-1]if D else'')
def _law(a):A,B=_s(a.get('governing_law')),_s(_dict(a.get('jurisdiction')).get('court'));return', '.join(A for A in(A,B)if A)
def _renewal(a):
	A=_dict(a.get('renewal'))
	if A.get('kind')not in('auto','option','mutual'):return
	return{'kind':A['kind'],'months':A.get('period_months'),'notice':A.get('notice_days'),'clause':_s(A.get('clause'))}
def _quote(refs,fn):
	for B in _list(refs):
		A=_s(_dict(fn.get(B)).get('quote'))
		if A:return A
	return''
def _flags(a,kcs,guarantees,registers):
	B=registers;A=[];C=a['id'];D={_s(A.get('clause_code'))for A in kcs if A.get('stance')!='expressly_none'}
	if _dict(a.get('renewal')).get('kind')=='auto':A.append('auto_renewal')
	if C in _list(B.get('change_of_control'))or'change_of_control'in D:A.append('change_of_control')
	if C in _list(B.get('restrictions')):A.append('restriction')
	if a.get('law_class')=='foreign':A.append('foreign_law')
	if'data_transfer'in D:A.append('data_abroad')
	if any(A.get('direction')=='given'for A in guarantees):A.append('guarantee')
	return A
def _security(guarantees):
	B=[]
	for A in guarantees:
		C=[_s(A.get('title'))or _s(A.get('kind')),_s(A.get('amount'))]
		if A.get('expiry'):C.append('עד '+_fmt_date(A['expiry']))
		E=' '.join(A for A in C if A);D=DIRECTION.get(_s(A.get('direction')));B.append(E+(' (%s)'%D if D else''))
	return'; '.join(A for A in B if A)
def _options(item,events):
	B=item.get('kind')
	if B=='outcome':
		A=_s(_dict(events.get(item.get('eventId'))).get('event_code'))
		if A in('nonrenewal_notice','term_end','auto_renewal'):return list(OUTCOME_RENEW)
		if A.startswith('option')or A=='first_refusal':return list(OUTCOME_OPTION)
		return['בוצע','לא בוצע','לא רלוונטי']
	return list(OPTIONS.get(B,DEFAULT_OPTIONS))
def _top_folder(path):A=_s(path).replace('\\','/').split('/');return A[0]if len(A)>1 and A[0]else''
def page_data(data_dir):
	I=data_dir;I=Path(I);C=_dict(_load(I/'clm-data.json'));N=_dict(_load(I/PROFILE));m=_playbooks(I);O=_dict(C.get('meta'));U={A.get('n'):A for A in _list(C.get('footnotes'))if isinstance(A,dict)};y={A.get('id'):A for A in _list(C.get('documents'))if isinstance(A,dict)};n=_dict(C.get('key_clause_labels'));o=_dict(C.get('registers'));p,V={},{}
	for E in _list(C.get('key_clauses')):
		if isinstance(E,dict):p.setdefault(E.get('agreementId'),[]).append(E)
	for W in _list(C.get('guarantees')):
		if isinstance(W,dict):V.setdefault(W.get('agreementId'),[]).append(W)
	P,q,J,K,X=[],[],{},{},[];Y={}
	for D in _list(C.get('timeline')):
		if isinstance(D,dict)and D.get('date'):Y[D.get('agreementId')]=max(Y.get(D.get('agreementId'),''),_s(D['date']))
	for A in _list(C.get('agreements')):
		if not isinstance(A,dict)or not A.get('id'):continue
		H=_s(A.get('type_code'))or _s(A.get('type_label'))or'other';Q=_pb_for(A,m)
		if H not in J:J[H]={'code':H,'label':_s(A.get('type_label'))or _s(A.get('family'))or H,'playbook':_pb_name(*Q)if Q else None,'owner':{'lawyer':'','business':'','backup':''}}
		G=_s(A.get('counterparty'))
		if G and G not in K:z={B:A for(B,A)in(('reg',_s(A.get('counterparty_id'))),('addr',_s(A.get('counterparty_notice_address'))))if A};K[G]=z
		elif G and A.get('counterparty_notice_address')and not K[G].get('addr'):K[G]['addr']=_s(A['counterparty_notice_address'])
		Z=[]
		for A0 in _list(A.get('doc_ids')):
			R=_dict(y.get(A0));S=_s(R.get('file'))
			if not S:continue
			Z.append({'file':S.replace('\\','/').split('/')[-1],'path':S,'kind':DOC_KIND.get(_s(R.get('doc_kind')),_s(R.get('doc_kind'))),'date':_s(R.get('date'))or None});a=_top_folder(S)
			if a and a not in X:X.append(a)
		b=_s(A.get('handling_stage'))
		if b:
			if b in NSTAGE:q.append({'id':A['id'],'cp':G,'type':H,'title':_s(A.get('title')),'stage':NSTAGE[b],'round':0,'since':Y.get(A['id'])or next((A['date']for A in Z if A['date']),None),'waiting':_s(A.get('waiting_on'))or None,'open':0,'red':0,'next':'','value':''})
			continue
		r=p.get(A['id'],[]);s=[]
		for E in r:c=_s(E.get('clause_code'));d=_s(E.get('policy_match'))or'not_compared';e=_s(E.get('policy_rule'));s.append({'code':c,'label':_s(n.get(c))or c,'summary':_s(E.get('summary')),'clause':_s(E.get('clause')),'quote':_quote(E.get('refs'),U),'policy':d if d in('match','differs')else'not_compared','rule':(_rule_key(Q[0],e)if Q else e)if e and d in('match','differs')else None})
		A1,A2=_value(A);T=_dict(A.get('dates'));f=_dict(A.get('our_role'));P.append({'id':A['id'],'number':_s(A.get('number')),'title':_s(A.get('title')),'type':H,'cp':G,'role':_s(f.get('value'))if f.get('confirmed')else'','role_src':_s(f.get('source')),'state':_s(A.get('agreement_state'))or None,'signed':T.get('signed')or None,'end':T.get('current_end')or T.get('end')or None,'end_note':_s(_dict(T.get('current_end_basis')).get('note')),'renewal':_renewal(A),'value':A1,'value_short':A2,'law':_law(A),'pay':_s(_dict(A.get('payment_terms')).get('text')),'security':_security(V.get(A['id'],[])),'docs':Z,'parent':None,'kc':s,'file':_s(A.get('file')),'not_found':[_s(n.get(A))or _s(A)for A in(A.get('clause_code')if isinstance(A,dict)else A for A in _list(A.get('key_clauses_not_found')))if A],'flags':_flags(A,r,V.get(A['id'],[]),o)})
	g={A['id']for A in P};t={A.get('id'):A for A in _list(C.get('events'))if isinstance(A,dict)};u=[]
	for B in _list(C.get('events')):
		if not isinstance(B,dict)or not B.get('id')or B.get('agreementId')not in g or B.get('superseded_by'):continue
		u.append({'id':B['id'],'agr':B['agreementId'],'label':_s(B.get('label')),'date':B.get('date')or None,'act_by':B.get('act_by')or None,'action':_s(B.get('action')),'if_nothing':_s(B.get('if_nothing')),'clause':_s(B.get('clause')),'quote':_quote(B.get('refs'),U),'obligor':_s(B.get('obligor'))or None,'critical':bool(B.get('critical')),'kind':_s(B.get('category')),'renewal':_s(B.get('event_code'))in RENEWAL_CODES,'trigger':_s(B.get('trigger')),'state':_s(B.get('state'))or None,'state_note':_s(B.get('state_note'))})
	v=[]
	for F in _list(C.get('review_queue')):
		if not isinstance(F,dict)or not F.get('id'):continue
		w=_dict(t.get(F.get('eventId')));A3=F.get('agreementId')if F.get('agreementId')in g else None;v.append({'id':F['id'],'kind':_s(F.get('kind')),'group':_s(F.get('group')),'agr':A3,'text':_s(F.get('text')),'quote':_quote(w.get('refs'),U),'clause':_s(w.get('clause')),'options':_options(F,t)})
	h=_dict(C.get('catalog'));i=[]
	for B in _list(C.get('events')):
		j=_s(_dict(B).get('event_code'))
		if j and j not in i:i.append(j)
	A4=[{'code':A,'label':_s(_dict(h.get(A)).get('label'))or A,'days':_dict(h.get(A)).get('lead_days')}for A in i if _dict(h.get(A)).get('lead_days')is not None];x=_s(O.get('company'))or _s(N.get('organization_name'));L=[]
	if C:
		L.append({'ok':bool(N),'label':'פרופיל החברה','detail':_s(N.get('organization_name'))or x if N else'לא נמצא פרופיל-לקוח.json בתיקיית הנתונים'})
		for D in J.values():
			M=sum(1 for A in P if A['type']==D['code'])
			if not M:continue
			if D['playbook']:L.append({'ok':True,'label':'פלייבוק ל'+D['label'],'detail':'הסכם אחד מושווה אליו'if M==1 else'%d הסכמים מושווים אליו'%M})
			else:L.append({'ok':False,'label':'אין פלייבוק ל'+D['label'],'detail':'הסכם אחד בלי השוואה למדיניות'if M==1 else'%d הסכמים בלי השוואה למדיניות'%M,'action':'לבנות פלייבוק'})
		k=[A for A in _list(o.get('key_clauses_unchecked'))if A in g]
		if k:L.append({'ok':False,'label':'סעיפי מפתח שלא נבדקו במלואם','detail':'בהסכם אחד'if len(k)==1 else'ב-%d הסכמים'%len(k)})
	l=[]
	for D in J.values():
		if D['playbook']and D['playbook']not in l:l.append(D['playbook'])
	return{'files':{},'texts':{},'docAccess':{'mode':'local','baseUrl':''},'flags':[list(A)for A in FLAGS],'negotiations':q,'cpinfo':K,'emails':{},'meta':{'company':x,'built':_s(O.get('last_updated')or O.get('generated_at'))[:10],'files':O.get('files_scanned')or 0,'folders':X},'types':list(J.values()),'agreements':P,'tasks':u,'review':v,'readiness':L,'lead':A4,'topics':_topics(m),'playbook_name':', '.join(l)}
def inject(template_text,data):
	B=template_text
	if B.count(MARKER)!=1:raise ValueError('התבנית אינה מכילה את הסמן %s פעם אחת'%MARKER)
	A=json.dumps(data,ensure_ascii=False,separators=(',',':'));A=A.replace('</','<\\/').replace('<!--','<\\!--').replace('\u2028','\\u2028').replace('\u2029','\\u2029');return B.replace(MARKER,A)
def render(data_dir,out_html,template=None,data=None):
	B=template;C=Path(B)if B else TEMPLATE;D=inject(C.read_text(encoding='utf-8'),data if data is not None else page_data(data_dir));A=Path(out_html)
	if A.parent and not A.parent.exists():A.parent.mkdir(parents=True)
	A.write_text(D,encoding='utf-8');return str(A)
def main(argv=None):
	sys.dont_write_bytecode=True;C=argparse.ArgumentParser(description='מסך ניהול החוזים מהנתונים של הלקוח');C.add_argument('--data-dir',required=True,help='תיקיית Areo-נתונים');C.add_argument('--out',required=True,help='קובץ ה-HTML לכתיבה');C.add_argument('--template',default=None,help='ברירת מחדל: ui/app/clm.html');A=C.parse_args(argv)
	if not os.path.isdir(A.data_dir):print('תיקיית הנתונים אינה קיימת: %s'%A.data_dir);return 2
	B=page_data(Path(A.data_dir));print('נכתב: %s · %d הסכמים, %d משימות, %d במשא ומתן, %d לאישור'%(render(A.data_dir,A.out,A.template,B),len(B['agreements']),len(B['tasks']),len(B['negotiations']),len(B['review'])));return 0
if __name__=='__main__':sys.exit(main())
