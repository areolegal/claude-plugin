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
COVER={'he':{'cover':'דף ליווי: ','stamp':'טיוטה · הופק בתאריך %s','template':'תבנית','filled':'משתנים שמולאו','defaulted':'נשארו כפי שהיו בהסכם המקורי','unfilled':'טעון השלמה','fill':'[להשלים] %s','removed':'סעיפים שהוסרו','clause':'סעיף %s','new':NEW_WORDING,'added':'סעיף חדש %s, אחרי סעיף %s','refs':'הפניות פנימיות שעודכנו','ref_line':'%s עודכן ל-%s','dangling':'הפניות לסעיף שהוסר, לבדיקה','dangling_line':'סעיף %s: %s','decisions':'מה הוחלט בטיוטה','notes':'הערות','run_risk':'להריץ על הטיוטה הערכת סיכונים לפני שהיא יוצאת?','gaps':'בטיוטה יש %d פרטים להשלים, מסומנים בצהוב','concern':'החשש העיקרי שלכם בעסקה','concern_answer':'כלשונכם: %s','concern_clauses':'המענה בטיוטה: סעיפים %s','options':'מוצע כאפשרות, לא נכלל'},'en':{'cover':'Cover note: ','stamp':'Draft · Produced on %s','template':'template','filled':'Variables filled','defaulted':'Left as in the original agreement','unfilled':'To complete','fill':'[to complete] %s','removed':'Clauses removed','clause':'Clause %s','new':NEW_WORDING_EN,'added':'New clause %s, after clause %s','refs':'Internal references updated','ref_line':'%s updated to %s','dangling':'References to a removed clause, to check','dangling_line':'Clause %s: %s','decisions':'Decisions','notes':'Notes','run_risk':'Run a risk assessment on the draft before it goes out?','gaps':'The draft has %d details to complete, highlighted in yellow','concern':'Your main concern in this deal','concern_answer':'In your words: %s','concern_clauses':'Where the draft answers it: clauses %s','options':'Offered as an option, not included'}}
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
def fill_variables(doc,values,skeleton):
	E=values;C,G={},{};F={A['id']:A.get('found_value')for A in(skeleton or{}).get('variables',[])if A.get('found_value')}
	for H in all_paragraphs(doc):
		I=para_text(H);D=[]
		for B in TAG_RX.finditer(I):
			A=B.group(1)
			if A in E:D.append((B.start(),B.end(),str(E[A])));C[A]=C.get(A,0)+1
			elif A in F:D.append((B.start(),B.end(),F[A]));G[A]=F[A]
		if D:replace_spans(H,D)
	J=sorted({B.group(1)for A in all_paragraphs(doc)for B in TAG_RX.finditer(para_text(A))});K=sorted(A for A in E if A not in C);return C,G,J,K
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
def comment(doc,p,author,lang='he'):
	A=author;C=Paragraph(p,doc._body);B=[A for A in C.runs if A.text]
	if not B:return False
	try:D=''.join(A[0]for A in(A or'Areo').split()[:2]);doc.add_comment(B,text=NEW_WORDING_EN if lang=='en'else NEW_WORDING,author=A or'Areo',initials=D);return True
	except Exception:return False
def main():
	K=argparse.ArgumentParser();K.add_argument('--template',required=True);K.add_argument('--values',required=True);K.add_argument('--out',required=True);K.add_argument('--cover');K.add_argument('--skeleton',help='ברירת מחדל: skeleton.json שליד התבנית');K.add_argument('--lang',choices=('he','en'),help='שפת הבועות ודף הליווי; בלעדיו: language ב-values.json, ואחריו שפת התבנית');K.add_argument('--force',action='store_true',help='לדרוס טיוטה או דף ליווי קיימים (הרצה חוזרת אחרי תיקון)');A=K.parse_args();X=A.skeleton or os.path.join(os.path.dirname(os.path.abspath(A.template)),'skeleton.json');Y=[A.template,A.values,X];guard_out(A.out,Y,A.force);guard_out(os.path.splitext(A.out)[0]+'.report.json',Y)
	if A.cover:guard_out(A.cover,Y+[A.out],A.force)
	H=json.load(io.open(A.values,encoding='utf-8'));Z=json.load(io.open(X,encoding='utf-8'))if os.path.isfile(X)else None;I=Document(A.template);l=str(A.lang or H.get('language')or template_lang(I)).strip().lower();Q='en'if l[:2]=='en'or l in('english','אנגלית')else'he';m=H.get('author')or'Areo';F={'template':os.path.basename(A.template),'built_at':datetime.date.today().isoformat(),'warnings':[]};n,o,N,a=fill_variables(I,H.get('variables')or{},Z);F.update(filled=sorted(n),defaulted=o,unfilled=N,unknown_variables=a);B=labelled_paragraphs(I);assign_segments(B);A2=H.get('segment',(Z or{}).get('body_segment',body_segment(B)));p={}
	for D in B:
		if D['label']:p.setdefault(D['key'],set()).add(D['segment'])
	q={id(A['p']):(A['key'],A['segment'])for A in B if A['label']};r=not any(A['kind']=='auto'for A in B)and any(A['kind']=='literal'for A in B);s={}
	for(C,D)in enumerate(B):
		if D['label']:s.setdefault((D['key'],D['segment']),C)
	def b(label):
		D=label;A,B=parse_target(D,A2);C=s.get((A,B))
		if C is not None and'@'not in str(D)and len(p.get(A,()))>1:F['warnings'].append(('Clause %s exists in more than one numbering sequence; the agreement body was chosen (sequence %d). For an annex: "%s@<sequence>".'if Q=='en'else'סעיף %s קיים ביותר מרצף מספור אחד; נבחר גוף ההסכם (רצף %d). לנספח: "%s@<רצף>".')%(A,B,A))
		if C is None:F['warnings'].append(('Clause %s was not found in sequence %d.'if Q=='en'else'לא נמצא סעיף %s ברצף %d.')%(A,B))
		return C
	t,u=[],[]
	for J in H.get('remove_clauses')or[]:
		C=b(J)
		if C is not None:t.append((J,subtree(B,C)));u.append({'segment':B[C]['segment']})
	c,L=[],[]
	for(J,E)in(H.get('replace_clauses')or{}).items():
		C=b(J)
		if C is None:continue
		if B[C]['kind']=='literal':
			O=LITERAL_RX.match(B[C]['text'])
			if O and not LITERAL_RX.match(E):E=B[C]['text'][:O.end(1)]+' '+E.lstrip()
		set_text_keep_format(B[C]['p'],E);comment(I,B[C]['p'],m,Q);c.append(norm_label(J))
	for P in H.get('add_clauses')or[]:
		C=b(P.get('after'))
		if C is None:continue
		A3=subtree(B,C)[-1];S=copy.deepcopy(B[C]['p']);E=P.get('text','')
		if r:O=re.match('^\\s*\\S+\\s*',B[C]['text']);E=(O.group(0)if O else'')+E
		set_text_keep_format(S,E);A3.addnext(S);comment(I,S,m,Q);L.append({'after':norm_label(P.get('after')),'p':S,'segment':B[C]['segment']})
	T=[]
	for(J,v)in t:
		for d in v:
			if d.getparent()is not None:d.getparent().remove(d)
		T.append({'label':norm_label(J),'paragraphs':len(v)})
	F.update(replaced=c,removed=T);U,V=[],[]
	if T or L:
		M=labelled_paragraphs(I);assign_segments(M);e=dict(q);e.update({id(A['p']):(None,A['segment'])for A in L})
		if r:renumber_literal(M,e,{A['segment']for A in u}|{A['segment']for A in L});M=labelled_paragraphs(I);assign_segments(M)
		w,x={},{};f={id(A['p']):A['key']for A in M if A['label']}
		for(g,(G,R))in q.items():
			if g in f:
				if f[g]!=G:w.setdefault(R,{})[G]=f[g]
			else:x.setdefault(R,set()).add(G)
		A4={id(A['p']):e.get(id(A['p']),(None,A['segment']))[1]for A in M}
		for D in M:
			E=D['text'];R=A4.get(id(D['p']),D['segment']);h=[]
			for(W,y,A5)in find_refs(E):
				O=re.match('(\\d+(?:\\.\\d+)*)',A5);G=O.group(1);i=w.get(R,{})
				if G in i:h.append((W,W+len(G),i[G]));U.append({'from':G,'to':i[G],'context':E[max(0,W-25):y+15].strip()})
				elif G in x.get(R,set()):V.append({'ref':G,'context':E[max(0,W-25):y+15].strip()})
			if h:replace_spans(D['p'],h)
		for P in L:J=next((A['label']for A in M if A['p']is P['p']),None);P['label']=J
	F.update(added=[{'after':A['after'],'label':A.get('label')}for A in L],reference_changes=U,dangling_references=V);N=sorted({B.group(1)for A in all_paragraphs(I)for B in TAG_RX.finditer(para_text(A))});F['unfilled']=N;I.save(A.out);from build_template_registry import docx_text as A6;from check_draft_integrity import count_placeholders as A7;F['placeholders']=A7(A6(A.out,limit=400000)[0]);A8=os.path.splitext(A.out)[0]+'.report.json';io.open(A8,'w',encoding='utf-8').write(json.dumps(F,ensure_ascii=False,indent=2))
	if A.cover:write_cover(A.cover,F,H,Z,Q)
	print('הטיוטה: %s'%A.out);print('משתנים שמולאו: %d · נשארו מההסכם המקורי: %d · ללא ערך: %d · מצייני חוסר: %d'%(len(n),len(o),len(N),F['placeholders']));print('סעיפים: הוחלפו %d · נוספו %d · נמחקו %d · הפניות שעודכנו %d'%(len(c),len(L),len(T),len(U)))
	for z in L:print('  סעיף חדש אחרי %s קיבל את המספר %s'%(z['after'],z.get('label')or'?'))
	for j in U:print('  הפניה: %s -> %s  ·  %s'%(j['from'],j['to'],j['context']))
	for A0 in V:print('  חוסם: הפניה לסעיף %s שנמחק  ·  %s'%(A0['ref'],A0['context']))
	if N:print('  חוסם: תגיות ללא ערך: %s'%', '.join(N))
	if a:print('  שים לב: ערכים לתגיות שאינן בתבנית: %s'%', '.join(a))
	for A9 in F['warnings']:print('  שים לב: '+A9)
	k=(H.get('cover')or{}).get('main_concern')or{};A1=isinstance(k,dict)and bool(k.get('answer'))and not k.get('clauses')
	if A1:print('  חוסם: החשש העיקרי שמסר הלקוח (cover.main_concern) לא תורגם לאף סעיף')
	sys.exit(1 if N or V or A1 else 0)
def write_cover(path,report,vals,skeleton,lang='he'):
	J=path;G=lang;C=report;import build_draft_docx as A;from docx import Document as O;A.RTL=G!='en';B=COVER['en'if G=='en'else'he'];E=O();A.base(E);F=vals.get('cover')or{};K={A['id']:A.get('label')or A['id']for A in(skeleton or{}).get('variables',[])};A.run(A.para(E,after=2),B['cover']+A.s(F.get('title')or C['template']),16,True,A.NAVY);A.run(A.para(E,after=6),B['stamp']%A.produced_on({'generated_at':C['built_at']}),9.5,False,A.INK_SOFT);H=(C.get('placeholders')or 0)+len(C.get('unfilled')or[]);L=A.tr('lead')
	if H:L+=' '+A.tr('lead_open')%(H,5*max(1,-(-H//5)))
	else:L+=' '+A.tr('lead_clear')
	A.run(A.para(E,after=2),L,12,True,A.INK);A.run(A.para(E,after=10),A.tr('next_fill')if H else A.tr('next_send'),11,False,A.NAVY)
	def D(title,lines):
		B=lines
		if not B:return
		A.h1(E,title)
		for C in B:A.rich(A.para(E,after=2,indent=.5),C,10.5)
	I=F.get('main_concern')or{}
	if isinstance(I,dict)and I.get('answer'):M=I.get('clauses')or[];D(B['concern'],[B['concern_answer']%A.s(I.get('answer')),B['concern_clauses']%', '.join(A.s(B)for B in(M if isinstance(M,list)else[M]))])
	D(A.TXT['en'if G=='en'else'he']['choices'],A.choice_lines(F,G));D(A.TXT['en'if G=='en'else'he']['key_dates'],A.key_date_lines(F,G));D(B['filled'],['%s: %s'%(K.get(A,A),(vals.get('variables')or{}).get(A,''))for A in C['filled']])
	if C.get('placeholders')is not None:A.para(E,B['gaps']%C['placeholders'],10.5,True,A.INK,before=6)
	D(B['defaulted'],['%s: %s'%(K.get(A,A),B)for(A,B)in C['defaulted'].items()]);D(B['unfilled'],[B['fill']%K.get(A,A)for A in C['unfilled']]);D(B['removed'],[B['clause']%A['label']for A in C['removed']]);D(B['new'],[B['clause']%A for A in C['replaced']]+[B['added']%(A.get('label')or'',A['after'])for A in C['added']]);D(B['refs'],[B['ref_line']%(A['from'],A['to'])for A in C['reference_changes']]);D(B['dangling'],[B['dangling_line']%(A['ref'],A['context'])for A in C['dangling_references']]);D(B['options'],['%s: %s'%(A.s(B.get('title')),A.s(B.get('reason')))if isinstance(B,dict)else A.s(B)for B in F.get('options')or[]]);D(B['decisions'],F.get('decisions')or[]);D(B['notes'],(F.get('notes')or[])+C['warnings']);A.para(E,B['run_risk'],10.5,True,A.INK,before=14);E.save(J);from build_template_registry import docx_text as P;N=A.client_text_problems((None,J),A.RTL,P,A._voice_check)
	if N:
		os.remove(J);print('דף הליווי לא נבנה:')
		for Q in N:print('  חוסם: '+Q)
		sys.exit(1)
if __name__=='__main__':main()
