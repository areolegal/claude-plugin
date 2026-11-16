#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (c) Areo. All rights reserved. Licensed under the terms at https://areo.co.il/legal/terms
import argparse,datetime,hashlib,io,json,os,re,sys
from docx import Document
from docx.oxml.ns import qn
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from docx_numbering import assign_segments,body_segment,labelled_paragraphs,replace_spans,segment_summary
from build_template_registry import guard_out
try:sys.stdout.reconfigure(encoding='utf-8')
except(AttributeError,ValueError):pass
TAG_RX=re.compile('\\{\\{\\s*([^{}]{1,60}?)\\s*\\}\\}')
BLANK_RX=re.compile('_{2,}|\\.{6,}|…{2,}')
BRACKET_RX=re.compile('\\[(?:[^\\[\\]\\n]{0,40})\\]')
MARKERS=re.compile('\\[\\s*(?:טעון בדיקה משפטית|טעון בדיקת פסיקה|needs legal review|טעון אימות|נוסח חדש[^\\]]*)\\s*\\]',re.I)
VALUE_PATTERNS=[('מספר_זיהוי',re.compile("(?:ח\\.?\\s?פ\\.?|ע\\.?\\s?מ\\.?|ת\\.?\\s?ז\\.?|מס['׳]?\\s*חברה|Company\\s+No\\.?|Reg\\.?\\s+No\\.?)\\s*[:\\-]?\\s*(\\d{8,9})")),('דואל',re.compile('([\\w.+-]+@[\\w-]+\\.[\\w.-]+)')),('טלפון',re.compile('(?<!\\d)(0\\d{1,2}-?\\d{3}-?\\d{4}|\\+972-?\\d{1,2}-?\\d{7})(?!\\d)')),('תאריך',re.compile('(?<!\\d)(\\d{1,2}[./]\\d{1,2}[./](?:\\d{4}|\\d{2}))(?!\\d)')),('סכום',re.compile('((?:₪|\\$|€)\\s*\\d[\\d,]*(?:\\.\\d+)?|\\d[\\d,]*(?:\\.\\d+)?\\s*(?:₪|ש\\"ח|ש״ח|שקלים|NIS|USD|EUR|דולר))'))]
LABEL_TYPES=[('תאריך',('ביום','תאריך','בחודש','שנת','בשנת','מיום','date','dated')),('מספר_זיהוי',('ח.פ','ח. פ','חפ','ע.מ','ת.ז',"מס' חברה",'company no')),('סכום',('סך','ש"ח','ש״ח','₪','תמורה','שכר','amount','fee')),('כתובת',('מרחוב','רחוב','כתובת','address')),('טלפון',('טלפון',"טל'",'phone','tel')),('דואל',('דוא"ל','מייל','email','e-mail')),('שם_צד',('חברת','בין','לבין','שם','name','between'))]
COMPANY_MARK=re.compile('בע\\"מ|בע״מ|\\bLtd\\b|\\bInc\\b|\\bLLC\\b|חברת\\s',re.I)
BODY_START=re.compile('^\\s*(?:הואיל|WHEREAS|R\\s?E\\s?C\\s?I\\s?T\\s?A\\s?L\\s?S|לפיכך)',re.I)
PARTY_LEAD=re.compile('^\\s*(?:-?\\s*ב\\s?י\\s?ן\\s?-?\\s*:?|ל\\s?ב\\s?י\\s?ן\\s*:?|חברת|between\\s*:?|and\\s*:?)\\s*',re.I)
def norm(s):return re.sub('[\\s\\"\'״׳.,()\\-]','',s or'').lower()
FIELD_END=re.compile('_{2,}|\\.{6,}|…{2,}|\\[[^\\[\\]\\n]{0,40}\\]|\\{\\{[^{}]*\\}\\}')
SIGNING_LINE=re.compile('חתימה|חותמת|signature|signed\\s+by',re.I)
def blank_label(text,start):
	C=start;A=text[max(0,C-30):C];B=None
	for D in FIELD_END.finditer(A):B=D
	if B:A=A[B.end():]
	A=re.split('[;,]',A)[-1];A=re.sub('\\s+',' ',A).strip(' :;,–-\t');E=A.split(' ');return' '.join(E[-3:]).strip()
def type_of_label(label):
	A=label.lower()
	for(B,C)in LABEL_TYPES:
		if any(B.lower()in A for B in C):return B
	return'טקסט'
def party_names(rows,company):
	B=company;E,C=[],None
	for D in rows:
		if D['label']or BODY_START.match(D['text']):break
		A=D['text'].strip()
		if not A or not COMPANY_MARK.search(A):continue
		A=PARTY_LEAD.sub('',A);A=re.split('\\s+(?:ח\\.?\\s?פ|ע\\.?\\s?מ|ת\\.?\\s?ז)|,|\\(|;|\\t',A)[0].strip(' :-–')
		if len(A)<3 or BLANK_RX.search(A):continue
		F=bool(B)and(norm(B)in norm(A)or norm(A)in norm(B))
		if C is None:C=F if B else None
		E.append((A,F))
	return E,C
from check_draft_integrity import ACTION_RX,BRACKET_GROUP_ALT_RX,COND_RX,DRAFTER_CUE_RX,NOTE_RX,OPT_HEAD_RX,SELECT_RX,SINGLE_BRACKET_RX,slash_options
from docx_numbering import LITERAL_RX,norm_label,para_text
SPACED_SLASH_RX=re.compile('(?<!\\S)([^\\s/\\[\\]{}()]+)((?:\\s+/\\s+[^\\s/\\[\\]{}()]+)+)')
TIGHT_SLASH_RX=re.compile('(?<![\\w/])([\\w\u0590-\u05ff]+(?:/[\\w\u0590-\u05ff]+)+)(?![\\w/])')
COND_LEAD_RX=re.compile('^\\s*(?:רק\\s+)?(?:אם|ככל\\s+ש|במקרה\\s+ש|כאשר|לשימוש\\s+(?:רק\\s+)?(?:אם|כאשר|במקרה\\s+ש)|לכלול\\s+(?:רק\\s+)?(?:אם|כאשר)|only\\s+if|if|where|when|use\\s+(?:only\\s+)?(?:if|where|when)|include\\s+(?:only\\s+)?(?:if|where|when))\\s*',re.I)
DECISION_RX=re.compile('בחר|החלט|לבחור|להחליט|האם|choose|select|decide|whether',re.I)
def cond_question(condition,lang):
	B=re.sub('^[\\[(]\\s*|\\s*[\\])]$','',condition or'').strip(' :.-');A=COND_LEAD_RX.sub('',B).strip(' :.-')
	if A and A!=B and len(A.split())>=2:return A[0].upper()+A[1:]+'?'if lang=='en'else A+'?'
def _strip_runs_note(doc,notes,current_of):
	for C in list(doc.element.body.iter(qn('w:p'))):
		F=[A for A in C.findall(qn('w:r'))if A.find(qn('w:t'))is not None];A=[]
		def D():
			if not A:return
			B=''.join(B.text or''for A in A for B in A.findall(qn('w:t')));D=[A for A in A if A.find(qn('w:rPr'))is not None and(A.find(qn('w:rPr')).find(qn('w:highlight'))is not None or A.find(qn('w:rPr')).find(qn('w:b'))is not None or A.find(qn('w:rPr')).find(qn('w:shd'))is not None and(A.find(qn('w:rPr')).find(qn('w:shd')).get(qn('w:fill'))or'auto').lower()not in('auto','ffffff'))]
			if D and len(D)==len(A)and len(B.split())>=3 and DRAFTER_CUE_RX.search(B)and not NOTE_RX.search(B):
				notes.append({'source':'highlight','clause':current_of(C),'text':B.strip()})
				for E in A:C.remove(E)
			del A[:]
		for E in F:
			B=E.find(qn('w:rPr'));G=B is not None and(B.find(qn('w:highlight'))is not None or B.find(qn('w:b'))is not None or B.find(qn('w:shd'))is not None)
			if G:A.append(E)
			else:D()
		D()
def _strip_comments(doc,notes,current_of):
	A=doc;from docx.opc.constants import RELATIONSHIP_TYPE as J
	if not any(A.reltype==J.COMMENTS for A in A.part.rels.values()):return
	G={}
	for C in A.comments:G[str(C.comment_id)]=(C.text or'').strip()
	H={}
	for D in A.element.body.iter(qn('w:p')):
		for F in('w:commentRangeStart','w:commentReference'):
			for B in D.iter(qn(F)):H.setdefault(B.get(qn('w:id')),D)
	for(K,I)in G.items():
		if I:D=H.get(K);notes.append({'source':'comment','clause':current_of(D)if D is not None else None,'text':I})
	for F in('w:commentRangeStart','w:commentRangeEnd'):
		for B in list(A.element.body.iter(qn(F))):B.getparent().remove(B)
	for B in list(A.element.body.iter(qn('w:commentReference'))):
		E=B.getparent()
		if E is not None and E.getparent()is not None:E.getparent().remove(E)
	for C in list(A.comments):C._comment_elm.getparent().remove(C._comment_elm)
def _strip_footnotes(doc,source,notes,current_of):
	import zipfile as H
	try:
		with H.ZipFile(source)as F:
			if'word/footnotes.xml'not in F.namelist():return
			I=F.read('word/footnotes.xml').decode('utf-8','ignore')
	except Exception:return
	E={}
	for(C,J)in re.findall('<w:footnote\\b[^>]*w:id="(-?\\d+)"[^>]*>(.*?)</w:footnote>',I,re.S):
		D=re.sub('\\s+',' ',''.join(re.findall('<w:t[^>]*>(.*?)</w:t>',J,re.S))).strip()
		if D and(DRAFTER_CUE_RX.search(D)or NOTE_RX.search(D)):E[C]=D
	for G in list(doc.element.body.iter(qn('w:footnoteReference'))):
		C=G.get(qn('w:id'))
		if C in E:
			B=G.getparent();A=B
			while A is not None and A.tag!=qn('w:p'):A=A.getparent()
			notes.append({'source':'footnote','clause':current_of(A)if A is not None else None,'text':E[C]})
			if B is not None and B.getparent()is not None:B.getparent().remove(B)
def _content_controls(doc,alternatives,current_of,new_id):
	from docx.oxml import OxmlElement as F
	for B in list(doc.element.body.iter(qn('w:sdt'))):
		E=B.find(qn('w:sdtPr'))
		if E is None:continue
		C=E.find(qn('w:dropDownList'))
		if C is None:C=E.find(qn('w:comboBox'))
		if C is None:continue
		D=[(A.get(qn('w:displayText'))or A.get(qn('w:value'))or'').strip()for A in C.findall(qn('w:listItem'))];D=[A for A in D if A];A=B.getparent()
		if len(D)<2 or A is None or A.tag!=qn('w:p'):continue
		G=new_id();alternatives.append({'id':G,'kind':'content_control','clause':current_of(A),'options':[{'value':'V%d'%(A+1),'text':B}for(A,B)in enumerate(D)],'context':para_text(A)[:80]});H=F('w:r');I=F('w:t');I.text='{{%s}}'%G;H.append(I);B.addprevious(H);A.remove(B)
def _option_paragraphs(rows,alternatives,new_id):
	A=rows;B,G=0,None
	while B<len(A):
		E=A[B]
		if E['label']:G=E['label']
		K=para_text(E['p']);L=LITERAL_RX.match(K);M=OPT_HEAD_RX.match(K,L.end()if L else 0)
		if not M:B+=1;continue
		C=[(E,M)];D=B+1
		while D<len(A):
			N=para_text(A[D]['p']);O=LITERAL_RX.match(N);P=OPT_HEAD_RX.match(N,O.end()if O else 0)
			if not P:break
			C.append((A[D],P));D+=1
		if len(C)>=2:
			Q=new_id();H=[]
			for(S,(F,T))in enumerate(C):U=para_text(F['p']);H.append({'value':'V%d'%(S+1),'text':U[T.end():].strip()})
			alternatives.append({'id':Q,'kind':'paragraph','clause':norm_label(G)if G else None,'options':H,'context':H[0]['text'][:80]});R,I=C[0];J=para_text(R['p']);V=I.start()+(len(J[I.start():])-len(J[I.start():].lstrip()));replace_spans(R['p'],[(V,len(J),'{{%s}}'%Q)])
			for(F,W)in C[1:]:F['p'].getparent().remove(F['p'])
		B=D
def learned_questions(alternatives,conditionals,notes,lang):
	G=lang!='en';E,H=[],[]
	for C in alternatives:A=C.get('clause');F=('איזה נוסח מתאים לעסקה הזו בסעיף %s?'%A if A else'איזה נוסח מתאים לעסקה הזו?')if G else'Which wording fits this deal in clause %s?'%A if A else'Which wording fits this deal?';J=[{'value':A['value'],'label':A['text'][:80]}for A in C['options']];E.append({'kind':'alternative','about':C['id'],'clause':A,'question':F,'options':J});H.append({'id':'T-'+C['id'],'question':F,'kind':'choice','options':J,'threshold':None,'source':'template','evidence':[{'template_clause':A}],'effects':{A['value']:{'variant':{C['id']:A['value']}}for A in C['options']},'follow_ups':[],'priority':{'clauses':1,'exposure':'medium'},'derivable_from':None})
	for D in conditionals:A=D.get('clause');F=cond_question(D.get('condition'),lang)or('הסעיף %s רלוונטי לעסקה הזו?'%A if G else'Is clause %s relevant to this deal?'%A);K=[{'value':'yes','label':'כן'if G else'Yes'},{'value':'no','label':'לא'if G else'No'}];E.append({'kind':'conditional','about':D['id'],'clause':A,'question':F,'options':K});H.append({'id':'T-'+D['id'],'question':F,'kind':'yes_no','options':K,'threshold':None,'source':'template','evidence':[{'template_clause':A}],'effects':{'yes':{'include':[D['id']]},'no':{'omit':[D['id']]}},'follow_ups':[],'priority':{'clauses':1,'exposure':'medium'},'derivable_from':None})
	for B in notes:
		if B.get('action_request'):continue
		I=next((A for A in E if A.get('clause')and A['clause']==B.get('clause')),None)
		if I is not None:I.setdefault('explanations',[]).append(B['text']);B['explains']=I['about']
		elif DECISION_RX.search(B['text']):E.append({'kind':'note','about':B['id'],'clause':B.get('clause'),'question':B['text']});B['as_question']=True
	return E,H
def main():
	R=argparse.ArgumentParser();R.add_argument('--source',required=True);R.add_argument('--family',required=True);R.add_argument('--kind',choices=['template','agreement'],required=True);R.add_argument('--out-dir',required=True);R.add_argument('--company',default='');R.add_argument('--force',action='store_true',help='לדרוס master.docx קיים. בלעדיו, תבנית אב שכבר נבנתה אינה נבנית מחדש');D=R.parse_args();guard_out(os.path.join(D.out_dir,'master.docx'),[D.source],D.force);guard_out(os.path.join(D.out_dir,'skeleton.json'),[D.source]);x=os.path.splitext(D.source)[1].lower()
	if x!='.docx':print('הקובץ שמור בפורמט Word ישן או שאינו Word (%s). פתחו אותו ב-Word, בחרו "שמירה בשם" ו-docx, וצרפו שוב.'%(x or'ללא סיומת'));sys.exit(2)
	J=Document(D.source);V=J.element.body
	if V.find('.//'+qn('w:ins'))is not None or V.find('.//'+qn('w:del'))is not None:print('המסמך מכיל שינויים במעקב (redline). תבנית אב נבנית ממסמך נקי: קבלו או דחו את השינויים ב-Word, שמרו, והריצו שוב.');sys.exit(2)
	h='he'if any(re.search('[\u0590-\u05ff]',A.text or'')for A in V.iter(qn('w:t')))else'en';y,z={},None;AG=labelled_paragraphs(J)
	for i in AG:
		if i['label']:z=norm_label(i['label'])
		y[id(i['p'])]=z
	def Z(p):return y.get(id(p))
	G,N,T,a=[],[],[],{'alt':0,'cond':0}
	def j():a['alt']+=1;return'חלופה_%d'%a['alt']
	def AH():a['cond']+=1;return'תנאי_%d'%a['cond']
	_strip_comments(J,G,Z);_strip_footnotes(J,D.source,G,Z);_strip_runs_note(J,G,Z);_content_controls(J,N,Z,j);A0=labelled_paragraphs(J);assign_segments(A0);_option_paragraphs(A0,N,j);O=labelled_paragraphs(J);k=assign_segments(O);l,A1=party_names(O,D.company)if D.kind=='agreement'else([],None);AI=[A for(A,B)in l if not B];U,b,m=[],{},{};F=None;c,d=True,False;e,A2=[],False;f,A3=False,None
	def n(typ,label,context,clause,found):A=typ;m[A]=m.get(A,0)+1;B={'id':'%s_%d'%(A,m[A]),'type':A,'label':label,'context':context,'clause':clause,'in_clause':bool(E['label']),'segment':E['segment'],'found_value':found,'occurrences':1};U.append(B);return B
	for E in O:
		if E['label']:F=E['label']
		B=E['text']
		if not B.strip():continue
		if c and(E['label']or BODY_START.match(B)):c,d=False,False
		if c:
			if re.match('^\\s*(?:ל\\s?ב\\s?י\\s?ן|and)\\b',B,re.I):d=False
			for(S,AJ)in l:
				if S in B:d=AJ
		W,K=[],[]
		def H(s,e):return all(e<=A or s>=B for(A,B)in K)
		def o(s,e,v):W.append((s,e,'{{%s}}'%v['id']));K.append((s,e))
		def p(s,e,new,swallow=False):
			A=swallow
			if A and e<len(B)and B[e]==' 'and(s==0 or B[s-1]==' '):e+=1
			elif A and s>0 and B[s-1]==' 'and(e>=len(B)or B[e]in'.,;:)'):s-=1
			W.append((s,e,new));K.append((s,e))
		for A in TAG_RX.finditer(B):K.append((A.start(),A.end()))
		q=False;A4=bool(SELECT_RX.search(B))
		for A in SELECT_RX.finditer(B):
			if H(A.start(),A.end()):p(A.start(),A.end(),'',True);q=True
		for A in NOTE_RX.finditer(B):
			if H(A.start(),A.end()):p(A.start(),A.end(),'',True);q=True;G.append({'source':'bracket','clause':norm_label(F)if F else None,'text':A.group(0).strip('[]()<> ')})
		for A in COND_RX.finditer(B):
			if H(A.start(),A.end()):A5=AH();p(A.start(),A.end(),'{{%s}}'%A5);T.append({'id':A5,'clause':norm_label(F)if F else None,'unit':'clause'if E['label']else'paragraph','condition':A.group(0).strip('[]() '),'context':B[:80]})
		X=[]
		for A in BRACKET_GROUP_ALT_RX.finditer(B):
			if H(A.start(),A.end()):X.append((A.start(),A.end(),[A.strip()for A in re.findall('\\[([^\\[\\]\\n]+)\\]',A.group(0))]));K.append((A.start(),A.end()))
		for A in SINGLE_BRACKET_RX.finditer(B):
			A6=A.group(1)
			if not H(A.start(),A.end())or MARKERS.fullmatch(A.group(0))or A6.strip().lower().startswith(('להשלים','to complete')):continue
			P=slash_options(A6,A4)
			if P:X.append((A.start(),A.end(),P));K.append((A.start(),A.end()))
		for A in SPACED_SLASH_RX.finditer(B):
			Q,I=A.start(),A.end()
			while I>Q and B[I-1]in'.,;:':I-=1
			if H(Q,I):
				P=[A.strip()for A in re.split('\\s+/\\s+',B[Q:I])]
				if len(P)>=2 and all(P):X.append((Q,I,P));K.append((Q,I))
		if A4:
			for A in TIGHT_SLASH_RX.finditer(B):
				if H(A.start(),A.end())and not re.fullmatch('ו/או|and/or|או/ו',A.group(0),re.I):X.append((A.start(),A.end(),A.group(0).split('/')));K.append((A.start(),A.end()))
		for(Q,I,P)in sorted(X):A7=j();N.append({'id':A7,'kind':'inline','clause':norm_label(F)if F else None,'options':[{'value':'V%d'%(A+1),'text':B}for(A,B)in enumerate(P)],'context':B[max(0,Q-30):I+20].strip()});W.append((Q,I,'{{%s}}'%A7))
		for A in TAG_RX.finditer(B):
			if A.group(1).startswith(('חלופה_','תנאי_')):continue
			if not any(B['id']==A.group(1)for B in U):U.append({'id':A.group(1),'type':'טקסט','label':A.group(1),'context':B[max(0,A.start()-30):A.end()+20].strip(),'clause':F,'found_value':None,'occurrences':1})
		if D.kind=='agreement':
			for S in AI:
				for A in re.finditer(re.escape(S),B):
					if H(A.start(),A.end()):
						C=b.get(('שם_צד',S))
						if C:C['occurrences']+=1
						else:C=b['שם_צד',S]=n('שם_צד','שם הצד שכנגד',S,F,S)
						o(A.start(),A.end(),C)
			for(Y,r)in VALUE_PATTERNS:
				for A in r.finditer(B):
					g,s=A.span(1)
					if not H(g,s):continue
					t=A.group(1)
					if c and d:continue
					C=b.get((Y,t))
					if C:C['occurrences']+=1
					else:
						C=b[Y,t]=n(Y,blank_label(B,g)or Y,B[max(0,g-30):s+20].strip(),F,t)
						if Y=='סכום'and E['label']:C['policy_value']=True
					o(g,s,C)
		if re.match('^\\s*(?:ולראיה|IN\\s+WITNESS)',B,re.I):f,A3=True,E['segment']
		elif f and(E['segment']!=A3 or re.match('^\\s*(?:נספח|Annex|Schedule|Exhibit)\\b',B,re.I)):f=False
		AK=(bool(SIGNING_LINE.search(B))or f)and not E['label']
		for A in MARKERS.finditer(B):K.append((A.start(),A.end()));e.append((F,A.group(0)))
		for r in(BLANK_RX,BRACKET_RX):
			for A in r.finditer(B):
				if AK or not H(A.start(),A.end()):continue
				A8=blank_label(B,A.start());C=n(type_of_label(A8),A8 or'שדה ריק',B[max(0,A.start()-30):A.end()+20].strip(),F,None);o(A.start(),A.end(),C)
		if W:replace_spans(E['p'],W)
		u=para_text(E['p']);A9=LITERAL_RX.match(u)
		if q and not(u[A9.end():]if A9 else u).strip()and E['p'].find('.//'+qn('w:drawing'))is None and E['p'].getparent()is not None:
			E['p'].getparent().remove(E['p'])
			if E['label']:A2=True
	for(AL,v)in enumerate(G,1):v['id']='הערה_%d'%AL;v['action_request']=bool(ACTION_RX.search(v['text']))
	AA=[('בתבנית יש הערה שמבקשת פעולה: "%s". Areo אינו מבצע הערות מהתבנית, והיא מובאת כאן לידיעתכם.'if h=='he'else'The template has a note asking for an action: "%s". Areo does not act on notes in a template; it is listed here for your information.')%re.sub('\\s+',' ',A['text'])[:80].strip()for A in G if A['action_request']];AM,AN=learned_questions(N,T,G,h);os.makedirs(D.out_dir,exist_ok=True);AB=os.path.join(D.out_dir,'master.docx');J.save(AB);L=[]
	if k>1:L.append('במסמך %d רצפי מספור (כל נספח מתחיל מ-1). הפניה לסעיף נפתרת בתוך הרצף שלה.'%k)
	w=[A for A in segment_summary(O)]
	if len(w)>1 and w[0]['top_clauses']==1:L.append('הרצף הראשון מכיל סעיף עליון אחד ("%s"), ואחריו המספור מתחיל שוב מ-1. כך Word מציג את המקור; כדאי לבדוק אם זו טעות במסמך.'%w[0]['first'])
	if e:L.append('בתבנית נשארו %d סימוני בדיקה (%s). תבנית אב נשמרת אחרי שנבדקו, וסימון שנשאר ייכנס לכל טיוטה שתמולא ממנה.'%(len(e),', '.join(sorted({A[1]for A in e}))))
	AC='\n'.join(A['text']for A in O)
	if'נספח מקורות'in AC or'נבנתה ללא נייר של החברה'in AC:L.append('המסמך כולל נספח מקורות או הודעה שנבנה ללא נייר של החברה. אלה חומר פנימי של טיוטת מחקר: לשמירה כתבנית, בנו את הטיוטה מחדש מה-JSON המאושר בלי sources ובלי notice.')
	AD=len(V.findall('.//'+qn('w:ffData')))+len(V.findall('.//'+qn('w:sdt')))
	if AD:L.append('%d שדות טופס או בקרי תוכן לא הומרו לתגיות ונשארו כמות שהם.'%AD)
	if D.kind=='agreement'and A1 is False:L.append('החברה אינה מופיעה ראשונה בבלוק הצדדים. ייתכן שזה הנייר של הצד שכנגד, ואז הוא אינו שלד מתאים לנייר הבית.')
	if D.kind=='agreement'and D.company and not any(A for(B,A)in l):L.append('שם החברה לא נמצא בבלוק הצדדים, ולכן לא הוכרע מי הצד שכנגד.')
	AE={'family':D.family,'kind':D.kind,'source_file':os.path.basename(D.source),'source_sha1':hashlib.sha1(open(D.source,'rb').read()).hexdigest(),'built_at':datetime.date.today().isoformat(),'master':'master.docx','company_listed_first':A1,'segments':segment_summary(O),'body_segment':body_segment(O),'clauses':[{'label':A['label'],'level':A['level'],'segment':A['segment'],'title':A['text'].strip()[:60]}for A in O if A['label']and A['p'].getparent()is not None],'variables':U,'optional_clauses':[],'alternatives':N,'conditional_clauses':T,'drafter_notes':G,'findings':AA,'learned_questions':AM,'template_drivers':AN,'language':h,'renumber':A2,'warnings':L};io.open(os.path.join(D.out_dir,'skeleton.json'),'w',encoding='utf-8').write(json.dumps(AE,ensure_ascii=False,indent=2));print('תבנית אב: %s'%AB);print('סעיפים ממוספרים: %d · רצפי מספור: %d · משתנים: %d'%(len(AE['clauses']),k,len(U)))
	for C in U:
		AF=' = %s'%C['found_value']if C['found_value']else''
		if C.get('policy_value'):AF+=' (ייתכן שזה סף של מדיניות ולא פרט של העסקה)'
		AO=('סעיף %s'if C.get('in_clause')else'אחרי סעיף %s')%C['clause']if C['clause']else'פתיח';print('  {{%s}}  %s%s  ·  %s  ·  %s'%(C['id'],C['label'],AF,AO,C['context'][:60]))
	if N or T or G:print('נלמד מהתבנית: חלופות %d · סעיפים מותנים %d · הערות למנסח %d'%(len(N),len(T),len(G)))
	for M in N:print('  {{%s}}  חלופה%s: %s'%(M['id'],' בסעיף %s'%M['clause']if M.get('clause')else'',' | '.join(A['text'][:40]for A in M['options'])))
	for M in T:print('  {{%s}}  סעיף מותנה%s: %s'%(M['id'],' %s'%M['clause']if M.get('clause')else'',M['condition'][:60]))
	for AP in AA:print('ממצא: '+AP)
	for AQ in L:print('שים לב: '+AQ)
if __name__=='__main__':main()
