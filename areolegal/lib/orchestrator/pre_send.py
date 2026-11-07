# -*- coding: utf-8 -*-
# Copyright (c) Areo. All rights reserved. Licensed under the terms at https://areo.co.il/legal/terms
import datetime as _dt,hashlib,io,json,os,re
from common import paths
def _now():return _dt.datetime.now().astimezone().replace(microsecond=0).isoformat()
def _write_json_atomic(path,data):
	paths.check_write_path(path);A=path+'.tmp'
	with io.open(A,'w',encoding='utf-8')as B:json.dump(data,B,ensure_ascii=False,indent=1)
	return A
def mark_superseded(path,state=None,deal_dir=None,reason='',superseded_by=None,lang='he'):
	D=state;A=path
	if not A or not os.path.exists(A):return
	B=paths.stale_path(A,lang);paths.check_write_path(B);os.replace(A,B)
	if D is not None:
		K=deal_dir or os.path.dirname(os.path.abspath(A))
		def G(p):return os.path.relpath(os.path.abspath(p),os.path.abspath(K)).replace('\\','/')
		E,L=G(A),G(B);F={'superseded':True,'superseded_at':_now(),'superseded_reason':reason or'gate_failed','superseded_by':superseded_by,'path':L,'original_path':E};H=False
		for I in D.setdefault('produced_documents',[]):
			if I.get('path')==E:I.update(F);H=True
		if not H:D['produced_documents'].append(dict(F,kind='superseded',sha256=_sha256(B),produced_at=F['superseded_at']))
		J=D.setdefault('quality_gate',{});C=J.get('send_copy')
		if C is None or isinstance(C,dict)and C.get('path')==E or C==E or isinstance(C,str)and os.path.basename(C)==os.path.basename(A):J['send_copy']=None
		D.setdefault('open_items',[]).append({'item':'עותק שהוחלף: %s'%os.path.basename(B),'kind':'send_copy_retracted','blocks_sending':True})
	return B
def retract_send_copy(send_path,state=None,lang='he',deal_dir=None):return mark_superseded(send_path,state,deal_dir=deal_dir,reason='gate_failed',lang=lang)
def save_state(state,state_path):
	B=state;A=state_path
	if B is None or not A:return
	B.setdefault('meta',{})['last_updated']=_now();C=_write_json_atomic(A,B);os.replace(C,A);return A
def _sha256(path):
	A=hashlib.sha256()
	with open(path,'rb')as B:
		for C in iter(lambda:B.read(1<<16),b''):A.update(C)
	return A.hexdigest()
RUN_RECORD='apply-report-round-%d.json'
def run_record_path(deal_dir,rnd):return os.path.join(deal_dir,RUN_RECORD%int(rnd))
def load_run_record(deal_dir,rnd):
	A=run_record_path(deal_dir,rnd)
	if not os.path.exists(A):return
	try:
		with io.open(A,encoding='utf-8')as B:return json.load(B)
	except ValueError:return
def _sent_shas(state):A=(state or{}).get('meta')or{};return{A.get('sha256')for A in A.get('sent_documents')or()if A.get('sha256')}
def reusable_path(deal_dir,rnd,run_id,kind,state=None):
	F=state;E=run_id;C=deal_dir
	if not(C and rnd and E):return
	A=load_run_record(C,rnd)
	if not A or A.get('run_id')!=E or A.get('delivered'):return
	if any((A or{}).get('sha256')in _sent_shas(F)for A in(A.get('files')or{}).values()):return
	B=(A.get('files')or{}).get(kind)or{}
	if not B.get('path')or not B.get('sha256'):return
	D=os.path.join(C,B['path'])
	if not os.path.exists(D)or _sha256(D)!=B['sha256']or B['sha256']in _sent_shas(F):return
	return D
def update_run_record(deal_dir,rnd,run_id,files):
	F=run_id;D=rnd;C=deal_dir;A=load_run_record(C,D)or{}
	if A.get('run_id')!=F:A={'round':int(D),'run_id':F,'delivered':False,'files':{}}
	for(G,B)in(files or{}).items():
		if B:H=os.path.relpath(os.path.abspath(B),os.path.abspath(C)).replace('\\','/');A['files'][G]={'path':H,'sha256':_sha256(B)if os.path.exists(B)else None}
	A['updated_at']=_now();E=run_record_path(C,D);I=_write_json_atomic(E,A);os.replace(I,E);return E
def refresh_run_record(path):
	B=path;C=os.path.dirname(os.path.abspath(B));H=os.path.basename(B);F=[]
	for I in sorted(os.listdir(C)):
		D=re.match('^apply-report-round-(\\d+)\\.json$',I);A=load_run_record(C,int(D.group(1)))if D else None
		if not A or A.get('delivered'):continue
		E=[B for(B,A)in(A.get('files')or{}).items()if isinstance(A,dict)and A.get('path')==H]
		if not E:continue
		for J in E:A['files'][J]['sha256']=_sha256(B)
		A['updated_at']=_now();G=run_record_path(C,int(D.group(1)));os.replace(_write_json_atomic(G,A),G);F+=E
	return F
def record_send_copy(state,send_path,deal_dir=None):C=send_path;B=state;F=deal_dir or os.path.dirname(os.path.abspath(C));D=os.path.relpath(os.path.abspath(C),os.path.abspath(F)).replace('\\','/');A={'path':D,'sha256':_sha256(C),'recorded_at':_now(),'status':'produced_pending_send'};B.setdefault('quality_gate',{})['send_copy']=A;E=[A for A in B.setdefault('produced_documents',[])if not(A.get('kind')=='send'and A.get('path')==D)];E.append({'kind':'send','path':D,'sha256':A['sha256'],'produced_at':A['recorded_at']});B['produced_documents']=E;return A
