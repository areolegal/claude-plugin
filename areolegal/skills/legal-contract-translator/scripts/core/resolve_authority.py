#!/usr/bin/env python3
"""Resolve the most-specific authority rule for a transaction/action.

Rules may contain `conditions` with any of:
entity_ids, contract_family_ids, company_roles, counterparty_segments, jurisdictions,
risk_tiers, min_deal_value, max_deal_value, clause_issues.
Unspecified conditions are wildcards. Equal-specificity conflicting matches are AMBIGUOUS.
"""
import argparse, json
from datetime import date
from pathlib import Path

LIST_FIELDS={
    'entity_ids':'legal_entity_id',
    'contract_family_ids':'contract_family_id',
    'company_roles':'company_role',
    'counterparty_segments':'counterparty_segment',
    'jurisdictions':'jurisdiction',
    'risk_tiers':'risk_tier',
    'clause_issues':'clause_issue',
}

def active(rule, as_of):
    ef=rule.get('effective_from'); ex=rule.get('expires_at')
    if ef and as_of < ef: return False
    if ex and as_of > ex: return False
    return True

def match(rule, ctx, action_type, as_of):
    if rule.get('action_type') != action_type or not active(rule, as_of): return None
    c=rule.get('conditions',{}) or {}
    score=0
    for ck, ctxk in LIST_FIELDS.items():
        vals=c.get(ck)
        if vals:
            score += 1
            if ctx.get(ctxk) not in vals: return None
    dv=ctx.get('deal_value')
    if c.get('min_deal_value') is not None:
        score += 1
        if dv is None or float(dv) < float(c['min_deal_value']): return None
    if c.get('max_deal_value') is not None:
        score += 1
        if dv is None or float(dv) > float(c['max_deal_value']): return None
    return score

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('authority_matrix'); ap.add_argument('transaction_context'); ap.add_argument('action_type')
    ap.add_argument('--clause-issue'); ap.add_argument('--jurisdiction'); ap.add_argument('--as-of', default=date.today().isoformat())
    args=ap.parse_args()
    matrix=json.loads(Path(args.authority_matrix).read_text(encoding='utf-8'))
    ctx=json.loads(Path(args.transaction_context).read_text(encoding='utf-8'))
    if args.clause_issue: ctx['clause_issue']=args.clause_issue
    if args.jurisdiction: ctx['jurisdiction']=args.jurisdiction
    matches=[]
    for r in matrix.get('rules',[]):
        s=match(r,ctx,args.action_type,args.as_of)
        if s is not None: matches.append((s,r))
    if not matches:
        print(json.dumps({'status':'NOT_FOUND','action_type':args.action_type},indent=2)); return 1
    best=max(s for s,_ in matches)
    top=[r for s,r in matches if s==best]
    authorities={(r.get('authorized_role'),r.get('authorized_person')) for r in top}
    if len(authorities)>1:
        print(json.dumps({'status':'AMBIGUOUS','specificity':best,'rules':[r.get('authority_rule_id') for r in top]},indent=2)); return 2
    r=top[0]
    print(json.dumps({'status':'RESOLVED','specificity':best,'authority_rule_id':r.get('authority_rule_id'),'authorized_role':r.get('authorized_role'),'authorized_person':r.get('authorized_person')},indent=2)); return 0
if __name__=='__main__': raise SystemExit(main())
