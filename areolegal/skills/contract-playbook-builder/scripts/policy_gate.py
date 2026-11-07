#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (c) Areo. All rights reserved. Licensed under the terms at https://areo.co.il/legal/terms
'שער המדיניות: האם מותר לומר על עמדה בפלייבוק שהיא מדיניות החברה.'
import argparse,datetime as _dt,io,json,os,sys
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
import areo_lib
from playbook import ingest_approval as IA,status as S
from playbook.approval_sheet import norm_text
TRACKS='green','yellow','red'
def load_record(a,model):
	if a.records:return IA.current_record(a.records)[1]
	B=S._latest_record(model)
	if not B or not B.get('record'):return
	A=B['record']
	if not os.path.isabs(A):A=os.path.join(os.path.dirname(os.path.abspath(a.model)),A)
	if not os.path.exists(A):return
	with io.open(A,encoding='utf-8')as C:return json.load(C)
def main(argv=None):
	sys.dont_write_bytecode=True;sys.stdout.reconfigure(encoding='utf-8');B=argparse.ArgumentParser(description=__doc__.split('\n')[0]);B.add_argument('--model',required=True,help='playbook-model.json של הפלייבוק שנבחר');B.add_argument('--rule',required=True,help='מזהה הכלל, כפי שבפלייבוק');B.add_argument('--track',required=True,choices=TRACKS);B.add_argument('--segment',help='מזהה הסגמנט, כשנבחר סגמנט');B.add_argument('--wording',help='הנוסח שהנושא ונותן עומד להחיל');B.add_argument('--records',help='תיקיית רשומות האישור; בלעדיה: הרשומה האחרונה שהמודל מפנה אליה');A=B.parse_args(argv)
	if not os.path.exists(A.model):print('המודל אינו קיים: %s'%A.model);return 2
	with io.open(A.model,encoding='utf-8')as J:D=json.load(J)
	if not any(B.get('rule_id')==A.rule for B in D.get('rules')or()):print('הכלל %s אינו בפלייבוק הזה'%A.rule);return 2
	F=load_record(A,D);E=IA.record_cells(F)if F else{};G=None
	if A.wording is not None:
		K=S.cell_key(A.rule,A.track,A.segment);H=E.get(K)or E.get(S.cell_key(A.rule,A.track))or{};I=(H.get('approved_text')or{}).get('wording')
		if I is not None:L=norm_text(A.wording)==norm_text(I);G=H.get('approved_fp')if L else'differs:'+norm_text(A.wording)[:40]
	C=S.policy_claim(D,E,A.rule,A.track,A.segment,wording_fp=G);M={'claim':bool(C['policy_claim']),'status':C['playbook_status'],'reason':C['reason'],'key':C['key'],'status_label':C['status_label'],'track':A.track,'checked_at':_dt.datetime.now().astimezone().isoformat(timespec='seconds')};print(json.dumps(M,ensure_ascii=False));return 0
if __name__=='__main__':sys.exit(main())
