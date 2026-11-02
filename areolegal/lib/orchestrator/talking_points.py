# -*- coding: utf-8 -*-
"""נקודות לשיחה בסיכום הפנימי (מימוש ייחוס, הערות הנושא ונותן 4.9, שינוי 85).

נקודות לשיחה הן מה שעורכת הדין אומרת כשהצד שכנגד פותח נושא. הן פנימיות, ואינן נכנסות לבועה. המודול כללי לכל
סוג הסכם: התוכן של כל נקודה (הנסיגה המוכנה, מה מבקשים אם נושא נפתח) בא מהפלייבוק או מתשובת המשתמש, ולעולם לא
מהרכיב. מקורות:
(1) נקודות חיכוך צפויות (expected_friction: high), עם הנסיגה שהפלייבוק מכין (prepared_fallback);
(2) כלל שההצעה בו כבר בנסיגה האחרונה (at_last_fallback): אין לאן לרדת בלי "נדרשת הכרעתך";
(3) ויתורים מכוונים, עם מה שמבקשים אם הנושא נפתח (if_raised);
(4) פריטים שנשארו בלי הכרעה לשיחה (for_call);
(5) הסלמה (escalation): סעיף STUCK לפי state_builder.stuck_reason (הצעה שלנו, או המדרגה שאחריה, נדחתה בשני סבבים
    בלי תזוזה שלהם, או עמדה סופית שלהם), ומוצעת שיחה במקום סבב נוסף. רשימת המאבק לבדה אינה הסלמה.
אין סימון "נבדק" של עורך דין בנקודות לשיחה (כלל יסוד 6): עורך דין מאשר את הפלייבוק בלבד, והנסיגה שבפלייבוק מוצגת.

שפה (דרישת מוצר 28.10.2026): הנקודות הן חלק מהסיכום הפנימי, ולכן בשפת התוצר. lang='en' נותן את המסגרת הקבועה
באנגלית; התוכן מהפלייבוק או מהמשתמש נשאר כמו שהוא.

    from orchestrator.talking_points import build_talking_points, merge_points

כל נקודה של הכלי נושאת id ("auto:<kind>:<מזהה הכרעה>") ו-source: auto, ו-merge_points ממזג אותן לקובץ המצב לפי id
בלי לגעת בנוסח של נקודות שנכתבו ביד. נקודה מסבב קודם מתעדכנת לפי מצב הסעיף (S1e-R3: "הצד שכנגד יחזור עם הצעה" נשארה
אחרי שההצעה הגיעה): כשהסעיף הוסכם, או שהצד השני שינה אותו או ביקש בו משהו חדש בסבב הזה, היא מקבלת status: superseded
ו-superseded: {round, why}, ואינה מוצגת. נקודה שנבנתה בסבב מקבלת round.
"""

TXT = {
    'he': {'friction': '%s: צפוי ויכוח.%s', 'fallback': ' נסיגה מוכנה: %s.',
           'no_fallback': ' אין נסיגה מוכנה: לברר מה חשוב להם לפני שמציעים.',
           'last': '%s: ההצעה כבר בנסיגה האחרונה. ירידה נוספת היא "נדרשת הכרעתך" (מצב 2).',
           'call': '%s: נשאר לשיחה, בלי נוסח מכריע.', 'conc': '%s: ויתרנו בסבב הזה.%s', 'raised': ' אם הנושא נפתח: %s.',
           'legal': ' טעון בדיקה משפטית: אין להציע נסיגה עד שעורך דין יסמן את הנושא "נבדק".',
           'escalation': '%s: תקוע (STUCK). מוצעת שיחה לפני סבב נוסף, עם נימוק חדש ולא חזרה על הקודם.',
           'closed': 'הסעיף הוסכם בסבב %s', 'changed': 'הצד השני שינה את הסעיף בסבב %s (סטטוס: %s)',
           'request': 'בקשה חדשה של הצד השני בסעיף בסבב %s', 'waived': 'ויתור ביודעין בהכרעה מפורשת (%s)'},
    'en': {'friction': '%s: expect pushback.%s', 'fallback': ' Prepared fallback: %s.',
           'no_fallback': ' No prepared fallback: find out what matters to them before offering anything.',
           'last': '%s: our offer is already at the last fallback. Going lower needs your decision (situation 2).',
           'call': '%s: left for the call, with no deciding wording.', 'conc': '%s: we conceded this round.%s',
           'raised': ' If the topic comes up: %s.',
           'legal': ' Requires legal review: offer no fallback until a lawyer marks the topic "Reviewed".',
           'escalation': '%s: stuck (STUCK). Propose a call before another round, with new reasoning '
                         'rather than repeating the old.',
           'closed': 'the clause was agreed in round %s', 'changed': 'the other side changed the clause in round %s '
                                                                   '(status: %s)',
           'request': 'a new request by the other side on the clause in round %s',
           'waived': 'knowingly waived by an express decision (%s)'},
}


def legal_review_open(d, reviewed=()):
    """תמיד False. עורך דין מאשר את הפלייבוק בלבד (כלל יסוד 6): נושא שהפלייבוק מסמן אינו מעכב נסיגה מוכנה, ואין
    סימון "נבדק" בנקודות לשיחה. נשאר כפונקציה כדי שהקריאה אליה תמשיך לעבוד."""
    return False


def merge_points(existing, generated, clauses=None, round_number=None, lang='he'):
    """מיזוג לפי מזהה (הרצה S1c, 28.10.2026: talking-points דרס נקודות שנכתבו ביד בקובץ המצב). נקודה שאינה של
    הכלי (בלי source: auto) לעולם אינה נמחקת, והנוסח שלה אינו משתנה. נקודה של הכלי שנסגרה בשיחה (closed_in_call), או
    שסומנה manual: true כי עורך הדין ערך אותה, נשארת כמו שהיא. שאר הנקודות של הכלי מוחלפות במה שנבנה עכשיו, לפי id.
    הסדר: הנקודות שנכתבו ביד, ואחריהן של הכלי.
    clauses ו-round_number (הסבב הנוכחי): נקודה מסבב קודם על סעיף שהוסכם, או שהצד השני שינה או ביקש בו משהו חדש בסבב
    הזה, מסומנת superseded עם הסיבה (S1e-R3), ונקודה שנבנתה עכשיו מקבלת round."""
    kept = [p for p in existing or () if not isinstance(p, dict) or p.get('source') != 'auto'
            or p.get('status') == 'closed_in_call' or p.get('manual')]
    kept_ids = {p.get('id') for p in kept if isinstance(p, dict) and p.get('id')}
    new = [p for p in generated if p.get('id') not in kept_ids]
    if not round_number:
        return kept + new
    rnd = int(round_number)
    T = TXT['en' if str(lang or '').lower()[:2] == 'en' else 'he']
    by = {c.get('clause_id'): c for c in clauses or () if isinstance(c, dict)}
    for p in new:
        p.setdefault('round', rnd)
    # נקודה לשיחה על סעיף שהמשתמש ויתר עליו ביודעין, בהכרעה מפורשת (סבב סגירה, "לוותר ביודעין"), אינה פתוחה עוד,
    # מכל סבב שהיא (S1g-R3: 15.2 ו-28 נשארו "פתוחות" אחרי הוויתור)
    import re
    waived = {}
    for cid, c in by.items():
        ud = c.get('user_decision') or {}
        if ud.get('answer_kind') == 'explicit' and re.search(r'לוותר|ויתור ביודעין|\bwaive', str(ud.get('answer') or ''),
                                                             re.I):
            waived[cid] = ud.get('question_id') or ''
    for p in kept:
        if not isinstance(p, dict) or p.get('status') in ('closed_in_call', 'closed', 'superseded'):
            continue
        ids = list(p.get('clause_ids') or ()) + ([p['clause_id']] if p.get('clause_id') else [])
        if ids and all(i in waived for i in ids):
            p['status'] = 'superseded'
            p['superseded'] = {'round': rnd, 'why': T['waived'] % waived[ids[0]]}
    for p in kept:
        # נקודה בלי round נכתבה בסבב הזה (write מסמן את הנקודות של סבב שהסתיים, negotiation_state.carry_over)
        if not isinstance(p, dict) or p.get('status') in ('closed_in_call', 'closed', 'superseded') \
                or p.get('round') is None or int(p['round']) >= rnd:
            continue
        ids = list(p.get('clause_ids') or ()) + ([p['clause_id']] if p.get('clause_id') else [])
        if not ids and str(p.get('id') or '').startswith('auto:'):
            ids = [str(p['id']).split(':', 2)[2].split('#')[0]]
        why = None
        for cid in ids:
            c = by.get(cid) or {}
            if c.get('status') == 'CLOSED':
                why = T['closed'] % c.get('closed_in_round')
            elif rnd in (int(c.get('their_change_round') or 0),
                         int((c.get('reopened_by_counterparty') or {}).get('round') or 0)):
                why = T['changed'] % (rnd, c.get('status'))
            elif int((c.get('their_request') or {}).get('round') or 0) == rnd:
                why = T['request'] % rnd
            if why:
                break
        if why:
            p['status'] = 'superseded'
            p['superseded'] = {'round': rnd, 'why': why}
    return kept + new


def _point(kind, d_or_c, topic, text):
    ref = d_or_c.get('id') or d_or_c.get('clause_ref') or topic
    return {'id': 'auto:%s:%s' % (kind, ref), 'source': 'auto', 'topic': topic, 'kind': kind, 'text': text}


def build_talking_points(decisions, concessions=(), lang='he', reviewed=()):
    """reviewed: מזהי הכרעות שעורך דין כבר סימן "נבדק" בקובץ המצב (clauses[].legal_review)."""
    T = TXT['en' if str(lang or '').lower()[:2] == 'en' else 'he']
    pts = []
    grouped = {}
    for d in decisions:
        # נקודות מקובצות לפי נושא: כל ההכרעות של אשכול אחד (cluster_id) באותו סוג נקודה הן נקודה אחת, עם כל הסעיפים
        key = d.get('cluster_id')
        if key and key in grouped:
            for p in grouped[key]:
                p.setdefault('clause_ids', [])
                if d.get('id') and d['id'] not in p['clause_ids']:
                    p['clause_ids'].append(d['id'])
            continue
        start = len(pts)
        topic = d.get('topic') or d.get('clause_label') or d.get('id')
        if d.get('expected_friction') == 'high':
            fb = d.get('prepared_fallback')
            if legal_review_open(d, reviewed):
                tail = T['legal']
            else:
                tail = (T['fallback'] % fb.rstrip('.')) if fb else T['no_fallback']
            pts.append(_point('friction', d, topic, T['friction'] % (topic, tail)))
        if d.get('at_last_fallback'):
            pts.append(_point('last_fallback', d, topic, T['last'] % topic))
        if d.get('coverage') == 'for_call':
            pts.append(_point('for_call', d, topic, T['call'] % topic))
        if d.get('escalation') or d.get('stuck_candidate'):
            pts.append(_point('escalation', d, topic, T['escalation'] % topic))
        if key:
            for p in pts[start:]:
                p['clause_ids'] = [d.get('id')] if d.get('id') else []
            grouped[key] = pts[start:]
    for c in concessions:
        ask = c.get('if_raised')
        pts.append(_point('concession', c, c.get('topic'),
                          T['conc'] % (c.get('topic'), (T['raised'] % ask.rstrip('.')) if ask else '')))
    # מזהה ייחודי גם כשכמה ויתורים חלים על אותו סעיף: השני מקבל "#2", וכן הלאה, לפי הסדר
    seen = {}
    for p in pts:
        n = seen[p['id']] = seen.get(p['id'], 0) + 1
        if n > 1:
            p['id'] = '%s#%d' % (p['id'], n)
    return pts
