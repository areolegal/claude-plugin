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
import json
import sys

import areo_lib  # noqa: F401  מוסיף את areolegal/lib לנתיב הייבוא

from common.cli import OutputRefused, guard_out, no_bytecode, parser  # noqa: E402
from orchestrator.resolve_playbook import (FAMILY_WORDS, ROLE_SIDE, ROLE_WORDS,  # noqa: E402
                                           family_of, resolve, side_of, source_label)


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
    family = a.family if a.family in FAMILY_WORDS else family_of(a.family)
    if family == "unknown":
        print("לא זוהתה משפחה מהשם %r. הקודים: %s"
              % (a.family, ", ".join(sorted(FAMILY_WORDS))))
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
    print("תוצאה: %s" % res.get("result", "—"))
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
