# -*- coding: utf-8 -*-
"""risk/page_text.py: הטקסט של עותק גולמי (HTML, טקסט או PDF), ונרמול אחד לעברית, לבדיקת קטעים וציטוטים.

הבעיות שהמודול סוגר (סבב 3):
- C1, פער 1; המהנדס 9: המקור הרשמי היחיד לנוסח חוק ישראלי הוא פרסום ברשומות (PDF באתר הכנסת).
  decode_page פענח את הבייטים של ה-PDF כטקסט, ולכן כל קטע מילולי מ-PDF נכשל ("הקטע המילולי לא נמצא בעותק
  הגולמי"), והרץ עקף בעטיפה בזמן ריצה. כאן: עותק שמתחיל ב-%PDF- נקרא דרך שכבת הטקסט שלו.
- C1, פער 2: norm() הפך ״ ל-" לפני חילוץ הקטע שבין המירכאות, ולכן "התשע"ז" או "ס"ח" בתוך קטע פיצלו אותו.
  כאן: גרשיים וגרש בתוך מילה עברית (בין שתי אותיות) מנורמלים ל-״ ו-׳ לפני כל דבר אחר, בטקסט ובקטע באותה
  פונקציה, ורק מירכאות שאינן בתוך מילה הן גבולות של ציטוט.
- C2, פער 6: store_page פענח תמיד UTF-8; דף מנבו (windows-1255) נשמר משובש. entity_store משתמש עכשיו ב-page_text.

שכבת הטקסט של PDF: PyMuPDF (pymupdf או fitz) כשמותקן, אחרת pypdf. שתיהן תלות רשות; כשאין אף אחת, או כשאין
ל-PDF שכבת טקסט (סריקה), PdfTextUnavailable, ואז נשמר לצד העותק קובץ טקסט (raw_copies[].text_file, עם
text_sha256), שהוולידטור קורא במקום ה-PDF. בדיקת הגיבוב רצה תמיד על העותק הגולמי עצמו.
"""
import html as _html
import re
import unicodedata

HEB = 'א-ת'
_BIDI = re.compile('[‎‏‪-‮⁦-⁩﻿­]')
_NIQQUD = re.compile('[֑-ׇ]')
_DQ = '"“”„״ʺ＂'      # כל סוגי המירכאות הכפולות וגרשיים
_SQ = "'‘’׳ʹ＇"             # כל סוגי הגרש


class PdfTextUnavailable(Exception):
    pass


def is_pdf(b):
    return isinstance(b, (bytes, bytearray)) and bytes(b[:1024]).lstrip().startswith(b'%PDF-')


def decode_page(b):
    """דף רשמי שנשמר גולמי: UTF-8 תקין קודם (עותק שנשמר מחדש שומר את ה-charset המקורי בדף), אחר כך
    ה-charset שבדף, ואחר כך windows-1255 (נבו). ל-PDF: שכבת הטקסט (pdf_text)."""
    if is_pdf(b):
        return pdf_text(b)
    m = re.search(rb'charset=["\']?([A-Za-z0-9_\-]+)', b[:4096])
    for enc in ['utf-8'] + ([m.group(1).decode('ascii', 'ignore')] if m else []) + ['cp1255']:
        try:
            return b.decode(enc)
        except (LookupError, UnicodeDecodeError):
            continue
    return b.decode('utf-8', 'replace')


def pdf_text(b):
    """שכבת הטקסט של PDF, עמוד אחרי עמוד. PyMuPDF נותן סדר לוגי בעברית ברשומות; pypdf כגיבוי."""
    b = bytes(b)
    try:
        try:
            import pymupdf as fitz  # noqa: F401
        except ImportError:
            import fitz  # type: ignore
        doc = fitz.open(stream=b, filetype='pdf')
        text = '\n'.join(p.get_text() for p in doc)
        doc.close()
        if text.strip():
            return text
    except ImportError:
        pass
    except Exception as e:  # PDF פגום
        raise PdfTextUnavailable('PDF לא נקרא: %s' % e)
    try:
        import io
        import pypdf
        r = pypdf.PdfReader(io.BytesIO(b))
        text = '\n'.join((pg.extract_text() or '') for pg in r.pages)
        if text.strip():
            return text
    except ImportError:
        raise PdfTextUnavailable('אין ספרייה לקריאת שכבת הטקסט של PDF (pymupdf או pypdf): לשמור text_file')
    except Exception as e:
        raise PdfTextUnavailable('PDF לא נקרא: %s' % e)
    raise PdfTextUnavailable('ל-PDF אין שכבת טקסט (סריקה): לשמור text_file')


def page_text(b):
    """הטקסט הגלוי של עותק גולמי: PDF דרך שכבת הטקסט; HTML בלי script, style ותגיות, עם ישויות מפוענחות."""
    t = decode_page(b)
    if is_pdf(b):
        return t
    if re.search(r'<(html|body|div|p|span|table|br)\b', t[:200000], re.I):
        t = re.sub(r'<script.*?</script>|<style.*?</style>', ' ', t, flags=re.S | re.I)
        t = _html.unescape(re.sub(r'<[^>]+>', ' ', t))
    return t


def norm(s):
    """נרמול אחד לטקסט ולציטוט: בלי סימני כיווניות, ניקוד ומקף רך; גרשיים וגרש בתוך מילה עברית הם ״ ו-׳;
    כל שאר המירכאות הן " ו-'; מקפים (מקף עברי, מקף קצר) הם -; רווחים מכווצים."""
    s = unicodedata.normalize('NFC', s or '')
    s = _BIDI.sub('', s)
    s = _NIQQUD.sub('', s)
    s = s.replace('־', '-').replace('‑', '-').replace('‐', '-').replace(' ', ' ')
    # קודם כל סוגי המירכאות לצורה אחת, אחר כך הכרעה אחת: גרשיים או מירכאה
    s = re.sub('[%s]' % re.escape(_DQ), '"', s)
    s = re.sub('[%s]' % re.escape(_SQ), "'", s)
    # גרשיים: מירכאה בין שתי אותיות עבריות ("התשע"ז", "ס"ח", "בע"מ")
    s = re.sub('(?<=[%s])"(?=[%s])' % (HEB, HEB), '״', s)
    # גרש: אחרי אות עברית, ואחריו אות עברית, ספרה, רווח, פיסוק או סוף ("ח'1", "פרק ח'", "צ'ק")
    s = re.sub("(?<=[%s])'(?=[%s0-9]|[\\s.,;:)\\]]|$)" % (HEB, HEB), '׳', s)
    return re.sub(r'\s+', ' ', s).strip()


def quote_segments(excerpt, min_len=8):
    """מה שנבדק מתוך excerpt: "מיקום: "ציטוט"" -> הציטוט; כמה קטעים מופרדים ב-... או …; מירכאות פנימיות
    נשארות (ציטוט שמכיל ציטוט). בלי מירכאות בכלל: כל ה-excerpt."""
    ex = norm(excerpt)
    i, j = ex.find('"'), ex.rfind('"')
    body = ex[i + 1:j] if 0 <= i < j else ex
    parts = [p.strip(' ."') for p in re.split(r'\s*(?:\.\.\.|…)\s*', body)]
    parts = [p for p in parts if len(p) >= min_len]
    return parts or ([body.strip(' ."')] if body.strip(' ."') else [])


def excerpt_in(excerpt, text):
    """כל קטע של הציטוט נמצא, מילה במילה אחרי נרמול, בטקסט. text יכול להיות מנורמל כבר."""
    t = norm(text)
    return all(seg in t for seg in quote_segments(excerpt))
