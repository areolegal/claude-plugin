# -*- coding: utf-8 -*-
# Copyright (c) Areo. All rights reserved. Licensed under the terms at https://areo.co.il/legal/terms
import argparse,hashlib,io,json,os,re,sys
from datetime import date
try:sys.stdout.reconfigure(encoding='utf-8')
except(AttributeError,ValueError):pass
SCHEMA='drivers/1'
KINDS='yes_no','choice','number_threshold'
SOURCES='agreements','published','research','template','playbook','client'
CLAUSE_KINDS='fixed','deal_data','dependent','alternative'
EXPOSURE='high','medium','low'
EXPOSURE_RANK={'high':0,'medium':1,'low':2}
MIN_SIDE={'agreements':2,'published':3}
OPEN_QUESTION={'he':'במה ההסכם הזה משתנה אצלכם מעסקה לעסקה?','en':'What changes in this agreement from one deal to the next for you?'}
YES_NO={'he':[{'value':'yes','label':'כן'},{'value':'no','label':'לא'}],'en':[{'value':'yes','label':'Yes'},{'value':'no','label':'No'}]}
CODE_RX=re.compile('(?<![\\w\\-])(?:DOC-\\d+|MAND-[\\w\\-]+|REG-\\d+|AGR-\\d+|Q-[\\w\\-]+|[CFOAVD]\\d+[a-z]?)(?![\\w\\-])')
CLAUSE_QUESTION_RX=re.compile('להוסיף\\s+סעיף|לכלול\\s+סעיף|\\badd\\s+(?:a\\s+)?clause|\\binclude\\s+(?:a\\s+)?clause',re.I)
LONG_DASH=re.compile('[‒–—―]')
Q='"“”״'
DEF_PATTERNS=[re.compile('\\(\\s*(?:להלן|hereinafter|the)?\\s*[:\\-]?\\s*[%s]([^%s]{2,40})[%s]\\s*\\)'%(Q,Q,Q),re.I),re.compile('[%s]([^%s]{2,40})[%s]\\s*(?:-\\s*)?(?:פירושו|פירושה|פירושם|משמעו|משמעה|משמעותו|means|shall\\s+mean)'%(Q,Q,Q),re.I)]
ANNEX_RX=re.compile("(נספח\\s+(?:[א-ת]['׳]?(?![א-ת])|\\d{1,2}(?!\\d))|(?:Annex|Appendix|Schedule|Exhibit)\\s+(?:[A-Z](?![a-z])|\\d{1,2}(?!\\d)))")
REF_RX=re.compile("(?:סעיף|סעיפים|ס['׳]|[Cc]lause|[Ss]ection)\\s+(\\d{1,3}(?:\\.\\d{1,3})*)")
def defined_terms(text):
	A=[]
	for C in DEF_PATTERNS:
		for D in C.finditer(text or''):
			B=' '.join(D.group(1).split())
			if B and B not in A:A.append(B)
	return A
def annexes(text):
	A=[]
	for C in ANNEX_RX.finditer(text or''):
		B=' '.join(C.group(1).replace('׳',"'").split())
		if B not in A:A.append(B)
	return A
def refs(text):return[A.group(1)for A in REF_RX.finditer(text or'')]
def _unquoted_uses(term,text):
	B=text;C=0
	for A in re.finditer(re.escape(term),B or''):
		D=B[max(0,A.start()-1):A.start()];E=B[A.end():A.end()+1]
		if D and D in Q and E and E in Q:continue
		C+=1
	return C
def companions(group_texts,other_texts,group_numbers=(),all_terms=()):
	E=group_numbers;A=' '.join(group_texts);C=' '.join(other_texts);B=list(defined_terms(A))
	for D in all_terms or():
		if D not in B and _unquoted_uses(D,A):B.append(D)
	F=annexes(A);H={'definitions':B,'annexes':F,'refs':sorted(set(refs(A))-set(E or()))};I=[A for A in B if not _unquoted_uses(A,C)];J=[A for A in F if A not in annexes(C)];G={str(A)for A in E or()if A};K=sorted({A for A in refs(C)if A in G or any(A.startswith(B+'.')for B in G)});L={'definitions':I,'annexes':J,'refs':K};return H,L
def sha1_of(path):
	A=path
	if not A or not os.path.isfile(A):return
	B=hashlib.sha1()
	with io.open(A,'rb')as C:B.update(C.read())
	return B.hexdigest()
def new_model(family,role,lang,files=(),research=None,template_set=()):B=research;A=files;return{'schema':SCHEMA,'family':family,'role':role,'lang':lang,'built_from':{'documents':['DOC-%d'%(A+1)for A in range(len(A))],'files':list(A),'template_set':list(template_set or()),'research':B,'research_sha1':sha1_of(B)},'built_at':date.today().isoformat(),'approved':{'at':None,'by':None,'changes':[]},'drivers':[],'clause_kinds':{},'dependent_on':{},'items':{},'open_question':None}
def open_question(lang):return{'question':OPEN_QUESTION['en'if lang=='en'else'he'],'answer':None}
def load(path):
	with io.open(path,encoding='utf-8-sig')as A:return json.load(A)
def save(path,model):
	A=os.path.dirname(os.path.abspath(path))
	if A and not os.path.isdir(A):os.makedirs(A)
	io.open(path,'w',encoding='utf-8').write(json.dumps(model,ensure_ascii=False,indent=2))
def needs_rebuild(saved,files,research_sha1,role,force=False):
	A=saved
	if force:return True,'force'
	if not A:return True,'new'
	B=set((A.get('built_from')or{}).get('files')or[]);C=set(files or[])
	if C-B:return True,'added'
	if B-C:return True,'removed'
	if(A.get('built_from')or{}).get('research_sha1')!=research_sha1:return True,'research'
	return False,'same'
def role_conflict(saved,role):A,B=(saved or{}).get('role'),role;return bool(A and B and str(A).strip().lower()!=str(B).strip().lower())
def load_answers(src):
	B=src
	if isinstance(B,dict):A=B
	elif B and os.path.isfile(B):A=load(B)
	else:A=json.loads(B or'{}')
	if isinstance(A.get('variance'),dict)and isinstance(A['variance'].get('drivers'),dict):return dict(A['variance']['drivers'])
	if isinstance(A.get('drivers'),dict):return dict(A['drivers'])
	return{A:B for(A,B)in A.items()if re.match('^D\\d+[a-z]?$',str(A))}
def by_id(model):return{A['id']:A for A in model.get('drivers')or[]}
def asked(model,answers):
	A=[]
	for B in model.get('drivers')or[]:
		C=B.get('ask_when')or{}
		if all(str(answers.get(A))==str(B)for(A,B)in C.items()):A.append(B['id'])
	return A
def _option(d,value):
	for A in d.get('options')or[]:
		if str(A.get('value'))==str(value):return A
def resolve(model,answers):
	E=model;C=answers;C=C or{};M=set(asked(E,C));D,F,G,H=[],[],{},{};I={'include':{'definitions':[],'annexes':[],'refs':[]},'omit':{'definitions':[],'annexes':[],'refs':[]}};J,K=[],[]
	for A in E.get('drivers')or[]:
		if A['id']not in M:K.append(A['id']);continue
		if A['id']not in C or C[A['id']]in(None,''):J.append(A['id']);continue
		B=(A.get('effects')or{}).get(str(C[A['id']]))or{};D+=[A for A in B.get('include')or[]if A not in D];F+=[A for A in B.get('omit')or[]if A not in F];G.update(B.get('variant')or{});H.update(B.get('data')or{});N='omit'if B.get('omit')and not B.get('include')else'include'
		for(O,P)in(B.get('companions')or{}).items():L=I[N].setdefault(O,[]);L+=[A for A in P if A not in L]
	D=[A for A in D if A not in F];return{'include':D,'omit':F,'variant':G,'data':H,'companions':I,'unanswered':J,'skipped':K,'open':bool((E.get('open_question')or{}).get('question'))and not(E.get('open_question')or{}).get('answer')}
def expected_presence(model,answers):A=resolve(model,answers);B={A:True for A in A['include']};B.update({A:False for A in A['omit']});return B
def _heading(model,item):A=(model.get('items')or{}).get(item)or{};return A.get('heading')or None
def cover_drivers(model,answers):
	E=answers;B=model;H=[];J=set(asked(B,E or{}))
	for A in B.get('drivers')or[]:
		if A['id']not in J or(E or{}).get(A['id'])in(None,''):continue
		F=E[A['id']];K=_option(A,F);C=(A.get('effects')or{}).get(str(F))or{};D=[A for A in(_heading(B,A)for A in C.get('include')or[])if A];G=[A for A in(_heading(B,A)for A in C.get('omit')or[])if A];I=[A for A in(_heading(B,A)for A in C.get('variant')or{})if A];H.append({'driver_id':A['id'],'question':A['question'],'answer':(K or{}).get('label')or str(F),'clauses_changed':D+[A for A in G if A not in D]+[A for A in I if A not in D and A not in G],'included':D,'omitted':G,'reworded':I,'companions':C.get('companions')or{}})
	return H
def segment_files(model,answers):
	B=model;G=list((B.get('built_from')or{}).get('files')or[]);H=list((B.get('built_from')or{}).get('documents')or[]);I=dict(zip(H,G));A=None
	for D in B.get('drivers')or[]:
		C=(answers or{}).get(D['id']);E=D.get('segments')or{}
		if C in(None,'')or str(C)not in E:continue
		F={I.get(A,A)for A in E[str(C)]};A=F if A is None else A&F
	return None if A is None else sorted(A)
def _lookup(obj,dotted):
	A=obj
	for B in(dotted or'').split('.'):
		if not isinstance(A,dict)or B not in A:return
		A=A[B]
	return A
def derive_answers(model,profile=None,request=None):
	H={'profile':profile or{},'request':request or{}};E={}
	for C in model.get('drivers')or[]:
		F=C.get('derivable_from');G=C.get('derivable_field')
		if not F or not G:continue
		A=_lookup(H.get(F)or{},G)
		if A in(None,''):continue
		B=C.get('expect')
		if B is None:D=bool(A)
		elif isinstance(B,list):D=A in B or str(A)in[str(A)for A in B]
		else:D=str(A).strip().lower()==str(B).strip().lower()
		E[C['id']]='yes'if D else'no'
	return E
def _norm_fact(s):return re.sub('\\s+',' ',str(s or'')).strip().strip('.?').lower()
def research_drivers(research,lang='he'):
	I=research;J=lang=='en';V=(I or{}).get('law')or[];K={}
	for(W,E)in enumerate(V):K[E.get('row',W+1)]=E
	L=[A for A in(I or{}).get('mandatory_clauses')or[]if A.get('status')!='הוסר'];M={}
	for C in L:M.setdefault(C.get('source_row'),[]).append(C)
	N,O,G={},{},{}
	for C in L:D='MAND-%s'%C.get('clause_id');O[D]={'heading':C.get('title')or C.get('requirement')or None,'type':'mandatory','source_row':C.get('source_row')};G[D]='fixed'
	for(P,E)in K.items():
		F=E.get('applies_when')or[]
		if isinstance(F,dict):F=[F]
		X=['MAND-%s'%A.get('clause_id')for A in M.get(P,[])]
		for A in F:
			if isinstance(A,str):A={'fact':A}
			H=_norm_fact(A.get('fact'))
			if not H:continue
			B=N.setdefault(H,{'cond':A,'rows':[],'mids':[]});B['rows'].append(P);B['mids']+=[A for A in X if A not in B['mids']]
	Q,R=[],{}
	for(H,B)in N.items():
		A=B['cond'];Y=(A.get('question')or'').strip()or('Does this condition apply to this deal: %s?'if J else'האם בעסקה הזו מתקיים התנאי: %s?')%str(A.get('fact')).strip().rstrip('.?');Z=str(A.get('derivable_from')or'');S,a,T=Z.partition('.');U={'id':None,'question':Y,'kind':'yes_no','options':[dict(A)for A in YES_NO['en'if J else'he']],'threshold':None,'source':'research','evidence':[{'research_row':A}for A in B['rows']],'effects':{'yes':{'include':list(B['mids']),'omit':[],'variant':{},'data':{},'companions':{'definitions':[],'annexes':[],'refs':[]}},'no':{'include':[],'omit':list(B['mids']),'variant':{},'data':{},'companions':{'definitions':[],'annexes':[],'refs':[]}}},'follow_ups':[],'priority':{'clauses':len(B['mids']),'exposure':'high'},'derivable_from':S if S in('profile','request')and T else None,'derivable_field':T or None,'expect':A.get('expect'),'condition':str(A.get('fact')).strip()};Q.append(U)
		for D in B['mids']:G[D]='dependent';R.setdefault(D,U)
	return Q,O,G,R
def number(model):
	B=model;E=B.get('drivers')or[];J={id(A):A.get('id')for A in E};G={}
	for A in E:
		D=A.get('_parent')
		if D is not None:G.setdefault(id(D),[]).append(A)
	H=lambda d:(-int((d.get('priority')or{}).get('clauses')or 0),EXPOSURE_RANK.get((d.get('priority')or{}).get('exposure'),3));C=[]
	def I(d):
		C.append(d)
		for A in sorted(G.get(id(d),[]),key=H):I(A)
	for A in sorted([A for A in E if A.get('_parent')is None],key=H):I(A)
	for(K,A)in enumerate(C,1):A['id']='D%d'%K
	for A in C:
		D=A.pop('_parent',None)
		if D is not None:A['ask_when']={D['id']:A.pop('_parent_value')}
	for A in C:A['follow_ups']=[{'when':list(B['ask_when'].values())[0],'driver':B['id']}for B in C if(B.get('ask_when')or{}).get(A['id'])is not None]
	F={}
	for(L,M)in(B.get('_dep')or{}).items():F[L]=M['id']
	B.pop('_dep',None)
	if F:B['dependent_on']=F
	B['drivers']=C;del J;return B
def _text_problems(where,s):
	A=where;B=[]
	if not s or not str(s).strip():return['%s: ריק'%A]
	if CODE_RX.search(str(s)):B.append('%s: קוד פנימי בטקסט שהלקוח רואה (%s)'%(A,CODE_RX.search(str(s)).group(0)))
	if LONG_DASH.search(str(s)):B.append('%s: קו ארוך; רק קו קצר'%A)
	return B
def validate(model,vmap=None):
	P=vmap;E=model;A=[]
	if not isinstance(E,dict):return['המודל אינו אובייקט']
	if E.get('schema')!=SCHEMA:A.append('schema אינו %s'%SCHEMA)
	for F in('family','lang','built_at'):
		if not E.get(F):A.append('חסר %s'%F)
	if E.get('lang')not in('he','en'):A.append('lang אינו he או en')
	L=E.get('built_from')
	if not isinstance(L,dict)or not isinstance(L.get('documents'),list):A.append('built_from.documents חסר');L={'documents':[]}
	J=E.get('approved')
	if not isinstance(J,dict)or'at'not in J or'by'not in J or not isinstance(J.get('changes'),list):A.append('approved חסר או חלקי ({at, by, changes})')
	elif J.get('at')and not J.get('by'):A.append('approved.at בלי approved.by')
	I=E.get('clause_kinds')or{};X=E.get('dependent_on')or{}
	for(D,F)in I.items():
		if F not in CLAUSE_KINDS:A.append('clause_kinds[%s]: סוג לא מוכר %s'%(D,F))
	Q=E.get('drivers')or[];R=[A.get('id')for A in Q]
	if len(set(R))!=len(R):A.append('מזהי שאלות כפולים')
	S=set(R);Y={}
	for C in Q:
		B=C.get('id')or'?'
		if not re.match('^D\\d+[a-z]?$',str(B)):A.append('%s: מזהה לא תקין'%B)
		A+=_text_problems('%s.question'%B,C.get('question'))
		if CLAUSE_QUESTION_RX.search(str(C.get('question')or'')):A.append('%s: השאלה היא על הוספת סעיף ולא על עובדה בעסקה'%B)
		if C.get('kind')not in KINDS:A.append('%s: kind לא מוכר'%B)
		N=C.get('options')or[];K=[str(A.get('value'))for A in N if isinstance(A,dict)]
		if len(N)<2 or len(K)!=len(N)or len(set(K))!=len(K):A.append('%s: צריך לפחות שתי תשובות שונות {value, label}'%B)
		for g in N:A+=_text_problems('%s.options'%B,(g or{}).get('label'))
		if C.get('kind')=='number_threshold'and not isinstance(C.get('threshold'),(int,float)):A.append('%s: number_threshold בלי סף מספרי'%B)
		T=C.get('source')
		if T not in SOURCES:A.append('%s: source לא מוכר'%B)
		if T!='client'and not C.get('evidence'):A.append('%s: אין ראיות (evidence)'%B)
		Z=C.get('support')or{};U=MIN_SIDE.get(T)
		if U and Z and min(int(A)for A in Z.values())<U:A.append('%s: מתחת לסף, פחות מ-%d בצד אחד של ההבחנה'%(B,U))
		a=C.get('effects')or{}
		for M in K:
			if M not in a:A.append('%s: אין השפעות לתשובה %s'%(B,M))
		for(M,G)in a.items():
			if M not in K:A.append('%s: השפעות לתשובה שאינה אפשרות (%s)'%(B,M))
			G=G or{};b=set(G.get('include')or[])&set(G.get('omit')or[])
			if b:A.append('%s: אותו סעיף נכלל ונשמט באותה תשובה (%s)'%(B,', '.join(sorted(b))))
			for H in list(G.get('include')or[])+list(G.get('omit')or[])+list((G.get('variant')or{}).keys()):
				if I.get(H)!='dependent':A.append('%s: %s בהשפעות אינו מסווג dependent'%(B,H))
				Y.setdefault(H,set()).add(B)
			for H in G.get('data')or{}:
				if I and I.get(H)not in(None,'deal_data'):A.append('%s: הנתון %s אינו deal_data'%(B,H))
			h=G.get('companions')or{}
			for F in h:
				if F not in('definitions','annexes','refs'):A.append('%s: נלווה לא מוכר %s'%(B,F))
		for c in C.get('follow_ups')or[]:
			if c.get('driver')not in S:A.append('%s: שאלת המשך לשאלה שאינה קיימת'%B)
			if str(c.get('when'))not in K:A.append('%s: שאלת המשך לתשובה שאינה אפשרות'%B)
		for(i,k)in(C.get('ask_when')or{}).items():
			if i not in S:A.append('%s: ask_when לשאלה שאינה קיימת'%B)
		d=C.get('priority')or{}
		if not isinstance(d.get('clauses'),int)or d.get('exposure')not in EXPOSURE:A.append('%s: priority חסר ({clauses, exposure})'%B)
		if C.get('derivable_from')not in(None,'profile','request'):A.append('%s: derivable_from אינו profile או request'%B)
	for(D,F)in I.items():
		if F=='dependent':
			V=X.get(D)
			if V not in S:A.append('%s: סעיף תלוי בלי שאלה מכוננת (dependent_on)'%D)
			elif V not in Y.get(D,set()):A.append('%s: השאלה %s אינה מכריעה בו'%(D,V))
	for D in X:
		if I.get(D)!='dependent':A.append('dependent_on[%s]: הפריט אינו מסווג dependent'%D)
	O=E.get('open_question');e=len(L.get('documents')or[])
	if e<2 and not L.get('template_set'):
		if not O or O.get('question')not in OPEN_QUESTION.values():A.append('פחות משני הסכמים בלי השאלה הפתוחה (פרק 6, כלל 11)')
	if O is not None and not isinstance(O,dict):A.append('open_question אינו אובייקט')
	if any(A.get('source')in('agreements','published')for A in Q)and e<2:A.append('שאלה שנלמדה מהסכמים, כשיש פחות משני הסכמים (אין שאלות מהזיכרון)')
	if P:
		f=set()
		for W in('constants','data_fields','optional_clauses','alternative_wordings'):f|={A.get('id')for A in P.get(W)or[]}
		j={A for(A,B)in(E.get('items')or{}).items()if str((B or{}).get('type')or'').startswith('template_')}
		for D in I:
			if not D.startswith('MAND-')and D not in f and D not in j:A.append('clause_kinds[%s]: אינו במפת השונות'%D)
		for W in('constants','optional_clauses','alternative_wordings'):
			for H in P.get(W)or[]:
				if H.get('id')not in I:A.append('%s מהמפה אינו מסווג ב-clause_kinds'%H.get('id'))
	return A
def _change(model,op,**A):B=dict(op=op,at=date.today().isoformat(),**A);model.setdefault('approved',{'at':None,'by':None,'changes':[]}).setdefault('changes',[]).append(B)
def approve(model,by):A=model;A['approved']['at']=date.today().isoformat();A['approved']['by']=by;return A
def rename(model,did,question):
	D=question;B=did;A=model;C=by_id(A).get(B)
	if not C:raise KeyError(B)
	_change(A,'rename',id=B,before=C['question'],after=D);C['question']=D;return A
def delete(model,did):
	B=did;A=model;D=by_id(A)
	if B not in D:raise KeyError(B)
	_change(A,'delete',id=B,question=D[B]['question']);A['drivers']=[A for A in A['drivers']if A['id']!=B]
	for(E,F)in list((A.get('dependent_on')or{}).items()):
		if F==B:del A['dependent_on'][E];A['clause_kinds'][E]='alternative'
	for C in A['drivers']:
		C['follow_ups']=[A for A in C.get('follow_ups')or[]if A.get('driver')!=B]
		if B in(C.get('ask_when')or{}):C.pop('ask_when')
	return A
def merge(model,ids,question=None):
	H=question;C=ids;B=model;I=by_id(B)
	if any(A not in I for A in C)or len(C)<2:raise KeyError(','.join(C))
	A=I[C[0]];_change(B,'merge',ids=list(C),question=H or A['question'])
	for F in C[1:]:
		J=I[F]
		for(M,G)in(J.get('effects')or{}).items():
			D=A.setdefault('effects',{}).setdefault(M,{'include':[],'omit':[],'variant':{},'data':{},'companions':{}})
			for E in('include','omit'):D[E]=D.get(E,[])+[A for A in G.get(E)or[]if A not in D.get(E,[])]
			D.setdefault('variant',{}).update(G.get('variant')or{});D.setdefault('data',{}).update(G.get('data')or{})
			for(E,N)in(G.get('companions')or{}).items():K=D.setdefault('companions',{}).setdefault(E,[]);K+=[A for A in N if A not in K]
		A['evidence']=(A.get('evidence')or[])+[B for B in J.get('evidence')or[]if B not in(A.get('evidence')or[])]
		for(O,P)in list((B.get('dependent_on')or{}).items()):
			if P==F:B['dependent_on'][O]=A['id']
		B['drivers']=[A for A in B['drivers']if A['id']!=F]
		for Q in B['drivers']:
			for L in Q.get('follow_ups')or[]:
				if L.get('driver')==F:L['driver']=A['id']
	if H:A['question']=H
	R=sum(len(set((A.get('include')or[])+(A.get('omit')or[])+list((A.get('variant')or{}).keys())))for A in A['effects'].values());A.setdefault('priority',{})['clauses']=max(int(A['priority'].get('clauses')or 0),R//max(1,len(A['effects'])));return B
def add(model,question,kind='yes_no',include=(),omit=(),lang=None):
	G=question;E=lang;D=omit;B=include;A=model;E=E or A.get('lang')or'he';J=1+max([int(re.sub('\\D','',A['id'])or 0)for A in A.get('drivers')or[]]or[0]);F='D%d'%J;K={'id':F,'question':G,'kind':kind,'options':[dict(A)for A in YES_NO['en'if E=='en'else'he']],'threshold':None,'source':'client','evidence':[],'effects':{'yes':{'include':list(B),'omit':list(D),'variant':{},'data':{},'companions':{}},'no':{'include':[],'omit':list(B),'variant':{},'data':{},'companions':{}}},'follow_ups':[],'priority':{'clauses':len(set(B)|set(D)),'exposure':'medium'},'derivable_from':None}
	for C in list(B)+list(D):
		A['clause_kinds'][C]='dependent';A.setdefault('dependent_on',{})[C]=F
		for L in A['drivers']:
			for H in(L.get('effects')or{}).values():
				for I in('include','omit'):
					if C in(H.get(I)or[]):H[I].remove(C)
	A['drivers'].append(K);_change(A,'add',id=F,question=G);return A
TEMPLATE_SET_QUESTION={'he':'איזו מהתבניות מתאימה לעסקה הזו?','en':'Which of these templates fits this deal?'}
def _clean_label(s):return re.sub('\\s+',' ',LONG_DASH.sub('-',str(s or''))).strip()
def _next_id(model):return 1+max([int(re.sub('\\D','',str(A.get('id')or''))or 0)for A in model.get('drivers')or[]]or[0])
def _origin_key(o):return json.dumps(o or{},ensure_ascii=False,sort_keys=True)
def _set_driver_for(files,registry,lang):
	D=files
	if len(D)<2:return None,None
	B={os.path.basename(A)for A in D}
	for C in(registry or{}).get('template_sets')or[]:
		J={os.path.basename(str(A))for A in C.get('templates')or[]}
		if B<=J and isinstance(C.get('driver'),dict):A=json.loads(json.dumps(C['driver']));E=[C for C in A.get('options')or[]if os.path.basename(str(((A.get('effects')or{}).get(C.get('value'))or{}).get('template')))in B];A['options']=E;A['effects']={B['value']:A['effects'][B['value']]for B in E};return A,C.get('id')
	K=lang=='en';F,G=[],{}
	for(H,I)in enumerate(sorted(B),1):F.append({'value':'t%d'%H,'label':os.path.splitext(I)[0]});G['t%d'%H]={'template':I}
	return{'question':TEMPLATE_SET_QUESTION['en'if K else'he'],'kind':'choice','options':F,'threshold':None,'source':'template','evidence':[{'doc':A}for A in sorted(B)],'effects':G,'follow_ups':[],'priority':{'clauses':len(B),'exposure':'high'},'derivable_from':None},None
def merge_template(model,skeletons,registry=None):
	e=skeletons;B=model;T=B.get('lang')or'he';M=[A for(B,A)in e];K=list(B.get('template_origins')or[])
	for E in('clause_kinds','dependent_on','items'):B.setdefault(E,{})
	N=[];F,j=_set_driver_for(M,registry,T);U=None;O={}
	if F:
		U={'kind':'template_set','set':j,'templates':sorted(os.path.basename(A)for A in M)};N.append((U,F,None,None))
		for G in F['options']:O[os.path.basename(str(F['effects'][G['value']].get('template')))]=G['value']
	for(V,k)in e:
		H=os.path.basename(k);l={str(A.get('label')):A.get('title')for A in V.get('clauses')or[]};W={}
		for I in V.get('drafter_notes')or[]:
			if isinstance(I,dict)and I.get('explains')and I.get('text')and not I.get('action_request'):W.setdefault(str(I['explains']),[]).append(_clean_label(I['text']))
		for m in V.get('template_drivers')or[]:
			A=json.loads(json.dumps(m));P={'kind':'template','template':H,'id':A.get('id')};f=re.sub('^T-','',str(A.get('id')or''))
			if W.get(f)and not A.get('help'):A['help']=' '.join(W[f])[:300]
			for G in A.get('options')or[]:G['label']=_clean_label(G.get('label'))[:80]or G.get('value')
			A['_items']={};X='%s/'%O[H]if F and O.get(H)else''
			if X:
				for C in(A.get('effects')or{}).values():
					for E in('include','omit'):
						if C.get(E):C[E]=[X+A for A in C[E]]
					if C.get('variant'):C['variant']={X+A:B for(A,B)in C['variant'].items()}
			J=next((A.get('template_clause')for A in A.get('evidence')or[]if isinstance(A,dict)),None);Q=_clean_label(l.get(str(J)))if J else'';Q=Q or(('Clause %s'if T=='en'else'סעיף %s')%J if J else None)
			for C in(A.get('effects')or{}).values():
				for D in list(C.get('include')or[])+list(C.get('omit')or[]):A['_items'][D]={'heading':Q,'type':'template_conditional','template':H,'clause':J}
				for D in C.get('variant')or{}:A['_items'][D]={'heading':Q,'type':'template_alternative','template':H,'clause':J}
			N.append((P,A,U if F else None,O.get(H)))
	g={_origin_key(B)for(B,A,A,A)in N};R=[]
	for A in list(B.get('drivers')or[]):
		if A.get('origin')and A['origin'].get('kind')in('template','template_set')and _origin_key(A['origin'])not in g:R.append(A['question']);delete(B,A['id']);B['approved']['changes'].pop()
	K=[A for A in K if A in g];Y={_origin_key(A.get('origin')):A['id']for A in B.get('drivers')or[]if A.get('origin')};S=[]
	for(P,A,Z,a)in N:
		b=_origin_key(P)
		if b in K:continue
		L='D%d'%_next_id(B);A=dict(A,id=L,origin=P);A.pop('distinguishing_clear',None);n=A.pop('_items',{});A.setdefault('follow_ups',[]);A.setdefault('derivable_from',None);A.setdefault('threshold',None)
		if Z is not None and a is not None and _origin_key(Z)in Y:h=Y[_origin_key(Z)];A['ask_when']={h:a};by_id(B)[h].setdefault('follow_ups',[]).append({'when':a,'driver':L})
		for C in(A.get('effects')or{}).values():
			for E in('include','omit'):C.setdefault(E,[])
			C.setdefault('variant',{});C.setdefault('data',{});C.setdefault('companions',{})
		B.setdefault('clause_kinds',{});B.setdefault('dependent_on',{});B.setdefault('items',{})
		for(D,c)in n.items():B['clause_kinds'][D]='dependent';B['dependent_on'].setdefault(D,L);B['items'].setdefault(D,c)
		B['drivers'].append(A);Y[b]=L;K.append(b);S.append(L)
	B['template_origins']=K;o=by_id(B);i=set()
	for A in B.get('drivers')or[]:
		if(A.get('origin')or{}).get('kind')!='template':continue
		for C in(A.get('effects')or{}).values():
			for D in list(C.get('include')or[])+list(C.get('omit')or[])+list((C.get('variant')or{}).keys()):
				i.add(D);B['clause_kinds'][D]='dependent'
				if B['dependent_on'].get(D)not in o:B['dependent_on'][D]=A['id']
	for(D,c)in list((B.get('items')or{}).items()):
		if str((c or{}).get('type')or'').startswith('template_')and D not in i:B['items'].pop(D,None);B['clause_kinds'].pop(D,None);B['dependent_on'].pop(D,None)
	d=B.setdefault('built_from',{'documents':[]});d['template_set']=sorted(set(d.get('template_set')or[])|{os.path.basename(A)for A in M})
	if len(d.get('documents')or[])<2 and not B.get('open_question'):B['open_question']=open_question(T)
	if S or R:_change(B,'template',added=S,removed=R,templates=sorted(os.path.basename(A)for A in M));B['approved']['at']=None;B['approved']['by']=None
	return{'added':S,'removed':R}
def _cli_template(a):
	D=[]
	for E in a.skeleton:
		try:F=load(E)
		except(OSError,ValueError)as B:print('skeleton.json לא נקרא: %s (%s)'%(E,B));return 2
		D.append((F,F.get('source_file')or os.path.basename(os.path.dirname(os.path.abspath(E)))))
	G=None
	if a.registry:
		try:G=load(a.registry)
		except(OSError,ValueError)as B:print('המרשם לא נקרא: %s (%s)'%(a.registry,B));return 2
	if os.path.isfile(a.drivers):
		try:A=load(a.drivers)
		except(OSError,ValueError)as B:print('drivers.json לא נקרא: %s'%B);return 2
		if a.role and role_conflict(A,a.role):print('drivers.json שבנתיב נבנה לצד אחר של המשפחה (%s). שמרו את הצד הזה בקובץ נפרד באותה תיקייה, drivers-<company_role_code>.json.'%A.get('role'));return 2
	else:H=D[0][0];I='en'if str(H.get('language')or'')[:2]=='en'else'he';A=new_model(H.get('family')or'',a.role,I);A['open_question']=open_question(I)
	C=merge_template(A,D,G);J=validate(A)
	if J:
		print('מודל השאלות לא נשמר, הוא אינו תקין אחרי הכנסת השאלות מהתבנית:')
		for K in J:print('  בעיה: '+K)
		return 1
	save(a.drivers,A);L=sum(1 for A in A['drivers']if(A.get('origin')or{}).get('kind')in('template','template_set'));print('שאלות מהתבנית במודל: %d (נוספו עכשיו: %d, יצאו: %d). נשמר: %s'%(L,len(C['added']),len(C['removed']),a.drivers))
	if C['added']or C['removed']:print('המודל השתנה: מציגים אותו ללקוח לאישור פעם אחת, יחד עם שאר השאלות, ואז drivers_lib.py approve.')
	elif(A.get('approved')or{}).get('at'):print('לא השתנה דבר, והמודל מאושר: ניגשים ישר לשאלות.')
	return 0
def main(argv=None):
	I=argparse.ArgumentParser(description='מודל השאלות המכוננות (drivers.json): בדיקה, אישור ושינויים');L=I.add_subparsers(dest='cmd',required=True)
	for D in('validate','approve','rename','merge','delete','add','resolve','cover','derive','template'):
		B=L.add_parser(D);B.add_argument('--drivers',required=True)
		if D=='template':B.add_argument('--skeleton',nargs='+',required=True,help='skeleton.json של התבנית, או של כל תבנית בערכה (build_master_template.py)');B.add_argument('--registry',help='template-registry.json: השאלה שבוחרת תבנית מתוך הערכה (template_sets)');B.add_argument('--role',help='company_role_code, כשמודל השאלות עוד לא קיים')
		if D=='validate':B.add_argument('--variance-map')
		if D=='approve':B.add_argument('--by',required=True,help='מי אישר (שם הלקוח או המשתמש)')
		if D in('rename','delete'):B.add_argument('--id',required=True)
		if D in('rename','add'):B.add_argument('--question',required=True)
		if D=='merge':B.add_argument('--ids',nargs='+',required=True);B.add_argument('--question')
		if D=='add':B.add_argument('--include',nargs='*',default=[]);B.add_argument('--omit',nargs='*',default=[])
		if D in('resolve','cover'):B.add_argument('--answers',required=True,help='answers.json ({D1: yes}) או קובץ ערכים/טיוטה עם variance.drivers')
		if D in('resolve','derive'):B.add_argument('--profile');B.add_argument('--request',help="request.json: שדות הבקשה (סוג הצד שכנגד וכו')")
	A=I.parse_args(argv)
	if A.cmd=='template':return _cli_template(A)
	try:C=load(A.drivers)
	except(OSError,ValueError)as F:print('drivers.json לא נקרא: %s'%F);return 2
	if A.cmd=='validate':
		M=load(A.variance_map)if getattr(A,'variance_map',None)else None;E=validate(C,M)
		for G in E:print('  בעיה: '+G)
		print('המודל תקין'if not E else'%d בעיות'%len(E));return 1 if E else 0
	if A.cmd in('resolve','derive','cover'):
		J=load(A.profile)if getattr(A,'profile',None)else{};K=load(A.request)if getattr(A,'request',None)else{}
		if A.cmd=='derive':print(json.dumps(derive_answers(C,J,K),ensure_ascii=False,indent=1));return 0
		H=dict(derive_answers(C,J,K));H.update(load_answers(A.answers));N=resolve(C,H)if A.cmd=='resolve'else cover_drivers(C,H);print(json.dumps(N,ensure_ascii=False,indent=1));return 0
	try:
		if A.cmd=='approve':approve(C,A.by)
		elif A.cmd=='rename':rename(C,A.id,A.question)
		elif A.cmd=='delete':delete(C,A.id)
		elif A.cmd=='merge':merge(C,A.ids,A.question)
		elif A.cmd=='add':add(C,A.question,include=A.include,omit=A.omit)
	except KeyError as F:print('אין שאלה כזו במודל: %s'%F);return 1
	E=validate(C)
	if E:
		print('השינוי לא נשמר, המודל אינו תקין אחריו:')
		for G in E:print('  בעיה: '+G)
		return 1
	save(A.drivers,C);print('נשמר: %s'%A.drivers);return 0
if __name__=='__main__':sys.exit(main())
