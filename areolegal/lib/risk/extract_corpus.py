# -*- coding: utf-8 -*-
"""risk/extract_corpus.py: חילוץ מסמכי Word לקובץ ביניים, לכל מסמך, תמיד (גם מסמך יחיד).

מחליף את contract-risk-assessor/scripts/extract_corpus.py שבחבילה (הערות 3.4 שינוי 22; 3.5).
מאחד את שתי ההדמיות של סבב 2 (C1ב: risk_c1b_r2/extract.py; C2: c2risk/extract_fixed.py) ומתקן בהן:
- פסקה בתוך תיבת טקסט נספרה פעמיים (פעם בפסקה העוטפת ופעם לבד). כאן כל פסקה נספרת פעם אחת, עם in_textbox.
- זיהוי טקסט מוסתר היה חלקי (בלי specVanish, בלי צבע קרוב ללבן מכל גוון, בלי גופן זעיר בחצאי נקודות).

לכל פסקה, בכל חלק (גוף, כותרות עליונות ותחתונות, הערות שוליים וסיום, תיבות טקסט):
  text_accept_all  הנוסח אחרי "קבל הכול" (w:ins ו-w:moveTo נשארים; w:del ו-w:moveFrom יוצאים)
  text_reject_all  הנוסח אחרי "דחה הכול" (ההפך)
  hidden           [{how, text}] how: vanish | specVanish | webHidden | color | font_size
לכל מסמך: comments [{id, author, date, text, anchored_text}], tracked {ins, del, moveFrom, moveTo},
track_revisions_on, sha256.

מספור אוטומטי של Word (w:numPr בפסקה או בסגנון שלה, ו-word/numbering.xml): המספר אינו חלק מהטקסט בקובץ, אבל
הוא חלק ממה שהקורא רואה ("5.2", "א.", "(ג)"). Numbering משחזר אותו לפי הרמות של abstractNum (start, numFmt,
lvlText, isLgl, lvlRestart), עם startOverride ו-lvlOverride של num, ובכל סוגי המספור הנפוצים: decimal, אותיות
לטיניות, ספרות רומיות, hebrew1 (גימטריה: א, ב... י, יא, טו, טז) ו-hebrew2 (סדר האלף-בית). התווית נכנסת לתחילת
הנוסח של הפסקה ("5.2 הספק..."), בשני הנוסחים, כמו שהיא מוצגת במסמך, וכך גם מספר סעיף שנוצר אוטומטית נמצא
בחילוץ ובבדיקת הציטוטים. תבליט אינו מספר, ואינו נוסף.

הערות 3.6 (סבב 3): מסמך PDF (הסכם חתום שנסרק עם שכבת טקסט, נספח או מחירון שנמסרו כ-PDF) נחלץ גם הוא, לחלק
"pdf/page-<N>", פסקה לכל פסקה (שורות מורכבות לפסקה, _pdf_paragraphs), עם "קבל הכול" ו"דחה הכול" זהים (אין מעקב שינויים ב-PDF), כדי שציטוט ממנו
ייבדק כמו ציטוט מ-Word. PDF בלי שכבת טקסט (סריקה): no_text_layer: true, ואין פסקאות; הרכיב מבקש עותק Word
או מציין זאת בפרק 5. שכבת הטקסט: risk/page_text.py.

שימוש: python3 -B extract_corpus.py --out <out.json> <doc1.docx|doc1.pdf> [doc2 ...]
       (גרסה 1.2.0: --out מפורש וחובה, עם סיומת .json; פלט לעולם אינו נכתב על קובץ קלט או בתיקיית מקור
       של הלקוח, common/cli.py. out.json לתיקייה זמנית בלבד, לעולם לא לתיקיית הלקוח)
       קובץ קלט שלא נמצא: הודעה וקוד יציאה 1. נתיב ארוך מ-260 תווים נקרא דרך common/paths.long_path.
תלויות: ספרייה סטנדרטית + lxml.
"""
import hashlib
import io
import json
import os
import re
import sys
import zipfile

if __name__ == '__main__':
    sys.dont_write_bytecode = True   # הרצה משורת הפקודה אינה כותבת __pycache__ לתוך החבילה
    for _s in (sys.stdout, sys.stderr):  # עברית בקונסולה שאינה UTF-8 (cp1252): בלי UnicodeEncodeError
        try:
            _s.reconfigure(encoding='utf-8', errors='replace')
        except (AttributeError, ValueError):
            pass

from lxml import etree

try:
    from .page_text import PdfTextUnavailable, is_pdf, pdf_text
except ImportError:  # pragma: no cover
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from page_text import PdfTextUnavailable, is_pdf, pdf_text
try:
    from common.cli import DOCX_BAD_EXIT, OutputRefused, docx_problem, guard_out, parser, run, utf8_stdio
    from common.paths import long_path
except ImportError:  # pragma: no cover
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from common.cli import DOCX_BAD_EXIT, OutputRefused, docx_problem, guard_out, parser, run, utf8_stdio
    from common.paths import long_path

W = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
NS = {'w': W}


def q(tag):
    return '{%s}%s' % (W, tag)


# Strict Open XML (ISO 29500 Strict): אותו מבנה, במרחבי שמות אחרים. בלי נרמול, q('p') אינו מוצא אף פסקה, והמסמך
# נקרא כריק (ובחילוץ של הבונה נבלע כ"כפילות" של כל מסמך ריק אחר). הנרמול מחליף את מרחבי השמות לאלה של Transitional
STRICT_NS = (
    (b'http://purl.oclc.org/ooxml/wordprocessingml/main', W.encode()),
    (b'http://purl.oclc.org/ooxml/officeDocument/relationships',
     b'http://schemas.openxmlformats.org/officeDocument/2006/relationships'),
    (b'http://purl.oclc.org/ooxml/officeDocument/math', b'http://schemas.openxmlformats.org/officeDocument/2006/math'),
    (b'http://purl.oclc.org/ooxml/drawingml/wordprocessingDrawing',
     b'http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing'),
    (b'http://purl.oclc.org/ooxml/drawingml/main', b'http://schemas.openxmlformats.org/drawingml/2006/main'),
)


def is_strict(data):
    return STRICT_NS[0][0] in data


def normalize_strict(data):
    """XML של Strict במרחבי השמות של Transitional; XML אחר חוזר כמו שהוא."""
    if not is_strict(data):
        return data
    for a, b in STRICT_NS:
        data = data.replace(a, b)
    return data


class OoxmlZip(object):
    """עוטף ZipFile: read() מחזיר XML של Strict מנורמל. strict: האם נמצא חלק כזה. פתיחת מסמך גם טוענת את
    המספור האוטומטי שלו (Numbering), כדי ש-para_texts יוסיף את התווית לפסקאות ממוספרות של אותו מסמך."""

    def __init__(self, z):
        self.z, self.strict = z, False
        global _NUMBERING
        try:
            _NUMBERING = Numbering(self)
        except Exception:  # noqa: BLE001  מספור פגום אינו מפיל את החילוץ: הטקסט נקרא בלי המספרים
            _NUMBERING = None

    def namelist(self):
        return self.z.namelist()

    def read(self, name):
        data = self.z.read(name)
        if name.endswith('.xml') and is_strict(data):
            self.strict = True
            return normalize_strict(data)
        return data


# ---- מספור אוטומטי ----
_NUMBERING = None
HEB_UNITS = 'אבגדהוזחט'
HEB_TENS = 'יכלמנסעפצ'
HEB_HUNDREDS = ('ק', 'ר', 'ש', 'ת', 'תק', 'תר', 'תש', 'תת', 'תתק')
HEB_ALPHABET = 'אבגדהוזחטיכלמנסעפצקרשת'


def _hebrew1(n):
    """גימטריה, כמו hebrew1 של Word: 1-9 א-ט, 10 י, 11 יא, 15 טו, 16 טז, 20 כ, 100 ק."""
    if n <= 0:
        return str(n)
    out = ''
    if n >= 100:
        out += HEB_HUNDREDS[min(n // 100, 9) - 1]
        n %= 100
    if n in (15, 16):
        return out + ('טו' if n == 15 else 'טז')
    if n >= 10:
        out += HEB_TENS[n // 10 - 1]
        n %= 10
    if n:
        out += HEB_UNITS[n - 1]
    return out


def _hebrew2(n):
    """סדר האלף-בית, כמו hebrew2 של Word: 1-22 א-ת, ואחר כך האות חוזרת (23 אא)."""
    if n <= 0:
        return str(n)
    k, r = divmod(n - 1, 22)
    return HEB_ALPHABET[r] * (k + 1)


def _roman(n):
    vals = ((1000, 'M'), (900, 'CM'), (500, 'D'), (400, 'CD'), (100, 'C'), (90, 'XC'), (50, 'L'), (40, 'XL'),
            (10, 'X'), (9, 'IX'), (5, 'V'), (4, 'IV'), (1, 'I'))
    out = ''
    for v, s in vals:
        while n >= v:
            out, n = out + s, n - v
    return out or str(n)


def _letters(n):
    out = ''
    while n > 0:
        n, r = divmod(n - 1, 26)
        out = chr(65 + r) + out
    return out


def fmt_number(n, fmt):
    """מספר בתבנית של Word (numFmt). תבנית לא מוכרת: ספרות."""
    f = (fmt or 'decimal')
    if f in ('decimal', 'decimalEnclosedParen', 'decimalEnclosedFullstop', 'decimalHalfWidth', 'decimalFullWidth'):
        return str(n)
    if f == 'decimalZero':
        return '%02d' % n
    if f == 'lowerLetter':
        return _letters(n).lower()
    if f == 'upperLetter':
        return _letters(n)
    if f == 'lowerRoman':
        return _roman(n).lower()
    if f == 'upperRoman':
        return _roman(n)
    if f == 'hebrew1':
        return _hebrew1(n)
    if f == 'hebrew2':
        return _hebrew2(n)
    if f in ('none', 'bullet'):
        return ''
    return str(n)


class Numbering(object):
    """המספור האוטומטי של מסמך אחד. label(p) מחזיר את התווית של פסקה ממוספרת ומקדם את המונים, לפי סדר הקריאה;
    פסקה שכבר חושבה מחזירה את אותה תווית (אין קידום כפול)."""

    def __init__(self, z):
        self.abstract, self.nums, self.styles = {}, {}, {}
        self.counters, self.done = {}, {}
        names = z.namelist()
        if 'word/numbering.xml' in names:
            x = etree.fromstring(z.read('word/numbering.xml'))
            for an in x.findall('w:abstractNum', NS):
                self.abstract[an.get(q('abstractNumId'))] = self._levels(an)
            for num in x.findall('w:num', NS):
                ref = num.find('w:abstractNumId', NS)
                over = {}
                for lo in num.findall('w:lvlOverride', NS):
                    il = int(lo.get(q('ilvl')) or 0)
                    so = lo.find('w:startOverride', NS)
                    lv = lo.find('w:lvl', NS)
                    over[il] = {'start': int(so.get(q('val'))) if so is not None else None,
                                'lvl': self._level(lv) if lv is not None else None}
                self.nums[num.get(q('numId'))] = (ref.get(q('val')) if ref is not None else None, over)
        if 'word/styles.xml' in names:
            sx = etree.fromstring(z.read('word/styles.xml'))
            for st in sx.findall('w:style', NS):
                sid = st.get(q('styleId'))
                based = st.find('w:basedOn', NS)
                np_ = st.find('w:pPr/w:numPr', NS)
                self.styles[sid] = (based.get(q('val')) if based is not None else None,
                                    self._numpr(np_) if np_ is not None else None)

    @staticmethod
    def _level(lv):
        def val(tag, default=None):
            el = lv.find('w:' + tag, NS)
            return el.get(q('val')) if el is not None and el.get(q('val')) is not None else default
        start = val('start', '1')
        restart = val('lvlRestart')
        return {'start': int(start) if str(start).lstrip('-').isdigit() else 1, 'fmt': val('numFmt', 'decimal'),
                'text': val('lvlText', ''), 'lgl': lv.find('w:isLgl', NS) is not None,
                'restart': int(restart) if restart is not None and str(restart).isdigit() else None}

    def _levels(self, an):
        return {int(lv.get(q('ilvl')) or 0): self._level(lv) for lv in an.findall('w:lvl', NS)}

    @staticmethod
    def _numpr(np_):
        il, ni = np_.find('w:ilvl', NS), np_.find('w:numId', NS)
        return (ni.get(q('val')) if ni is not None else None, int(il.get(q('val'))) if il is not None else None)

    def _style_numpr(self, sid, seen=None):
        seen = seen or set()
        while sid and sid not in seen:
            seen.add(sid)
            based, np_ = self.styles.get(sid, (None, None))
            if np_ and np_[0]:
                return np_
            sid = based
        return None

    def _resolve(self, p):
        ppr = p.find('w:pPr', NS)
        num_id, ilvl = None, None
        if ppr is not None:
            np_ = ppr.find('w:numPr', NS)
            if np_ is not None:
                num_id, ilvl = self._numpr(np_)
            st = ppr.find('w:pStyle', NS)
            if st is not None and (num_id is None or ilvl is None):
                snp = self._style_numpr(st.get(q('val')))
                if snp:
                    num_id = num_id if num_id is not None else snp[0]
                    ilvl = ilvl if ilvl is not None else snp[1]
        if not num_id or num_id == '0' or num_id not in self.nums:
            return None
        return num_id, (ilvl or 0)

    def _lvl(self, num_id, il):
        ref, over = self.nums[num_id]
        o = over.get(il) or {}
        lv = dict(o.get('lvl') or (self.abstract.get(ref) or {}).get(il) or {'start': 1, 'fmt': 'decimal',
                                                                            'text': '%%%d.' % (il + 1),
                                                                            'lgl': False, 'restart': None})
        if o.get('start') is not None:
            lv['start'] = o['start']
        return lv

    def label(self, p):
        key = id(p)
        if key in self.done:
            return self.done[key][1]
        r = self._resolve(p)
        if r is None:
            self.done[key] = (p, '')
            return ''
        num_id, il = r
        cnt = self.counters.setdefault(num_id, {})
        lv = self._lvl(num_id, il)
        cnt[il] = cnt[il] + 1 if il in cnt else lv['start']
        for deeper in [k for k in cnt if k > il]:
            rs = self._lvl(num_id, deeper).get('restart')
            if rs is None or (rs != 0 and il + 1 <= rs):   # lvlRestart 0: אינה מתחילה מחדש
                del cnt[deeper]
        if lv['fmt'] in ('bullet', 'none'):
            self.done[key] = (p, '')
            return ''

        def part(m):
            k = int(m.group(1)) - 1
            if k > il:
                return ''
            v = cnt.get(k, self._lvl(num_id, k)['start'])
            return fmt_number(v, 'decimal' if lv['lgl'] else self._lvl(num_id, k)['fmt'])
        out = re.sub(r'%([1-9])', part, lv['text'] or '').strip()
        self.done[key] = (p, out)
        return out


PARTS_RE = re.compile(r'^word/(document|header\d*|footer\d*|footnotes|endnotes)\.xml$')
INS_TAGS = (q('ins'), q('moveTo'))
DEL_TAGS = (q('del'), q('moveFrom'))
TEXT_TAGS = (q('t'), q('delText'), q('instrText'))


def _is_near_white(val):
    val = (val or '').strip().upper()
    if val in ('', 'AUTO'):
        return False
    if not re.match(r'^[0-9A-F]{6}$', val):
        return False
    r, g, b = int(val[0:2], 16), int(val[2:4], 16), int(val[4:6], 16)
    return min(r, g, b) >= 0xF0


def run_hidden(run):
    """אופן ההסתרה של ריצה, או None. sz בחצאי נקודות: פחות מ-8 = פחות מ-4 נקודות."""
    rpr = run.find('w:rPr', NS)
    if rpr is None:
        return None
    for tag in ('vanish', 'specVanish', 'webHidden'):
        el = rpr.find('w:' + tag, NS)
        if el is not None and el.get(q('val'), 'true') not in ('0', 'false', 'off'):
            return tag
    c = rpr.find('w:color', NS)
    if c is not None and _is_near_white(c.get(q('val'))):
        return 'color'
    for tag in ('sz', 'szCs'):
        sz = rpr.find('w:' + tag, NS)
        if sz is not None:
            try:
                if int(sz.get(q('val'))) < 8:
                    return 'font_size'
            except (TypeError, ValueError):
                pass
    return None


def _own_paragraph(el, p):
    """האם el שייך לפסקה p עצמה ולא לפסקה מקוננת (תיבת טקסט) בתוכה."""
    a = el.getparent()
    while a is not None and a is not p:
        if a.tag == q('p'):
            return False
        a = a.getparent()
    return True


def _flags(el, p):
    ins = dele = False
    a = el.getparent()
    while a is not None and a is not p:
        if a.tag in INS_TAGS:
            ins = True
        elif a.tag in DEL_TAGS:
            dele = True
        a = a.getparent()
    return ins, dele


def para_texts(p):
    acc, rej, hidden = [], [], []
    for el in p.iter():
        tag = el.tag
        if tag not in TEXT_TAGS and tag not in (q('tab'), q('br'), q('cr'), q('noBreakHyphen')):
            continue
        if not _own_paragraph(el, p):
            continue
        if tag == q('instrText'):
            continue  # קוד שדה (HYPERLINK, PAGE) אינו טקסט של ההסכם
        if tag in TEXT_TAGS:
            txt = el.text or ''
        elif tag == q('tab'):
            txt = ' '
        elif tag == q('noBreakHyphen'):
            txt = '-'
        else:
            txt = '\n'
        ins, dele = _flags(el, p)
        if tag == q('delText'):
            dele = True
        if not dele:
            acc.append(txt)
        if not ins:
            rej.append(txt)
        run = el.getparent()
        while run is not None and run.tag != q('r'):
            run = run.getparent()
        if run is not None and txt.strip():
            how = run_hidden(run)
            if how:
                hidden.append({'how': how, 'text': txt})
    norm = lambda parts: re.sub(r'[ \t ]+', ' ', ''.join(parts)).strip()
    # מספור אוטומטי: התווית ("5.2", "א.") בתחילת שני הנוסחים, כמו שהיא מוצגת במסמך
    lab = _NUMBERING.label(p) if _NUMBERING is not None and p.tag == q('p') else ''
    if lab:
        if ''.join(acc).strip():
            acc = [lab + ' '] + acc
        if ''.join(rej).strip():
            rej = [lab + ' '] + rej
    # איחוד ריצות מוסתרות רצופות לקטע אחד לכל אופן הסתרה
    merged = []
    for h in hidden:
        if merged and merged[-1]['how'] == h['how']:
            merged[-1]['text'] += h['text']
        else:
            merged.append(dict(h))
    return norm(acc), norm(rej), merged


def para_changes(p):
    """קטעי השינויים במעקב של הפסקה, לפי הסדר: [{'kind': 'ins' | 'del', 'text', 'author'?}]. ריצות רצופות מאותו
    סוג מאוחדות לקטע אחד, והרווחים המקוריים נשמרים כלשונם (ולא נדבקים): כך שחזור של נוסח שנמחק נעשה מהקטע
    עצמו ולא מהדבקת יחידות. מכאן נגזר סיווג הראיה של ציטוט (ev_kind: תוספת של החברה, מחיקה של החברה, נוסח
    של הצד שכנגד שלא שונה) בבונה הפלייבוק. ריק כשאין בפסקה שינויים במעקב."""
    out = []
    for el in p.iter():
        tag = el.tag
        if tag not in TEXT_TAGS and tag not in (q('tab'), q('br'), q('cr'), q('noBreakHyphen')):
            continue
        if not _own_paragraph(el, p) or tag == q('instrText'):
            continue
        ins, dele = _flags(el, p)
        if tag == q('delText'):
            dele = True
        if not (ins or dele):
            continue
        txt = (el.text or '') if tag in TEXT_TAGS else (' ' if tag == q('tab') else '-' if tag == q('noBreakHyphen') else '\n')
        kind = 'del' if dele else 'ins'
        author = ''
        a = el.getparent()
        while a is not None and a is not p:
            if a.tag in INS_TAGS or a.tag in DEL_TAGS:
                author = a.get(q('author')) or ''
                break
            a = a.getparent()
        if out and out[-1]['kind'] == kind and out[-1].get('author', '') == author:
            out[-1]['text'] += txt
        else:
            seg = {'kind': kind, 'text': txt}
            if author:
                seg['author'] = author
            out.append(seg)
    return [s for s in out if s['text'].strip()]


def comments_of(z):
    out = {}
    if 'word/comments.xml' not in z.namelist():
        return out
    x = etree.fromstring(z.read('word/comments.xml'))
    for c in x.findall('w:comment', NS):
        cid = c.get(q('id'))
        text = ' '.join(''.join(t.text or '' for t in pp.iter(q('t'))) for pp in c.findall('.//w:p', NS)).strip()
        out[cid] = {'id': cid, 'author': c.get(q('author')), 'date': c.get(q('date')), 'text': text,
                    'anchored_text': '', 'part': None}
    return out


def anchored_ranges(x):
    """הטקסט שבין commentRangeStart ל-commentRangeEnd, בנוסח "קבל הכול"."""
    res, open_ = {}, {}
    for el in x.iter():
        if el.tag == q('commentRangeStart'):
            open_[el.get(q('id'))] = []
        elif el.tag == q('commentRangeEnd'):
            i = el.get(q('id'))
            if i in open_:
                res[i] = re.sub(r'\s+', ' ', ''.join(open_.pop(i))).strip()
        elif el.tag == q('t'):
            for v in open_.values():
                v.append(el.text or '')
    return res


# הרכבת פסקאות מ-PDF. PyMuPDF מחזיר "שורה" לכל קטע בשורה החזותית, בסדר לוגי (גם בעברית), ולכן get_text()
# פירק פסקה עברית לשברי מילים ("ל" / "הסכם") ומספר סעיף יצא בשורה משלו. כאן: קטעים באותו גובה הם שורה אחת,
# מחוברים כמו שהם (הרווחים בתוך הקטעים), ושורות מתחברות לפסקה עד מרווח אנכי, תחילת סעיף, או סוף משפט בשורה
# קצרה. מספר סעיף שעומד לבד מוצמד לשורה שאחריו.
PDF_CLAUSE_START = re.compile(r'^\s*(?:\(?\d{1,3}(?:\.\d{1,3})*\)?[.)]?(?=\s|$)|\(?\d{1,3}(?:\.\d{1,3})+\)?'
                              r'|\([א-תa-zA-Z]{1,4}\)|[א-ת][.)](?=\s)|(?i:section|clause|article)\s+\d|[•●▪◦\-]\s)')
PDF_CLAUSE_ONLY = re.compile(r'^\s*\(?(?:\d+(?:\.\d+)*|[א-ת]|[a-zA-Z]|[ivxIVX]{1,6})\)?[.)]?\s*$')
PDF_SENTENCE_END = re.compile(r'[.:;!?״"”)]\s*$')


def _pdf_rows(page):
    """השורות החזותיות של עמוד, לפי הסדר: [(טקסט, x0, y0, x1, y1)]. קטעים באותו בלוק ובאותו גובה הם שורה אחת."""
    rows = []
    for b in page.get_text('dict').get('blocks', []):
        if b.get('type') != 0:
            continue
        cur = None
        for ln in b.get('lines', []):
            t = ''.join(s.get('text', '') for s in ln.get('spans', []))
            x0, y0, x1, y1 = ln['bbox']
            if cur and min(y1, cur[4]) - max(y0, cur[2]) > 0.5 * min(y1 - y0, cur[4] - cur[2]):
                # אותה שורה חזותית: רווח רק כשיש פער אופקי ואין רווח בגבול
                gap = max(x0, cur[1]) - min(x1, cur[3])
                h = max(1.0, y1 - y0)
                sep = ' ' if gap > 0.25 * h and t[:1].strip() and cur[0][-1:].strip() else ''
                cur = [cur[0] + sep + t, min(x0, cur[1]), min(y0, cur[2]), max(x1, cur[3]), max(y1, cur[4])]
            else:
                if cur:
                    rows.append(cur)
                cur = [t, x0, y0, x1, y1]
        if cur:
            rows.append(cur)
    return [(re.sub(r'[ \t ]+', ' ', r[0]).strip(),) + tuple(r[1:]) for r in rows
            if r[0].strip()]


def _pdf_paragraphs(rows):
    """מחבר שורות חזותיות לפסקאות. פסקה חדשה: מרווח אנכי גדול מהמרווח הרגיל בין שורות בעמוד, שורה שנפתחת
    במספר סעיף, או שורה קודמת קצרה שמסתיימת בסוף משפט. מספר סעיף שעומד לבד מוצמד לשורה שאחריו."""
    if not rows:
        return []
    left, right = min(r[1] for r in rows), max(r[3] for r in rows)
    width = max(1.0, right - left)
    # המרווח הרגיל בין שורות באותה פסקה: הרבעון התחתון של המרווחים החיוביים בעמוד (מסמך ברווח שורה וחצי
    # אינו נחתך בכל שורה, ומרווח בין פסקאות עדיין גדול ממנו)
    gaps = sorted(b[2] - a[4] for a, b in zip(rows, rows[1:]) if 0 <= b[2] - a[4] < 2 * (b[4] - b[2]))
    line_gap = gaps[len(gaps) // 4] if gaps else 0.0
    paras, cur, prev = [], None, None
    for r in rows:
        t, x0, y0, x1, y1 = r
        if cur is None:
            cur, prev = [t], r
            continue
        h = max(1.0, min(y1 - y0, prev[4] - prev[2]))
        gap = y0 - prev[4]
        para_gap = max(0.5 * h, line_gap + 0.35 * h)
        lone_num = PDF_CLAUSE_ONLY.match(prev[0]) and len(cur) == 1 and gap <= para_gap
        if lone_num:
            new = False
        elif gap > para_gap or gap < -0.5 * h or PDF_CLAUSE_START.match(t):
            new = True
        else:
            short = (prev[3] - prev[1]) < 0.8 * width
            new = bool(short and PDF_SENTENCE_END.search(prev[0]))
        if new:
            paras.append(cur)
            cur = [t]
        else:
            cur.append(t)
        prev = r
    paras.append(cur)
    out = []
    for p in paras:
        s = p[0]
        for t in p[1:]:
            # מקף בסוף שורה אחרי אות (פיצול מילה באנגלית) מתחבר בלי רווח; אחרת רווח אחד
            s += t if re.search(r'[A-Za-z]-$', s) else ' ' + t
        out.append(re.sub(r'[ \t ]+', ' ', s).strip())
    return out


def _pdf_pages(raw):
    """פסקאות לכל עמוד: עם PyMuPDF, לפי עמוד ובהרכבת שורות לפסקאות; אחרת שכבת הטקסט כולה כעמוד אחד, שורה
    לפסקה."""
    try:
        try:
            import pymupdf as fitz
        except ImportError:
            import fitz  # type: ignore
        doc = fitz.open(stream=raw, filetype='pdf')
        pages = [_pdf_paragraphs(_pdf_rows(p)) for p in doc]
        doc.close()
        if any(pages):
            return pages
    except ImportError:
        pass
    return [[t for t in (re.sub(r'[ \t ]+', ' ', ln).strip() for ln in pdf_text(raw).splitlines()) if t]]


def extract_pdf(path, raw):
    doc = {'file': os.path.basename(path), 'sha256': hashlib.sha256(raw).hexdigest(), 'parts': {},
           'tracked': {'ins': 0, 'del': 0, 'moveFrom': 0, 'moveTo': 0}, 'format': 'pdf',
           'track_revisions_on': False, 'comments': [], 'hidden_total': 0}
    try:
        pages = _pdf_pages(raw)
    except PdfTextUnavailable as e:
        # "אין ספרייה" אינו "סריקה": PDF עם שכבת טקסט סומן כסרוק כשלא הותקנה
        # ספריית PDF, והרכיב ביקש מהלקוח עותק Word בלי צורך. תיקון מקומי של
        # ניל, דווח
        if str(e).startswith('אין ספרייה'):
            doc['unreadable_reason'] = str(e)
        else:
            doc['no_text_layer'] = True
        return doc
    i = 0
    for n, texts in enumerate(pages, 1):
        paras = []
        for t in texts:
            if t:
                paras.append({'i': i, 'style': '', 'text_accept_all': t, 'text_reject_all': t, 'hidden': []})
                i += 1
        doc['parts']['pdf/page-%d' % n] = paras
    if not i:
        doc['no_text_layer'] = True
    return doc


def extract(path):
    # נתיב ארוך מ-260 תווים ב-Windows נפתח רק דרך long_path (קידומת \\?\); השם בפלט נשאר basename
    with open(long_path(path), 'rb') as fh:
        raw = fh.read()
    if is_pdf(raw):
        return extract_pdf(path, raw)
    z = OoxmlZip(zipfile.ZipFile(io.BytesIO(raw)))
    names = z.namelist()
    parts = sorted((n for n in names if PARTS_RE.match(n)), key=lambda n: (n != 'word/document.xml', n))
    doc = {'file': os.path.basename(path), 'sha256': hashlib.sha256(raw).hexdigest(), 'parts': {},
           'tracked': {'ins': 0, 'del': 0, 'moveFrom': 0, 'moveTo': 0}}
    cm = comments_of(z)
    for part in parts:
        x = etree.fromstring(z.read(part))
        for k in doc['tracked']:
            doc['tracked'][k] += len(x.findall('.//w:' + k, NS))
        paras = []
        for i, p in enumerate(x.iter(q('p'))):
            a, r, h = para_texts(p)
            if not a and not r and not h:
                continue
            ppr = p.find('w:pPr', NS)
            style = ''
            if ppr is not None and ppr.find('w:pStyle', NS) is not None:
                style = ppr.find('w:pStyle', NS).get(q('val')) or ''
            in_tb = any(anc.tag == q('txbxContent') for anc in p.iterancestors())
            rec = {'i': i, 'style': style, 'text_accept_all': a, 'text_reject_all': r, 'hidden': h}
            if in_tb:
                rec['in_textbox'] = True
            if a != r:
                rec['changed'] = True
            paras.append(rec)
        for k, v in anchored_ranges(x).items():
            if k in cm:
                cm[k]['anchored_text'] = v
                cm[k]['part'] = part
        doc['parts'][part] = paras
    settings = z.read('word/settings.xml').decode('utf-8', 'replace') if 'word/settings.xml' in names else ''
    doc['track_revisions_on'] = '<w:trackRevisions' in settings
    doc['comments'] = list(cm.values())
    doc['hidden_total'] = sum(len(p['hidden']) for ps in doc['parts'].values() for p in ps)
    if z.strict:
        doc['ooxml_strict'] = True
    if not any(doc['parts'].values()):
        # מסמך Word בלי אף פסקה עם טקסט (בדרך כלל סריקה שהודבקה כתמונה): כמו PDF סרוק
        doc['no_text_layer'] = True
    return doc


def body_text(doc, view='accept'):
    """כל הנוסח של המסמך בנוסח אחד, לבדיקת ציטוטים (validate_register)."""
    key = 'text_accept_all' if view == 'accept' else 'text_reject_all'
    return ' '.join(p[key] for ps in doc['parts'].values() for p in ps if p[key])


def reject_all_equals(doc_response, doc_received):
    """בדיקת שינוי שלא סומן (שינוי 15): "דחה הכול" של התגובה שלנו שווה מילה במילה לטיוטה שהתקבלה.
    מחזיר (equal, [אינדקסים של פסקאות שונות])."""
    a = [p['text_reject_all'] for p in doc_response['parts'].get('word/document.xml', []) if p['text_reject_all']]
    b = [p['text_accept_all'] for p in doc_received['parts'].get('word/document.xml', []) if p['text_accept_all']]
    norm = lambda s: re.sub(r'\s+', ' ', s).strip()
    diffs = [i for i, (x, y) in enumerate(zip(a, b)) if norm(x) != norm(y)]
    if len(a) != len(b):
        diffs.append(min(len(a), len(b)))
    return not diffs, diffs


def main(argv=None):
    """נקודת הכניסה. argv בלי שם התוכנית (כמו argparse). --out חובה, עם סיומת .json, ואינו קובץ קלט."""
    ap = parser('חילוץ Word ו-PDF לקובץ ביניים (JSON)', out_required=True)
    ap.add_argument('inputs', nargs='+', help='מסמכי Word או PDF לחילוץ (קריאה בלבד)')
    a = ap.parse_args(argv)
    if not a.out.lower().endswith('.json'):
        raise OutputRefused('--out חייב להסתיים ב-.json: %s' % a.out)
    out_path = guard_out(a.out, a.inputs)
    missing = [p for p in a.inputs if not os.path.isfile(long_path(p))]
    if missing:
        # קובץ שלא נמצא מדווח, ואינו מדולג בשקט ואינו נופל ב-traceback
        sys.stdout.reconfigure(encoding='utf-8')
        for p in missing:
            print('לא נמצא: %s (נתיב של %d תווים)' % (p, len(os.path.abspath(p))))
        return 1
    # DOC, קובץ מוצפן, ZIP פגום או קובץ בלי document.xml: הודעה דו-לשונית וקוד 2, ולא traceback (Strict נקרא)
    bad = []
    for p in a.inputs:
        with open(long_path(p), 'rb') as fh:
            pdf = is_pdf(fh.read(1024))
        found = None if pdf else docx_problem(p, strict_ok=True)
        if found:
            bad.append(found[1])
    if bad:
        utf8_stdio()
        print('\n'.join(bad))
        return DOCX_BAD_EXIT
    out = [extract(p) for p in a.inputs]
    with open(out_path, 'w', encoding='utf-8') as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
    sys.stdout.reconfigure(encoding='utf-8')
    for d in out:
        t = d['tracked']
        print('%s ins=%d del=%d comments=%d hidden=%d parts=%d' % (
            d['file'], t['ins'], t['del'], len(d['comments']), d['hidden_total'], len(d['parts'])))
    return 0


if __name__ == '__main__':
    sys.exit(run(main))
