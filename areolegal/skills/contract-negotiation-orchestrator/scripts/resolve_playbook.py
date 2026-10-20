#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""איתור הפלייבוק לעסקה, בסקריפט ולא בשיקול דעת.

`overview.md`, שלב א.2: אין פלייבוק בנתיב קבוע אחד. רכיב הפלייבוק שומר
פלייבוק נפרד לכל משפחת הסכמים ולכל פוזיציה, והאיתור צריך לדרג את
המועמדים, לפסול את מי שאינו מתאים למשפחה ולצד, ולהגיד במילים על מה
ההכרעה נשענת. מודל שעושה את זה בשיקול דעת בוחר אחרת בכל הרצה.

התוצאה נכתבת ל-`--out` ונכנסת לקובץ המצב בשדה `playbook_resolution`
(`negotiation_state_schema.md`). `source_label` הוא המשפט שמוצג
למשתמש, ואין לנסח אותו מחדש.

    python3 scripts/resolve_playbook.py --data Areo-נתונים \\
        --folder <תיקיית ההסכם> --family "הסכם שירותים" --role customer \\
        --language he --out Areo-נתונים/transactions/<id>/playbook-resolution.json

המימוש ב-`areolegal/lib/orchestrator/resolve_playbook.py` (קוד הייחוס
של ענבל). הסקריפט הזה הוא העטיפה שלו בלבד, ואין בו שיקול דעת משל עצמו.
"""
import glob
import json
import os
import re
import sys

import areo_lib  # noqa: F401  מוסיף את areolegal/lib לנתיב הייבוא

from common.cli import OutputRefused, guard_out, no_bytecode, parser  # noqa: E402
from orchestrator.resolve_playbook import (FAMILY_WORDS, ROLE_SIDE, ROLE_WORDS,  # noqa: E402
                                           family_of, resolve, side_of, source_label)


def _norm(s):
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s]", " ", str(s or "").lower())).strip()


def playbook_families(data_dir):
    """{קוד המשפחה: השמות שלה} לכל פלייבוק של הלקוח, מתוך הגרעין: family_code, family_id, השם והכינויים.

    הבונה בונה פלייבוק לכל סוג הסכם שבתיקייה, ו-FAMILY_WORDS מכיר שש משפחות בלבד. בהרצה חיה
    (20.10.2026) הנושא ונותן לא מצא את הפלייבוק של הסכמי המנוי לענן שנבנה שעה קודם, גם כשקיבל את
    הקוד המדויק, כי "saas_subscription" אינו ברשימה, ועצר לפני ההכרעות."""
    out = {}
    entries = {}
    try:
        with open(os.path.join(data_dir, "playbooks", "index.json"), encoding="utf-8") as fh:
            for e in json.load(fh).get("playbooks") or ():
                rel = e.get("core_path") or e.get("path") or ""
                core = os.path.join(data_dir, rel)
                core = os.path.join(core, "playbook-core.json") if os.path.isdir(core) else core
                entries[os.path.normcase(os.path.abspath(core))] = e
    except (OSError, ValueError, AttributeError):
        pass
    for core in glob.glob(os.path.join(data_dir, "playbooks", "*", "playbook-core.json")):
        try:
            with open(core, encoding="utf-8") as fh:
                c = json.load(fh)
        except (OSError, ValueError):
            continue
        e = entries.get(os.path.normcase(os.path.abspath(core)), {})
        names = {e.get("family_name") or "", c.get("family_name") or "", c.get("family_id") or ""}
        names |= set(e.get("family_aliases") or ())
        # אותו סדר כמו _builder_candidate בספרייה, כדי שהקוד כאן יהיה הקוד שהספרייה משווה אליו
        code = c.get("family_code") or e.get("family_code") or family_of(" ".join(n for n in names if n))
        if not code or code == "unknown":
            code = c.get("family_id")
        if not code:
            continue
        names |= {code, c.get("family_code") or "", e.get("family_code") or ""}
        for f in c.get("contract_families") or ():
            if isinstance(f, dict):
                names.add(f.get("contract_family_name") or "")
                names |= set(f.get("family_aliases") or ())
        out.setdefault(code, set()).update(n for n in names if n)
    return out


def family_code(name, data_dir, label=None):
    """הקוד של המשפחה: קוד מוכר, קוד או שם או כינוי של פלייבוק קיים, ורק אחריהם FAMILY_WORDS."""
    if name in FAMILY_WORDS:
        return name
    known = playbook_families(data_dir)
    for code, names in known.items():
        if name == code or name in names:
            return code
    for text in (name, label):
        t = _norm(text)
        if not t:
            continue
        for code, names in known.items():
            if any(_norm(n) and (_norm(n) in t or t in _norm(n)) for n in names):
                return code
    return family_of(name)


def main(argv=None):
    no_bytecode()
    ap = parser(__doc__.split("\n")[0], out_required=False)
    ap.add_argument("--data", required=True, help="תיקיית Areo-נתונים של הלקוח")
    ap.add_argument("--folder", required=True, help="התיקייה שבה ההסכם שהגיע")
    ap.add_argument("--family", required=True, help="משפחת ההסכמים, כפי שהלקוח קורא לה")
    ap.add_argument("--role", required=True, help="הפוזיציה של החברה בהסכם")
    ap.add_argument("--language", required=True, help="שפת ההסכם: he / en")
    ap.add_argument("--counterparty-kind", default="company",
                    help="סוג הצד שכנגד, כשהוא משנה את ההתאמה")
    ap.add_argument("--uploaded", help="פלייבוק שהלקוח העלה בעצמו, כשיש")
    ap.add_argument("--min-skill-version",
                    help="גרסת סקיל מינימלית: פלייבוק שנבנה לפניה מסומן כישן")
    ap.add_argument("--family-label", help="שם המשפחה כפי שהוא בהסכם, כשהוא שונה")
    ap.add_argument("--answer-kind", help="explicit כשהמשתמש בחר במפורש, לשורת המקור")
    a = ap.parse_args(argv)

    # `resolve()` משווה קודים, והסקיל מקבל מהמשתמש שם בעברית. שם שאינו
    # מתורגם אינו "אין פלייבוק": הוא עצירה. `family_of` מחזיר 'unknown'
    # ולא ערך ריק, ו-`side_of` מחזיר None, ולכן שתי הבדיקות שונות
    family = family_code(a.family, a.data, a.family_label)
    if family == "unknown":
        print("לא זוהתה משפחה מהשם %r. הקודים: %s"
              % (a.family, ", ".join(sorted(set(FAMILY_WORDS) | set(playbook_families(a.data))))))
        return 2
    role = a.role if a.role in ROLE_WORDS else side_of(a.role)
    if not role:
        # תפקיד שאינו בעברית ואינו קוד מוכר: אולי קוד נרדף שבמפתח
        # (customer, buyer, licensee), ואלה נפתרים בתוך `resolve`
        role = a.role if a.role.strip().lower() in ROLE_SIDE else None
        if not role:
            print("לא זוהתה פוזיציה מהשם %r. הקודים: %s"
                  % (a.role, ", ".join(sorted(set(ROLE_SIDE) | set(ROLE_WORDS)))))
            return 2

    res = resolve(a.data, a.folder, family, role, a.language,
                  counterparty_kind=a.counterparty_kind, uploaded=a.uploaded,
                  min_skill_version=a.min_skill_version,
                  agreement_family_label=a.family_label)
    res["source_label"] = source_label(res, activation_answer_kind=a.answer_kind)

    print("משפחה: %s   פוזיציה: %s" % (family, role))
    print("תוצאה: %s" % res.get("result", "-"))
    if res.get("chosen"):
        print("נבחר : %s" % res["chosen"])
    if res.get("reason"):
        print("סיבה : %s" % res["reason"])
    print("מועמדים: %d" % len(res.get("candidates") or []))
    print("שורת המקור: %s" % res.get("source_label", ""))

    if a.out:
        try:
            path = guard_out(a.out, inputs=[a.uploaded] if a.uploaded else [])
        except OutputRefused as exc:
            print("סירוב: %s" % exc)
            return 1
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(res, fh, ensure_ascii=False, indent=2)
        print("נכתב %s" % path)
    # פלייבוק שלא נמצא אינו שגיאה של הסקריפט: הוא תשובה, והרכיב עוצר לפיה
    return 0


if __name__ == "__main__":
    sys.exit(main())
