#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""איתור הפלייבוק לעסקה, בסקריפט ולא בשיקול דעת.

`n1b-learning.md`, שלב א.2: אין פלייבוק בנתיב קבוע אחד. רכיב הפלייבוק שומר
פלייבוק נפרד לכל משפחת הסכמים ולכל פוזיציה, והאיתור צריך לדרג את
המועמדים, לפסול את מי שאינו מתאים למשפחה ולצד, ולהגיד במילים על מה
ההכרעה נשענת. מודל שעושה את זה בשיקול דעת בוחר אחרת בכל הרצה.

התוצאה נכתבת ל-`--out` ונכנסת לקובץ המצב בשדה `playbook_resolution`
(`n8-state-schema.md`). `source_label` הוא המשפט שמוצג
למשתמש, ואין לנסח אותו מחדש.

    python "AREO_RT/skills/contract-negotiation-orchestrator/scripts/resolve_playbook.py" --data Areo-נתונים \\
        --folder <תיקיית ההסכם> --family "<משפחה>" --role "<תפקיד>" \\
        --language he --out Areo-נתונים/transactions/<id>/playbook-resolution.json

המימוש ב-`areolegal/lib/orchestrator/resolve_playbook.py` (קוד הייחוס). הסקריפט הזה הוא העטיפה שלו בלבד, ואין בו שיקול דעת משל עצמו.
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # גם ב-python -I, שאינו מוסיף את תיקיית הסקריפט
import areo_lib  # noqa: F401  מוסיף את areolegal/lib לנתיב הייבוא

from common.cli import OutputRefused, guard_out, no_bytecode, parser  # noqa: E402
from orchestrator.resolve_playbook import resolve, role_code, role_side, source_label  # noqa: E402

SIDE_Q = {"he": "לפי ההסכם עצמו, אתם \"%s\", אבל ביקשתם לעבוד כ-\"%s\". מי אתם בהסכם הזה?",
          "en": "According to the agreement itself, you are \"%s\", but you asked us to work as \"%s\". "
                "Which side are you in this agreement?"}


def side_check(a, role, lang):
    """הצד שלנו מול המסמך עצמו (content_checks.document_sides), כמו ב-CLM: הצד אינו נלמד מהפלייבוק לבדו. מחזיר
    {document_side, requested_side, conflict, question} או None כשאין טיוטה לבדוק."""
    if not a.draft or not os.path.exists(a.draft):
        return None
    ours, theirs = list(a.company or []), list(a.counterparty or [])
    if a.profile and os.path.exists(a.profile):
        try:
            with open(a.profile, encoding="utf-8") as fh:
                prof = json.load(fh)
            ours += [prof.get("organization_name"), prof.get("organization_name_en")] + list(prof.get("aliases") or [])
        except (OSError, ValueError):
            pass
    import content_checks
    doc = content_checks.document_sides(a.draft, [x for x in ours if x], theirs, role_side)
    req = role_side(role)
    out = {"document_side": doc.get("ours"), "basis": doc.get("basis"), "term": doc.get("our_term") or doc.get("their_term"),
           "requested_side": req, "conflict": False, "compared": False}
    ds = doc.get("ours")
    same_script = bool(ds and req) and bool(re.search(r"[֐-׿]", ds)) == bool(re.search(r"[֐-׿]", req))
    if ds and req and "mutual" not in (ds, req) and same_script:
        out["compared"] = True
    if out["compared"] and ds != req:
        L = "en" if lang == "en" else "he"
        out["conflict"] = True
        out["question"] = {"key": "side_conflict", "kind": "side_conflict", "situation": 4, "blocks_sending": True,
                           "text": SIDE_Q[L] % (out["term"] or ds, role),
                           "options": [out["term"] or ds, role],
                           "recommendation": out["term"] or ds}
    return out


def _model_path(chosen):
    """playbook-model.json של הפלייבוק שנבחר: הקובץ עצמו, או בתיקייה שלו."""
    if not chosen:
        return None
    if os.path.basename(chosen) == "playbook-model.json" and os.path.exists(chosen):
        return chosen
    p = os.path.join(os.path.dirname(chosen) if os.path.isfile(chosen) else chosen, "playbook-model.json")
    return p if os.path.exists(p) else None


def playbook_validation(chosen):
    """{errors, codes, checker} של הפלייבוק שנבחר, או None כשאין מודל לבדוק. המאמת המשותף (playbook.validate_model)
    כשהוא זמין; אחרת בדיקה מינימלית מקומית: יש כללים, ולכל כלל מזהה ועמדה ירוקה."""
    path = _model_path(chosen)
    if not path:
        return None
    try:
        with open(path, encoding="utf-8") as fh:
            model = json.load(fh)
    except (OSError, ValueError) as exc:
        return {"errors": 1, "codes": ["MODEL_UNREADABLE"], "checker": "local", "message": str(exc)}
    try:
        from playbook import validate_model as VM
        found = VM.validate(model, check_wording=False)
        errs = VM.errors(found)
        codes = sorted({f.get("code") for f in errs})
        return {"errors": len(errs), "codes": codes, "checker": "playbook.validate_model"}
    except Exception:  # noqa: BLE001  המאמת המשותף חסר או נכשל: בדיקה מינימלית
        rules = model.get("rules") or []
        bad = [r.get("id") for r in rules if not r.get("id") or not (r.get("tracks") or {}).get("green")]
        codes = (["NO_RULES"] if not rules else []) + (["RULE_INCOMPLETE"] if bad else [])
        return {"errors": len(codes), "codes": codes, "checker": "local"}


def main(argv=None):
    no_bytecode()
    ap = parser(__doc__.split("\n")[0], out_required=False)
    ap.add_argument("--data", required=True, help="תיקיית Areo-נתונים של הלקוח")
    ap.add_argument("--folder", required=True, help="התיקייה שבה ההסכם שהגיע")
    ap.add_argument("--family", required=True, help="משפחת ההסכמים, כפי שהלקוח קורא לה")
    ap.add_argument("--role", required=True, help="הפוזיציה של החברה בהסכם")
    ap.add_argument("--language", required=True, help="שפת ההסכם: he / en")
    ap.add_argument("--counterparty-kind", default="company",
                    help="סוג הצד שכנגד: company, individual, public_body (גם גוף ממשלתי או רשות), npo או "
                         "partnership; כמה בפסיק. נבדק מול applicability של הפלייבוק (activation_ok)")
    ap.add_argument("--uploaded", help="פלייבוק שהלקוח העלה בעצמו, כשיש")
    ap.add_argument("--min-skill-version",
                    help="גרסת סקיל מינימלית: פלייבוק שנבנה לפניה מסומן כישן")
    ap.add_argument("--family-label", help="שם המשפחה כפי שהוא בהסכם, כשהוא שונה")
    ap.add_argument("--answer-kind", help="explicit כשהמשתמש בחר במפורש, לשורת המקור")
    ap.add_argument("--lang", choices=("he", "en"), default="he", help="שפת שורת המקור (שפת התוצר)")
    ap.add_argument("--draft", help="הטיוטה שהתקבלה (docx): הצד שלנו נבדק מול הגדרות הצדדים בהסכם עצמו")
    ap.add_argument("--profile", help="פרופיל-לקוח.json: שמות החברה, לזיהוי הצד שלנו בהסכם")
    ap.add_argument("--company", action="append", help="שם נוסף של החברה כפי שהוא בהסכם")
    ap.add_argument("--counterparty", action="append", help="שם הצד השני כפי שהוא בהסכם")
    a = ap.parse_args(argv)

    # ביקורת כלליות, ממצאים 1 ו-4: השם עובר לספרייה כמו שהוא (קוד, שם או כינוי, בעברית או באנגלית), והיא
    # משווה אותו קודם לפלייבוקים הקיימים. שם שאינו מוכר אינו עצירה: התוצאה no_match או "לבחירה". רק ארגומנט
    # ריק הוא עצירה, כי אין מה לחפש
    if not (a.family or "").strip():
        print("חסרה משפחת ההסכם (--family). השלימו אותה מתוכן ההסכם, בעברית או באנגלית.")
        return 2
    if not (a.role or "").strip():
        print("חסרה הפוזיציה של החברה (--role). השלימו אותה בשער הפוזיציה.")
        return 2
    # תפקיד שאינו במילון, ו-other, עוברים כמו שהם: הספרייה אינה מתאימה אותם אוטומטית ומחזירה "לבחירה"
    role = role_code(a.role) or a.role.strip()

    res = resolve(a.data, a.folder, a.family.strip(), role, a.language,
                  counterparty_kind=a.counterparty_kind, uploaded=a.uploaded,
                  min_skill_version=a.min_skill_version,
                  agreement_family_label=a.family_label)
    # פלייבוק במעמד Draft או "מוצע": "מפלייבוק מוצע" (באג 7)
    res["source_label"] = source_label(res, activation_answer_kind=a.answer_kind, lang=a.lang)

    fam = res.get("requested_family") or {}
    print("משפחה: %s (%s)   פוזיציה: %s"
          % (a.family.strip(), ", ".join(fam.get("families") or ["לא במילון"]), role))
    print("תוצאה: %s" % res.get("result", "-"))
    if res.get("chosen"):
        print("נבחר : %s" % res["chosen"])
    if res.get("reason"):
        print("סיבה : %s" % res["reason"])
    if res.get("choices"):
        print("לבחירה: %s" % ", ".join(res["choices"]))
    print("מועמדים: %d" % len(res.get("candidates") or []))
    unread = [c["path"] for c in res.get("candidates") or [] if c.get("unread")]
    if unread:
        print("לא נקראו (לקריאה ב-AREO_RT/skills/contract-negotiation-orchestrator/scripts/read_playbook_doc.py): %s" % ", ".join(unread))
    print("שורת המקור: %s" % res.get("source_label", ""))
    # מעמד הפלייבוק: התווית של שער המדיניות (status.gate_status). פער מול הגרעין או האינדקס: מציגים את התווית של
    # השער, ומציעים לבנות מחדש את הגרעין ברכיב הפלייבוק (ממצא 1, הרצה S1c)
    if res.get("activation_ok") is not None:
        print("תנאי ההפעלה: %s" % ("מתקיימים" if res["activation_ok"] else "אינם מתקיימים: %s. שאלה אחת במנת השאלות "
                                   "(מצב 4)" % res.get("activation_reason", "")))
    if res.get("status_label"):
        print("מעמד הפלייבוק (שער המדיניות): %s" % res["status_label"])
    if res.get("label_mismatch"):
        print("פער תוויות: %s אומרים תווית אחרת. מציגים את התווית של שער המדיניות, ומציעים לבנות מחדש את הגרעין "
              "ברכיב הפלייבוק" % ", ".join(res["label_mismatch"]))
    # פלייבוק שאינו עובר את המאמת: אזהרה, ולא עבודה שקטה איתו
    pv = playbook_validation(res.get("chosen"))
    if pv:
        res["playbook_validation"] = pv
        if pv.get("errors"):
            print("אזהרה: הפלייבוק שנבחר אינו עובר את הבדיקה של סוכן הפלייבוק (%d ממצאים חוסמים: %s). הוא משמש בעסקה "
                  "הזו, ובשורה הראשונה של ההודעה נאמר: \"המדיניות שבה השתמשנו צריכה תיקון אצל סוכן הפלייבוק.\" "
                  "(EN: \"The policy we used needs fixing with the playbook agent.\")"
                  % (pv["errors"], ", ".join(pv["codes"][:5])))
    sc = side_check(a, role, a.lang)
    if sc is not None:
        res["side_check"] = sc
        if sc["conflict"]:
            # הצד שבהסכם סותר את הצד שביקשו: לא ממשיכים לפי הפלייבוק עד תשובה (שאלה אחת, ראשונה במנה)
            print("סתירה בצד: %s" % sc["question"]["text"])
        elif sc["document_side"]:
            print("הצד שלנו לפי ההסכם תואם את הפוזיציה (%s)" % sc["document_side"])
        else:
            print("ההסכם אינו מכריע את הצד שלנו (%s): הפוזיציה כפי שנמסרה" % sc["basis"])
    notice = res.get("proposed_notice") or {}
    if notice:
        # המשפט המתוסרט על פלייבוק מוצע, כפי שהוא, בשפת הממשק (ממצא 5)
        print("המשפט על פלייבוק מוצע: %s" % notice.get("en" if a.lang == "en" else "he", ""))

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
