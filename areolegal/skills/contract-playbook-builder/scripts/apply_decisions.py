# -*- coding: utf-8 -*-
# Copyright (c) Areo. All rights reserved. Licensed under the terms at https://areo.co.il/legal/terms
import argparse,hashlib,io,json,os,shutil,sys
from datetime import datetime,timezone
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
import areo_lib
from playbook import after_ingest
from playbook import approval_sheet as A
from playbook import ingest_approval as IA
from playbook import status as S
for _s in(sys.stdout,sys.stderr):
	try:_s.reconfigure(encoding='utf-8',errors='replace')
	except(AttributeError,ValueError):pass
STATUS={'accept':'approved','edit':'approved_with_change','reject':'rejected','na':'not_relevant'}
HE={'approved':'אושר','approved_with_change':'אושר עם שינוי','rejected':'לא אושר','not_relevant':'לא רלוונטי'}
EN_STATUS={'approved':'approved','approved_with_change':'approved with a change','rejected':'not approved','not_relevant':'not relevant','held':'not recorded'}
HE.setdefault('held','האישור לא נרשם')
OUTCOME_PICK={'approve':'accept','approve_change':'edit','reject':'reject','not_relevant':'na'}
PICK_ORDER='reject','edit','accept','na'
REVERSE={B:A for(A,B)in STATUS.items()}
FIELDS={'pos':'position','crit':'match_criteria','clause':'proposed_clause','comments':'comments'}
COLORS='green','yellow','red'
def now():return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
def load(path,what):
	A=path
	if not os.path.exists(A):sys.exit('שגיאה: %s לא נמצא בנתיב %s'%(what,A))
	try:return json.load(io.open(A,encoding='utf-8'))
	except ValueError as B:sys.exit('שגיאה: %s אינו JSON תקין (%s)'%(what,B))
def write(path,data):
	A=path
	if os.path.exists(A):shutil.copyfile(A,A+'.bak')
	with io.open(A,'w',encoding='utf-8')as B:json.dump(data,B,ensure_ascii=False,indent=2);B.write('\n')
def from_db(raw):
	B=raw;E=B.get('documents')or B.get('docs')or B
	if isinstance(E,dict):E=[{'id':A,'data':B}for(A,B)in E.items()]
	H,I,J,K,F={},{},{},{},[]
	for G in E:
		C=G.get('id')or(G.get('data')or{}).get('rule_id');A=G.get('data')or{}
		if not C or A.get('applied'):continue
		D=A.get('status')
		if D in STATUS:D=STATUS[D]
		if D not in HE:continue
		H[C]=REVERSE[D]
		if A.get('note'):I[C]=A['note']
		if A.get('wording'):J[C]=A['wording']
		if A.get('by'):K[C]=A['by']
		if A.get('at'):F.append(A['at'])
	return{'playbook':B.get('playbook')or{},'decisions':H,'notes':I,'ruleEdits':J,'by_rule':K,'exported':B.get('read_at')or(max(F)if F else'')}
def from_wizard(raw):
	D=raw;G,K,L,R,M,H,S,T,I={},{},{},{},[],{},{},{},{};J={};U=D.get('by')or'';V=D.get('lang')or'';N=(D.get('schema')or 0)>=2
	for A in D.get('entries')or[]:
		B,E=A.get('rule_id'),A.get('type')
		if not B or not E:continue
		if A.get('by')or U:R[B]=A.get('by')or U
		if A.get('at'):M.append(A['at']);S[B]=A['at']
		T[B]=A.get('clause_lang')or None
		if E=='decision':
			C,O=A.get('track'),A.get('outcome')
			if C not in COLORS or O not in OUTCOME_PICK:continue
			F=str(A.get('wording')or'');J.setdefault(B,{})[C]={'outcome':O,'wording':F}
			if A.get('clause_hash'):H.setdefault(B,{})[C]=A['clause_hash']
			if O=='approve_change'and F.strip():L.setdefault(B,{})[C]={'clause':F}
		elif E=='approve':
			G[B]='accept';P={A:B for(A,B)in(A.get('track_hashes')or{}).items()if A in COLORS and B}
			if P:H.setdefault(B,{}).update(P);I[B]=[A for A in COLORS if A in P]
			else:
				if A.get('clause_hash'):H.setdefault(B,{})['green']=A['clause_hash']
				I[B]=['green']
			for W in I[B]:J.setdefault(B,{}).setdefault(W,{'outcome':'approve','wording':''})
		elif E=='suggestion':
			G[B]='edit';C=A.get('track')or'green';F=(A.get('wording')if N else A.get('wording')or A.get('text'))or''
			if not str(F).strip():G.pop(B,None);continue
			L.setdefault(B,{})[C]={'clause':F}
			if A.get('clause_hash'):H.setdefault(B,{})[C]=A['clause_hash']
		elif E in('comment','note'):K[B]=(A.get('note')if N else A.get('note')or A.get('text'))or''
		if E=='approve'and not N and A.get('text'):K[B]=A['text']
	for(B,Q)in J.items():X={OUTCOME_PICK[A['outcome']]for A in Q.values()};G[B]=next(A for A in PICK_ORDER if A in X);I[B]=[A for A in COLORS if A in Q and Q[A]['outcome']=='approve']
	return{'playbook':D.get('playbook')or{},'decisions':G,'notes':K,'ruleEdits':L,'by_rule':R,'seen_hash':H,'at_rule':S,'clause_lang':T,'approve_tracks':I,'positions':J,'lang':V,'exported':D.get('created')or(max(M)if M else'')}
def wiz_hash(text):return A.wiz_hash(text)
def seen_matches(light,want,clause_lang,file_lang):
	D=clause_lang;C=want;B=light.get('proposed_clause')
	if not isinstance(B,dict):return wiz_hash(B or'')==C
	if D:return wiz_hash(B.get(D)or'')==C
	E,F=A.clause_text(B,file_lang or'he');return C in{wiz_hash(E),wiz_hash(B.get('he')or''),wiz_hash(B.get('en')or'')}
def records_dir_for(model_path,model):
	B=os.path.dirname(os.path.abspath(model_path));A=S._latest_record(model)or{}
	if A.get('record'):D=A['record']if os.path.isabs(A['record'])else os.path.join(B,A['record']);return os.path.dirname(os.path.normpath(D))
	C=os.path.dirname(B)
	if os.path.basename(C)=='playbooks':return os.path.join(os.path.dirname(C),'אישורים')
	return os.path.join(B,'אישורים')
def index_for(records,index_arg):
	A=index_arg
	if A:return A
	B=os.path.join(os.path.dirname(os.path.abspath(records)),'playbooks','index.json');return B if os.path.exists(B)else None
MSG={'he':{'counted':'נספרו כמאושרות: {a}. עכשיו מאושרות {n} מתוך {m} עמדות במדיניות.','already':'מתוך מה שאישרתם, {n} כבר היו מאושרות קודם ולא נספרו שוב.','value':'לא נספרו עד שייקבע הערך שבסוגריים: {n}, {r}.','legal':'לא נספרו עד שעורך דין יעבור עליהן ויאשר בצ\'אט ("נבדק ולאשר"): {n}, {r}.','person':"לא נספרו, כי השם באשף אינו שם מלא של אדם: {r}. אשרו אותם בצ'אט בשם המאשר.",'held':'לא נספרו, כי הנוסח השתנה מאז שאושר באשף: {r}. כדאי לשאול אם לאשר את הנוסח הנוכחי.','read':'בקובץ {m} הכרעות, ונקלטו {n}: {s}.','commented':'הערות שנרשמו לסעיפים, בלי לשנות את המעמד שלהם: {r}.','edited':'שינויי נוסח שהוחלו: {n}. הנוסח הקודם נשמר ביומן ההחלטות.','stale_edit':'{r}: הנוסח השתנה מאז שההצעה נכתבה, ולכן היא לא הוחלה. כדאי להשוות ולהחליט.','no_change':'{r}: סומן "אושר עם שינוי", אבל אין נוסח חדש או הערה. הנוסח נשאר כפי שהיה.','dry':'ריצת יובש. לא נכתב דבר.'},'en':{'counted':'Counted as approved: {a}. {n} of {m} positions in the policy are now approved.','already':'Of what you approved, {n} were already approved before and were not counted again.','value':'Not counted until the value in brackets is set: {n}, in {r}.','legal':'Not counted until a lawyer reviews them and approves in the chat ("reviewed and approve"): {n}, in {r}.','person':"Not counted, because the name in the wizard is not a person's full name: {r}. Approve them in the chat in the approver's name.",'held':'Not counted, because the wording changed after it was approved in the wizard: {r}. Ask whether to approve the current wording.','read':'The file has {m} decisions, and {n} were applied: {s}.','commented':'Comments added to clauses, without changing their status: {r}.','edited':'Wording changes applied: {n}. The previous wording is kept in the decision log.','stale_edit':'{r}: the wording changed after the suggestion was written, so it was not applied. Compare and decide.','no_change':'{r}: marked "approved with a change", but there is no new wording or comment. The wording stays as it was.','dry':'Dry run. Nothing was written.'}}
def nums(model,rids,lang='he'):
	B=rids;C=', '.join(A.display_num(model,B)or B for B in B)
	if lang=='en':return('clause %s'if len(B)==1 else'clauses %s')%C
	return('סעיף %s'if len(B)==1 else'סעיפים %s')%C
def npos(n,lang='he'):
	if lang=='en':return'1 position'if n==1 else'%d positions'%n
	return'עמדה אחת'if n==1 else'%d עמדות'%n
def _clip(text,n=400):A=text;A=' '.join(str(A or'').split());return A if len(A)<=n else A[:n-1]+'…'
def lang_for_preview(dec,model):return S.norm_lang(dec.get('lang'))or S.model_lang(model)
def rules_of(model):return model.get('rules')or[]
def rule_id(rule):return rule.get('rule_id')or rule.get('id')or''
def tl_of(rule):return rule.get('traffic_light')or rule.get('tl')or{}
def as_list(value):
	A=value
	if isinstance(A,list):return[str(A).strip()for A in A if str(A).strip()]
	return[A.strip()for A in str(A).split('\n')if A.strip()]
def check_batch(model,dec,force):
	A=dec.get('exported')or'';B=model.setdefault('applied_decision_batches',[])
	if A and any(B.get('exported')==A for B in B):
		if not force:sys.exit('הקובץ הזה כבר נקלט ב-%s. אין מה לקלוט שוב. לקליטה חוזרת מכוונת הוסף --force.'%next(B.get('applied_at','')for B in B if B.get('exported')==A))
		print('אזהרה: הקובץ כבר נקלט בעבר, נקלט שוב לבקשתך.')
	return A,B
def check_kind(dec):
	A=dec.get('kind')
	if A=='comments_and_proposals':sys.exit('שגיאה: זה קובץ הערות והצעות מגרסה קודמת של סביבת העבודה, ולא קובץ ההערות של האשף. הוא אינו נקלט. כתבו את ההערות באשף ההערות (בסביבת העבודה: "להעיר על הסעיף באשף"), והעלו את הקובץ שהוא מפיק.\nError: this is a comments file from an earlier version of the workspace, not the wizard\'s comments file, and it is not ingested. Write the comments in the comments wizard and upload the file it creates.')
	if A and A not in('areo-playbook-notes','decisions'):sys.exit('שגיאה: סוג הקובץ %r אינו מוכר. נדרש קובץ ההחלטות של האשף (kind: areo-playbook-notes).'%A)
def check_playbook(model,dec):
	E=model;check_kind(dec);F=dec.get('playbook')or{};A,B=F.get('id'),E.get('playbook_id')
	if not A:return['קובץ ההחלטות אינו נושא מזהה פלייבוק. ודא שהוא הופק מסביבת העבודה של הפלייבוק הזה ולא מאחר.']
	if B and A!=B:sys.exit('שגיאה: הקובץ שייך לפלייבוק %s, והמודל הוא %s. אין לקלוט בין פלייבוקים.'%(A,B))
	G=[];C,D=F.get('model_updated'),E.get('last_updated')
	if C and D and C!=D:G.append('המודל עודכן מאז שההחלטות התקבלו (%s מול %s). כל סעיף שנוסחו השתנה מאז מסומן כטעון אימות ואינו מוחל.'%(C,D))
	return G
def apply_edits(rule,edits,log_entry):
	M=log_entry;O,I=tl_of(rule),0
	for F in COLORS:
		J=(edits or{}).get(F)or{};C=O.get(F)
		if not isinstance(C,dict):continue
		for(G,E)in FIELDS.items():
			if G not in J:continue
			B=as_list(J[G])if G=='crit'else str(J[G]);D=C.get(E)
			if G=='clause':
				N=A.clause_text(D,'he')[0]if isinstance(D,dict)else D
				if N==B:continue
				if isinstance(D,dict):
					K='he'if any(1424<=ord(A)<=1535 for A in B)else'en';C[E]={'he':B if K=='he'else'','en':B if K=='en'else'','source_language':K}
					for L in D:
						if L not in('he','en','source_language'):C[E][L]=D[L]
				else:C[E]=B
				H=C.get('fallback_wording')
				if F=='yellow'and isinstance(H,dict)and H.get('text'):H['text']=B
				elif F=='yellow'and isinstance(H,str)and H.strip():C['fallback_wording']=B
				C['edited_by_user']=True;M.setdefault('wording_changes',[]).append({'track':F,'field':E,'from':N,'to':B,'source':'wizard_suggestion'});I+=1;continue
			if D==B:continue
			C[E]=B;C['edited_by_user']=True;M.setdefault('wording_changes',[]).append({'track':F,'field':E,'from':D,'to':B});I+=1
	return I
def sync_core(core,decisions_by_id,model_by_id):
	C=0
	for A in core.get('clauses')or[]:
		D=A.get('id');E=decisions_by_id.get(D)
		if not E:continue
		A['decision']=E;F=model_by_id.get(D)
		if F:
			G=tl_of(F)
			for(H,I)in(('preferred_wording','green'),('fallback_wording','yellow'),('red_line','red')):
				B=G.get(I)or{}
				if B.get('edited_by_user')and B.get('proposed_clause'):A[H]=B['proposed_clause']
		C+=1
	return C
def main():
	G=argparse.ArgumentParser(add_help=True);G.add_argument('--decisions',required=True);G.add_argument('--from-db',action='store_true',help='הקובץ הוא קריאה ממאגר ה-Artifact ולא ייצוא מהדפדפן');G.add_argument('--model',required=True);G.add_argument('--core');G.add_argument('--by',default='');G.add_argument('--dry-run',action='store_true');G.add_argument('--force',action='store_true');G.add_argument('--records',help='תיקיית רשומות האישור (Areo-נתונים/אישורים). בלעדיה נגזרת מהמודל');G.add_argument('--index',help='playbooks/index.json, להטבעת המעמד. בלעדיו: לצד תיקיית האישורים, כשקיים');G.add_argument('--lang',help='שפת ההודעות: he או en. בלעדיו lang של קובץ ההערות');A=G.parse_args();B=load(A.decisions,'קובץ ההחלטות');check_kind(B)
	if A.from_db:
		B=from_db(B)
		if not B['decisions']:sys.exit('במאגר אין הכרעה שטרם נקלטה. אין מה לקלוט.')
	elif B.get('kind')=='areo-playbook-notes'or'entries'in B:
		B=from_wizard(B)
		if not B['decisions']and not B['notes']:sys.exit('בקובץ האשף אין אישור, הצעה או הערה. אין מה לקלוט.')
	D=load(A.model,'מודל הפלייבוק');A3=check_playbook(D,B);d,A4=check_batch(D,B,A.force);e={rule_id(A):A for A in rules_of(D)if rule_id(A)};U=B.get('decisions')or{};P=B.get('notes')or{};p=B.get('ruleEdits')or{}
	if not U and not any(str(A).strip()for A in P.values()):sys.exit('בקובץ אין אף הכרעה. אין מה לקלוט.')
	J,Q,V,W,X,f=[],{},[],{},[],[];g={}
	for(C,q)in sorted(U.items()):
		K=STATUS.get(q)
		if not K:V.append('%s: ערך הכרעה לא מוכר (%s)'%(C,q));continue
		I=e.get(C)
		if I is None:V.append('%s: אין סעיף כזה במודל'%C);continue
		E={'rule_id':C,'topic':I.get('topic_name',''),'status':K,'status_he':HE[K],'note':P.get(C,''),'decided_at':d,'applied_at':now(),'by':(B.get('by_rule')or{}).get(C)or A.by,'source':os.path.basename(A.decisions)};Y=[]
		for(Z,r)in((B.get('seen_hash')or{}).get(C)or{}).items():
			A5=(tl_of(I)or{}).get(Z)or{}
			if r and not seen_matches(A5,r,(B.get('clause_lang')or{}).get(C),B.get('lang')):Y.append(Z)
		h={'green':'בירוק','yellow':'בצהוב','red':'באדום'};i=(B.get('positions')or{}).get(C)or{};j=(B.get('approve_tracks')or{}).get(C)or(['green']if K=='approved'and not i else[]);R=[A for A in j if A in Y];s=[A for A in j if A not in Y]
		if R and not s and K=='approved':E['status'],E['status_he']='held','האישור לא נרשם';E['review_code']='held';E['review_required']='הנוסח %s השתנה במודל מאז שהלקוח אישר אותו, ולכן האישור לא נרשם. יש לשאול אם לאשר את הנוסח הנוכחי.'%' ו'.join(h.get(A,A)for A in R);J.append(E);X.append(C);continue
		if R:E['review_code']='held_partial';E['review_required']='הנוסח %s השתנה במודל מאז שהלקוח אישר אותו, ולכן האישור על העמדה הזאת לא נרשם. יש לשאול אם לאשר את הנוסח הנוכחי.'%' ו'.join(h.get(A,A)for A in R);X.append(C)
		k=[A for A in Y if A not in j]
		if k:
			E['review_code']='stale_edit';E['review_required']='הנוסח %s השתנה במודל מאז שהלקוח ראה אותו, ולכן ההצעה לא הוחלה. יש להשוות ולהכריע.'%' ו'.join(h.get(A,A)for A in k)
			for Z in k:(p.get(C)or{}).pop(Z,None)
		if i:E['positions']={A:dict(status=STATUS[OUTCOME_PICK[B['outcome']]],status_he=HE[STATUS[OUTCOME_PICK[B['outcome']]]],**{'held':True}if A in R else{})for(A,B)in i.items()}
		g[C]=s;A6=apply_edits(I,p.get(C),E)
		if K=='approved_with_change'and not A6 and not P.get(C)and not E.get('review_required'):E['review_code']='no_change';E['review_required']='סומן אושר עם שינוי, אך לא נמצא נוסח חדש ולא הערה. הנוסח נשאר כפי שהיה.'
		I['decision']={A:E[A]for A in('status','status_he','note','decided_at','applied_at','by','positions')if A in E};J.append(E);Q[C]=I['decision'];W[K]=W.get(K,0)+1
	for C in sorted(P):
		l=str(P[C]or'').strip()
		if C in U or not l:continue
		I=e.get(C)
		if I is None:V.append('%s: אין סעיף כזה במודל'%C);continue
		t=(B.get('by_rule')or{}).get(C)or A.by;u=(B.get('at_rule')or{}).get(C)or d;I.setdefault('client_notes',[]).append({'text':l,'by':t,'at':u,'source':os.path.basename(A.decisions)});J.append({'rule_id':C,'topic':I.get('topic_name',''),'status':'comment','status_he':'הערה','note':l,'decided_at':u,'applied_at':now(),'by':t,'source':os.path.basename(A.decisions)});f.append(C)
	A7={'green':('ירוקה','green'),'yellow':('צהובה','yellow'),'red':('אדומה','red')}
	for N in J:
		for a in N.get('wording_changes',[]):m=lang_for_preview(B,D);print(('Wording suggestion, %s, %s position:\n  now:  %s\n  new:  %s'if m=='en'else'הצעת נוסח, %s, העמדה ה%s:\n  עכשיו: %s\n  חדש:  %s')%(nums(D,[N['rule_id']],m),A7.get(a['track'],(a['track'],)*2)[m=='en'],_clip(a['from']),_clip(a['to'])))
	for n in A3:print('אזהרה: '+n)
	for n in V:print('לא נקלט, '+n)
	F=S.norm_lang(A.lang)or S.norm_lang(B.get('lang'))or S.model_lang(D);H=MSG[F];v={A:g[A]for A in Q if g.get(A)};L=None
	if v:
		A8=S.record_cells_for(D,A.model);A9=hashlib.sha256(io.open(A.decisions,'rb').read()).hexdigest();L=IA.wizard_approvals(D,v,B.get('by_rule')or{},os.path.basename(A.decisions),A9,B.get('at_rule'),None,A8,F);T,O=L['summary'],L['rules'];w=S.derive_status(D,L['cells'],lang=F);print(H['counted'].format(a=npos(T['approved'],F),n=w['approved_count'],m=w['positions_count']))
		if T['already']:print(H['already'].format(n=npos(T['already'],F)))
		if O['pending_value']:print(H['value'].format(n=npos(T['pending_value'],F),r=nums(D,O['pending_value'],F)))
		if O['pending_legal']:print(H['legal'].format(n=npos(T['pending_legal'],F),r=nums(D,O['pending_legal'],F)))
		if O['not_person']:print(H['person'].format(r=nums(D,O['not_person'],F)))
	if X:print(H['held'].format(r=nums(D,X,F)))
	AA=HE if F=='he'else EN_STATUS;AB=', '.join('%s: %d'%(AA[A],W[A])for A in sorted(W));print(H['read'].format(n=len(Q),m=len(U),s=AB or'-'))
	if f:print(H['commented'].format(r=nums(D,f,F)))
	x=sum(len(A.get('wording_changes',[]))for A in J)
	if x:print(H['edited'].format(n=x))
	for N in J:
		if N.get('review_code')in('stale_edit','no_change'):print(H[N['review_code']].format(r=nums(D,[N['rule_id']],F)))
	if A.dry_run:print(H['dry']);return
	D.setdefault('decision_log',[]).extend(J);A4.append({'exported':d,'applied_at':now(),'count':len(J),'source':os.path.basename(A.decisions),'by':A.by});D['last_updated']=now()[:10];M=load(A.core,'גרעין ההפעלה')if A.core else None
	if L is not None and any(A.get('via')=='wizard'for A in L['cells'].values()):
		y=A.records or records_dir_for(A.model,D);b=index_for(y,A.index);c=load(b,'האינדקס')if b and os.path.exists(b)else None
		try:import ingest_approval as AC;E,z=AC.index_entry_of(c,D,M)
		except Exception:E,z=None,None
		AD=(S._latest_record(D)or{}).get('record_id');o=IA.save_chat_record(y,L,supersedes=AD)
		try:A0=os.path.relpath(os.path.abspath(o),os.path.dirname(os.path.abspath(A.model)))
		except ValueError:A0=os.path.abspath(o)
		A1=after_ingest.apply_ingest(D,M,E,L,A0)
		if c is not None and E is not None:
			with io.open(b,'w',encoding='utf-8')as AE:json.dump(c if isinstance(c,dict)else z,AE,ensure_ascii=False,indent=1)
		print('רשומת האישור: %s'%o);print(S.label_for(A1['status'],F))
		for AF in A1.get('problems')or():print('  סתירה בין השכבות: %s'%AF)
	write(A.model,D);print('נכתב %s (גיבוי ב-%s.bak)'%(A.model,A.model))
	if M is not None:AG=sync_core(M,Q,e);M['source_model_updated']=D['last_updated'];M['generated_at']=now()[:10];write(A.core,M);print('סונכרנו %d סעיפים בגרעין ההפעלה.'%AG)
	else:print('הגרעין לא סונכרן. הרץ שוב עם --core, או בנה אותו מחדש מהמודל.')
	A2=os.path.join(os.path.dirname(os.path.abspath(A.decisions))or'.','decisions-applied.json');write(A2,{'applied_at':now(),'by':A.by,'playbook_id':D.get('playbook_id',''),'rules':sorted(Q),'note':'סמן את המסמכים האלה במאגר כ-applied:true, כדי שלא ייקלטו שוב וכדי שהדף יציג אותם כמי שנכנסו למדיניות.'});print('רשימת הסעיפים לסימון במאגר נכתבה ל-%s'%A2);print('הצעד הבא: בנה מחדש את סביבת העבודה מהמודל ופרסם לאותו קישור, כדי שכל המשתמשים המשותפים יראו את הפלייבוק המעודכן.')
if __name__=='__main__':main()
