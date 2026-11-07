# -*- coding: utf-8 -*-
# Copyright (c) Areo. All rights reserved. Licensed under the terms at https://areo.co.il/legal/terms
import re
try:from playbook.validity import playbook_warnings
except ImportError:playbook_warnings=None
PLACEHOLDER=re.compile('\\[[^\\[\\]\\n]{1,60}\\]')
TXT={'he':{'no_clauses':'בפלייבוק אין עמדות.','no_family':'בפלייבוק לא נרשם סוג ההסכם.','no_role':'בפלייבוק לא נרשם הצד של החברה בהסכם.','no_position':'לנושא "%s" אין עמדה.','dup':'אותו נושא מופיע פעמיים: %s.','placeholder':'בנוסח המועדף של "%s" נשאר מקום ריק להשלמה: %s.','kind':'הפלייבוק נבנה מהסכמים עם צד מסוג אחר (%s), ולא עם %s. כדאי לבדוק כל עמדה לפני שמחילים אותה.','not_observed':'בהסכמים שמהם נבנה הפלייבוק לא היה צד מסוג %s. כדאי לבדוק כל עמדה לפני שמחילים אותה.','draft':'הפלייבוק הוא עדיין טיוטת מדיניות, שמחכה לאישור שלכם.'},'en':{'no_clauses':'The playbook has no positions.','no_family':'The playbook does not record the agreement type.','no_role':"The playbook does not record the company's side.",'no_position':'The topic "%s" has no position.','dup':'The same topic appears twice: %s.','placeholder':'The preferred wording of "%s" still has a blank to fill in: %s.','kind':'The playbook was built from agreements with a different kind of counterparty (%s), not %s. Check each position before applying it.','not_observed':'None of the agreements behind the playbook was with a %s. Check each position before applying it.','draft':'The playbook is still a draft policy, awaiting your approval.'}}
def _s(v):return str(v or'').strip()
def _lang(lang):return'en'if _s(lang).lower().startswith('en')else'he'
def core_problems(core,counterparty_kind=None,lang='he'):
	try:return _problems(core,counterparty_kind,_lang(lang))
	except Exception:return[]
def _problems(core,counterparty_kind,lang):
	C=core;D=TXT[lang]
	if not isinstance(C,dict):return[('warn',D['no_clauses'])]
	A=[];I=C.get('clauses')or C.get('rules')or[]
	if not I:A.append(('warn',D['no_clauses']))
	if not(_s(C.get('family_id'))or C.get('contract_families')):A.append(('warn',D['no_family']))
	if not(_s(C.get('company_role_code'))or _s(C.get('company_role'))):A.append(('warn',D['no_role']))
	F={}
	for B in I:
		if not isinstance(B,dict):continue
		J=_s(B.get('title')or B.get('clause_issue')or B.get('id'));G=_s(B.get('id'))
		if G:F[G]=F.get(G,0)+1
		K=B.get('green')or{};O=_s(K.get('position'))or _s(B.get('preferred_wording'))or _s((B.get('yellow')or{}).get('position'))or _s((B.get('red')or{}).get('position'))or _s(B.get('red_line'))
		if not O:A.append(('warn',D['no_position']%J))
		L=PLACEHOLDER.search(_s(K.get('preferred_wording'))or _s(B.get('preferred_wording')))
		if L:A.append(('warn',D['placeholder']%(J,L.group(0))))
	M=[A for(A,B)in F.items()if B>1]
	if M:A.append(('warn',D['dup']%', '.join(M[:5])))
	N=C.get('applicability')or{};H=[_s(A)for A in N.get('counterparty_kinds')or[]if _s(A)];P=[_s(A.get('kind')if isinstance(A,dict)else A)for A in N.get('not_observed')or[]];E=_s(counterparty_kind)
	if E and E in P:A.append(('warn',D['not_observed']%E))
	elif E and H and E not in H:A.append(('warn',D['kind']%(', '.join(H),E)))
	if playbook_warnings is not None:A+=[('warn',A)for A in playbook_warnings(None,core=C,lang=lang)]
	if _s(C.get('playbook_status')).lower()in('draft','partiallyapproved'):A.append(('info',D['draft']))
	return A
