#!/usr/bin/env python3
import json, sys
from pathlib import Path

VALID_STATUS={"Draft","InternalReview","ReadyForExternal","Superseded"}

def main(path):
    d=json.loads(Path(path).read_text(encoding='utf-8'))
    e=[]
    for k in ["schema_version","core_version","document_id","status","legal_entity_id","template_lineage","classification"]:
        if d.get(k) in (None,""): e.append(f"missing {k}")
    if d.get('status') not in VALID_STATUS: e.append('invalid status')
    t=d.get('template_lineage') or {}
    for k in ['template_id','template_version','template_status']:
        if not t.get(k): e.append(f"template_lineage missing {k}")
    if d.get('status')=='ReadyForExternal':
        if d.get('classification')!='external_shareable': e.append('ReadyForExternal requires external_shareable classification')
        if d.get('unresolved_material_placeholders'): e.append('ReadyForExternal has unresolved material placeholders')
        for i,x in enumerate(d.get('deviations',[])):
            if x.get('material') and x.get('approval_required') and not x.get('approved_at'):
                e.append(f"deviations[{i}] material deviation lacks approval")
        for i,a in enumerate(d.get('required_approvals',[])):
            if a.get('required') and not a.get('approved_at'):
                e.append(f"required_approvals[{i}] incomplete")
    if e:
        print('INVALID'); [print('-',x) for x in e]; return 1
    print('VALID'); return 0
if __name__=='__main__':
    if len(sys.argv)!=2:
        print('usage: validate_draft_manifest.py MANIFEST.json'); raise SystemExit(2)
    raise SystemExit(main(sys.argv[1]))
