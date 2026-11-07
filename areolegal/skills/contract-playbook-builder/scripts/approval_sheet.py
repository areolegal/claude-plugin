#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (c) Areo. All rights reserved. Licensed under the terms at https://areo.co.il/legal/terms
'הפקת גיליון "עמדות משא ומתן לאישור", והמניפסט שלו.'
import json,os,sys
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
import areo_lib
from common.cli import OutputRefused,guard_out,no_bytecode,parser
from playbook.approval_sheet import build_sheet
from playbook.status import deliverable_lang
MANIFEST='approval-sheet-manifest.json'
def main(argv=None):
	no_bytecode();B=parser(__doc__.split('\n')[0],out_required=False,out_help='נתיב המניפסט. בלעדיו הוא נכתב כ-%s לצד הגיליון'%MANIFEST);B.add_argument('--model',required=True,help='playbook-model.json');B.add_argument('--out-dir',required=True,help='התיקייה שבה ייכתבו הגיליון והמניפסט');B.add_argument('--company',default='',help='שם החברה, לשער הגיליון');B.add_argument('--lang',default=None,choices=('he','en'),help='שפת הגיליון. בלעדיו: deliverable_language מהפרופיל או מהמודל, וברירת המחדל עברית');B.add_argument('--profile',help='פרופיל-לקוח.json: deliverable_language, לשפת הגיליון');B.add_argument('--token-uid',help='מזהה ההפקה. לבדיקות בלבד; בלעדיו הוא מוגרל');B.add_argument('--no-wording-gate',action='store_true',help='מדלג על שער הנוסח. לאבחון בלבד, ולא להפקה שנשלחת לחתימה');A=B.parse_args(argv)
	if not os.path.exists(A.model):print('המודל אינו קיים: %s'%A.model);return 2
	with open(A.model,encoding='utf-8')as C:G=json.load(C)
	H=None
	if A.profile and os.path.exists(A.profile):
		with open(A.profile,encoding='utf-8')as C:H=json.load(C)
	I=deliverable_lang(G,H,A.lang);os.makedirs(A.out_dir,exist_ok=True);E=A.out or os.path.join(A.out_dir,MANIFEST)
	try:E=guard_out(E,inputs=[A.model])
	except OutputRefused as F:print('סירוב: %s'%F);return 1
	try:J,D=build_sheet(G,A.out_dir,company=A.company,lang=I,token_uid=A.token_uid,check_wording=not A.no_wording_gate)
	except Exception as F:print('ההפקה נעצרה: %s'%F);return 3
	with open(E,'w',encoding='utf-8')as C:json.dump(D,C,ensure_ascii=False,indent=1)
	print('הגיליון : %s'%J);print('המניפסט : %s'%E);print('ההפקה   : %s'%D['token']);print('השפה    : %s'%I);print('שורות   : %d   תאים: %d   שאלות מכריעות: %d'%(len(D.get('rows')or{}),len(D.get('cells')or{}),len(D.get('questions')or{})));print('שמור את המניפסט. בלעדיו העותק החתום אינו ניתן לקליטה.')
	if A.no_wording_gate:print('אזהרה: שער הנוסח דולג. אין לשלוח את הגיליון הזה לחתימה.')
	return 0
if __name__=='__main__':sys.exit(main())
