# -*- coding: utf-8 -*-
# Copyright (c) Areo. All rights reserved. Licensed under the terms at https://areo.co.il/legal/terms
import argparse,datetime,hashlib,json,os,sys
if __name__=='__main__':sys.dont_write_bytecode=True
ACTIONS={'setup':('profile_built','entity_added'),'playbook':('playbook_built','playbook_updated'),'negotiator':('round_produced','signing_copy_produced'),'drafter':('draft_produced',),'risk':('risk_report','background_check_report'),'strategist':('prep_center',),'translator':('translation_produced',),'register':('agreement_registered',),'clm':('workspace_built','workspace_updated')}
LEDGER_NAME='.areo-actions.json'
PAYLOAD_KEYS='skill','action','count','date'
def payload(skill,action,today=None):
	B=action;A=skill
	if A not in ACTIONS:raise ValueError('unknown skill: %s'%A)
	if B not in ACTIONS[A]:raise ValueError('not a counted action for %s: %s (counted: %s)'%(A,B,', '.join(ACTIONS[A])))
	C={'skill':A,'action':B,'count':1,'date':(today or datetime.date.today()).isoformat()};assert tuple(C)==PAYLOAD_KEYS;return C
def _digest(skill,action,output_id):return hashlib.sha256(('%s|%s|%s'%(skill,action,output_id)).encode('utf-8')).hexdigest()
def record(skill,action,output_id,ledger_dir=None,today=None,dry_run=False):
	G=output_id;F=action;E=skill;C=ledger_dir;I=payload(E,F,today)
	if not G:raise ValueError('output id is required (one action per completed output)')
	H=_digest(E,F,G);A=os.path.join(C,LEDGER_NAME)if C else None;B=[]
	if A and os.path.exists(A):
		try:
			with open(A,encoding='utf-8')as D:B=json.load(D).get('counted',[])
		except(OSError,ValueError):B=[]
	if H in B:return
	if A and not dry_run:
		os.makedirs(C,exist_ok=True)
		with open(A,'w',encoding='utf-8',newline='\n')as D:json.dump({'counted':B+[H]},D)
	return I
def main(argv=None):
	A=argparse.ArgumentParser(description='מונה פעולה שהושלמה (בלי תוכן)');A.add_argument('--skill',required=True,choices=sorted(ACTIONS));A.add_argument('--action',required=True);A.add_argument('--output-id',required=True,help='מזהה מקומי של התוצר; נשמר כגיבוב בלבד ואינו נשלח');A.add_argument('--ledger',help='תיקיית Areo-נתונים של הלקוח (לפנקס נגד ספירה כפולה)');A.add_argument('--dry-run',action='store_true');B=A.parse_args(argv)
	try:C=record(B.skill,B.action,B.output_id,B.ledger,dry_run=B.dry_run)
	except ValueError as D:print('לא נספר: %s'%D,file=sys.stderr);return 2
	if C:print(json.dumps(C,ensure_ascii=False,separators=(',',':')))
	return 0
if __name__=='__main__':sys.exit(main())
