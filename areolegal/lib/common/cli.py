# -*- coding: utf-8 -*-
"""common/cli.py: ממשק אחד לכל נקודת כניסה של החבילה (`main`), ושמירה על קובצי הקלט של הלקוח (גרסה 1.2.0).

הבעיה (סבב בדיקה 4): `risk\\extract_corpus.main` קיבל argv קצר, פירש את ההסכם של הלקוח כנתיב הפלט, ודרס אותו
ב-JSON. הכלל עכשיו, בכל נקודת כניסה:
1. `main(argv=None) -> int`, עם argparse. הקלט בארגומנטים מפורשים, והפלט רק ב-`--out` מפורש. אין ארגומנט
   מיקומי שמשמש לפלט.
2. `guard_out(out, inputs)` לפני כל כתיבה: מסרב (OutputRefused) כש-`--out` מצביע על אחד מקובצי הקלט (אחרי
   realpath ו-normcase), כשהוא בתוך תיקייה שמקבלת קבצים מהלקוח או מהצד שכנגד (SOURCE_DIR_NAMES, למשל
   `מהצד-שכנגד`), או כשהוא קובץ Word או PDF קיים.
3. `no_bytecode()` בראש כל נקודת כניסה, לפני ייבוא מודולים של החבילה: הרצה משורת הפקודה אינה כותבת
   `__pycache__` לתוך החבילה.

    from common.cli import parser, guard_out, OutputRefused
    ap = parser('תיאור', out_required=True)
    a = ap.parse_args(argv)
    guard_out(a.out, a.inputs)

Python 3, ספרייה סטנדרטית בלבד.
"""
import argparse
import os
import sys

# שמות תיקיות שמקבלות קבצים מהלקוח או מהצד שכנגד. פלט לעולם אינו נכתב בתוכן (בכל עומק).
SOURCE_DIR_NAMES = ('מהצד-שכנגד', 'מהצד שכנגד', 'מהצד_שכנגד', 'קבצי-מקור', 'מקור', 'source', 'sources-in',
                    'from-counterparty', 'incoming')
PROTECTED_EXT = ('.docx', '.doc', '.docm', '.dotx', '.pdf', '.xlsx', '.pptx')


class OutputRefused(Exception):
    """נתיב הפלט אסור: קובץ קלט, תיקיית מקור של הלקוח, או מסמך קיים."""


def no_bytecode():
    """לקרוא בראש נקודת כניסה, לפני ייבוא מודולים של החבילה."""
    sys.dont_write_bytecode = True


def _key(p):
    return os.path.normcase(os.path.realpath(os.path.abspath(p)))


def guard_out(out, inputs=(), source_dirs=(), allow_existing_doc=False):
    """מחזיר את הנתיב המוחלט של הפלט, או זורק OutputRefused.
    inputs: כל קובצי הקלט של ההרצה. source_dirs: תיקיות מקור נוספות של הלקוח (מעבר לשמות הקבועים)."""
    if not out or not str(out).strip():
        raise OutputRefused('חסר --out מפורש')
    k = _key(out)
    for p in inputs or ():
        if p and _key(p) == k:
            raise OutputRefused('--out הוא קובץ קלט: %s. פלט לעולם אינו נכתב על קובץ קלט' % p)
    parts = [x for x in k.replace('\\', '/').split('/') if x]
    names = {os.path.normcase(n) for n in SOURCE_DIR_NAMES}
    if any(x in names for x in parts[:-1]) or (os.path.isdir(k) and parts and parts[-1] in names):
        raise OutputRefused('--out בתוך תיקיית מקור של הלקוח (%s): %s' % ('/'.join(sorted(
            {x for x in parts if x in names})), out))
    for d in source_dirs or ():
        dk = _key(d)
        if k == dk or k.startswith(dk.rstrip('\\/') + os.sep):
            raise OutputRefused('--out בתוך תיקיית מקור של הלקוח: %s' % d)
    if not allow_existing_doc and os.path.isfile(k) and os.path.splitext(k)[1].lower() in PROTECTED_EXT:
        raise OutputRefused('--out הוא מסמך קיים (%s). פלט JSON או HTML נכתב רק לקובץ חדש או לקובץ פלט' % out)
    return os.path.abspath(out)


def parser(description, out_required=True, out_help=None):
    """ArgumentParser עם --out מפורש. בנקודת כניסה שרק מדווחת, --out אופציונלי (בלעדיו: הדפסה בלבד)."""
    ap = argparse.ArgumentParser(description=description)
    ap.add_argument('--out', required=out_required,
                    help=out_help or 'קובץ הפלט. לעולם לא קובץ קלט ולא תיקיית מקור של הלקוח')
    return ap


def write_json(out, data, inputs=()):
    """כתיבת פלט JSON אחרי guard_out."""
    import json
    path = guard_out(out, inputs)
    d = os.path.dirname(path)
    if d:
        os.makedirs(d, exist_ok=True)
    with open(path, 'w', encoding='utf-8') as fh:
        json.dump(data, fh, ensure_ascii=False, indent=1)
    return path


def run(main, argv=None):
    """עוטף main: OutputRefused מודפס ומחזיר 2, בלי traceback."""
    try:
        return main(argv)
    except OutputRefused as e:
        try:
            sys.stderr.reconfigure(encoding='utf-8')
        except Exception:  # pragma: no cover
            pass
        print('refused: %s' % e, file=sys.stderr)
        return 2
