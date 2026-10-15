# -*- coding: utf-8 -*-
"""risk/pre_send.py: חוזה הלולאה לפני משלוח, הצד של מעריך הסיכונים (הערות 3.6).

הבעיה (סבב 3): המרשם של שתי העסקאות כלל pre_send_fixes, אבל הן לא חזרו לנושא ונותן; העותק "למשלוח" של C1
נשאר בתיקייה תחת השם הסופי, ושער המשלוח עבר על פערים שהתגובה יצרה. המהנדס 3, המנהל המסחרי 1, עורך הדין של
הצד שכנגד 5.

החוזה (משותף להערות מעריך הסיכונים 3.6 ולהערות הנושא ונותן 4.9):
- המרשם (risk-register.json, בתיקיית העסקה) הוא המקור. כל שורה ב-pre_send_fixes[]:
    id          "PSF-01": מזהה יציב בתוך המרשם
    clause_ref  מזהה הסעיף בקובץ המצב (מפתח ב-numbering_map, או clauses[].clause_id); לעולם לא מזהה כלל
    status      open | resolved | accepted_as_concession (בקוד הנושא ונותן: conceded, אותו ערך). מעריך הסיכונים
                כותב תמיד open.
    kind        missing | incomplete | created_by_response | polish. polish: ליטוש שאינו משנה את התוצאה המשפטית;
                מוצג בשורה נפרדת ואינו חוסם משלוח.
    kind, gap, where, risk_ids  כמו בסכמה 3.5
- הנושא ונותן קורא את השורות (fixes_for_negotiation), פותח מחדש את ההכרעה בסעיף clause_ref, ומסמן כל שורה
  resolved (ההכרעה תוקנה) או accepted_as_concession (נרשם ויתור מכוון ב-deliberate_concessions עם אותו
  clause_ref). שער המשלוח שלו מסרב להפיק עותק למשלוח כל עוד יש שורה open, וכשהמרשם חדש מהעותק.
- מעריך הסיכונים אינו כותב לקובץ המצב. בהרצה הבאה, ויתור שנרשם מופיע כסיכון שהתקבל.
"""
import hashlib
import io
import json
import os
import sys

if __name__ == '__main__':
    sys.dont_write_bytecode = True   # הרצה משורת הפקודה אינה כותבת __pycache__ לתוך החבילה

try:
    from common.cli import guard_out, parser, run, write_json
except ImportError:  # pragma: no cover
    import sys as _sys
    _sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from common.cli import guard_out, parser, run, write_json

FIX_FIELDS = ('id', 'clause_ref', 'status', 'kind', 'gap', 'where', 'risk_ids')
OPEN = 'open'


def load(path):
    with io.open(path, encoding='utf-8') as fh:
        return json.load(fh)


def fixes_for_negotiation(register, register_path=None):
    """מה שהנושא ונותן צריך מהמרשם, בלי שאר הדוח."""
    M = register.get('meta') or {}
    out = {
        'transaction_id': M.get('transaction_id'),
        'text_status': (M.get('source_version') or {}).get('text_status'),
        'generated_at': M.get('generated_at'),
        'last_updated': M.get('last_updated'),
        'fixes': [{k: p.get(k) for k in FIX_FIELDS} for p in register.get('pre_send_fixes') or []],
    }
    if register_path:
        with open(register_path, 'rb') as fh:
            out['register_sha256'] = hashlib.sha256(fh.read()).hexdigest()
        out['register_mtime'] = os.path.getmtime(register_path)
    return out


def open_fixes(register):
    """שורות פתוחות שחוסמות משלוח (ליטוש אינו חוסם)."""
    return [p for p in register.get('pre_send_fixes') or [] if (p.get('status') or OPEN) == OPEN
            and p.get('kind') != 'polish']


def contract_errors(register, state=None):
    """בדיקה ממוקדת של החוזה (גם הוולידטור בודק אותה): id, clause_ref ו-status בכל שורה; clause_ref קיים
    בקובץ המצב; מזהה העסקה זהה."""
    E = []
    seen = set()
    known = set(((state or {}).get('numbering_map') or {}).keys()) | {
        c.get('clause_id') for c in (state or {}).get('clauses') or [] if c.get('clause_id')}
    for i, p in enumerate(register.get('pre_send_fixes') or []):
        for k in ('id', 'clause_ref', 'status'):
            if not p.get(k):
                E.append('pre_send %d: חסר %s' % (i, k))
        if p.get('id') in seen:
            E.append('pre_send %d: id כפול' % i)
        seen.add(p.get('id'))
        if p.get('status') and p['status'] not in ('open', 'resolved', 'accepted_as_concession', 'conceded'):
            E.append('pre_send %d: status לא חוקי' % i)
        if state is not None and p.get('clause_ref') and p['clause_ref'] not in known:
            E.append('pre_send %d: clause_ref %s אינו בקובץ המצב' % (i, p['clause_ref']))
    if state is not None:
        tid = ((state.get('meta') or {}).get('transaction_id'))
        if tid and tid != (register.get('meta') or {}).get('transaction_id'):
            E.append('המרשם שייך לעסקה אחרת')
    return E


def main(argv=None):
    """python -I pre_send.py --register <risk-register.json> [--out fixes.json]. המרשם נקרא בלבד."""
    ap = parser('השורות "לתיקון" שהנושא ונותן קורא מהמרשם', out_required=False)
    ap.add_argument('--register', required=True, help='risk-register.json (קריאה בלבד)')
    a = ap.parse_args(argv)
    data = fixes_for_negotiation(load(a.register), a.register)
    if a.out:
        write_json(a.out, data, inputs=[a.register])
    sys.stdout.reconfigure(encoding='utf-8')
    print(json.dumps(data, ensure_ascii=False, indent=1))
    return 0


if __name__ == '__main__':
    sys.exit(run(main))
