#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""מסמך הביניים של מצב 4: המחקר מוצג לאישור **לפני** שנכתבת מילה בטיוטה.

    python3 build_research_brief.py --research "Areo-נתונים/research-<slug>.json" \\
        --out "<סוג ההסכם> - מחקר לאישור.docx"

research.json:
  {
    "agreement_type": "הסכם SaaS", "company_role": "ספק", "consent_at": "2026-09-16",
    "law": [{"instrument": "חוק הגנת הפרטיות, התשמ\\"א-1981", "sections": "סעיף 17",
             "regulator": "הרשות להגנת הפרטיות", "effect": "סעיף חובה",
             "impact": "איך זה משפיע על ההסכם", "url": "https://www.gov.il/...", "verified": true}],
    "structures": [{"title": "...", "publisher": "...", "source_type": "רגולטור",
                    "url": "https://...", "governing_law": "ישראל",
                    "contributes": "מה הוא תורם למבנה", "topics": ["תמורה", "סודיות"]}],
    "case_law_sensitive": ["הגבלת אחריות"], "foreign_institutions": []
  }

המסמך: טבלת הדין במתכונת סקר ציות, טבלת מקורות המבנה, והערות (רוויה, מקורות
שלא אומתו, נוסח ממשלתי, דין זר). הסקריפט **חוסם** מקור דין שאינו מהכנסת או
מ-gov.il, יותר משבעה מקורות מבנה, ומחקר בלי תיעוד לאישור המשתמש.
"""
import argparse
import datetime
import io
import json
import os
import sys

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.shared import Pt

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_draft_docx as B  # noqa: E402
from research_sources import check  # noqa: E402

HEAD_BG = "E8EDF2"


def table(doc, header, rows):
    tbl = doc.add_table(rows=1 + len(rows), cols=len(header))
    tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    B.table_borders(tbl)
    for j, h in enumerate(header):
        c = tbl.rows[0].cells[j]
        B.cell_text(c, h, True, 9.5, B.NAVY)
        c._tc.get_or_add_tcPr().append(B._el("w:shd", val="clear", color="auto", fill=HEAD_BG))
    for i, row in enumerate(rows):
        for j, val in enumerate(row):
            B.cell_text(tbl.rows[i + 1].cells[j], val, False, 9.5)
    B.para(doc, after=6)
    return tbl


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--research", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    r = json.load(io.open(a.research, encoding="utf-8"))
    blocking, flags, notes = check(r)

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
    B.run(B.para(doc, after=2), "מחקר לפני ניסוח: " + B.s(r.get("agreement_type") or "הסכם"), 17, True, B.NAVY)
    B.run(B.para(doc, after=4), "טיוטה · הופק בתאריך %s · החברה בהסכם: %s · אישור למחקר: %s" % (
        B.produced_on({"generated_at": today}), B.s(r.get("company_role") or "[להשלים]"),
        B.produced_on({"generated_at": r.get("consent_at")})), 9.5, False, B.INK_SOFT)
    B.para(doc, "אין בתיקייה תבנית, פלייבוק או הסכמים מסוג זה. לכן הדין נמפה מאתר הכנסת ומאתרי gov.il "
                "בלבד, ומבנה ההסכם נלקח מהסכמים דומים שפורסמו. **אף מילה בטיוטה לא נכתבת לפני אישורכם.**"
           .replace("**", ""), 10.5, False, B.INK, after=10)

    B.h1(doc, "1. הדין החל")
    table(doc, ["מקור נורמטיבי", "סעיפים", "רגולטור", "השפעה על ההסכם", "קישור", "סטטוס"],
          [[B.s(x.get("instrument")), B.s(x.get("sections")), B.s(x.get("regulator")),
            "%s: %s" % (B.s(x.get("effect") or "אחר"), B.s(x.get("impact"))), B.s(x.get("url")),
            ", ".join(flags["law"][i]) or "אומת"]
           for i, x in enumerate(r.get("law") or [])])

    B.h1(doc, "2. מקורות המבנה")
    table(doc, ["מקור", "מפרסם וסוג", "דין חל", "מה הוא תורם", "קישור", "שימוש"],
          [[B.s(x.get("title")), "%s · %s" % (B.s(x.get("publisher")), B.s(x.get("source_type"))),
            B.s(x.get("governing_law")), B.s(x.get("contributes")), B.s(x.get("url")),
            ", ".join(flags["structures"][i])]
           for i, x in enumerate(r.get("structures") or [])])

    if notes:
        B.h1(doc, "3. הערות")
        for n in notes:
            B.rich(B.para(doc, after=3, indent=0.5), n, 10.5)
    B.para(doc, "לאשר את המחקר ואת המקורות, או להסיר חלק מהם לפני הניסוח?", 11, True, B.INK, before=14)
    doc.save(a.out)

    unverified = sum(1 for f in flags["law"] if "טעון אימות" in f)
    print("מסמך המחקר: %s" % a.out)
    print("מקורות דין: %d (טעוני אימות: %d) · מקורות מבנה: %d"
          % (len(r.get("law") or []), unverified, len(r.get("structures") or [])))
    for n in notes:
        print("  " + n)


if __name__ == "__main__":
    main()
