# -*- coding: utf-8 -*-
"""
בונה את פרופיל-לקוח.json מתשובות השאלון, וגוזר את הרגולטורים לפי טבלאות
המיפוי שב-references/full_spec.md.

מדוע סקריפט ולא גזירה בכל הרצה: מיפוי הרגולטורים הוא כלל דטרמיניסטי, ולא
שיקול דעת. גזירה ידנית חוזרת בכל התקנה מייצרת שונות בין לקוחות באותו מצב
עובדתי, וזה בדיוק מה שפרופיל אמור למנוע. הסקריפט אינו שואל דבר ואינו ממציא
דבר: הוא מקבל את התשובות שכבר נמסרו ומחיל עליהן את הטבלאות.

הרצה:
  python3 build_profile.py --answers answers.json --out Areo-נתונים/פרופיל-לקוח.json

מבנה answers.json:
{
  "organization_name": "שם החברה",
  "organization_type": "חברה פרטית",
  "listed_in": ["ישראל"],
  "sectors": ["הייטק", "סייבר"],
  "financial_activity": ["מנהל תיקים"],
  "markets": ["ישראל", "האיחוד האירופי"],
  "display_language": "he"
}
"""
import argparse
import io
import json
import os
import sys
import uuid
from datetime import datetime

SCHEMA_VERSION = "1.0"
CORE_VERSION = "2.0.0"

# הרשימה הסגורה שמוצגת למשתמש. כל היתר נשמרים ואינם מוצגים.
PRIMARY_DISPLAY = [
    "הרשות להגנת הפרטיות",
    "רשות התחרות",
    "רשות ניירות ערך",
    "רשות שוק ההון, ביטוח וחיסכון",
    "בנק ישראל, הפיקוח על הבנקים",
    "SEC",
    "רשות הגנת המידע באיחוד האירופי, GDPR",
]

SEC_ISA = {"מנהל תיקים", "יועץ השקעות", "משווק השקעות", "מנהל קרנות נאמנות",
           "חתם", "נאמן לאיגרות חוב", "זירת סוחר", "רכז הצעה, מימון המונים",
           "חברת דירוג אשראי"}
CMISA = {"מבטח", "קרן פנסיה או גמל", "נותן שירותים פיננסיים מוסדר"}
BOI = {"תאגיד בנקאי", "חברת כרטיסי אשראי"}

SECTOR_REGULATORS = {
    "אנרגיה": ["רשות החשמל", "משרד האנרגיה", "המשרד להגנת הסביבה"],
    "ביומד": ["משרד הבריאות", "רשות החדשנות"],
    "בריאות": ["משרד הבריאות"],
    "מזון ומשקאות": ["משרד הבריאות", "הרשות להגנת הצרכן ולסחר הוגן"],
    "תקשורת ומדיה": ["משרד התקשורת"],
    "נדל״ן": ["רשם הקבלנים", "רשות מקרקעי ישראל"],
    "בנייה ותשתיות": ["רשם הקבלנים", "המשרד להגנת הסביבה"],
    "ביטחון ותעופה": ["אפ״י", "ITAR ו-EAR"],
    "תחבורה ולוגיסטיקה": ["משרד התחבורה"],
    "חינוך": ["משרד החינוך", "הרשות להגנת הצרכן ולסחר הוגן"],
    "קמעונאות": ["הרשות להגנת הצרכן ולסחר הוגן"],
    "תיירות ומלונאות": ["הרשות להגנת הצרכן ולסחר הוגן"],
    "תעשייה": ["המשרד להגנת הסביבה", "רשות החדשנות"],
    "הייטק": ["רשות החדשנות"],
    "סייבר": ["רשות החדשנות"],
}

MARKET_REGULATORS = {
    "האיחוד האירופי": [("רשות הגנת המידע באיחוד האירופי, GDPR", "Likely"),
                       ("חוק ה-AI האירופי", "Likely")],
    "בריטניה": [("ICO", "Likely"), ("SFO תחת UK Bribery Act", "Likely")],
    "ארצות הברית": [("FTC", "Likely"), ("DOJ תחת FCPA", "Likely"),
                    ("OFAC", "Likely"), ("BIS", "Likely")],
}

CORPORATE_REGULATORS = {
    "חברה ממשלתית": [("רשות החברות הממשלתיות", "Confirmed"),
                     ("חוק חובת המכרזים", "Confirmed")],
    "עמותה או חל״צ": [("רשם העמותות", "Confirmed")],
}

LISTING_REGULATORS = {
    "ישראל": [("רשות ניירות ערך", "Confirmed"), ("הבורסה לניירות ערך בתל אביב", "Confirmed")],
    "נאסד״ק": [("SEC", "Confirmed")],
    "לונדון": [("FCA", "Confirmed")],
    "רישום דואלי": [("רשות ניירות ערך", "Confirmed")],
}

# סעיפי קטלוג שהפרופיל מפעיל. רכיב הפלייבוק קורא את השדה הזה ראשון.
CATALOG_TRIGGERS = [
    (lambda a: True, ["הגנת הפרטיות ואבטחת מידע"]),
    (lambda a: "האיחוד האירופי" in a["markets"], ["DPA", "SCC", "סעיפי AI"]),
    (lambda a: "בריטניה" in a["markets"], ["DPA", "IDTA", "איסור שוחד"]),
    (lambda a: "ארצות הברית" in a["markets"], ["סנקציות", "בקרת יצוא", "פרטיות מדינתית"]),
    (lambda a: a["organization_type"] == "חברת אג״ח",
     ["שטר נאמנות ואמות מידה פיננסיות"]),
    (lambda a: bool(a["financial_activity"]), ["ציות רגולטורי פיננסי"]),
]


def add(reg_list, name, status, basis):
    for r in reg_list:
        if r["regulator_name"] == name:
            order = {"Confirmed": 0, "Likely": 1, "Potential": 2, "UserDeclared": 3}
            if order[status] < order[r["applicability_status"]]:
                r["applicability_status"] = status
                r["basis"] = basis
            return
    reg_list.append({"regulator_name": name, "applicability_status": status, "basis": basis})


def derive(a):
    regs = []
    # ציר 1, רוחבי
    add(regs, "הרשות להגנת הפרטיות", "Confirmed",
        "חוק הגנת הפרטיות, התשמ״א-1981; חל על כל ארגון")
    add(regs, "רשות התחרות", "Potential", "חל על כל ארגון, בדירוג Potential")
    for n in ["רשות המסים", "רשם החברות, רשות התאגידים",
              "משרד העבודה, מינהל הסדרה ואכיפה", "המוסד לביטוח לאומי",
              "נציבות שוויון זכויות לאנשים עם מוגבלות"]:
        add(regs, n, "Confirmed", "ציר רוחבי, חל על כל ארגון")

    # ציר 2, מעמד תאגידי
    for name, status in CORPORATE_REGULATORS.get(a["organization_type"], []):
        add(regs, name, status, "צורת ההתאגדות: %s" % a["organization_type"])
    if a["organization_type"] == "חברת אג״ח":
        add(regs, "רשות ניירות ערך", "Confirmed", "חברת אג״ח, כתאגיד מדווח")
    for where in a["listed_in"]:
        for name, status in LISTING_REGULATORS.get(where, []):
            basis = "נסחרת ב%s" % where
            if where == "רישום דואלי":
                basis = "רישום כפול, פרק ה׳3 לחוק ניירות ערך"
            add(regs, name, status, basis)

    # ציר 3, עיסוק פיננסי
    for act in a["financial_activity"]:
        if act in SEC_ISA:
            add(regs, "רשות ניירות ערך", "Confirmed", "עיסוק מפוקח: %s" % act)
        elif act in CMISA:
            add(regs, "רשות שוק ההון, ביטוח וחיסכון", "Confirmed", "עיסוק מפוקח: %s" % act)
        elif act in BOI:
            add(regs, "בנק ישראל, הפיקוח על הבנקים", "Confirmed", "עיסוק מפוקח: %s" % act)

    # ציר 3ב, ענף
    for sec in a["sectors"]:
        for name in SECTOR_REGULATORS.get(sec, []):
            add(regs, name, "Likely", "ענף פעילות: %s" % sec)

    # ציר 4, גיאוגרפי
    for mk in a["markets"]:
        for name, status in MARKET_REGULATORS.get(mk, []):
            add(regs, name, status, "שוק פעילות: %s" % mk)

    primary = [r for r in regs if r["regulator_name"] in PRIMARY_DISPLAY]
    secondary = [r for r in regs if r["regulator_name"] not in PRIMARY_DISPLAY]
    primary.sort(key=lambda r: PRIMARY_DISPLAY.index(r["regulator_name"]))
    return primary, secondary


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--answers", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    a = json.load(io.open(args.answers, encoding="utf-8"))
    for k, default in (("listed_in", []), ("sectors", []), ("financial_activity", []),
                       ("markets", []), ("display_language", "he")):
        a.setdefault(k, default)
    for k in ("organization_name", "organization_type"):
        if not a.get(k):
            print("חסר שדה חובה בתשובות: %s" % k)
            sys.exit(2)

    primary, secondary = derive(a)
    catalog = []
    for cond, items in CATALOG_TRIGGERS:
        if cond(a):
            for it in items:
                if it not in catalog:
                    catalog.append(it)

    now = datetime.now()
    profile = {
        "schema_version": SCHEMA_VERSION,
        "core_version": CORE_VERSION,
        "profile_id": "orgprof_" + uuid.uuid4().hex[:12],
        "version": 1,
        "status": "Provisional",
        "checked_at": now.strftime("%Y-%m-%d"),
        "confidential": "חסוי: הוכן לצורך קבלת ייעוץ משפטי",
        "organization_name": a["organization_name"],
        "organization_type": a["organization_type"],
        "organization_type_basis": "הצהרת המשתמש בהקמה",
        "public_market": {"listed": bool(a["listed_in"]), "venues": a["listed_in"]},
        "sector": {"primary": a["sectors"][0] if a["sectors"] else None,
                   "all": a["sectors"],
                   "financial_activity": a["financial_activity"]},
        "material_operating_jurisdictions": a["markets"],
        "regulatory_footprint_primary": primary,
        "regulatory_footprint_secondary": secondary,
        "clause_catalog_activated": catalog,
        "unresolved_questions": [],
        "onboarding": {"research_performed": False,
                       "method": "הצהרת המשתמש בלבד, בלי מחקר רשת"},
        "notes": ["הפרופיל שומר זהות רגולטורים בלבד, ולא תוכן חובות."],
        "display_language": a["display_language"],
        "deliverable_language": a.get("deliverable_language", a["display_language"]),
        "connections": a.get("connections", {
            "folders": [], "email": None, "calendar": None,
            "email_tracking": None, "scheduled_scan": None,
            "doc_access": {"mode": "local", "baseUrl": ""}, "asked_at": ""}),
        "areo_notice_shown": True,
        "generated_at": now.strftime("%Y-%m-%dT%H:%M:%S"),
        "last_updated": now.strftime("%Y-%m-%dT%H:%M:%S"),
    }

    d = os.path.dirname(os.path.abspath(args.out))
    if d and not os.path.isdir(d):
        os.makedirs(d)
    io.open(args.out, "w", encoding="utf-8").write(
        json.dumps(profile, ensure_ascii=False, indent=2))

    print("הפרופיל נבנה: %s" % profile["profile_id"])
    print("רגולטורים עיקריים, לתצוגה (%d):" % len(primary))
    for r in primary:
        print("   %-42s %-12s %s" % (r["regulator_name"], r["applicability_status"], r["basis"]))
    print("רגולטורים נוספים, נשמרים ואינם מוצגים: %d" % len(secondary))
    if catalog:
        print("סעיפי קטלוג שהופעלו: " + ", ".join(catalog))


if __name__ == "__main__":
    main()
