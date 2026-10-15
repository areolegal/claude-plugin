# -*- coding: utf-8 -*-
"""common/terms.py: התאמה של מונח אסור לפי גבולות מילה, גם בעברית (גרסה 1.2.0).

הבעיה (סבב בדיקה 4): בדיקת המונחים האסורים בשער האיכות חיפשה מחרוזת, ולכן "ירוק" נמצא בתוך "ירוקנו" ובתוך
"פירוק", ו"צהוב" בתוך מילים אחרות. אותה בעיה בכל רשימת מונחים אסורים בחבילה.

הכלל: מונח נמצא רק כמילה שלמה. לפניו: תחילת טקסט או תו שאינו אות, ואחריו: סוף טקסט או תו שאינו אות.
בעברית מותרות לפניו אותיות השימוש (ו, ה, ב, כ, ל, מ, ש: "הירוק", "והצהוב"), ואחריו סיומת נטייה (ה, ים, ות:
"ירוקה"); באנגלית סיומת רבים (s, es). מונח שמסתיים במילה בת אות אחת ("יודע ש") או בתו שאינו אות אינו מקבל
גבול מימין. ספרייה סטנדרטית בלבד.

    from common.terms import terms_re, find_term
    rx = terms_re(['ירוק', 'צהוב', 'policy'])
    find_term('נוסח ירוקנו', rx)   # None
"""
import re

LETTER = r'[^\W\d_]'
HE_PREFIX = r'(?:[ובכלמשה]{1,3})?'
HE_SUFFIX = r'(?:ה|ים|ות)?'
EN_SUFFIX = r'(?:s|es)?'
_HE = re.compile(r'[\u05d0-\u05ea]')


def _wrap(term, is_regex=False):
    body = term if is_regex else re.escape(term)
    plain = term if not is_regex else re.sub(r'\\.|[\[\](){}?*+|^$]', '', term)
    he = bool(_HE.search(plain))
    first = plain[:1]
    last_word = (plain.split() or [''])[-1]
    left = '(?<!%s)' % LETTER if re.match(LETTER, first or '0') or is_regex else ''
    pre = HE_PREFIX if he and _HE.match(first or '') else ''
    right = ''
    if plain and re.match(LETTER, plain[-1]) and len(last_word) > 1:
        right = (HE_SUFFIX if _HE.match(plain[-1]) else EN_SUFFIX) + '(?!%s)' % LETTER
    return left + pre + '(?:' + body + ')' + right


def terms_re(terms, flags=re.I, regex_terms=()):
    """ביטוי אחד לכל הרשימה. terms: מחרוזות מילוליות. regex_terms: ביטויים (למשל r'market (practice|standard)')
    שמקבלים את אותם גבולות. ביטוי שאינו מילה (כתובת, קוד) לא נכנס לכאן ונבדק בנפרד."""
    parts = [_wrap(t) for t in terms if t] + [_wrap(t, True) for t in regex_terms if t]
    return re.compile('|'.join(parts), flags)


def find_term(text, rx):
    """המונח הראשון שנמצא כמילה שלמה, או None."""
    m = rx.search(text or '')
    return m.group(0) if m else None


def find_all(text, terms, flags=re.I):
    """כל המונחים מהרשימה שנמצאו כמילה שלמה, בסדר הרשימה."""
    return [t for t in terms if terms_re([t], flags).search(text or '')]
