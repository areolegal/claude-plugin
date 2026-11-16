# -*- coding: utf-8 -*-
# Copyright (c) Areo. All rights reserved. Licensed under the terms at https://areo.co.il/legal/terms
import argparse,difflib,io,json,os,re,sys
from collections import Counter,OrderedDict
from datetime import date
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from build_template_registry import docx_paragraphs,guard_out,family_matches,normalize_role,pdf_text,word_count
from build_clause_bank import HEADING_INLINE,HEADING_SPLIT,NOT_A_HEADING,looks_like_bare_heading,topic_of
import drivers_lib as DL
try:sys.stdout.reconfigure(encoding='utf-8')
except(AttributeError,ValueError):pass
SAME=.86
DATA_SPAN=8
MAX_QUESTIONS=8
TOKEN=re.compile('[\\w\u0590-\u05ff][\\w\u0590-\u05ff\'\\"״׳.,/%\\-]*|[^\\s\\w]',re.U)
NUM=re.compile('^\\d[\\d,./%\\-]*$')
DATE=re.compile('\\d{1,2}[./-]\\d{1,2}[./-]\\d{2,4}|\\d{4}-\\d{2}-\\d{2}')
CUR=re.compile('₪|ש\\"ח|ש״ח|\\$|€|£|(?<![A-Za-z])(?:ILS|NIS|USD|EUR|GBP|CHF|JPY|CAD|AUD)(?![A-Za-z])')
PERIOD=re.compile('(?:יום|ימים|חודש|חודשים|שנה|שנים|שבוע|שבועות|day|days|month|months|year|years|week|weeks)\\b',re.I)
PCT=re.compile('%|אחוז|percent',re.I)
ORG=re.compile('בע\\"מ|בע״מ|\\(ע\\"ר\\)|\\bLtd\\b|\\bInc\\b|\\bLLC\\b|\\bGmbH\\b|\\bplc\\b|\\bLLP\\b|University|אוניברסיט|עמותה|רשות|עיריית|משרד|Council|Ministry|Authority',re.I)
STOP=set('של את על עם או גם כי אם לא כל זה זו זאת הוא היא הם הן אשר יהיה תהיה יהיו בין לבין לפי עד מן מ ב ל ה ו\nthe a an of to and or in on for by with as at be is are this that shall will may any all such from its their it\n'.split())
def tok_spans(s):
	D=[]
	for E in TOKEN.finditer(s or''):
		B,C=E.group(0),E.start();A=B.rstrip('.,;:')
		if A and A!=B and not re.match('^[א-ת]\\.[א-ת]\\.?$',B):
			D.append((A,C,C+len(A)))
			for(F,G)in enumerate(B[len(A):]):D.append((G,C+len(A)+F,C+len(A)+F+1))
		else:D.append((B,C,E.end()))
	return D
def toks(s):return[A for(A,B,B)in tok_spans(s)]
def norm_tok(t):t=t.strip('"\'״׳.,;:()').lower();return'<n>'if NUM.match(t)else t
def ratio(a,b):return difflib.SequenceMatcher(None,[norm_tok(A)for A in a],[norm_tok(A)for A in b],autojunk=False).ratio()
def kind_of(value):
	A=value or''
	if DATE.search(A):return'date'
	if CUR.search(A):return'amount'
	if re.search('\\d',A)and PCT.search(A):return'rate'
	if re.search('\\d',A)and PERIOD.search(A):return'period'
	if re.search('\\d',A):return'number'
	if ORG.search(A):return'party'
	return'text'
def amounts(text):
	A=[]
	for B in re.finditer('(?:(?:₪|\\$|€|£|ILS|NIS|USD|EUR|GBP)\\s?(\\d[\\d,]*(?:\\.\\d+)?))|(?:(\\d[\\d,]*(?:\\.\\d+)?)\\s?(?:₪|ש\\"ח|ש״ח|ILS|NIS|USD|EUR|GBP|\\$|€|£))',text):
		C=(B.group(1)or B.group(2)or'').replace(',','')
		try:A.append(float(C))
		except ValueError:pass
	return A
def split_all(paras):
	D=paras;A=[]
	for(C,F)in enumerate(D):
		E=F.strip()
		if NOT_A_HEADING.search(E):continue
		B=HEADING_INLINE.match(E)
		if B and not re.match('^\\d{1,2}\\.\\d{1,2}\\.\\d{4}',E):A.append((C,B.group(1),B.group(2).strip(' :.-'),''));continue
		B=HEADING_SPLIT.match(E)
		if B:A.append((C,B.group(1),B.group(2).strip(' :.-'),B.group(3).strip()));continue
		if looks_like_bare_heading(F)and C+1<len(D)and len(D[C+1])>40:A.append((C,None,E.rstrip('.:'),''))
	G=next((A for(A,B,C,C)in A if B),None)
	if G is not None:A=[A for A in A if A[1]or A[0]>G]
	H=[]
	for(I,(C,L,J,M))in enumerate(A):
		N=A[I+1][0]if I+1<len(A)else len(D);K=re.sub('\\s+',' ',' '.join([M]+D[C+1:N])).strip()
		if len(J)>=2 and K:H.append((L,J,K))
	return H
def unreadable(text):
	A=(text or'').strip()
	if len(A)<200:return'אין בו טקסט שאפשר לקרוא (מסמך סרוק או ריק)'
	if A.startswith('%PDF')or'\x00'in A[:2000]:return'הקובץ נקרא כבייטים ולא כטקסט'
	B=re.sub('\\s+','',A[:20000]);C=len(re.findall('[A-Za-z\\u0590-\\u05FF]',B))
	if not B or C/float(len(B))<.55:return'הטקסט שחולץ אינו קריא'
def read_paras(d):
	A=os.path.join(d.get('folder',''),d['file']);B=A.lower()
	if B.endswith('.docx'):D='base'if d.get('approved_current_basis')=='redline_base'else'final';return docx_paragraphs(A,limit=20000,mode=D),None
	if B.endswith('.pdf'):
		C,E=pdf_text(A)
		if not C.strip():return[],E or'אין בו טקסט שאפשר לקרוא (מסמך סרוק)'
		return[A.strip()for A in C.split('\n')if A.strip()],None
	if B.endswith(('.txt','.md')):return[A.strip()for A in io.open(A,encoding='utf-8',errors='ignore').read().split('\n')if A.strip()],None
	return[],'סוג קובץ שאינו נקרא (%s)'%(os.path.splitext(A)[1]or'בלי סיומת')
HEAD_PREFIX=re.compile('^(?:[\\u05d0-\\u05ea]|[A-Za-z]|\\d{1,3})[.)]\\s*(?=\\S)')
SIGN_START=re.compile('^\\s*(?:IN\\s+WITNESS|ולראי{1,2}ה|ובאו\\s+הצדדים\\s+על\\s+החתום)',re.I)
def read_doc(d,paras=None):
	A=paras
	if A is None:A,K=read_paras(d)
	H=next((A for(A,B)in enumerate(A)if A>3 and SIGN_START.match(B)),None);A=A[:H]if H else A;C=[(B,HEAD_PREFIX.sub('',A).strip()or A,C)for(B,A,C)in split_all(A)];E=None
	for(L,M)in enumerate(A):
		if C and C[0][1]and C[0][1]in M:E=L;break
	N=A[:E]if E else A[:6];B=OrderedDict()
	for(I,F,G)in C:
		J,K=topic_of(F,G);D=J or'כותרת: '+re.sub('\\s+',' ',F.strip().lower())
		if D in B:B[D]['text']+=' '+G;B[D]['numbers'].append(I)
		else:B[D]={'topic':J,'heading':F.strip(),'numbers':[I],'text':G}
	return{'title':A[0]if A else'','preamble':' '.join(N),'clauses':B,'text':' '.join(A)}
def data_spans(ref,other):
	C,D=toks(ref),toks(other);K=difflib.SequenceMatcher(None,[norm_tok(A)for A in C],[norm_tok(A)for A in D],autojunk=False);F,I=[],False
	for(L,A,G,E,J)in K.get_opcodes():
		if L=='equal':
			for B in range(G-A):
				if C[A+B]!=D[E+B]and NUM.match(C[A+B].strip('"\'.,;:()')):H=' '.join(C[max(0,A+B-4):A+B]);F.append((H,C[A+B],D[E+B],A+B))
			continue
		if max(G-A,J-E)>DATA_SPAN:I=True;continue
		H=' '.join(C[max(0,A-4):A]);F.append((H,' '.join(C[A:G]),' '.join(D[E:J]),A))
	return F,I
def template_of(ref,spans_at):
	D=ref;A=tok_spans(D);B,C=[],0
	for(E,G,H)in sorted(spans_at):
		if E>=len(A):continue
		F,I=A[E][1],A[min(len(A),E+max(1,G))-1][2]
		if F<C:continue
		B.append(D[C:F]);B.append('{{%s}}'%H);C=I
	B.append(D[C:]);return''.join(B)
def words_of(s):return{A for A in(norm_tok(A)for A in toks(s))if len(A)>2 and A not in STOP and A!='<n>'}
def body_words(doc,exclude=()):
	A=Counter()
	for(B,C)in doc['clauses'].items():
		if B in exclude:continue
		A.update(A for A in(norm_tok(A)for A in toks(C['text']))if len(A)>2 and A not in STOP and A!='<n>')
	return A
def signals(ids,yes,no,docs,fields,exclude=()):
	C=no;B=yes;A=docs;D=[]
	if not B or not C:return D
	B,C=list(B),list(C)
	for(W,P)in(('כותרת','title'),('מבוא','preamble')):
		I=[words_of(A[B][P])for B in B];J=[words_of(A[B][P])for B in C];Q=set.intersection(*I)-set.union(*J)if len(I)>1 and J else set();R=set.intersection(*J)-set.union(*I)if len(J)>1 and I else set()
		if Q or R:D.append({'kind':W,'with':sorted(Q)[:6],'without':sorted(R)[:6]})
	for E in fields:
		if E.get('per_deal')or E.get('type')not in('amount','rate','period','number')or not E.get('by_doc'):continue
		K={E['by_doc'].get(A)for A in B}-{None,''};L={E['by_doc'].get(A)for A in C}-{None,''}
		if K and L and not K&L:D.append({'kind':'שדה','field':E['id'],'context':E['context'],'with':sorted(K)[:4],'without':sorted(L)[:4]})
	G=[max(amounts(A[B]['text'])or[0])for B in B];H=[max(amounts(A[B]['text'])or[0])for B in C]
	if len([A for A in G if A])>1 and len([A for A in H if A])>1 and(min(G)>max(H)or max(G)<min(H)):D.append({'kind':'טווח סכומים','with':[min(G),max(G)],'without':[min(H),max(H)]})
	M={bool(ORG.search(A[B]['preamble']))for B in B};N={bool(ORG.search(A[B]['preamble']))for B in C}
	if len(M)==1 and len(N)==1 and M!=N:D.append({'kind':'סוג הצד שכנגד','with':['תאגיד או גוף'if True in M else'אדם פרטי'],'without':['תאגיד או גוף'if True in N else'אדם פרטי']})
	X={B for A in D if A['kind']in('כותרת','מבוא')for B in A['with']+A['without']};F={}
	for(S,T,Y)in(('with',B,C),('without',C,B)):
		if len(T)<2:F[S]=[];continue
		U=[body_words(A[B],exclude)for B in T];V=set()
		for O in Y:V|=words_of(A[O]['text'])|words_of(A[O]['title'])|words_of(A[O]['preamble'])
		Z=set.intersection(*[set(A)for A in U])-V-X;F[S]=sorted(Z,key=lambda w:(-sum(A[w]for A in U),-len(w),w))[:6]
	if F['with']or F['without']:D.append({'kind':'מונח בגוף','with':F['with'],'without':F['without']})
	return D
SOURCE_WORDS={'he':{'company':'בהסכמים שלכם','third_party':'בנוסחים שנמצאו','published':'בהסכמים שפורסמו'},'en':{'company':'in your agreements','third_party':'in the forms we found','published':'in the published agreements'}}
SOURCE=['company']
SIGNAL_ORDER={'סוג הצד שכנגד':0,'טווח סכומים':1,'שדה':2,'כותרת':3,'מבוא':4,'מונח בגוף':5}
def signal_phrase(sig,lang):
	C=sig;B=lang=='en';C=[A for A in C or[]if A.get('with')and A.get('kind')in SIGNAL_ORDER]
	if not C:return''
	A=sorted(C,key=lambda x:SIGNAL_ORDER[x['kind']])[0]
	if A['kind']in('כותרת','מבוא','מונח בגוף'):F=A['with'][0];return{'כותרת':' Usually when the title says "%s".'if B else' בדרך כלל כשבכותרת מופיע "%s".','מבוא':' Usually when the opening says "%s".'if B else' בדרך כלל כשבמבוא מופיע "%s".','מונח בגוף':' Usually when the agreement deals with "%s".'if B else' בדרך כלל כשההסכם עוסק ב"%s".'}[A['kind']]%F
	if A['kind']=='שדה':return(' Usually when %s is %s.'if B else' בדרך כלל כש%s הוא %s.')%(A['context']or('the value'if B else'הערך'),' / '.join(str(A)for A in A['with']))
	if A['kind']=='טווח סכומים':
		E,D='{:,.0f}'.format(A['with'][0]),'{:,.0f}'.format(A['with'][1])
		if E==D:return(' Usually when the amounts reach %s.'if B else' בדרך כלל כשהסכומים מגיעים ל-%s.')%D
		return(' Usually for amounts of %s to %s.'if B else' בדרך כלל בסכומים של %s עד %s.')%(E,D)
	return(' Usually when the other side is %s.'if B else' בדרך כלל כשהצד השני הוא %s.')%' / '.join(A['with'][:2])
def build(docs_meta,docs,profile,skeleton=None,defaults=None):
	f=docs_meta;Z=profile;A=docs;g='en'if sum(1 for A in f if(A.get('language')or'')[:2]=='en')>len(f)/2 else'he';O=list(range(len(A)));L=lambda i:'DOC-%d'%(i+1);h=OrderedDict()
	for(B,q)in enumerate(A):
		for C in q['clauses']:h.setdefault(C,[]).append(B)
	a,J,S,T=[],[],[],[];M=[0]
	def i(topic,heading,ctx,by_doc,refs):A=by_doc;A={B:A.strip(' ,;:.')if A.strip(' ,;:.')else A for(B,A)in A.items()};M[0]+=1;B=Counter(A for A in A.values());C={'id':'F%d'%M[0],'topic':topic,'heading':heading,'context':ctx.strip(),'type':kind_of(next(iter(A.values()),'')),'values':[{'value':B,'count':C,'documents':[L(A)for(A,C)in A.items()if C==B]}for(B,C)in B.most_common()],'default':B.most_common(1)[0][0]if B and B.most_common(1)[0][1]>1 else None,'per_deal':not B or B.most_common(1)[0][1]==1,'by_doc':A,'refs':refs};J.append(C);return C
	def P(k,members):return[{'doc':L(B),'clause':', '.join(A for A in A[B]['clauses'][k]['numbers']if A)or None}for B in members]
	b=max(O,key=lambda i:len(A[i]['preamble']));j={}
	for B in O:
		if B==b:continue
		c,v=data_spans(A[b]['preamble'],A[B]['preamble'])
		for(K,E,d,N)in c:j.setdefault((N,K,E),{b:E})[B]=d
	for((N,K,E),G)in sorted(j.items()):
		for B in O:G.setdefault(B,E)
		if len(set(G.values()))>1:i('מבוא','המבוא והצדדים'if g=='he'else'Preamble and parties',K,G,[{'doc':L(A),'clause':None}for A in G])
	for(C,D)in h.items():
		k=A[D[0]]['clauses'][C];U,V=k['topic'],k['heading'];W=max(D,key=lambda i:sum(ratio(toks(A[i]['clauses'][C]['text']),toks(A[B]['clauses'][C]['text']))for B in D));X=A[W]['clauses'][C]['text'];I=[[W]]
		for B in D:
			if B==W:continue
			for Q in I:
				if ratio(toks(A[Q[0]]['clauses'][C]['text']),toks(A[B]['clauses'][C]['text']))>=SAME:Q.append(B);break
			else:I.append([B])
		l,m={},[]
		for B in I[0][1:]:
			c,w=data_spans(X,A[B]['clauses'][C]['text'])
			for(K,E,d,N)in c:l.setdefault((N,K,E),{W:E})[B]=d
		n=[]
		for((N,K,E),G)in sorted(l.items()):
			for B in I[0]:G.setdefault(B,E)
			if len(set(G.values()))>1:R=i(U,V,K,G,P(C,list(G)));m.append(R);n.append((N,len(toks(E))or 1,R['id']))
		e=[{'variant':'V%d'%(D+1),'documents':[L(A)for A in B],'text':A[B[0]]['clauses'][C]['text'],'refs':P(C,B)}for(D,B)in enumerate(I)]
		if len(D)==len(A)and len(I)==1:a.append({'id':'C%d'%(len(a)+1),'topic':U,'heading':V,'text':X,'text_template':template_of(X,n),'fields':[A['id']for A in m],'refs':P(C,D)});continue
		if len(D)<len(A):o,p=D,[A for A in O if A not in D];S.append({'id':'O%d'%(len(S)+1),'topic':U,'heading':V,'with':[L(A)for A in o],'without':[L(A)for A in p],'signals':[],'_yes':o,'_no':p,'_key':C,'wording':X,'variants':e if len(I)>1 else[],'refs':P(C,D)})
		else:
			for(F,Q)in zip(e,I):F['_yes'],F['_no']=Q,[A for A in D if A not in Q]
			T.append({'id':'A%d'%(len(T)+1),'topic':U,'heading':V,'variants':e,'refs':P(C,D),'_key':C})
	for(Y,r)in[(A,A['_key'])for A in S]+[(B,A['_key'])for A in T for B in A['variants']]:
		if'_yes'in Y:Y['signals']=signals(O,Y['_yes'],Y['_no'],A,J,exclude=(r,))
	s=[{str(A['value']).replace(',','')for A in A['values']}for A in J]
	for H in defaults or[]:
		t={str(A['value']).split()[0].replace(',','')for A in H.get('distribution')or[]}
		if any(t<=A for A in s):continue
		if H.get('value')is not None and len(H.get('distribution')or[])>1:M[0]+=1;J.append({'id':'F%d'%M[0],'topic':None,'heading':H['parameter'],'context':H.get('question'),'type':kind_of(str(H['value'])),'source':'derive_deal_defaults','values':[{'value':A['value'],'count':A['documents']}for A in H['distribution']],'default':H['value'],'by_doc':{},'refs':[{'doc':None,'file':H.get('source_file')}]})
	for F in(skeleton or{}).get('variables')or[]:M[0]+=1;J.append({'id':'F%d'%M[0],'topic':None,'heading':F.get('label')or F.get('id'),'context':F.get('id'),'type':F.get('type')or'text','source':'skeleton','values':[{'value':F.get('found_value'),'count':1}]if F.get('found_value')else[],'default':F.get('found_value'),'by_doc':{},'refs':[]})
	u={str(A).strip()for A in((Z or{}).get('organization_name'),(Z or{}).get('organization_name_en'),(Z or{}).get('registration_number'))if A}
	for R in J:
		if any(any(A and A in str(B['value'])for A in u)for B in R['values']):R['derivable_from']='profile'
	return g,a,J,S,T
EXPOSURE_TOPICS={'אחריות והגבלתה','שיפוי','ביטוח','ערבויות וביטחונות','אי תחרות ואי שידול','הגנת הפרטיות ואבטחת מידע','קניין רוחני ומותג','הפרה, סעדים ותרופות'}
PART_WORDS={'he':{'company':'חלק מההסכמים שלכם','third_party':'חלק מהנוסחים שנמצאו','published':'חלק מההסכמים שפורסמו'},'en':{'company':'some of your agreements','third_party':'some of the forms we found','published':'some of the published agreements'}}
PARTY_KIND={'תאגיד או גוף':('a company or other body','תאגיד או גוף',['תאגיד','גוף ציבורי','צד זר','company','corporation','body','public body']),'אדם פרטי':('an individual','אדם פרטי',['יחיד','אדם פרטי','individual','person'])}
def _nice(x):return int(float('%.2g'%x))if x>=10 else int(round(x))
def _run_phrase(text,words):
	C=words;A,B=[],[]
	for D in toks(text):
		if norm_tok(D)in C:B.append(D.strip('"\'״׳.,;:()'))
		else:A,B=max(A,B,key=len),[]
	A=max(A,B,key=len);return' '.join(A[:4])or sorted(C)[0]
def item_name(it,n_docs=2):
	A=it;B=clean_heading({'heading':A.get('heading'),'topic':A.get('topic'),'with':A.get('with')or[0]*n_docs})
	if B:return B
	if A.get('topic')and A['topic']!='שונות':return A['topic']
	C=re.findall('[A-Za-zא-ת][A-Za-zא-ת\'\\"״׳\\-]*',A.get('heading')or'');return' '.join(C[:5])or None
def _join(names,en):
	A=names;A=[A for A in A if A]
	if len(A)<=1:return''.join(A)
	return', '.join(A[:-1])+(' and 'if en else' ו-')+A[-1]
def fact_question(sigs,lang,part,docs,side_docs,fields):
	H=side_docs;B=lang=='en';O=[dict(A)for A in DL.YES_NO['en'if B else'he']];P=sorted([A for A in sigs or[]if A.get('kind')in SIGNAL_ORDER and(A.get('with')or A.get('without'))],key=lambda x:SIGNAL_ORDER[x['kind']]);Q={A['id']:A for A in fields}
	for A in P:
		C=A['kind'];D={'kind':'yes_no','options':O,'threshold':None,'with_value':'yes','without_value':'no','derivable_from':None,'derivable_field':None,'expect':None,'signal':A}
		if C=='סוג הצד שכנגד'and A.get('with')and A['with'][0]in PARTY_KIND:R,S,T=PARTY_KIND[A['with'][0]];return dict(D,question=('Is the other party in this deal %s?'if B else'הצד השני בעסקה הזו הוא %s?')%(R if B else S),derivable_from='request',derivable_field='counterparty_type',expect=T)
		if C=='טווח סכומים'and A.get('with')and A.get('without'):(I,U),(V,J)=A['with'],A['without'];E=I>J;W,X=(J,I)if E else(U,V);K=_nice((W+X)/2.);F='{:,.0f}'.format(K);return dict(D,kind='number_threshold',threshold=K,question=('Is the amount in this deal above %s?'if B else'הסכום בעסקה הזו עולה על %s?')%F,options=[{'value':'above','label':('Above %s'if B else'מעל %s')%F},{'value':'below','label':('Up to %s'if B else'עד %s')%F}],with_value='above'if E else'below',without_value='below'if E else'above')
		if C=='שדה'and A.get('with')and A.get('without'):
			Y=Q.get(A.get('field'))or{}
			if not askable_field(Y):continue
			Z=' '.join((A.get('context')or'').split());return dict(D,kind='choice',question=('Which applies to this deal: "%s ..."?'if B else'מה נכון לעסקה הזו: "%s ..."?')%Z,options=[{'value':'yes','label':' / '.join(str(A)for A in A['with'])},{'value':'no','label':' / '.join(str(A)for A in A['without'])}])
		if C in('כותרת','מבוא','מונח בגוף'):
			L=A.get('with')or A.get('without');G=not A.get('with');M={'כותרת':'title','מבוא':'preamble'}.get(C);a=H[1]if G else H[0]
			if M:N=_run_phrase(docs[a[0]][M],set(L))
			else:N=L[0]
			b={'כותרת':('Does "%s" describe this deal, as in the title of %s?','האם "%s" מתאר את העסקה הזו, כמו בכותרת של %s?'),'מבוא':('Does "%s" describe this deal, as in the opening of %s?','האם "%s" מתאר את העסקה הזו, כמו במבוא של %s?'),'מונח בגוף':('Does this deal involve "%s", as in %s?','האם העסקה הזו כוללת "%s", כמו %s?')}[C];return dict(D,question=b[0 if B else 1]%(N,part),with_value='no'if G else'yes',without_value='yes'if G else'no')
def group_question(units,lang,part,n_docs):
	F=part;E=units;A=lang=='en';J=[dict(A)for A in DL.YES_NO['en'if A else'he']];H=[A for(A,B)in E if A['type']=='O'];B=[]
	for K in H or[A for(A,B)in E]:
		G=item_name(K['obj'],n_docs)
		if G and G not in B:B.append(G)
	I={'kind':'yes_no','options':J,'threshold':None,'with_value':'yes','without_value':'no','derivable_from':None,'derivable_field':None,'expect':None,'signal':None}
	if H:
		if len(B)>1:C=('In %s, the clauses on %s appear together. Are they relevant to this deal?'if A else'ב%s מופיעים יחד הסעיפים %s. הם רלוונטיים לעסקה הזו?')%(F,_join(B,A))
		else:C=('In %s, the clause on %s appears. Is it relevant to this deal?'if A else'ב%s מופיע הסעיף %s. הוא רלוונטי לעסקה הזו?')%(F,B[0]if B else'this topic'if A else'בנושא הזה')
		return dict(I,question=C)
	D,L=E[0];M,N=(D['obj']['variants'][0],D['obj']['variants'][1])if L else(D['obj']['variants'][1],D['obj']['variants'][0]);C=('In %s, the clauses on %s are worded differently. Which wording fits this deal?'if A else'ב%s הסעיפים %s מנוסחים אחרת. איזה נוסח מתאים לעסקה הזו?')%(F,_join(B,A));return dict(I,kind='choice',question=C,options=[{'value':'yes','label':'"%s"'%excerpt(M['text'],60)},{'value':'no','label':'"%s"'%excerpt(N['text'],60)}])
def _independent(idx,metas):
	from urllib.parse import urlparse as D;B=set()
	for C in idx:A=metas[C];B.add(str(A.get('publisher')or D(A.get('url')or'').hostname or A.get('file')or C).lower())
	return len(B)
def find_drivers(docs,metas,fields,optional,alternatives,lang,source):
	a=source;U=lang;M=fields;F=docs;b=len(F);V=list(range(b));d=frozenset(V);c=a=='published';W=DL.MIN_SIDE['published'if c else'agreements'];N=(lambda s:_independent(s,metas))if c else len;z=1 if b>=6 else 0;e=PART_WORDS['en'if U=='en'else'he'][a if a in PART_WORDS['he']else'company'];k=[{'item':A['id'],'type':'O','yes':frozenset(A['_yes']),'key':A['_key'],'obj':A}for A in optional]
	for J in alternatives:
		if len(J['variants'])==2 and'_yes'in J['variants'][0]:k.append({'item':J['id'],'type':'A','yes':frozenset(J['variants'][0]['_yes']),'no':frozenset(J['variants'][1]['_yes']),'key':J['_key'],'obj':J})
	l=lambda x,y:len(x^y)<=z;C=[]
	for B in sorted(k,key=lambda u:(u['type']!='O',-len(u['yes']))):
		for A in C:
			if l(B['yes'],A['yes']):A['units'].append((B,True));break
			if B['type']=='A'and l(B['no'],A['yes']):A['units'].append((B,False));break
		else:C.append({'yes':B['yes'],'units':[(B,True)]})
	f=lambda c:tuple(A['key']for(A,B)in c['units'])
	def y(c):
		B=set()
		for A in signals(V,c['yes'],d-c['yes'],F,M,exclude=f(c)):
			if A['kind']in('כותרת','מבוא','מונח בגוף'):B|={('with',A['kind'],B)for B in A['with']}|{('without',A['kind'],B)for B in A['without']}
			elif A['kind']=='שדה':B.add(('field',A['field'],tuple(A['with']),tuple(A['without'])))
		return B
	X=True
	while X:
		X=False;m=[y(A)for A in C]
		for g in range(len(C)):
			for h in range(g+1,len(C)):
				if m[g]&m[h]:C[g]['units']+=C[h]['units'];del C[h];X=True;break
			if X:break
	for A in C:D,K=A['yes'],d-A['yes'];A['ok']=N(D)>=W and N(K)>=W;A['sig']=signals(V,D,K,F,M,exclude=f(A))if A['ok']else[];A['fact']=fact_question(A['sig'],U,e,F,(sorted(D),sorted(K)),M)if A['ok']else None;A['driver']=A['ok']and(bool(A['fact'])or len(A['units'])>=2);A['parent']=None
	for A in C:
		if any(A['type']!='O'or not B for(A,B)in A['units']):continue
		n=[B for B in C if B is not A and B['driver']and A['yes']<B['yes']and N(A['yes'])>=W and N(B['yes']-A['yes'])>=W]
		if n:A['parent']=min(n,key=lambda p:len(p['yes']));A['driver']=True
	o,p=[],{}
	for A in[A for A in C if A['driver']]:
		D,K=A['yes'],d-A['yes']
		if A['parent']is not None:q=A['parent']['yes']-D;A['sig']=signals(V,D,q,F,M,exclude=f(A));A['fact']=fact_question(A['sig'],U,e,F,(sorted(D),sorted(q)),M)
		E=A['fact']or group_question(A['units'],U,e,b);G,H=E['with_value'],E['without_value'];I={A:{'include':[],'omit':[],'variant':{},'data':{},'companions':{'definitions':[],'annexes':[],'refs':[]}}for A in(G,H)}
		for(B,Y)in A['units']:
			if B['type']=='O':I[G if Y else H]['include'].append(B['item']);I[H if Y else G]['omit'].append(B['item'])
			else:r,s=B['obj']['variants'][0]['variant'],B['obj']['variants'][1]['variant'];I[G]['variant'][B['item']]=r if Y else s;I[H]['variant'][B['item']]=s if Y else r
		for Z in M:
			P=Z.get('by_doc')or{}
			if Z.get('per_deal')or not P or not askable_field(Z):continue
			i=Counter(P[A]for A in D if A in P);j=Counter(P[A]for A in K if A in P)
			if i and j and i.most_common(1)[0][0]!=j.most_common(1)[0][0]:
				for(Q,A0)in((G,i),(H,j)):A1,A2=A0.most_common(1)[0];I[Q]['data'][Z['id']]=A1 if A2>=2 else None
		R=[A['key']for(A,B)in A['units']if A['type']=='O']
		if R:
			A3=sorted(D);t=max(A3,key=lambda i:sum(1 for A in R if A in F[i]['clauses']));S=F[t]['clauses'];A4=[S[A]['text']for A in R if A in S];A5=[B['text']for(A,B)in S.items()if A not in R];A6=[B for A in R if A in S for B in S[A]['numbers']if B];T=[]
			for O in F:
				for A7 in O['clauses'].values():T+=[A for A in DL.defined_terms(A7['text'])if A not in T]
				T+=[A for A in DL.defined_terms(O['preamble'])if A not in T]
			A8,A9=DL.companions(A4,A5+[F[t]['preamble']],A6,T);u=all(B for(A,B)in A['units']if A['type']=='O');I[G if u else H]['companions']=A8;I[H if u else G]['companions']=A9
		AA=' '.join(A['obj'].get('wording')or' '.join(A['text']for A in A['obj'].get('variants')or[])for(A,B)in A['units']);AB={A['obj'].get('topic')for(A,B)in A['units']};AC='high'if AB&EXPOSURE_TOPICS or CUR.search(AA)else'medium'if len(A['units'])>=2 else'low';v=[]
		for(B,_)in A['units']:
			for w in B['obj'].get('refs')or[]:v.append({'doc':w['doc'],'clause':w.get('clause'),'item':B['item']})
		O={'id':None,'question':E['question'],'kind':E['kind'],'options':E['options'],'threshold':E['threshold'],'source':'published'if c else'agreements','evidence':v,'effects':I,'follow_ups':[],'priority':{'clauses':len(A['units']),'exposure':AC},'derivable_from':E['derivable_from'],'derivable_field':E['derivable_field'],'expect':E['expect'],'signal':{'kind':E['signal']['kind'],'with':E['signal'].get('with'),'without':E['signal'].get('without')}if E.get('signal')else None,'segments':{G:['DOC-%d'%(A+1)for A in sorted(D)],H:['DOC-%d'%(A+1)for A in sorted(K if A['parent']is None else A['parent']['yes']-D)]},'support':{G:N(D),H:N(K if A['parent']is None else A['parent']['yes']-D)}};A['obj']=O;o.append(O)
		for(B,_)in A['units']:p[B['item']]=O
	for A in[A for A in C if A['driver']and A['parent']is not None]:
		L=A['parent']['obj'];x=next(B for B in L['segments']if set(L['segments'][B])=={'DOC-%d'%(A+1)for A in A['parent']['yes']});A['obj']['_parent'],A['obj']['_parent_value']=L,x
		for Q in L['effects']:
			if Q!=x:L['effects'][Q]['omit']+=[A['item']for(A,B)in A['units']if A['item']not in L['effects'][Q]['omit']]
		L['priority']['clauses']+=len(A['units'])
	return o,p
def excerpt(t,n=70):t=re.sub('\\s+',' ',t or'').strip();return t if len(t)<=n else t[:n].rsplit(' ',1)[0]+'...'
COUNT_WORDS={'he':{'company':'ההסכמים שלכם','third_party':'הנוסחים שנמצאו','published':'ההסכמים שפורסמו'},'en':{'company':'of your agreements','third_party':'of the forms we found','published':'of the published agreements'}}
YES_NO={'he':('כן, להוסיף','לא, בלי הסעיף'),'en':('Yes, add it','No, leave it out')}
CORE_SHARE=.6
END_WORDS=set('של על את לפני אחרי עם או ו כי אם כגון לרבות לפי בין the of to and or in on for by with a an such including'.split())
HEADING_OK=re.compile("^[A-Za-z\\u05d0-\\u05ea][A-Za-z\\u05d0-\\u05ea ,'\\-&]*$")
def _bare(w):w=w.strip(".,:;'").lower();return w[1:]if len(w)>3 and w[0]=='ה'else w
def clean_heading(o):
	A=' '.join(str(o.get('heading')or'').split()).strip(' :.-')
	if not A or not HEADING_OK.match(A):return
	C=A.split();B=C[0]
	if len(C)>5 or len(B)<3 or B[0]=='ו'and len(B)>3 and not B.startswith('ו/')or C[-1].strip('.,:;').lower()in END_WORDS or B.endswith(','):return
	D=bool(o.get('topic'))and o['topic']!='שונות'
	if len(C)==1:
		if D and A.isascii()and len(A)>=6:return A
		if not(D and _bare(A)in{_bare(A)for A in re.split('[\\s,]+',o['topic'])}):return
		return A
	if D:return A
	return A if len(A)>=8 and len(o['with'])>=2 else None
def askable_field(f):
	if f.get('derivable_from')or f.get('topic')=='מבוא'or f.get('heading')in('המבוא והצדדים','Preamble and parties'):return False
	A=' '.join((f.get('context')or f.get('heading')or'').split());B=re.findall('[A-Za-zא-ת]{3,}',A);return len(B)>=2 and not re.search('[_@()\\"]',A)
def driver_questions(model):
	D=model;B=[]
	for A in(D or{}).get('drivers')or[]:B.append({'id':'Q-'+A['id'],'about':A['id'],'kind':'driver','text':A['question'],'options':[A['label']for A in A['options']],'option_values':[A['value']for A in A['options']],'ask_when':A.get('ask_when'),'derivable_from':A.get('derivable_from'),'derivable_field':A.get('derivable_field'),'source':A.get('source')})
	C=(D or{}).get('open_question')
	if C and C.get('question'):B.append({'id':'Q-open','about':'open_question','kind':'open','text':C['question'],'options':[],'free_text':True})
	return B
def questions(lang,fields,optional,alternatives,model=None):
	P=model;O=fields;K=optional;J=lang;E=J=='en';Q='en'if E else'he';G,R=YES_NO[Q];b=max([len(A['with'])+len(A['without'])for A in K]or[0]);S=COUNT_WORDS[Q][SOURCE[0]];F,T=[],[];L=set(((P or{}).get('dependent_on')or{}).keys())
	for A in sorted([A for A in K if not A.get('playbook_topic')and A['id']not in L],key=lambda x:-len(x['with'])):
		H=len(A['with'])+len(A['without']);A['core']=H>=3 and len(A['with'])/float(H)>=CORE_SHARE;I=clean_heading(A);A['askable']=bool(I)
		if not I:continue
		if A['core']:T.append((A,I,H));continue
		U=A['signals'];F.append({'id':'Q-'+A['id'],'about':A['id'],'kind':'optional','text':('Add a clause on %s? It appears in %d of %d %s.%s'if E else'להוסיף סעיף בנושא %s? מופיע ב-%d מתוך %d %s.%s')%(I,len(A['with']),H,S,signal_phrase(U,J)),'options':[G,R],'default':G if len(A['with'])>=len(A['without'])else R})
	for B in[A for A in alternatives if A['id']not in L]:
		if not clean_heading({'heading':B.get('heading'),'topic':B.get('topic'),'with':[B for A in B['variants']for B in A['documents']]}):B['askable']=False;continue
		M=[re.sub('\\s+',' ',A['text']).split(' ')for A in B['variants']];C=0
		while all(len(A)>C for A in M)and len({A[C]for A in M})==1:C+=1
		C=max(0,C-3)
		for(V,W)in zip(B['variants'],M):V['_from']=('...'if C else'')+' '.join(W[C:])
		F.append({'id':'Q-'+B['id'],'about':B['id'],'kind':'alternative','text':('Which wording do you want for the clause on %s?'if E else'איזה נוסח אתם רוצים לסעיף בנושא %s?')%B['heading'],'options':['"%s"%s'%(excerpt(A.pop('_from',A['text'])),signal_phrase(A.get('signals')or[],J))for A in B['variants']],'option_values':[A['variant']for A in B['variants']],'default':max(B['variants'],key=lambda v:len(v['documents']))['variant']})
	X=[A for A in O if askable_field(A)and A.get('per_deal')];Y=[A for A in O if askable_field(A)and not A.get('per_deal')]
	for D in X+Y:Z=' '.join((D.get('context')or D.get('heading')or'').split());F.append({'id':'Q-'+D['id'],'about':D['id'],'kind':'data','text':('What goes in the agreement for: %s?'if E else'מה לרשום בהסכם הזה: %s?')%Z,'options':[]if D.get('per_deal')else[A['value']for A in D['values'][:4]if A['value']],'free_text':True,'default':D.get('default')})
	a,N=driver_questions(P)+F[:MAX_QUESTIONS],F[MAX_QUESTIONS:];N+=[{'id':'Q-'+A['id'],'about':A['id'],'kind':'optional','status':'playbook_topic','text':('%s: included, you already have a position on it'if E else'%s: נכלל, כבר יש לכם עמדה בנושא')%A['heading'],'default':G}for A in K if A.get('playbook_topic')and A['id']not in L];N+=[{'id':'Q-'+A['id'],'about':A['id'],'kind':'optional','status':'core_included','text':('%s: included, it appears in %d of %d %s'if E else'%s: נכלל, מופיע ב-%d מתוך %d %s')%(B,len(A['with']),C,S),'default':G}for(A,B,C)in T];return a,[dict(A,status=A.get('status')or('default_for_approval'if A.get('default')not in(None,'')else'to_complete'))for A in N]
def build_model(family,role,lang,files,research_path,research,docs=None,metas=None,fields=(),optional=(),alternatives=(),constants=(),source='company'):
	N=alternatives;M=optional;L=fields;K=research;F=docs;E=lang;A=DL.new_model(family,role,E,files,research_path);O,P=[],{}
	if F and len(F)>=2:O,P=find_drivers(F,metas,list(L),list(M),list(N),E,source)
	Q,R,S,T=DL.research_drivers(K,E)if K else([],{},{},{});A['drivers']=O+Q;A['_dep']=dict(P);A['_dep'].update(T);DL.number(A);B=len(F or[]);C,D={},{}
	for I in constants:C[I['id']]='fixed';D[I['id']]={'heading':item_name(dict(I,**{'with':[0]*B}),B),'type':'constant'}
	for J in L:C[J['id']]='deal_data';D[J['id']]={'heading':J.get('heading'),'type':'field'}
	for G in M:C[G['id']]='dependent'if G['id']in A['dependent_on']else'alternative';D[G['id']]={'heading':item_name(G,B),'type':'optional'}
	for H in N:C[H['id']]='dependent'if H['id']in A['dependent_on']else'alternative';D[H['id']]={'heading':item_name(dict(H,**{'with':[0]*B}),B),'type':'alternative'}
	C.update(S);D.update(R);A['clause_kinds'],A['items']=C,D
	if B<2:A['open_question']=DL.open_question(E)
	return A
def main():
	E=argparse.ArgumentParser(description='מפת השונות בין ההסכמים הקיימים של החברה מאותו סוג ובאותו צד');E.add_argument('--registry',required=True,help='template-registry.json');E.add_argument('--family',required=True,nargs='+',help='משפחת ההסכם: family_id של הפלייבוק, שם המשפחה במרשם, או שם או כינוי שלה (אפשר כמה)');E.add_argument('--playbook',help='playbook-core.json: שם המשפחה והכינויים שלה (family_aliases), ונושאי העמדות. נושא שיש עליו עמדה בפלייבוק אינו נשאל');E.add_argument('--role',help='התפקיד של החברה בהסכם (company_role_code מהפלייבוק)');E.add_argument('--profile',help='פרופיל-לקוח.json: שדות שהפרופיל קובע אינם נשאלים');E.add_argument('--skeleton',help='skeleton.json של המשפחה, כשיש תבנית אב: המשתנים שלו נכנסים כשדות');E.add_argument('--out',required=True);E.add_argument('--force',action='store_true',help='לדרוס מפה קיימת');E.add_argument('--drivers-out',help='drivers.json של המשפחה והצד (Areo-נתונים/תבניות/<משפחה>/drivers.json): מודל השאלות המכוננות. נשמר פעם אחת, ונבנה מחדש רק כשנוספו הסכמים, כשהמחקר השתנה, או עם --rebuild-drivers. גם עם הסכם אחד או בלי הסכמים הוא נכתב');E.add_argument('--research',help='research-<slug>.json: תנאי התחולה (applies_when) של המקורות הופכים לשאלות מכוננות, וסעיפי החובה שלהם לסעיפים תלויים');E.add_argument('--rebuild-drivers',action='store_true',help='לבנות את drivers.json מחדש לבקשת הלקוח');A=E.parse_args();f=[A.registry,A.profile,A.skeleton,A.playbook,A.research];guard_out(A.out,f,A.force)
	if A.drivers_out:guard_out(A.drivers_out,f+[A.out],A.force)
	if os.path.isfile(A.registry):g=json.load(io.open(A.registry,encoding='utf-8'))
	elif A.drivers_out:g={'documents':[]}
	else:print('המרשם לא נמצא: %s'%A.registry);sys.exit(2)
	O=normalize_role(A.role)if A.role else None;H={}
	if A.playbook and os.path.isfile(A.playbook):
		try:H=json.load(io.open(A.playbook,encoding='utf-8-sig'))
		except(OSError,ValueError):H={}
	G=list(A.family)
	if not O and H.get('company_role_code'):O=normalize_role(H.get('company_role_code'))
	for M in H.get('contract_families')or[]:G+=[M.get('contract_family_name')]+list(M.get('family_aliases')or[])
	G+=[H.get('family_id'),H.get('family_code')];G=[re.sub('^fam_','',str(A)).replace('_',' ')for A in G if A];s={A for A in re.split('[\\s_]+',str(H.get('company_role_code')or'').lower())if A};G+=[A for B in list(G)for A in B.split()if len(A)>3 and A.lower()not in s and A not in G]
	def t(d):
		if family_matches(d.get('family'),G)or any(family_matches(A,G)for A in d.get('family_candidates')or[]):return True
		B=(d.get('file')or'')+' '+(d.get('title')or'');return any(len(A)>2 and word_count(A.lower(),B.lower())for A in G)
	C,P=[],[]
	for B in g.get('documents')or[]:
		if not t(B):continue
		if B.get('doc_class')in('redline',)and not B.get('user_approved'):P.append((B['file'],'טיוטה עם עקוב אחר שינויים, לא נוסח סופי'));continue
		if B.get('paper')=='counterparty':P.append((B['file'],'הנייר של הצד השני בעסקה'));continue
		h=B.get('company_role')or(B.get('company_role_candidates')or[None])[0]
		if O and h and normalize_role(h)!=O:P.append((B['file'],'נכתב בצד ההפוך'));continue
		B=dict(B);B['paper']=B.get('paper')or('company'if B.get('company_paper')or B.get('user_approved')else'third_party');C.append(B)
	i,j=[],{}
	for B in C:
		k,Q=read_paras(B);Q=Q or unreadable('\n'.join(k))
		if Q:P.append((B['file'],Q));continue
		i.append(B);j[id(B)]=k
	C=i
	for(M,Q)in P:print('  לא נכלל: %s (%s)'%(M,Q))
	l=json.load(io.open(A.profile,encoding='utf-8'))if A.profile and os.path.isfile(A.profile)else{};X=None
	if A.research and os.path.isfile(A.research):from research_sources import normalise as u;X=u(json.load(io.open(A.research,encoding='utf-8')))
	Y=[A['file']for A in C];R=O or A.role;D,K,m=None,False,'new'
	if A.drivers_out and os.path.isfile(A.drivers_out):
		try:D=DL.load(A.drivers_out)
		except(OSError,ValueError):D=None
		if D and DL.role_conflict(D,R):print('drivers.json שבנתיב נבנה לצד אחר של המשפחה (%s). מודל השאלות נשמר לכל משפחה ולכל צד: שמרו את הצד הזה בקובץ נפרד באותה תיקייה, למשל drivers-%s.json.\nThe saved drivers.json is for another side (%s); save this side in a separate file.'%(D.get('role'),re.sub('[^\\w\\-]+','-',str(R)),D.get('role')));sys.exit(2)
		v,m=DL.needs_rebuild(D,Y,DL.sha1_of(A.research),R,A.rebuild_drivers);K=not v
	def n(model,reused):
		C=reused;A=model;B=A.get('approved')or{};D=sum(1 for A in A['drivers']if A.get('source')=='research');print('שאלות מכוננות: %d (מההסכמים: %d, מהמחקר: %d)%s'%(len(A['drivers']),len(A['drivers'])-D,D,' · שאלה פתוחה: כן'if A.get('open_question')else''))
		if C and B.get('at'):print('נמצא מודל שאלות שמור ומאושר (%s, %s): אינו נבנה מחדש ואינו מוצג שוב לאישור. ניגשים ישר לשאלות.'%(B.get('at'),B.get('by')))
		elif C:print('נמצא מודל שאלות שמור שטרם אושר: מציגים אותו ללקוח לאישור פעם אחת (drivers_lib.py approve).')
		else:print('מודל השאלות נבנה%s: מציגים אותו ללקוח לאישור פעם אחת (שינוי שם, איחוד, מחיקה, הוספה), ואז drivers_lib.py approve.'%{'added':' מחדש, כי נוספו הסכמים','removed':' מחדש, כי הוסרו הסכמים','research':' מחדש, כי המחקר השתנה','force':' מחדש, לבקשתכם'}.get(m,''))
	def o(model):
		if D and(D.get('approved')or{}).get('at')and not K:model['previous']={'built_at':D.get('built_at'),'approved':D.get('approved'),'files':(D.get('built_from')or{}).get('files')}
	if len(C)<2:
		if not A.drivers_out:print('נמצאו %d הסכמים קריאים מהסוג ומהצד הזה. מפת שונות צריכה לפחות שניים; עם הסכם אחד עובדים לפי השלד (template-flow.md, פרקים 1 עד 4).\nFound %d readable agreements of this type and side. A variance map needs at least two; with one agreement, work from the skeleton.'%(len(C),len(C)));sys.exit(2)
		I=str(l.get('display_language')or'').strip().lower()[:2];I=I if I in('he','en')else'en'if C and(C[0].get('language')or'')[:2]=='en'else'he';F=D if K else build_model(A.family[0],R,I,Y,A.research,X)
		if not K:o(F);DL.save(A.drivers_out,F)
		print('נמצאו %d הסכמים קריאים מהסוג ומהצד הזה: אין שונות למדוד, ומפת השונות לא נבנתה. מודל השאלות נשמר: %s. השאלות ממנו, והשאלה הפתוחה, נכנסות לאותו טופס.'%(len(C),A.drivers_out));n(F,K);sys.exit(0)
	w=json.load(io.open(A.skeleton,encoding='utf-8'))if A.skeleton and os.path.isfile(A.skeleton)else None;T=[read_doc(A,j[id(A)])for A in C];U={A['paper']for A in C};SOURCE[0]='company'if U=={'company'}or'company'in U else'published'if'published'in U else'third_party'
	try:from derive_deal_defaults import derive as x;p=x([(A['file'],A.get('family'),B['text'],A.get('company_role'))for(A,B)in zip(C,T)])
	except Exception:p=[]
	I,Z,S,L,N=build(C,T,l,w,p);V=[]
	for W in H.get('clauses')or H.get('rules')or[]:
		if isinstance(W,dict):V+=[str(W.get('title')or''),str(W.get('clause_issue')or'')]+[str(A)for A in W.get('topic_ids')or[]]
	V=[A.lower()for A in V if len(A)>2]
	for a in L:
		b=(a.get('heading')or'').lower();c=(a.get('topic')or'').lower()
		if any(word_count(b,A)or word_count(A,b)or c and(c in A or A in c)for A in V if b):a['playbook_topic']=True
	if any(A.get('paper')in('published','third_party')for A in C)and'company'not in U:
		y="Areo proposal (not based on the client's documents)"if I=='en'else'הצעת Areo (לא מבוסס על מסמכי הלקוח)'
		for J in L+N:J['areo_proposal'],J['label']=True,y
	if K:F=D
	else:F=build_model(A.family[0],R,I,Y,A.research,X,T,C,S,L,N,Z,SOURCE[0]);o(F)
	d=F.get('dependent_on')or{}
	for J in L+N:
		if J['id']in d:J['driver_id']=d[J['id']]
	q,r=questions(I,S,L,N,F)
	for M in S:M['by_doc']={'DOC-%d'%(A+1):B for(A,B)in M['by_doc'].items()}
	for J in L+N:
		for e in('_yes','_no','_key','_from'):J.pop(e,None)
		for z in J.get('variants')or[]:
			for e in('_yes','_no','_from'):z.pop(e,None)
	A0={'generated_at':date.today().isoformat(),'family':A.family[0],'family_names':G,'company_role':O or A.role,'language':I,'not_included':[{'file':A,'why':B}for(A,B)in P],'documents':[{'id':'DOC-%d'%(B+1),'file':A['file'],'doc_class':A.get('doc_class'),'paper':A['paper'],'title':C['title'][:120]}for(B,(A,C))in enumerate(zip(C,T))],'constants':Z,'data_fields':S,'optional_clauses':L,'alternative_wordings':N,'questions':q,'defaults_for_approval':r,'drivers':F['drivers'],'clause_kinds':F.get('clause_kinds')or{},'dependent_on':d,'drivers_file':A.drivers_out};B=os.path.dirname(os.path.abspath(A.out))
	if B and not os.path.isdir(B):os.makedirs(B)
	io.open(A.out,'w',encoding='utf-8').write(json.dumps(A0,ensure_ascii=False,indent=2))
	if A.drivers_out and not K:DL.save(A.drivers_out,F)
	print('מפת השונות: %s'%A.out);print('הסכמים: %d · קבועים: %d · שדות נתונים: %d · סעיפים אופציונליים: %d · נוסחים חלופיים: %d · שאלות: %d (+%d ברירות מחדל לאישור)'%(len(C),len(Z),len(S),len(L),len(N),len(q),len(r)))
	if A.drivers_out:print('מודל השאלות: %s'%A.drivers_out)
	n(F,K)
if __name__=='__main__':main()
