#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""פנקס העסקה: קובץ המצב של המשא ומתן, נכתב ונבדק בקוד ולא ביד.

`negotiation_state.json` הוא הזיכרון של העסקה בין סבב לסבב: מה הצענו בכל
סעיף, על מה ויתרנו, מה הכריע המשתמש, ומה נשלח ומה התקבל. טעות בו עוברת לכל
הסבבים הבאים: ויתור שלא נרשם הוא ויתור שיינתן פעמיים, ומסמך שנשלח ולא נרשם
הוא קובץ שהרכיב לא יזהה כשהוא חוזר. לכן הוא נבנה במבנה אחד, בקוד הייחוס
(`areolegal/lib/orchestrator/state_builder.py`), ונבדק לפני כל כתיבה.

הפעולות:

* `write` - בסוף כל סבב. בונה את קובץ המצב של הסבב מקובץ ההכרעות, ו**מעביר
  מהסבב הקודם את כל מה שמצטבר**: מסמכים שנשלחו והתקבלו, ויתורים מכוונים,
  הכרעות משתמש, נקודות פתוחות, התחייבויות, ותיעוד הסעיפים שלא נפתחו מחדש.
  לפני הכתיבה הקובץ הקודם נשמר כ-`negotiation_state_round_<N>.json`
  (`n8-state-schema.md`, "כלל גרסאות").
* `decide` - רושם הכרעה של המשתמש ("נדרשת הכרעתך", אחד מתשעת המצבים), בקובץ
  ובסעיפים שהיא חלה עליהם. **תשובה כללית אינה אישור** (פאנל S1d-R2, 29.10.2026): פריט שדורש תשובה מפורשת
  (`--requires-explicit`, או שמנת השאלות רשמה אותו ב-`question_batches[].requires_explicit`) ונענה בתשובה כללית נרשם
  `outcome: held_requires_explicit`, ההמלצה אינה מוחלת, והוא נשאל שוב במפורש.
* `write` מעריך מחדש את open_items בכל סבב (state_builder.refresh_open_items): פריט שהתיישן נסגר עם הסיבה, ופריט
  בדיקה משפטית מפסיק לחסום משלוח אחרי שהשער עבר. כשבסבב נרשמו עמדות שונות מהפלייבוק, `write` מדפיס את שורת עדכון
  הפלייבוק לסיכום (state_builder.playbook_update_line).
* `stance` - רושם את הגישה להחלת הפלייבוק בעסקה (playbook, stricter או lenient)
  ב-`meta.deal_context.stance`, עם הסבב שבו נקבעה. גישה קודמת עוברת ל-history.
* `check` - בודק את הקובץ מול המבנה. קוד יציאה 3 כשיש שגיאה.
* `sent` - רושם ב-`meta.sent_documents` את הקובץ שנשלח בפועל בסבב שהסתיים, גם כשהעותק למשלוח לא הופק והמשתמש
  שלח את קובץ העבודה או קובץ אחר (H5). `--basis user_confirmed` כשהמשתמש אמר איזה קובץ נשלח; `assumed_last_work`
  כשהתשובה אינה ידועה וההשוואה נעשית מול קובץ העבודה האחרון ("בסיס משוער").
  **העותק למשלוח אינו "נשלח" בסוף הסבב** (S1d-R2, 28.10.2026): `write` עם `--gate` (שעבר) או `--produced send=`
  רושם אותו ב-`quality_gate.send_copy` במעמד `produced_pending_send` ("הופק, ממתין לשליחה"), וגם `--sent` עם אותו
  קובץ אינו רושם אותו כנשלח. הוא עובר ל-`sent` רק ב-`sent`, באישור המשתמש. `round_tools.py basis` שואל בתחילת הסבב
  הבא "נשלח העותק שהופק?", ואינו רושם בעצמו (S1e-R3, 28.10.2026: העותק שהופק נרשם כנשלח, אף שנשלח קובץ שעורכת
  הדין ערכה).
  **רשומה אחת לכל סבב**: קובץ אחר שנרשם לאותו סבב מחליף את הרשומה הקודמת, והיא נשמרת ב-`history` של הרשומה החדשה.
  **עריכה לפני המשלוח**: כשהקובץ שנשלח שונה מהעותק שהופק באותו סבב, `sent` משווה ביניהם
  (`compare_rounds.edits_before_sending`) ורושם כל הבדל ב-`lawyer_overrides` (source: edited_before_sending): הפסקה,
  clause_id, הנוסח שהופק והנוסח שנשלח. הסעיף שעורך הדין שינה מקבל את הנוסח שנשלח (sent_text, וגם pending_text או
  agreed_text כשהם קיימים), וההשוואה בסבב הבא היא מול הקובץ שנשלח. `--edited` נשאר, וההבדלים נרשמים גם בלעדיו.
* `reopen` - הוראה רשומה של עורך הדין לפתוח מחדש סעיף מוסכם (CLOSED), קבלה שנשלחה או ויתור שנמסר, עם התאריך
  והסיבה (phase3, כלל 5). בלי הוראה כזו סעיף מוסכם אינו נפתח, ו-`check` נכשל (STATE_REOPEN_WITHOUT_INSTRUCTION).
  הסבב ב-reopen_log הוא הסבב הנוכחי (state_builder.current_round), ולא הסבב שבקובץ לפני write (S1e-R3).
  **החזרה לנוסח המוסכם אינה פתיחה מחדש** (S1e-R3, 6(h)): הכרעה שמחזירה בעקוב אחר שינויים שינוי שקט של הצד השני בסעיף
  CLOSED (silent_change עם החזרה, או `kind: restore_agreed` בקובץ ההכרעות) משאירה את הסעיף CLOSED, נרשמת עליו
  ב-`restore_agreed` וב-silent_changes (decision: revert, kind: restore_agreed), ואינה דורשת reopen.

**הסטטוס של כל סעיף נקבע בקוד** (בדיקה עצמאית S1c, H2): הכרעת קבלה (A1) נרשמת ACCEPTED_PENDING, ולא CLOSED.
`write --compare <round-compare.json>` בסבב הבא סוגר אותה (CLOSED, closed_in_round, agreed_text) רק כשהצד השני לא
שינה את הנוסח או קיבל אותו, ורק כשאין עליה נקודה פתוחה לשיחה. אותה השוואה רושמת את השינויים השקטים ב-`silent_changes`,
ואת הדחיות. ברירת המחדל אחרי דחייה היא MOVING; STUCK רק כשאותה הצעה שלנו, או המדרגה שאחריה, נדחתה בשני סבבים בלי
תזוזה שלהם, או כשהצד השני כתב שהעמדה סופית (`state_builder.stuck_reason`). STUCK שנקבע בהשוואה אינו נדרס בהכרעה
בלי סטטוס מפורש.

**write ממזג, ואינו דורס** (S1d, 28.10.2026: בסבב 2 נמחקו meta.deal_context, time_anchors, checks_reviewed,
review_table ו-internal_summary). כל שדה שהסבב אינו בונה מחדש עובר כמו שהוא; מילון מתמזג לפי מפתח, ורשימה מצטרפת.
רשומות של סבב קודם שמתייחסות למספרי פסקאות בטיוטה של אותו סבב (time_anchors, checks_reviewed, post_checks_done,
review_table) נשמרות עם `round` של הסבב שלהן, והבדיקות של הסבב החדש אינן קוראות אותן כאילו הן שלו.
**text_status** עובר מ-write ל-write באותו סבב (בלי `--text-status`); בסבב חדש הוא `our_unsent_response`. `sent` (וגם
`write --sent`) על הסבב הנוכחי מעביר תגובה או טיוטה שלנו ל-`our_sent_response`. **meta.updated_by** הוא `orchestrator`
בכל כתיבה של הרכיב.
* `migrate` - קובץ בפורמט ישן: נשמר כמו שהוא בתיקיית `history/` של העסקה
  (`negotiation_state.<חותמת זמן>.v<גרסה>.json`, ולא ליד הקובץ החי), ונכתב
  במקומו קובץ לפי המבנה.

**קובץ שאינו עובר את הבדיקה אינו נכתב במקום הקובץ החי.** הוא נשמר לצד הקובץ
החי כ-`negotiation_state.rejected.json`, והשגיאות מודפסות. הקובץ החי נשאר
כפי שהיה.

    python "AREO_RT/skills/contract-negotiation-orchestrator/scripts/negotiation_state.py" write --deal "Areo-נתונים/transactions/<id>" \\
        --decisions decisions_round_2.json --profile Areo-נתונים/פרופיל-לקוח.json \\
        --resolution playbook-resolution.json --gate gate-send.json \\
        --produced send="<סוג ההסכם> - <החברה> - סבב 2 - 15.10.2026.docx"

קוד יציאה: **0** נכתב ותקין, **3** הקובץ אינו תקין ולא נכתב, **2** קלט חסר.
"""
import argparse
import copy
import hashlib
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # גם ב-python -I, שאינו מוסיף את תיקיית הסקריפט
import areo_lib  # noqa: F401  מוסיף את areolegal/lib לנתיב הייבוא

from orchestrator import state_builder as SB  # noqa: E402
from orchestrator import state_migrate as SM  # noqa: E402
from common import paths  # noqa: E402

LIVE = "negotiation_state.json"
REJECTED = "negotiation_state.rejected.json"
UPDATED_BY = "orchestrator"   # meta.updated_by: הרכיב שכתב אחרון (n8-state-schema.md: orchestrator / strategist)
# text_status שמשמעו נוסח שלנו שטרם נשלח: עובר ל-our_sent_response כשהקובץ של הסבב נרשם כנשלח
UNSENT_OURS = ("", "our_unsent_response", "our_draft")

# מה שמצטבר לאורך העסקה, ועובר מסבב לסבב כמו שהוא
CARRY_TOP = ("playbook_source", "positions_source", "profile_gap", "playbook_status", "strategy_summary",
             "case_law", "exception_log", "clarification_questions", "posture_confirmation",
             "lawyer_overrides", "sources_log", "client_answers", "company_representations",
             "open_items", "talking_points", "commitments", "packages", "entity_details",
             "question_batches", "signing_checklist", "playbook_resolution", "silent_changes")
# רשימות שהסבב החדש מוסיף עליהן, ולא מחליף אותן
APPEND_TOP = ("deliberate_concessions", "user_decisions", "produced_documents")
CARRY_META = ("client_name", "counterparty_name", "contract_type", "position", "our_role", "paper_type",
              "lang", "deal_context", "sent_documents", "received_documents")
# שדות meta שהסבב הנוכחי מחשב מחדש. כל שדה meta אחר שכבר נכתב (entity_check, bilingual, deal_documents,
# exposed_comments, combo_checks וכל שדה עתידי) עובר כמו שהוא (באג 5, הרצה S1b, 28.10.2026)
FRESH_META = ("transaction_id", "schema_version", "refs_version", "round_number", "round_stage",
              "generated_at", "last_updated", "confidential")
# שדות של הסבב עצמו: נשמרים בהרצה חוזרת של write באותו סבב. בסבב הבא הם נשמרים תחת הסבב שלהם (round בכל רשומה),
# ואינם נמחקים (S1d, 28.10.2026)
SAME_ROUND_TOP = ("time_anchors", "post_checks_done", "checks_reviewed", "review_table", "internal_summary")
EMPTY = (None, "", [], {})


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
    state.setdefault("meta", {})["updated_by"] = UPDATED_BY
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


# שדות של הסבבים הקודמים שהכרעה חדשה אינה מוחקת: הם מצטברים
KEEP_LISTS = ("rejections", "reopen_log", "concession_history")


def _recorded_concession(prev_list, x, key):
    """הוויתור על הצעה נגדית הדוקה (state_builder.counter_tighter_concession) כבר רשום בסעיף לאותו סבב, ביד או ב-write
    קודם, גם בנוסח אחר: אינו נרשם שוב."""
    return key == "concession_history" and isinstance(x, dict) and x.get("kind") == "counter_tighter" and any(
        isinstance(y, dict) and y.get("round") == x.get("round") and y.get("who") == "us"
        and y.get("kind") in (None, "counter_tighter") for y in prev_list or ())


def merge_clauses(prev, new):
    """סעיף שלא נפתח בסבב הזה נשאר כמו שהיה. סעיף שנפתח מקבל את ההכרעה
    החדשה, ושומר את מה שהסבבים הקודמים כתבו בו ושאין לו תחליף עכשיו
    (agreed_text, last_round_changes, היסטוריה). סעיף CLOSED שההכרעה החדשה בו היא קבלה (A1) נשאר CLOSED; הכרעה
    שמשנה אותו בלי הוראה רשומה (reopen) נכשלת בבדיקה (STATE_REOPEN_WITHOUT_INSTRUCTION)."""
    by_id = {c.get("clause_id"): c for c in new}
    out = []
    for c in prev:
        cid = c.get("clause_id")
        if cid in by_id:
            nc = by_id.pop(cid)
            if c.get("status") == "CLOSED" and (nc.get("decision_code") == "A1" or nc.get("op") == "accept"):
                out.append(copy.deepcopy(c))
                continue
            if restores_agreed(c, nc):
                # החזרה לנוסח המוסכם אחרי שינוי שקט שלהם: הסעיף נשאר CLOSED, וזו אינה פתיחה מחדש מצדנו (S1e-R3)
                kept = copy.deepcopy(c)
                kept["restore_agreed"] = {"round": nc.get("decided_in_round"), "kind": "restore_agreed",
                                          "silent_change": nc.get("silent_change"), "op": nc.get("op"),
                                          "decision_code": nc.get("decision_code")}
                for k in ("user_decision",):
                    if nc.get(k) and not kept.get(k):
                        kept[k] = copy.deepcopy(nc[k])
                out.append(kept)
                continue
            if nc.get("carried_from") and nc.get("op") == "accept":
                # הכרעה מהסבב הקודם שהועברה לפסקה שלא השתנתה (round_tools.py carry): הסעיף נשאר כמו שהיה, כולל
                # accepted_in_round, הבדיקה המשפטית והסטטוס שנקבע בהשוואה (S1d-R2)
                out.append(copy.deepcopy(c))
                continue
            merged = copy.deepcopy(c)
            merged.update(nc)
            for k in KEEP_LISTS:
                if c.get(k) or nc.get(k):
                    merged[k] = copy.deepcopy(c.get(k) or []) + [x for x in nc.get(k) or [] if x not in (c.get(k) or [])
                                                                 and not _recorded_concession(c.get(k), x, k)]
            # STUCK שנקבע בהשוואת הסבב (apply_compare) אינו נדרס בהכרעה בלי סטטוס מפורש (S1d: write הדפיס STUCK על
            # D11 ושמר MOVING)
            if c.get("status") == "STUCK" and merged.get("status") == "MOVING":
                merged["status"] = "STUCK"
            # הסבב שבו נפתחה הבדיקה המשפטית נשמר מהסבב הראשון שבו נפתחה (השער: סעיף שלא השתנה מאז אינו חוסם)
            lr = c.get("legal_review_round") or (c.get("decided_in_round") if c.get("legal_review_required") else None)
            if lr and merged.get("legal_review_required"):
                merged["legal_review_round"] = min(int(lr), int(merged.get("legal_review_round") or lr))
            # הסבב הראשון שבו הסעיף הוכרע (decided_in_round מתעדכן בכל הכרעה חדשה)
            if c.get("first_round") or c.get("decided_in_round"):
                merged["first_round"] = int(c.get("first_round") or c.get("decided_in_round"))
            if c.get("status") == "CLOSED":
                merged["status"] = "MOVING"   # בלי reopen_log של הסבב הזה הבדיקה עוצרת, ומפנה ל-reopen
            out.append(merged)
        else:
            out.append(copy.deepcopy(c))
    out += [c for c in new if c.get("clause_id") in by_id]
    return out


def restores_agreed(prev_clause, new_clause):
    """הכרעה בסעיף CLOSED שמחזירה את הנוסח המוסכם אחרי שינוי שלא סומן של הצד השני: kind: restore_agreed בקובץ
    ההכרעות, או silent_change עם הכרעת החזרה (REVERT_OPS), כשאין לסעיף הוראת reopen בסבב הזה."""
    if prev_clause.get("status") != "CLOSED" or new_clause.get("decision_kind") == "accept_with_condition":
        # קבלה בתנאי של שינוי שקט בסעיף מוסכם אינה החזרה לנוסח המוסכם: היא פתיחה מחדש, בהוראה רשומה (reopen)
        return False
    rnd = int(new_clause.get("decided_in_round") or 0)
    if any(isinstance(r, dict) and int(r.get("round") or 0) >= rnd for r in prev_clause.get("reopen_log") or ()):
        return False
    return new_clause.get("decision_kind") == "restore_agreed" or bool(
        new_clause.get("silent_change") and new_clause.get("op") in SB.REVERT_OPS)


def merge_value(old, new, deep=True):
    """מיזוג במקום דריסה: ערך חדש ריק אינו מוחק ערך קיים; שני מילונים מתמזגים לפי מפתח (הערך החדש גובר בכל מפתח
    שיש לו ערך), ושתי רשימות מצטרפות בלי כפילות. אחרת הערך החדש גובר. כך meta.deal_context (stance, proportionality,
    counterparty_kind, existing_agreements_with_counterparty, facts) עובר לסבב הבא גם כשהשלד כותב בו facts ריק.
    deep=False: מילון שהסבב בונה מחדש (playbook_resolution מ---resolution) מתמזג רק ברמה העליונה: מפתח שהסבב כתב מחליף
    את הקודם כמו שהוא, ומפתח שלא כתב נשמר."""
    if new in EMPTY:
        return copy.deepcopy(old if old is not None else new)
    if old in EMPTY:
        return copy.deepcopy(new)
    if isinstance(old, dict) and isinstance(new, dict):
        out = copy.deepcopy(old)
        for k, v in new.items():
            out[k] = merge_value(old.get(k), v) if deep else copy.deepcopy(v if v not in EMPTY else old.get(k, v))
        return out
    if isinstance(old, list) and isinstance(new, list):
        return copy.deepcopy(old) + [copy.deepcopy(x) for x in new if x not in old]
    return copy.deepcopy(new)


def tag_round(value, rnd):
    """רשומות של סבב קודם נשמרות תחת הסבב שלהן: round בכל רשומה שאין בה. מספרי הפסקאות בהן הם של הטיוטה של אותו
    סבב, ולכן הבדיקות של סבב אחר אינן קוראות אותן (content_checks.this_round)."""
    if isinstance(value, list):
        return [dict(x, round=x.get("round") or rnd) if isinstance(x, dict) else x for x in value]
    return copy.deepcopy(value)


def carry_over(prev, st, same_round=False, gate=None, text_status_given=False):
    prev_round = int((prev.get("meta") or {}).get("round_number") or 0)
    for k, v in (prev.get("meta") or {}).items():
        if k in FRESH_META:
            continue
        # שדה שאינו בשלד עובר תמיד, גם ריק: רשימה ריקה היא רישום (למשל exposed_comments, או בדיקת ההתנגשות).
        # שדה שהסבב כותב בו מתמזג עם הקיים, ואינו מוחק אותו (S1d: deal_context נמחק כי בשלד יש facts ריק)
        st["meta"][k] = merge_value(v, st["meta"].get(k)) if k in st["meta"] else copy.deepcopy(v)
    for k in CARRY_TOP:
        st[k] = merge_value(prev.get(k), st.get(k), deep=False)
    if not same_round:
        # נקודה לשיחה מסבב שהסתיים נושאת את הסבב שלה, כדי שבסבב הבא תתעדכן לפי מצב הסעיף (talking_points.merge_points)
        for p in st.get("talking_points") or ():
            if isinstance(p, dict) and p.get("round") is None:
                p["round"] = prev_round
    for k in SAME_ROUND_TOP:
        old = prev.get(k) if same_round else tag_round(prev.get(k), prev_round)
        st[k] = merge_value(old, st.get(k))
    for k in APPEND_TOP:
        st[k] = copy.deepcopy(prev.get(k) or []) + [x for x in st.get(k) or []
                                                     if x not in (prev.get(k) or [])]
    st["clauses"] = merge_clauses(prev.get("clauses") or [], st.get("clauses") or [])
    # מפת הסעיפים מצטברת: סעיף מסבב קודם שומר את המיפוי שלו, והסבב הנוכחי מעדכן את מה שנפתח בו
    st["clause_map"] = dict(prev.get("clause_map") or {}, **(st.get("clause_map") or {}))
    nm_prev = prev.get("numbering_map") or {}
    SB.fill_clause_map(dict(st, coverage_index=list(prev.get("coverage_index") or []) + list(st.get("coverage_index")
                                                                                            or []),
                            numbering_map=dict(nm_prev, **(st.get("numbering_map") or {}))))
    # תשובה שנרשמה ב-decide לפני שהסעיף נכתב (סבב 1): נרשמת עכשיו על הסעיף שהיא חלה עליו
    for q in st.get("user_decisions") or []:
        for c in st["clauses"]:
            if c.get("clause_id") in (q.get("applies_to") or []) and not c.get("user_decision"):
                c["user_decision"] = {"question_id": q.get("id"), "answer": q.get("answer"),
                                      "answer_kind": q.get("answer_kind"), "recorded_at": q.get("recorded_at")}
                if q.get("requires_explicit"):
                    c["user_decision"].update(requires_explicit=True, outcome=q.get("outcome"))
    nm = dict(prev.get("numbering_map") or {})
    nm.update({k: v for k, v in (st.get("numbering_map") or {}).items() if v or k not in nm})
    st["numbering_map"] = nm
    st["meta"]["generated_at"] = (prev.get("meta") or {}).get("generated_at") or st["meta"]["generated_at"]
    if same_round:
        # באותו סבב: דוח השער והעותק למשלוח שכבר נרשמו נשמרים, כש-write חוזר בלי --gate (S1d-R2: send_copy נשאר null).
        # שער משלוח שנכשל ב-write הזה אינו מחזיר עותק למשלוח קודם: הוא הוסר ("לא למשלוח")
        failed_send = bool(gate) and gate.get("mode") == "send" and not gate.get("passed")
        qg, pqg = st.setdefault("quality_gate", {}), prev.get("quality_gate") or {}
        for k in ("work", "send", "send_copy"):
            if k == "send_copy" and failed_send:
                continue
            if not qg.get(k) and pqg.get(k):
                qg[k] = copy.deepcopy(pqg[k])
        # text_status עובר באותו סבב, כש-write חוזר בלי --text-status (למשל אחרי sent)
        if not text_status_given and prev.get("text_status"):
            st["text_status"] = prev["text_status"]
    return st


def place_labels_of(received, deal, decisions, numbers, lang):
    """{מזהה הכרעה: מקום} להכרעות על פסקה בלי מספר סעיף (content_checks.place_labels)."""
    if not numbers or not isinstance(decisions, dict):
        return {}
    for path in received or ():
        path = path if not path or os.path.isabs(path) else os.path.join(deal, path)
        if path and os.path.exists(path) and path.lower().endswith(".docx"):
            try:
                import content_checks
                places = content_checks.place_labels(path, lang, numbers)
            except Exception:
                return {}
            out = {}
            en = str(lang or "").lower()[:2] == "en"
            for d in decisions.get("decisions") or ():
                if not isinstance(d, dict) or not d.get("id"):
                    continue
                p = d.get("para")
                if isinstance(p, int) and p < len(places) and places[p]:
                    out[d["id"]] = places[p]
                ap = d.get("after_para")
                if d.get("op") == "insert_paragraph" and isinstance(ap, int) and ap < len(numbers):
                    # סעיף חדש: אחרי הסעיף שבהסכם, ולא "אחרי פסקה 12"
                    prev = next((numbers[k] for k in range(ap, -1, -1) if numbers[k]), None)
                    where = (("clause %s" if en else "סעיף %s") % prev) if prev else places[ap]
                    out[d["id"]] = ("New clause after %s" if en else "סעיף חדש אחרי %s") % where
            return out
    return {}


def clause_numbers_of(received, deal):
    """מספר הסעיף של כל פסקה בטיוטה שהתקבלה (content_checks.numbered_labels), למפת הסעיפים. בלי טיוטה: None."""
    for path in received or ():
        path = path if not path or os.path.isabs(path) else os.path.join(deal, path)
        if path and os.path.exists(path) and path.lower().endswith(".docx"):
            try:
                import content_checks
                return content_checks.numbered_labels(path)
            except Exception as exc:     # מפת הסעיפים נכתבת גם בלי מספרים: para ו-element_id נשארים
                print("מספרי הסעיפים לא נקראו מהטיוטה (%s). מפת הסעיפים נכתבת בלי clause_number" % exc)
                return None
    return None


def schedules_of(received, deal, numbers=None):
    """התוספת או הנספח של כל פסקה בטיוטה שהתקבלה (content_checks.schedule_of_paragraphs), לשם הסעיף במפת המספור:
    "תוספת 2, פסקה 4" ולא "סעיף 4" (S1d-R2). numbers: מספרי הסעיפים, כדי שגוף ההסכם שבא אחרי הנספחים לא ייקרא
    נספח. בלי טיוטה: None."""
    texts = received_texts_of(received, deal)
    if not texts:
        return None
    try:
        import content_checks
        return content_checks.schedule_of_paragraphs(texts, numbers)
    except Exception:  # noqa: BLE001  בלי זיהוי התוספות: המספור כמו קודם
        return None


def received_texts_of(received, deal):
    """הטקסט של כל פסקה בטיוטה שהתקבלה (קבל הכול, לפי body_paragraphs), לנוסח שקיבלנו (pending_text)."""
    for path in received or ():
        path = path if not path or os.path.isabs(path) else os.path.join(deal, path)
        if path and os.path.exists(path) and path.lower().endswith(".docx"):
            try:
                import common.docx_tracked as dt
                return dt.received_paragraphs(path)
            except Exception as exc:  # noqa: BLE001  בלי הטקסט: ההצמדה בסבב הבא לפי clause_map בלבד
                print("הטקסט של הטיוטה לא נקרא (%s). pending_text לא נרשם" % exc)
                return None
    return None


def record_sent(st, path, deal, rnd, basis="user_confirmed", edited=False):
    """רשומה אחת ב-sent_documents לכל סבב, והוויתורים המכוונים של הסבב מסומנים כנמסרו. קובץ אחר לאותו סבב מחליף את
    הרשומה הקודמת, והיא נשמרת ב-history (S1e-R3: שתי רשומות לסבב 2). אותו קובץ אינו נרשם פעמיים."""
    rec = doc_record(path, deal, "sent_at")
    rec.update(round=rnd, basis=basis, edited_before_sending=bool(edited))
    docs = st["meta"]["sent_documents"]
    same = next((d for d in docs if isinstance(d, dict) and d.get("sha256") == rec["sha256"]), None)
    replaced = []
    if same is not None:
        if str(same.get("round")) == str(rnd):
            if edited:
                same["edited_before_sending"] = True
            if basis == "user_confirmed" and same.get("basis") != "user_confirmed":
                same.setdefault("history", []).append({"basis": same.get("basis"), "until": rec["sent_at"]})
                same["basis"] = basis
        rec = same
    else:
        replaced = [d for d in docs if isinstance(d, dict) and str(d.get("round")) == str(rnd)]
        if replaced:
            hist = []
            for d in replaced:
                hist += d.get("history") or []
                hist.append(dict({k: v for k, v in d.items() if k != "history"}, replaced_at=rec["sent_at"]))
                docs.remove(d)
            rec["history"] = hist
        docs.append(rec)
    # העותק למשלוח שהיה "הופק, ממתין לשליחה" עובר ל"נשלח". כשנרשם קובץ אחר במקומו, הוא חוזר ל"הופק" ונרשם מה נשלח
    sc = (st.get("quality_gate") or {}).get("send_copy")
    if isinstance(sc, dict) and sc.get("sha256") == rec["sha256"]:
        # בסיס משוער ("לא ידוע") אינו אישור שנשלח: העותק נשאר "הופק, ממתין לשליחה"
        if rec.get("basis") != "assumed_last_work":
            sc.update(status="sent", sent_at=rec["sent_at"])
            sc.pop("sent_instead", None)
    elif isinstance(sc, dict) and sc.get("sha256") and (
            any(d.get("sha256") == sc["sha256"] for d in replaced)
            or str(rnd) == str((st.get("meta") or {}).get("round_number"))):
        if sc.get("status") == "sent":
            sc["status"] = "produced_pending_send"
            sc.pop("sent_at", None)
        sc["sent_instead"] = rec["file_name"]
    # הקובץ של הסבב הנוכחי נשלח: תגובה או טיוטה שלנו אינה עוד "שטרם נשלחה" (מעריך הסיכונים קורא את השדה)
    if str(rnd) == str((st.get("meta") or {}).get("round_number")) and (st.get("text_status") or "") in UNSENT_OURS:
        st["text_status"] = "our_sent_response"
    # "ויתור שניתן אינו נלקח בחזרה" חל רק על ויתור שנמסר לצד השני
    for w in st.get("deliberate_concessions") or ():
        if not w.get("delivered_in_round"):
            w["delivered_in_round"] = rnd
    return rec


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
    # קובץ שנוצר ב-decide לפני הכתיבה הראשונה של הסבב (אין בו קובץ הכרעות ולא נשלח דבר) הוא אותו סבב. וגם: write
    # שני באותו סבב, עם אותו קובץ הכרעות (decisions_round_<N>.json של הסבב שבקובץ). write רץ לפני השער, ושוב אחריו
    # עם --gate ו---sent, ולכן ההרצה השנייה אינה סבב חדש
    same_decisions = bool(a.decisions) and prev is not None and \
        os.path.basename(a.decisions) == "decisions_round_%d.json" % prev_round == prev.get("decisions_file")
    open_round = prev is not None and ((not prev.get("decisions_file") and not (prev.get("meta") or {}).get(
        "sent_documents")) or same_decisions)
    rnd = a.round or (prev_round if open_round else (prev_round + 1 if prev else 1))
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

    gate = load(a.gate, "דוח השער", required=False)
    lang = a.lang or ((prev or {}).get("meta") or {}).get("lang") or "he"
    decisions = load(a.decisions, "קובץ ההכרעות", required=False)
    numbers = clause_numbers_of(a.received, deal)
    # פסקה בלי מספר סעיף (מבוא, חתימות, נוסח ערבות מצורף) מקבלת שם מקום שהלקוח מוצא ב-Word, ולא "פסקה 8".
    # תווית מפורשת (--clause-labels) גוברת
    clause_labels = dict(place_labels_of(a.received, deal, decisions, numbers, lang))
    clause_labels.update(load(a.clause_labels, "מספרי הסעיפים", required=False) or {})
    st = SB.build_state(
        tid, rnd, profile=load(a.profile, "הפרופיל", required=False),
        decisions=decisions, deal_dir=deal,
        produced=produced, resolution=load(a.resolution, "תוצאת האיתור", required=False),
        gate=gate,
        concessions=load(a.concessions, "הוויתורים", required=False) or (),
        lang=lang, text_status=a.text_status, counterparty_name=a.counterparty or "",
        contract_type=a.contract_type or "",
        clause_labels=clause_labels or None,
        para_count=a.para_count, clause_numbers=numbers,
        received_texts=received_texts_of(a.received, deal), clause_schedules=schedules_of(a.received, deal, numbers))

    compare = load(a.compare, "השוואת הסבב", required=False)
    if prev is not None:
        prev = copy.deepcopy(prev)
        log = []
        SB.normalize_statuses(prev, log)
        if compare is not None and rnd > prev_round:
            # בסיס ההשוואה נרשם כקובץ שנשלח בסבב הקודם, כשאין עדיין רשומה כזו (H5)
            if not any(int(d.get("round") or 0) == prev_round for d in prev["meta"].get("sent_documents") or ()) \
                    and compare.get("sent") and os.path.exists(compare["sent"]):
                record_sent(prev, compare["sent"], deal, prev_round,
                            "assumed_last_work" if compare.get("base") == "assumed" else "compare_base")
                print("נרשם כקובץ שנשלח בסבב %d: %s (%s)" % (prev_round, os.path.basename(compare["sent"]),
                                                          "בסיס משוער" if compare.get("base") == "assumed"
                                                          else "בסיס ההשוואה"))
            # הסטטוסים לפי מה שהצד השני עשה, לפני שההכרעות של הסבב הזה נכתבות
            log += SB.apply_compare(prev, compare, rnd)
        for line in log:
            print("  %s" % line)
        st = carry_over(prev, st, same_round=rnd == prev_round, gate=gate, text_status_given=bool(a.text_status))
        # הסבב הקודם נשמר לפני שהקובץ החי משתנה. הרצה חוזרת של אותו סבב
        # אינה דורסת את העותק של הסבב הקודם
        hist = os.path.join(deal, "negotiation_state_round_%d.json" % prev_round)
        if rnd > prev_round and not os.path.exists(hist):
            dump(hist, prev)
            print("הסבב הקודם נשמר: %s" % hist)

    # העותק למשלוח שהופק בסבב (--produced send, או מהשער): "הופק, ממתין לשליחה" (S1d-R2, 28.10.2026)
    qg = st.setdefault("quality_gate", {})
    for kind, p in produced:
        if kind == "send" and not (qg.get("send_copy") or {}).get("path"):
            rec = SB.produced_document(p, deal, "send")
            qg["send_copy"] = SB.send_copy_pending({"path": rec["path"], "sha256": rec["sha256"],
                                                   "recorded_at": rec["produced_at"]})
    # תחילת שם הקובץ (סוג ההסכם והחברה) נקבעת בסבב הראשון ונשמרת ב-meta.file_prefix; apply_redlines.py משתמש בה
    # בסבבי ההמשך. קובץ מצב ישן: לפי הקובץ הראשון שהופק. שינוי (אחרי תשובה לשאלה file_prefix) נרשם עם ההיסטוריה (S1d-R2)
    fp_now = next((paths.prefix_from_name(p) for kind, p in produced if kind == "work" and paths.prefix_from_name(p)),
                  None)
    rec = st["meta"].get("file_prefix") if isinstance(st["meta"].get("file_prefix"), dict) else {}
    fp_old = (rec["agreement_type"], rec.get("company") or "") if rec.get("agreement_type") else \
        (paths.stored_prefix(prev) if prev else None)
    if fp_old or fp_now:
        cur = fp_old or fp_now
        rec = dict(rec, agreement_type=cur[0], company=cur[1])
        rec.setdefault("set_in_round", 1 if fp_old else rnd)
        if fp_old and fp_now and tuple(fp_now) != tuple(fp_old) and paths.prefix_switch_answer(st) == "switch":
            rec.setdefault("history", []).append({"agreement_type": fp_old[0], "company": fp_old[1], "until_round": rnd})
            rec.update(agreement_type=fp_now[0], company=fp_now[1], set_in_round=rnd)
        st["meta"]["file_prefix"] = rec
    pending_sha = (qg.get("send_copy") or {}).get("sha256") if (qg.get("send_copy") or {}).get("status") \
        == "produced_pending_send" else None
    for path in a.sent or ():
        p = path if os.path.isabs(path) else os.path.join(deal, path)
        if not os.path.exists(p):
            print("--sent %r אינו קיים" % path)
            return 2
        if pending_sha and sha256(p) == pending_sha:
            # העותק למשלוח של הסבב הזה אינו נרשם כנשלח בסוף הסבב, לפני שעורך הדין שלח אותו. הוא עובר ל"נשלח" באישור
            # המשתמש (negotiation_state.py sent), או בתחילת הסבב הבא (round_tools.py basis)
            print("%s הוא העותק למשלוח של הסבב: נרשם \"הופק, ממתין לשליחה\", ולא \"נשלח\". אחרי המשלוח: "
                  "negotiation_state.py sent --deal <תיקיית העסקה> --file <הקובץ>" % os.path.basename(p))
            continue
        record_sent(st, p, deal, rnd)
    for path in a.received or ():
        p = path if os.path.isabs(path) else os.path.join(deal, path)
        if not os.path.exists(p):
            print("--received %r אינו קיים" % path)
            return 2
        rec = doc_record(p, deal, "received_at")
        rec["round"] = rnd
        if rec["sha256"] not in {d.get("sha256") for d in st["meta"]["received_documents"]}:
            st["meta"]["received_documents"].append(rec)

    SB.link_silent_decisions(st, load(a.decisions, "קובץ ההכרעות", required=False))
    if prev is not None and rnd > prev_round:
        carry_time_anchors(prev, st, deal, prev_round, a.received)
    # open_items מוערך מחדש מול הסטטוס הנוכחי של כל סעיף, ופריט שהתיישן נסגר עם הסיבה (פאנל S1e-R3)
    for line in SB.refresh_open_items(st, rnd, load(a.decisions, "קובץ ההכרעות", required=False)):
        print("  %s" % line)
    from orchestrator import proportionality as P
    # תשובה מפורשת שכבר נרשמה לשאלה הנפרדת (commercial:<id>, held:<id>:r<N>, או applies_to עם הסעיף) משחררת
    answered = set()
    for q in st.get("user_decisions") or ():
        if isinstance(q, dict) and q.get("answer_kind") == "explicit":
            answered.update(str(x) for x in q.get("applies_to") or ())
            parts = str(q.get("id") or "").split(":")
            if len(parts) >= 2 and parts[0] in ("commercial", "held"):
                answered.add(parts[1])
    for v in P.commercial_concession_violations(st.get("deliberate_concessions")):
        if str(v.get("clause_ref")) in answered:
            continue
        # נושא מסחרי מחייב אינו ויתור מכוון בלי שאלה נפרדת ותשובה מפורשת (round_tools.py questions מוסיף אותה)
        print("  ויתור על נושא מסחרי מחייב בלי שאלה נפרדת: %s (%s). נשאל במנה הבאה, ואינו נמסר כוויתור עד תשובה "
              "מפורשת" % (v.get("topic"), v.get("clause_ref")))
    deal_only = isinstance(st.get("positions_source"), dict) and st["positions_source"].get("mode") == "deal_only"
    line = None if deal_only else SB.playbook_update_line(st, rnd, st["meta"].get("lang") or "he")
    if line:
        print("לשורה בסיכום: %s" % line)
    SB.summarize(st)
    open_silent = SB.unresolved_silent_changes(st, rnd)
    if open_silent:
        print("שינויים שקטים בלי הכרעה מסומנת (חוסמים משלוח): %s. ההכרעה נכנסת לקובץ ההכרעות עם silent_change: "
              "<מזהה>, בהחזרה בעקוב אחר שינויים או בקבלה עם בועה" % ", ".join(x["id"] for x in open_silent))
    print("עסקה: %s   סבב: %d (%s)" % (tid, rnd, st["meta"]["round_stage"]))
    print("סעיפים: %d   ויתורים מכוונים: %d   הכרעות משתמש: %d"
          % (len(st["clauses"]), len(st["deliberate_concessions"]), len(st["user_decisions"])))
    gaps = SB.coverage_gaps(st.get("coverage_index"))
    if gaps:
        print("רכיבים בלי הכרעה במפתח הכיסוי: %d" % len(gaps))
    infer_paper_type(st, received_texts_of(a.received, deal))
    # כלל יסוד 11: רשומת יומן לסבב, מהסבב הראשון. playbook_map.py rounds (עם השוואת הסבב) מחליף אותה באותו סבב
    try:
        import playbook_map as PM
        PM.update_ledger(st, PM.round_view(st, compare))
    except Exception as exc:  # noqa: BLE001  היומן אינו מפיל את הכתיבה
        print("יומן הסבבים לא נרשם (%s). להריץ playbook_map.py rounds" % exc)
    return write_checked(deal, st)


def infer_paper_type(st, texts):
    """meta.paper_type ריק בסוף הסבב: כשבנוסח אין שום סימן להליך תחרותי, לזכייה או לתנאים מקוונים, סוג הנייר הוא
    negotiable (n1b-learning.md, שלב א.6: "אין פריט ואין שאלה"), ונרשם עם הבסיס. כשיש סימן, השדה נשאר ריק, השאלה
    נדרשת (round_tools.py paper-type), והבדיקה מזהירה."""
    meta = st.setdefault("meta", {})
    if meta.get("paper_type") or not texts:
        return None
    try:
        from orchestrator import resolve_playbook as RPL
        res = RPL.detect_paper_type(texts)
    except Exception:  # noqa: BLE001
        return None
    if res.get("suggested") == "negotiable" and res.get("confident"):
        meta["paper_type"] = "negotiable"
        meta["paper_type_basis"] = {"answer_kind": "inferred_no_signs", "recorded_at": SB.now_iso(),
                                    "suggested": "negotiable"}
        print("סוג הנייר: אין בנוסח סימן להליך תחרותי או לתנאים מקוונים, נרשם negotiable")
        return "negotiable"
    print("סוג הנייר לא נקבע, ובנוסח יש סימנים (%s): לשאול במנה ולרשום ב-round_tools.py paper-type --set"
          % ", ".join(k for k, v in (res.get("signals") or {}).items() if v))
    return None


def carry_time_anchors(prev, st, deal, prev_round, received):
    """תשובה לעוגן זמן אינה נשאלת שוב בסבב הבא: עוגן של הסבב הקודם שאותו נוסח שלו נמצא גם בטיוטה שהתקבלה עכשיו
    נרשם גם לסבב הזה, במספר הפסקה החדש (carried_from_round). הרשומה של הסבב הקודם נשארת תחת הסבב שלה."""
    old_rec = next((d for d in (prev.get("meta") or {}).get("received_documents") or () if isinstance(d, dict)
                    and str(d.get("round")) == str(prev_round)), None)
    new_paras = received_texts_of(received, deal)
    old_paras = received_texts_of([old_rec.get("file_name")], deal) if old_rec else None
    if not old_paras:
        # הטיוטה של הסבב הקודם אינה בתיקייה (S1e-R3: העוגן "dated [ ]" לא עבר, והשער נכשל ב-TIME_ANCHOR): הפסקאות שלה
        # מהקובץ שנשלח באותו סבב, בתצוגה שהצד השני ראה (compare_rounds.base_paragraphs)
        old_paras = sent_base_texts(prev, deal, prev_round)
    if not (new_paras and old_paras):
        return
    try:
        import content_checks as CC
    except Exception:  # noqa: BLE001  בלי בדיקות התוכן: העוגן נשאל שוב, כמו קודם
        return
    old = {(x["para"], x["issue"]): x["text"] for x in CC.time_anchors(old_paras)}
    new = CC.time_anchors(new_paras)
    have = {(x.get("para"), x.get("issue")) for x in st.get("time_anchors") or () if isinstance(x, dict)
            and str(x.get("round") or st["meta"]["round_number"]) == str(st["meta"]["round_number"])}
    for x in list(st.get("time_anchors") or ()):
        if not isinstance(x, dict) or str(x.get("round")) != str(prev_round):
            continue
        text = old.get((x.get("para"), x.get("issue")))
        hit = next((n for n in new if text and n["issue"] == x.get("issue") and n["text"] == text), None)
        if hit and (hit["para"], hit["issue"]) not in have:
            rec = {k: v for k, v in x.items() if k != "round"}
            rec.update(para=hit["para"], carried_from_round=prev_round)
            st["time_anchors"].append(rec)
            have.add((hit["para"], hit["issue"]))
            print("  עוגן זמן מסבב %s (פסקה %s): אותו נוסח בפסקה %s, והתשובה עוברת" % (prev_round, x.get("para"),
                                                                                  hit["para"]))


def our_names(deal, profile=None):
    """השמות שלנו (lawyer_name, lawyer_name_en, lawyer_aliases) מהפרופיל: --profile, או Areo-נתונים/פרופיל-לקוח.json
    שמעל תיקיית העסקה."""
    prof = profile
    if prof is None:
        p = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(deal))), "פרופיל-לקוח.json")
        prof = load(p, "הפרופיל") if os.path.exists(p) else None
    if not prof:
        return []
    import lawyer
    v = lawyer.lawyer_view(prof)
    out = []
    for n in [v.get("lawyer_name"), v.get("lawyer_name_en")] + list(v.get("lawyer_aliases") or []):
        if n and str(n).strip() and str(n).strip() not in out:
            out.append(str(n).strip())
    return out


def sent_base_texts(st, deal, rnd):
    """הטקסט של כל פסקה בטיוטה שהתקבלה בסבב rnd, מהקובץ שנשלח באותו סבב: השינויים שלנו מאותו סבב דחויים, והסימונים
    הפתוחים שלנו מסבבים קודמים נשארים (compare_rounds.base_paragraphs). None כשאין קובץ כזה."""
    rec = next((d for d in reversed((st.get("meta") or {}).get("sent_documents") or []) if isinstance(d, dict)
                and str(d.get("round")) == str(rnd)), None)
    p = rec and (rec["file_name"] if os.path.isabs(rec["file_name"]) else os.path.join(deal, rec["file_name"]))
    if not p or not os.path.exists(p):
        return None
    try:
        import compare_rounds as CR
        import common.docx_tracked as dt
        ours = our_names(deal)
        return CR.base_paragraphs(dt.body_paragraphs(dt.document_root(p)), ours,
                                  CR.prior_keys(p, ours, deal, rnd))[1]
    except Exception as exc:  # noqa: BLE001  קובץ שאינו נקרא: העוגן נשאל שוב, כמו קודם
        print("הפסקאות של הקובץ שנשלח בסבב %s לא נקראו (%s)" % (rnd, exc))
        return None


def produced_for_round(st, deal, rnd):
    """העותק שהופק בסבב rnd, להשוואה מול הקובץ שנשלח: העותק למשלוח של הסבב (quality_gate.send_copy), ובלעדיו קובץ
    העבודה האחרון שהופק. רק לסבב שבקובץ המצב; לסבב קודם אין רישום אמין של מה שהופק בו."""
    if str(rnd) != str((st.get("meta") or {}).get("round_number")):
        return None
    sc = (st.get("quality_gate") or {}).get("send_copy") or {}
    cands = [sc.get("path")] + [d.get("path") for d in reversed(st.get("produced_documents") or ())
                                if isinstance(d, dict) and d.get("kind") == "work"]
    for f in cands:
        p = f and (f if os.path.isabs(f) else os.path.join(deal, f))
        if p and os.path.exists(p):
            return p
    return None


def record_lawyer_edits(st, deal, rnd, produced, sent, ours):
    """ההבדלים בין העותק שהופק לקובץ שנשלח נרשמים ב-lawyer_overrides (source: edited_before_sending, auto: true),
    במקום רשומות אוטומטיות קודמות של אותו סבב. הסעיף שעורך הדין שינה מקבל את הנוסח שנשלח: sent_text, וגם pending_text
    (ACCEPTED_PENDING) או agreed_text (CLOSED, עם ההיסטוריה), כדי שההסכמה בסבב הבא תירשם לפי מה שנשלח. מחזיר את
    הרשומות."""
    import compare_rounds as CR
    from orchestrator import question_batch as QB
    edits = CR.edits_before_sending(produced, sent, ours, CR.prior_keys(produced, ours, deal, rnd))
    dec_path = os.path.join(deal, "decisions_round_%d.json" % int(rnd))
    decs = load(dec_path, "קובץ ההכרעות") if os.path.exists(dec_path) else {}
    decs = decs.get("decisions", []) if isinstance(decs, dict) else (decs or [])
    clauses = {c.get("clause_id"): c for c in st.get("clauses") or ()}
    nm = st.get("numbering_map") or {}
    rows = []
    for e in edits:
        at = e.get("para") if isinstance(e.get("para"), int) else None
        ds = [d for d in decs if at is not None and d.get("para") == at] or \
             [d for d in decs if at is None and isinstance(e.get("after_para"), int)
              and d.get("after_para") == e["after_para"]]
        main = next((d for d in ds if d.get("op") not in (None, "accept")), None) or (ds[0] if ds else {})
        cid = main.get("id")
        cl = clauses.get(cid) or {}
        before, after = QB.diff_window(e.get("produced_text"), e.get("sent_text"), mark=False)
        rows.append({"date": SB.now_iso()[:10], "round": int(rnd), "para": e.get("para"),
                     "after_para": e.get("after_para"), "sent_para": e.get("sent_para"), "clause_id": cid,
                     "clause_ids": [d.get("id") for d in ds], "clause": nm.get(cid) or "",
                     "rule_ids": list(main.get("rule_ids") or cl.get("rule_ids") or []),
                     "decision_code": main.get("decision_code") or cl.get("decision_code") or "",
                     "kind": e["kind"], "before": before, "after": after,
                     "produced_text": e.get("produced_text") or "", "sent_text": e.get("sent_text") or "",
                     "source": "edited_before_sending", "auto": True, "candidate_for_playbook_update": False})
        if cl and e["kind"].startswith("text_") and e.get("sent_text"):
            cl["sent_text"] = e["sent_text"]
            if cl.get("pending_text"):
                cl["pending_text"] = e["sent_text"]
            if cl.get("status") == "CLOSED" and cl.get("agreed_text") and cl["agreed_text"] != e["sent_text"]:
                cl.setdefault("agreed_text_history", []).append({"text": cl["agreed_text"], "until_round": int(rnd),
                                                                 "replaced_by": "edited_before_sending"})
                cl["agreed_text"] = e["sent_text"]
    st["lawyer_overrides"] = [o for o in st.get("lawyer_overrides") or () if not (
        isinstance(o, dict) and o.get("auto") and o.get("source") == "edited_before_sending"
        and str(o.get("round")) == str(rnd))] + rows
    return rows


def cmd_decide(a):
    live = os.path.join(a.deal, LIVE)
    if os.path.exists(live):
        st = load(live, "קובץ המצב")
    else:
        # סבב 1: התשובות נרשמות לפני שקובץ המצב נכתב לראשונה (באג 5, הרצה S1b). נוצר שלד לפי המבנה, ו-write
        # בסוף הסבב ממשיך אותו באותו סבב ושומר את התשובות
        os.makedirs(a.deal, exist_ok=True)
        st = SB.skeleton()
        st["meta"].update(transaction_id=os.path.basename(os.path.abspath(a.deal)), round_number=1,
                          round_stage=SB.stage_for_round(1), generated_at=SB.now_iso(), last_updated=SB.now_iso())
        print("אין עדיין קובץ מצב בעסקה: נוצר שלד לסבב 1, וההכרעה נרשמת בו")
    # פריט שדורש תשובה מפורשת (--requires-explicit, או שנרשם כך במנת השאלות): תשובה כללית אינה מחילה את ההמלצה
    # (פאנל S1d-R2, 29.10.2026: "תציגו לנו לאישור" החיל את 48 השעות)
    req = bool(a.requires_explicit) or any(a.id in (b.get("requires_explicit") or ())
                                           for b in st.get("question_batches") or () if isinstance(b, dict))
    try:
        rec = SB.record_user_decision(st, a.id, a.situation, a.answer, a.answer_kind,
                                      applies_to=a.applies_to or (), recommendation=a.recommendation,
                                      requires_explicit=req)
    except ValueError as exc:
        print("ההכרעה לא נרשמה: %s" % exc)
        return 2
    if a.applies_to_para:
        # שאלה שנשאלה לפני שיש הכרעות (נושאים רגישים): התשובה חלה על הפסקאות, ו-content_checks קורא אותן
        rec["applies_to_paras"] = sorted(set(a.applies_to_para))
    missing = [c for c in rec["applies_to"]
               if c not in {x.get("clause_id") for x in st.get("clauses", [])}]
    if missing:
        print("אין עדיין בקובץ סעיף בשם %s. ההכרעה נשמרה ב-user_decisions, ותירשם על הסעיף כש-write יכתוב אותו"
              % ", ".join(missing))
    st["meta"]["last_updated"] = SB.now_iso()
    print("הכרעה %s: %s (%s)" % (rec["id"], rec["answer"], rec["outcome"]))
    if rec["outcome"] == SB.HELD_REQUIRES_EXPLICIT:
        print("הפריט נשאר פתוח: תשובה כללית אינה מחילה הכרעה מסוג זה (מעבר לפלייבוק, הצעה נגדית הדוקה, סכום, גבול הקו "
              "האדום או התחייבות תפעולית). ההמלצה אינה מוחלת, ובהכרעה בקובץ ההכרעות: coverage: for_call, עד תשובה "
              "מפורשת. הפריט נשאל שוב במפורש במנה הבאה")
    return write_checked(a.deal, st)


def cmd_stance(a):
    live = os.path.join(a.deal, LIVE)
    if os.path.exists(live):
        st = load(live, "קובץ המצב")
    else:
        # סבב 1: הגישה נשאלת במנת השאלות, לפני שקובץ המצב נכתב. נוצר שלד, ו-write ממשיך אותו (כמו ב-decide)
        os.makedirs(a.deal, exist_ok=True)
        st = SB.skeleton()
        st["meta"].update(transaction_id=os.path.basename(os.path.abspath(a.deal)), round_number=1,
                          round_stage=SB.stage_for_round(1), generated_at=SB.now_iso(), last_updated=SB.now_iso())
        print("אין עדיין קובץ מצב בעסקה: נוצר שלד לסבב 1, והגישה נרשמת בו")
    # בלי --round: הסבב הנוכחי לפי קובץ המצב (received_documents, sent_documents או meta.round_number), ולא
    # meta.round_number לבדו, שמתעדכן רק ב-write שבסוף הסבב (S1d-R2: הגישה נרשמה בסבב 2 כסבב 1)
    rnd = a.round or SB.current_round(st)
    try:
        rec = SB.record_stance(st, a.value, rnd, a.answer_kind)
    except ValueError as exc:
        print("הגישה לא נרשמה: %s" % exc)
        return 2
    st["meta"]["last_updated"] = SB.now_iso()
    print("הגישה: %s (סבב %d, %s)" % (rec["value"], rec["round"], rec["answer_kind"]))
    return write_checked(a.deal, st)


def cmd_sent(a):
    """הקובץ שנשלח בפועל בסבב שהסתיים (H5): העותק למשלוח, קובץ העבודה, או קובץ שעורך הדין ערך."""
    live = os.path.join(a.deal, LIVE)
    st = load(live, "קובץ המצב")
    p = a.file if os.path.isabs(a.file) else os.path.join(a.deal, a.file)
    if not os.path.exists(p):
        print("--file %r אינו קיים" % a.file)
        return 2
    rnd = a.round or int((st.get("meta") or {}).get("round_number") or 1)
    # הקובץ שנשלח שונה מהעותק שהופק באותו סבב: ההבדלים נרשמים ב-lawyer_overrides, גם בלי --edited (S1e-R3)
    produced = produced_for_round(st, a.deal, rnd) if a.basis == "user_confirmed" else None
    rows = []
    if produced and sha256(produced) != sha256(p):
        try:
            rows = record_lawyer_edits(st, a.deal, rnd, produced, p,
                                       our_names(a.deal, load(a.profile, "הפרופיל", required=False)))
        except Exception as exc:  # noqa: BLE001  הרישום נעשה גם כשההשוואה נכשלה, והדבר נאמר
            print("ההבדלים מול העותק שהופק לא נקראו (%s). הקובץ נרשם כנשלח בלי lawyer_overrides" % exc)
    rec = record_sent(st, p, a.deal, rnd, a.basis, a.edited or bool(rows))
    st["meta"]["last_updated"] = SB.now_iso()
    print("נרשם כקובץ שנשלח בסבב %d: %s (%s)%s" % (rnd, rec["file_name"], a.basis,
                                                  ". ההשוואה בסבב הבא מסומנת \"בסיס משוער\""
                                                  if a.basis == "assumed_last_work" else ""))
    if rec.get("history"):
        print("הרשומה הקודמת של סבב %d (%s) הוחלפה, ונשמרה ב-history" % (
            rnd, ", ".join(h.get("file_name") or "?" for h in rec["history"] if h.get("replaced_at"))))
    if rows:
        where = []
        for r in rows:
            lab = r.get("clause") or r.get("clause_id") or (
                "פסקה %s" % r["para"] if isinstance(r.get("para"), int) else
                "אחרי פסקה %s" % r["after_para"] if isinstance(r.get("after_para"), int) else "בועה")
            if lab not in where:
                where.append(lab)
        print("לשורה בסיכום: הקובץ שנשלח שונה מהעותק שהופק (%s) ב-%d מקומות: %s. ההבדלים נרשמו ב-lawyer_overrides, "
              "וההשוואה בסבב הבא היא מול הקובץ שנשלח" % (os.path.basename(produced), len(rows), ", ".join(where)))
    return write_checked(a.deal, st)


def cmd_reopen(a):
    st = load(os.path.join(a.deal, LIVE), "קובץ המצב")
    try:
        # בלי --round: הסבב הנוכחי (current_round), ולא meta.round_number שמתעדכן רק ב-write (S1e-R3)
        rec = SB.record_reopen(st, a.clause, a.instruction, a.reason or "", a.round or SB.current_round(st))
    except ValueError as exc:
        print("לא נפתח: %s" % exc)
        return 2
    SB.record_user_decision(st, "reopen-%s-%d" % (a.clause, rec["round"]), None, a.instruction, "explicit",
                            applies_to=[a.clause])
    SB.summarize(st)
    st["meta"]["last_updated"] = SB.now_iso()
    print("נפתח מחדש בהוראת עורך הדין: %s (היה %s), %s" % (a.clause, rec["previous_status"], rec["recorded_at"]))
    return write_checked(a.deal, st)


# --------------------------------------------------------------------------- הערות המילוי כבדיקות (n8b/n8c -> קוד)
# סקירת ארכיטקטורה 30.10.2026, סעיף 5.1ד: הערות המילוי של n8b-state-notes.md ו-n8c-state-notes.md שאפשר לבדוק
# הפכו לבדיקות כאן, עם הודעה מנחה. בקבצים נשאר רק מה שאינו ניתן לבדיקה (איך קובעים ערך). validate_state (הספרייה
# המשותפת) בודק את המבנה; כאן נבדקים ערכי השדות שהנושא ונותן כותב.
DECISION_BASES = ("PolicyDerived", "PolicyBenchmark", "UserDecided", "Law", "CompanyPractice", "ExpertJudgment")
AREO_BASES = ("UserDecided", "Law", "CompanyPractice", "ExpertJudgment")
IMPORTANCE = ("CRITICAL", "HIGH", "MEDIUM", "LOW")
DECISION_CODES = ("A1", "A2", "A3", "R1", "R2", "R3", "N1")
ROUND_BASIS = ("state", "document", "user")
PAPER_TYPES = ("negotiable", "tender_pre_bid", "tender_awarded", "standard_form_online")
TENDER_TYPES = ("tender_pre_bid", "tender_awarded", "standard_form_online")
LAST_ROUND_CHANGES = ("our_accepted", "our_accepted_partial", "our_rejected", "their_rejected_our_insert", "our_open",
                      "their_tracked", "their_silent")
SILENT_DECISIONS = ("revert", "accept_with_comment", "accept_with_condition")
WAYS = ("existing_playbook", "proposed_playbook", "none")
POSITIONS_MODES = ("playbook", "market", "both", "deal_only")   # market/both: מקובלות שוק לבקשת הלקוחה, דרך הבונה; deal_only: בלי פלייבוק ובלי שוק
BUILD_STATES = ("not_requested", "awaiting_builder", "returned", "declined", "unavailable")
RESOLUTION_RESULTS = ("match", "choose", "no_match")
PLAYBOOK_MATCH = ("match", "side_mismatch", "family_mismatch", "mutuality_mismatch", "asked")
PLAYBOOK_STATUS_READ = ("policy_gate", "unavailable")
UPDATED_BY_VALUES = ("orchestrator", "strategist")   # ערכי האנום לבדיקה; UPDATED_BY (מחרוזת) הוא מה שנכתב
DR_ANSWER_KINDS = ("explicit", "delegated", "none")
DR_OUTCOMES = ("applied_recommendation", "unanswered_for_call", "held_requires_explicit", "applied", "applied_other",
               "answered")
ENTITY_STATUS = ("value", "signing_blank", "open")
ENTITY_SOURCES = ("profile", "signed_agreement", "incorporation_certificate", "letterhead", "client_answer")
ENTITY_CHECKS = ("ok", "missing", "wrong_length", "bad_check_digit", "not_company")
MUTUAL_RESULTS = ("both_ways", "our_direction_only", "deliberate_concession", "decision_required")
INVOKERS = ("us", "them", "both")
EXPOSED_SIDES = ("them", "us")
CONCESSION_WHO = ("us", "them")
COVERAGE_DECISIONS = tuple(SB.COVERAGE_DECISIONS) + ("awaiting_playbook",)
FORBIDDEN_IMPORTANCE = ("לא נקבע", "לא מוגדר", "n/a", "unknown", "")
RULE_ID_RX = re.compile(r"^(R|V|Q|SEG|DS|LG|PB|OS|EMP)-?\d+[a-z]?$", re.I)
MAX_TALKING_POINTS = 7


def notes_checks(st):
    """בדיקות ערכי השדות (n8b/n8c). מחזיר (errors, warnings), כל אחד [{code, message, where}]. שגיאה: ערך שאינו מהרשימה
    הסגורה, או צירוף שהקבצים אוסרים; אזהרה: שדה חסר שהקבצים דורשים, כשקובץ ישן עדיין יכול להיות בלעדיו."""
    E, Wn = [], []

    def e(code, msg, where=None):
        E.append({"code": code, "message": msg, "where": where})

    def w(code, msg, where=None):
        Wn.append({"code": code, "message": msg, "where": where})

    def enum(val, allowed, code, where, field, when=True):
        if when and val is not None and val not in allowed:
            e(code, "%s חייב להיות אחד מ: %s (נמצא %r)" % (field, ", ".join(allowed), val), where)

    st = st or {}
    meta = st.get("meta") or {}
    enum(meta.get("round_basis"), ROUND_BASIS, "STATE_ROUND_BASIS", "meta/round_basis", "round_basis")
    enum(meta.get("updated_by"), UPDATED_BY_VALUES, "STATE_UPDATED_BY", "meta/updated_by", "updated_by")
    pt = meta.get("paper_type")
    # ריק (ברירת המחדל של state_builder.skeleton) הוא אזהרה בלבד, STATE_PAPER_TYPE_MISSING להלן, ולא ערך שגוי
    enum(pt or None, PAPER_TYPES, "STATE_PAPER_TYPE", "meta/paper_type", "paper_type")
    if pt in (None, ""):
        w("STATE_PAPER_TYPE_MISSING", "meta.paper_type ריק: כשאין סימן להליך תחרותי או לתנאים אחידים הערך הוא negotiable "
          "(round_tools.py paper-type --set)", "meta/paper_type")
    # כלל יסוד 11: רשומת יומן לכל סבב, מהסבב הראשון (write רושם אותה; playbook_map.py rounds מחליף אותה)
    try:
        cur_round = int(meta.get("round_number") or 1)
    except (TypeError, ValueError):
        cur_round = 1
    logged = {x.get("round") for x in meta.get("round_ledger") or [] if isinstance(x, dict)}
    missing_rounds = [r for r in range(1, cur_round + 1) if r not in logged]
    if missing_rounds:
        w("STATE_ROUND_LEDGER_MISSING", "אין רשומה ביומן הסבבים (meta.round_ledger) לסבב %s: write של סוף הסבב רושם אותה, "
          "ו-playbook_map.py rounds מחליף אותה" % ", ".join(str(r) for r in missing_rounds), "meta/round_ledger")
    if st.get("clarification_questions") and pt not in TENDER_TYPES:
        e("STATE_CLARIFICATION_NOT_TENDER", "clarification_questions ממולא רק בהליך תחרותי או בתנאים מקוונים (paper_type %r)" % pt,
          "clarification_questions")
    # קובץ ההכרעות וקובץ המצב: סעיפים
    closed_missing = {}
    for c in st.get("clauses") or []:
        if not isinstance(c, dict):
            continue
        cid = c.get("clause_id")
        enum(c.get("decision_code"), DECISION_CODES, "STATE_DECISION_CODE", cid, "decision_code")
        basis = c.get("decision_basis")
        enum(basis, DECISION_BASES, "STATE_DECISION_BASIS", cid, "decision_basis")
        ud = c.get("user_decision") or {}
        if basis == "UserDecided" and ud.get("answer_kind") != "explicit":
            e("STATE_USER_DECIDED_NOT_EXPLICIT", "UserDecided רק עם תשובה מפורשת של המשתמש (user_decision.answer_kind: "
              "explicit); תשובה כללית היא delegated והבסיס הוא מקור ההמלצה", cid)
        # source_label: areo_proposal נבדק בקובץ ההכרעות (content_checks AREO_LABEL_MISSING); בקובץ המצב השדה הוא תווית תצוגה
        imp = c.get("importance")
        if imp is not None and (imp not in IMPORTANCE or str(imp).strip().lower() in FORBIDDEN_IMPORTANCE):
            e("STATE_IMPORTANCE", "importance חייב להיות CRITICAL, HIGH, MEDIUM או LOW; \"לא נקבע\" ו\"לא מוגדר\" אינם ערכים (נמצא %r)" % imp, cid)
        rids = c.get("rule_ids")
        if rids is not None:
            if not isinstance(rids, list):
                e("STATE_RULE_IDS", "rule_ids הוא רשימה של מזהי כללים, ולא מחרוזת אחת (%r)" % rids, cid)
            else:
                for r in rids:
                    if str(r) in DECISION_CODES:
                        e("STATE_RULE_IDS", "קוד הכרעה (%s) אינו מזהה כלל: rule_ids מקבל מזהי כללים מהפלייבוק בלבד" % r, cid)
        if "legal_review" in c:
            w("STATE_LEGAL_REVIEW_FIELD", "אין סימון \"נבדק\" של עורך דין בעסקה (כלל יסוד 6): legal_review אינו נכתב; "
              "legal_review_required הוא מידע בלבד", cid)
        dr = c.get("decision_required")
        if isinstance(dr, dict):
            if dr.get("required") is True and not dr.get("situation"):
                e("STATE_DECISION_REQUIRED", "decision_required.required: true רק באחד מתשעת המצבים (situation)", cid)
            enum(dr.get("answer_kind"), DR_ANSWER_KINDS, "STATE_DECISION_REQUIRED", cid, "decision_required.answer_kind")
            enum(dr.get("outcome"), DR_OUTCOMES, "STATE_DECISION_REQUIRED", cid, "decision_required.outcome")
            if dr.get("answer_kind") == "delegated" and dr.get("outcome") not in (None, "applied_recommendation", "held_requires_explicit"):
                e("STATE_DECISION_REQUIRED", "תשובה delegated נרשמת outcome: applied_recommendation (או held_requires_explicit "
                  "כשהפריט דורש תשובה מפורשת)", cid)
            if dr.get("answer_kind") == "delegated" and basis == "UserDecided":
                e("STATE_USER_DECIDED_NOT_EXPLICIT", "delegated אינו UserDecided: הבסיס הוא מקור ההמלצה", cid)
        for lr in c.get("last_round_changes") or []:
            cls = lr.get("classification") if isinstance(lr, dict) else lr
            enum(cls, LAST_ROUND_CHANGES, "STATE_LAST_ROUND_CHANGE", cid, "last_round_changes[].classification")
        mc = c.get("mutual_check")
        if isinstance(mc, dict):
            enum(mc.get("result"), MUTUAL_RESULTS, "STATE_MUTUAL_CHECK", cid, "mutual_check.result")
            enum(mc.get("likely_invoker"), INVOKERS, "STATE_MUTUAL_CHECK", cid, "mutual_check.likely_invoker")
        if c.get("status") == "CLOSED":
            missing = [k for k in ("agreed_text", "closed_in_round", "closed_basis") if not c.get(k)]
            if missing:
                closed_missing.setdefault(tuple(missing), []).append(cid)
        if c.get("status") == "ACCEPTED_PENDING" and not c.get("pending_text") and "pending_text" in c:
            w("STATE_PENDING_FIELDS", "סעיף ACCEPTED_PENDING ממלא pending_text ו-accepted_in_round", cid)
    for missing, ids in closed_missing.items():
        w("STATE_CLOSED_FIELDS", "%d סעיפים CLOSED בלי %s (סעיף CLOSED ממלא agreed_text, closed_in_round ו-closed_basis)"
          % (len(ids), ", ".join(missing)), ", ".join(str(x) for x in ids[:8]) + (" ..." if len(ids) > 8 else ""))
    for x in st.get("concession_history") or []:
        if isinstance(x, dict):
            enum(x.get("who"), CONCESSION_WHO, "STATE_CONCESSION_WHO", x.get("clause_id") or x.get("topic"), "concession_history[].who")
    # שינויים שקטים של הסבב הנוכחי: הכרעה והפניה (state_builder.unresolved_silent_changes), וסוג ההכרעה
    for s in st.get("silent_changes") or []:
        if isinstance(s, dict):
            enum(s.get("decision"), SILENT_DECISIONS, "STATE_SILENT_DECISION", s.get("id"), "silent_changes[].decision")
    try:
        for s in SB.unresolved_silent_changes(st):
            w("SILENT_CHANGE_UNDECIDED", "שינוי שקט של הסבב בלי decision ו-decision_ref: חוסם משלוח בשער", s.get("id"))
    except Exception:  # noqa: BLE001
        pass
    # מקור העמדות ופתרון הפלייבוק
    ps = st.get("positions_source") if isinstance(st.get("positions_source"), dict) else {}
    enum(ps.get("way"), WAYS, "STATE_POSITIONS_WAY", "positions_source/way", "positions_source.way")
    enum(ps.get("mode") or None, POSITIONS_MODES, "STATE_POSITIONS_MODE", "positions_source/mode", "positions_source.mode")
    if ps.get("mode") == "deal_only":
        # בלי פלייבוק: אין מקור פלייבוק ואין בנייה שממתינה לבונה; playbook_resolution אינו נדרש
        if ps.get("way") not in (None, "", "none"):
            e("STATE_POSITIONS_MODE", "ב-deal_only ה-way הוא none (או חסר)", "positions_source/way")
        if (ps.get("proposed_playbook") or {}).get("build_state") == "awaiting_builder":
            e("STATE_POSITIONS_MODE", "ב-deal_only אין בנייה שממתינה לבונה (build_state: awaiting_builder)",
              "positions_source/proposed_playbook/build_state")
    pp = ps.get("proposed_playbook") if isinstance(ps.get("proposed_playbook"), dict) else {}
    bs = pp.get("build_state")
    enum(bs, BUILD_STATES, "STATE_BUILD_STATE", "positions_source/proposed_playbook/build_state", "build_state")
    if bs == "awaiting_builder" and ps.get("way") not in (None, "proposed_playbook"):
        e("STATE_BUILD_STATE", "כל עוד build_state הוא awaiting_builder, way הוא proposed_playbook", "positions_source/way")
    for i, ce in enumerate(st.get("coverage_index") or []):
        if not isinstance(ce, dict):
            continue
        enum(ce.get("decision"), COVERAGE_DECISIONS, "STATE_COVERAGE_DECISION", "coverage_index[%d]" % i, "coverage_index[].decision")
        if ce.get("decision") == "awaiting_playbook" and bs != "awaiting_builder":
            e("STATE_AWAITING_PLAYBOOK", "awaiting_playbook תקין רק כש-build_state הוא awaiting_builder", "coverage_index[%d]" % i)
        if ce.get("decision") and not ce.get("reason"):
            e("STATE_COVERAGE_REASON", "רשומה במפתח הכיסוי בלי reason", "coverage_index[%d]" % i)
    pr = st.get("playbook_resolution") if isinstance(st.get("playbook_resolution"), dict) else {}
    res = pr.get("result")
    enum(res, RESOLUTION_RESULTS, "STATE_PLAYBOOK_RESOLUTION", "playbook_resolution/result", "playbook_resolution.result")
    if res in ("choose", "no_match") and pr.get("chosen"):
        e("STATE_PLAYBOOK_RESOLUTION", "chosen ריק בכל מה שאינו match", "playbook_resolution/chosen")
    if res == "choose" and not pr.get("question"):
        e("STATE_PLAYBOOK_RESOLUTION", "ב-choose השאלה האחת (question) נכנסת למנת השאלות כלשונה", "playbook_resolution/question")
    if pr and "activation_ok" not in pr:
        w("STATE_ACTIVATION_OK_MISSING", "playbook_resolution נושא תמיד activation_ok (true/false, null כשלא נבחר פלייבוק)",
          "playbook_resolution/activation_ok")
    pst = st.get("playbook_status") if isinstance(st.get("playbook_status"), dict) else {}
    enum(pst.get("read_from"), PLAYBOOK_STATUS_READ, "STATE_PLAYBOOK_STATUS", "playbook_status/read_from", "playbook_status.read_from")
    pos = meta.get("position") if isinstance(meta.get("position"), dict) else {}
    enum(pos.get("playbook_match"), PLAYBOOK_MATCH, "STATE_POSITION_MATCH", "meta/position/playbook_match", "position.playbook_match")
    # ישות, הערות שנחשפו, פסיקה, מסמכי העסקה, דו-לשוני, רשימת החתימה
    ed = st.get("entity_details") if isinstance(st.get("entity_details"), dict) else {}
    for k, v in ed.items():
        if isinstance(v, dict):
            enum(v.get("status"), ENTITY_STATUS, "STATE_ENTITY_DETAIL", "entity_details/%s" % k, "entity_details.status")
            enum(v.get("source"), ENTITY_SOURCES, "STATE_ENTITY_DETAIL", "entity_details/%s" % k, "entity_details.source")
            enum(v.get("check"), ENTITY_CHECKS, "STATE_ENTITY_DETAIL", "entity_details/%s" % k, "entity_details.check")
            if v.get("status") == "value" and v.get("check") not in (None, "ok"):
                e("STATE_ENTITY_DETAIL", "status: value רק כשהבדיקה עברה (check: ok)", "entity_details/%s" % k)
    for i, x in enumerate(meta.get("exposed_comments") or []):
        if isinstance(x, dict):
            enum(x.get("side"), EXPOSED_SIDES, "STATE_EXPOSED_SIDE", "meta/exposed_comments[%d]" % i, "exposed_comments[].side")
            if not x.get("quote"):
                e("STATE_EXPOSED_QUOTE", "exposed_comments שומר את ההערה במלואה (quote)", "meta/exposed_comments[%d]" % i)
    cl = st.get("case_law") if isinstance(st.get("case_law"), dict) else None
    if cl is not None:
        conn = cl.get("connector")
        if conn in (None, "", "אין", "none") and cl.get("rulings"):
            e("STATE_CASE_LAW", "כש-case_law.connector הוא \"אין\", rulings ריק: אין פסיקה בלי מחבר (כלל יסוד 2)", "case_law")
    dd = meta.get("deal_documents") if isinstance(meta.get("deal_documents"), dict) else {}
    for i, cf in enumerate(dd.get("conflicts") or []):
        if isinstance(cf, dict) and not cf.get("decision"):
            e("STATE_DEAL_DOC_CONFLICT", "סתירה בין מסמכי העסקה בלי decision באותו סבב", "meta/deal_documents/conflicts[%d]" % i)
    bl = meta.get("bilingual") if isinstance(meta.get("bilingual"), dict) else {}
    for i, mm in enumerate(bl.get("mismatches") or []):
        if isinstance(mm, dict) and not (mm.get("origin") and mm.get("decision")):
            e("STATE_BILINGUAL_MISMATCH", "פער בין הגרסאות נרשם עם origin ו-decision", "meta/bilingual/mismatches[%d]" % i)
    sc = st.get("signing_checklist") if isinstance(st.get("signing_checklist"), dict) else {}
    if sc:
        open_items = [x for x in sc.get("checks") or () if isinstance(x, dict) and x.get("status") == "open"]
        if sc.get("passed") is True and open_items:
            e("STATE_SIGNING_PASSED", "signing_checklist.passed: true רק כשאין אף פריט פתוח (%d פתוחים)" % len(open_items), "signing_checklist")
        if sc.get("clean_copy_path") and not sc.get("passed"):
            e("STATE_SIGNING_CLEAN_COPY", "clean_copy_path נכתב רק אחרי passed: true", "signing_checklist")
    # קבצים שנשלחו והתקבלו: רשומה אחת לכל סבב, עם נתיב וטביעת אצבע
    seen_rounds = set()
    for i, d in enumerate(meta.get("sent_documents") or []):
        if not isinstance(d, dict):
            continue
        r = d.get("round")
        if r in seen_rounds:
            w("STATE_SENT_DUPLICATE", "sent_documents: רשומה אחת לכל סבב; קובץ אחר לאותו סבב מחליף את הקודמת (history)",
              "meta/sent_documents[%d]" % i)
        seen_rounds.add(r)
        if not (d.get("path") or d.get("file_name") or d.get("file")):
            e("STATE_SENT_FIELDS", "רשומת קובץ שנשלח בלי נתיב", "meta/sent_documents[%d]" % i)
    tps = [t for t in st.get("talking_points") or () if isinstance(t, dict)
           and t.get("status") not in ("closed_in_call", "superseded")]
    if len(tps) > MAX_TALKING_POINTS:
        w("STATE_TALKING_POINTS", "talking_points מציג עד %d נקודות לפי priority (%d פתוחות)" % (MAX_TALKING_POINTS, len(tps)),
          "talking_points")
    for i, t in enumerate(st.get("talking_points") or []):
        if isinstance(t, dict) and t.get("source") == "auto" and not str(t.get("id") or "").startswith("auto:"):
            e("STATE_TALKING_POINT_ID", "נקודה של הכלי נושאת id \"auto:<kind>:<מזהה הכרעה>\"", "talking_points[%d]" % i)
    qg = st.get("quality_gate") if isinstance(st.get("quality_gate"), dict) else {}
    for k in ("work", "send"):
        g = qg.get(k)
        if g and (not isinstance(g, dict) or not isinstance(g.get("passed"), bool)
                  or ("codes" in g and g["codes"] is not None and not isinstance(g["codes"], list))):
            e("STATE_QUALITY_GATE", "quality_gate.%s: {\"passed\": bool, \"codes\": [...]} (ריק עד שהשער רץ)" % k, "quality_gate/%s" % k)
    for i, lo in enumerate(st.get("lawyer_overrides") or []):
        if isinstance(lo, dict) and not (lo.get("clause_id") and (("before" in lo and "after" in lo)
                                                                  or ("produced_text" in lo and "sent_text" in lo))):
            e("STATE_LAWYER_OVERRIDE", "רשומת lawyer_overrides: clause_id, והנוסח שהופק מול הנוסח שנשלח (before/after או "
              "produced_text/sent_text)", "lawyer_overrides[%d]" % i)
    return E, Wn


def cmd_check(a):
    st = load(os.path.join(a.deal, LIVE), "קובץ המצב")
    errors = SB.validate_state(st)
    bad_ts = SM.non_iso_timestamps(st)
    n_err, n_warn = notes_checks(st)
    errors = list(errors) + n_err
    for x in n_warn:
        print("  אזהרה [%s] %s%s" % (x["code"], x["message"], "  (%s)" % x["where"] if x.get("where") else ""))
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
    misplaced = [k for k in SB.ROOT_ONLY if k in (old.get("meta") or {})]   # עוגני זמן ב-meta: עוברים לשורש
    # CLOSED מוקדם (H2), ושדות meta שנכתבו בשורש: גם הם המרה
    early = [c for c in old.get("clauses") or () if SB.premature_closed(old, c)]
    stray = [k for k in ("last_updated", "updated_by", "date") if k in old]
    if str((old.get("meta") or {}).get("schema_version")) == SB.SCHEMA_VERSION and not (misplaced or early or stray):
        print("הקובץ כבר במבנה הנוכחי (%s). אין מה להמיר." % SB.SCHEMA_VERSION)
        return 0
    legacy = SM.history_path(a.deal, old)
    if os.path.exists(legacy):
        print("כבר קיים %s. הקובץ הישן אינו נדרס" % legacy)
        return 2
    new, log = SM.migrate_state(old)
    SB.fill_clause_map(new)
    os.makedirs(os.path.dirname(legacy), exist_ok=True)
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
    w.add_argument("--lang", choices=("he", "en"), help="בלעדיו: מהקובץ הקיים, או he")

    d = sub.add_parser("decide", help="הכרעה של המשתמש")
    d.add_argument("--deal", required=True)
    d.add_argument("--id", required=True, help="מזהה השאלה")
    d.add_argument("--situation", type=int, choices=list(SB.SITUATIONS),
                   help='אחד מתשעת המצבים של "נדרשת הכרעתך"')
    d.add_argument("--answer", required=True, help="התשובה, במילים של המשתמש")
    d.add_argument("--answer-kind", required=True, choices=SB.ANSWER_KINDS,
                   help="explicit: המשתמש הכריע. delegated: המשתמש אמר להחיל את ההמלצה")
    d.add_argument("--applies-to", action="append", help="clause_id שההכרעה חלה עליו")
    d.add_argument("--applies-to-para", action="append", type=int,
                   help="מספר פסקה בטיוטה שהתקבלה (מ-0) שההכרעה חלה עליה, לשאלה שנשאלה לפני ההכרעות (sensitive_topics: "
                        "הפסקאות שבפריט, paras)")
    d.add_argument("--recommendation", help="ההמלצה שהוצגה למשתמש")
    d.add_argument("--requires-explicit", action="store_true",
                   help="הפריט דורש תשובה מפורשת (מצב 2, counter_tighter, סכום, גבול הקו האדום, התחייבות תפעולית): "
                        "תשובה כללית נרשמת ואינה מחילה את ההמלצה. בלעדיו: לפי question_batches בקובץ המצב")

    s = sub.add_parser("stance", help="הגישה להחלת הפלייבוק בעסקה")
    s.add_argument("--deal", required=True)
    s.add_argument("--value", required=True, choices=SB.STANCES,
                   help="playbook: לפי הפלייבוק (ההמלצה); stricter: מחמירה; lenient: מקלה")
    s.add_argument("--answer-kind", required=True, choices=SB.ANSWER_KINDS,
                   help="explicit: המשתמש בחר; delegated: בלי תשובה או \"לפי ההמלצה\", ואז playbook")
    s.add_argument("--round", type=int, help="הסבב שבו נקבעה; בלעדיו: הסבב שבקובץ המצב")

    w.add_argument("--compare", help="הפלט של compare_rounds.py לסבב הזה: CLOSED, MOVING, STUCK ושינויים שקטים")

    sn = sub.add_parser("sent", help="הקובץ שנשלח בפועל בסבב שהסתיים")
    sn.add_argument("--deal", required=True)
    sn.add_argument("--file", required=True, help="הקובץ שנשלח: העותק למשלוח, קובץ העבודה, או קובץ שנערך")
    sn.add_argument("--round", type=int, help="בלעדיו: הסבב שבקובץ המצב")
    sn.add_argument("--basis", choices=("user_confirmed", "assumed_last_work"), default="user_confirmed",
                    help="assumed_last_work: לא ידוע מה נשלח, וההשוואה מול קובץ העבודה האחרון (בסיס משוער)")
    sn.add_argument("--edited", action="store_true", help="עורך הדין ערך את הקובץ לפני המשלוח. ההבדלים מול העותק "
                                                          "שהופק נרשמים ב-lawyer_overrides גם בלעדיו")
    sn.add_argument("--profile", help="פרופיל-לקוח.json: השמות שלנו. בלעדיו: הפרופיל שמעל תיקיית העסקה")

    ro = sub.add_parser("reopen", help="הוראה רשומה של עורך הדין לפתוח מחדש סעיף מוסכם או ויתור שנמסר")
    ro.add_argument("--deal", required=True)
    ro.add_argument("--clause", required=True, help="clause_id")
    ro.add_argument("--instruction", required=True, help="ההוראה, במילים של עורך הדין")
    ro.add_argument("--reason", help="הסיבה, למשל: הוסכם בשיחה מיום ...")
    ro.add_argument("--round", type=int, help="בלעדיו: הסבב שבקובץ המצב")

    c = sub.add_parser("check", help="בדיקת הקובץ מול המבנה")
    c.add_argument("--deal", required=True)

    m = sub.add_parser("migrate", help="המרת קובץ בפורמט ישן")
    m.add_argument("--deal", required=True)

    a = ap.parse_args(argv)
    return {"write": cmd_write, "decide": cmd_decide, "stance": cmd_stance, "check": cmd_check,
            "migrate": cmd_migrate, "sent": cmd_sent, "reopen": cmd_reopen}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
