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
def main():
	H=argparse.ArgumentParser();H.add_argument('--source',required=True);H.add_argument('--family',required=True);H.add_argument('--kind',choices=['template','agreement'],required=True);H.add_argument('--out-dir',required=True);H.add_argument('--company',default='');H.add_argument('--force',action='store_true',help='לדרוס master.docx קיים. בלעדיו, תבנית אב שכבר נבנתה אינה נבנית מחדש');C=H.parse_args();guard_out(os.path.join(C.out_dir,'master.docx'),[C.source],C.force);guard_out(os.path.join(C.out_dir,'skeleton.json'),[C.source]);g=os.path.splitext(C.source)[1].lower()
	if g!='.docx':print('הקובץ שמור בפורמט Word ישן או שאינו Word (%s). פתחו אותו ב-Word, בחרו "שמירה בשם" ו-docx, וצרפו שוב.'%(g or'ללא סיומת'));sys.exit(2)
	U=Document(C.source);M=U.element.body
	if M.find('.//'+qn('w:ins'))is not None or M.find('.//'+qn('w:del'))is not None:print('המסמך מכיל שינויים במעקב (redline). תבנית אב נבנית ממסמך נקי: קבלו או דחו את השינויים ב-Word, שמרו, והריצו שוב.');sys.exit(2)
	G=labelled_paragraphs(U);V=assign_segments(G);W,h=party_names(G,C.company)if C.kind=='agreement'else([],None);p=[A for(A,B)in W if not B];J,N,X=[],{},{};K=None;O,P=True,False;Q=[];R,i=False,None
	def Y(typ,label,context,clause,found):A=typ;X[A]=X.get(A,0)+1;B={'id':'%s_%d'%(A,X[A]),'type':A,'label':label,'context':context,'clause':clause,'in_clause':bool(E['label']),'segment':E['segment'],'found_value':found,'occurrences':1};J.append(B);return B
	for E in G:
		if E['label']:K=E['label']
		D=E['text']
		if not D.strip():continue
		if O and(E['label']or BODY_START.match(D)):O,P=False,False
		if O:
			if re.match('^\\s*(?:ל\\s?ב\\s?י\\s?ן|and)\\b',D,re.I):P=False
			for(I,q)in W:
				if I in D:P=q
		Z,S=[],[]
		def a(s,e):return all(e<=A or s>=B for(A,B)in S)
		def b(s,e,v):Z.append((s,e,'{{%s}}'%v['id']));S.append((s,e))
		for A in TAG_RX.finditer(D):
			S.append((A.start(),A.end()))
			if not any(B['id']==A.group(1)for B in J):J.append({'id':A.group(1),'type':'טקסט','label':A.group(1),'context':D[max(0,A.start()-30):A.end()+20].strip(),'clause':K,'found_value':None,'occurrences':1})
		if C.kind=='agreement':
			for I in p:
				for A in re.finditer(re.escape(I),D):
					if a(A.start(),A.end()):
						B=N.get(('שם_צד',I))
						if B:B['occurrences']+=1
						else:B=N['שם_צד',I]=Y('שם_צד','שם הצד שכנגד',I,K,I)
						b(A.start(),A.end(),B)
			for(L,c)in VALUE_PATTERNS:
				for A in c.finditer(D):
					T,d=A.span(1)
					if not a(T,d):continue
					e=A.group(1)
					if O and P:continue
					B=N.get((L,e))
					if B:B['occurrences']+=1
					else:
						B=N[L,e]=Y(L,blank_label(D,T)or L,D[max(0,T-30):d+20].strip(),K,e)
						if L=='סכום'and E['label']:B['policy_value']=True
					b(T,d,B)
		if re.match('^\\s*(?:ולראיה|IN\\s+WITNESS)',D,re.I):R,i=True,E['segment']
		elif R and(E['segment']!=i or re.match('^\\s*(?:נספח|Annex|Schedule|Exhibit)\\b',D,re.I)):R=False
		r=(bool(SIGNING_LINE.search(D))or R)and not E['label']
		for A in MARKERS.finditer(D):S.append((A.start(),A.end()));Q.append((K,A.group(0)))
		for c in(BLANK_RX,BRACKET_RX):
			for A in c.finditer(D):
				if r or not a(A.start(),A.end()):continue
				j=blank_label(D,A.start());B=Y(type_of_label(j),j or'שדה ריק',D[max(0,A.start()-30):A.end()+20].strip(),K,None);b(A.start(),A.end(),B)
		if Z:replace_spans(E['p'],Z)
	os.makedirs(C.out_dir,exist_ok=True);k=os.path.join(C.out_dir,'master.docx');U.save(k);F=[]
	if V>1:F.append('במסמך %d רצפי מספור (כל נספח מתחיל מ-1). הפניה לסעיף נפתרת בתוך הרצף שלה.'%V)
	f=[A for A in segment_summary(G)]
	if len(f)>1 and f[0]['top_clauses']==1:F.append('הרצף הראשון מכיל סעיף עליון אחד ("%s"), ואחריו המספור מתחיל שוב מ-1. כך Word מציג את המקור; כדאי לבדוק אם זו טעות במסמך.'%f[0]['first'])
	if Q:F.append('בתבנית נשארו %d סימוני בדיקה (%s). תבנית אב נשמרת אחרי שנבדקו, וסימון שנשאר ייכנס לכל טיוטה שתמולא ממנה.'%(len(Q),', '.join(sorted({A[1]for A in Q}))))
	l='\n'.join(A['text']for A in G)
	if'נספח מקורות'in l or'נבנתה ללא נייר של החברה'in l:F.append('המסמך כולל נספח מקורות או הודעה שנבנה ללא נייר של החברה. אלה חומר פנימי של טיוטת מחקר: לשמירה כתבנית, בנו את הטיוטה מחדש מה-JSON המאושר בלי sources ובלי notice.')
	m=len(M.findall('.//'+qn('w:ffData')))+len(M.findall('.//'+qn('w:sdt')))
	if m:F.append('%d שדות טופס או בקרי תוכן לא הומרו לתגיות ונשארו כמות שהם.'%m)
	if C.kind=='agreement'and h is False:F.append('החברה אינה מופיעה ראשונה בבלוק הצדדים. ייתכן שזה הנייר של הצד שכנגד, ואז הוא אינו שלד מתאים לנייר הבית.')
	if C.kind=='agreement'and C.company and not any(A for(B,A)in W):F.append('שם החברה לא נמצא בבלוק הצדדים, ולכן לא הוכרע מי הצד שכנגד.')
	n={'family':C.family,'kind':C.kind,'source_file':os.path.basename(C.source),'source_sha1':hashlib.sha1(open(C.source,'rb').read()).hexdigest(),'built_at':datetime.date.today().isoformat(),'master':'master.docx','company_listed_first':h,'segments':segment_summary(G),'body_segment':body_segment(G),'clauses':[{'label':A['label'],'level':A['level'],'segment':A['segment'],'title':A['text'].strip()[:60]}for A in G if A['label']],'variables':J,'optional_clauses':[],'warnings':F};io.open(os.path.join(C.out_dir,'skeleton.json'),'w',encoding='utf-8').write(json.dumps(n,ensure_ascii=False,indent=2));print('תבנית אב: %s'%k);print('סעיפים ממוספרים: %d · רצפי מספור: %d · משתנים: %d'%(len(n['clauses']),V,len(J)))
	for B in J:
		o=' = %s'%B['found_value']if B['found_value']else''
		if B.get('policy_value'):o+=' (ייתכן שזה סף של מדיניות ולא פרט של העסקה)'
		s=('סעיף %s'if B.get('in_clause')else'אחרי סעיף %s')%B['clause']if B['clause']else'פתיח';print('  {{%s}}  %s%s  ·  %s  ·  %s'%(B['id'],B['label'],o,s,B['context'][:60]))
	for t in F:print('שים לב: '+t)
if __name__=='__main__':main()
