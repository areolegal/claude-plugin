#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (c) Areo. All rights reserved. Licensed under the terms at https://areo.co.il/legal/terms
'התוצרים בהליך תחרותי ובתנאים מקוונים: טבלת שאלות הבהרה ותזכיר החלטה פנימי, בקובצי Word.'
import argparse,datetime as _dt,io,json,os,re,sys
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
import areo_lib
from docx import Document
from docx.shared import Pt
from common import paths,rtl
from common.cli import OutputRefused,guard_out
from orchestrator import state_builder as SB
MAX_QUESTIONS=20
PRIORITY={'HIGH':0,'MEDIUM':1,'LOW':2}
_LABEL_START='(?:^|[.:;!?\\n]\\s*)(?:\\d+[.)]\\s*)?'
_LABEL_END='\\s*(?:[.:;,!\\-]|$)'
FORBIDDEN=re.compile(_LABEL_START+'(?:(?:לא|אינו)\\s+)?(?:מוסכם|מקובל)(?:\\s+עלינו)?'+_LABEL_END+'|'+_LABEL_START+'(?:not\\s+)?(?:agreed|accepted|acceptable)'+_LABEL_END+"|(?:לא\\s+|אינו\\s+)?מקובל\\s+עלינו|\\b(?:not\\s+)?acceptable\\s+to\\s+us\\b|\\bwe\\s+(?:do\\s+not\\s+|don't\\s+)?agree\\b|(?:לא|אינו|אינה)\\s+(?:מוסכם|מוסכמת|מקובל|מקובלת)\\s+על\\s+(?:ה)?(?:חברה|לקוח|לקוחה|מזמין|מזמינה)(?![א-ת])|\\b(?:not\\s+)?(?:agreed|accepted|acceptable)\\s+(?:to|by)\\s+(?:the\\s+)?(?:company|client|customer)\\b|פלייבוק|playbook|קו\\s+(?:ה)?אדום|red\\s+lines?\\b|מדיניות\\s+(?:ה)?(?:חברה|פנימית|חוזית|שלנו)|מדיניותנו|\\b(?:our|internal|company|contracting)\\s+polic(?:y|ies)\\b|(?:עמדת|מדרגת)\\s+(?:ה)?נסיגה|נסיגה\\s+(?:ראשונה|אחרונה|שנייה)|\\bfallback\\s+position\\b|\\b(?:our|first|last)\\s+fallback\\b|עמדת\\s+(?:ה)?חברה|עמדתנו|\\bour\\s+position\\b",re.I|re.M)
RECOMMEND={'go':'לגשת','go_priced':'לגשת ולתמחר את הסיכון','go_if_answered':'לגשת בכפוף לתשובה לשאלה','no_go':'לא לגשת'}
NATURE={'mandatory_law':'הוראת דין כופה','commercial':'עמדה מסחרית של המזמין'}
SIGN_FROM_GO={'tender_awarded':{'go':'sign','go_priced':'sign_with_reservation','go_if_answered':'sign_with_reservation','no_go':'no_sign'},'standard_form_online':{'go':'sign','go_priced':'sign_priced','go_if_answered':'request_signed','no_go':'no_sign'}}
PAPER_TXT={'he':{'tender_awarded':{'memo':'תזכיר החלטה פנימי: חתימה על הסכם ההליך התחרותי','recommend':{'sign':'לחתום','sign_with_reservation':'לחתום עם הסתייגות','no_sign':'לא לחתום'}},'standard_form_online':{'memo':'תזכיר החלטה פנימי: האם לקבל את התנאים','recommend':{'sign':'לקבל את התנאים','sign_priced':'לקבל ולתמחר את הסיכון','request_signed':'לבקש הסכם ארגוני חתום','no_sign':'לא לקבל'},'nature':{'mandatory_law':'הוראת דין כופה','commercial':'עמדה מסחרית של הצד שכנגד'}}},'en':{'tender_awarded':{'memo':'Internal decision memo: signing the procedure agreement','recommend':{'sign':'Sign','sign_with_reservation':'Sign with a reservation','no_sign':'Do not sign'}},'standard_form_online':{'memo':'Internal decision memo: whether to accept the terms','recommend':{'sign':'Accept the terms','sign_priced':'Accept and price the risk','request_signed':'Ask for a signed enterprise agreement','no_sign':'Do not accept'},'nature':{'mandatory_law':'Mandatory law','commercial':'Commercial position of the counterparty'}}}}
TXT={'he':{'recommend':RECOMMEND,'nature':NATURE,'q_title':'טבלת שאלות הבהרה','q_head':('מספר','מסמך','סעיף','עמוד','השאלה'),'memo':'תזכיר החלטה פנימי: האם לגשת','internal':'פנימי, לא למשלוח','q_deadline':'המועד האחרון לשאלות הבהרה: %s','s_deadline':'המועד האחרון להגשה: %s','m_head':('נושא','סעיף','מה קובע הסעיף','דין כופה או עמדה מסחרית','השפעה על המחיר','השפעה על הסיכון','המלצה'),'f_questions':'שאלות הבהרה','f_memo':'תזכיר פנימי'},'en':{'recommend':{'go':'Bid','go_priced':'Bid and price the risk','go_if_answered':'Bid subject to the answer','no_go':'Do not bid'},'nature':{'mandatory_law':'Mandatory law','commercial':'Commercial position of the buyer'},'q_title':'Clarification questions','q_head':('No.','Document','Clause','Page','Question'),'memo':'Internal decision memo: whether to bid','internal':'Internal, not for sending','q_deadline':'Deadline for clarification questions: %s','s_deadline':'Submission deadline: %s','m_head':('Topic','Clause','What the clause says','Mandatory law or commercial position','Price impact','Risk impact','Recommendation'),'f_questions':'Clarification questions','f_memo':'Internal memo'}}
def load(path,what):
	A=path
	if not A or not os.path.exists(A):print('%s אינו קיים: %s'%(what,A));raise SystemExit(2)
	with io.open(A,encoding='utf-8')as B:return json.load(B)
def table(doc,head,rows,lang='he'):
	A=doc.add_table(rows=1,cols=len(head));A.style='Table Grid'
	for(B,C)in enumerate(head):
		A.rows[0].cells[B].text=C
		for D in A.rows[0].cells[B].paragraphs[0].runs:D.bold=True
	for E in rows:
		F=A.add_row().cells
		for(B,G)in enumerate(E):F[B].text=str(G or'')
	if lang!='en':rtl.set_table_rtl(A)
	return A
def out_path(deal,agreement_type,company,what,date):A=' - '.join(A for A in(agreement_type,company,what,date)if A)+'.docx';A=re.sub('[\\\\/:*?"<>|]','',A);B=paths.unique_path(os.path.join(deal,A));paths.check_write_path(B);guard_out(B);return B
def _scrub(text,lang='he'):
	A=text
	if A is None:return
	try:import content_checks as B;return B.scrub_client_text(A,None,lang)
	except Exception:return A
def build_questions(qs,path,company,lang='he'):
	A=lang;D=TXT[A];B=Document();rtl.add_paragraph(B,D['q_title'],bold=True,size=16);E=[]
	for(F,C)in enumerate(qs,1):E.append((F,_scrub(C.get('document'),A),C.get('contract_ref'),C.get('page'),_scrub(C.get('question'),A)))
	table(B,D['q_head'],E,A);rtl.enforce(B,A,author=company,keep_hebrew=True);B.save(path)
def build_memo(memo,path,company,paper,lang='he'):
	G=paper;D=memo;B=lang;C=dict(TXT[B],**PAPER_TXT[B].get(G,{}));A=Document();rtl.add_paragraph(A,C['memo'],bold=True,size=16);rtl.add_paragraph(A,C['internal'],bold=True,size=11)
	if G=='tender_pre_bid':
		if D.get('questions_deadline'):rtl.add_paragraph(A,C['q_deadline']%D['questions_deadline'],bold=True)
		if D.get('submission_deadline'):rtl.add_paragraph(A,C['s_deadline']%D['submission_deadline'],bold=True)
	if G=='standard_form_online'and D.get('signed_agreement_recommendation'):rtl.add_paragraph(A,D['signed_agreement_recommendation'])
	H=[]
	for E in D.get('items')or[]:F=E.get('recommendation');F=SIGN_FROM_GO.get(G,{}).get(F,F);H.append((_scrub(E.get('topic'),B),E.get('contract_ref'),_scrub(E.get('what'),B),C['nature'].get(E.get('nature'),''),_scrub(E.get('price_impact'),B),_scrub(E.get('risk_impact'),B),C['recommend'].get(F,F or'')))
	table(A,C['m_head'],H,B)
	for I in A.sections[0].header.paragraphs or[A.sections[0].header.add_paragraph()]:I.add_run(C['internal']).font.size=Pt(9)
	rtl.enforce(A,B,author=company,keep_hebrew=True);A.save(path)
def main(argv=None):
	sys.dont_write_bytecode=True;sys.stdout.reconfigure(encoding='utf-8',errors='replace');C=argparse.ArgumentParser(description=__doc__.split('\n')[0]);C.add_argument('--deal',required=True);C.add_argument('--memo',required=True,help='JSON התזכיר');C.add_argument('--agreement-type',required=True);C.add_argument('--company',default='');C.add_argument('--date',help='התאריך בשם הקובץ (כלל 3.6: D.M.YYYY בעברית, "3 April 2027" באנגלית, או ISO); בלעדיו: היום');C.add_argument('--lang',choices=('he','en'),help='שפת התוצרים; בלעדיו: meta.lang בקובץ המצב');A=C.parse_args(argv);F=load(os.path.join(A.deal,'negotiation_state.json'),'קובץ המצב');G=F.get('paper_type')or(F.get('meta')or{}).get('paper_type')
	if G not in('tender_pre_bid','tender_awarded','standard_form_online'):print('סוג הנייר הוא %s, ולא הליך תחרותי או תנאים מקוונים. התגובה נבנית ב-apply_redlines.py.'%G);return 2
	N=load(A.memo,'התזכיר');D=rtl.lang_of(A.lang,(F.get('meta')or{}).get('lang'));I=TXT[D];J=SB.display_date(A.date,D)if A.date and re.fullmatch('\\d{4}-\\d{2}-\\d{2}',A.date)else A.date or SB.display_date(None,D);H=[]
	if G=='tender_pre_bid':
		E=sorted(F.get('clarification_questions')or[],key=lambda q:(PRIORITY.get(str(q.get('priority')).upper(),3),q.get('number')or 0));K=[A for A in E if FORBIDDEN.search(A.get('question')or'')]
		if K:
			for L in K:print('שאלה %s נוסחה כעמדה ולא כבקשה ("%s"): התשובות מתפרסמות לכל המציעים.'%(L.get('number'),FORBIDDEN.search(L['question']).group(0)))
			return 3
		if len(E)>MAX_QUESTIONS:print('יש %d שאלות; בטבלה נכנסות %d המהותיות ביותר, לפי החשיבות.'%(len(E),MAX_QUESTIONS));E=E[:MAX_QUESTIONS]
		B=out_path(A.deal,A.agreement_type,A.company,I['f_questions'],J);build_questions(E,B,A.company,D);H.append(B)
	B=out_path(A.deal,A.agreement_type,A.company,I['f_memo'],J);build_memo(N,B,A.company,G,D);H.append(B)
	for B in H:M=rtl.audit(B,D,run_date=_dt.date.today());print('נבנה: %s%s'%(B,''if not M else'  (בדיקת כיווניות: %s)'%'; '.join(M[:3])))
	return 0
def _main(argv=None):
	try:return main(argv)
	except OutputRefused as A:print('סירוב: %s'%A);return 1
if __name__=='__main__':sys.exit(_main())
