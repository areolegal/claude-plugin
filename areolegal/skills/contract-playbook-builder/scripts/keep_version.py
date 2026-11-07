#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (c) Areo. All rights reserved. Licensed under the terms at https://areo.co.il/legal/terms
import argparse,datetime,io,json,shutil,sys
from pathlib import Path
for _s in(sys.stdout,sys.stderr):
	try:_s.reconfigure(encoding='utf-8',errors='replace')
	except(AttributeError,ValueError):pass
KEEP=['playbook-model.json','playbook-core.json','decisions-applied.json','corpus-manifest.json','clause-inventory.json']
KEEP_GLOBS=['*.docx','*.xlsx','*.pptx','*.html']
def version_of(folder):
	A=folder/'playbook-model.json'
	if not A.is_file():return
	try:B=json.loads(io.open(A,encoding='utf-8').read())
	except ValueError as C:sys.exit('playbook-model.json אינו JSON תקין, ולכן אין לכתוב עליו: %s'%C)
	return str(B.get('version')or'0.0')
def main():
	F=argparse.ArgumentParser();F.add_argument('folder');F.add_argument('--check',action='store_true',help='בדיקה בלבד');G=F.parse_args();A=Path(G.folder).resolve()
	if not A.is_dir():sys.exit('אין תיקייה כזאת: %s'%A)
	D=version_of(A)
	if D is None:print('אין בתיקייה playbook-model.json: זו בנייה ראשונה, ואין גרסה לשמור.');return 0
	I=(A/'playbook-model.json').read_bytes()
	for H in(A/'versions').glob('**/*playbook-model.json')if(A/'versions').is_dir()else():
		if H.read_bytes()==I:print('הגרסה הזו כבר שמורה ב-%s, ואין צורך לשמור אותה שוב.'%H.parent.relative_to(A));return 0
	B=A/'versions'/D
	if B.exists():J=datetime.datetime.now().strftime('%Y-%m-%d-%H%M');B=A/'versions'/('%s-%s'%(D,J))
	C=[A/B for B in KEEP if(A/B).is_file()]
	for K in KEEP_GLOBS:C+=[A for A in A.glob(K)if A.is_file()]
	if not C:print('אין מה לשמור בתיקייה %s'%A);return 0
	if G.check:
		print('ישמרו %d קבצים ל-%s:'%(len(C),B))
		for E in C:print('   ',E.name)
		return 0
	B.mkdir(parents=True)
	for E in C:shutil.copy2(E,B/E.name)
	print('הגרסה הקודמת (%s) נשמרה ב-%s, %d קבצים.'%(D,B.relative_to(A),len(C)));print('אפשר לכתוב עכשיו את הגרסה החדשה.');return 0
if __name__=='__main__':raise SystemExit(main())
