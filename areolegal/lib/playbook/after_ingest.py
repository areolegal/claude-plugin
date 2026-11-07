# -*- coding: utf-8 -*-
# Copyright (c) Areo. All rights reserved. Licensed under the terms at https://areo.co.il/legal/terms
import io,json,os,re,shutil
try:from playbook import status as S,surfaces_render as R
except ImportError:import sys;sys.path.insert(0,os.path.dirname(os.path.dirname(os.path.abspath(__file__))));from playbook import status as S;from playbook import surfaces_render as R
LOCAL_COPY_DIRNAME='Areo-playbooks-local'
def local_copy_dir(family_id,base=None):A=base;B=re.sub('[^\\w.-]+','_',str(family_id or'playbook'),flags=re.U).strip('._')or'playbook';A=A or os.environ.get('AREO_LOCAL_COPY_BASE')or os.path.join(os.path.expanduser('~'),LOCAL_COPY_DIRNAME);return os.path.join(A,B)
def save_local_copy(paths,family_id,base=None):
	D=base;C=local_copy_dir(family_id,D);A={'dir':C,'copied':[],'errors':[]}
	if'://'in str(D or''):A['errors'].append('העותק המקומי נכתב לדיסק בלבד: %s'%D);return A
	try:os.makedirs(C,exist_ok=True)
	except OSError as E:A['errors'].append('%s: %s'%(C,E));return A
	for B in paths:
		if not B:continue
		if not os.path.isfile(B):A['errors'].append('חסר: %s'%B);continue
		try:shutil.copy2(B,os.path.join(C,os.path.basename(B)));A['copied'].append(os.path.basename(B))
		except OSError as E:A['errors'].append('%s: %s'%(B,E))
	return A
def close_questions(model,record,record_id):
	A=record;B=[];F=sorted({A.get('name')for A in(A.get('signers')or{}).values()if A.get('name')});G={A.get('id')or A.get('queue_id'):A for A in model.get('validation_queue')or[]}
	for(C,D)in(A.get('choices')or{}).items():
		E=G.get(C)
		if E is None:continue
		E.update(status='closed',answered=True,answer_verbatim=D.get('text')or'',answer_index=D.get('index'),answered_via=record_id,answered_by=', '.join(F),answered_at=A.get('received_at'));B.append(C)
	return B
LEGAL_Q_PREFIXES='טעון בדיקה משפטית','Legal review required','Needs legal review'
def close_legal_questions(model,cells,record,record_id):
	D=[]
	for A in model.get('validation_queue')or[]:
		F=A.get('status')or('closed'if A.get('answered')else'open')
		if F!='open'or A.get('answered'):continue
		if not str(A.get('question')or'').strip().startswith(LEGAL_Q_PREFIXES):continue
		C=[A for A in A.get('rule_ids')or[A.get('rule_id')]if A and A!='GLOBAL']
		if not C:continue
		B=[(A,B)for(A,B)in cells.items()if A.split('|')[0]in C and(B or{}).get('legal_review_required')]
		if not B or set(A.split('|')[0]for(A,B)in B)!=set(C):continue
		if not all(S.cell_counts(A)and A.get('legal_review_done_by')for(B,A)in B):continue
		E=sorted({A.get('legal_review_done_by')for(B,A)in B});G=max(str(A.get('legal_review_done_at')or record.get('received_at')or'')for(B,A)in B);A.update(status='closed',answered=True,answered_via=record_id,answered_by=', '.join(E),answered_at=G,answer_verbatim='נבדק בידי %s ואושר כפי שהוא'%', '.join(E),closed_by='legal_review');D.append(A.get('id')or A.get('queue_id'))
	return D
def record_entry(record,record_id,record_path,cells):
	A=record;C=[]
	for(D,E)in sorted(cells.items()):
		for F in E.get('assumptions_confirmed')or[]:C.append(dict(F,cell=D))
	B={'record_id':record_id,'record':record_path,'token':A.get('token'),'signed_sha256':A.get('signed_sha256'),'evidence':A.get('evidence'),'simulated':A.get('simulated'),'counts':A.get('counts'),'choices':A.get('choices')or{},'assumptions_confirmed':C,'signers':{A:{A:B.get(A)for A in('name','role','date')}for(A,B)in(A.get('signers')or{}).items()},'warnings':A.get('warnings')or[],'supersedes':A.get('supersedes')}
	if A.get('kind')=='chat':B.update({B:A.get(B)for B in('kind','batch_id','stage','reply_sha256','decisions','updates','skipped')})
	if A.get('kind')=='wizard':B.update({B:A.get(B)for B in('kind','source_file','source_sha256')})
	return B
def apply_ingest(model,core,index_entry,result,record_path,word_path=None,workspace_path=None):
	M=workspace_path;L=word_path;K=result;J=index_entry;E=record_path;A=model;F=dict(K['record']);C=K['cells'];D=os.path.splitext(os.path.basename(E))[0]
	if os.path.exists(E):
		with io.open(E,encoding='utf-8')as P:Q=json.load(P)
		F['supersedes']=Q.get('supersedes')
	N=close_questions(A,F,D);N+=close_legal_questions(A,C,F,D);O=[A for A in A.get('approval_records')or[]if A.get('record_id')!=D];O.append(record_entry(F,D,E,C));A['approval_records']=O;H=S.stamp(A,core,J,C,record_id=D);B=I=None
	if L:B,U=R.restamp_docx(L,A,H,C)
	if M:I=R.restamp_workspace(M,H)
	G=(A.get('handoff')or{}).get('paths')
	if isinstance(G,dict)and B:G['word']=os.path.join(os.path.dirname(G.get('word')or''),os.path.basename(B))if G.get('word')else B
	T=S.check_consistency(A,core,J,C,word_path=B,workspace_path=I);return{'status':H,'word':B,'workspace':I,'closed':N,'problems':T}
