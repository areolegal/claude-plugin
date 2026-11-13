# -*- coding: utf-8 -*-
# Copyright (c) Areo. All rights reserved. Licensed under the terms at https://areo.co.il/legal/terms
import json,re,sys
from pathlib import Path
REPEAT_MIN=3
OUT_NAME='מדדים.json'
def _read(p):
	try:return json.loads(Path(p).read_text(encoding='utf-8'))
	except(OSError,ValueError):return
def _norm(t):return re.sub('\\s+',' ',str(t or'')).strip().lower()
def deal_logs(data_dir):
	A=[];C=Path(data_dir)/'transactions'
	if not C.is_dir():return A
	for E in sorted(A for A in C.iterdir()if A.is_dir()):
		B=_read(E/'negotiation_state.json')
		if not isinstance(B,dict):continue
		D=[A for A in(B.get('meta')or{}).get('metrics_log')or()if isinstance(A,dict)]
		if D:A.append((_norm((B.get('positions_source')or{}).get('family')),D))
	return A
def compute(logs,family=None,backtest=None):
	J=_norm(family);A={'deals':0,'rounds':0,'applied':0,'accepted':0,'rejected':0,'rate':None,'steps':{},'no_rule':0,'by_rule':{},'repeat':[],'backtest':backtest}
	for(K,L)in logs:
		if J and K and K!=J:continue
		A['deals']+=1;H={}
		for D in L:
			M=int(D.get('round')or 0);A['rounds']+=1;A['no_rule']+=int(D.get('no_rule')or 0);H[M]={}
			for F in D.get('applied')or():
				if not isinstance(F,dict)or not F.get('rule_id'):continue
				C=str(int(F.get('step')or 0));A['applied']+=1;A['steps'][C]=A['steps'].get(C,0)+1;B=A['by_rule'].setdefault(F['rule_id'],{'applied':0,'accepted':0,'rejected':0,'steps':{},'accepted_at':{}});B['applied']+=1;B['steps'][C]=B['steps'].get(C,0)+1;H[M][F['rule_id']]=C
		for D in L:
			I=H.get(int(D.get('outcome_of_round')or 0))or{}
			for G in('accepted','rejected'):
				for E in D.get(G)or():
					A[G]+=1;B=A['by_rule'].setdefault(E,{'applied':0,'accepted':0,'rejected':0,'steps':{},'accepted_at':{}});B[G]+=1
					if G=='accepted'and E in I:B['accepted_at'][I[E]]=B['accepted_at'].get(I[E],0)+1
	N=A['accepted']+A['rejected'];A['rate']=round(A['accepted']/N,3)if N else None
	for(E,B)in A['by_rule'].items():
		for(C,O)in B['accepted_at'].items():
			if C!='0'and O>=REPEAT_MIN:A['repeat'].append({'rule_id':E,'step':int(C),'times':O})
	return A
def main(argv=None):import argparse as E;sys.stdout.reconfigure(encoding='utf-8');B=E.ArgumentParser(description='ארבעת המדדים של הפלייבוק, אצל הלקוח');B.add_argument('--data',required=True);C=B.parse_args(argv);A=compute(deal_logs(C.data));D=Path(C.data)/OUT_NAME;D.write_text(json.dumps(A,ensure_ascii=False,indent=1),encoding='utf-8');print('עסקאות: %d · סבבים: %d · שיעור קבלה: %s · בלי כלל: %d · נשמר: %s'%(A['deals'],A['rounds'],'-'if A['rate']is None else'%d%%'%round(A['rate']*100),A['no_rule'],D));return 0
if __name__=='__main__':sys.exit(main())
