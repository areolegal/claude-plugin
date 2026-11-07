# -*- coding: utf-8 -*-
# Copyright (c) Areo. All rights reserved. Licensed under the terms at https://areo.co.il/legal/terms
import datetime as dt,json,os,shutil
from common.paths import long_path
from.import dates as D
from.import model as M
REGISTER_SCHEMA='areo-obligations-register/1'
COMPUTED_KEYS='computed',
def obl_dir(data):return os.path.join(data,'obligations')
def agreement_path(data,aid):return os.path.join(obl_dir(data),aid,'obligations.json')
def register_path(data):return os.path.join(obl_dir(data),'register.json')
def _read(p):
	with open(long_path(p),encoding='utf-8')as A:return json.load(A)
def _write(p,data):
	A=long_path(p);os.makedirs(os.path.dirname(A),exist_ok=True);B=A+'.tmp'
	with open(B,'w',encoding='utf-8')as C:json.dump(data,C,ensure_ascii=False,indent=1)
	os.replace(B,A)
def _backup(p):
	if not os.path.isfile(long_path(p)):return
	B=os.path.join(os.path.dirname(long_path(p)),'history');os.makedirs(B,exist_ok=True);C=dt.datetime.now().strftime('%Y%m%d-%H%M%S');A=os.path.join(B,'obligations-%s.json'%C);D=1
	while os.path.exists(A):A=os.path.join(B,'obligations-%s-%d.json'%(C,D));D+=1
	shutil.copy2(long_path(p),A);return A
def agreement_files(data):
	A=obl_dir(data)
	if not os.path.isdir(long_path(A)):return[]
	B=[]
	for D in sorted(os.listdir(long_path(A))):
		C=os.path.join(A,D,'obligations.json')
		if os.path.isfile(long_path(C)):B.append(C)
	return B
def with_computed(rec,as_of,lang):
	B=as_of;A=rec;E,F=D.compute_all(A['agreement'],A['obligations'],B,lang)
	for C in A['obligations']:C['computed']=E[C['id']]
	A['term']=F;A.setdefault('meta',{})['computed_as_of']=D.iso(D.parse(B)or dt.date.today());return A
def add(data,draft,as_of=None,lang='he',today=None):
	K=as_of;I=lang;H=draft;G=data;E=today;E=D.iso(D.parse(E)or dt.date.today());P=H['agreement']['agreement_id'];B=agreement_path(G,P);J=_read(B)if os.path.isfile(long_path(B))else None;C={'schema':M.SCHEMA,'agreement':H['agreement'],'obligations':[dict((A,B)for(A,B)in A.items()if A not in COMPUTED_KEYS)for A in H['obligations']],'meta':{'registered_at':(J or{}).get('meta',{}).get('registered_at',E),'updated_at':E,'lang':M.lang_key(I)}};L,N=[],[]
	if J:
		O={A['id']:A for A in J.get('obligations',[])}
		for A in C['obligations']:
			F=O.get(A['id'])
			if F and A.get('status','open')=='open'and not A.get('status_log')and F.get('status_log'):A['status'],A['status_log']=F.get('status','open'),F['status_log'];L.append(A['id'])
		Q={A['id']for A in C['obligations']};N=[A for A in O if A not in Q]
	with_computed(C,K,I);R=_backup(B);_write(B,C);S=rebuild(G,K,I);return{'path':B,'backup':R,'kept_status':L,'removed':N,'record':C,'register':register_path(G),'register_data':S}
def foreign_ids(data,aid,ids):
	E,A=set(ids),{}
	for F in agreement_files(data):
		C=_read(F);D=(C.get('agreement')or{}).get('agreement_id')
		if D==aid:continue
		for B in C.get('obligations',[]):
			if B.get('id')in E and B['id']not in A:A[B['id']]=D
	return A
class AmbiguousId(Exception):0
def set_status(data,oid,status,by,date,note='',as_of=None,lang='he',agreement=None):
	J=agreement;I=as_of;H=lang;G=oid;E=status
	if E not in M.STATUS:raise ValueError(M.msg('STATUS',H,G,E))
	if not by or not D.parse(date):raise ValueError(M.msg('STATUS',H,G,E))
	F=[]
	for B in agreement_files(data):
		A=_read(B)
		if J and(A.get('agreement')or{}).get('agreement_id')!=J:continue
		for C in A['obligations']:
			if C.get('id')==G:F.append((B,A,C));break
	if not F:raise KeyError(G)
	if len(F)>1:raise AmbiguousId(', '.join(A[1]['agreement']['agreement_id']for A in F))
	B,A,C=F[0];C['status']=E;C.setdefault('status_log',[]).append({'status':E,'by':by,'date':D.iso(D.parse(date)),'note':note or''});A['meta']['updated_at']=D.iso(dt.date.today());with_computed(A,I,H);_backup(B);_write(B,A);rebuild(data,I,H);return B,C
def load_records(data,as_of=None,lang='he'):return[with_computed(_read(A),as_of,lang)for A in agreement_files(data)]
def rebuild(data,as_of=None,lang='he'):
	E=as_of;F=load_records(data,E,lang);C={'schema':REGISTER_SCHEMA,'updated_at':D.iso(dt.date.today()),'as_of':D.iso(D.parse(E)or dt.date.today()),'agreements':[],'obligations':[]}
	for B in F:
		A=B['agreement'];C['agreements'].append({'agreement_id':A['agreement_id'],'title':A.get('title',''),'counterparty':A.get('counterparty',''),'family':A.get('family',''),'our_side':A.get('our_side',''),'language':A.get('language',''),'documents':A.get('documents',[]),'dates':A.get('dates',{}),'notices':A.get('notices',{}),'term':B['term'],'obligation_count':len(B['obligations']),'updated_at':B.get('meta',{}).get('updated_at')})
		for G in B['obligations']:C['obligations'].append(dict(G,agreement_id=A['agreement_id']))
	_write(register_path(data),C);return C
def occurrences(data,frm,to,lang='he'):
	A=frm;A,to=D.parse(A),D.parse(to);F=[]
	for B in load_records(data,A,lang):
		H=D.Ctx(B['agreement'],A,lang,B['obligations'])
		for C in B['obligations']:
			G=C.get('timing')or{}
			if G.get('kind')=='recurring':
				I,J,K=H.occurrences(G,A,to)
				for E in I:F.append((E,B,C,J))
			else:
				E=D.parse(C['computed'].get('due_date'))
				if E and A<=E<=to and G.get('kind')not in('ongoing',):F.append((E,B,C,C['computed'].get('calc','')))
	F.sort(key=lambda x:(x[0],x[1]['agreement']['agreement_id'],x[2]['id']));return F
def overdue(data,as_of,lang='he'):
	A=as_of;A=D.parse(A);C=[]
	for F in load_records(data,A,lang):
		for B in F['obligations']:
			E=D.parse(B['computed'].get('due_date'))
			if E and E<A and B.get('status','open')=='open'and(B.get('timing')or{}).get('kind')not in('recurring','ongoing','term_end'):C.append((E,F,B))
	C.sort(key=lambda x:x[0]);return C
