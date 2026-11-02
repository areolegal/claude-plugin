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

**ארבעה דברים שהקליטה אינה עושה בשתיקה.** עמודה שנחתמה בשם תפקיד ולא
בשם אדם אינה נקלטת; עמדה טעונת בדיקה משפטית אינה מאושרת בלי מי בדק ומתי;
תא שנשארו בו סוגריים של ערך שלא נקבע ("[מכפיל]", "[number] hours") אינו
מאושר עד שהערך נכתב במקומם; וקליטה בלי ראיה (`--upload-ref`) נרשמת
כ-`simulated`, ואינה פותחת את שער המדיניות. כל אחד מאלה מודפס, ואינו מרוכך.

    python3 scripts/ingest_approval.py --signed "<הגיליון החתום>.docx" \\
        --manifest "<approval-sheet-manifest.json>" \\
        --model playbook-model.json --core playbook-core.json \\
        --index Areo-נתונים/playbooks/index.json \\
        --records "Areo-נתונים/אישורים" \\
        --received-via user_upload \\
        --upload-ref "<הקובץ בתיקיית ההעלאות>"

**אישור בצ'אט במנות ("אישור פלייבוק").** אותו סקריפט, אותן רשומות ואותו
מעמד, בלי גיליון Word:

    # המנה הבאה בתור (עד 8 עמדות), כטקסט מוכן לצ'אט
    python3 scripts/ingest_approval.py --queue --model playbook-model.json \\
        --records "Areo-נתונים/אישורים" [--stage batch|decisions|questions|topics] \\
        [--lang he|en] [--revisit-skipped]
    # התשובה של המאשר, מילה במילה, מול המנה הפתוחה
    python3 scripts/ingest_approval.py --answer "<התשובה כלשונה>" \\
        --approver "<שם מלא>" --role "<תפקיד>" --model playbook-model.json \\
        --core playbook-core.json --index Areo-נתונים/playbooks/index.json \\
        --records "Areo-נתונים/אישורים" [--word ... --workspace ...]
    # "עדכון פלייבוק מעסקה": הצעות עדכון מקובץ המצב של עסקה, לאותו תור
    python3 scripts/ingest_approval.py --queue --from-deal \\
        "Areo-נתונים/transactions/<deal>/negotiation_state.json" \\
        --model playbook-model.json --records "Areo-נתונים/אישורים"
    # המעמד והתקדמות האישור, בלי לכתוב דבר
    python3 scripts/ingest_approval.py --status --model playbook-model.json

קודי יציאה בתור: 0 תקין; 2 קלט חסר; 3 התשובה לא נקלטה (לא מובנת, אין מנה
פתוחה, המאשר אינו שם מלא של אדם), ושום דבר לא נכתב; 4 סתירה בין השכבות.
כשתשובה שינתה נוסח (ערך של החלטת הנהלה, "לשנות", עדכון מעסקה), הגרסה
הקודמת נשמרת קודם ב-`keep_version.py`, ואחרי הקליטה בונים מחדש את הגרעין,
הרישום, ה-Word וסביבת העבודה (SKILL.md, "בדיקות החובה").

המימוש ב-`areolegal/lib/playbook/ingest_approval.py`, `playbook/status.py`
ו-`playbook/after_ingest.py`. ההחלטה מה נספר כמאושר
היא שלהם, ולא של הסקריפט הזה ולא של המודל שמריץ אותו.
"""
import io
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # גם ב-python -I, שאינו מוסיף את תיקיית הסקריפט
import areo_lib  # noqa: F401  מוסיף את areolegal/lib לנתיב הייבוא

from common.cli import OutputRefused, guard_out, no_bytecode, parser  # noqa: E402
from playbook import after_ingest, ingest_approval  # noqa: E402
from playbook import status as S  # noqa: E402
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


def index_entry_of(index, model, core=None):
    """הרשומה של הפלייבוק הזה ב-playbooks/index.json, לפי המשפחה והצד. הצד נקרא גם מהגרעין ומ-
    scope_summary.contract_families, כמו ב-register_playbook.py: במודל שאין בו company_role_code בשורש הרשומה לא נמצאה, והמעמד לא נכתב לאינדקס."""
    if not index:
        return None, None
    entries = index.get("playbooks") if isinstance(index, dict) else index
    if not isinstance(entries, list):
        return None, None
    core = core or {}
    fams = (model.get("scope_summary") or {}).get("contract_families") or [{}]
    fam = model.get("family_code") or model.get("family_id") or core.get("family_code")
    role = (model.get("company_role_code") or core.get("company_role_code")
            or fams[0].get("company_role_code") or model.get("company_role"))
    hits = [e for e in entries if isinstance(e, dict)
            and (e.get("family_code") or e.get("family_id")) == fam and e.get("company_role_code") == role]
    # רשומת legacy (פלייבוק במבנה הישן בשורש) אינה מוחתמת כשיש רשומה של תיקיית הסוג לאותו סוג וצד;
    # היא נבחרת רק כשהיא הרשומה היחידה, כלומר כשמאשרים את הפלייבוק הישן עצמו
    for e in [h for h in hits if not h.get("legacy")] or hits:
        return e, entries
    return None, entries


HERE = os.path.dirname(os.path.abspath(__file__))
RECORDS_LINE = "רשומה : %s"
# שורת מצב התור, בשפת התור ובלי מונחים פנימיים (areo-voice.md)
QUEUE_LINE = {"he": "מחכים לכם: %d עמדות לאישור במנה, %d מספרים לקבוע, %d שאלות, %d נושאים לעבור עליהם אחד אחד, "
                    "ועוד %d עמדות שמחכות לקביעת מספר.",
              "en": "Waiting for you: %d positions to approve in a batch, %d numbers to set, %d questions, %d topics to "
                    "go through one by one, and %d more positions waiting for a number."}


def _lang(a, model):
    """שפת הממשק של התור: --lang, ואז display_language מהפרופיל, ואז שפת הפלייבוק."""
    if a.lang:
        return S.norm_lang(a.lang) or "he"
    if a.profile and os.path.exists(a.profile):
        prof = load(a.profile, "הפרופיל")
        got = S.norm_lang(prof.get("display_language"))
        if got:
            return got
    return S.model_lang(model)


def _deal_states(paths):
    """קובצי המצב של העסקאות: קובץ negotiation_state.json, או תיקייה שנסרקת (בלי versions/)."""
    files = []
    for p in paths or ():
        if os.path.isdir(p):
            for root, dirs, names in os.walk(p):
                dirs[:] = [d for d in dirs if d != "versions"]
                if "negotiation_state.json" in names:
                    files.append(os.path.join(root, "negotiation_state.json"))
        elif os.path.exists(p):
            files.append(p)
    return [load(f, "קובץ המצב") for f in sorted(files)]


def _changes_wording(batch, answers):
    """האם התשובה תשנה נוסח במודל: לשנות, ערך של החלטת הנהלה, או עדכון מעסקה שאושר."""
    for it in batch["items"]:
        act = (answers.get(it["n"]) or {}).get("action")
        if act == "change" or (it["kind"] == "update" and act == "approve"):
            return True
    return False


def _keep_version(model_path):
    """הגרסה הקיימת נשמרת ב-versions/ לפני שתשובה משנה נוסח (workflow.md, שלב 13, סעיף 1)."""
    res = subprocess.run([sys.executable, "-B", os.path.join(HERE, "keep_version.py"),
                          os.path.dirname(os.path.abspath(model_path))],
                         capture_output=True, text=True, encoding="utf-8", errors="replace")
    line = (res.stdout or res.stderr or "").strip().splitlines()
    if line:
        print(line[0])


def playbooks_folder_from_profile(profile_path):
    """תיקיית הפלייבוקים שהלקוח קבע: connections.playbooks_folder בפרופיל המקומי; בלעדיה תיקיית 'פלייבוקים' בתוך
    התיקייה שחיבר (connections.shared_output_folder); בלי שתיהן None (ואז after_ingest נופל לתיקיית הבית). שום דבר אינו נשלח לשרת."""
    if not profile_path or not os.path.exists(profile_path):
        return None
    try:
        with open(profile_path, encoding="utf-8") as fh:
            conn = (json.load(fh) or {}).get("connections") or {}
    except (OSError, ValueError):
        return None
    if conn.get("playbooks_folder"):
        return str(conn["playbooks_folder"])
    if conn.get("shared_output_folder"):
        return os.path.join(str(conn["shared_output_folder"]), "פלייבוקים")
    return None


def _local_copy(a, model, out):
    """כלל מייסד 6: אחרי הקליטה הפלייבוק נשמר גם בעותק מקומי במחשב של הלקוח, לצד התיקייה שחיבר. שום דבר אינו נשלח
    לשרת של Areo. כשהעותק לא נכתב, אומרים זאת."""
    base = getattr(a, "local_copy_dir", None) or playbooks_folder_from_profile(getattr(a, "profile", None))
    res = after_ingest.save_local_copy([a.model, a.core, (out or {}).get("word") or a.word,
                                        (out or {}).get("workspace") or a.workspace],
                                       model.get("family_id") or model.get("playbook_id"),
                                       base)
    if res["copied"]:
        print("עותק מקומי: %s (%d קבצים)" % (res["dir"], len(res["copied"])))
    for e in res["errors"]:
        print("עותק מקומי לא נשמר: %s" % e)
    return res


def chat_main(a):
    """תור האישור בצ'אט: --status, --queue (כולל --from-deal) ו---answer."""
    if not os.path.exists(a.model):
        print("המודל אינו קיים: %s" % a.model)
        return 2
    model = load(a.model, "המודל")
    lang = _lang(a, model)
    T = ingest_approval.Q[lang]
    cells = S.record_cells_for(model, a.model)
    if a.status:
        st = S.derive_status(model, cells, lang=lang)
        qf = ingest_approval.load_queue(a.records, model) if a.records else {}
        qs = ingest_approval.queue_state(model, cells, lang, a.revisit_skipped, qf.get("demoted") or [],
                                         qf.get("skipped") or [])
        print(st["label"])
        print(S.progress_line(st, lang))
        print(QUEUE_LINE[lang] % (len(qs["batch"]), len(qs["decisions"]), len(qs["questions"]), len(qs["topics"]),
                                  qs["waiting"]))
        return 0
    if not a.records:
        print("--records חובה בתור האישור: שם נשמרים המנה והרשומות")
        return 2
    queue = ingest_approval.load_queue(a.records, model)

    if a.queue:
        notes = []
        if a.from_deal:
            states = _deal_states(a.from_deal)
            if not states:
                print("לא נמצא קובץ מצב של עסקה: %s" % ", ".join(a.from_deal))
                return 2
            batch, notes = ingest_approval.deal_updates(states, model, lang)
        else:
            batch = ingest_approval.make_batch(model, cells, lang, a.stage, a.revisit_skipped,
                                               queue.get("demoted") or [], queue.get("skipped") or [])
        st = S.derive_status(model, cells, lang=lang)
        print(st["label"])
        print(S.progress_line(st, lang))
        if batch is None:
            print(T["empty"])
        else:
            batch = ingest_approval.issue_batch(queue, batch, lang, a.today)
            ingest_approval.save_queue(a.records, model, queue)
            print()
            print(ingest_approval.render_batch(batch, model, lang))
        for n in notes:
            print(n)
        return 0

    batch = ingest_approval.open_batch(queue)
    if not batch:
        print("אין מנה פתוחה בתור. הפיקו מנה ב---queue, והציגו אותה, לפני שקולטים תשובה.")
        return 3
    try:
        answers = ingest_approval.parse_reply(a.answer, batch)
        if not ingest_approval._is_person_name(a.approver or ""):
            raise ingest_approval.ReplyError('"%s" אינו שם מלא של אדם (--approver). כל תשובה נרשמת בשם המאשר'
                                             % (a.approver or ""))
    except ingest_approval.ReplyError as exc:
        print("התשובה לא נקלטה, ושום דבר לא נכתב: %s" % exc)
        return 3
    core = load(a.core, "הגרעין") if a.core else None
    index = load(a.index, "האינדקס") if a.index else None
    entry, entries = index_entry_of(index, model, core)
    if a.index and entry is None:
        print("אזהרה: אין ב-%s רשומה למשפחה ולצד של המודל, ולכן המעמד לא ייכתב לאינדקס." % a.index)
    if _changes_wording(batch, answers):
        _keep_version(a.model)
    try:
        res = ingest_approval.apply_answers(model, batch, answers, a.approver, a.role, a.answer, a.today,
                                            cells, lang)
    except ingest_approval.ReplyError as exc:
        print("התשובה לא נקלטה, ושום דבר לא נכתב: %s" % exc)
        return 3
    prior = (S._latest_record(model) or {}).get("record_id")
    path = ingest_approval.save_chat_record(a.records, res, supersedes=prior)
    try:
        rel = os.path.relpath(os.path.abspath(path), os.path.dirname(os.path.abspath(a.model)))
    except ValueError:   # כונן אחר ב-Windows
        rel = os.path.abspath(path)
    changed = res["wording_changed"]
    out = after_ingest.apply_ingest(model, core, entry, res, rel,
                                    word_path=None if changed else a.word,
                                    workspace_path=None if changed else a.workspace)
    save(a.model, model)
    if a.core:
        save(a.core, core)
    if a.index and entry is not None:
        save(a.index, index if isinstance(index, dict) else entries)
    batch.update(status="answered", record_id=os.path.splitext(os.path.basename(path))[0],
                 answered_by=a.approver)
    # החלטה ושאלה שדולגו אינן חוזרות במנה הבאה (תא שדולג נשמר ברשומה עצמה, status: skipped)
    queue.setdefault("skipped", []).extend(k for k in res["record"].get("skipped") or () if ":" in k)
    if batch["stage"] == "batch":
        queue.setdefault("demoted", []).extend(
            it["key"] for it in batch["items"] if (answers.get(it["n"]) or {}).get("action") == "except")
    ingest_approval.save_queue(a.records, model, queue)
    _local_copy(a, model, out)

    sm, st = res["summary"], out["status"]
    print(ingest_approval.summary_line(sm, lang))
    print(S.label_for(st, lang))
    print(S.progress_line(st, lang))
    for w in res["warnings"]:
        print("  %s %s" % ("Note:" if lang == "en" else "שימו לב:", w))
    if out.get("closed"):
        print("%s %s" % ("Answered questions:" if lang == "en" else "שאלות שנענו:", ", ".join(out["closed"])))
    print(RECORDS_LINE % path)
    if changed:
        print("הנוסח השתנה בפלייבוק (גרסה %s). יש לבנות מחדש את הגרעין, הרישום, ה-Word וסביבת העבודה "
              "(SKILL.md, \"בדיקות החובה\"), ורק אז להמשיך." % model.get("version"))
    for p in out.get("problems") or ():
        print("  סתירה בין השכבות: %s" % p)
    return 4 if out.get("problems") else 0


def main(argv=None):
    no_bytecode()
    ap = parser(__doc__.split("\n")[0], out_required=False,
                out_help="דוח הקליטה (JSON). הקבצים עצמם מתעדכנים בכל מקרה")
    ap.add_argument("--signed", help="הגיליון החתום שחזר. חובה בקליטת גיליון")
    ap.add_argument("--manifest", help="המניפסט של אותה הפקה. חובה בקליטת גיליון")
    ap.add_argument("--model", required=True, help="playbook-model.json")
    ap.add_argument("--core", help="playbook-core.json")
    ap.add_argument("--index", help="playbooks/index.json")
    ap.add_argument("--records", help="תיקיית רשומות האישור. חובה בקליטת גיליון ובתור")
    ap.add_argument("--local-copy-dir", help="תיקיית הבסיס של העותק המקומי (ברירת מחדל: Areo-playbooks-local בתיקיית הבית)")
    # תור האישור בצ'אט
    ap.add_argument("--queue", action="store_true", help="מפיק את המנה הבאה בתור האישור")
    ap.add_argument("--answer", help="התשובה של המאשר למנה הפתוחה, מילה במילה")
    ap.add_argument("--status", action="store_true", help="המעמד והתקדמות האישור, בלי לכתוב")
    ap.add_argument("--stage", choices=ingest_approval.STAGES, help="שלב מסוים בתור")
    ap.add_argument("--from-deal", action="append", help="קובץ המצב של עסקה, או תיקיית transactions")
    ap.add_argument("--approver", help="השם המלא של המאשר")
    ap.add_argument("--role", help="התפקיד של המאשר")
    ap.add_argument("--lang", help="שפת הממשק של התור: he או en")
    ap.add_argument("--profile", help="פרופיל-לקוח.json, לשפת הממשק")
    ap.add_argument("--revisit-skipped", action="store_true", help="גם עמדות שדולגו")
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

    if a.queue or a.status or a.answer is not None:
        return chat_main(a)
    if not (a.signed and a.manifest and a.records):
        print("קליטת גיליון: --signed, --manifest ו---records חובה. לאישור בצ'אט: --queue או --answer")
        return 2
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
    entry, entries = index_entry_of(index, model, core)
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

    # מה שכבר אושר בצ'אט על אותו נוסח אינו נמחק בגלל עמודה שלא נחתמה בגיליון
    carried = ingest_approval.merge_prior(res, S.record_cells_for(model, a.model))
    if carried:
        print("נשמרו %d עמדות שאושרו קודם בצ'אט, על אותו נוסח, בעמודות שלא נחתמו בגיליון." % carried)
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
    _local_copy(a, model, out)
    print("מעמד  : %s" % st.get("playbook_status"))
    print("תווית : %s" % st.get("label"))
    cells = res["cells"]
    approved = sum(1 for v in cells.values() if v.get("status") == "approved")
    print("תאים  : %d מאושרים מתוך %d" % (approved, len(cells)))
    # סוגריים של ערך שלא נקבע ("[מכפיל]") שנשארו בתא חתום: התא אינו נספר כמאושר
    unset = sorted(k for k, v in cells.items() if (v.get("reason") or "").startswith("נשאר ערך שלא נקבע"))
    if unset:
        print("חסר ערך: %d תאים עם סוגריים של ערך שלא נקבע (דף \"החלטות הנהלה\"): %s"
              % (len(unset), ", ".join(unset)))
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
