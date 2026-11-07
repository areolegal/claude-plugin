#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (c) Areo. All rights reserved. Licensed under the terms at https://areo.co.il/legal/terms
import json,sys
from pathlib import Path
try:sys.stdout.reconfigure(encoding='utf-8')
except(AttributeError,ValueError):pass
VALID_STATUS={'Draft','InternalReview','ReadyForExternal','Superseded'}
def main(path):
	B=json.loads(Path(path).read_text(encoding='utf-8'));A=[]
	for C in['schema_version','core_version','document_id','status','legal_entity_id','template_lineage','classification']:
		if B.get(C)in(None,''):A.append(f"missing {C}")
	if B.get('status')not in VALID_STATUS:A.append('invalid status')
	D=B.get('template_lineage')or{}
	for C in['template_id','template_version','template_status']:
		if not D.get(C):A.append(f"template_lineage missing {C}")
	if B.get('status')=='ReadyForExternal':
		if B.get('classification')!='external_shareable':A.append('ReadyForExternal requires external_shareable classification')
		if B.get('unresolved_material_placeholders'):A.append('ReadyForExternal has unresolved material placeholders')
	if A:print('INVALID');[print('-',A)for A in A];return 1
	print('VALID');return 0
if __name__=='__main__':import argparse;ap=argparse.ArgumentParser(description='Validates a draft manifest (status, lineage, classification, placeholders; no approval gates). Exit 0 valid, 1 invalid, 2 usage error.');ap.add_argument('manifest',help='MANIFEST.json');raise SystemExit(main(ap.parse_args().manifest))
