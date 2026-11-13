#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (c) Areo. All rights reserved. Licensed under the terms at https://areo.co.il/legal/terms
'קליטת גיליון העמדות החתום, וכתיבת המעמד לכל השכבות בפעולה אחת.'
import io,json,os,subprocess,sys
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
import areo_lib
from common.cli import OutputRefused,guard_out,no_bytecode,parser
from playbook import after_ingest,ingest_approval
from playbook import status as S
from playbook.ingest_approval import EVIDENCE_KINDS
def load(path,what):
	A=path
	if not os.path.exists(A):print('%s אינו קיים: %s'%(what,A));raise SystemExit(2)
	with open(A,encoding='utf-8')as B:return json.load(B)
def save(path,data):
	with open(path,'w',encoding='utf-8')as A:json.dump(data,A,ensure_ascii=False,indent=1)
def index_entry_of(index,model,core=None):
	C=core;B=index;A=model
	if not B:return None,None
	D=B.get('playbooks')if isinstance(B,dict)else B
	if not isinstance(D,list):return None,None
	C=C or{};F=(A.get('scope_summary')or{}).get('contract_families')or[{}];G=A.get('family_code')or A.get('family_id')or C.get('family_code');H=A.get('company_role_code')or C.get('company_role_code')or F[0].get('company_role_code')or A.get('company_role');E=[A for A in D if isinstance(A,dict)and(A.get('family_code')or A.get('family_id'))==G and A.get('company_role_code')==H]
	for I in[A for A in E if not A.get('legacy')]or E:return I,D
	return None,D
HERE=os.path.dirname(os.path.abspath(__file__))
RECORDS_LINE='רשומה : %s'
QUEUE_LINE={'he':'מחכים לכם: %d עמדות לאישור במנה, %d מספרים לקבוע, %d שאלות, %d נושאים לעבור עליהם אחד אחד, ועוד %d עמדות שמחכות לקביעת מספר.','en':'Waiting for you: %d positions to approve in a batch, %d numbers to set, %d questions, %d topics to go through one by one, and %d more positions waiting for a number.'}
def _lang(a,model):
	if a.lang:return S.norm_lang(a.lang)or'he'
	if a.profile and os.path.exists(a.profile):
		B=load(a.profile,'הפרופיל');A=S.norm_lang(B.get('display_language'))
		if A:return A
	return S.model_lang(model)
def _deal_states(paths):
	B=[]
	for A in paths or():
		if os.path.isdir(A):
			for(D,C,E)in os.walk(A):
				C[:]=[A for A in C if A!='versions']
				if'negotiation_state.json'in E:B.append(os.path.join(D,'negotiation_state.json'))
		elif os.path.exists(A):B.append(A)
	return[load(A,'קובץ המצב')for A in sorted(B)]
def _changes_wording(batch,answers):
	for A in batch['items']:
		B=(answers.get(A['n'])or{}).get('action')
		if B=='change'or A['kind']=='update'and B=='approve':return True
	return False
def _keep_version(model_path):
	A=subprocess.run([sys.executable,'-B',os.path.join(HERE,'keep_version.py'),os.path.dirname(os.path.abspath(model_path))],capture_output=True,text=True,encoding='utf-8',errors='replace');B=(A.stdout or A.stderr or'').strip().splitlines()
	if B:print(B[0])
def playbooks_folder_from_profile(profile_path):
	B=profile_path
	if not B or not os.path.exists(B):return
	try:
		with open(B,encoding='utf-8')as C:A=(json.load(C)or{}).get('connections')or{}
	except(OSError,ValueError):return
	if A.get('playbooks_folder'):return str(A['playbooks_folder'])
	if A.get('shared_output_folder'):return os.path.join(str(A['shared_output_folder']),'פלייבוקים')
def _local_copy(a,model,out):
	B=model;C=getattr(a,'local_copy_dir',None)or playbooks_folder_from_profile(getattr(a,'profile',None));A=after_ingest.save_local_copy([a.model,a.core,(out or{}).get('word')or a.word,(out or{}).get('workspace')or a.workspace],B.get('family_id')or B.get('playbook_id'),C)
	if A['copied']:print('עותק מקומי: %s (%d קבצים)'%(A['dir'],len(A['copied'])))
	for D in A['errors']:print('עותק מקומי לא נשמר: %s'%D)
	return A
def chat_main(a):
	if not os.path.exists(a.model):print('המודל אינו קיים: %s'%a.model);return 2
	A=load(a.model,'המודל');B=_lang(a,A);V=ingest_approval.Q[B];H=S.record_cells_for(A,a.model)
	if a.status:D=S.derive_status(A,H,lang=B);Q=ingest_approval.load_queue(a.records,A)if a.records else{};I=ingest_approval.queue_state(A,H,B,a.revisit_skipped,Q.get('demoted')or[],Q.get('skipped')or[]);print(D['label']);print(S.progress_line(D,B));print(QUEUE_LINE[B]%(len(I['batch']),len(I['decisions']),len(I['questions']),len(I['topics']),I['waiting']));return 0
	if not a.records:print('--records חובה בתור האישור: שם נשמרים המנה והרשומות');return 2
	E=ingest_approval.load_queue(a.records,A)
	if a.queue:
		R=[]
		if a.from_deal:
			T=_deal_states(a.from_deal)
			if not T:print('לא נמצא קובץ מצב של עסקה: %s'%', '.join(a.from_deal));return 2
			C,R=ingest_approval.deal_updates(T,A,B)
		else:C=ingest_approval.make_batch(A,H,B,a.stage,a.revisit_skipped,E.get('demoted')or[],E.get('skipped')or[])
		D=S.derive_status(A,H,lang=B);print(D['label']);print(S.progress_line(D,B))
		if C is None:print(V['empty'])
		else:C=ingest_approval.issue_batch(E,C,B,a.today);ingest_approval.save_queue(a.records,A,E);print();print(ingest_approval.render_batch(C,A,B))
		for W in R:print(W)
		return 0
	C=ingest_approval.open_batch(E)
	if not C:print('אין מנה פתוחה בתור. הפיקו מנה ב---queue, והציגו אותה, לפני שקולטים תשובה.');return 3
	try:
		K=ingest_approval.parse_reply(a.answer,C)
		if not ingest_approval._is_person_name(a.approver or''):raise ingest_approval.ReplyError('"%s" אינו שם מלא של אדם (--approver). כל תשובה נרשמת בשם המאשר'%(a.approver or''))
	except ingest_approval.ReplyError as L:print('התשובה לא נקלטה, ושום דבר לא נכתב: %s'%L);return 3
	M=load(a.core,'הגרעין')if a.core else None;N=load(a.index,'האינדקס')if a.index else None;O,X=index_entry_of(N,A,M)
	if a.index and O is None:print('אזהרה: אין ב-%s רשומה למשפחה ולצד של המודל, ולכן המעמד לא ייכתב לאינדקס.'%a.index)
	if _changes_wording(C,K):_keep_version(a.model)
	try:F=ingest_approval.apply_answers(A,C,K,a.approver,a.role,a.answer,a.today,H,B)
	except ingest_approval.ReplyError as L:print('התשובה לא נקלטה, ושום דבר לא נכתב: %s'%L);return 3
	Y=(S._latest_record(A)or{}).get('record_id');J=ingest_approval.save_chat_record(a.records,F,supersedes=Y)
	try:U=os.path.relpath(os.path.abspath(J),os.path.dirname(os.path.abspath(a.model)))
	except ValueError:U=os.path.abspath(J)
	P=F['wording_changed'];G=after_ingest.apply_ingest(A,M,O,F,U,word_path=None if P else a.word,workspace_path=None if P else a.workspace);save(a.model,A)
	if a.core:save(a.core,M)
	if a.index and O is not None:save(a.index,N if isinstance(N,dict)else X)
	C.update(status='answered',record_id=os.path.splitext(os.path.basename(J))[0],answered_by=a.approver);E.setdefault('skipped',[]).extend(A for A in F['record'].get('skipped')or()if':'in A)
	if C['stage']=='batch':E.setdefault('demoted',[]).extend(A['key']for A in C['items']if(K.get(A['n'])or{}).get('action')=='except')
	ingest_approval.save_queue(a.records,A,E);_local_copy(a,A,G);Z,D=F['summary'],G['status'];print(ingest_approval.summary_line(Z,B));print(S.label_for(D,B));print(S.progress_line(D,B))
	for b in F['warnings']:print('  %s %s'%('Note:'if B=='en'else'שימו לב:',b))
	if G.get('closed'):print('%s %s'%('Answered questions:'if B=='en'else'שאלות שנענו:',', '.join(G['closed'])))
	print(RECORDS_LINE%J)
	if P:print('הנוסח השתנה בפלייבוק (גרסה %s). יש לבנות מחדש את הגרעין, הרישום וסביבת העבודה (SKILL.md, "בדיקות החובה"), ורק אז להמשיך.'%A.get('version'))
	for c in G.get('problems')or():print('  סתירה בין השכבות: %s'%c)
	return 4 if G.get('problems')else 0
def main(argv=None):
	no_bytecode();B=parser(__doc__.split('\n')[0],out_required=False,out_help='דוח הקליטה (JSON). הקבצים עצמם מתעדכנים בכל מקרה');B.add_argument('--signed',help='הגיליון החתום שחזר. חובה בקליטת גיליון');B.add_argument('--manifest',help='המניפסט של אותה הפקה. חובה בקליטת גיליון');B.add_argument('--model',required=True,help='playbook-model.json');B.add_argument('--core',help='playbook-core.json');B.add_argument('--index',help='playbooks/index.json');B.add_argument('--records',help='תיקיית רשומות האישור. חובה בקליטת גיליון ובתור');B.add_argument('--local-copy-dir',help='תיקיית הבסיס של העותק המקומי (ברירת מחדל: Areo-playbooks-local בתיקיית הבית)');B.add_argument('--queue',action='store_true',help='מפיק את המנה הבאה בתור האישור');B.add_argument('--answer',help='התשובה של המאשר למנה הפתוחה, מילה במילה');B.add_argument('--status',action='store_true',help='המעמד והתקדמות האישור, בלי לכתוב');B.add_argument('--stage',choices=ingest_approval.STAGES,help='שלב מסוים בתור');B.add_argument('--from-deal',action='append',help='קובץ המצב של עסקה, או תיקיית transactions');B.add_argument('--approver',help='השם המלא של המאשר');B.add_argument('--role',help='התפקיד של המאשר');B.add_argument('--lang',help='שפת הממשק של התור: he או en');B.add_argument('--profile',help='פרופיל-לקוח.json, לשפת הממשק');B.add_argument('--revisit-skipped',action='store_true',help='גם עמדות שדולגו');B.add_argument('--received-via',choices=EVIDENCE_KINDS,help='הערוץ שבו הקובץ הגיע: user_upload (המשתמש העלה אותו) או chat_attachment (צרופה של המארח)');B.add_argument('--upload-ref',help='הקובץ בתיקיית ההעלאות, או מזהה הצרופה. בלעדיו הקליטה היא simulated');B.add_argument('--word',help='ה-Word של הפלייבוק, להטבעת המעמד מחדש');B.add_argument('--workspace',help='קובץ סביבת העבודה, להטבעת המעמד מחדש');B.add_argument('--supersedes',help='מזהה רשומה שהקליטה הזאת מחליפה');B.add_argument('--reason',help='נימוק להחלפת רשומה. חובה עם --supersedes');B.add_argument('--today',help='תאריך הקליטה. לבדיקות בלבד');A=B.parse_args(argv)
	if A.queue or A.status or A.answer is not None:return chat_main(A)
	if not(A.signed and A.manifest and A.records):print("קליטת גיליון: --signed, --manifest ו---records חובה. לאישור בצ'אט: --queue או --answer");return 2
	if A.supersedes and not A.reason:print('--supersedes בלי --reason: החלפת רשומת אישור אינה פעולה שקטה');return 2
	if not os.path.exists(A.signed):print('הגיליון החתום אינו קיים: %s'%A.signed);return 2
	P=load(A.manifest,'המניפסט');E=load(A.model,'המודל');G=load(A.core,'הגרעין')if A.core else None;H=load(A.index,'האינדקס')if A.index else None;I,Q=index_entry_of(H,E,G)
	if A.index and I is None:print('אזהרה: אין ב-%s רשומה למשפחה ולצד של המודל, ולכן המעמד לא ייכתב לאינדקס. זו שכבה שתישאר מאחור.'%A.index)
	try:D=ingest_approval.ingest(A.signed,P,received_via=A.received_via,upload_ref=A.upload_ref,today=A.today)
	except ValueError as J:print('הקליטה נעצרה: %s'%J);return 3
	for R in D.get('warnings')or():print('  אזהרה: %s'%R)
	if not D.get('record'):print('לא נקלטה רשומה. הגיליון אינו הגרסה הסופית לחתימה, או שאין בו חתימה קבילה.');return 3
	N=ingest_approval.merge_prior(D,S.record_cells_for(E,A.model))
	if N:print("נשמרו %d עמדות שאושרו קודם בצ'אט, על אותו נוסח, בעמודות שלא נחתמו בגיליון."%N)
	K=ingest_approval.save_record(A.records,A.signed,D,supersedes=A.supersedes,reason=A.reason);C=after_ingest.apply_ingest(E,G,I,D,K,word_path=A.word,workspace_path=A.workspace);save(A.model,E)
	if A.core:save(A.core,G)
	if A.index and I is not None:save(A.index,H if isinstance(H,dict)else Q)
	L=C['status'];_local_copy(A,E,C);print('מעמד  : %s'%L.get('playbook_status'));print('תווית : %s'%L.get('label'));F=D['cells'];T=sum(1 for A in F.values()if A.get('status')=='approved');print('תאים  : %d מאושרים מתוך %d'%(T,len(F)));M=sorted(A for(A,B)in F.items()if(B.get('reason')or'').startswith('נשאר ערך שלא נקבע'))
	if M:print('חסר ערך: %d תאים עם סוגריים של ערך שלא נקבע (דף "החלטות הנהלה"): %s'%(len(M),', '.join(M)))
	if C.get('closed'):print('נסגרו : %s'%', '.join(C['closed']))
	print('רשומה : %s'%K)
	if D['record'].get('simulated'):print('הקליטה simulated (אין --upload-ref): שער המדיניות אינו נפתח.')
	for U in C.get('problems')or():print('  סתירה בין השכבות: %s'%U)
	if C.get('word'):print('Word  : %s'%C['word'])
	if C.get('workspace'):print('סביבה : %s'%C['workspace'])
	if A.out:
		try:O=guard_out(A.out,inputs=[A.signed,A.manifest,A.model,A.core,A.index,A.word,A.workspace])
		except OutputRefused as J:print('הדוח לא נכתב. סירוב: %s'%J)
		else:save(O,{'status':L,'cells':F,'record_path':K,'closed':C.get('closed'),'problems':C.get('problems'),'warnings':D.get('warnings')});print('נכתב %s'%O)
	return 4 if C.get('problems')else 0
if __name__=='__main__':sys.exit(main())
