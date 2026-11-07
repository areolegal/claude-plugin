# -*- coding: utf-8 -*-
# Copyright (c) Areo. All rights reserved. Licensed under the terms at https://areo.co.il/legal/terms
import re
from clm.i18n import t
VALUE_CATS='תעריף','דמי מנוי'
CURRENCIES=('ILS',('₪','ש"ח','ש״ח'),('שקל',),('ILS','NIS')),('USD',('$',),('דולר',),('USD',)),('EUR',('€',),('אירו','יורו'),('EUR',)),('GBP',('£','ליש"ט','ליש״ט'),('פאונד','לירה','לירות','שטרלינג'),('GBP',))
KNOWN={A[0]for A in CURRENCIES}
PORTFOLIO_STATES='signed_not_effective','in_force','renewal_window','extended'
NOT_PER_UNIT={'לחודש','לשנה','לרבעון','לפני','לרבות','ללא','לאחר','לפי','לתקופה','לשנים','לחודשים'}
HEB_WORD=re.compile('[א-ת"״\']+')
ENG_PER=re.compile('\\bper\\s+(?!month|year|annum|quarter)[a-z]',re.I)
def _compile(symbols,words,codes):A=[re.escape(A)for A in symbols];A+=['(?<![א-ת])[בהולמש]?%s(?:ים)?(?![א-ת])'%re.escape(A)for A in words];A+=['(?<![A-Za-z])%s(?![A-Za-z])'%A for A in codes];return re.compile('|'.join(A),re.I)
_PATTERNS=[(A,_compile(B,C,D))for(A,B,C,D)in CURRENCIES]
def _marks(text):
	A=text
	if not isinstance(A,str)or not A.strip():return set()
	return{B for(B,C)in _PATTERNS if C.search(A)}
ISO_CODE=re.compile('^[A-Za-z]{3}$')
OPERATIONS='replace','add','delete'
ISO_DATE=re.compile('^\\d{4}-\\d{2}-\\d{2}$')
def explicit_code(v):
	if isinstance(v,str)and ISO_CODE.match(v.strip()):return v.strip().upper()
def currency_of(row,fallback=None):
	C=fallback;B=row;D=B.get('currency')
	if explicit_code(D):return explicit_code(D)
	for E in(B.get('unit'),B.get('label')):
		A=_marks(E)
		if len(A)==1:return A.pop()
		if A:return
	if explicit_code(C):return explicit_code(C)
	A=_marks(C);return A.pop()if len(A)==1 else None
PER_PERIOD=re.compile('לכל\\s+(?:חודש|שנה|רבעון)')
def per_unit(row):
	A=' '.join(str(row.get(A)or'')for A in('unit','period'))
	for(D,C)in _PATTERNS:A=C.sub(' ',A)
	A=PER_PERIOD.sub(' ',A)
	for B in HEB_WORD.findall(A):
		if B.startswith('ל')and len(B)>=3 and B not in NOT_PER_UNIT:return True
	return bool(ENG_PER.search(A))
def _kind(row):
	A=str(row.get('period')or'')
	if A=='חודשי':return'monthly'
	if A.startswith('שנתי'):return'annual'
def _number(v):return isinstance(v,(int,float))and not isinstance(v,bool)
def tidy(by):return{B:int(A)if float(A).is_integer()else round(A,2)for(B,A)in sorted(by.items())}
PER_UNIT_REASON='תעריף ליחידה, תלוי בהיקף','Rate per unit, depends on volume'
AMEND_INCOMPLETE='תיקון כספי בלי רכיב, פעולה או תאריך תוקף, לא נספר','Money amendment without a component, an operation or an effective date, not counted'
def _ckey(category,name,idx):A=' '.join(str(name or'').split()).casefold();return category,A or'#%d'%idx
def _entry(r,fallback_currency,not_counted,unknown):
	B=not_counted;A,F=r.get('value_kind'),r.get('basis');C=t(*PER_UNIT_REASON)if A=='unit'or F=='usage'else t('סכום כולל, לא שנתי','Total amount, not annual')if A=='total'else t('תקרה, לא שווי','A cap, not a value')if A=='max'else None
	if C:B.append({'label':r.get('label')or'','reason':C});return
	D=A if A in('monthly','annual')else _kind(r)
	if not D:return
	if per_unit(r):B.append({'label':r.get('label')or'','reason':t(*PER_UNIT_REASON)});return
	E=currency_of(r,fallback_currency)
	if not E:unknown.append(r.get('label')or'');return
	G='אומדן'in str(r.get('period')or'')or r.get('basis')=='estimate';return{'label':r.get('label')or'','category':r.get('category'),'kind':D,'cur':E,'value':r['value'],'estimated':G}
def annual(rows,fallback_currency=None,as_of=None):
	R=as_of;Q=fallback_currency;D,J=[],[];G={};S=[]
	for(I,B)in enumerate(rows):
		if B.get('category')not in VALUE_CATS:continue
		H=B.get('_rank')or'';T=B.get('label')or''
		if not H:
			if not _number(B.get('value')):continue
			A=_entry(B,Q,D,J)
			if A:A.update(source='agreement',since='',effective='');G.setdefault(_ckey(A['category'],T,I),[]).append(A)
			continue
		C,E,F=str(B.get('component')or'').strip(),B.get('operation'),B.get('effective_date')
		if not C or E not in OPERATIONS or not isinstance(F,str)or not ISO_DATE.match(F):D.append({'label':C or T,'reason':t(*AMEND_INCOMPLETE)});continue
		if R and F>R:D.append({'label':C,'reason':t('תיקון שטרם נכנס לתוקף','An amendment not yet in effect')});continue
		S.append((F,H,I,C,E,B))
	K=''
	for(F,H,I,C,E,B)in sorted(S,key=lambda x:x[:3]):
		L=_ckey(B.get('category'),C,I);M=G.get(L)
		if E=='add'and M:D.append({'label':C,'reason':t('הרכיב כבר קיים, להשתמש בהחלפה','The component already exists, use replace')});continue
		if E in('replace','delete')and not M:D.append({'label':C,'reason':t('הרכיב לא נמצא בהסכם','The component was not found in the agreement')});continue
		A=None
		if E!='delete':
			if not _number(B.get('value')):D.append({'label':C,'reason':t(*AMEND_INCOMPLETE)});continue
			A=_entry(B,Q,D,J)
			if not A:continue
			A.update(label=C,source='amendment',since=H,effective=F)
		for V in M or[]:D.append({'label':V['label'],'reason':t('הוחלף בתיקון להסכם','Replaced by an amendment')if E=='replace'else t('בוטל בתיקון להסכם','Removed by an amendment')})
		G.pop(L,None)
		if A:G[L]=[A]
		K=max(K,H)
	N,O,P={},[],False
	for W in G.values():
		for A in W:U=A['value']*(12 if A['kind']=='monthly'else 1);N[A['cur']]=N.get(A['cur'],0)+U;P=P or A['estimated'];O.append({'component':A['label'],'category':A['category'],'period':A['kind'],'currency':A['cur'],'value':A['value'],'annual_value':U,'source':A['source'],'since':A['since']or None,'effective_date':A['effective']or None})
	O.sort(key=lambda c:(c['currency'],c['component']));return{'by_currency':tidy(N),'components':O,'unknown_currency':J,'not_counted':D,'amended_on':K or None,'estimated':P}
def normalize(value,in_portfolio):
	A=dict(value or{})
	if not isinstance(A.get('annual_by_currency'),dict):A['annual_by_currency']={};A['annual']=None;A['unknown_currency']=list(A.get('unknown_currency')or[])+[t('שווי מהרצה קודמת, ממתין לחילוץ מחדש','Value from an earlier run, waiting to be read again')]
	for B in('not_counted','unknown_currency'):A.setdefault(B,[])
	A.setdefault('total_currency',None);A.setdefault('components',[]);A['in_portfolio']=bool(in_portfolio);return A
