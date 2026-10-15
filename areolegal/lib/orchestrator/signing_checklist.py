# -*- coding: utf-8 -*-
"""רשימת הבדיקה לפני חתימה (מימוש ייחוס, הערות הנושא ונותן 4.9, שינוי 85; נשען על 75).

הרשימה נבנית מתוצאת השער ומקובץ המצב, ואינה נכתבת ביד:
- כל שדה ריק לשלב החתימה שהשער מצא (signing_blank), לפי הפרט ב-entity_details;
- מצייני המקום של הצד שכנגד (תאריך, שם, קווי חתימה);
- השם הרשום של הלקוחה (organization_legal_name, עם "בע"מ" או "Ltd."), כשהוא חסר בפרופיל (שב3-16);
- נספח שההסכם מפנה אליו ולא צורף; בדיקה משפטית פתוחה; ושורות "לתיקון לפני שליחת התגובה" פתוחות.
אין בה "אישורים" (החלטת מוצר 1, 14.10.2026). passed הוא True רק כשאין אף פריט פתוח.

    from orchestrator.signing_checklist import build_signing_checklist
"""
from orchestrator import pre_send


def build_signing_checklist(gate_info, state=None, profile=None, register=None, decisions=None):
    st, prof = state or {}, profile or {}
    checks = []
    blanks = (gate_info or {}).get('placeholders', {}).get('signing_blanks', [])
    for k, v in (st.get('entity_details') or {}).items():
        if (v or {}).get('status') == 'signing_blank':
            checks.append({'item': 'signing_blank', 'detail': k, 'status': 'open'})
    if blanks and not any(c['item'] == 'signing_blank' for c in checks):
        checks.append({'item': 'signing_blank', 'detail': 'unknown', 'count': len(blanks), 'status': 'open'})
    for x in (gate_info or {}).get('placeholders', {}).get('theirs', []):
        checks.append({'item': 'their_placeholder', 'text': x.get('text'), 'status': 'open'})
    if not prof.get('organization_legal_name'):
        checks.append({'item': 'registered_legal_name', 'status': 'open',
                       'text': 'השם הרשום של הלקוחה, כפי שהוא ברשם החברות'})
    for oi in st.get('open_items', []):
        if oi.get('kind') == 'annex' and oi.get('status') != 'done':
            checks.append({'item': 'annex', 'text': oi.get('item'), 'status': 'open'})
    for cl in st.get('clauses', []):
        lr = cl.get('legal_review') or {}
        if cl.get('legal_review_required') and not (lr.get('done_by') and lr.get('done_at')):
            checks.append({'item': 'legal_review', 'clause_id': cl.get('clause_id'), 'status': 'open'})
    if register is not None:
        for fx in pre_send.open_fixes(register, st, decisions):
            checks.append({'item': 'pre_send_fix', 'fix_id': fx.get('id'), 'clause_ref': pre_send.clause_ref(fx),
                           'status': 'open'})
    return {'checks': checks, 'passed': not any(c['status'] == 'open' for c in checks)}
