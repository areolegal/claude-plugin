#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""יציאה לרשת של מעריך הסיכונים: בקשה אחת למקור רשמי, דרך שכבת הרשת האחת.

הסקריפט עוטף את קוד הייחוס של ענבל (`areolegal/lib/common/net.py`, `fetch`,
ו-`risk/entity_store.py`, `EntityStore.store_page`; הערות מעריך הסיכונים 3.6,
שינויים 10.10, 18.10, 19.5 ו-19.11). **אין שולף אחר**: לא בסקריפט שנכתב לריצה,
לא בכלי חיפוש ולא בדפדפן.

* **רק מקור ממשלתי או רשמי מהרשימה** שהבודק מקבל (`validate_register`,
  `APPROVED_DOMAINS`). כל דומיין אחר, כולל אתרי חדשות, מאגרים מסחריים והאתר
  של הצד השני, מסורב לפני הבקשה ואחרי הפניה.
* **השאלה, לא ההסכם.** המטרה (`--purpose`) והכתובת נבדקות לפני השליחה: שם
  החברה, שם הצד שכנגד (בשאילתה רגולטורית), מספר חברה, טלפון או מספר ארוך בלי
  הקשר רשמי עוצרים את הבקשה. מזהה רשמי של חוק או תקנה אינו פרט של הלקוח.
* **בחקר ישות** (`--kind entity`) השאילתה בנויה רק משם הצד שכנגד, מספר הרישום
  שלו (`--registration-no`) ומדינה, וחקר ישות רץ רק בבקשה מפורשת של המשתמש.
* **עשר בקשות לשאלה** (`--question`), ואז עצירה.
* **מזהה גלוי** של Areo, עם כתובת קשר, בכל בקשה. חסימה (403, 429, CAPTCHA) עוצרת
  את הדומיין עד סוף ההרצה, בלי ניסיון חוזר, ומחזירה משימה לעורך הדין.
* **העותק הגולמי** נשמר בתיקיית העסקה, ב-`sources/<source_id>.<סיומת>`, עם
  SHA-256 והכתובת הסופית, בתקרות של 200 קילובייט לקטע ו-2 מגה-בייט לעסקה. דף
  גדול נשמר רק כחלון סביב הקטע המילולי (`--excerpt`).

    python3 scripts/fetch_source.py --deal "<תיקיית העסקה>" --source-id SRC-01 \\
        --url "<הכתובת המדויקת>" --purpose "<השאלה, בלי פרטי הלקוח>" --question Q1 \\
        [--excerpt "<הקטע המילולי>"] --profile "<פרופיל-לקוח.json>" [--counterparty "<השם>"]

הפלט הוא JSON: `log` נכנס כמו שהוא ל-`research.search_log` (או ל-`lookups` בחקר
ישות), ו-`stored` ל-`research.raw_copies`. הטקסט עצמו אינו מודפס; הוא נקרא
מהעותק השמור.

קוד יציאה: **0** נשמר, **3** סורב, נחסם או לא נשמר (ראו `reason` ו-
`lawyer_task`), **2** קלט חסר.
"""
import argparse
import io
import json
import os
import re
import sys
import tempfile
from urllib.parse import unquote, urlsplit

import areo_lib  # noqa: F401  מוסיף את areolegal/lib לנתיב הייבוא

from common import net  # noqa: E402
from risk.entity_store import EntityStore  # noqa: E402
from risk.validate_register import APPROVED_DOMAINS  # noqa: E402

MAX_PER_QUESTION = 10


def run_dir_for(deal):
    """מצב ההרצה (חסימות ומונה לשאלה) נשמר בתיקייה זמנית, ולא בתיקיית הלקוח. המפתח הוא הנתיב
    המלא של העסקה, כדי ששתי עסקאות באותו שם לא יחלקו מונה."""
    import hashlib
    key = hashlib.sha256(os.path.abspath(deal).encode("utf-8")).hexdigest()[:16]
    d = os.path.join(tempfile.gettempdir(), "areo-net", key)
    os.makedirs(d, exist_ok=True)
    return d


def count_question(run_dir, question):
    # המונה הוא להרצה, ולא לנצח: קובץ ליום, כך שהרצה של מחר מתחילה מאפס
    import datetime as _dt
    p = os.path.join(run_dir, "questions-%s.json" % _dt.date.today().isoformat())
    try:
        with io.open(p, encoding="utf-8") as fh:
            counts = json.load(fh)
    except (OSError, ValueError):
        counts = {}
    counts[question] = counts.get(question, 0) + 1
    with io.open(p, "w", encoding="utf-8") as fh:
        json.dump(counts, fh)
    return counts[question]


def names_from(profile_path):
    if not profile_path:
        return []
    with io.open(profile_path, encoding="utf-8") as fh:
        prof = json.load(fh)
    names = [prof.get("organization_name"), prof.get("registered_legal_name"), prof.get("company_name")]
    names += [e.get("name") if isinstance(e, dict) else e for e in prof.get("related_entities") or ()]
    return [n for n in names if n and len(str(n)) >= 2]


def out(res, code):
    print(json.dumps(res, ensure_ascii=False, indent=1))
    return code


def main(argv=None):
    sys.dont_write_bytecode = True
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--deal", required=True, help="תיקיית העסקה: העותק נשמר ב-sources/")
    ap.add_argument("--source-id", required=True, help="מזהה המקור במרשם, למשל SRC-01")
    ap.add_argument("--url", required=True, help="הכתובת המדויקת של הדף במקור הרשמי")
    ap.add_argument("--purpose", required=True, help="השאלה שהבקשה עונה עליה, בלי פרטי הלקוח")
    ap.add_argument("--question", required=True, help="מזהה השאלה ב-research.question: עד עשר בקשות לשאלה")
    ap.add_argument("--excerpt", help="הקטע המילולי: בדף גדול נשמר רק חלון סביבו")
    ap.add_argument("--profile", help="פרופיל-לקוח.json: שמות החברה, שאסור שיופיעו בשאילתה")
    ap.add_argument("--counterparty", help="שם הצד שכנגד: אסור בשאילתה רגולטורית")
    ap.add_argument("--kind", choices=("regulatory", "entity"), default="regulatory",
                    help="entity: חקר ישות, שבו שם הצד שכנגד ומספר הרישום שלו הם השאילתה עצמה")
    ap.add_argument("--registration-no", help="בחקר ישות: מספר הרישום של הצד שכנגד, כפי שהוא בהסכם")
    a = ap.parse_args(argv)

    if not os.path.isdir(a.deal):
        print("תיקיית העסקה אינה קיימת: %s" % a.deal)
        return 2
    blocked_names = names_from(a.profile)
    if a.counterparty and a.kind == "regulatory":
        blocked_names.append(a.counterparty)
    query = unquote(urlsplit(a.url).query or "") + " " + unquote(urlsplit(a.url).path) + " " + a.purpose
    if a.kind == "entity":
        # בחקר ישות השאילתה בנויה רק משם, מספר רישום ומדינה של הצד שכנגד: הם אינם פרט של הלקוח
        if not (a.counterparty or a.registration_no):
            print("בחקר ישות נדרשים --counterparty או --registration-no: השאילתה בנויה רק מהם")
            return 2
        for own in (a.counterparty, a.registration_no):
            if own:
                query = query.replace(own, " ")
    detail = net.client_detail_in_query(query, blocked_names)
    if detail:
        return out({"status": None, "blocked": False, "stored": None,
                    "reason": "refused: פרט של הלקוח או של העסקה בשאילתה (%s). השאילתה נבנית מהשאלה בלבד" % detail},
                   3)
    run_dir = run_dir_for(a.deal)
    n = count_question(run_dir, a.question)
    if n > MAX_PER_QUESTION:
        return out({"status": None, "blocked": False, "stored": None,
                    "reason": "refused: %d בקשות לשאלה %s. עוצרים, ומה שלא נמצא נכתב בפרק 5"
                              % (MAX_PER_QUESTION, a.question)}, 3)

    res = net.fetch(a.url, a.purpose, allowed_domains=APPROVED_DOMAINS, store=EntityStore(a.deal),
                    source_id=a.source_id, excerpt=a.excerpt, run_dir=run_dir)
    show = {k: v for k, v in res.items() if k not in ("content", "text")}
    show["question"] = a.question
    ok = bool(res.get("stored")) and not res.get("blocked")
    return out(show, 0 if ok else 3)


if __name__ == "__main__":
    sys.exit(main())
