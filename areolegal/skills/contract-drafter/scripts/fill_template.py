#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (c) Areo. All rights reserved. Licensed under the terms at https://areo.co.il/legal/terms
import argparse,copy,datetime,io,json,os,re,sys
from docx import Document
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.text.paragraph import Paragraph
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from docx_numbering import LITERAL_RX,assign_segments,body_segment,find_refs,labelled_paragraphs,norm_label,para_text,replace_spans
from build_template_registry import guard_out
try:sys.stdout.reconfigure(encoding='utf-8')
except(AttributeError,ValueError):pass
TAG_RX=re.compile('\\{\\{\\s*([^{}]{1,60}?)\\s*\\}\\}')
NEW_WORDING='נוסח חדש, אינו מהתבנית'
NEW_WORDING_EN='New wording, not from the template'
HEB_RX=re.compile('[\u0590-\u05ff]')
COVER={'he':{'cover':'דף ליווי: ','stamp':'טיוטה · הופק בתאריך %s','template':'תבנית','filled':'משתנים שמולאו','defaulted':'נשארו כפי שהיו בהסכם המקורי','unfilled':'טעון השלמה','fill':'[להשלים] %s','removed':'סעיפים שהוסרו','clause':'סעיף %s','new':NEW_WORDING,'added':'סעיף חדש %s, אחרי סעיף %s','refs':'הפניות פנימיות שעודכנו','ref_line':'%s עודכן ל-%s','dangling':'הפניות לסעיף שהוסר, לבדיקה','dangling_line':'סעיף %s: %s','decisions':'מה הוחלט בטיוטה','notes':'הערות','gaps':'בטיוטה יש %d פרטים להשלים, מסומנים בצהוב','concern':'החשש העיקרי שלכם בעסקה','concern_answer':'כלשונכם: %s','concern_clauses':'המענה בטיוטה: סעיפים %s','options':'מוצע כאפשרות, לא נכלל','findings':'ממצאים בתבנית'},'en':{'cover':'Cover note: ','stamp':'Draft · Produced on %s','template':'template','filled':'Variables filled','defaulted':'Left as in the original agreement','unfilled':'To complete','fill':'[to complete] %s','removed':'Clauses removed','clause':'Clause %s','new':NEW_WORDING_EN,'added':'New clause %s, after clause %s','refs':'Internal references updated','ref_line':'%s updated to %s','dangling':'References to a removed clause, to check','dangling_line':'Clause %s: %s','decisions':'Decisions','notes':'Notes','gaps':'The draft has %d details to complete, highlighted in yellow','concern':'Your main concern in this deal','concern_answer':'In your words: %s','concern_clauses':'Where the draft answers it: clauses %s','options':'Offered as an option, not included','findings':'Findings in the template'}}
RESEARCH_BUBBLE={'he':'תוצאת מחקר עומק: הצעת Areo (לא מבוסס על מסמכי הלקוח)','en':"Deep research result: Areo's proposal (not based on the client's documents)"}
SOURCE_ORDER='template_alternative','client_agreement','playbook','new_wording'
def template_lang(doc):return'he'if any(HEB_RX.search(A.text or'')for A in doc.element.body.iter(qn('w:t')))else'en'
STOP_SUBTREE=re.compile('^\\s*(?:ולראיה|IN\\s+WITNESS|נספח\\s|Annex\\s|Schedule\\s|Exhibit\\s)',re.I)
def all_paragraphs(doc):
	for B in doc.element.body.iter(qn('w:p')):yield B
	for A in doc.sections:
		for C in(A.header,A.footer,A.first_page_header,A.first_page_footer):
			try:
				for B in C._element.iter(qn('w:p')):yield B
			except Exception:continue
def in_table(p):
	A=p.getparent()
	while A is not None:
		if A.tag==qn('w:tbl'):return A
		A=A.getparent()
def fill_variables(doc,values,skeleton,track=None):
	D=track;C=values;E,I={},{};F={A['id']:A.get('found_value')for A in(skeleton or{}).get('variables',[])if A.get('found_value')}
	for G in all_paragraphs(doc):
		J=para_text(G);H=[]
		for B in TAG_RX.finditer(J):
			A=B.group(1)
			if A in C:
				H.append((B.start(),B.end(),str(C[A])));E[A]=E.get(A,0)+1
				if D is not None:D.setdefault(A,[]).append((G,str(C[A])))
			elif A in F:
				H.append((B.start(),B.end(),F[A]));I[A]=F[A]
				if D is not None:D.setdefault(A,[]).append((G,str(F[A])))
		if H:replace_spans(G,H)
	K=sorted({B.group(1)for A in all_paragraphs(doc)for B in TAG_RX.finditer(para_text(A))});L=sorted(A for A in C if A not in E);return E,I,K,L
def parse_target(label,default_seg):
	A=label
	if'@'in str(A):B,C=str(A).split('@',1);return norm_label(B),int(C)
	return norm_label(str(A)),default_seg
def subtree(rows,i):
	B=rows[i];D=in_table(B['p']);C=[B['p']]
	for A in rows[i+1:]:
		if A['segment']!=B['segment']:break
		if A['label']and A['level']is not None and A['level']<=B['level']:break
		if not A['label']and STOP_SUBTREE.match(A['text']):break
		if in_table(A['p'])is not D:break
		C.append(A['p'])
	return C
def renumber_literal(rows,before,segments):
	F={}
	for A in rows:F[id(A['p'])]=before.get(id(A['p']),(None,A['segment']))[1]
	I={}
	for A in rows:
		if A['kind']!='literal':continue
		G=F[id(A['p'])]
		if G not in segments:continue
		C=LITERAL_RX.match(A['text'])
		if not C:continue
		D=A['level'];B=I.setdefault(G,[])
		while len(B)<D+1:B.append(0 if len(B)==D else 1)
		del B[D+1:];B[D]+=1;E='.'.join(str(A)for A in B);H=C.group(1)
		if H.endswith('.'):E+='.'
		if E!=H:replace_spans(A['p'],[(C.start(1),C.end(1),E)])
def set_text_keep_format(p,text):
	E=p.findall(qn('w:r'));B=None
	for A in E:
		if A.find(qn('w:t'))is not None:B=A.find(qn('w:rPr'));break
	for D in list(p):
		if D.tag in(qn('w:r'),qn('w:hyperlink'),qn('w:ins'),qn('w:del'),qn('w:fldSimple')):p.remove(D)
	A=OxmlElement('w:r')
	if B is not None:A.append(copy.deepcopy(B))
	C=OxmlElement('w:t');C.text=text;C.set('{http://www.w3.org/XML/1998/namespace}space','preserve');A.append(C);p.append(A)
def comment(doc,p,author,lang='he',text=None):
	A=author;C=Paragraph(p,doc._body);B=[A for A in C.runs if A.text]
	if not B:return False
	try:D=''.join(A[0]for A in(A or'Areo').split()[:2]);doc.add_comment(B,text=text or(NEW_WORDING_EN if lang=='en'else NEW_WORDING),author=A or'Areo',initials=D);return True
	except Exception:return False
def collect_effects(drivers,answers):
	P=drivers;I=answers;A={'include':[],'omit':[],'variant':{},'data':{},'template':None,'why':{},'unanswered':[],'companions_add':{'definitions':[],'annexes':[],'refs':[]},'companions_remove':{'definitions':[],'annexes':[],'refs':[]},'applied':[]}
	if not P:return A
	Q=[A for A in P.get('drivers')or[]if isinstance(A,dict)and A.get('id')];L={}
	for B in Q:
		for E in B.get('follow_ups')or[]:
			if isinstance(E,dict)and E.get('driver'):L[E['driver']]=B['id'],str(E.get('when'))
	for B in Q:
		D=B['id']
		if D in L:
			U,V=L[D]
			if str(I.get(U))!=V:continue
		if D not in I or I.get(D)in(None,''):
			if B.get('effects'):A['unanswered'].append(D)
			continue
		M=I[D];N=B.get('effects')or{};J=str(M)
		if J not in N and B.get('kind')=='number_threshold'and B.get('threshold')is not None:
			try:J='above'if float(str(M).replace(',',''))>=float(B['threshold'])else'below'
			except ValueError:pass
		C=N.get(J)
		if not isinstance(C,dict):
			if N:A['unanswered'].append(D)
			continue
		R=next((A.get('label')for A in B.get('options')or[]if str(A.get('value'))==J),None)or str(M);H=B.get('question')or'',R;A['applied'].append({'driver':D,'question':B.get('question'),'answer':R,'items':[]});S=A['applied'][-1]['items']
		for F in('include','omit'):
			for G in C.get(F)or[]:A[F].append(G);A['why'][G]=H;S.append(G)
		for(O,K)in(C.get('variant')or{}).items():A['variant'][O]=K;A['why'][O]=H;S.append(O)
		for(E,K)in(C.get('data')or{}).items():
			if K is not None:A['data'][E]=K;A['why'][E]=H
		if C.get('template'):A['template']=C['template'];A['why']['template']=H
		W=C.get('companions')or{};T='companions_remove'if C.get('omit')and not C.get('include')else'companions_add'
		for F in('definitions','annexes','refs'):
			for G in W.get(F)or[]:
				if G not in A[T][F]:A[T][F].append(G)
				A['why'].setdefault('%s:%s'%(F,G),H)
	return A
def ref_items(drivers):
	B={}
	for C in(drivers or{}).get('drivers')or[]:
		for A in C.get('evidence')or[]:
			if isinstance(A,dict)and A.get('clause')and A.get('item'):B.setdefault(str(A['clause']),set()).add(str(A['item']))
	return{B:next(iter(A))for(B,A)in B.items()if len(A)==1}
def pick_from_set(folder,choice):
	F=folder;A=choice
	if not A:return
	G=os.path.splitext(os.path.basename(str(A)))[0]
	for B in sorted(os.listdir(F)):
		C=os.path.join(F,B);D=os.path.join(C,'skeleton.json')
		if not os.path.isfile(os.path.join(C,'master.docx')):continue
		E=''
		if os.path.isfile(D):
			try:E=json.load(io.open(D,encoding='utf-8')).get('source_file')or''
			except ValueError:E=''
		if os.path.basename(E)==os.path.basename(str(A))or B==G or B==str(A):return os.path.join(C,'master.docx'),D
XML_SPACE='{http://www.w3.org/XML/1998/namespace}space'
SENT_A,SENT_B='\ue000','\ue001'
def _run_with(rpr,text,highlight=None):
	F=highlight;B=OxmlElement('w:r')
	if rpr is not None:B.append(copy.deepcopy(rpr))
	if F:
		A=B.find(qn('w:rPr'))
		if A is None:A=OxmlElement('w:rPr');B.insert(0,A)
		for G in A.findall(qn('w:highlight')):A.remove(G)
		D=OxmlElement('w:highlight');D.set(qn('w:val'),F);C=None
		for H in('w:u','w:effect','w:bdr','w:shd','w:fitText','w:vertAlign','w:rtl','w:cs','w:em','w:lang','w:eastAsianLayout'):
			C=A.find(qn(H))
			if C is not None:break
		if C is not None:C.addprevious(D)
		else:A.append(D)
	E=OxmlElement('w:t');E.text=text;E.set(XML_SPACE,'preserve');B.append(E);return B
def _has_content(r):
	for A in r:
		if A.tag==qn('w:rPr'):continue
		if A.tag==qn('w:t')and not(A.text or''):continue
		return True
	return False
def mark_span(p,start,end,label):
	K=label;H=end;G=start;L=para_text(p)
	if not 0<=G<H<=len(L):return False
	replace_spans(p,[(G,H,SENT_A+L[G:H]+SENT_B)])
	for I in list(p.iter(qn('w:t'))):
		M=I.text or''
		if SENT_A not in M:continue
		A=I.getparent();Q,J=M.split(SENT_A,1);R,S=J.split(SENT_B,1)if SENT_B in J else(J,'');N=A.find(qn('w:rPr'));D=list(A).index(I);B,C=copy.deepcopy(A),copy.deepcopy(A);O,P=list(B)[D],list(C)[D];O.text,P.text=Q,S;O.set(XML_SPACE,'preserve');P.set(XML_SPACE,'preserve')
		for E in list(B)[D+1:]:B.remove(E)
		for E in list(C)[:D]:
			if E.tag!=qn('w:rPr'):C.remove(E)
		F=[B]if _has_content(B)else[];F.append(_run_with(N,R,'yellow'))
		if K:F.append(_run_with(N,' '+K,'yellow'))
		if _has_content(C):F.append(C)
		for T in F:A.addprevious(T)
		A.getparent().remove(A);return True
	return False
def strip_commercial_marks(src,dst):
	from docx import Document as I;from check_draft_integrity import COMMERCIAL_LABEL_RX as J;E=I(src);F=0
	for K in all_paragraphs(E):
		G=list(K.iter(qn('w:r')))
		for(L,A)in enumerate(G):
			H=''.join(A.text or''for A in A.findall(qn('w:t')))
			if not J.fullmatch(H.strip())or not H.strip():continue
			F+=1;B=L-1
			while B>=0:
				C=G[B].find(qn('w:rPr'));D=C.find(qn('w:highlight'))if C is not None else None
				if D is None or D.get(qn('w:val'))!='yellow':break
				C.remove(D);B-=1
			if A.getparent()is not None:A.getparent().remove(A)
	E.save(dst);return F
def is_commercial_var(v,extra=()):
	from check_draft_integrity import COMMERCIAL_NATURE_RX as A
	if v.get('id')in extra or v.get('commercial'):return True
	if v.get('type')=='סכום':return True
	return bool(A.search('%s %s'%(v.get('label')or'',v.get('context')or'')))
def apply_commercial(doc,rows_by_key,base_seg,vals,skeleton,track,lang):
	O=track;K=rows_by_key;G=vals;from check_draft_integrity import COMMERCIAL_LABEL as U,COMMERCIAL_NATURE_RX as V,commercial_amounts as W;L=U['en'if lang=='en'else'he'];P=G.get('variable_sources')or{};X={str(A).strip()for(B,A)in(G.get('variables')or{}).items()if str(P.get(B,'answer'))=='answer'and str(A).strip()};I=[]
	def Q(p):
		for(A,B)in K.items():
			if any(A is p for A in B):return A
	F=set()
	for C in G.get('commercial')or[]:
		if not isinstance(C,dict)or not C.get('text')or str(C.get('value_source',''))=='answer':continue
		Y=K.get(norm_label(str(C.get('clause')or'')))if C.get('clause')else None
		for A in Y or list(all_paragraphs(doc)):
			D=para_text(A);B=D.find(C['text'])
			if B>=0 and(id(A),B)not in F:mark_span(A,B,B+len(C['text']),L);F.add((id(A),B));I.append({'clause':C.get('clause')or Q(A),'text':C['text'],'topic':C.get('topic'),'value_source':C.get('value_source')or'template'});break
	Z=set(G.get('commercial_variables')or[])
	for E in(skeleton or{}).get('variables')or[]:
		if not is_commercial_var(E,Z)or E['id']not in O:continue
		R=str(P.get(E['id'],'answer'if E['id']in(G.get('variables')or{})else'agreement'))
		if R=='answer':continue
		for(A,H)in O[E['id']]:
			D=para_text(A);B=D.find(H)
			if B<0 or not H.strip()or(id(A),B)in F:continue
			if COMMERCIAL_LABEL_RX_CACHE.match(D[B+len(H):].lstrip()):continue
			mark_span(A,B,B+len(H),L);F.add((id(A),B));I.append({'clause':Q(A),'text':H,'topic':E.get('label')or E['id'],'value_source':R})
	for(S,a)in K.items():
		for A in a:
			D=para_text(A);b=W(D)
			for(J,M)in reversed(b):
				N=D[J:M]
				if(id(A),J)in F or any(N in A or A in N for A in X if len(A)>=2):continue
				if COMMERCIAL_LABEL_RX_CACHE.match(D[M:].lstrip()):continue
				mark_span(A,J,M,L);F.add((id(A),J));T=V.search(D);I.append({'clause':S,'text':N,'topic':T.group(0)if T else S,'value_source':'template'})
	return I
COMMERCIAL_LABEL_RX_CACHE=re.compile('\\(\\s*(?:נושא\\s+מסחרי|commercial\\s+point)\\s*\\)',re.I)
DEF_PARA_RX='^\\s*(?:\\d+(?:\\.\\d+)*\\.?\\s*)?["“”״]%s["“”״]'
def def_paragraphs(doc,term):B=re.compile(DEF_PARA_RX%re.escape(term));return[A for A in doc.element.body.iter(qn('w:p'))if B.match(para_text(A))]
def term_defined(doc,term):A='\n'.join(para_text(A)for A in doc.element.body.iter(qn('w:p')));return bool(re.search('["“”״]%s["“”״]'%re.escape(term),A))
ANNEX_HEAD=re.compile('^\\s*(?:נספח|Annex|Schedule|Exhibit)\\b',re.I)
def annex_block(doc,title):
	C=[A for A in doc.element.body if A.tag in(qn('w:p'),qn('w:tbl'))];F=re.sub('\\s+',' ',title).strip().lower()
	for(G,A)in enumerate(C):
		if A.tag!=qn('w:p'):continue
		D=re.sub('\\s+',' ',para_text(A)).strip()
		if ANNEX_HEAD.match(D)and F in D.lower():
			E=[A]
			for B in C[G+1:]:
				if B.tag==qn('w:p')and ANNEX_HEAD.match(para_text(B)):break
				E.append(B)
			return E
	return[]
def wording_coverage(doc_text_tokens,wording):from check_draft_integrity import _coverage as A,_vtoks as B;return A(B(wording),doc_text_tokens)
def main():
	S=argparse.ArgumentParser();S.add_argument('--template',required=True);S.add_argument('--values',required=True);S.add_argument('--out',required=True);S.add_argument('--cover');S.add_argument('--skeleton',help='ברירת מחדל: skeleton.json שליד התבנית');S.add_argument('--lang',choices=('he','en'),help='שפת הבועות ודף הליווי; בלעדיו: language ב-values.json, ואחריו שפת התבנית');S.add_argument('--force',action='store_true',help='לדרוס טיוטה או דף ליווי קיימים (הרצה חוזרת אחרי תיקון)');S.add_argument('--drivers',help='drivers.json של המשפחה והצד (או של ערכת התבניות): התשובות ב-variance.drivers מוחלות על כל ההשפעות שלהן, כולל הגדרות, נספחים והפניות');S.add_argument('--variance-map',help='variance-map.json: הנוסח של הלקוח מהסכם אחר, לסעיף שהתשובה מחייבת ואינו בתבנית (המקור השני בסדר של פרק 7, כלל 4)');S.add_argument('--clean-copy',help='עותק לצד השני: בלי סימוני הנושאים המסחריים (הערכים נשארים)');A=S.parse_args();G=json.load(io.open(A.values,encoding='utf-8'));AH=json.load(io.open(A.drivers,encoding='utf-8'))if A.drivers else None;Ae=dict((G.get('variance')or{}).get('drivers')or G.get('drivers_answers')or{});E=collect_effects(AH,Ae);Af=json.load(io.open(A.variance_map,encoding='utf-8'))if A.variance_map else{};u=E.get('template')or G.get('template_choice')
	if os.path.isdir(A.template):
		Ag=pick_from_set(A.template,u)
		if not Ag:print('לא נבחרה תבנית מתוך ערכת התבניות (%s). התשובה לשאלה שבוחרת בין התבניות חסרה, או שאינה מתאימה לאף תבנית בתיקייה.'%(u or'אין תשובה'));sys.exit(2)
		A.template,BD=Ag;A.skeleton=A.skeleton or BD
	AI=A.skeleton or os.path.join(os.path.dirname(os.path.abspath(A.template)),'skeleton.json');v=[A.template,A.values,AI,A.drivers,A.variance_map];guard_out(A.out,v,A.force);guard_out(os.path.splitext(A.out)[0]+'.report.json',v)
	if A.cover:guard_out(A.cover,v+[A.out],A.force)
	if A.clean_copy:guard_out(A.clean_copy,v+[A.out,A.cover],A.force)
	Z=json.load(io.open(AI,encoding='utf-8'))if os.path.isfile(AI)else None;H=Document(A.template);Ah=str(A.lang or G.get('language')or template_lang(H)).strip().lower();Q='en'if Ah[:2]=='en'or Ah in('english','אנגלית')else'he';w=G.get('author')or'Areo';F={'template':os.path.basename(A.template),'built_at':datetime.date.today().isoformat(),'warnings':[]}
	if u:F['template_choice']=os.path.basename(str(u))
	W=[];T=[];m=G.get('item_map')or{};g={A['id']:A for A in(Z or{}).get('alternatives')or[]};h={A['id']:A for A in(Z or{}).get('conditional_clauses')or[]}
	def x(x):C,B,A=str(x).partition('/');return A if B and(A in g or A in h)else x
	E['include']=[x(A)for A in E['include']];E['omit']=[x(A)for A in E['omit']];E['variant']={x(A):B for(A,B)in E['variant'].items()};E['why']={x(A):B for(A,B)in E['why'].items()}
	def I(item):A,B=E['why'].get(item,('',''));return'%s: %s'%(A,B)if A else''
	y=dict(G.get('variables')or{});Ai=dict(G.get('variable_sources')or{})
	for(i,BE)in E['data'].items():
		z=m.get(i,i)
		if any(A['id']==z for A in(Z or{}).get('variables')or[])or z in y:y[z]=BE;Ai[z]='answer'
		else:T.append('נתון %s לפי התשובה (%s) אינו ממופה למשתנה בתבנית (item_map)'%(i,I(i)))
	G=dict(G,variables=y,variable_sources=Ai);Aj={};Ak,Al,d,AJ=fill_variables(H,y,Z,Aj);F.update(filled=sorted(Ak),defaulted=Al,unfilled=d,unknown_variables=AJ);AK=dict(G.get('alternatives')or{});AK.update({A:B for(A,B)in E['variant'].items()if A in g});Am={}
	for e in all_paragraphs(H):
		K=para_text(e);f=[]
		for L in TAG_RX.finditer(K):
			J=L.group(1)
			if J not in g or J not in AK:continue
			A0=str(AK[J]);A1=next((A for A in g[J]['options']if A['value']==A0 or A['text']==A0),None);f.append((L.start(),L.end(),A1['text']if A1 else A0));Am[J]=A1['text']if A1 else A0,e
		if f:replace_spans(e,f)
	for(J,(j,A2))in Am.items():W.append({'clause':g[J].get('clause'),'change':'chosen','answer':I(J),'source':'template_alternative','text':j[:80],'_p':A2})
	C=labelled_paragraphs(H);assign_segments(C);n=G.get('segment',(Z or{}).get('body_segment',body_segment(C)));An={}
	for M in C:
		if M['label']:An.setdefault(M['key'],set()).add(M['segment'])
	Ao={id(A['p']):(A['key'],A['segment'])for A in C if A['label']};Ap=not any(A['kind']=='auto'for A in C)and any(A['kind']=='literal'for A in C);Aq={}
	for(D,M)in enumerate(C):
		if M['label']:Aq.setdefault((M['key'],M['segment']),D)
	def k(label):
		D=label;A,B=parse_target(D,n);C=Aq.get((A,B))
		if C is not None and'@'not in str(D)and len(An.get(A,()))>1:F['warnings'].append(('Clause %s exists in more than one numbering sequence; the agreement body was chosen (sequence %d). For an annex: "%s@<sequence>".'if Q=='en'else'סעיף %s קיים ביותר מרצף מספור אחד; נבחר גוף ההסכם (רצף %d). לנספח: "%s@<רצף>".')%(A,B,A))
		if C is None:F['warnings'].append(('Clause %s was not found in sequence %d.'if Q=='en'else'לא נמצא סעיף %s ברצף %d.')%(A,B))
		return C
	A3,AL=[],[];o,A4=[],[]
	def AM(i,why='',item=None):
		if any(C[i]['p']is B for(D,A)in A3 for B in A):return
		A3.append((C[i]['label']or'',subtree(C,i)if C[i]['label']else[C[i]['p']]));AL.append({'segment':C[i]['segment']});A=TAG_RX.sub('',para_text(C[i]['p']));B=LITERAL_RX.match(A);A=re.sub('\\s+',' ',A[B.end():]if B else A).strip();W.append({'clause':norm_label(C[i]['label'])if C[i]['label']else None,'change':'removed','answer':why,'source':None,'text':A[:50]})
		if item:A4.append(item)
	for N in G.get('remove_clauses')or[]:
		D=k(N)
		if D is not None:A3.append((N,subtree(C,D)));AL.append({'segment':C[D]['segment']})
	A5=dict(G.get('conditions')or{});A5.update({A:'include'for A in E['include']if A in h});A5.update({A:'omit'for A in E['omit']if A in h})
	for(D,M)in enumerate(C):
		A6=para_text(M['p'])
		for L in TAG_RX.finditer(A6):
			l=L.group(1)
			if l not in h or l not in A5:continue
			if str(A5[l]).strip().lower()in('include','yes','true','1','כן','לכלול'):
				A7,A8=L.start(),L.end()
				if A8<len(A6)and A6[A8]==' ':A8+=1
				elif A7>0 and A6[A7-1]==' ':A7-=1
				replace_spans(M['p'],[(A7,A8,'')]);o.append(l)
			else:AM(D,I(l),l)
	AN={A.get('id'):A for A in Af.get('optional_clauses')or[]};BF={A.get('id'):A for A in Af.get('alternative_wordings')or[]};from check_draft_integrity import _coverage as BG,_vtoks as Ar
	def AO(item):
		A=m.get(item)
		if A:return k(A)
		B=(AN.get(item)or{}).get('wording')
		if not B:return
		E=Ar(B)
		for(D,F)in enumerate(C):
			if F['label']and BG(E,Ar(' '.join(para_text(A)for A in subtree(C,D))))>=.85:return D
	def BH(heading):
		D=re.sub('\\s+',' ',str(heading or'')).strip()
		if len(D)<3:return
		B=[]
		for(G,E)in enumerate(C):
			if not E['label']:continue
			A=re.sub('\\s+',' ',TAG_RX.sub('',para_text(E['p']))).strip();F=LITERAL_RX.match(A);A=(A[F.end():]if F else A).strip().rstrip('.:')
			if A==D:B.append(G)
		return B[0]if len(B)==1 else None
	def As(item):
		D=item;B=[]
		if(AN.get(D)or{}).get('wording'):B.append({'text':AN[D]['wording'],'source':'client_agreement'})
		C=(G.get('effect_wording')or{}).get(D)
		for A in C if isinstance(C,list)else[C]if C else[]:
			if isinstance(A,str):A={'text':A}
			if isinstance(A,dict)and A.get('text'):B.append(dict(A,source=A.get('source')or'new_wording'))
		B.sort(key=lambda w:SOURCE_ORDER.index(w['source'])if w['source']in SOURCE_ORDER else len(SOURCE_ORDER));return B[0]if B else None
	def BI():A=[A for A in C if A['label']and A['segment']==n and A['level']==min((A['level']for A in C if A['label']and A['segment']==n),default=0)];return A[-1]['label']if A else None
	At,Au=[],[]
	for B in E['include']:
		if B in h:continue
		D=AO(B)
		if D is not None:o.append(B);continue
		X=As(B)
		if not X:T.append('התשובה (%s) מחייבת סעיף שאינו בתבנית, ואין לו נוסח ממקור מוגדר (effect_wording)'%I(B));continue
		At.append({'after':X.get('after')or m.get(B+'@after')or BI(),'text':X['text'],'source':X['source'],'answer':I(B),'item':B})
	for B in E['omit']:
		if B in h:continue
		D=AO(B)
		if D is not None:AM(D,I(B),B)
		else:A4.append(B)
	for(J,AP)in E['variant'].items():
		if J in g:continue
		N=m.get(J);j=next((A.get('text')for A in(BF.get(J)or{}).get('variants')or[]if A.get('variant')==AP),None);Av='client_agreement'
		if not j:X=As('%s:%s'%(J,AP));j,Av=(X['text'],X['source'])if X else(None,None)
		if not N or k(N)is None or not j:T.append('נוסח לפי התשובה (%s) לא הוחל: אין מיקום בתבנית (item_map) או נוסח'%I(J));continue
		Au.append((N,{'text':j,'source':Av,'answer':I(J)}));o.append('%s:%s'%(J,AP))
	A9=[]
	for O in E['companions_remove']['definitions']:
		for p in def_paragraphs(H,O):A9.append(p);W.append({'clause':None,'change':'removed','answer':I('definitions:'+O),'source':None,'text':'"%s"'%O})
	for P in E['companions_remove']['annexes']:
		Aw=annex_block(H,P);A9+=Aw
		if Aw:W.append({'clause':None,'change':'removed','answer':I('annexes:'+P),'source':None,'text':P})
	BJ=ref_items(AH);BK=(AH or{}).get('items')or{}
	for b in E['companions_remove']['refs']:
		B=m.get('ref:%s'%b)or BJ.get(str(b));D=AO(B)if B else None
		if D is None and B:D=BH((BK.get(B)or{}).get('heading'))
		if D is not None:AM(D,I('refs:'+b),B)
		elif B and B in A4:continue
		else:F['warnings'].append(('Clause %s in the earlier agreements could not be matched with certainty to a clause of the template; nothing was deleted for it. A reference left without its clause is flagged by the integrity check.'if Q=='en'else'סעיף %s בהסכמים הקודמים לא הותאם בוודאות לסעיף בתבנית, ולכן לא נמחק דבר בגללו. הפניה שנשארה בלי הסעיף שלה תסומן בבקרת השלמות.')%b)
	AQ,Y=[],[];AR=G.get('gap_research')or{};BL={str(A.get('topic'))for A in AR.get('topics')or[]if isinstance(A,dict)and len(A.get('sources')or[])<3}
	def Ax(source):
		A=source
		if A=='template_alternative':return None,False
		if A=='gap_research':return RESEARCH_BUBBLE['en'if Q=='en'else'he'],True
		return None,True
	def Ay(item):
		A=item
		if isinstance(A,str):A={'text':A}
		B,C=A.get('text',''),A.get('source')or'new_wording'
		if C=='gap_research'and str(A.get('topic'))in BL:B=('[to complete: %s]'if Q=='en'else'[להשלים: %s]')%A.get('topic')
		return B,C,A.get('answer')or''
	for(N,B)in list((G.get('replace_clauses')or{}).items())+Au:
		D=k(N)
		if D is None:continue
		K,q,AS=Ay(B)
		if C[D]['kind']=='literal':
			L=LITERAL_RX.match(C[D]['text'])
			if L and not LITERAL_RX.match(K):K=C[D]['text'][:L.end(1)]+' '+K.lstrip()
		set_text_keep_format(C[D]['p'],K);AT,AU=Ax(q)
		if AU:comment(H,C[D]['p'],w,Q,AT)
		AQ.append(norm_label(N));W.append({'clause':norm_label(N),'change':'changed','answer':AS,'source':q,'text':K[:60]})
	for B in list(G.get('add_clauses')or[])+At:
		D=k(B.get('after'))
		if D is None:
			if B.get('item'):T.append('סעיף לפי התשובה (%s) לא נוסף: לא נמצא מקום בתבנית'%(B.get('answer')or B['item']))
			continue
		Az=subtree(C,D)[-1]
		for R in Y:
			if R['after']==norm_label(B.get('after')):Az=R['p']
		c=copy.deepcopy(C[D]['p']);K,q,AS=Ay(B)
		if Ap:L=re.match('^\\s*\\S+\\s*',C[D]['text']);K=(L.group(0)if L else'')+K
		set_text_keep_format(c,K);Az.addnext(c);AT,AU=Ax(q)
		if AU:comment(H,c,w,Q,AT)
		Y.append({'after':norm_label(B.get('after')),'p':c,'segment':C[D]['segment'],'source':q,'answer':AS,'item':B.get('item'),'topic':B.get('topic')})
		if B.get('item'):o.append(B['item'])
	A_=G.get('companion_text')or{}
	for O in E['companions_add']['definitions']:
		if term_defined(H,O):continue
		r=(A_.get('definitions')or{}).get(O);s=[A for A in H.element.body.iter(qn('w:p'))if re.match('^\\s*(?:\\d+(?:\\.\\d+)*\\.?\\s*)?["“”״][^"“”״]{2,60}["“”״]\\s*[-\\u2013:]',para_text(A))]
		if not r or not s:T.append('ההגדרה "%s" נדרשת לפי התשובה (%s) ואינה בטיוטה'%(O,I('definitions:'+O)));continue
		c=copy.deepcopy(s[-1]);B0=LITERAL_RX.match(para_text(s[-1]));set_text_keep_format(c,(para_text(s[-1])[:B0.end()]+' 'if B0 else'')+'"%s" - %s'%(O,r));s[-1].addnext(c);comment(H,c,w,Q);W.append({'clause':None,'change':'added','answer':I('definitions:'+O),'source':'new_wording','text':'"%s"'%O})
	for P in E['companions_add']['annexes']:
		if annex_block(H,P):continue
		r=(A_.get('annexes')or{}).get(P)
		if not r:T.append('הנספח "%s" נדרש לפי התשובה (%s) ואינו בטיוטה'%(P,I('annexes:'+P)));continue
		AV=[A for A in H.element.body if A.tag==qn('w:p')][-1];AA=copy.deepcopy(AV);set_text_keep_format(AA,P if ANNEX_HEAD.match(P)else('Annex: %s'if Q=='en'else'נספח: %s')%P);AV.addnext(AA);B1=copy.deepcopy(AV);set_text_keep_format(B1,r);AA.addnext(B1);comment(H,AA,w,Q);W.append({'clause':None,'change':'added','answer':I('annexes:'+P),'source':'new_wording','text':P})
	for b in E['companions_add']['refs']:
		if k(b)is None:T.append('הסעיף הקשור %s נדרש לפי התשובה (%s) ואינו בטיוטה'%(b,I('refs:'+b)))
	AB=[]
	for(N,B2)in A3:
		for e in B2:
			if e.getparent()is not None:e.getparent().remove(e)
		AB.append({'label':norm_label(N)if N else'','paragraphs':len(B2)})
	for p in A9:
		if p.getparent()is not None:p.getparent().remove(p)
	for O in E['companions_remove']['definitions']:
		if term_defined(H,O):T.append('ההגדרה "%s" נשארה בטיוטה, והסעיף שלה הושמט (%s)'%(O,I('definitions:'+O)))
	for R in Y:
		if R.get('source')!='template_alternative':W.append({'clause':None,'change':'added','answer':R.get('answer'),'source':R['source'],'after':R['after'],'_p':R['p'],'topic':R.get('topic')})
	F.update(replaced=AQ,removed=AB);AC,AD=[],[];B3=bool((Z or{}).get('renumber'))
	if AB or Y or A9 or B3:
		a=labelled_paragraphs(H);assign_segments(a);AW=dict(Ao);AW.update({id(A['p']):(None,A['segment'])for A in Y})
		if Ap:renumber_literal(a,AW,{A['segment']for A in AL}|{A['segment']for A in Y}|({A['segment']for A in a}if B3 else set()));a=labelled_paragraphs(H);assign_segments(a)
		B4,B5={},{};AX={id(A['p']):A['key']for A in a if A['label']}
		for(AY,(U,t))in Ao.items():
			if AY in AX:
				if AX[AY]!=U:B4.setdefault(t,{})[U]=AX[AY]
			else:B5.setdefault(t,set()).add(U)
		BM={id(A['p']):AW.get(id(A['p']),(None,A['segment']))[1]for A in a}
		for M in a:
			K=M['text'];t=BM.get(id(M['p']),M['segment']);f=[]
			for(AE,B6,BN)in find_refs(K):
				L=re.match('(\\d+(?:\\.\\d+)*)',BN);U=L.group(1);AZ=B4.get(t,{})
				if U in AZ:f.append((AE,AE+len(U),AZ[U]));AC.append({'from':U,'to':AZ[U],'context':K[max(0,AE-25):B6+15].strip()})
				elif U in B5.get(t,set()):AD.append({'ref':U,'context':K[max(0,AE-25):B6+15].strip()})
			if f:replace_spans(M['p'],f)
		for B in Y:N=next((A['label']for A in a if A['p']is B['p']),None);B['label']=N
	F.update(added=[{'after':A['after'],'label':A.get('label')}for A in Y],reference_changes=AC,dangling_references=AD);d=sorted({B.group(1)for A in all_paragraphs(H)for B in TAG_RX.finditer(para_text(A))});F['unfilled']=d;Aa=labelled_paragraphs(H);assign_segments(Aa);B7,B8={},None
	for V in Aa:
		if V['label']:B8=norm_label(V['label'])
		B7[id(V['p'])]=B8
	for AF in W:
		A2=AF.pop('_p',None)
		if A2 is not None:AF['clause']=B7.get(id(A2))or AF.get('after')or AF.get('clause')
	B9,Ab,AG={},None,False
	for V in Aa:
		if not V['label']and STOP_SUBTREE.match(V['text'])and re.match('^\\s*(?:ולראיה|IN\\s+WITNESS)',V['text'],re.I):AG=True
		if V['label']:Ab,AG=norm_label(V['label']),False if V['segment']!=n else AG
		if AG or Ab is None:continue
		B9.setdefault(Ab,[]).append(V['p'])
	BO=apply_commercial(H,B9,n,G,Z,Aj,Q);F['commercial']=BO;H.save(A.out);from build_template_registry import docx_text as BP;from check_draft_integrity import count_commercial_marks as BQ,count_placeholders as BR;BA=BP(A.out,limit=400000)[0];F['placeholders']=BR(BA);F['commercial_marks']=BQ(BA);F['adaptations']=W;F['findings']=list((Z or{}).get('findings')or[]);F['driver_effects']={'answers':Ae,'applied':E['applied'],'unanswered':E['unanswered'],'items_present':sorted(set(o)),'items_omitted':sorted(set(A4)),'unapplied':T}
	if AR:F['gap_research']=AR
	if A.clean_copy:F['clean_copy']=os.path.basename(A.clean_copy);strip_commercial_marks(A.out,A.clean_copy)
	BS=os.path.splitext(A.out)[0]+'.report.json';io.open(BS,'w',encoding='utf-8').write(json.dumps(F,ensure_ascii=False,indent=2))
	if A.cover:write_cover(A.cover,F,G,Z,Q)
	print('הטיוטה: %s'%A.out);print('משתנים שמולאו: %d · נשארו מההסכם המקורי: %d · ללא ערך: %d · מצייני חוסר: %d'%(len(Ak),len(Al),len(d),F['placeholders']));print('סעיפים: הוחלפו %d · נוספו %d · נמחקו %d · הפניות שעודכנו %d'%(len(AQ),len(Y),len(AB),len(AC)))
	for R in Y:print('  סעיף חדש אחרי %s קיבל את המספר %s'%(R['after'],R.get('label')or'?'))
	for Ac in AC:print('  הפניה: %s -> %s  ·  %s'%(Ac['from'],Ac['to'],Ac['context']))
	for BB in AD:print('  חוסם: הפניה לסעיף %s שנמחק  ·  %s'%(BB['ref'],BB['context']))
	if d:print('  חוסם: תגיות ללא ערך: %s'%', '.join(d))
	if AJ:print('  שים לב: ערכים לתגיות שאינן בתבנית: %s'%', '.join(AJ))
	for X in F['warnings']:print('  שים לב: '+X)
	Ad=(G.get('cover')or{}).get('main_concern')or{};BC=isinstance(Ad,dict)and bool(Ad.get('answer'))and not Ad.get('clauses')
	if BC:print('  חוסם: החשש העיקרי שמסר הלקוח (cover.main_concern) לא תורגם לאף סעיף')
	if F['commercial_marks']:print('נושאים מסחריים שסומנו בצהוב: %d. הם להכרעת הלקוח, רשומים בדף הליווי ובהודעת המסירה; טיוטה שנשארו בה סימונים אינה נשלחת לצד השני כמו שהיא (--clean-copy).'%F['commercial_marks'])
	for i in F['findings']:print('  ממצא: '+i)
	for BT in T:print('  חוסם: '+BT)
	for BU in E['unanswered']:print('  חוסם: שאלה מכוננת %s בלי תשובה (variance.drivers), וההשפעות שלה לא הוחלו'%BU)
	sys.exit(1 if d or AD or BC or T or E['unanswered']else 0)
def write_cover(path,report,vals,skeleton,lang='he'):
	L=path;G=lang;B=report;import build_draft_docx as A;from docx import Document as T;A.RTL=G!='en';C=COVER['en'if G=='en'else'he'];E=T();A.base(E);F=vals.get('cover')or{};M={A['id']:A.get('label')or A['id']for A in(skeleton or{}).get('variables',[])};A.run(A.para(E,after=2),C['cover']+A.s(F.get('title')or B['template']),16,True,A.NAVY);A.run(A.para(E,after=6),C['stamp']%A.produced_on({'generated_at':B['built_at']}),9.5,False,A.INK_SOFT);H=(B.get('placeholders')or 0)+len(B.get('unfilled')or[]);N=A.tr('lead')
	if H:N+=' '+A.tr('lead_open')%(H,5*max(1,-(-H//5)))
	else:N+=' '+A.tr('lead_clear')
	A.run(A.para(E,after=2),N,12,True,A.INK);A.run(A.para(E,after=10),A.tr('next_fill')if H else A.tr('next_commercial')if B.get('commercial_marks')else A.tr('next_send'),11,False,A.NAVY)
	def D(title,lines):
		B=lines
		if not B:return
		A.h1(E,title)
		for C in B:A.rich(A.para(E,after=2,indent=.5),C,10.5)
	I=F.get('main_concern')or{}
	if isinstance(I,dict)and I.get('answer'):O=I.get('clauses')or[];D(C['concern'],[C['concern_answer']%A.s(I.get('answer')),C['concern_clauses']%', '.join(A.s(B)for B in(O if isinstance(O,list)else[O]))])
	J=F.get('drivers')
	if not J:
		U=B.get('adaptations')or[];J=[]
		for K in(B.get('driver_effects')or{}).get('applied')or[]:V='%s: %s'%(K.get('question'),K.get('answer'));J.append({'question':K.get('question'),'answer':K.get('answer'),'clauses_changed':[A['clause']for A in U if A.get('answer')==V and A.get('clause')]})
	D(A.tr('drivers_title'),A.driver_lines(J));Q=B.get('adaptations')or[];D(A.tr('adapt_title'),A.adaptation_lines(Q))
	if B.get('commercial_marks'):
		A.h1(E,A.tr('commercial_title'));A.para(E,A.tr('commercial_count')%B['commercial_marks'],10.5,True,A.INK,after=4)
		for P in A.commercial_lines(B.get('commercial')or[]):A.rich(A.para(E,after=2,indent=.5),P,10.5)
	R=B.get('gap_research')or{}
	if R.get('topics'):
		A.h1(E,A.tr('research_title'));A.para(E,A.tr('research_lead'),10.5,False,A.INK,after=4)
		for P in A.research_lines(R):A.rich(A.para(E,after=2,indent=.5),P,10.5)
	D(C['findings'],B.get('findings')or[]);D(A.TXT['en'if G=='en'else'he']['choices'],A.choice_lines(F,G));D(A.TXT['en'if G=='en'else'he']['key_dates'],A.key_date_lines(F,G));D(C['filled'],['%s: %s'%(M.get(A,A),(vals.get('variables')or{}).get(A,''))for A in B['filled']])
	if B.get('placeholders')is not None:A.para(E,C['gaps']%B['placeholders'],10.5,True,A.INK,before=6)
	D(C['defaulted'],['%s: %s'%(M.get(A,A),B)for(A,B)in B['defaulted'].items()]);D(C['unfilled'],[C['fill']%M.get(A,A)for A in B['unfilled']])
	if not Q:D(C['removed'],[C['clause']%A['label']for A in B['removed']]);D(C['new'],[C['clause']%A for A in B['replaced']]+[C['added']%(A.get('label')or'',A['after'])for A in B['added']])
	D(C['refs'],[C['ref_line']%(A['from'],A['to'])for A in B['reference_changes']]);D(C['dangling'],[C['dangling_line']%(A['ref'],A['context'])for A in B['dangling_references']]);D(C['options'],['%s: %s'%(A.s(B.get('title')),A.s(B.get('reason')))if isinstance(B,dict)else A.s(B)for B in F.get('options')or[]]);D(C['decisions'],F.get('decisions')or[]);D(C['notes'],(F.get('notes')or[])+B['warnings']);E.save(L);from build_template_registry import docx_text as W;S=A.client_text_problems((None,L),A.RTL,W,A._voice_check)
	if S:
		os.remove(L);print('דף הליווי לא נבנה:')
		for X in S:print('  חוסם: '+X)
		sys.exit(1)
if __name__=='__main__':main()
