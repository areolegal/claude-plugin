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
4. `load_docx_or_explain(path)` לפני קריאת docx של הלקוח: DOC, קובץ מוצפן, ZIP פגום, קובץ בלי document.xml ו-Strict
   מקבלים הודעה דו-לשונית וקוד 2, ולא traceback. `utf8_stdio()`: פלט בעברית גם בקונסולה שאינה UTF-8.

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


def utf8_stdio():
    """stdout ו-stderr ב-UTF-8, כש-reconfigure זמין. בלעדיו, בקונסולה ב-cp1252 (או PYTHONIOENCODING=cp1252),
    print של עברית נופל ב-UnicodeEncodeError, והסקריפט מסתיים בקוד 1 אחרי שכבר כתב חלק מהפלט."""
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding='utf-8', errors='replace')
        except (AttributeError, ValueError):  # לא TextIOWrapper (לכידה בבדיקות, pythonw)
            pass


# קובץ Word שאינו נקרא: אבחון והודעה דו-לשונית, במקום traceback של zipfile או של python-docx.
# כל נקודת כניסה שקוראת docx מהלקוח: doc, msg, code = load_docx_or_explain(path); if doc is None: print(msg); return code
DOCX_BAD_EXIT = 2
OLE_MAGIC = b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1'   # Compound File: DOC ישן, או docx שהוצפן בסיסמה
STRICT_W = 'http://purl.oclc.org/ooxml/wordprocessingml/main'
DOCX_MESSAGES = {
    'missing': ('הקובץ לא נמצא: %s',
                'File not found: %s'),
    'ole': ('הקובץ %s אינו docx: זה קובץ Word ישן (DOC) או מסמך מוצפן בסיסמה. פתחו אותו ב-Word, הסירו את '
            'הסיסמה אם יש, ושמרו בשמירה בשם כ-"Word Document (.docx)".',
            '%s is not a .docx: it is an old Word file (DOC) or a password-protected document. Open it in Word, '
            'remove the password if there is one, and use Save As "Word Document (.docx)".'),
    'not_zip': ('הקובץ %s פגום, או שאינו מסמך Word (אינו ZIP תקין). פתחו אותו ב-Word ושמרו מחדש, או בקשו עותק תקין.',
                '%s is corrupt or is not a Word document (not a valid ZIP). Open it in Word and save it again, '
                'or ask for a working copy.'),
    'no_document': ('בקובץ %s אין word/document.xml: זה אינו מסמך Word (אולי Excel, PowerPoint או ZIP אחר).',
                    '%s has no word/document.xml: it is not a Word document (perhaps Excel, PowerPoint or another ZIP).'),
    'bad_xml': ('הקובץ %s פגום: word/document.xml אינו XML תקין. פתחו אותו ב-Word ושמרו מחדש.',
                '%s is corrupt: word/document.xml is not valid XML. Open it in Word and save it again.'),
    'strict': ('המסמך %s שמור בתבנית Strict Open XML, שהכלי אינו קורא. פתחו אותו ב-Word ושמרו בשמירה בשם '
               'כ-"Word Document (.docx)" (לא "Strict Open XML Document").',
               '%s is saved as Strict Open XML, which this tool does not read. Open it in Word and use Save As '
               '"Word Document (.docx)" (not "Strict Open XML Document").'),
    'unreadable': ('לא ניתן לקרוא את %s כמסמך Word (%s).',
                   '%s cannot be read as a Word document (%s).'),
}


def docx_message(kind, path, detail=''):
    """ההודעה הדו-לשונית: עברית, ובשורה שאחריה אנגלית."""
    he, en = DOCX_MESSAGES[kind]
    args = (path, detail) if kind == 'unreadable' else (path,)
    return (he % args) + '\n' + (en % args)


def docx_problem(path, strict_ok=False):
    """(kind, message) כשהקובץ אינו נקרא כמסמך Word רגיל, או None. בודק בלי לטעון: קיום, כותרת OLE (DOC או
    קובץ מוצפן), ZIP פגום, word/document.xml חסר, ומרחב השמות של Strict (strict_ok=True: Strict אינו בעיה, למי
    שמנרמל אותו בעצמו)."""
    import zipfile
    try:
        from common.paths import long_path
    except ImportError:  # pragma: no cover
        long_path = lambda p: p  # noqa: E731
    name = os.path.basename(str(path))
    try:
        with open(long_path(str(path)), 'rb') as fh:
            head = fh.read(8)
    except (FileNotFoundError, IsADirectoryError, NotADirectoryError):
        return 'missing', docx_message('missing', path)
    except OSError as e:
        return 'unreadable', docx_message('unreadable', name, type(e).__name__)
    if head == OLE_MAGIC:
        return 'ole', docx_message('ole', name)
    try:
        with zipfile.ZipFile(long_path(str(path))) as z:
            if 'word/document.xml' not in z.namelist():
                return 'no_document', docx_message('no_document', name)
            head = z.open('word/document.xml').read(4096).decode('utf-8', 'replace')
    except Exception:  # noqa: BLE001  BadZipFile, zlib.error, EOFError: הקובץ פגום
        return 'not_zip', docx_message('not_zip', name)
    if not strict_ok and STRICT_W in head:
        return 'strict', docx_message('strict', name)
    return None


def load_docx_or_explain(path, loader=None, strict_ok=False):
    """(doc, None, 0) כשהמסמך נטען, או (None, message, code) כשלא: הודעה דו-לשונית (עברית ואנגלית) וקוד 2
    (DOCX_BAD_EXIT). קובץ שלא נמצא: קוד 1, כמו בשאר נקודות הכניסה. loader: הפונקציה שטוענת (ברירת מחדל:
    docx.Document); loader=False: בדיקה בלבד, ו-doc הוא הנתיב."""
    found = docx_problem(path, strict_ok=strict_ok)
    if found:
        kind, msg = found
        return None, msg, (1 if kind == 'missing' else DOCX_BAD_EXIT)
    if loader is False:
        return path, None, 0
    if loader is None:
        from docx import Document as loader
    try:
        return loader(path), None, 0
    except Exception as e:  # noqa: BLE001  כל כישלון טעינה אחר: הודעה, לא traceback
        return None, docx_message('unreadable', os.path.basename(str(path)), type(e).__name__), DOCX_BAD_EXIT
