#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""שומר המחקר: בודק כל חיפוש ברשת לפני שהוא נשלח, בזמן מושב מחקר של בונה הפלייבוק.

`market-research.md`: "כל שאילתה נבדקת בקוד לפני שהיא נשלחת". החיפוש עצמו נעשה בכלי
החיפוש של Claude, ולכן עד עכשיו הבדיקה רצה רק כשהמסמך נקרא (`market_research.py fetch`),
אחרי שהשאילתה כבר יצאה למנוע החיפוש. ה-hook הזה רץ לפני כל WebSearch ו-WebFetch:

* אין מושב מחקר פעיל (`market_research.py start`), או שפג: לא עושה דבר. כל חיפוש אחר של
  המשתמש אינו מושפע.
* WebSearch בזמן המושב: אותה בדיקה של `query`. שאילתה עם שם הלקוח, פרט מזהה, רצף מילים
  או מספר מההסכמים נעצרת (קוד 2) ואינה נשלחת. שאילתה שעברה נרשמת ביומן השאילתות, ו-`fetch`
  יקבל אותה.
* WebFetch בזמן המושב: נעצר. קריאה במחקר עוברת רק ב-`market_research.py fetch`, עם הזהות
  הגלויה, הקצב, רשימת האתרים לפי סוג המקור והיומן.

תקלה בבדיקה עצמה בזמן מושב עוצרת את החיפוש, ולא מעבירה אותו: שאילתה שלא נבדקה אינה
יוצאת.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.join(os.path.dirname(HERE), "skills", "contract-playbook-builder", "scripts")


def block(msg):
    sys.stderr.write(msg + "\n")
    return 2


def main():
    try:
        event = json.load(sys.stdin)
    except ValueError:
        return 0
    tool = event.get("tool_name")
    if tool not in ("WebSearch", "WebFetch"):
        return 0
    sys.dont_write_bytecode = True
    sys.path.insert(0, SCRIPTS)
    try:
        import market_research as MR
        session = MR.load_session()
    except Exception:  # noqa: BLE001  בלי מושב תקין אין מה לשמור
        return 0
    if not session:
        return 0
    if tool == "WebFetch":
        return block("Areo: מושב מחקר פתוח. קריאה של מסמך במחקר עוברת רק ב-market_research.py fetch "
                     "(זהות גלויה, קצב, אתרים לפי סוג המקור, יומן). בסוף המחקר: market_research.py stop.")
    query = (event.get("tool_input") or {}).get("query") or ""
    try:
        corpus = MR.load(session["corpus"], "החילוץ") if session.get("corpus") else None
        profile = MR.load(session["profile"], "הפרופיל") if session.get("profile") else None
        # ה-hook אינו יודע אם החיפוש לשוק או לדין. שם חוק (מהרשימה של המושב, או בצורה של שם חוק) אינו
        # פרט של הלקוח, ולכן בשאילתה כזו הבדיקה היא של שאילתה רגולטורית; fetch בודק שוב לפי המטרה
        purpose = "legal" if session.get("statutes") or MR.STATUTE_RX.search(query) else "market"
        problem = MR.check_query(query, purpose, session["family_dir"], corpus, profile,
                                 session.get("statutes") or (), via="hook")
    except BaseException as exc:  # noqa: BLE001  SystemExit מ-load כשקובץ חסר
        return block("Areo: בדיקת השאילתה נכשלה (%s), ולכן החיפוש לא נשלח." % type(exc).__name__)
    if problem:
        return block("Areo: השאילתה נעצרה ולא נשלחה: %s. חפש בשאילתה כללית: סוג ההסכם, נושא הסעיף, "
                     "הצד, תחום השיפוט והענף בלבד." % problem)
    return 0


if __name__ == "__main__":
    sys.exit(main())
