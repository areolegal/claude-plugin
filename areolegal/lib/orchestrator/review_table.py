# -*- coding: utf-8 -*-
"""טבלת "לאישורך" בסיכום הפנימי (מימוש ייחוס, הערות הנושא ונותן 4.9, שינויים 83 ו-85).

"לאישורך" היא טבלה אחת שבה עורכת הדין עוברת על כל מה שהרכיב הכריע. היא אינה שרשרת אישורים: אין בה עמודת
"מי מאשר", אין "טעון אישור מנכ"ל" ואין "ממתין לאישור" (החלטת מוצר 1, 14.10.2026). הכרעה שחוצה קו אדום או
יורדת מתחת לנסיגה האחרונה אינה בטבלה כ"מהפלייבוק": היא "נדרשת הכרעתך" (מצב 2) במנת השאלות, ובטבלה היא מופיעה
עם התשובה שניתנה. נושא ציות (מצב 8) לעולם אינו בטבלה.

    from orchestrator.review_table import build_review_table, render_markdown, check_review_table

שפה (דרישת מוצר 28.10.2026): הטבלה היא חלק מהסיכום הפנימי, תוצר, ולכן בשפת התוצר (deliverable_language). lang='en'
נותן עמודות, תוויות וויתורים באנגלית; lang='he' (ברירת המחדל) כמו תמיד. שמות העמודות הם גם המפתחות בשורה.
"""
import re

HEB_RX = re.compile('[א-ת]')

from common.terms import terms_re

COLUMNS = ('סעיף', 'מה הוכרע', 'תווית מקור')
# 1.2.0: סוג התשובה מוצג בעברית; המחרוזות explicit ו-delegated אינן מגיעות לטבלה
ANSWER_KIND_HE = {'explicit': 'הכרעה מפורשת', 'delegated': 'תשובה כללית, הוחלה ההמלצה'}
ENGLISH_KIND = terms_re(('explicit', 'delegated'))
# התוויות בטבלה בקול של Areo (areo-voice.md): "מהמדיניות שלכם", "מטיוטת המדיניות". התוויות הישנות ("מהפלייבוק",
# "מפלייבוק מוצע") עדיין נקראות (LEGACY_LABELS), בקובצי הכרעות ובטבלאות שנשמרו קודם
SOURCE_LABELS = {'playbook': 'מהמדיניות שלכם', 'proposed_playbook': 'מטיוטת המדיניות', 'profile': 'מהפרופיל', 'answer': 'נכנס לנוסח מתשובתכם',
                 'professional': 'שיקול מקצועי', 'other_playbook': 'שיקול מקצועי, בהשראת פלייבוק של סוג אחר'}
BANNED = ('מי מאשר', 'מאשר', 'טעון אישור', 'ממתין לאישור', 'מנכ"ל', 'הנהלה בכירה', 'טבלת הסמכויות')
BANNED_RE = terms_re(BANNED)
# אותה טבלה באנגלית. התוויות אינן משתמשות במחרוזות explicit ו-delegated, כדי שהבדיקה english_label תישאר תקפה
COLUMNS_EN = ('Clause', 'What was decided', 'Source label')
ANSWER_KIND_EN = {'explicit': 'your express decision', 'delegated': 'a general answer, the recommendation was applied'}
SOURCE_LABELS_EN = {'playbook': 'From your policy', 'proposed_playbook': 'From the draft policy',
                    'profile': 'From the profile',
                    'answer': 'Entered the wording from your answer', 'professional': 'Professional judgment',
                    'other_playbook': 'Professional judgment, inspired by a playbook of another type'}
TXT = {'he': {'cols': COLUMNS, 'kind': ANSWER_KIND_HE, 'src': SOURCE_LABELS, 'pb': SOURCE_LABELS['playbook'],
              'ppb': SOURCE_LABELS['proposed_playbook'],
              'red_ans': 'חוצה קו אדום: הכרעתך ("%s")', 'red_ans_none': 'תשובה מפורשת',
              'red_need': 'חוצה קו אדום: נדרשת הכרעתך', 'conc': 'ויתורים מכוונים (%d)',
              'conc_label': 'הכרעתך: %s', 'no_answer': 'בלי תשובה',
              'stance': {'stricter': ', בגישה מחמירה', 'lenient': ', בגישה מקלה'},
              'hidden': 'ועוד %d סעיפים שקיבלנו כמו שהם. הרשימה המלאה מוצגת כשתבקשו.'},
       'en': {'cols': COLUMNS_EN, 'kind': ANSWER_KIND_EN, 'src': SOURCE_LABELS_EN, 'pb': SOURCE_LABELS_EN['playbook'],
              'ppb': SOURCE_LABELS_EN['proposed_playbook'],
              'red_ans': 'Crosses a red line: your decision ("%s")', 'red_ans_none': 'an express answer',
              'red_need': 'Crosses a red line: your decision is needed',
              'conc': 'Deliberate concessions (%d)', 'conc_label': 'Your decision: %s', 'no_answer': 'no answer',
              'stance': {'stricter': ', stricter approach', 'lenient': ', more lenient approach'},
              'hidden': 'And %d more clauses we accepted as they are. The full list is shown on request.'}}
# הבסיס של ההכרעה (decision_basis) והתווית שבה (source_label), כשאין source: איזו תווית מקור (S1d-R2)
BASIS_SOURCE = {'PolicyBenchmark': 'playbook', 'PolicyDerived': 'playbook', 'ExpertJudgment': 'professional',
                'UserDecided': 'answer', 'Profile': 'profile', 'ProfileFact': 'profile'}
LEGACY_LABELS = {'מהפלייבוק': 'playbook', 'מפלייבוק מוצע': 'proposed_playbook', 'From the playbook': 'playbook',
                 'From the proposed playbook': 'proposed_playbook'}
LABEL_KEY_HE = dict({v: k for k, v in SOURCE_LABELS.items()}, **{k: v for k, v in LEGACY_LABELS.items() if HEB_RX.search(k)})
PLAYBOOK_LABELS = {SOURCE_LABELS['playbook'], SOURCE_LABELS_EN['playbook'], 'מהפלייבוק', 'From the playbook'}
PROPOSED_LABELS = {SOURCE_LABELS['proposed_playbook'], SOURCE_LABELS_EN['proposed_playbook'], 'מפלייבוק מוצע',
                   'From the proposed playbook'}
HEB = re.compile('[א-ת]')
BANNED_EN_RE = terms_re(('who approves', 'approver', 'requires approval', 'pending approval', 'CEO',
                         'senior management', 'authority table'))


def _lang(lang):
    return 'en' if str(lang or '').lower()[:2] == 'en' else 'he'


def columns(lang='he'):
    """שמות העמודות (והמפתחות בכל שורה) בשפת התוצר."""
    return TXT[_lang(lang)]['cols']


def _label(d, default_label, lang='he', proposed=False):
    t = TXT[_lang(lang)]
    if d.get('crosses_red_line'):
        ud = d.get('user_decision') or {}
        if ud.get('answer_kind') == 'explicit':
            return t['red_ans'] % (ud.get('answer') or t['red_ans_none'])
        return t['red_need']
    src = d.get('source')
    # התווית שבהכרעה עצמה (source_label, ובלעדיה הבסיס, decision_basis) גוברת: בהרצה S1d-R2 כל שורה קיבלה "מפלייבוק
    # מוצע", גם שיקול מקצועי ותשובת הלקוחה. בטבלה באנגלית תווית בעברית מתורגמת לפי הבסיס
    own = str(d.get('source_label') or '').strip()
    if own in ('areo_proposal', 'הצעת Areo', 'Areo proposal'):
        # סעיף AREO: אין לו עמדה בפלייבוק, וההכרעה היא הצעת Areo. התווית האחידה של כלל 3.5: "סעיף AREO: <נושא>"
        # (EN: "Areo clause: <topic>"), לפי topic של ההכרעה, ובלעדיו summary
        topic = str(d.get('topic') or d.get('summary') or '').strip().rstrip('.')
        own = ('Areo clause: %s' if _lang(lang) == 'en' else 'סעיף AREO: %s') % (topic or d.get('id') or '')
    if own in LEGACY_LABELS:
        # תווית ישנה בקובץ הכרעות שנשמר קודם: מוצגת בנוסח החדש, בשפת הטבלה
        own = (SOURCE_LABELS_EN if _lang(lang) == 'en' else SOURCE_LABELS)[LEGACY_LABELS[own]]
    if own and _lang(lang) == 'en' and HEB.search(own):
        own = SOURCE_LABELS_EN.get(LABEL_KEY_HE.get(own) or BASIS_SOURCE.get(d.get('decision_basis')) or '', '')
    if src is None and not own:
        src = BASIS_SOURCE.get(d.get('decision_basis'))
    if own:
        label = t['ppb'] if proposed and own in PLAYBOOK_LABELS else own
    elif proposed and src in (None, 'playbook'):
        label = t['ppb']   # פלייבוק במעמד Draft או "מוצע": לעולם לא "מהפלייבוק" (באג 7, הרצה S1b)
    else:
        label = t['src'].get(src, default_label if default_label is not None else t['pb'])
    # הכרעה שנבעה מהגישה להחלת הפלייבוק (stance_applied): התווית אומרת זאת, כדי שעורך הדין יראה למה
    return label + t['stance'].get(d.get('stance_applied'), '')


def shown_to_client(d, conceded=()):
    """האם ההכרעה בטבלה שבתצוגה (הרצה S1c, 28.10.2026: הטבלה מנתה את כל 239 ההכרעות, כולל כל הקבלות): כל הכרעה
    שאינה "קבל", וקבלה רק כשהיא מהותית (material: true, או tier: deal_breaker), ויתור מכוון שנרשם (המזהה שלה
    ב-deliberate_concessions[].clause_ref, או deliberate_concession: true), חוצה קו אדום, או נבעה מהגישה
    (stance_applied). tier: deliberate_concession לבדו הוא הדרגה של הוראה משנית שמתקבלת כמו שהיא (n3b-matrix.md),
    ואינו מכניס לתצוגה. הכרעה שהועברה מהסבב הקודם (carried_from) אינה בתצוגה. הרשימה המלאה נשמרת בקובץ המצב."""
    if d.get('op') != 'accept':
        return True
    if d.get('carried_from') and not d.get('crosses_red_line'):
        return False   # הכרעה מהסבב הקודם, שהועברה לפסקה שלא השתנתה (round_tools.py carry): לא הוכרעה בסבב הזה
    return bool(d.get('material') or d.get('tier') == 'deal_breaker' or d.get('deliberate_concession')
                or d.get('id') in set(conceded or ()) or d.get('crosses_red_line') or d.get('stance_applied'))


COMPLIANCE_RX = re.compile(r'bribery|corruption|FCPA|anti-?bribery|sanction|boycott|export control|money laundering|'
                           r'\bAML\b|modern slavery|שוחד|שחיתות|סנקצי|חרם|פיקוח על יצוא|הלבנת הון|מימון טרור', re.I)


def is_compliance(d):
    """נושא ציות (מצב 8): situation 8, compliance: true, או נושא ציות בשם הנושא או בכותרת הכלל. אינו בטבלת "לאישורך",
    אלא בבלוק "נושאי ציות: נדרשת הכרעתך"."""
    if d.get('situation') == 8 or d.get('compliance') is True or d.get('kind') == 'compliance':
        return True
    return bool(COMPLIANCE_RX.search(' '.join(str(d.get(k) or '') for k in ('topic', 'category_name', 'rule_title'))))


OP_WHAT = {'he': {'accept': 'קיבלנו את הנוסח שלהם', 'delete_paragraph': 'מחקנו את הסעיף', 'comment_only': 'הערה בלבד, בלי שינוי',
                  'for_call': 'נשאיר לשיחה עם הצד השני', 'insert_paragraph': 'הוספנו סעיף', 'replace': 'תיקנו את הנוסח',
                  'replace_span': 'תיקנו את הנוסח'},
           'en': {'accept': 'We accepted their wording', 'delete_paragraph': 'We deleted the clause',
                  'comment_only': 'A comment only, no change', 'for_call': 'Left for a call with the other side',
                  'insert_paragraph': 'We added a clause', 'replace': 'We edited the wording',
                  'replace_span': 'We edited the wording'}}


def clause_ref(d, nm=None, lang='he'):
    """מספר הסעיף בהסכם (numbering_map), ובלעדיו clause_label או מספר הפסקה. מזהה פנימי (A41, K8) אינו מוצג."""
    v = (nm or {}).get(d.get('id')) or d.get('clause_label')
    if v:
        return v
    if isinstance(d.get('para'), int):
        return ('Paragraph %d' if _lang(lang) == 'en' else 'פסקה %d') % (d['para'] + 1)
    if isinstance(d.get('after_para'), int):
        return ('New clause after paragraph %d' if _lang(lang) == 'en' else 'סעיף חדש אחרי פסקה %d') % (d['after_para'] + 1)
    return ''


def what_decided(d, lang='he'):
    """העמודה "מה הוכרע" לעולם אינה ריקה: summary, ובלעדיו plain_effect, המשפט הראשון של הבועה לצד השני, הנוסח
    שנכנס, או תיאור הפעולה."""
    for k in ('summary', 'plain_effect'):
        if str(d.get(k) or '').strip():
            return str(d[k]).strip()
    ext = str(d.get('external_comment') or '').strip()
    if ext:
        return re.split(r'(?<=[.!?])\s', ext, 1)[0][:160]
    t = OP_WHAT[_lang(lang)]
    new = str(d.get('new') or d.get('new_text') or d.get('text') or '').strip()
    base = t['for_call'] if d.get('coverage') == 'for_call' else t.get(d.get('op'), t['replace'])
    return ('%s: "%s"' % (base, new[:80] + ('...' if len(new) > 80 else ''))) if new else base


def table_decisions(decisions):
    """ההכרעות שמקבלות שורה: בלי נושאי ציות, ושורה אחת לאשכול (cluster_id), ולא "(המשך)" לכל פסקה באשכול."""
    out, clusters = [], set()
    for d in decisions:
        if is_compliance(d):
            continue
        c = d.get('cluster_id')
        if c and c in clusters:
            continue
        if c:
            clusters.add(c)
        out.append(d)
    return out


def display_rows(decisions, rows, concessions=()):
    """השורות לתצוגה מתוך השורות המלאות (אותו סדר כמו decisions; שורת הוויתורים, כשיש, נשארת). concessions:
    deliberate_concessions של קובץ המצב. מחזיר (rows, hidden_count)."""
    conceded = {c.get('clause_ref') for c in concessions or () if isinstance(c, dict)}
    shown = table_decisions(decisions)
    out, hidden = [], 0
    for i, r in enumerate(rows):
        if i < len(shown) and not shown_to_client(shown[i], conceded):
            hidden += 1
            continue
        out.append(r)
    return out, hidden


def hidden_line(n, lang='he'):
    return TXT[_lang(lang)]['hidden'] % n


def build_review_table(decisions, numbering_map=None, default_label=None, concessions=(), lang='he', proposed=False):
    """decisions: רשימת הכרעות (dict עם id, summary, source, crosses_red_line, situation, user_decision).
    concessions: ויתורים מכוונים (שורה אחת לכולם, אחרי ההכרעות). lang: שפת התוצר (he או en). proposed: הפלייבוק
    במעמד Draft או "מוצע" (resolve_playbook.is_proposed_status): התווית "מפלייבוק מוצע"."""
    t = TXT[_lang(lang)]
    c_clause, c_what, c_label = t['cols']
    nm = numbering_map or {}
    rows = []
    for d in table_decisions(decisions):   # נושא ציות: בבלוק "נושאי ציות: נדרשת הכרעתך", ולא כאן
        rows.append({c_clause: clause_ref(d, nm, lang),
                     c_what: what_decided(d, lang),
                     c_label: _label(d, default_label, lang, proposed)})
    if concessions:
        rows.append({c_clause: t['conc'] % len(concessions),
                     c_what: '; '.join(c.get('topic', '') for c in concessions),
                     c_label: t['conc_label'] % ', '.join(sorted({t['kind'].get(
                         (c.get('user_decision') or {}).get('answer_kind'), t['no_answer']) for c in concessions}))})
    return rows


def _row_lang(rows):
    """שפת הטבלה לפי מפתחות השורות (לבדיקה של טבלה שנבנתה קודם)."""
    return 'en' if any(set(r) & set(COLUMNS_EN) for r in rows) else 'he'


def render_markdown(rows, lang=None):
    cols = columns(lang or _row_lang(rows))
    out = ['| %s |' % ' | '.join(cols), '|%s' % ('---|' * len(cols))]
    for r in rows:
        out.append('| %s |' % ' | '.join(str(r.get(c, '')).replace('|', '/') for c in cols))
    return '\n'.join(out)


def check_review_table(rows, decisions=(), lang=None):
    """הפרות: עמודה או תווית של שרשרת אישורים; קו אדום שנחצה ומתויג "מהפלייבוק"; נושא ציות בטבלה.
    בטבלה באנגלית: אותן הפרות בנוסח האנגלי, ותווית בשפה האחרת (other_language_label) היא הפרה."""
    lang = _lang(lang or _row_lang(rows))
    t = TXT[lang]
    cols = t['cols']
    v = []
    for r in rows:
        if set(r) - set(cols):
            v.append('extra_column:%s' % ','.join(sorted(set(r) - set(cols))))
        txt = ' '.join(str(x) for x in r.values())
        if BANNED_RE.search(txt) or (lang == 'en' and BANNED_EN_RE.search(txt)):
            v.append('approval_chain_wording')
        if ENGLISH_KIND.search(txt):
            v.append('english_label')
        if lang == 'en' and any(x in str(r.get(cols[2], '')) for x in ('מהפלייבוק', 'מהמדיניות', 'מטיוטת', 'הכרעתך',
                                                                        'ויתורים')):
            v.append('other_language_label')
    by_id = {d.get('id'): d for d in decisions}
    for r, d in zip(rows, table_decisions(decisions)):
        if d.get('crosses_red_line') and r.get(cols[2]) in PLAYBOOK_LABELS | PROPOSED_LABELS:
            v.append('red_line_labeled_from_playbook')
    if any(d.get('situation') == 8 for d in by_id.values()) and any(
            r.get(cols[0]) in {d.get('id') for d in by_id.values() if d.get('situation') == 8} for r in rows):
        v.append('compliance_in_table')
    return sorted(set(v))
