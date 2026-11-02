# -*- coding: utf-8 -*-
"""רשימת הבדיקה לפני חתימה (מימוש ייחוס, הערות הנושא ונותן 4.9, שינוי 85; נשען על 75).

הרשימה נבנית מתוצאת השער ומקובץ המצב, ואינה נכתבת ביד:
- כל שדה ריק לשלב החתימה שהשער מצא (signing_blank), לפי הפרט ב-entity_details;
- מצייני המקום של הצד שכנגד (תאריך, שם, קווי חתימה);
- השם הרשום של הלקוחה, כשהוא חסר בפרופיל: organization_name, ובהסכם באנגלית גם organization_name_en;
- נספח שההסכם מפנה אליו ולא צורף; בדיקה משפטית פתוחה;
- שינוי שקט בלי הכרעה מסומנת, סעיף STUCK, WALK-AWAY או OPENED, ונקודה לשיחה שעוד לא נסגרה (בדיקה עצמאית S1c,
  28.10.2026: 15.2 נשאר נקודה פתוחה עד סבב הסגירה, והרשימה לא הציגה אותו).
- בדיקה שעורך הדין או הרכיב ביצעו בקריאה ונכשלה (manual_check): שמות הישויות, מספרי רישום, חותמים וסמכות,
  תאריכים, נספחים, שאריות או הפניות (round_tools.py signing --fail). בדיקה שנכשלה נשארת פתוחה בהרצות הבאות עד
  שנמסר שהיא עברה (--pass), ואינה נמחקת בשקט.
אין בה "אישורים" (החלטת מוצר 1, 14.10.2026). passed הוא True רק כשאין אף פריט פתוח. המרשם של מעריך הסיכונים אינו
נקרא כאן; הפרמטר register נשאר בחתימה לתאימות, ואינו בשימוש.

שפה (דרישת מוצר 28.10.2026): הרשימה היא תוצר, ולכן בשפת התוצר (deliverable_language). lang='en' נותן את הטקסט
הקבוע ואת label של כל פריט באנגלית; item נשאר קוד קבוע, זהה בשתי השפות.

    from orchestrator.signing_checklist import build_signing_checklist
"""
LEGAL_NAME = {'he': 'השם הרשום של הלקוחה, כפי שהוא ברשם החברות',
              'en': "The client's registered name, as it appears in the companies register"}
LEGAL_NAME_EN = {'he': 'השם הרשום של הלקוחה באנגלית (organization_name_en), להסכם באנגלית',
                 'en': "The client's registered English name (organization_name_en), for an English agreement"}
# הבדיקות שעורך הדין או הרכיב מבצעים בקריאה (n7b-round-steps.md, שלב ו). הנוסח הנקי מול המוסכם נבדק ב-clean-copy
MANUAL_CHECKS = ('entity_names', 'registration_numbers', 'signatories_authority', 'dates', 'annexes',
                 'no_leftovers', 'cross_references')
# התווית שמוצגת לכל פריט ברשימה לפני חתימה
ITEM_LABELS = {
    'he': {'signing_blank': 'שדה ריק לשלב החתימה', 'their_placeholder': 'מציין מקום של הצד שכנגד',
           'registered_legal_name': 'השם הרשום של הלקוחה', 'annex': 'נספח שלא צורף',
           'legal_review': 'בדיקה משפטית פתוחה', 'manual_check': 'בדיקה בקריאה שנכשלה',
           'silent_change': 'שינוי שלא סומן, בלי הכרעה', 'open_clause': 'סעיף שלא הוסכם',
           'talking_point': 'נקודה לשיחה שלא נסגרה'},
    'en': {'signing_blank': 'Field left blank for signing', 'their_placeholder': "Counterparty's placeholder",
           'registered_legal_name': "Client's registered name", 'annex': 'Annex not attached',
           'legal_review': 'Open legal review', 'manual_check': 'Check by reading that failed',
           'silent_change': 'Unmarked change without a decision', 'open_clause': 'Clause not agreed',
           'talking_point': 'Talking point not closed'},
}
STATUS = {'he': {'open': 'פתוח', 'closed': 'סגור', 'passed': 'עובר: כן',
                 'failed': 'עובר: לא. העותק לחתימה אינו מופק'},
          'en': {'open': 'Open', 'closed': 'Closed', 'passed': 'Passed: yes',
                 'failed': 'Passed: no. The signing copy is not produced'}}


def _lang(lang):
    return 'en' if str(lang or '').lower()[:2] == 'en' else 'he'


def parse_manual(values):
    """--fail "<check>=<פרט>": רשימת {check, detail}. check חייב להיות אחד מ-MANUAL_CHECKS (ValueError אחרת)."""
    out = []
    for v in values or ():
        if isinstance(v, dict):
            check, detail = v.get('check'), v.get('detail') or ''
        else:
            check, _, detail = str(v).partition('=')
        check = (check or '').strip()
        if check not in MANUAL_CHECKS:
            raise ValueError('בדיקה לא מוכרת: %r (אחת מ: %s)' % (check, ', '.join(MANUAL_CHECKS)))
        out.append({'check': check, 'detail': detail.strip()})
    return out


def build_signing_checklist(gate_info, state=None, profile=None, register=None, decisions=None, lang='he',
                            manual=None):
    """manual: בדיקות בקריאה שנכשלו ([{check, detail}] או "<check>=<פרט>"), כל אחת פריט פתוח."""
    st, prof = state or {}, profile or {}
    lang = _lang(lang)
    agreement_lang = _lang((gate_info or {}).get('lang') or (st.get('meta') or {}).get('lang'))
    checks = []
    blanks = (gate_info or {}).get('placeholders', {}).get('signing_blanks', [])
    for k, v in (st.get('entity_details') or {}).items():
        if (v or {}).get('status') == 'signing_blank':
            checks.append({'item': 'signing_blank', 'detail': k, 'status': 'open'})
    if blanks and not any(c['item'] == 'signing_blank' for c in checks):
        checks.append({'item': 'signing_blank', 'detail': 'unknown', 'count': len(blanks), 'status': 'open'})
    for x in (gate_info or {}).get('placeholders', {}).get('theirs', []):
        checks.append({'item': 'their_placeholder', 'text': x.get('text'), 'status': 'open'})
    if not str(prof.get('organization_name') or '').strip():
        checks.append({'item': 'registered_legal_name', 'status': 'open', 'text': LEGAL_NAME[lang]})
    elif agreement_lang == 'en' and not str(prof.get('organization_name_en') or '').strip():
        checks.append({'item': 'registered_legal_name', 'status': 'open', 'text': LEGAL_NAME_EN[lang]})
    for oi in st.get('open_items', []):
        if oi.get('kind') == 'annex' and oi.get('status') != 'done':
            checks.append({'item': 'annex', 'text': oi.get('item'), 'status': 'open'})
    # אין פריט "בדיקה משפטית פתוחה" ברשימה שלפני חתימה (כלל יסוד 6): עורך דין מאשר את הפלייבוק בלבד
    from orchestrator.state_builder import unresolved_silent_changes, open_point_clauses
    for x in unresolved_silent_changes(st, None) if st.get('meta') else ():
        checks.append({'item': 'silent_change', 'detail': x.get('clause') or x.get('id'), 'status': 'open'})
    for cl in st.get('clauses', []):
        if cl.get('status') in ('STUCK', 'WALK-AWAY', 'OPENED'):
            checks.append({'item': 'open_clause', 'clause_id': cl.get('clause_id'),
                           'detail': '%s (%s)' % (cl.get('contract_ref') or cl.get('clause_id'), cl['status']),
                           'status': 'open'})
    # נקודה לשיחה שלא נסגרה (open_point_clauses), על סעיף שעוד לא הוסכם, או נקודה שנכתבה ביד בלי סעיף
    held = open_point_clauses(st)
    closed = {cl.get('clause_id') for cl in st.get('clauses', []) if cl.get('status') == 'CLOSED'}
    for p in st.get('talking_points') or ():
        if not isinstance(p, dict) or p.get('status') in ('closed_in_call', 'closed'):
            continue
        pid = str(p.get('id') or '')
        ids = list(p.get('clause_ids') or ()) or ([pid.split(':', 2)[2].split('#')[0]] if pid.startswith('auto:') else [])
        if (ids and any(i in held and i not in closed for i in ids)) or (not ids and p.get('source') != 'auto'):
            checks.append({'item': 'talking_point', 'detail': p.get('topic') or p.get('text') or p.get('id'),
                           'status': 'open'})
    for m in parse_manual(manual):
        checks.append({'item': 'manual_check', 'check': m['check'], 'detail': m['detail'] or m['check'],
                       'status': 'open'})
    for c in checks:
        c['label'] = ITEM_LABELS[lang].get(c['item'], c['item'])
    return {'checks': checks, 'passed': not any(c['status'] == 'open' for c in checks)}


def render_lines(res, lang=None):
    """הרשימה כשורות טקסט, בשפת התוצר: [מצב] תווית: פרט, ושורת הסיכום."""
    lang = _lang(lang)
    S = STATUS[lang]
    out = []
    for c in res.get('checks') or []:
        detail = c.get('detail') or c.get('text') or c.get('clause_id') or ''
        label = c.get('label') or ITEM_LABELS[lang].get(c.get('item'), c.get('item'))
        out.append('  [%s] %s%s' % (S['open'] if c.get('status') == 'open' else S['closed'], label,
                                    (': %s' % detail) if detail else ''))
    out.append(S['passed'] if res.get('passed') else S['failed'])
    return out
