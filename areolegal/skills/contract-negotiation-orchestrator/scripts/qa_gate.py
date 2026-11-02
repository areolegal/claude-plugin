#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""שער האיכות: הבדיקה שאין דליפה פנימית, ובניית העותק למשלוח.

`external_comments_guide.md`, "היחס לתיעוד הפנימי": **הבדיקה שאין דליפה
אינה נעשית בעין. שער האיכות האוטומטי סורק את טקסט כל הבועות החיצוניות
ואת כל חלקי הקובץ, וכל מילה מהרשימה האסורה עוצרת את המסירה.** אין לכתוב
למשתמש שאין דליפה, אלא את תוצאת השער כפי שהיא.

שני מצבים, והם אינם אותו דבר:

* `--mode work` - בודק את קובץ העבודה. הכותרת הפנימית **חייבת** להיות בו,
  ובועה פנימית בו היא תקינה. זהו הקובץ שנשאר אצל עורך הדין.
* `--mode send` - גוזר עותק בלי השכבה הפנימית, מריץ עליו את השער, ו**משנה
  את שמו לשם הסופי רק כשהוא עובר**. כשהוא נכשל, הקובץ הזמני נמחק ואין
  בתיקייה קובץ "למשלוח" כלל, ועותק "למשלוח" ישן שנמצא בנתיב מקבל את
  הסיומת " - לא למשלוח". כך אין מצב שבו קובץ שנכשל בשער יושב בתיקייה
  ומחכה שמישהו ישלח אותו בטעות. **קובץ קיים אינו נדרס** (`n6-gate-and-send.md`,
  "אין דריסה"): כשהנתיב תפוס, העותק החדש מקבל " (2)", ואם השער נכשל,
  העותק הקודם הוא שמקבל " - לא למשלוח".

קוד היציאה הוא חלק מהתשובה: **0** עבר, **3** נכשל בשער (וזו תשובה, לא
תקלה), **2** קלט חסר או שאינו קריא, **1** נתיב פלט שסורב.

    python "AREO_RT/skills/contract-negotiation-orchestrator/scripts/qa_gate.py" --mode send \\
        --work "<קובץ העבודה>.docx" --received "<הטיוטה שהתקבלה>.docx" \\
        --send "<העותק למשלוח>.docx" --profile "Areo-נתונים/פרופיל-לקוח.json" \\
        --deal "Areo-נתונים/transactions/<id>" --out <דוח>.json

**קובץ המצב והפלייבוק:** עם `--deal` ובלי `--state`, קובץ המצב נקרא מ-
`<תיקיית העסקה>/negotiation_state.json`. "טעון בדיקה משפטית" נגזר מקובץ המצב, מקובץ ההכרעות ומהפלייבוק:
`--core`, ובלעדיו הגרעין שקובץ המצב רושם (`playbook_resolution.chosen`, יחסית ל-Areo-נתונים). **במצב משלוח קובץ
מצב חסר או בלי סעיפים הוא כשל (STATE_NO_CLAUSES)**: `negotiation_state.py write` רץ לפני השער.

**כיסוי כללי הפלייבוק והמאמת העצמאי (n4d-rule-coverage.md, n9-verify.md).** עם הכרעות וגרעין, השער קורא את
`<תיקיית העסקה>/rule-coverage.json` (או `--coverage`) ומריץ את `playbook_map.check_coverage`: במצב משלוח הקודים
RULE_COVERAGE_PLAN_MISSING, RULE_PLANNED_NOT_RESOLVED, RULE_APPLIED_BY_COMMENT_ONLY, RULE_PARTIAL_MARKED_FULL,
EQUIVALENCE_MISSING, OPENING_DEPARTURE_UNEXPLAINED, POSITION_BASIS_MISSING ו-BASIS_APPROVAL_UNSUPPORTED חוסמים;
במצב עבודה הם אזהרה. המאמת העצמאי הוא תנאי להשלמה: במצב משלוח קובץ ממצאים חסר (VERIFY_MISSING) או שאינו במבנה
(VERIFY_SCHEMA) חוסם, וכל ממצא `open` (VERIFY_OPEN) חוסם אלא אם בקובץ ההכרעות יש `verify_resolutions[]` תקין:
`{"check", "where", "resolution": "fixed:<מזהה הכרעה>" | "accepted_by_lawyer", "note"}`. במצב עבודה הכול אזהרה.

**הדוח בשם קנוני:** עם `--deal` ובלי `--out`, הדוח נכתב ל-`<תיקיית העסקה>/runs/round-<N>/gate-work.json`
או `gate-send.json` (N: הסבב בקובץ ההכרעות או בקובץ המצב). הרצה חוזרת מחליפה את הקובץ, והדוח הקודם עובר ל-`history`
שבאותה תיקייה, במקום gate-work-2, gate-work-3. `--out` מפורש נשאר כמו שהוא.

**עותק שהוסר נרשם בקובץ המצב:** כשהשער במצב משלוח נכשל ועותק "למשלוח" קודם קיבל " - לא למשלוח", קובץ המצב של
העסקה (`--state`, או `<תיקיית העסקה>/negotiation_state.json`) נשמר מיד: `quality_gate.send_copy` מתאפס, ונפתח פריט
שחוסם משלוח. המרשם של מעריך הסיכונים אינו נקרא ואינו חוסם (`--register` נשאר לתאימות, ואינו בשימוש).

**הפקה מחדש באותה ריצה** (`--run-id`, אותו מזהה כמו ב-`apply_redlines.py`): עותק למשלוח שהשער הזה הפיק באותה
ריצה, ושלא נמסר ולא נשלח, מוחלף ואינו מקבל " (2)" (`orchestrator/pre_send.reusable_path`).

המימוש ב-`areolegal/lib/orchestrator/qa_gate.py` (קוד הייחוס).
רשימת המילים האסורות, קודי הכשל והניסוחים הם שלו, והסקריפט הזה אינו
מנסח אותם מחדש ואינו מוסיף להם שיקול דעת.
"""
import json
import re
import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # גם ב-python -I, שאינו מוסיף את תיקיית הסקריפט
import areo_lib  # noqa: F401  מוסיף את areolegal/lib לנתיב הייבוא

from common.cli import OutputRefused, guard_out, load_docx_or_explain, no_bytecode, parser  # noqa: E402
from common import docx_tracked, paths  # noqa: E402
from orchestrator import pre_send, qa_gate  # noqa: E402
from lawyer import lawyer_view  # noqa: E402
import content_checks  # noqa: E402
import playbook_map  # noqa: E402


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


def playbook_of(state, deal):
    """הגרעין שקובץ המצב רושם (playbook_resolution.chosen, או positions_source.document), יחסית ל-Areo-נתונים
    (שתי רמות מעל תיקיית העסקה). None כשאין או כשאינו קריא: אז "טעון בדיקה משפטית" נגזר מקובץ המצב ומההכרעות."""
    if not (state and deal):
        return None
    rel = ((state.get("playbook_resolution") or {}).get("chosen")
           or (state.get("positions_source") or {}).get("document") or "")
    if not rel or not str(rel).endswith(".json"):
        return None
    data = os.path.dirname(os.path.dirname(os.path.abspath(deal)))
    p = rel if os.path.isabs(rel) else os.path.join(data, str(rel).replace("\\", "/"))
    try:
        with open(p, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return None


# קודים שחוסמים רק את המשלוח: במצב עבודה הם אזהרה, ולכן הם מוצגים כבר בבדיקה הראשונה כשאלה אחת לכל קבוצה, ולא
# מתגלים רק בשלב המשלוח. כל קבוצה היא שאלה אחת, עם כל הסעיפים שלה. אין כאן קבוצה של אישור עורך דין (כלל יסוד 6:
# עורך דין מאשר את הפלייבוק בלבד). מה שהוא החלטה של הלקוח עצמו, כמו סעיף ציות או ויתור על קו אדום, נשאל פעם אחת
PRE_SEND_GROUPS = (
    (("COMPLIANCE", "CONTAIN_CONCESSION_UNDECIDED"), "explicit_group",
     "%d סעיפים צריכים את ההכרעה שלכם לפני שליחה (%s).",
     "%d clauses need your decision before sending (%s).",
     ["לאשר את ההמלצה בכולם", "לעבור עליהם אחד אחד"], ["Approve the recommendation for all", "Go through them one by one"]),
)


def coverage_for_gate(a, decisions, core, state, mode):
    """בדיקות כיסוי הכללים (playbook_map.check_coverage) על תוכנית הכיסוי של העסקה. בלי הכרעות או בלי כללים בגרעין:
    אין מה לבדוק. הממצאים {code, message, where, blocking}; במצב work הכול אזהרה."""
    if decisions is None or not playbook_map.rules_of(core):
        return []
    path = getattr(a, "coverage", None) or (os.path.join(a.deal, playbook_map.COVERAGE_FILE) if a.deal else None)
    plan = None
    if path and os.path.exists(path):
        try:
            with open(path, encoding="utf-8") as fh:
                plan = json.load(fh)
        except (OSError, ValueError):
            plan = {"rules": "לא קריא"}   # קובץ שאינו JSON: RULE_COVERAGE_PLAN_INCOMPLETE, ולא היעדר תוכנית
    return playbook_map.check_coverage(plan, core, decisions, state, mode, a.work)


def pre_send_preview(a, profile, state, expected, decisions, core, core_given, lawyer):
    """במצב עבודה: מה יחסום את המשלוח, עכשיו. בדיקות התוכן במצב משלוח, והשער על עותק זמני בלי השכבה הפנימית (נמחק
    מיד). מחזיר רשימת כשלים (code, message, where), בלי כפילויות."""
    found = []
    if decisions is not None:
        found += [f for f in content_checks.run_checks(
            a.work, a.received, decisions.get("decisions", []) if isinstance(decisions, dict) else decisions,
            state=state, core=core_given, manifest=load(a.manifest, "המניפסט", required=False),
            profile={"lawyer_names": lawyer}, mode="send") if f["blocking"]]
        found += [f for f in coverage_for_gate(a, decisions, core, state, "send") if f["blocking"]]
        found += [f for f in verifier_findings(getattr(a, "verify_findings", None), "send", decisions, a.work) if f["blocking"]]
    tmpdir = tempfile.mkdtemp(prefix="areo-pre-")
    try:
        tmp = os.path.join(tmpdir, "send-check.docx")
        docx_tracked.strip_internal(a.work, tmp)
        found += qa_gate.run_gate(tmp, a.received, "send", profile, state=state, expected_accept=expected,
                                  decisions=decisions, lang=a.lang, core=core, deal_dir=a.deal)["failures"]
    except Exception as exc:  # noqa: BLE001  התצוגה המקדימה אינה מפילה את בדיקת קובץ העבודה
        print("הערה: התצוגה המקדימה של בדיקת המשלוח לא רצה (%s)" % exc)
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)
    out, seen = [], set()
    for f in found:
        k = (f.get("code"), str(f.get("where")))
        if k not in seen:
            seen.add(k)
            out.append({"code": f.get("code"), "message": f.get("message"), "where": f.get("where")})
    return out


def pre_send_items(pre, state, lang, received_labels=None):
    """פריטי שאלה למנה, אחד לכל קבוצה (PRE_SEND_GROUPS), עם מספרי הסעיפים בהסכם. clause_ids: מזהי ההכרעות, ל-decide
    --applies-to. מה שאינו בקבוצה נשאר ברשימה הפנימית בלבד."""
    nm = (state or {}).get("numbering_map") or {}
    en = lang == "en"
    items = []
    for codes, key, he, en_t, he_o, en_o in PRE_SEND_GROUPS:
        hits = [f for f in pre if f["code"] in codes]
        if not hits:
            continue
        ids, refs, paras = [], [], []
        word = "Clause %s" if en else "סעיף %s"
        for f in hits:
            for w in str(f.get("where") or "").split(","):
                w = w.strip()
                m = re.match(r"para (\d+)$", w)
                if m:
                    # פסקה בלי הכרעה: מספר הסעיף בטיוטה שהתקבלה
                    k = int(m.group(1))
                    lab = (received_labels or [None] * (k + 1))[k] if received_labels and k < len(received_labels) else None
                    paras.append(k)
                    if lab and (word % lab) not in refs:
                        refs.append(word % lab)
                elif w and w not in ids:
                    ids.append(w)
                    r = nm.get(w)
                    if r and r not in refs:
                        refs.append(r)
        n = max(len(ids) + len(paras), 1)
        items.append({"key": "pre_send:" + key, "kind": "pre_send", "situation": 3, "blocks_sending": True,
                      "text": ((en_t if en else he) % (n, ", ".join(refs) or "-")).replace(
                          "1 סעיפים", "סעיף אחד").replace("1 clauses", "One clause"),
                      "options": list(en_o if en else he_o), "recommendation": (en_o if en else he_o)[0],
                      "clause_ids": ids, "paras": paras})
    return items


def accepted_fingerprint(work):
    """sha256 של הנוסח המתקבל ("קבל הכול") של קובץ העבודה, כרשימת פסקאות. כל שינוי בנוסח משנה אותה."""
    import hashlib
    acc = docx_tracked.accept_all(work)
    return hashlib.sha256(json.dumps(list(acc), ensure_ascii=False).encode("utf-8")).hexdigest()


def dump_for_verifier(a):
    """קבצי הקלט של המאמת העצמאי (n9-verify.md): הנוסח המתקבל ("קבל הכול" על קובץ העבודה) והבועות החיצוניות שלנו,
    עם מספרי הפסקאות והסעיפים. נכתבים רק לנתיב שעובר guard_out (תיקיית העסקה או תיקייה זמנית), ולעולם לא נשלחים."""
    try:
        labels = content_checks.numbered_labels(a.work)
    except Exception:  # noqa: BLE001
        labels = []
    lab = lambda i: labels[i] if i is not None and i < len(labels) else None  # noqa: E731
    outs = []
    if a.dump_accepted_text:
        acc = docx_tracked.accept_all(a.work)
        outs.append((a.dump_accepted_text, [{"para": i, "label": lab(i), "text": t} for i, t in enumerate(acc)]))
    if a.dump_external_bubbles:
        parts = docx_tracked.read_package(a.work)
        from lxml import etree
        root = etree.fromstring(parts["word/document.xml"])
        received_ids = {c["id"] for c in docx_tracked.read_comments(docx_tracked.read_package(a.received))}
        spans = docx_tracked.comment_paragraph_spans(root)
        internal = set(content_checks.INTERNAL_AUTHORS)
        bubbles = []
        for c in docx_tracked.read_comments(parts):
            if c["id"] in received_ids or c["author"] in internal:
                continue
            first, last = spans.get(c["id"], (None, None))
            paras = list(range(first, last + 1)) if first is not None else []
            bubbles.append({"id": c["id"], "author": c["author"], "paras": paras,
                            "labels": [lab(i) for i in paras], "text": c["text"]})
        outs.append((a.dump_external_bubbles, bubbles))
    if a.dump_accepted_text:
        # טביעת האצבע של הנוסח המתקבל: המאמת מעתיק אותה לקובץ הממצאים שלו (work_sha256), והשער פוסל אימות שנעשה על נוסח אחר
        fp = accepted_fingerprint(a.work)
        outs.append((a.dump_accepted_text + ".sha256", {"work_sha256": fp}))
    for path, data in outs:
        try:
            p = guard_out(path, inputs=[a.work, a.received])
        except OutputRefused as exc:
            print("סירוב: %s" % exc)
            return 1
        os.makedirs(os.path.dirname(os.path.abspath(p)) or ".", exist_ok=True)
        with open(p, "w", encoding="utf-8") as fh:
            json.dump(data, fh, ensure_ascii=False, indent=1)
        print("נכתב %s (%d)" % (p, len(data)))
    return 0


def verifier_warnings(path):
    """אזהרות מהמאמת העצמאי: VERIFY_SCHEMA לקובץ שאינו במבנה, ו-VERIFY_OPEN לכל ממצא פתוח, עם המיקום והציטוט.
    בשלב הראשון אזהרה בלבד; ההורה מכריע לפי המטריצה (n3b) ומריץ את השער שוב. ממצא note אינו אזהרה."""
    data = load(path, "קובץ הממצאים של המאמת", required=False)   # נשאר לתאימות; השער משתמש ב-verifier_findings
    if data is None:
        return [{"code": "VERIFY_SCHEMA", "message": "קובץ הממצאים של המאמת חסר או אינו JSON", "where": path}]
    errs = content_checks.validate_verify_findings(data)
    if errs:
        return [{"code": "VERIFY_SCHEMA", "message": "קובץ הממצאים אינו במבנה: " + "; ".join(errs[:5]), "where": path}]
    out = []
    for f in data["findings"]:
        if f.get("severity") != "open":
            continue
        out.append({"code": "VERIFY_OPEN", "message": "המאמת העצמאי (%s): %s. ציטוט: \"%s\". לבדוק: %s"
                    % (f["check"], f["issue"].strip(), f["quote"].strip()[:160], (f.get("suggest") or "").strip()),
                    "where": f["where"]})
    return out


def _resolution_for(finding, decisions):
    """verify_resolutions[] התקין שמכסה את הממצא (לפי check ו-where). מחזיר (רשומה, סיבת אי-תקינות)."""
    doc = decisions if isinstance(decisions, dict) else {}
    decs = [d for d in (doc.get("decisions") if isinstance(doc.get("decisions"), list) else []) if isinstance(d, dict)]
    key = (str(finding.get("check")), str(finding.get("where")).strip())
    # הכרעה מתקנת מצהירה בעצמה על הממצא שהיא מתקנת: fixes_findings: [{"check", "where"}]. קיום מזהה בלבד אינו סגירה
    ids = {d.get("id") for d in decs
           if any(isinstance(x, dict) and (str(x.get("check")), str(x.get("where")).strip()) == key
                  for x in (d.get("fixes_findings") or []))}
    why = ""
    for r in doc.get("verify_resolutions") or []:
        if not isinstance(r, dict) or (str(r.get("check")), str(r.get("where")).strip()) != key:
            continue
        res, note = str(r.get("resolution") or ""), str(r.get("note") or "").strip()
        if not note:
            why = "חסרה הערה ב-verify_resolutions"
        elif res == "accepted_by_lawyer":
            return r, ""
        elif res.startswith("fixed:") and res[6:] in ids:
            return r, ""
        else:
            why = ("resolution חייב להיות fixed:<מזהה הכרעה שמצהירה ב-fixes_findings על הממצא הזה> או accepted_by_lawyer")
    return None, why


def verifier_findings(path, mode, decisions=None, work=None):
    """הממצאים של המאמת העצמאי כתנאי להשלמה. {code, message, where, blocking}. במצב send: קובץ חסר = VERIFY_MISSING,
    קובץ שאינו במבנה = VERIFY_SCHEMA, וממצא open בלי verify_resolutions תקין = VERIFY_OPEN, וכולם חוסמים. במצב work הכול
    אזהרה, והיעדר --verify-findings אינו ממצא."""
    send = mode == "send"
    if not path or not os.path.exists(path):
        if not path and not send:
            return []
        code = "VERIFY_MISSING" if send else "VERIFY_SCHEMA"
        return [{"code": code, "blocking": send, "where": path or "",
                 "message": "המאמת העצמאי (n9-verify.md) לא רץ או שקובץ הממצאים שלו חסר: ללא קריאה עצמאית של הנוסח "
                            "המתקבל אי אפשר לשלוח. להריץ את המאמת ולהעביר --verify-findings"}]
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, ValueError):
        data = None
    errs = ["הקובץ אינו JSON תקין"] if data is None else content_checks.validate_verify_findings(data)
    if errs:
        return [{"code": "VERIFY_SCHEMA", "blocking": send, "where": path,
                 "message": "קובץ הממצאים אינו במבנה: " + "; ".join(errs[:5])}]
    out = []
    # האימות קשור לנוסח שנבדק: בלי טביעת אצבע של הנוסח (work_sha256), או עם טביעה של נוסח אחר, הוא אינו תקף
    if work:
        try:
            fp = accepted_fingerprint(work)
        except Exception:  # noqa: BLE001
            fp = None
        have = str(data.get("work_sha256") or "")
        if fp and not have:
            out.append({"code": "VERIFY_NOT_BOUND", "blocking": send, "where": path,
                        "message": "בקובץ הממצאים אין work_sha256: אי אפשר לדעת על איזה נוסח הבדיקה נעשתה. להעתיק אותה "
                                   "מקובץ ה-.sha256 שנוצר עם --dump-accepted-text"})
        elif fp and have != fp:
            out.append({"code": "VERIFY_STALE", "blocking": send, "where": path,
                        "message": "הנוסח המתקבל השתנה אחרי שהמאמת קרא אותו (או שהקובץ הוא מסבב אחר). להפיק מחדש את קבצי הקלט "
                                   "של המאמת ולהריץ אותו שוב"})
    for f in data["findings"]:
        if f.get("severity") != "open":
            continue
        res, why = _resolution_for(f, decisions)
        if res is not None:
            continue
        out.append({"code": "VERIFY_OPEN", "blocking": send, "where": f["where"],
                    "message": "המאמת העצמאי (%s): %s. ציטוט: \"%s\". לבדוק: %s%s. לסגירה: הכרעה מתקנת, או verify_resolutions "
                               "(fixed:<מזהה הכרעה> | accepted_by_lawyer, עם הערה)"
                               % (f["check"], f["issue"].strip(), f["quote"].strip()[:160], (f.get("suggest") or "").strip(),
                                  " [%s]" % why if why else "")})
    return out


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
    ap.add_argument("--deal", help="תיקיית העסקה: קובץ המצב, דוח השער בשם הקנוני ורשומת ההפקה")
    ap.add_argument("--register", help="נשאר לתאימות, ואינו בשימוש: המרשם של מעריך הסיכונים אינו חוסם משלוח")
    ap.add_argument("--decisions", help="קובץ ההכרעות של הסבב")
    ap.add_argument("--expected-accept",
                    help="JSON עם מערך נוסחי היעד, פסקה לפסקה. בלעדיו בדיקת "
                         "ההלוך ושוב של \"קבל הכול\" אינה רצה, והדבר נאמר בפלט")
    ap.add_argument("--core", help="playbook-core.json: סימני האדום של הכללים (content_checks)")
    ap.add_argument("--manifest", help="corpus-manifest.json: שמות הצדדים בהסכמים החתומים (content_checks)")
    ap.add_argument("--lang", choices=("he", "en"),
                    help="שפת ההסכם. בלעדיו: נגזרת מהטיוטה שהתקבלה")
    ap.add_argument("--run-id", help="מזהה הריצה, כמו ב-apply_redlines.py: עותק למשלוח מאותה ריצה, שלא נמסר, מוחלף")
    # המאמת העצמאי (n9-verify.md): שני קבצי קלט שההורה מוסר לו בנתיב מקומי, וקובץ הממצאים שחוזר ממנו
    ap.add_argument("--dump-accepted-text", help="כותב JSON: הנוסח המתקבל אחרי \"קבל הכול\" על קובץ העבודה, פסקה לפסקה "
                                                 "[{para, label, text}], למאמת העצמאי")
    ap.add_argument("--dump-external-bubbles", help="כותב JSON: הבועות החיצוניות שלנו [{id, author, paras, labels, text}], "
                                                    "למאמת העצמאי")
    ap.add_argument("--verify-findings", help="קובץ הממצאים של המאמת העצמאי: במצב עבודה אזהרה (VERIFY_OPEN, "
                                              "VERIFY_SCHEMA); במצב משלוח חוסם: חסר = VERIFY_MISSING, ממצא open בלי "
                                              "verify_resolutions בקובץ ההכרעות = VERIFY_OPEN")
    ap.add_argument("--coverage", help="rule-coverage.json: תוכנית כיסוי הכללים. ברירת מחדל: <תיקיית העסקה>/rule-coverage.json")
    a = ap.parse_args(argv)
    if a.dump_accepted_text or a.dump_external_bubbles:
        code = dump_for_verifier(a)
        if code:
            return code

    for p, what in ((a.work, "קובץ העבודה"), (a.received, "הטיוטה שהתקבלה")):
        if not os.path.exists(p):
            print("%s אינו קיים: %s" % (what, p))
            return 2
    # Word פגום, DOC, מוצפן או Strict: הודעה דו-לשונית וקוד 2, ולא traceback של zipfile
    for p in (a.work, a.received):
        ok, msg, code = load_docx_or_explain(p, loader=False)
        if ok is None:
            print(msg)
            return code
    profile = lawyer_view(load(a.profile, "הפרופיל"))
    if not profile.get("lawyer_name"):
        print("אין בפרופיל שם עורך דין (branding.lawyer_name). השער מזהה את הבועות שלנו לפיו")
        return 2
    state = load(a.state, "קובץ המצב", required=False)
    state_path = a.state if state is not None else None
    if state is None and a.deal and os.path.exists(os.path.join(a.deal, "negotiation_state.json")):
        # עם --deal השער קורא את קובץ המצב של העסקה גם בלי --state (ממצא 3, הרצה S1c)
        state_path = os.path.join(a.deal, "negotiation_state.json")
        state = load(state_path, "קובץ המצב")
    decisions = load(a.decisions, "קובץ ההכרעות", required=False)
    core_given = content_checks.attach_related(load(a.core, "הגרעין", required=False), a.core)
    core = core_given if core_given is not None else playbook_of(state, a.deal)
    expected = load(a.expected_accept, "נוסחי היעד", required=False)
    if expected is not None and not isinstance(expected, list):
        print("--expected-accept הוא מערך של נוסחי פסקאות, ולא %s"
              % type(expected).__name__)
        return 2
    if expected is None:
        print("הערה: בלי --expected-accept, בדיקת \"קבל הכול\" (RT_ACCEPT) אינה רצה.")

    # בדיקות התוכן של הסבב (content_checks.py, הערות הנושא ונותן 4.0 עד 4.7): ממצא חוסם הוא כשל
    # בשער, ובמצב משלוח העותק אינו מופק כלל
    extra_fail, extra_warn = [], []
    if decisions is None:
        print("הערה: בלי --decisions, בדיקות התוכן של הסבב (content_checks) אינן רצות.")
    else:
        lawyer = [profile.get("lawyer_name"), profile.get("lawyer_name_en")] + list(profile.get("lawyer_aliases") or [])
        if isinstance(decisions, dict) and decisions.get("author"):
            lawyer.append(decisions["author"])   # השם שחתם על הבועות בסבב: בועה שלו אינה מקור של הצד שכנגד
        found = content_checks.run_checks(
            a.work, a.received, decisions.get("decisions", []) if isinstance(decisions, dict) else decisions,
            state=state, core=core_given,
            manifest=load(a.manifest, "המניפסט", required=False), profile={"lawyer_names": lawyer}, mode=a.mode)
        extra_fail = [dict(f, code=f["code"]) for f in found if f["blocking"]]
        extra_warn = [dict(f, code=f["code"]) for f in found if not f["blocking"]]

    # כיסוי כללי הפלייבוק והמאמת העצמאי: במצב משלוח חוסמים (העותק אינו מופק), במצב עבודה אזהרה
    for f in coverage_for_gate(a, decisions, core, state, a.mode) + verifier_findings(a.verify_findings, a.mode, decisions, a.work):
        (extra_fail if f.get("blocking") else extra_warn).append(dict(f))

    if a.mode == "send" and extra_fail:
        if not a.send:
            print("ב--mode send דרוש --send: הנתיב שאליו ישונה שם העותק אם יעבור")
            return 2
        previous = a.send if os.path.exists(a.send) else None
        # גם כאן כל בדיקות השער רצות, על עותק זמני בלי השכבה הפנימית שנמחק מיד, כדי שהדוח יהיה שלם (בדיקה עצמאית
        # S1c: עברית בהסכם באנגלית ואורך בועה לא דווחו כשבדיקת תוכן חסמה). שום עותק למשלוח אינו נכתב
        tmpdir = tempfile.mkdtemp(prefix="areo-gate-")
        try:
            tmp = os.path.join(tmpdir, "send-check.docx")
            docx_tracked.strip_internal(a.work, tmp)
            full = qa_gate.run_gate(tmp, a.received, "send", profile, state=state, expected_accept=expected,
                                    decisions=decisions, lang=a.lang, core=core, deal_dir=a.deal)
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
        extra_fail = list(full["failures"]) + extra_fail
        extra_warn = list(full["warnings"]) + extra_warn
        res = {"mode": "send", "passed": False, "failures": extra_fail, "warnings": extra_warn,
               "info": full.get("info") or {}, "send_copy": None}
        if previous:
            res["retracted"] = pre_send.retract_send_copy(previous, state, "he", deal_dir=a.deal)
    elif a.mode == "work":
        res = qa_gate.run_gate(a.work, a.received, "work", profile, state=state,
                               expected_accept=expected, decisions=decisions, lang=a.lang, core=core,
                               deal_dir=a.deal)
        # מה יחסום את המשלוח מוצג כבר עכשיו, בשאלה אחת לכל קבוצה (ולא חסם אחרי חסם בשלב המשלוח)
        lawyer = [profile.get("lawyer_name"), profile.get("lawyer_name_en")] + list(profile.get("lawyer_aliases") or [])
        res["pre_send"] = pre_send_preview(a, profile, state, expected, decisions, core, core_given, lawyer)
        try:
            rlabels = content_checks.numbered_labels(a.received)
        except Exception:  # noqa: BLE001
            rlabels = None
        res["pre_send_items"] = pre_send_items(res["pre_send"], state, (res.get("info") or {}).get("lang") or "he",
                                               rlabels)
    else:
        if not a.send:
            print("ב--mode send דרוש --send: הנתיב שאליו ישונה שם העותק אם יעבור")
            return 2
        try:
            # `allow_existing_doc`: הספרייה מטפלת בעותק קיים בנתיב, ולא
            # דורסת אותו בשקט - בכשל הוא מקבל " - לא למשלוח". חסימה כאן
            # הייתה מונעת הרצה שנייה באותו סבב, שהיא המצב הרגיל
            guard_out(a.send, inputs=[a.work, a.received], allow_existing_doc=True)
        except OutputRefused as exc:
            print("סירוב על --send: %s" % exc)
            return 1
        previous = a.send if os.path.exists(a.send) else None
        rnd = ((state or {}).get("meta") or {}).get("round_number")
        same_run = pre_send.reusable_path(a.deal, rnd, a.run_id, "send", state) if previous else None
        if same_run and os.path.normcase(os.path.abspath(same_run)) == os.path.normcase(os.path.abspath(a.send)):
            # עותק שהשער הזה הפיק באותה ריצה, ושלא נמסר ולא נשלח: מוחלף, ולא " (2)" (ממצא 7, הרצה S1c)
            target, previous = a.send, None
            print("העותק למשלוח מאותה ריצה (%s) לא נמסר, ולכן הוא מוחלף" % os.path.basename(a.send))
        else:
            target = paths.unique_path(a.send)
        if previous:
            print("בנתיב --send כבר יש עותק. הוא אינו נדרס: העותק החדש ייכתב ל-%s"
                  % os.path.basename(target))
        res = qa_gate.build_send_copy(a.work, a.received, target, profile, state=state,
                                      expected_accept=expected, deal_dir=a.deal,
                                      decisions=decisions, lang=a.lang, core=core)
        if res.get("send_copy") and a.run_id and a.deal and rnd:
            pre_send.update_run_record(a.deal, rnd, a.run_id, {"send": res["send_copy"]})
        if not res["passed"] and previous:
            # עותק "למשלוח" קודם, כשהעותק החדש נכשל, אינו נשאר מוכן למשלוח
            res["retracted"] = pre_send.retract_send_copy(
                previous, state, res.get("info", {}).get("lang", "he"), deal_dir=a.deal)

    if res.get("retracted") and state is not None and state_path:
        # ההסרה נרשמת בקובץ המצב עצמו, ולא רק בזיכרון: בסבב הבא אין עותק למשלוח רשום, והפריט החוסם נשאר
        state.setdefault("meta", {})["updated_by"] = "orchestrator"
        pre_send.save_state(state, state_path)
        print("קובץ המצב עודכן: אין עותק למשלוח (%s)" % state_path)

    if extra_fail or extra_warn:
        if not (a.mode == "send" and res.get("failures") is extra_fail):
            res["failures"] = list(res.get("failures") or []) + extra_fail
            res["warnings"] = list(res.get("warnings") or []) + extra_warn
        if extra_fail:
            res["passed"] = False
    # יחידת הספירה האחת (content_checks.unit_counts): אותם מספרים בדוח השער, בראש הסיכום ובפנקס
    try:
        items_d = decisions.get("decisions", []) if isinstance(decisions, dict) else (decisions or [])
        res.setdefault("info", {})["counts"] = content_checks.unit_counts(
            items_d, len(docx_tracked.received_paragraphs(a.received)), ((state or {}).get("meta") or {}).get("playbook_map"))
    except Exception:  # noqa: BLE001
        pass
    report(res)
    if a.mode == "work" and res.get("pre_send"):
        print("לפני שליחה, בלי שינוי, ייחסם המשלוח על %d פריטים. שאלה אחת לכל קבוצה, למנה (pre_send_items בדוח):"
              % len(res["pre_send"]))
        for it in res.get("pre_send_items") or ():
            print("  - " + it["text"])
        rest = [f for f in res["pre_send"] if not any(f["code"] in g[0] for g in PRE_SEND_GROUPS)]
        for f in rest:
            print("  [%s] %s%s" % (f["code"], f["message"], "  (%s)" % f["where"] if f.get("where") else ""))
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
        # תיקיית הדוח (למשל runs/round-1) עוד לא קיימת בהרצה הראשונה: נוצרת, ולא FileNotFoundError
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(res, fh, ensure_ascii=False, indent=2, default=str)
        print("נכתב %s" % path)
    elif a.deal:
        # בלי --out: השם הקנוני בתיקיית העסקה, עם היסטוריה (ולא gate-work-2, gate-work-3)
        rnd = (decisions.get("round") if isinstance(decisions, dict) else None) or             ((state or {}).get("meta") or {}).get("round_number")
        path = qa_gate.run_report_path(a.deal, rnd, "gate-%s.json" % a.mode)
        if path:
            try:
                guard_out(path, inputs=[a.work, a.received, a.profile])
            except OutputRefused as exc:
                print("הדוח לא נכתב. סירוב: %s" % exc)
            else:
                qa_gate.write_run_report(path, res)
                print("נכתב %s" % path)

    # כשל בשער הוא תשובה ולא תקלה, ולכן הוא קוד נפרד: הרכיב אינו ממשיך
    # למסירה, וגם אינו מדווח על שגיאה טכנית שלא הייתה
    return 0 if res["passed"] else 3


if __name__ == "__main__":
    sys.exit(main())
