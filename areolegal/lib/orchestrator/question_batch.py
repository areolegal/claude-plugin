# -*- coding: utf-8 -*-
"""מנת השאלות האחת שלפני ההכרעות (מימוש ייחוס, הערות הנושא ונותן 4.9, שינוי 85; נשען על 46, 52 ו-70).

בסבב 3 כל רץ כתב את המנה בקוד הדבקה: באחד "חוסם משלוח, תשובה של מילה אחת" הופיע בלי התווית "נדרשת הכרעתך",
שאלת הרכיבים המשלימים נשאלה פעמיים, ושאלת "שווי ההתקשרות" נשאלה על הסכם סודיות בלי תמורה.

כללים:
- "נדרשת הכרעתך" רק בתשעת המצבים (1 עד 9), בתבנית קבועה: "נדרשת הכרעתך (מצב N[, חוסם משלוח])". אין מצב עשירי:
  מצב שאינו 1 עד 9 זורק ValueError. חציית קו אדום או ירידה מתחת לנסיגה האחרונה היא מצב 2 (החלטת מוצר 1,
  14.10.2026), ואין לצידה "מאשר" או "טעון אישור".
- שאלה שאינה "נדרשת הכרעתך" (כרטיס עסקה, רכיבים משלימים) נשאלת בלי התווית.
- כל שאלה נשאלת פעם אחת: מפתח שכבר נשאל (asked_before) אינו נשאל שוב.
- בהסכם בלי תמורה, שאלת השווי של כרטיס העסקה אינה נשאלת.
- פריט חוסם משלוח ראשון; אחריו לפי מספר המצב; אחריו השאר. מעבר ל-max_questions, פריטים מאותו מצב מקובצים לשאלה אחת.

    from orchestrator.question_batch import build_batch
    b = build_batch(items, no_consideration=False, asked_before={'components'})
    b['text'], b['questions'], b['skipped']
"""
from orchestrator.state_builder import SITUATIONS

LABEL = {'he': 'נדרשת הכרעתך', 'en': 'נדרשת הכרעתך'}  # התווית תמיד בעברית, גם בנייר באנגלית (שפת הצ'אט)
BLOCKS = 'חוסם משלוח, תשובה של מילה אחת'


def label_for(situation, blocks_sending=False):
    if situation not in SITUATIONS:
        raise ValueError('אין מצב עשירי ל"נדרשת הכרעתך": %r' % (situation,))
    return '%s (מצב %d%s)' % (LABEL['he'], situation, ', ' + BLOCKS if blocks_sending else '')


def _line(n, it):
    opts = ' '.join('[%s]' % o for o in it.get('options', []))
    rec = (' המלצה: %s.' % it['recommendation'].rstrip('.')) if it.get('recommendation') else ''
    head = ('**%s:** ' % label_for(it['situation'], it.get('blocks_sending'))) if it.get('situation') else ''
    return ('%d. %s%s%s %s' % (n, head, it['text'].rstrip(), rec, opts)).rstrip()


def build_batch(items, no_consideration=False, asked_before=(), max_questions=8, status_line=None):
    """items: [{'key', 'text', 'situation' (1..9 או None), 'recommendation', 'options', 'blocks_sending',
    'kind' (למשל 'deal_card_value', 'components')}]. מחזיר dict: text, questions, skipped."""
    asked = set(asked_before or ())
    qs, skipped, seen = [], [], set()
    for it in items:
        if it.get('situation') is not None and it['situation'] not in SITUATIONS:
            raise ValueError('אין מצב עשירי ל"נדרשת הכרעתך": %r' % (it['situation'],))
        key = it.get('key') or it['text']
        if key in asked or key in seen:
            skipped.append({'key': key, 'why': 'כבר נשאלה'})
            continue
        if no_consideration and it.get('kind') == 'deal_card_value':
            skipped.append({'key': key, 'why': 'הסכם בלי תמורה'})
            continue
        seen.add(key)
        qs.append(it)
    qs.sort(key=lambda x: (not x.get('blocks_sending'), x.get('situation') or 99))
    if len(qs) > max_questions:
        grouped, by_sit = [], {}
        for it in qs:
            if it.get('situation') and not it.get('blocks_sending'):
                by_sit.setdefault(it['situation'], []).append(it)
            else:
                grouped.append(it)
        for sit, group in sorted(by_sit.items()):
            if len(group) == 1:
                grouped.append(group[0])
                continue
            table = '\n'.join('   | %s | %s |' % (g['text'].rstrip('.'), g.get('recommendation', '')) for g in group)
            grouped.append({'key': 'situation-%d' % sit, 'situation': sit, 'options': ['לאשר את כל ההמלצות',
                                                                                     'לשנות שורה'],
                            'text': 'כמה פריטים מאותו סוג:\n   | הפער | ההמלצה |\n' + table})
        qs = grouped
    lines = ([status_line] if status_line else []) + [_line(n, it) for n, it in enumerate(qs, 1)]
    return {'text': '\n'.join(lines), 'questions': qs, 'skipped': skipped}
