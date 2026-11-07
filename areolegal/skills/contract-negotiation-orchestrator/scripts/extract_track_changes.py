# -*- coding: utf-8 -*-
# Copyright (c) Areo. All rights reserved. Licensed under the terms at https://areo.co.il/legal/terms
import argparse
from datetime import date as _date
def _he_date(d):return'%d.%d.%d'%(d.day,d.month,d.year)
import json,os,re,sys,zipfile
from pathlib import Path
from xml.etree import ElementTree as ET
for _s in(sys.stdout,sys.stderr):
	try:_s.reconfigure(encoding='utf-8',errors='replace')
	except(AttributeError,ValueError):pass
try:sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)));import areo_lib;from common.cli import OutputRefused,guard_out,load_docx_or_explain
except ImportError:
	class OutputRefused(Exception):0
	def guard_out(out,inputs=()):
		A=out;B=os.path.normcase(os.path.realpath(A))
		if any(A and os.path.normcase(os.path.realpath(A))==B for A in inputs):raise OutputRefused('--output הוא קובץ קלט: %s'%A)
		if os.path.isfile(B)and B.lower().endswith(('.docx','.doc','.docm','.dotx','.pdf','.xlsx','.pptx')):raise OutputRefused('--output הוא מסמך קיים: %s'%A)
		return os.path.abspath(A)
	def load_docx_or_explain(path,loader=None,strict_ok=False):
		A=path
		if not os.path.exists(A):return None,'הקובץ לא נמצא: %s\nFile not found: %s'%(A,A),1
		try:
			with zipfile.ZipFile(A)as D:D.getinfo('word/document.xml')
			return A,None,0
		except Exception as B:C=os.path.basename(A);return None,'לא ניתן לקרוא את %s כמסמך Word (%s).\n%s cannot be read as a Word document (%s).'%(C,type(B).__name__,C,type(B).__name__),2
NS={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main','w14':'http://schemas.microsoft.com/office/word/2010/wordml','w15':'http://schemas.microsoft.com/office/word/2012/wordml'}
for(prefix,uri)in NS.items():ET.register_namespace(prefix,uri)
def _q(tag):A,B=tag.split(':');return f"{{{NS[A]}}}{B}"
def _get_text_from_run(run_elem):
	A=[]
	for B in run_elem.iter(_q('w:t')):
		if B.text:A.append(B.text)
	return''.join(A)
def _get_paragraph_index(para,all_paras):
	for(A,B)in enumerate(all_paras):
		if B is para:return A
	return-1
def _get_paragraph_text(para):
	A=[]
	for B in para.iter(_q('w:t')):
		if B.text:A.append(B.text)
	return''.join(A)
def _get_paragraph_first_words(para,n=5):A=_get_paragraph_text(para).strip();B=A.split();return' '.join(B[:n])
def extract_track_changes(docx_path):
	J=docx_path;J=Path(J)
	if not J.exists():raise FileNotFoundError(f"קובץ לא נמצא: {J}")
	K=[];D=[]
	with zipfile.ZipFile(J,'r')as R:
		with R.open('word/document.xml')as L:o=ET.parse(L)
		p=o.getroot();A={}
		try:
			with R.open('word/comments.xml')as L:q=ET.parse(L)
			r=q.getroot()
			for M in r.iter(_q('w:comment')):
				C=M.get(_q('w:id'));N=M.get(_q('w:author'));O=M.get(_q('w:date'));Y=''
				for Z in M.iter(_q('w:t')):
					if Z.text:Y+=Z.text
				a=list(M.iter(_q('w:p')));A[C]={'id':C,'author':N,'date':O,'text':Y,'para_id':a[-1].get(_q('w14:paraId'))if a else None}
		except KeyError:pass
		b={}
		try:
			with R.open('word/commentsExtended.xml')as L:
				for S in ET.parse(L).getroot().iter(_q('w15:commentEx')):b[S.get(_q('w15:paraId'))]=S.get(_q('w15:paraIdParent')),S.get(_q('w15:done'))=='1'
		except KeyError:pass
		c={A['para_id']:A for A in A.values()if A.get('para_id')}
		for B in A.values():d,s=b.get(B.get('para_id'),(None,False));B['parent_id']=c[d]['id']if d in c else None;B['done']=s
		for B in A.values():
			F,e=B,set()
			while F.get('parent_id')in A and F['id']not in e:e.add(F['id']);F=A[F['parent_id']]
			B['thread_root_id']=F['id']
		f=p.find(_q('w:body'))
		if f is None:return{'changes':[],'comments':[]}
		t=list(f.iter(_q('w:p')))
		for(P,G)in enumerate(t):
			T=_get_paragraph_text(G);g=_get_paragraph_first_words(G);U=g if g else f"פסקה ריקה {P}"
			for H in G.iter(_q('w:ins')):
				N=H.get(_q('w:author'),'unknown');O=H.get(_q('w:date'),'');V=''
				for u in H.iter(_q('w:r')):V+=_get_text_from_run(u)
				if V:K.append({'type':'insertion','paragraph_index':P,'paragraph_locator':U,'paragraph_full_text':T,'old_text':'','new_text':V,'author':N,'date':O})
			h={}
			for H in G.iter(_q('w:ins')):
				for v in H.iter(_q('w:del')):h[id(v)]=H.get(_q('w:author'),'unknown')
			for Q in G.iter(_q('w:del')):
				N=Q.get(_q('w:author'),'unknown');O=Q.get(_q('w:date'),'');W=''
				for i in Q.iter(_q('w:delText')):
					if i.text:W+=i.text
				if W:K.append({'type':'deletion','paragraph_index':P,'paragraph_locator':U,'paragraph_full_text':T,'old_text':W,'new_text':'','author':N,'date':O,'inside_insertion_by':h.get(id(Q))})
			for w in G.iter(_q('w:commentReference')):
				C=w.get(_q('w:id'))
				if C in A:E=A[C].copy();E['paragraph_index']=P;E['paragraph_locator']=U;E['paragraph_full_text']=T;D.append(E)
	j={A['id']for A in D}
	for(C,B)in A.items():
		if C not in j:
			I=next((A for A in D if A['id']==B.get('thread_root_id')),None);E=B.copy()
			for k in('paragraph_index','paragraph_locator','paragraph_full_text'):E[k]=I.get(k)if I else None
			D.append(E);j.add(C)
	l={}
	for B in D:l.setdefault(B.get('thread_root_id')or B['id'],[]).append(B['id'])
	m=[]
	for(X,x)in l.items():I=A.get(X)or{};n=[A[B]for B in x if B!=X and B in A];m.append({'root_id':X,'root_author':I.get('author'),'done':bool(I.get('done')),'replies':[{'id':A['id'],'author':A['author'],'date':A['date']}for A in n],'answered_by_other':any(A['author']!=I.get('author')for A in n)})
	return{'changes':K,'comments':D,'threads':m,'total_changes':len(K),'total_comments':len(D),'future_dated':future_dated(K,A.values())}
def future_dated(changes,comments,today=None):B=(today or _date.today()).isoformat();A=[{'kind':'comment','author':A.get('author'),'date':A.get('date')}for A in comments if(A.get('date')or'')[:10]>B];A+=[{'kind':A.get('type'),'author':A.get('author'),'date':A.get('date')}for A in changes if(A.get('date')or'')[:10]>B];return A
def merge_paired_changes(extracted):
	C=extracted;B=C['changes']
	if not B:return C
	E=[];F=False
	for(D,A)in enumerate(B):
		if F:F=False;continue
		if D+1<len(B)and A['type']=='deletion'and B[D+1]['type']=='insertion'and A['paragraph_index']==B[D+1]['paragraph_index']and A['author']==B[D+1]['author']:E.append({'type':'modification','paragraph_index':A['paragraph_index'],'paragraph_locator':A['paragraph_locator'],'paragraph_full_text':A['paragraph_full_text'],'old_text':A['old_text'],'new_text':B[D+1]['new_text'],'author':A['author'],'date':A['date']});F=True
		else:E.append(A)
	C['changes']=E;C['total_changes']=len(E);return C
def compare_rounds(current_extracted,previous_extracted):
	B=current_extracted;I=B['changes'];C=previous_extracted['changes']
	def D(ch):return ch.get('paragraph_locator',''),ch.get('new_text',''),ch.get('old_text','')
	E={D(A):A for A in C};F={A['paragraph_locator']:A for A in C};G=[]
	for A in I:
		H=D(A)
		if H in E:A['comparison_status']='REPEATED';A['previous_round']=E[H]
		elif A['paragraph_locator']in F:A['comparison_status']='EVOLVED';A['previous_round']=F[A['paragraph_locator']]
		else:A['comparison_status']='NEW'
		G.append(A)
	B['changes']=G;B['comparison_done']=True;return B
def main(argv=None):
	C=argparse.ArgumentParser(description='חילוץ track changes מקובץ DOCX');C.add_argument('input',help='קובץ DOCX קלט');C.add_argument('--output',default='changes.json',help='קובץ פלט JSON. לעולם לא קובץ הקלט, מסמך קיים או תיקיית מקור של הלקוח');C.add_argument('--compare-to-previous',help='קובץ DOCX מסבב קודם להשוואה');C.add_argument('--no-merge',action='store_true',help='בטל מיזוג של מחיקה והוספה לתיקון');A=C.parse_args(argv)
	try:guard_out(A.output,inputs=[A.input,A.compare_to_previous])
	except OutputRefused as G:print('סירוב: %s'%G);return 1
	for H in[A.input]+([A.compare_to_previous]if A.compare_to_previous else[]):
		I,J,K=load_docx_or_explain(H,loader=False)
		if I is None:print(J);return K
	print(f"מחלץ track changes מ: {A.input}");B=extract_track_changes(A.input)
	if not A.no_merge:B=merge_paired_changes(B)
	if A.compare_to_previous:
		print(f"משווה לסבב קודם: {A.compare_to_previous}");E=extract_track_changes(A.compare_to_previous)
		if not A.no_merge:E=merge_paired_changes(E)
		B=compare_rounds(B,E)
	F=Path(A.output)
	with open(F,'w',encoding='utf-8')as L:json.dump(B,L,ensure_ascii=False,indent=2)
	print(f"נשמר: {F}");print(f'סה"כ שינויים: {B["total_changes"]}');print(f'סה"כ הערות: {B["total_comments"]}');D=B.get('future_dated')or[]
	if D:print('אזהרה (לא חוסמת): %d בועות או שינויים מתוארכים אחרי היום (%s), עד %s (%s). תשובות שלנו יתוארכו היום, ולכן יופיעו לפניהם. התאריכים לא שונו'%(len(D),_he_date(_date.today()),_he_date(_date.fromisoformat(max(A['date']for A in D)[:10])),', '.join(sorted({A['author']or'?'for A in D}))))
	return 0
if __name__=='__main__':sys.exit(main())
