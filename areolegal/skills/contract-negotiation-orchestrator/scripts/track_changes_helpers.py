# -*- coding: utf-8 -*-
"""עקוב אחר שינויים אמיתי (w:ins / w:del) והערות Word (comments.xml) ב-python-docx."""

from docx.oxml.ns import qn, nsmap
from docx.oxml import OxmlElement
from docx.opc.part import Part
from docx.opc.packuri import PackURI
from docx.shared import Pt
import copy

W = nsmap['w']
# שם החותם על ההערות ועל השינויים המסומנים. **חייב להיקבע מהפרופיל בכל הרצה.**
# הערך כאן הוא נפילה אחרונה בלבד; אם הוא מגיע לתוצר, שם עורך הדין לא נמסר.
AUTHOR = "עורך הדין של החברה"
DATE = "2026-08-13T00:00:00Z"
_ids = {"rev": 100, "cmt": 0}


def _rid():
    _ids["rev"] += 1
    return str(_ids["rev"])


def _mk_run(text, ltr=True, strike=False, delete=False, size=10.5):
    r = OxmlElement('w:r')
    rPr = OxmlElement('w:rPr')
    rf = OxmlElement('w:rFonts')
    for a in ('w:ascii', 'w:hAnsi', 'w:cs'):
        rf.set(qn(a), 'David')
    rPr.append(rf)
    sz = OxmlElement('w:sz'); sz.set(qn('w:val'), str(int(size * 2))); rPr.append(sz)
    szc = OxmlElement('w:szCs'); szc.set(qn('w:val'), str(int(size * 2))); rPr.append(szc)
    rtl = OxmlElement('w:rtl'); rtl.set(qn('w:val'), '0' if ltr else '1'); rPr.append(rtl)
    r.append(rPr)
    t = OxmlElement('w:delText' if delete else 'w:t')
    t.set(qn('xml:space'), 'preserve')
    t.text = text
    r.append(t)
    return r


def add_plain(p, text, ltr=True, size=10.5, bold=False):
    r = _mk_run(text, ltr=ltr, size=size)
    if bold:
        r.find(qn('w:rPr')).append(OxmlElement('w:b'))
    p._p.append(r)
    return p


def add_ins(p, text, ltr=True, size=10.5):
    """הוספה בעקוב אחר שינויים."""
    ins = OxmlElement('w:ins')
    ins.set(qn('w:id'), _rid()); ins.set(qn('w:author'), AUTHOR); ins.set(qn('w:date'), DATE)
    ins.append(_mk_run(text, ltr=ltr, size=size))
    p._p.append(ins)
    return p


def add_del(p, text, ltr=True, size=10.5):
    """מחיקה בעקוב אחר שינויים."""
    dele = OxmlElement('w:del')
    dele.set(qn('w:id'), _rid()); dele.set(qn('w:author'), AUTHOR); dele.set(qn('w:date'), DATE)
    dele.append(_mk_run(text, ltr=ltr, delete=True, size=size))
    p._p.append(dele)
    return p


# ------------------------------------------------- קליטת הטיוטה של הצד שכנגד
# הטיוטה שחוזרת מהצד שכנגד כבר מסומנת בעקוב אחר שינויים ובהערות שלו. אי אפשר
# לסמן את הסבב שלנו מעליהם כמו שהם, משתי סיבות:
#
# 1. python-docx רואה רק w:r שהם ילדים ישירים של w:p. טקסט שהצד שכנגד הוסיף
#    יושב בתוך w:ins, ולכן אינו נכלל ב-paragraph.text: פסקה שנקראת אצלו
#    "תוך לא יאוחר מ-48 שעות" נקראת ב-python-docx "תוך לא יאוחר מ- שעות".
#    הציטוט שההכרעה מסתמכת עליו נלקח מ-extract_track_changes, שכן רואה את
#    ההוספות, ולכן שתי התמונות אינן מדברות על אותו טקסט.
# 2. apply_edit מוחק את ה-w:r הישירים בלבד. ה-w:ins של הצד שכנגד היה נשאר
#    בפסקה לצד המחיקה וההוספה שלנו, והטקסט היה נכפל ברגע שמקבלים את השינויים.
#
# לכן הטיוטה נקלטת כפי שעורך דין קולט אותה: מקבלים את השינויים שהצד שכנגד
# הציע, הם הופכים לנוסח הבסיס, והסבב שלנו מסומן מעליו. כך המסמך היוצא קורא
# חד-משמעית: זה מה שהצעתם, וזה מה שאנחנו משנים בו.

_REV_KEEP = ('w:ins', 'w:moveTo')          # הקבלה משאירה את התוכן
_REV_DROP = ('w:del', 'w:moveFrom')        # הקבלה מסירה את התוכן
_REV_RECORD = ('w:pPrChange', 'w:rPrChange', 'w:sectPrChange', 'w:tblPrChange',
               'w:trPrChange', 'w:tcPrChange', 'w:tblGridChange',
               'w:cellIns', 'w:cellDel', 'w:cellMerge')  # רישום עיצוב, בלי תוכן


def _para_mark_deletions(body):
    """פסקאות שסימן הפסקה שלהן נמחק. קבלתן מאחדת פסקה עם זו שאחריה."""
    out = []
    for p in body.iter(qn('w:p')):
        pPr = p.find(qn('w:pPr'))
        rPr = pPr.find(qn('w:rPr')) if pPr is not None else None
        if rPr is not None and rPr.find(qn('w:del')) is not None:
            out.append(p)
    return out


def accept_revisions(doc):
    """מקבל את כל התיקונים שבמסמך, כך שהנוסח המוצע הופך לנוסח הבסיס.

    מחזיר מונים: כמה הוספות ומחיקות נקלטו, וכמה סימני פסקה מחוקים נמצאו.
    איחוד פסקאות אינו מבוצע: הוא משנה את מבנה ההסכם, ולכן הוא מדווח
    לעורך הדין ולא מנוחש. שאר הרישום מוסר, והטקסט נשאר כפי שהצד שכנגד הציע.
    """
    body = doc.element.body
    stats = {"accepted_insertions": 0, "accepted_deletions": 0,
             "paragraph_marks_deleted": len(_para_mark_deletions(body))}

    # מחיקות תחילה: הן מסירות איתן גם הוספה שנמחקה אחר כך, וזו התוצאה הנכונה
    for tag in _REV_DROP:
        for el in list(body.iter(qn(tag))):
            parent = el.getparent()
            if parent is None:
                continue
            if parent.tag == qn('w:rPr'):     # סימן פסקה מחוק: מסירים את הרישום בלבד
                parent.remove(el)
                continue
            parent.remove(el)
            stats["accepted_deletions"] += 1

    # הוספות: התוכן עולה מדרגה ומחליף את עטיפת ה-w:ins
    for tag in _REV_KEEP:
        for el in list(body.iter(qn(tag))):
            parent = el.getparent()
            if parent is None:
                continue
            if parent.tag == qn('w:rPr'):
                parent.remove(el)
                continue
            at = list(parent).index(el)
            for child in reversed(list(el)):
                parent.insert(at, child)
            parent.remove(el)
            stats["accepted_insertions"] += 1

    for tag in _REV_RECORD:
        for el in list(body.iter(qn(tag))):
            parent = el.getparent()
            if parent is not None:
                parent.remove(el)

    return stats


# ------------------------------------------------------------------ comments
# כל החלקים שמרכיבים הערות ב-DOCX. comments.xml לבדו אינו מספיק: הנספחים
# מפנים זה לזה לפי מזהים, ושארית שנשארת אחרי החלפת comments.xml מפנה לריק.
_COMMENT_RELTYPES = (
    "http://schemas.openxmlformats.org/officeDocument/2006/relationships/comments",
    "http://schemas.microsoft.com/office/2011/relationships/commentsExtended",
    "http://schemas.microsoft.com/office/2016/09/relationships/commentsIds",
    "http://schemas.microsoft.com/office/2018/08/relationships/commentsExtensible",
    "http://schemas.microsoft.com/office/2011/relationships/people",
)


def _drop_comment_parts(doc):
    """מנתק את חלקי ההערות הקיימים מהמסמך."""
    for rId, rel in list(doc.part.rels.items()):
        if rel.reltype in _COMMENT_RELTYPES:
            doc.part.drop_rel(rId)


def strip_comments(doc):
    """מסיר את ההערות שהיו בטיוטה, ומחזיר את רשימתן לדיווח.

    שתי סיבות, ושתיהן מחייבות:

    1. attach_comments כותב את comments.xml מחדש, והמזהים שלו מתחילים מאפס.
       בטיוטה אמיתית כבר יש הערות עם מזהים 1, 6, 100 ומעלה, ולכן בועה שלנו
       הייתה נקשרת לעוגן של הצד שכנגד והקובץ היה נפתח משובש.
    2. בטיוטות חוזרות יושבות גם הערות פנימיות של הצד שלנו מסבבים קודמים.
       מסמך שיוצא לצד שכנגד ובו הערה פנימית הוא דליפה.

    המסיר מדווח מה הוסר, כדי שעורך הדין יראה במה בדיוק מדובר.
    """
    removed = []
    try:
        part = doc.part.part_related_by(_COMMENT_RELTYPES[0])
    except KeyError:
        part = None
    if part is not None:
        from docx.oxml import parse_xml
        for c in parse_xml(part.blob).findall(qn('w:comment')):
            text = "".join(t.text or "" for t in c.iter(qn('w:t')))
            removed.append({"author": c.get(qn('w:author')) or "",
                            "date": c.get(qn('w:date')) or "",
                            "text": text.strip()})

    body = doc.element.body
    for tag in ('w:commentRangeStart', 'w:commentRangeEnd'):
        for el in list(body.iter(qn(tag))):
            el.getparent().remove(el)
    for ref in list(body.iter(qn('w:commentReference'))):
        run = ref.getparent()
        run.remove(ref)
        # ריצה שנשארה בלי תוכן היא שארית של העוגן בלבד
        if run.tag == qn('w:r') and not run.findall(qn('w:t')) \
                and not run.findall(qn('w:delText')) and not run.findall(qn('w:drawing')):
            run.getparent().remove(run)

    _drop_comment_parts(doc)
    _ids["cmt"] = 0
    return removed


COMMENTS_XML_HEAD = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
    '<w:comments xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
)
CT_COMMENTS = ("application/vnd.openxmlformats-officedocument"
               ".wordprocessingml.comments+xml")
RT_COMMENTS = ("http://schemas.openxmlformats.org/officeDocument/2006/relationships/comments")

_comments = []


def _initials(name):
    """ראשי תיבות מהשם שנמסר. Word מציג אותם על בועת ההערה."""
    parts = [w for w in (name or "").replace(",", " ").split() if w]
    return ("".join(w[0] for w in parts[:2]) or "עד")[:4]


def add_comment(p, text, initials=None):
    """מוסיף הערת Word הצמודה לפסקה, בעברית RTL."""
    cid = str(_ids["cmt"]); _ids["cmt"] += 1
    _comments.append((cid, text, initials or _initials(AUTHOR)))
    start = OxmlElement('w:commentRangeStart'); start.set(qn('w:id'), cid)
    end = OxmlElement('w:commentRangeEnd'); end.set(qn('w:id'), cid)
    ref_r = OxmlElement('w:r')
    rPr = OxmlElement('w:rPr')
    st = OxmlElement('w:rStyle'); st.set(qn('w:val'), 'CommentReference'); rPr.append(st)
    ref_r.append(rPr)
    ref = OxmlElement('w:commentReference'); ref.set(qn('w:id'), cid)
    ref_r.append(ref)
    p._p.insert(0 if p._p.find(qn('w:pPr')) is None else 1, start)
    p._p.append(end)
    p._p.append(ref_r)
    return cid


def _comment_xml(cid, text, initials="עד"):
    paras = []
    for chunk in text.split('\n'):
        runs = ('<w:r><w:rPr><w:rFonts w:ascii="David" w:hAnsi="David" w:cs="David"/>'
                '<w:sz w:val="18"/><w:szCs w:val="18"/><w:rtl/></w:rPr>'
                '<w:t xml:space="preserve">' + _esc(chunk) + '</w:t></w:r>')
        paras.append('<w:p><w:pPr><w:bidi/></w:pPr>' + runs + '</w:p>')
    return ('<w:comment w:id="' + cid + '" w:author="' + _esc(AUTHOR) +
            '" w:initials="' + _esc(initials) + '" w:date="' + DATE + '">' + ''.join(paras) + '</w:comment>')


def _esc(s):
    return (s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
             .replace('"', '&quot;'))


def attach_comments(doc):
    """יוצר את word/comments.xml, מקשר אותו ומוסיף Content-Type.

    הקובץ נכתב מחדש ואינו מתווסף לקיים, ולכן כל חלק הערות שנשאר מהטיוטה
    מנותק כאן תחילה. בלי זה נוצרים שני חלקים באותו שם, והמזהים מתנגשים.
    """
    if not _comments:
        return doc
    _drop_comment_parts(doc)
    xml = COMMENTS_XML_HEAD + ''.join(_comment_xml(c, t, i) for c, t, i in _comments) + '</w:comments>'
    part = Part(PackURI('/word/comments.xml'), CT_COMMENTS, xml.encode('utf-8'),
                doc.part.package)
    doc.part.relate_to(part, RT_COMMENTS)
    return doc


def enable_track_changes(doc):
    """מפעיל 'עקוב אחר שינויים' בהגדרות המסמך."""
    settings = doc.settings.element
    for tag in ('w:trackChanges',):
        if settings.find(qn(tag)) is None:
            settings.append(OxmlElement(tag))
    return doc
