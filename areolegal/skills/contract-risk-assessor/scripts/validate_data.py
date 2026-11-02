#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""בדיקת risk-register.json (ודוח חקר הישות) לפני בניית הדוח.

הבודק הוא `lib/risk/validate_register.py` של הספרייה המשותפת. הוא בודק את המרשם לפי הסכמה 3.6: שמונה
עדשות ב-`primary_lens`, `side` בהסכם הדדי, `text_status` מול קובץ המצב, ויתורים
מכוונים שלא נפתחו מחדש כסיכונים שהתקבלו, מקורות מהרשימה המורשית עם
עותק גולמי, ביטויים חסומים, אורך הדוח, ובפרופיל מה שהוא כבר מכריע. בלי מחבר פסיקה סגור
(`--case-law-connector`), אזכור פסק דין בטקסט המוצג של המרשם או של דוח בדיקת הרקע הוא שגיאה. עם `--deal`
נבדקת גם תיקיית העותקים `sources/`: בלי רשימות מלאות, בלי טוקנים ובתוך התקרות.

    python "AREO_RT/skills/contract-risk-assessor/scripts/validate_data.py" --data "<תיקיית העסקה>/risk-register.json" \\
        --deal "<תיקיית העסקה>" [--state "<תיקיית העסקה>/negotiation_state.json"] \\
        --profile "<פרופיל-לקוח.json>" --corpus "<חילוץ.json>" [--entity entity-report.json] \\
        [--approved-sources "<מקורות-מאושרים.json אחר>"] [--case-law-connector "<שם המחבר>"]

`--purpose entity` (או `--entity`, שמפעיל אותו): דוח בדיקת הרקע נבדק מול מקורות בדיקת הרקע וכלל
התקשורת, המטרה היחידה שבה המעריך יוצא לרשת. במרשם עצמו אין יציאה לרשת:
`research.mode` הוא `not_permitted`, ויומן או מקור ברשת בו הם שגיאה.

`--state` רק כשיש קובץ מצב לעסקה. מרשם שאינו של עסקה (`scope` שאינו `deal`) עם `--state` לקובץ שאינו
קיים: אזהרה, והבדיקה רצה בלי קובץ מצב. במרשם של עסקה קובץ מצב חסר הוא קלט חסר (קוד יציאה 2).

כל הקלט קריאה בלבד. `--out` (אופציונלי) כותב את רשימת השגיאות, ולעולם לא על
קובץ קלט.

קוד יציאה: **0** אין שגיאות (אזהרות מותרות), **3** יש שגיאות, ולכן הדוח אינו
נבנה, **2** קלט חסר או שאינו JSON.
"""
import io
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # גם ב-python -I, שאינו מוסיף את תיקיית הסקריפט
import areo_lib  # noqa: F401  מוסיף את areolegal/lib לנתיב הייבוא

from common.cli import OutputRefused, guard_out, parser  # noqa: E402
from common.paths import long_path  # noqa: E402
from risk import entity_store as ES  # noqa: E402
from risk import extract_corpus as EC  # noqa: E402
from risk import validate_register as VR  # noqa: E402
import risk_states as RS  # noqa: E402  שלושה מצבים לכל סיכון


def load(path, what):
    if not path:
        return None
    if not os.path.exists(long_path(path)):
        print("%s אינו קיים: %s" % (what, path))
        raise SystemExit(2)
    try:
        with io.open(long_path(path), encoding="utf-8") as fh:
            return json.load(fh)
    except ValueError as exc:
        print("%s אינו JSON תקין (%s)" % (what, exc))
        raise SystemExit(2)


def corpus_for_check(corpus):
    """הבודק קורא חילוץ בצורת רשימה, ולכל מסמך file ו-parts. הפלט של
    extract_corpus.py שבחבילה הוא מניפסט (root, documents[].path), ולכן כל מסמך בו
    נקרא שוב, מקומית, בפונקציית החילוץ של הספרייה, כדי שהציטוטים ייבדקו מול הנוסח
    המלא בשני ההיטלים. מסמך שאינו Word או PDF אינו נבדק כאן, ונאמר."""
    if corpus is None or isinstance(corpus, list):
        return corpus
    root = corpus.get("root") or ""
    out = []
    for d in corpus.get("documents") or ():
        path = os.path.join(root, d.get("path") or "")
        if d.get("format") in ("docx", "pdf") and os.path.exists(long_path(path)):
            out.append(EC.extract(path))
        else:
            print("אזהרה: %s לא נקרא לבדיקת הציטוטים (%s)" % (d.get("path"), d.get("format")))
    return out


def main(argv=None):
    sys.dont_write_bytecode = True
    sys.stdout.reconfigure(encoding="utf-8")
    ap = parser(__doc__.split("\n")[0], out_required=False, out_help="רשימת השגיאות (JSON); לא קובץ קלט")
    ap.add_argument("--data", required=True, help="risk-register.json")
    ap.add_argument("--corpus", help="הפלט של extract_corpus.py: לבדיקת הציטוטים מההסכם")
    ap.add_argument("--deal", help="תיקיית העסקה: העותקים הגולמיים של המקורות")
    ap.add_argument("--state", help="negotiation_state.json של העסקה")
    ap.add_argument("--profile", help="פרופיל-לקוח.json")
    ap.add_argument("--playbook-status", help="מעמד הפלייבוק, משער המדיניות")
    ap.add_argument("--entity", help="entity-report.json, כשנעשתה בדיקת רקע לבקשת הלקוח")
    ap.add_argument("--purpose", choices=(VR.ENTITY_PURPOSE,),
                    help="entity: בדיקת רקע על הצד שכנגד, המטרה היחידה שמתירה את מקורות בדיקת הרקע ואת "
                         "התקשורת (דוח בדיקת הרקע נבדק כך גם בלעדיו)")
    ap.add_argument("--amendments", help="JSON: רשימת התיקונים הידועים בחוקים שהמרשם נשען עליהם")
    ap.add_argument("--approved-sources", help="מקורות-מאושרים.json (ברירת מחדל: משתנה הסביבה %s, ואחריו העותק שבתוסף, "
                                               "lib/מקורות-מאושרים.json)"
                    % VR.APPROVED_SOURCES_ENV)
    ap.add_argument("--case-law-connector", help="שם מחבר הפסיקה הסגור שהלקוח חיבר בהפעלה הזו (כלל 1.1). בלעדיו, "
                                                 "אזכור פסק דין בטקסט המוצג הוא שגיאה")
    a = ap.parse_args(argv)

    reg = load(a.data, "המרשם")
    state_path = a.state
    if state_path and not os.path.exists(long_path(state_path)) and (reg.get("meta") or {}).get("scope") != "deal":
        # בלי עסקה אין קובץ מצב: הבדיקה רצה בלעדיו, ולא נעצרת על קלט חסר
        print("אזהרה: אין קובץ מצב (%s); המרשם אינו של עסקה, והבדיקה רצה בלי קובץ מצב" % state_path)
        state_path = None
    try:
        errors, warnings = VR.validate(reg, corpus_for_check(load(a.corpus, "החילוץ")), a.deal, load(state_path, "קובץ המצב"),
                                       load(a.profile, "הפרופיל"), load(a.playbook_status, "מעמד הפלייבוק"),
                                       load(a.amendments, "רשימת התיקונים"), a.approved_sources,
                                       a.case_law_connector)
    except (AttributeError, TypeError, KeyError) as exc:
        # שדה בצורה אחרת מהסכמה (למשל meta.counterparty כמחרוזת במרשם ישן) מפיל את הבודק
        # באמצע. זו שגיאה במרשם, ולא תקלה: הדוח אינו נבנה
        print("שגיאה: המרשם אינו במבנה של הסכמה 3.6, והבדיקה נעצרה (%s: %s)" % (type(exc).__name__, exc))
        print("הדוח אינו נבנה. תקן את המרשם והרץ שוב.")
        return 3
    st_err, st_warn = RS.check(reg)  # נוכחי / מוצע / מוסכם; מרשם בלי states נקרא כנוכחי בלבד
    errors += st_err
    warnings += st_warn
    if a.entity:
        errors += ["entity " + e for e in VR.validate_entity_report(load(a.entity, "דוח חקר הישות"),
                                                                       a.approved_sources,
                                                                       a.purpose or VR.ENTITY_PURPOSE,
                                                                       a.case_law_connector)]
    if a.deal and os.path.isdir(os.path.join(a.deal, ES.SOURCES_DIR)):
        # תיקיית העותקים: בלי רשימות מלאות, בלי טוקנים בכתובות, ובתוך התקרות
        errors += ["sources " + str(p) for p in ES.audit_deal_dir(a.deal)]
    for w in warnings:
        print("אזהרה: %s" % w)
    for e in errors:
        print("שגיאה: %s" % e)
    print("שגיאות: %d, אזהרות: %d" % (len(errors), len(warnings)))
    if errors:
        print("הדוח אינו נבנה. תקן את המרשם והרץ שוב.")
    if a.out:
        inputs = [x for x in (a.data, a.corpus, state_path, a.profile, a.playbook_status, a.entity, a.amendments,
                              a.approved_sources) if x]
        try:
            out = guard_out(a.out, inputs=inputs)
        except OutputRefused as exc:
            print("סירוב: %s" % exc)
            return 1
        with io.open(out, "w", encoding="utf-8") as fh:
            json.dump({"errors": errors, "warnings": warnings}, fh, ensure_ascii=False, indent=1)
    return 3 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
