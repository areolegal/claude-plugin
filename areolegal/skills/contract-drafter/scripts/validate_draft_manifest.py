#!/usr/bin/env python3
import json, sys
from pathlib import Path

try:  # פלט עברי במסוף של Windows
    sys.stdout.reconfigure(encoding="utf-8")
except (AttributeError, ValueError):  # pragma: no cover
    pass

# אין שער אישור של עורך דין על הטיוטה (כלל 6): הסטטוס מתאר את מצב הקובץ בלבד. InternalReview נשאר מוכר לקבצים ישנים
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
    if e:
        print('INVALID'); [print('-',x) for x in e]; return 1
    print('VALID'); return 0
if __name__=='__main__':
    import argparse
    ap=argparse.ArgumentParser(description='Validates a draft manifest (status, lineage, classification, placeholders; no approval gates). '
                                           'Exit 0 valid, 1 invalid, 2 usage error.')
    ap.add_argument('manifest', help='MANIFEST.json')
    raise SystemExit(main(ap.parse_args().manifest))
