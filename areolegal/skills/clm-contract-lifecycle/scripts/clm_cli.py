# -*- coding: utf-8 -*-
"""נקודת הכניסה של הסוכן: scan, assemble, validate, build, acceptance.

שימוש לדוגמה:
  python scripts/clm_cli.py scan --folders "הסכמים" --data-dir "Areo-נתונים"
  python scripts/clm_cli.py assemble --data-dir "Areo-נתונים" --company "שם החברה" --today 2026-10-22 --lang he
  python scripts/clm_cli.py validate --data "Areo-נתונים/clm-data.json"
  python scripts/clm_cli.py build --data "Areo-נתונים/clm-data.json" --out "Areo Workspace - חוזים.html"
"""
import argparse
import datetime as dt
import json
import os
import sys

# python -I מתעלם מ-PYTHONDONTWRITEBYTECODE: בלי השורה הזו נכתב __pycache__ בתיקיית הסוכן
sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from clm import assemble, build, doc_kind, fingerprint  # noqa: E402
from clm.validate import check_data  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _load(path, default=None):
    if not os.path.exists(path):
        return default
    with open(path, encoding="utf-8-sig") as f:
        return json.load(f)


def _dump(obj, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)


def cmd_scan(a):
    ingest = os.path.join(a.data_dir, "ingest")
    previous = _load(os.path.join(ingest, "state.json"), {})
    report = {}
    files = fingerprint.scan(a.folders, previous=previous, excluded=tuple(a.exclude or ()), work_dir=ingest, report=report)
    if report["missing"]:
        # נתיב חסר עוצר בלי לכתוב scan.json: אחרת כל ההסכמים שבו היו מסומנים "הוסר"
        for m in report["missing"]:
            print("לא נמצא: %s. בדקו את הנתיב (תיקייה או קובץ), וחברו אותו שוב" % m)
        print("הסריקה לא נשמרה, כי נתיב אחד או יותר לא נמצא.")
        return 2
    for f in files:
        if f["status"] == "unsupported":
            f["suggested_kind"], f["reasons"] = None, ["סוג קובץ שאינו נקרא; נפתח פריט באימות הנתונים"]
            continue
        sig = doc_kind.docx_signals(f["abs"]) if f["abs"] and f["abs"].lower().endswith(".docx") else {}
        f["suggested_kind"], f["reasons"] = doc_kind.suggest(f["path"], sig)
        if f.get("attachments"):
            f["suggested_kind"], f["reasons"] = "non_agreement", ["מייל: ההסכם בקבצים המצורפים, שנסרקו כרשומות נפרדות"]
        if f.get("scanned"):
            f["reasons"].append("PDF סרוק בלי שכבת טקסט; " + ("זיהוי טקסט ב-text_path" if f.get("ocr") == "done"
                                                              else "אין זיהוי טקסט: לקרוא מתמונות העמודים"))
    _dump({"generated_at": dt.datetime.now().isoformat(timespec="minutes"), "folders": a.folders, "files": files,
           "skipped": {"system": report["system"], "data_dirs": report["data_dirs"]}},
          os.path.join(ingest, "scan.json"))
    labels = {"new": "חדשים", "changed": "השתנו", "same": "ללא שינוי", "duplicate": "כפולים", "removed": "הוסרו",
              "unreadable": "נעולים", "unsupported": "בסוג שאינו נקרא"}
    counts = {}
    for f in files:
        counts[f["status"]] = counts.get(f["status"], 0) + 1
    if not files:
        print("לא נמצאו קבצים בנתיבים: %s" % ", ".join(a.folders))
    else:
        print("נסרקו %d קבצים: %s" % (len(files), ", ".join("%s %d" % (labels.get(k, k), n) for k, n in sorted(counts.items()))))
    print("לחילוץ: %d" % sum(1 for f in files if f["status"] in ("new", "changed")))
    unreadable = [f["path"] for f in files if f["status"] == "unreadable"]
    if unreadable:
        print("לא נקראו (נעולים או לא זמינים), החילוץ הקודם נשמר: %s" % ", ".join(unreadable))
    unsupported = [f["path"] for f in files if f["status"] == "unsupported"]
    if unsupported:
        print("לא נקראו, סוג קובץ שאינו נתמך (פריט באימות הנתונים): %s" % ", ".join(unsupported))
    for f in files:
        if f.get("attachments") is not None:
            print("מייל: %s, %d קבצים מצורפים נסרקו כרשומות נפרדות" % (f["path"], len(f["attachments"])))
        if f.get("reason") == "eml_unreadable":
            print("מייל שלא ניתן לפרק: %s. לקרוא אותו ישירות" % f["path"])
    deps = fingerprint.dependencies()
    no_check = [f["path"] for f in files if f.get("pdf_check") == "unavailable"]
    if no_check:
        print("לא נבדק אם המסמכים האלה סרוקים, כי חסרה במחשב ספריית PDF (pip install pymupdf): %s" % ", ".join(no_check))
    scanned = [f for f in files if f.get("scanned")]
    if scanned and not (deps["tesseract"] and deps["pymupdf"]):
        print("זיהוי טקסט אינו זמין: %s. המסמכים הסרוקים נקראים מתמונות העמודים." % " ו".join(
            x for x, ok in (("חסר tesseract (התקנה: https://github.com/tesseract-ocr/tesseract, עם heb ו-eng)", deps["tesseract"]),
                            ("חסרה הספרייה pymupdf (pip install pymupdf)", deps["pymupdf"])) if not ok))
    if scanned:
        print("PDF סרוק בלי שכבת טקסט: %s" % ", ".join(
            "%s (%s)" % (f["path"], "זוהה טקסט" if f.get("ocr") == "done" else
                         "זיהוי הטקסט נכשל" if f.get("ocr") == "failed" else "אין במחשב כלי לזיהוי טקסט")
            for f in scanned))
    if report["system"]:
        print("קובצי מערכת ונעילה שלא נסרקו: %d (%s)" % (len(report["system"]), ", ".join(report["system"][:5])))
    for d in report["data_dirs"]:
        print("תיקיית הנתונים של Areo לא נסרקה: %s" % d)
    return 0


def _profiles(data_dir):
    """פרופיל-לקוח.json בתיקיית הנתונים, ואחריו בתיקיית Areo-נתונים לצידה: רק מה שנקרא כמילון."""
    here = os.path.abspath(data_dir)
    for base in (here, os.path.join(os.path.dirname(here), "Areo-נתונים")):
        try:
            profile = _load(os.path.join(base, "פרופיל-לקוח.json"))
        except (ValueError, UnicodeDecodeError, OSError):
            continue
        if isinstance(profile, dict):
            yield profile


def _company_aliases(data_dir):
    """שם החברה באנגלית מ-פרופיל-לקוח.json (בתיקיית הנתונים, או בתיקיית Areo-נתונים לצידה), אם קיים וריק לא."""
    for profile in _profiles(data_dir):
        name = profile.get("organization_name_en")
        if isinstance(name, str) and name.strip():
            return (name.strip(),)
    return ()


# מדינת ההתאגדות (ISO) לשם הדין המקומי, בשפת הנתונים. מדינה שאינה כאן נלקחת מ-incorporation_country_name כלשונו
COUNTRY_NAMES = {"IL": ("ישראל", "Israel"), "GB": ("בריטניה", "United Kingdom"), "US": ("ארצות הברית", "United States"),
                 "DE": ("גרמניה", "Germany"), "FR": ("צרפת", "France"), "NL": ("הולנד", "Netherlands"),
                 "IE": ("אירלנד", "Ireland"), "CY": ("קפריסין", "Cyprus")}


def _profile_home_law(data_dir, lang):
    """הדין המקומי מהפרופיל: מדינת ההתאגדות. None כשאין פרופיל או מדינה."""
    for profile in _profiles(data_dir):
        code = str(profile.get("incorporation_country") or "").strip().upper()
        if code in COUNTRY_NAMES:
            return COUNTRY_NAMES[code][1 if lang == "en" else 0]
        name = profile.get("incorporation_country_name")
        if isinstance(name, str) and name.strip():
            return name.strip()
    return None


def _profile_lang(data_dir):
    """שפת הנתונים מהפרופיל: deliverable_language, ואחריו display_language. None כשאין."""
    for profile in _profiles(data_dir):
        for key in ("deliverable_language", "display_language"):
            v = profile.get(key)
            if isinstance(v, str) and v.strip():
                return v.strip()
    return None


def cmd_assemble(a):
    ingest = os.path.join(a.data_dir, "ingest")
    scan = _load(os.path.join(ingest, "scan.json"))
    if not scan:
        print("לא נמצאה סריקה. יש להריץ scan תחילה.")
        return 1
    good, bad = assemble.load_extracts(os.path.join(ingest, "extract"))
    playbooks, pb_error = assemble.load_playbooks(a.playbooks or os.path.join(a.data_dir, "playbooks", "index.json"))
    if pb_error:
        print("אזהרה: " + pb_error)
    out_path = os.path.join(a.data_dir, "clm-data.json")
    aliases = _company_aliases(a.data_dir)
    previous = _load(out_path)
    lang = assemble.resolve_lang(a.lang or _profile_lang(a.data_dir), previous)
    data = assemble.assemble(scan, good, a.company, dt.date.fromisoformat(a.today),
                             previous=previous, default_owner=a.default_owner, bad_extracts=bad,
                             playbooks=playbooks, home_law=a.home_law or _profile_home_law(a.data_dir, lang),
                             home_law_source="flag" if a.home_law else "profile",
                             company_aliases=aliases, lang=lang,
                             # the real time of this run when it is today's run; a date in the past or future keeps
                             # the fixed morning stamp (tests, a rebuild "as of" another day)
                             as_of=(dt.datetime.now().strftime("%Y-%m-%dT%H:%M")
                                    if a.today == dt.date.today().isoformat() else None))
    _dump(data, out_path)
    # state.json מתקדם רק לקובץ שחולץ. קובץ שהשתנה ולא חולץ שומר את ה-sha הקודם, ולכן נשאר בתור החילוץ
    # ומסומן "הוסר" אם יימחק; קובץ חדש שלא חולץ אינו נרשם ונשאר "חדש".
    state_path = os.path.join(ingest, "state.json")
    prev_state = _load(state_path, {}) or {}
    state = {}
    for f in scan["files"]:
        if f["status"] in ("removed", "duplicate"):
            continue
        if f.get("sha256") and f["sha256"] in good:
            state[f["path"]] = f["sha256"]
        elif f["path"] in prev_state:
            state[f["path"]] = prev_state[f["path"]]
    _dump(state, state_path)
    print("הסכמים %d, מועדים %d, ציטוטים %d, לאימות %d" % (len(data["agreements"]), len(data["events"]),
                                                       len(data["footnotes"]), len(data["review_queue"])))
    return 0


def cmd_validate(a):
    try:
        data = _load(a.data, {})
    except ValueError:
        print("קובץ הנתונים אינו JSON תקין")
        return 1
    errors, warns = check_data(data)
    for e in errors:
        print("שגיאה: " + e)
    for w in warns:
        print("אזהרה: " + w)
    print("%d שגיאות, %d אזהרות" % (len(errors), len(warns)))
    return 1 if errors else 0


def cmd_build(a):
    try:
        build.build(a.data, a.template, a.out, audience=a.audience, hide_ids=a.hide_id, hide_types=a.hide_type)
    except build.AudienceError as e:
        print("שגיאה: %s" % e)
        return 1
    print("נשמר: " + a.out)
    return 0


def cmd_acceptance(a):
    from clm import acceptance
    if not os.path.exists(a.data):
        print("לא נמצא קובץ הנתונים: %s. יש להריץ assemble תחילה." % a.data)
        return 1
    try:
        data = _load(a.data)
    except ValueError:
        print("קובץ הנתונים אינו JSON תקין")
        return 1
    if not isinstance(data, dict) or any(k not in data for k in ("documents", "agreements", "events")):
        print("קובץ הנתונים אינו במבנה clm-data.json. יש להריץ validate")
        return 1
    ok, lines = acceptance.report(data)
    print("\n".join(lines))
    return 0 if ok else 1


def main(argv=None):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser(prog="clm_cli")
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("scan")
    s.add_argument("--folders", nargs="+", required=True)
    s.add_argument("--data-dir", required=True)
    s.add_argument("--exclude", nargs="*")
    s = sub.add_parser("assemble")
    s.add_argument("--data-dir", required=True)
    s.add_argument("--company", required=True)
    s.add_argument("--today", default=dt.date.today().isoformat())
    s.add_argument("--default-owner", default="me")
    s.add_argument("--playbooks", help="אינדקס הפלייבוקים; ברירת מחדל <data-dir>/playbooks/index.json")
    s.add_argument("--home-law", default=None, help="הדין שנחשב דין מקומי בסיווג הדין החל; ברירת מחדל: מדינת ההתאגדות מהפרופיל, ואחריה ההרצה הקודמת")
    s.add_argument("--lang", choices=("he", "en"), default=None,
                   help="שפת הנתונים (meta.lang). ברירת מחדל: deliverable_language או display_language מהפרופיל, "
                        "אחריהם השפה של ההרצה הקודמת, ואז he")
    s = sub.add_parser("validate")
    s.add_argument("--data", required=True)
    s = sub.add_parser("build")
    s.add_argument("--data", required=True)
    s.add_argument("--out", required=True)
    s.add_argument("--template", default=os.path.join(ROOT, "assets", "workspace-template.html"))
    s.add_argument("--audience", choices=("full", "restricted"), default="full",
                   help="full: העותק המלא המקומי. restricted: עותק לקהל מצומצם, ההסכמים המוסתרים מוסרים מהנתונים לפני ההטמעה")
    s.add_argument("--hide-id", action="append", default=[], help="מזהה הסכם להסרה מהעותק המצומצם (אפשר כמה פעמים)")
    s.add_argument("--hide-type", action="append", default=[], help="קוד סוג הסכם להסרה מהעותק המצומצם (אפשר כמה פעמים)")
    s = sub.add_parser("acceptance")
    s.add_argument("--data", required=True)
    a = p.parse_args(argv)
    return {"scan": cmd_scan, "assemble": cmd_assemble, "validate": cmd_validate,
            "build": cmd_build, "acceptance": cmd_acceptance}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
