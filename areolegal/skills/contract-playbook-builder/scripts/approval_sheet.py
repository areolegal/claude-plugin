#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""הפקת גיליון "עמדות משא ומתן לאישור", והמניפסט שלו.

הגיליון הוא המסמך שהיועץ המשפטי של החברה חותם עליו, ובו לכל כלל שלושת
התאים (ירוק, צהוב, אדום), הנוסח שיוחל מילה במילה, שורות ההשפעה לפי
הפוזיציה של החברה, וההנחות שהבונה הניח ושצריך לאשר.

**המניפסט אינו נספח, והוא חובה.** הוא נשמר לצד הגיליון, והוא מה שמאפשר
לקליטה לדעת לאיזו הפקה העותק החתום שייך (`token`), איזו שורה היא איזה
כלל, ומה היה הגיבוב של הקובץ שיצא. בלי המניפסט אין קליטה: קובץ חתום בלי
ההפקה שלו אינו ניתן לאימות, ו-`ingest_approval.py` יסרב לו.

    python3 scripts/approval_sheet.py --model playbook-model.json \\
        --out-dir "Areo-נתונים/גיליונות" --company "<שם החברה>"

המימוש ב-`areolegal/lib/playbook/approval_sheet.py` (קוד הייחוס של ענבל),
וכך גם שער הנוסח שעוצר הפקה שבה נוסח תא חסר או אינו עברית. הסקריפט הזה
אינו מנסח, אינו מסדר ואינו מחליט דבר על הגיליון.
"""
import json
import os
import sys

import areo_lib  # noqa: F401  מוסיף את areolegal/lib לנתיב הייבוא

from common.cli import OutputRefused, guard_out, no_bytecode, parser  # noqa: E402
from playbook.approval_sheet import build_sheet  # noqa: E402

MANIFEST = "approval-sheet-manifest.json"


def main(argv=None):
    no_bytecode()
    ap = parser(__doc__.split("\n")[0], out_required=False,
                out_help="נתיב המניפסט. בלעדיו הוא נכתב כ-%s לצד הגיליון" % MANIFEST)
    ap.add_argument("--model", required=True, help="playbook-model.json")
    ap.add_argument("--out-dir", required=True, help="התיקייה שבה ייכתבו הגיליון והמניפסט")
    ap.add_argument("--company", default="", help="שם החברה, לשער הגיליון")
    ap.add_argument("--lang", default="he", choices=("he",),
                    help="שפת הגיליון. הוא נחתם בישראל, ולכן עברית בלבד")
    ap.add_argument("--token-uid", help="מזהה ההפקה. לבדיקות בלבד; בלעדיו הוא מוגרל")
    ap.add_argument("--no-wording-gate", action="store_true",
                    help="מדלג על שער הנוסח. לאבחון בלבד, ולא להפקה שנשלחת לחתימה")
    a = ap.parse_args(argv)

    if not os.path.exists(a.model):
        print("המודל אינו קיים: %s" % a.model)
        return 2
    with open(a.model, encoding="utf-8") as fh:
        model = json.load(fh)

    os.makedirs(a.out_dir, exist_ok=True)
    manifest_path = a.out or os.path.join(a.out_dir, MANIFEST)
    try:
        manifest_path = guard_out(manifest_path, inputs=[a.model])
    except OutputRefused as exc:
        print("סירוב: %s" % exc)
        return 1

    try:
        path, manifest = build_sheet(model, a.out_dir, company=a.company, lang=a.lang,
                                     token_uid=a.token_uid,
                                     check_wording=not a.no_wording_gate)
    except Exception as exc:
        # שער הנוסח עוצר הפקה פגומה, וזו תשובה: גיליון בלי נוסח תא אינו
        # מסמך שאפשר לחתום עליו
        print("ההפקה נעצרה: %s" % exc)
        return 3

    with open(manifest_path, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, ensure_ascii=False, indent=1)

    print("הגיליון : %s" % path)
    print("המניפסט : %s" % manifest_path)
    print("ההפקה   : %s" % manifest["token"])
    print("שורות   : %d   תאים: %d   שאלות מכריעות: %d"
          % (len(manifest.get("rows") or {}), len(manifest.get("cells") or {}),
             len(manifest.get("questions") or {})))
    print("שמור את המניפסט. בלעדיו העותק החתום אינו ניתן לקליטה.")
    if a.no_wording_gate:
        print("אזהרה: שער הנוסח דולג. אין לשלוח את הגיליון הזה לחתימה.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
