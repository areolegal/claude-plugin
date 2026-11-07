# -*- coding: utf-8 -*-
# Copyright (c) Areo. All rights reserved. Licensed under the terms at https://areo.co.il/legal/terms
import re
HEB_RX=re.compile('[א-ת]')
from common.terms import terms_re
COLUMNS='סעיף','מה הוכרע','תווית מקור'
ANSWER_KIND_HE={'explicit':'הכרעה מפורשת','delegated':'תשובה כללית, הוחלה ההמלצה'}
ENGLISH_KIND=terms_re(('explicit','delegated'))
SOURCE_LABELS={'playbook':'מהמדיניות שלכם','proposed_playbook':'מטיוטת המדיניות','profile':'מהפרופיל','answer':'נכנס לנוסח מתשובתכם','professional':'שיקול מקצועי','other_playbook':'שיקול מקצועי, בהשראת פלייבוק של סוג אחר'}
BANNED='מי מאשר','מאשר','טעון אישור','ממתין לאישור','מנכ"ל','הנהלה בכירה','טבלת הסמכויות'
BANNED_RE=terms_re(BANNED)
COLUMNS_EN='Clause','What was decided','Source label'
ANSWER_KIND_EN={'explicit':'your express decision','delegated':'a general answer, the recommendation was applied'}
SOURCE_LABELS_EN={'playbook':'From your policy','proposed_playbook':'From the draft policy','profile':'From the profile','answer':'Entered the wording from your answer','professional':'Professional judgment','other_playbook':'Professional judgment, inspired by a playbook of another type'}
TXT={'he':{'cols':COLUMNS,'kind':ANSWER_KIND_HE,'src':SOURCE_LABELS,'pb':SOURCE_LABELS['playbook'],'ppb':SOURCE_LABELS['proposed_playbook'],'red_ans':'חוצה קו אדום: הכרעתך ("%s")','red_ans_none':'תשובה מפורשת','red_need':'חוצה קו אדום: נדרשת הכרעתך','conc':'ויתורים מכוונים (%d)','conc_label':'הכרעתך: %s','no_answer':'בלי תשובה','stance':{'stricter':', בגישה מחמירה','lenient':', בגישה מקלה'},'hidden':'ועוד %d סעיפים שקיבלנו כמו שהם. הרשימה המלאה מוצגת כשתבקשו.'},'en':{'cols':COLUMNS_EN,'kind':ANSWER_KIND_EN,'src':SOURCE_LABELS_EN,'pb':SOURCE_LABELS_EN['playbook'],'ppb':SOURCE_LABELS_EN['proposed_playbook'],'red_ans':'Crosses a red line: your decision ("%s")','red_ans_none':'an express answer','red_need':'Crosses a red line: your decision is needed','conc':'Deliberate concessions (%d)','conc_label':'Your decision: %s','no_answer':'no answer','stance':{'stricter':', stricter approach','lenient':', more lenient approach'},'hidden':'And %d more clauses we accepted as they are. The full list is shown on request.'}}
BASIS_SOURCE={'PolicyBenchmark':'playbook','PolicyDerived':'playbook','ExpertJudgment':'professional','UserDecided':'answer','Profile':'profile','ProfileFact':'profile'}
LEGACY_LABELS={'מהפלייבוק':'playbook','מפלייבוק מוצע':'proposed_playbook','From the playbook':'playbook','From the proposed playbook':'proposed_playbook'}
LABEL_KEY_HE=dict({B:A for(A,B)in SOURCE_LABELS.items()},**{A:B for(A,B)in LEGACY_LABELS.items()if HEB_RX.search(A)})
PLAYBOOK_LABELS={SOURCE_LABELS['playbook'],SOURCE_LABELS_EN['playbook'],'מהפלייבוק','From the playbook'}
PROPOSED_LABELS={SOURCE_LABELS['proposed_playbook'],SOURCE_LABELS_EN['proposed_playbook'],'מפלייבוק מוצע','From the proposed playbook'}
HEB=re.compile('[א-ת]')
BANNED_EN_RE=terms_re(('who approves','approver','requires approval','pending approval','CEO','senior management','authority table'))
def _lang(lang):return'en'if str(lang or'').lower()[:2]=='en'else'he'
def columns(lang='he'):return TXT[_lang(lang)]['cols']
def _label(d,default_label,lang='he',proposed=False):
	G=proposed;F=default_label;C=lang;B=TXT[_lang(C)]
	if d.get('crosses_red_line'):
		H=d.get('user_decision')or{}
		if H.get('answer_kind')=='explicit':return B['red_ans']%(H.get('answer')or B['red_ans_none'])
		return B['red_need']
	D=d.get('source');A=str(d.get('source_label')or'').strip()
	if A in('areo_proposal','הצעת Areo','Areo proposal'):I=str(d.get('topic')or d.get('summary')or'').strip().rstrip('.');A=('Areo clause: %s'if _lang(C)=='en'else'סעיף AREO: %s')%(I or d.get('id')or'')
	if A in LEGACY_LABELS:A=(SOURCE_LABELS_EN if _lang(C)=='en'else SOURCE_LABELS)[LEGACY_LABELS[A]]
	if A and _lang(C)=='en'and HEB.search(A):A=SOURCE_LABELS_EN.get(LABEL_KEY_HE.get(A)or BASIS_SOURCE.get(d.get('decision_basis'))or'','')
	if D is None and not A:D=BASIS_SOURCE.get(d.get('decision_basis'))
	if A:E=B['ppb']if G and A in PLAYBOOK_LABELS else A
	elif G and D in(None,'playbook'):E=B['ppb']
	else:E=B['src'].get(D,F if F is not None else B['pb'])
	return E+B['stance'].get(d.get('stance_applied'),'')
def shown_to_client(d,conceded=()):
	if d.get('op')!='accept':return True
	if d.get('carried_from')and not d.get('crosses_red_line'):return False
	return bool(d.get('material')or d.get('tier')=='deal_breaker'or d.get('deliberate_concession')or d.get('id')in set(conceded or())or d.get('crosses_red_line')or d.get('stance_applied'))
COMPLIANCE_RX=re.compile('bribery|corruption|FCPA|anti-?bribery|sanction|boycott|export control|money laundering|\\bAML\\b|modern slavery|שוחד|שחיתות|סנקצי|חרם|פיקוח על יצוא|הלבנת הון|מימון טרור',re.I)
def is_compliance(d):
	if d.get('situation')==8 or d.get('compliance')is True or d.get('kind')=='compliance':return True
	return bool(COMPLIANCE_RX.search(' '.join(str(d.get(A)or'')for A in('topic','category_name','rule_title'))))
OP_WHAT={'he':{'accept':'קיבלנו את הנוסח שלהם','delete_paragraph':'מחקנו את הסעיף','comment_only':'הערה בלבד, בלי שינוי','for_call':'נשאיר לשיחה עם הצד השני','insert_paragraph':'הוספנו סעיף','replace':'תיקנו את הנוסח','replace_span':'תיקנו את הנוסח'},'en':{'accept':'We accepted their wording','delete_paragraph':'We deleted the clause','comment_only':'A comment only, no change','for_call':'Left for a call with the other side','insert_paragraph':'We added a clause','replace':'We edited the wording','replace_span':'We edited the wording'}}
def clause_ref(d,nm=None,lang='he'):
	A=(nm or{}).get(d.get('id'))or d.get('clause_label')
	if A:return A
	if isinstance(d.get('para'),int):return('Paragraph %d'if _lang(lang)=='en'else'פסקה %d')%(d['para']+1)
	if isinstance(d.get('after_para'),int):return('New clause after paragraph %d'if _lang(lang)=='en'else'סעיף חדש אחרי פסקה %d')%(d['after_para']+1)
	return''
def what_decided(d,lang='he'):
	for C in('summary','plain_effect'):
		if str(d.get(C)or'').strip():return str(d[C]).strip()
	D=str(d.get('external_comment')or'').strip()
	if D:return re.split('(?<=[.!?])\\s',D,1)[0][:160]
	A=OP_WHAT[_lang(lang)];B=str(d.get('new')or d.get('new_text')or d.get('text')or'').strip();E=A['for_call']if d.get('coverage')=='for_call'else A.get(d.get('op'),A['replace']);return'%s: "%s"'%(E,B[:80]+('...'if len(B)>80 else''))if B else E
def table_decisions(decisions):
	C,D=[],set()
	for B in decisions:
		if is_compliance(B):continue
		A=B.get('cluster_id')
		if A and A in D:continue
		if A:D.add(A)
		C.append(B)
	return C
def display_rows(decisions,rows,concessions=()):
	E={A.get('clause_ref')for A in concessions or()if isinstance(A,dict)};A=table_decisions(decisions);B,C=[],0
	for(D,F)in enumerate(rows):
		if D<len(A)and not shown_to_client(A[D],E):C+=1;continue
		B.append(F)
	return B,C
def hidden_line(n,lang='he'):return TXT[_lang(lang)]['hidden']%n
def build_review_table(decisions,numbering_map=None,default_label=None,concessions=(),lang='he',proposed=False):
	C=lang;B=concessions;A=TXT[_lang(C)];F,G,H=A['cols'];I=numbering_map or{};D=[]
	for E in table_decisions(decisions):D.append({F:clause_ref(E,I,C),G:what_decided(E,C),H:_label(E,default_label,C,proposed)})
	if B:D.append({F:A['conc']%len(B),G:'; '.join(A.get('topic','')for A in B),H:A['conc_label']%', '.join(sorted({A['kind'].get((B.get('user_decision')or{}).get('answer_kind'),A['no_answer'])for B in B}))})
	return D
def _row_lang(rows):return'en'if any(set(A)&set(COLUMNS_EN)for A in rows)else'he'
def render_markdown(rows,lang=None):
	A=columns(lang or _row_lang(rows));B=['| %s |'%' | '.join(A),'|%s'%('---|'*len(A))]
	for C in rows:B.append('| %s |'%' | '.join(str(C.get(A,'')).replace('|','/')for A in A))
	return'\n'.join(B)
def check_review_table(rows,decisions=(),lang=None):
	G=decisions;E=rows;C=lang;C=_lang(C or _row_lang(E));I=TXT[C];D=I['cols'];A=[]
	for B in E:
		if set(B)-set(D):A.append('extra_column:%s'%','.join(sorted(set(B)-set(D))))
		F=' '.join(str(A)for A in B.values())
		if BANNED_RE.search(F)or C=='en'and BANNED_EN_RE.search(F):A.append('approval_chain_wording')
		if ENGLISH_KIND.search(F):A.append('english_label')
		if C=='en'and any(A in str(B.get(D[2],''))for A in('מהפלייבוק','מהמדיניות','מטיוטת','הכרעתך','ויתורים')):A.append('other_language_label')
	H={A.get('id'):A for A in G}
	for(B,J)in zip(E,table_decisions(G)):
		if J.get('crosses_red_line')and B.get(D[2])in PLAYBOOK_LABELS|PROPOSED_LABELS:A.append('red_line_labeled_from_playbook')
	if any(A.get('situation')==8 for A in H.values())and any(A.get(D[0])in{A.get('id')for A in H.values()if A.get('situation')==8}for A in E):A.append('compliance_in_table')
	return sorted(set(A))
