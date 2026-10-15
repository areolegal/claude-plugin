# -*- coding: utf-8 -*-
"""טבלת "לאישורך" בסיכום הפנימי (מימוש ייחוס, הערות הנושא ונותן 4.9, שינויים 83 ו-85).

"לאישורך" היא טבלה אחת שבה עורכת הדין עוברת על כל מה שהרכיב הכריע. היא אינה שרשרת אישורים: אין בה עמודת
"מי מאשר", אין "טעון אישור מנכ"ל" ואין "ממתין לאישור" (החלטת מוצר 1, 14.10.2026). הכרעה שחוצה קו אדום או
יורדת מתחת לנסיגה האחרונה אינה בטבלה כ"מהפלייבוק": היא "נדרשת הכרעתך" (מצב 2) במנת השאלות, ובטבלה היא מופיעה
עם התשובה שניתנה. נושא ציות (מצב 8) לעולם אינו בטבלה.

    from orchestrator.review_table import build_review_table, render_markdown, check_review_table
"""
from common.terms import terms_re

COLUMNS = ('סעיף', 'מה הוכרע', 'תווית מקור')
# 1.2.0: סוג התשובה מוצג בעברית; המחרוזות explicit ו-delegated אינן מגיעות לטבלה
ANSWER_KIND_HE = {'explicit': 'הכרעה מפורשת', 'delegated': 'תשובה כללית, הוחלה ההמלצה'}
ENGLISH_KIND = terms_re(('explicit', 'delegated'))
SOURCE_LABELS = {'playbook': 'מהפלייבוק', 'profile': 'מהפרופיל', 'answer': 'נכנס לנוסח מתשובתכם',
                 'professional': 'שיקול מקצועי', 'other_playbook': 'שיקול מקצועי, בהשראת פלייבוק של סוג אחר'}
BANNED = ('מי מאשר', 'מאשר', 'טעון אישור', 'ממתין לאישור', 'מנכ"ל', 'הנהלה בכירה', 'טבלת הסמכויות')
BANNED_RE = terms_re(BANNED)


def _label(d, default_label):
    if d.get('crosses_red_line'):
        ud = d.get('user_decision') or {}
        if ud.get('answer_kind') == 'explicit':
            return 'חוצה קו אדום: הכרעתך ("%s")' % (ud.get('answer') or 'תשובה מפורשת')
        return 'חוצה קו אדום: נדרשת הכרעתך (מצב 2)'
    return SOURCE_LABELS.get(d.get('source'), default_label)


def build_review_table(decisions, numbering_map=None, default_label='מהפלייבוק', concessions=()):
    """decisions: רשימת הכרעות (dict עם id, summary, source, crosses_red_line, situation, user_decision).
    concessions: ויתורים מכוונים (שורה אחת לכולם, אחרי ההכרעות)."""
    nm = numbering_map or {}
    rows = []
    for d in decisions:
        if d.get('situation') == 8:
            continue  # נושא ציות: בבלוק "נושאי ציות: נדרשת הכרעתך", ולא כאן
        rows.append({'סעיף': nm.get(d.get('id'), d.get('clause_label', d.get('id', ''))),
                     'מה הוכרע': d.get('summary', ''), 'תווית מקור': _label(d, default_label)})
    if concessions:
        rows.append({'סעיף': 'ויתורים מכוונים (%d)' % len(concessions),
                     'מה הוכרע': '; '.join(c.get('topic', '') for c in concessions),
                     'תווית מקור': 'הכרעתך: %s' % ', '.join(sorted({ANSWER_KIND_HE.get(
                         (c.get('user_decision') or {}).get('answer_kind'), 'בלי תשובה') for c in concessions}))})
    return rows


def render_markdown(rows):
    out = ['| %s |' % ' | '.join(COLUMNS), '|%s' % ('---|' * len(COLUMNS))]
    for r in rows:
        out.append('| %s |' % ' | '.join(str(r.get(c, '')).replace('|', '/') for c in COLUMNS))
    return '\n'.join(out)


def check_review_table(rows, decisions=()):
    """הפרות: עמודה או תווית של שרשרת אישורים; קו אדום שנחצה ומתויג "מהפלייבוק"; נושא ציות בטבלה."""
    v = []
    for r in rows:
        if set(r) - set(COLUMNS):
            v.append('extra_column:%s' % ','.join(sorted(set(r) - set(COLUMNS))))
        txt = ' '.join(str(x) for x in r.values())
        if BANNED_RE.search(txt):
            v.append('approval_chain_wording')
        if ENGLISH_KIND.search(txt):
            v.append('english_label')
    by_id = {d.get('id'): d for d in decisions}
    for r, d in zip(rows, decisions):
        if d.get('crosses_red_line') and r.get('תווית מקור') == 'מהפלייבוק':
            v.append('red_line_labeled_from_playbook')
    if any(d.get('situation') == 8 for d in by_id.values()) and any(
            r.get('סעיף') in {d.get('id') for d in by_id.values() if d.get('situation') == 8} for r in rows):
        v.append('compliance_in_table')
    return sorted(set(v))
