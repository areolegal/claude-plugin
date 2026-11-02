# -*- coding: utf-8 -*-
"""מידתיות, מיקוד בסבב 1 מול טופס סטנדרטי של צד דומיננטי, וויתורים מכוונים שמועברים למעריך הסיכונים
(מימוש ייחוס, הערות הנושא ונותן 4.8, שינויים 70, 71 ו-72;
4.9, שינויים 82, 83 ו-89).

עקרונות:
- מבחינת הצד שכנגד, סעיף חדש הוא דרישה. לכן ספירת המידתיות סופרת את R1 עד R3 וגם את N1, ושני המונים
  מוצגים בנפרד. נושא חובה אינו הופך לוויתור בגלל הספירה, אבל הוא נספר. כותרת פרק או מבנה (structural)
  אינה בקשה, ואינה נספרת (4.9, שינוי 89).
- התרעה בעסקה קטנה מחייבת שאלה אחת (מצב 4) עם שלוש חלופות, ובחלופה המומלצת שלושה ויתורים קונקרטיים.
  "תגובה מלאה" אינה נקבעת בלי תשובה מפורשת. הוויתורים המוצעים: הנמוכים בחשיבות לנו, ובתוכם קודם אלה שהצד
  שכנגד צפוי להיאבק עליהם יותר (expected_friction). פריט שהפלייבוק או המשתמש סימנו never_concede אינו מוצע.
- מול טופס סטנדרטי של צד דומיננטי: אין מסלול "מכתב צד". סבב 1 מבקש רק את מה שהכי חשוב ללקוחה (הגנה על מידע
  של לקוחות, קווים אדומים קריטיים, נושאי חובה ופריטי העדיפות שלה). דין, פורום ושפה אינם נדרשים אלא אם הפלייבוק
  מסמן אותם אדום והמשתמש ענה במפורש שהם נדרשים. לעולם לא מוותרים על פריט עדיפות בזמן שמבקשים פריט בעל ערך נמוך.
- נוסח ריפוי (4.9, שינוי 82): כשמקבלים כמות שהוא נוסח שהפלייבוק מסמן אדום, ולכלל יש בפלייבוק נוסח ריפוי
  (cure_wording) שאינו מחליף את הבחירה שלהם, הריפוי נכנס לבקשות כפריט חובה. ויתור על אדום אפשרי רק כשאין לו נוסח
  ריפוי, ורק בהכרעה מפורשת של המשתמש ("נדרשת הכרעתך", מצב 2). בחירה בגיליון החתום שיש לה נוסח אינה ויתור. התוכן
  של נוסח הריפוי בא תמיד מהפלייבוק, ולעולם לא מהרכיב.
- נושאים מסחריים מחייבים, גם כשהפלייבוק שותק (S1e-R3): סיום בלי עילה, תקופה שאינה תואמת להסכם המסחרי או לשווי,
  החזר תשלומים, שינוי שליטה, ותקרה מול ביטוח (commercial_topic). נושא כזה אינו בין הוויתורים המוצעים, נכנס לבדיקת
  החשיבות גם בתגובה ממוקדת (decisions_required), וויתור עליו דורש שאלה נפרדת ותשובה מפורשת.
- אין שרשרת אישורים (החלטת מוצר 1, 14.10.2026). ויתור מכוון נרשם עם הכרעת המשתמש (user_decision), ועובר למעריך
  הסיכונים כסיכון שהתקבל. אין "מאשר נדרש" ואין מצב "ממתין לאישור".

Python 3, ספרייה סטנדרטית בלבד.
"""

REJECTION_CODES = ('R1', 'R2', 'R3')
# meta.deal_context.proportionality.user_choice: התשובה לשאלת המידתיות (מצב 4). אוצר מילים אחד, גם ב-n8-state-schema.md
USER_CHOICES = ('send_as_is', 'concede_three', 'focused', 'full_response', 'unanswered')
ADDITION_CODE = 'N1'
IMPORTANCE_RANK = {'critical': 0, 'CRITICAL': 0, 'high': 1, 'HIGH': 1, 'medium': 2, 'MEDIUM': 2, 'low': 3, 'LOW': 3}
FRICTION_RANK = {'high': 0, 'medium': 1, 'low': 2}
LAW_FORUM_LANGUAGE = ('governing_law', 'forum', 'language')
# הנכס הקריטי של החברה בעסקה (מתוך business_interest_brief: רציפות אספקה, זמינות המושכר, מידע של לקוחות, קניין רוחני):
# critical_asset. client_data הוא שם ישן ומקרה פרטי שלו
PRIORITY_KINDS = ('critical_asset', 'client_data')
# טקסט קבוע בשתי השפות (דרישת מוצר 28.10.2026): שורת הסיכום, האפשרויות ושורת ההחלטה מוצגות בשיחה ובסיכום הפנימי.
# lang='en' נותן אותן באנגלית; הקודים (violations, open_at) קבועים בשתי השפות.
TXT = {'he': {'summary': '%d דרישות על הנוסח שלהם, ו-%d נושאים שהוספנו (מהם %d נושאי חובה): %d בקשות בסך הכול, '
                         'מול התקשרות של %s.',
              'summary_no_value': '%d דרישות על הנוסח שלהם, ו-%d נושאים שהוספנו (מהם %d נושאי חובה): %d בקשות בסך '
                                  'הכול. שווי ההתקשרות לא נמסר.',
              'options': ['לשלוח כפי שהיא', 'לוותר מראש על שלושת הפריטים המוצעים', 'תגובה ממוקדת'],
              'cure': 'ריפוי: %s', 'row': 'מקבלים כמות שהוא את: %s. [לאשר] [להוסיף לתגובה]',
              'yellow_kept': 'הצהוב נשמר לסבב הבא'},
       'en': {'summary': '%d requests on their wording, and %d topics we added (%d of them mandatory): %d requests in '
                         'total, against an engagement of %s.',
              'summary_no_value': '%d requests on their wording, and %d topics we added (%d of them mandatory): %d '
                                  'requests in total. The value of the engagement was not provided.',
              'options': ['Send as is', 'Concede the three proposed items up front', 'A focused response'],
              'cure': 'Cure: %s', 'row': 'Accepting as is: %s. [Approve] [Add to the response]',
              'yellow_kept': 'The yellow position is kept for the next round'}}


def _t(lang):
    return TXT['en' if str(lang or '').lower()[:2] == 'en' else 'he']


# נושאים מסחריים מחייבים, גם כשהפלייבוק שותק (S1e-R3, 28.10.2026: 15.2, סיום מיידי בהודעה, הפך לוויתור בשורה ברשימה
# ולא טופל בשלושה סבבים). נושא כזה אינו ויתור מכוון בלי שאלה נפרדת למשתמש ותשובה מפורשת, ואינו מוצע בין שלושת
# הוויתורים; הוא נכנס לבדיקת החשיבות גם בתגובה ממוקדת. commercial_topic בהכרעה או בוויתור גובר על הזיהוי במילים
COMMERCIAL_TOPICS = {
    'termination_without_cause': r'סיום (?:מיידי|בהודעה|בלי עילה|ללא עילה|מטעמי נוחות)|זכות סיום מיידית|'
                                 r'terminat\w*\s+(?:for convenience|without cause|at any time|immediately|on notice)|'
                                 r'for convenience|without cause',
    'term_mismatch': r'\bתקופ[הת] (?:ה?הסכם|ההתקשרות)|תקופה וחידוש|חידוש אוטומטי|\bterm (?:of|and renewal)\b|'
                     r'\bduration\b|automatic(?:ally)? renew',
    # החזר של תשלום ששולם מראש ביציאה מוקדמת. לא פירעון (repay, החזר קרן), שהוא ההתחייבות העיקרית
    'refund': r'החזר (?:יחסי|חלק יחסי|כספי)|החזר (?:ה)?(?:תשלומים|תשלום|דמי|תמורה)[^.]{0,40}(?:מראש|ששולמ|שולמ)|'
              r'שולמו? מראש|\brefund|prepaid|paid in advance',
    'change_of_control': r'שינוי (?:ב)?שליטה|change of control',
    'cap_vs_insurance': r'(?:ביטוח|insurance|insured)[^.]{0,80}(?:תקרה|cap|liabilit|אחריות|תשלומים|payment)|'
                        r'(?:תקרה|cap|liabilit|אחריות)[^.]{0,80}(?:ביטוח|insurance)',
}
COMMERCIAL_LABELS = {'he': {'termination_without_cause': 'סיום בלי עילה',
                            'term_mismatch': 'תקופה מול שווי העסקה או ההסכם הראשי, כשיש',
                            'refund': 'החזר תשלום ששולם מראש', 'change_of_control': 'שינוי שליטה',
                            'cap_vs_insurance': 'תקרה מול ביטוח'},
                     'en': {'termination_without_cause': 'termination without cause',
                            'term_mismatch': 'term against the deal value or the main agreement, if any',
                            'refund': 'refund of prepaid amounts',
                            'change_of_control': 'change of control', 'cap_vs_insurance': 'cap against insurance'}}


def commercial_topic(item):
    """הנושא המסחרי המחייב של הכרעה, ויתור או טקסט (COMMERCIAL_TOPICS), או None."""
    import re
    if isinstance(item, dict):
        if item.get('commercial_topic') in COMMERCIAL_TOPICS:
            return item['commercial_topic']
        text = ' '.join(str(item.get(k) or '') for k in ('topic', 'summary', 'reason', 'title', 'clause_label'))
    else:
        text = str(item or '')
    return next((k for k, rx in COMMERCIAL_TOPICS.items() if re.search(rx, text, re.I)), None)


def commercial_concession_violations(concessions):
    """ויתור מכוון על נושא מסחרי מחייב בלי תשובה מפורשת לשאלה נפרדת: [{'code', 'topic', 'clause_ref'}]."""
    return [{'code': 'commercial_topic_conceded_without_separate_question', 'topic': w.get('topic'),
             'clause_ref': w.get('clause_ref'), 'commercial_topic': commercial_topic(w)}
            for w in concessions or () if isinstance(w, dict) and commercial_topic(w) and not _explicit(w)]


def _for_call(d):
    """פריט שהוכרע לשיחה (coverage: for_call, או held_for: talking_point): הנוסח שלהם לא שונה, ולכן אין
    בו בקשה בכתב."""
    return d.get('coverage') == 'for_call' or d.get('held_for') == 'talking_point'


def _counted(d):
    """כותרת פרק (structural), שינוי עקבי (conforming), שנובע משינוי אחר, ופריט לשיחה אינם בקשה."""
    return not d.get('structural') and not d.get('conforming') and not _for_call(d)


def ask_key(d):
    """יחידת הספירה היא בקשה, ולא פסקה: כל ההכרעות של אשכול אחד (cluster_id, אותו כלל באותו סעיף, גם על פני כמה
    פסקאות) הן בקשה אחת; הכרעה בלי אשכול היא בקשה משלה."""
    return ('c', d['cluster_id']) if d.get('cluster_id') else ('d', d.get('id'))


def _unique_asks(decisions, codes):
    out, seen = [], set()
    for d in decisions:
        if d.get('decision_code') in codes and _counted(d) and ask_key(d) not in seen:
            seen.add(ask_key(d))
            out.append(d)
    return out


def count_asks(decisions):
    """R1 עד R3 ו-N1, לפי בקשה (ask_key). כותרת פרק ושינוי עקבי אינם נספרים."""
    rej = _unique_asks(decisions, REJECTION_CODES)
    # N1 באותו אשכול של דחייה הוא חלק מאותה בקשה, ואינו נספר שוב
    rej_keys = {ask_key(d) for d in rej}
    add = [d for d in _unique_asks(decisions, (ADDITION_CODE,)) if ask_key(d) not in rej_keys]
    return {'rejections': len(rej), 'additions': len(add),
            'mandatory_additions': sum(1 for d in add if d.get('mandatory')),
            'asks': len(rej) + len(add)}


# שווי שלא נמסר: השורה נכתבת בלי השווי, ולא עם מציין מקום (S1e-R3: "<שווי>" הודפס כמו שהוא)
NO_VALUE = ('', '<שווי>', '<value>', 'לא ידוע', 'unknown')


def summary_line(counts, value_text, lang='he'):
    args = (counts['rejections'], counts['additions'], counts['mandatory_additions'], counts['asks'])
    if str(value_text or '').strip() in NO_VALUE:
        return _t(lang)['summary_no_value'] % args
    return _t(lang)['summary'] % (args + (value_text,))


def _concession_candidates(decisions, context=None):
    """ויתורים אפשריים: לא נושא חובה, לא שובר עסקה, לא פריט עדיפות של הלקוחה, לא כותרת, ולא פריט never_concede
    (מהפלייבוק או מהמשתמש, למשל בקרת עלות כשהתמורה משתנה והנספח חסר). הנמוכים בחשיבות לנו קודם, ובתוכם קודם אלה
    שהצד שכנגד צפוי להיאבק עליהם יותר. context נשמר לממשק."""
    c = [d for d in _unique_asks(decisions, REJECTION_CODES + (ADDITION_CODE,))
         if not d.get('mandatory') and d.get('tier') != 'deal_breaker'
         and not d.get('client_priority') and not d.get('never_concede') and not commercial_topic(d)
         and (d.get('user_decision') or {}).get('answer_kind') != 'explicit']   # בקשה שהלקוח הכריע בה במפורש
    # סעיף שהנוסח המקורי שלהם בו כבר בצהוב הוא ויתור מתוכנן, ולכן הוא מוצע
    # ראשון: הנוסח שלהם ממילא מקובל עלינו, והוויתור הוא החזרה אליו
    return sorted(c, key=lambda d: (0 if d.get('their_track') == 'yellow' else 1,
                                    -IMPORTANCE_RANK.get(d.get('importance', 'medium'), 2),
                                    FRICTION_RANK.get(d.get('expected_friction', 'medium'), 1), d.get('id', '')))


def assess(decisions, fight_list_size, value_band='לא ידוע', value_text=None, user_choice=None,
           answer_kind=None, context=None, lang='he'):
    """ההתרעה סופרת את כל הבקשות (R1 עד R3 ו-N1, בלי כותרות) מול רשימת המאבק.
    מחזיר dict: counts, summary_line, alert, question_required, proposed_concessions, violations."""
    counts = count_asks(decisions)
    alert = counts['asks'] > fight_list_size
    res = {'counts': counts, 'summary_line': summary_line(counts, value_text, lang), 'alert': alert,
           'question_required': False, 'proposed_concessions': [], 'violations': []}
    if alert and user_choice is None:
        res['question_required'] = True  # "נדרשת הכרעתך", מצב 4
        res['proposed_concessions'] = [d.get('id') for d in _concession_candidates(decisions, context)[:3]]
        res['options'] = list(_t(lang)['options'])
    if user_choice == 'full_response' and answer_kind != 'explicit':
        res['violations'].append('full_response_without_explicit_answer')
    if alert and user_choice == 'unanswered' and value_band in ('קטנה', 'small'):
        # בעסקה קטנה התרעה בלי שאלה היא כשל: השאלה נשאלת חובה (ב-C1ב היא לא נשאלה, ו"לא הוסר פריט")
        res['violations'].append('small_deal_alert_without_question')
    return res


def _explicit(item):
    return (item.get('user_decision') or {}).get('answer_kind') == 'explicit'


def _cure_item(it, lang='he'):
    return {'id': '%s-cure' % it.get('id'), 'topic': _t(lang)['cure'] % it.get('topic', it.get('id')), 'kind': 'cure',
            'cure_of': it.get('id'), 'cure_wording': it['cure_wording'], 'mandatory': True,
            'importance': it.get('importance', 'high')}


def focus_round1(items, client_confirmed_law=False, max_asks=None, lang='he'):
    """מיקוד סבב 1 מול טופס סטנדרטי של צד דומיננטי. items: רשימת dict עם id, topic, kind
    (critical_asset (או client_data, השם הישן) / red_line / governing_law / forum / language / other),
    importance, playbook_red (bool), client_priority (bool), mandatory (bool), cure_wording (נוסח ריפוי מהעמודה
    האדומה, כשיש), chosen_option_wording (נוסח של בחירה בגיליון החתום, כשיש), user_decision ({answer_kind, ...}).

    מחזיר dict: asks (מבקשים בסבב 1, כולל פריטי ריפוי), accepted_as_is (מקבלים כמות שהוא, בשורת החלטה אחת),
    decisions_required (אדום בלי ריפוי שהקבלה שלו היא "נדרשת הכרעתך", מצב 4), for_call (אדום שאינו קריטי, או עמדה בחשיבות
    קריטית, בלי ריפוי,
    שלא נכנס לרשימת המאבק: אינו ויתור ואינו בקשה בנוסח, אלא נקודה פתוחה לשיחה, עד הכרעה מפורשת), decision_row, alert,
    violations.
    סדר הקדימות בתגובה ממוקדת, כשנמסר max_asks (רשימת המאבק): נושאי חובה, הנכס הקריטי, אדום קריטי ופריטי עדיפות;
    אחריהם ריפוי ובחירה בגיליון; ואחריהם שאר האדום, ועמדות בחשיבות קריטית שהנוסח שלהם סותר, לפי החשיבות,
    עד שהרשימה מתמלאת. בלי max_asks כולם בבקשות. אף אחד מהם אינו "מקבלים כמות שהוא" בלי הכרעה מפורשת."""
    asks, accepted, needs, other_red = [], [], [], []
    for it in items:
        kind = it.get('kind', 'other')
        critical_red = it.get('playbook_red') and IMPORTANCE_RANK.get(it.get('importance', 'medium'), 2) == 0
        if it.get('chosen_option_wording'):
            asks.append(it)  # בחירה בגיליון שיש לה נוסח נכנסת לנוסח, ואינה ויתור (שב3-8)
        elif kind in LAW_FORUM_LANGUAGE:
            if it.get('playbook_red') and (client_confirmed_law or _explicit(it) and it['user_decision'].get('ask')):
                asks.append(it)
            else:
                accepted.append(it)
                if it.get('playbook_red') and it.get('cure_wording'):
                    asks.append(_cure_item(it, lang))
                elif it.get('playbook_red') and not _explicit(it):
                    needs.append(it)
        elif kind in PRIORITY_KINDS or critical_red or it.get('client_priority') or it.get('mandatory'):
            asks.append(it)
        elif commercial_topic(it) and not _explicit(it):
            # נושא מסחרי מחייב (סיום בלי עילה, תקופה, החזר, שינוי שליטה, תקרה מול ביטוח) נכנס לבדיקת החשיבות גם
            # בתגובה ממוקדת: אינו "מקבלים כמות שהוא" בשורה ברשימה, אלא שאלה נפרדת (S1e-R3, 15.2)
            needs.append(it)
        elif it.get('playbook_red') and it.get('cure_wording'):
            accepted.append(it)
            asks.append(_cure_item(it, lang))
        elif (it.get('playbook_red') or _heavy(it)) and not _explicit(it):
            # תשובה כללית אינה חוצה קו אדום, ואינה מוותרת על קו אדום (חשיבות קריטית): בלי נוסח ריפוי, הפריט אינו
            # ויתור (בקשה, או נקודה לשיחה כשהוא מעבר לרשימת המאבק)
            other_red.append(it)
        else:
            accepted.append(it)
    other_red.sort(key=lambda i: IMPORTANCE_RANK.get(i.get('importance', 'medium'), 2))
    room = len(other_red) if not max_asks else max(0, max_asks - len([a for a in asks if not a.get('structural')]))
    asks.extend(other_red[:room])
    for_call = other_red[room:]
    row = ''
    if accepted:
        row = _t(lang)['row'] % ', '.join(i.get('topic', i.get('id')) for i in accepted)
    counted = [a for a in asks if not a.get('structural')]
    return {'asks': asks, 'accepted_as_is': accepted, 'decisions_required': needs, 'for_call': for_call,
            'decision_row': row,
            'alert': bool(max_asks) and len(counted) > max_asks,
            'violations': check_round1_focus(asks, accepted, client_confirmed_law)}


def _heavy(it):
    """קו אדום שהנוסח שלהם סותר: עמדה בחשיבות קריטית, walk_away או red_line. עמדה בחשיבות גבוהה אינה כזו: מול נוסח
    אחיד היא יכולה להיות ויתור מכוון בתגובה ממוקדת."""
    return IMPORTANCE_RANK.get(it.get('importance', 'medium'), 2) == 0 or bool(it.get('walk_away')) \
        or it.get('red_line') is True


def check_round1_focus(asks, accepted, client_confirmed_law=False, route=None, concessions=()):
    """בדיקה של תגובה שכבר נבנתה (גם כשהיא לא נבנתה דרך focus_round1)."""
    v = []
    if route == 'side_letter':
        v.append('side_letter_route')  # אין מסלול מכתב צד
    low_asked = [a for a in asks if not a.get('client_priority') and a.get('kind', 'other') == 'other'
                 and IMPORTANCE_RANK.get(a.get('importance', 'medium'), 2) >= 2 and not a.get('mandatory')]
    prio_waived = [a for a in accepted if a.get('client_priority') or a.get('kind') in PRIORITY_KINDS]
    if prio_waived and low_asked:
        v.append('priority_waived_while_low_value_asked')
    for a in asks:
        if a.get('kind') in LAW_FORUM_LANGUAGE and not (a.get('playbook_red') and (client_confirmed_law or _explicit(a))):
            v.append('law_forum_language_without_red_and_confirmation')
            break
    cured = {a.get('cure_of') for a in asks if a.get('kind') == 'cure'}
    for a in list(accepted) + list(concessions):
        if a.get('playbook_red') and a.get('cure_wording') and a.get('id') not in cured:
            v.append('red_line_waived_although_cure_exists')
            break
    for a in list(accepted) + list(concessions):
        if a.get('chosen_option_wording'):
            v.append('sheet_choice_with_wording_treated_as_waiver')
            break
    for a in list(concessions):
        if a.get('playbook_red') and not a.get('cure_wording') and not _explicit(a):
            v.append('red_line_crossed_without_user_decision')
            break
    for a in list(accepted) + list(concessions):
        if a.get('kind', 'other') not in LAW_FORUM_LANGUAGE and _heavy(a) and not a.get('cure_wording') \
                and not _explicit(a):
            v.append('critical_position_conceded_without_user_decision')
            break
    if commercial_concession_violations(list(accepted) + list(concessions)):
        v.append('commercial_topic_conceded_without_separate_question')
    return v


def round1_opening(green_feasible, yellow_is_last_fallback, intermediate=None, lang='he'):
    """עמדת הפתיחה בסבב 1. כשבדיקת ההיתכנות פוסלת את הירוק והצהוב הוא הנסיגה האחרונה, פותחים בנקודת ביניים
    (מהפלייבוק או מהמשתמש) ושומרים את הצהוב לסבב הבא. הצעת הצהוב עצמו בסבב 1 היא "נדרשת
    הכרעתך" (מצב 4), ובלי תשובה מפורשת היא אינה מוחלת."""
    if green_feasible:
        return {'open_at': 'green', 'question_required': False}
    if yellow_is_last_fallback:
        return {'open_at': 'intermediate', 'intermediate': intermediate, 'question_required': intermediate is None,
                'note': _t(lang)['yellow_kept']}
    return {'open_at': 'yellow', 'question_required': False}


def waiver_handoff(state):
    """ויתורים מכוונים שנרשמו, למעריך הסיכונים: כל אחד מדווח כסיכון שהתקבל. ויתור שנפתח מחדש (reopened_in_round)
    אינו ויתור, ואינו מועבר. רק ויתור עם נימוק ועם הכרעת משתמש (user_decision.answer_kind: explicit או delegated) נרשם כמכוון. אין שדה
    אישור ואין מאשר. clause_ref הוא מזהה הסעיף בקובץ המצב (clause_id), ולא מזהה כלל."""
    out = []
    for w in (state or {}).get('deliberate_concessions', []):
        ud = w.get('user_decision') or ({'answer_kind': w['answer_kind']} if w.get('answer_kind') else {})
        if not w.get('reason') or ud.get('answer_kind') not in ('explicit', 'delegated') or w.get('reopened_in_round'):
            continue
        out.append({'topic': w.get('topic'), 'clause_ref': w.get('clause_ref'), 'rule_ids': w.get('rule_ids', []),
                    'reason': w['reason'],
                    'user_decision': {'answer_kind': ud['answer_kind'], 'answer': ud.get('answer'),
                                      'recorded_at': ud.get('recorded_at') or w.get('recorded_at')},
                    'crosses_red_line': bool(w.get('crosses_red_line')),
                    'gap_codes': w.get('gap_codes', []),
                    'recorded_at': w.get('recorded_at'), 'report_as': 'accepted_risk'})
    return out
