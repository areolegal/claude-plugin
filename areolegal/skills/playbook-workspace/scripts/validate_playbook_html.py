#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""בודק שסביבת העבודה שנבנתה היא אפליקציה עובדת ולא קליפה.

למה הקובץ הזה קיים: התוצר הוא HTML של מאות קילובייטים, ואי אפשר לראות בעין אם
ההזרקה הצליחה. כשלים שקטים אפשריים: הנתונים לא הוזרקו והמסכים ריקים, ספריית
הגרפים לא הוטמעה והלוחות לא נטענים, או שהתוצר נבנה מתבנית ישנה.

הבדיקה היא על המחרוזות שבתוצר, ולכן היא זולה ורצה בכל בנייה. היא אינה מחליפה
את רתמות ה-jsdom, שמריצות את הדף בפועל (`qa_artifact.js`, `qa_basis.js`,
`qa_shared_decisions.js`, `qa_imposed.js`).

**מה נבדק גם בשלילה:** בדף אין אישור מדיניות. אין בו כפתורי הכרעה, אין טקסט
שאומר שעמדה אושרה או נכנסה למדיניות, אין ייצוא ל-Office ואין חבילת סוכן
(`dashboard_spec.md`, "מה אסור"). פעולה כזאת שחוזרת לתבנית נתפסת כאן.

    python3 validate_playbook_html.py <קובץ.html> [--lang he|en] [--artifact]
"""
from __future__ import annotations

import argparse
import io
import re
import sys

# סמני הזרקה שחייבים להיעלם בבנייה. אם נשארו, הסקריפט לא רץ או רץ חלקית.
MUST_BE_REPLACED = ["/*__DATA__*/null", "/*__CHARTJS__*/", "__ENTITY__", "__FAMILIES__"]

# המסכים. כל אחד הוא פונקציית תצוגה בתבנית; היעדר אחד פירושו מסך חסר.
VIEWS = ["vOverview", "vRules", "vSegPolicy", "vCompare", "vCommercial", "vFindings",
         "vAdditions", "vPrecedents", "vDecisions", "vSources", "vExport"]

# האינטראקציות שבלעדיהן זו תצוגה ולא סביבת עבודה.
INTERACTIONS = ["save", "tune", "globalSearch", "openRule", "toggleEdit",
                "localStorage", "setNote", "setProp", "dlComments", "basisText",
                "covPanel", "imposedLayers"]

# שלד העמוד.
STRUCTURE = ['id="nav"', 'id="wrap"', 'id="rlist"', 'id="drawer"', 'id="pbbar"',
             "normalizeRules", "boot"]

# מה שאסור להיות בדף. שם פונקציה ומחרוזת תצוגה גם יחד.
FORBIDDEN = [
    ("function decide(", "כפתור הכרעה: הדף אינו מאשר מדיניות"),
    ("approveAll", "כפתור אישור כל הפלייבוק"),
    ("אישור כל הפלייבוק", "טקסט אישור כל הפלייבוק"),
    ("נכנס למדיניות", "טקסט שאומר שעמדה נכנסה למדיניות"),
    ("function agentPack", "חבילת סוכן"),
    ("function officeBlob", "ייצוא למסמכי Office"),
    ("function decisionsPack", "יומן החלטות כ-JSON"),
    ("ההחלטה שלך", "פס הכרעה בסעיף"),
    ("טרם הוכרע", "תווית מצב הכרעה"),
    ("נערך ידנית", "תווית עריכה של מדיניות"),
]
# המפרט אוסר במפורש כפתור או טקסט "מאשר", "אושר" או "נכנס למדיניות".
# הבדיקה היא על המילה עצמה בתוך טקסט שהמשתמש רואה, ולא על כל הופעה של
# האותיות, כדי שלא תיפול על "אישור ביטוחי" או "מאושרת" בתוך ציטוט מהסכם.
APPROVAL_WORDS = re.compile(
    r">\s*(?:מאשר|מאשרת|לא מאשר|אושר|אושרו|מאושר)\s*<"
    r"|>[^<]{0,40}(?:אישור כל הפלייבוק|נכנס למדיניות|אושר עם שינוי)")

# תוויות חובה שהמפרט קובע מילה במילה
REQUIRED_HE = [
    ("הצעה, לא מדיניות", "התווית שמבדילה הצעה ממדיניות"),
    ("נימוקים מלאים", "מונה הנימוקים, במקום מונה האישורים"),
    ("שאלות פתוחות", "שם המסך שהחליף את מסך ההחלטות"),
]

MIN_BYTES = 150_000          # פחות מזה: הגרפים או הנתונים לא נכנסו


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("path")
    ap.add_argument("--lang", default="he", choices=("he", "en"))
    ap.add_argument("--artifact", action="store_true",
                    help="תוצר לעמוד משותף: בלי doctype, ובלי מסלולי הורדה")
    a = ap.parse_args()

    try:
        html = io.open(a.path, encoding="utf-8").read()
    except OSError as e:
        print("לא ניתן לקרוא את הקובץ: %s" % e)
        return 1

    bad = []
    for m in MUST_BE_REPLACED:
        if m in html:
            bad.append("סמן הזרקה לא הוחלף: %s, ההזרקה לא הושלמה" % m)
    for m in VIEWS:
        if m not in html:
            bad.append("מסך חסר: %s" % m)
    for m in INTERACTIONS:
        if m not in html:
            bad.append("אינטראקציה חסרה: %s" % m)
    for m in STRUCTURE:
        if m not in html:
            bad.append("רכיב מבנה חסר: %s" % m)
    for m, why in FORBIDDEN:
        if m in html:
            bad.append("אסור בדף, %s (%s)" % (why, m))
    for m in APPROVAL_WORDS.findall(html)[:4]:
        bad.append("אסור בדף, שפת אישור בטקסט שהמשתמש רואה: %s" % str(m)[:60])
    if a.lang == "he":
        for m, why in REQUIRED_HE:
            if m not in html:
                bad.append("תווית חובה חסרה, %s (%s)" % (why, m))
    if len(html.encode("utf-8")) < MIN_BYTES:
        bad.append("התוצר קטן מ-%d בתים; הנתונים או ספריית הגרפים כנראה לא נכנסו"
                   % MIN_BYTES)
    if a.lang == "he":
        # בתוצר המקומי הכיווניות על התגית; בעמוד משותף אין <html> שלנו,
        # והיא נקבעת בסקריפט קצר בראש התוכן
        rtl = ('dir="rtl"' in html
               or 'setAttribute("dir","rtl")' in html.replace(" ", ""))
        if not rtl:
            bad.append("חסרה כיווניות rtl, ותוצר עברי חייב אותה")
        if "—" in html or "–" in html:
            bad.append("נמצא מקף ארוך; אסור בכל תוצר")

    # הדף אינו פונה לשרת חיצוני: לא גופנים, לא ספריות ולא קישור שאינו https
    for m in re.findall(r'(?:src|href)="(http://[^"]{0,120})"', html):
        bad.append("פנייה לא מאובטחת מהדף: %s" % m[:80])
    for m in re.findall(r'<(?:script|link)[^>]+(?:src|href)="(https://[^"]{0,120})"', html):
        bad.append("הדף טוען מהרשת, ואסור לו: %s" % m[:80])

    if a.artifact:
        # רק בראש הקובץ: המחרוזת מופיעה גם בתוך קוד הדף, בקובץ השיתוף
        if html.lstrip()[:200].upper().startswith("<!DOCTYPE"):
            bad.append("תוצר לעמוד משותף אינו נושא doctype")
        if 'publishTarget": "artifact"' not in html and "publishTarget':'artifact'" not in html:
            bad.append("בתוצר המשותף publishTarget אינו artifact")

    if bad:
        print("נכשל, %d ממצאים:" % len(bad))
        for b in bad:
            print("  - %s" % b)
        print("אין למסור את התוצר. בנה מחדש מהתבנית שנמשכה מהשירות.")
        return 1
    print("עבר: התוצר הוא סביבת עבודה מלאה (%d מסכים, %d אינטראקציות, %d KB), "
          "ואין בו פעולת אישור" % (len(VIEWS), len(INTERACTIONS),
                                   len(html.encode("utf-8")) // 1024))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
