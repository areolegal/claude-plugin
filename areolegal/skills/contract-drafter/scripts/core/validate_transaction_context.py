#!/usr/bin/env python3
import json, sys
from pathlib import Path

VALID_IMPORTANCE={"low","medium","high","critical"}

def main(path):
    d=json.loads(Path(path).read_text(encoding='utf-8'))
    e=[]
    for k in ["schema_version","core_version","transaction_id","legal_entity_id","contract_family_id","company_role"]:
        if d.get(k) in (None,""): e.append(f"missing {k}")
    if d.get('strategic_importance') and d.get('strategic_importance') not in VALID_IMPORTANCE:
        e.append('invalid strategic_importance')
    if d.get('deal_value') is not None:
        try: float(d['deal_value'])
        except Exception: e.append('deal_value must be numeric when present')
        if not d.get('currency'): e.append('currency required when deal_value is present')
    if e:
        print('INVALID'); [print('-',x) for x in e]; return 1
    print('VALID'); return 0
if __name__=='__main__':
    if len(sys.argv)!=2:
        print('usage: validate_transaction_context.py TRANSACTION.json'); raise SystemExit(2)
    raise SystemExit(main(sys.argv[1]))
