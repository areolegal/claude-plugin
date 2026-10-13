#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""שומר את הגרסה הקיימת של פלייבוק לפני שכותבים עליה.

הכלל חל על כל פלייבוק, לא רק על אחד שסומן מאושר, כי כמעט כל מה שהבונה
מפיק הוא טיוטה, וטיוטה שנדרסת אובדת (`core-contract.md`, "Draft status and
auditability"; `workflow.md` שלב 10). הגרסה הקודמת נשמרת בתיקיית הסוג שלה
בלבד, ואין נגיעה בפלייבוק של סוג אחר או של פוזיציה אחרת.

  python3 keep_version.py <תיקיית-הסוג>            # שומר, ומדפיס לאן
  python3 keep_version.py <תיקיית-הסוג> --check     # בודק בלבד, בלי לכתוב

תיקיית הסוג היא זו שבה יושב `playbook-model.json`, למשל
`Areo-נתונים/playbooks/fam_services_customer`.
"""
import argparse
import datetime
import io
import json
import shutil
import sys
from pathlib import Path

# מה נשמר: המודל, הגרעין שהרכיבים קוראים, והתוצרים שהופקו מהם
KEEP = ["playbook-model.json", "playbook-core.json", "decisions-applied.json",
        "corpus-manifest.json", "clause-inventory.json"]
KEEP_GLOBS = ["*.docx", "*.xlsx", "*.pptx", "*.html"]


def version_of(folder):
    """גרסת הפלייבוק שיושב בתיקייה, כדי לתת לה שם בארכיון."""
    model = folder / "playbook-model.json"
    if not model.is_file():
        return None
    try:
        d = json.loads(io.open(model, encoding="utf-8").read())
    except ValueError as e:
        sys.exit("playbook-model.json אינו JSON תקין, ולכן אין לכתוב עליו: %s" % e)
    return str(d.get("version") or "0.0")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("folder")
    ap.add_argument("--check", action="store_true", help="בדיקה בלבד")
    a = ap.parse_args()
    folder = Path(a.folder).resolve()
    if not folder.is_dir():
        sys.exit("אין תיקייה כזאת: %s" % folder)

    ver = version_of(folder)
    if ver is None:
        print("אין בתיקייה playbook-model.json: זו בנייה ראשונה, ואין גרסה לשמור.")
        return 0

    dest = folder / "versions" / ver
    # שתי בניות באותו יום לאותה גרסה אינן דורסות זו את זו
    if dest.exists():
        stamp = datetime.datetime.now().strftime("%Y-%m-%d-%H%M")
        dest = folder / "versions" / ("%s-%s" % (ver, stamp))

    items = [folder / n for n in KEEP if (folder / n).is_file()]
    for pat in KEEP_GLOBS:
        items += [p for p in folder.glob(pat) if p.is_file()]
    if not items:
        print("אין מה לשמור בתיקייה %s" % folder)
        return 0

    if a.check:
        print("ישמרו %d קבצים ל-%s:" % (len(items), dest))
        for p in items:
            print("   ", p.name)
        return 0

    dest.mkdir(parents=True)
    for p in items:
        shutil.copy2(p, dest / p.name)
    print("הגרסה הקודמת (%s) נשמרה ב-%s, %d קבצים."
          % (ver, dest.relative_to(folder), len(items)))
    print("אפשר לכתוב עכשיו את הגרסה החדשה.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
