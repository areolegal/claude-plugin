#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""בונה את Areo Workspace | סיכונים (או את דוח חקר הישות) בתיקיית העסקה, בלי לקרוא את התבנית להקשר.

הבנייה והכתיבה הן קוד הייחוס של ענבל (`areolegal/lib/risk/build.py`,
`write_report`; הערות מעריך הסיכונים 3.6, שינויים 13.28, 17.9 ו-17.11):

* **שם קבוע, בתיקיית העסקה בלבד.** "Areo Workspace - סיכונים.html" ולצדו
  `risk-register.json`; לחקר ישות "Areo Workspace - חקר ישות.html" ולצדו
  `entity-report.json`. התיקייה היא זו של `--data`, אלא אם נמסר `--deal`.
  אין `--out` חופשי, ואין בסקריפט מחיקה, העברה או שינוי שם.
* **דוח של עסקה אחרת אינו נדרס.** כשבתיקייה כבר דוח, מזהה העסקה שבנתונים
  המוטמעים בו נבדק מול המרשם, והבנייה נכשלת כשהם שונים. אין דגל דריסה.
* **מזהה העסקה במרשם זהה לשם תיקיית העסקה** (בסקירה של עסקה).
* **בדיקה סטטית של התבנית** לפני כתיבה: כל הערה נסגרת, ואין טעינה מהרשת.
* **התבנית אינה בתיקיית העסקה.** עותק התבנית נשמר מהשירות לתיקייה זמנית;
  עותק שנשמר בתיקיית הלקוח מסורב, כדי שלא יישאר שם אחרי ההרצה.
* **הלוגו** מהפרופיל (`--profile`, `branding.logo_path`) מוטמע עד 150 קילובייט
  (`risk/logo.py`). כשאי אפשר, הדוח נבנה בלי לוגו, ונאמר למה.
* **מקפים ארוכים** בנתונים מוחלפים בקצרים, ודוח שנשאר בו מקף ארוך אינו נכתב.
* **בדיקת העמודים בכל הרצה** (`risk/render_check.py`): לפני הכתיבה הדוח נבנה
  בתיקייה זמנית ומודפס ל-PDF בגודל A4 בדפדפן בלי ממשק (Chrome או Edge). גוף
  ריק, שגיאת JavaScript, בקשה לרשת, סימון חיסיון שמסתיר כותרת, או יותר משמונה
  עמודים (שני עמודים בחקר ישות) עוצרים את הבנייה, והדוח אינו נכתב: מקצרים את
  הנתונים, ולא את התבנית. בלי דפדפן במחשב, הבדיקה אינה רצה, וזה נאמר.

    python3 scripts/build_risk_report.py --data "<תיקיית העסקה>/risk-register.json" \\
        --template "<תיקייה זמנית>/risk-report-template.html" --profile "<פרופיל-לקוח.json>"

    python3 scripts/build_risk_report.py --kind entity --data "<תיקיית העסקה>/entity-report.json" \\
        --template "<תיקייה זמנית>/entity-report-template.html"

`--artifact <קובץ>` מפיק בנוסף תוכן לפרסום כעמוד משותף, רק כשהמשתמש ביקש:
בלי doctype, html, head ו-body, ו-publishTarget=artifact.

הסקריפט אינו ממציא נתונים ואינו ממציא כתובות. במצב `meta.docAccess.mode = base`
בלבד, מסמך בלי כתובת מקבל כתובת שנגזרת מ-baseUrl.

קוד יציאה: **0** נבנה, **3** הבנייה סורבה (דוח של עסקה אחרת, מזהה שאינו שם
התיקייה, תבנית שנכשלה בבדיקה, נתיב ארוך מדי, או בדיקת העמודים נכשלה), **2** קלט
חסר, **1** נתיב שסורב.
"""
import argparse
import copy
import io
import json
import os
import re
import sys
import tempfile
import urllib.parse

import areo_lib  # noqa: F401  מוסיף את areolegal/lib לנתיב הייבוא

from common.cli import OutputRefused, guard_out  # noqa: E402
from common.paths import PathTooLong  # noqa: E402
from risk import build as B  # noqa: E402
from risk import logo as LG  # noqa: E402
from risk import render_check as RC  # noqa: E402
from risk.render_check import build_report  # noqa: E402

LONG_DASHES = ("—", "–")


def load(path, what):
    if not os.path.exists(path):
        print("%s אינו קיים: %s" % (what, path))
        raise SystemExit(2)
    try:
        with io.open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except ValueError as exc:
        print("%s אינו JSON תקין (%s)" % (what, exc))
        raise SystemExit(2)


def short_dashes(o):
    if isinstance(o, str):
        return o.replace("—", ", ").replace("–", "-")
    if isinstance(o, list):
        return [short_dashes(x) for x in o]
    if isinstance(o, dict):
        return {k: short_dashes(v) for k, v in o.items()}
    return o


def derive_urls(data):
    """גזירת כתובות במצב base בלבד, ורק למסמך שאין לו כתובת ולא סומן none."""
    meta = data.setdefault("meta", {})
    acc = meta.get("docAccess") or {"mode": "local"}
    meta["docAccess"] = acc
    if acc.get("mode") != "base" or not acc.get("baseUrl"):
        return 0
    base = acc["baseUrl"].rstrip("/")
    n = 0
    for d in data.get("documents", []) or []:
        f = d.get("file")
        if not f or d.get("webUrl") or d.get("urlSource") == "none":
            continue
        d["webUrl"] = base + "/" + urllib.parse.quote(f)
        d["urlSource"] = "derived"
        n += 1
    return n


def inside(path, folder):
    path, folder = os.path.realpath(path), os.path.realpath(folder)
    return os.path.commonpath([path, folder]) == folder


def to_artifact(html):
    """הפשטה לתוכן בלבד, כנדרש בעמוד משותף."""
    title = re.search(r"<title>.*?</title>", html, re.S)
    body = re.search(r"<body[^>]*>(.*)</body>", html, re.S)
    if not (title and body):
        raise ValueError("מבנה התבנית אינו כצפוי, לא ניתן להפיק עמוד משותף")
    head_bits = re.findall(r"<style>.*?</style>|<script>.*?</script>", html[:html.index("<body")], re.S)
    return (title.group(0) + "\n" + "\n".join(head_bits) +
            '\n<script>document.documentElement.setAttribute("dir","rtl");'
            'document.documentElement.setAttribute("lang","he");</script>\n' +
            body.group(1).strip() + "\n")


def add_logo(data, profile_path):
    prof = load(profile_path, "הפרופיל")
    path = (prof.get("branding") or {}).get("logo_path") or prof.get("logo_path")
    if not path:
        return "אין לוגו בפרופיל"
    if not os.path.isabs(path):
        path = os.path.join(os.path.dirname(os.path.abspath(profile_path)), path)
    if not os.path.exists(path):
        return "הלוגו שבפרופיל אינו נמצא (%s)" % path
    try:
        data.setdefault("meta", {}).setdefault("branding", {})["logo"] = LG.logo_data_uri(path)
    except LG.LogoError as exc:
        return "הדוח נבנה בלי לוגו: %s" % exc
    return "הלוגו הוטמע"


def page_check(a, data):
    """הדוח נבנה בתיקייה זמנית ונבדק בדפדפן אמיתי לפני שהוא נכתב לתיקיית העסקה.
    מחזיר שורת סיכום כשעבר, False כשנכשל, ו-None כשאין דפדפן (או --no-page-check)."""
    if a.no_page_check or not RC.find_browser():
        return None
    K = RC.KINDS[a.kind]
    with io.open(a.template, encoding="utf-8") as fh:
        tpl = fh.read()
    work = tempfile.mkdtemp(prefix="areo-render-")
    page = os.path.join(work, "Areo Workspace - %s.html" % K["name"])
    with io.open(page, "w", encoding="utf-8") as fh:
        fh.write(build_report(tpl, data, K["placeholder"]))
    res = RC.run_check(page, work, RC.band_text_from_register(data), markers=K["markers"],
                       body_limit=K["body_limit"])
    if res.get("verdict") == "PASS":
        return "עברה (%s עמודים בגוף, עד %d)" % (res.get("body_pages"), K["body_limit"])
    print("הדוח לא נכתב: בדיקת העמודים נכשלה (%s)." % ", ".join(res.get("fails") or ["?"]))
    if res.get("body_pages"):
        print("  עמודים בגוף: %s, המותר: %d. קצרו את הנתונים, ולא את התבנית." % (res["body_pages"], K["body_limit"]))
    for k in ("external_requests", "js_exceptions", "markers_missing", "heading_overlaps"):
        if res.get(k):
            print("  %s: %s" % (k, res[k][:5]))
    return False


def main(argv=None):
    sys.dont_write_bytecode = True
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--data", required=True, help="risk-register.json, או entity-report.json עם --kind entity")
    ap.add_argument("--template", required=True, help="עותק התבנית, בתיקייה זמנית")
    ap.add_argument("--kind", choices=("risk", "entity"), default="risk")
    ap.add_argument("--deal", help="תיקיית העסקה; בלעדיו: התיקייה של --data")
    ap.add_argument("--profile", help="פרופיל-לקוח.json: הלוגו")
    ap.add_argument("--artifact", help="תוכן לעמוד משותף, רק כשהמשתמש ביקש")
    ap.add_argument("--no-page-check", action="store_true", help="לבדיקות בלבד: בלי בדיקת העמודים בדפדפן")
    a = ap.parse_args(argv)

    data = load(a.data, "קובץ הנתונים")
    if not os.path.exists(a.template):
        print("התבנית אינה קיימת: %s" % a.template)
        return 2
    deal = a.deal or os.path.dirname(os.path.abspath(a.data))
    if not os.path.isdir(deal):
        print("תיקיית העסקה אינה קיימת: %s" % deal)
        return 2
    if inside(a.template, deal):
        print("עותק התבנית בתוך תיקיית העסקה (%s). שמור אותו בתיקייה זמנית, ולא בתיקיית הלקוח." % a.template)
        return 1

    notes = []
    if a.profile:
        notes.append(add_logo(data, a.profile))
    data = short_dashes(data)
    n = derive_urls(data) if a.kind == "risk" else 0
    data.setdefault("meta", {})["publishTarget"] = "local"
    checked = page_check(a, data)
    if checked is False:
        return 3
    try:
        html_path, json_path = B.write_report(deal, a.template, data, kind=a.kind)
    except (B.BuildError, PathTooLong, ValueError) as exc:
        print("הדוח לא נבנה: %s" % exc)
        return 3
    with io.open(html_path, encoding="utf-8") as fh:
        html = fh.read()
    if any(d in html for d in LONG_DASHES):
        print("מקף ארוך זלג לדוח (מהתבנית): %s. יש לתקן את התבנית." % html_path)
        return 3
    print("הדוח: %s" % html_path)
    print("  בדיקת העמודים: %s" % (checked if checked else "לא רצה, אין Chrome או Edge במחשב הזה"))
    print("הנתונים לצדו: %s" % json_path)
    for x in notes:
        print("  %s" % x)
    if a.kind == "risk":
        docs = data.get("documents", []) or []
        mode = (data["meta"].get("docAccess") or {}).get("mode", "local")
        print("  מצב גישה: %s. מסמכים עם קישור חי: %d מתוך %d. נגזרו כעת: %d"
              % (mode, sum(1 for x in docs if x.get("webUrl")), len(docs), n))

    if a.artifact:
        try:
            out = guard_out(a.artifact, inputs=[a.data, a.template, html_path, json_path])
        except OutputRefused as exc:
            print("העמוד המשותף לא נכתב. סירוב: %s" % exc)
            return 1
        d = copy.deepcopy(data)
        d["meta"]["publishTarget"] = "artifact"
        placeholder = B.NAMES[a.kind][2]
        with io.open(a.template, encoding="utf-8") as fh:
            tpl = fh.read()
        with io.open(out, "w", encoding="utf-8") as fh:
            fh.write(to_artifact(build_report(tpl, d, placeholder)))
        print("  תוכן לעמוד משותף: %s" % out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
