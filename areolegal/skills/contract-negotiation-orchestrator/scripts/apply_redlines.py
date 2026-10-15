#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""סימון ההכרעות על הטיוטה של הצד שכנגד, בעקוב אחר שינויים, במנוע האחד.

הקובץ נבנה **על הטיוטה שלהם**, ולא כמסמך חדש. הסימון נעשה במנוע של ענבל
(`areolegal/lib/common/docx_tracked.py`, הערות הנושא ונותן 4.8, שינויים 76
ו-77), שמחליף את המנוע הקודם שישב כאן:

* **סימון כירורגי.** רק ההבדל בין הנוסח שלהם לנוסח היעד מסומן, ברמת המילה,
  ומספר, סכום או סוגריים מרובעים כיחידה אחת. פסקה שלמה אינה נמחקת ונכתבת
  מחדש בגלל מילה.
* **הבועה היא `external_comment` בלבד.** אין פתיח קבוע, אין "סעיף X למדיניות
  שלנו" ואין צבע. המסלול ומזהי הכללים נרשמים בקובץ המצב בלבד.
* **השינויים וההערות של הצד שכנגד נשארים במקומם**, עם המחבר והתאריך שלהם.
  שום דבר שלהם אינו מתקבל או נמחק בשקט.
* **שכבה פנימית בקובץ העבודה:** בועה פנימית ליד כל תיקון, במחבר
  "פנימי, למחיקה לפני המשלוח", וכותרת "טיוטת עבודה פנימית, לא למשלוח". העותק
  למשלוח נגזר ממנו ב-`qa_gate.py --mode send`, ולא כאן.
* **"עקוב אחר שינויים" דולק בקובץ**, והשעה בכל שינוי היא שעת ההרצה.
* **בדיקת הלוך ושוב:** "דחה הכול" חייב להחזיר את הטיוטה שהתקבלה, ו"קבל
  הכול" את נוסחי היעד. הכרעה שאינה ניתנת לסימון בבטחה אינה מוחלת חלקית:
  היא מדווחת כ"לא סומנה".

הקלט הוא קובץ ההכרעות של הסבב, `decisions_round_<n>.json`
(`negotiation_state_schema.md`, "קובץ ההכרעות"): לכל הכרעה `id`, `op`
(replace, replace_span, insert_paragraph, delete_paragraph, comment_only או
accept) ו-`decision_code`, והשדות של אותה פעולה. הקובץ נבדק מול החוזה לפני
כל החלה, ושגיאה בו עוצרת את ההרצה בלי לכתוב קובץ.

    python3 scripts/apply_redlines.py --draft "<הטיוטה שהתקבלה>.docx" \\
        --decisions decisions_round_2.json --profile Areo-נתונים/פרופיל-לקוח.json \\
        --deal "Areo-נתונים/transactions/<id>" --agreement-type "הסכם ייעוץ" \\
        --company "<שם החברה המקוצר>" --round 2

**שמות הקבצים נגזרים בקוד** (`overview.md`, "שמירה, נתיבים ושמות קבצים"):
`<סוג ההסכם> - <שם החברה> - סבב <N> - <DD.MM.YYYY>.docx` לעותק למשלוח, ואותו
שם עם " - פנימי" לקובץ העבודה ועם " - כפי שהופק" לעותק כפי שהופק, עד 230
תווים לנתיב, ובלי לדרוס קובץ קיים: שם תפוס מקבל " (2)". הסקריפט מדפיס את
הנתיב של העותק למשלוח, וזה הנתיב שמועבר ל-`qa_gate.py --send`. `--out` מפורש
נשאר לבדיקות ולמקרה חריג.

לצד קובץ העבודה נכתבים שני קבצים: `<שם>.expected.json`, נוסחי היעד שהשער
בודק מולם (`qa_gate.py --expected-accept`), ו-`<שם>.as_produced.docx`, עותק
של קובץ העבודה כפי שהופק, כדי שאפשר יהיה לראות מה עורך הדין שינה בו לפני
המשלוח (שינוי 3ז).

קוד יציאה: **0** הכול סומן והבדיקה עברה, **3** קובץ העבודה נכתב אבל לא הכול
סומן או שבדיקת ההלוך ושוב נכשלה (אינו מוכן למשלוח), **2** קלט שגוי, ולא נכתב
דבר, **1** נתיב פלט שסורב.
"""
import datetime as _dt
import json
import os
import shutil
import sys

import areo_lib  # noqa: F401  מוסיף את areolegal/lib לנתיב הייבוא

from common.cli import OutputRefused, guard_out, no_bytecode, parser  # noqa: E402
import common.docx_tracked as dt  # noqa: E402
from common import gap_checks, paths  # noqa: E402
from orchestrator import qa_gate  # noqa: E402
from lawyer import lawyer_view  # noqa: E402


def load(path, what):
    if not os.path.exists(path):
        print("%s אינו קיים: %s" % (what, path))
        raise SystemExit(2)
    with open(path, encoding="utf-8") as fh:
        try:
            return json.load(fh)
        except ValueError as exc:
            print("%s אינו JSON תקין (%s)" % (what, exc))
            raise SystemExit(2)


def side_paths(out):
    stem = out[:-5] if out.lower().endswith(".docx") else out
    return stem + ".expected.json", stem + ".as_produced.docx"


def main(argv=None):
    no_bytecode()
    sys.stdout.reconfigure(encoding="utf-8")
    ap = parser(__doc__.split("\n")[0], out_required=False,
                out_help="קובץ העבודה (docx), במקום שם לפי הכלל. לעולם לא הטיוטה שהתקבלה")
    ap.add_argument("--draft", required=True, help="הטיוטה שהתקבלה מהצד שכנגד")
    ap.add_argument("--decisions", required=True, help="decisions_round_<n>.json")
    ap.add_argument("--profile", help="פרופיל-לקוח.json: שם עורך הדין וראשי התיבות")
    ap.add_argument("--author", help="שם עורך הדין, כשאינו בפרופיל או בקובץ ההכרעות")
    ap.add_argument("--initials", help="ראשי התיבות לבועות")
    ap.add_argument("--report", help="דוח ההרצה (JSON)")
    ap.add_argument("--deal", help="תיקיית העסקה: שם הקובץ נגזר לפי הכלל")
    ap.add_argument("--agreement-type", help="סוג ההסכם, בשם המקוצר")
    ap.add_argument("--company", help="שם החברה המקוצר, בלי סיומת התאגדות")
    ap.add_argument("--round", type=int, help="מספר הסבב")
    ap.add_argument("--date", help="DD.MM.YYYY; בלעדיו: היום")
    a = ap.parse_args(argv)
    if bool(a.out) == bool(a.deal):
        print("יש לתת --deal עם סוג ההסכם, החברה והסבב (שם לפי הכלל), או --out מפורש, ולא את שניהם")
        return 2

    if not os.path.exists(a.draft):
        print("הטיוטה אינה קיימת: %s" % a.draft)
        return 2
    dec = load(a.decisions, "קובץ ההכרעות")
    profile = lawyer_view(load(a.profile, "הפרופיל") if a.profile else {})

    # שם עורך הדין: מהשורה, מקובץ ההכרעות, או מהפרופיל לפי שפת ההסכם
    # (lawyer_name_en בנייר באנגלית). בלעדיו אין מי שחותם על הבועות
    lang = gap_checks.detect_lang("\n".join(dt.received_paragraphs(a.draft)))
    author = a.author or dec.get("author")
    initials = a.initials or dec.get("initials")
    if not author and profile.get("lawyer_name"):
        author = qa_gate.author_for(profile, lang)
        initials = initials or qa_gate.initials_for(profile, lang)
    if not author:
        print("אין שם עורך דין: לא ב---author, לא בקובץ ההכרעות ולא בפרופיל (lawyer_name). "
              "שאלו מי חותם על ההערות לצד שכנגד, ושמרו בפרופיל.")
        return 2

    errors = dt.validate_decisions(dec)
    if errors:
        print("קובץ ההכרעות אינו עומד בחוזה, ולא נכתב קובץ (%d):" % len(errors))
        for e in errors:
            print("  - %s" % e)
        return 2

    send_path = None
    if a.deal:
        if not (a.agreement_type and a.round):
            print("עם --deal נדרשים --agreement-type ו---round")
            return 2
        date = a.date or _dt.date.today().strftime("%d.%m.%Y")
        try:
            names = paths.safe_out_paths(a.deal, a.agreement_type, a.company or "", a.round, date,
                                         lang=lang)
        except paths.PathTooLong as exc:
            print("הנתיב ארוך מדי גם אחרי קיצור: %s. קצרו את שם התיקייה." % exc)
            return 2
        os.makedirs(a.deal, exist_ok=True)
        a.out = paths.unique_path(names.work)
        send_path = paths.unique_path(names.send)
        produced_name = paths.unique_path(names.as_produced)
    expected_path, produced_path = side_paths(a.out)
    if a.deal:
        produced_path = produced_name
    try:
        out = guard_out(a.out, inputs=[a.draft, a.decisions])
        guard_out(expected_path, inputs=[a.draft, a.decisions])
        guard_out(produced_path, inputs=[a.draft, a.decisions], allow_existing_doc=True)
    except OutputRefused as exc:
        print("סירוב: %s" % exc)
        return 1

    res = dt.apply_decisions(a.draft, dec, out_path=out, author=author, initials=initials)
    if res.get("errors"):
        print("קובץ ההכרעות נדחה: %s" % "; ".join(res["errors"]))
        return 2
    with open(expected_path, "w", encoding="utf-8") as fh:
        json.dump(res["expected_accept"], fh, ensure_ascii=False, indent=1)
    shutil.copyfile(out, produced_path)

    marked = len(dec["decisions"]) - len(res["not_marked"])
    print("קובץ העבודה: %s" % out)
    print("  הכרעות: %d, סומנו: %d, לא סומנו: %d" % (len(dec["decisions"]), marked,
                                                     len(res["not_marked"])))
    for nm in res["not_marked"]:
        print("    לא סומנה %s: %s" % (nm["id"], nm["reason"]))
    for v in res["verify"]:
        print("  בדיקת הלוך ושוב: %s" % v)
    print("  נוסחי היעד לשער: %s" % expected_path)
    print("  העותק כפי שהופק: %s" % produced_path)
    if send_path:
        print("  העותק למשלוח (ל-qa_gate.py --send): %s" % send_path)
    if res["not_marked"]:
        print("הכרעה שלא סומנה לא הוחלה בכלל, ולא חלקית. מסור אותה למשתמש לטיפול ידני, "
              "ואל תסמן אותה בעצמך.")

    if a.report:
        try:
            rp = guard_out(a.report, inputs=[a.draft, a.decisions])
        except OutputRefused as exc:
            print("הדוח לא נכתב. סירוב: %s" % exc)
        else:
            with open(rp, "w", encoding="utf-8") as fh:
                json.dump({"work": out, "author": author, "lang": lang,
                           "decisions": len(dec["decisions"]), "not_marked": res["not_marked"],
                           "verify": res["verify"], "expected_accept": expected_path,
                           "as_produced": produced_path, "send": send_path},
                          fh, ensure_ascii=False, indent=2)
    return 0 if res["ok"] else 3


if __name__ == "__main__":
    sys.exit(main())
