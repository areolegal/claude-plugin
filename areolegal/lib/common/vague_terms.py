# -*- coding: utf-8 -*-
# Copyright (c) Areo. All rights reserved. Licensed under the terms at https://areo.co.il/legal/terms
import io,json,os,re,sys,unicodedata
TERMS=['סטנדרט מחמיר','רמה מקצועית גבוהה','ברמה (?:מקצועית )?גבוהה','ברמה הגבוהה ביותר','כמקובל בענף','כמקובל בשוק','כנהוג בענף','לפי הנהוג','הסטנדרטים המקובלים','מאמצים מסחריים סבירים','מאמצים סבירים','מאמץ סביר','מיטב המאמצים','מירב המאמצים','מיטב מאמצי(?:ו|ה|הם)','כמיטב יכולת(?:ו|ה|ם)','בהקדם האפשרי','בהקדם','תוך זמן סביר','באופן מיידי','מיידית','באופן מקצועי ויעיל','שביעות רצו(?:ן|נה|נו|נם|נן)(?: (?:המלאה )?של)?','סביר(?:ה|ים|ות)?','מהותי(?:ת|ים|ות)?','best practices?','industry[- ]standard','industry practice','state of the art','high(?:est)? (?:professional )?standards?','(?:all )?best (?:efforts|endeavou?rs)','commercially reasonable (?:efforts|endeavou?rs)','commercially reasonable','(?:all )?reasonable (?:efforts|endeavou?rs)','(?:all )?reasonable assistance','as soon as (?:reasonably )?practicable','as soon as possible','within a reasonable time','in a timely manner','promptly','immediately','to the (?:reasonable )?satisfaction of','satisfactory','good industry practice','workmanlike manner','material(?:ly)?','substantial(?:ly)?']
VAGUE=re.compile('(?<![\\w\u0590-\u05ff])(?:[ובכלמשה]{1,2}(?=[\u0590-\u05ff]))?((?:%s))(?![\\w\u0590-\u05ff])'%'|'.join(TERMS),re.I)
DEFINED_TEST=re.compile('\\bISO\\b|\\bIEC\\b|\\bSOC ?2\\b|ת[\\"״]י|תקן (?:ישראלי|בינלאומי|מס)|לפי תקן|בהתאם לתקן|נספח|annex|schedule|exhibit|appendix|הוראות(?:יה|יו)? בכתב|written instructions|\\d+(?:[.,]\\d+)?\\s*(?:%|ימים|ימי עסקים|שעות|חודשים|days|business days|hours|months)',re.I)
CONTEXT_MAX=200
SENT_END=re.compile('[.;](?=\\s|$)')
def context_of(text,start,end,a=None,b=None):
	E=start;D=end;A=text;a=0 if a is None else a;b=len(A)if b is None else b
	if b-a>CONTEXT_MAX:
		F=max(0,(CONTEXT_MAX-(D-E))//2);B,C=max(a,E-F),min(b,D+F)
		if B>a and' 'in A[B:E]:B=A.index(' ',B)+1
		if C<b and' 'in A[D:C]:C=A.rindex(' ',D,C)
		a,b=B,C
	return A[a:b].strip()
def find(text):
	A=text;A=unicodedata.normalize('NFKC',A or'').replace('\xad','');C=[]
	for B in VAGUE.finditer(A):F=max(A.rfind('.',0,B.start()),A.rfind(';',0,B.start()))+1;G=min([A for A in(A.find('.',B.end()),A.find(';',B.end()))if A>=0]or[len(A)]);D=[A.end()for A in SENT_END.finditer(A,0,B.start())];E=SENT_END.search(A,B.end());C.append({'term':B.group(1),'defined':bool(DEFINED_TEST.search(A[F:G])),'start':B.start(1),'context':context_of(A,B.start(1),B.end(1),D[-1]if D else 0,E.end()if E else len(A))})
	return C
def undefined(text):return[A for A in find(text)if not A['defined']]
def _paragraphs(path):
	A=path;sys.path.insert(0,os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
	if A.lower().endswith('.docx'):from common import docx_tracked as C;return C.received_paragraphs(A)
	with io.open(A,'rb')as D:B=D.read()
	from risk.page_text import is_pdf as E,pdf_text as F
	if E(B):return F(B).split('\n')
	return B.decode('utf-8-sig','replace').split('\n')
def _corpus_paragraphs(data):
	C=data;E=C.get('documents')if isinstance(C,dict)else C
	if not isinstance(E,list):raise ValueError('הקובץ אינו corpus.json של extract_corpus.py')
	for B in E:
		F=B.get('path')or B.get('file')or''
		if'paragraphs'in B:
			for(D,A)in enumerate(B.get('paragraphs')or[]):yield(F,A.get('i',D),A.get('text')or'',{B:A[B]for B in('clause','page')if A.get(B)})
		else:
			for(G,H)in(B.get('parts')or{}).items():
				for(D,A)in enumerate(H):yield(F,A.get('i',D),A.get('text_accept_all')or'',{'part':G})
def main(argv=None):
	A=argv;A=sys.argv[1:]if A is None else A
	if not A or not os.path.exists(A[0]):print('שימוש: vague_terms.py <corpus.json, או קובץ טקסט, docx או PDF>');return 2
	D=[]
	if A[0].lower().endswith('.json'):
		try:
			with io.open(A[0],encoding='utf-8-sig')as H:E=json.load(H)
			I=list(_corpus_paragraphs(E))
		except(ValueError,AttributeError)as F:print('corpus.json לא נקרא: %s'%F);return 2
		for(J,G,C,K)in I:
			for B in find(C):D.append(dict({'file':J,'paragraph':G,'term':B['term'],'defined':B['defined'],'context':B['context'],'text':C[:160]},**K))
		for L in E.get('unreadable')or[]if isinstance(E,dict)else[]:print('לא נקרא, ולכן לא נסרק: %s'%L,file=sys.stderr)
	else:
		try:M=_paragraphs(A[0])
		except Exception as F:print('המסמך לא נקרא (%s). הריצו extract_corpus.py והעבירו את corpus.json'%F);return 2
		for(G,C)in enumerate(M):
			for B in find(C):D.append({'paragraph':G,'term':B['term'],'defined':B['defined'],'context':B['context'],'text':C[:160]})
	print(json.dumps(D,ensure_ascii=False,indent=1));return 0
if __name__=='__main__':sys.exit(main())
