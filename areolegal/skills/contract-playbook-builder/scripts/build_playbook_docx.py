#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""בונה את מסמך הפלייבוק ב-Word, בגרסה המקוצרת או המלאה, ישירות מ-playbook-model.json.

**זה המסלול היחיד להפקת הפלייבוק ב-Word.** אין לכתוב את המסמך מחדש בכל הרצה:
כך נוצרו מסמכים בלי שום עיצוב, טקסט שחור על לבן בברירות המחדל של Word, בלי צבעי
הרמזור שהם שפת המוצר.

העיצוב: Arial (מותקן בכל מחשב ומכסה עברית), כותרות בכחול כהה, ירוק Areo להדגשה,
ושלושת המסלולים בירוק, בענבר ובאדום עם קו צבע ורקע עדין. כריכה, סימון חיסיון,
כותרת תחתונה עם מספר עמוד, וכיווניות מימין לשמאל בכל פסקה, ריצה, טבלה וסעיף.

    python3 build_playbook_docx.py --model Areo-נתונים/playbook-model.json \\
        --profile Areo-נתונים/פרופיל-לקוח.json --version short --out "<שם>.docx"
"""
import argparse
import datetime
import io
import json

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

# ---------- פלטה: נגזרת מסביבת העבודה, מותאמת לנייר ----------
INK = "16191F"
INK_SOFT = "5B6472"
LINE = "D7DBE0"
BRAND = "0B6B4F"
NAVY = "12314F"
GREEN, GREEN_BG = "0F6B4C", "E9F5F0"
AMBER, AMBER_BG = "8A6212", "FBF2DF"
RED, RED_BG = "9E2723", "FAEBEA"
SURF = "F5F7F9"

# Arial: מותקן בכל מחשב Windows ו-Mac ומכסה עברית במלואה. גופן שאינו מותקן אצל
# הנמען מוחלף בשקט, וההיררכיה של המסמך נשברת יחד איתו.
FONT = "Arial"

TRACKS = {"green": ("עמדת ברירת מחדל, הנוסח המועדף", GREEN, GREEN_BG),
          "yellow": ("ויתור ראשוני מותר", AMBER, AMBER_BG),
          "red": ("הקו האדום", RED, RED_BG)}
CONF = {"High": ("קריטי", RED), "Medium": ("גבוה", AMBER), "Low": ("בינוני", INK_SOFT)}
REQ = {"Required": "חובה", "Recommended": "מומלץ", "Optional": "רשות",
       "Conditional": "מותנה", "Prohibited": "אסור"}
RAT = [("executive_policy_rationale", "תקציר נימוק המדיניות"),
       ("protected_interest_and_clause_purpose", "מטרת הסעיף והאינטרס המוגן"),
       ("legal_risk_and_legal_framework", "החשיפה המשפטית והמסגרת הנורמטיבית"),
       ("contractual_risk_allocation_mechanism", "מנגנון חוזי והקצאת סיכון"),
       ("company_role_and_policy_fit", "פוזיציית החברה וההתאמה למדיניות"),
       ("business_operational_impact", "ההשלכה העסקית והתפעולית"),
       ("internal_evidence_rationale", "ראיות מתוך מאגר החברה"),
       ("market_practice_assessment", "מקובלות שוק"),
       ("tradeoff_statement", "האיזון שנבחר"),
       ("related_clause_rationale", "סעיפים קשורים"),
       ("uncertainties_and_limitations", "אי-ודאות ומגבלות")]
PERSP = [("legal_analysis", "ניתוח משפטי"), ("business_analysis", "ניתוח עסקי"),
         ("internal_corpus_findings", "ממצאי מאגר פנימי"),
         ("internal_contracting_trend", "מגמת התקשרות פנימית"),
         ("external_market_trend", "מגמת שוק חיצונית")]

# ---------- כלי XML ----------
# סדר הילדים ב-w:pPr קבוע בסכמה של OOXML. אלמנט שמצורף בסוף אינו מוצג בשקט:
# כך נעלמו רקעים וקווי צבע בגרסה הראשונה, והמסמך נראה כאילו אין לו עיצוב.
PPR_ORDER = ["pStyle", "keepNext", "keepLines", "pageBreakBefore", "numPr", "pBdr",
             "shd", "tabs", "bidi", "spacing", "ind", "contextualSpacing", "jc",
             "outlineLvl", "rPr"]


def _el(tag, **attrs):
    e = OxmlElement(tag)
    for k, v in attrs.items():
        e.set(qn("w:" + k), v)
    return e


def _local(tag):
    return tag.split("}")[-1]


def ppr_put(p, el):
    """מכניס אלמנט ל-w:pPr במקומו לפי הסכמה, ומחליף אלמנט קיים מאותו סוג."""
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


def shade(p, fill):
    ppr_put(p, _el("w:shd", val="clear", color="auto", fill=fill))


def bar(p, color, size=18, side="start"):
    """קו צבע לצד הפסקה או מעליה."""
    ppr = p._p.get_or_add_pPr()
    b = ppr.find(qn("w:pBdr"))
    if b is None:
        b = ppr_put(p, _el("w:pBdr"))
    old = b.find(qn("w:" + side))
    if old is not None:
        b.remove(old)
    b.append(_el("w:" + side, val="single", sz=str(size), space="8", color=color))


def rtl_p(p):
    ppr_put(p, _el("w:bidi"))


def run(p, text, size=11, bold=False, color=INK, italic=False):
    r = p.add_run(text)
    r.font.name = FONT
    r.font.size = Pt(size)
    r.bold = bold
    r.italic = italic
    r.font.color.rgb = RGBColor.from_string(color)
    rpr = r._r.get_or_add_rPr()
    rf = rpr.find(qn("w:rFonts"))
    if rf is None:
        rf = _el("w:rFonts")
        rpr.insert(0, rf)
    for k in ("ascii", "hAnsi", "cs"):
        rf.set(qn("w:" + k), FONT)
    rpr.append(_el("w:rtl"))
    return r


def para(doc, text="", size=11, bold=False, color=INK, before=0, after=4, line=1.15,
         container=None, italic=False):
    p = (container or doc).add_paragraph()
    rtl_p(p)
    pf = p.paragraph_format
    pf.space_before = Pt(before)
    pf.space_after = Pt(after)
    pf.line_spacing = line
    pf.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    if text:
        run(p, text, size, bold, color, italic)
    return p


def table_borders(tbl, color=LINE):
    tpr = tbl._tbl.tblPr
    b = _el("w:tblBorders")
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        b.append(_el("w:" + edge, val="single", sz="4", space="0", color=color))
    tpr.append(b)
    tpr.append(_el("w:bidiVisual"))


def cell_text(cell, text, bold=False, size=10, color=INK, fill=None):
    cell.text = ""
    p = cell.paragraphs[0]
    rtl_p(p)
    p.paragraph_format.space_before = Pt(2)
    p.paragraph_format.space_after = Pt(2)
    run(p, text, size, bold, color)
    if fill:
        cell._tc.get_or_add_tcPr().append(_el("w:shd", val="clear", color="auto", fill=fill))


# ---------- ניקוי נתונים לתצוגה ----------
def s(v, limit=None):
    """טקסט לתצוגה: רווחים מנורמלים, ובלי מקפים ארוכים, שאסורים בכל תוצר."""
    t = " ".join(str(v).split()) if v else ""
    t = t.replace("—", ", ").replace("–", "-").replace(" ,", ",")
    return t[:limit] if limit else t


def clean_company(v):
    """שם החברה לכריכה. פרט שטרם הושלם בפרופיל אינו מוצג על השער."""
    t = " ".join(str(v or "").split())
    for sep in (", ח.פ", " ח.פ"):
        if sep in t and "[" in t.split(sep, 1)[1][:20]:
            t = t.split(sep, 1)[0]
    return t.strip(" ,")


def short_role(v):
    """הפוזיציה בכמה מילים. במודל השדה נושא לעיתים פסקת הסבר שלמה."""
    t = " ".join(str(v or "").split())
    for sep in (" — ", " - ", "(", ",", ";", "."):
        if sep in t:
            t = t.split(sep)[0]
    return t.strip() or "לא צוין"


def produced_on(d):
    """תאריך ההפקה בפורמט יום.חודש.שנה. כשחסר במודל, תאריך היום."""
    raw = (d.get("generated_at") or d.get("last_updated") or "")[:10]
    if len(raw) == 10 and raw[4] == "-":
        y, mo, day = raw.split("-")
        return "%s.%s.%s" % (day, mo, y)
    return datetime.date.today().strftime("%d.%m.%Y")


# ---------- בלוקי המסמך ----------
def base(doc):
    st = doc.styles["Normal"]
    st.font.name = FONT
    st.font.size = Pt(11)
    st.element.rPr.rFonts.set(qn("w:cs"), FONT)
    for sec in doc.sections:
        sec.left_margin = sec.right_margin = Cm(2.2)
        sec.top_margin = Cm(2.0)
        sec.bottom_margin = Cm(1.8)
        sec._sectPr.append(_el("w:bidi"))


def h1(doc, text, num=""):
    p = para(doc, before=20, after=2)
    if num:
        run(p, num + "   ", 18, True, BRAND)
    run(p, text, 18, True, NAVY)
    bar(para(doc, after=10), LINE, 8, "top")


def h2(doc, text):
    run(para(doc, before=14, after=4), text, 13.5, True, NAVY)


def h3(doc, text):
    run(para(doc, before=9, after=2), text, 11, True, INK_SOFT)


def cover(doc, m):
    run(para(doc, before=150, after=2), m["company"], 13, True, BRAND)
    run(para(doc, after=0), "פלייבוק חוזי", 30, True, NAVY)
    run(para(doc, after=14), m["family"], 16, False, INK_SOFT)
    bar(para(doc, after=16), BRAND, 26, "top")
    run(para(doc, after=6), "הגרסה המלאה" if m["full"] else "הגרסה המקוצרת", 11, True, BRAND)
    for k, v in [("פוזיציית החברה", m["role"]), ("גרסה", m["version"]),
                 ("הופק בתאריך", m["date"]), ("מאגר המקור", m["corpus"])]:
        p = para(doc, after=3)
        run(p, k + ": ", 10.5, True, INK_SOFT)
        run(p, v, 10.5, False, INK)
    p = para(doc, before=18, after=0)
    shade(p, SURF)
    bar(p, BRAND, 18)
    run(p, "חסוי. הוכן לצורך קבלת ייעוץ משפטי ומיועד לשימוש פנימי בלבד.", 9.5, True, INK_SOFT)
    p = para(doc, after=0)
    shade(p, SURF)
    run(p, "טיוטה מקצועית. חובה בדיקת עורך דין לפני הסתמכות או שליחה.", 9.5, False, INK_SOFT)
    p.runs[-1].add_break(WD_BREAK.PAGE)


def kv(doc, rows):
    t = doc.add_table(rows=0, cols=2)
    table_borders(t)
    for k, v in rows:
        c = t.add_row().cells
        cell_text(c[0], k, True, 10, INK_SOFT, SURF)
        cell_text(c[1], v, False, 10)
        c[0].width = Cm(4.6)
        c[1].width = Cm(11.2)
    para(doc, after=8)


def ev_table(doc, ev):
    t = doc.add_table(rows=1, cols=3)
    table_borders(t)
    for i, head in enumerate(["ההסכם", "סעיף", "הנוסח שנמצא"]):
        cell_text(t.rows[0].cells[i], head, True, 9.5, NAVY, SURF)
    for e in ev:
        c = t.add_row().cells
        cell_text(c[0], s(e.get("agreement") or e.get("source_document"), 40), False, 9)
        cell_text(c[1], s(e.get("clause_ref"), 18), False, 9)
        cell_text(c[2], s(e.get("quote") or e.get("text")), False, 9, INK_SOFT)
    for row in t.rows:
        row.cells[0].width = Cm(4.0)
        row.cells[1].width = Cm(2.0)
        row.cells[2].width = Cm(9.8)
    para(doc, after=8)


def anchors(doc, r, limit):
    srcs = [s(x, limit) for x in (r.get("regulatory_sources") or []) if x]
    if not srcs:
        return
    h3(doc, "עיגונים בדין")
    for a in srcs:
        p = para(doc, after=2)
        bar(p, LINE, 8)
        run(p, a, 9.5, False, INK_SOFT)


def topic(doc, r, n, full):
    h2(doc, "%d. %s" % (n, s(r.get("topic_name"))))
    pres = r.get("presence_rule") or {}
    lvl, col = CONF.get(s(r.get("confidence") or r.get("confidence_level")), ("גבוה", AMBER))
    p = para(doc, after=8)
    shade(p, SURF)
    run(p, "רמת חשיבות  ", 9.5, True, INK_SOFT)
    run(p, lvl, 9.5, True, col)
    req = pres.get("requirement") if isinstance(pres, dict) else pres
    if req:
        run(p, "     כלל נוכחות  ", 9.5, True, INK_SOFT)
        run(p, REQ.get(req, s(req, 30)), 9.5, False, INK)
    if r.get("clause_issue"):
        para(doc, s(r["clause_issue"]), 10.5, after=8, color=INK_SOFT)

    tl = r.get("traffic_light") or {}
    for key in ("green", "yellow", "red"):
        blk = tl.get(key) or {}
        # הנוסח המוצע לעולם אינו מקוצר, בשתי הגרסאות: זה הטקסט שעורך הדין מעתיק אל ההסכם.
        text = s(blk.get("proposed_clause") or blk.get("meaning"))
        if not text:
            continue
        title, color, fill = TRACKS[key]
        p = para(doc, before=8, after=2)
        bar(p, color, 22)
        shade(p, fill)
        run(p, title, 11, True, color)
        p = para(doc, after=2)
        bar(p, color, 22)
        shade(p, fill)
        run(p, text, 10.5, False, INK)
        if blk.get("meaning") and blk.get("proposed_clause"):
            p = para(doc, after=6)
            bar(p, color, 22)
            shade(p, fill)
            run(p, s(blk["meaning"]), 9.5, False, INK_SOFT, italic=True)

    pr = r.get("policy_rationale") or {}
    if not full:
        if pr.get("executive_policy_rationale"):
            h3(doc, "נימוק משפטי")
            para(doc, s(pr["executive_policy_rationale"], 900), 10.5, after=6)
        anchors(doc, r, 160)
    else:
        cp = r.get("company_perspective") or {}
        if any(cp.get(k) for k, _ in PERSP):
            h3(doc, "פרספקטיבת החברה")
            for k, label in PERSP:
                if cp.get(k):
                    p = para(doc, after=4)
                    run(p, label + ": ", 10, True, INK_SOFT)
                    run(p, s(cp[k]), 10, False, INK)
        if any(pr.get(k) for k, _ in RAT):
            h3(doc, "מדוע נבחרה מדיניות זו")
            for k, label in RAT:
                if pr.get(k):
                    p = para(doc, after=4)
                    run(p, label + ": ", 10, True, INK_SOFT)
                    run(p, s(pr[k]), 10, False, INK)
        anchors(doc, r, None)
        if r.get("evidence"):
            h3(doc, "הראיות מהמאגר")
            ev_table(doc, r["evidence"])
    bar(para(doc, before=6, after=10), LINE, 6, "top")


def footer(doc, m):
    for sec in doc.sections:
        p = sec.footer.paragraphs[0]
        rtl_p(p)
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run(p, "%s · %s · חסוי · עמוד " % (m["company"], m["family"]), 8.5, False, INK_SOFT)
        p._p.append(_el("w:fldSimple", instr="PAGE"))


def build(d, prof, out, full):
    sc = d.get("scope_summary") or {}
    fams = sc.get("contract_families") or []
    m = {"company": clean_company(prof.get("organization_name")) or "החברה",
         "family": ", ".join(f.get("contract_family_name", "") if isinstance(f, dict) else str(f)
                             for f in fams) or "הסכמי החברה",
         "role": short_role(sc.get("company_role")),
         "role_full": s(sc.get("company_role"), 600),
         "version": str(d.get("version") or "1.0"),
         "date": produced_on(d),
         "corpus": "%s מסמכים" % sc.get("total_document_count", "לא צוין"),
         "full": full}
    doc = Document()
    base(doc)
    cover(doc, m)
    footer(doc, m)

    h1(doc, "תמונת מצב", "1")
    kv(doc, [("סוג ההסכמים", m["family"]),
             ("פוזיציית החברה", m["role_full"] or m["role"]),
             ("נושאי מדיניות", str(len(d["rules"]))),
             ("מסמכים שנותחו", m["corpus"]),
             ("טווח תאריכים", s(sc.get("date_range"), 120) or "לא צוין"),
             ("מעמד הפלייבוק", s(d.get("playbook_status")) or "לא צוין")])
    lim = sc.get("limitations")
    if lim:
        h3(doc, "מגבלות")
        for x in ([lim] if isinstance(lim, str) else lim):
            q = para(doc, after=4)
            bar(q, AMBER, 12)
            run(q, s(x), 10, False, INK_SOFT)

    h1(doc, "מדיניות לפי נושא", "2")
    for i, r in enumerate(d["rules"], 1):
        topic(doc, r, i, full)

    if full and d.get("source_log"):
        h1(doc, "נספח: ההסכמים שנותחו", "3")
        t = doc.add_table(rows=1, cols=3)
        table_borders(t)
        for i, head in enumerate(["ההסכם", "הצד שכנגד", "מעמד הקריאה"]):
            cell_text(t.rows[0].cells[i], head, True, 9.5, NAVY, SURF)
        for src in d["source_log"]:
            if not isinstance(src, dict):
                continue
            c = t.add_row().cells
            cell_text(c[0], s(src.get("agreement_name") or src.get("document_name"), 40), False, 9)
            cell_text(c[1], s(src.get("counterparty"), 40) or "לא צוין", False, 9)
            cell_text(c[2], s(src.get("read_status"), 40) or "לא צוין", False, 9)
    doc.save(out)


def main():
    ap = argparse.ArgumentParser(description="בונה את מסמך הפלייבוק ב-Word מהמודל הקנוני")
    ap.add_argument("--model", required=True, help="playbook-model.json")
    ap.add_argument("--profile", required=True, help="פרופיל-לקוח.json")
    ap.add_argument("--version", required=True, choices=["short", "full"],
                    help="short = הגרסה המקוצרת, full = הגרסה המלאה")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    d = json.load(io.open(a.model, encoding="utf-8"))
    prof = json.load(io.open(a.profile, encoding="utf-8"))
    if not d.get("rules"):
        print("במודל אין כללים. אין ממה לבנות מסמך.")
        return 1
    build(d, prof, a.out, a.version == "full")
    print("נבנה %s (%s, %d נושאים)" % (a.out, "מלאה" if a.version == "full" else "מקוצרת",
                                      len(d["rules"])))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
