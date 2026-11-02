#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""סיכום המחקר של הניסוח מבחוץ: מה נמצא, בלי שער אישור. הניסוח מבחוץ מותר רק כשללקוח אין פלייבוק ואין הסכמי טיוטה והוא ביקש זאת
במפורש, ורק ממקורות מהרשימה המאושרת. המסמך מסכם, ושואל שאלה רגילה אחת; הטיוטה אינה ממתינה לתשובה.

    python3 build_research_brief.py --research "Areo-נתונים/research-<slug>.json" \\
        --out "<סוג ההסכם> - סיכום מחקר.docx" [--matrix "<קובץ ה-Excel>"]

התוכן נקבע לפי היקף העבודה שנבחר (scope):
  research / both   תמצית דרגים 1 עד 3 (הטבלה המלאה בקובץ ה-Excel), סעיפי חובה,
                    סעיפים מומלצים מדרגים 4 ו-5, ושאלה רגילה א'.
  agreements / both ההסכמים, כל אחד עם קישור לחיץ, כיוון ונימוק וסעיפי חובה חסרים,
                    ושאלה רגילה ב'.
לכל מקור ולכל הסכם יש היפר-קישור אמיתי ב-Word. פערים ומקורות טעוני אימות בסוף.
שפה: `--lang he|en` או deliverable_language מ-`--profile`. באנגלית כל טקסט קבוע באנגלית והמסמך LTR מלא.
ההערות ודגלי השימוש שמגיעים מ-research_sources.py מתורגמים כאן (en_text) בתוצר באנגלית.

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
                              ApprovedSourcesMissing, check, normalise, scope_has)
from build_template_registry import guard_out  # noqa: E402

try:                                   # פלט עברי במסוף של Windows
    sys.stdout.reconfigure(encoding="utf-8")
except (AttributeError, ValueError):   # pragma: no cover
    pass

HEAD_BG = "E8EDF2"

# טקסט קבוע בשתי השפות (דרישת מוצר: deliverable_language קובע את שפת התוצר)
TXT = {
    "he": {"title": "סיכום המחקר לפני הניסוח: ", "agreement": "הסכם", "stamp": "טיוטה · הופק בתאריך %s · הפוזיציה: %s · היקף: %s",
           "intro": "לא נמצאו בתיקייה טיוטות, הסכמים או פלייבוק מסוג זה, וביקשתם לנסח מבחוץ. הטיוטה נבנית ממקורות מהרשימה "
                    "המאושרת בלבד, והיא תאמר זאת בבירור. להלן מה שנמצא.",
           "law": "1. הדין החל: תמצית דרגים 1 עד 3",
           "matrix": "הטבלה המלאה, כולל הנחיות, עמדות סגל ומקורות בהליך, בקובץ: %s",
           "law_head": ["דרג", "מקור", "סעיפים", "המשמעות להסכם", "סטטוס"], "verified": "אומת", "unverified": "טעון אימות",
           "mand": "2. סעיפי חובה", "mand_head": ["מזהה", "סעיף", "הדרישה", "מקור", "הצד החייב"],
           "rec": "סעיפים מומלצים, מהנחיות ועמדות סגל",
           "qa": "שאלה א': להשאיר את %d סעיפי החובה שנגזרו מהמחקר הרגולטורי, או להסיר חלק מהם? להשאיר את כולם · להסיר סעיפים",
           "ags": "%d. הסכמים מייצגים", "ags_head": ["מס'", "הסכם", "מפרסם", "כיוון ונימוק", "סעיפי חובה חסרים", "שימוש"],
           "qb": "שאלה ב': להשתמש ב-%d ההסכמים כבסיס, או להסיר חלק מהם? להשתמש בכולם · להסיר הסכמים",
           "gaps": "פערים ומקורות טעוני אימות", "unv_line": "טעון אימות, ואינו בסיס לסעיף חובה: ",
           "approve": "שאלה אחת לפני הניסוח"},
    "en": {"title": "Research summary before drafting: ", "agreement": "Agreement",
           "stamp": "Draft · Produced on %s · Position: %s · Scope: %s",
           "intro": "No drafts, agreements or playbook of this type were found in the folder, and you asked to draft from outside "
                    "sources. The draft is built only from sources on the approved list, and it will say so plainly. "
                    "Below is what was found.",
           "law": "1. Applicable law: summary of ranks 1 to 3",
           "matrix": "The full table, including guidance, staff positions and sources in process, is in: %s",
           "law_head": ["Rank", "Source", "Sections", "Meaning for the agreement", "Status"], "verified": "Verified",
           "unverified": "Needs verification",
           "mand": "2. Mandatory clauses", "mand_head": ["ID", "Clause", "Requirement", "Source", "Bound party"],
           "rec": "Recommended clauses, from guidance and staff positions",
           "qa": "Question A: keep the %d mandatory clauses derived from the regulatory research, or remove some? "
                 "Keep all · Remove clauses",
           "ags": "%d. Representative agreements",
           "ags_head": ["No.", "Agreement", "Publisher", "Orientation and reason", "Missing mandatory clauses", "Use"],
           "qb": "Question B: use the %d agreements as the basis, or remove some of them? Use all · Remove agreements",
           "gaps": "Gaps and sources that need verification", "unv_line": "Needs verification, and is not a basis for a mandatory clause: ",
           "approve": "One question before drafting"},
}
# ההערות ודגלי השימוש של research_sources.py נכתבים שם בעברית; בתוצר באנגלית הם מתורגמים כאן, לפי תחילת המחרוזת
EN_TEXT = (("מותר כלשונו, בציון המקור", "Verbatim use allowed, with attribution"),
           ("מבנה, נושאים ועמדות בלבד", "Structure, topics and positions only"),
           ("נכתב לטובת המדינה כלקוח", "Written in favour of the state as customer"),
           ("לעיון בלבד", "For reference only"), ("חסר נימוק לכיוון", "Orientation reason missing"),
           ("סעיפי חובה לא מוכרים: ", "Unknown mandatory clauses: "), ("שכבות שנבדקו: ", "Layers checked: "),
           ("המחקר מוגבל למאגר המקורות המאושרים", "The research is limited to approved sources. A point with no approved "
                                          "source is marked: AREO did not find an approved source for this point."),
           ("נבחר איסוף הסכמים בלבד", "Only collecting agreements was chosen, so the law sources in the file are "
                                     "not part of the output."),
           ("נמצאו ", "Fewer relevant agreements were found than the target: "),
           ("דין זר", "Law other than the agreement's governing law"),
           ("תחום שיפוט לא צוין", "Jurisdiction not stated"),
           ("מקור לא מסווג: ", "Unclassified source: make sure it is not a law firm website or a commercial "
                               "repository"))


def en_text(t):
    """תרגום הערה או דגל קבוע מ-research_sources.py; מה שאחרי התחילה (שמות, מספרים) נשאר."""
    for he, en in EN_TEXT:
        if t.startswith(he):
            rest = t[len(he):]
            if he in ("המחקר מוגבל למאגר המקורות המאושרים", "נבחר איסוף הסכמים בלבד", "דין זר", "תחום שיפוט לא צוין",
                      "מקור לא מסווג: "):
                return en
            if he == "נמצאו ":
                return en + rest.split(" ", 1)[0]
            return en + rest
    return t


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
    ap.add_argument("--lang", choices=("he", "en"), help="שפת המסמך; בלעדיו: deliverable_language בפרופיל, ואחרת עברית")
    ap.add_argument("--profile", help="פרופיל-לקוח.json: שפת התוצר (deliverable_language)")
    ap.add_argument("--approved-sources", help="מקורות-מאושרים.json (ברירת מחדל: משתנה הסביבה AREO_APPROVED_SOURCES, ואחריו העותק שבתוסף, "
                                               "lib/מקורות-מאושרים.json). נתיב שנמסר ואינו קיים: מחקר רגולטורי "
                                               "נעצר בקוד 2")
    ap.add_argument("--force", action="store_true", help="לדרוס קובץ פלט קיים")
    a = ap.parse_args()
    guard_out(a.out, [a.research, a.profile, a.matrix, a.approved_sources], a.force)
    r = normalise(json.load(io.open(a.research, encoding="utf-8")))
    prof = json.load(io.open(a.profile, encoding="utf-8")) if a.profile else {}
    try:
        blocking, flags, notes = check(r, stage="brief", approved_sources=a.approved_sources,
                                       inc_country=prof.get("incorporation_country"))
    except ApprovedSourcesMissing as e:
        print("סירוב: %s" % e)
        sys.exit(2)
    if blocking:
        print("המחקר אינו מוכן:")
        for b in blocking:
            print("  חוסם: " + b)
        sys.exit(1)

    B.RTL = not B.is_en(a.lang or B.profile_lang(prof) or "he")
    T = TXT["he" if B.RTL else "en"]
    ranks = NORM_RANKS if B.RTL else B.NORM_RANKS_EN
    scope = (SCOPES if B.RTL else B.SCOPES_EN)[r["scope"]]
    del B.GAPS[:]
    doc = Document()
    B.base(doc)
    today = datetime.date.today().isoformat()
    B.run(B.para(doc, after=2), T["title"] + B.s(r.get("agreement_type") or T["agreement"]), 17, True, B.NAVY)
    B.run(B.para(doc, after=4), T["stamp"] % (
        B.produced_on({"generated_at": today}), B.s(r.get("company_role")), scope),
        9.5, False, B.INK_SOFT)
    B.para(doc, T["intro"], 10.5, False, B.INK, after=10)

    questions = []
    if scope_has(r, "research"):
        law = r.get("law") or []
        core = [x for x in law if x.get("rank") in MANDATORY_ALLOWED_RANKS]
        B.h1(doc, T["law"])
        if a.matrix:
            B.para(doc, T["matrix"] % os.path.basename(str(a.matrix).replace("\\", "/")), 10, False, B.INK_SOFT, after=6)  # שם הקובץ בלבד: נתיב מקומי לא נכנס למסמך שהלקוח רואה
        grid(doc, T["law_head"],
             [[ranks.get(x.get("rank"), ""), (B.s(x.get("instrument")), x.get("url")), B.s(x.get("sections")),
               B.s(x.get("meaning")), T["verified"] if x.get("verified") else T["unverified"]] for x in core],
             link_cols=(1,))

        mand = r.get("mandatory_clauses") or []
        B.h1(doc, T["mand"])
        by_row = {x.get("row", i + 1): x for i, x in enumerate(law)}
        grid(doc, T["mand_head"],
             [[B.s(m.get("clause_id")), B.s(m.get("title")), B.s(m.get("requirement")),
               ("%s, %s" % (B.s(by_row.get(m.get("source_row"), {}).get("instrument")), B.s(m.get("source_section"))),
                by_row.get(m.get("source_row"), {}).get("url")),
               B.s(m.get("bound_party"))] for m in mand],
             link_cols=(3,))
        rec = [x for x in law if x.get("rank") in RECOMMENDED_RANKS]
        if rec:
            B.h1(doc, T["rec"])
            for x in rec:
                p = B.para(doc, after=3, indent=0.5)
                B.rich(p, "%s: %s " % (ranks[x["rank"]], B.s(x.get("contract_treatment"))), 10.5)
                B.link(p, x.get("url"), B.s(x.get("instrument")), 10)
        questions.append(T["qa"] % len(mand))

    if scope_has(r, "agreements"):
        ags = r.get("agreements") or []
        B.h1(doc, T["ags"] % (3 if scope_has(r, "research") else 1))
        grid(doc, T["ags_head"],
             [[str(x.get("no", i + 1)), (B.s(x.get("title")), x.get("url")), B.s(x.get("publisher")),
               "%s: %s" % (B.ORIENT_HE.get(x.get("orientation"), B.s(x.get("orientation"))) if B.RTL else B.ORIENT_EN.get(x.get("orientation"),
                                                                                  B.s(x.get("orientation"))),
                           B.s(x.get("orientation_reason"))),
               ", ".join(x.get("missing_mandatory") or []) or "-",
               ", ".join(f if B.RTL else en_text(f) for f in flags["agreements"][i])] for i, x in enumerate(ags)],
             link_cols=(1,))
        questions.append(T["qb"] % len(ags))

    gaps = [n for n in notes]
    unverified = [x for x in (r.get("law") or []) if not x.get("verified")] if scope_has(r, "research") else []
    if gaps or unverified:
        B.h1(doc, T["gaps"])
        for g in gaps:
            B.rich(B.para(doc, after=3, indent=0.5), g if B.RTL else en_text(g), 10.5)
        for x in unverified:
            p = B.para(doc, after=3, indent=0.5)
            B.run(p, T["unv_line"], 10.5, True)
            B.link(p, x.get("url"), B.s(x.get("instrument")), 10.5)

    B.h1(doc, T["approve"])
    for q in questions:
        B.para(doc, q, 11, True, B.INK, before=4, after=4)
    if not B.RTL:
        B.mixed_direction(doc)
    doc.save(a.out)

    print("סיכום המחקר: %s" % a.out)
    print("היקף: %s · מקורות דין: %d · סעיפי חובה: %d · הסכמים: %d" % (
        SCOPES[r["scope"]], len(r.get("law") or []) if scope_has(r, "research") else 0,
        len(r.get("mandatory_clauses") or []) if scope_has(r, "research") else 0,
        len(r.get("agreements") or []) if scope_has(r, "agreements") else 0))
    for n in notes:
        print("  " + n)


if __name__ == "__main__":
    main()
