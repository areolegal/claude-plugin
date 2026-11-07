#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (c) Areo. All rights reserved. Licensed under the terms at https://areo.co.il/legal/terms
'שער האיכות: הבדיקה שאין דליפה פנימית, ובניית העותק למשלוח.'
import json,re,os,shutil,sys,tempfile
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
import areo_lib
from common.cli import OutputRefused,guard_out,load_docx_or_explain,no_bytecode,parser
from common import docx_tracked,paths
from orchestrator import pre_send,qa_gate
from lawyer import lawyer_view
import content_checks,playbook_map
def load(path,what,required=True):
	B=what;A=path
	if not A:
		if required:print('חסר %s'%B);raise SystemExit(2)
		return
	if not os.path.exists(A):print('%s אינו קיים: %s'%(B,A));raise SystemExit(2)
	try:
		with open(A,encoding='utf-8')as C:return json.load(C)
	except ValueError as D:print('%s אינו JSON תקין (%s): %s'%(B,D,A));raise SystemExit(2)
def playbook_of(state,deal):
	B=state
	if not(B and deal):return
	A=(B.get('playbook_resolution')or{}).get('chosen')or(B.get('positions_source')or{}).get('document')or''
	if not A or not str(A).endswith('.json'):return
	C=os.path.dirname(os.path.dirname(os.path.abspath(deal)));D=A if os.path.isabs(A)else os.path.join(C,str(A).replace('\\','/'))
	try:
		with open(D,encoding='utf-8')as E:return json.load(E)
	except(OSError,ValueError):return
PRE_SEND_GROUPS=(('COMPLIANCE','CONTAIN_CONCESSION_UNDECIDED'),'explicit_group','%d סעיפים צריכים את ההכרעה שלכם לפני שליחה (%s).','%d clauses need your decision before sending (%s).',['לאשר את ההמלצה בכולם','לעבור עליהם אחד אחד'],['Approve the recommendation for all','Go through them one by one']),
def coverage_for_gate(a,decisions,core,state,mode):
	C=decisions
	if C is None or not playbook_map.rules_of(core):return[]
	A=getattr(a,'coverage',None)or(os.path.join(a.deal,playbook_map.COVERAGE_FILE)if a.deal else None);B=None
	if A and os.path.exists(A):
		try:
			with open(A,encoding='utf-8')as D:B=json.load(D)
		except(OSError,ValueError):B={'rules':'לא קריא'}
	return playbook_map.check_coverage(B,core,C,state,mode,a.work)
def pre_send_preview(a,profile,state,expected,decisions,core,core_given,lawyer):
	D=state;A=decisions;B=[]
	if A is not None:B+=[A for A in content_checks.run_checks(a.work,a.received,A.get('decisions',[])if isinstance(A,dict)else A,state=D,core=core_given,manifest=load(a.manifest,'המניפסט',required=False),profile={'lawyer_names':lawyer},mode='send')if A['blocking']];B+=[A for A in coverage_for_gate(a,A,core,D,'send')if A['blocking']];B+=[A for A in verifier_findings(getattr(a,'verify_findings',None),'send',A,a.work)if A['blocking']]
	E=tempfile.mkdtemp(prefix='areo-pre-')
	try:F=os.path.join(E,'send-check.docx');docx_tracked.strip_internal(a.work,F);B+=qa_gate.run_gate(F,a.received,'send',profile,state=D,expected_accept=expected,decisions=A,lang=a.lang,core=core,deal_dir=a.deal)['failures']
	except Exception as J:print('הערה: התצוגה המקדימה של בדיקת המשלוח לא רצה (%s)'%J)
	finally:shutil.rmtree(E,ignore_errors=True)
	G,H=[],set()
	for C in B:
		I=C.get('code'),str(C.get('where'))
		if I not in H:H.add(I);G.append({'code':C.get('code'),'message':C.get('message'),'where':C.get('where')})
	return G
def pre_send_items(pre,state,lang,received_labels=None):
	F=received_labels;P=(state or{}).get('numbering_map')or{};C=lang=='en';J=[]
	for(Q,R,S,T,K,L)in PRE_SEND_GROUPS:
		M=[A for A in pre if A['code']in Q]
		if not M:continue
		D,B,G=[],[],[];N='Clause %s'if C else'סעיף %s'
		for U in M:
			for A in str(U.get('where')or'').split(','):
				A=A.strip();O=re.match('para (\\d+)$',A)
				if O:
					E=int(O.group(1));H=(F or[None]*(E+1))[E]if F and E<len(F)else None;G.append(E)
					if H and N%H not in B:B.append(N%H)
				elif A and A not in D:
					D.append(A);I=P.get(A)
					if I and I not in B:B.append(I)
		V=max(len(D)+len(G),1);J.append({'key':'pre_send:'+R,'kind':'pre_send','situation':3,'blocks_sending':True,'text':((T if C else S)%(V,', '.join(B)or'-')).replace('1 סעיפים','סעיף אחד').replace('1 clauses','One clause'),'options':list(L if C else K),'recommendation':(L if C else K)[0],'clause_ids':D,'paras':G})
	return J
def accepted_fingerprint(work):import hashlib as A;B=docx_tracked.accept_all(work);return A.sha256(json.dumps(list(B),ensure_ascii=False).encode('utf-8')).hexdigest()
def dump_for_verifier(a):
	try:C=content_checks.numbered_labels(a.work)
	except Exception:C=[]
	E=lambda i:C[i]if i is not None and i<len(C)else None;B=[]
	if a.dump_accepted_text:K=docx_tracked.accept_all(a.work);B.append((a.dump_accepted_text,[{'para':A,'label':E(A),'text':B}for(A,B)in enumerate(K)]))
	if a.dump_external_bubbles:
		F=docx_tracked.read_package(a.work);from lxml import etree;L=etree.fromstring(F['word/document.xml']);M={A['id']for A in docx_tracked.read_comments(docx_tracked.read_package(a.received))};N=docx_tracked.comment_paragraph_spans(L);O=set(content_checks.INTERNAL_AUTHORS);G=[]
		for A in docx_tracked.read_comments(F):
			if A['id']in M or A['author']in O:continue
			H,P=N.get(A['id'],(None,None));I=list(range(H,P+1))if H is not None else[];G.append({'id':A['id'],'author':A['author'],'paras':I,'labels':[E(A)for A in I],'text':A['text']})
		B.append((a.dump_external_bubbles,G))
	if a.dump_accepted_text:Q=accepted_fingerprint(a.work);B.append((a.dump_accepted_text+'.sha256',{'work_sha256':Q}))
	for(R,J)in B:
		try:D=guard_out(R,inputs=[a.work,a.received])
		except OutputRefused as S:print('סירוב: %s'%S);return 1
		os.makedirs(os.path.dirname(os.path.abspath(D))or'.',exist_ok=True)
		with open(D,'w',encoding='utf-8')as T:json.dump(J,T,ensure_ascii=False,indent=1)
		print('נכתב %s (%d)'%(D,len(J)))
	return 0
def verifier_warnings(path):
	B=path;C=load(B,'קובץ הממצאים של המאמת',required=False)
	if C is None:return[{'code':'VERIFY_SCHEMA','message':'קובץ הממצאים של המאמת חסר או אינו JSON','where':B}]
	D=content_checks.validate_verify_findings(C)
	if D:return[{'code':'VERIFY_SCHEMA','message':'קובץ הממצאים אינו במבנה: '+'; '.join(D[:5]),'where':B}]
	E=[]
	for A in C['findings']:
		if A.get('severity')!='open':continue
		E.append({'code':'VERIFY_OPEN','message':'המאמת העצמאי (%s): %s. ציטוט: "%s". לבדוק: %s'%(A['check'],A['issue'].strip(),A['quote'].strip()[:160],(A.get('suggest')or'').strip()),'where':A['where']})
	return E
def _resolution_for(finding,decisions):
	F=decisions;E=finding;B=F if isinstance(F,dict)else{};H=[A for A in(B.get('decisions')if isinstance(B.get('decisions'),list)else[])if isinstance(A,dict)];G=str(E.get('check')),str(E.get('where')).strip();I={A.get('id')for A in H if any(isinstance(A,dict)and(str(A.get('check')),str(A.get('where')).strip())==G for A in A.get('fixes_findings')or[])};C=''
	for A in B.get('verify_resolutions')or[]:
		if not isinstance(A,dict)or(str(A.get('check')),str(A.get('where')).strip())!=G:continue
		D,J=str(A.get('resolution')or''),str(A.get('note')or'').strip()
		if not J:C='חסרה הערה ב-verify_resolutions'
		elif D=='accepted_by_lawyer':return A,''
		elif D.startswith('fixed:')and D[6:]in I:return A,''
		else:C='resolution חייב להיות fixed:<מזהה הכרעה שמצהירה ב-fixes_findings על הממצא הזה> או accepted_by_lawyer'
	return None,C
def verifier_findings(path,mode,decisions=None,work=None):
	A=path;B=mode=='send'
	if not A or not os.path.exists(A):
		if not A and not B:return[]
		J='VERIFY_MISSING'if B else'VERIFY_SCHEMA';return[{'code':J,'blocking':B,'where':A or'','message':'המאמת העצמאי (n9-verify.md) לא רץ או שקובץ הממצאים שלו חסר: ללא קריאה עצמאית של הנוסח המתקבל אי אפשר לשלוח. להריץ את המאמת ולהעביר --verify-findings'}]
	try:
		with open(A,encoding='utf-8')as K:D=json.load(K)
	except(OSError,ValueError):D=None
	G=['הקובץ אינו JSON תקין']if D is None else content_checks.validate_verify_findings(D)
	if G:return[{'code':'VERIFY_SCHEMA','blocking':B,'where':A,'message':'קובץ הממצאים אינו במבנה: '+'; '.join(G[:5])}]
	E=[]
	if work:
		try:F=accepted_fingerprint(work)
		except Exception:F=None
		H=str(D.get('work_sha256')or'')
		if F and not H:E.append({'code':'VERIFY_NOT_BOUND','blocking':B,'where':A,'message':'בקובץ הממצאים אין work_sha256: אי אפשר לדעת על איזה נוסח הבדיקה נעשתה. להעתיק אותה מקובץ ה-.sha256 שנוצר עם --dump-accepted-text'})
		elif F and H!=F:E.append({'code':'VERIFY_STALE','blocking':B,'where':A,'message':'הנוסח המתקבל השתנה אחרי שהמאמת קרא אותו (או שהקובץ הוא מסבב אחר). להפיק מחדש את קבצי הקלט של המאמת ולהריץ אותו שוב'})
	for C in D['findings']:
		if C.get('severity')!='open':continue
		L,I=_resolution_for(C,decisions)
		if L is not None:continue
		E.append({'code':'VERIFY_OPEN','blocking':B,'where':C['where'],'message':'המאמת העצמאי (%s): %s. ציטוט: "%s". לבדוק: %s%s. לסגירה: הכרעה מתקנת, או verify_resolutions (fixed:<מזהה הכרעה> | accepted_by_lawyer, עם הערה)'%(C['check'],C['issue'].strip(),C['quote'].strip()[:160],(C.get('suggest')or'').strip(),' [%s]'%I if I else'')})
	return E
def report(res):
	A=res;print('מצב: %s'%A['mode'])
	for B in A['failures']:print('  כשל   [%s] %s%s'%(B.get('code','?'),B.get('message',''),'  (%s)'%B['where']if B.get('where')else''))
	for C in A['warnings']:print('  אזהרה [%s] %s%s'%(C.get('code','?'),C.get('message',''),'  (%s)'%C['where']if C.get('where')else''))
	D=A.get('info')or{};print('  שפה: %s   בועות חיצוניות: %s   בועות פנימיות: %s'%(D.get('lang','?'),D.get('external_comments','?'),D.get('internal_comments','?')));print('תוצאה: %s'%('עבר'if A['passed']else'נכשל: %d'%len(A['failures'])))
def main(argv=None):
	no_bytecode();D=parser(__doc__.split('\n')[0],out_required=False);D.add_argument('--mode',required=True,choices=('work','send'));D.add_argument('--work',required=True,help='קובץ העבודה, עם השכבה הפנימית');D.add_argument('--received',required=True,help='הטיוטה שהתקבלה מהצד שכנגד');D.add_argument('--profile',required=True,help='profile.json של הלקוח');D.add_argument('--send',help='נתיב העותק למשלוח. דרוש ב--mode send');D.add_argument('--state',help='negotiation_state.json של העסקה');D.add_argument('--deal',help='תיקיית העסקה: קובץ המצב, דוח השער בשם הקנוני ורשומת ההפקה');D.add_argument('--register',help='נשאר לתאימות, ואינו בשימוש: המרשם של מעריך הסיכונים אינו חוסם משלוח');D.add_argument('--decisions',help='קובץ ההכרעות של הסבב');D.add_argument('--expected-accept',help='JSON עם מערך נוסחי היעד, פסקה לפסקה. בלעדיו בדיקת ההלוך ושוב של "קבל הכול" אינה רצה, והדבר נאמר בפלט');D.add_argument('--core',help='playbook-core.json: סימני האדום של הכללים (content_checks)');D.add_argument('--manifest',help='corpus-manifest.json: שמות הצדדים בהסכמים החתומים (content_checks)');D.add_argument('--lang',choices=('he','en'),help='שפת ההסכם. בלעדיו: נגזרת מהטיוטה שהתקבלה');D.add_argument('--run-id',help='מזהה הריצה, כמו ב-apply_redlines.py: עותק למשלוח מאותה ריצה, שלא נמסר, מוחלף');D.add_argument('--dump-accepted-text',help='כותב JSON: הנוסח המתקבל אחרי "קבל הכול" על קובץ העבודה, פסקה לפסקה [{para, label, text}], למאמת העצמאי');D.add_argument('--dump-external-bubbles',help='כותב JSON: הבועות החיצוניות שלנו [{id, author, paras, labels, text}], למאמת העצמאי');D.add_argument('--verify-findings',help='קובץ הממצאים של המאמת העצמאי: במצב עבודה אזהרה (VERIFY_OPEN, VERIFY_SCHEMA); במצב משלוח חוסם: חסר = VERIFY_MISSING, ממצא open בלי verify_resolutions בקובץ ההכרעות = VERIFY_OPEN');D.add_argument('--coverage',help='rule-coverage.json: תוכנית כיסוי הכללים. ברירת מחדל: <תיקיית העסקה>/rule-coverage.json');A=D.parse_args(argv)
	if A.dump_accepted_text or A.dump_external_bubbles:
		Q=dump_for_verifier(A)
		if Q:return Q
	for(R,b)in((A.work,'קובץ העבודה'),(A.received,'הטיוטה שהתקבלה')):
		if not os.path.exists(R):print('%s אינו קיים: %s'%(b,R));return 2
	for R in(A.work,A.received):
		c,d,Q=load_docx_or_explain(R,loader=False)
		if c is None:print(d);return Q
	F=lawyer_view(load(A.profile,'הפרופיל'))
	if not F.get('lawyer_name'):print('אין בפרופיל שם עורך דין (branding.lawyer_name). השער מזהה את הבועות שלנו לפיו');return 2
	C=load(A.state,'קובץ המצב',required=False);M=A.state if C is not None else None
	if C is None and A.deal and os.path.exists(os.path.join(A.deal,'negotiation_state.json')):M=os.path.join(A.deal,'negotiation_state.json');C=load(M,'קובץ המצב')
	E=load(A.decisions,'קובץ ההכרעות',required=False);S=content_checks.attach_related(load(A.core,'הגרעין',required=False),A.core);N=S if S is not None else playbook_of(C,A.deal);H=load(A.expected_accept,'נוסחי היעד',required=False)
	if H is not None and not isinstance(H,list):print('--expected-accept הוא מערך של נוסחי פסקאות, ולא %s'%type(H).__name__);return 2
	if H is None:print('הערה: בלי --expected-accept, בדיקת "קבל הכול" (RT_ACCEPT) אינה רצה.')
	G,K=[],[]
	if E is None:print('הערה: בלי --decisions, בדיקות התוכן של הסבב (content_checks) אינן רצות.')
	else:
		T=[F.get('lawyer_name'),F.get('lawyer_name_en')]+list(F.get('lawyer_aliases')or[])
		if isinstance(E,dict)and E.get('author'):T.append(E['author'])
		W=content_checks.run_checks(A.work,A.received,E.get('decisions',[])if isinstance(E,dict)else E,state=C,core=S,manifest=load(A.manifest,'המניפסט',required=False),profile={'lawyer_names':T},mode=A.mode);G=[dict(A,code=A['code'])for A in W if A['blocking']];K=[dict(A,code=A['code'])for A in W if not A['blocking']]
	for L in coverage_for_gate(A,E,N,C,A.mode)+verifier_findings(A.verify_findings,A.mode,E,A.work):(G if L.get('blocking')else K).append(dict(L))
	if A.mode=='send'and G:
		if not A.send:print('ב--mode send דרוש --send: הנתיב שאליו ישונה שם העותק אם יעבור');return 2
		I=A.send if os.path.exists(A.send)else None;X=tempfile.mkdtemp(prefix='areo-gate-')
		try:Y=os.path.join(X,'send-check.docx');docx_tracked.strip_internal(A.work,Y);U=qa_gate.run_gate(Y,A.received,'send',F,state=C,expected_accept=H,decisions=E,lang=A.lang,core=N,deal_dir=A.deal)
		finally:shutil.rmtree(X,ignore_errors=True)
		G=list(U['failures'])+G;K=list(U['warnings'])+K;B={'mode':'send','passed':False,'failures':G,'warnings':K,'info':U.get('info')or{},'send_copy':None}
		if I:B['retracted']=pre_send.retract_send_copy(I,C,'he',deal_dir=A.deal)
	elif A.mode=='work':
		B=qa_gate.run_gate(A.work,A.received,'work',F,state=C,expected_accept=H,decisions=E,lang=A.lang,core=N,deal_dir=A.deal);T=[F.get('lawyer_name'),F.get('lawyer_name_en')]+list(F.get('lawyer_aliases')or[]);B['pre_send']=pre_send_preview(A,F,C,H,E,N,S,T)
		try:Z=content_checks.numbered_labels(A.received)
		except Exception:Z=None
		B['pre_send_items']=pre_send_items(B['pre_send'],C,(B.get('info')or{}).get('lang')or'he',Z)
	else:
		if not A.send:print('ב--mode send דרוש --send: הנתיב שאליו ישונה שם העותק אם יעבור');return 2
		try:guard_out(A.send,inputs=[A.work,A.received],allow_existing_doc=True)
		except OutputRefused as O:print('סירוב על --send: %s'%O);return 1
		I=A.send if os.path.exists(A.send)else None;P=((C or{}).get('meta')or{}).get('round_number');a=pre_send.reusable_path(A.deal,P,A.run_id,'send',C)if I else None
		if a and os.path.normcase(os.path.abspath(a))==os.path.normcase(os.path.abspath(A.send)):V,I=A.send,None;print('העותק למשלוח מאותה ריצה (%s) לא נמסר, ולכן הוא מוחלף'%os.path.basename(A.send))
		else:V=paths.unique_path(A.send)
		if I:print('בנתיב --send כבר יש עותק. הוא אינו נדרס: העותק החדש ייכתב ל-%s'%os.path.basename(V))
		B=qa_gate.build_send_copy(A.work,A.received,V,F,state=C,expected_accept=H,deal_dir=A.deal,decisions=E,lang=A.lang,core=N)
		if B.get('send_copy')and A.run_id and A.deal and P:pre_send.update_run_record(A.deal,P,A.run_id,{'send':B['send_copy']})
		if not B['passed']and I:B['retracted']=pre_send.retract_send_copy(I,C,B.get('info',{}).get('lang','he'),deal_dir=A.deal)
	if B.get('retracted')and C is not None and M:C.setdefault('meta',{})['updated_by']='orchestrator';pre_send.save_state(C,M);print('קובץ המצב עודכן: אין עותק למשלוח (%s)'%M)
	if G or K:
		if not(A.mode=='send'and B.get('failures')is G):B['failures']=list(B.get('failures')or[])+G;B['warnings']=list(B.get('warnings')or[])+K
		if G:B['passed']=False
	try:e=E.get('decisions',[])if isinstance(E,dict)else E or[];B.setdefault('info',{})['counts']=content_checks.unit_counts(e,len(docx_tracked.received_paragraphs(A.received)),((C or{}).get('meta')or{}).get('playbook_map'))
	except Exception:pass
	report(B)
	if A.mode=='work'and B.get('pre_send'):
		print('לפני שליחה, בלי שינוי, ייחסם המשלוח על %d פריטים. שאלה אחת לכל קבוצה, למנה (pre_send_items בדוח):'%len(B['pre_send']))
		for f in B.get('pre_send_items')or():print('  - '+f['text'])
		g=[A for A in B['pre_send']if not any(A['code']in B[0]for B in PRE_SEND_GROUPS)]
		for L in g:print('  [%s] %s%s'%(L['code'],L['message'],'  (%s)'%L['where']if L.get('where')else''))
	if A.mode=='send':
		if B.get('send_copy'):print('העותק למשלוח: %s'%B['send_copy'])
		else:
			print('לא נוצר עותק למשלוח, והקובץ הזמני נמחק.')
			if B.get('retracted'):print('עותק למשלוח קודם סומן: %s'%B['retracted'])
	if A.out:
		try:J=guard_out(A.out,inputs=[A.work,A.received,A.profile])
		except OutputRefused as O:print('סירוב: %s'%O);return 1
		os.makedirs(os.path.dirname(os.path.abspath(J)),exist_ok=True)
		with open(J,'w',encoding='utf-8')as h:json.dump(B,h,ensure_ascii=False,indent=2,default=str)
		print('נכתב %s'%J)
	elif A.deal:
		P=(E.get('round')if isinstance(E,dict)else None)or((C or{}).get('meta')or{}).get('round_number');J=qa_gate.run_report_path(A.deal,P,'gate-%s.json'%A.mode)
		if J:
			try:guard_out(J,inputs=[A.work,A.received,A.profile])
			except OutputRefused as O:print('הדוח לא נכתב. סירוב: %s'%O)
			else:qa_gate.write_run_report(J,B);print('נכתב %s'%J)
	return 0 if B['passed']else 3
if __name__=='__main__':sys.exit(main())
