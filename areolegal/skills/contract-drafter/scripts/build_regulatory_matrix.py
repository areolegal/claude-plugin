#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""קובץ ה-Excel של מצב 4, לחברה שעליה עובדים בהרצה הזאת.

    python3 build_regulatory_matrix.py --research "Areo-נתונים/research-<slug>.json" \\
        --out "<סוג ההסכם> - מטריצה רגולטורית <יום.חודש.שנה>.xlsx"

הגיליונות נקבעים לפי היקף העבודה שהמשתמש בחר (scope):
  research / both   "מטריצה רגולטורית" ו"סעיפי חובה"
  agreements / both "הסכמים מייצגים"

כל הגיליונות מימין לשמאל, שורת כותרת מוקפאת עם מסנן, Arial ועטיפת טקסט. בתוצר באנגלית (`--lang en`, או
deliverable_language מ-`--profile`): שמות הגיליונות, הכותרות והערכים הקבועים באנגלית, והגיליונות משמאל לימין.
כל מקור ישירות לחיץ, וכל סעיף חובה מקושר פנימית לשורת המקור שלו. תאריכים
נכתבים כמחרוזת יום.חודש.שנה, כדי שהתצוגה האזורית לא תהפוך אותם.

קוד יציאה 1 כשכללי המקורות של research_sources.py נכשלים: מקור מדומיין אסור,
מקור בלי קישור, סדר שאינו לפי המדרג, או סעיף חובה על מקור לא מאומת.
"""
import argparse
import io
import json
import os
import sys

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from research_sources import (NORM_RANKS, NOT_FOUND, RANK_STATUS, check, display_date,  # noqa: E402
                              normalise, scope_has, ApprovedSourcesMissing)
from build_template_registry import guard_out  # noqa: E402

try:                                   # פלט עברי במסוף של Windows
    sys.stdout.reconfigure(encoding="utf-8")
except (AttributeError, ValueError):   # pragma: no cover
    pass

FONT = "Arial"
HEAD_FILL = PatternFill("solid", fgColor="12314F")
STATUS_FILL = {"מחייב": "E8EDF2", "מנחה": "F4F4F4", "בהליך": "FFF4E0"}
THIN = Side(style="thin", color="C9CFD6")
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
WRAP = Alignment(horizontal="right", vertical="top", wrap_text=True, readingOrder=2)
WRAP_LTR = Alignment(horizontal="left", vertical="top", wrap_text=True, readingOrder=1)

LAW_SHEET = "מטריצה רגולטורית"
MAND_SHEET = "סעיפי חובה"
AGR_SHEET = "הסכמים מייצגים"

# טקסט קבוע בשתי השפות (דרישת מוצר: deliverable_language קובע את שפת התוצר)
TXT = {
    "he": {"sheets": (LAW_SHEET, MAND_SHEET, AGR_SHEET),
           "law_head": ["מס\"ד", "דרג", "סוג המקור", "שם המקור", "גוף מפרסם", "מעמד", "תאריך פרסום מקורי",
                        "תאריך פרסום או תיקון אחרון", "סעיפים רלוונטיים", "תמצית הסעיפים", "המשמעות להסכם",
                        "אופן ההתייחסות בהסכם", "סוג השפעה", "סעיף חובה", "קישור", "סטטוס אימות"],
           "mand_head": ["מזהה", "שם הסעיף", "הדרישה", "שורת מקור", "סעיף בחיקוק", "הצד החייב",
                         "נוסח מוצע בתמצית", "סטטוס"],
           "ags_head": ["מס'", "כותרת", "מפרסם", "סוג האתר", "דין חל", "כיוון", "נימוק לכיוון", "נושאים",
                        "מה ההסכם תורם", "סעיפי חובה חסרים", "תאריך פרסום", "שימוש", "קישור"],
           "yes": "כן", "no": "לא", "verified": "אומת", "unverified": "טעון אימות", "included": "כלול", "removed": "הוסר לבקשת הלקוח", "row": "שורה %s"},
    "en": {"sheets": ("Regulatory matrix", "Mandatory clauses", "Representative agreements"),
           "law_head": ["No.", "Rank", "Source type", "Source", "Publisher", "Standing", "Original publication date",
                        "Last publication or amendment", "Relevant sections", "Summary of sections",
                        "Meaning for the agreement", "Treatment in the agreement", "Type of effect", "Mandatory clause",
                        "Link", "Verification status"],
           "mand_head": ["ID", "Clause name", "Requirement", "Source row", "Section in the law", "Bound party",
                         "Proposed wording in brief", "Status"],
           "ags_head": ["No.", "Title", "Publisher", "Site type", "Governing law", "Orientation", "Orientation reason",
                        "Topics", "What the agreement contributes", "Missing mandatory clauses", "Publication date",
                        "Use", "Link"],
           "yes": "Yes", "no": "No", "verified": "Verified", "unverified": "Needs verification", "included": "Included", "removed": "Removed by the client",
           "row": "Row %s"},
}
STATUS_EN = {"מחייב": "Binding", "מנחה": "Guidance", "בהליך": "In process"}
SOURCE_TYPE_EN = {"אתר משפטי": "Legal website", "משרד עורכי דין": "Law firm", "רגולטור": "Regulator",
                  "גוף ציבורי": "Public body", "הליך תחרותי ציבורי": "Public competitive procedure", "דיווח פומבי": "Public filing",
                  "אחר": "Other"}
RANKS_EN = {1: "Primary legislation", 2: "Secondary legislation", 3: "Binding regulator instruction",
            4: "Regulator guidance", 5: "Staff position or FAQ", 6: "Source in process"}
B_ORIENT_HE = {"לטובת הפוזיציה": "לטובת הצד שלכם", "מאוזן": "מאוזן", "נגד הפוזיציה": "נגד הצד שלכם"}
ORIENT_EN = {"לטובת הפוזיציה": "Favours our position", "מאוזן": "Balanced", "נגד הפוזיציה": "Against our position"}
FLAGS_EN = {"מותר כלשונו, בציון המקור": "Verbatim use allowed, with attribution",
            "מבנה, נושאים ועמדות בלבד": "Structure, topics and positions only",
            "נכתב לטובת המדינה כלקוח": "Written in favour of the state as customer", "לעיון בלבד": "For reference only",
            "חסר נימוק לכיוון": "Orientation reason missing"}
LTR = False   # נקבע מהשפה בזמן הבנייה


def ddate(v):
    """תאריך לתצוגה; "לא אותר" של research_sources באנגלית בתוצר באנגלית."""
    d = display_date(v, "en" if LTR else "he")
    return "[not found]" if LTR and d == NOT_FOUND else d


def sheet(wb, title, header, widths):
    ws = wb.create_sheet(title)
    ws.sheet_view.rightToLeft = not LTR
    ws.append(header)
    for j, w in enumerate(widths, 1):
        c = ws.cell(row=1, column=j)
        c.font = Font(name=FONT, bold=True, color="FFFFFF", size=10)
        c.fill = HEAD_FILL
        c.alignment = Alignment(horizontal="left" if LTR else "right", vertical="center", wrap_text=True,
                                readingOrder=1 if LTR else 2)
        c.border = BORDER
        ws.column_dimensions[get_column_letter(j)].width = w
    ws.freeze_panes = "A2"
    return ws


def put(ws, row, values, fill=None):
    for j, v in enumerate(values, 1):
        c = ws.cell(row=row, column=j, value=v)
        c.font = Font(name=FONT, size=10)
        c.alignment = WRAP_LTR if LTR else WRAP
        c.border = BORDER
        if fill:
            c.fill = PatternFill("solid", fgColor=fill)


def hyperlink(cell, target, text=None):
    cell.value = text if text is not None else target
    cell.hyperlink = target
    cell.font = Font(name=FONT, size=10, color="0B5CAD", underline="single")


def finish(ws, ncols, nrows):
    if nrows:
        ws.auto_filter.ref = "A1:%s%d" % (get_column_letter(ncols), nrows + 1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--research", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--lang", choices=("he", "en"), help="שפת הקובץ; בלעדיו: deliverable_language בפרופיל, ואחרת עברית")
    ap.add_argument("--profile", help="פרופיל-לקוח.json: שפת התוצר (deliverable_language)")
    ap.add_argument("--approved-sources", help="מקורות-מאושרים.json (ברירת מחדל: משתנה הסביבה AREO_APPROVED_SOURCES, ואחריו העותק שבתוסף, "
                                               "lib/מקורות-מאושרים.json). נתיב שנמסר ואינו קיים: מחקר רגולטורי "
                                               "נעצר בקוד 2")
    ap.add_argument("--force", action="store_true", help="לדרוס קובץ פלט קיים")
    a = ap.parse_args()
    guard_out(a.out, [a.research, a.profile, a.approved_sources], a.force)
    global LTR
    prof = json.load(io.open(a.profile, encoding="utf-8")) if a.profile else {}
    dl = str(prof.get("deliverable_language") or "").strip().lower()
    if dl == "both":   # both: התוצר הראשי בשפת הממשק (language-policy.md)
        dl = str(prof.get("display_language") or "").strip().lower()
    v = str(a.lang or dl or "he").strip().lower()
    LTR = v[:2] == "en" or v in ("english", "אנגלית")
    T = TXT["en" if LTR else "he"]
    law_sheet, mand_sheet, agr_sheet = T["sheets"]
    r = normalise(json.load(io.open(a.research, encoding="utf-8")))
    try:
        blocking, flags, notes = check(r, stage="brief", approved_sources=a.approved_sources,
                                       inc_country=prof.get("incorporation_country"))
    except ApprovedSourcesMissing as e:
        print("סירוב: %s" % e)
        sys.exit(2)
    if blocking:
        print("קובץ ה-Excel לא נבנה:")
        for b in blocking:
            print("  חוסם: " + b)
        sys.exit(1)

    wb = Workbook()
    wb.remove(wb.active)
    law_rows = {}

    if scope_has(r, "research"):
        header = T["law_head"]
        ws = sheet(wb, law_sheet, header, [6, 6, 16, 32, 20, 9, 12, 14, 16, 36, 36, 40, 12, 9, 34, 14])
        for i, src in enumerate(r.get("law") or []):
            n = i + 2
            rank = src.get("rank")
            status = src.get("status") or RANK_STATUS.get(rank, "")
            law_rows[src.get("row", i + 1)] = n
            put(ws, n, [src.get("row", i + 1), rank,
                        src.get("source_kind") or (RANKS_EN if LTR else NORM_RANKS).get(rank, ""),
                        src.get("instrument", ""), src.get("publisher", ""), STATUS_EN.get(status, status) if LTR else status,
                        ddate(src.get("published_original")), ddate(src.get("published_last")),
                        src.get("sections", ""), src.get("sections_summary", ""), src.get("meaning", ""),
                        src.get("contract_treatment", ""), src.get("effect", ""),
                        T["yes"] if src.get("mandatory") else T["no"], src.get("url", ""),
                        T["verified"] if src.get("verified") else T["unverified"]],
                STATUS_FILL.get(status))
            hyperlink(ws.cell(row=n, column=4), src["url"], src.get("instrument", ""))
            hyperlink(ws.cell(row=n, column=15), src["url"])
        finish(ws, len(header), len(r.get("law") or []))

        header = T["mand_head"]
        ws = sheet(wb, mand_sheet, header, [8, 24, 40, 10, 14, 14, 44, 16])
        for i, m in enumerate(r.get("mandatory_clauses") or []):
            n = i + 2
            put(ws, n, [m.get("clause_id", ""), m.get("title", ""), m.get("requirement", ""),
                        m.get("source_row", ""), m.get("source_section", ""), m.get("bound_party", ""),
                        m.get("proposed_text", ""),
                        # כלול, או הוסר לבקשת הלקוח. אין עמודת אישור ואין סטטוס "מאושר" (כלל 6)
                        T["removed"] if m.get("status") == "הוסר" else T["included"]])
            target = law_rows.get(m.get("source_row"))
            if target:
                hyperlink(ws.cell(row=n, column=4), "#'%s'!D%d" % (law_sheet, target),
                          T["row"] % m.get("source_row"))
        finish(ws, len(header), len(r.get("mandatory_clauses") or []))

    if scope_has(r, "agreements"):
        header = T["ags_head"]
        ws = sheet(wb, agr_sheet, header, [6, 30, 20, 14, 12, 14, 36, 30, 34, 16, 12, 22, 34])
        for i, ag in enumerate(r.get("agreements") or []):
            n = i + 2
            put(ws, n, [ag.get("no", i + 1), ag.get("title", ""), ag.get("publisher", ""),
                        SOURCE_TYPE_EN.get(ag.get("source_type"), ag.get("source_type", "")) if LTR
                        else ag.get("source_type", ""), ag.get("governing_law", ""),
                        ORIENT_EN.get(ag.get("orientation"), ag.get("orientation", "")) if LTR else B_ORIENT_HE.get(ag.get("orientation"), ag.get("orientation", "")),
                        ag.get("orientation_reason", ""), ", ".join(ag.get("topics") or []),
                        ag.get("contributes", ""), ", ".join(ag.get("missing_mandatory") or []),
                        ddate(ag.get("published")),
                        ", ".join(FLAGS_EN.get(f, f) if LTR else f for f in flags["agreements"][i]),
                        ag.get("url", "")])
            hyperlink(ws.cell(row=n, column=2), ag["url"], ag.get("title", ""))
            hyperlink(ws.cell(row=n, column=13), ag["url"])
        finish(ws, len(header), len(r.get("agreements") or []))

    wb.save(a.out)
    print("קובץ ה-Excel: %s" % a.out)
    print("גיליונות: %s" % " · ".join(wb.sheetnames))
    for note in notes:
        print("  " + note)


if __name__ == "__main__":
    main()
