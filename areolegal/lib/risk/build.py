# -*- coding: utf-8 -*-
# Copyright (c) Areo. All rights reserved. Licensed under the terms at https://areo.co.il/legal/terms
import io,json,os,re,shutil,sys,time
try:from.render_check import build_report,static_checks
except ImportError:sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)));from render_check import build_report,static_checks
try:from common.paths import check_write_path,long_path
except ImportError:sys.path.insert(0,os.path.dirname(os.path.dirname(os.path.abspath(__file__))));from common.paths import check_write_path,long_path
NAMES={'risk':('Areo Workspace - סיכונים.html','risk-register.json','__RISK_DATA__'),'entity':('Areo Workspace - חקר ישות.html','entity-report.json','__ENTITY_DATA__')}
NAMES_EN={'risk':('Areo Workspace - Risks.html','risk-register.json','__RISK_DATA__'),'entity':('Areo Workspace - Entity check.html','entity-report.json','__ENTITY_DATA__')}
def names_for(kind,lang=None):return(NAMES_EN if lang=='en'else NAMES)[kind]
def html_names(kind):return NAMES[kind][0],NAMES_EN[kind][0]
def lang_of(data):return'en'if((data or{}).get('meta')or{}).get('display_language')=='en'else'he'
class BuildError(Exception):0
def _embedded_tid(html_path):
	try:
		with io.open(long_path(html_path),encoding='utf-8')as B:C=B.read()
	except OSError:return
	A=re.search('"transaction_id"\\s*:\\s*"([^"]*)"',C);return A.group(1)if A else None
HISTORY_DIR='history'
_EMBED_RE=re.compile('const DATA\\s*=\\s*')
def _embedded_data(html_path):
	try:
		with io.open(long_path(html_path),encoding='utf-8')as C:A=C.read()
		B=_EMBED_RE.search(A);return json.JSONDecoder().raw_decode(A,B.end())[0]if B else None
	except(OSError,ValueError):return
def _history_path(hist,name,stamp):
	B=stamp;C,D=os.path.splitext(name);A=os.path.join(hist,'%s.%s%s'%(C,B,D));E=2
	while os.path.exists(long_path(A)):A=os.path.join(hist,'%s.%s-%d%s'%(C,B,E,D));E+=1
	return A
def _same_file(a,b):
	try:return bool(a)and os.path.exists(long_path(a))and os.path.samefile(long_path(a),long_path(b))
	except OSError:return False
def archive_previous(deal_dir,kind='risk',data_path=None,lang=None):
	A=deal_dir;J,K,R=names_for(kind,lang);D=os.path.join(A,K);B=[os.path.join(A,B)for B in dict.fromkeys((J,)+html_names(kind))if os.path.exists(long_path(os.path.join(A,B)))];L=B[0]if B else os.path.join(A,J);M=bool(B);E=os.path.exists(long_path(D))and not _same_file(data_path,D)
	if not M and not E:return[]
	F=os.path.join(A,HISTORY_DIR);os.makedirs(long_path(F),exist_ok=True);G=[];N=_embedded_data(L)if M and not E else None
	for(C,P)in[(A,True)for A in B]+[(D,E)]:
		if not P:continue
		O=time.strftime('%Y%m%dT%H%M%S',time.localtime(os.path.getmtime(long_path(C))));H=_history_path(F,os.path.basename(C),O);check_write_path(H);shutil.move(long_path(C),long_path(H));G.append(H)
		if C==L and N is not None:
			I=_history_path(F,K,O);check_write_path(I)
			with io.open(long_path(I),'w',encoding='utf-8',newline='\n')as Q:json.dump(N,Q,ensure_ascii=False,indent=1)
			G.append(I)
	return G
def write_report(deal_dir,template_path,data,kind='risk',data_path=None,archived=None,lang=None):
	K=archived;E=lang;D=kind;B=data;A=deal_dir;E=E or lang_of(B);N,O,P=names_for(D,E);F=(B.get('meta')or{}).get('transaction_id')
	if D=='risk'and(B.get('meta')or{}).get('scope')=='deal'and F!=os.path.basename(os.path.normpath(A)):raise BuildError('meta.transaction_id (%s) אינו שם תיקיית העסקה (%s)'%(F,os.path.basename(A)))
	with io.open(long_path(template_path),encoding='utf-8')as C:L=C.read()
	M=static_checks(L)
	if M:raise BuildError('התבנית נכשלה בבדיקה הסטטית: %s'%'; '.join(M))
	H=os.path.join(A,N);I=os.path.join(A,O)
	for Q in html_names(D):
		G=os.path.join(A,Q);J=_embedded_tid(G)if os.path.exists(long_path(G))else None
		if J and F and J!=F:raise BuildError('בתיקייה דוח של עסקה אחרת (%s): לא נדרס'%J)
	for G in(H,I):check_write_path(G)
	R=build_report(L,B,P);S=archive_previous(A,D,data_path,E)
	if K is not None:K.extend(S)
	with io.open(I,'w',encoding='utf-8',newline='\n')as C:json.dump(B,C,ensure_ascii=False,indent=1)
	with io.open(H,'w',encoding='utf-8',newline='\n')as C:C.write(R)
	return H,I
