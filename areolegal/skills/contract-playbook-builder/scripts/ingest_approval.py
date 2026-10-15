#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""קליטת גיליון העמדות החתום, וכתיבת המעמד לכל השכבות בפעולה אחת.

`playbook-schema.md`, `playbook_status`: **נגזר בקוד, ולעולם אינו נכתב
ידנית**, ו"אחרי כל קליטה של גיליון העמדות, הערך ו-`status_label` נכתבים
מחדש **באותה פונקציה לכל השכבות**": המודל, הגרעין, הרשומה ב-
`playbooks/index.json`, ה-`handoff`, התאים, ו-`policy_status` של כל כלל
ושל כל סעיף. באותה פעולה גם ה-Word וסביבת העבודה מקבלים את המעמד החדש.

שש שכבות שנכתבות ביד הן שש שכבות שייסתרו זו את זו, וזה כבר קרה: המודל
אמר "מדיניות מאושרת" בעוד התאים נשארו מהרשומה המדומה, השאלות המכריעות
נשארו פתוחות, וה-handoff נשאר Draft. לכן אין כאן דגל שמאפשר לכתוב רק
חלק: או שהכול נכתב, או שהקליטה נעצרת.

`--received-via` הוא **אחד משני קודים**, `user_upload` או
`chat_attachment`, ולא תיאור במילים. כל ערך אחר נספר כ"אין ראיה", הרשומה
נעשית `simulated`, והפלייבוק נשאר `Draft` אחרי חתימה אמיתית.

**שלושה דברים שהקליטה אינה עושה בשתיקה.** עמודה שנחתמה בשם תפקיד ולא
בשם אדם אינה נקלטת; עמדה טעונת בדיקה משפטית אינה מאושרת בלי מי בדק ומתי;
וקליטה בלי ראיה (`--upload-ref`) נרשמת כ-`simulated`, ואינה פותחת את שער
המדיניות. כל אחד מאלה מודפס, ואינו מרוכך.

    python3 scripts/ingest_approval.py --signed "<הגיליון החתום>.docx" \\
        --manifest "<approval-sheet-manifest.json>" \\
        --model playbook-model.json --core playbook-core.json \\
        --index Areo-נתונים/playbooks/index.json \\
        --records "Areo-נתונים/אישורים" \\
        --received-via user_upload \\
        --upload-ref "<הקובץ בתיקיית ההעלאות>"

המימוש ב-`areolegal/lib/playbook/ingest_approval.py`, `playbook/status.py`
ו-`playbook/after_ingest.py` (קוד הייחוס של ענבל). ההחלטה מה נספר כמאושר
היא שלהם, ולא של הסקריפט הזה ולא של המודל שמריץ אותו.
"""
import json
import os
import sys

import areo_lib  # noqa: F401  מוסיף את areolegal/lib לנתיב הייבוא

from common.cli import OutputRefused, guard_out, no_bytecode, parser  # noqa: E402
from playbook import after_ingest, ingest_approval  # noqa: E402
from playbook.ingest_approval import EVIDENCE_KINDS  # noqa: E402


def load(path, what):
    if not os.path.exists(path):
        print("%s אינו קיים: %s" % (what, path))
        raise SystemExit(2)
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def save(path, data):
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=1)


def index_entry_of(index, model):
    """הרשומה של הפלייבוק הזה ב-playbooks/index.json, לפי המשפחה והצד."""
    if not index:
        return None, None
    entries = index.get("playbooks") if isinstance(index, dict) else index
    if not isinstance(entries, list):
        return None, None
    fam = model.get("family_code") or model.get("family_id")
    role = model.get("company_role_code") or model.get("company_role")
    for e in entries:
        if e.get("family_code") == fam and e.get("company_role_code") == role:
            return e, entries
    return None, entries


def main(argv=None):
    no_bytecode()
    ap = parser(__doc__.split("\n")[0], out_required=False,
                out_help="דוח הקליטה (JSON). הקבצים עצמם מתעדכנים בכל מקרה")
    ap.add_argument("--signed", required=True, help="הגיליון החתום שחזר")
    ap.add_argument("--manifest", required=True, help="המניפסט של אותה הפקה")
    ap.add_argument("--model", required=True, help="playbook-model.json")
    ap.add_argument("--core", help="playbook-core.json")
    ap.add_argument("--index", help="playbooks/index.json")
    ap.add_argument("--records", required=True, help="תיקיית רשומות האישור")
    # אוצר מילים סגור (`ingest_approval.EVIDENCE_KINDS`), ולא תיאור חופשי:
    # כל מחרוזת אחרת נספרת כ"אין ראיה", הרשומה נעשית simulated, והפלייבוק
    # נשאר Draft אחרי חתימה אמיתית. choices הופך את הטעות לבלתי אפשרית
    ap.add_argument("--received-via", choices=EVIDENCE_KINDS,
                    help="הערוץ שבו הקובץ הגיע: user_upload (המשתמש העלה "
                         "אותו) או chat_attachment (צרופה של המארח)")
    ap.add_argument("--upload-ref", help="הקובץ בתיקיית ההעלאות, או מזהה הצרופה. "
                                         "בלעדיו הקליטה היא simulated")
    ap.add_argument("--word", help="ה-Word של הפלייבוק, להטבעת המעמד מחדש")
    ap.add_argument("--workspace", help="קובץ סביבת העבודה, להטבעת המעמד מחדש")
    ap.add_argument("--supersedes", help="מזהה רשומה שהקליטה הזאת מחליפה")
    ap.add_argument("--reason", help="נימוק להחלפת רשומה. חובה עם --supersedes")
    ap.add_argument("--today", help="תאריך הקליטה. לבדיקות בלבד")
    a = ap.parse_args(argv)

    if a.supersedes and not a.reason:
        print("--supersedes בלי --reason: החלפת רשומת אישור אינה פעולה שקטה")
        return 2
    if not os.path.exists(a.signed):
        print("הגיליון החתום אינו קיים: %s" % a.signed)
        return 2
    manifest = load(a.manifest, "המניפסט")
    model = load(a.model, "המודל")
    core = load(a.core, "הגרעין") if a.core else None
    index = load(a.index, "האינדקס") if a.index else None
    entry, entries = index_entry_of(index, model)
    if a.index and entry is None:
        print("אזהרה: אין ב-%s רשומה למשפחה ולצד של המודל, ולכן המעמד "
              "לא ייכתב לאינדקס. זו שכבה שתישאר מאחור." % a.index)

    try:
        res = ingest_approval.ingest(a.signed, manifest, received_via=a.received_via,
                                     upload_ref=a.upload_ref, today=a.today)
    except ValueError as exc:
        print("הקליטה נעצרה: %s" % exc)
        return 3

    for w in res.get("warnings") or ():
        print("  אזהרה: %s" % w)
    if not res.get("record"):
        print("לא נקלטה רשומה. הגיליון אינו הגרסה הסופית לחתימה, או שאין בו חתימה קבילה.")
        return 3

    record_path = ingest_approval.save_record(a.records, a.signed, res,
                                              supersedes=a.supersedes, reason=a.reason)
    out = after_ingest.apply_ingest(model, core, entry, res, record_path,
                                    word_path=a.word, workspace_path=a.workspace)

    # הכתיבה לדיסק נעשית אחרי שכל השכבות עודכנו באותו אובייקט, כדי שלא
    # יישאר על הדיסק מצב שבו חלק מהשכבות עודכנו וחלק לא
    save(a.model, model)
    if a.core:
        save(a.core, core)
    if a.index and entry is not None:
        save(a.index, index if isinstance(index, dict) else entries)

    st = out["status"]
    print("מעמד  : %s" % st.get("playbook_status"))
    print("תווית : %s" % st.get("label"))
    cells = res["cells"]
    approved = sum(1 for v in cells.values() if v.get("status") == "approved")
    print("תאים  : %d מאושרים מתוך %d" % (approved, len(cells)))
    if out.get("closed"):
        print("נסגרו : %s" % ", ".join(out["closed"]))
    print("רשומה : %s" % record_path)
    if res["record"].get("simulated"):
        print("הקליטה simulated (אין --upload-ref): שער המדיניות אינו נפתח.")
    for p in out.get("problems") or ():
        print("  סתירה בין השכבות: %s" % p)
    if out.get("word"):
        print("Word  : %s" % out["word"])
    if out.get("workspace"):
        print("סביבה : %s" % out["workspace"])

    if a.out:
        try:
            path = guard_out(a.out, inputs=[a.signed, a.manifest, a.model, a.core,
                                            a.index, a.word, a.workspace])
        except OutputRefused as exc:
            # הקבצים כבר עודכנו, ולכן זה אינו כשל של הקליטה אלא של הדוח
            print("הדוח לא נכתב. סירוב: %s" % exc)
        else:
            save(path, {"status": st, "cells": cells, "record_path": record_path,
                        "closed": out.get("closed"), "problems": out.get("problems"),
                        "warnings": res.get("warnings")})
            print("נכתב %s" % path)

    # סתירה בין השכבות אחרי הקליטה היא בדיוק מה שהפונקציה הזאת נועדה
    # למנוע, ולכן היא אינה "אזהרה" אלא כשל
    return 4 if out.get("problems") else 0


if __name__ == "__main__":
    sys.exit(main())
