# -*- coding: utf-8 -*-
"""מנוע עקוב אחר שינויים כירורגי, אחד לכל הרכיבים (מימוש ייחוס, הערות הנושא ונותן 4.8, שינויים 76 ו-77;
4.9, שינויים 84 ו-86: כל שינוי עם בועה חיצונית, ונייר באנגלית כנייר מלא).

מאחד את שלושת המנועים של ההדמיות בסבב 2 (c1b/engine.py, c1run/engine.py, build_response.py) ואת הבדיקות
העצמאיות של מהנדס הסקילים (rev2eng) למנוע אחד:

- עריכה ברמת המילה, עם עידון לאות כשרוב המילה נשמר, ומספר, סכום או סוגריים מרובעים כיחידה אחת.
- החלפת טווח (replace_span), נוסח יעד מלא לפסקה (set_text), הוספת פסקה ומחיקת פסקה עם סימן הפסקה,
  ובועה בלבד (comment_only). כמה הכרעות על אותה פסקה מאוחדות לסימון אחד.
- בועות חיצוניות במחבר עורך הדין ובראשי התיבות מהפרופיל, ובועות פנימיות במחבר הקבוע INTERNAL_AUTHOR (בעברית) או INTERNAL_AUTHOR_EN (בקובץ באנגלית).
- w:trackRevisions במקומו לפי סדר הסכמה של settings.xml, ובלי w:trackChanges.
- תאריך אמיתי: w:date הוא השעה המקומית בתבנית YYYY-MM-DDTHH:MM:SS, בלי Z (בסימון ובבועה, באותו אופן), ו-w16du:dateUtc
  הוא UTC אמיתי עם Z. שעה מקומית עם Z הציגה את כל השינויים כמה שעות בעתיד (ממצא ביקורת, 30.10.2026). השעון מתקדם בשנייה לכל הכרעה, כך שהשינויים אינם נושאים כולם אותה שנייה.
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
  בסבב 2 ואילך "המקור" הוא הטיוטה שהתקבלה כמו שהיא, כולל הסימונים הפתוחים שלנו מסבבים קודמים (prior_revisions),
  ו"דחה הכול" דוחה רק את הסימונים של הסבב הנוכחי (בדיקה עצמאית S1c, סבב 2, 28.10.2026).
- סימון בפסקה שיש בה סימון פתוח שלנו מסבב קודם: הטקסט הגלוי להתאמה הוא הנוסח אחרי קבלת הסימונים הפתוחים, מחיקה
  בתוך הוספה פתוחה שלנו היא w:del חדש מקונן בה, הוספה בתוכה מפצלת אותה, והכרעה שכבר קיימת במחיקה פתוחה שלנו
  מדווחת "קיימת מסבב קודם" (prior_edit_exists). הודעת "לא סומנה" מזהה של מי הסימון שחוסם (_whose).

תלות: Python 3, lxml. אין שימוש ב-python-docx כאן (הוא נשאר לבדיקות ולרכיבים אחרים).
"""
import copy
import datetime as _dt
import difflib
import io
import re
import secrets
import zipfile

from lxml import etree

W_NS = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
R_NS = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
MC_NS = 'http://schemas.openxmlformats.org/markup-compatibility/2006'
W16DU_NS = 'http://schemas.microsoft.com/office/word/2023/wordml/word16du'
W14_NS = 'http://schemas.microsoft.com/office/word/2010/wordml'
PKG_REL_NS = 'http://schemas.openxmlformats.org/package/2006/relationships'
CT_NS = 'http://schemas.openxmlformats.org/package/2006/content-types'
W = '{%s}' % W_NS
XML_SPACE = '{http://www.w3.org/XML/1998/namespace}space'
DATE_UTC_ATTR = '{%s}dateUtc' % W16DU_NS
MC_IGNORABLE = '{%s}Ignorable' % MC_NS

INTERNAL_AUTHOR = 'פנימי, למחיקה לפני המשלוח'
INTERNAL_AUTHOR_EN = 'Internal, delete before sending'
INTERNAL_AUTHORS = (INTERNAL_AUTHOR, INTERNAL_AUTHOR_EN)   # מזהים בהסרה את שניהם, בלי קשר לשפת הקובץ
INTERNAL_INITIALS = 'פנ'
INTERNAL_INITIALS_EN = 'Int'
INTERNAL_HEADER_TEXT = 'טיוטת עבודה פנימית, לא למשלוח'
INTERNAL_HEADER_TEXT_EN = 'Internal working draft, not for sending'


def internal_author(lang='he'):
    """(מחבר, ראשי תיבות, טקסט כותרת עליונה) של הבועות הפנימיות, לפי שפת התוצר (deliverable_language)."""
    if str(lang or 'he').lower().startswith('en'):
        return INTERNAL_AUTHOR_EN, INTERNAL_INITIALS_EN, INTERNAL_HEADER_TEXT_EN
    return INTERNAL_AUTHOR, INTERNAL_INITIALS, INTERNAL_HEADER_TEXT
INTERNAL_HEADER_PART = 'word/headerInternal.xml'
INTERNAL_REL_PREFIX = 'rIdInt'
# סעיף AREO: סעיף שאין לו עמדה בפלייבוק, וההכרעה בו היא הצעת Areo (source_label: areo_proposal). בקובץ העבודה בלבד
# הנוסח שלנו בו מסומן במירקור צהוב, ולצידו בועה פנימית שנפתחת בתווית הקבועה. strip_internal מסיר את שניהם
AREO_LABEL = {'he': 'סעיף AREO: אין לסעיף הזה עמדה בפלייבוק, וההכרעה היא הצעת Areo מנקודת המבט של %s%s.',
              'en': "Areo clause: the playbook has no position on this clause; the decision is Areo's proposal from "
                    "%s's position%s."}
AREO_LABEL_PREFIXES = ('סעיף AREO', 'Areo clause')
AREO_HIGHLIGHT = 'yellow'


def areo_label(company, role=None, lang='he'):
    """התווית הקבועה של סעיף AREO, בשפת הממשק: החברה, והתפקיד שלה בהסכם כשהוא ידוע."""
    en = str(lang or '').lower()[:2] == 'en'
    tail = ((' as %s' if en else ' כ%s') % role) if role else ''
    return AREO_LABEL['en' if en else 'he'] % (company or ('the company' if en else 'החברה'), tail)


AREO_SOURCE_LABELS = ('areo_proposal', 'הצעת Areo', 'Areo proposal')


def is_areo_decision(d):
    return (d or {}).get('source_label') in AREO_SOURCE_LABELS or (d or {}).get('areo_clause') is True


def _areo_comment_ids(comments_root):
    """מזהי הבועות הפנימיות שנפתחות בתווית של סעיף AREO."""
    out = set()
    if comments_root is None:
        return out
    for c in comments_root.findall(W + 'comment'):
        text = ''.join(t.text or '' for t in c.iter(W + 't')).strip()
        if c.get(W + 'author') in INTERNAL_AUTHORS and text.startswith(AREO_LABEL_PREFIXES):
            out.add(c.get(W + 'id'))
    return out


def areo_paragraphs(doc_root, ids):
    """פסקאות הגוף שבטווח של בועה פנימית של סעיף AREO (מהפסקה של commentRangeStart ועד זו של commentRangeEnd)."""
    if not ids:
        return []
    out, active = [], set()
    for p in body_paragraphs(doc_root):
        starts = {e.get(W + 'id') for e in p.iter(W + 'commentRangeStart')} & ids
        ends = {e.get(W + 'id') for e in p.iter(W + 'commentRangeEnd')} & ids
        active |= starts
        if active:
            out.append(p)
        active -= ends
    return out


def _revision_runs(p, author=None):
    """הריצות שבתוך w:ins ו-w:del של הפסקה (של author, כשנמסר): (ריצות בהוספה, ריצות במחיקה)."""
    ins, dels = [], []
    for rev in p.iter(W + 'ins', W + 'del'):
        if rev.getparent() is not None and local(rev.getparent().tag) == 'rPr':
            continue
        if author and rev.get(W + 'author') != author:
            continue
        (ins if local(rev.tag) == 'ins' else dels).extend(r for r in rev.iter(W + 'r')
                                                           if r.find(W + 'commentReference') is None)
    return ins, dels
COMMENTS_PART = 'word/comments.xml'
REL_TYPE = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships/'
CT_COMMENTS = 'application/vnd.openxmlformats-officedocument.wordprocessingml.comments+xml'
CT_HEADER = 'application/vnd.openxmlformats-officedocument.wordprocessingml.header+xml'
DATE_FMT = '%Y-%m-%dT%H:%M:%SZ'          # UTC אמיתי: w16du:dateUtc ומאפייני הקובץ
DATE_FMT_LOCAL = '%Y-%m-%dT%H:%M:%S'     # w:date: שעה מקומית בלי Z (Z על שעה מקומית הוא תווית שגויה)


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
    """שעון ההכרעות. w:date הוא השעה המקומית בלי Z, ו-dateUtc הוא UTC אמיתי עם Z.
    מתקדם בשנייה לכל tick, מנקודת התחלה שנקבעת כך שהשינוי האחרון אינו בעתיד."""

    def __init__(self, now=None, steps=0):
        now = now or _dt.datetime.now().astimezone()
        if now.tzinfo is None:
            now = now.astimezone()
        self.t = (now - _dt.timedelta(seconds=steps)).replace(microsecond=0)

    def stamp(self):
        loc = self.t.replace(tzinfo=None).strftime(DATE_FMT_LOCAL)
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
    # ההתאמה מעוגנת במילות תוכן (L1): רווח, פיסוק ומילת קישור קצרה אינם פותחים התאמה, כך ש-" the " ו-" of " אינם
    # מפזרים את ההבדל לרסיסים שהאיחוד מוחק כולם, כולל מילה זהה כמו "EEA". תחילית וסיומת משותפות הן תמיד זהות
    pre = 0
    while pre < min(len(ta), len(tb)) and ta[pre] == tb[pre]:
        pre += 1
    suf = 0
    while suf < min(len(ta), len(tb)) - pre and ta[-1 - suf] == tb[-1 - suf]:
        suf += 1
    sm = difflib.SequenceMatcher(_diff_junk, ta[pre:len(ta) - suf], tb[pre:len(tb) - suf], autojunk=False)
    codes = [(op, i1 + pre, i2 + pre, j1 + pre, j2 + pre) for op, i1, i2, j1, j2 in sm.get_opcodes()]
    if pre:
        codes.insert(0, ('equal', 0, pre, 0, pre))
    if suf:
        codes.append(('equal', len(ta) - suf, len(ta), len(tb) - suf, len(tb)))
    for op, i1, i2, j1, j2 in codes:
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


# מילת תוכן: מילה לטינית של ארבע אותיות ומעלה, ראשי תיבות (EEA), ספרה, או מילה עברית של שלוש אותיות ומעלה. אי של
# טקסט זהה שיש בו מילת תוכן אינו מאוחד לשינוי: מילה זהה אינה נמחקת ומוקלדת מחדש (בדיקה עצמאית S1c, ממצא L1:
# "EEA" ו-"assistance" נמחקו והוקלדו מחדש). רק מילות קישור קצרות ("the", "of", "של") ופיסוק מאוחדים
CONTENT_WORD = re.compile(r'[A-Za-z]{4,}|\b[A-Z]{2,}\b|\d|[א-ת]{3,}')


def _diff_junk(tok):
    return not CONTENT_WORD.search(tok)


def cleanup_ops(ops, min_side=10, max_equal=14):
    """איחוד איים קצרים של טקסט זהה בין שני שינויים מהותיים, כך שמשפט שנכתב מחדש נקרא כמחיקה אחת
    והכנסה אחת ולא כרסיסים. לא מאחד כשמדובר במספרים או בסוגריים, ולא אי שיש בו מילת תוכן (CONTENT_WORD)."""
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
            if CONTENT_WORD.search(eq[3]):
                continue
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


# --------------------------------------------------------------------------------------- גרשיים
# L3 (בדיקה עצמאית S1c): הנוסח שהוכנס נכתב בגרשיים ישרים, והמסמך במעוגלים. הסגנון נגזר מהמסמך עצמו, ונוסח שאנחנו
# מכניסים מותאם אליו. גרש או גרשיים בצמוד לאות עברית (בע"מ, ח"פ, נספח א') הם קיצור, ולא מירכאות, ואינם משתנים
QUOTE_FOLD = str.maketrans({'“': '"', '”': '"', '‘': "'", '’': "'"})


def quote_style(texts):
    """(מירכאות כפולות מעוגלות?, גרש מעוגל?) לפי רוב ההופעות בטקסט המסמך."""
    s = ''.join(texts)
    dq = s.count('“') + s.count('”') > s.count('"')
    sq = s.count('‘') + s.count('’') > s.count("'")
    return dq, sq


def match_quotes(text, style):
    """מירכאות וגרש ישרים בטקסט שאנחנו מכניסים, כשהמסמך כותב אותם מעוגלים: פותח אחרי רווח, סוגר או גרש בתוך מילה."""
    dq, sq = style
    if not (dq or sq) or not text:
        return text
    out = []
    for i, ch in enumerate(text):
        prev = text[i - 1] if i else ''
        nxt = text[i + 1] if i + 1 < len(text) else ''
        if ch in '"\'' and not (HEB_CHAR.match(prev or ' ') or HEB_CHAR.match(nxt or ' ')):
            opening = not prev or prev.isspace() or prev in '([{/'
            if ch == '"' and dq:
                ch = '“' if opening else '”'
            elif ch == "'" and sq:
                ch = '‘' if opening and nxt and not nxt.isspace() else '’'
        out.append(ch)
    return ''.join(out)


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
    """צמתי טקסט של הפסקה לפי הסדר, בלי תיבות טקסט מקוננות. רק צומת שיושב בתוך ריצה (w:r, או m:r בנוסחה) הוא
    טקסט: w:tab שב-w:pPr/w:tabs הוא עצירת טאב בעיצוב הפסקה ולא תו, ו-pPr ו-rPr (כולל pPrChange ו-rPrChange) אינם
    נסרקים כלל. בלי הכלל הזה para_text ספר את עצירות הטאב, והיחידות (_units) לא, ו-140 מתוך 236 פסקאות בהרצה
    S1b לא היו ניתנות לעריכה (28.10.2026)."""
    def walk(el, anc):
        for ch in el:
            if ch.tag in _SKIP or ch.tag == W + 'p':
                continue
            tag = local(ch.tag)
            if tag in ('pPr', 'rPr'):
                continue
            if tag in ('t', 'delText', 'tab', 'br', 'cr'):
                if anc and anc[-1] == 'r':
                    yield ch, anc
            else:
                yield from walk(ch, anc + (tag,))
    # השורש נכנס לשרשרת, כדי שגם קריאה על ריצה בודדת (_units) תמצא את הטקסט שלה
    yield from walk(p, () if p.tag == W + 'p' else (local(p.tag),))


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


def _revision_of(node, p):
    """(סוג, כותב) של השינוי הקרוב ביותר שעוטף את צומת הטקסט בתוך הפסקה: ('ins'|'del', author) או None.
    מחיקה שלנו של הוספה שלהם נראית כ-del שלנו, כי היא העוטפת הקרובה."""
    out = []
    for a in node.iterancestors():
        if a is p:
            break
        if a.tag in (W + 'ins', W + 'del'):
            out.append((local(a.tag), a.get(W + 'author')))
    return out


def received_reject_text(p, keep=()):
    """הטקסט של פסקה בטיוטה שהתקבלה, אחרי דחיית כל השינויים הפתוחים בה (ההוספות יוצאות, המחיקות חוזרות).
    keep: מחברים שהסימונים הפתוחים שלהם נשארים כמו בטיוטה (ההוספה בטקסט, המחיקה לא): הסימונים שלנו מסבבים
    קודמים, שהם חלק מהמקור. מחיקה שלהם בתוך הוספה שלנו נדחית, וההוספה שלנו נשארת."""
    out = ''
    for n, anc in _text_nodes(p):
        if all((kind == 'del') != (who in keep) for kind, who in _revision_of(n, p)):
            out += _node_text(n)
    return out


def revision_key(e):
    """(סוג, מחבר, תאריך) של סימון מעקב. מזהה את אותו סימון בטיוטה שהתקבלה ובקובץ העבודה גם כש-Word מספר מחדש
    את w:id בשמירה; w:date נשמר."""
    return (local(e.tag), e.get(W + 'author'), e.get(W + 'date'))


def prior_revisions(root, authors):
    """הסימונים הפתוחים בשמותינו (authors) שכבר נמצאים בטיוטה שהתקבלה: הצעות שלנו מסבבים קודמים, שהצד שכנגד לא
    קיבל ולא דחה. הם חלק מהמקור של הסבב, כמו הטיוטה עצמה, ו"דחה הכול" של הסבב אינו מסיר אותם."""
    names = {a for a in authors if a}
    return {revision_key(e) for e in root.iter(W + 'ins', W + 'del') if e.get(W + 'author') in names}


def set_aside_prior(root, prior, label='%s (סבב קודם)'):
    """בעץ שנבדק (לא בקובץ שנשמר): סימון שלנו מסבב קודם (prior) מקבל מחבר נפרד, כדי שכל בדיקה שמחפשת "השינויים
    שלנו בסבב הזה" לפי המחבר תראה אותו כחלק מהטיוטה שהתקבלה. מחזיר את קבוצת השמות החדשים."""
    names = set()
    for e in root.iter(W + 'ins', W + 'del'):
        if revision_key(e) in prior:
            e.set(W + 'author', label % e.get(W + 'author'))
            names.add(e.get(W + 'author'))
    return names


def prior_edit_exists(p, old, new, prior):
    """הכרעה למחוק מחדש (או להחליף מחדש) טקסט שכבר נמחק בסימון פתוח שלנו מסבב קודם, שהצד שכנגד לא קיבל ולא
    דחה. הטקסט הגלוי הוא הנוסח אחרי קבלת הסימונים הפתוחים, ולכן old אינו בו; כאן הוא נמצא בנוסח שבו המחיקות
    הפתוחות שלנו חוזרות. מחזיר (המחיקה הראשונה, האחרונה) כשכל old בתוך מחיקה כזו, ו-new כבר בנוסח הגלוי באותו
    מקום (או ריק): ההכרעה קיימת, ואין מסמנים כפילות. None כש-old אינו שם. UnsupportedEdit כשרק חלק ממנו נמחק,
    או כשהנוסח שבא במקומו אינו new (בדיקה עצמאית S1c, סבב 2, 13(ii), 28.10.2026)."""
    if not old:
        return None
    chars, vis = [], ''
    for n, anc in _text_nodes(p):
        dels = []
        for a in n.iterancestors():
            if a is p:
                break
            if a.tag == W + 'del':
                dels.append(a)
        txt = _node_text(n)
        if not dels and local(n.tag) != 'delText':
            chars += [(c, None, len(vis) + k) for k, c in enumerate(txt)]
            vis += txt
        elif dels and all(revision_key(d) in prior for d in dels):
            chars += [(c, dels[-1], len(vis)) for c in txt]
    full = ''.join(c for c, _, _ in chars)
    if full.count(old) != 1:
        return None
    i0 = full.index(old)
    span = chars[i0:i0 + len(old)]
    gone = [d for _, d, _ in span if d is not None]
    if not gone:
        return None
    if len(gone) < len(span):
        raise UnsupportedEdit('חלק מ-"%s" כבר נמחק בסימון פתוח שלנו מסבב קודם. כתבו את old מול הנוסח הגלוי, אחרי '
                              'קבלת הסימונים הפתוחים מהסבב הקודם' % old[:40])
    at = span[-1][2]
    if new and vis[at:at + len(new)] != new and vis[max(0, at - len(new)):at] != new:
        raise UnsupportedEdit('"%s" כבר נמחק בסימון פתוח שלנו מסבב קודם, והנוסח שבא במקומו אינו "%s". כתבו את '
                              'old מול הנוסח הגלוי, אחרי קבלת הסימונים הפתוחים מהסבב הקודם' % (old[:40], new[:40]))
    return gone[0], gone[-1]


def reject_ours_view(root, author, prior=()):
    """הטיוטה כפי שהתקבלה, אחרי דחיית השינויים שלנו בלבד: הוספה שלנו יוצאת, מחיקה שלנו חוזרת, והשינויים
    הפתוחים של הצד שכנגד נשארים בדיוק כמו בטיוטה שהתקבלה (כמו para_text: ההוספות שלהם בטקסט, המחיקות שלהם
    לא). פסקה שאנחנו הוספנו נעלמת ומתמזגת עם הבאה; סימני פסקה שלהם אינם ממזגים, כמו ב-para_text.
    prior: מפתחות (revision_key) של הסימונים שלנו שכבר היו בטיוטה שהתקבלה (prior_revisions). הם נשארים כמו
    השינויים של הצד שכנגד: "דחה הכול" של הסבב דוחה רק את מה שסומן בסבב הזה.

    verify_roundtrip ו-RT_REJECT השוו את "דחה הכול" ל-para_text של
    הטיוטה שהתקבלה. "דחה הכול" דוחה גם את ההוספות של הצד שכנגד, ולכן כל טיוטה שהגיעה עם שינויים פתוחים
    נכשלה, גם כשההכרעה היחידה הייתה בועה (20.10.2026)."""
    prior = prior or ()

    def now_ours(e):
        return e is not None and e.get(W + 'author') == author and revision_key(e) not in prior

    out, buf = [], ''
    for p in body_paragraphs(root):
        txt = _reject_ours_para(p, now_ours)
        rpr = p.find(W + 'pPr/' + W + 'rPr')
        mark_ins = rpr.find(W + 'ins') if rpr is not None else None
        buf += txt
        if now_ours(mark_ins):
            continue
        out.append(buf)
        buf = ''
    if buf:
        out.append(buf)
    return out


def _reject_ours_para(p, now_ours):
    """הטקסט של פסקה אחת אחרי דחיית השינויים שלנו בסבב הזה בלבד (now_ours), כמו reject_ours_view."""
    txt = ''
    for n, anc in _text_nodes(p):
        revs = []
        for a in n.iterancestors():
            if a is p:
                break
            if a.tag in (W + 'ins', W + 'del'):
                revs.append((local(a.tag), now_ours(a)))
        ours = [k for k, mine in revs if mine]
        theirs = [k for k, mine in revs if not mine]
        if ours:
            keep = ours[0] == 'del'          # מחיקה שלנו חוזרת, הוספה שלנו יוצאת
        else:
            keep = 'del' not in theirs and local(n.tag) != 'delText'
        if keep:
            txt += _node_text(n)
    return txt


# כפילות בנוסח שהכנסנו (S1d-R2, 13(ii), 28.10.2026): רצף של DUP_WORDS מילים שמופיע ב"קבל הכול" של הפסקה יותר פעמים
# מבנוסח שלפני הסבב, ואחת ההופעות בהוספה שלנו מהסבב הזה. בדיקת ההלוך ושוב השוותה לנוסחי היעד, שנגזרו מאותה הכרעה,
# ולכן ההוספה הישנה והחדשה עברו יחד
DUP_WORDS = 12


def duplicated_insertions(p, now_ours, k=DUP_WORDS):
    """הרצפים (k מילים) שהוספה שלנו מהסבב הזה (now_ours) הכפילה בפסקה: מופיעים ב"קבל הכול" יותר פעמים מאשר בנוסח
    שאחרי דחיית השינויים שלנו (reject_ours), ולפחות אחת ההופעות בתוך הוספה שלנו. רשימה ריקה כשאין."""
    chars, flags = [], []
    for n, anc in _text_nodes(p):
        if local(n.tag) == 'delText' or 'del' in anc:
            continue
        mine = False
        for a in n.iterancestors():
            if a is p:
                break
            mine = mine or (a.tag == W + 'ins' and now_ours(a))
        txt = _node_text(n)
        chars.append(txt)
        flags += [mine] * len(txt)
    if not any(flags):
        return []
    acc = ''.join(chars)
    words = [(m.start(), m.end(), m.group(0).lower()) for m in re.finditer(r'\w+', acc)]
    base_w = [w.lower() for w in re.findall(r'\w+', _reject_ours_para(p, now_ours))]
    base = {}
    for i in range(len(base_w) - k + 1):
        g = tuple(base_w[i:i + k])
        base[g] = base.get(g, 0) + 1
    occ = {}
    for i in range(len(words) - k + 1):
        occ.setdefault(tuple(w for _, _, w in words[i:i + k]), []).append((words[i][0], words[i + k - 1][1]))
    return [' '.join(g) for g, spans in occ.items() if len(spans) > 1 and len(spans) > base.get(g, 0)
            and any(any(flags[s:e]) for s, e in spans)]


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


def future_dated(path_or_parts, exclude_authors=(), today=None):
    """בועות וסימוני מעקב שמתוארכים אחרי היום (today, date; ברירת מחדל: היום המקומי), של כל מחבר שאינו ב-exclude_authors
    (השמות שלנו). [{kind: comment/ins/del, author, date}]. לאזהרה בקליטה בלבד: התאריכים אינם משתנים, אבל התשובות שלנו
    יתוארכו היום, ויופיעו ב-Word לפני הבועות שהן עונות להן (S1d-R2, 28.10.2026)."""
    parts = path_or_parts if isinstance(path_or_parts, dict) else read_package(path_or_parts)
    day = (today or _dt.date.today()).isoformat()
    skip = {a for a in exclude_authors or () if a}
    out = []
    for c in read_comments(parts):
        if c.get('author') not in skip and (c.get('date') or '')[:10] > day:
            out.append({'kind': 'comment', 'author': c.get('author'), 'date': c.get('date')})
    if 'word/document.xml' in parts:
        for e in etree.fromstring(parts['word/document.xml']).iter(W + 'ins', W + 'del'):
            d = e.get(W + 'date') or ''
            if e.get(W + 'author') not in skip and d[:10] > day:
                out.append({'kind': local(e.tag), 'author': e.get(W + 'author'), 'date': d})
    return out


def comment_paragraphs(root):
    """לכל מזהה בועה: אינדקס הפסקה (ברשימת body_paragraphs של המסמך המסומן) שבה היא מתחילה."""
    where = {}
    for i, p in enumerate(body_paragraphs(root)):
        for s in p.iter(W + 'commentRangeStart'):
            where.setdefault(s.get(W + 'id'), i)
    return where


def comment_paragraph_spans(root):
    """לכל מזהה בועה: (הפסקה הראשונה, הפסקה האחרונה) שהטווח שלה עובר בהן. בועה של אשכול (כלל 8) מכסה כמה
    פסקאות, והשער סופר אותה ככיסוי של כל אחת מהן."""
    start, end = {}, {}
    for i, p in enumerate(body_paragraphs(root)):
        for s in p.iter(W + 'commentRangeStart'):
            start.setdefault(s.get(W + 'id'), i)
        for e in p.iter(W + 'commentRangeEnd'):
            end[e.get(W + 'id')] = i
    return {cid: (i, max(i, end.get(cid, i))) for cid, i in start.items()}


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


_FIELD_RUN_CHILDREN = _EDITABLE_RUN_CHILDREN | {'fldChar', 'instrText'}


class _Unit:
    __slots__ = ('el', 'text', 'editable', 's', 'e', 'deleted', 'field')

    def __init__(self, el, text, editable, deleted=False, field=False):
        self.el, self.text, self.editable, self.deleted = el, text, editable, deleted
        self.field = field   # ריצה של שדה מורכב (begin עד end), שאפשר למחוק רק בשלמותו
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

    def __init__(self, src, author, initials=None, clock=None, prior_authors=(), prior_keys=(), lang='he'):
        self.parts = read_package(src)
        self.internal_author, self.internal_initials, self.internal_header_text = internal_author(lang)
        self.order = list(self.parts)
        self.root = etree.fromstring(self.parts['word/document.xml'])
        self.body = self.root.find(W + 'body')
        self.paras = body_paragraphs(self.root)
        self.orig_texts = [para_text(p) for p in self.paras]
        self.received_texts = list(self.orig_texts)   # כפי שהתקבלו, לפני שהוכרעו השינויים הפתוחים שלהם
        self.resolved = {}                             # פסקה: accept או reject
        self.author = author
        # הסימונים הפתוחים שלנו מסבבים קודמים: חלק מהטיוטה שהתקבלה, ולא מהסבב הזה (verify_roundtrip). שלנו לפי
        # המחבר, לפי השמות האחרים שלנו בפרופיל (prior_authors), ולפי המפתחות של הסימונים שלנו בקבצים שנשלחו
        # (prior_keys, מ-meta.sent_documents), גם כשבסבב הקודם חתם שם אחר
        self.our_names = {author} | {a for a in prior_authors or () if a}
        sent = {tuple(k) for k in prior_keys or ()}
        self.prior = prior_revisions(self.root, [author] + list(prior_authors or ())) | {
            revision_key(e) for e in self.root.iter(W + 'ins', W + 'del') if revision_key(e) in sent}
        self.existing = []         # הכרעות שכבר קיימות בסימון פתוח שלנו מסבב קודם (prior_edit_exists)
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
        self.quotes = quote_style(self.orig_texts)   # L3: נוסח שמוכנס בגרשיים של המסמך

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
        """היחידות של הפסקה: כל ריצה, לפי הסדר, בכל עומק (היפר-קישור, בקר תוכן, שדה פשוט, smartTag, bdo/dir).
        הטקסט של כל יחידה נמדד באותה פונקציה כמו para_text (_text_nodes), כך שהסכום שלהן שווה לו תמיד. ריצה בתוך
        מכל נעול (_LOCKED_CONTAINERS), ריצה של שדה מורכב (מ-fldChar begin ועד end, כולל תוצאת השדה) וריצה שיש בה
        רכיב שאינו טקסט (הפניה להערת שוליים, ציור, סמל) אינן ניתנות לעריכה, אבל נספרות במקומן.
        הוספה או מחיקה פתוחה שלנו מסבב קודם (self.prior) אינה חוסמת: ריצה בתוך הוספה כזו ניתנת לעריכה (מחיקה בה
        נכתבת כ-w:del חדש בתוך ה-w:ins הקיים, כמו ב-Word), וריצה בתוך מחיקה כזו אינה גלויה ונספרת באורך אפס."""
        units = []
        field = [0]   # עומק השדה המורכב שהריצה הנוכחית בתוכו

        def add_run(r, locked, deleted):
            kids = {local(c.tag) for c in r}
            txt = '' if deleted else ''.join(_node_text(n) for n, anc in _text_nodes(r))
            in_field = field[0] > 0
            has_fc = False
            for fc in r.iter(W + 'fldChar'):
                has_fc = True
                kind = fc.get(W + 'fldCharType')
                if kind == 'begin':
                    field[0] += 1
                elif kind == 'end' and field[0]:
                    field[0] -= 1
            plain = not locked and not deleted and r.tag == W + 'r'
            units.append(_Unit(r, txt, plain and not in_field and kids <= _EDITABLE_RUN_CHILDREN, deleted,
                               field=plain and (in_field or has_fc) and kids <= _FIELD_RUN_CHILDREN))

        def walk(el, locked, deleted):
            for ch in el:
                if ch.tag in _SKIP:
                    continue
                tag = local(ch.tag)
                if tag in ('pPr', 'rPr', 'sdtPr', 'sdtEndPr'):
                    continue
                if tag == 'r':
                    add_run(ch, locked, deleted)
                elif tag in ('ins', 'del') and revision_key(ch) in self.prior:
                    walk(ch, locked, deleted or tag == 'del')
                elif tag in _REVISION_CONTAINERS:
                    raise UnsupportedEdit('בפסקה יש %s' % self._whose(ch))
                else:
                    walk(ch, locked or tag in _LOCKED_CONTAINERS, deleted)

        walk(p, False, False)
        pos = 0
        for u in units:
            u.s, pos = pos, pos + len(u.text)
            u.e = pos
        if ''.join(u.text for u in units) != para_text(p):
            raise UnsupportedEdit('מבנה הפסקה אינו נתמך (טקסט מחוץ לריצות)')
        return units

    # ----------------------------------------------------------------- השינויים הפתוחים של הצד שכנגד
    # בסבב 2 ואילך השינויים שלהם יושבים בדיוק בסעיפים שעונים עליהם, והמנוע סירב לסמן בפסקה כזו
    # (UnsupportedEdit), ולכן ההכרעות החשובות של הסבב נמסרו לסימון ידני (הרצה חיה, 20.10.2026). עכשיו,
    # כמו עורך דין ב-Word, השינוי שלהם בפסקה מוכרע קודם: נדחה (reject) או מתקבל (accept), ועליו
    # מסמנים את השינוי שלנו. 
    def _their(self, el):
        """סימון של הצד שכנגד: לא בשמנו, ולא סימון שלנו מסבב קודם (self.prior), גם כשנחתם בשם אחר שלנו."""
        return el.get(W + 'author') not in self.our_names and revision_key(el) not in self.prior

    def _now_ours(self, el):
        return el is not None and el.get(W + 'author') == self.author and revision_key(el) not in self.prior

    def _whose(self, el):
        """תיאור הסימון שחוסם, להודעת "לא סומנה": שלנו מסבב קודם או של הצד שכנגד, עם המחבר והתאריך. בהרצה S1c
        (סבב 2, 13(ii)) ההודעה ייחסה לצד שכנגד הוספה פתוחה שלנו מסבב 1."""
        kind = {'ins': 'הוספה', 'del': 'מחיקה', 'moveFrom': 'העברה', 'moveTo': 'העברה'}.get(local(el.tag), 'סימון')
        who = '%s, %s' % (el.get(W + 'author') or '?', el.get(W + 'date') or '?')
        if not self._their(el):
            return '%s פתוחה שלנו מסבב קודם (%s), שהמנוע אינו עורך בתוכה: לסמן ידנית' % (kind, who)
        return '%s פתוחה של הצד שכנגד (%s): להכריע אותה (their_changes) לפני הסימון' % (kind, who)

    def has_their_revisions(self, idx):
        p = self.paras[idx]
        return any(self._their(e) for e in p.iter(W + 'ins', W + 'del', W + 'moveFrom', W + 'moveTo'))

    def snapshot_para(self, idx):
        import copy
        return copy.deepcopy(self.paras[idx]), self.orig_texts[idx], self.resolved.get(idx)

    def restore_para(self, idx, snap):
        """מחזיר פסקה למצב שלפני resolve_theirs: הכרעה שלא סומנה אינה מוחלת, גם לא חלקית."""
        el, text, mode = snap
        cur = self.paras[idx]
        cur.getparent().replace(cur, el)
        self.paras[idx] = el
        self.orig_texts[idx] = text
        if mode is None:
            self.resolved.pop(idx, None)
        else:
            self.resolved[idx] = mode

    def resolve_theirs(self, idx, mode):
        """מכריע את השינויים הפתוחים של הצד שכנגד בפסקה: reject מוחק את ההוספות שלהם ומחזיר את המחיקות
        שלהם לטקסט רגיל; accept משאיר את ההוספות כטקסט רגיל ומוחק את מה שמחקו. כמו "דחה" ו"קבל" ב-Word,
        ההכרעה עצמה אינה מסומנת; השינוי שלנו מסומן אחריה, מול הטקסט שנוצר. עוגני ההערות שלהם נשמרים."""
        if mode not in ('accept', 'reject'):
            raise UnsupportedEdit('their_changes: %r אינו accept או reject' % (mode,))
        p = self.paras[idx]
        mark = p.find(W + 'pPr/' + W + 'rPr')
        if mark is not None and any(m is not None and self._their(m)
                                    for m in (mark.find(W + 'ins'), mark.find(W + 'del'))):
            raise UnsupportedEdit('הצד שכנגד פיצל או איחד כאן פסקאות: לסמן ידנית')
        if any(self._their(e) for e in p.iter(W + 'moveFrom', W + 'moveTo')):
            raise UnsupportedEdit('הצד שכנגד העביר כאן טקסט ממקום למקום: לסמן ידנית')
        anchors = (W + 'commentRangeStart', W + 'commentRangeEnd', W + 'bookmarkStart', W + 'bookmarkEnd')
        for e in list(p.iter(W + 'ins', W + 'del')):
            parent = e.getparent()
            if parent is None or parent.tag == W + 'rPr' or not self._their(e):
                continue
            keep = (e.tag == W + 'ins') == (mode == 'accept')
            pos = parent.index(e)
            if keep:
                if e.tag == W + 'del':
                    for x in e.iter(W + 'delText'):
                        x.tag = W + 't'
                    for x in e.iter(W + 'delInstrText'):
                        x.tag = W + 'instrText'
                moved = list(e)
            else:
                # הטקסט יוצא, אבל עוגני ההערות והסימניות שלהם נשארים במקומם
                moved = [x for x in e.iter() if x.tag in anchors] + \
                        [r for r in e.iter(W + 'r') if r.find(W + 'commentReference') is not None]
            for ch in moved:
                parent.insert(pos, ch)
                pos += 1
            parent.remove(e)
        # הוספה שלנו מסבב קודם שכל תוכנה היה המחיקה שלהם, ונשארה ריקה אחרי קבלה: אין סימון ריק בקובץ
        for e in list(p.iter(W + 'ins', W + 'del')):
            if e.getparent() is not None and e.getparent().tag != W + 'rPr' and not len(e) and not self._their(e):
                e.getparent().remove(e)
        self.orig_texts[idx] = para_text(p)
        self.resolved[idx] = mode
        return self.orig_texts[idx]

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
        target = match_quotes(target, self.quotes)
        if target == orig:
            raise UnsupportedEdit('נוסח היעד זהה לנוסח שהתקבל')
        ops = [(o[0], o[1], o[2], o[3], 'all') for o in char_ops(orig, target)]
        self._apply_ops(idx, ops, {'all': (external, internal)})
        self.targets[idx] = target
        return target

    def replace_span(self, idx, old, new, external=None, internal=None):
        return self.edit_spans(idx, [(old, new, external, internal)])

    def edit_spans(self, idx, spans, dry_run=False):
        """כמה החלפות באותה פסקה, בסימון אחד. spans: (old, new, external, internal). כל בועה מעוגנת לטווח שלה.
        dry_run: רק בודק שאפשר לסמן (UnsupportedEdit כשלא), בלי לגעת בפסקה."""
        self._check_idx(idx)
        tagged = [(self._absorb_prior_ins(idx, old, match_quotes(new, self.quotes)), match_quotes(new, self.quotes),
                   's%d' % k) for k, (old, new, _, _) in enumerate(spans)]
        ops, target = span_ops(self.orig_texts[idx], tagged)
        if dry_run:
            self._check_ops(idx, ops)
            return target
        bubbles = {'s%d' % k: (ext, intl) for k, (_, _, ext, intl) in enumerate(spans)}
        self._apply_ops(idx, ops, bubbles)
        self.targets[idx] = target
        return target

    def _prior_ins_ranges(self, idx):
        """הטווחים (התחלה, סוף) בנוסח הנוכחי של הפסקה שיושבים בהוספה פתוחה שלנו מסבב קודם (self.prior), כולל טקסט
        שחזר אליה כשהמחיקה שלהם בתוכה נדחתה (resolve_theirs)."""
        out, pos = [], 0
        for n, anc in _text_nodes(self.paras[idx]):
            if local(n.tag) == 'delText' or 'del' in anc:
                continue
            txt = _node_text(n)
            inside = False
            for a in n.iterancestors():
                if a is self.paras[idx]:
                    break
                inside = inside or (a.tag == W + 'ins' and revision_key(a) in self.prior)
            if inside and txt:
                if out and out[-1][1] == pos:
                    out[-1][1] = pos + len(txt)
                else:
                    out.append([pos, pos + len(txt)])
            pos += len(txt)
        return [tuple(r) for r in out]

    def _absorb_prior_ins(self, idx, old, new):
        """S1d-R2, 13(ii) (28.10.2026): המחיקה שלהם בתוך הוספה פתוחה שלנו מסבב קודם נדחתה (their_changes: reject), ולכן
        ההוספה שלנו חזרה לנוסח. replace_span ש-old שלו צמוד אליה, ו-new שלו הוא גרסה שלה (רוב המילים שלה ב-new),
        מחליף גם אותה: ההבדל מסומן בתוך ההוספה הקיימת, ואין שתי הוספות (הישנה והחדשה) זו לצד זו. מחזיר את old,
        מורחב כשצריך."""
        orig = self.orig_texts[idx]
        if not old or not new or orig.count(old) != 1:
            return old
        i0 = orig.index(old)
        i1 = i0 + len(old)
        lo, hi = i0, i1
        for s, e in self._prior_ins_ranges(idx):
            if s < i1 and e > i0:
                continue
            if s >= i1 and not orig[i1:s].strip():
                cand = (i0, e)
            elif e <= i0 and not orig[e:i0].strip():
                cand = (s, i1)
            else:
                continue
            wa, wb = re.findall(r'\w+', orig[s:e].lower()), re.findall(r'\w+', new.lower())
            if len(wa) < 4:
                continue
            # גרסה שלה: רוב המילים של הקצר מבין השניים נמצאות בארוך, ולפחות שש מילים משותפות (ניסוח מחדש של כל ההצעה,
            # כמו ב-S1d-R2, משתף כשני שלישים מהמילים; "notify <party>" לבדו אינו גרסה שלה)
            same = sum(b.size for b in difflib.SequenceMatcher(None, wa, wb, autojunk=False).get_matching_blocks())
            if same >= max(6, 0.5 * min(len(wa), len(wb))):
                lo, hi = min(lo, cand[0]), max(hi, cand[1])
        return orig[lo:hi]

    def _check_ops(self, idx, ops):
        """היחידות של הפסקה, אחרי בדיקה שאף שינוי אינו נוגע בטווח נעול. ריצות נעולות סמוכות (שדה מורכב על כל
        ריצותיו) הן טווח אחד, כך שאין הוספה בין שתי ריצות של אותו שדה."""
        units = self._units(self.paras[idx])
        blocks, cur = [], None
        for u in units:
            if u.editable:
                cur = None
            elif cur is None:
                cur = [u.s, u.e, [u]]
                blocks.append(cur)
            else:
                cur[1] = u.e
                cur[2].append(u)
        self._field_del = {}
        for op, a0, a1, txt, tag in ops:
            for s, e, us in blocks:
                if e <= s:
                    continue
                if op == 'delete' and a0 < e and a1 > s:
                    # שדה מורכב (למשל הפניה לסעיף) שהמחיקה מכסה בשלמותו נמחק על כל ריצותיו, כמו ש-Word מוחק שדה.
                    # מחיקה של חלק משדה, או של אובייקט נעול אחר, אינה נתמכת
                    if a0 <= s and a1 >= e and all(u.field for u in us):
                        for u in us:
                            self._field_del[id(u)] = tag
                        continue
                    raise UnsupportedEdit('השינוי נוגע בשדה או באובייקט נעול בפסקה %d' % idx)
                if op == 'insert' and s < a0 < e:
                    raise UnsupportedEdit('הוספה בתוך שדה נעול בפסקה %d' % idx)
        if not any(u.editable for u in units):
            raise UnsupportedEdit('אין בפסקה %d ריצה שאפשר לערוך' % idx)
        return units

    def _apply_ops(self, idx, ops, bubbles):
        p = self.paras[idx]
        units = self._check_ops(idx, ops)
        editable = [u for u in units if u.editable]

        def owner(pos):
            for u in editable:
                if u.s < pos <= u.e:
                    return u
            for u in editable:
                if u.s >= pos:
                    return u
            return editable[-1]

        assigned, style_of = {}, {}
        for k, o in enumerate(ops):
            if o[0] == 'insert':
                assigned[k] = owner(o[1])
                # החלפה (מחיקה ומיד אחריה הוספה): הטקסט שהוכנס יורש את העיצוב של הריצה שהוא מחליף, הריצה הראשונה
                # בטווח שנמחק שיש בה טקסט, ולא של הריצה שבסוף הטווח (L2: שם במקום "X" מודגש יצא לא מודגש)
                prev = ops[k - 1] if k else None
                if prev is not None and prev[0] == 'delete' and prev[2] == o[1]:
                    src = next((u for u in editable if u.s < prev[2] and u.e > prev[1]
                                and u.text[max(prev[1], u.s) - u.s:min(prev[2], u.e) - u.s].strip()), None)
                    if src is not None:
                        style_of[k] = src
        made = {}  # tag -> [elements]
        rtl_para = self._para_rtl(p)
        for u in units:
            if id(u) in self._field_del:
                d = self._rev('del')
                u.el.addprevious(d)
                for t in u.el.findall(W + 't'):
                    t.tag = W + 'delText'
                    t.set(XML_SPACE, 'preserve')
                for t in u.el.findall(W + 'instrText'):
                    t.tag = W + 'delInstrText'
                d.append(u.el)
                made.setdefault(self._field_del[id(u)], []).append(d)
                continue
            if not u.editable or u.e == u.s:
                continue
            rpr = u.el.find(W + 'rPr')
            pieces = []
            for k, (op, a0, a1, txt, tag) in enumerate(ops):
                if op == 'insert':
                    if assigned[k] is u:
                        src = style_of.get(k)
                        el = self._ins_el(src.el.find(W + 'rPr') if src is not None else rpr, txt, rtl_para)
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
            for el in pieces:
                if el.tag == W + 'ins' and el.getparent().tag == W + 'ins':
                    self._split_prior_ins(el)
        for tag, els in made.items():
            ext, intl = bubbles.get(tag, (None, None))
            self._anchor(els[0], els[-1], ext, intl, ref_wrap=None)
        self._edited.add(idx)
        self.clock.tick()

    def _split_prior_ins(self, el):
        """הוספה חדשה שנפלה בתוך הוספה פתוחה שלנו מסבב קודם: ההוספה הקודמת מתפצלת סביבה (אותו מחבר ואותו תאריך,
        מזהה חדש לחלק השני), וההוספה החדשה יושבת ביניהן, כך שאין w:ins בתוך w:ins ו"דחה" של כל אחת דוחה רק אותה."""
        prior = el.getparent()
        tail = list(el.itersiblings())
        if tail:
            second = etree.Element(prior.tag, attrib=dict(prior.attrib))
            second.set(W + 'id', self._id())
            for x in tail:
                second.append(x)
            prior.addnext(second)
        prior.addnext(el)
        if not len(prior):
            prior.getparent().remove(prior)

    def delete_paragraph(self, idx, external=None, internal=None):
        """מחיקת פסקה שלמה עם סימן הפסקה. כל ריצה נמחקת במקומה, גם בתוך היפר-קישור, בקר תוכן או שדה: שדה מורכב
        נמחק על כל ריצותיו (instrText הופך ל-delInstrText, כמו ש-Word כותב), ושדה פשוט (fldSimple) מומר קודם לשדה
        מורכב שווה ערך. הפניה להערת שוליים וציור נמחקים עם הפסקה. רק נוסחה (oMath) אינה נמחקת כאן."""
        self._check_idx(idx)
        p = self.paras[idx]
        units = self._units(p)
        if any(u.el.tag != W + 'r' and u.text for u in units):
            raise UnsupportedEdit('פסקה %d כוללת נוסחה, ואינה נמחקת בשלמותה' % idx)
        for fs in list(p.iter(W + 'fldSimple')):
            self._expand_fld_simple(fs)
        units = self._units(p)
        made = []
        for u in units:
            r = u.el
            kids = [local(c.tag) for c in r if local(c.tag) != 'rPr']
            if not kids or kids == ['commentReference'] or u.deleted:
                continue   # ריצה ריקה, ההפניה לבועה קיימת, או טקסט שכבר נמחק אצלנו בסבב קודם: נשארות
            d = self._rev('del')
            r.addprevious(d)
            r.getparent().remove(r)
            for t in r.findall(W + 't'):
                t.tag = W + 'delText'
                t.set(XML_SPACE, 'preserve')
            for t in r.findall(W + 'instrText'):
                t.tag = W + 'delInstrText'
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

    @staticmethod
    def _expand_fld_simple(fs):
        """שדה פשוט (w:fldSimple) לשדה מורכב שווה ערך במקומו: begin, instrText, separate, התוצאה ו-end. כך אפשר
        למחוק אותו בעקוב אחר שינויים כמו ש-Word מוחק שדה."""
        runs = [r for r in fs if r.tag == W + 'r']
        rpr = runs[0].find(W + 'rPr') if runs else None

        def run(kind=None, instr=None):
            r = etree.Element(W + 'r')
            if rpr is not None:
                r.append(copy.deepcopy(rpr))
            if instr is not None:
                it = etree.SubElement(r, W + 'instrText')
                it.set(XML_SPACE, 'preserve')
                it.text = instr
            else:
                fc = etree.SubElement(r, W + 'fldChar')
                fc.set(W + 'fldCharType', kind)
            return r

        begin = run('begin')
        fc = begin.find(W + 'fldChar')
        for k in ('fldLock', 'dirty'):
            if fs.get(W + k) is not None:
                fc.set(W + k, fs.get(W + k))
        data = fs.find(W + 'fldData')
        if data is not None:
            fs.remove(data)
            fc.append(data)
        new = [begin, run(instr=fs.get(W + 'instr') or ''), run('separate')] + list(fs) + [run('end')]
        parent, pos = fs.getparent(), fs.getparent().index(fs)
        parent.remove(fs)
        for k, el in enumerate(new):
            parent.insert(pos + k, el)

    def insert_paragraph(self, after_idx, text, number=None, template_idx=None, external=None, internal=None):
        """פסקה חדשה אחרי פסקת העוגן (ואחרי פסקאות שכבר נוספו אחריה). pPr מהתבנית (ברירת מחדל: העוגן),
        סימן הפסקה מסומן הוספה, והמספר המוקלד (כשיש) נכנס כטקסט באותה תבנית של הנייר שלהם."""
        if not 0 <= after_idx < len(self.paras):
            raise UnsupportedEdit('אין פסקת עוגן %s' % after_idx)
        if not text or not text.strip():
            raise UnsupportedEdit('אין מוסיפים פסקה ריקה')
        text = match_quotes(text, self.quotes)
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
        # פסקה חדשה בעברית מקבלת w:bidi משלה, גם כשפסקת התבנית בנייר שלהם נכתבה בלי bidi ובלי סגנון RTL: אחרת
        # Word מציג אותה משמאל לימין. יישור לשמאל מוחלף ביישור לימין; יישור לשני הצדדים נשאר
        if len(HEB_CHAR.findall(text)) >= len(re.findall('[A-Za-z]', text)) and HEB_CHAR.search(text):
            rtl_para = True
            b = ppr.find(W + 'bidi')
            if b is None:
                etree.SubElement(ppr, W + 'bidi')
            elif b.get(W + 'val') in ('0', 'false'):
                b.attrib.pop(W + 'val')
            jc = ppr.find(W + 'jc')
            if jc is not None and jc.get(W + 'val') in ('left', 'start'):
                jc.set(W + 'val', 'right')
            fix_schema_order(ppr)
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
                                       (self.internal_author, self.internal_initials, internal)):
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
        """נוסחי היעד אחרי "קבל הכול". סימן פסקה שהצד שכנגד מחק ונשאר פתוח (איחוד פסקאות שלהם) מתקבל גם הוא,
        ולכן הפסקה מתמזגת עם הבאה, כמו ב-paragraph_views. בלי זה כל טיוטה עם איחוד פסקאות פתוח נכשלה בבדיקת
        ההלוך ושוב, גם בלי אף הכרעה."""
        out, buf = [], ''
        for i, t in enumerate(self.orig_texts):
            tgt = self.targets.get(i, t)
            items = [(tgt, self._their_mark_deleted(i))] if tgt is not None else []
            items += [(txt, False) for _, txt in self.inserted.get(i, [])]
            for txt, merge in items:
                buf += txt
                if not merge:
                    out.append(buf)
                    buf = ''
        if buf:
            out.append(buf)
        return out

    def _their_mark_deleted(self, idx):
        rpr = self.paras[idx].find(W + 'pPr/' + W + 'rPr')
        d = rpr.find(W + 'del') if rpr is not None else None
        # סימן פסקה שנמחק לפני הסבב הזה (שלהם, או שלנו מסבב קודם) ונשאר פתוח: "קבל הכול" ממזג
        return d is not None and not self._now_ours(d)

    def verify_roundtrip(self):
        """[] כשהכול תקין. אחרת רשימת כשלים: (view, index, expected, got)."""
        self.finalize()
        fails = []
        for view, expected in (('accept', self.expected_accept()), ('reject', self.orig_texts)):
            # "דחה" הוא דחיית השינויים שלנו בסבב הזה בלבד: השינויים הפתוחים של הצד שכנגד, והסימונים הפתוחים שלנו
            # מסבבים קודמים, נשארים כפי שהתקבלו
            got = paragraph_views(self.root, view) if view == 'accept' else reject_ours_view(self.root, self.author,
                                                                                              self.prior)
            if got != expected:
                for i in range(max(len(got), len(expected))):
                    g = got[i] if i < len(got) else None
                    e = expected[i] if i < len(expected) else None
                    if g != e:
                        fails.append((view, i, e, g))
                        break
        # כפילות שההכרעה עצמה יצרה (הוספה ישנה וחדשה זו לצד זו): נוסחי היעד נגזרים מאותה הכרעה ואינם מגלים אותה
        for i in sorted(self._edited):
            dup = duplicated_insertions(self.paras[i], self._now_ours)
            if dup:
                fails.append(('duplicate', i, '', dup[0]))
        ours = [h for e in self.root.iter(W + 'ins') if e.get(W + 'author') == self.author
                for h in e.iter(W + 'highlight')]
        if ours:
            fails.append(('highlight', None, 0, len(ours)))  # צבע בטקסט שהכנסנו; הצבע של הנייר שלהם נשאר כמו שהוא
        return fails

    # ----------------------------------------------------------------- חלקי החבילה
    def _used_para_ids(self):
        used = set()
        for data in self.parts.values():
            if isinstance(data, (bytes, bytearray)) and b'paraId' in data:
                used.update(m.upper() for m in re.findall(rb'paraId="([0-9A-Fa-f]{8})"', data))
        return used

    def _comments_xml(self):
        if self._base_comments:
            root = etree.fromstring(self._base_comments)
        else:
            root = etree.Element(W + 'comments', nsmap={'w': W_NS})
        if W14_NS not in root.nsmap.values():
            # w14:paraId לכל פסקה בבועה (L4): בלעדיו התשובה בשרשור (commentsExtended) אינה מוצאת את הבועה
            nsmap = dict(root.nsmap)
            nsmap['w14'] = W14_NS
            nsmap.setdefault('mc', MC_NS)
            new = etree.Element(root.tag, nsmap=nsmap)
            for k, v in root.attrib.items():
                new.set(k, v)
            for ch in list(root):
                new.append(ch)
            root = new
        ign = (root.get(MC_IGNORABLE) or '').split()
        if 'w14' not in ign:
            root.set(MC_IGNORABLE, ' '.join(ign + ['w14']))
        used = self._used_para_ids()

        def para_id():
            while True:
                pid = ('%08X' % secrets.randbits(31)).encode()
                if pid not in used and pid != b'00000000':
                    used.add(pid)
                    return pid.decode()
        for cid, author, initials, text, date in self.comments:
            c = etree.SubElement(root, W + 'comment')
            c.set(W + 'id', cid)
            c.set(W + 'author', author)
            c.set(W + 'date', date)
            c.set(W + 'initials', initials)
            rtl_c = len(HEB_CHAR.findall(text)) >= len(re.findall('[A-Za-z]', text))  # בועה באנגלית: LTR
            for k, line in enumerate(text.split('\n')):
                p = etree.SubElement(c, W + 'p')
                p.set('{%s}paraId' % W14_NS, para_id())
                p.set('{%s}textId' % W14_NS, '77777777')
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

    def _next_rid(self):
        ids = [int(x) for x in re.findall(rb'Id="rId(\d+)"', self.parts['word/_rels/document.xml.rels'])]
        return 'rId%d' % (max(ids or [0]) + 1)

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
        if self.internal_author == INTERNAL_AUTHOR:
            etree.SubElement(rp, W + 'rtl')
        t = etree.SubElement(r, W + 't')
        t.text = self.internal_header_text
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
            for tag in ('Template', 'TotalTime', 'Company', 'Manager', 'Pages', 'Lines'):
                app = re.sub(r'\s*<%s>[^<]*</%s>' % (tag, tag), '', app)
                app = re.sub(r'\s*<%s/>' % tag, '', app)
            # L4: שם המסמך שלהם (TitlesOfParts, ואיתו HeadingPairs שסופר אותו) נמחק, והספירות מחושבות מחדש מהנוסח
            # אחרי "קבל הכול". עמודים ושורות אי אפשר לחשב בלי עימוד, ולכן הם נמחקים, ו-Word מחשב אותם בפתיחה
            for tag in ('HeadingPairs', 'TitlesOfParts'):
                app = re.sub(r'\s*<%s>.*?</%s>' % (tag, tag), '', app, flags=re.S)
                app = re.sub(r'\s*<%s/>' % tag, '', app)
            acc = paragraph_views(self.root, 'accept')
            text = '\n'.join(acc)
            counts = {'Words': len(text.split()), 'Characters': len(re.sub(r'\s', '', text)),
                      'CharactersWithSpaces': len(text.replace('\n', '')), 'Paragraphs': sum(1 for t in acc if t.strip())}
            for tag, n in counts.items():
                app = re.sub(r'<%s>[^<]*</%s>' % (tag, tag), '<%s>%d</%s>' % (tag, n, tag), app)
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

    def _highlight_areo(self):
        """סעיף AREO: מירקור צהוב על הנוסח שהכנסנו בפסקאות שבטווח של הבועה הפנימית עם התווית, ובלי הוספה, על מה
        שמחקנו בהן. רק בקובץ העבודה: strip_internal מסיר אותו בעותק למשלוח."""
        ids = {c[0] for c in self.comments if c[1] in INTERNAL_AUTHORS
               and str(c[3] or '').strip().startswith(AREO_LABEL_PREFIXES)}
        for p in areo_paragraphs(self.root, ids):
            ins, dels = _revision_runs(p, self.author)
            for r in ins or dels:
                rpr = r.find(W + 'rPr')
                if rpr is None:
                    rpr = etree.Element(W + 'rPr')
                    r.insert(0, rpr)
                if rpr.find(W + 'highlight') is None:
                    h = etree.SubElement(rpr, W + 'highlight')
                    h.set(W + 'val', AREO_HIGHLIGHT)
                    fix_schema_order(rpr)

    def to_bytes(self, internal_header=True):
        self.finalize()
        self._highlight_areo()
        if self.comments:
            self.parts[COMMENTS_PART] = self._comments_xml()
            self._add_rel(self._next_rid(), 'comments', 'comments.xml')   # מזהה בסגנון Word, ולא rIdCm (L4)
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
    doc = etree.fromstring(parts['word/document.xml'])
    if COMMENTS_PART in parts:
        cx = etree.fromstring(parts[COMMENTS_PART])
        # סעיף AREO: המירקור הצהוב שהוספנו בקובץ העבודה יוצא עם הבועה הפנימית שלו
        for p in areo_paragraphs(doc, _areo_comment_ids(cx)):
            ins, dels = _revision_runs(p)
            for r in ins + dels:
                rpr = r.find(W + 'rPr')
                for h in list(rpr.findall(W + 'highlight')) if rpr is not None else ():
                    if h.get(W + 'val') == AREO_HIGHLIGHT:
                        rpr.remove(h)
        for c in cx.findall(W + 'comment'):
            if c.get(W + 'author') in INTERNAL_AUTHORS:
                drop.add(c.get(W + 'id'))
                cx.remove(c)
        parts[COMMENTS_PART] = etree.tostring(cx, xml_declaration=True, encoding='UTF-8', standalone=True)
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
                'conforms_to': {'type': 'string', 'description': 'עם conforming: ההכרעה (או הסעיף הפתוח) שהתיקון '
                                                                 'העקבי נובע ממנה. אינו פתיחה מחדש של סעיף מוסכם '
                                                                 '(S1d-R2)'},
                'their_rejected': {'type': 'array', 'description': 'סבב המשך: הרכיבים שהצד השני דחה במפורש, כל אחד '
                                                                  'מחרוזת או {component, terms, red_line}. מדרגת '
                                                                  'ביניים מוותרת על מה שאינו בקו האדום (S1d-R2)'},
                'carried_from': {'type': 'object', 'description': 'הכרעה מהסבב הקודם שהועברה לפסקה שלא השתנתה '
                                                                  '(round_tools.py carry): {round, id, para, op}'},
                'structural': {'type': 'boolean', 'description': 'כותרת פרק או מבנה. אינו נספר בבקשות (4.9, שינוי 89), '
                                                                  'ומקבל בועה קצרה'},
                'decision_code': {'enum': ['A1', 'A2', 'A3', 'R1', 'R2', 'R3', 'N1']},
                'their_changes': {'enum': ['reject', 'accept', 'keep'],
                                  'description': 'פסקה עם שינויים פתוחים של הצד שכנגד: לדחות אותם ולסמן את שלנו מול '
                                                 'הנוסח שלפניהם, לקבל אותם ולסמן מעליהם, או להשאיר אותם פתוחים (בועה '
                                                 'בלבד). בלי השדה: קבלה ב-A1 עד A3, keep ב-comment_only, ודחייה בשאר. '
                                                 'ב-reject, old ו-new_text נכתבים מול הנוסח שלפני השינויים שלהם'},
                'rule_ids': {'type': 'array', 'items': {'type': 'string'}},
                # בדיקות השלמות המבנית
                'cluster_id': {'type': 'string', 'description': 'כלל 8: כל השינויים של אותו כלל באותו סעיף הם אשכול '
                                                                'אחד, עם בועה אחת שמעוגנת על כל הקטע. רק הכרעה אחת '
                                                                'באשכול נושאת external_comment'},
                'regime': {'enum': ['mutuality', 'cost', 'period', 'definition', 'cap_or_exception', 'law_or_forum', 'none'],
                           'description': 'כלל 2: ההכרעה משנה משטר, ולכן כל סעיף שתלוי בה מוכרע באותו סבב. none: נגיעה '
                                          'שאינה משנה משמעות (כתיב, כינוי, מספר הליך)'},
                'dependents': {'type': 'array', 'items': {'type': 'object'},
                               'description': 'כלל 2: {para, decision} (מזהה ההכרעה שמטפלת בו) או {para, keep: true, '
                                              'reason} לכל סעיף תלוי'},
                'fact_source': {'enum': ['profile', 'user_answer', 'agreement'],
                                'description': 'כלל 6: המקור לעובדה על אחד הצדדים שהבועה נשענת עליה'},
                'their_track': {'enum': ['green', 'yellow', 'red'],
                                'description': 'כלל 10: המסלול של הנוסח המקורי שלהם, לפני הסימון'},
                'fallback': {'enum': ['their_wording', 'playbook'],
                             'description': 'כלל 10: עמדת הנסיגה. בנוסח שלהם שבצהוב: their_wording'},
                'policy_gate': {'type': 'object'},
                'safe_wording': {'type': 'object'},
                'mandatory': {'type': 'boolean'},
                # בדיקה עצמאית S1c (28.10.2026)
                'kind': {'enum': ['hidden_text_removal'],
                         'description': 'מחיקה של טקסט מוסתר (vanish) בטיוטה שלהם, עם הבועה הניטרלית '
                                        '(external_comments_guide.md, "טקסט מוסתר שהוסר"). השער בודק ש-old מוסתר '
                                        'בטיוטה שהתקבלה, ואינו דורש שהבועה תקרא בשמם מושגים שבטקסט המוסתר'},
                'silent_change': {'type': 'string', 'description': 'מזהה שינוי שקט מ-silent_changes בקובץ המצב, '
                                                                   'שההכרעה הזו מסמנת (החזרה, או קבלה עם בועה)'},
            }}},
    }}


def validate_decisions(dec):
    """בדיקה בלי ספרייה חיצונית. מחזיר רשימת שגיאות; ריקה כשהקובץ תקין."""
    errs = []
    for k in DECISIONS_SCHEMA['required']:
        if k not in dec:
            errs.append('חסר %s' % k)
    seen = set()
    bubbled = {}
    for d in dec.get('decisions', []):
        if d.get('cluster_id') and d.get('external_comment'):
            bubbled.setdefault(d['cluster_id'], []).append(d.get('id', '?'))
    for cl, ids in sorted(bubbled.items()):
        if len(ids) > 1:
            errs.append('אשכול %s: יותר מבועה חיצונית אחת (%s). לאשכול בועה אחת על כל הקטע' % (cl, ', '.join(ids)))
    # M5: שינוי עקבי באותה פסקה של השינוי העיקרי אינו מקבל בועה נפרדת; הבועה של הפסקה מכסה אותו
    para_bubbled = {d.get('para') for d in dec.get('decisions', []) if d.get('external_comment')
                    and isinstance(d.get('para'), int)}
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
        cl = d.get('cluster_id')
        if op in ('replace', 'replace_span', 'insert_paragraph', 'delete_paragraph') and not d.get('external_comment') \
                and cl and cl in bubbled:
            pass   # כלל 8: הבועה של האשכול נמצאת בהכרעה אחרת, ומכסה גם את השינוי הזה
        elif op in ('replace', 'replace_span') and not d.get('external_comment') and d.get('conforming') \
                and d.get('para') in para_bubbled:
            pass   # M5: שינוי עקבי באותה פסקה, והבועה של השינוי העיקרי בפסקה מכסה אותו
        elif op in ('replace', 'replace_span', 'insert_paragraph', 'delete_paragraph') and not d.get('external_comment'):
            if cl:
                errs.append('%s: לאשכול %s אין בועה חיצונית באף הכרעה' % (did, cl))
            elif d.get('conforming') or d.get('structural'):
                errs.append('%s: שינוי טכני בלי בועה חיצונית קצרה (כל שינוי שהצד שכנגד רואה מקבל בועה)' % did)
            else:
                errs.append('%s: שינוי מהותי בלי בועה חיצונית' % did)
        if op == 'accept' and d.get('decision_code') not in ACCEPT_CODES:
            errs.append('%s: accept רק עם decision_code A1, A2 או A3' % did)
        if op == 'accept' and (d.get('external_comment') or d.get('internal_comment')):
            errs.append('%s: accept הוא בלי סימון ובלי בועה; לבועה בלבד: comment_only' % did)
        if op == 'insert_paragraph' and d.get('structural') and d.get('mandatory'):
            errs.append('%s: כותרת מבנית אינה נושא חובה' % did)
    return errs


def their_changes_mode(d):
    """מה עושים בשינויים הפתוחים של הצד שכנגד בפסקה שההכרעה נוגעת בה. השדה their_changes גובר; בלעדיו:
    בועה בלבד משאירה אותם פתוחים; הכרעת קבלה (A1 עד A3, או op accept) מקבלת אותם; כל הכרעה שמסמנת נוסח
    דוחה אותם ומסמנת את שלנו מול הנוסח שלפניהם (הנוסח שלנו מהסבב הקודם)."""
    if d.get('their_changes'):
        return d['their_changes']
    if d.get('op') == 'comment_only':     # בועה בלבד אינה משנה טקסט: השינוי שלהם נשאר פתוח, כפי שהגיע
        return 'keep'
    if d.get('op') == 'accept' or d.get('decision_code') in ACCEPT_CODES:
        return 'accept'
    return 'reject'


def mark_decisions(doc, dec):
    """מסמן את ההכרעות על TrackedDocx פתוח, בלי בדיקת החוזה. מחזיר not_marked. apply_decisions קורא לה אחרי
    validate_decisions; הבדיקות משתמשות בה כדי לשחזר תגובה ישנה שאינה עומדת בחוזה הנוכחי."""
    not_marked = []
    inserted = {}
    by_para = {}
    for d in dec['decisions']:
        if d['op'] == 'replace_span':
            by_para.setdefault(d['para'], []).append(d)
    for d in dec['decisions']:
        snap = None
        group = None
        try:
            op = d['op']
            para = d.get('para')
            if op == 'replace_span':
                # כל ה-replace_span של הפסקה מוכרעים יחד, בהכרעה הראשונה שלה. הכרעה מאוחרת יותר באותה פסקה כבר
                # סומנה או דווחה שם, כל אחת בנפרד, ולעולם אינה נשמטת בשקט (הרצה S1b, 28.10.2026)
                group = by_para.pop(para, None)
                if group is None:
                    continue
            received = None
            if op != 'insert_paragraph' and isinstance(para, int) and 0 <= para < len(doc.paras) \
                    and doc.has_their_revisions(para):
                mode = their_changes_mode(d)
                if mode != 'keep':
                    received = doc.orig_texts[para]
                    snap = (para, doc.snapshot_para(para))
                    doc.resolve_theirs(para, mode)
            if op == 'replace':
                doc.set_text(d['para'], d['new_text'], d.get('external_comment'), d.get('internal_comment'))
            elif op == 'replace_span':
                bad = _mark_span_group(doc, para, group, received)
                not_marked.extend(bad)
                if snap is not None and len(bad) == len(group):
                    doc.restore_para(*snap)
            elif op == 'insert_paragraph':
                inserted[d['id']] = doc.insert_paragraph(d['after_para'], d['text'], d.get('number'),
                                                         d.get('template_para'), d.get('external_comment'),
                                                         d.get('internal_comment'))
            elif op == 'delete_paragraph':
                doc.delete_paragraph(d['para'], d.get('external_comment'), d.get('internal_comment'))
            elif op == 'accept':
                continue   # לקבל כמו שהוא: אין סימון; הרכיב נכנס לכיסוי דרך state_builder.build_coverage
            else:
                doc.comment_only(d['para'], d.get('external_comment'), d.get('internal_comment'))
        except UnsupportedEdit as e:
            if snap is not None:
                doc.restore_para(*snap)
            for g in group or [d]:
                not_marked.append({'id': g['id'], 'reason': str(e)})
    span_clusters(doc, dec, inserted, {x['id'] for x in not_marked})
    return not_marked


def _mark_span_group(doc, idx, group, received=None):
    """מסמן את כל ה-replace_span של פסקה אחת בסימון אחד. כל עריכה נבדקת קודם לבדה: עריכה שאינה ניתנת לסימון
    מדווחת בנפרד, עם הסיבה שלה, ושאר העריכות באותה פסקה מסומנות בלעדיה. received: הנוסח שהתקבל, כשהשינויים
    הפתוחים של הצד שכנגד בפסקה הוכרעו לפני הסימון. מחזיר את רשימת העריכות שלא סומנו."""
    base = doc.orig_texts[idx] if isinstance(idx, int) and 0 <= idx < len(doc.orig_texts) else None
    ok, bad, existing = [], [], []
    for g in group:
        sp = (g['old'], g['new'], g.get('external_comment'), g.get('internal_comment'))
        try:
            # למחוק מחדש טקסט שהמחיקה הפתוחה שלנו מסבב קודם עדיין עליו: ההכרעה כבר מסומנת, ואין מסמנים כפילות
            if g.get('old') and base is not None and g['old'] not in base:
                hit = prior_edit_exists(doc.paras[idx], g['old'], match_quotes(g.get('new') or '', doc.quotes),
                                        doc.prior)
                if hit:
                    existing.append((g, hit))
                    continue
            # old שנכתב מול הנוסח שלהם, כשהשינויים שלהם נדחו: ההודעה אומרת מה לעשות, ולא רק "לא נמצא"
            if received is not None and g.get('old') and base is not None and g['old'] not in base \
                    and g['old'] in received:
                raise UnsupportedEdit('"%s" הוא מהנוסח של הצד שכנגד, והשינויים שלהם בפסקה נדחו '
                                      '(their_changes: reject). כתבו את old מול הנוסח שלפני השינויים שלהם, '
                                      'או קבעו their_changes: accept' % g['old'][:40])
            doc.edit_spans(idx, [sp], dry_run=True)
            ok.append((g, sp))
        except UnsupportedEdit as e:
            bad.append({'id': g['id'], 'reason': str(e)})
    if ok:
        try:
            doc.edit_spans(idx, [sp for _, sp in ok])
        except UnsupportedEdit as e:
            # כל עריכה תקינה לבדה, אבל יחד אינן מסתדרות (טווחים חופפים): כל אחת מדווחת
            bad += [{'id': g['id'], 'reason': str(e)} for g, _ in ok]
    for g, (first, last) in existing:
        # הבועה של ההכרעה מעוגנת על המחיקה הקיימת, והסימון עצמו אינו משתנה
        doc._anchor(first, last, g.get('external_comment'), g.get('internal_comment'), ref_wrap=None)
        doc.clock.tick()
        doc.existing.append({'id': g['id'], 'para': idx,
                             'note': 'קיימת מסבב קודם: "%s" כבר נמחק בסימון פתוח שלנו (%s, %s), שהצד שכנגד לא קיבל '
                                     'ולא דחה. לא סומנה כפילות' % (g['old'][:40], first.get(W + 'author'),
                                                                   first.get(W + 'date'))})
    return bad


def span_clusters(doc, dec, inserted, skipped=()):
    """כלל 8: הבועה של אשכול נפרשת מתחילת הפסקה הראשונה של האשכול ועד סוף האחרונה,
    כך שבועה אחת מכסה את כל השינויים של אותו כלל באותו סעיף, ואין צורך בבועות הפניה. השער סופר בועה כזו ככיסוי של
    כל פסקה בטווח (comment_paragraph_spans)."""
    clusters = {}
    for d in dec['decisions']:
        if d.get('cluster_id') and d['id'] not in skipped and d['op'] != 'accept':
            clusters.setdefault(d['cluster_id'], []).append(d)
    if not any(len(v) > 1 for v in clusters.values()):
        return
    used = set()
    for members in clusters.values():
        lead = next((d for d in members if d.get('external_comment')), None)
        if lead is None or len(members) < 2:
            continue
        cid = next((c[0] for c in doc.comments if c[1] == doc.author and c[3] == lead['external_comment']
                    and c[0] not in used), None)
        if cid is None:
            continue
        used.add(cid)
        # פסקה שהוספנו עוד אינה בעץ (finalize מכניס אותה אחרי העוגן), ולכן הסדר לוגי: (עוגן, מקום אחריו)
        elems = []
        for d in members:
            key = p = None
            if d['op'] == 'insert_paragraph' and inserted.get(d['id']) is not None:
                p = inserted[d['id']]
                chain = [q for q, _ in doc.inserted.get(d['after_para'], [])]
                key = (d['after_para'], 1 + next((k for k, q in enumerate(chain) if q is p), 0))
            elif isinstance(d.get('para'), int) and 0 <= d['para'] < len(doc.paras):
                p, key = doc.paras[d['para']], (d['para'], 0)
            if p is not None and all(p is not q for _, q in elems):
                elems.append((key, p))
        elems = [p for _, p in sorted(elems, key=lambda kp: kp[0])]
        if len(elems) < 2:
            continue
        first = elems[0]
        last = next((p for p in reversed(elems) if _mark(p) != 'del'), elems[-1])
        trees = [doc.root] + [q for items in doc.inserted.values() for q, _ in items]
        start = next((x for t in trees for x in t.iter(W + 'commentRangeStart') if x.get(W + 'id') == cid), None)
        end = next((x for t in trees for x in t.iter(W + 'commentRangeEnd') if x.get(W + 'id') == cid), None)
        if start is None or end is None:
            continue
        ref = end.getnext()
        run = ref
        if ref is not None and local(ref.tag) in ('ins', 'del'):
            run = next((r for r in ref if r.find(W + 'commentReference') is not None), None)
        if run is None or run.find(W + 'commentReference') is None:
            continue
        start.getparent().remove(start)
        ppr = first.find(W + 'pPr')
        first.insert(list(first).index(ppr) + 1 if ppr is not None else 0, start)
        end.getparent().remove(end)
        if ref is not run:
            ref.remove(run)
            if not len(ref) and ref.getparent() is not None:
                ref.getparent().remove(ref)
        elif run.getparent() is not None:
            run.getparent().remove(run)
        last.append(end)
        mark = _mark(last)
        if mark in ('ins', 'del'):
            wrap = doc._rev(mark)
            wrap.append(run)
            last.append(wrap)
        else:
            last.append(run)


def apply_decisions(received, dec, out_path=None, author=None, initials=None, now=None, internal_header=True,
                    prior_authors=(), prior_keys=(), lang=None):
    """מחיל קובץ הכרעות על הטיוטה שהתקבלה. מחזיר dict: ok, errors, not_marked, existing, verify, expected_accept,
    data (bytes של קובץ העבודה). הכרעה שאינה ניתנת לסימון מדווחת ב-not_marked ואינה מוחלת חלקית. הכרעה שכבר
    קיימת בסימון פתוח שלנו מסבב קודם מדווחת ב-existing, ונחשבת מסומנת. prior_authors ו-prior_keys: השמות האחרים
    שלנו ומפתחות הסימונים שלנו מהקבצים שנשלחו (TrackedDocx)."""
    errs = validate_decisions(dec)
    if errs:
        return {'ok': False, 'errors': errs}
    author = author or dec.get('author')
    clock = RevisionClock(now=now, steps=len(dec['decisions']))
    doc = TrackedDocx(received, author=author, initials=initials or dec.get('initials'), clock=clock,
                      prior_authors=prior_authors, prior_keys=prior_keys, lang=lang or dec.get('lang') or 'he')
    not_marked = mark_decisions(doc, dec)
    verify = doc.verify_roundtrip()
    data = doc.to_bytes(internal_header=internal_header)
    if out_path:
        with open(out_path, 'wb') as f:
            f.write(data)
    return {'ok': not verify and not not_marked, 'errors': [], 'not_marked': not_marked, 'existing': doc.existing,
            'verify': verify, 'expected_accept': doc.expected_accept(), 'original': doc.orig_texts, 'data': data,
            'doc': doc}


def sent_revision_keys(sent_paths, received_paths=()):
    """מפתחות (revision_key) של הסימונים שלנו בקבצים שנשלחו (meta.sent_documents): כל סימון בקובץ שנשלח, חוץ
    מסימונים שכבר היו בטיוטות שהתקבלו (השינויים של הצד שכנגד שהשארנו פתוחים). כך סימון פתוח שחזר אלינו מזוהה
    כשלנו גם כשנחתם בשם אחר מהשם של הסבב הזה. קובץ שאינו נקרא מדולג."""
    def keys(path):
        try:
            root = document_root(path)
        except Exception:  # noqa: BLE001  קובץ חסר או פגום: ההיסטוריה ממנו אינה זמינה
            return set()
        return {revision_key(e) for e in root.iter(W + 'ins', W + 'del')}
    theirs = set()
    for path in received_paths or ():
        theirs |= keys(path)
    out = set()
    for path in sent_paths or ():
        out |= keys(path) - theirs
    return out
