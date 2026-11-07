# -*- coding: utf-8 -*-
# Copyright (c) Areo. All rights reserved. Licensed under the terms at https://areo.co.il/legal/terms
import calendar,datetime as dt
from clm.i18n import t
STATES={'upcoming','pending_trigger','missing','needs_action','lapsed_pending'}
LADDER=14,7,3,1,0
GENERIC='לבחון את הסעיף','לפעול לפי הנדרש','Review the clause','Act as required'
RENEWING={'term_end','nonrenewal_notice','auto_renewal'}
NEEDS_ACTION_NOTE={'term_end':('תום התקופה חלף. לאשר אם ההסכם הסתיים, הוארך או התחדש','The term has ended. Confirm whether the agreement ended, was extended or renewed'),'guarantee_expiry':('הערבות פקעה. לוודא שהומצאה ערבות חדשה בתוקף','The guarantee has expired. Make sure a new valid guarantee was provided')}
HINT={'right_lapses':('האם מומש או פקע','was it exercised or did it lapse'),'opportunity':('האם מומש או לא נוצל','was it used or not'),'auto_change':('האם השינוי נכנס לתוקף כפי שנקבע','did the change take effect as set'),'we_breach':('האם בוצע','was it done'),'they_breach_monitor':('האם הצד שכנגד קיים','did the other side comply')}
def _hint(cons):return t(*HINT[cons])
def parse(s):return dt.date.fromisoformat(s)if s else None
def fmt(d):return'%d.%d.%d'%(d.day,d.month,d.year)if d else''
def add_months(d,months):A,B=divmod(d.month-1+months,12);A,B=d.year+A,B+1;return dt.date(A,B,min(d.day,calendar.monthrange(A,B)[1]))
def is_month_end(d):return d.day==calendar.monthrange(d.year,d.month)[1]
def add_months_eom(d,months):A=add_months(d,months);return dt.date(A.year,A.month,calendar.monthrange(A.year,A.month)[1])if is_month_end(d)else A
def term_end_after(start,months):B=start;A=add_months(B,months);return A if A.day<B.day else A-dt.timedelta(days=1)
def _positive_int(v):return isinstance(v,int)and not isinstance(v,bool)and v>0
def _next_reminder(act_by,today):
	A=today
	for C in LADDER:
		B=act_by-dt.timedelta(days=C)
		if B>=A:return B.isoformat()
	return A.isoformat()
def _passed(ev,prefix=None):
	A,B=ev['event_code'],ev['consequence']
	if A in NEEDS_ACTION_NOTE:return'needs_action',t(*NEEDS_ACTION_NOTE[A])
	C=prefix or t('המועד חלף','The date has passed')
	if B=='we_breach':return'needs_action',C+t(', והחובה עדיין דורשת טיפול',', and the duty still needs handling')
	return'lapsed_pending',C+t('. לאשר מה קרה: ','. Confirm what happened: ')+_hint(B)
def _passed_occurrence(main,ev,when,renewal):
	F=renewal;B=when;A=ev
	if F:D='needs_action'if A['consequence']=='we_breach'else'lapsed_pending';C=t('המועד מיום %s חלף וההסכם התחדש לכאורה מכוח סעיף החידוש. לאמת שההסכם התחדש','The date of %s has passed, and the agreement appears to have renewed under its renewal clause. Confirm that it renewed')%fmt(B)
	elif A['consequence']=='we_breach':D,C='needs_action',t('המועד החוזר מיום %s חלף, והחובה עדיין דורשת טיפול. לאשר שבוצע','The recurring date of %s has passed, and the duty still needs handling. Confirm it was done')%fmt(B)
	else:D,C='lapsed_pending',t('המועד החוזר מיום %s חלף. לאשר מה קרה: %s','The recurring date of %s has passed. Confirm what happened: %s')%(fmt(B),_hint(A['consequence']))
	E=dict(main);E.pop('label_contract',None);E.update(label=A.get('label',main.get('label')),date=B.isoformat(),act_by=None,next_reminder=None,state=D,state_note=C,action=C,history=[],derived=B.isoformat()!=A.get('date'),renewed=False,occurrence='passed',renewal_check=F);return E
def derive_all(ev,today,events_catalog,role_confirmed=True,cp=None):
	I=today;A=ev;E=events_catalog[A['event_code']];cp=cp or t('הצד שכנגד','the other side');D=dict(A);B=parse(A.get('date'));F,H,J=[],'',False;P=A.get('recurrence')or{};G=P.get('months')if E['rollable']else None
	if not _positive_int(G):G=None
	L=P.get('max')if G else None
	if not G and A['event_code']in RENEWING and _positive_int(A.get('renewal_months')):G,L,J=A['renewal_months'],A.get('renewal_max'),True
	if A.get('relative')or B is None and A.get('trigger'):C='pending_trigger'
	elif B is None:C,H='missing',t('המועד אינו כתוב בהסכם. להשלים','The agreement gives no date. Fill it in')
	elif B<I and G:
		R,M,S=B,0,add_months_eom if J else add_months
		while B<I and(L is None or M<L):F.append(B.isoformat());M+=1;B=S(R,G*M)
		if B<I:C,H=_passed(A,t('המועד החוזר האחרון שבהסכם חלף','The last recurring date in the agreement has passed'))
		else:C,H='upcoming',t('מועד חוזר: מחושב מהמחזור הקודם (%s)','Recurring date: computed from the previous cycle (%s)')%fmt(parse(F[-1]))
	elif B<I:C,H=_passed(A)
	else:C='upcoming'
	K=B-dt.timedelta(days=E['lead_days'])if C=='upcoming'else None;N=bool(F)and C=='upcoming';D.update(date=B.isoformat()if B else None,contract_date_original=A.get('date'),act_by=K.isoformat()if K else None,lead_days=E['lead_days'],state=C,state_note=H,history=F,derived=bool(F),category=E['category'],critical=E['critical'],role_pending=not role_confirmed,if_nothing=A.get('if_nothing')or E['if_nothing'],next_reminder=_next_reminder(K,I)if K else None,status='open',renewed=J and N)
	if C in('needs_action','lapsed_pending'):D['action']=H
	elif F or not A.get('action')or any(B in A['action']for B in GENERIC):O=A.get('notice_days');Q=t('המועד','the date');T=t(' (הודעה של %d יום מראש)'," (%d day's notice)"if O==1 else" (%d days' notice)")%O if O else'';D['action']=E['action'].format(cp=cp,date=fmt(B)or Q,act_by=fmt(K)or Q,notice=T,title=A['label'])
	if N and J and A['event_code']=='term_end':D['label_contract']=A.get('label');D['label']=t('תום התקופה הנוכחית, אחרי חידוש','End of the current term, after renewal')
	if N:return[D,_passed_occurrence(D,A,parse(F[-1]),J)]
	return[D]
def derive(ev,today,events_catalog,role_confirmed=True,cp=None):return derive_all(ev,today,events_catalog,role_confirmed=role_confirmed,cp=cp)[0]
