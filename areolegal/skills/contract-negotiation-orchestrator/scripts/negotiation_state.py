#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""פנקס העסקה: קובץ המצב של המשא ומתן, נכתב ונבדק בקוד ולא ביד.

`negotiation_state.json` הוא הזיכרון של העסקה בין סבב לסבב: מה הצענו בכל
סעיף, על מה ויתרנו, מה הכריע המשתמש, ומה נשלח ומה התקבל. טעות בו עוברת לכל
הסבבים הבאים: ויתור שלא נרשם הוא ויתור שיינתן פעמיים, ומסמך שנשלח ולא נרשם
הוא קובץ שהרכיב לא יזהה כשהוא חוזר. לכן הוא נבנה במבנה אחד, בקוד הייחוס
(`areolegal/lib/orchestrator/state_builder.py`), ונבדק לפני כל כתיבה.

ארבע פעולות:

* `write` — בסוף כל סבב. בונה את קובץ המצב של הסבב מקובץ ההכרעות, ו**מעביר
  מהסבב הקודם את כל מה שמצטבר**: מסמכים שנשלחו והתקבלו, ויתורים מכוונים,
  הכרעות משתמש, נקודות פתוחות, התחייבויות, ותיעוד הסעיפים שלא נפתחו מחדש.
  לפני הכתיבה הקובץ הקודם נשמר כ-`negotiation_state_round_<N>.json`
  (`negotiation_state_schema.md`, "כלל גרסאות").
* `decide` — רושם הכרעה של המשתמש ("נדרשת הכרעתך", אחד מתשעת המצבים), בקובץ
  ובסעיפים שהיא חלה עליהם.
* `check` — בודק את הקובץ מול המבנה. קוד יציאה 3 כשיש שגיאה.
* `migrate` — קובץ בפורמט ישן: נשמר כמו שהוא כ-`negotiation_state_legacy.json`,
  ונכתב במקומו קובץ לפי המבנה.

**קובץ שאינו עובר את הבדיקה אינו נכתב במקום הקובץ החי.** הוא נשמר לצד הקובץ
החי כ-`negotiation_state.rejected.json`, והשגיאות מודפסות. הקובץ החי נשאר
כפי שהיה.

    python3 scripts/negotiation_state.py write --deal "Areo-נתונים/transactions/<id>" \\
        --decisions decisions_round_2.json --profile Areo-נתונים/פרופיל-לקוח.json \\
        --resolution playbook-resolution.json --gate gate-send.json \\
        --produced send="תגובת החברה - סבב 2 - למשלוח.docx" \\
        --sent "תגובת החברה - סבב 2 - למשלוח.docx"

קוד יציאה: **0** נכתב ותקין, **3** הקובץ אינו תקין ולא נכתב, **2** קלט חסר.
"""
import argparse
import copy
import hashlib
import json
import os
import sys

import areo_lib  # noqa: F401  מוסיף את areolegal/lib לנתיב הייבוא

from orchestrator import state_builder as SB  # noqa: E402
from orchestrator import state_migrate as SM  # noqa: E402

LIVE = "negotiation_state.json"
REJECTED = "negotiation_state.rejected.json"
LEGACY = "negotiation_state_legacy.json"

# מה שמצטבר לאורך העסקה, ועובר מסבב לסבב כמו שהוא
CARRY_TOP = ("playbook_source", "positions_source", "profile_gap", "playbook_status", "strategy_summary",
             "case_law", "exception_log", "clarification_questions", "posture_confirmation",
             "lawyer_overrides", "sources_log", "client_answers", "company_representations",
             "open_items", "talking_points", "commitments", "packages", "entity_details",
             "question_batches", "signing_checklist", "playbook_resolution")
# רשימות שהסבב החדש מוסיף עליהן, ולא מחליף אותן
APPEND_TOP = ("deliberate_concessions", "user_decisions", "produced_documents")
CARRY_META = ("client_name", "counterparty_name", "contract_type", "position", "our_role", "paper_type",
              "lang", "deal_context", "sent_documents", "received_documents")


def load(path, what, required=True):
    if not path:
        if required:
            print("חסר %s" % what)
            raise SystemExit(2)
        return None
    if not os.path.exists(path):
        print("%s אינו קיים: %s" % (what, path))
        raise SystemExit(2)
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def dump(path, data):
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=1)


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def doc_record(path, deal, when_key):
    rel = os.path.relpath(os.path.abspath(path), os.path.abspath(deal)).replace("\\", "/")
    return {"file_name": rel, "sha256": sha256(path), when_key: SB.now_iso()}


def report(errors):
    for e in errors:
        print("  [%s] %s%s" % (e.get("code"), e.get("message"),
                               "  (%s)" % e["where"] if e.get("where") else ""))


def write_checked(deal, state):
    """כותב רק קובץ תקין. קובץ לא תקין נשמר לצד הקובץ החי, והחי אינו משתנה."""
    errors = SB.validate_state(state)
    if errors:
        dump(os.path.join(deal, REJECTED), state)
        print("קובץ המצב אינו תקין, ולא נכתב במקום הקובץ החי (%d שגיאות):" % len(errors))
        report(errors)
        print("הגרסה שנדחתה: %s" % os.path.join(deal, REJECTED))
        return 3
    dump(os.path.join(deal, LIVE), state)
    rej = os.path.join(deal, REJECTED)
    if os.path.exists(rej):
        os.remove(rej)
    print("נכתב %s" % os.path.join(deal, LIVE))
    return 0


def merge_clauses(prev, new):
    """סעיף שלא נפתח בסבב הזה נשאר כמו שהיה. סעיף שנפתח מקבל את ההכרעה
    החדשה, ושומר את מה שהסבבים הקודמים כתבו בו ושאין לו תחליף עכשיו
    (agreed_text, last_round_changes, היסטוריה)."""
    by_id = {c.get("clause_id"): c for c in new}
    out = []
    for c in prev:
        cid = c.get("clause_id")
        if cid in by_id:
            merged = copy.deepcopy(c)
            merged.update(by_id.pop(cid))
            out.append(merged)
        else:
            out.append(copy.deepcopy(c))
    out += [c for c in new if c.get("clause_id") in by_id]
    return out


def carry_over(prev, st):
    for k in CARRY_META:
        v = (prev.get("meta") or {}).get(k)
        if v not in (None, "", [], {}) and st["meta"].get(k) in (None, "", [], {}):
            st["meta"][k] = copy.deepcopy(v)
    for k in CARRY_TOP:
        if prev.get(k) not in (None, "", [], {}) and st.get(k) in (None, "", [], {}):
            st[k] = copy.deepcopy(prev[k])
    for k in APPEND_TOP:
        st[k] = copy.deepcopy(prev.get(k) or []) + [x for x in st.get(k) or []
                                                     if x not in (prev.get(k) or [])]
    st["clauses"] = merge_clauses(prev.get("clauses") or [], st.get("clauses") or [])
    nm = dict(prev.get("numbering_map") or {})
    nm.update({k: v for k, v in (st.get("numbering_map") or {}).items() if v or k not in nm})
    st["numbering_map"] = nm
    st["meta"]["generated_at"] = (prev.get("meta") or {}).get("generated_at") or st["meta"]["generated_at"]
    return st


def cmd_write(a):
    deal = a.deal
    os.makedirs(deal, exist_ok=True)
    live = os.path.join(deal, LIVE)
    prev = load(live, "קובץ המצב") if os.path.exists(live) else None
    if prev is not None and str((prev.get("meta") or {}).get("schema_version")) != SB.SCHEMA_VERSION:
        print("קובץ המצב הקיים בפורמט ישן (%s). הרץ קודם: negotiation_state.py migrate --deal ..."
              % (prev.get("meta") or {}).get("schema_version"))
        return 2

    prev_round = int((prev or {}).get("meta", {}).get("round_number") or 0)
    rnd = a.round or (prev_round + 1 if prev else 1)
    if prev is not None and rnd < prev_round:
        print("סבב %d קטן מהסבב שבקובץ (%d). קובץ מצב אינו חוזר לאחור" % (rnd, prev_round))
        return 2
    tid = a.transaction_id or (prev or {}).get("meta", {}).get("transaction_id") or os.path.basename(
        os.path.abspath(deal))

    produced = []
    for item in a.produced or ():
        kind, _, path = item.partition("=")
        p = path if os.path.isabs(path) else os.path.join(deal, path)
        if not kind or not path or not os.path.exists(p):
            print("--produced %r: צריך סוג=נתיב לקובץ שקיים" % item)
            return 2
        produced.append((kind, p))

    st = SB.build_state(
        tid, rnd, profile=load(a.profile, "הפרופיל", required=False),
        decisions=load(a.decisions, "קובץ ההכרעות", required=False), deal_dir=deal,
        produced=produced, resolution=load(a.resolution, "תוצאת האיתור", required=False),
        gate=load(a.gate, "דוח השער", required=False),
        concessions=load(a.concessions, "הוויתורים", required=False) or (),
        lang=a.lang, text_status=a.text_status, counterparty_name=a.counterparty or "",
        contract_type=a.contract_type or "",
        clause_labels=load(a.clause_labels, "מספרי הסעיפים", required=False),
        para_count=a.para_count)

    if prev is not None:
        st = carry_over(prev, st)
        # הסבב הקודם נשמר לפני שהקובץ החי משתנה. הרצה חוזרת של אותו סבב
        # אינה דורסת את העותק של הסבב הקודם
        hist = os.path.join(deal, "negotiation_state_round_%d.json" % prev_round)
        if rnd > prev_round and not os.path.exists(hist):
            dump(hist, prev)
            print("הסבב הקודם נשמר: %s" % hist)

    for path in a.sent or ():
        p = path if os.path.isabs(path) else os.path.join(deal, path)
        if not os.path.exists(p):
            print("--sent %r אינו קיים" % path)
            return 2
        rec = doc_record(p, deal, "sent_at")
        rec["round"] = rnd
        if rec["sha256"] not in {d.get("sha256") for d in st["meta"]["sent_documents"]}:
            st["meta"]["sent_documents"].append(rec)
    for path in a.received or ():
        p = path if os.path.isabs(path) else os.path.join(deal, path)
        if not os.path.exists(p):
            print("--received %r אינו קיים" % path)
            return 2
        rec = doc_record(p, deal, "received_at")
        rec["round"] = rnd
        if rec["sha256"] not in {d.get("sha256") for d in st["meta"]["received_documents"]}:
            st["meta"]["received_documents"].append(rec)

    print("עסקה: %s   סבב: %d (%s)" % (tid, rnd, st["meta"]["round_stage"]))
    print("סעיפים: %d   ויתורים מכוונים: %d   הכרעות משתמש: %d"
          % (len(st["clauses"]), len(st["deliberate_concessions"]), len(st["user_decisions"])))
    gaps = SB.coverage_gaps(st.get("coverage_index"))
    if gaps:
        print("רכיבים בלי הכרעה במפתח הכיסוי: %d" % len(gaps))
    return write_checked(deal, st)


def cmd_decide(a):
    live = os.path.join(a.deal, LIVE)
    st = load(live, "קובץ המצב")
    try:
        rec = SB.record_user_decision(st, a.id, a.situation, a.answer, a.answer_kind,
                                      applies_to=a.applies_to or (), recommendation=a.recommendation)
    except ValueError as exc:
        print("ההכרעה לא נרשמה: %s" % exc)
        return 2
    missing = [c for c in rec["applies_to"]
               if c not in {x.get("clause_id") for x in st.get("clauses", [])}]
    if missing:
        print("אזהרה: אין בקובץ סעיף בשם %s, ולכן ההכרעה לא נרשמה עליו" % ", ".join(missing))
    st["meta"]["last_updated"] = SB.now_iso()
    print("הכרעה %s: %s (%s)" % (rec["id"], rec["answer"], rec["outcome"]))
    return write_checked(a.deal, st)


def cmd_check(a):
    st = load(os.path.join(a.deal, LIVE), "קובץ המצב")
    errors = SB.validate_state(st)
    bad_ts = SM.non_iso_timestamps(st)
    if not errors and not bad_ts:
        m = st.get("meta", {})
        print("תקין. עסקה %s, סבב %s (%s)." % (m.get("transaction_id"), m.get("round_number"),
                                                 m.get("round_stage")))
        return 0
    report(errors)
    for k, v in bad_ts:
        print("  [STATE_TIMESTAMP] %s=%s" % (k, v))
    return 3


def cmd_migrate(a):
    live = os.path.join(a.deal, LIVE)
    old = load(live, "קובץ המצב")
    if str((old.get("meta") or {}).get("schema_version")) == SB.SCHEMA_VERSION:
        print("הקובץ כבר במבנה הנוכחי (%s). אין מה להמיר." % SB.SCHEMA_VERSION)
        return 0
    legacy = os.path.join(a.deal, LEGACY)
    if os.path.exists(legacy):
        print("כבר קיים %s. הקובץ הישן אינו נדרס" % legacy)
        return 2
    new, log = SM.migrate_state(old)
    dump(legacy, old)
    print("הקובץ הישן נשמר כמו שהוא: %s" % legacy)
    for line in log[:20]:
        print("  %s" % line)
    return write_checked(a.deal, new)


def main(argv=None):
    sys.dont_write_bytecode = True
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)

    w = sub.add_parser("write", help="קובץ המצב בסוף סבב")
    w.add_argument("--deal", required=True, help="תיקיית העסקה, Areo-נתונים/transactions/<id>")
    w.add_argument("--transaction-id", help="בלעדיו: מהקובץ הקיים, או שם התיקייה")
    w.add_argument("--round", type=int, help="בלעדיו: הסבב שבקובץ ועוד אחד, או 1")
    w.add_argument("--decisions", help="קובץ ההכרעות של הסבב")
    w.add_argument("--profile", help="פרופיל-לקוח.json")
    w.add_argument("--resolution", help="הפלט של resolve_playbook.py")
    w.add_argument("--gate", help="הדוח של qa_gate.py")
    w.add_argument("--concessions", help="JSON: רשימת הוויתורים המכוונים של הסבב")
    w.add_argument("--clause-labels", help='JSON: {"<מזהה הכרעה>": "סעיף 3"}')
    w.add_argument("--para-count", type=int, help="מספר הפסקאות בטיוטה שהתקבלה, למפתח הכיסוי")
    w.add_argument("--produced", action="append", help="סוג=נתיב: work, send, as_produced, decisions")
    w.add_argument("--sent", action="append", help="הקובץ שנשלח לצד שכנגד בסבב הזה")
    w.add_argument("--received", action="append", help="הקובץ שהתקבל מהצד שכנגד בסבב הזה")
    w.add_argument("--counterparty", help="שם הצד שכנגד")
    w.add_argument("--contract-type", help="סוג ההסכם")
    w.add_argument("--text-status", choices=SB.TEXT_STATUS)
    w.add_argument("--lang", default="he", choices=("he", "en"))

    d = sub.add_parser("decide", help="הכרעה של המשתמש")
    d.add_argument("--deal", required=True)
    d.add_argument("--id", required=True, help="מזהה השאלה")
    d.add_argument("--situation", type=int, choices=list(SB.SITUATIONS),
                   help='אחד מתשעת המצבים של "נדרשת הכרעתך"')
    d.add_argument("--answer", required=True, help="התשובה, במילים של המשתמש")
    d.add_argument("--answer-kind", required=True, choices=SB.ANSWER_KINDS,
                   help="explicit: המשתמש הכריע. delegated: המשתמש אמר להחיל את ההמלצה")
    d.add_argument("--applies-to", action="append", help="clause_id שההכרעה חלה עליו")
    d.add_argument("--recommendation", help="ההמלצה שהוצגה למשתמש")

    c = sub.add_parser("check", help="בדיקת הקובץ מול המבנה")
    c.add_argument("--deal", required=True)

    m = sub.add_parser("migrate", help="המרת קובץ בפורמט ישן")
    m.add_argument("--deal", required=True)

    a = ap.parse_args(argv)
    return {"write": cmd_write, "decide": cmd_decide, "check": cmd_check, "migrate": cmd_migrate}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
