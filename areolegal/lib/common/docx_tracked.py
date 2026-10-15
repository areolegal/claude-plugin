# -*- coding: utf-8 -*-
"""מנוע עקוב אחר שינויים כירורגי, אחד לכל הרכיבים (מימוש ייחוס, הערות הנושא ונותן 4.8, שינויים 76 ו-77;
4.9, שינויים 84 ו-86: כל שינוי עם בועה חיצונית, ונייר באנגלית כנייר מלא).

מאחד את שלושת המנועים של ההדמיות בסבב 2 (c1b/engine.py, c1run/engine.py, build_response.py) ואת הבדיקות
העצמאיות של מהנדס הסקילים (rev2eng) למנוע אחד:

- עריכה ברמת המילה, עם עידון לאות כשרוב המילה נשמר, ומספר, סכום או סוגריים מרובעים כיחידה אחת.
- החלפת טווח (replace_span), נוסח יעד מלא לפסקה (set_text), הוספת פסקה ומחיקת פסקה עם סימן הפסקה,
  ובועה בלבד (comment_only). כמה הכרעות על אותה פסקה מאוחדות לסימון אחד.
- בועות חיצוניות במחבר עורך הדין ובראשי התיבות מהפרופיל, ובועות פנימיות במחבר הקבוע INTERNAL_AUTHOR.
- w:trackRevisions במקומו לפי סדר הסכמה של settings.xml, ובלי w:trackChanges.
- תאריך אמיתי: w:date הוא השעה המקומית בתבנית YYYY-MM-DDTHH:MM:SSZ (כמו ש-Word כותב), ו-w16du:dateUtc
  הוא UTC אמיתי. השעון מתקדם בשנייה לכל הכרעה, כך שהשינויים אינם נושאים כולם אותה שנייה.
- בלי w:highlight בטקסט שהוכנס; rPr מועתק מהריצה הסמוכה ומפוצל לפי כתב. בפסקה מימין לשמאל: עברית, פיסוק
  וספרות עם w:rtl, וקטע לטיני בלי. בפסקה משמאל לימין (נייר באנגלית, בלי w:bidi): רק קטע שיש בו אות עברית
  מקבל w:rtl, ופיסוק, ספרות ומרכאות נשארים LTR (4.9, שינוי 86).
- בועה בעברית נכתבת עם w:bidi; בועה שרובה לטינית נכתבת בלי w:bidi ובלי w:rtl על ריצות בלי עברית.
- כל הצהרות מרחבי השמות של המסמך נשמרות, וכל קידומת שב-mc:Ignorable מוצהרת (בסבב 2 ניקוי מרחבי
  השמות מחק את w14 ו-wp14, ו-Word דחה את הקובץ כפגום).
- פסקה אחרונה: מחיקה שלה מוחקת את סימן הפסקה שלפניה, והוספה אחריה מסמנת את סימן הפסקה שלה, כמו ש-Word
  עושה, כך שאחרי "קבל הכול" אין פסקה ריקה בסוף ההסכם.
- כותרת פנימית בקובץ העבודה, ועותק למשלוח (strip_internal) בלי בועות פנימיות ובלי הכותרת.
- הטלה של "קבל הכול" ושל "דחה הכול" לרשימת פסקאות, ו-verify_roundtrip מול הטיוטה שהתקבלה ומול נוסחי היעד.

תלות: Python 3, lxml. אין שימוש ב-python-docx כאן (הוא נשאר לבדיקות ולרכיבים אחרים).
"""
import copy
import datetime as _dt
import difflib
import io
import re
import zipfile

from lxml import etree

W_NS = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
R_NS = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
MC_NS = 'http://schemas.openxmlformats.org/markup-compatibility/2006'
W16DU_NS = 'http://schemas.microsoft.com/office/word/2023/wordml/word16du'
PKG_REL_NS = 'http://schemas.openxmlformats.org/package/2006/relationships'
CT_NS = 'http://schemas.openxmlformats.org/package/2006/content-types'
W = '{%s}' % W_NS
XML_SPACE = '{http://www.w3.org/XML/1998/namespace}space'
DATE_UTC_ATTR = '{%s}dateUtc' % W16DU_NS
MC_IGNORABLE = '{%s}Ignorable' % MC_NS

INTERNAL_AUTHOR = 'פנימי, למחיקה לפני המשלוח'
INTERNAL_INITIALS = 'פנ'
INTERNAL_HEADER_TEXT = 'טיוטת עבודה פנימית, לא למשלוח'
INTERNAL_HEADER_PART = 'word/headerInternal.xml'
INTERNAL_REL_PREFIX = 'rIdInt'
COMMENTS_PART = 'word/comments.xml'
REL_TYPE = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships/'
CT_COMMENTS = 'application/vnd.openxmlformats-officedocument.wordprocessingml.comments+xml'
CT_HEADER = 'application/vnd.openxmlformats-officedocument.wordprocessingml.header+xml'
DATE_FMT = '%Y-%m-%dT%H:%M:%SZ'


class UnsupportedEdit(Exception):
    """ההכרעה אינה ניתנת לסימון כירורגי בפסקה הזו. הכרעה כזו מדווחת "לא סומנה" ואינה מוחלת."""


# --------------------------------------------------------------------------------------- סדר סכמה
ORDER_PPR = ("pStyle", "keepNext", "keepLines", "pageBreakBefore", "framePr", "widowControl", "numPr",
             "suppressLineNumbers", "pBdr", "shd", "tabs", "suppressAutoHyphens", "kinsoku", "wordWrap",
             "overflowPunct", "topLinePunct", "autoSpaceDE", "autoSpaceDN", "bidi", "adjustRightInd",
             "snapToGrid", "spacing", "ind", "contextualSpacing", "mirrorIndents", "suppressOverlap", "jc",
             "textDirection", "textAlignment", "textboxTightWrap", "outlineLvl", "divId", "cnfStyle", "rPr",
             "sectPr", "pPrChange")
ORDER_RPR = ("ins", "del", "moveFrom", "moveTo", "rStyle", "rFonts", "b", "bCs", "i", "iCs", "caps",
             "smallCaps", "strike", "dstrike", "outline", "shadow", "emboss", "imprint", "noProof", "snapToGrid",
             "vanish", "webHidden", "color", "spacing", "w", "kern", "position", "sz", "szCs", "highlight", "u",
             "effect", "bdr", "shd", "fitText", "vertAlign", "rtl", "cs", "em", "lang", "eastAsianLayout",
             "specVanish", "oMath", "rPrChange")
ORDER_SECTPR = ("headerReference", "footerReference", "footnotePr", "endnotePr", "type", "pgSz", "pgMar",
                "paperSrc", "pgBorders", "lnNumType", "pgNumType", "cols", "formProt", "vAlign", "noEndnote",
                "titlePg", "textDirection", "bidi", "rtlGutter", "docGrid", "printerSettings", "sectPrChange")
ORDER_TBLPR = ("tblStyle", "tblpPr", "tblOverlap", "bidiVisual", "tblStyleRowBandSize", "tblStyleColBandSize",
               "tblW", "jc", "tblCellSpacing", "tblInd", "tblBorders", "shd", "tblLayout", "tblCellMar",
               "tblLook", "tblCaption", "tblDescription", "tblPrChange")
ORDERS = {'pPr': ORDER_PPR, 'rPr': ORDER_RPR, 'sectPr': ORDER_SECTPR, 'tblPr': ORDER_TBLPR}
# ילדים של w:settings שבאים לפני trackRevisions לפי CT_Settings
SETTINGS_BEFORE_TRACK = ("writeProtection", "view", "zoom", "removePersonalInformation", "removeDateAndTime",
                         "doNotDisplayPageBoundaries", "displayBackgroundShape", "printPostScriptOverText",
                         "printFractionalCharacterWidth", "printFormsData", "embedTrueTypeFonts",
                         "embedSystemFonts", "saveSubsetFonts", "saveFormsData", "mirrorMargins",
                         "alignBordersAndEdges", "bordersDoNotSurroundHeader", "bordersDoNotSurroundFooter",
                         "gutterAtTop", "hideSpellingErrors", "hideGrammaticalErrors", "activeWritingStyle",
                         "proofState", "formsDesign", "attachedTemplate", "linkStyles", "stylePaneFormatFilter",
                         "stylePaneSortMethod", "documentType", "mailMerge", "revisionView")


def local(tag):
    return tag.split('}')[-1] if isinstance(tag, str) else ''


def fix_schema_order(root):
    """ממיין ילדי pPr, rPr, sectPr ו-tblPr לפי סדר הסכמה, בלי לשנות ערכים. מחזיר כמה מכלים תוקנו."""
    n = 0
    for name, order in ORDERS.items():
        for parent in root.iter(W + name):
            kids = list(parent)
            known = [k for k in kids if local(k.tag) in order]
            ranks = [order.index(local(k.tag)) for k in known]
            if ranks != sorted(ranks):
                unknown = [k for k in kids if local(k.tag) not in order]
                for k in kids:
                    parent.remove(k)
                for k in sorted(known, key=lambda k: order.index(local(k.tag))) + unknown:
                    parent.append(k)
                n += 1
    return n


def audit_schema_order(root):
    bad = 0
    for name, order in ORDERS.items():
        for parent in root.iter(W + name):
            ranks = [order.index(local(c.tag)) for c in parent if local(c.tag) in order]
            if ranks != sorted(ranks):
                bad += 1
    return bad


# --------------------------------------------------------------------------------------- שעון
class RevisionClock:
    """שעון ההכרעות. w:date הוא השעה המקומית עם Z (כמו ש-Word כותב), ו-dateUtc הוא UTC אמיתי.
    מתקדם בשנייה לכל tick, מנקודת התחלה שנקבעת כך שהשינוי האחרון אינו בעתיד."""

    def __init__(self, now=None, steps=0):
        now = now or _dt.datetime.now().astimezone()
        if now.tzinfo is None:
            now = now.astimezone()
        self.t = (now - _dt.timedelta(seconds=steps)).replace(microsecond=0)

    def stamp(self):
        loc = self.t.replace(tzinfo=None).strftime(DATE_FMT)
        utc = self.t.astimezone(_dt.timezone.utc).strftime(DATE_FMT)
        return loc, utc

    def tick(self):
        self.t += _dt.timedelta(seconds=1)


# --------------------------------------------------------------------------------------- טוקנים והבדל
TOK = re.compile(r'\[[^\]\n]*\]|\d[\d,./]*\d|\d|[A-Za-z]+|[֐-׿"\'׳״\-]+|\s+|.', re.S)


def tokens(s):
    return TOK.findall(s)


def char_ops(a, b):
    """הבדל ברמת המילה, עם עידון לאות כשרוב המילה נשמר. מספרים וסוגריים מרובעים הם יחידה אחת.
    מחזיר רשימה של (op, a0, a1, text) כש-op הוא equal / delete / insert, במיקומים של a."""
    ta, tb = tokens(a), tokens(b)
    pa, pb = [0], [0]
    for t in ta:
        pa.append(pa[-1] + len(t))
    for t in tb:
        pb.append(pb[-1] + len(t))
    out = []
    for op, i1, i2, j1, j2 in difflib.SequenceMatcher(None, ta, tb, autojunk=False).get_opcodes():
        a0, a1, b0, b1 = pa[i1], pa[i2], pb[j1], pb[j2]
        if op == 'equal':
            out.append(('equal', a0, a1, a[a0:a1]))
            continue
        if (op == 'replace' and i2 - i1 == 1 and j2 - j1 == 1 and not re.match(r'[\d\[]', ta[i1])
                and not re.match(r'[\d\[]', tb[j1]) and not ta[i1].isspace()):
            wa, wb = ta[i1], tb[j1]
            sm = difflib.SequenceMatcher(None, wa, wb, autojunk=False)
            same = sum(bl.size for bl in sm.get_matching_blocks())
            if same * 2 > max(len(wa), len(wb)):
                for op2, k1, k2, l1, l2 in sm.get_opcodes():
                    if op2 == 'equal':
                        out.append(('equal', a0 + k1, a0 + k2, wa[k1:k2]))
                    else:
                        if k2 > k1:
                            out.append(('delete', a0 + k1, a0 + k2, ''))
                        if l2 > l1:
                            out.append(('insert', a0 + k2, a0 + k2, wb[l1:l2]))
                continue
        if a1 > a0:
            out.append(('delete', a0, a1, ''))
        if b1 > b0:
            out.append(('insert', a1, a1, b[b0:b1]))
    return cleanup_ops(out)


def cleanup_ops(ops, min_side=10, max_equal=14):
    """איחוד איים קצרים של טקסט זהה בין שני שינויים מהותיים, כך שמשפט שנכתב מחדש נקרא כמחיקה אחת
    והכנסה אחת ולא כרסיסים. לא מאחד כשמדובר במספרים או בסוגריים."""
    def size(o):
        return (o[2] - o[1]) if o[0] == 'delete' else (len(o[3]) if o[0] == 'insert' else 0)

    groups = []
    for o in ops:
        if o[0] == 'equal':
            groups.append(['equal', o])
        elif groups and groups[-1][0] == 'chg':
            groups[-1][1].append(o)
        else:
            groups.append(['chg', [o]])
    changed = True
    while changed:
        changed = False
        for i in range(1, len(groups) - 1):
            g = groups[i]
            if g[0] != 'equal' or groups[i - 1][0] != 'chg' or groups[i + 1][0] != 'chg':
                continue
            eq = g[1]
            ins_txt = ''.join(o[3] for o in groups[i - 1][1] + groups[i + 1][1] if o[0] == 'insert')
            cond_a = ((eq[2] - eq[1]) <= max_equal and sum(size(o) for o in groups[i - 1][1]) >= min_side
                      and sum(size(o) for o in groups[i + 1][1]) >= min_side)
            cond_b = len(eq[3].split()) <= 1 and len(eq[3]) <= 7 and not re.search(r'[\d\[]', ins_txt + eq[3])
            if cond_a or cond_b:
                merged = (groups[i - 1][1] + [('delete', eq[1], eq[2], ''), ('insert', eq[2], eq[2], eq[3])]
                          + groups[i + 1][1])
                groups[i - 1:i + 2] = [['chg', merged]]
                changed = True
                break
    out = []
    for g in groups:
        if g[0] == 'equal':
            out.append(g[1])
            continue
        dels = [o for o in g[1] if o[0] == 'delete']
        ins = ''.join(o[3] for o in g[1] if o[0] == 'insert')
        if dels:
            a0, a1 = min(o[1] for o in dels), max(o[2] for o in dels)
            out.append(('delete', a0, a1, ''))
            pos = a1
        else:
            pos = g[1][0][1]
        if ins:
            out.append(('insert', pos, pos, ins))
    return out


def span_ops(orig, spans):
    """הבדל רק בתוך טווחים מוגדרים. spans: רשימה של (old, new, tag). כל old חייב להופיע פעם אחת בדיוק.
    מחזיר (ops, target), ולכל op שאינו equal נוסף tag (לעיגון הבועה של אותו טווח)."""
    located = []
    for old, new, tag in spans:
        if not old or orig.count(old) != 1:
            raise UnsupportedEdit('הטווח "%s" אינו מופיע פעם אחת בדיוק בפסקה' % (old or '')[:40])
        i = orig.index(old)
        located.append((i, i + len(old), new, tag))
    located.sort()
    for x in range(1, len(located)):
        if located[x][0] < located[x - 1][1]:
            raise UnsupportedEdit('שני טווחים חופפים באותה פסקה')
    ops, pos, target = [], 0, ''
    for i0, i1, new, tag in located:
        if i0 > pos:
            ops.append(('equal', pos, i0, orig[pos:i0], None))
            target += orig[pos:i0]
        for op, a0, a1, txt in char_ops(orig[i0:i1], new):
            ops.append((op, i0 + a0, i0 + a1, txt, None if op == 'equal' else tag))
        target += new
        pos = i1
    if pos < len(orig):
        ops.append(('equal', pos, len(orig), orig[pos:], None))
        target += orig[pos:]
    return ops, target


LATIN = re.compile(r'[A-Za-z][A-Za-z0-9/&.\-]*(?:[ ][A-Za-z0-9/&.\-]+)*')
HEB_SEG = re.compile('[\u0590-\u05ff](?:[\u0590-\u05ff"\'\u05f3\u05f4\\- ]*[\u0590-\u05ff])?')
HEB_CHAR = re.compile('[\u0590-\u05ff]')


def script_split(text, rtl_para=True):
    """(קטע, LTR?) לפי כתב.
    rtl_para=True (פסקה עברית): קטע לטיני הוא LTR; ספרות וסימנים נשארים עם הטקסט העברי הסמוך (RTL).
    rtl_para=False (פסקה משמאל לימין): רק קטע שיש בו אות עברית הוא RTL; כל השאר, כולל פיסוק וספרות, LTR."""
    if not rtl_para:
        out, pos = [], 0
        for m in HEB_SEG.finditer(text):
            if m.start() > pos:
                out.append((text[pos:m.start()], True))
            out.append((m.group(), False))
            pos = m.end()
        if pos < len(text):
            out.append((text[pos:], True))
        return [x for x in out if x[0]]
    out, pos = [], 0
    for m in LATIN.finditer(text):
        if m.start() > pos:
            out.append((text[pos:m.start()], False))
        out.append((m.group(), True))
        pos = m.end()
    if pos < len(text):
        out.append((text[pos:], False))
    return [x for x in out if x[0]]


# --------------------------------------------------------------------------------------- הטלות
_SKIP = {W + 'txbxContent', '{%s}Fallback' % MC_NS}


def body_paragraphs(root):
    """כל פסקאות הגוף לפי הסדר, כולל טבלאות, בלי תיבות טקסט ובלי ענף ה-Fallback (שמופיע פעמיים)."""
    body = root.find(W + 'body')
    out = []

    def walk(el):
        for ch in el:
            if ch.tag in _SKIP:
                continue
            if ch.tag == W + 'p':
                out.append(ch)
            else:
                walk(ch)
    walk(body)
    return out


def _text_nodes(p):
    """צמתי טקסט של הפסקה לפי הסדר, בלי תיבות טקסט מקוננות."""
    def walk(el, anc):
        for ch in el:
            if ch.tag in _SKIP or ch.tag == W + 'p':
                continue
            tag = local(ch.tag)
            if tag in ('t', 'delText', 'tab', 'br', 'cr'):
                yield ch, anc
            else:
                yield from walk(ch, anc + (tag,))
    yield from walk(p, ())


def _node_text(node):
    tag = local(node.tag)
    if tag in ('t', 'delText'):
        return node.text or ''
    if tag == 'tab':
        return '\t'
    return '\n'


def para_text(p):
    """הטקסט הנוכחי של פסקה בלי סימוני מעקב (הטיוטה שהתקבלה)."""
    return ''.join(_node_text(n) for n, anc in _text_nodes(p) if local(n.tag) != 'delText' and 'del' not in anc)


def _mark(p):
    rpr = p.find(W + 'pPr/' + W + 'rPr')
    if rpr is None:
        return None
    if rpr.find(W + 'del') is not None and rpr.find(W + 'ins') is not None:
        return 'both'
    if rpr.find(W + 'del') is not None:
        return 'del'
    if rpr.find(W + 'ins') is not None:
        return 'ins'
    return None


def paragraph_views(root, mode):
    """הטלה של המסמך לרשימת פסקאות: accept (קבל הכול), reject (דחה הכול), או reject_del_only (מקבלים
    הוספות ודוחים מחיקות, המצב שבו הצד שכנגד דוחה רק את המחיקות). פסקה שסימן הפסקה שלה נעלם בהטלה
    מתמזגת עם הפסקה הבאה, כמו ב-Word."""
    out, buf = [], ''
    for p in body_paragraphs(root):
        txt = ''
        for n, anc in _text_nodes(p):
            tag = local(n.tag)
            in_ins, in_del = 'ins' in anc, 'del' in anc or tag == 'delText'
            if mode == 'accept':
                keep = not in_del
            elif mode == 'reject':
                keep = not in_ins
            else:  # reject_del_only
                keep = True
            if keep:
                txt += _node_text(n)
        m = _mark(p)
        if mode == 'accept':
            gone = m in ('del', 'both')
        elif mode == 'reject':
            gone = m in ('ins', 'both')
        else:
            gone = m == 'both'
        buf += txt
        if gone:
            continue
        out.append(buf)
        buf = ''
    if buf:
        out.append(buf)
    return out


def read_package(path_or_bytes):
    data = path_or_bytes if isinstance(path_or_bytes, (bytes, bytearray)) else open(path_or_bytes, 'rb').read()
    z = zipfile.ZipFile(io.BytesIO(data))
    return {n: z.read(n) for n in z.namelist()}


def document_root(path_or_bytes):
    return etree.fromstring(read_package(path_or_bytes)['word/document.xml'])


def accept_all(path):
    return paragraph_views(document_root(path), 'accept')


def reject_all(path):
    return paragraph_views(document_root(path), 'reject')


def received_paragraphs(path):
    return [para_text(p) for p in body_paragraphs(document_root(path))]


def read_comments(path_or_parts):
    """רשימת הבועות: id, author, initials, date, text."""
    parts = path_or_parts if isinstance(path_or_parts, dict) else read_package(path_or_parts)
    if COMMENTS_PART not in parts:
        return []
    root = etree.fromstring(parts[COMMENTS_PART])
    out = []
    for c in root.findall(W + 'comment'):
        text = '\n'.join(''.join(t.text or '' for t in p.iter(W + 't')) for p in c.findall(W + 'p'))
        out.append({'id': c.get(W + 'id'), 'author': c.get(W + 'author'), 'initials': c.get(W + 'initials'),
                    'date': c.get(W + 'date'), 'text': text})
    return out


def comment_paragraphs(root):
    """לכל מזהה בועה: אינדקס הפסקה (ברשימת body_paragraphs של המסמך המסומן) שבה היא מתחילה."""
    where = {}
    for i, p in enumerate(body_paragraphs(root)):
        for s in p.iter(W + 'commentRangeStart'):
            where.setdefault(s.get(W + 'id'), i)
    return where


def revision_text(p, kind, author=None):
    """הטקסט שהוכנס (kind=ins) או נמחק (kind=del) בפסקה, ובמחבר מסוים כשנמסר."""
    out = []
    for el in p.iter(W + kind):
        if el.getparent() is not None and local(el.getparent().tag) == 'rPr':
            continue
        if author and el.get(W + 'author') != author:
            continue
        for n in el.iter(W + ('t' if kind == 'ins' else 'delText')):
            out.append(n.text or '')
    return ''.join(out)


# --------------------------------------------------------------------------------------- המנוע
_EDITABLE_RUN_CHILDREN = {'rPr', 't', 'tab', 'br', 'lastRenderedPageBreak', 'softHyphen'}
_LOCKED_CONTAINERS = {'sdt', 'fldSimple', 'smartTag', 'customXml', 'oMath', 'oMathPara'}
_REVISION_CONTAINERS = {'ins', 'del', 'moveFrom', 'moveTo'}


class _Unit:
    __slots__ = ('el', 'text', 'editable', 's', 'e')

    def __init__(self, el, text, editable):
        self.el, self.text, self.editable = el, text, editable
        self.s = self.e = 0


class TrackedDocx:
    """מסמך שהתקבל מהצד שכנגד, ועליו ההכרעות שלנו בעקוב אחר שינויים.

        doc = TrackedDocx(received_path, author='עורך הדין מהפרופיל', initials='ע"ד')
        doc.replace_span(18, '30', '[60]', external='...', internal='...')
        doc.insert_paragraph(7, 'טקסט הסעיף', number='3.‏ ', external='...')
        doc.delete_paragraph(0, external='...')
        doc.save(out_path, internal_header=True)
        doc.verify_roundtrip()   # [] כשהכול תקין
    """

    def __init__(self, src, author, initials=None, clock=None):
        self.parts = read_package(src)
        self.order = list(self.parts)
        self.root = etree.fromstring(self.parts['word/document.xml'])
        self.body = self.root.find(W + 'body')
        self.paras = body_paragraphs(self.root)
        self.orig_texts = [para_text(p) for p in self.paras]
        self.author = author
        self.initials = initials or ''.join(w[0] for w in author.split()[:2])
        self.clock = clock or RevisionClock()
        self.targets = {}          # אינדקס מקורי -> נוסח יעד, או None כשנמחקה
        self.inserted = {}         # אינדקס עוגן -> [(p, text)]
        self.comments = []         # (cid, author, initials, text, date)
        self.decision_log = []
        self.highlight_in = len(list(self.root.iter(W + 'highlight')))
        self._base_comments = self.parts.get(COMMENTS_PART)
        self._next_id = self._max_id() + 1
        self._edited = set()
        self._finalized = False
        self.rtl_default = self._styles_rtl_default()

    # ----------------------------------------------------------------- מזהים ותאריכים
    def _max_id(self):
        mx = 0
        for name in ('word/document.xml', COMMENTS_PART):
            if name in self.parts:
                for m in re.finditer(rb'w:id="(\d+)"', self.parts[name]):
                    mx = max(mx, int(m.group(1)))
        return max(mx, 100)

    def _id(self):
        self._next_id += 1
        return str(self._next_id)

    def _rev(self, tag):
        el = etree.Element(W + tag)
        loc, utc = self.clock.stamp()
        el.set(W + 'id', self._id())
        el.set(W + 'author', self.author)
        el.set(W + 'date', loc)
        el.set(DATE_UTC_ATTR, utc)
        return el

    # ----------------------------------------------------------------- כיוון
    def _styles_rtl_default(self):
        """האם פסקה בלי w:bidi משלה היא מימין לשמאל, לפי docDefaults והסגנון Normal ב-styles.xml."""
        data = self.parts.get('word/styles.xml')
        if not data:
            return False
        st = etree.fromstring(data)
        for el in st.iter(W + 'pPrDefault'):
            b = el.find('.//' + W + 'bidi')
            if b is not None and b.get(W + 'val') not in ('0', 'false'):
                return True
        for sty in st.findall(W + 'style'):
            if sty.get(W + 'default') == '1' and sty.get(W + 'type') == 'paragraph':
                b = sty.find(W + 'pPr/' + W + 'bidi')
                if b is not None and b.get(W + 'val') not in ('0', 'false'):
                    return True
        return False

    def _para_rtl(self, p):
        b = p.find(W + 'pPr/' + W + 'bidi')
        if b is not None:
            return b.get(W + 'val') not in ('0', 'false')
        if self.rtl_default:
            return True
        # בלי bidi ובלי ברירת מחדל: הפסקה עברית כשרוב האותיות בה עבריות (נייר עברי שנכתב בלי bidi)
        txt = para_text(p)
        return len(HEB_CHAR.findall(txt)) >= len(re.findall('[A-Za-z]', txt))

    # ----------------------------------------------------------------- ריצות
    @staticmethod
    def _clean_rpr(rpr, latin):
        rp = copy.deepcopy(rpr) if rpr is not None else etree.Element(W + 'rPr')
        rp.tag = W + 'rPr'
        for tag in ('highlight', 'ins', 'del', 'rPrChange', 'vanish', 'webHidden'):
            for x in rp.findall(W + tag):
                rp.remove(x)
        for x in rp.findall(W + 'rtl'):
            rp.remove(x)
        if latin:
            for x in rp.findall(W + 'cs'):
                rp.remove(x)
        else:
            etree.SubElement(rp, W + 'rtl')
        fix_schema_order(rp)
        return rp

    @staticmethod
    def _content(r, text, deleted):
        for k, piece in enumerate(re.split(r'(\t|\n)', text)):
            if piece == '\t':
                etree.SubElement(r, W + 'tab')
            elif piece == '\n':
                etree.SubElement(r, W + 'br')
            elif piece:
                t = etree.SubElement(r, W + ('delText' if deleted else 't'))
                t.set(XML_SPACE, 'preserve')
                t.text = piece

    def _orig_run(self, rpr, text, deleted=False):
        r = etree.Element(W + 'r')
        if rpr is not None:
            r.append(copy.deepcopy(rpr))
        self._content(r, text, deleted)
        return r

    def _ins_el(self, rpr, text, rtl_para=True):
        ins = self._rev('ins')
        for seg, lat in script_split(text, rtl_para):
            r = etree.SubElement(ins, W + 'r')
            r.append(self._clean_rpr(rpr, lat))
            self._content(r, seg, False)
        return ins

    # ----------------------------------------------------------------- יחידות של פסקה
    def _units(self, p):
        units = []

        def add_run(r, inside_locked=False):
            kids = {local(c.tag) for c in r}
            txt = ''.join(_node_text(n) for n, anc in _text_nodes(r))
            units.append(_Unit(r, txt, not inside_locked and kids <= _EDITABLE_RUN_CHILDREN))

        for ch in p:
            tag = local(ch.tag)
            if tag == 'r':
                add_run(ch)
            elif tag == 'hyperlink':
                for r in ch:
                    if local(r.tag) == 'r':
                        add_run(r)
                    elif local(r.tag) in _REVISION_CONTAINERS:
                        raise UnsupportedEdit('בפסקה יש סימוני מעקב פתוחים של הצד שכנגד')
            elif tag in _REVISION_CONTAINERS:
                raise UnsupportedEdit('בפסקה יש סימוני מעקב פתוחים של הצד שכנגד')
            elif tag in _LOCKED_CONTAINERS:
                txt = ''.join(_node_text(n) for n, anc in _text_nodes(ch) if 'del' not in anc)
                units.append(_Unit(ch, txt, False))
        pos = 0
        for u in units:
            u.s, pos = pos, pos + len(u.text)
            u.e = pos
        if ''.join(u.text for u in units) != para_text(p):
            raise UnsupportedEdit('מבנה הפסקה אינו נתמך (טקסט מחוץ לריצות)')
        return units

    # ----------------------------------------------------------------- פעולות
    def _check_idx(self, idx):
        if not 0 <= idx < len(self.paras):
            raise UnsupportedEdit('אין פסקה %s בטיוטה' % idx)
        if idx in self._edited:
            raise UnsupportedEdit('פסקה %d כבר סומנה. מאחדים את ההכרעות לפני הסימון' % idx)

    def set_text(self, idx, target, external=None, internal=None):
        """נוסח יעד מלא לפסקה. מסמנים רק את ההבדל."""
        self._check_idx(idx)
        orig = self.orig_texts[idx]
        if target == orig:
            raise UnsupportedEdit('נוסח היעד זהה לנוסח שהתקבל')
        ops = [(o[0], o[1], o[2], o[3], 'all') for o in char_ops(orig, target)]
        self._apply_ops(idx, ops, {'all': (external, internal)})
        self.targets[idx] = target
        return target

    def replace_span(self, idx, old, new, external=None, internal=None):
        return self.edit_spans(idx, [(old, new, external, internal)])

    def edit_spans(self, idx, spans):
        """כמה החלפות באותה פסקה, בסימון אחד. spans: (old, new, external, internal). כל בועה מעוגנת לטווח שלה."""
        self._check_idx(idx)
        tagged = [(old, new, 's%d' % k) for k, (old, new, _, _) in enumerate(spans)]
        ops, target = span_ops(self.orig_texts[idx], tagged)
        bubbles = {'s%d' % k: (ext, intl) for k, (_, _, ext, intl) in enumerate(spans)}
        self._apply_ops(idx, ops, bubbles)
        self.targets[idx] = target
        return target

    def _apply_ops(self, idx, ops, bubbles):
        p = self.paras[idx]
        units = self._units(p)
        locked = [(u.s, u.e) for u in units if not u.editable and u.e > u.s]
        for op, a0, a1, txt, tag in ops:
            for s, e in locked:
                if op == 'delete' and a0 < e and a1 > s:
                    raise UnsupportedEdit('השינוי נוגע בשדה או באובייקט נעול בפסקה %d' % idx)
                if op == 'insert' and s < a0 < e:
                    raise UnsupportedEdit('הוספה בתוך שדה נעול בפסקה %d' % idx)
        editable = [u for u in units if u.editable]
        if not editable:
            raise UnsupportedEdit('אין בפסקה %d ריצה שאפשר לערוך' % idx)

        def owner(pos):
            for u in editable:
                if u.s < pos <= u.e:
                    return u
            for u in editable:
                if u.s >= pos:
                    return u
            return editable[-1]

        assigned = {}
        for k, o in enumerate(ops):
            if o[0] == 'insert':
                assigned[k] = owner(o[1])
        made = {}  # tag -> [elements]
        rtl_para = self._para_rtl(p)
        for u in units:
            if not u.editable or u.e == u.s:
                continue
            rpr = u.el.find(W + 'rPr')
            pieces = []
            for k, (op, a0, a1, txt, tag) in enumerate(ops):
                if op == 'insert':
                    if assigned[k] is u:
                        el = self._ins_el(rpr, txt, rtl_para)
                        pieces.append(el)
                        made.setdefault(tag, []).append(el)
                    continue
                s, e = max(a0, u.s), min(a1, u.e)
                if s >= e:
                    continue
                seg = u.text[s - u.s:e - u.s]
                if op == 'equal':
                    pieces.append(self._orig_run(rpr, seg))
                else:
                    d = self._rev('del')
                    d.append(self._orig_run(rpr, seg, deleted=True))
                    pieces.append(d)
                    made.setdefault(tag, []).append(d)
            for el in pieces:
                u.el.addprevious(el)
            u.el.getparent().remove(u.el)
        for tag, els in made.items():
            ext, intl = bubbles.get(tag, (None, None))
            self._anchor(els[0], els[-1], ext, intl, ref_wrap=None)
        self._edited.add(idx)
        self.clock.tick()

    def delete_paragraph(self, idx, external=None, internal=None):
        self._check_idx(idx)
        p = self.paras[idx]
        units = self._units(p)
        if any(not u.editable and u.text for u in units):
            raise UnsupportedEdit('פסקה %d כוללת שדה או אובייקט, ואינה נמחקת בשלמותה' % idx)
        made = []
        for u in units:
            if not u.editable or not u.text:
                continue
            d = self._rev('del')
            u.el.addprevious(d)
            r = u.el
            r.getparent().remove(r)
            for t in r.findall(W + 't'):
                t.tag = W + 'delText'
                t.set(XML_SPACE, 'preserve')
            d.append(r)
            made.append(d)
        self._mark_para(p, 'del')
        if made:
            self._anchor(made[0], made[-1], external, internal, ref_wrap='del')
        elif external or internal:
            self.comment_only(idx, external, internal)
        self.targets[idx] = None
        self._edited.add(idx)
        self.clock.tick()

    def insert_paragraph(self, after_idx, text, number=None, template_idx=None, external=None, internal=None):
        """פסקה חדשה אחרי פסקת העוגן (ואחרי פסקאות שכבר נוספו אחריה). pPr מהתבנית (ברירת מחדל: העוגן),
        סימן הפסקה מסומן הוספה, והמספר המוקלד (כשיש) נכנס כטקסט באותה תבנית של הנייר שלהם."""
        if not 0 <= after_idx < len(self.paras):
            raise UnsupportedEdit('אין פסקת עוגן %s' % after_idx)
        if not text or not text.strip():
            raise UnsupportedEdit('אין מוסיפים פסקה ריקה')
        tp = self.paras[after_idx if template_idx is None else template_idx]
        p = etree.Element(W + 'p')
        tppr = tp.find(W + 'pPr')
        ppr = copy.deepcopy(tppr) if tppr is not None else etree.Element(W + 'pPr')
        for tag in ('rPr', 'sectPr', 'pPrChange'):
            for x in ppr.findall(W + tag):
                ppr.remove(x)
        p.append(ppr)
        self._mark_para(p, 'ins')
        truns = [r for r in tp.iter(W + 'r') if r.find(W + 't') is not None]
        body_rpr = truns[-1].find(W + 'rPr') if truns else None
        num_rpr = truns[0].find(W + 'rPr') if truns else None
        rtl_para = self._para_rtl(tp)
        ins = self._ins_el(body_rpr, text, rtl_para)
        if number:
            num_ins = self._ins_el(num_rpr, number, rtl_para)
            for r in list(num_ins)[::-1]:
                ins.insert(0, r)
        p.append(ins)
        self._anchor(ins, ins, external, internal, ref_wrap='ins')
        self.inserted.setdefault(after_idx, []).append((p, (number or '') + text))
        self.clock.tick()
        return p

    def comment_only(self, idx, external=None, internal=None):
        p = self.paras[idx]
        kids = [c for c in p if local(c.tag) != 'pPr']
        if not kids:
            r = etree.SubElement(p, W + 'r')
            kids = [r]
        self._anchor(kids[0], kids[-1], external, internal, ref_wrap=None)
        self.clock.tick()

    # ----------------------------------------------------------------- בועות
    def _anchor(self, first, last, external, internal, ref_wrap):
        for author, initials, text in ((self.author, self.initials, external),
                                       (INTERNAL_AUTHOR, INTERNAL_INITIALS, internal)):
            if not text:
                continue
            cid = self._id()
            loc, _ = self.clock.stamp()
            self.comments.append((cid, author, initials, text, loc))
            s = etree.Element(W + 'commentRangeStart')
            s.set(W + 'id', cid)
            e = etree.Element(W + 'commentRangeEnd')
            e.set(W + 'id', cid)
            first.addprevious(s)
            last.addnext(e)
            r = etree.Element(W + 'r')
            rp = etree.SubElement(r, W + 'rPr')
            etree.SubElement(rp, W + 'rtl')
            ref = etree.SubElement(r, W + 'commentReference')
            ref.set(W + 'id', cid)
            if ref_wrap:
                wrap = self._rev(ref_wrap)
                wrap.append(r)
                e.addnext(wrap)
            else:
                e.addnext(r)
            last = e if not ref_wrap else e.getnext()

    def _mark_para(self, p, tag):
        ppr = p.find(W + 'pPr')
        if ppr is None:
            ppr = etree.Element(W + 'pPr')
            p.insert(0, ppr)
        rpr = ppr.find(W + 'rPr')
        if rpr is None:
            rpr = etree.SubElement(ppr, W + 'rPr')
        if rpr.find(W + tag) is None:
            rpr.insert(0, self._rev(tag))
        fix_schema_order(rpr)
        fix_schema_order(ppr)

    @staticmethod
    def _unmark_para(p, tag):
        rpr = p.find(W + 'pPr/' + W + 'rPr')
        if rpr is not None:
            for x in rpr.findall(W + tag):
                rpr.remove(x)

    # ----------------------------------------------------------------- סידור סופי
    def _final_body_paragraph(self):
        ps = [c for c in self.body if c.tag == W + 'p']
        return ps[-1] if ps else None

    def finalize(self):
        if self._finalized:
            return
        last_orig = len(self.paras) - 1
        last_p = self.paras[last_orig]
        is_body_last = last_p.getparent() is self.body and self._final_body_paragraph() is last_p
        # (1) פסקאות שנוספו נכנסות אחרי העוגן שלהן
        for idx in sorted(self.inserted, reverse=True):
            anchor = self.paras[idx]
            for p, _ in self.inserted[idx]:
                anchor.addnext(p)
                anchor = p
        chain = [p for p, _ in self.inserted.get(last_orig, [])]
        if is_body_last and chain and self._final_body_paragraph() is chain[-1]:
            if self.targets.get(last_orig, '') is None:
                # (3) הפסקה האחרונה נמחקה ונוספו אחריה פסקאות: כל הפסקאות החדשות חוץ מהאחרונה זזות לפני
                # הפסקה האחרונה, והטקסט של האחרונה נכנס לפסקה האחרונה עצמה, כך שסימן הפסקה הסופי נשמר.
                new_last = chain[-1]
                for p in chain[:-1]:
                    last_p.addprevious(p)
                self._unmark_para(last_p, 'del')
                for ch in [c for c in new_last if local(c.tag) != 'pPr']:
                    last_p.append(ch)
                new_last.getparent().remove(new_last)
            else:
                # (2) הוספה אחרי הפסקה האחרונה: כמו ב-Word, סימן הפסקה של העוגן מסומן הוספה, והפסקה
                # החדשה האחרונה מקבלת את סימן הפסקה הסופי, בלי סימון.
                self._mark_para(last_p, 'ins')
                self._unmark_para(chain[-1], 'ins')
        elif is_body_last and self.targets.get(last_orig, '') is None:
            # (4) מחיקת הפסקה האחרונה: מוחקים את סימן הפסקה של הפסקה הקודמת שלא נמחקה, כך שאחרי "קבל הכול"
            # ההסכם אינו מסתיים בפסקה ריקה.
            prev = last_p.getprevious()
            while prev is not None and (prev.tag != W + 'p' or _mark(prev) == 'del'):
                prev = prev.getprevious()
            if prev is None:
                raise UnsupportedEdit('אין פסקה לפני הפסקה האחרונה שנמחקה')
            if _mark(prev) == 'ins':
                raise UnsupportedEdit('לפני הפסקה האחרונה שנמחקה יש פסקה שהוספנו: מוסיפים אחרי הפסקה האחרונה')
            self._mark_para(prev, 'del')
        self._finalized = True

    def expected_accept(self):
        out = []
        for i, t in enumerate(self.orig_texts):
            tgt = self.targets.get(i, t)
            if tgt is not None:
                out.append(tgt)
            out += [txt for _, txt in self.inserted.get(i, [])]
        return out

    def verify_roundtrip(self):
        """[] כשהכול תקין. אחרת רשימת כשלים: (view, index, expected, got)."""
        self.finalize()
        fails = []
        for view, expected in (('accept', self.expected_accept()), ('reject', self.orig_texts)):
            got = paragraph_views(self.root, view)
            if got != expected:
                for i in range(max(len(got), len(expected))):
                    g = got[i] if i < len(got) else None
                    e = expected[i] if i < len(expected) else None
                    if g != e:
                        fails.append((view, i, e, g))
                        break
        ours = [h for e in self.root.iter(W + 'ins') if e.get(W + 'author') == self.author
                for h in e.iter(W + 'highlight')]
        if ours:
            fails.append(('highlight', None, 0, len(ours)))  # צבע בטקסט שהכנסנו; הצבע של הנייר שלהם נשאר כמו שהוא
        return fails

    # ----------------------------------------------------------------- חלקי החבילה
    def _comments_xml(self):
        if self._base_comments:
            root = etree.fromstring(self._base_comments)
        else:
            root = etree.Element(W + 'comments', nsmap={'w': W_NS})
        for cid, author, initials, text, date in self.comments:
            c = etree.SubElement(root, W + 'comment')
            c.set(W + 'id', cid)
            c.set(W + 'author', author)
            c.set(W + 'date', date)
            c.set(W + 'initials', initials)
            rtl_c = len(HEB_CHAR.findall(text)) >= len(re.findall('[A-Za-z]', text))  # בועה באנגלית: LTR
            for k, line in enumerate(text.split('\n')):
                p = etree.SubElement(c, W + 'p')
                ppr = etree.SubElement(p, W + 'pPr')
                if rtl_c:
                    etree.SubElement(ppr, W + 'bidi')
                if k == 0:
                    r = etree.SubElement(p, W + 'r')
                    if rtl_c:
                        etree.SubElement(etree.SubElement(r, W + 'rPr'), W + 'rtl')
                    etree.SubElement(r, W + 'annotationRef')
                for seg, lat in script_split(line, rtl_c):
                    r = etree.SubElement(p, W + 'r')
                    if not lat:
                        etree.SubElement(etree.SubElement(r, W + 'rPr'), W + 'rtl')
                    t = etree.SubElement(r, W + 't')
                    t.set(XML_SPACE, 'preserve')
                    t.text = seg
        return etree.tostring(root, xml_declaration=True, encoding='UTF-8', standalone=True)

    def _add_rel(self, rid, rtype, target):
        rels = etree.fromstring(self.parts['word/_rels/document.xml.rels'])
        for r in rels:
            if r.get('Target') == target:
                return r.get('Id')
        ids = {r.get('Id') for r in rels}
        while rid in ids:
            rid += 'x'
        e = etree.SubElement(rels, '{%s}Relationship' % PKG_REL_NS)
        e.set('Id', rid)
        e.set('Type', REL_TYPE + rtype)
        e.set('Target', target)
        self.parts['word/_rels/document.xml.rels'] = etree.tostring(rels, xml_declaration=True, encoding='UTF-8',
                                                                    standalone=True)
        return rid

    def _add_override(self, part, ctype):
        ct = etree.fromstring(self.parts['[Content_Types].xml'])
        if any(o.get('PartName') == '/' + part for o in ct):
            return
        e = etree.SubElement(ct, '{%s}Override' % CT_NS)
        e.set('PartName', '/' + part)
        e.set('ContentType', ctype)
        self.parts['[Content_Types].xml'] = etree.tostring(ct, xml_declaration=True, encoding='UTF-8',
                                                           standalone=True)

    def _add_internal_header(self):
        hdr = etree.Element(W + 'hdr', nsmap={'w': W_NS})
        p = etree.SubElement(hdr, W + 'p')
        ppr = etree.SubElement(p, W + 'pPr')
        etree.SubElement(ppr, W + 'bidi')
        jc = etree.SubElement(ppr, W + 'jc')
        jc.set(W + 'val', 'center')
        r = etree.SubElement(p, W + 'r')
        rp = etree.SubElement(r, W + 'rPr')
        etree.SubElement(rp, W + 'b')
        etree.SubElement(rp, W + 'rtl')
        t = etree.SubElement(r, W + 't')
        t.text = INTERNAL_HEADER_TEXT
        self.parts[INTERNAL_HEADER_PART] = etree.tostring(hdr, xml_declaration=True, encoding='UTF-8',
                                                          standalone=True)
        self._add_override(INTERNAL_HEADER_PART, CT_HEADER)
        for sect in self.root.iter(W + 'sectPr'):
            refs = [h for h in sect.findall(W + 'headerReference') if h.get(W + 'type', 'default') == 'default']
            if refs:
                orig = refs[0].get('{%s}id' % R_NS)
                rid = self._add_rel('%s_%s' % (INTERNAL_REL_PREFIX, orig), 'header', 'headerInternal.xml')
                refs[0].set('{%s}id' % R_NS, rid)
            else:
                rid = self._add_rel(INTERNAL_REL_PREFIX, 'header', 'headerInternal.xml')
                h = etree.Element(W + 'headerReference')
                h.set(W + 'type', 'default')
                h.set('{%s}id' % R_NS, rid)
                sect.insert(0, h)

    def _enable_track_revisions(self):
        s = etree.fromstring(self.parts['word/settings.xml'])
        for x in s.findall(W + 'trackChanges'):
            s.remove(x)
        if s.find(W + 'trackRevisions') is None:
            tr = etree.Element(W + 'trackRevisions')
            prev = None
            for k in s:
                if local(k.tag) in SETTINGS_BEFORE_TRACK:
                    prev = k
            if prev is not None:
                prev.addnext(tr)
            else:
                s.insert(0, tr)
        self.parts['word/settings.xml'] = etree.tostring(s, xml_declaration=True, encoding='UTF-8', standalone=True)

    def _clean_metadata(self):
        stamp = self.clock.t.astimezone(_dt.timezone.utc).strftime(DATE_FMT)
        a = esc(self.author)
        core = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
                '<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" '
                'xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" '
                'xmlns:dcmitype="http://purl.org/dc/dcmitype/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">'
                '<dc:creator>%s</dc:creator><cp:lastModifiedBy>%s</cp:lastModifiedBy><cp:revision>1</cp:revision>'
                '<dcterms:created xsi:type="dcterms:W3CDTF">%s</dcterms:created>'
                '<dcterms:modified xsi:type="dcterms:W3CDTF">%s</dcterms:modified></cp:coreProperties>'
                % (a, a, stamp, stamp))
        self.parts['docProps/core.xml'] = core.encode('utf-8')
        if 'docProps/app.xml' in self.parts:
            app = self.parts['docProps/app.xml'].decode('utf-8')
            for tag in ('Template', 'TotalTime', 'Company', 'Manager'):
                app = re.sub(r'\s*<%s>[^<]*</%s>' % (tag, tag), '', app)
                app = re.sub(r'\s*<%s/>' % tag, '', app)
            self.parts['docProps/app.xml'] = app.encode('utf-8')
        if 'docProps/thumbnail.jpeg' in self.parts:
            del self.parts['docProps/thumbnail.jpeg']
            self.parts['_rels/.rels'] = re.sub(rb'<Relationship [^>]*thumbnail[^>]*/>', b'', self.parts['_rels/.rels'])
            self.parts['[Content_Types].xml'] = re.sub(rb'<Override PartName="/docProps/thumbnail\.jpeg"[^>]*/>', b'',
                                                       self.parts['[Content_Types].xml'])
        if b'dataBinding' not in etree.tostring(self.root):
            for n in [n for n in self.parts if n.startswith('customXml/')]:
                del self.parts[n]
            self.parts['word/_rels/document.xml.rels'] = re.sub(
                rb'<Relationship [^>]*customXml[^>]*/>', b'', self.parts['word/_rels/document.xml.rels'])
            self.parts['[Content_Types].xml'] = re.sub(rb'<Override PartName="/customXml/[^"]*"[^>]*/>', b'',
                                                       self.parts['[Content_Types].xml'])

    def _serialize_document(self):
        """מצהיר על w16du ומוסיף אותו ל-mc:Ignorable, בלי להסיר אף הצהרה קיימת."""
        nsmap = dict(self.root.nsmap)
        nsmap.setdefault('mc', MC_NS)
        nsmap['w16du'] = W16DU_NS
        new_root = etree.Element(self.root.tag, nsmap=nsmap)
        for k, v in self.root.attrib.items():
            new_root.set(k, v)
        ign = new_root.get(MC_IGNORABLE, '').split()
        if 'w16du' not in ign:
            ign.append('w16du')
        new_root.set(MC_IGNORABLE, ' '.join(ign))
        for ch in list(self.root):
            new_root.append(ch)
        self.root = new_root
        self.body = new_root.find(W + 'body')
        fix_schema_order(self.root)
        self.parts['word/document.xml'] = etree.tostring(new_root, xml_declaration=True, encoding='UTF-8',
                                                         standalone=True)

    def to_bytes(self, internal_header=True):
        self.finalize()
        if self.comments:
            self.parts[COMMENTS_PART] = self._comments_xml()
            self._add_rel('rIdCm', 'comments', 'comments.xml')
            self._add_override(COMMENTS_PART, CT_COMMENTS)
        if internal_header and INTERNAL_HEADER_PART not in self.parts:
            self._add_internal_header()
        self._enable_track_revisions()
        self._clean_metadata()
        self._serialize_document()
        return write_package(self.parts, self.order)

    def save(self, out_path, internal_header=True):
        data = self.to_bytes(internal_header)
        with open(out_path, 'wb') as f:
            f.write(data)
        return out_path


def esc(s):
    return (s or '').replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;')


def write_package(parts, order=()):
    names = ['[Content_Types].xml'] + [n for n in order if n in parts and n != '[Content_Types].xml']
    names += [n for n in parts if n not in names]
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as z:
        for n in names:
            z.writestr(n, parts[n])
    return buf.getvalue()


# --------------------------------------------------------------------------------------- עותק למשלוח
def strip_internal(src, dst=None):
    """מסיר את הבועות הפנימיות (המחבר הקבוע), את העיגונים ואת ריצות ההפניה שלהן, ואת הכותרת הפנימית.
    מחזיר bytes, וכותב ל-dst כשנמסר. מרחבי השמות נשמרים."""
    parts = read_package(src)
    order = list(parts)
    drop = set()
    if COMMENTS_PART in parts:
        cx = etree.fromstring(parts[COMMENTS_PART])
        for c in cx.findall(W + 'comment'):
            if c.get(W + 'author') == INTERNAL_AUTHOR:
                drop.add(c.get(W + 'id'))
                cx.remove(c)
        parts[COMMENTS_PART] = etree.tostring(cx, xml_declaration=True, encoding='UTF-8', standalone=True)
    doc = etree.fromstring(parts['word/document.xml'])
    for tag in ('commentRangeStart', 'commentRangeEnd'):
        for e in list(doc.iter(W + tag)):
            if e.get(W + 'id') in drop:
                e.getparent().remove(e)
    for ref in list(doc.iter(W + 'commentReference')):
        if ref.get(W + 'id') in drop:
            run = ref.getparent()
            holder = run.getparent()
            holder.remove(run)
            if local(holder.tag) in ('ins', 'del') and len(holder) == 0:
                holder.getparent().remove(holder)
    rels = etree.fromstring(parts['word/_rels/document.xml.rels'])
    for rel in list(rels):
        rid = rel.get('Id', '')
        if rid.startswith(INTERNAL_REL_PREFIX):
            orig = rid[len(INTERNAL_REL_PREFIX) + 1:] if rid.startswith(INTERNAL_REL_PREFIX + '_') else None
            for h in list(doc.iter(W + 'headerReference')):
                if h.get('{%s}id' % R_NS) == rid:
                    if orig:
                        h.set('{%s}id' % R_NS, orig)
                    else:
                        h.getparent().remove(h)
            rels.remove(rel)
    parts['word/_rels/document.xml.rels'] = etree.tostring(rels, xml_declaration=True, encoding='UTF-8',
                                                           standalone=True)
    parts.pop(INTERNAL_HEADER_PART, None)
    parts['[Content_Types].xml'] = re.sub(rb'<Override PartName="/word/headerInternal\.xml"[^>]*/>', b'',
                                          parts['[Content_Types].xml'])
    parts['word/document.xml'] = etree.tostring(doc, xml_declaration=True, encoding='UTF-8', standalone=True)
    data = write_package(parts, order)
    if dst:
        with open(dst, 'wb') as f:
            f.write(data)
    return data


# --------------------------------------------------------------------------------------- קובץ ההכרעות
DECISION_OPS = ('replace', 'replace_span', 'insert_paragraph', 'delete_paragraph', 'comment_only', 'accept')
# accept (גרסה 1.2.0): הכרעה מפורשת "לקבל כמו שהוא" ברכיב שלא נגעו בו. אין סימון ואין בועה, אבל לרכיב יש
# clause_id, והוא נכנס למפתח הכיסוי (state_builder.build_coverage). decision_code: A1, A2 או A3.
ACCEPT_CODES = ('A1', 'A2', 'A3')
DECISIONS_SCHEMA = {
    '$schema': 'https://json-schema.org/draft/2020-12/schema',
    'title': 'decisions_round_<n>.json',
    'type': 'object',
    'required': ['transaction_id', 'round', 'received_sha256', 'decisions'],
    'properties': {
        'transaction_id': {'type': 'string'},
        'lang': {'enum': ['he', 'en'], 'description': 'שפת הנייר המחייב (4.9, שינוי 86). בלי השדה: לפי רוב האותיות'},
        'round': {'type': 'integer', 'minimum': 1},
        'received_sha256': {'type': 'string'},
        'decisions': {'type': 'array', 'items': {
            'type': 'object',
            'required': ['id', 'op', 'decision_code'],
            'properties': {
                'id': {'type': 'string'},
                'op': {'enum': list(DECISION_OPS)},
                'para': {'type': 'integer', 'description': 'אינדקס הפסקה בטיוטה שהתקבלה'},
                'new_text': {'type': 'string', 'description': 'replace: נוסח יעד מלא לפסקה'},
                'old': {'type': 'string', 'description': 'replace_span: הטווח, פעם אחת בדיוק בפסקה'},
                'new': {'type': 'string'},
                'after_para': {'type': 'integer', 'description': 'insert_paragraph: פסקת העוגן'},
                'text': {'type': 'string'},
                'number': {'type': 'string', 'description': 'מספר מוקלד בנייר עם מספור מוקלד (60א, 77)'},
                'external_comment': {'type': 'string'},
                'internal_comment': {'type': 'string'},
                'conforming': {'type': 'boolean', 'description': 'שינוי טכני או עקבי. גם הוא מקבל בועה חיצונית קצרה '
                                                                  '(4.9, שינוי 84)'},
                'structural': {'type': 'boolean', 'description': 'כותרת פרק או מבנה. אינו נספר בבקשות (4.9, שינוי 89), '
                                                                  'ומקבל בועה קצרה'},
                'reopened_from_fix': {'anyOf': [{'type': 'string'}, {'type': 'array', 'items': {'type': 'string'}}],
                                      'description': 'מזהה שורת pre_send_fixes שההכרעה נפתחה בגללה, או רשימה כששתי '
                                                     'שורות חלות על אותו סעיף (4.9, שינוי 80; 1.2.0)'},
                'decision_code': {'enum': ['A1', 'A2', 'A3', 'R1', 'R2', 'R3', 'N1']},
                'rule_ids': {'type': 'array', 'items': {'type': 'string'}},
                'policy_gate': {'type': 'object'},
                'safe_wording': {'type': 'object'},
                'mandatory': {'type': 'boolean'},
            }}},
    }}


def validate_decisions(dec):
    """בדיקה בלי ספרייה חיצונית. מחזיר רשימת שגיאות; ריקה כשהקובץ תקין."""
    errs = []
    for k in DECISIONS_SCHEMA['required']:
        if k not in dec:
            errs.append('חסר %s' % k)
    seen = set()
    for d in dec.get('decisions', []):
        did = d.get('id', '?')
        if did in seen:
            errs.append('%s: מזהה כפול' % did)
        seen.add(did)
        op = d.get('op')
        if op not in DECISION_OPS:
            errs.append('%s: op לא מוכר: %s' % (did, op))
            continue
        need = {'replace': ('para', 'new_text'), 'replace_span': ('para', 'old', 'new'),
                'insert_paragraph': ('after_para', 'text'), 'delete_paragraph': ('para',),
                'comment_only': ('para',), 'accept': ('para',)}[op]
        for f in need:
            if f not in d:
                errs.append('%s: חסר %s' % (did, f))
        if d.get('decision_code') not in DECISIONS_SCHEMA['properties']['decisions']['items']['properties'][
                'decision_code']['enum']:
            errs.append('%s: decision_code לא מוכר' % did)
        if op == 'insert_paragraph' and d.get('decision_code') in ('R1', 'R2', 'R3'):
            errs.append('%s: נושא חסר שנוסף נרשם N1, ולא R1 עד R3' % did)
        if op != 'insert_paragraph' and d.get('decision_code') == 'N1':
            errs.append('%s: N1 רק לנושא חסר שנוסף' % did)
        if op in ('replace', 'replace_span', 'insert_paragraph', 'delete_paragraph') and not d.get('external_comment'):
            if d.get('conforming') or d.get('structural'):
                errs.append('%s: שינוי טכני בלי בועה חיצונית קצרה (כל שינוי שהצד שכנגד רואה מקבל בועה)' % did)
            else:
                errs.append('%s: שינוי מהותי בלי בועה חיצונית' % did)
        if op == 'accept' and d.get('decision_code') not in ACCEPT_CODES:
            errs.append('%s: accept רק עם decision_code A1, A2 או A3' % did)
        if op == 'accept' and (d.get('external_comment') or d.get('internal_comment')):
            errs.append('%s: accept הוא בלי סימון ובלי בועה; לבועה בלבד: comment_only' % did)
        rf = d.get('reopened_from_fix')
        if rf is not None and not (isinstance(rf, str) or (isinstance(rf, list) and all(isinstance(x, str) for x in rf))):
            errs.append('%s: reopened_from_fix הוא מזהה או רשימת מזהים' % did)
        if op == 'insert_paragraph' and d.get('structural') and d.get('mandatory'):
            errs.append('%s: כותרת מבנית אינה נושא חובה' % did)
    return errs


def mark_decisions(doc, dec):
    """מסמן את ההכרעות על TrackedDocx פתוח, בלי בדיקת החוזה. מחזיר not_marked. apply_decisions קורא לה אחרי
    validate_decisions; הבדיקות משתמשות בה כדי לשחזר תגובה ישנה שאינה עומדת בחוזה הנוכחי."""
    not_marked = []
    by_para = {}
    for d in dec['decisions']:
        if d['op'] == 'replace_span':
            by_para.setdefault(d['para'], []).append(d)
    for d in dec['decisions']:
        try:
            op = d['op']
            if op == 'replace':
                doc.set_text(d['para'], d['new_text'], d.get('external_comment'), d.get('internal_comment'))
            elif op == 'replace_span':
                group = by_para.pop(d['para'], None)
                if group:
                    doc.edit_spans(d['para'], [(g['old'], g['new'], g.get('external_comment'),
                                                g.get('internal_comment')) for g in group])
            elif op == 'insert_paragraph':
                doc.insert_paragraph(d['after_para'], d['text'], d.get('number'), d.get('template_para'),
                                     d.get('external_comment'), d.get('internal_comment'))
            elif op == 'delete_paragraph':
                doc.delete_paragraph(d['para'], d.get('external_comment'), d.get('internal_comment'))
            elif op == 'accept':
                continue   # לקבל כמו שהוא: אין סימון; הרכיב נכנס לכיסוי דרך state_builder.build_coverage
            else:
                doc.comment_only(d['para'], d.get('external_comment'), d.get('internal_comment'))
        except UnsupportedEdit as e:
            not_marked.append({'id': d['id'], 'reason': str(e)})
    return not_marked


def apply_decisions(received, dec, out_path=None, author=None, initials=None, now=None, internal_header=True):
    """מחיל קובץ הכרעות על הטיוטה שהתקבלה. מחזיר dict: ok, errors, not_marked, verify, expected_accept,
    data (bytes של קובץ העבודה). הכרעה שאינה ניתנת לסימון מדווחת ב-not_marked ואינה מוחלת חלקית."""
    errs = validate_decisions(dec)
    if errs:
        return {'ok': False, 'errors': errs}
    author = author or dec.get('author')
    clock = RevisionClock(now=now, steps=len(dec['decisions']))
    doc = TrackedDocx(received, author=author, initials=initials or dec.get('initials'), clock=clock)
    not_marked = mark_decisions(doc, dec)
    verify = doc.verify_roundtrip()
    data = doc.to_bytes(internal_header=internal_header)
    if out_path:
        with open(out_path, 'wb') as f:
            f.write(data)
    return {'ok': not verify and not not_marked, 'errors': [], 'not_marked': not_marked, 'verify': verify,
            'expected_accept': doc.expected_accept(), 'original': doc.orig_texts, 'data': data, 'doc': doc}
