#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""יציאה לרשת של מעריך הסיכונים: בקשה אחת למקור רשמי, דרך שכבת הרשת האחת.

הסקריפט עוטף את שכבת הרשת של הספרייה המשותפת (`lib/common/net.py`, `fetch`, ו-`risk/entity_store.py`,
`EntityStore.store_page`). **אין שולף אחר**: לא בסקריפט שנכתב לריצה, לא בכלי חיפוש ולא בדפדפן.

* **פסיקה לעולם לא** (כלל 1.1): כתובת של אתר בית משפט, מאגר פסיקה או מדור פסיקה באתר מאושר
  (`common.case_law.case_law_url`, ו-`case_law_only` שבקובץ המקורות) מסורבת לפני כל הכרעה אחרת,
  ושוב על הכתובת הסופית אחרי הפניה. הליכים משפטיים נגד הצד שכנגד הם משימה לעורך הדין.
* **רק בדיקת רקע על הצד שכנגד** (מטרה D בכללים המשותפים): הבקשה
  יוצאת רק עם `--purpose entity` (או `--kind entity`), ורק לבקשה מפורשת של הלקוח. כל מטרה אחרת,
  כולל אימות של דרישה רגולטורית, מסורבת לפני הבקשה (קוד 3): דרישה שלא אומתה במסמכים או
  בפלייבוק מסומנת "טעון בדיקה משפטית", בלי יציאה לרשת.
* **מקור רשמי מהרשימה** שהבודק מקבל (`validate_register.approved_domains(..., purpose="entity")`):
  הקובץ המשותף `מקורות-מאושרים.json`, הרשימה הרגילה וגם הקטגוריה `entity_check` (מרשמים,
  רשימות סנקציות). העותק נארז בתוסף (`lib/מקורות-מאושרים.json`) ונקרא כברירת מחדל; `--approved-sources`
  (או משתנה הסביבה `AREO_APPROVED_SOURCES`) גובר עליו. אין רשימת נפילה בקוד: כשהרשימה אינה נקראת, הבקשה מסורבת. מקור עם הגבלת נתיב נבדק גם בנתיב,
  ותתי-דומיינים רק כשהרשימה מתירה אותם.
* **או כלי תקשורת**, לפי כלל ולא לפי רשימה (`validate_register.media_problem`): לא רשת חברתית,
  בלוג, פורום, מנוע חיפוש או מאגר מסחרי, ולעולם לא בית משפט או מאגר פסיקה (כלל 1.1). הפלט מסמן
  `source_class: "media"` ואת התווית "אות לא מאומת, מהתקשורת"; אות כזה אינו בסיס יחיד לממצא.
* **השאלה, לא ההסכם.** המטרה והכתובת נבדקות לפני השליחה: שם החברה, מספר חברה, טלפון או מספר
  ארוך בלי הקשר רשמי עוצרים את הבקשה. השאילתה בנויה רק מהשם הפומבי של הצד שכנגד
  (`--counterparty`), מספר הרישום שלו (`--registration-no`) ומדינה.
* **עשר בקשות לשאלה** (`--question`), ואז עצירה.
* **מזהה גלוי** של Areo, עם כתובת קשר, בכל בקשה. חסימה (403, 429, CAPTCHA) עוצרת
  את הדומיין עד סוף ההרצה, בלי ניסיון חוזר, ומחזירה משימה לעורך הדין.
* **העותק הגולמי** נשמר בתיקיית העסקה, ב-`sources/<source_id>.<סיומת>`, עם
  SHA-256 והכתובת הסופית, בתקרות של 200 קילובייט לקטע ו-2 מגה-בייט לעסקה. דף
  גדול נשמר רק כחלון סביב הקטע המילולי (`--excerpt`).

    python "AREO_RT/skills/contract-risk-assessor/scripts/fetch_source.py" --purpose entity --deal "<תיקיית העסקה>" --source-id ENT-SRC-01 \\
        --url "<הכתובת המדויקת>" --question E1 --counterparty "<השם>" [--registration-no "<המספר>"] \\
        [--excerpt "<הקטע המילולי>"] --profile "<פרופיל-לקוח.json>" \\
        [--approved-sources "<מקורות-מאושרים.json אחר; ברירת מחדל: העותק שבתוסף>"]

הפלט הוא JSON: `log` נכנס כמו שהוא ל-`lookups` של `entity-report.json`, `stored` ל-`raw_copies`
שלו, ו-`source_class` קובע אם המקור נרשם ב-`sources` כרשמי או כתקשורתי (`class: "media"`).
הטקסט עצמו אינו מודפס; הוא נקרא מהעותק השמור.

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
from urllib.parse import unquote, unquote_plus, urlsplit

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # גם ב-python -I, שאינו מוסיף את תיקיית הסקריפט
import areo_lib  # noqa: F401  מוסיף את areolegal/lib לנתיב הייבוא

from common import net  # noqa: E402
from common.case_law import case_law_url  # noqa: E402
from risk.entity_store import EntityStore  # noqa: E402
from risk.validate_register import (APPROVED_SOURCES_ENV, ENTITY_PURPOSE, approved_domains, domain_ok,  # noqa: E402
                                    media_problem, media_rule)

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


REGISTRY = "ישויות.json"


def registry_for(profile_path, registry_path=None):
    """ישויות.json: הנתיב שנמסר, ואחרת ליד הפרופיל (ישות ברירת המחדל, בשורש Areo-נתונים) או שתי תיקיות
    מעליו (ישויות/<שם-הישות>/פרופיל-לקוח.json). None כשאין."""
    if registry_path:
        return registry_path if os.path.isfile(registry_path) else None
    if not profile_path:
        return None
    d = os.path.dirname(os.path.abspath(profile_path))
    for cand in (os.path.join(d, REGISTRY), os.path.join(os.path.dirname(os.path.dirname(d)), REGISTRY)):
        if os.path.isfile(cand):
            return cand
    return None


def names_from(profile_path, registry_path=None):
    """שמות הארגון שאסור שיופיעו בשאילתה: organization_name ו-organization_name_en מהפרופיל, ושמות כל
    הישויות ב-ישויות.json כשהוא קיים."""
    names = []
    if profile_path:
        with io.open(profile_path, encoding="utf-8") as fh:
            prof = json.load(fh)
        names += [prof.get("organization_name"), prof.get("organization_name_en")]
    reg = registry_for(profile_path, registry_path)
    if reg:
        try:
            with io.open(reg, encoding="utf-8") as fh:
                entities = (json.load(fh) or {}).get("entities") or []
        except (OSError, ValueError):
            entities = []
        names += [e.get("name") for e in entities if isinstance(e, dict)]
    out_names = []
    for n in names:
        n = str(n or "").strip()
        if len(n) >= 2 and n.casefold() not in {x.casefold() for x in out_names}:
            out_names.append(n)
    return out_names


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
    ap.add_argument("--purpose", required=True,
                    help="entity: בדיקת רקע על הצד שכנגד, המטרה היחידה שבה המעריך יוצא לרשת. כל ערך אחר מסורב, "
                         "אלא עם --kind entity (ואז זו השאלה, בלי פרטי הלקוח)")
    ap.add_argument("--question", required=True, help="מזהה השאלה ב-research.question: עד עשר בקשות לשאלה")
    ap.add_argument("--excerpt", help="הקטע המילולי: בדף גדול נשמר רק חלון סביבו")
    ap.add_argument("--profile", help="פרופיל-לקוח.json: שמות החברה, שאסור שיופיעו בשאילתה")
    ap.add_argument("--entities", help="ישויות.json: שמות כל הישויות, שאסור שיופיעו בשאילתה (בלעדיו: ליד "
                                       "הפרופיל, או בשורש Areo-נתונים מעל תיקיית הישות)")
    ap.add_argument("--counterparty", help="השם הפומבי של הצד שכנגד: בבדיקת רקע הוא השאילתה עצמה")
    ap.add_argument("--kind", choices=("regulatory", "entity"), default="regulatory",
                    help="entity: כמו --purpose entity. regulatory: מסורב (אין אימות רגולטורי ברשת)")
    ap.add_argument("--registration-no", help="בחקר ישות: מספר הרישום של הצד שכנגד, כפי שהוא בהסכם")
    ap.add_argument("--approved-sources", help="מקורות-מאושרים.json (ברירת מחדל: %s, ואחריו העותק שבתוסף, "
                                               "lib/מקורות-מאושרים.json; אין רשימת נפילה בקוד)" % APPROVED_SOURCES_ENV)
    a = ap.parse_args(argv)

    if not os.path.isdir(a.deal):
        print("תיקיית העסקה אינה קיימת: %s" % a.deal)
        return 2
    if a.approved_sources and not os.path.isfile(a.approved_sources):
        print("קובץ המקורות המאושרים אינו קיים: %s" % a.approved_sources)
        return 2
    # המעריך יוצא לרשת רק לבדיקת רקע על הצד שכנגד, לבקשת הלקוח (מטרה D). אימות
    # רגולטורי אינו יוצא לרשת: דרישה שלא אומתה במסמכים או בפלייבוק מסומנת "טעון בדיקה משפטית"
    entity = a.kind == ENTITY_PURPOSE or a.purpose.strip().lower() == ENTITY_PURPOSE
    if not entity:
        return out({"status": None, "blocked": False, "stored": None, "source_class": None,
                    "reason": "refused: מעריך הסיכונים יוצא לרשת רק לבדיקת רקע על הצד שכנגד, לבקשת הלקוח "
                              "(--purpose entity). דרישה רגולטורית שלא אומתה במסמכים או בפלייבוק מסומנת "
                              "\"טעון בדיקה משפטית\", בלי יציאה לרשת"}, 3)
    # פסיקה: לפני ההכרעה בין מקור רשמי לכלי תקשורת, בכל כתובת (כלל 1.1)
    why = case_law_url(a.url)
    if why:
        return out({"status": None, "blocked": False, "stored": None, "source_class": None,
                    "reason": "refused: %s. הליכים משפטיים נגד הצד שכנגד הם משימה לעורך הדין, "
                              "\"טעון בדיקה משפטית\"" % why}, 3)
    rules, used = approved_domains(a.approved_sources, ENTITY_PURPOSE)
    if not used:
        return out({"status": None, "blocked": False, "stored": None, "source_class": None,
                    "reason": "refused: קובץ המקורות המאושרים (מקורות-מאושרים.json) לא נקרא. אין רשימת נפילה: "
                              "העותק נארז בתוסף (lib/מקורות-מאושרים.json); נתיב אחר עובר ב---approved-sources"}, 3)
    if any(net.rule_matches(a.url, r) for r in getattr(rules, "refuse", ())):
        return out({"status": None, "blocked": False, "stored": None, "source_class": None,
                    "reason": "refused: מדור פסיקה ברשימה (case_law_only). פסיקה רק ממחבר פסיקה סגור (כלל 1.1)"}, 3)
    source_class = "official" if domain_ok(a.url, rules) else None
    if not source_class:
        why = media_problem(a.url, a.approved_sources, ENTITY_PURPOSE)
        if why:
            return out({"status": None, "blocked": False, "stored": None, "source_class": None,
                        "reason": "refused: לא מקור רשמי ברשימה, ולא כלי תקשורת (%s): %s"
                                  % (urlsplit(a.url).hostname, why)}, 3)
        source_class = "media"
    blocked_names = names_from(a.profile, a.entities)
    # הנתיב של כתובת ממקור מורשה נושא את מספר המסמך (מזהה מסמך או מזהה תאגיד בנתיב), ולכן
    # בדיקת "מספר בן 5 ספרות ומעלה" חלה רק על מחרוזת השאילתה ועל המטרה. בנתיב נבדקים שמות הלקוח
    # ומספר חברה או זהות עם ספרת ביקורת
    path = unquote(urlsplit(a.url).path)
    for name in blocked_names:
        if name and name.casefold() in path.casefold():
            return out({"status": None, "blocked": False, "stored": None,
                        "reason": "refused: פרט של הלקוח או של העסקה בכתובת (%s)" % name}, 3)
    for num in re.findall(r"(?<!\d)\d{9}(?!\d)", path):
        if net._id_check_digit(num) and num != (a.registration_no or ""):
            return out({"status": None, "blocked": False, "stored": None,
                        "reason": "refused: מספר חברה או זהות בכתובת (%s)" % num}, 3)
    # "+" בשאילתה הוא רווח: בלי unquote_plus, "q=Client+Co" לא נתפס כשם הלקוח
    query = unquote_plus(urlsplit(a.url).query or "") + " " + a.purpose
    if source_class == "media":
        # מזהה ידיעה בכתובת של כלי תקשורת (did=1001234567) אינו פרט של הלקוח; מספר חברה או זהות עם ספרת ביקורת נשאר
        query = re.sub(r"\d{5,}", lambda m: m.group(0) if net._id_check_digit(m.group(0)) else " ", query)
    # בבדיקת רקע השאילתה בנויה רק משם, מספר רישום ומדינה של הצד שכנגד: הם אינם פרט של הלקוח (חריג לכלל 1.6)
    if not (a.counterparty or a.registration_no):
        print("בבדיקת רקע נדרשים --counterparty או --registration-no: השאילתה בנויה רק מהם")
        return 2
    for own in (a.counterparty, a.registration_no):
        if own:
            query = query.replace(own, " ")
    # שם הארגון נבדק בלי תלות ברישיות ("ANANFLOW" כמו "AnanFlow")
    detail = (next((nm for nm in blocked_names if nm.casefold() in query.casefold()), "")
              or net.client_detail_in_query(query, blocked_names))
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

    # שכבת הרשת בודקת את אותם כללים, בדומיין ובנתיב, לפני הבקשה ושוב על הכתובת הסופית אחרי הפניה, וגם את
    # הפסיקה. כלי תקשורת: רק הדומיין הרשום שלו, כך שהפניה לאתר אחר מסורבת
    if source_class == "media":
        hosts = (net.registrable_domain((urlsplit(a.url).hostname or "").lower()),)
    else:
        hosts = rules   # Rules: הכללים המורשים, וכללי הדחייה של case_law_only במאפיין refuse
    purpose = "entity: בדיקת רקע על הצד שכנגד" if a.purpose.strip().lower() == ENTITY_PURPOSE else a.purpose
    res = net.fetch(a.url, purpose, allowed_domains=hosts, store=EntityStore(a.deal),
                    source_id=a.source_id, excerpt=a.excerpt, run_dir=run_dir)
    show = {k: v for k, v in res.items() if k not in ("content", "text")}
    show["question"] = a.question
    show["source_class"] = source_class
    if source_class == "media":
        # אות לא מאומת: אינו ממצא, אינו בסיס יחיד לדגל אדום או לשינוי בדרגה, ונרשם ב-media_signals
        show["label"] = media_rule(a.approved_sources)["label"]
    ok = bool(res.get("stored")) and not res.get("blocked")
    return out(show, 0 if ok else 3)


if __name__ == "__main__":
    sys.exit(main())
