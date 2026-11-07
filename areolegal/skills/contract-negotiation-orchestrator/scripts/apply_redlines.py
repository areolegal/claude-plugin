#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (c) Areo. All rights reserved. Licensed under the terms at https://areo.co.il/legal/terms
'סימון ההכרעות על הטיוטה של הצד שכנגד, בעקוב אחר שינויים, במנוע האחד.'
import datetime as _dt,json,os,re,shutil,sys
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
import areo_lib
from common.cli import OutputRefused,guard_out,load_docx_or_explain,no_bytecode,parser
import common.docx_tracked as dt
from common import gap_checks,paths
from orchestrator import pre_send,qa_gate
from orchestrator import state_builder as SB
from lawyer import lawyer_view,needs_english_name
import threads
def scrub_internal_codes(decisions):
	import content_checks as E;C=0
	for A in decisions or():
		for B in('external_comment','external_bubble'):
			if A.get(B):
				D=E.scrub_client_text(A[B])
				if D!=A[B]:A[B]=D;C+=1
	return C
def load(path,what):
	A=path
	if not os.path.exists(A):print('%s אינו קיים: %s'%(what,A));raise SystemExit(2)
	with open(A,encoding='utf-8')as B:
		try:return json.load(B)
		except ValueError as C:print('%s אינו JSON תקין (%s)'%(what,C));raise SystemExit(2)
def side_paths(out):A=out;B=A[:-5]if A.lower().endswith('.docx')else A;return B+'.expected.json',B+'.as_produced.docx'
def sentences(text):return[A.strip()for A in re.split('(?<=[.!?;])\\s+',text or'')if len(A.strip())>=20]
def marked_shares(draft,dec,ours=()):
	F=draft;C=dt.received_paragraphs(F);G=dt.body_paragraphs(dt.document_root(F));H=[]
	for A in dec.get('decisions')or[]:
		if A.get('op')!='replace'or not isinstance(A.get('para'),int)or A['para']>=len(C):continue
		B,D=C[A['para']],A.get('new_text')or''
		if len(G)==len(C)and dt.their_changes_mode(A)=='reject':B=dt.received_reject_text(G[A['para']],set(ours or()))
		I=dt.char_ops(B,D);L=sum(A[2]-A[1]for A in I if A[0]=='delete')+sum(len(A[3])for A in I if A[0]=='insert');E=[A for A in re.findall('\\w+',B)];M=set(re.findall('\\w+',D));J=sum(1 for A in E if A in M)/len(E)if E else .0;K=int(round(1e2*L/max(1,len(B)+len(D))));A['marked_share'],A['token_overlap']=K,round(J,2);H.append((A.get('id'),K,J))
	return H
def mark_survivors(draft,dec):
	C=dt.received_paragraphs(draft);D=[]
	for A in dec.get('decisions')or[]:
		if A.get('op')!='replace'or not isinstance(A.get('para'),int)or A['para']>=len(C):continue
		E=re.sub('\\s+',' ',A.get('new_text')or'');B=[A for A in sentences(C[A['para']])if re.sub('\\s+',' ',A)in E]
		if B:F='נשאר מהנוסח שלהם, לאישור: '+' | '.join(B);A['internal_comment']=((A.get('internal_comment')or'')+' '+F).strip();A['survived_sentences']=B;D.append((A.get('id'),B))
	return D
def _bare(s):return re.sub('[\\s\\u200e\\u200f.)\\-]+','',s or'')
def _strip_once(text,num):
	D=num;A=text;E,B='',0
	while B<len(A)and E!=D:
		if _bare(A[B]):
			if not D.startswith(E+A[B]):return
			E+=A[B]
		B+=1
	if E!=D:return
	C=B
	while C<len(A)and not _bare(A[C]):C+=1
	F=A[C:]
	if C==B and F:return
	if F[:1].isdigit()and _strip_once(F,D)is None:return
	return F
def strip_repeated_number(d):
	if d.get('op')!='insert_paragraph'or not d.get('number')or not d.get('text'):return
	B=_bare(d['number']);A=_strip_once(d['text'],B)if B else None
	while A is not None:d['text']=A;A=_strip_once(A,B)
HEB=re.compile('[\u0590-\u05ff]')
ENTITY_FIELDS='new','new_text','text','external_comment'
def _name_variants(name):A=name.strip();return sorted({A,A.replace('"','״'),A.replace('״','"')},key=len,reverse=True)
def english_entity_name(dec,profile,decisions_path=None):
	E=profile;C=decisions_path;F,B=E.get('organization_name'),E.get('organization_name_en')
	if not F:return[]
	G=_name_variants(F)+([qa_gate.ENTITY_NAME_EN_PLACEHOLDER]if B else[]);B=B or qa_gate.ENTITY_NAME_EN_PLACEHOLDER
	def H(items):
		E=[]
		for C in items:
			for D in ENTITY_FIELDS:
				A=C.get(D)
				if isinstance(A,str)and any(B in A for B in G):
					for F in G:A=A.replace(F,B)
					C[D]=A;E.append((C.get('id'),D))
		return E
	I=H(dec.get('decisions')or[])
	if I and C:
		with open(C,encoding='utf-8')as D:A=json.load(D)
		H(A.get('decisions',[])if isinstance(A,dict)else A)
		with open(C,'w',encoding='utf-8')as D:json.dump(A,D,ensure_ascii=False,indent=1)
	return I
def record_dependents(draft,decisions_path):
	F=decisions_path;E=draft;import content_checks as G
	with open(F,encoding='utf-8')as D:B=json.load(D)
	J=B.get('decisions',[])if isinstance(B,dict)else B;K=dt.received_paragraphs(E);L=G.numbered_labels(E);H,I=[],False
	for A in J:
		C=G.dependents_of(A,K,L)
		if C:
			H.append((A.get('id'),A.get('regime'),C))
			if A.get('dependents_found')!=C:A['dependents_found'],I=C,True
	if I:
		with open(F,'w',encoding='utf-8')as D:json.dump(B,D,ensure_ascii=False,indent=1)
	return H
def prior_history(profile,author,deal_dir,state):
	C=deal_dir;A=profile;D=[A for A in[A.get('lawyer_name'),A.get('lawyer_name_en')]+list(A.get('lawyer_aliases')or[])if A and A!=author];E=(state or{}).get('meta')or{}
	def F(rec):A=rec.get('file_name')or rec.get('path')or'';return A if os.path.isabs(A)else os.path.join(C or'',A)
	B=[A for A in E.get('sent_documents')or()if isinstance(A,dict)]
	if not(C and B):return D,set()
	G=max(int(A.get('round')or 0)for A in B);H=[F(A)for A in E.get('received_documents')or()if isinstance(A,dict)and int(A.get('round')or 0)<=G];return D,dt.sent_revision_keys([F(A)for A in B],H)
def file_prefix(a,st,profile,lang):
	C=lang;A=a.agreement_type,a.company or'';B=paths.stored_prefix(st)if st else None
	if not B or tuple(B)==A:return A
	D=a.file_prefix or paths.prefix_switch_answer(st)
	if D=='switch':print('שם הקובץ: התחילית מוחלפת ל-"%s" (במקום "%s" מהסבב הראשון), לפי התשובה לשאלה'%(' - '.join(A for A in A if A),' - '.join(A for A in B if A)));return A
	print('שם הקובץ: התחילית "%s" נקבעה בסבב הראשון ונשמרת (ולא "%s")'%(' - '.join(A for A in B if A),' - '.join(A for A in A if A)));E=A[1]if paths.name_lang(A[1])==C else profile.get('organization_name_en')if C=='en'else''
	if D is None and paths.prefix_switch_item(B,C,E):print('  התחילית בשפה שאינה שפת ההסכם. השאלה אם להחליף נשאלת פעם אחת, במנת השאלות (key: file_prefix, round_tools.py questions --profile), והתשובה נרשמת ב-negotiation_state.py decide --id file_prefix')
	return tuple(B)
def file_date(value,lang):
	A=value
	if A and re.fullmatch('\\d{4}-\\d{2}-\\d{2}',A):return SB.display_date(A,lang)
	return A or SB.display_date(None,lang)
def main(argv=None):
	no_bytecode();sys.stdout.reconfigure(encoding='utf-8',errors='replace');C=parser(__doc__.split('\n')[0],out_required=False,out_help='קובץ העבודה (docx), במקום שם לפי הכלל. לעולם לא הטיוטה שהתקבלה');C.add_argument('--draft',required=True,help='הטיוטה שהתקבלה מהצד שכנגד');C.add_argument('--decisions',required=True,help='decisions_round_<n>.json');C.add_argument('--profile',help='פרופיל-לקוח.json: שם עורך הדין וראשי התיבות');C.add_argument('--author',help='שם עורך הדין, כשאינו בפרופיל או בקובץ ההכרעות');C.add_argument('--initials',help='ראשי התיבות לבועות');C.add_argument('--report',help='דוח ההרצה (JSON)');C.add_argument('--internal-layer',dest='internal_layer',action='store_true',default=True,help='ברירת המחדל: לכתוב את השכבה הפנימית לקובץ העבודה (בועות פנימיות וכותרת פנימית)');C.add_argument('--no-internal-layer',dest='internal_layer',action='store_false',help='קובץ עבודה בלי השכבה הפנימית (רק לבדיקות; הנימוק נשאר בקובץ ההכרעות ובקובץ המצב)');C.add_argument('--deal',help='תיקיית העסקה: שם הקובץ נגזר לפי הכלל');C.add_argument('--agreement-type',help='סוג ההסכם, בשם המקוצר');C.add_argument('--company',help='שם החברה המקוצר, בלי סיומת התאגדות');C.add_argument('--round',type=int,help='מספר הסבב');C.add_argument('--date',help='התאריך בשם הקובץ (כלל 3.6: D.M.YYYY בעברית, "3 April 2027" באנגלית, או ISO); בלעדיו: היום');C.add_argument('--run-id',help='מזהה הריצה: הפקה מחדש באותה ריצה, לפני מסירה, מחליפה את הקבצים שלה');C.add_argument('--file-prefix',choices=('keep','switch'),help='סבב המשך: keep (ברירת המחדל) שומר את תחילת שם הקובץ מהסבב הראשון; switch מחליף אותה ל---agreement-type ו---company של ההרצה, אחרי שהמשתמש ענה לשאלה');A=C.parse_args(argv)
	if bool(A.out)==bool(A.deal):print('יש לתת --deal עם סוג ההסכם, החברה והסבב (שם לפי הכלל), או --out מפורש, ולא את שניהם');return 2
	if not os.path.exists(A.draft):print('הטיוטה אינה קיימת: %s'%A.draft);return 2
	m,n,o=load_docx_or_explain(A.draft,loader=False)
	if m is None:print(n);return o
	B=load(A.decisions,'קובץ ההכרעות');E=lawyer_view(load(A.profile,'הפרופיל')if A.profile else{});G=gap_checks.detect_lang('\n'.join(dt.received_paragraphs(A.draft)));F=A.author;O=A.initials
	if not F and E.get('lawyer_name'):
		F=qa_gate.author_for(E,G);O=O or qa_gate.initials_for(E,G)
		if B.get('author')and B['author']!=F:print('  "author" בקובץ ההכרעות (%s) שונה מעורך הדין בפרופיל; הסימונים והבועות נחתמים בשם מהפרופיל: %s'%(B['author'],F))
	if not F:F=B.get('author');O=O or B.get('initials')
	if not A.author and needs_english_name(E,G):print('ההסכם באנגלית, ובפרופיל אין שם באנגלית לעורך הדין (lawyer_name_en). קובץ העבודה מופק, והעותק למשלוח חסום עד שהשם נמסר. שאלה אחת: "באיזה שם באנגלית לחתום על ההערות לצד שכנגד?" (EN: "Which English name should sign the comments to the other side?"); התשובה נשמרת ב-build_profile.py של רכיב ההקמה: --set branding.lawyer_name_en="<השם>" --out <profile_path>, וקובץ העבודה מופק מחדש מאותן הכרעות.')
	if not F:print('אין שם עורך דין: לא ב---author, לא בקובץ ההכרעות ולא בפרופיל (lawyer_name). שאלו מי חותם על ההערות לצד שכנגד, ושמרו בפרופיל.');return 2
	c=G=='en'and E.get('organization_name')and not E.get('organization_name_en')
	if G=='en':
		for(J,p)in english_entity_name(B,E,A.decisions):print('  %s: השם העברי של החברה ב-%s הוחלף ב%s'%(J,p,'מציין המקום %s'%qa_gate.ENTITY_NAME_EN_PLACEHOLDER if c else'שם הרשום באנגלית (organization_name_en)'))
	if c:print('ההסכם באנגלית, ובפרופיל אין שם רשום באנגלית לחברה (organization_name_en). קובץ העבודה מופק, והעותק למשלוח חסום בשער (ENTITY_NAME_EN_MISSING) עד שהשם נמסר. שאלה אחת במנת השאלות: "מה השם הרשום של החברה באנגלית, כפי שהוא מופיע במרשם?" (EN: "What is the company\'s registered name in English?"); התשובה נשמרת ב-organization_name_en בפרופיל ברכיב ההקמה, וקובץ העבודה מופק מחדש מאותן הכרעות. השם העברי אינו מתועתק ואינו מתורגם.')
	W,I=None,None
	if A.deal and os.path.exists(os.path.join(A.deal,'negotiation_state.json')):
		with open(os.path.join(A.deal,'negotiation_state.json'),encoding='utf-8')as K:I=json.load(K)
		W=I.get('paper_type')or(I.get('meta')or{}).get('paper_type')
	if W in('tender_pre_bid','standard_form_online'):print('סוג הנייר הוא %s: אין סימון בגוף ואין בועות. התוצרים נבנים ב-AREO_RT/skills/contract-negotiation-orchestrator/scripts/tender_outputs.py.'%W);return 2
	X=dt.validate_decisions(B)
	if X:
		print('קובץ ההכרעות אינו עומד בחוזה, ולא נכתב קובץ (%d):'%len(X))
		for q in X:print('  - %s'%q)
		return 2
	S=None
	if A.deal:
		if not(A.agreement_type and A.round):print('עם --deal נדרשים --agreement-type ו---round');return 2
		r=file_date(A.date,G);s,t=file_prefix(A,I,E,G)
		try:Y=paths.safe_out_paths(A.deal,s,t,A.round,r,lang=G)
		except paths.PathTooLong as L:print('הנתיב ארוך מדי גם אחרי קיצור: %s. קצרו את שם התיקייה.'%L);return 2
		os.makedirs(A.deal,exist_ok=True)
		def Z(kind,name):
			B=pre_send.reusable_path(A.deal,A.round,A.run_id,kind,I)
			if B:T.append(kind)
			return B or paths.unique_path(name)
		T=[];A.out=Z('work',Y.work);S=Z('send',Y.send);u=Z('as_produced',Y.as_produced)
		if T:print('הפקה מחדש באותה ריצה (%s), לפני מסירה: הקבצים שלה מוחלפים (%s)'%(A.run_id,', '.join(T)))
	P,M=side_paths(A.out)
	if A.deal:M=u
	try:N=guard_out(A.out,inputs=[A.draft,A.decisions],allow_existing_doc=bool(A.deal and'work'in T));guard_out(P,inputs=[A.draft,A.decisions]);guard_out(M,inputs=[A.draft,A.decisions],allow_existing_doc=True)
	except OutputRefused as L:print('סירוב: %s'%L);return 1
	v=mark_survivors(A.draft,B)
	for H in B['decisions']:strip_repeated_number(H)
	if not A.internal_layer:
		for H in B['decisions']:H['internal_note']=H.pop('internal_comment',None)
	U=[A for A in B['decisions']if dt.is_areo_decision(A)and A.get('op')!='accept']
	if U:
		Q=str(E.get('display_language')or'he');Q='he'if Q not in('he','en')else Q;w=((I or{}).get('meta')or{}).get('position')or{};x=(I or{}).get('meta',{}).get('our_role')or w.get('our_side_in_agreement')or B.get('our_role');y=A.company or(E.get('organization_name_en')if Q=='en'else None)or E.get('organization_name');d=dt.areo_label(y,x,Q)
		for H in U:a=H.get('internal_comment');H['internal_comment']=d+(' '+a if a and not str(a).startswith(d)else'')
		print('סעיפי AREO (אין להם עמדה בפלייבוק): %d, מסומנים בקובץ העבודה במירקור צהוב ובבועה פנימית: %s'%(len(U),', '.join(str(A.get('id'))for A in U)))
	b=A.deal or os.path.dirname(os.path.abspath(A.decisions));V=I
	if V is None and os.path.exists(os.path.join(b,'negotiation_state.json')):
		try:
			with open(os.path.join(b,'negotiation_state.json'),encoding='utf-8')as K:V=json.load(K)
		except ValueError:V=None
	e,z=prior_history(E,F,b,V);f=scrub_internal_codes(B['decisions'])
	if f:print('קודים פנימיים הוסרו מבועות לפני הכתיבה לקובץ: %d'%f)
	D=dt.apply_decisions(A.draft,B,out_path=N,author=F,initials=O,internal_header=bool(A.internal_layer),prior_authors=e,prior_keys=z);A0=marked_shares(A.draft,B,{F}|set(e or()));g=[(A['reply_to_comment'],A.get('external_comment')or'')for A in B['decisions']if A.get('reply_to_comment')and A.get('external_comment')];A1=threads.apply_threads(N,g,F)if g and not D.get('errors')else[]
	if D.get('errors'):print('קובץ ההכרעות נדחה: %s'%'; '.join(D['errors']));return 2
	with open(P,'w',encoding='utf-8')as K:json.dump(D['expected_accept'],K,ensure_ascii=False,indent=1)
	shutil.copyfile(N,M);A2=len(B['decisions'])-len(D['not_marked']);print('קובץ העבודה: %s'%N);print('  הכרעות: %d, סומנו: %d%s, לא סומנו: %d'%(len(B['decisions']),A2,' (מהן קיימות מסבב קודם: %d)'%len(D['existing'])if D.get('existing')else'',len(D['not_marked'])))
	for h in D['not_marked']:print('    לא סומנה %s: %s'%(h['id'],h['reason']))
	for i in D.get('existing')or():print('    %s: %s'%(i['id'],i['note']))
	for A3 in D['verify']:print('  בדיקת הלוך ושוב: %s'%(A3,))
	for(J,j,A4)in A0:print('  %s: סומנו %d%% מהפסקה%s'%(J,j,', ורוב המילים נשארו: לסמן ב-replace_span רק את מה שמשתנה'if j>=80 and A4>=.4 else''))
	for(J,A5)in v:print('  משפטים מהנוסח שלהם ששרדו בהחלפה %s (לאישור מפורש): %s'%(J,' | '.join(A5)))
	for(A6,A7)in A1:print('  בועה %s שלהם: %s'%(A6,A7))
	for(J,A8,A9)in record_dependents(A.draft,A.decisions):print('  סעיפים תלויים ב-%s (%s): פסקאות %s. לכל אחד הכרעה, או dependents עם keep ו-reason'%(J,A8,', '.join(map(str,A9))))
	if A.deal and A.run_id:pre_send.update_run_record(A.deal,A.round,A.run_id,{'work':N,'as_produced':M,'expected_accept':P})
	if G=='en':
		for H in B['decisions']:
			k=[A for A in('new','new_text','text')if HEB.search(H.get(A)or'')]
			if k:print('  אזהרה: %s מכניס אותיות עבריות לנוסח של הסכם באנגלית (%s). שער האיכות חוסם זאת (LANG_HEBREW_IN_EN), אלא כשזה ציטוט של נוסח קיים'%(H.get('id'),', '.join(k)))
	print('  נוסחי היעד לשער: %s'%P);print('  העותק כפי שהופק: %s'%M)
	if S:print('  העותק למשלוח (ל-qa_gate.py --send): %s'%S)
	if D['not_marked']:print('הכרעה שלא סומנה לא הוחלה בכלל, ולא חלקית. מסור אותה למשתמש לטיפול ידני, ואל תסמן אותה בעצמך.')
	l={'work':N,'author':F,'lang':G,'decisions':len(B['decisions']),'not_marked':D['not_marked'],'existing':D.get('existing')or[],'verify':D['verify'],'expected_accept':P,'as_produced':M,'send':S}
	if A.report:
		try:R=guard_out(A.report,inputs=[A.draft,A.decisions])
		except OutputRefused as L:print('הדוח לא נכתב. סירוב: %s'%L)
		else:
			os.makedirs(os.path.dirname(os.path.abspath(R)),exist_ok=True)
			with open(R,'w',encoding='utf-8')as K:json.dump(l,K,ensure_ascii=False,indent=2)
	elif A.deal:
		R=qa_gate.run_report_path(A.deal,A.round,'apply.json')
		try:guard_out(R,inputs=[A.draft,A.decisions])
		except OutputRefused as L:print('הדוח לא נכתב. סירוב: %s'%L)
		else:print('  דוח ההרצה: %s'%qa_gate.write_run_report(R,l))
	return 0 if D['ok']else 3
if __name__=='__main__':sys.exit(main())
