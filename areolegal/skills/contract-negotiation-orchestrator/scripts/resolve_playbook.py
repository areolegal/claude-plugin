#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (c) Areo. All rights reserved. Licensed under the terms at https://areo.co.il/legal/terms
'איתור הפלייבוק לעסקה, בסקריפט ולא בשיקול דעת.'
import json,os,re,sys
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
import areo_lib
from common.cli import OutputRefused,guard_out,no_bytecode,parser
from orchestrator.resolve_playbook import resolve,role_code,role_side,source_label
SIDE_Q={'he':'לפי ההסכם עצמו, אתם "%s", אבל ביקשתם לעבוד כ-"%s". מי אתם בהסכם הזה?','en':'According to the agreement itself, you are "%s", but you asked us to work as "%s". Which side are you in this agreement?'}
def side_check(a,role,lang):
	E=role
	if not a.draft or not os.path.exists(a.draft):return
	G,H=list(a.company or[]),list(a.counterparty or[])
	if a.profile and os.path.exists(a.profile):
		try:
			with open(a.profile,encoding='utf-8')as I:F=json.load(I)
			G+=[F.get('organization_name'),F.get('organization_name_en')]+list(F.get('aliases')or[])
		except(OSError,ValueError):pass
	import content_checks as J;D=J.document_sides(a.draft,[A for A in G if A],H,role_side);C=role_side(E);A={'document_side':D.get('ours'),'basis':D.get('basis'),'term':D.get('our_term')or D.get('their_term'),'requested_side':C,'conflict':False,'compared':False};B=D.get('ours');K=bool(B and C)and bool(re.search('[\u0590-\u05ff]',B))==bool(re.search('[\u0590-\u05ff]',C))
	if B and C and'mutual'not in(B,C)and K:A['compared']=True
	if A['compared']and B!=C:L='en'if lang=='en'else'he';A['conflict']=True;A['question']={'key':'side_conflict','kind':'side_conflict','situation':4,'blocks_sending':True,'text':SIDE_Q[L]%(A['term']or B,E),'options':[A['term']or B,E],'recommendation':A['term']or B}
	return A
def _model_path(chosen):
	A=chosen
	if not A:return
	if os.path.basename(A)=='playbook-model.json'and os.path.exists(A):return A
	B=os.path.join(os.path.dirname(A)if os.path.isfile(A)else A,'playbook-model.json');return B if os.path.exists(B)else None
def playbook_validation(chosen):
	B=_model_path(chosen)
	if not B:return
	try:
		with open(B,encoding='utf-8')as G:C=json.load(G)
	except(OSError,ValueError)as H:return{'errors':1,'codes':['MODEL_UNREADABLE'],'checker':'local','message':str(H)}
	try:from playbook import validate_model as D;I=D.validate(C,check_wording=False);E=D.errors(I);A=sorted({A.get('code')for A in E});return{'errors':len(E),'codes':A,'checker':'playbook.validate_model'}
	except Exception:F=C.get('rules')or[];J=[A.get('id')for A in F if not A.get('id')or not(A.get('tracks')or{}).get('green')];A=(['NO_RULES']if not F else[])+(['RULE_INCOMPLETE']if J else[]);return{'errors':len(A),'codes':A,'checker':'local'}
def main(argv=None):
	no_bytecode();C=parser(__doc__.split('\n')[0],out_required=False);C.add_argument('--data',required=True,help='תיקיית Areo-נתונים של הלקוח');C.add_argument('--folder',required=True,help='התיקייה שבה ההסכם שהגיע');C.add_argument('--family',required=True,help='משפחת ההסכמים, כפי שהלקוח קורא לה');C.add_argument('--role',required=True,help='הפוזיציה של החברה בהסכם');C.add_argument('--language',required=True,help='שפת ההסכם: he / en');C.add_argument('--counterparty-kind',default='company',help='סוג הצד שכנגד: company, individual, public_body (גם גוף ממשלתי או רשות), npo או partnership; כמה בפסיק. נבדק מול applicability של הפלייבוק (activation_ok)');C.add_argument('--uploaded',help='פלייבוק שהלקוח העלה בעצמו, כשיש');C.add_argument('--min-skill-version',help='גרסת סקיל מינימלית: פלייבוק שנבנה לפניה מסומן כישן');C.add_argument('--family-label',help='שם המשפחה כפי שהוא בהסכם, כשהוא שונה');C.add_argument('--answer-kind',help='explicit כשהמשתמש בחר במפורש, לשורת המקור');C.add_argument('--lang',choices=('he','en'),default='he',help='שפת שורת המקור (שפת התוצר)');C.add_argument('--draft',help='הטיוטה שהתקבלה (docx): הצד שלנו נבדק מול הגדרות הצדדים בהסכם עצמו');C.add_argument('--profile',help='פרופיל-לקוח.json: שמות החברה, לזיהוי הצד שלנו בהסכם');C.add_argument('--company',action='append',help='שם נוסף של החברה כפי שהוא בהסכם');C.add_argument('--counterparty',action='append',help='שם הצד השני כפי שהוא בהסכם');B=C.parse_args(argv)
	if not(B.family or'').strip():print('חסרה משפחת ההסכם (--family). השלימו אותה מתוכן ההסכם, בעברית או באנגלית.');return 2
	if not(B.role or'').strip():print('חסרה הפוזיציה של החברה (--role). השלימו אותה בשער הפוזיציה.');return 2
	F=role_code(B.role)or B.role.strip();A=resolve(B.data,B.folder,B.family.strip(),F,B.language,counterparty_kind=B.counterparty_kind,uploaded=B.uploaded,min_skill_version=B.min_skill_version,agreement_family_label=B.family_label);A['source_label']=source_label(A,activation_answer_kind=B.answer_kind,lang=B.lang);J=A.get('requested_family')or{};print('משפחה: %s (%s)   פוזיציה: %s'%(B.family.strip(),', '.join(J.get('families')or['לא במילון']),F));print('תוצאה: %s'%A.get('result','-'))
	if A.get('chosen'):print('נבחר : %s'%A['chosen'])
	if A.get('reason'):print('סיבה : %s'%A['reason'])
	if A.get('choices'):print('לבחירה: %s'%', '.join(A['choices']))
	print('מועמדים: %d'%len(A.get('candidates')or[]));G=[A['path']for A in A.get('candidates')or[]if A.get('unread')]
	if G:print('לא נקראו (לקריאה ב-AREO_RT/skills/contract-negotiation-orchestrator/scripts/read_playbook_doc.py): %s'%', '.join(G))
	print('שורת המקור: %s'%A.get('source_label',''))
	if A.get('activation_ok')is not None:print('תנאי ההפעלה: %s'%('מתקיימים'if A['activation_ok']else'אינם מתקיימים: %s. שאלה אחת במנת השאלות (מצב 4)'%A.get('activation_reason','')))
	if A.get('status_label'):print('מעמד הפלייבוק (שער המדיניות): %s'%A['status_label'])
	if A.get('label_mismatch'):print('פער תוויות: %s אומרים תווית אחרת. מציגים את התווית של שער המדיניות, ומציעים לבנות מחדש את הגרעין ברכיב הפלייבוק'%', '.join(A['label_mismatch']))
	E=playbook_validation(A.get('chosen'))
	if E:
		A['playbook_validation']=E
		if E.get('errors'):print('אזהרה: הפלייבוק שנבחר אינו עובר את הבדיקה של סוכן הפלייבוק (%d ממצאים חוסמים: %s). הוא משמש בעסקה הזו, ובשורה הראשונה של ההודעה נאמר: "המדיניות שבה השתמשנו צריכה תיקון אצל סוכן הפלייבוק." (EN: "The policy we used needs fixing with the playbook agent.")'%(E['errors'],', '.join(E['codes'][:5])))
	D=side_check(B,F,B.lang)
	if D is not None:
		A['side_check']=D
		if D['conflict']:print('סתירה בצד: %s'%D['question']['text'])
		elif D['document_side']:print('הצד שלנו לפי ההסכם תואם את הפוזיציה (%s)'%D['document_side'])
		else:print('ההסכם אינו מכריע את הצד שלנו (%s): הפוזיציה כפי שנמסרה'%D['basis'])
	H=A.get('proposed_notice')or{}
	if H:print('המשפט על פלייבוק מוצע: %s'%H.get('en'if B.lang=='en'else'he',''))
	if B.out:
		try:I=guard_out(B.out,inputs=[B.uploaded]if B.uploaded else[])
		except OutputRefused as K:print('סירוב: %s'%K);return 1
		with open(I,'w',encoding='utf-8')as L:json.dump(A,L,ensure_ascii=False,indent=2)
		print('נכתב %s'%I)
	return 0
if __name__=='__main__':sys.exit(main())
