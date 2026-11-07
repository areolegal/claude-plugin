# -*- coding: utf-8 -*-
# Copyright (c) Areo. All rights reserved. Licensed under the terms at https://areo.co.il/legal/terms
try:from playbook import status as S,validate_model as V
except ImportError:import os;import sys;sys.path.insert(0,os.path.dirname(os.path.dirname(os.path.abspath(__file__))));from playbook import status as S;from playbook import validate_model as V
GROUPS={'LEGAL_CORE_MISSING':'legal_core','LEGAL_CORE_REVIEW_ONLY':'legal_core','LEGAL_CORE_STATUTE':'legal_core','RATIONALE_DUPLICATE':'rationale_dup','TRACK_WORDING_MISMATCH':'wording_mismatch','COUNTERPARTY_UNREALISTIC':'public_body','SOURCE_NOT_SHOWN':'source_shown','LABEL_MISMATCH':'label','LABEL_DRIFT':'label'}
ORDER='no_source','source_shown','legal_core','public_body','wording_mismatch','rationale_dup','label','other','no_company_position'
_HE_REVIEW='כדאי שעורך דין יעבור עליהם לפני שמסתמכים עליהם.'
_HE_REVIEW1='כדאי שעורך דין יעבור עליו לפני שמסתמכים עליו.'
TEXT={'he':{'no_source':{'n':'ב-{n} נקודות AREO לא מצאה מקור מורשה. כדאי שעורך דין יבדוק אותן לפני שמסתמכים עליהן.','one':'בנקודה אחת AREO לא מצאה מקור מורשה. כדאי שעורך דין יבדוק אותה לפני שמסתמכים עליה.','some':'בחלק מהנקודות AREO לא מצאה מקור מורשה. כדאי שעורך דין יבדוק אותן לפני שמסתמכים עליהן.'},'source_shown':{'n':'ב-{n} נושאים לא מוצג על איזה הסכם וסעיף העמדה נשענת. כדאי לבנות מחדש בסוכן הפלייבוק.','one':'בנושא אחד לא מוצג על איזה הסכם וסעיף העמדה נשענת. כדאי לבנות מחדש בסוכן הפלייבוק.','some':'בחלק מהנושאים לא מוצג על איזה הסכם וסעיף העמדה נשענת. כדאי לבנות מחדש בסוכן הפלייבוק.'},'legal_core':{'n':'ב-{n} נושאים חסר ההסבר המשפטי לעמדה. '+_HE_REVIEW,'one':'בנושא אחד חסר ההסבר המשפטי לעמדה. '+_HE_REVIEW1,'some':'בחלק מהנושאים חסר ההסבר המשפטי לעמדה. '+_HE_REVIEW},'public_body':{'n':'ב-{n} נושאים הפשרה מבקשת מגוף ציבורי לוותר על סמכות שאינו יכול לוותר עליה.','one':'בנושא אחד הפשרה מבקשת מגוף ציבורי לוותר על סמכות שאינו יכול לוותר עליה.','some':'בחלק מהנושאים הפשרה מבקשת מגוף ציבורי לוותר על סמכות שאינו יכול לוותר עליה.'},'wording_mismatch':{'n':'ב-{n} נושאים הנוסח המוצע אינו תואם את העמדה שכתובה לידו. כדאי לבדוק לפני שליחה.','one':'בנושא אחד הנוסח המוצע אינו תואם את העמדה שכתובה לידו. כדאי לבדוק לפני שליחה.','some':'בחלק מהנושאים הנוסח המוצע אינו תואם את העמדה שכתובה לידו. כדאי לבדוק לפני שליחה.'},'rationale_dup':{'some':'ההסברים לעמדות חוזרים כמעט מילה במילה בין נושאים, ולכן אינם מסבירים את הנושא עצמו.'},'label':{'some':'תיאור המדיניות אינו אחיד בקבצים שלה. כדאי לבנות אותה מחדש בסוכן הפלייבוק.'},'other':{'some':'המדיניות לא עברה את כל הבדיקות שלה. כדאי לבנות אותה מחדש בסוכן הפלייבוק.'},'no_company_position':{'some':'אף עמדה במדיניות אינה נשענת על דוגמה מההסכמים שלכם. כולן המלצה של Areo.'},'head':'לפני שמסתמכים על המדיניות הזו:'},'en':{'no_source':{'n':'On {n} points, AREO did not find an approved source. Have a lawyer check them before relying on them.','one':'On one point, AREO did not find an approved source. Have a lawyer check it before relying on it.','some':'On some points, AREO did not find an approved source. Have a lawyer check them before relying on them.'},'source_shown':{'n':'In {n} topics, the agreement and clause the position rests on are not shown. Rebuild with the playbook agent.','one':'In one topic, the agreement and clause the position rests on are not shown. Rebuild with the playbook agent.','some':'In some topics, the agreement and clause the position rests on are not shown. Rebuild with the playbook agent.'},'legal_core':{'n':'In {n} topics, the legal reasoning behind the position is missing. Have a lawyer review them.','one':'In one topic, the legal reasoning behind the position is missing. Have a lawyer review it.','some':'In some topics, the legal reasoning behind the position is missing. Have a lawyer review them.'},'public_body':{'n':'In {n} topics, the compromise asks a public body to give up a power it cannot waive.','one':'In one topic, the compromise asks a public body to give up a power it cannot waive.','some':'In some topics, the compromise asks a public body to give up a power it cannot waive.'},'wording_mismatch':{'n':"In {n} topics, the proposed wording doesn't match the position next to it. Check before sending.",'one':"In one topic, the proposed wording doesn't match the position next to it. Check before sending.",'some':"In some topics, the proposed wording doesn't match the position next to it. Check before sending."},'rationale_dup':{'some':"The explanations repeat almost word for word across topics, so they don't explain each topic."},'label':{'some':'The policy is described differently across its files. Rebuild it with the playbook agent.'},'other':{'some':"The policy didn't pass all of its own checks. Rebuild it with the playbook agent."},'no_company_position':{'some':"No position in this policy rests on an example from your agreements. All of them are Areo's recommendations."},'head':'Before relying on this policy:'}}
def _lang(lang):return'en'if str(lang or'').strip().lower().startswith('en')else'he'
def _findings(model):
	A=[]
	for B in(V.rationale_findings,V.fallback_findings,V.position_source_findings):
		try:A+=B(model)
		except Exception:continue
	return A
def _no_source_points(model):
	try:return len(V.no_source_notes(model))
	except Exception:return 0
def validity_summary(model,core=None):
	A=model;A=A if isinstance(A,dict)else{};C=[A for A in _findings(A)if A.get('severity')=='error']
	try:C+=[{'code':A,'severity':'error','rule_id':None}for(A,B)in S.label_findings(A,core)if A in('LABEL_MISMATCH','LABEL_DRIFT')]
	except Exception:pass
	D,E={},{}
	for B in C:
		D[B['code']]=D.get(B['code'],0)+1;F=GROUPS.get(B['code'],'other');E.setdefault(F,set())
		if B.get('rule_id'):E[F].add(B['rule_id'])
	try:G=bool(S.no_company_position(A))
	except Exception:G=False
	H={'status':'invalid'if C else'valid','codes':dict(sorted(D.items())),'rules':{A:len(B)for(A,B)in sorted(E.items())},'no_company_position':G};I=_no_source_points(A)
	if I:H['rules']['no_source']=I
	return H
def _lines(summary,lang):
	D=summary;H=TEXT[_lang(lang)];G=D.get('rules')or{};A=set(G)
	for I in D.get('codes')or{}:A.add(GROUPS.get(I,'other'))
	if D.get('status')=='invalid'and not A-{'no_source'}:A.add('other')
	if D.get('no_company_position'):A.add('no_company_position')
	E=[]
	for F in ORDER:
		if F not in A:continue
		B,C=H[F],G.get(F)
		if isinstance(C,int)and C==1 and'one'in B:E.append(B['one'])
		elif isinstance(C,int)and C>1 and'n'in B:E.append(B['n'].format(n=C))
		else:E.append(B['some'])
	return E
def _core_no_source_points(core):return sum(1 for A in core.get('clauses')or core.get('rules')or[]if isinstance(A,dict)and A.get('no_approved_source'))
def playbook_warnings(model=None,core=None,lang='he'):
	D=model;A=core
	try:
		if isinstance(D,dict)and D.get('rules')is not None:B=validity_summary(D,A)
		elif isinstance(A,dict)and isinstance(A.get('validity'),dict):
			B=dict(A['validity']);B['rules']=dict(B.get('rules')or{});C=_core_no_source_points(A)
			if C and not B['rules'].get('no_source'):B['rules']['no_source']=C
		elif isinstance(A,dict):C=_core_no_source_points(A);return _lines({'status':'valid','rules':{'no_source':C}},lang)if C else[]
		else:return[]
		return _lines(B,lang)
	except Exception:return[]
def warning_block(model=None,core=None,lang='he'):
	A=playbook_warnings(model,core,lang)
	if not A:return''
	return'\n'.join([TEXT[_lang(lang)]['head']]+['- '+A for A in A])
