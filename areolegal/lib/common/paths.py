# -*- coding: utf-8 -*-
"""נתיבי פלט בטוחים לכל הרכיבים (מימוש ייחוס, הערות הנושא ונותן 4.8, שינויים 20א ו-71; 4.9, שינוי 88: גבול אחד, 230, בקוד, בשער ובהערות).

הכלל: שם קצר וקבוע, ושלושת שמות הקבצים של אותו סבב (קובץ העבודה, העותק למשלוח והעותק "כפי שהופק")
מקוצרים יחד, באותו סדר קבוע, כך שהארוך שבהם, יחד עם רזרבה לסיומת " (NN)" כשהשם תפוס, אינו עולה
על 230 תווים בנתיב המלא. 230 משאיר עוד כעשרה תווים עד 240, לקבצים הזמניים של Word ו-OneDrive.
PATH_LIMIT הוא הקבוע היחיד: check_write_path, שער האיכות (PKG_PATH_LENGTH) ושאר הרכיבים מייבאים אותו, ואין
גבול אחר (לא 235 ולא 240).

    from common.paths import safe_out_paths, long_path
    names = safe_out_paths(folder, 'הסכם ייעוץ', 'EXAMPLECO', 1, '14.10.2026')
    names.work, names.send, names.as_produced

Python 3, ספרייה סטנדרטית בלבד.
"""
import os
import re
from collections import namedtuple

PATH_LIMIT = 230                 # אורך מרבי של נתיב מלא, כולל רזרבה לסיומת התנגשות
COLLISION_RESERVE = len(' (99)')  # רזרבה קבועה ל-" (2)" עד " (99)"
WORK_SUFFIX = {'he': ' - פנימי', 'en': ' - internal'}
AS_PRODUCED_SUFFIX = {'he': ' - כפי שהופק', 'en': ' - as produced'}
ROUND_WORD = {'he': 'סבב', 'en': 'Round'}
TYPE_MAX = 20
COMPANY_MAX = 15
TYPE_MIN = 12
_BAD = re.compile(r'[\\/:*?"<>|\x00-\x1f]')

OutPaths = namedtuple('OutPaths', 'work send as_produced longest step')


class PathTooLong(Exception):
    """התיקייה המחוברת עצמה ארוכה מדי: אין שם מינימלי שנכנס בגבול."""

    def __init__(self, length, limit=PATH_LIMIT):
        self.length, self.limit = length, limit
        super().__init__('הנתיב ארוך מדי: %d תווים (הגבול %d). יש לחבר תיקייה בנתיב קצר יותר.' % (length, limit))


def clean_name(s):
    """מסיר תווים שאסורים בשם קובץ ב-Windows, ומאחד רווחים."""
    s = _BAD.sub('', s or '')
    return re.sub(r'\s+', ' ', s).strip().rstrip('.')


def _base(agreement_type, company, round_no, date, lang):
    parts = [clean_name(agreement_type)]
    if company:
        parts.append(clean_name(company))
    parts += ['%s %d' % (ROUND_WORD[lang], round_no), date]
    return ' - '.join(parts)


def _variants(folder, base, ext, lang):
    work = os.path.join(folder, base + WORK_SUFFIX[lang] + ext)
    send = os.path.join(folder, base + ext)
    asp = os.path.join(folder, base + AS_PRODUCED_SUFFIX[lang] + ext)
    return work, send, asp


def safe_out_paths(folder, agreement_type, company, round_no, date, lang='he', ext='.docx', limit=PATH_LIMIT):
    """מחזיר OutPaths עם שלושת הנתיבים, אחרי קיצור משותף בסדר קבוע:
    (0) סוג ההסכם עד 20 תווים ושם החברה עד 15; (1) בלי שם החברה; (2) סוג ההסכם עד 12 תווים.
    אין קיצור אחר. כשגם (2) אינו נכנס: PathTooLong עם האורך.
    הבדיקה היא על os.path.abspath, כולל רזרבה קבועה לסיומת התנגשות.
    """
    folder = os.path.abspath(folder)
    steps = [(agreement_type[:TYPE_MAX], (company or '')[:COMPANY_MAX]),
             (agreement_type[:TYPE_MAX], ''),
             (agreement_type[:TYPE_MIN], '')]
    longest = 0
    for step, (at, co) in enumerate(steps):
        base = _base(at, co, round_no, date, lang)
        work, send, asp = _variants(folder, base, ext, lang)
        longest = max(len(work), len(send), len(asp)) + COLLISION_RESERVE
        if longest <= limit:
            return OutPaths(work, send, asp, longest, step)
    raise PathTooLong(longest, limit)


def unique_path(path):
    """כשהשם תפוס: " (2)", " (3)" וכו', בתוך הרזרבה שנשמרה. לעולם אינו דורס קובץ קיים."""
    if not os.path.exists(path):
        return path
    stem, ext = os.path.splitext(path)
    for n in range(2, 100):
        cand = '%s (%d)%s' % (stem, n, ext)
        if not os.path.exists(cand):
            return cand
    raise FileExistsError(path)


def check_write_path(path, limit=PATH_LIMIT):
    """בדיקה לפני כל כתיבה (גם לקובץ זמני ולקובץ המצב), מול PATH_LIMIT. מחזיר את האורך, או זורק PathTooLong.
    שם עם סיומת התנגשות (" (2)") נכנס בגבול, כי safe_out_paths שמר לו רזרבה."""
    n = len(os.path.abspath(path))
    if n > limit:
        raise PathTooLong(n, limit)
    return n


def stale_path(path, lang='he'):
    """השם שאליו מועבר עותק "למשלוח" שכבר הופק, כשנפתח אחריו תיקון לפני המשלוח (שינוי 80). הקובץ אינו נמחק:
    הוא מקבל סיומת " - לא למשלוח" (או " - not for sending"), כך שבתיקייה אין קובץ בשם הסופי."""
    stem, ext = os.path.splitext(path)
    return unique_path(stem + (' - לא למשלוח' if lang == 'he' else ' - not for sending') + ext)


def long_path(path):
    """נתיב שאפשר לפתוח גם מעבר ל-260 תווים ב-Windows (קידומת \\\\?\\). לקריאה של קבצים קיימים בלבד;
    קבצים חדשים נכתבים תמיד בנתיב שעבר את safe_out_paths."""
    p = os.path.abspath(path)
    if os.name != 'nt' or p.startswith('\\\\?\\'):
        return p
    if p.startswith('\\\\'):
        return '\\\\?\\UNC\\' + p[2:]
    return '\\\\?\\' + p
