# -*- coding: utf-8 -*-
"""risk/logo.py: הלוגו מהפרופיל כתמונה מוטמעת של עד 150 קילובייט, לשדה meta.branding.logo.

הבעיה (סבב 3): בפרופיל branding.logo_path מפנה ל-PNG של 4.9 מגה-בייט, והסכמה והוולידטור מחייבים תמונה מוטמעת
של עד 150 קילובייט. שני הרצים הקטינו בעזר משלהם (C1: JPEG של 17.8 קילובייט; C2: 120 על 120, 27 קילובייט),
ו-PIL אינה בתלויות המוצהרות. סיכום C1 פער 4; סיכום C2 פער 1.

הכלל (הערות 3.6): logo_data_uri(path) מחזיר data URI של עד MAX_BYTES:
1. קובץ PNG, JPEG, GIF או WebP שכבר קטן מהתקרה ורוחבו וגובהו עד MAX_PX: מוטמע כמו שהוא (ספרייה סטנדרטית).
2. אחרת: הקטנה ב-Pillow (תלות רשות, רק לכאן): הצלע הארוכה עד MAX_PX, PNG שומר שקיפות; אם עדיין גדול,
   JPEG על רקע לבן, באיכות יורדת, ואז צלע קטנה יותר. התוצאה תמיד עד התקרה, או LogoError.
3. בלי Pillow ועם קובץ גדול: LogoError עם הודעה אחת ללקוח ("לוגו קטן מ-150 קילובייט"), והדוח נבנה בלי לוגו.
לעולם לא נתיב, לעולם לא כתובת ברשת.
"""
import base64
import io
import os
import struct
import sys

if __name__ == '__main__':
    sys.dont_write_bytecode = True   # הרצה משורת הפקודה אינה כותבת __pycache__ לתוך החבילה

try:
    from common.cli import guard_out, parser, run, write_json
except ImportError:  # pragma: no cover
    import sys as _sys
    _sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from common.cli import guard_out, parser, run, write_json

MAX_BYTES = 150 * 1024
MAX_PX = 240
_MIME = {b'\x89PNG': 'image/png', b'\xff\xd8\xff': 'image/jpeg', b'GIF8': 'image/gif', b'RIFF': 'image/webp'}


class LogoError(Exception):
    pass


def _mime(b):
    for sig, m in _MIME.items():
        if b.startswith(sig):
            if m == 'image/webp' and b[8:12] != b'WEBP':
                continue
            return m
    return None


def _png_size(b):
    if b.startswith(b'\x89PNG\r\n\x1a\n') and b[12:16] == b'IHDR':
        return struct.unpack('>II', b[16:24])
    return None


def data_uri(b, mime):
    return 'data:%s;base64,%s' % (mime, base64.b64encode(b).decode('ascii'))


def uri_bytes(uri):
    """הגודל כמו שהוולידטור מודד: אורך ה-data URI כולו כפול 3/4."""
    return len(uri) * 3 // 4


def logo_data_uri(path, max_bytes=MAX_BYTES, max_px=MAX_PX):
    with open(path, 'rb') as fh:
        raw = fh.read()
    mime = _mime(raw)
    if not mime:
        raise LogoError('הקובץ אינו תמונה מוכרת (PNG, JPEG, GIF או WebP)')
    size = _png_size(raw)
    if uri_bytes(data_uri(raw, mime)) <= max_bytes and (size is None or max(size) <= max_px * 2):
        return data_uri(raw, mime)
    try:
        from PIL import Image
    except ImportError:
        raise LogoError('הלוגו %d קילובייט, מעל %d, ואין Pillow להקטנה: לבקש מהלקוח לוגו קטן מ-%d קילובייט'
                        % (len(raw) // 1024, max_bytes // 1024, max_bytes // 1024))
    img = Image.open(io.BytesIO(raw))
    img.load()
    for px in (max_px, max_px * 3 // 4, max_px // 2, max_px // 3):
        im = img.copy()
        im.thumbnail((px, px))
        if im.mode in ('P', 'LA', 'RGBA') or 'transparency' in im.info:
            buf = io.BytesIO()
            im.convert('RGBA').save(buf, 'PNG', optimize=True)
            if uri_bytes(data_uri(buf.getvalue(), 'image/png')) <= max_bytes:
                return data_uri(buf.getvalue(), 'image/png')
            bg = Image.new('RGB', im.size, (255, 255, 255))
            bg.paste(im.convert('RGBA'), mask=im.convert('RGBA').split()[-1])
            im = bg
        im = im.convert('RGB')
        for q in (85, 70, 55):
            buf = io.BytesIO()
            im.save(buf, 'JPEG', quality=q, optimize=True)
            if uri_bytes(data_uri(buf.getvalue(), 'image/jpeg')) <= max_bytes:
                return data_uri(buf.getvalue(), 'image/jpeg')
    raise LogoError('לא ניתן להקטין את הלוגו מתחת ל-%d קילובייט' % (max_bytes // 1024))


def main(argv=None):
    """python -I logo.py --logo <path> [--out uri.txt]. הלוגו נקרא בלבד; --out רק לקובץ ה-data URI."""
    ap = parser('הלוגו כ-data URI של עד 150 קילובייט', out_required=False)
    ap.add_argument('--logo', required=True, help='קובץ הלוגו מהפרופיל (קריאה בלבד)')
    a = ap.parse_args(argv)
    u = logo_data_uri(a.logo)
    if a.out:
        path = guard_out(a.out, [a.logo])
        with open(path, 'w', encoding='ascii') as fh:
            fh.write(u)
    print('%s %d bytes' % (u[:30], uri_bytes(u)))
    return 0


if __name__ == '__main__':
    sys.exit(run(main))
