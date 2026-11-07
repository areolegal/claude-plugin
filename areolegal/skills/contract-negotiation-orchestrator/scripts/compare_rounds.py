#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (c) Areo. All rights reserved. Licensed under the terms at https://areo.co.il/legal/terms
'השוואת סבב: מה קרה לכל הצעה שלנו, ומה הם שינו בשקט.'
import copy,datetime as _dt,difflib,json,os,re,sys
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
import areo_lib
from common.cli import OutputRefused,guard_out,load_docx_or_explain,no_bytecode,parser
import common.docx_tracked as dt,lawyer,threads as TH
from orchestrator import state_builder as SB
try:from content_checks import DEF_PATTERNS
except Exception:DEF_PATTERNS=[re.compile('\\(\\s*(?:להלן:?\\s*|the\\s+|hereinafter\\s+)?[\\"״“]([^\\"״”]{2,50})[\\"״”](?:\\s*(?:או|or)\\s*[\\"״“]([^\\"״”]{2,50})[\\"״”])?\\s*\\)'),re.compile('\\(להלן:?\\s*[\\"״“]([^\\"״”]{2,50})[\\"״”]'),re.compile('[\\"״“]([^\\"״”]{2,50})[\\"״”]\\s*(?:-|פירושו|פירושה|משמעו|משמעה|יהיה פירושו)'),re.compile('[\\"“]([A-Z][^\\"”]{1,50})[\\"”]\\s+(?:means|shall mean|has the meaning)'),re.compile('\\((?:the|hereinafter)?\\s*[\\"“]([A-Z][^\\"”]{1,50})[\\"”]\\)')]
W=dt.W
XML_SPACE='{http://www.w3.org/XML/1998/namespace}space'
BIDI=re.compile('[\u200e\u200f\u202a-\u202e]')
CLAUSE=re.compile('^\\s*(?:סעיף\\s+)?(\\d+(?:\\.\\d+)*)\\s*[.)\\s]')
CLAUSE_EXTRA=re.compile('^\\s*(?:(?i:section|clause|article|sec\\.|art\\.)\\s*(\\d+(?:\\.\\d+)*|[IVX]{1,6}|[A-Z])\\b[.):]?(?=\\s*$|\\s*[\\-:.]|\\s+[A-Z\\"“(\\[]|\\s+[א-ת])|\\(?(\\d+(?:\\.\\d+)+)\\)?[.):]?|\\(?(\\d+)\\)?[.):])(?:\\s+|$)|^\\s*\\(?(?:([אבגדהוזחטיכלמנסעפצקרשת])\\)?[.):]|([ivx]{1,6}|[IVX]{1,6}|[A-Za-z])\\)?[.)])\\s+')
REPEATING=re.compile('^(?:[A-Za-z]|[ivx]{1,6}|[IVX]{1,6}|[א-ת])$')
NEAR=.72
KINDS='their_silent','their_rejected_our_insert','their_tracked','our_accepted','our_accepted_partial','our_rejected','our_open'
def norm(s):return re.sub('\\s+',' ',re.sub('[\u200e\u200f\u202a-\u202e]','',s or'')).strip()
def clause_of(text):
	B=norm(text);A=CLAUSE.match(B)
	if A:return A.group(1)
	A=CLAUSE_EXTRA.match(B);return next((A for A in A.groups()if A),None)if A else None
def project(para,accept_authors=None,reject_authors=None,accept_rest=True):
	D=copy.deepcopy(para);G=set(accept_authors or());H=set(reject_authors or())
	def E(el):
		A=el.get(W+'author')
		if A in G:return True
		if A in H:return False
		return accept_rest
	for A in list(D.iter(W+'ins')):
		if A.getparent()is None:continue
		B=A.getparent()
		if E(A):
			for C in list(A):B.insert(list(B).index(A),C)
		B.remove(A)
	for A in list(D.iter(W+'del')):
		if A.getparent()is None:continue
		B=A.getparent()
		if E(A):B.remove(A);continue
		for C in list(A):
			for F in C.iter(W+'delText'):F.tag=W+'t';F.set(XML_SPACE,'preserve')
			B.insert(list(B).index(A),C)
		B.remove(A)
	return dt.para_text(D)
def _revs(p):return[A for A in p.iter(W+'ins',W+'del')if A.getparent()is not None and dt.local(A.getparent().tag)!='rPr']
def _full_text(el):
	A=[]
	for B in el.iter(W+'t',W+'delText',W+'tab'):A.append('\t'if dt.local(B.tag)=='tab'else B.text or'')
	return''.join(A)
def marked_by(para,ours):return any(A.get(W+'author')in ours for A in _revs(para))
def marked_by_others(para,ours):return any(A.get(W+'author')not in ours for A in _revs(para))
def _innermost(node,p):
	for A in node.iterancestors():
		if A is p:return
		if A.tag in(W+'ins',W+'del')and A.getparent()is not None and dt.local(A.getparent().tag)!='rPr':return A
def mark_fates(para,target,revs):
	G=target;E=[]
	for(J,P)in dt._text_nodes(para):
		A=_innermost(J,para);B=BIDI.sub('',dt._node_text(J))
		if E and E[-1][0]is A:E[-1][1]+=B
		else:E.append([A,B])
	G=BIDI.sub('',G or'');K={id(B):A for(A,B)in enumerate(revs)};H,L=[(0,0,())],set()
	while H:
		F,C,D=H.pop()
		if(F,C,D)in L:continue
		L.add((F,C,D))
		if F==len(E):
			if C==len(G):return{K[A]:B for(A,B)in D if A in K}
			continue
		A,B=E[F]
		if A is None:
			if G.startswith(B,C):H.append((F+1,C+len(B),D))
			continue
		I=dict(D)
		for M in[I[id(A)]]if id(A)in I else['rejected','accepted']:
			N=(M=='accepted')==(dt.local(A.tag)=='ins')
			if N and not G.startswith(B,C):continue
			O=D if id(A)in I else tuple(sorted(D+((id(A),M),)));H.append((F+1,C+(len(B)if N else 0),O))
def pair_up(a,b,a_alt=None):
	G=a_alt;G=G or a;H,C,D=[],list(range(len(a))),list(range(len(b)));L={}
	for B in D:
		E=clause_of(b[B])
		if E:L.setdefault(E,[]).append(B)
	for A in list(C):
		E=clause_of(a[A])or clause_of(G[A])
		if E and L.get(E)and not REPEATING.match(E):B=L[E].pop(0);H.append((A,B));C.remove(A);D.remove(B)
	for A in list(C):
		I,M=None,.0
		for B in D:
			J=difflib.SequenceMatcher(None,norm(a[A]),norm(b[B])).ratio()
			if G[A]!=a[A]:J=max(J,difflib.SequenceMatcher(None,norm(G[A]),norm(b[B])).ratio())
			if J>M:I,M=B,J
		if I is not None and M>=NEAR:H.append((A,I));C.remove(A);D.remove(I)
	N=dict(H)
	for A in list(C):
		F=N.get(A-1);K=N.get(A+1);B=None
		if F is not None and K is not None and K-F==2:B=F+1
		elif F is not None and A==len(a)-1 and F+1==len(b)-1:B=F+1
		elif K is not None and A==0 and K==1:B=0
		if B is not None and B in D and norm(a[A])and norm(b[B]):H.append((A,B));N[A]=B;C.remove(A);D.remove(B)
	return sorted(H),C,D
def authors_of(a):
	D=list(a.author or[])
	if a.profile:
		with open(a.profile,encoding='utf-8')as E:B=lawyer.lawyer_view(json.load(E))
		D+=[B.get('lawyer_name'),B.get('lawyer_name_en')]+list(B.get('lawyer_aliases')or[])
	C=[]
	for A in D:
		if A and A.strip()and A.strip()not in C:C.append(A.strip())
	return C
def resolve_sent(a):
	if a.sent:return a.sent,'assumed'if a.assumed_base else'sent'
	C=os.path.join(a.deal or'','negotiation_state.json')
	if not a.deal or not os.path.exists(C):return None,None
	with open(C,encoding='utf-8')as G:D=json.load(G)
	E=sorted((D.get('meta')or{}).get('sent_documents')or[],key=lambda d:d.get('round')or 0)
	if E:B=E[-1];A=B.get('file_name')or B.get('path')or'';A=A if os.path.isabs(A)else os.path.join(a.deal,A);return A,'assumed'if B.get('basis')=='assumed_last_work'else'sent'
	for H in('send','work'):
		F=[A for A in D.get('produced_documents')or[]if A.get('kind')==H]
		if F:A=F[-1].get('path')or'';return A if os.path.isabs(A)else os.path.join(a.deal,A),'assumed'
	return None,None
def snippet(a,b,width=150):
	a,b=norm(a),norm(b);A=0
	while A<min(len(a),len(b))and a[A]==b[A]:A+=1
	B=0
	while B<min(len(a),len(b))-A and a[len(a)-1-B]==b[len(b)-1-B]:B+=1
	C=max(0,A-40);D=lambda s:('…'if C else'')+s[C:min(len(s)-B+20,C+width)]+('…'if len(s)-B+20<len(s)else'');return D(a),D(b)
def defined_terms(paras):
	A={}
	for(C,D)in enumerate(paras):
		for E in DEF_PATTERNS:
			for F in E.finditer(D or''):
				for B in F.groups():
					if B:A.setdefault(B.strip(),C)
	return A
def orphaned_terms(proposed,now):
	B=now;A=proposed;G,H=defined_terms(A),defined_terms(B);E=[]
	for(C,F)in G.items():
		if C in H:continue
		I=re.compile('(?<![\\w\u0590-\u05ff])'+re.escape(C)+'(?![\\w\u0590-\u05ff])');D=[A for(A,B)in enumerate(B)if I.search(B or'')]
		if D:E.append({'term':C,'defined_in':clause_of(A[F])or'','defined_text':A[F][:300],'used_in':[clause_of(B[A])or''for A in D],'used_paras':D,'note':'ההגדרה נמחקה בנוסח שחזר, והמונח עדיין משמש. שאלה במנת השאלות: להחזיר את ההגדרה בעקוב אחר שינויים, או לתקן את הסעיף שמשתמש בו'})
	return E
def thread_view(sent_path,recv_path,ours,now):
	B=ours
	try:J,K=TH.read_threads(sent_path),TH.read_threads(recv_path)
	except Exception as L:print('הבועות לא נקראו (%s). ההשוואה רצה בלי שרשורים'%L);return[]
	M={(A['author'],A['date'],norm(A['text']))for A in J};G={}
	for H in K:G.setdefault(H['root_id'],[]).append(H)
	I=[]
	for(E,F)in G.items():A=next((A for A in F if A['id']==E),F[0]);C=[{'id':A['id'],'author':A['author'],'date':A['date'],'text':A['text'][:600],'ours':A['author']in B,'new':(A['author'],A['date'],norm(A['text']))not in M,'done':A['done']}for A in sorted(F,key=lambda c:(c['id']!=E,c['date']or''))];D=A.get('para');I.append({'root_id':E,'root_author':A['author'],'root_ours':A['author']in B,'para':D,'clause':clause_of(now[D])if isinstance(D,int)and D<len(now)else None,'done':A['done'],'entries':C,'their_reply_to_ours':A['author']in B and any(A['new']and not A['ours']for A in C),'their_new_thread':A['author']not in B and C[0]['new'],'last_is_theirs':not C[-1]['ours']})
	return I
def _state(deal):
	A=os.path.join(deal or'','negotiation_state.json')
	if not deal or not os.path.exists(A):return
	with open(A,encoding='utf-8')as B:return json.load(B)
def _sha(path):
	import hashlib as B;A=B.sha256()
	with open(path,'rb')as C:
		for D in iter(lambda:C.read(1<<16),b''):A.update(D)
	return A.hexdigest()
def _deal_path(deal,f):return f if not f or os.path.isabs(f)else os.path.join(deal,f)
def sent_round(st,sent_path):
	A=(st or{}).get('meta')or{}
	try:B=_sha(sent_path)
	except OSError:B=None
	C=next((A for A in A.get('sent_documents')or()if isinstance(A,dict)and B and A.get('sha256')==B and str(A.get('round')or'').isdigit()),None);return int(C['round'])if C else int(A.get('round_number')or 0)
def prior_keys(sent_path,ours,deal=None,round_number=None):
	E=sent_path;B=deal;C=_state(B)
	if not C:return set()
	F={A for A in ours or()if A};G=int(round_number or sent_round(C,E));H=C.get('meta')or{};J=next((A for A in H.get('received_documents')or()if isinstance(A,dict)and str(A.get('round'))==str(G)),None);A=_deal_path(B,(J or{}).get('file_name'))
	if A and os.path.exists(A):
		try:return dt.prior_revisions(dt.document_root(A),F)
		except Exception:pass
	I=set()
	for D in H.get('sent_documents')or():
		if not isinstance(D,dict)or int(D.get('round')or 0)>=G:continue
		A=_deal_path(B,D.get('file_name'))
		if A and os.path.exists(A)and os.path.abspath(A)!=os.path.abspath(E):
			try:K=dt.document_root(A)
			except Exception:continue
			I|={dt.revision_key(A)for A in K.iter(W+'ins',W+'del')if A.get(W+'author')in F}
	return I
def base_paragraphs(sent_paras,ours,prior=(),before=None):
	D=before;C=sent_paras;A=prior;A=set(A or());I=set(ours or())
	def E(e):return e is not None and e.get(W+'author')in I and dt.revision_key(e)not in A
	F=[D[B]if D is not None and not A else dt._reject_ours_para(C,E)for(B,C)in enumerate(C)];B,G=[],0
	for(J,K)in zip(C,F):H=E(J.find(W+'pPr/'+W+'rPr/'+W+'ins'))and not norm(K);B.append(None if H else G);G+=0 if H else 1
	return B,[A for(A,B)in zip(F,B)if B is not None]
def _pair_blocks(a,b):
	C,D=[norm(A)for A in a],[norm(A)for A in b];E,L,M,I=[],[],[],{}
	for(P,J,N,F,K)in difflib.SequenceMatcher(None,C,D,autojunk=False).get_opcodes():
		if P=='equal':I.update({F+A:J+A for A in range(N-J)});continue
		B,G=set(),[]
		for A in range(J,N):
			Q=[A for A in range(F,K)if A not in B];H=max(Q,key=lambda j:difflib.SequenceMatcher(None,C[A],D[j]).ratio(),default=None)
			if H is not None and difflib.SequenceMatcher(None,C[A],D[H]).ratio()>=.5:E.append((A,H));B.add(H)
			else:G.append(A)
		R=[A for A in range(F,K)if A not in B]
		for(A,O)in zip([A for A in G if C[A]],[A for A in R if D[A]]):E.append((A,O));B.add(O);G.remove(A)
		L+=G;M+=[A for A in range(F,K)if A not in B]
	I.update({B:A for(A,B)in E});return sorted(E),L,M,I
def edits_before_sending(produced_path,sent_path,ours,prior=()):
	O=sent_path;N=produced_path;P,Q=dt.document_root(N),dt.document_root(O);R,Y=dt.body_paragraphs(P),dt.body_paragraphs(Q);K,L=[dt.para_text(A)for A in R],[dt.para_text(A)for A in Y];H,f=base_paragraphs(R,ours,prior)
	def I(i):
		if i is None or i>=len(H):return None,None
		if H[i]is not None:return H[i],None
		return None,next((H[A]for A in range(i-1,-1,-1)if H[A]is not None),None)
	B=[];S,Z,a,b=_pair_blocks(K,L)
	for(D,C)in S:E,J=I(D);B.append({'kind':'text_edited','para':E,'after_para':J,'sent_para':C,'produced_text':K[D],'sent_text':L[C]})
	for D in Z:
		if norm(K[D]):E,J=I(D);B.append({'kind':'text_deleted','para':E,'after_para':J,'sent_para':None,'produced_text':K[D],'sent_text':''})
	for C in a:
		if norm(L[C]):c=max((A for(A,B)in S if B<C),default=None);E,J=I(c);B.append({'kind':'text_added','para':None,'after_para':E if E is not None else J,'sent_para':C,'produced_text':'','sent_text':L[C]})
	T=set(ours or());U=[A for A in dt.read_comments(N)if A['author']in T];V=[A for A in dt.read_comments(O)if A['author']in T];d,e=dt.comment_paragraphs(P),dt.comment_paragraphs(Q)
	for A in U:A['base']=I(d.get(A['id']))[0]
	for F in V:F['base']=I(b.get(e.get(F['id'])))[0]
	G,W=list(V),[]
	for A in U:
		X=next((B for B in G if norm(B['text'])==norm(A['text'])and(B['date']==A['date']or B['base']==A['base'])),None)
		if X is not None:G.remove(X)
		else:W.append(A)
	for A in W:
		M=next((B for B in G if B['date']and B['date']==A['date']),None)or next((B for B in G if A['base']is not None and B['base']==A['base']),None)
		if M is not None:G.remove(M);B.append({'kind':'external_comment_rewritten','para':A['base'],'author':A['author'],'produced_text':A['text'],'sent_text':M['text']})
		else:B.append({'kind':'external_comment_deleted','para':A['base'],'author':A['author'],'produced_text':A['text'],'sent_text':''})
	for F in G:B.append({'kind':'external_comment_added','para':F['base'],'author':F['author'],'produced_text':'','sent_text':F['text']})
	return B
def sent_edits_line(sent_path,deal):
	E=sent_path;B=_state(deal)
	if not B:return
	try:H=_sha(E)
	except OSError:return
	A=next((A for A in(B.get('meta')or{}).get('sent_documents')or()if isinstance(A,dict)and A.get('sha256')==H),None)
	if not A or not A.get('edited_before_sending'):return
	F=[B for B in B.get('lawyer_overrides')or()if isinstance(B,dict)and B.get('source')=='edited_before_sending'and str(B.get('round'))==str(A.get('round'))];I=B.get('numbering_map')or{};C=[]
	for G in F:
		D=G.get('clause')or I.get(G.get('clause_id'))or''
		if D and D not in C:C.append(D)
	return'ההשוואה היא מול הקובץ שנשלח בפועל בסבב %s, %s, שעורך הדין ערך לפני המשלוח: %d הבדלים מול העותק שהופק%s, רשומים ב-lawyer_overrides'%(A.get('round'),os.path.basename(A.get('file_name')or E),len(F),' (%s)'%', '.join(C[:8])if C else'')
def state_clauses(path):
	A=path
	if not A or not os.path.exists(A):return{}
	with open(A,encoding='utf-8')as B:C=json.load(B)
	return{A.get('clause_id'):A for A in C.get('clauses')or[]}
def main(argv=None):
	no_bytecode();N=parser(__doc__.split('\n')[0],out_required=False);N.add_argument('--sent',help='הקובץ שהחברה שלחה בסבב הקודם. בלעדיו: מקובץ המצב (--deal)');N.add_argument('--received',required=True,help='הקובץ שחזר מהצד שכנגד');N.add_argument('--author',action='append',help='שם עורך הדין של החברה, כפי שהוא בסימונים שלנו. אפשר כמה פעמים');N.add_argument('--profile',help='פרופיל-לקוח.json: כל השמות שלנו (lawyer_name, lawyer_name_en, lawyer_aliases)');N.add_argument('--deal',help='תיקיית העסקה: בסיס ההשוואה כשאין --sent, וסעיפים CLOSED שנפתחו');N.add_argument('--assumed-base',action='store_true',help='--sent לא אושר כקובץ שנשלח בפועל: התוצאה מסומנת בסיס משוער');E=N.parse_args(argv);F=authors_of(E)
	if not F:print('חסר שם עורך הדין שלנו: --profile, או --author (אפשר כמה פעמים)');return 2
	I,j=resolve_sent(E)
	if not I or not os.path.exists(I):print('אין קובץ שנשלח להשוואה%s. כתוב בסיכום: "לא ניתן לאתר שינויים שלא סומנו: הקובץ שנשלח אינו זמין."'%(' (%s)'%I if I else''));return 2
	if not os.path.exists(E.received):print('הקובץ שחזר מהצד שכנגד אינו קיים: %s'%E.received);return 2
	for u in(I,E.received):
		v,V,w=load_docx_or_explain(u,loader=False)
		if v is None:print(V);return w
	if E.out:
		try:guard_out(E.out,inputs=[I,E.received])
		except OutputRefused as a:print('סירוב: %s'%a);return 1
	X=dt.body_paragraphs(dt.document_root(I));D=[project(A,accept_authors=F,accept_rest=True)for A in X];O=[project(A,reject_authors=F,accept_rest=True)for A in X];R,AB=base_paragraphs(X,F,prior_keys(I,F,E.deal),O);S=dt.body_paragraphs(dt.document_root(E.received));L=[project(A,accept_authors=F,accept_rest=False)for A in S];H=[project(A,accept_rest=True)for A in S];C={'sent':I,'received':E.received,'author':F[0],'authors':F,'base':j,'clauses':[],'counts':{}}
	def J(kind,para_text_,**B):A={'classification':kind,'clause':clause_of(para_text_)};A.update(B);C['clauses'].append(A)
	def Y(i,j):
		A={'sent_para':i,'base_para':R[i]if i is not None else None,'received_para':j,'we_sent':D[i]if i is not None else''}
		if i is not None and R[i]is None:A['after_base_para']=next((R[A]for A in range(i-1,-1,-1)if R[A]is not None),None)
		return A
	def x(sp,rp):
		B=[(dt.local(A.tag),A.get(W+'author'),norm(_full_text(A)))for A in _revs(sp)if A.get(W+'author')not in F];C=[]
		for A in _revs(rp):
			if A.get(W+'author')in F:continue
			if any(A.tag==W+'ins'and A.get(W+'author')in F for A in A.iterancestors(W+'ins')):continue
			D=dt.local(A.tag),A.get(W+'author'),norm(_full_text(A))
			if D in B:B.remove(D);continue
			C.append(A)
		return C
	k,y,z=pair_up(D,L,O)
	for(A,B)in k:
		b,Z=X[A],S[B];c=_revs(b)
		if norm(L[B])in(norm(D[A]),norm(O[A])):A0='accepted'if norm(L[B])==norm(D[A])else'rejected';d={A:A0 for A in range(len(c))}
		else:d=mark_fates(b,L[B],c)
		A1=d is not None;K=Y(A,B)
		if not A1:
			J('their_silent',D[A],they_opened_with=L[B],note='הנוסח השתנה בלי סימון מעקב. נדרשת הכרעתך (מצב 9), ומוצג בשורות הראשונות של הסיכום',**K)
			if marked_by(Z,F):J('our_open',D[A],we_proposed=D[A],now=H[B],note='ההצעה עוד מסומנת: לא קיבלו ולא דחו. אין לגעת בה',**K)
		else:
			A2=[(dt.local(A.tag),norm(_full_text(A)),A)for A in _revs(Z)if A.get(W+'author')in F];l,T=set(),[]
			for(A3,e)in enumerate(c):
				if e.get(W+'author')not in F:continue
				m,f=dt.local(e.tag),norm(_full_text(e))
				if not f:continue
				n=d.get(A3,'accepted');o=next((A for A in A2 if id(A[2])not in l and A[0]==m and A[1]==f),None)
				if o is not None:l.add(id(o[2]));n='open'
				T.append({'kind':m,'text':f,'fate':n})
			U=[(A,[A for A in A.iter(W+'del')if A.get(W+'author')not in F])for A in _revs(Z)if A.tag==W+'ins'and A.get(W+'author')in F];U=[(B,A)for(B,A)in U if A]
			if U:A4=''.join(_full_text(B)for(C,A)in U for B in A);J('their_rejected_our_insert',D[A],we_proposed=D[A],now=H[B],marks=T,they_deleted=A4,fully=all(norm(''.join(_full_text(A)for A in B))==norm(_full_text(A))for(A,B)in U),note='הם מחקו בעקוב אחר שינויים את מה שהוספנו: דחייה של ההצעה שלנו, במעקב. סיווג אחד; המחיקה שלהם מוכרעת לפי מספר הזיהוי שלה (their_changes)',**K)
			elif T:
				g={A['fate']for A in T}
				if g=={'open'}:J('our_open',D[A],we_proposed=D[A],now=H[B],note='ההצעה עוד מסומנת: לא קיבלו ולא דחו. אין לגעת בה',**K)
				elif g=={'accepted'}:J('our_accepted',D[A],we_proposed=D[A],now=H[B],note='ההצעה נשארה. הסעיף עובר ל-CLOSED כשאין בו נקודה פתוחה (negotiation_state.py write --compare)',**K)
				elif g=={'rejected'}:J('our_rejected',D[A],we_proposed=D[A],was_before=O[A],now=H[B],note='הנוסח חזר למה שהיה. הסעיף מוכרע מחדש לפי הפלייבוק',**K)
				else:J('our_accepted_partial',D[A],we_proposed=D[A],now=H[B],marks=T,note='קבלה חלקית: לכל סימון הגורל שלו (accepted, rejected, open). אינה שינוי שקט',**K)
		h=x(b,Z)
		if h:J('their_tracked',H[B],now=H[B],they_added=''.join(_full_text(A)for A in h if A.tag==W+'ins'),they_deleted=''.join(_full_text(A)for A in h if A.tag==W+'del'),note='מוכרע לפי מספר הזיהוי שלו, כמו בסבב הראשון',**K)
	for A in y:
		if not norm(D[A]):
			if norm(O[A]):J('our_accepted',O[A],we_proposed='',now='',note='מחקנו את הפסקה, והיא אינה בקובץ שחזר: המחיקה התקבלה',**Y(A,None))
			continue
		if not norm(O[A]):J('our_rejected',D[A],we_proposed=D[A],was_before='',now='',note='פסקה שהוספנו אינה בקובץ שחזר: ההוספה נדחתה',**Y(A,None));continue
		J('their_silent',D[A],they_opened_with='',note='פסקה ששלחנו אינה בקובץ שחזר, ואין סימון מחיקה',**Y(A,None))
	for B in z:
		if not norm(L[B])and not norm(H[B]):continue
		K={'sent_para':None,'base_para':None,'received_para':B,'we_sent':''}
		if marked_by_others(S[B],F)and not norm(L[B]):J('their_tracked',H[B],now=H[B],they_added=dt.revision_text(S[B],'ins'),note='פסקה שהם הוסיפו במעקב',**K)
		else:J('their_silent',L[B]or H[B],they_opened_with=L[B],note='פסקה שאינה במה ששלחנו, ואין סימון הוספה',**K)
	p={norm(A.get('agreed_text')):B for(B,A)in state_clauses(os.path.join(E.deal,'negotiation_state.json')if E.deal else None).items()if A.get('status')=='CLOSED'and A.get('agreed_text')}
	for G in C['clauses']:
		if G['classification']in('their_silent','their_tracked','their_rejected_our_insert')and p.get(norm(G.get('we_sent'))):G['reopens_closed']=p[norm(G['we_sent'])]
	C['para_map']=[{'sent_para':A,'base_para':R[A],'received_para':B}for(A,B)in k];C['threads']=thread_view(I,E.received,F,H)
	for G in C['clauses']:G['threads']=[A['root_id']for A in C['threads']if A['para']is not None and A['para']==G['received_para']]
	C['orphaned_terms']=orphaned_terms(D,H)
	for G in C['clauses']:P=G['classification'];C['counts'][P]=C['counts'].get(P,0)+1
	C['counts']['their_replies']=sum(1 for A in C['threads']if A['their_reply_to_ours']);C['counts']['their_new_comments']=sum(1 for A in C['threads']if A['their_new_thread']);M=[];q=sent_edits_line(I,E.deal)
	if q:M.append(q)
	if j=='assumed':M.append('בסיס משוער: ההשוואה היא מול %s, ולא מול קובץ שאושר כנשלח. שינוי "שקט" עשוי להיות עריכה שלנו לפני המשלוח'%os.path.basename(I))
	for G in C['clauses']:
		if G.get('reopens_closed'):M.append('פתיחה מחדש של סעיף מוסכם: %s (%s)'%(G.get('clause')or G['reopens_closed'],G['classification']))
		if G['classification']=='their_silent':A5,A6=snippet(G.get('we_sent'),G.get('they_opened_with'));M.append('שינוי שלא סומן: סעיף %s. נשלח: "%s". חזר: "%s"'%(G.get('clause')or'?',A5,A6))
	for i in C['orphaned_terms']:M.append('מונח בלי הגדרה: "%s" (ההגדרה ב-%s נמחקה; משמש ב-%s)'%(i['term'],i['defined_in']or'?',', '.join(A for A in i['used_in']if A)or'?'))
	Q=dt.future_dated(E.received,F);C['intake_warnings']=[]
	if Q:r=sum(1 for A in Q if A['kind']=='comment');A7=max(A['date']for A in Q);V='אזהרה (לא חוסמת): בטיוטה שחזרה %d בועות ו-%d סימוני מעקב של הצד השני מתוארכים אחרי היום (%s), עד %s (%s). התשובות שלנו מתוארכות היום, ולכן יופיעו לפני הבועות שלהם. התאריכים לא שונו'%(r,len(Q)-r,SB.display_date(None,'he'),SB.display_date(A7[:10],'he'),', '.join(sorted({A['author']or'?'for A in Q})));C['intake_warnings'].append({'code':'THEIR_DATES_IN_FUTURE','message':V,'items':Q});M.append(V)
	C['summary_head']=M
	if M:
		print('לשורות הראשונות של הסיכום:')
		for A8 in M:print('  '+A8)
	for P in KINDS:s=C['counts'].get(P,0);A9='  <-- הממצא החשוב ביותר'if P=='their_silent'and s else'';print('  %-26s %3d%s'%(P,s,A9))
	print('  %-26s %3d'%('their_replies (שרשור)',C['counts']['their_replies']));print('  %-26s %3d'%('their_new_comments',C['counts']['their_new_comments']))
	if not C['clauses']:print('  אין הבדל בין מה ששלחנו למה שחזר.')
	if E.out:
		try:t=guard_out(E.out,inputs=[I,E.received])
		except OutputRefused as a:print('סירוב: %s'%a);return 1
		with open(t,'w',encoding='utf-8')as AA:json.dump(C,AA,ensure_ascii=False,indent=2)
		print('נכתב %s'%t)
	return 0
if __name__=='__main__':sys.exit(main())
