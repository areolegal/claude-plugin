#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""בונה את Areo Workspace | סיכונים (או את דוח חקר הישות) בתיקיית העסקה, בלי לקרוא את התבנית להקשר.

הבנייה והכתיבה הן של הספרייה המשותפת (`lib/risk/build.py`, `write_report`):

* **שם קבוע לפי שפת הדוח, בתיקיית העסקה בלבד.** בעברית "Areo Workspace - סיכונים.html", ובאנגלית
  "Areo Workspace - Risks.html", ולצדו `risk-register.json`; לחקר ישות "Areo Workspace - חקר ישות.html"
  או "Areo Workspace - Entity check.html", ולצדו `entity-report.json`. התיקייה היא זו של `--data`, אלא אם
  נמסר `--deal`.
  אין `--out` חופשי, ואין בסקריפט מחיקה או שינוי שם.
* **דוח של עסקה אחרת אינו נדרס.** כשבתיקייה כבר דוח, מזהה העסקה שבנתונים
  המוטמעים בו נבדק מול המרשם, והבנייה נכשלת כשהם שונים. אין דגל דריסה.
* **גרסה קודמת של אותה עסקה עוברת ל-`history`**, גם כשהיא בשפה האחרת: לפני הכתיבה
  הדוח והמרשם הקודמים עוברים ל-`<תיקיית העסקה>/history`, עם התאריך והשעה שבהם
  נכתבו (`risk/build.archive_previous`). מרשם שהוא קובץ הקלט (`--data`) הוא הגרסה
  החדשה; הגרסה הקודמת שלו נשמרת מהנתונים שבדוח הקודם. הפלט אומר מה הועבר.
* **מזהה העסקה במרשם זהה לשם תיקיית העסקה** (בסקירה של עסקה).
* **בדיקה סטטית של התבנית** לפני כתיבה: כל הערה נסגרת, ואין טעינה מהרשת.
* **התבנית נארזת בתוסף.** בלי `--template` נקרא העותק שבתוסף, לפי `--kind`:
  `skills/contract-risk-assessor/assets/risk-report-template.html` או `assets/entity-report-template.html`.
  אין הורדה מהשרת בזמן ריצה. `--template` מפורש עדיין מתקבל, ועותק תבנית בתוך תיקיית הלקוח מסורב,
  כדי שלא יישאר שם אחרי ההרצה.
* **צבעי המותג** מהפרופיל (`--profile`, `branding.theme`), כשהלקוח אישר מיתוג, נכנסים ל-`meta.branding.theme`.
* **הלוגו** מהפרופיל (`--profile`, `branding.logo_path`) מוטמע עד 150 קילובייט
  (`risk/logo.py`). כשאי אפשר, הדוח נבנה בלי לוגו, ונאמר למה.
* **שם עורך הדין** בסימון החיסיון הוא שם בלבד: תואר בתחילתו ("עו"ד") יוצא, כי התבנית מוסיפה אותו,
  וכך גם `branding.lawyer_role` מהפרופיל כשהוא כבר בסוף השם (`risk/render_check.counsel_name`).
* **מקפים ארוכים** בנתונים מוחלפים בקצרים, ודוח שנשאר בו מקף ארוך אינו נכתב.
* **בדיקת העמודים בכל הרצה** (`risk/render_check.py`): לפני הכתיבה הדוח נבנה
  בתיקייה זמנית ומודפס ל-PDF בגודל A4 בדפדפן בלי ממשק (Chrome או Edge). גוף
  ריק, שגיאת JavaScript, בקשה לרשת, סימון חיסיון שמסתיר כותרת, או יותר משמונה
  עמודים (שני עמודים בחקר ישות) עוצרים את הבנייה, והדוח אינו נכתב: מקצרים את
  הנתונים, ולא את התבנית. בלי דפדפן במחשב, הבדיקה אינה רצה, וזה נאמר.

    python3 -B "AREO_RT/skills/contract-risk-assessor/scripts/build_risk_report.py" --data "<תיקיית העסקה>/risk-register.json" \\
        --profile "<פרופיל-לקוח.json>"

    python3 -B "AREO_RT/skills/contract-risk-assessor/scripts/build_risk_report.py" --kind entity --data "<תיקיית העסקה>/entity-report.json"

**שפת הדוח** (דרישת מוצר: deliverable_language קובע את שפת התוצרים): `--lang he|en`, ובלעדיו
`deliverable_language` מהפרופיל (`both`: `display_language` שבפרופיל), ובלעדיו `meta.display_language` שבמרשם. השפה נרשמת ב-`meta.display_language`,
והתבנית מציגה עברית RTL או אנגלית LTR (title, lang, dir, כל התוויות, סימון החיסיון ו"Generated"). נוסח מצוטט נשאר
בשפת המקור. שם הקובץ נגזר משפת הדוח (B.names_for), ושני השמות נבדקים כשמחפשים דוח קיים.

`--artifact <קובץ>` מפיק בנוסף תוכן לפרסום כ-Artifact פרטי בחשבון הלקוח בלבד, רק כשהמשתמש ביקש
(כלל 2.1 ב-areo-hard-rules.md: לעולם לא קישור ציבורי, לא בגלריה, לא מחוץ לארגון;
הפרטיות מאושרת מתוצאת הפרסום ולא נקראים בחזרה; העותק המקומי נשאר תמיד בתיקיית העסקה):
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

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # גם ב-python -I, שאינו מוסיף את תיקיית הסקריפט
import areo_lib  # noqa: F401  מוסיף את areolegal/lib לנתיב הייבוא

from common.cli import OutputRefused, guard_out  # noqa: E402
from common.branding import apply_theme  # noqa: E402
from common.paths import PathTooLong, long_path  # noqa: E402
from risk import build as B  # noqa: E402
from risk import logo as LG  # noqa: E402
from risk import render_check as RC  # noqa: E402
from risk.render_check import build_report  # noqa: E402
from risk import validate_register as VR  # noqa: E402
import risk_states as RS  # noqa: E402  שלושה מצבים לכל סיכון (נוכחי, מוצע, מוסכם)

LONG_DASHES = ("—", "–")
# התבניות שנארזות בתוסף, לפי סוג הדוח: ברירת המחדל של --template (אין הורדה מהשרת בזמן ריצה)
ASSETS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets")
DEFAULT_TEMPLATES = {"risk": os.path.join(ASSETS, "risk-report-template.html"),
                     "entity": os.path.join(ASSETS, "entity-report-template.html")}


def load(path, what):
    if not os.path.exists(long_path(path)):
        print("%s אינו קיים: %s" % (what, path))
        raise SystemExit(2)
    try:
        with io.open(long_path(path), encoding="utf-8") as fh:
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


def to_artifact(html, lang="he"):
    """הפשטה לתוכן בלבד, כנדרש ב-Artifact. הכיוון והשפה לפי שפת התוצר."""
    title = re.search(r"<title>.*?</title>", html, re.S)
    body = re.search(r"<body[^>]*>(.*)</body>", html, re.S)
    if not (title and body):
        raise ValueError("מבנה התבנית אינו כצפוי, לא ניתן להפיק תוכן ל-Artifact")
    head_bits = re.findall(r"<style>.*?</style>|<script>.*?</script>", html[:html.index("<body")], re.S)
    d, l = ("ltr", "en") if lang == "en" else ("rtl", "he")
    return (title.group(0) + "\n" + "\n".join(head_bits) +
            '\n<script>document.documentElement.setAttribute("dir","%s");'
            'document.documentElement.setAttribute("lang","%s");</script>\n' % (d, l) +
            body.group(1).strip() + "\n")


def apply_lang(data, lang_arg, profile_path):
    """שפת התוצר: --lang, אחריו deliverable_language בפרופיל, אחריו display_language שבמרשם.
    נרשמת ב-meta.display_language, השדה שהתבנית והוולידטור מכירים, ומוחזרת כ-he או en."""
    prof = load(profile_path, "הפרופיל") if profile_path else {}
    meta = data.setdefault("meta", {})
    dl = prof.get("deliverable_language")
    if str(dl or "").strip().lower() == "both":
        # "both": התוצר הראשי בשפת הממשק (language-policy.md)
        dl = prof.get("display_language")
    v = lang_arg or dl or meta.get("display_language") or "he"
    lang = "en" if str(v).strip().lower()[:2] == "en" or str(v).strip().lower() in ("english", "אנגלית") else "he"
    meta["display_language"] = lang
    return lang


def derive_fields(data, profile_path, lang):
    """שדות שנגזרים בקוד, ולא נכתבים ביד: severity_level של כל סיכון מהניקוד (אחרי בקרות, ובהיעדרן הגולמי, לפי
    הספים 16, 9 ו-4, כמו בבודק), ושם החברה בשפת הדוח (organization_name_en בדוח באנגלית, כשהוא בפרופיל)."""
    for r in data.get("risks") or []:
        if not r.get("severity_level"):
            res, inh = r.get("residual") or {}, r.get("inherent") or {}
            score = res.get("score") if res.get("score") is not None else inh.get("score")
            if score is not None:
                r["severity_level"] = VR.lvl(score)
    RS.derive_levels(data)  # סיכון עם states: הדרגה מהמצב הנוכחי או המוסכם בלבד, ובקרה מוצעת אינה מורידה
    if lang == "en" and profile_path:
        en = (load(profile_path, "הפרופיל").get("organization_name_en") or "").strip()
        if en:
            data.setdefault("meta", {})["company"] = en


def clean_counsel(data, profile_path):
    """שם עורך הדין בסימון החיסיון: meta.prepared_for_counsel הוא שם בלבד. התבנית העברית
    מוסיפה "עו״ד", ולכן תואר בתחילת השם יוצא, וכך גם התפקיד (branding.lawyer_role בפרופיל) כשהוא כבר בסוף השם."""
    meta = data.setdefault("meta", {})
    if not meta.get("prepared_for_counsel"):
        return
    role = ((load(profile_path, "הפרופיל").get("branding") or {}).get("lawyer_role")) if profile_path else None
    meta["prepared_for_counsel"] = RC.counsel_name(meta["prepared_for_counsel"], role) or None


def add_logo(data, profile_path):
    prof = load(profile_path, "הפרופיל")
    path = (prof.get("branding") or {}).get("logo_path") or prof.get("logo_path")
    if not path:
        return "אין לוגו בפרופיל"
    if not os.path.isabs(path):
        # הנתיב בפרופיל יחסי לתיקייה שמחזיקה את Areo-נתונים ("Areo-נתונים/<קובץ>"), או לתיקיית הפרופיל עצמה
        here = os.path.dirname(os.path.abspath(profile_path))
        cands = [os.path.join(os.path.dirname(here), path), os.path.join(here, path),
                 os.path.join(here, os.path.basename(path))]
        path = next((c for c in cands if os.path.exists(c)), cands[0])
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
    with io.open(long_path(a.template), encoding="utf-8") as fh:
        tpl = fh.read()
    work = tempfile.mkdtemp(prefix="areo-render-")
    page = os.path.join(work, B.names_for(a.kind, RC.lang_of(data))[0])
    with io.open(page, "w", encoding="utf-8") as fh:
        fh.write(build_report(tpl, data, K["placeholder"]))
    res = None
    for attempt in (1, 2):
        # תקלה של הדפדפן עצמו (פסק זמן, חיבור שנפל) אינה כשל של הדוח: ניסיון חוזר אחד, ואם גם הוא
        # נכשל, הבדיקה לא הושלמה, וזה נאמר, כמו כשאין דפדפן במחשב
        try:
            res = RC.run_check(page, work, RC.band_text_from_register(data),
                               markers=RC.markers_for(a.kind, RC.lang_of(data)), body_limit=K["body_limit"])
            break
        except Exception as exc:  # noqa: BLE001
            err = "%s: %s" % (type(exc).__name__, exc)
    if res is None:
        print("  בדיקת העמודים לא הושלמה: תקלה בדפדפן (%s)" % err[:120])
        return None
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
    ap.add_argument("--template", help="התבנית; בלעדיו: העותק שבתוסף לפי --kind (assets/risk-report-template.html "
                                       "או assets/entity-report-template.html)")
    ap.add_argument("--kind", choices=("risk", "entity"), default="risk")
    ap.add_argument("--deal", help="תיקיית העסקה; בלעדיו: התיקייה של --data")
    ap.add_argument("--profile", help="פרופיל-לקוח.json: הלוגו ושפת התוצר (deliverable_language)")
    ap.add_argument("--lang", choices=("he", "en"), help="שפת הדוח; בלעדיו: deliverable_language בפרופיל, "
                                                         "ואחריו meta.display_language")
    ap.add_argument("--artifact", help="תוכן ל-Artifact פרטי בחשבון הלקוח, רק כשהמשתמש ביקש")
    ap.add_argument("--no-page-check", action="store_true", help="לבדיקות בלבד: בלי בדיקת העמודים בדפדפן")
    a = ap.parse_args(argv)

    data = load(a.data, "קובץ הנתונים")
    a.template = a.template or DEFAULT_TEMPLATES[a.kind]
    if not os.path.exists(long_path(a.template)):
        print("התבנית אינה קיימת: %s" % a.template)
        return 2
    deal = a.deal or os.path.dirname(os.path.abspath(a.data))
    if not os.path.isdir(deal):
        print("תיקיית העסקה אינה קיימת: %s" % deal)
        return 2
    if inside(a.template, deal):
        print("עותק התבנית בתוך תיקיית העסקה (%s). בלי --template נקרא העותק שבתוסף (%s), "
              "ואין לשמור תבנית בתיקיית הלקוח." % (a.template, DEFAULT_TEMPLATES[a.kind]))
        return 1

    notes = []
    lang = apply_lang(data, a.lang, a.profile)
    if a.kind == "risk":
        derive_fields(data, a.profile, lang)
    clean_counsel(data, a.profile)
    if a.profile:
        notes.append(add_logo(data, a.profile))
        brand = apply_theme(data, load(a.profile, "הפרופיל"))
        if brand:
            notes.append(brand)
    data = short_dashes(data)
    n = derive_urls(data) if a.kind == "risk" else 0
    data.setdefault("meta", {})["publishTarget"] = "local"
    checked = page_check(a, data)
    if checked is False:
        return 3
    archived = []
    try:
        html_path, json_path = B.write_report(deal, a.template, data, kind=a.kind, data_path=a.data,
                                              archived=archived, lang=lang)
    except (B.BuildError, PathTooLong, ValueError) as exc:
        print("הדוח לא נבנה: %s" % exc)
        return 3
    with io.open(html_path, encoding="utf-8") as fh:
        html = fh.read()
    if any(d in html for d in LONG_DASHES):
        print("מקף ארוך זלג לדוח (מהתבנית): %s. יש לתקן את התבנית." % html_path)
        return 3
    print("הדוח: %s" % html_path)
    print("  בדיקת העמודים: %s" % (checked if checked else "לא הושלמה (אין Chrome או Edge, או תקלה בדפדפן)"))
    print("הנתונים לצדו: %s" % json_path)
    if archived:
        # הודעת המסירה אומרת שהגרסה הקודמת נשמרה, ולא שהוחלפה (r5-report.md, שלב 6)
        print("  הגרסה הקודמת של הדוח והמרשם הועברה לתיקייה history של העסקה: %s"
              % ", ".join(os.path.basename(p) for p in archived))
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
            print("תוכן ה-Artifact לא נכתב. סירוב: %s" % exc)
            return 1
        d = copy.deepcopy(data)
        d["meta"]["publishTarget"] = "artifact"
        placeholder = B.NAMES[a.kind][2]
        with io.open(long_path(a.template), encoding="utf-8") as fh:
            tpl = fh.read()
        with io.open(out, "w", encoding="utf-8") as fh:
            fh.write(to_artifact(build_report(tpl, d, placeholder), lang))
        print("  תוכן ל-Artifact פרטי: %s" % out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
