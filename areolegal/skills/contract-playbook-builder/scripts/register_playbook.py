#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""שמירת הפלייבוק בתיקייה שלו, ורישומו באינדקס.

`playbook-schema.md`, "מיקום": פלייבוק אחד לכל סוג הסכם ולכל פוזיציה,
ב-`Areo-נתונים/playbooks/<family_id>/`, עם רשומה ב-
`Areo-נתונים/playbooks/index.json`. **פלייבוק לעולם אינו נכתב על פלייבוק
של סוג אחר או של פוזיציה אחרת, ואינו דוחק אותו.** לפני עדכון או בנייה
מחדש, הגרסה הקודמת של אותו פלייבוק נשמרת ב-`versions/` שבתיקיית הסוג.

`playbook-qa.md`, בדיקה 3, היא בדיוק שלושת הדברים האלה: הפלייבוק נשמר
בתיקייה שלו, הרשומה באינדקס עודכנה, **ולא השתנתה שום רשומה של סוג אחר
או של פוזיציה אחרת**. הסקריפט משווה את האינדקס לפני ואחרי, ומסרב כשנגע
ברשומה שאינה שלו.

`canonical-storage.md`, "Every playbook is in the index": פלייבוק במבנה
הישן שיושב בשורש `Areo-נתונים` נרשם גם הוא, **בלי להזיז אותו**, עם
`legacy: true`. בלי הרישום הזה הוא אינו נמצא באיתור.

הרשומה נכתבת בשמות שהאיתור קורא (`orchestrator/resolve_playbook`):
`core_path`, `family_code`, `company_role_code`, `family_aliases[]`,
`language`, `last_updated`, ואיתם `corpus_origin`, `playbook_status`,
`status_label` ו-`produced_with`, כדי שרכיב שמחפש פלייבוק יראה את מעמדו
בלי לפתוח את המודל.

    python3 scripts/register_playbook.py --data Areo-נתונים \\
        --model <playbook-model.json> --core <playbook-core.json>

קוד יציאה: **0** נרשם, **3** סירוב (רשומה של פלייבוק אחר הייתה משתנה,
או שחסר במודל מה שהרשומה דורשת), **2** קלט חסר.
"""
import copy
import datetime as _dt
import json
import os
import shutil
import sys

import areo_lib  # noqa: F401  מוסיף את areolegal/lib לנתיב הייבוא

from common.cli import OutputRefused, guard_out, no_bytecode, parser  # noqa: E402
from playbook import status as S  # noqa: E402

# השדות שהאיתור משתמש בהם, ולכן רשומה בלעדיהם אינה נמצאת
KEY_FIELDS = ("core_path", "family_code", "company_role_code")
CARRIED = ("corpus_origin", "playbook_status", "status_label", "produced_with")


def load(path, what):
    if not os.path.exists(path):
        print("%s אינו קיים: %s" % (what, path))
        raise SystemExit(2)
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def entry_identity(e):
    """מה מזהה רשומה: הסוג והפוזיציה. שתיהן יחד, כי סוג אחד מופיע בשני צדדים."""
    return (e.get("family_id") or e.get("family_code"),
            e.get("company_role_code"), bool(e.get("legacy")))


def model_entry(model, core, core_rel, legacy=False):
    st = S.derive_status(model)
    e = {"core_path": core_rel,
         "family_id": model.get("family_id"),
         "family_code": (model.get("family_code") or (core or {}).get("family_code")),
         "company_role_code": (model.get("company_role_code")
                               or (core or {}).get("company_role_code")),
         "family_aliases": list(((model.get("meta") or {}).get("build_request") or {})
                                .get("family_aliases") or []),
         "family_name": ((model.get("meta") or {}).get("build_request") or {}).get("family_label")
                        or model.get("family_label"),
         "language": (model.get("output_language")
                      or ((model.get("meta") or {}).get("build_request") or {}).get("language")),
         "last_updated": _dt.date.today().isoformat(),
         "playbook_status": st["playbook_status"],
         "status_label": st["label"],
         "corpus_origin": (model.get("scope_summary") or {}).get("corpus_origin"),
         "produced_with": model.get("produced_with")}
    if legacy:
        e["legacy"] = True
    return {k: v for k, v in e.items() if v not in (None, "")}


def keep_previous(folder):
    """הגרסה הקודמת של אותו פלייבוק נשמרת ב-versions/, ולא נדרסת."""
    kept = []
    versions = os.path.join(folder, "versions")
    stamp = _dt.datetime.now().strftime("%Y-%m-%d-%H%M%S")
    for name in ("playbook-model.json", "playbook-core.json"):
        src = os.path.join(folder, name)
        if not os.path.exists(src):
            continue
        os.makedirs(versions, exist_ok=True)
        dst = os.path.join(versions, "%s-%s" % (stamp, name))
        shutil.copy2(src, dst)
        kept.append(dst)
    return kept


def main(argv=None):
    no_bytecode()
    ap = parser(__doc__.split("\n")[0], out_required=False,
                out_help="דוח הרישום (JSON). האינדקס מתעדכן בכל מקרה")
    ap.add_argument("--data", required=True, help="תיקיית Areo-נתונים של הלקוח")
    ap.add_argument("--model", required=True, help="playbook-model.json שנבנה")
    ap.add_argument("--core", required=True, help="playbook-core.json שנבנה")
    ap.add_argument("--dry-run", action="store_true",
                    help="מראה מה היה נכתב, בלי לכתוב דבר")
    a = ap.parse_args(argv)

    if not os.path.isdir(a.data):
        print("תיקיית הנתונים אינה קיימת: %s" % a.data)
        return 2
    model = load(a.model, "המודל")
    core = load(a.core, "הגרעין")

    family_id = model.get("family_id")
    if not family_id:
        print("אין במודל family_id, ולכן אין תיקייה לשמור בה ואין רשומה לרשום. "
              "זהו מזהה קבוע לסוג ההסכם ולפוזיציה (fam_<סוג>_<קוד-פוזיציה>).")
        return 3

    folder = os.path.join(a.data, "playbooks", family_id)
    index_path = os.path.join(a.data, "playbooks", "index.json")
    core_rel = os.path.join("playbooks", family_id, "playbook-core.json").replace("\\", "/")
    entry = model_entry(model, core, core_rel)
    missing = [f for f in KEY_FIELDS if not entry.get(f)]
    if missing:
        print("הרשומה לא תימצא באיתור בלי %s. השדות נגזרים מהמודל ומהגרעין."
              % ", ".join(missing))
        return 3

    index = {"playbooks": []}
    if os.path.exists(index_path):
        index = load(index_path, "האינדקס")
        if not isinstance(index, dict) or not isinstance(index.get("playbooks"), list):
            print("האינדקס אינו במבנה {\"playbooks\": [...]}: %s" % index_path)
            return 3
    before = copy.deepcopy(index["playbooks"])

    mine = entry_identity(entry)
    others_before = [e for e in before if entry_identity(e) != mine]
    kept = [e for e in index["playbooks"] if entry_identity(e) != mine]
    updated = kept + [entry]

    # פלייבוק במבנה הישן בשורש: נרשם, ולא מוזז
    legacy_core = os.path.join(a.data, "playbook-core.json")
    legacy_entry = None
    if os.path.exists(legacy_core) and os.path.abspath(legacy_core) != os.path.abspath(a.core):
        legacy_model_path = os.path.join(a.data, "playbook-model.json")
        legacy_model = {}
        if os.path.exists(legacy_model_path):
            try:
                with open(legacy_model_path, encoding="utf-8") as fh:
                    legacy_model = json.load(fh)
            except ValueError:
                legacy_model = {}
        with open(legacy_core, encoding="utf-8") as fh:
            lc = json.load(fh)
        legacy_entry = {"core_path": "playbook-core.json", "legacy": True}
        for key, value in (("family_id", legacy_model.get("family_id") or lc.get("family_id")),
                           ("family_code", legacy_model.get("family_code") or lc.get("family_code")),
                           ("company_role_code", legacy_model.get("company_role_code")
                            or lc.get("company_role_code")),
                           ("family_aliases", list(legacy_model.get("family_aliases") or []))):
            if value:
                legacy_entry[key] = value
        lid = entry_identity(legacy_entry)
        if lid != mine and not any(entry_identity(e) == lid for e in updated):
            updated.append(legacy_entry)
        else:
            legacy_entry = None

    # בדיקה 3 של playbook-qa: לא השתנתה שום רשומה אחרת
    others_after = [e for e in updated
                    if entry_identity(e) != mine
                    and (legacy_entry is None or entry_identity(e) != entry_identity(legacy_entry))]
    if others_after != others_before:
        print("סירוב: רשומה של סוג אחר או של פוזיציה אחרת הייתה משתנה. "
              "פלייבוק אינו דוחק פלייבוק אחר.")
        for e in others_before:
            if e not in others_after:
                print("  הייתה נעלמת: %s" % json.dumps(e, ensure_ascii=False)[:120])
        return 3

    if a.dry_run:
        print("ריצה יבשה. היה נכתב:")
        print("  תיקייה : %s" % folder)
        print("  רשומה  : %s" % json.dumps(entry, ensure_ascii=False, indent=1))
        if legacy_entry:
            print("  ועוד רשומה לפלייבוק במבנה הישן, בלי להזיז אותו")
        return 0

    os.makedirs(folder, exist_ok=True)
    kept_versions = keep_previous(folder)
    for src, name in ((a.model, "playbook-model.json"), (a.core, "playbook-core.json")):
        dst = os.path.join(folder, name)
        if os.path.abspath(src) != os.path.abspath(dst):
            shutil.copy2(src, dst)

    index["playbooks"] = updated
    os.makedirs(os.path.dirname(index_path), exist_ok=True)
    with open(index_path, "w", encoding="utf-8") as fh:
        json.dump(index, fh, ensure_ascii=False, indent=1)

    print("תיקייה: %s" % folder)
    print("אינדקס: %s (%d רשומות)" % (index_path, len(updated)))
    print("רשומה : %s / %s   מעמד: %s"
          % (entry.get("family_code"), entry.get("company_role_code"),
             entry.get("playbook_status")))
    if kept_versions:
        print("הגרסה הקודמת נשמרה: %s" % ", ".join(os.path.basename(p) for p in kept_versions))
    if legacy_entry:
        print("נרשם גם פלייבוק במבנה הישן שבשורש, בלי להזיז אותו.")
    print("רשומות שלא נגעתי בהן: %d" % len(others_before))

    if a.out:
        try:
            path = guard_out(a.out, inputs=[a.model, a.core, index_path])
        except OutputRefused as exc:
            print("הדוח לא נכתב. סירוב: %s" % exc)
        else:
            with open(path, "w", encoding="utf-8") as fh:
                json.dump({"folder": folder, "index": index_path, "entry": entry,
                           "kept_versions": kept_versions,
                           "legacy_registered": bool(legacy_entry),
                           "untouched_entries": len(others_before)},
                          fh, ensure_ascii=False, indent=2)
            print("נכתב %s" % path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
