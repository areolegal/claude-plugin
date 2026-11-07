# -*- coding: utf-8 -*-
# Copyright (c) Areo. All rights reserved. Licensed under the terms at https://areo.co.il/legal/terms
import os,re
from collections import namedtuple
PATH_LIMIT=230
COLLISION_RESERVE=len(' (99)')
WORK_SUFFIX={'he':' - פנימי','en':' - internal'}
AS_PRODUCED_SUFFIX={'he':' - כפי שהופק','en':' - as produced'}
ROUND_WORD={'he':'סבב','en':'Round'}
TYPE_MAX=20
COMPANY_MAX=15
TYPE_MIN=12
_BAD=re.compile('[\\\\/:*?"<>|\\x00-\\x1f]')
OutPaths=namedtuple('OutPaths','work send as_produced longest step')
class PathTooLong(Exception):
	def __init__(A,length,limit=PATH_LIMIT):C=limit;B=length;A.length,A.limit=B,C;super().__init__('הנתיב ארוך מדי: %d תווים (הגבול %d). יש לחבר תיקייה בנתיב קצר יותר.'%(B,C))
def clean_name(s):s=_BAD.sub('',s or'');return re.sub('\\s+',' ',s).strip().rstrip('.')
def _base(agreement_type,company,round_no,date,lang):
	B=company;A=[clean_name(agreement_type)]
	if B:A.append(clean_name(B))
	A+=['%s %d'%(ROUND_WORD[lang],round_no),date];return' - '.join(A)
def _variants(folder,base,ext,lang):C=ext;B=base;A=folder;D=os.path.join(A,B+WORK_SUFFIX[lang]+C);E=os.path.join(A,B+C);F=os.path.join(A,B+AS_PRODUCED_SUFFIX[lang]+C);return D,E,F
def safe_out_paths(folder,agreement_type,company,round_no,date,lang='he',ext='.docx',limit=PATH_LIMIT):
	D=limit;C=agreement_type;B=folder;B=os.path.abspath(B);H=[(C[:TYPE_MAX],(company or'')[:COMPANY_MAX]),(C[:TYPE_MAX],''),(C[:TYPE_MIN],'')];A=0
	for(I,(J,K))in enumerate(H):
		L=_base(J,K,round_no,date,lang);E,F,G=_variants(B,L,ext,lang);A=max(len(E),len(F),len(G))+COLLISION_RESERVE
		if A<=D:return OutPaths(E,F,G,A,I)
	raise PathTooLong(A,D)
_ROUND_PART=re.compile('^(?:%s) \\d+$'%'|'.join(ROUND_WORD.values()))
_HEB=re.compile('[א-ת]')
_LAT=re.compile('[A-Za-z]')
def prefix_from_name(name):
	A=os.path.basename(str(name or'')).split(' - ');B=next((A for(A,B)in enumerate(A)if _ROUND_PART.match(B.strip())),None)
	if not B:return
	return A[0],' - '.join(A[1:B])
def stored_prefix(state):
	B=state;C=(B or{}).get('meta')or{};A=C.get('file_prefix')
	if isinstance(A,dict)and A.get('agreement_type'):return A['agreement_type'],A.get('company')or''
	F=[A for A in(B or{}).get('produced_documents')or()if isinstance(A,dict)and A.get('kind')in('work','send','as_produced')]+[A for A in C.get('sent_documents')or()if isinstance(A,dict)]
	for D in F:
		E=prefix_from_name(D.get('path')or D.get('file_name'))
		if E:return E
def name_lang(s):
	if _HEB.search(s or''):return'he'
	return'en'if _LAT.search(s or'')else None
def prefix_switch_item(prefix,lang,alt_company,ui_lang='he'):
	B=prefix;A=alt_company;A=re.sub('[,\\s]+(Ltd|Limited|Inc|LLC|Corp|Corporation|GmbH|PLC|AG|בע"מ)\\.?$','',str(A or'').strip(),flags=re.I)
	if not B or not A or name_lang(B[1])in(None,lang)or name_lang(A)!=lang or clean_name(A)==clean_name(B[1]):return
	C=' - '.join(A for A in B if A);D=' - '.join(A for A in(B[0],clean_name(A))if A)
	if str(ui_lang or'').lower()[:2]=='en':return{'key':'file_prefix','kind':'file_prefix','situation':None,'blocks_sending':False,'text':'The file names of this deal start with "%s" (set in the first round). The agreement is in English, and an English company name is now known. Switch the file names to "%s"?'%(C,D),'recommendation':'Keep "%s", so that all rounds stay together'%C,'options':['Keep (recommended)','Switch to "%s"'%D]}
	return{'key':'file_prefix','kind':'file_prefix','situation':None,'blocks_sending':False,'text':'שמות הקבצים בעסקה הזו נפתחים ב-"%s" (נקבע בסבב הראשון). ההסכם באנגלית, ועכשיו ידוע שם החברה באנגלית. להחליף את תחילת שמות הקבצים ל-"%s"?'%(C,D),'recommendation':'להשאיר את "%s", כדי שכל הסבבים יישארו יחד'%C,'options':['להשאיר (ההמלצה)','להחליף ל-"%s"'%D]}
def prefix_switch_answer(state):
	A=next((A for A in reversed((state or{}).get('user_decisions')or())if isinstance(A,dict)and A.get('id')=='file_prefix'),None)
	if not A:return
	return'switch'if re.match('\\s*(להחליף|החלף|switch|replace|yes|כן)',str(A.get('answer')or''),re.I)else'keep'
def unique_path(path):
	A=path
	if not os.path.exists(A):return A
	C,D=os.path.splitext(A)
	for E in range(2,100):
		B='%s (%d)%s'%(C,E,D)
		if not os.path.exists(B):return B
	raise FileExistsError(A)
def check_write_path(path,limit=PATH_LIMIT):
	B=limit;A=len(os.path.abspath(path))
	if A>B:raise PathTooLong(A,B)
	return A
def stale_path(path,lang='he'):A,B=os.path.splitext(path);return unique_path(A+(' - לא למשלוח'if lang=='he'else' - not for sending')+B)
def long_path(path):
	A=os.path.abspath(path)
	if os.name!='nt'or A.startswith('\\\\?\\'):return A
	if A.startswith('\\\\'):return'\\\\?\\UNC\\'+A[2:]
	return'\\\\?\\'+A
def plain_path(path):
	A=str(path)
	if A.startswith('\\\\?\\UNC\\'):return'\\\\'+A[8:]
	if A.startswith('\\\\?\\'):return A[4:]
	return A
