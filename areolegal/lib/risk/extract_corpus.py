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

הערות 3.6 (סבב 3): מסמך PDF (הסכם חתום שנסרק עם שכבת טקסט, נספח או מחירון שנמסרו כ-PDF) נחלץ גם הוא, לחלק
"pdf/page-<N>", פסקה לכל שורה, עם "קבל הכול" ו"דחה הכול" זהים (אין מעקב שינויים ב-PDF), כדי שציטוט ממנו
ייבדק כמו ציטוט מ-Word. PDF בלי שכבת טקסט (סריקה): no_text_layer: true, ואין פסקאות; הרכיב מבקש עותק Word
או מציין זאת בפרק 5. שכבת הטקסט: risk/page_text.py.

שימוש: python -I extract_corpus.py --out <out.json> <doc1.docx|doc1.pdf> [doc2 ...]
       (גרסה 1.2.0: --out מפורש וחובה, עם סיומת .json; פלט לעולם אינו נכתב על קובץ קלט או בתיקיית מקור
       של הלקוח, common/cli.py. out.json לתיקייה זמנית בלבד, לעולם לא לתיקיית הלקוח)
תלויות: ספרייה סטנדרטית + lxml.
"""
import hashlib
import json
import os
import re
import sys
import zipfile

if __name__ == '__main__':
    sys.dont_write_bytecode = True   # הרצה משורת הפקודה אינה כותבת __pycache__ לתוך החבילה

from lxml import etree

try:
    from .page_text import PdfTextUnavailable, is_pdf, pdf_text
except ImportError:  # pragma: no cover
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from page_text import PdfTextUnavailable, is_pdf, pdf_text
try:
    from common.cli import OutputRefused, guard_out, parser, run
except ImportError:  # pragma: no cover
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from common.cli import OutputRefused, guard_out, parser, run

W = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
NS = {'w': W}


def q(tag):
    return '{%s}%s' % (W, tag)


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
    # איחוד ריצות מוסתרות רצופות לקטע אחד לכל אופן הסתרה
    merged = []
    for h in hidden:
        if merged and merged[-1]['how'] == h['how']:
            merged[-1]['text'] += h['text']
        else:
            merged.append(dict(h))
    return norm(acc), norm(rej), merged


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


def _pdf_pages(raw):
    """טקסט לכל עמוד: PyMuPDF לפי עמוד כשמותקן, אחרת שכבת הטקסט כולה כעמוד אחד."""
    try:
        try:
            import pymupdf as fitz
        except ImportError:
            import fitz  # type: ignore
        doc = fitz.open(stream=raw, filetype='pdf')
        pages = [p.get_text() for p in doc]
        doc.close()
        if any(x.strip() for x in pages):
            return pages
    except ImportError:
        pass
    return [pdf_text(raw)]


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
    for n, txt in enumerate(pages, 1):
        paras = []
        for line in txt.splitlines():
            t = re.sub(r'[ 	 ]+', ' ', line).strip()
            if t:
                paras.append({'i': i, 'style': '', 'text_accept_all': t, 'text_reject_all': t, 'hidden': []})
                i += 1
        doc['parts']['pdf/page-%d' % n] = paras
    if not i:
        doc['no_text_layer'] = True
    return doc


def extract(path):
    with open(path, 'rb') as fh:
        raw = fh.read()
    if is_pdf(raw):
        return extract_pdf(path, raw)
    z = zipfile.ZipFile(path)
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
