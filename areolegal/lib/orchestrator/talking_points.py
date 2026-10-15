# -*- coding: utf-8 -*-
"""נקודות לשיחה בסיכום הפנימי (מימוש ייחוס, הערות הנושא ונותן 4.9, שינוי 85).

נקודות לשיחה הן מה שעורכת הדין אומרת כשהצד שכנגד פותח נושא. הן פנימיות, ואינן נכנסות לבועה. המודול כללי לכל
סוג הסכם: התוכן של כל נקודה (הנסיגה המוכנה, מה מבקשים אם נושא נפתח) בא מהפלייבוק או מתשובת המשתמש, ולעולם לא
מהרכיב (החלטה 22). מקורות:
(1) נקודות חיכוך צפויות (expected_friction: high), עם הנסיגה שהפלייבוק מכין (prepared_fallback);
(2) כלל שההצעה בו כבר בנסיגה האחרונה (at_last_fallback): אין לאן לרדת בלי "נדרשת הכרעתך";
(3) ויתורים מכוונים, עם מה שמבקשים אם הנושא נפתח (if_raised);
(4) פריטים שנשארו בלי הכרעה לשיחה (for_call).

    from orchestrator.talking_points import build_talking_points
"""


def build_talking_points(decisions, concessions=()):
    pts = []
    for d in decisions:
        topic = d.get('topic', d.get('id'))
        if d.get('expected_friction') == 'high':
            fb = d.get('prepared_fallback')
            pts.append({'topic': topic, 'kind': 'friction',
                        'text': '%s: צפוי ויכוח.%s' % (topic, (' נסיגה מוכנה: %s.' % fb.rstrip('.')) if fb else
                                                       ' אין נסיגה מוכנה: לברר מה חשוב להם לפני שמציעים.')})
        if d.get('at_last_fallback'):
            pts.append({'topic': topic, 'kind': 'last_fallback',
                        'text': '%s: ההצעה כבר בנסיגה האחרונה. ירידה נוספת היא "נדרשת הכרעתך" (מצב 2).' % topic})
        if d.get('coverage') == 'for_call':
            pts.append({'topic': topic, 'kind': 'for_call', 'text': '%s: נשאר לשיחה, בלי נוסח מכריע.' % topic})
    for c in concessions:
        ask = c.get('if_raised')
        pts.append({'topic': c.get('topic'), 'kind': 'concession',
                    'text': '%s: ויתרנו בסבב הזה.%s' % (c.get('topic'), (' אם הנושא נפתח: %s.' % ask.rstrip('.'))
                                                       if ask else '')})
    return pts
