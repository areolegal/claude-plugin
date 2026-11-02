# -*- coding: utf-8 -*-
"""נתיבי פלט בטוחים לכל הרכיבים (מימוש ייחוס, הערות הנושא ונותן 4.8, שינויים 20א ו-71; 4.9, שינוי 88: גבול אחד, 230, בקוד, בשער ובהערות).

הכלל: שם קצר וקבוע, ושלושת שמות הקבצים של אותו סבב (קובץ העבודה, העותק למשלוח והעותק "כפי שהופק")
מקוצרים יחד, באותו סדר קבוע, כך שהארוך שבהם, יחד עם רזרבה לסיומת " (NN)" כשהשם תפוס, אינו עולה
על 230 תווים בנתיב המלא. 230 משאיר עוד כעשרה תווים עד 240, לקבצים הזמניים של Word ו-OneDrive.
PATH_LIMIT הוא הקבוע היחיד: check_write_path, שער האיכות (PKG_PATH_LENGTH) ושאר הרכיבים מייבאים אותו, ואין
גבול אחר (לא 235 ולא 240).

    from common.paths import safe_out_paths, long_path, plain_path
    names = safe_out_paths(folder, '<סוג ההסכם>', '<חברה>', 1, '3.4.2027')
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


# התחילית של שם הקובץ (סוג ההסכם ושם החברה) נקבעת בסבב הראשון ונשמרת בקובץ המצב (meta.file_prefix). סבב המשך
# משתמש בה, גם כששם החברה נמסר אחר כך בשפה אחרת (למשל בסבב 1 "<סוג> - <שם בעברית>", ובסבב 2
# "<סוג> - <השם באנגלית>"). החלפה רק אחרי שאלה אחת, כשהתחילית בשפה שאינה שפת ההסכם (prefix_switch_item)
_ROUND_PART = re.compile(r'^(?:%s) \d+$' % '|'.join(ROUND_WORD.values()))
_HEB = re.compile('[א-ת]')
_LAT = re.compile('[A-Za-z]')


def prefix_from_name(name):
    """(סוג ההסכם, שם החברה) מתוך שם קובץ לפי הכלל ("<סוג> - <חברה> - Round 2 - <תאריך>..."), או None."""
    parts = os.path.basename(str(name or '')).split(' - ')
    k = next((i for i, x in enumerate(parts) if _ROUND_PART.match(x.strip())), None)
    if not k:
        return None
    return parts[0], ' - '.join(parts[1:k])


def stored_prefix(state):
    """התחילית שנקבעה בסבב הראשון: meta.file_prefix, ובקובץ מצב ישן לפי שם הקובץ הראשון שהופק או נשלח. או None."""
    meta = (state or {}).get('meta') or {}
    fp = meta.get('file_prefix')
    if isinstance(fp, dict) and fp.get('agreement_type'):
        return fp['agreement_type'], fp.get('company') or ''
    docs = [d for d in (state or {}).get('produced_documents') or () if isinstance(d, dict)
            and d.get('kind') in ('work', 'send', 'as_produced')] + \
           [d for d in meta.get('sent_documents') or () if isinstance(d, dict)]
    for d in docs:
        pr = prefix_from_name(d.get('path') or d.get('file_name'))
        if pr:
            return pr
    return None


def name_lang(s):
    """שפת הכתב של שם: he, en, או None כשאין אותיות."""
    if _HEB.search(s or ''):
        return 'he'
    return 'en' if _LAT.search(s or '') else None


def prefix_switch_item(prefix, lang, alt_company, ui_lang='he'):
    """שאלת ההחלפה, פעם אחת (key: file_prefix): התחילית השמורה בשפה שאינה שפת ההסכם (lang), ונמסר שם בשפת ההסכם
    (alt_company). פריט למנת השאלות, או None כשאין מה לשאול."""
    # שם החברה בשם הקובץ הוא השם המקוצר, בלי סיומת התאגדות
    alt_company = re.sub(r'[,\s]+(Ltd|Limited|Inc|LLC|Corp|Corporation|GmbH|PLC|AG|בע"מ)\.?$', '',
                         str(alt_company or '').strip(), flags=re.I)
    if not prefix or not alt_company or name_lang(prefix[1]) in (None, lang) or name_lang(alt_company) != lang \
            or clean_name(alt_company) == clean_name(prefix[1]):
        return None
    old = ' - '.join(x for x in prefix if x)
    new = ' - '.join(x for x in (prefix[0], clean_name(alt_company)) if x)
    if str(ui_lang or '').lower()[:2] == 'en':
        return {'key': 'file_prefix', 'kind': 'file_prefix', 'situation': None, 'blocks_sending': False,
                'text': 'The file names of this deal start with "%s" (set in the first round). The agreement is in '
                        'English, and an English company name is now known. Switch the file names to "%s"?' % (old, new),
                'recommendation': 'Keep "%s", so that all rounds stay together' % old,
                'options': ['Keep (recommended)', 'Switch to "%s"' % new]}
    return {'key': 'file_prefix', 'kind': 'file_prefix', 'situation': None, 'blocks_sending': False,
            'text': 'שמות הקבצים בעסקה הזו נפתחים ב-"%s" (נקבע בסבב הראשון). ההסכם באנגלית, ועכשיו ידוע שם החברה '
                    'באנגלית. להחליף את תחילת שמות הקבצים ל-"%s"?' % (old, new),
            'recommendation': 'להשאיר את "%s", כדי שכל הסבבים יישארו יחד' % old,
            'options': ['להשאיר (ההמלצה)', 'להחליף ל-"%s"' % new]}


def prefix_switch_answer(state):
    """התשובה לשאלת ההחלפה (user_decisions, id file_prefix): 'switch', 'keep', או None כשלא נענתה."""
    rec = next((q for q in reversed((state or {}).get('user_decisions') or ()) if isinstance(q, dict)
                and q.get('id') == 'file_prefix'), None)
    if not rec:
        return None
    return 'switch' if re.match(r'\s*(להחליף|החלף|switch|replace|yes|כן)', str(rec.get('answer') or ''), re.I) \
        else 'keep'


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
    """השם שאליו מועבר עותק "למשלוח" שכבר הופק, כשהשער במצב משלוח נכשל אחריו. הקובץ אינו נמחק:
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


def plain_path(path):
    """ההפך של long_path: הנתיב בלי הקידומת \\\\?\\, להצגה ולשמירה בקובץ פלט. מי שקורא את הנתיב השמור
    פותח אותו שוב דרך long_path."""
    p = str(path)
    if p.startswith('\\\\?\\UNC\\'):
        return '\\\\' + p[8:]
    if p.startswith('\\\\?\\'):
        return p[4:]
    return p
