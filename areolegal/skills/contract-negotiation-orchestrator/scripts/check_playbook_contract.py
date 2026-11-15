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
ROLE_MODES='one_sided','mutual'
CLASSES='A1','A2','B','C','D'
PAPERS='ours','theirs','third_party','unknown'
DOC_STATUS='signed','exchanged_draft'
def evidence_findings(core):
	E=core;A=[]
	if E.get('role_mode')not in(None,'')+ROLE_MODES:A.append('role_mode "%s" אינו one_sided או mutual'%E.get('role_mode'))
	if E.get('evidence_class')not in(None,'')+CLASSES:A.append('evidence_class "%s" בפלייבוק אינו אחד מ-A1, A2, B, C, D'%E.get('evidence_class'))
	for B in E.get('clauses')or[]:
		if not isinstance(B,dict):continue
		C=B.get('id')
		if B.get('evidence_class')not in(None,'')+CLASSES:A.append('%s: evidence_class "%s" אינו אחד מ-A1, A2, B, C, D'%(C,B.get('evidence_class')))
		if B.get('confidence')not in(None,'','high','medium','low','High','Medium','Low'):A.append('%s: confidence "%s" אינו high, medium או low'%(C,B.get('confidence')))
		F=(B.get('yellow')or{}).get('fallback_ladder')or[]
		if F:
			if' '.join(str(F[0].get('wording')or'').split())!=' '.join(str(B.get('fallback_wording')or'').split()):A.append('%s: המדרגה הראשונה בסולם אינה נוסח הנסיגה (fallback_wording)'%C)
			for(I,G)in enumerate(F):
				if not str(G.get('wording')or'').strip():A.append('%s: מדרגה %d בסולם בלי נוסח להחלה'%(C,I+1))
				if G.get('origin')not in(None,'','observed','derived','lower_bound','calibrated','template'):A.append('%s: origin "%s" במדרגה %d'%(C,G.get('origin'),I+1))
			if sum(1 for A in F if A.get('floor'))>1:A.append('%s: יותר מרצפה אחת בסולם'%C)
		for H in('green','yellow','red'):
			for D in(B.get(H)or{}).get('sources')or[]:
				if isinstance(D,dict)and D.get('paper')not in(None,'')+PAPERS:A.append('%s/%s: paper "%s" במקור'%(C,H,D.get('paper')))
				if isinstance(D,dict)and D.get('doc_status')not in(None,'')+DOC_STATUS+('template','form','guidance','policy','table','correspondence'):A.append('%s/%s: doc_status "%s" במקור'%(C,H,D.get('doc_status')))
	return A
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
	for b in(sys.stdout,sys.stderr):
		try:b.reconfigure(encoding='utf-8',errors='replace')
		except(AttributeError,ValueError):pass
	J=argparse.ArgumentParser(description=__doc__.split('\n')[0]);J.add_argument('model',help='playbook-model.json');J.add_argument('--core',help='playbook-core.json');J.add_argument('--index',help='playbooks/index.json. בלעדיו: האינדקס שמעל תיקיית הגרעין, כשהוא קיים');J.add_argument('--min-skill-version',help='גרסת בונה מינימלית. פלייבוק שנבנה לפניה מדווח כישן');D=J.parse_args(argv)
	try:E=json.loads(Path(D.model).read_text(encoding='utf-8'))
	except Exception as N:print('cannot read the model (%s): %s'%(D.model,N));return 2
	B=None
	if D.core:
		try:B=json.loads(Path(D.core).read_text(encoding='utf-8'))
		except Exception as N:print('cannot read the core (%s): %s'%(D.core,N));return 2
	C,F=[],[]
	for A in TOP:
		if not nonempty(E.get(A)):C.append('אין %s במודל'%A)
	c=[A for A in(E.get('scope_summary')or{}).get('contract_families')or()if isinstance(A,dict)];d={'company_role_code':next((A.get('company_role_code')for A in c if A.get('company_role_code')),None),'family_code':E.get('family_id')}
	for A in MATCH:
		if not nonempty(E.get(A))and not nonempty((B or{}).get(A))and not nonempty(d.get(A)):C.append('אין %s במודל ולא בגרעין. בלעדיו האיתור אינו מתאים את הפלייבוק למשפחה ולצד'%A)
	for A in STATUS:
		if not nonempty(E.get(A)):C.append('אין %s במודל. המעמד מוצג כפי שהוא, ואינו מנוסח מחדש'%A)
		elif A=='status_label'and S is not None:continue
		elif B is not None and A in B and B.get(A)!=E.get(A):C.append('%s בגרעין "%s" ובמודל "%s". הקורא אינו יודע במי להאמין'%(A,B.get(A),E.get(A)))
	if'presentation_label'in json.dumps(E,ensure_ascii=False):C.append('presentation_label במודל. התווית היחידה היא status_label')
	G=E.get('rules')
	if not isinstance(G,list)or not G:C.append('אין rules[] במודל: אין ממה להכריע');G=[]
	H=core_rules_by_id(B)
	for O in G:
		if isinstance(O,dict):C+=rule_findings(O,H.get(O.get('rule_id')))
		else:C.append('כלל שאינו אובייקט ב-rules[]')
	if B is not None and H:
		W={A.get('rule_id')for A in G if isinstance(A,dict)}
		for M in sorted(set(H)-W):C.append('%s: בגרעין ואינו במודל'%M)
		for M in sorted(W-set(H)):
			if M:F.append('%s: במודל ואינו בגרעין'%M)
	if B is not None:C+=evidence_findings(B)
	try:from playbook import decision_kit as K
	except ImportError:K=None
	if K is not None:
		if B is not None:
			for P in B.get('clauses')or():
				if isinstance(P,dict):C+=['%s: %s'%(P.get('id'),A)for A in K.check_core_kit(P.get('decision_kit'))]
		X=[A for A in G if isinstance(A,dict)and A.get('importance')in K.SUBSTANTIAL];Q=[A.get('rule_id')for A in X if not((H.get(A.get('rule_id'))or{}).get('decision_kit')if B is not None else K.core_kit(A))]
		if Q:F.append('ערכת ההכרעה חסרה ב-%d כללים מהותיים (%s): מסווגים כמו קודם, מול העמדה והנוסח, ובסיכום הפנימי שורה אחת שמציעה לבנות מחדש את הגרעין ברכיב הפלייבוק'%(len(Q),', '.join(str(A)for A in Q[:6])))
		Y=[A.get('rule_id')for A in X if not(_val(A,H.get(A.get('rule_id')),'post_checks')or[])]
		if Y:F.append('כלל קריטי בלי בדיקת תוצאה: %s. נרשם בשורה בסיכום הפנימי, ואין להמציא בדיקה במקומו'%', '.join(str(A)for A in Y[:6]))
	if D.min_skill_version:
		R=str((E.get('produced_with')or{}).get('skill_version')or'')
		if R and _older(R,D.min_skill_version):F.append('הפלייבוק נבנה בגרסת בונה %s, והמינימום הוא %s. אמור זאת ללקוחה ואל תוריד בשקט'%(R,D.min_skill_version))
	T=[A.get('rule_id')for A in G if isinstance(A,dict)and _val(A,H.get(A.get('rule_id')),'round1_posture')is None]
	if T:F.append('אין round1_posture ל-%d כללים (%s). מחזיקים בירוק, ונאמר בסיכום הפנימי'%(len(T),', '.join(str(A)for A in T[:6])))
	I=[]
	if S is None:F.append('הספרייה המשותפת אינה זמינה, ולכן פער התוויות מול שער המדיניות לא נבדק')
	else:
		U=D.index or(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(D.core))),'index.json')if D.core else None);e=index_entry_for(U,D.core,E,B)if U and os.path.exists(U)else None;L=S.label_gap(E,D.model,core=B,index_entry=e)
		if L['mismatch']:
			I.append('התווית של שער המדיניות: "%s"'%L['label'])
			for Z in L['mismatch']:I.append('%s: "%s"'%(Z,L['stored'][Z]))
			if set(L['mismatch'])-{'model'}:I.append('מציגים ללקוחה את התווית של שער המדיניות, ומציעים לבנות מחדש את הגרעין ברכיב הפלייבוק (build_playbook_core.py ו-register_playbook.py)')
			else:I.append('רק המודל נושא תווית ישנה. מציגים ללקוחה את התווית של שער המדיניות; המודל מתעדכן בשמירה הבאה שלו ברכיב הפלייבוק')
	def a():
		if I:
			print('LABEL MISMATCH')
			for A in I:print('-',A)
	if C:
		print('CONTRACT NOT MET')
		for f in C:print('-',f)
		for V in F:print('! note:',V)
		print('%d errors'%len(C));a();return 3
	print('CONTRACT MET')
	for V in F:print('! note:',V)
	a();return 0
def _older(a,b):
	def C(v):return[int(A)if A.isdigit()else 0 for A in str(v).split('.')]
	A,B=C(a),C(b);A+=[0]*(len(B)-len(A));B+=[0]*(len(A)-len(B));return A<B
if __name__=='__main__':sys.exit(main())
