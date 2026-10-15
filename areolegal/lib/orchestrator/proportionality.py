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
  של נוסח הריפוי בא תמיד מהפלייבוק, ולעולם לא מהרכיב (החלטה 22).
- אין שרשרת אישורים (החלטת מוצר 1, 14.10.2026). ויתור מכוון נרשם עם הכרעת המשתמש (user_decision), ועובר למעריך
  הסיכונים כסיכון שהתקבל. אין "מאשר נדרש" ואין מצב "ממתין לאישור".

Python 3, ספרייה סטנדרטית בלבד.
"""

REJECTION_CODES = ('R1', 'R2', 'R3')
ADDITION_CODE = 'N1'
IMPORTANCE_RANK = {'critical': 0, 'CRITICAL': 0, 'high': 1, 'HIGH': 1, 'medium': 2, 'MEDIUM': 2, 'low': 3, 'LOW': 3}
FRICTION_RANK = {'high': 0, 'medium': 1, 'low': 2}
LAW_FORUM_LANGUAGE = ('governing_law', 'forum', 'language')


def _counted(d):
    return not d.get('structural')


def count_asks(decisions):
    """R1 עד R3 ו-N1. כותרת פרק (structural: true) אינה נספרת."""
    rej = [d for d in decisions if d.get('decision_code') in REJECTION_CODES and _counted(d)]
    add = [d for d in decisions if d.get('decision_code') == ADDITION_CODE and _counted(d)]
    return {'rejections': len(rej), 'additions': len(add),
            'mandatory_additions': sum(1 for d in add if d.get('mandatory')),
            'asks': len(rej) + len(add)}


def summary_line(counts, value_text):
    return ('%d דרישות על הנוסח שלהם, ו-%d נושאים שהוספנו (מהם %d נושאי חובה): %d בקשות בסך הכול, '
            'מול התקשרות של %s.' % (counts['rejections'], counts['additions'], counts['mandatory_additions'],
                                     counts['asks'], value_text))


def _concession_candidates(decisions, context=None):
    """ויתורים אפשריים: לא נושא חובה, לא שובר עסקה, לא פריט עדיפות של הלקוחה, לא כותרת, ולא פריט never_concede
    (מהפלייבוק או מהמשתמש, למשל בקרת עלות כשהתמורה משתנה והנספח חסר). הנמוכים בחשיבות לנו קודם, ובתוכם קודם אלה
    שהצד שכנגד צפוי להיאבק עליהם יותר. context נשמר לממשק."""
    c = [d for d in decisions if d.get('decision_code') in REJECTION_CODES + (ADDITION_CODE,)
         and _counted(d) and not d.get('mandatory') and d.get('tier') != 'deal_breaker'
         and not d.get('client_priority') and not d.get('never_concede')]
    return sorted(c, key=lambda d: (-IMPORTANCE_RANK.get(d.get('importance', 'medium'), 2),
                                    FRICTION_RANK.get(d.get('expected_friction', 'medium'), 1), d.get('id', '')))


def assess(decisions, fight_list_size, value_band='לא ידוע', value_text='<שווי>', user_choice=None,
           answer_kind=None, context=None):
    """ההתרעה סופרת את כל הבקשות (R1 עד R3 ו-N1, בלי כותרות) מול רשימת המאבק.
    מחזיר dict: counts, summary_line, alert, question_required, proposed_concessions, violations."""
    counts = count_asks(decisions)
    alert = counts['asks'] > fight_list_size
    res = {'counts': counts, 'summary_line': summary_line(counts, value_text), 'alert': alert,
           'question_required': False, 'proposed_concessions': [], 'violations': []}
    if alert and user_choice is None:
        res['question_required'] = True  # "נדרשת הכרעתך", מצב 4
        res['proposed_concessions'] = [d.get('id') for d in _concession_candidates(decisions, context)[:3]]
        res['options'] = ['לשלוח כפי שהיא', 'לוותר מראש על שלושת הפריטים המוצעים', 'תגובה ממוקדת']
    if user_choice == 'full_response' and answer_kind != 'explicit':
        res['violations'].append('full_response_without_explicit_answer')
    if alert and user_choice == 'unanswered' and value_band in ('קטנה', 'small'):
        # בעסקה קטנה התרעה בלי שאלה היא כשל: השאלה נשאלת חובה (ב-C1ב היא לא נשאלה, ו"לא הוסר פריט")
        res['violations'].append('small_deal_alert_without_question')
    return res


def _explicit(item):
    return (item.get('user_decision') or {}).get('answer_kind') == 'explicit'


def _cure_item(it):
    return {'id': '%s-cure' % it.get('id'), 'topic': 'ריפוי: %s' % it.get('topic', it.get('id')), 'kind': 'cure',
            'cure_of': it.get('id'), 'cure_wording': it['cure_wording'], 'mandatory': True,
            'importance': it.get('importance', 'high')}


def focus_round1(items, client_confirmed_law=False, max_asks=None):
    """מיקוד סבב 1 מול טופס סטנדרטי של צד דומיננטי. items: רשימת dict עם id, topic, kind
    (client_data / red_line / governing_law / forum / language / other),
    importance, playbook_red (bool), client_priority (bool), mandatory (bool), cure_wording (נוסח ריפוי מהעמודה
    האדומה, כשיש), chosen_option_wording (נוסח של בחירה בגיליון החתום, כשיש), user_decision ({answer_kind, ...}).

    מחזיר dict: asks (מבקשים בסבב 1, כולל פריטי ריפוי), accepted_as_is (מקבלים כמות שהוא, בשורת החלטה אחת),
    decisions_required (אדום בלי ריפוי שהקבלה שלו היא "נדרשת הכרעתך", מצב 4), decision_row, alert, violations."""
    asks, accepted, needs = [], [], []
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
                    asks.append(_cure_item(it))
                elif it.get('playbook_red') and not _explicit(it):
                    needs.append(it)
        elif kind == 'client_data' or critical_red or it.get('client_priority') or it.get('mandatory'):
            asks.append(it)
        elif it.get('playbook_red') and it.get('cure_wording'):
            accepted.append(it)
            asks.append(_cure_item(it))
        elif it.get('playbook_red') and not _explicit(it):
            asks.append(it)  # תשובה כללית אינה חוצה קו אדום; בלי נוסח ריפוי, האדום נשאר בבקשות
        else:
            accepted.append(it)
    row = ''
    if accepted:
        row = 'מקבלים כמות שהוא את: %s. [לאשר] [להוסיף לתגובה]' % ', '.join(i.get('topic', i.get('id')) for i in accepted)
    counted = [a for a in asks if not a.get('structural')]
    return {'asks': asks, 'accepted_as_is': accepted, 'decisions_required': needs, 'decision_row': row,
            'alert': bool(max_asks) and len(counted) > max_asks,
            'violations': check_round1_focus(asks, accepted, client_confirmed_law)}


def check_round1_focus(asks, accepted, client_confirmed_law=False, route=None, concessions=()):
    """בדיקה של תגובה שכבר נבנתה (גם כשהיא לא נבנתה דרך focus_round1)."""
    v = []
    if route == 'side_letter':
        v.append('side_letter_route')  # אין מסלול מכתב צד
    low_asked = [a for a in asks if not a.get('client_priority') and a.get('kind', 'other') == 'other'
                 and IMPORTANCE_RANK.get(a.get('importance', 'medium'), 2) >= 2 and not a.get('mandatory')]
    prio_waived = [a for a in accepted if a.get('client_priority') or a.get('kind') == 'client_data']
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
    return v


def round1_opening(green_feasible, yellow_is_last_fallback, intermediate=None):
    """עמדת הפתיחה בסבב 1. כשבדיקת ההיתכנות פוסלת את הירוק והצהוב הוא הנסיגה האחרונה, פותחים בנקודת ביניים
    (מהפלייבוק או מהמשתמש) ושומרים את הצהוב לסבב הבא. הצעת הצהוב עצמו בסבב 1 היא "נדרשת
    הכרעתך" (מצב 4), ובלי תשובה מפורשת היא אינה מוחלת."""
    if green_feasible:
        return {'open_at': 'green', 'question_required': False}
    if yellow_is_last_fallback:
        return {'open_at': 'intermediate', 'intermediate': intermediate, 'question_required': intermediate is None,
                'note': 'הצהוב נשמר לסבב הבא'}
    return {'open_at': 'yellow', 'question_required': False}


def waiver_handoff(state):
    """ויתורים מכוונים שנרשמו, למעריך הסיכונים: כל אחד מדווח כסיכון שהתקבל, ולא כתיקון לפני המשלוח.
    רק ויתור עם נימוק ועם הכרעת משתמש (user_decision.answer_kind: explicit או delegated) נרשם כמכוון. אין שדה
    אישור ואין מאשר. clause_ref הוא מזהה הסעיף בקובץ המצב (clause_id), ולא מזהה כלל."""
    out = []
    for w in (state or {}).get('deliberate_concessions', []):
        ud = w.get('user_decision') or ({'answer_kind': w['answer_kind']} if w.get('answer_kind') else {})
        if not w.get('reason') or ud.get('answer_kind') not in ('explicit', 'delegated'):
            continue
        out.append({'topic': w.get('topic'), 'clause_ref': w.get('clause_ref'), 'rule_ids': w.get('rule_ids', []),
                    'reason': w['reason'],
                    'user_decision': {'answer_kind': ud['answer_kind'], 'answer': ud.get('answer'),
                                      'recorded_at': ud.get('recorded_at') or w.get('recorded_at')},
                    'crosses_red_line': bool(w.get('crosses_red_line')),
                    'from_pre_send_fix': w.get('from_pre_send_fix'), 'gap_codes': w.get('gap_codes', []),
                    'recorded_at': w.get('recorded_at'), 'report_as': 'accepted_risk'})
    return out
