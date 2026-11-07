# -*- coding: utf-8 -*-
# Copyright (c) Areo. All rights reserved. Licensed under the terms at https://areo.co.il/legal/terms
import argparse,io,json,re,sys
if __name__=='__main__':sys.dont_write_bytecode=True
CAPABILITIES={'workspace':{'db':{'rules':[{'path':'comments','read':'view','write':'interact'},{'path':'approvals','read':'view','write':'admin'}]},'user':{'scopes':['profile']},'downloads':True},'risk':{},'prep_center':{}}
USE_RX=re.compile('claude\\.use\\(\\s*[\'"]([a-z]+)[\'"]\\s*\\)')
def used_capabilities(paths):
	A=set()
	for B in paths:
		with io.open(B,encoding='utf-8',errors='replace')as C:A.update(USE_RX.findall(C.read()))
	A.discard('permissions');return A
def missing(kind,paths):A=set(CAPABILITIES.get(kind,{}));return sorted(used_capabilities(paths)-A)
def main(argv=None):
	B=argparse.ArgumentParser(description='ההצהרה על יכולות הריצה של עמוד Areo, ובדיקה שכל יכולת שהתבנית קוראת לה מוצהרת');B.add_argument('--kind',required=True,choices=sorted(CAPABILITIES));B.add_argument('--templates',nargs='+',required=True,help='קובצי התבנית שהעמוד המשותף נבנה מהם');A=B.parse_args(argv);C=missing(A.kind,A.templates);print(json.dumps({'capabilities':CAPABILITIES[A.kind],'missing':C},ensure_ascii=False))
	if C:print("חסרה הצהרה על: %s. הוסיפו אותן ל-CAPABILITIES['%s'] לפני הפרסום"%(', '.join(C),A.kind));return 3
	return 0
if __name__=='__main__':sys.exit(main())
