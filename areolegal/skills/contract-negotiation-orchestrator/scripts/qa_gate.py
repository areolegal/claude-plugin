#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""שער האיכות: הבדיקה שאין דליפה פנימית, ובניית העותק למשלוח.

`external_comments_guide.md`, "היחס לתיעוד הפנימי": **הבדיקה שאין דליפה
אינה נעשית בעין. שער האיכות האוטומטי סורק את טקסט כל הבועות החיצוניות
ואת כל חלקי הקובץ, וכל מילה מהרשימה האסורה עוצרת את המסירה.** אין לכתוב
למשתמש שאין דליפה, אלא את תוצאת השער כפי שהיא.

שני מצבים, והם אינם אותו דבר:

* `--mode work` — בודק את קובץ העבודה. הכותרת הפנימית **חייבת** להיות בו,
  ובועה פנימית בו היא תקינה. זהו הקובץ שנשאר אצל עורך הדין.
* `--mode send` — גוזר עותק בלי השכבה הפנימית, מריץ עליו את השער, ו**משנה
  את שמו לשם הסופי רק כשהוא עובר**. כשהוא נכשל, הקובץ הזמני נמחק ואין
  בתיקייה קובץ "למשלוח" כלל, ועותק "למשלוח" ישן שנמצא בנתיב מקבל את
  הסיומת " - לא למשלוח". כך אין מצב שבו קובץ שנכשל בשער יושב בתיקייה
  ומחכה שמישהו ישלח אותו בטעות. קובץ קיים בנתיב `--send` נדרס כשהשער
  עובר, ולכן השם נגזר לפי סבב, והסקריפט אומר זאת לפני שהוא רץ.

קוד היציאה הוא חלק מהתשובה: **0** עבר, **3** נכשל בשער (וזו תשובה, לא
תקלה), **2** קלט חסר או שאינו קריא, **1** נתיב פלט שסורב.

    python3 scripts/qa_gate.py --mode send \\
        --work "<קובץ העבודה>.docx" --received "<הטיוטה שהתקבלה>.docx" \\
        --send "<העותק למשלוח>.docx" --profile Areo-נתונים/profile.json \\
        --deal "Areo-נתונים/transactions/<id>" --out <דוח>.json

המימוש ב-`areolegal/lib/orchestrator/qa_gate.py` (קוד הייחוס של ענבל).
רשימת המילים האסורות, קודי הכשל והניסוחים הם שלו, והסקריפט הזה אינו
מנסח אותם מחדש ואינו מוסיף להם שיקול דעת.
"""
import json
import os
import sys

import areo_lib  # noqa: F401  מוסיף את areolegal/lib לנתיב הייבוא

from common.cli import OutputRefused, guard_out, no_bytecode, parser  # noqa: E402
from orchestrator import pre_send, qa_gate  # noqa: E402


def load(path, what, required=True):
    if not path:
        if required:
            print("חסר %s" % what)
            raise SystemExit(2)
        return None
    if not os.path.exists(path):
        print("%s אינו קיים: %s" % (what, path))
        raise SystemExit(2)
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except ValueError as exc:
        print("%s אינו JSON תקין (%s): %s" % (what, exc, path))
        raise SystemExit(2)


def report(res):
    """הדפסת התוצאה כפי שהשער מחזיר אותה, בלי פרשנות ובלי ריכוך."""
    print("מצב: %s" % res["mode"])
    for f in res["failures"]:
        print("  כשל   [%s] %s%s" % (f.get("code", "?"), f.get("message", ""),
                                     "  (%s)" % f["where"] if f.get("where") else ""))
    for w in res["warnings"]:
        print("  אזהרה [%s] %s%s" % (w.get("code", "?"), w.get("message", ""),
                                     "  (%s)" % w["where"] if w.get("where") else ""))
    info = res.get("info") or {}
    print("  שפה: %s   בועות חיצוניות: %s   בועות פנימיות: %s"
          % (info.get("lang", "?"), info.get("external_comments", "?"),
             info.get("internal_comments", "?")))
    print("תוצאה: %s" % ("עבר" if res["passed"] else "נכשל: %d" % len(res["failures"])))


def main(argv=None):
    no_bytecode()
    ap = parser(__doc__.split("\n")[0], out_required=False)
    ap.add_argument("--mode", required=True, choices=("work", "send"))
    ap.add_argument("--work", required=True, help="קובץ העבודה, עם השכבה הפנימית")
    ap.add_argument("--received", required=True, help="הטיוטה שהתקבלה מהצד שכנגד")
    ap.add_argument("--profile", required=True, help="profile.json של הלקוח")
    ap.add_argument("--send", help="נתיב העותק למשלוח. דרוש ב--mode send")
    ap.add_argument("--state", help="negotiation_state.json של העסקה")
    ap.add_argument("--deal", help="תיקיית העסקה. ממנה נקרא risk-register.json")
    ap.add_argument("--register", help="risk-register.json, כשאינו בתיקיית העסקה")
    ap.add_argument("--decisions", help="קובץ ההכרעות של הסבב")
    ap.add_argument("--expected-accept",
                    help="JSON עם מערך נוסחי היעד, פסקה לפסקה. בלעדיו בדיקת "
                         "ההלוך ושוב של \"קבל הכול\" אינה רצה, והדבר נאמר בפלט")
    ap.add_argument("--lang", choices=("he", "en"),
                    help="שפת ההסכם. בלעדיו: נגזרת מהטיוטה שהתקבלה")
    a = ap.parse_args(argv)

    for p, what in ((a.work, "קובץ העבודה"), (a.received, "הטיוטה שהתקבלה")):
        if not os.path.exists(p):
            print("%s אינו קיים: %s" % (what, p))
            return 2
    profile = load(a.profile, "הפרופיל")
    state = load(a.state, "קובץ המצב", required=False)
    decisions = load(a.decisions, "קובץ ההכרעות", required=False)
    register = load(a.register, "המרשם", required=False)
    if register is None and a.deal:
        register = pre_send.load_register(a.deal)
    expected = load(a.expected_accept, "נוסחי היעד", required=False)
    if expected is not None and not isinstance(expected, list):
        print("--expected-accept הוא מערך של נוסחי פסקאות, ולא %s"
              % type(expected).__name__)
        return 2
    if expected is None:
        print("הערה: בלי --expected-accept, בדיקת \"קבל הכול\" (RT_ACCEPT) אינה רצה.")

    if a.mode == "work":
        res = qa_gate.run_gate(a.work, a.received, "work", profile, state=state,
                               expected_accept=expected, register=register,
                               decisions=decisions, lang=a.lang)
    else:
        if not a.send:
            print("ב--mode send דרוש --send: הנתיב שאליו ישונה שם העותק אם יעבור")
            return 2
        try:
            # `allow_existing_doc`: הספרייה מטפלת בעותק קיים בנתיב, ולא
            # דורסת אותו בשקט — בכשל הוא מקבל " - לא למשלוח". חסימה כאן
            # הייתה מונעת הרצה שנייה באותו סבב, שהיא המצב הרגיל
            guard_out(a.send, inputs=[a.work, a.received], allow_existing_doc=True)
        except OutputRefused as exc:
            print("סירוב על --send: %s" % exc)
            return 1
        if os.path.exists(a.send):
            # בהצלחה הוא נדרס. השם נגזר לפי סבב, ולכן זה נאמר ואינו שקט
            print("הערה: בנתיב --send כבר יש קובץ. אם השער יעבור הוא יידרס, "
                  "ואם ייכשל הוא יקבל \" - לא למשלוח\".")
        res = qa_gate.build_send_copy(a.work, a.received, a.send, profile, state=state,
                                      expected_accept=expected, deal_dir=a.deal,
                                      register=register, decisions=decisions, lang=a.lang)

    report(res)
    if a.mode == "send":
        if res.get("send_copy"):
            print("העותק למשלוח: %s" % res["send_copy"])
        else:
            print("לא נוצר עותק למשלוח, והקובץ הזמני נמחק.")
            if res.get("retracted"):
                print("עותק למשלוח קודם סומן: %s" % res["retracted"])

    if a.out:
        try:
            path = guard_out(a.out, inputs=[a.work, a.received, a.profile])
        except OutputRefused as exc:
            print("סירוב: %s" % exc)
            return 1
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(res, fh, ensure_ascii=False, indent=2, default=str)
        print("נכתב %s" % path)

    # כשל בשער הוא תשובה ולא תקלה, ולכן הוא קוד נפרד: הרכיב אינו ממשיך
    # למסירה, וגם אינו מדווח על שגיאה טכנית שלא הייתה
    return 0 if res["passed"] else 3


if __name__ == "__main__":
    sys.exit(main())
