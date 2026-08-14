# -*- coding: utf-8 -*-
"""עקוב אחר שינויים אמיתי (w:ins / w:del) והערות Word (comments.xml) ב-python-docx."""

from docx.oxml.ns import qn, nsmap
from docx.oxml import OxmlElement
from docx.opc.part import Part
from docx.opc.packuri import PackURI
from docx.shared import Pt
import copy

W = nsmap['w']
AUTHOR = "HIGHLAW, יועצת משפטית"
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


# ------------------------------------------------------------------ comments
COMMENTS_XML_HEAD = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
    '<w:comments xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
)
CT_COMMENTS = ("application/vnd.openxmlformats-officedocument"
               ".wordprocessingml.comments+xml")
RT_COMMENTS = ("http://schemas.openxmlformats.org/officeDocument/2006/relationships/comments")

_comments = []


def add_comment(p, text, initials="HL"):
    """מוסיף הערת Word הצמודה לפסקה, בעברית RTL."""
    cid = str(_ids["cmt"]); _ids["cmt"] += 1
    _comments.append((cid, text))
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


def _comment_xml(cid, text):
    paras = []
    for chunk in text.split('\n'):
        runs = ('<w:r><w:rPr><w:rFonts w:ascii="David" w:hAnsi="David" w:cs="David"/>'
                '<w:sz w:val="18"/><w:szCs w:val="18"/><w:rtl/></w:rPr>'
                '<w:t xml:space="preserve">' + _esc(chunk) + '</w:t></w:r>')
        paras.append('<w:p><w:pPr><w:bidi/></w:pPr>' + runs + '</w:p>')
    return ('<w:comment w:id="' + cid + '" w:author="' + _esc(AUTHOR) +
            '" w:initials="HL" w:date="' + DATE + '">' + ''.join(paras) + '</w:comment>')


def _esc(s):
    return (s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
             .replace('"', '&quot;'))


def attach_comments(doc):
    """יוצר את word/comments.xml, מקשר אותו ומוסיף Content-Type."""
    if not _comments:
        return doc
    xml = COMMENTS_XML_HEAD + ''.join(_comment_xml(c, t) for c, t in _comments) + '</w:comments>'
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
