#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (c) Areo. All rights reserved. Licensed under the terms at https://areo.co.il/legal/terms
'הבדיקה החוזרת (הערות ענבל, 12.11.2026, 6.2): חמישית מההסכמים החתומים מוחזקת בצד לפני הגזירה, ואחרי שהפלייבוק'
import argparse,io,json,sys
SIGNED='signed','agreement','amendment'
def select(model,min_signed=15):
	A=model;B=sorted(str(A.get('source_id'))for A in A.get('source_log')or()if isinstance(A,dict)and A.get('included')is not False and A.get('doc_role')in SIGNED and A.get('source_id'))
	if len(B)<min_signed:A['backtest']={'status':'not_run','holdout_ids':[],'reason':'%d הסכמים חתומים: מעט מכדי להחזיק חמישית בצד. הספים לא נבדקו מול ההסכמים.'%len(B)};return A
	C=B[4::5];A['backtest']={'status':'holdout','holdout_ids':C,'results':[]};return A
def main(argv=None):
	sys.stdout.reconfigure(encoding='utf-8');D=argparse.ArgumentParser(description=__doc__.split('\n')[0]);E=D.add_subparsers(dest='cmd',required=True);F=E.add_parser('select');F.add_argument('--model',required=True);F.add_argument('--min-signed',type=int,default=15);G=E.add_parser('record');G.add_argument('--model',required=True);G.add_argument('--results',required=True);B=D.parse_args(argv)
	with io.open(B.model,encoding='utf-8')as C:A=json.load(C)
	if B.cmd=='select':A=select(A,B.min_signed);print('בדיקה חוזרת: %s'%('הוחזקו %d הסכמים'%len(A['backtest']['holdout_ids'])if A['backtest']['status']=='holdout'else A['backtest']['reason']))
	else:
		with io.open(B.results,encoding='utf-8')as C:H=[A for A in json.load(C)if isinstance(A,dict)]
		I=A.setdefault('backtest',{'status':'holdout','holdout_ids':[]});I['results']=H;I['status']='done';print('נרשמו %d תוצאות'%len(H))
	with io.open(B.model,'w',encoding='utf-8')as C:json.dump(A,C,ensure_ascii=False,indent=1)
	return 0
if __name__=='__main__':sys.exit(main())
