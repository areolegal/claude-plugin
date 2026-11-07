# -*- coding: utf-8 -*-
# Copyright (c) Areo. All rights reserved. Licensed under the terms at https://areo.co.il/legal/terms
import argparse,io,json,os,re,sys,zipfile
from collections import Counter
from datetime import date
for _s in(sys.stdout,sys.stderr):
	try:_s.reconfigure(encoding='utf-8',errors='replace')
	except(AttributeError,ValueError):pass
HEB=re.compile('[\u0590-\u05ff]')
LAT=re.compile('[A-Za-z]')
SKIP_DIRS={'Areo-נתונים','__pycache__','.git','node_modules'}
EXTS='.docx','.doc','.pdf','.txt','.md','.rtf'
def docx_text(path,limit=60000):
	try:
		with zipfile.ZipFile(path)as A:
			if'word/document.xml'not in A.namelist():return''
			B=A.read('word/document.xml').decode('utf-8','ignore')
		C=' '.join(re.findall('<w:t[^>]*>(.*?)</w:t>',B,re.S));return re.sub('<[^>]+>|\\s+',' ',C)[:limit]
	except Exception:return''
def pdf_text(path,limit=60000):
	B=limit;A=[]
	try:
		try:import pymupdf as D
		except ImportError:import fitz as D
		with D.open(path)as E:
			for C in E:
				A.append(C.get_text())
				if sum(len(A)for A in A)>=B:break
	except ImportError:
		try:
			from pypdf import PdfReader as F
			for C in F(path).pages:
				A.append(C.extract_text()or'')
				if sum(len(A)for A in A)>=B:break
		except Exception:return''
	except Exception:return''
	return re.sub('\\s+',' ',' '.join(A))[:B]
def text_of(path):
	A=path;B=A.lower()
	if B.endswith('.docx'):return docx_text(A)
	if B.endswith('.pdf'):return pdf_text(A)
	if B.endswith(('.txt','.md')):
		try:return io.open(A,encoding='utf-8',errors='ignore').read()[:60000]
		except Exception:return''
	return''
def action_for(result,display_language):
	B=display_language;A=result
	if not B:return
	if A.get('unreadable',0)>A.get('readable',0):return'ask_direct'
	if A.get('readable',0)<5:return'no_ask_small_corpus'
	if A.get('verdict')=='מובהק':return'no_ask_match'if A.get('dominant')==B else'ask'
	return'ask'
def classify(text):
	B=len(HEB.findall(text));D=len(LAT.findall(text));C=B+D
	if C<200:return None,.0
	A=float(B)/C
	if A>=.85:return'he',A
	if A<=.15:return'en',A
	return'bilingual',A
def main():
	D=argparse.ArgumentParser();D.add_argument('--folders',nargs='+',required=True);D.add_argument('--json');D.add_argument('--max-files',type=int,default=400);D.add_argument('--display-language',choices=('he','en'),help='שפת הממשק מהפרופיל; כשנמסרת, הפלט כולל את הפעולה לפי language-policy.md, שלב 2');B=D.parse_args();A=Counter();N=[];O=0
	for J in B.folders:
		if not os.path.isdir(J):print('תיקייה לא נמצאה: %s'%J);continue
		for(P,Q,U)in os.walk(J):
			Q[:]=[A for A in Q if A not in SKIP_DIRS]
			for H in sorted(U):
				if O>=B.max_files:break
				if not H.lower().endswith(EXTS)or H.startswith('~$'):continue
				V=os.path.join(P,H);R=text_of(V)
				if not R:A['unreadable']+=1;continue
				K,E=classify(R);O+=1
				if not K:A['too_short']+=1;continue
				A[K]+=1;N.append({'file':H,'folder':P,'language':K,'hebrew_share':round(E,2)})
	F=A['he']+A['en']+A['bilingual']
	if not F:print('לא נקרא אף מסמך שאפשר לזהות את שפתו. אם ההסכמים הם DOC, RTF או PDF סרוק, הסקריפט אינו קורא אותם, ויש לשאול את המשתמש ישירות.');G={'readable':0,'dominant':None,'unreadable':A['unreadable']}
	else:
		S=[(A[B],B)for B in('he','en','bilingual')if A[B]];S.sort(reverse=True);W,X=S[0];E=float(W)/F
		if E>=.8:I='מובהק'
		elif E>=.6:I='רוב, לא מובהק'
		else:I='מעורב, אין שפה דומיננטית'
		G={'generated_at':date.today().isoformat(),'folders':B.folders,'readable':F,'unreadable':A['unreadable'],'too_short':A['too_short'],'distribution':{'he':A['he'],'en':A['en'],'bilingual':A['bilingual']},'dominant':X,'dominant_share':round(E,2),'verdict':I,'files':N,'usage_rule':'הממצא מוצג למשתמש ואינו מכריע. שפת התוצר נקבעת בתשובת המשתמש ונשמרת בפרופיל בשדה deliverable_language.'};T={'he':'עברית','en':'אנגלית','bilingual':'דו לשוני'};print('נסרקו %d מסמכים קריאים'%F)
		for C in('he','en','bilingual'):
			if A[C]:print('  %-12s %d מסמכים (%d%%)'%(T[C],A[C],round(1e2*A[C]/F)))
		if A['unreadable']:print('  %d מסמכים לא נקראו (DOC, RTF, PDF סרוק או קובץ פגום)'%A['unreadable'])
		print('שפה דומיננטית: %s, %s'%(T[G['dominant']],I))
	L=action_for(G,B.display_language)
	if L:G['action']=L;print('פעולה לפי language-policy.md: %s'%L)
	if B.json:
		C=os.path.normcase(os.path.realpath(B.json))
		if os.path.isfile(C)and C.lower().endswith(EXTS):print('refused: --json הוא קובץ קלט או מסמך קיים: %s'%B.json,file=sys.stderr);sys.exit(2)
		M=os.path.dirname(os.path.abspath(B.json))
		if M and not os.path.isdir(M):os.makedirs(M)
		io.open(B.json,'w',encoding='utf-8').write(json.dumps(G,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
