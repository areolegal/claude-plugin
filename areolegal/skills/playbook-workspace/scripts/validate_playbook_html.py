#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""בודק שסביבת העבודה שנבנתה היא אפליקציה עובדת ולא קליפה.

למה הקובץ הזה קיים: התוצר הוא HTML של מאות קילובייטים, ואי אפשר לראות בעין אם
ההזרקה הצליחה. כשלים שקטים אפשריים: הנתונים לא הוזרקו והמסכים ריקים, ספריית
הגרפים לא הוטמעה והלוחות לא נטענים, או שהתוצר נבנה מתבנית ישנה.

**גרסה זו נכתבה מול התבנית הנוכחית.** הגרסה הקודמת בדקה סמנים של תבנית שיצאה
משימוש (app-shell, id="topics", finalizePlaybook), נכשלה על כל תוצר תקין,
ולא נתפסה מפני שאיש לא הריץ אותה מול תוצר אמיתי.

    python3 validate_playbook_html.py <קובץ.html> [--lang he|en]
"""
from __future__ import annotations

import argparse
import io
import sys

# סמני הזרקה שחייבים להיעלם בבנייה. אם נשארו, הסקריפט לא רץ או רץ חלקית.
MUST_BE_REPLACED = ["/*__DATA__*/null", "/*__CHARTJS__*/", "__ENTITY__"]

# המסכים. כל אחד הוא פונקציית תצוגה בתבנית; היעדר אחד פירושו מסך חסר.
VIEWS = ["vOverview", "vRules", "vSegPolicy", "vCompare", "vFindings",
         "vAdditions", "vPrecedents", "vDecisions", "vSources"]

# האינטראקציות שבלעדיהן זו תצוגה ולא סביבת עבודה.
INTERACTIONS = ["decide", "save", "tune", "globalSearch", "docExport",
                "openRule", "toggleEdit", "localStorage"]

# שלד העמוד.
STRUCTURE = ['id="nav"', 'id="wrap"', 'id="rlist"', 'id="drawer"', "normalizeRules", "boot"]

MIN_BYTES = 150_000          # פחות מזה: הגרפים או הנתונים לא נכנסו


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("path")
    ap.add_argument("--lang", default="he", choices=("he", "en"))
    a = ap.parse_args()

    try:
        html = io.open(a.path, encoding="utf-8").read()
    except OSError as e:
        print("לא ניתן לקרוא את הקובץ: %s" % e); return 1

    bad = []
    for m in MUST_BE_REPLACED:
        if m in html:
            bad.append("סמן הזרקה לא הוחלף: %s — ההזרקה לא הושלמה" % m)
    for m in VIEWS:
        if m not in html:
            bad.append("מסך חסר: %s" % m)
    for m in INTERACTIONS:
        if m not in html:
            bad.append("אינטראקציה חסרה: %s" % m)
    for m in STRUCTURE:
        if m not in html:
            bad.append("רכיב מבנה חסר: %s" % m)
    if len(html.encode("utf-8")) < MIN_BYTES:
        bad.append("התוצר קטן מ-%d בתים; הנתונים או ספריית הגרפים כנראה לא נכנסו"
                   % MIN_BYTES)
    if a.lang == "he":
        if 'dir="rtl"' not in html:
            bad.append('חסר dir="rtl" — תוצר עברי חייב כיווניות')
        if "—" in html:
            bad.append("נמצא מקף ארוך; אסור בכל תוצר")

    if bad:
        print("נכשל, %d ממצאים:" % len(bad))
        for b in bad:
            print("  - %s" % b)
        print("אין למסור את התוצר. בנה מחדש מהתבנית שנמשכה מהשירות.")
        return 1
    print("עבר: התוצר הוא סביבת עבודה מלאה (%d מסכים, %d אינטראקציות, %d KB)"
          % (len(VIEWS), len(INTERACTIONS), len(html.encode("utf-8")) // 1024))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
