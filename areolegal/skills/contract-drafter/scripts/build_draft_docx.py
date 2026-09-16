#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""בונה את מסמך הטיוטה ב-Word ישירות מ-draft.json.

**זה המסלול היחיד להפקת טיוטה ב-Word.** אין לכתוב את המסמך ב-python-docx בכל
הרצה, ואין "לשפר" את העיצוב ביד. בנייה ידנית היא מה שגרם לטיוטה לצאת בברירות
המחדל של Word, בלי היררכיה ובלי כיווניות, והיא גם מה שגרם לשלב ההפקה להימשך
עשרות דקות: המודל נאלץ לפלוט סדרתית גם את נוסח ההסכם וגם את קוד הבנייה שלו.
כאן המודל פולט **נתונים בלבד**, והסקריפט עושה את המספור, ההיררכיה, הכיווניות
וסימון החוסרים.

הסקריפט אוכף כיווניות בעצמו. **אין להעביר את התוצר שלו ב-rtl-docx-enforcer:**
מעבר נוסף מייצר שכתוב מלא של המסמך בלי להוסיף דבר.

    python3 build_draft_docx.py --draft Areo-נתונים/draft-<slug>.json \\
        --profile Areo-נתונים/פרופיל-לקוח.json --out "<שם המסמך>.docx"

מבנה draft.json, במלואו. שדה חסר מדולג בשקט; אין שדה חובה מלבד clauses:
    meta{doc_type,title,language,classification,transaction_id,template{},
         parties[{defined_as,name,reg,address,role}],place_date,generated_at}
    recitals[str]  definitions[{term,text}]
    clauses[{number,heading,text,children[...]}]
    annexes[{label,title,text|clauses[]}]
    signatures{note,blocks[{name,by,title}]}
"""
import argparse
import datetime
import io
import json
import re
import sys

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

# ---------- פלטה: מסמך משפטי, לא דוח. מאופקת בכוונה ----------
INK = "16191F"
INK_SOFT = "5B6472"
LINE = "C9CFD6"
NAVY = "12314F"
GAP_BG = "FFF2A8"      # רקע לציון חוסר, כדי שלא ייחתם מסמך עם [להשלים]
FONT = "Arial"

RTL = True             # נקבע מ-meta.language בזמן הבנייה

PPR_ORDER = ["pStyle", "keepNext", "keepLines", "pageBreakBefore", "numPr", "pBdr",
             "shd", "tabs", "bidi", "spacing", "ind", "contextualSpacing", "jc",
             "outlineLvl", "rPr"]

GAP_RX = re.compile(r"(\[[^\[\]]{0,80}\])")


# ---------- כלי XML ----------
def _el(tag, **attrs):
    e = OxmlElement(tag)
    for k, v in attrs.items():
        e.set(qn("w:" + k), v)
    return e


def _local(tag):
    return tag.split("}")[-1]


def ppr_put(p, el):
    """סדר הילדים ב-w:pPr קבוע בסכמת OOXML. אלמנט שמצורף בסוף מתעלמים ממנו בשקט."""
    ppr = p._p.get_or_add_pPr()
    name = _local(el.tag)
    old = ppr.find(qn("w:" + name))
    if old is not None:
        ppr.remove(old)
    idx = PPR_ORDER.index(name) if name in PPR_ORDER else 99
    for child in ppr:
        c = _local(child.tag)
        if (PPR_ORDER.index(c) if c in PPR_ORDER else 99) > idx:
            child.addprevious(el)
            return el
    ppr.append(el)
    return el


def dir_p(p):
    if RTL:
        ppr_put(p, _el("w:bidi"))


def run(p, text, size=11, bold=False, color=INK, italic=False, fill=None, underline=False):
    r = p.add_run(text)
    r.font.name = FONT
    r.font.size = Pt(size)
    r.bold = bold
    r.italic = italic
    r.underline = underline
    r.font.color.rgb = RGBColor.from_string(color)
    rpr = r._r.get_or_add_rPr()
    rf = rpr.find(qn("w:rFonts"))
    if rf is None:
        rf = _el("w:rFonts")
        rpr.insert(0, rf)
    for k in ("ascii", "hAnsi", "cs"):
        rf.set(qn("w:" + k), FONT)
    if fill:
        rpr.append(_el("w:shd", val="clear", color="auto", fill=fill))
    if RTL:
        rpr.append(_el("w:rtl"))
    return r


GAPS = []


def rich(p, text, size=11, bold=False, color=INK):
    """כותב טקסט ומסמן כל ציין חוסר ברקע, כדי שלא ייעלם בקריאה."""
    for part in GAP_RX.split(s(text)):
        if not part:
            continue
        if GAP_RX.fullmatch(part):
            GAPS.append(part)
            run(p, part, size, True, INK, fill=GAP_BG)
        else:
            run(p, part, size, bold, color)
    return p


def para(doc, text="", size=11, bold=False, color=INK, before=0, after=5, line=1.2,
         container=None, align=None, indent=0.0, italic=False):
    p = (container or doc).add_paragraph()
    dir_p(p)
    pf = p.paragraph_format
    pf.space_before = Pt(before)
    pf.space_after = Pt(after)
    pf.line_spacing = line
    pf.alignment = align if align is not None else WD_ALIGN_PARAGRAPH.JUSTIFY
    if indent:
        pf.left_indent = Cm(indent) if not RTL else None
        pf.right_indent = Cm(indent) if RTL else None
    if text:
        run(p, text, size, bold, color, italic)
    return p


def table_borders(tbl, color=LINE, visible=True):
    tpr = tbl._tbl.tblPr
    b = _el("w:tblBorders")
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        b.append(_el("w:" + edge, val="single" if visible else "none",
                     sz="4", space="0", color=color))
    tpr.append(b)
    if RTL:
        tpr.append(_el("w:bidiVisual"))


def cell_text(cell, text, bold=False, size=10.5, color=INK, align=None):
    p = cell.paragraphs[0]
    for r in list(p._p.findall(qn("w:r"))):
        p._p.remove(r)           # cell.text = "" leaves a run with no rPr, hence no w:rtl
    dir_p(p)
    p.paragraph_format.space_before = Pt(3)
    p.paragraph_format.space_after = Pt(3)
    if align is not None:
        p.alignment = align
    # split BEFORE s(): it normalises whitespace and would swallow the newlines
    lines = str(text).split("\n") if text else [""]
    for i, line in enumerate(lines):
        if i:
            run(p, "", size, bold, color)._r.append(_el("w:br"))
        rich(p, line, size, bold, color)


# ---------- ניקוי ----------
def s(v, limit=None):
    """מקף ארוך אסור בכל תוצר, וגם רווחים כפולים שנוצרים בהרכבת נוסח."""
    t = " ".join(str(v).split()) if v not in (None, "") else ""
    t = t.replace("—", ", ").replace("–", "-").replace(" ,", ",")
    return t[:limit] if limit else t


def produced_on(meta):
    raw = s(meta.get("generated_at"))[:10]
    if len(raw) == 10 and raw[4] == "-":
        y, mo, d = raw.split("-")
        return "%s.%s.%s" % (d, mo, y)
    return datetime.date.today().strftime("%d.%m.%Y")


def txt(node, *keys):
    for k in keys:
        if node.get(k):
            return s(node[k])
    return ""


# ---------- בלוקי המסמך ----------
def base(doc):
    st = doc.styles["Normal"]
    st.font.name = FONT
    st.font.size = Pt(11)
    st.element.rPr.rFonts.set(qn("w:cs"), FONT)
    for sec in doc.sections:
        sec.left_margin = sec.right_margin = Cm(2.4)
        sec.top_margin = Cm(2.2)
        sec.bottom_margin = Cm(2.0)
        if RTL:
            sec._sectPr.append(_el("w:bidi"))


def title_block(doc, m):
    t = txt(m, "title", "doc_type") or "טיוטה"
    p = para(doc, before=0, after=4, align=WD_ALIGN_PARAGRAPH.CENTER)
    run(p, t, 19, True, NAVY)
    sub = " · ".join([x for x in (txt(m, "doc_type") if txt(m, "title") else "",
                                  txt(m, "place_date")) if x])
    if sub:
        p = para(doc, before=0, after=2, align=WD_ALIGN_PARAGRAPH.CENTER)
        run(p, sub, 10.5, False, INK_SOFT)
    stamp = "טיוטה · הופק בתאריך %s" % produced_on(m)
    cls = txt(m, "classification")
    if cls:
        stamp += " · " + cls
    p = para(doc, before=0, after=14, align=WD_ALIGN_PARAGRAPH.CENTER)
    run(p, stamp, 9.5, False, INK_SOFT)
    notice = txt(m, "notice")
    if notice:
        box = para(doc, before=0, after=10)
        ppr_put(box, _el("w:shd", val="clear", color="auto", fill="F5F7F9"))
        run(box, notice, 10, True, NAVY)
    rule = para(doc, before=0, after=14)
    ppr = rule._p.get_or_add_pPr()
    b = ppr_put(rule, _el("w:pBdr"))
    b.append(_el("w:top", val="single", sz="8", space="6", color=LINE))


def parties(doc, m):
    ps = m.get("parties") or []
    if not ps:
        return
    for i, party in enumerate(ps):
        p = para(doc, before=2, after=2)
        name = txt(party, "name") or "[להשלים]"
        head = name
        for extra in (txt(party, "reg"), txt(party, "address")):
            if extra:
                head += ", " + extra
        rich(p, head, 11, False)
        defined = txt(party, "defined_as") or txt(party, "role")
        if defined:
            run(p, ' (להלן: "%s")' % defined, 11, True)
        if i < len(ps) - 1:
            para(doc, "מצד אחד;" if i == 0 and len(ps) == 2 else "מצד אחד;",
                 10, False, INK_SOFT, after=6, align=WD_ALIGN_PARAGRAPH.LEFT
                 if RTL else WD_ALIGN_PARAGRAPH.RIGHT)
    para(doc, "מצד שני;", 10, False, INK_SOFT, after=12,
         align=WD_ALIGN_PARAGRAPH.LEFT if RTL else WD_ALIGN_PARAGRAPH.RIGHT)


def recitals(doc, rs):
    if not rs:
        return
    for r in rs:
        body = s(r)
        p = para(doc, before=0, after=5, indent=0.6)
        if not body.startswith("הואיל") and RTL:
            run(p, "הואיל ו", 11, True)
        rich(p, body, 11)
    para(doc, "לפיכך הוסכם, הותנה והוצהר בין הצדדים כדלקמן:", 11, True, INK,
         before=8, after=12)


def definitions(doc, defs):
    if not defs:
        return
    h1(doc, "הגדרות")
    for d in defs:
        p = para(doc, before=2, after=4, indent=0.6)
        run(p, '"%s" ' % txt(d, "term"), 11, True)
        run(p, "- ", 11, False, INK_SOFT)
        rich(p, txt(d, "text", "definition"), 11)


def h1(doc, text, num=""):
    p = para(doc, before=16, after=6, align=WD_ALIGN_PARAGRAPH.JUSTIFY)
    if num:
        run(p, "%s. " % num, 13, True, NAVY)
    run(p, s(text), 13, True, NAVY)
    return p


def clause(doc, c, depth=0):
    """סעיף ותתי-סעיפיו. המספר נכתב לתוך הטקסט ולא כמספור אוטומטי של Word,
    כדי שבקרת השלמות תמצא אותו ושהכיווניות לא תהפוך את הספרה והנקודה."""
    num = s(c.get("number"))
    head = txt(c, "heading", "title")
    body = txt(c, "text", "body")
    if c.get("needs_case_law") and body:
        # the law sources in state 4 exclude case law, so a clause whose validity rests
        # on it (liability caps, non-compete, liquidated damages) is marked for the lawyer
        body += " [טעון בדיקת פסיקה]"
    if depth == 0:
        if head:
            h1(doc, head, num)
            if body:
                rich(para(doc, before=0, after=5, indent=0.6), body, 11)
        else:
            p = para(doc, before=8, after=5)
            if num:
                run(p, "%s. " % num, 11, True)
            rich(p, body, 11)
    else:
        p = para(doc, before=0, after=4, indent=0.6 + 0.6 * depth)
        if num:
            run(p, "%s " % num, 11, True)
        if head:
            run(p, s(head) + ". ", 11, True)
        rich(p, body, 11)
    for ch in (c.get("children") or c.get("subclauses") or []):
        clause(doc, ch, depth + 1)


def page_break(doc):
    p = para(doc, before=0, after=0)
    run(p, "")._r.append(_el("w:br", type="page"))
    return p


def annexes(doc, ans):
    if not ans:
        return
    for a in ans:
        page_break(doc)
        label = txt(a, "label") or "נספח"
        title = txt(a, "title")
        p = para(doc, before=0, after=10, align=WD_ALIGN_PARAGRAPH.CENTER)
        run(p, label + (" - " + title if title else ""), 15, True, NAVY)
        if a.get("text"):
            rich(para(doc, before=0, after=5), txt(a, "text"), 11)
        for c in (a.get("clauses") or []):
            clause(doc, c)


def signatures(doc, sig, m):
    blocks = (sig or {}).get("blocks") or []
    if not blocks:
        blocks = [{"name": txt(p, "defined_as", "name")} for p in (m.get("parties") or [])]
    if not blocks:
        return
    para(doc, s((sig or {}).get("note")) or "ולראיה באו הצדדים על החתום:",
         11, True, INK, before=22, after=14)
    tbl = doc.add_table(rows=2, cols=len(blocks))
    tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    table_borders(tbl, LINE, visible=False)
    for i, b in enumerate(blocks):
        cell_text(tbl.rows[0].cells[i], "_______________________", False, 11,
                  INK_SOFT, WD_ALIGN_PARAGRAPH.CENTER)
        lines = [txt(b, "name")]
        if txt(b, "by"):
            lines.append("על ידי: " + txt(b, "by"))
        if txt(b, "title"):
            lines.append(txt(b, "title"))
        cell_text(tbl.rows[1].cells[i], "\n".join([x for x in lines if x]),
                  False, 10, INK, WD_ALIGN_PARAGRAPH.CENTER)


def sources_annex(doc, d):
    """נספח המקורות של מצב 4. פנימי: מוסר לפני שליחה החוצה, כמו כל חומר פנימי."""
    src = d.get("sources") or {}
    law, st = src.get("law") or [], src.get("structures") or []
    if not (law or st):
        return
    page_break(doc)
    p = para(doc, before=0, after=4, align=WD_ALIGN_PARAGRAPH.CENTER)
    run(p, "נספח מקורות", 15, True, NAVY)
    para(doc, "פנימי. יש להסיר לפני שליחה לצד שכנגד.", 9.5, True, INK_SOFT, after=10,
         align=WD_ALIGN_PARAGRAPH.CENTER)

    def grid(header, rows):
        tbl = doc.add_table(rows=1 + len(rows), cols=len(header))
        tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
        table_borders(tbl)
        for j, h in enumerate(header):
            cell_text(tbl.rows[0].cells[j], h, True, 9.5, NAVY)
        for i, row in enumerate(rows):
            for j, v in enumerate(row):
                cell_text(tbl.rows[i + 1].cells[j], v, False, 9.5)
        para(doc, after=6)

    if law:
        h1(doc, "הדין החל")
        grid(["מקור נורמטיבי", "סעיפים", "השפעה", "קישור", "סטטוס"],
             [[s(x.get("instrument")), s(x.get("sections")), s(x.get("effect")), s(x.get("url")),
               "אומת" if x.get("verified") else "טעון אימות"] for x in law])
    if st:
        h1(doc, "מקורות המבנה")
        grid(["מקור", "מפרסם", "קישור"],
             [[s(x.get("title")), s(x.get("publisher")), s(x.get("url"))] for x in st])
    mapping = []

    def walk(cs):
        for c in cs or []:
            if c.get("source"):
                mapping.append([s(c.get("number")), txt(c, "heading") or txt(c, "text")[:40], s(c.get("source"))])
            walk(c.get("children") or c.get("subclauses"))
    walk(d.get("clauses"))
    if mapping:
        h1(doc, "מקור לכל סעיף")
        grid(["סעיף", "נושא", "נגזר מ"], mapping)


def footer(doc, m):
    bits = [txt(m, "doc_type") or "טיוטה"]
    if txt(m, "classification"):
        bits.append(txt(m, "classification"))
    bits.append(produced_on(m))
    for sec in doc.sections:
        p = sec.footer.paragraphs[0]
        dir_p(p)
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run(p, " · ".join(bits) + " · עמוד ", 8.5, False, INK_SOFT)
        p._p.append(_el("w:fldSimple", instr="PAGE"))


# ---------- הרכבה ----------
def build(d, prof, out):
    global RTL
    m = d.get("meta") or {}
    lang = s(m.get("language")) or s((prof or {}).get("deliverable_language")) or "he"
    RTL = lang.lower() not in ("en", "english", "אנגלית")

    del GAPS[:]
    doc = Document()
    base(doc)
    title_block(doc, m)
    parties(doc, m)
    recitals(doc, d.get("recitals"))
    definitions(doc, d.get("definitions"))
    for c in (d.get("clauses") or []):
        clause(doc, c)
    annexes(doc, d.get("annexes"))
    signatures(doc, d.get("signatures"), m)
    sources_annex(doc, d)
    footer(doc, m)
    doc.save(out)

    # counted from what was actually written, not from the input: a placeholder
    # that never reached the page must not be reported as marked.
    gaps = len(GAPS)
    return {"out": out, "rtl": RTL, "clauses": len(d.get("clauses") or []),
            "definitions": len(d.get("definitions") or []),
            "annexes": len(d.get("annexes") or []), "placeholders": gaps}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--draft", required=True)
    ap.add_argument("--profile")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    d = json.load(io.open(a.draft, encoding="utf-8"))
    prof = {}
    if a.profile:
        try:
            prof = json.load(io.open(a.profile, encoding="utf-8"))
        except (OSError, ValueError):
            prof = {}
    r = build(d, prof, a.out)
    print("הטיוטה נבנתה: %s" % r["out"])
    print("סעיפים ראשיים: %d · הגדרות: %d · נספחים: %d · כיווניות: %s"
          % (r["clauses"], r["definitions"], r["annexes"], "RTL" if r["rtl"] else "LTR"))
    if r["placeholders"]:
        print("מצייני חוסר שסומנו ברקע: %d. אין לסווג ReadyForExternal כל עוד הם פתוחים."
              % r["placeholders"])


if __name__ == "__main__":
    main()
