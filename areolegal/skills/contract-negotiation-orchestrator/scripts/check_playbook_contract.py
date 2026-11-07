#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (c) Areo. All rights reserved. Licensed under the terms at https://areo.co.il/legal/terms
'חוזה הנתונים: האם הנושא ונותן יכול לעבוד עם הפלייבוק הזה.'
import argparse,json,os,sys
from pathlib import Path
try:sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)));import areo_lib;from playbook import status as S
except ImportError:S=None
POSTURES='hold_green','offer_yellow','not_applicable'
TRACKS='green','yellow','red'
WORDED='green','yellow'
TOP='schema_version','core_version','family_id','produced_with'
MATCH='company_role_code','family_code'
STATUS='status_label','playbook_status'
def nonempty(v):return bool(v)and(not isinstance(v,str)or bool(v.strip()))
def wording_of(cell):
	for B in('wording','preferred_wording','proposed_clause','fallback_wording','text','clause_text','wording_he'):
		A=cell.get(B)
		if isinstance(A,dict):A=A.get('he')or A.get('en')
		if nonempty(A):return A
def rule_findings(rule,core_rule):
	I=core_rule;A=rule;E=[];K=A.get('rule_id')or'(כלל בלי מזהה)'
	def B(msg):E.append('%s: %s'%(K,msg))
	if not nonempty(A.get('rule_id')):E.append('כלל בלי rule_id: אין לו שם בשום הכרעה ובשום קובץ מצב')
	if not(nonempty(A.get('topic'))or nonempty(A.get('topic_name'))):B('אין topic_name. הנושא הוא מה שמוצג ללקוחה ומה שנרשם בקובץ המצב')
	if not nonempty(A.get('importance')):B('אין importance. הדרגה בפקטור 1 נשענת עליה')
	if not(nonempty(A.get('policy_ref'))or nonempty(A.get('rule_id'))):B('אין policy_ref. מספר הכלל נכנס לבועה החיצונית')
	F=_val(A,I,'round1_posture')
	if F is not None and F not in POSTURES:B('round1_posture="%s", ומותר %s. חסר מותר, ואז מחזיקים בירוק'%(F,' או '.join(POSTURES)))
	J=A.get('traffic_light')or{}
	if not isinstance(J,dict):B('traffic_light אינו אובייקט');return E
	for D in TRACKS:
		G=J.get(D)
		if not isinstance(G,dict):B('אין מסלול %s. שלושת המסלולים נשלפים בכל הכרעה'%D);continue
		if not nonempty(G.get('position')):B('%s: אין position. זו העמדה שמוצגת'%D)
		if D in WORDED and not wording_of(G):B('%s: אין נוסח להחלה. הנושא ונותן מכניס נוסח לגוף ההסכם, ולא תקציר'%D)
	for C in('fallback_wording','fallback_source'):
		if not nonempty(_val(A,I,C)):B('אין %s. הנסיגה היא מה שמוצע כשהירוק נדחה'%C)
	for H in A.get('segment_overrides')or():
		if isinstance(H,dict):
			for C in('fallback_wording','fallback_source'):
				if C in H and not nonempty(H.get(C)):B('segment_overrides: %s ריק'%C)
	return E
def _val(rule,core_rule,field):
	A=field
	if A in rule:return rule.get(A)
	return(core_rule or{}).get(A)
def core_rules_by_id(core):
	B={}
	for D in('clauses','rules'):
		for A in(core or{}).get(D)or():
			if isinstance(A,dict):
				C=A.get('rule_id')or A.get('id')
				if C:B[C]=A
	return B
def index_entry_for(index_path,core_path,model,core):
	E=core_path;D=index_path;B=model
	try:C=json.loads(Path(D).read_text(encoding='utf-8'))
	except Exception:return
	F=C.get('playbooks')if isinstance(C,dict)else C;G=os.path.normcase(os.path.abspath(E))if E else None;I=os.path.dirname(os.path.dirname(os.path.abspath(D)));J=(core or{}).get('family_code')or B.get('family_code')or B.get('family_id');K=(core or{}).get('company_role_code')or B.get('company_role_code')
	for A in F or():
		H=A.get('core_path')or A.get('path')if isinstance(A,dict)else None
		if G and H and os.path.normcase(os.path.abspath(os.path.join(I,H.replace('\\','/'))))==G:return A
	for A in F or():
		if isinstance(A,dict)and(A.get('family_code')or A.get('family_id'))==J and A.get('company_role_code')==K and not A.get('legacy'):return A
def main(argv=None):
	for W in(sys.stdout,sys.stderr):
		try:W.reconfigure(encoding='utf-8',errors='replace')
		except(AttributeError,ValueError):pass
	I=argparse.ArgumentParser(description=__doc__.split('\n')[0]);I.add_argument('model',help='playbook-model.json');I.add_argument('--core',help='playbook-core.json');I.add_argument('--index',help='playbooks/index.json. בלעדיו: האינדקס שמעל תיקיית הגרעין, כשהוא קיים');I.add_argument('--min-skill-version',help='גרסת בונה מינימלית. פלייבוק שנבנה לפניה מדווח כישן');B=I.parse_args(argv)
	try:C=json.loads(Path(B.model).read_text(encoding='utf-8'))
	except Exception as M:print('cannot read the model (%s): %s'%(B.model,M));return 2
	E=None
	if B.core:
		try:E=json.loads(Path(B.core).read_text(encoding='utf-8'))
		except Exception as M:print('cannot read the core (%s): %s'%(B.core,M));return 2
	D,F=[],[]
	for A in TOP:
		if not nonempty(C.get(A)):D.append('אין %s במודל'%A)
	X=[A for A in(C.get('scope_summary')or{}).get('contract_families')or()if isinstance(A,dict)];Y={'company_role_code':next((A.get('company_role_code')for A in X if A.get('company_role_code')),None),'family_code':C.get('family_id')}
	for A in MATCH:
		if not nonempty(C.get(A))and not nonempty((E or{}).get(A))and not nonempty(Y.get(A)):D.append('אין %s במודל ולא בגרעין. בלעדיו האיתור אינו מתאים את הפלייבוק למשפחה ולצד'%A)
	for A in STATUS:
		if not nonempty(C.get(A)):D.append('אין %s במודל. המעמד מוצג כפי שהוא, ואינו מנוסח מחדש'%A)
		elif A=='status_label'and S is not None:continue
		elif E is not None and A in E and E.get(A)!=C.get(A):D.append('%s בגרעין "%s" ובמודל "%s". הקורא אינו יודע במי להאמין'%(A,E.get(A),C.get(A)))
	if'presentation_label'in json.dumps(C,ensure_ascii=False):D.append('presentation_label במודל. התווית היחידה היא status_label')
	G=C.get('rules')
	if not isinstance(G,list)or not G:D.append('אין rules[] במודל: אין ממה להכריע');G=[]
	J=core_rules_by_id(E)
	for N in G:
		if isinstance(N,dict):D+=rule_findings(N,J.get(N.get('rule_id')))
		else:D.append('כלל שאינו אובייקט ב-rules[]')
	if E is not None and J:
		T={A.get('rule_id')for A in G if isinstance(A,dict)}
		for L in sorted(set(J)-T):D.append('%s: בגרעין ואינו במודל'%L)
		for L in sorted(T-set(J)):
			if L:F.append('%s: במודל ואינו בגרעין'%L)
	if B.min_skill_version:
		O=str((C.get('produced_with')or{}).get('skill_version')or'')
		if O and _older(O,B.min_skill_version):F.append('הפלייבוק נבנה בגרסת בונה %s, והמינימום הוא %s. אמור זאת ללקוחה ואל תוריד בשקט'%(O,B.min_skill_version))
	P=[A.get('rule_id')for A in G if isinstance(A,dict)and _val(A,J.get(A.get('rule_id')),'round1_posture')is None]
	if P:F.append('אין round1_posture ל-%d כללים (%s). מחזיקים בירוק, ונאמר בסיכום הפנימי'%(len(P),', '.join(str(A)for A in P[:6])))
	H=[]
	if S is None:F.append('הספרייה המשותפת אינה זמינה, ולכן פער התוויות מול שער המדיניות לא נבדק')
	else:
		Q=B.index or(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(B.core))),'index.json')if B.core else None);Z=index_entry_for(Q,B.core,C,E)if Q and os.path.exists(Q)else None;K=S.label_gap(C,B.model,core=E,index_entry=Z)
		if K['mismatch']:
			H.append('התווית של שער המדיניות: "%s"'%K['label'])
			for U in K['mismatch']:H.append('%s: "%s"'%(U,K['stored'][U]))
			if set(K['mismatch'])-{'model'}:H.append('מציגים ללקוחה את התווית של שער המדיניות, ומציעים לבנות מחדש את הגרעין ברכיב הפלייבוק (build_playbook_core.py ו-register_playbook.py)')
			else:H.append('רק המודל נושא תווית ישנה. מציגים ללקוחה את התווית של שער המדיניות; המודל מתעדכן בשמירה הבאה שלו ברכיב הפלייבוק')
	def V():
		if H:
			print('LABEL MISMATCH')
			for A in H:print('-',A)
	if D:
		print('CONTRACT NOT MET')
		for a in D:print('-',a)
		for R in F:print('! note:',R)
		print('%d errors'%len(D));V();return 3
	print('CONTRACT MET')
	for R in F:print('! note:',R)
	V();return 0
def _older(a,b):
	def C(v):return[int(A)if A.isdigit()else 0 for A in str(v).split('.')]
	A,B=C(a),C(b);A+=[0]*(len(B)-len(A));B+=[0]*(len(A)-len(B));return A<B
if __name__=='__main__':sys.exit(main())
