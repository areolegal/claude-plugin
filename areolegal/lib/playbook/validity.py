# -*- coding: utf-8 -*-
"""playbook/validity.py: אזהרה קצרה ללקוח כשהפלייבוק שבשימוש אינו עובר את הבדיקות של עצמו.

הבעיה (ניסוי ארבעת הסוגים): פלייבוק שהועתק נכשל במאמת שלו (46 כללים משפטיים בלי שלד משפטי, נימוקים כמעט זהים ב-48
כללים, פשרה לא ריאלית מול גוף ציבורי), וכל הסוכנים עבדו איתו בלי לומר דבר.

מה יש כאן, לכל סוכן שמחיל פלייבוק (הנושא ונותן, מעריך הסיכונים, האסטרטג, המנסח):

    from playbook.validity import playbook_warnings
    for line in playbook_warnings(model, core=core, lang='en'):
        print(line)

- playbook_warnings(model=None, core=None, lang='he') -> list[str]: שורות קצרות בקול של Areo (areo-voice.md),
  בעברית או באנגלית, ריקה כשאין מה לומר. אינה חוסמת, אינה זורקת חריגה, אינה צריכה את ההסכמים, את מלאי הסעיפים או
  את קובץ החילוץ, ואינה כותבת קובץ. מספיק הגרעין לבדו: הבונה כותב לגרעין ולאינדקס את תוצאת הבדיקה (validity).
- validity_summary(model, core=None) -> {'status': 'valid'|'invalid', 'codes': {code: n}, 'rules': {code: n}}:
  התוצאה שהבונה כותב לגרעין (build_playbook_core.py) ולאינדקס (register_playbook.py), כדי שסוכן שיש בידו רק
  הגרעין יוכל להזהיר.

הבדיקות הן תת-קבוצה זולה של playbook/validate_model.py, אותן פונקציות ולא העתק: שלד משפטי ונימוקים
(rationale_findings), נוסח שאינו תואם את תיאורו ופשרה לא ריאלית מול גוף ציבורי (fallback_findings), עמדה בלי הסכם
וסעיף שעליהם נשענה (position_source_findings), ותווית שנסחפה (status.label_findings). כללי לכל סוג הסכם, לכל דין
ולכל סוג חברה.

אין כאן רצפות ותקרות של הדין. נקודה שמחקר הרשת הותר לה ולא נמצא לה מקור מורשה מוצגת ללקוח כ"AREO לא מצאה מקור מורשה
לנקודה זו" (validate_model.no_source_notes), ואינה חוסמת דבר.
"""

try:
    from playbook import status as S
    from playbook import validate_model as V
except ImportError:  # pragma: no cover
    import os
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from playbook import status as S
    from playbook import validate_model as V

# קוד ממצא -> מפתח השורה ללקוח. קוד שאינו כאן נספר תחת 'other'
GROUPS = {
    'LEGAL_CORE_MISSING': 'legal_core', 'LEGAL_CORE_REVIEW_ONLY': 'legal_core', 'LEGAL_CORE_STATUTE': 'legal_core',
    'RATIONALE_DUPLICATE': 'rationale_dup',
    'TRACK_WORDING_MISMATCH': 'wording_mismatch',
    'COUNTERPARTY_UNREALISTIC': 'public_body',
    'SOURCE_NOT_SHOWN': 'source_shown',
    'LABEL_MISMATCH': 'label', 'LABEL_DRIFT': 'label',
}
ORDER = ('no_source', 'source_shown', 'legal_core', 'public_body', 'wording_mismatch', 'rationale_dup', 'label',
         'other', 'no_company_position')

# בקול של Areo: התוצאה, ואחריה פעולה אחת. משפטים קצרים, בלי קודים, בלי שמות של רכיבים, בלי "מסלול" ו"ראיה".
# לכל קבוצה שלושה נוסחים: n (כמה נושאים), one (נושא אחד) ו-some (כשהמספר אינו ידוע, למשל בגרעין ישן או בממצא
# שאינו שייך לנושא אחד)
_HE_REVIEW = 'כדאי שעורך דין יעבור עליהם לפני שמסתמכים עליהם.'
_HE_REVIEW1 = 'כדאי שעורך דין יעבור עליו לפני שמסתמכים עליו.'
TEXT = {
    'he': {
        'no_source': {'n': 'ב-{n} נקודות AREO לא מצאה מקור מורשה. כדאי שעורך דין יבדוק אותן לפני שמסתמכים עליהן.',
                      'one': 'בנקודה אחת AREO לא מצאה מקור מורשה. כדאי שעורך דין יבדוק אותה לפני שמסתמכים עליה.',
                      'some': 'בחלק מהנקודות AREO לא מצאה מקור מורשה. כדאי שעורך דין יבדוק אותן לפני שמסתמכים עליהן.'},
        'source_shown': {'n': 'ב-{n} נושאים לא מוצג על איזה הסכם וסעיף העמדה נשענת. כדאי לבנות מחדש בסוכן הפלייבוק.',
                         'one': 'בנושא אחד לא מוצג על איזה הסכם וסעיף העמדה נשענת. כדאי לבנות מחדש בסוכן הפלייבוק.',
                         'some': 'בחלק מהנושאים לא מוצג על איזה הסכם וסעיף העמדה נשענת. כדאי לבנות מחדש בסוכן '
                                 'הפלייבוק.'},
        'legal_core': {'n': 'ב-{n} נושאים חסר ההסבר המשפטי לעמדה. ' + _HE_REVIEW,
                       'one': 'בנושא אחד חסר ההסבר המשפטי לעמדה. ' + _HE_REVIEW1,
                       'some': 'בחלק מהנושאים חסר ההסבר המשפטי לעמדה. ' + _HE_REVIEW},
        'public_body': {'n': 'ב-{n} נושאים הפשרה מבקשת מגוף ציבורי לוותר על סמכות שאינו יכול לוותר עליה.',
                        'one': 'בנושא אחד הפשרה מבקשת מגוף ציבורי לוותר על סמכות שאינו יכול לוותר עליה.',
                        'some': 'בחלק מהנושאים הפשרה מבקשת מגוף ציבורי לוותר על סמכות שאינו יכול לוותר עליה.'},
        'wording_mismatch': {'n': 'ב-{n} נושאים הנוסח המוצע אינו תואם את העמדה שכתובה לידו. כדאי לבדוק לפני שליחה.',
                             'one': 'בנושא אחד הנוסח המוצע אינו תואם את העמדה שכתובה לידו. כדאי לבדוק לפני שליחה.',
                             'some': 'בחלק מהנושאים הנוסח המוצע אינו תואם את העמדה שכתובה לידו. כדאי לבדוק לפני '
                                     'שליחה.'},
        'rationale_dup': {'some': 'ההסברים לעמדות חוזרים כמעט מילה במילה בין נושאים, ולכן אינם מסבירים את הנושא '
                                  'עצמו.'},
        'label': {'some': 'תיאור המדיניות אינו אחיד בקבצים שלה. כדאי לבנות אותה מחדש בסוכן הפלייבוק.'},
        'other': {'some': 'המדיניות לא עברה את כל הבדיקות שלה. כדאי לבנות אותה מחדש בסוכן הפלייבוק.'},
        'no_company_position': {'some': 'אף עמדה במדיניות אינה נשענת על דוגמה מההסכמים שלכם. כולן המלצה של Areo.'},
        'head': 'לפני שמסתמכים על המדיניות הזו:',
    },
    'en': {
        'no_source': {'n': 'On {n} points, AREO did not find an approved source. Have a lawyer check them before '
                           'relying on them.',
                      'one': 'On one point, AREO did not find an approved source. Have a lawyer check it before '
                             'relying on it.',
                      'some': 'On some points, AREO did not find an approved source. Have a lawyer check them before '
                              'relying on them.'},
        'source_shown': {'n': 'In {n} topics, the agreement and clause the position rests on are not shown. Rebuild '
                              'with the playbook agent.',
                         'one': 'In one topic, the agreement and clause the position rests on are not shown. Rebuild '
                                'with the playbook agent.',
                         'some': 'In some topics, the agreement and clause the position rests on are not shown. '
                                 'Rebuild with the playbook agent.'},
        'legal_core': {'n': 'In {n} topics, the legal reasoning behind the position is missing. Have a lawyer '
                            'review them.',
                       'one': 'In one topic, the legal reasoning behind the position is missing. Have a lawyer '
                              'review it.',
                       'some': 'In some topics, the legal reasoning behind the position is missing. Have a lawyer '
                               'review them.'},
        'public_body': {'n': 'In {n} topics, the compromise asks a public body to give up a power it cannot waive.',
                        'one': 'In one topic, the compromise asks a public body to give up a power it cannot waive.',
                        'some': 'In some topics, the compromise asks a public body to give up a power it cannot '
                                'waive.'},
        'wording_mismatch': {'n': "In {n} topics, the proposed wording doesn't match the position next to it. Check "
                                  "before sending.",
                             'one': "In one topic, the proposed wording doesn't match the position next to it. Check "
                                    "before sending.",
                             'some': "In some topics, the proposed wording doesn't match the position next to it. "
                                     "Check before sending."},
        'rationale_dup': {'some': "The explanations repeat almost word for word across topics, so they don't "
                                  "explain each topic."},
        'label': {'some': 'The policy is described differently across its files. Rebuild it with the playbook '
                          'agent.'},
        'other': {'some': "The policy didn't pass all of its own checks. Rebuild it with the playbook agent."},
        'no_company_position': {'some': "No position in this policy rests on an example from your agreements. All "
                                        "of them are Areo's recommendations."},
        'head': 'Before relying on this policy:',
    },
}


def _lang(lang):
    return 'en' if str(lang or '').strip().lower().startswith('en') else 'he'


def _findings(model):
    """הממצאים של הבדיקות הזולות. כל בדיקה לבדה, כדי שתקלה באחת לא תסתיר את האחרות."""
    out = []
    for fn in (V.rationale_findings, V.fallback_findings, V.position_source_findings):
        try:
            out += fn(model)
        except Exception:  # noqa: BLE001  מודל חלקי: הבדיקה הזו אינה רצה, והאחרות כן
            continue
    return out


def _no_source_points(model):
    """מספר הנקודות שמחקר הרשת הותר להן ולא נמצא להן מקור מורשה (validate_model.no_source_notes)."""
    try:
        return len(V.no_source_notes(model))
    except Exception:  # noqa: BLE001
        return 0


def validity_summary(model, core=None):
    """{'status': 'valid'|'invalid', 'codes': {code: n}, 'rules': {group: n}, 'no_company_position': bool}. רק ממצאים
    בחומרת error נספרים ל-invalid. rules: מספר הנושאים (rule_id שונים) בכל קבוצה. נקודה בלי מקור מורשה (no_source)
    נספרת ב-rules אך אינה הופכת את הפלייבוק ל-invalid: שום דבר אינו נחסם בגללה."""
    model = model if isinstance(model, dict) else {}
    found = [f for f in _findings(model) if f.get('severity') == 'error']
    try:
        found += [{'code': c, 'severity': 'error', 'rule_id': None} for c, _m in S.label_findings(model, core)
                  if c in ('LABEL_MISMATCH', 'LABEL_DRIFT')]
    except Exception:  # noqa: BLE001
        pass
    codes, rules = {}, {}
    for f in found:
        codes[f['code']] = codes.get(f['code'], 0) + 1
        g = GROUPS.get(f['code'], 'other')
        rules.setdefault(g, set())
        if f.get('rule_id'):
            rules[g].add(f['rule_id'])
    try:
        ncp = bool(S.no_company_position(model))
    except Exception:  # noqa: BLE001
        ncp = False
    out = {'status': 'invalid' if found else 'valid', 'codes': dict(sorted(codes.items())),
           'rules': {g: len(v) for g, v in sorted(rules.items())}, 'no_company_position': ncp}
    n = _no_source_points(model)
    if n:
        out['rules']['no_source'] = n
    return out


def _lines(summary, lang):
    T = TEXT[_lang(lang)]
    rules = summary.get('rules') or {}
    groups = set(rules)
    for c in summary.get('codes') or {}:
        groups.add(GROUPS.get(c, 'other'))
    if summary.get('status') == 'invalid' and not groups - {'no_source'}:
        groups.add('other')
    if summary.get('no_company_position'):
        groups.add('no_company_position')
    out = []
    for g in ORDER:
        if g not in groups:
            continue
        forms, n = T[g], rules.get(g)
        if isinstance(n, int) and n == 1 and 'one' in forms:
            out.append(forms['one'])
        elif isinstance(n, int) and n > 1 and 'n' in forms:
            out.append(forms['n'].format(n=n))
        else:
            out.append(forms['some'])
    return out


def _core_no_source_points(core):
    """מספר הסעיפים בגרעין שמסומנים no_approved_source (הבונה כותב אותם מהמודל)."""
    return sum(1 for c in (core.get('clauses') or core.get('rules') or []) if isinstance(c, dict)
               and c.get('no_approved_source'))


def playbook_warnings(model=None, core=None, lang='he'):
    """שורות אזהרה קצרות ללקוח, בעברית (he) או באנגלית (en), כשהפלייבוק שבשימוש אינו עובר את הבדיקות של עצמו, וכשיש בו
    נקודות ש-AREO לא מצאה להן מקור מורשה. רשימה ריקה כשאין מה לומר. model: playbook-model.json (dict), כשהוא בידי
    הסוכן; core: playbook-core.json. בלי model, השורות נגזרות מ-core['validity'] שהבונה כתב (ומסימון
    no_approved_source בסעיפי הגרעין, לגרעין ישן). אינה חוסמת ואינה זורקת חריגה."""
    try:
        if isinstance(model, dict) and model.get('rules') is not None:
            summary = validity_summary(model, core)
        elif isinstance(core, dict) and isinstance(core.get('validity'), dict):
            summary = dict(core['validity'])
            summary['rules'] = dict(summary.get('rules') or {})
            n = _core_no_source_points(core)
            if n and not summary['rules'].get('no_source'):
                summary['rules']['no_source'] = n
        elif isinstance(core, dict):
            n = _core_no_source_points(core)
            return _lines({'status': 'valid', 'rules': {'no_source': n}}, lang) if n else []
        else:
            return []
        return _lines(summary, lang)
    except Exception:  # noqa: BLE001  אזהרה אינה מפילה את הסוכן שקרא לה
        return []


def warning_block(model=None, core=None, lang='he'):
    """אותן שורות, עם שורת פתיחה אחת ("לפני שמסתמכים על המדיניות הזו:"), כטקסט אחד. '' כשאין מה לומר."""
    lines = playbook_warnings(model, core, lang)
    if not lines:
        return ''
    return '\n'.join([TEXT[_lang(lang)]['head']] + ['- ' + x for x in lines])
