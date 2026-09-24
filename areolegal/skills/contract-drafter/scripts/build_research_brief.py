#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""מסמך הביניים של מצב 4: מה נמצא, לאישור, **לפני** שנכתבת מילה בטיוטה.

    python3 build_research_brief.py --research "Areo-נתונים/research-<slug>.json" \\
        --out "<סוג ההסכם> - מחקר לאישור.docx" [--matrix "<קובץ ה-Excel>"]

התוכן נקבע לפי היקף העבודה שנבחר (scope):
  research / both   תמצית דרגים 1 עד 3 (הטבלה המלאה בקובץ ה-Excel), סעיפי חובה,
                    סעיפים מומלצים מדרגים 4 ו-5, ושאלת אישור א'.
  agreements / both ההסכמים, כל אחד עם קישור לחיץ, כיוון ונימוק וסעיפי חובה חסרים,
                    ושאלת אישור ב'.
לכל מקור ולכל הסכם יש היפר-קישור אמיתי ב-Word. פערים ומקורות טעוני אימות בסוף.

קוד יציאה 1 לפי כללי research_sources.py.
"""
import argparse
import datetime
import io
import json
import os
import sys

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_draft_docx as B  # noqa: E402
from research_sources import (MANDATORY_ALLOWED_RANKS, NORM_RANKS, RECOMMENDED_RANKS, SCOPES,  # noqa: E402
                              check, normalise, scope_has)

HEAD_BG = "E8EDF2"


def grid(doc, header, rows, link_cols=()):
    """rows: רשימת שורות; בעמודה שב-link_cols הערך הוא (טקסט, קישור)."""
    tbl = doc.add_table(rows=1 + len(rows), cols=len(header))
    tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    B.table_borders(tbl)
    for j, h in enumerate(header):
        c = tbl.rows[0].cells[j]
        B.cell_text(c, h, True, 9.5, B.NAVY)
        c._tc.get_or_add_tcPr().append(B._el("w:shd", val="clear", color="auto", fill=HEAD_BG))
    for i, row in enumerate(rows):
        for j, val in enumerate(row):
            cell = tbl.rows[i + 1].cells[j]
            if j in link_cols:
                text, url = val
                B.cell_link(cell, url, text)
            else:
                B.cell_text(cell, val, False, 9.5)
    B.para(doc, after=6)
    return tbl


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--research", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--matrix", help="שם קובץ ה-Excel, להפניה במסמך")
    a = ap.parse_args()
    r = normalise(json.load(io.open(a.research, encoding="utf-8")))
    blocking, flags, notes = check(r, stage="brief")
    if blocking:
        print("המחקר אינו מוכן לאישור:")
        for b in blocking:
            print("  חוסם: " + b)
        sys.exit(1)

    B.RTL = True
    del B.GAPS[:]
    doc = Document()
    B.base(doc)
    today = datetime.date.today().isoformat()
    B.run(B.para(doc, after=2), "לאישור לפני ניסוח: " + B.s(r.get("agreement_type") or "הסכם"), 17, True, B.NAVY)
    B.run(B.para(doc, after=4), "טיוטה · הופק בתאריך %s · הפוזיציה: %s · היקף: %s" % (
        B.produced_on({"generated_at": today}), B.s(r.get("company_role")), SCOPES[r["scope"]]),
        9.5, False, B.INK_SOFT)
    B.para(doc, "לא נמצאו בתיקייה טיוטות, הסכמים או פלייבוק מסוג זה. להלן מה שנמצא. "
                "אף מילה בטיוטה לא נכתבת לפני אישורכם.", 10.5, False, B.INK, after=10)

    questions = []
    if scope_has(r, "research"):
        law = r.get("law") or []
        core = [x for x in law if x.get("rank") in MANDATORY_ALLOWED_RANKS]
        B.h1(doc, "1. הדין החל: תמצית דרגים 1 עד 3")
        if a.matrix:
            B.para(doc, "הטבלה המלאה, כולל הנחיות, עמדות סגל ומקורות בהליך, בקובץ: %s" % a.matrix,
                   10, False, B.INK_SOFT, after=6)
        grid(doc, ["דרג", "מקור", "סעיפים", "המשמעות להסכם", "סטטוס"],
             [[NORM_RANKS.get(x.get("rank"), ""), (B.s(x.get("instrument")), x.get("url")), B.s(x.get("sections")),
               B.s(x.get("meaning")), "אומת" if x.get("verified") else "טעון אימות"] for x in core],
             link_cols=(1,))

        mand = r.get("mandatory_clauses") or []
        B.h1(doc, "2. סעיפי חובה לאישור")
        by_row = {x.get("row", i + 1): x for i, x in enumerate(law)}
        grid(doc, ["מזהה", "סעיף", "הדרישה", "מקור", "הצד החייב"],
             [[B.s(m.get("clause_id")), B.s(m.get("title")), B.s(m.get("requirement")),
               ("%s, %s" % (B.s(by_row.get(m.get("source_row"), {}).get("instrument")), B.s(m.get("source_section"))),
                by_row.get(m.get("source_row"), {}).get("url")),
               B.s(m.get("bound_party"))] for m in mand],
             link_cols=(3,))
        rec = [x for x in law if x.get("rank") in RECOMMENDED_RANKS]
        if rec:
            B.h1(doc, "סעיפים מומלצים, מהנחיות ועמדות סגל")
            for x in rec:
                p = B.para(doc, after=3, indent=0.5)
                B.rich(p, "%s: %s " % (NORM_RANKS[x["rank"]], B.s(x.get("contract_treatment"))), 10.5)
                B.link(p, x.get("url"), B.s(x.get("instrument")), 10)
        questions.append("אישור א': לאשר את המחקר הרגולטורי ואת %d סעיפי החובה שנגזרו ממנו? "
                         "מאשר · מאשר עם הסרות · לתקן" % len(mand))

    if scope_has(r, "agreements"):
        ags = r.get("agreements") or []
        B.h1(doc, "%d. הסכמים מייצגים" % (3 if scope_has(r, "research") else 1))
        grid(doc, ["מס'", "הסכם", "מפרסם", "כיוון ונימוק", "סעיפי חובה חסרים", "שימוש"],
             [[str(x.get("no", i + 1)), (B.s(x.get("title")), x.get("url")), B.s(x.get("publisher")),
               "%s: %s" % (B.s(x.get("orientation")), B.s(x.get("orientation_reason"))),
               ", ".join(x.get("missing_mandatory") or []) or "-",
               ", ".join(flags["agreements"][i])] for i, x in enumerate(ags)],
             link_cols=(1,))
        questions.append("אישור ב': לאשר את %d ההסכמים, או למחוק חלק מהם? מאשר את כולם · למחוק הסכמים" % len(ags))

    gaps = [n for n in notes]
    unverified = [x for x in (r.get("law") or []) if not x.get("verified")] if scope_has(r, "research") else []
    if gaps or unverified:
        B.h1(doc, "פערים ומקורות טעוני אימות")
        for g in gaps:
            B.rich(B.para(doc, after=3, indent=0.5), g, 10.5)
        for x in unverified:
            p = B.para(doc, after=3, indent=0.5)
            B.run(p, "טעון אימות, ואינו בסיס לסעיף חובה: ", 10.5, True)
            B.link(p, x.get("url"), B.s(x.get("instrument")), 10.5)

    B.h1(doc, "לאישורכם")
    for q in questions:
        B.para(doc, q, 11, True, B.INK, before=4, after=4)
    doc.save(a.out)

    print("מסמך האישור: %s" % a.out)
    print("היקף: %s · מקורות דין: %d · סעיפי חובה: %d · הסכמים: %d" % (
        SCOPES[r["scope"]], len(r.get("law") or []) if scope_has(r, "research") else 0,
        len(r.get("mandatory_clauses") or []) if scope_has(r, "research") else 0,
        len(r.get("agreements") or []) if scope_has(r, "agreements") else 0))
    for n in notes:
        print("  " + n)


if __name__ == "__main__":
    main()
