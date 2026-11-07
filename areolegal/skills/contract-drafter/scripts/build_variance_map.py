# -*- coding: utf-8 -*-
# Copyright (c) Areo. All rights reserved. Licensed under the terms at https://areo.co.il/legal/terms
import argparse,difflib,io,json,os,re,sys
from collections import Counter,OrderedDict
from datetime import date
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from build_template_registry import docx_paragraphs,guard_out,family_matches,normalize_role,pdf_text,word_count
from build_clause_bank import HEADING_INLINE,HEADING_SPLIT,NOT_A_HEADING,looks_like_bare_heading,topic_of
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
def signals(ids,yes,no,docs,fields):
	E=no;D=yes;B=docs;C=[]
	if not D or not E:return C
	for(Q,N)in(('כותרת','title'),('מבוא','preamble')):
		H=[words_of(B[A][N])for A in D];I=[words_of(B[A][N])for A in E];O=set.intersection(*H)-set.union(*I)if len(H)>1 and I else set();P=set.intersection(*I)-set.union(*H)if len(I)>1 and H else set()
		if O or P:C.append({'kind':Q,'with':sorted(O)[:6],'without':sorted(P)[:6]})
	for A in fields:
		if A.get('per_deal')or A.get('type')not in('amount','rate','period','number')or not A.get('by_doc'):continue
		J={A['by_doc'].get(B)for B in D}-{None,''};K={A['by_doc'].get(B)for B in E}-{None,''}
		if J and K and not J&K:C.append({'kind':'שדה','field':A['id'],'context':A['context'],'with':sorted(J)[:4],'without':sorted(K)[:4]})
	F=[max(amounts(B[A]['text'])or[0])for A in D];G=[max(amounts(B[A]['text'])or[0])for A in E]
	if len([A for A in F if A])>1 and len([A for A in G if A])>1 and(min(F)>max(G)or max(F)<min(G)):C.append({'kind':'טווח סכומים','with':[min(F),max(F)],'without':[min(G),max(G)]})
	L={bool(ORG.search(B[A]['preamble']))for A in D};M={bool(ORG.search(B[A]['preamble']))for A in E}
	if len(L)==1 and len(M)==1 and L!=M:C.append({'kind':'סוג הצד שכנגד','with':['תאגיד או גוף'if True in L else'אדם פרטי'],'without':['תאגיד או גוף'if True in M else'אדם פרטי']})
	return C
SOURCE_WORDS={'he':{'company':'בהסכמים שלכם','third_party':'בנוסחים שנמצאו','published':'בהסכמים שפורסמו'},'en':{'company':'in your agreements','third_party':'in the forms we found','published':'in the published agreements'}}
SOURCE=['company']
def signal_phrase(sig,lang):
	C=sig;B=lang=='en';C=[A for A in C or[]if A.get('with')and A['kind']in('שדה','טווח סכומים','סוג הצד שכנגד')]
	if not C:return''
	F={'שדה':0,'טווח סכומים':1,'סוג הצד שכנגד':2};A=sorted(C,key=lambda x:F[x['kind']])[0]
	if A['kind']=='שדה':return(' Usually when %s is %s.'if B else' בדרך כלל כש%s הוא %s.')%(A['context']or('the value'if B else'הערך'),' / '.join(str(A)for A in A['with']))
	if A['kind']=='טווח סכומים':
		E,D='{:,.0f}'.format(A['with'][0]),'{:,.0f}'.format(A['with'][1])
		if E==D:return(' Usually when the amounts reach %s.'if B else' בדרך כלל כשהסכומים מגיעים ל-%s.')%D
		return(' Usually for amounts of %s to %s.'if B else' בדרך כלל בסכומים של %s עד %s.')%(E,D)
	return(' Usually when the other side is %s.'if B else' בדרך כלל כשהצד השני הוא %s.')%' / '.join(A['with'][:2])
def build(docs_meta,docs,profile,skeleton=None,defaults=None):
	f=docs_meta;Z=profile;A=docs;g='en'if sum(1 for A in f if(A.get('language')or'')[:2]=='en')>len(f)/2 else'he';R=list(range(len(A)));L=lambda i:'DOC-%d'%(i+1);h=OrderedDict()
	for(C,q)in enumerate(A):
		for B in q['clauses']:h.setdefault(B,[]).append(C)
	a,H,S,T=[],[],[],[];M=[0]
	def i(topic,heading,ctx,by_doc,refs):A=by_doc;A={B:A.strip(' ,;:.')if A.strip(' ,;:.')else A for(B,A)in A.items()};M[0]+=1;B=Counter(A for A in A.values());C={'id':'F%d'%M[0],'topic':topic,'heading':heading,'context':ctx.strip(),'type':kind_of(next(iter(A.values()),'')),'values':[{'value':B,'count':C,'documents':[L(A)for(A,C)in A.items()if C==B]}for(B,C)in B.most_common()],'default':B.most_common(1)[0][0]if B and B.most_common(1)[0][1]>1 else None,'per_deal':not B or B.most_common(1)[0][1]==1,'by_doc':A,'refs':refs};H.append(C);return C
	def O(k,members):return[{'doc':L(B),'clause':', '.join(A for A in A[B]['clauses'][k]['numbers']if A)or None}for B in members]
	b=max(R,key=lambda i:len(A[i]['preamble']));j={}
	for C in R:
		if C==b:continue
		c,u=data_spans(A[b]['preamble'],A[C]['preamble'])
		for(I,G,d,N)in c:j.setdefault((N,I,G),{b:G})[C]=d
	for((N,I,G),J)in sorted(j.items()):
		if len(set(J.values()))>1:i('מבוא','המבוא והצדדים'if g=='he'else'Preamble and parties',I,J,[{'doc':L(A),'clause':None}for A in J])
	for(B,D)in h.items():
		k=A[D[0]]['clauses'][B];U,V=k['topic'],k['heading'];W=max(D,key=lambda i:sum(ratio(toks(A[i]['clauses'][B]['text']),toks(A[C]['clauses'][B]['text']))for C in D));X=A[W]['clauses'][B]['text'];K=[[W]]
		for C in D:
			if C==W:continue
			for P in K:
				if ratio(toks(A[P[0]]['clauses'][B]['text']),toks(A[C]['clauses'][B]['text']))>=SAME:P.append(C);break
			else:K.append([C])
		l,m={},[]
		for C in K[0][1:]:
			c,v=data_spans(X,A[C]['clauses'][B]['text'])
			for(I,G,d,N)in c:l.setdefault((N,I,G),{W:G})[C]=d
		n=[]
		for((N,I,G),J)in sorted(l.items()):
			if len(set(J.values()))>1:Q=i(U,V,I,J,O(B,list(J)));m.append(Q);n.append((N,len(toks(G))or 1,Q['id']))
		e=[{'variant':'V%d'%(D+1),'documents':[L(A)for A in C],'text':A[C[0]]['clauses'][B]['text'],'refs':O(B,C)}for(D,C)in enumerate(K)]
		if len(D)==len(A)and len(K)==1:a.append({'id':'C%d'%(len(a)+1),'topic':U,'heading':V,'text':X,'text_template':template_of(X,n),'fields':[A['id']for A in m],'refs':O(B,D)});continue
		if len(D)<len(A):o,p=D,[A for A in R if A not in D];S.append({'id':'O%d'%(len(S)+1),'topic':U,'heading':V,'with':[L(A)for A in o],'without':[L(A)for A in p],'signals':[],'_yes':o,'_no':p,'wording':X,'variants':e if len(K)>1 else[],'refs':O(B,D)})
		else:
			for(E,P)in zip(e,K):E['_yes'],E['_no']=P,[A for A in D if A not in P]
			T.append({'id':'A%d'%(len(T)+1),'topic':U,'heading':V,'variants':e,'refs':O(B,D)})
	for Y in S+[B for A in T for B in A['variants']]:
		if'_yes'in Y:Y['signals']=signals(R,Y.pop('_yes'),Y.pop('_no'),A,H)
	r=[{str(A['value']).replace(',','')for A in A['values']}for A in H]
	for F in defaults or[]:
		s={str(A['value']).split()[0].replace(',','')for A in F.get('distribution')or[]}
		if any(s<=A for A in r):continue
		if F.get('value')is not None and len(F.get('distribution')or[])>1:M[0]+=1;H.append({'id':'F%d'%M[0],'topic':None,'heading':F['parameter'],'context':F.get('question'),'type':kind_of(str(F['value'])),'source':'derive_deal_defaults','values':[{'value':A['value'],'count':A['documents']}for A in F['distribution']],'default':F['value'],'by_doc':{},'refs':[{'doc':None,'file':F.get('source_file')}]})
	for E in(skeleton or{}).get('variables')or[]:M[0]+=1;H.append({'id':'F%d'%M[0],'topic':None,'heading':E.get('label')or E.get('id'),'context':E.get('id'),'type':E.get('type')or'text','source':'skeleton','values':[{'value':E.get('found_value'),'count':1}]if E.get('found_value')else[],'default':E.get('found_value'),'by_doc':{},'refs':[]})
	t={str(A).strip()for A in((Z or{}).get('organization_name'),(Z or{}).get('organization_name_en'),(Z or{}).get('registration_number'))if A}
	for Q in H:
		if any(any(A and A in str(B['value'])for A in t)for B in Q['values']):Q['derivable_from']='profile'
	return g,a,H,S,T
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
def questions(lang,fields,optional,alternatives):
	N=fields;K=optional;J=lang;E=J=='en';O='en'if E else'he';G,P=YES_NO[O];Z=max([len(A['with'])+len(A['without'])for A in K]or[0]);Q=COUNT_WORDS[O][SOURCE[0]];F,R=[],[]
	for A in sorted([A for A in K if not A.get('playbook_topic')],key=lambda x:-len(x['with'])):
		H=len(A['with'])+len(A['without']);A['core']=H>=3 and len(A['with'])/float(H)>=CORE_SHARE;I=clean_heading(A);A['askable']=bool(I)
		if not I:continue
		if A['core']:R.append((A,I,H));continue
		S=[A for A in A['signals']if A['kind']in('שדה','טווח סכומים','סוג הצד שכנגד')];F.append({'id':'Q-'+A['id'],'about':A['id'],'kind':'optional','text':('Add a clause on %s? It appears in %d of %d %s.%s'if E else'להוסיף סעיף בנושא %s? מופיע ב-%d מתוך %d %s.%s')%(I,len(A['with']),H,Q,signal_phrase(S,J)),'options':[G,P],'default':G if len(A['with'])>=len(A['without'])else P})
	for B in alternatives:
		if not clean_heading({'heading':B.get('heading'),'topic':B.get('topic'),'with':[B for A in B['variants']for B in A['documents']]}):B['askable']=False;continue
		L=[re.sub('\\s+',' ',A['text']).split(' ')for A in B['variants']];C=0
		while all(len(A)>C for A in L)and len({A[C]for A in L})==1:C+=1
		C=max(0,C-3)
		for(T,U)in zip(B['variants'],L):T['_from']=('...'if C else'')+' '.join(U[C:])
		F.append({'id':'Q-'+B['id'],'about':B['id'],'kind':'alternative','text':('Which wording do you want for the clause on %s?'if E else'איזה נוסח אתם רוצים לסעיף בנושא %s?')%B['heading'],'options':['"%s"%s'%(excerpt(A.pop('_from',A['text'])),signal_phrase([A for A in A.get('signals')or[]if A['kind']in('שדה','טווח סכומים','סוג הצד שכנגד')],J))for A in B['variants']],'option_values':[A['variant']for A in B['variants']],'default':max(B['variants'],key=lambda v:len(v['documents']))['variant']})
	V=[A for A in N if askable_field(A)and A.get('per_deal')];W=[A for A in N if askable_field(A)and not A.get('per_deal')]
	for D in V+W:X=' '.join((D.get('context')or D.get('heading')or'').split());F.append({'id':'Q-'+D['id'],'about':D['id'],'kind':'data','text':('What goes in the agreement for: %s?'if E else'מה לרשום בהסכם הזה: %s?')%X,'options':[]if D.get('per_deal')else[A['value']for A in D['values'][:4]if A['value']],'free_text':True,'default':D.get('default')})
	Y,M=F[:MAX_QUESTIONS],F[MAX_QUESTIONS:];M+=[{'id':'Q-'+A['id'],'about':A['id'],'kind':'optional','status':'playbook_topic','text':('%s: included, you already have a position on it'if E else'%s: נכלל, כבר יש לכם עמדה בנושא')%A['heading'],'default':G}for A in K if A.get('playbook_topic')];M+=[{'id':'Q-'+A['id'],'about':A['id'],'kind':'optional','status':'core_included','text':('%s: included, it appears in %d of %d %s'if E else'%s: נכלל, מופיע ב-%d מתוך %d %s')%(B,len(A['with']),C,Q),'default':G}for(A,B,C)in R];return Y,[dict(A,status=A.get('status')or('default_for_approval'if A.get('default')not in(None,'')else'to_complete'))for A in M]
def main():
	F=argparse.ArgumentParser(description='מפת השונות בין ההסכמים הקיימים של החברה מאותו סוג ובאותו צד');F.add_argument('--registry',required=True,help='template-registry.json');F.add_argument('--family',required=True,nargs='+',help='משפחת ההסכם: family_id של הפלייבוק, שם המשפחה במרשם, או שם או כינוי שלה (אפשר כמה)');F.add_argument('--playbook',help='playbook-core.json: שם המשפחה והכינויים שלה (family_aliases), ונושאי העמדות. נושא שיש עליו עמדה בפלייבוק אינו נשאל');F.add_argument('--role',help='התפקיד של החברה בהסכם (company_role_code מהפלייבוק)');F.add_argument('--profile',help='פרופיל-לקוח.json: שדות שהפרופיל קובע אינם נשאלים');F.add_argument('--skeleton',help='skeleton.json של המשפחה, כשיש תבנית אב: המשתנים שלו נכנסים כשדות');F.add_argument('--out',required=True);F.add_argument('--force',action='store_true',help='לדרוס מפה קיימת');A=F.parse_args();guard_out(A.out,[A.registry,A.profile,A.skeleton,A.playbook],A.force)
	if not os.path.isfile(A.registry):print('המרשם לא נמצא: %s'%A.registry);sys.exit(2)
	e=json.load(io.open(A.registry,encoding='utf-8'));J=normalize_role(A.role)if A.role else None;E={}
	if A.playbook and os.path.isfile(A.playbook):
		try:E=json.load(io.open(A.playbook,encoding='utf-8-sig'))
		except(OSError,ValueError):E={}
	D=list(A.family)
	if not J and E.get('company_role_code'):J=normalize_role(E.get('company_role_code'))
	for G in E.get('contract_families')or[]:D+=[G.get('contract_family_name')]+list(G.get('family_aliases')or[])
	D+=[E.get('family_id'),E.get('family_code')];D=[re.sub('^fam_','',str(A)).replace('_',' ')for A in D if A];f={A for A in re.split('[\\s_]+',str(E.get('company_role_code')or'').lower())if A};D+=[A for B in list(D)for A in B.split()if len(A)>3 and A.lower()not in f and A not in D]
	def g(d):
		if family_matches(d.get('family'),D)or any(family_matches(A,D)for A in d.get('family_candidates')or[]):return True
		B=(d.get('file')or'')+' '+(d.get('title')or'');return any(len(A)>2 and word_count(A.lower(),B.lower())for A in D)
	C,H=[],[]
	for B in e.get('documents')or[]:
		if not g(B):continue
		if B.get('doc_class')in('redline',)and not B.get('user_approved'):H.append((B['file'],'טיוטה עם עקוב אחר שינויים, לא נוסח סופי'));continue
		if B.get('paper')=='counterparty':H.append((B['file'],'הנייר של הצד השני בעסקה'));continue
		V=B.get('company_role')or(B.get('company_role_candidates')or[None])[0]
		if J and V and normalize_role(V)!=J:H.append((B['file'],'נכתב בצד ההפוך'));continue
		B=dict(B);B['paper']=B.get('paper')or('company'if B.get('company_paper')or B.get('user_approved')else'third_party');C.append(B)
	W,X=[],{}
	for B in C:
		Y,I=read_paras(B);I=I or unreadable('\n'.join(Y))
		if I:H.append((B['file'],I));continue
		W.append(B);X[id(B)]=Y
	C=W
	for(G,I)in H:print('  לא נכלל: %s (%s)'%(G,I))
	if len(C)<2:print('נמצאו %d הסכמים קריאים מהסוג ומהצד הזה. מפת שונות צריכה לפחות שניים; עם הסכם אחד עובדים לפי השלד (template-flow.md, פרקים 1 עד 4).\nFound %d readable agreements of this type and side. A variance map needs at least two; with one agreement, work from the skeleton.'%(len(C),len(C)));sys.exit(2)
	h=json.load(io.open(A.profile,encoding='utf-8'))if A.profile and os.path.isfile(A.profile)else{};i=json.load(io.open(A.skeleton,encoding='utf-8'))if A.skeleton and os.path.isfile(A.skeleton)else None;Q=[read_doc(A,X[id(A)])for A in C];L={A['paper']for A in C};SOURCE[0]='company'if L=={'company'}or'company'in L else'published'if'published'in L else'third_party'
	try:from derive_deal_defaults import derive as j;Z=j([(A['file'],A.get('family'),B['text'],A.get('company_role'))for(A,B)in zip(C,Q)])
	except Exception:Z=[]
	R,a,M,K,N=build(C,Q,h,i,Z);O=[]
	for P in E.get('clauses')or E.get('rules')or[]:
		if isinstance(P,dict):O+=[str(P.get('title')or''),str(P.get('clause_issue')or'')]+[str(A)for A in P.get('topic_ids')or[]]
	O=[A.lower()for A in O if len(A)>2]
	for S in K:
		T=(S.get('heading')or'').lower();U=(S.get('topic')or'').lower()
		if any(word_count(T,A)or word_count(A,T)or U and(U in A or A in U)for A in O if T):S['playbook_topic']=True
	if any(A.get('paper')in('published','third_party')for A in C)and'company'not in L:
		k="Areo proposal (not based on the client's documents)"if R=='en'else'הצעת Areo (לא מבוסס על מסמכי הלקוח)'
		for b in K+N:b['areo_proposal'],b['label']=True,k
	c,d=questions(R,M,K,N)
	for G in M:G['by_doc']={'DOC-%d'%(A+1):B for(A,B)in G['by_doc'].items()}
	l={'generated_at':date.today().isoformat(),'family':A.family[0],'family_names':D,'company_role':J or A.role,'language':R,'not_included':[{'file':A,'why':B}for(A,B)in H],'documents':[{'id':'DOC-%d'%(B+1),'file':A['file'],'doc_class':A.get('doc_class'),'paper':A['paper'],'title':C['title'][:120]}for(B,(A,C))in enumerate(zip(C,Q))],'constants':a,'data_fields':M,'optional_clauses':K,'alternative_wordings':N,'questions':c,'defaults_for_approval':d};B=os.path.dirname(os.path.abspath(A.out))
	if B and not os.path.isdir(B):os.makedirs(B)
	io.open(A.out,'w',encoding='utf-8').write(json.dumps(l,ensure_ascii=False,indent=2));print('מפת השונות: %s'%A.out);print('הסכמים: %d · קבועים: %d · שדות נתונים: %d · סעיפים אופציונליים: %d · נוסחים חלופיים: %d · שאלות: %d (+%d ברירות מחדל לאישור)'%(len(C),len(a),len(M),len(K),len(N),len(c),len(d)))
if __name__=='__main__':main()
