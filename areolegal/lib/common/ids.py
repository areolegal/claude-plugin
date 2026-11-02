# -*- coding: utf-8 -*-
"""מספר תאגיד ומספר זהות ישראליים: פורמט, ספרת ביקורת, והשוואה רק לפרופיל ולמסמכי החברה
(מימוש ייחוס, הערות הנושא ונותן 4.8, שינוי 75; 4.9, שינוי 86: שדה ריק לשלב החתימה גם בנייר באנגלית).

כללים:
- מספר תאגיד הוא 9 ספרות בדיוק. ספרת הביקורת לפי אותו אלגוריתם של מספר זהות: משקלות 1,2,1,2...
  משמאל, סכום הספרות של כל מכפלה, והסכום מתחלק ב-10.
- הקידומות התקינות של תאגיד ישראלי: 51 ו-52 (חברה, כולל חל"צ וחברה ממשלתית), 55 (שותפות), 56 (חברת חוץ),
  57 (אגודה שיתופית), 58 (עמותה), 50 (גוף ציבורי: משרד ממשלתי, רשות מקומית, תאגיד סטטוטורי), ו-53, 54, 59
  (מספרים אחרים שניתנים לגופים ציבוריים, למוסדות ולהקדשות). קידומת אחרת, למשל מספר זהות של אדם,
  מסומנת "not_company" כשהצפי הוא תאגיד, והשאלה עולה ללקוחה.
- ספרת הביקורת נבדקת רק כשהרישום ישראלי (incorporation_country או organization_type בפרופיל,
  israeli_registry). מספר זר נבדק רק מול הפרופיל. בהיעדר מידע על ההתאגדות: אזהרה, ולא כשל.
- מספר בן 8 ספרות אינו מספר תאגיד. לא משלימים לו אפס מוביל.
- ההשוואה היא רק מול הפרופיל ומול מסמכי החברה (הסכם חתום, תעודת התאגדות, נייר פירמה). שם של
  תיקייה אינו מקור, לעולם.
- פרט שנכשל בבדיקה אינו נכנס לנוסח כאילו הוא תקין, גם לא בסוגריים. הוא נשאל פעם אחת, במנת השאלות.
  תשובה "נשלים לפני החתימה" נותנת שדה ריק מסומן לשלב החתימה (SIGNING_BLANK), שאינו חוסם את העותק
  למשלוח ונרשם ברשימת הבדיקה לפני חתימה.

Python 3, ספרייה סטנדרטית בלבד.
"""
import re

SIGNING_BLANKS = {'he': '________ (יושלם בחתימה)', 'en': '________ (to be completed at signing)'}
SIGNING_BLANK = SIGNING_BLANKS['he']  # תאימות לאחור: הנוסח העברי
COMPANY_PREFIXES = ('51', '52')
OTHER_PREFIXES = {'55': 'שותפות', '56': 'חברת חוץ', '57': 'אגודה שיתופית', '58': 'עמותה',
                  '50': 'גוף ציבורי', '53': 'גוף ציבורי או מוסד', '54': 'גוף ציבורי או מוסד',
                  '59': 'גוף ציבורי או מוסד'}  # כל קידומת אחרת: unknown_prefix
# צורות התאגדות שמעידות על רישום ישראלי. "חברת חוץ" רשומה בישראל (קידומת 56) גם כשהתאגדה בחו"ל. בפרופיל
# באנגלית צורת ההתאגדות נשמרת בתווית האנגלית של הטופס, ולכן גם היא כאן.
ISRAELI_FORMS = ('חברה ממשלתית', 'עמותה', 'אגודה שיתופית', 'חברת חוץ', 'חל״צ', 'חל"צ',
                 'Government company', 'Non-profit association (amuta)', 'Public benefit company (PBC)',
                 'Cooperative society', 'Foreign company registered in Israel')
ALLOWED_SOURCES = ('profile', 'signed_agreement', 'incorporation_certificate', 'letterhead', 'client_answer')
COMPLETE_AT_SIGNING = re.compile(r'נשלים\s+(לפני|ב)\s*(ה)?חתימה|יושלם\s+(לפני|ב)\s*(ה)?חתימה|נמלא\s+(לפני|ב)\s*(ה)?חתימה|'
                                 r'complete(d)?\s+(at|before)\s+signing|to be completed at signing')


def check_digit_ok(num):
    """אלגוריתם ספרת הביקורת של מספר זהות ומספר תאגיד (9 ספרות)."""
    if not re.fullmatch(r'\d{9}', num):
        return False
    total = 0
    for i, ch in enumerate(num):
        d = int(ch) * (1 if i % 2 == 0 else 2)
        total += d if d < 10 else d - 9
    return total % 10 == 0


def normalize(raw):
    """מסיר רווחים, מקפים ונקודות. אינו משלים אפסים."""
    return re.sub(r'[\s\-.‎‏]', '', str(raw or ''))


def israeli_registry(profile):
    """האם מספר הרישום שלנו ישראלי: True, False, או None כשאין בפרופיל מידע להכריע."""
    p = profile or {}
    c = str(p.get('incorporation_country') or p.get('incorporation_country_name') or '').strip()
    t = str(p.get('organization_type') or '').strip()
    if t.startswith('חברת חוץ'):
        return True
    if c:
        return c.upper() in ('IL', 'ISR', 'ISRAEL') or c == 'ישראל'
    if t.startswith('חברה זרה') or t.startswith('Foreign company (not'):
        return False
    if t.startswith(ISRAELI_FORMS):
        return True
    return None


def validate_company_number(raw, expect_company=True, israeli=True):
    """מחזיר dict: valid (bool), number, reason (ok / missing / not_digits / wrong_length / bad_check_digit /
    not_company / foreign_not_checked), kind. ברישום ישראלי (ברירת המחדל): "valid" רק כשהמספר בן 9 ספרות,
    ספרת הביקורת תקינה, וכשמצפים לתאגיד, הקידומת אחת מ-50 עד 59. kind: company, או שם הסוג
    מ-OTHER_PREFIXES (עמותה, גוף ציבורי וכו').
    israeli=False: מספר זר. אין בדיקת פורמט או ספרת ביקורת; הוא נבדק רק מול הפרופיל.
    """
    num = normalize(raw)
    out = {'raw': raw, 'number': num, 'valid': False, 'kind': None}
    if not num:
        out['reason'] = 'missing'
        return out
    if israeli is False:
        out.update(valid=True, reason='foreign_not_checked', kind='foreign')
        return out
    if not num.isdigit():
        out['reason'] = 'not_digits'
        return out
    if len(num) != 9:
        out['reason'] = 'wrong_length'
        out['length'] = len(num)
        return out
    if not check_digit_ok(num):
        out['reason'] = 'bad_check_digit'
        return out
    prefix = num[:2]
    out['kind'] = 'company' if prefix in COMPANY_PREFIXES else OTHER_PREFIXES.get(prefix, 'unknown_prefix')
    if expect_company and prefix not in COMPANY_PREFIXES and prefix not in OTHER_PREFIXES:
        out['reason'] = 'not_company'
        return out
    out['valid'] = True
    out['reason'] = 'ok'
    return out


def validate_person_id(raw):
    """מספר זהות: עד 9 ספרות, משלימים אפסים מובילים לפי הנוהג, וספרת ביקורת."""
    num = normalize(raw)
    if not num.isdigit() or not 5 <= len(num) <= 9:
        return {'raw': raw, 'number': num, 'valid': False, 'reason': 'wrong_length'}
    num = num.zfill(9)
    ok = check_digit_ok(num)
    return {'raw': raw, 'number': num, 'valid': ok, 'reason': 'ok' if ok else 'bad_check_digit'}


def resolve_company_number(profile_value, document_values=(), folder_names=(), israeli=True):
    """קובע את מספר התאגיד שלנו לנוסח. מקורות מותרים: הפרופיל ומסמכי החברה בלבד.

    document_values: רשימה של (source, value), כש-source אחד מ-ALLOWED_SOURCES. מקור אחר נדחה.
    folder_names: מתקבל רק כדי לתעד שהוא לא נקרא. שום ערך ממנו אינו משמש.

    מחזיר dict:
      status: confirmed (מספר תקין אחד שכל המקורות המותרים מסכימים עליו) /
              invalid (המספר בפרופיל נכשל בבדיקה, ואין מספר תקין במסמכים) /
              conflict (שני מספרים תקינים שונים במקורות המותרים) /
              missing (אין מספר בשום מקור מותר)
      number: המספר לנוסח, רק כש-status הוא confirmed
      ask: True כשצריך שאלה אחת במנת השאלות (מצב 3)
      checks: תוצאת הבדיקה לכל מקור
      ignored: מקורות שנדחו (כולל שמות תיקיות)
    israeli: כמו ב-validate_company_number. מספר זר (False) נבדק רק בהשוואה בין המקורות.
    """
    checks, ignored = [], []
    if profile_value:
        checks.append(('profile', validate_company_number(profile_value, israeli=israeli)))
    for src, val in document_values:
        if src not in ALLOWED_SOURCES:
            ignored.append((src, val))
            continue
        checks.append((src, validate_company_number(val, israeli=israeli)))
    for name in folder_names:
        ignored.append(('folder_name', name))
    valid_numbers = sorted({c['number'] for _, c in checks if c['valid']})
    res = {'checks': checks, 'ignored': ignored, 'number': None}
    if not checks:
        res.update(status='missing', ask=True)
    elif len(valid_numbers) > 1:
        res.update(status='conflict', ask=True)
    elif len(valid_numbers) == 1 and all(c['valid'] for _, c in checks):
        res.update(status='confirmed', ask=False, number=valid_numbers[0])
    elif len(valid_numbers) == 1:
        # מספר תקין במסמך של החברה, ומספר פגום בפרופיל: מציעים את התקין, ושואלים פעם אחת כדי לתקן את הפרופיל.
        res.update(status='invalid', ask=True, recommended=valid_numbers[0])
    else:
        res.update(status='invalid', ask=True)
    return res


def signing_blank(lang='he'):
    """השדה הריק לשלב החתימה בשפת הנייר. בנייר באנגלית: "________ (to be completed at signing)"."""
    return SIGNING_BLANKS.get(lang, SIGNING_BLANKS['he'])


def is_complete_at_signing(answer):
    """האם תשובת הלקוחה היא "נשלים לפני החתימה" או דומה לה."""
    return bool(answer and COMPLETE_AT_SIGNING.search(str(answer)))


def detail_for_draft(detail, answer=None, value=None, validator=None, lang='he'):
    """מה נכנס לנוסח בפרט זיהוי שלנו (מספר תאגיד, כתובת, שם החותם).

    - value תקין (לפי validator, כשיש) נכנס כמו שהוא.
    - value שנכשל בבדיקה אינו נכנס לעולם, גם לא בסוגריים.
    - תשובה "נשלים לפני החתימה": השדה הריק בשפת הנייר (signing_blank(lang)), שאינו חוסם את העותק למשלוח.
    - אחרת: None, כלומר הפרט עדיין פתוח (שאלה במנת השאלות), והעותק למשלוח חסום.
    מחזיר (text_or_None, status) כש-status הוא value / signing_blank / open.
    """
    if value is not None:
        ok = True if validator is None else validator(value).get('valid', False)
        if ok:
            return value, 'value'
    if is_complete_at_signing(answer):
        return signing_blank(lang), 'signing_blank'
    return None, 'open'
