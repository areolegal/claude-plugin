#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (c) Areo. All rights reserved. Licensed under the terms at https://areo.co.il/legal/terms
'קורא פלייבוק של הלקוח ממסמך Word, PDF או Excel, בלי לכתוב דבר לתיקיית הלקוח.'
import argparse,io,json,os,re,sys
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
import areo_lib
from common.cli import OutputRefused,guard_out,load_docx_or_explain
TRACK_WORDS={'red':'מסלול אדום|קו(?:ים)? אדום|קווים אדומים|אדום|לא מקובל(?:ת)?|לא מתקבל|red[\\s\\-]lines?|red|unacceptable|not acceptable|walk[\\s\\-]?away|deal[\\s\\-]?breakers?|no[\\s\\-]?go','yellow':'מסלול צהוב|צהוב|עמדת נסיגה|נסיגה|ויתור מותר|פשרה|yellow|fall[\\s\\-]?back|acceptable|compromise','green':'מסלול ירוק|ירוק|עמדה מועדפת|מועדפ(?:ת|ים|ות)|מועדף|רגיל(?:ה)?|ברירת מחדל|העמדה שלנו|green|preferred(?: position)?|standard(?: position)?|ideal'}
_LB,_LA='(?<![^\\W\\d_])','(?![^\\W\\d_])'
TRACK_LABELS={A:'^(?:ה)?(?:%s)%s(?!\\s+flags)'%(B,_LA)for(A,B)in TRACK_WORDS.items()}
FIELD_LABELS={'red_flags':'^(?:סימני אדום|סימני זיהוי|סימנים|red flags|flags|watch for)\\b','alternatives':'^(?:נוסח חלופי|נוסח מוצע|נוסח|alternative wording|proposed wording|wording|clause)\\b','segment':'^(?:סגמנט|פלח|segment)\\b','notes':'^(?:הערה|הערות|הסבר|נימוק|note|notes|rationale)\\b'}
OPERATING=re.compile('הוראות הפעלה|כללי הפעלה|אופן השימוש|operating (?:rules|instructions)|how to use',re.I)
HEADER_TRACKS={A:re.compile(_LB+'(?:[וה])?(?:%s)'%B+_LA,re.I)for(A,B)in TRACK_WORDS.items()}
HEADER_TOPIC=re.compile(_LB+'(?:ה)?(?:נושא|סעיף|topic|clause|issue|term|provision)s?'+_LA,re.I)
HEADER_FLAGS=re.compile('סימני|flags',re.I)
def strip_label(text,rx):return re.sub(rx+'\\s*[:\\-.]?\\s*','',text,count=1,flags=re.I).strip()
def header_track(h):
	if HEADER_FLAGS.search(h):return
	return next((A for(A,B)in HEADER_TRACKS.items()if B.search(h)),None)
def topic_from_table(rows):
	B=rows
	for(K,L)in enumerate((B or[])[:10]):
		D=[str(A or'')for A in L];H=[header_track(A)for A in D];I={A:next((B for(B,C)in enumerate(H)if C==A),None)for A in('green','yellow','red')}
		if sum(A is not None for A in I.values())>=2:B=B[K:];break
	else:return[]
	E=next((A for(A,B)in enumerate(D)if HEADER_TOPIC.search(B)and H[A]is None),0);C=next((A for(A,B)in enumerate(D)if HEADER_FLAGS.search(B)),None);J=[]
	for A in B[1:]:
		A=[str(A or'').strip()for A in A]
		if not any(A)or E>=len(A)or not A[E]:continue
		F={'topic':A[E],'red_flags':[],'alternatives':[],'notes':[]}
		for(M,G)in I.items():F[M]=A[G]if G is not None and G<len(A)else''
		if C is not None and C<len(A)and A[C]:F['red_flags']=[A.strip()for A in re.split('[;\\n•]',A[C])if A.strip()]
		J.append(F)
	return J
def topics_from_lines(lines):
	E,H,I,B,F=[],[],[],None,False
	for(A,J)in lines:
		A=A.strip()
		if not A:continue
		if J:
			F=bool(OPERATING.search(A))
			if not F:B={'topic':re.sub('^\\d+(?:\\.\\d+)*[.)]?\\s*','',A),'green':'','yellow':'','red':'','red_flags':[],'alternatives':[],'notes':[]};E.append(B)
			continue
		if F:I.append(A);continue
		if B is None:continue
		for(C,D)in TRACK_LABELS.items():
			if re.search(D,A,re.I):B[C]=(B[C]+' '+strip_label(A,D)).strip();break
		else:
			for(C,D)in FIELD_LABELS.items():
				if re.search(D,A,re.I):
					G=strip_label(A,D)
					if C=='segment':H.append({'topic':B['topic'],'segment':G})
					elif C=='red_flags':B['red_flags']+=[A.strip()for A in re.split('[;•]',G)if A.strip()]
					else:B[C].append(G)
					break
			else:B['notes'].append(A)
	E=[A for A in E if A['green']or A['yellow']or A['red']or A['red_flags']];return E,H,I
def read_docx(path,d=None):
	if d is None:import docx;d=docx.Document(path)
	C=[]
	for E in d.tables:C+=topic_from_table([[A.text for A in A.cells]for A in E.rows])
	D=[]
	for A in d.paragraphs:B=A.text.strip();F=(A.style.name or'').lower()if A.style is not None else'';G=bool(A.runs)and all(A.bold for A in A.runs if A.text.strip());H=F.startswith(('heading','כותרת','title'))or len(B)<=70 and(G or re.match('^\\d+(?:\\.\\d+)?[.)]\\s+\\S',B))and not re.search('[.:]$',B)and not any(re.search(A,B,re.I)for A in list(TRACK_LABELS.values())+list(FIELD_LABELS.values()));D.append((B,H))
	I,J,K=topics_from_lines(D);return C+I,J,K
def read_pdf(path):
	from risk.page_text import PdfTextUnavailable as C,pdf_text as D
	with open(path,'rb')as E:F=E.read()
	try:G=D(F)
	except C as H:raise ValueError('ה-PDF אינו נקרא (%s): בקשו מהלקוח עותק Word'%H)
	B=[]
	for I in G.splitlines():A=I.strip();J=bool(re.match('^\\d+(?:\\.\\d+)?[.)]?\\s+\\S',A))and len(A)<=70 and not re.search('[.:]$',A);B.append((A,J))
	return topics_from_lines(B)
def read_xlsx(path):
	try:import openpyxl as F
	except ImportError:raise ValueError('לקריאת Excel נדרש openpyxl (pip install openpyxl)')
	G=F.load_workbook(path,read_only=True,data_only=True);A,B=[],[]
	for C in G.worksheets:
		D=[list(A)for A in C.iter_rows(values_only=True)];E=topic_from_table(D)
		if E:A+=E
		elif OPERATING.search(C.title or''):B+=[' '.join(str(A)for A in A if A)for A in D if any(A)]
	return A,[],B
def main(argv=None):
	sys.dont_write_bytecode=True;sys.stdout.reconfigure(encoding='utf-8',errors='replace');D=argparse.ArgumentParser(description=__doc__.split('\n')[0]);D.add_argument('file');D.add_argument('--out',help='קובץ JSON בתיקייה זמנית; לעולם לא בתיקיית הלקוח');A=D.parse_args(argv)
	if not os.path.exists(A.file):print('המסמך אינו קיים: %s'%A.file);return 2
	if A.out and os.path.commonpath([os.path.realpath(A.out),os.path.realpath(os.path.dirname(A.file))])==os.path.realpath(os.path.dirname(A.file)):print('--out בתיקיית הלקוח (%s). הקורא אינו כותב לשם; בחרו תיקייה זמנית.'%os.path.dirname(A.file));return 1
	if A.out:
		try:guard_out(A.out,inputs=[A.file])
		except OutputRefused as E:print('סירוב: %s'%E);return 1
	B=os.path.splitext(A.file)[1].lower();F=None
	if B in('.docx','.doc','.docm'):
		F,J,K=load_docx_or_explain(A.file)
		if F is None:print(J);return K
	try:
		if B in('.docx','.doc','.docm'):C,G,H=read_docx(A.file,F)
		elif B=='.pdf':C,G,H=read_pdf(A.file)
		elif B in('.xlsx','.xlsm'):C,G,H=read_xlsx(A.file)
		else:print('פורמט שאינו נקרא: %s. Word, PDF או Excel.'%B);return 2
	except ValueError as E:print(str(E));return 3
	I={'source':os.path.basename(A.file),'format':B[1:],'topics':C,'segments':G,'operating_rules':H}
	if A.out:
		with io.open(A.out,'w',encoding='utf-8')as L:json.dump(I,L,ensure_ascii=False,indent=1)
	print(json.dumps(I,ensure_ascii=False,indent=1))
	if not C:print('לא נמצא במסמך אף נושא עם מסלולים. ייתכן שאינו פלייבוק, או שהוא מסמך רקע (n1b-learning.md, "מסמך רקע אינו מועמד").');return 3
	return 0
if __name__=='__main__':sys.exit(main())
