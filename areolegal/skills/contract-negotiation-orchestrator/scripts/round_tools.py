#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (c) Areo. All rights reserved. Licensed under the terms at https://areo.co.il/legal/terms
'הכלים של הסבב: מנת השאלות, "לאישורך", נקודות לשיחה, הרשימה לפני חתימה ומידתיות.'
import argparse,hashlib,json,os,re,sys
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
import areo_lib
from orchestrator import proportionality as P,question_batch as QB,review_table as RT
from orchestrator.resolve_playbook import is_proposed_status
from orchestrator import signing_checklist as SC,state_builder as SB,talking_points as TP
import copy,threads as TH
from lawyer import lawyer_view
import common.docx_tracked as dt
from common import gap_checks,paths
from common.cli import OutputRefused,guard_out
from lxml import etree
LIVE='negotiation_state.json'
MAX_TALKING_POINTS=7
def load(path,what,required=True):
	A=path
	if not A:
		if required:print('חסר %s'%what);raise SystemExit(2)
		return
	if not os.path.exists(A):print('%s אינו קיים: %s'%(what,A));raise SystemExit(2)
	with open(A,encoding='utf-8')as B:return json.load(B)
def decisions_of(path):A=load(path,'קובץ ההכרעות');return A.get('decisions',[])if isinstance(A,dict)else A
def state_of(deal):
	if not deal:return
	A=os.path.join(deal,LIVE);return load(A,'קובץ המצב')if os.path.exists(A)else None
def save_state(deal,state):
	B=deal;A=state;A.setdefault('meta',{})['updated_by']='orchestrator';C=SB.validate_state(A)
	if C:
		E=os.path.join(B,'negotiation_state.rejected.json')
		with open(E,'w',encoding='utf-8')as D:json.dump(A,D,ensure_ascii=False,indent=1)
		print('קובץ המצב לא עודכן (%d שגיאות), והגרסה שנדחתה ב-%s:'%(len(C),E))
		for F in C[:10]:print('  [%s] %s'%(F.get('code'),F.get('message')))
		return False
	A['meta']['last_updated']=SB.now_iso()
	with open(os.path.join(B,LIVE),'w',encoding='utf-8')as D:json.dump(A,D,ensure_ascii=False,indent=1)
	print('קובץ המצב עודכן: %s'%os.path.join(B,LIVE));return True
def profile_deliverable_lang(profile):
	B=profile or{};A=str(B.get('deliverable_language')or'').lower()
	if A=='both'or not A:A=str(B.get('display_language')or'').lower()
	return A[:2]if A[:2]in('he','en')else None
def out_lang(a,st):A=load(a.profile,'הפרופיל',required=False)if getattr(a,'profile',None)else None;B=str(getattr(a,'lang',None)or profile_deliverable_lang(A)or((st or{}).get('meta')or{}).get('lang')or'he').lower();return'en'if B[:2]=='en'else'he'
def _sha(path):
	A=hashlib.sha256()
	with open(path,'rb')as B:
		for C in iter(lambda:B.read(1<<16),b''):A.update(C)
	return A.hexdigest()
def compare_round(st,compare):
	C=(st or{}).get('meta')or{};B=(compare or{}).get('received')
	if B and os.path.exists(B):
		D=_sha(B)
		for A in C.get('received_documents')or():
			if isinstance(A,dict)and A.get('sha256')==D and str(A.get('round')or'').isdigit():return int(A['round'])
	return int(C.get('round_number')or 0)+1
def compare_applied(st,rnd):
	A=rnd;B=(st or{}).get('meta')or{}
	if int(B.get('round_number')or 0)!=int(A):return False
	return any(int(B.get('their_change_round')or 0)==A or B.get('closed_in_round')==A or int((B.get('escalation')or{}).get('round')or 0)==A for B in st.get('clauses')or())or any(int(B.get('round')or 0)==A for B in st.get('silent_changes')or())
def sent_basis(st,rnd=None):A=rnd;B=(st or{}).get('meta')or{};A=int(A or B.get('round_number')or 1);D=next((B for B in reversed(B.get('sent_documents')or[])if isinstance(B,dict)and str(B.get('round'))==str(A)),None);C=[A for A in(st or{}).get('produced_documents')or()if isinstance(A,dict)];E=next((A.get('path')for A in reversed(C)if A.get('kind')=='send'),None)or next((A.get('path')for A in reversed(C)if A.get('kind')=='work'),None);return D,A,E
def cmd_basis(a):
	D=state_of(a.deal)
	if D is None:print('אין קובץ מצב בתיקיית העסקה: אין סבב קודם, ואין בסיס להשוואה');return 2
	E,B,C=sent_basis(D,a.round);A=a.lang=='en';H=(D.get('quality_gate')or{}).get('send_copy')or{}
	if not E and H.get('status')=='produced_pending_send'and H.get('path'):J=os.path.basename(H['path']);K=candidate_sent_files(D,a.deal,H.get('recorded_at'));G=['Yes']+['Another file: %s'%A for A in K]+['Another file: attach it','Unknown']if A else['כן']+['קובץ אחר: %s'%A for A in K]+['קובץ אחר: צרפו אותו','לא ידוע'];print(('Was the produced copy sent, %s? %s'if A else'נשלח העותק שהופק, %s? %s')%(J,' '.join('[%s]'%A for A in G)));print(('Yes: negotiation_state.py sent --deal <deal> --file "%s" --round %d. Another file: negotiation_state.py sent --deal <deal> --file <the file> --round %d (the differences from the produced copy are recorded in lawyer_overrides, and the comparison is against the file that was sent). Unknown: compare_rounds.py --deal without --sent compares against the produced copy, marked "assumed base".'if A else'כן: negotiation_state.py sent --deal <תיקיית העסקה> --file "%s" --round %d. קובץ אחר: negotiation_state.py sent --deal <תיקיית העסקה> --file <הקובץ> --round %d (ההבדלים מהעותק שהופק נרשמים ב-lawyer_overrides, וההשוואה היא מול הקובץ שנשלח). לא ידוע: compare_rounds.py --deal בלי --sent משווה לעותק שהופק, מסומן "בסיס משוער".')%(J,B,B));return 3
	if E:
		F=E.get('file_name')or'';L=F if os.path.isabs(F)else os.path.join(a.deal,F)
		if os.path.exists(L)and(not E.get('sha256')or _sha(L)==E.get('sha256')):print(('Comparison base for round %d is known: %s (%s). Run compare_rounds.py --deal without --sent.'if A else'בסיס ההשוואה של סבב %d ידוע: %s (%s). compare_rounds.py --deal רץ בלי --sent.')%(B,F,E.get('basis')or'user_confirmed'));return 0
		print(('The file recorded as sent in round %d (%s) is missing or was changed after it was recorded.'if A else'הקובץ שנרשם כנשלח בסבב %d (%s) אינו בנתיב, או שהשתנה אחרי שנרשם.')%(B,F));C=F or C;I='Which file was actually sent to the other side in round %d? %s'if A else'איזה קובץ נשלח בפועל לצד שכנגד בסבב %d? %s'
	else:I='The send copy of round %d is not recorded as sent. Put this question in the single opening batch, and meanwhile compare against the last work file (assumed basis): which file was sent to the other side in round %d? %s'if A else'העותק למשלוח של סבב %d אינו רשום כנשלח. השאלה נכנסת למנה האחת שבפתיחה, וההשוואה רצה בינתיים מול קובץ העבודה האחרון (בסיס משוער): איזה קובץ נשלח לצד שכנגד בסבב %d? %s'
	G=(['%s (recommended)'%C]if A else['%s (ההמלצה)'%C])if C else[];N=next((A.get('produced_at')for A in reversed((D or{}).get('produced_documents')or())if isinstance(A,dict)and A.get('path')==C),None);G+=[A for A in candidate_sent_files(D,a.deal,N)if A!=C];G+=['Another file: attach it','Unknown']if A else['קובץ אחר: צרפו אותו','לא ידוע'];M=' '.join('[%s]'%A for A in G);print(I%((B,M)if I.count('%')==2 else(B,B,M)));print(('Answer: negotiation_state.py sent --deal <deal> --file <file> --round %d, then compare_rounds.py --deal without --sent. No answer, or "Unknown": compare_rounds.py --deal without --sent compares against the last work file, marked "assumed base", and the batch does not ask again.'if A else'תשובה: negotiation_state.py sent --deal <תיקיית העסקה> --file <הקובץ> --round %d, ואחריה compare_rounds.py --deal בלי --sent. בלי תשובה, או "לא ידוע": compare_rounds.py --deal בלי --sent משווה לקובץ העבודה האחרון, מסומן "בסיס משוער", והמנה אינה שואלת שוב.')%B);return 3
def candidate_sent_files(st,deal,since=None):
	E=since;import datetime as J;F=[A for A in(st or{}).get('produced_documents')or()if isinstance(A,dict)];G={os.path.normcase(os.path.basename(A.get('path')or''))for A in F};K={re.sub(' \\(\\d+\\)$','',os.path.splitext(A)[0])for A in G};L={A.get('sha256')for A in F}|{A.get('sha256')for A in((st or{}).get('meta')or{}).get('received_documents')or()if isinstance(A,dict)}
	try:C=J.datetime.fromisoformat(E).timestamp()if E else None
	except ValueError:C=None
	H=[]
	for A in os.listdir(deal):
		B=os.path.normcase(A)
		if not B.endswith('.docx')or A.startswith('~$')or B in G:continue
		if re.sub(' \\(\\d+\\)$','',os.path.splitext(B)[0])in K or re.search(' - (?:internal|as produced)(?: \\(\\d+\\))?$|לא למשלוח',os.path.splitext(B)[0]):continue
		D=os.path.join(deal,A);I=max(os.path.getmtime(D),os.path.getctime(D))
		if C is not None and I<C or _sha(D)in L:continue
		H.append((I,A))
	return[A for(B,A)in sorted(H,reverse=True)]
def prefix_item(st,compare,a):
	B=compare
	if not st or B is None or paths.prefix_switch_answer(st):return
	A=B.get('received')
	if not A or not os.path.exists(A):return
	try:D=gap_checks.detect_lang('\n'.join(dt.received_paragraphs(A)))
	except Exception:return
	E=load(a.profile,'הפרופיל',required=False)if getattr(a,'profile',None)else None;C=(st.get('entity_details')or{}).get('name_en')or{};F=(E or{}).get('organization_name_en')or(C.get('value')if isinstance(C,dict)else'');return paths.prefix_switch_item(paths.stored_prefix(st),D,F,a.lang or'he')
def sensitive_item(st,a):0
CODE_RX=re.compile('\\s*\\((?:\\s*(?:[ARKNQ]|REG-?|APR-?)\\d+[a-z]?\\s*,?)+\\)|\\b(?:[ARKNQ]\\d{1,3}[a-z]?|REG-\\d+|APR-\\d+)\\b')
def client_text(t,core=None,lang='he'):import content_checks as A;t=CODE_RX.sub('',str(t or''));return A.scrub_client_text(t,core,lang)
def is_deal_only(st):A=(st or{}).get('positions_source');return isinstance(A,dict)and A.get('mode')=='deal_only'
def cmd_questions(a):
	B=load(a.items,'רשימת הפריטים');A=state_of(a.deal);J=set(a.asked_before or())
	if A:
		for C in A.get('question_batches')or():J|=set(C.get('keys')or())
		J-=SB.held_for_explicit(A)
	O=load(a.strategy,'נתוני האסטרטג',required=False)if a.strategy else load(os.path.join(a.deal,'strategy-data.json'),'נתוני האסטרטג',required=False)if a.deal and os.path.exists(os.path.join(a.deal,'strategy-data.json'))else None
	if a.ask_stance:J.discard('stance')
	G=((A or{}).get('meta')or{}).get('paper_type')in('tender_pre_bid','tender_awarded','standard_form_online');P=(A or{}).get('playbook_resolution')or{};G=G or bool(P and P.get('result')not in(None,'match'));G=G or is_deal_only(A)
	if not G and(a.ask_stance or not SB.stance_of(A))and not any(isinstance(A,dict)and A.get('key')=='stance'for A in B):B=[QB.stance_item(a.lang or'he')]+list(B)
	Q=load(a.resolution,'תוצאת האיתור',required=False)or(A or{}).get('playbook_resolution');Y=any(A.get('id')=='playbook_activation'for A in(A or{}).get('user_decisions')or());L=(Q or{}).get('side_check')or{}
	if L.get('conflict')and L.get('question')and not any(A.get('id')=='side_conflict'for A in(A or{}).get('user_decisions')or()):
		if not any(isinstance(A,dict)and A.get('key')=='side_conflict'for A in B):B=[L['question']]+list(B)
	M=QB.activation_item(Q,a.lang or'he',kind_segment=a.kind_segment)
	if M and not Y and not any(isinstance(A,dict)and A.get('key')==M['key']for A in B):B=list(B)+[M]
	D=load(a.compare,'השוואת הסבב',required=False);E=a.status_line
	if((A or{}).get('meta')or{}).get('paper_type')=='tender_awarded':R=PAPER_Q['en'if a.lang=='en'else'he']['only_errors'];E='%s\n%s'%(R,E)if E else R
	H=SB.current_round(A)if A is not None else None;F=None
	if D is not None:
		H=compare_round(A,D);F=copy.deepcopy(A)if A else SB.skeleton()
		if not compare_applied(F,H):SB.apply_compare(F,D,H)
		I={A.get('key')for A in B if isinstance(A,dict)};B=list(B)+[A for A in QB.round_items(D,F,H,a.lang or'he',strategy=O)if A['key']not in I]
		if D.get('base')=='assumed':S=('Assumed base: the comparison is against %s, the last work file; an unmarked change may be our own edit before sending.'if a.lang=='en'else'בסיס משוער: ההשוואה היא מול %s, קובץ העבודה האחרון; שינוי שלא סומן עשוי להיות עריכה שלנו לפני המשלוח.')%os.path.basename(D.get('sent')or'?');E='%s\n%s'%(E,S)if E else S
	N=prefix_item(A,D,a)
	if N and N['key']not in{A.get('key')for A in B if isinstance(A,dict)}:B=list(B)+[N]
	if a.profile:Z=lawyer_view(load(a.profile,'הפרופיל',required=False)or{});I={A.get('key')for A in B if isinstance(A,dict)};B=list(B)+[A for A in QB.comment_name_item(Z,a.lang or'he')if A['key']not in I]
	if getattr(a,'agreement_lang',None)=='en'and a.profile:b=lawyer_view(load(a.profile,'הפרופיל',required=False)or{});I={A.get('key')for A in B if isinstance(A,dict)};B=list(B)+[A for A in QB.english_name_items(b,a.lang or'he')if A['key']not in I]
	T=[A for A in B if isinstance(A,dict)and A.get('kind')=='sent_basis'];B=[A for A in B if A not in T]
	for U in T:print(('  (not asked: %s, the sent file is asked alone before the comparison: round_tools.py basis)'if a.lang=='en'else'  (לא נשאלה: %s, הקובץ שנשלח נשאל לבד לפני ההשוואה: round_tools.py basis)')%(U.get('key')or U.get('text')))
	try:C=QB.build_batch(B,no_consideration=a.no_consideration,asked_before=J,max_questions=a.max,status_line=E,lang=a.lang or'he',strategy=O,round_number=H)
	except ValueError as c:print('המנה לא נבנתה: %s'%c);return 2
	for d in C.get('memos')or():print(d);print('')
	print(C['text'])
	for V in C['skipped']:print(('  (not asked: %s, %s)'if a.lang=='en'else'  (לא נשאלה: %s, %s)')%(V['key'],V['why']))
	W=QB.ready_signal(D)if D is not None else None
	if W:print_signing_preview(F if F is not None else A,a,W)
	X=False
	if A is None and a.deal and os.path.isdir(a.deal):
		A,X=SB.skeleton(),True;A['meta'].update(transaction_id=os.path.basename(os.path.abspath(a.deal)),round_number=1,round_stage=SB.stage_for_round(1),generated_at=SB.now_iso(),last_updated=SB.now_iso())
		if SB.validate_state(A):A=None
	if A is not None:
		K={'round':compare_round(A,D)if D is not None else SB.current_round(A),'asked_at':SB.now_iso(),'keys':[B for A in C['questions']for B in A.get('group_keys')or[A.get('key')or A.get('text')]]}
		if C.get('deferred')or C.get('applied_by_recommendation'):K['deferred']=C.get('deferred')or[];K['applied_by_recommendation']=C.get('applied_by_recommendation')or[]
		if C.get('requires_explicit'):K['requires_explicit']=C['requires_explicit']
		A.setdefault('question_batches',[]).append(K)
		if not save_state(a.deal,A):return 0 if X else 3
	return 0
def print_signing_preview(st,a,ready):
	C=ready;A=(a.lang or'he')=='en';print(('\nThe other side signals it is ready to finalise (comment %s): "%s". Pre-signing checklist, preview:'if A else'\nהצד השני מאותת שהוא מוכן לסיים (בועה %s): "%s". הרשימה לפני חתימה, בתצוגה מקדימה:')%(C.get('root_id'),C.get('text')));D=load(a.profile,'הפרופיל',required=False)if getattr(a,'profile',None)else None;E=SC.build_signing_checklist({},state=st or{},profile=D,lang='en'if A else'he');B=[A for A in E['checks']if A.get('status')=='open']
	for F in SC.render_lines({'checks':B,'passed':not B},'en'if A else'he')[:-1][:12]:print(F)
	print(('  %d items missing before signature (preview; not recorded as passed)'if A else'  חסרים %d פריטים לפני חתימה (תצוגה מקדימה; אינה נרשמת כ"עברה")')%len(B))
def cmd_review(a):
	D=decisions_of(a.decisions);A=state_of(a.deal);J=(A or{}).get('numbering_map')or{};F=load(a.concessions,'הוויתורים',required=False)or(A or{}).get('deliberate_concessions')or[];B=out_lang(a,A);E=A or{};K=(E.get('positions_source')or{}).get('way')=='proposed_playbook'or is_proposed_status(E.get('playbook_status'))or is_proposed_status((E.get('playbook_resolution')or{}).get('playbook_status'));C=RT.build_review_table(D,numbering_map=J,concessions=F,lang=B,proposed=K);L,G=(C,0)if a.full else RT.display_rows(D,C,F);print(RT.render_markdown(L,B))
	if G:print(RT.hidden_line(G,B))
	H=RT.columns(B)[2];M=[dict(A,**{H:re.sub('\\("[^"]*"\\)','("…")',str(A.get(H,'')))})for A in C];I=RT.check_review_table(M,D,B)
	for N in I:print('  הפרה בטבלה: %s'%N)
	if A is not None:
		O=str((A.get('meta')or{}).get('round_number'));A['review_table']=[A for A in A.get('review_table')or[]if isinstance(A,dict)and A.get('round')and str(A['round'])!=O]+C
		if not save_state(a.deal,A):return 3
	return 3 if I else 0
def cmd_talking_points(a):
	F=decisions_of(a.decisions);A=state_of(a.deal);G=load(a.concessions,'הוויתורים',required=False)or(A or{}).get('deliberate_concessions')or[];H=set();I=[{'id':A.get('clause_id'),'topic':A.get('contract_ref')or A.get('clause_id'),'escalation':A.get('escalation')}for A in(A or{}).get('clauses')or()if A.get('status')=='STUCK'and A.get('escalation')and A.get('clause_id')not in{A.get('id')for A in F}];J=TP.build_talking_points(list(F)+I,G,lang=out_lang(a,A),reviewed=H);C=SB.current_round(A)if A is not None else None;D=TP.merge_points((A or{}).get('talking_points')or[],J,clauses=(A or{}).get('clauses'),round_number=C,lang=out_lang(a,A));E=[A for A in D if not(isinstance(A,dict)and A.get('status')=='superseded')]
	for B in D:
		if isinstance(B,dict)and(B.get('superseded')or{}).get('round')==C and C:print('  עודכנה לפי מצב הסעיף: %s (%s)'%(B.get('topic')or B.get('id'),B['superseded'].get('why')))
	if len(E)>MAX_TALKING_POINTS:print('  %d נקודות; בסיכום מוצגות שבע הראשונות'%len(E))
	for(K,B)in enumerate(E[:MAX_TALKING_POINTS],1):print('%d. %s'%(K,B.get('text')or'%s: %s'%(B.get('topic',''),B.get('our_goal',''))))
	if A is not None:
		A['talking_points']=D
		if not save_state(a.deal,A):return 3
	return 0
def cmd_signing(a):
	if a.preview:A=state_of(a.deal);print_signing_preview(A,a,{'root_id':'-','text':a.preview if isinstance(a.preview,str)else''});return 0
	F=load(a.gate,'דוח השער');A=state_of(a.deal)
	try:C=SC.parse_manual(a.fail);G={A['check']for A in SC.parse_manual('%s='%A for A in a.pass_ or())}
	except ValueError as H:print(H);return 2
	for B in((A or{}).get('signing_checklist')or{}).get('checks')or():
		if isinstance(B,dict)and B.get('item')=='manual_check'and B.get('status')=='open'and B.get('check')not in G and B.get('check')not in{A['check']for A in C}:C.append({'check':B.get('check'),'detail':B.get('detail')or''});print('נשארת פתוחה מהרצה קודמת: %s (משחרר: --pass %s)'%(B.get('check'),B.get('check')))
	D=SC.build_signing_checklist(F.get('info')or{},state=A,profile=load(a.profile,'הפרופיל',required=False),decisions=decisions_of(a.decisions)if a.decisions else None,lang=out_lang(a,A),manual=C)
	for I in SC.render_lines(D,out_lang(a,A)):print(I)
	if A is not None:
		E=A.get('signing_checklist')or{};E.update(D);A['signing_checklist']=E
		if not save_state(a.deal,A):return 3
	return 0 if D['passed']else 3
def cmd_proportionality(a):
	D=decisions_of(a.decisions);C=out_lang(a,None);A=P.assess(D,a.fight_list,value_band=a.value_band,value_text=a.value_text,user_choice=a.user_choice,answer_kind=a.answer_kind,lang=C);print(A['summary_line'])
	if A['question_required']:B=C=='en';print(('%s: more requests (%d) than the fight list (%d).'if B else'%s: יותר בקשות (%d) מרשימת המאבק (%d).')%(QB.label_for(4,lang=C),A['counts']['asks'],a.fight_list));print(('  Proposed concessions: %s'if B else'  ויתורים מוצעים: %s')%', '.join(A['proposed_concessions']or['none'if B else'אין']));print(('  Options: %s'if B else'  אפשרויות: %s')%' | '.join(A.get('options')or()))
	for E in A['violations']:print('  הפרה: %s'%E)
	return 3 if A['question_required']or A['violations']else 0
CLEAN_PARTS=re.compile('^word/(document|header\\d*|footer\\d*|footnotes|endnotes)\\.xml$')
COMMENT_PARTS=re.compile('^word/comments(Extended|Ids|Extensible)?\\.xml$')
def _merge_deleted_marks(root):
	B=dt.body_paragraphs(root)
	for(C,A)in enumerate(B):
		D=A.find(dt.W+'pPr/'+dt.W+'rPr')
		if D is None or D.find(dt.W+'del')is None:continue
		if C+1>=len(B):continue
		E=B[C+1];F=1 if E.find(dt.W+'pPr')is not None else 0
		for G in[A for A in A if A.tag!=dt.W+'pPr']:E.insert(F,G);F+=1
		A.getparent().remove(A)
def _clean_part(root):
	C=root
	if C.find(dt.W+'body')is not None:_merge_deleted_marks(C)
	for A in list(C.iter()):
		if not isinstance(A.tag,str):continue
		D=dt.local(A.tag);B=A.getparent()
		if B is None:continue
		if D in('del','moveFrom')and dt.local(B.tag)!='rPr':B.remove(A)
		elif D.endswith('PrChange')or D in('commentRangeStart','commentRangeEnd','moveFromRangeStart','moveFromRangeEnd','moveToRangeStart','moveToRangeEnd'):B.remove(A)
		elif D in('del','ins','moveTo')and dt.local(B.tag)=='rPr':B.remove(A)
	for A in list(C.iter(dt.W+'ins',dt.W+'moveTo')):
		B=A.getparent()
		if B is None:continue
		F=B.index(A)
		for G in list(A):B.insert(F,G);F+=1
		B.remove(A)
	for H in list(C.iter(dt.W+'commentReference')):
		E=H.getparent()
		if E is not None and E.getparent()is not None:E.getparent().remove(E)
	return C
def cmd_clean_copy(a):
	E=state_of(a.deal)
	if E is None:print('אין קובץ מצב בתיקיית העסקה, ולכן אין רשימה לפני חתימה שעברה');return 2
	if not(E.get('signing_checklist')or{}).get('passed'):print('הרשימה לפני חתימה לא עברה (round_tools.py signing). העותק לחתימה אינו מופק.');return 3
	if not os.path.exists(a.agreed):print('הנוסח המוסכם אינו קיים: %s'%a.agreed);return 2
	try:D=guard_out(a.out,inputs=[a.agreed])
	except OutputRefused as L:print('סירוב: %s'%L);return 1
	B=dt.read_package(dt.strip_internal(a.agreed));M={A for A in B if COMMENT_PARTS.match(A)}
	for A in list(B):
		if A in M:del B[A]
		elif CLEAN_PARTS.match(A):F=etree.fromstring(B[A]);B[A]=etree.tostring(_clean_part(F),xml_declaration=True,encoding='UTF-8',standalone=True)
		elif A=='word/settings.xml':
			F=etree.fromstring(B[A])
			for H in list(F.iter(dt.W+'trackRevisions')):H.getparent().remove(H)
			B[A]=etree.tostring(F,xml_declaration=True,encoding='UTF-8',standalone=True)
		elif A=='word/_rels/document.xml.rels':C=B[A].decode('utf-8');C=re.sub('<Relationship [^>]*Target="comments[^"]*"[^>]*/>','',C);B[A]=C.encode('utf-8')
		elif A=='[Content_Types].xml':C=B[A].decode('utf-8');C=re.sub('<Override [^>]*PartName="/word/comments[^"]*"[^>]*/>','',C);B[A]=C.encode('utf-8')
	with open(D,'wb')as G:G.write(dt.write_package(B))
	I=dt.read_package(D);J=any(re.search('<w:(ins|del|moveFrom|moveTo)\\b',I[A].decode('utf-8','ignore'))for A in I if CLEAN_PARTS.match(A))
	if dt.accept_all(a.agreed)!=dt.received_paragraphs(D)or J:os.remove(D);print('העותק הנקי אינו זהה לנוסח המוסכם%s, ולא נשמר.'%(' (נשאר בו סימון)'if J else''));return 3
	with open(a.agreed,'rb')as G:N=hashlib.sha256(G.read()).hexdigest()
	print('העותק לחתימה: %s'%D);K=E.setdefault('signing_checklist',{});K['agreed_version_sha256']=N;K['clean_copy_path']=D
	if not save_state(a.deal,E):return 3
	return 0
def cmd_round_rules(a):
	H=state_of(a.deal);A=a.round or int(((H or{}).get('meta')or{}).get('round_number')or 1);D=a.lang or'he';B=QB.round_row(A,D);C=D=='en';print(('Round %d (%s)'if C else'סבב %d (%s)')%(A,B['stage']))
	for(I,J,K)in(('goal','מטרה','Goal'),('retreat','נסיגה מותרת','Allowed retreat'),('tone','טון','Tone'),('on_acceptance','מה עונים על קבלה','On acceptance')):print('  %s: %s'%(K if C else J,B[I]))
	print(('  Comment length: up to %d sentences, %d words'if C else'  אורך בועה: עד %d משפטים, %d מילים')%(B['max_sentences'],B['max_words']))
	if not a.decisions:return 0
	E=a.compare or(os.path.join(a.deal,'round-compare-%d.json'%A)if a.deal else None);L=(load(E,'השוואת הסבב',required=False)or{}).get('threads')if E and os.path.exists(E)else None;F=QB.round_violations(load(a.decisions,'קובץ ההכרעות'),A,state=H,lang=D,threads=L)
	for G in F:print('  [%s] %s: %s'%(G['code'],G['id'],G['message']))
	if not F:print('  קובץ ההכרעות עומד במטריצת הסבב.'if not C else'  The decisions file meets the round matrix.')
	return 3 if F else 0
CARRY_DROP='old','new','new_text','text','external_comment','internal_comment','reply_to_comment','their_changes','after_para','template_para','number','mandatory','kind','cluster_id','silent_change','dependents','dependents_found','same_topic','structural','conforming','conforms_to','their_rejected','status','escalation_basis','coverage'
OPEN_KINDS='their_silent','their_tracked','their_rejected_our_insert','our_rejected','our_accepted_partial','our_open'
def _n(s):return re.sub('\\s+',' ',re.sub('[\u200e\u200f\u202a-\u202e]','',s or'')).strip()
def align_paragraphs(base,recv,compare=None):
	O=compare;import difflib as J;E=[_n(A)for A in base];D=[_n(A)for A in recv];B,F={},{}
	for H in(O or{}).get('clauses')or():
		A=H.get('received_para')
		if not isinstance(A,int):continue
		if isinstance(H.get('base_para'),int):B.setdefault(A,H['base_para'])
		elif isinstance(H.get('after_base_para'),int):F.setdefault(A,H['after_base_para'])
	for P in(O or{}).get('para_map')or():
		A,K=P.get('received_para'),P.get('base_para')
		if isinstance(A,int)and isinstance(K,int)and A<len(D)and K<len(E)and D[A]and A not in F:B.setdefault(A,K)
	U=J.SequenceMatcher(a=E,b=D,autojunk=False)
	for(Q,L,R,M,V)in U.get_opcodes():
		if Q=='equal':
			for C in range(R-L):
				if M+C not in F:B.setdefault(M+C,L+C)
		elif Q=='replace':
			S=set(B.values())
			for G in range(M,V):
				if G in B or G in F or not D[G]:continue
				T=[A for A in range(L,R)if A not in S and E[A]]
				if not T:continue
				N=max(T,key=lambda ii:J.SequenceMatcher(a=E[ii],b=D[G]).ratio())
				if J.SequenceMatcher(a=E[N],b=D[G]).ratio()>.6:B[G]=N;S.add(N)
	for A in range(len(D)):
		if not D[A]and A not in F:
			C=A-1
			while C>=0 and C not in B:C-=1
			I=B[C]+(A-C)if C>=0 else A
			if 0<=I<len(E)and not E[I]and I not in B.values():B[A]=I
	return B,F
def carry_decisions(prev_decs,base,recv,compare=None,existing=(),prev_round=1):
	J=existing;I=prev_decs;F=compare;E=recv;D=prev_round;from orchestrator.state_builder import their_requests as T;K,L=align_paragraphs(base,E,F);M={}
	for B in I:
		if isinstance(B.get('para'),int):M.setdefault(B['para'],[]).append(B)
	N={}
	for B in I:
		if B.get('op')=='insert_paragraph'and isinstance(B.get('after_para'),int):N.setdefault(B['after_para'],[]).append(B)
	U={A.get('para')for A in J if isinstance(A.get('para'),int)};O={A.get('id')for A in J};P={A.get('received_para')for A in(F or{}).get('clauses')or()if A.get('classification')in OPEN_KINDS};P|=set(T((F or{}).get('threads')));Q,G=[],[]
	for C in range(len(E)):
		if C in U:continue
		if C in P:G.append((C,'השתנתה בסבב, או שיש עליה בקשה חדשה של הצד השני'));continue
		A=None
		if C in L:V=N.get(L[C])or[];A=max(V,key=lambda d:_ratio(d.get('text'),E[C]),default=None)
		elif C in K:H=M.get(K[C])or[];A=next((A for A in H if A.get('op')!='accept'),None)or(H[0]if H else None)
		if A is None or A.get('id')in O:
			if not _n(E[C]):A={'id':'K%d-%d'%(D+1,C),'op':'accept','decision_code':'A1','reason':'פסקה ריקה','rule_ids':[]}
			else:G.append((C,'אין לה הכרעה מקבילה בסבב הקודם'if A is None else'ההכרעה %s כבר הוחלה על פסקה אחרת בסבב'%A.get('id')));continue
		O.add(A['id']);B={A:copy.deepcopy(B)for(A,B)in A.items()if A not in CARRY_DROP};R=A.get('op')not in(None,'accept')
		if R:B['their_track']='green'
		S=A.get('summary')or A.get('reason')or'';B.update(op='accept',para=C,decision_code='A1',carried_from={'round':D,'id':A['id'],'para':A.get('para',A.get('after_para')),'op':A.get('op')},reason=('ההצעה שלנו מסבב %d התקבלה, ולא השתנתה בסבב הזה'if R else'לא השתנה בסבב הזה; נשאר כפי שהוכרע בסבב %d')%D,summary='ללא שינוי מסבב %d: '%D+S if S else'ללא שינוי מסבב %d'%D);Q.append(B)
	return Q,G
def _ratio(a,b):import difflib as A;return A.SequenceMatcher(a=_n(a),b=_n(b)).ratio()
def cmd_carry(a):
	P=state_of(a.deal)
	if not(a.compare or a.round):print('חסר --compare (round-compare-<N>.json), או --round');return 2
	C=load(a.compare or os.path.join(a.deal,'round-compare-%d.json'%a.round),'השוואת הסבב');A=a.round or compare_round(P,C);Q=a.prev_decisions or os.path.join(a.deal,'decisions_round_%d.json'%(A-1));E=load(Q,'קובץ ההכרעות של הסבב הקודם');V=E.get('decisions',[])if isinstance(E,dict)else E;H=a.received or(C or{}).get('received');B=a.prev_received
	if not B:I=next((B for B in((P or{}).get('meta')or{}).get('received_documents')or()if isinstance(B,dict)and str(B.get('round'))==str(A-1)),None);B=I and(I['file_name']if os.path.isabs(I['file_name'])else os.path.join(a.deal,I['file_name']))
	L=None
	if not a.prev_received and(not B or not os.path.exists(B)):
		D=(C or{}).get('sent')
		if D and os.path.exists(D):import compare_rounds as R;S=(C or{}).get('authors')or[(C or{}).get('author')];L=R.base_paragraphs(dt.body_paragraphs(dt.document_root(D)),S,R.prior_keys(D,S,a.deal,A-1))[1];print(('The round %d draft is not in the folder (%s): aligning against the file sent in round %d, %s, as the other side saw it'if a.lang=='en'else'הטיוטה של סבב %d אינה בתיקייה (%s): היישור מול הקובץ שנשלח בסבב %d, %s, כפי שהצד השני ראה אותו')%(A-1,B,A-1,os.path.basename(D)));B=D
	for(M,W)in((H,'הטיוטה שחזרה (--received)'),(B,'הטיוטה של הסבב הקודם (--prev-received)')):
		if not M or not os.path.exists(M):print('חסר %s: %s'%(W,M));return 2
	N=a.decisions or os.path.join(a.deal,'decisions_round_%d.json'%A);F=load(N,'קובץ ההכרעות של הסבב')if os.path.exists(N)else None;T=(F.get('decisions',[])if isinstance(F,dict)else F)or[];J,K=carry_decisions(V,L if L is not None else dt.received_paragraphs(B),dt.received_paragraphs(H),C,T,prev_round=A-1);G=dict(F)if isinstance(F,dict)else{A:E.get(A)for A in('transaction_id','lang','author','initials')if isinstance(E,dict)};G['round']=A;G.setdefault('received_sha256',_sha(H));G['decisions']=sorted(list(T)+J,key=lambda d:d.get('para')if isinstance(d.get('para'),int)else d.get('after_para',10**6)+.5);O=dt.validate_decisions(dict(G,decisions=J))if J else[]
	if O:
		print('ההכרעות שהועברו אינן עומדות בחוזה (%d):'%len(O))
		for X in O[:10]:print('  - %s'%X)
		return 2
	print(('Carried from round %d: %d decisions. Left to decide in this round: %d paragraphs'if a.lang=='en'else'הועברו מסבב %d: %d הכרעות. נשארו להכרעה בסבב הזה: %d פסקאות')%(A-1,len(J),len(K)))
	for(Y,Z)in K:print('  פסקה %d: %s'%(Y,Z))
	if a.dry_run:return 3 if K else 0
	try:U=guard_out(a.out or N,inputs=[H,B,Q,a.compare or''])
	except OutputRefused as b:print('סירוב: %s'%b);return 1
	with open(U,'w',encoding='utf-8')as c:json.dump(G,c,ensure_ascii=False,indent=1)
	print('נכתב %s'%U);return 3 if K else 0
PAPER_TYPES='negotiable','tender_pre_bid','tender_awarded','standard_form_online'
PAPER_Q={'he':{'text':'לפי הנוסח, זה נראה כמו %s. נכון? (%s)','names':{'negotiable':'הסכם רגיל למשא ומתן','tender_pre_bid':'הליך תחרותי לפני הגשת הצעות','tender_awarded':'חוזה של הליך תחרותי שכבר זכיתם בו','standard_form_online':'תנאים מקוונים אחידים'},'opts':['כן, %s','לא, הסכם רגיל למשא ומתן'],'opts_other':'לא, זה הליך תחרותי או תנאים מקוונים','unsure':'הזיהוי אינו ודאי, ולכן אין המלצה: אתם קובעים.','owner_q':'לפי הקובץ, זה נראה כמו %s. של מי הנייר?','owners':{'ours':'הנוסח שלנו, שחזר עם הערות','theirs':'נוסח שהצד השני ניסח','template':'תבנית של גורם שלישי'},'award':'האם מסמכי ההליך התחרותי מתירים הערות או סטיות אחרי הזכייה, ובאיזה היקף?','rec':'אין שינויים מהותיים, רק הבהרות ותיקון טעויות','dev_yes':'מותרות גם סטיות, ואפרט איזה','only_errors':'זה חוזה של הליך תחרותי שזכיתם בו, ולכן רק תיקון טעויות. אחרי הזכייה אסור לשנות את התנאים שעליהם התחרו כל המציעים: המחיר, השטח, התקופה והאופציות נשארים כמו בהליך תחרותי, ושינוי בהם עלול לבטל את הזכייה. מה שכן מתקנים: טעות ברורה בשם, במספר, בתאריך או בהפניה. את הסיכונים שנשארים מנהלים, ולא מתקנים בנוסח.'},'en':{'text':'From the wording, this looks like %s. Correct? (%s)','names':{'negotiable':'an ordinary negotiable agreement','tender_pre_bid':'a competitive procedure before bids are submitted','tender_awarded':'the contract of a competitive procedure you have won','standard_form_online':'standard online terms'},'opts':['Yes, %s','No, an ordinary negotiable agreement'],'opts_other':'No, it is a competitive procedure or online terms','unsure':'The identification is not certain, so there is no recommendation: you decide.','owner_q':'From the file, this looks like %s. Whose paper is it?','owners':{'ours':'Our wording, returned with comments','theirs':'Wording drafted by the other side','template':"A third party's template"},'award':'Do the procedure documents allow comments or deviations after award, and to what extent?','rec':'No material changes, only clarifications and corrections of errors','dev_yes':'Deviations are also allowed, and I will say which','only_errors':'This is the contract of a competitive procedure you won, so we only correct errors. After the award, the terms all bidders competed on cannot change: the price, area, term and options stay as in the procedure, and changing them could cancel the award. What we do correct: a clear error in a name, number, date or cross-reference. The risks that remain are managed, not changed in the wording.'}}
def cmd_paper_type(a):
	from orchestrator import resolve_playbook as O;C=state_of(a.deal)if a.deal else None;J='en'if a.lang=='en'else'he'
	if a.set:
		if a.set not in PAPER_TYPES:print('סוג נייר לא מוכר: %s (%s)'%(a.set,', '.join(PAPER_TYPES)));return 2
		if C is None:
			if not a.deal or not os.path.isdir(a.deal):print('חסרה תיקיית העסקה (--deal)');return 2
			C=SB.skeleton();C['meta'].update(transaction_id=os.path.basename(os.path.abspath(a.deal)),round_number=1,round_stage=SB.stage_for_round(1),generated_at=SB.now_iso(),last_updated=SB.now_iso())
		D=C.setdefault('meta',{});D['paper_type']=a.set;D['paper_type_basis']={'answer_kind':a.answer_kind or'explicit','recorded_at':SB.now_iso(),'suggested':a.suggested or None};print('סוג הנייר נרשם: %s'%a.set);return 0 if save_state(a.deal,C)else 3
	if not a.draft or not os.path.exists(a.draft):print('חסרה הטיוטה (--draft)');return 2
	P=dt.received_paragraphs(a.draft);B=O.detect_paper_type(P);Q=list(((C or{}).get('meta')or{}).get('deal_context',{}).get('facts')or[])
	if a.facts:L=load(a.facts,'העובדות');Q+=L if isinstance(L,list)else L.get('facts')or[]
	B['facts_mismatch']=O.facts_mismatch(Q,P);A=PAPER_Q[J];E=A['names'][B['suggested']];R=', '.join(C for A in('award','tender','online')for C in B['signals'][A][:2]);F=A['text']%(E,R)
	if not R:F=F.replace(' ()','')
	G=bool(B.get('confident'))
	if not G:F=A['unsure']+' '+F
	S={'key':'paper_type','kind':'paper_type','situation':4,'blocks_sending':True,'text':F,'confident':G,'recommendation':A['opts'][0]%E if G and B.get('recommended')==B['suggested']else None,'options':[A['opts'][0]%E,A['opts'][1]]}
	if B['suggested']=='negotiable':S.update(options=[A['opts'][0]%E,A['opts_other']],recommendation=A['opts'][0]%E if G else None)
	H=[]if B['suggested']=='negotiable'and G else[S]
	try:import content_checks as T;from lawyer import lawyer_view as U;I=U(load(a.profile,'הפרופיל'))if getattr(a,'profile',None)else{};V=[I.get('organization_name'),I.get('organization_name_en')];W=[I.get('lawyer_name'),I.get('lawyer_name_en')]+list(I.get('lawyer_aliases')or[]);D=(C or{}).get('meta')or{};X=[D.get('counterparty'),(D.get('deal_context')or{}).get('counterparty')];Y=[A.get('sha256')for A in D.get('sent_documents')or()if isinstance(A,dict)];B['paper_owner']=T.paper_owner(a.draft,[A for A in V if A],[A for A in X if A],[A for A in W if A],[A for A in Y if A])
	except Exception as M:B['paper_owner']={'owner':None,'confident':False,'signals':[],'error':str(M)}
	N=B['paper_owner']
	if N.get('owner')and not N.get('confident'):H.append({'key':'paper_owner','kind':'paper_owner','situation':4,'blocks_sending':False,'text':A['owner_q']%A['owners'][N['owner']],'recommendation':None,'options':[A['owners']['ours'],A['owners']['theirs'],A['owners']['template']]})
	if B['suggested']=='tender_awarded':H.append({'key':'tender_deviation','kind':'paper_type','situation':4,'blocks_sending':True,'text':A['award'],'recommendation':A['rec'],'options':[A['rec'],A['dev_yes']]})
	for K in B['facts_mismatch']:H.append({'key':'fact_mismatch:%s:%s'%(K['unit'],K['fact_value']),'kind':'fact_mismatch','situation':4,'blocks_sending':True,'text':('מה שמסרתם (%s) שונה מהנוסח (%s). איזה נכון לעסקה הזו?'if J=='he'else'What you told us (%s) differs from the wording (%s). Which is right for this deal?')%(K['fact'],', '.join('%g'%A for A in K['draft_values'])),'options':['הנוסח'if J=='he'else'The wording','מה שמסרתי'if J=='he'else'What I said']})
	B['question_items']=H;print(json.dumps(B,ensure_ascii=False,indent=1))
	if a.items_out:
		try:Z=guard_out(a.items_out,inputs=[a.draft])
		except OutputRefused as M:print('סירוב: %s'%M);return 1
		with open(Z,'w',encoding='utf-8')as b:json.dump(H,b,ensure_ascii=False,indent=1)
	return 0
def cmd_accept_rest(a):
	if not os.path.exists(a.received):print('הטיוטה אינה קיימת: %s'%a.received);return 2
	A=load(a.decisions,'קובץ ההכרעות')if os.path.exists(a.decisions)else{};A=A if isinstance(A,dict)else{'decisions':A};C=A.get('decisions')or[];I={A.get('para')for A in C if isinstance(A.get('para'),int)};J={A.get('id')for A in C};K=dt.received_paragraphs(a.received);B=[]
	for(D,L)in enumerate(K):
		if D in I:continue
		E='K%d'%D
		while E in J:E+='k'
		F=not(L or'').strip();B.append({'id':E,'op':'accept','para':D,'decision_code':'A1','structural':F,'reason':('פסקה ריקה'if F else'לא שונתה: הנוסח שלהם מקובל כמו שהוא')if a.lang!='en'else'Empty paragraph'if F else'Unchanged: their wording is accepted as is'})
	A.setdefault('round',a.round or A.get('round')or 1);A.setdefault('received_sha256',_sha(a.received));A['decisions']=sorted(list(C)+B,key=lambda d:d.get('para')if isinstance(d.get('para'),int)else d.get('after_para',10**6)+.5);G=dt.validate_decisions(dict(A,decisions=B))if B else[]
	if G:
		print('ההכרעות שנוספו אינן עומדות בחוזה (%d):'%len(G))
		for M in G[:10]:print('  - %s'%M)
		return 2
	print(('Accepted as is: %d paragraphs with no decision (%d of them empty). Existing decisions: %d'if a.lang=='en'else'התקבלו כמו שהן: %d פסקאות בלי הכרעה (מהן %d ריקות). הכרעות קיימות: %d')%(len(B),sum(1 for A in B if A['structural']),len(C)))
	if a.dry_run:return 0
	try:H=guard_out(a.out or a.decisions,inputs=[a.received])
	except OutputRefused as N:print('סירוב: %s'%N);return 1
	with open(H,'w',encoding='utf-8')as O:json.dump(A,O,ensure_ascii=False,indent=1)
	print('נכתב %s'%H);return 0
def cmd_resolve_threads(a):
	D=load(a.compare,'השוואת הסבב');G={}
	for E in D.get('clauses')or():
		if E.get('received_para')is not None:G.setdefault(E['received_para'],set()).add(E['classification'])
	H=re.compile('^\\s*(?:agreed|accepted|noted|thank you|thanks|מוסכם|מקובל|תודה)[.!]?\\s*$',re.I);B=[]
	for A in D.get('threads')or():
		if not A.get('root_ours')or A.get('done'):continue
		C=G.get(A.get('para'),set());K=[A for A in A.get('entries')or()if A.get('new')and not A.get('ours')]
		if C and C<={'our_accepted'}:B.append(A['root_id'])
		elif not C and all(H.match(A.get('text')or'')for A in K)and not(A.get('last_is_theirs')and not H.match((A.get('entries')or[{}])[-1].get('text')or'')):B.append(A['root_id'])
	I=stale_proposals(D,decisions_of(a.decisions)if a.decisions else[],B)
	for(L,M)in I['missing']:print(('  Comment %s: decision %s changes our position in this thread, and its reply does not say "%s"'if a.lang=='en'else'  בועה %s: ההכרעה %s משנה את העמדה שלנו בשרשור, והתשובה אינה אומרת "%s"')%(L,M,QB.REPLACES['en']))
	print(('%d threads to mark done: %s'if a.lang=='en'else'שרשורים לסימון "בוצע": %d: %s')%(len(B),', '.join(B)or'-'));J=3 if I['missing']else 0
	if a.dry_run or not B:return J
	try:F=guard_out(a.out,inputs=[D.get('received')or'',D.get('sent')or''],allow_existing_doc=os.path.abspath(a.out)==os.path.abspath(a.docx))
	except OutputRefused as N:print('סירוב: %s'%N);return 1
	O=TH.mark_done(a.docx,B,out_path=F);print('סומנו %d בועות ב-%s'%(len(O),F));from orchestrator import pre_send as P;C=P.refresh_run_record(F)
	if C:print('רשומת ההפקה של הריצה עודכנה (%s)'%', '.join(C))
	return J
def stale_proposals(compare,decisions,roots):
	C=roots;B={'missing':[]};D=[A for A in decisions or()if isinstance(A,dict)and A.get('op')in QB.CHANGE_OPS]
	if not D:return B
	for A in(compare or{}).get('threads')or():
		if not A.get('root_ours')or A.get('done')or A.get('root_id')in C:continue
		if not any(A.get('ours')and not A.get('new')for A in A.get('entries')or()):continue
		E=[B for B in D if B.get('para')==A.get('para')]
		if not E:continue
		F=[B for B in E if B.get('reply_to_comment')and QB.thread_of([A],B['reply_to_comment'])]
		if F:B['missing']+=[(A['root_id'],B.get('id'))for B in F if not re.search(QB.REPLACES_RE,B.get('external_comment')or'',re.I)];continue
		G=SB.their_requests([dict(A,para=A.get('para')if isinstance(A.get('para'),int)else-1)])
		if not G:C.append(A['root_id'])
	return B
def cmd_summary_head(a):
	A=state_of(a.deal)
	if A is None:print('אין קובץ מצב בתיקיית העסקה');return 2
	F=out_lang(a,A);D=F=='en';E=a.round or int((A.get('meta')or{}).get('round_number')or 1);C=[]
	try:
		import content_checks as K;P=A.get('decisions_file')or'decisions_round_%d.json'%E;L=os.path.join(a.deal,P);G=load(L,'קובץ ההכרעות',required=False)if os.path.exists(L)else None;M=G.get('decisions',[])if isinstance(G,dict)else G or[];H=(A.get('meta')or{}).get('para_count')
		if not isinstance(H,int)and A.get('coverage_index'):H=len([A for A in A['coverage_index']if isinstance(A,dict)and A.get('element_type')!='missing_topic'])
		if M:C.append(K.counts_line(K.unit_counts(M,H,(A.get('meta')or{}).get('playbook_map')),F))
	except Exception:pass
	if SB.stage_for_round(E)=='closing':
		for I in SB.critical_open_clauses(A):C.append(('Critical and still open: %s (%s). Recommendation: %s'if D else'פריט קריטי פתוח: %s (%s). ההמלצה: %s')%(I['ref'],I['status'],I['recommendation']or('decide before signature'if D else'להכריע לפני החתימה')))
	N=[A for A in A.get('open_items')or()if isinstance(A,dict)]
	for B in N:
		if B.get('blocks_sending')and B.get('status')not in SB.OPEN_ITEM_DONE:C.append(('Needed before sending: %s'if D else'נדרש לפני שליחה: %s')%client_text(B.get('item')))
	for B in N:
		if int((B.get('closed')or{}).get('round')or 0)==E:C.append(('Closed: %s (%s)'if D else'נסגר: %s (%s)')%(client_text(B.get('item')),client_text(B['closed'].get('why'))))
		elif int((B.get('updated')or{}).get('round')or 0)==E:C.append(('Updated: %s (%s)'if D else'עודכן: %s (%s)')%(client_text(B.get('item')),client_text(B['updated'].get('why'))))
	for B in SB.open_items_to_recheck(A,E):C.append(('Still open? %s. The clause changed in this response.'if D else'עדיין פתוח? %s. הסעיף השתנה בתגובה הזו.')%client_text(B.get('item')))
	if is_deal_only(A):
		Q=((A.get('positions_source')or{}).get('deal_only')or{}).get('build_offer_said')
		if not Q:C.append('A reusable playbook can be built from this review. Build one?'if D else'אפשר לבנות מהביקורת הזו פלייבוק לשימוש חוזר בעסקאות מהסוג הזה. לבנות?')
	else:
		J=SB.playbook_update_line(A,E,F)
		if J:C.append(J)
		O=SB.areo_clauses_line(A,E,F,with_trigger=not J)
		if O:C.append(O)
	for R in C:print(R)
	if not C:print('No lines for the head of the summary.'if D else'אין שורות לראש הסיכום.')
	return 0
def main(argv=None):sys.dont_write_bytecode=True;O=argparse.ArgumentParser(description=__doc__.split('\n')[0]);B=O.add_subparsers(dest='cmd',required=True);A=B.add_parser('questions',help='מנת השאלות');A.add_argument('--items',required=True,help='JSON: [{key, text, situation (1-9 או null), recommendation, options, blocks_sending, kind}]');A.add_argument('--deal',help='תיקיית העסקה: שאלות שכבר נשאלו אינן נשאלות שוב');A.add_argument('--asked-before',action='append');A.add_argument('--no-consideration',action='store_true',help='הסכם בלי תמורה: בלי שאלת שווי');A.add_argument('--max',type=int,default=8);A.add_argument('--status-line',help='שורת המעמד שבראש המנה');A.add_argument('--lang',choices=('he','en'),help='שפת הממשק (display_language); ברירת מחדל: עברית');A.add_argument('--resolution',help='הפלט של resolve_playbook.py; בלעדיו playbook_resolution שבקובץ המצב');A.add_argument('--compare',help='הפלט של compare_rounds.py: שינויים שקטים, סעיף מוסכם שנפתח, מונח בלי הגדרה, STUCK (לפי stuck_reason)');A.add_argument('--kind-segment',help='הסגמנט בפלייבוק לסוג הצד שכנגד: מחילים את הווריאנט שלו, ואין שאלת החלה');A.add_argument('--profile',help='פרופיל-לקוח.json: organization_name_en, לשאלה אם להחליף את תחילת שם הקובץ');A.add_argument('--agreement-lang',choices=('he','en'),help='שפת ההסכם. en עם --profile: כשבפרופיל אין שם באנגלית לעורך הדין (lawyer_name_en) או לחברה (organization_name_en), השאלה נכנסת למנה מראש, ולא באמצע ההפקה');A.add_argument('--ask-stance',action='store_true',help='לשאול שוב את שאלת הגישה: המשתמש ביקש לשנות, או סבב חדש שבו המצב השתנה');A.add_argument('--strategy',help='strategy-data.json של האסטרטג; בלעדיו: strategy-data.json בתיקיית העסקה, כשקיים');A.add_argument('--received',help='הטיוטה שהתקבלה (docx): נושאים רגישים (דין ופורום, חידוש אוטומטי, מס, אחריות בלי תקרה, מידע רגיש, דין מגזרי זר) נשאלים כבר במנה, בשאלה אחת לכולם. בלעדיו: הקובץ האחרון ב-received_documents שבקובץ המצב');D=B.add_parser('paper-type',help='סוג הנייר (הליך תחרותי, תנאים מקוונים, משא ומתן): הצעה מהנוסח, בדיקת העובדות מול הנוסח, שאלה למנה, ורישום ב-meta.paper_type עם --set');D.add_argument('--draft',help='הטיוטה שהתקבלה (docx)');D.add_argument('--deal',help='תיקיית העסקה: העובדות מ-meta.deal_context.facts, והרישום ב---set');D.add_argument('--facts',help='JSON: עובדות שהמשתמש מסר, כשאינן עדיין בקובץ המצב');D.add_argument('--items-out',help='פריטי השאלה למנה (JSON), להוספה ל---items של questions');D.add_argument('--set',help='לרשום את סוג הנייר אחרי תשובת המשתמש: '+' / '.join(PAPER_TYPES));D.add_argument('--answer-kind',choices=('explicit','delegated'));D.add_argument('--suggested',help='ההצעה של הכלי, לרישום לצד התשובה');D.add_argument('--profile',help='פרופיל-לקוח.json: השמות שלנו, לסיווג "נייר של מי" (paper_owner) מסימני הקובץ');D.add_argument('--lang',choices=('he','en'));G=B.add_parser('accept-rest',help='כל פסקה בלי הכרעה מקבלת accept בצעד אחד (מפתח כיסוי מלא, גם בסבב 1)');G.add_argument('--decisions',required=True,help='decisions_round_<N>.json: קובץ ההכרעות שנכתב עד עכשיו');G.add_argument('--received',required=True,help='הטיוטה שהתקבלה (docx)');G.add_argument('--round',type=int);G.add_argument('--out',help='ברירת מחדל: אותו קובץ הכרעות');G.add_argument('--lang',choices=('he','en'));G.add_argument('--dry-run',action='store_true');H=B.add_parser('review',help='טבלת "לאישורך"');H.add_argument('--decisions',required=True);H.add_argument('--deal');H.add_argument('--concessions');H.add_argument('--lang',choices=('he','en'),help='שפת התוצר; בלעדיו: הפרופיל, ואחריו meta.lang בקובץ המצב');H.add_argument('--profile',help='פרופיל-לקוח.json: deliverable_language (both: שפת הממשק)');H.add_argument('--full',action='store_true',help='להציג את כל ההכרעות, גם קבלות שאינן מהותיות');J=B.add_parser('talking-points',help='נקודות לשיחה');J.add_argument('--decisions',required=True);J.add_argument('--deal');J.add_argument('--concessions');J.add_argument('--lang',choices=('he','en'),help='שפת התוצר; בלעדיו: הפרופיל, ואחריו meta.lang בקובץ המצב');J.add_argument('--profile',help='פרופיל-לקוח.json: deliverable_language (both: שפת הממשק)');E=B.add_parser('signing',help='הרשימה לפני חתימה');E.add_argument('--gate',help='הדוח של qa_gate.py (חובה, חוץ מ---preview)');E.add_argument('--preview',nargs='?',const=True,default=False,help='תצוגה מקדימה כשהצד השני מאותת שהוא מוכן לסיים: מה שחסר, בלי דוח שער ובלי רישום כ"עברה"; ערך אופציונלי: הציטוט שלהם');E.add_argument('--deal');E.add_argument('--profile');E.add_argument('--register',help='נשאר לתאימות, ואינו בשימוש: המרשם של מעריך הסיכונים אינו חוסם חתימה');E.add_argument('--fail',action='append',help='בדיקה בקריאה שנכשלה: <check>=<הפרט והמקום>. check אחד מ: %s'%', '.join(SC.MANUAL_CHECKS));E.add_argument('--pass',dest='pass_',action='append',help='בדיקה בקריאה שנכשלה בהרצה קודמת ועברה עכשיו: <check>');E.add_argument('--decisions');E.add_argument('--lang',choices=('he','en'),help='שפת התוצר; בלעדיו: meta.lang בקובץ המצב');F=B.add_parser('proportionality',help='מידתיות');F.add_argument('--decisions',required=True);F.add_argument('--fight-list',type=int,required=True,help='מספר הפריטים ברשימת המאבק');F.add_argument('--value-band',default='לא ידוע',help='קטנה / בינונית / גדולה / לא ידוע');F.add_argument('--value-text',help='השווי במילים, לשורת הסיכום. בלעדיו: "שווי ההתקשרות לא נמסר"');F.add_argument('--user-choice',choices=P.USER_CHOICES);F.add_argument('--answer-kind',choices=('explicit','delegated'));F.add_argument('--lang',choices=('he','en'),help='שפת שורת הסיכום והאפשרויות');M=B.add_parser('clean-copy',help='העותק הנקי לחתימה');M.add_argument('--agreed',required=True,help='הנוסח המוסכם, עם השינויים שעוד לא התקבלו');M.add_argument('--out',required=True,help='העותק לחתימה (docx)');M.add_argument('--deal',required=True,help='תיקיית העסקה: הרשימה לפני חתימה צריכה לעבור');K=B.add_parser('round-rules',help='מטריצת הסבבים, ובדיקת קובץ ההכרעות מולה');K.add_argument('--round',type=int,help='בלעדיו: הסבב שבקובץ המצב');K.add_argument('--decisions',help='קובץ ההכרעות של הסבב: בדיקה מול המטריצה (קוד יציאה 3 על הפרה)');K.add_argument('--deal');K.add_argument('--lang',choices=('he','en'));K.add_argument('--compare',help='הפלט של compare_rounds.py; בלעדיו: round-compare-<N>.json בתיקיית העסקה, כשקיים');C=B.add_parser('carry',help='שלד ההכרעות של סבב המשך: הכרעה מהסבב הקודם לכל פסקה שלא השתנתה');C.add_argument('--deal',required=True,help='תיקיית העסקה');C.add_argument('--compare',help='round-compare-<N>.json; בלעדיו: לפי --round בתיקיית העסקה');C.add_argument('--round',type=int,help='הסבב; בלעדיו: לפי השוואת הסבב וקובץ המצב');C.add_argument('--received',help='הטיוטה שחזרה; בלעדיו: received שבהשוואה');C.add_argument('--prev-received',help='הטיוטה של הסבב הקודם; בלעדיו: received_documents בקובץ המצב');C.add_argument('--prev-decisions',help='קובץ ההכרעות של הסבב הקודם; בלעדיו: decisions_round_<N-1>.json');C.add_argument('--decisions',help='קובץ ההכרעות של הסבב (ההכרעות שכבר נכתבו נשמרות); בלעדיו: decisions_round_<N>.json בתיקיית העסקה, כשקיים');C.add_argument('--out',help='בלעדיו: --decisions, או decisions_round_<N>.json');C.add_argument('--dry-run',action='store_true');C.add_argument('--lang',choices=('he','en'));I=B.add_parser('resolve-threads',help='סימון "בוצע" לשרשורים שלנו בנושאים שנסגרו');I.add_argument('--docx',required=True,help='קובץ העבודה של הסבב, אחרי apply_redlines.py ולפני השער');I.add_argument('--compare',required=True,help='הפלט של compare_rounds.py לסבב הזה');I.add_argument('--out',required=True,help='הקובץ שנכתב; אותו נתיב כמו --docx מעדכן את קובץ העבודה במקומו');I.add_argument('--dry-run',action='store_true');I.add_argument('--lang',choices=('he','en'));I.add_argument('--decisions',help='קובץ ההכרעות של הסבב: עמדה חדשה בבועה חדשה מסמנת את הבועה הקודמת שלנו "בוצע"; תשובה בשרשור צריכה לומר שהיא מחליפה את ההצעה הקודמת (קוד 3)');L=B.add_parser('summary-head',help='השורות הראשונות של הסיכום: פריט קריטי פתוח, open_items, עדכון הפלייבוק');L.add_argument('--deal',required=True);L.add_argument('--round',type=int,help='בלעדיו: הסבב שבקובץ המצב');L.add_argument('--lang',choices=('he','en'),help='שפת התוצר; בלעדיו: הפרופיל, ואחריו meta.lang בקובץ המצב');L.add_argument('--profile',help='פרופיל-לקוח.json: deliverable_language (both: שפת הממשק)');N=B.add_parser('basis',help='בסיס ההשוואה לפני compare_rounds.py: ידוע, או שאלה אחת לבד לפני ההשוואה');N.add_argument('--deal',required=True,help='תיקיית העסקה');N.add_argument('--round',type=int,help='הסבב שנשלח; בלעדיו: הסבב שבקובץ המצב');N.add_argument('--lang',choices=('he','en'));Q=O.parse_args(argv);return{'questions':cmd_questions,'basis':cmd_basis,'review':cmd_review,'talking-points':cmd_talking_points,'signing':cmd_signing,'proportionality':cmd_proportionality,'clean-copy':cmd_clean_copy,'round-rules':cmd_round_rules,'resolve-threads':cmd_resolve_threads,'accept-rest':cmd_accept_rest,'paper-type':cmd_paper_type,'carry':cmd_carry,'summary-head':cmd_summary_head}[Q.cmd](Q)
if __name__=='__main__':sys.exit(main())
