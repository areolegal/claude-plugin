#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (c) Areo. All rights reserved. Licensed under the terms at https://areo.co.il/legal/terms
'שמירת הפלייבוק בתיקייה שלו, ורישומו באינדקס.'
import copy,datetime as _dt,json,os,shutil,sys
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
import areo_lib
from common.cli import OutputRefused,guard_out,no_bytecode,parser
from playbook import status as S
KEY_FIELDS='core_path','family_code','company_role_code'
CARRIED='corpus_origin','playbook_status','status_label','produced_with'
def load(path,what):
	A=path
	if not os.path.exists(A):print('%s אינו קיים: %s'%(what,A));raise SystemExit(2)
	with open(A,encoding='utf-8')as B:return json.load(B)
def entry_identity(e):return e.get('family_id')or e.get('family_code'),e.get('company_role_code'),bool(e.get('legacy'))
def _aliases(model):
	A=model;D=[];G=(A.get('meta')or{}).get('build_request')or{};E=A.get('family_id');F=[G.get('family_aliases'),A.get('family_aliases')];H=list(A.get('contract_families')or())+list((A.get('scope_summary')or{}).get('contract_families')or())
	for B in H:
		if isinstance(B,dict)and(not E or(B.get('contract_family_id')or B.get('family_id'))in(None,E)):F.append(B.get('family_aliases'))
	for I in F:
		for C in I or():
			if isinstance(C,str)and C.strip()and C.strip()not in D:D.append(C.strip())
	return D
def model_entry(model,core,core_rel,legacy=False,model_path=None):
	B=core;A=model;C=S.gate_status(A,model_path);D={'core_path':core_rel,'family_id':A.get('family_id'),'family_code':A.get('family_code')or(B or{}).get('family_code'),'company_role_code':A.get('company_role_code')or(B or{}).get('company_role_code'),'family_aliases':_aliases(A),'family_name':((A.get('meta')or{}).get('build_request')or{}).get('family_label')or A.get('family_label'),'language':A.get('output_language')or((A.get('meta')or{}).get('build_request')or{}).get('language'),'last_updated':_dt.date.today().isoformat(),'playbook_status':C['playbook_status'],'status_label':C['label'],'corpus_origin':(A.get('scope_summary')or{}).get('corpus_origin'),'produced_with':A.get('produced_with'),'validity':validity_of(A,B)}
	if legacy:D['legacy']=True
	return{B:A for(B,A)in D.items()if A not in(None,'')}
def validity_of(model,core):
	try:from playbook import validity as A
	except ImportError:return
	return A.validity_summary(model,core)
def build_identity(model):A=model;return A.get('build_id')or'',str(A.get('version')or''),str(A.get('generated_at')or'')
def previous_build(folder,model,src_model):
	A=os.path.join(folder,'playbook-model.json')
	if not os.path.exists(A)or os.path.abspath(A)==os.path.abspath(src_model):return False
	try:
		with open(A,encoding='utf-8')as B:C=json.load(B)
	except ValueError:return True
	return build_identity(C)!=build_identity(model)
def keep_previous(folder):
	A=folder;B=[];C=os.path.join(A,'versions');G=_dt.datetime.now().strftime('%Y-%m-%d-%H%M%S')
	for D in('playbook-model.json','playbook-core.json'):
		E=os.path.join(A,D)
		if not os.path.exists(E):continue
		os.makedirs(C,exist_ok=True);F=os.path.join(C,'%s-%s'%(G,D));shutil.copy2(E,F);B.append(F)
	return B
def main(argv=None):
	no_bytecode();J=parser(__doc__.split('\n')[0],out_required=False,out_help='דוח הרישום (JSON). האינדקס מתעדכן בכל מקרה');J.add_argument('--data',required=True,help='תיקיית Areo-נתונים של הלקוח');J.add_argument('--model',required=True,help='playbook-model.json שנבנה');J.add_argument('--core',required=True,help='playbook-core.json שנבנה');J.add_argument('--dry-run',action='store_true',help='מראה מה היה נכתב, בלי לכתוב דבר');A=J.parse_args(argv)
	if not os.path.isdir(A.data):print('תיקיית הנתונים אינה קיימת: %s'%A.data);return 2
	H=load(A.model,'המודל');R=load(A.core,'הגרעין');N=H.get('family_id')
	if not N:print('אין במודל family_id, ולכן אין תיקייה לשמור בה ואין רשומה לרשום. זהו מזהה קבוע לסוג ההסכם ולפוזיציה (fam_<סוג>_<קוד-פוזיציה>).');return 3
	D=os.path.join(A.data,'playbooks',N);E=os.path.join(A.data,'playbooks','index.json');b=os.path.join('playbooks',N,'playbook-core.json').replace('\\','/');B=model_entry(H,R,b,model_path=A.model);S=[A for A in KEY_FIELDS if not B.get(A)]
	if S:print('הרשומה לא תימצא באיתור בלי %s. השדות נגזרים מהמודל ומהגרעין.'%', '.join(S));return 3
	F={'playbooks':[]}
	if os.path.exists(E):
		F=load(E,'האינדקס')
		if not isinstance(F,dict)or not isinstance(F.get('playbooks'),list):print('האינדקס אינו במבנה {"playbooks": [...]}: %s'%E);return 3
	c=copy.deepcopy(F['playbooks']);L=entry_identity(B);M=[A for A in c if entry_identity(A)!=L];d=[A for A in F['playbooks']if entry_identity(A)!=L];K=d+[B];O=os.path.join(A.data,'playbook-core.json');C=None
	if os.path.exists(O)and os.path.abspath(O)!=os.path.abspath(A.core):
		T=os.path.join(A.data,'playbook-model.json');I={}
		if os.path.exists(T):
			try:
				with open(T,encoding='utf-8')as G:I=json.load(G)
			except ValueError:I={}
		with open(O,encoding='utf-8')as G:P=json.load(G)
		C={'core_path':'playbook-core.json','legacy':True}
		for(e,U)in(('family_id',I.get('family_id')or P.get('family_id')),('family_code',I.get('family_code')or P.get('family_code')),('company_role_code',I.get('company_role_code')or P.get('company_role_code')),('family_aliases',list(I.get('family_aliases')or[]))):
			if U:C[e]=U
		V=entry_identity(C)
		if V!=L and not any(entry_identity(A)==V for A in K):K.append(C)
		else:C=None
	W=[A for A in K if entry_identity(A)!=L and(C is None or entry_identity(A)!=entry_identity(C))]
	if W!=M:
		print('סירוב: רשומה של סוג אחר או של פוזיציה אחרת הייתה משתנה. פלייבוק אינו דוחק פלייבוק אחר.')
		for X in M:
			if X not in W:print('  הייתה נעלמת: %s'%json.dumps(X,ensure_ascii=False)[:120])
		return 3
	if A.dry_run:
		print('ריצה יבשה. היה נכתב:');print('  תיקייה : %s'%D);print('  רשומה  : %s'%json.dumps(B,ensure_ascii=False,indent=1))
		if C:print('  ועוד רשומה לפלייבוק במבנה הישן, בלי להזיז אותו')
		print('  גרסה קודמת ב-versions/: %s'%('תישמר (בתיקייה פלייבוק מבנייה קודמת)'if previous_build(D,H,A.model)else'אין מה לשמור'));return 0
	os.makedirs(D,exist_ok=True);Q=keep_previous(D)if previous_build(D,H,A.model)else[]
	for(Y,f)in((A.model,'playbook-model.json'),(A.core,'playbook-core.json')):
		Z=os.path.join(D,f)
		if os.path.abspath(Y)!=os.path.abspath(Z):shutil.copy2(Y,Z)
	F['playbooks']=K;os.makedirs(os.path.dirname(E),exist_ok=True)
	with open(E,'w',encoding='utf-8')as G:json.dump(F,G,ensure_ascii=False,indent=1)
	print('תיקייה: %s'%D);print('אינדקס: %s (%d רשומות)'%(E,len(K)));print('רשומה : %s / %s   מעמד: %s'%(B.get('family_code'),B.get('company_role_code'),B.get('playbook_status')))
	if Q:print('הגרסה הקודמת נשמרה: %s'%', '.join(os.path.basename(A)for A in Q))
	if C:print('נרשם גם פלייבוק במבנה הישן שבשורש, בלי להזיז אותו.')
	print('רשומות שלא נגעתי בהן: %d'%len(M))
	if(B.get('validity')or{}).get('status')=='invalid':
		from playbook import validity as g;print('הפלייבוק אינו עובר את הבדיקות של עצמו: %s'%', '.join('%s x%d'%(A,B)for(A,B)in B['validity']['codes'].items()))
		for h in g.playbook_warnings(H,R,lang=H.get('output_language')or'he'):print('ללקוח: %s'%h)
	if A.out:
		try:a=guard_out(A.out,inputs=[A.model,A.core,E])
		except OutputRefused as i:print('הדוח לא נכתב. סירוב: %s'%i)
		else:
			with open(a,'w',encoding='utf-8')as G:json.dump({'folder':D,'index':E,'entry':B,'kept_versions':Q,'legacy_registered':bool(C),'untouched_entries':len(M)},G,ensure_ascii=False,indent=2)
			print('נכתב %s'%a)
	return 0
if __name__=='__main__':sys.exit(main())
