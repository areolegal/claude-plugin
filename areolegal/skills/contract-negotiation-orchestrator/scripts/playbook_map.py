#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""מיפוי הפלייבוק להסכם, ויומן הסבבים: כללי היסוד 9, 11, 12 ו-15 של Areo בקוד.

הקובץ הזה אינו מכיל נושא, סוג הסכם, צד או דין. הכול מגיע מהפלייבוק של הלקוח, מקובץ ההכרעות ומקובץ המצב.
הוא קורא קבצים מקומיים בלבד (תיקיית העסקה והפלייבוק שהלקוח חיבר), ואינו פונה לשום שרת.

**1. מיפוי הפלייבוק להסכם (כלל 15).** בכל ריצה נבנית מפה אחת: כל סעיף בפלייבוק <- הסעיף או הסעיפים בהסכם.
לכל סעיף בפלייבוק בדיוק תוצאה רשומה אחת מתוך שלוש:

| תוצאה | משמעות | מה נרשם |
|---|---|---|
| `applied` | הפלייבוק הוחל בסימון, בבועה או בהערה | העמדה, המקור (הסכם וסעיף), הסעיפים בהסכם, מזהי ההכרעות |
| `accepted_as_is` | הנוסח בהסכם מקובל כמו שהוא | העמדה, המקור, הסעיפים בהסכם והסיבה |
| `no_matching_clause` | אין בהסכם סעיף לנושא | העמדה והמקור של מה שהיה מוחל, ואם נוסף סעיף: ההכרעה שהוסיפה אותו |

תוצאה נגזרת מההכרעות (`rule_ids` בכל הכרעה). סעיף בפלייבוק שאין עליו הכרעה נרשם ביד, ב-`declare`, כ-
`accepted_as_is` (עם הסעיפים בהסכם והסיבה) או כ-`no_matching_clause`. סעיף בפלייבוק בלי תוצאה כלל
הוא כשל (`PLAYBOOK_RULE_NO_OUTCOME`): הבדיקה נכשלת, ולא מדלגים בשקט.

**הכיוון ההפוך.** כל סעיף בהסכם שאין לו סעיף מקביל בפלייבוק נרשם ב-`unmatched_agreement_clauses`, עם הודעה
קבועה ללקוח: אין סעיף בפלייבוק, והתשובה ניתנת על בסיס שיקול הדעת המקצועי של AREO, בלי פסיקה ובלי מקורות שלא
אושרו. ההודעה מוצגת בסיכום ללקוח וביומן הפנימי, ואינה נכנסת לעותק שהצד השני רואה.

**2. מקור (כלל 12).** לכל עמדה נרשם ההסכם והסעיף שעליהם היא נשענת, כפי שהפלייבוק רושם אותם. כשהפלייבוק
אינו נושא מקור לעמדה: "AREO לא מצאה מקור מורשה לנקודה זו", ומה עושים הלאה. לעולם לא ממלאים מהזיכרון.
`annotate` כותב את שורת המקור בבועה הפנימית של כל הכרעה (לא בבועה לצד השני: שם לא נקראים הסכמים אחרים).

**3. יומן הסבבים (כלל 11).** לכל סבב נגזר מקובץ המצב: מה הוסכם, מה פתוח, ואיזה סעיף מוסכם הצד השני החזיר
לאחור. סבב 1, 2, 3, 4 ואילך מובחנים בשם. מטפלים רק בפתוחים, ואין פותחים מחדש סעיף מוסכם.

כל מה שנרשם נכנס ל-`meta.playbook_map` ול-`meta.round_ledger` בקובץ המצב של העסקה (מפתח: `meta.transaction_id`).

    python "AREO_RT/skills/contract-negotiation-orchestrator/scripts/playbook_map.py" build --playbook <core|model>.json \\
        --decisions decisions_round_<N>.json --deal "Areo-נתונים/transactions/<id>" [--received <טיוטה>.docx]
    ... declare --deal <תיקייה> --rule R-07 --outcome no_matching_clause [--reason "..."]
    ... check   --playbook <core|model>.json --deal <תיקייה> [--mode work|send]
    ... annotate --playbook <core|model>.json --decisions decisions_round_<N>.json
    ... rounds  --deal <תיקייה> [--compare round-compare.json]

**כיסוי מלא של כללי הפלייבוק (n4d-rule-coverage.md).** לפני העריכה: `plan` כותב שלד ל-`<העסקה>/rule-coverage.json`,
`check-plan` בודק שכל כלל בו ושכל שדה מלא. אחרי העריכה: `result` רושם לכל כלל אחת מארבע תוצאות
(applied_full | applied_partial | not_applied | not_applicable), ו-`check --decisions` מריץ את בדיקות הכיסוי:
RULE_COVERAGE_PLAN_MISSING, RULE_PLANNED_NOT_RESOLVED, RULE_APPLIED_BY_COMMENT_ONLY, RULE_PARTIAL_MARKED_FULL,
EQUIVALENCE_MISSING, OPENING_DEPARTURE_UNEXPLAINED, POSITION_BASIS_MISSING, BASIS_APPROVAL_UNSUPPORTED (חוסמים משלוח),
ו-APPROVAL_OPEN_MISSING (אינו חוסם).

    ... plan       --playbook <core>.json --deal <תיקייה> [--force]
    ... check-plan --playbook <core>.json --deal <תיקייה>
    ... result     --deal <תיקייה> --rule R-07 --result applied_full|applied_partial|not_applied|not_applicable
                   [--reason "..."] [--decision D1 --decision D2]

קוד יציאה: **0** תקין, **3** יש ממצא חוסם, **2** קלט חסר.
"""
import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # גם ב-python -I, שאינו מוסיף את תיקיית הסקריפט
import areo_lib  # noqa: F401  מוסיף את areolegal/lib לנתיב הייבוא (ו-UTF-8 לפלט)

OUTCOMES = ("applied", "accepted_as_is", "no_matching_clause")
CHANGING_OPS = ("replace", "replace_span", "insert_paragraph", "delete_paragraph", "comment_only")
TRACKS = ("green", "yellow", "red")
LIVE = "negotiation_state.json"

NOTICE = {
    "he": "אין סעיף בפלייבוק לנושא הזה. התשובה ניתנת על בסיס שיקול הדעת המקצועי של AREO, בלי פסיקה ובלי מקורות שלא אושרו.",
    "en": "The playbook has no clause on this topic. AREO answered on its own professional judgment, "
          "with no case law and no unapproved sources."}
NO_SOURCE = {
    "he": "AREO לא מצאה מקור מורשה לנקודה זו. הצעד הבא: להוסיף לתיקיית הסכמים של החברה הסכם שמסדיר אותה, או לאשר "
          "את העמדה בפלייבוק.",
    "en": "AREO did not find an approved source for this point. Next step: add to the company's agreements folder an "
          "agreement that covers it, or confirm the position in the playbook."}
SOURCE_PREFIX = {"he": "מקור: ", "en": "Source: "}

ROUND_NAMES = {1: ("first", "סבב ראשון", "Round 1 (first)"), 2: ("second", "סבב שני", "Round 2 (second)"),
               3: ("third", "סבב שלישי", "Round 3 (third)"), 4: ("fourth", "סבב רביעי", "Round 4 (fourth)")}
ROUND_RULE = {
    "first": ("סבב ראשון: הפלייבוק מוחל במלואו על ההסכם. כל הנקודות פתוחות.",
              "First round: the whole playbook is applied to the agreement. Every point is open."),
    "other": ("סבב המשך: מטפלים רק בנקודות הפתוחות. מה שהוסכם אינו נפתח מחדש.",
              "Follow-up round: only the open points are handled. Agreed points are not reopened.")}


# --------------------------------------------------------------------------- קריאת הפלייבוק
def _text(v):
    if isinstance(v, dict):
        for k in ("he", "text", "en"):
            if isinstance(v.get(k), str) and v[k].strip():
                return v[k].strip()
        return ""
    return v.strip() if isinstance(v, str) else ""


def rules_of(playbook):
    """רשימת הכללים בפלייבוק, בכל אחת משתי הצורות (הגרעין: clauses[], המודל: rules[])."""
    pb = playbook if isinstance(playbook, dict) else {}
    out = []
    for r in pb.get("clauses") or pb.get("rules") or []:
        if isinstance(r, dict) and (r.get("id") or r.get("rule_id")):
            out.append(r)
    return out


def rule_id(r):
    return r.get("id") or r.get("rule_id")


def rule_topic(r):
    return _text(r.get("title") or r.get("topic_name") or r.get("topic")) or str(rule_id(r))


def rule_position(r, track=None):
    """(מסלול, טקסט העמדה). בלי מסלול: הירוק, ואם אין, הצהוב, ואם אין, האדום."""
    tl = r.get("traffic_light") if isinstance(r.get("traffic_light"), dict) else {}
    for t in ([track] if track in TRACKS else []) + list(TRACKS):
        cell = tl.get(t) if isinstance(tl.get(t), dict) else (r.get(t) if isinstance(r.get(t), dict) else {})
        txt = _text(cell.get("position")) or (_text(cell.get("red_line")) if t == "red" else "")
        if txt:
            return t, txt
    return None, ""


def _source_titles(playbook):
    out = {}
    for s in (playbook or {}).get("source_log") or []:
        if isinstance(s, dict) and s.get("source_id"):
            out[s["source_id"]] = _text(s.get("short_name") or s.get("title") or s.get("file"))
    return out


def rule_sources(r, playbook=None):
    """[{agreement, clause, source_id}]: ההסכמים והסעיפים שהעמדה נשענת עליהם, כפי שהפלייבוק רושם אותם
    (evidence[] עם source_ref ו-clause_ref, ובמודל source_log למעבר משם המקור לשם ההסכם). כלל שרושם רק תווית מקור
    (source_label) מקבל רשומה עם label."""
    titles = _source_titles(playbook)
    out, seen = [], set()
    for ev in r.get("evidence") or []:
        if not isinstance(ev, dict):
            continue
        sid = ev.get("source_ref") or ev.get("source_id")
        agr = titles.get(sid) or _text(ev.get("agreement") or ev.get("source_title")) or sid
        cl = _text(ev.get("clause_ref") or ev.get("clause"))
        if agr and (agr, cl) not in seen:
            seen.add((agr, cl))
            out.append({"agreement": agr, "clause": cl, "source_id": sid or ""})
    tl = r.get("traffic_light") if isinstance(r.get("traffic_light"), dict) else {}
    for t in TRACKS:
        cell = tl.get(t) if isinstance(tl.get(t), dict) else (r.get(t) if isinstance(r.get(t), dict) else {})
        lab = _text(cell.get("source_label")) or _text(r.get("source_label"))
        if lab and ("label", lab) not in seen:
            seen.add(("label", lab))
            out.append({"agreement": "", "clause": "", "label": lab})
    if r.get("policy_status") in ("market_standard", "areo_proposal") or r.get("basis") in ("market_standard", "areo_proposal"):
        out.append({"agreement": "", "clause": "", "label": r.get("basis") or r.get("policy_status")})
    return out


def source_text(sources, lang="he"):
    """שורת המקור לתצוגה: 'מקור: <הסכם>, <סעיף>; ...'. בלי מקור: ההודעה 'AREO לא מצאה מקור מורשה לנקודה זו'."""
    L = "en" if lang == "en" else "he"
    parts = []
    for s in sources or []:
        if s.get("agreement"):
            parts.append("%s, %s" % (s["agreement"], s["clause"]) if s.get("clause") else s["agreement"])
        elif s.get("label"):
            parts.append(s["label"])
    return (SOURCE_PREFIX[L] + "; ".join(parts)) if parts else NO_SOURCE[L]


# --------------------------------------------------------------------------- בניית המפה
def _agreement_clauses(paras, labels, structural):
    """הסעיפים בהסכם שהמיפוי מתייחס אליהם: פסקה לא ריקה עם מספר סעיף, ובלי מספור: פסקה של שמונה מילים ומעלה.
    כותרות ופסקאות מבניות אינן סעיף."""
    out = []
    for i, t in enumerate(paras or []):
        t = (t or "").strip()
        if not t or i in structural:
            continue
        lab = labels[i] if labels and i < len(labels) else None
        if lab or len(t.split()) >= 8:
            out.append((i, lab or None))
    return out


def build_map(playbook, decisions, round_number=1, deal_id="", paras=None, labels=None, declared=None, lang="he",
              coverage=None):
    """מפה אחת לריצה. decisions: רשימת ההכרעות. declared: [{rule_id, outcome, agreement_paras, reason}] שנרשמו ביד.
    paras ו-labels: פסקאות ההסכם שהתקבל ומספרי הסעיפים (בלעדיהם אין זיהוי של סעיפים בלי התאמה בפלייבוק)."""
    L = "en" if lang == "en" else "he"
    ds_all = [d for d in decisions or [] if isinstance(d, dict)]
    declared = {x.get("rule_id"): x for x in declared or [] if isinstance(x, dict) and x.get("rule_id")}

    def label(i):
        lab = labels[i] if labels and isinstance(i, int) and 0 <= i < len(labels) else None
        return lab or ("פסקה %s" % i if L == "he" else "paragraph %s" % i)

    cov_res = coverage_results_view(coverage) if coverage else {}
    rules_out, matched = [], set()
    for r in rules_of(playbook):
        rid = rule_id(r)
        ds = [d for d in ds_all if rid in (d.get("rule_ids") or [])]
        dec = declared.get(rid)
        entry = {"rule_id": rid, "topic": rule_topic(r), "outcome": None, "agreement_clauses": [], "decision_ids": [],
                 "reason": ""}
        paras_of, added_after = [], []
        for d in ds:
            if d.get("op") == "insert_paragraph":
                if isinstance(d.get("after_para"), int):
                    added_after.append(d["after_para"])    # סעיף שנוסף: פסקת העוגן אינה סעיף שהפלייבוק חל עליו
                continue
            p = d.get("para")
            if isinstance(p, int) and p not in paras_of:
                paras_of.append(p)
        if ds:
            entry["decision_ids"] = [d.get("id") for d in ds]
            track = next((d.get("offered_track") or d.get("track") for d in ds if d.get("offered_track") or d.get("track")), None)
            if all(d.get("op") == "insert_paragraph" for d in ds):
                entry["outcome"] = "no_matching_clause"
                entry["added_by"] = entry["decision_ids"]
                entry["reason"] = "אין בהסכם סעיף לנושא; נוסף סעיף" if L == "he" else \
                    "No clause on this topic in the agreement; a clause was added"
            elif any(d.get("op") in CHANGING_OPS for d in ds):
                entry["outcome"] = "applied"
            else:
                entry["outcome"] = "accepted_as_is"
                entry["reason"] = next((d.get("reason") for d in ds if d.get("reason")), "")
        else:
            track = None
        if dec and ds and dec.get("round") and int(dec["round"]) < int(round_number or 1):
            dec = None   # הכרזה מסבב קודם מול הכרעה של הסבב הזה: ההכרעה גוברת, וההכרזה הישנה נשמטת
            declared.pop(rid, None)
        if dec:
            if ds and dec.get("outcome") != entry["outcome"]:
                entry["conflict"] = {"decisions": entry["outcome"], "declared": dec.get("outcome")}
            elif not ds:
                entry["outcome"] = dec.get("outcome") if dec.get("outcome") in OUTCOMES else None
                entry["reason"] = dec.get("reason") or ""
                track = dec.get("track")
            for p in dec.get("agreement_paras") or []:
                if isinstance(p, int) and p not in paras_of:
                    paras_of.append(p)
        if rid in cov_res:
            entry["result"] = cov_res[rid]
            if not entry["outcome"] and cov_res[rid] in EXTRA_OUTCOMES:
                entry["outcome"] = cov_res[rid]
            elif not entry["outcome"] and cov_res[rid] in ("applied_full", "applied_partial"):
                entry["outcome"] = "applied"
        entry["agreement_clauses"] = [label(p) for p in paras_of] + [
            ("נוסף אחרי %s" if L == "he" else "added after %s") % label(p) for p in added_after]
        entry["paras"] = paras_of
        if entry["outcome"] != "no_matching_clause":
            matched.update(paras_of)
        else:
            matched.update(paras_of)   # הסעיף שנוסף או שהוצהר: כבר מטופל בפלייבוק
        tr, pos = rule_position(r, track)
        entry["track"] = tr
        entry["position"] = pos
        entry["sources"] = rule_sources(r, playbook)
        entry["source_text"] = source_text(entry["sources"], L)
        entry["source_found"] = bool(entry["sources"])
        rules_out.append(entry)

    structural = {d.get("para") for d in ds_all if d.get("structural") and isinstance(d.get("para"), int)}
    unmatched = []
    for i, lab in _agreement_clauses(paras, labels, structural):
        if i in matched:
            continue
        covered = [d.get("id") for d in ds_all if d.get("para") == i or d.get("after_para") == i]
        unmatched.append({"para": i, "clause": lab or label(i), "decision_ids": covered, "answered_on": "areo_judgment",
                          "notice": NOTICE[L]})
    return {"round": int(round_number or 1), "deal_id": deal_id or "", "lang": L,
            "rules": rules_out, "unmatched_agreement_clauses": unmatched,
            "declared": list(declared.values()),
            "counts": {"rules": len(rules_out),
                       **{o: sum(1 for e in rules_out if e["outcome"] == o) for o in OUTCOMES},
                       "no_outcome": sum(1 for e in rules_out if not e["outcome"]),
                       **({r: sum(1 for e in rules_out if e.get("result") == r) for r in RESULTS} if cov_res else {}),
                       "unmatched_agreement_clauses": len(unmatched)}}


# --------------------------------------------------------------------------- הבדיקה
def _f(code, message, where="", blocking=False):
    return {"code": code, "message": message, "where": where, "blocking": bool(blocking)}


def check_map(pm, playbook, mode="send"):
    """ממצאים {code, message, where, blocking}. נכשל (blocking) כשסעיף בפלייבוק בלי תוצאה רשומה, עם שתי תוצאות
    סותרות, תוצאה בלי עמדה, או סעיף בהסכם בלי ההודעה ללקוח. מקור חסר אינו חוסם: הוא פריט גלוי ללקוח
    (NO_APPROVED_SOURCE). במצב work הכשלים הם אזהרה."""
    blk = mode != "work"
    out = []
    rules = rules_of(playbook)
    if not rules:
        return out
    if not isinstance(pm, dict) or not pm.get("rules"):
        out.append(_f("PLAYBOOK_MAP_MISSING",
                      "לא נבנה מיפוי של הפלייבוק להסכם: אין תוצאה רשומה לאף סעיף בפלייבוק. להריץ playbook_map.py build",
                      "", blk))
        return out
    seen = {}
    for e in pm["rules"]:
        seen.setdefault(e.get("rule_id"), []).append(e)
    for r in rules:
        rid = rule_id(r)
        es = seen.get(rid) or []
        if not es:
            out.append(_f("PLAYBOOK_RULE_NO_OUTCOME", "סעיף בפלייבוק בלי תוצאה רשומה: %s (%s)" % (rid, rule_topic(r)),
                          rid, blk))
            continue
        if len(es) > 1 or es[0].get("conflict"):
            out.append(_f("PLAYBOOK_RULE_TWO_OUTCOMES", "לסעיף %s יותר מתוצאה אחת: צריכה להיות אחת בדיוק" % rid, rid, blk))
        e = es[0]
        if e.get("outcome") not in OUTCOMES + EXTRA_OUTCOMES:
            out.append(_f("PLAYBOOK_RULE_NO_OUTCOME", "סעיף בפלייבוק בלי תוצאה רשומה: %s (%s)" % (rid, rule_topic(r)),
                          rid, blk))
            continue
        if e["outcome"] in ("applied", "accepted_as_is") and not (e.get("position") or "").strip():
            out.append(_f("PLAYBOOK_OUTCOME_NO_POSITION", "הסעיף %s נרשם %s בלי העמדה שהוחלה" % (rid, e["outcome"]),
                          rid, blk))
        if e["outcome"] in ("applied", "accepted_as_is") and not e.get("agreement_clauses"):
            out.append(_f("PLAYBOOK_OUTCOME_NO_CLAUSE", "הסעיף %s נרשם %s בלי הסעיף בהסכם" % (rid, e["outcome"]), rid, blk))
        if not e.get("sources"):
            out.append(_f("NO_APPROVED_SOURCE", "%s (%s)" % (NO_SOURCE["he"], rule_topic(r)), rid, False))
    for u in pm.get("unmatched_agreement_clauses") or []:
        if not (u.get("notice") or "").strip():
            out.append(_f("UNMATCHED_CLAUSE_NO_NOTICE", "סעיף בהסכם בלי סעיף מקביל בפלייבוק ובלי ההודעה ללקוח: %s"
                          % u.get("clause"), str(u.get("clause")), blk))
    return out


def check_sources_shown(decisions, pm, lang="he"):
    """כלל 12: הכרעה שנשענת על כלל בפלייבוק ואינה קבלה, והבועה הפנימית שלה אינה נושאת את שורת המקור. אזהרה."""
    out = []
    by_rule = {e["rule_id"]: e for e in (pm or {}).get("rules") or []}
    pref = SOURCE_PREFIX["en" if lang == "en" else "he"]
    for d in decisions or []:
        if not isinstance(d, dict) or d.get("op") == "accept" or not d.get("rule_ids"):
            continue
        ic = d.get("internal_comment") or ""
        if pref.strip() not in ic and NO_SOURCE["he"][:25] not in ic and NO_SOURCE["en"][:25] not in ic:
            known = [by_rule[r] for r in d["rule_ids"] if r in by_rule]
            out.append(_f("SOURCE_NOT_SHOWN", "ההכרעה %s נשענת על כלל בפלייבוק, ובבועה הפנימית שלה אין מקור "
                          "(הסכם וסעיף)%s. להריץ playbook_map.py annotate" % (d.get("id"), "" if known else " ומפה"),
                          d.get("id"), False))
    return out


# --------------------------------------------------------------------------- שורת המקור בבועה הפנימית
def annotate(decisions, pm, lang="he"):
    """מוסיף לבועה הפנימית של כל הכרעה (שאינה קבלה) שנשענת על כלל, את שורת המקור: ההסכם והסעיף, או 'AREO לא מצאה
    מקור מורשה לנקודה זו'. מחזיר את מספר ההכרעות שעודכנו. הבועה לצד השני אינה משתנה."""
    by_rule = {e["rule_id"]: e for e in (pm or {}).get("rules") or []}
    pref = SOURCE_PREFIX["en" if lang == "en" else "he"]
    n = 0
    for d in decisions or []:
        if not isinstance(d, dict) or d.get("op") == "accept":
            continue
        ids = [r for r in d.get("rule_ids") or [] if r in by_rule]
        if not ids:
            continue
        ic = d.get("internal_comment") or ""
        if pref.strip() in ic or NO_SOURCE["he"][:25] in ic or NO_SOURCE["en"][:25] in ic:
            continue
        # שורת המקור ללקוח: ההסכם והסעיף, ושם הנושא של הכלל. בלי קוד הכלל (R01, R-7): קוד פנימי אינו טקסט ללקוח
        lines = ["%s (%s)" % (by_rule[r]["source_text"], by_rule[r].get("topic") or "") if by_rule[r].get("topic")
                 else by_rule[r]["source_text"] for r in ids]
        d["internal_comment"] = (ic + "\n" if ic else "") + "\n".join(lines)
        n += 1
    return n


# --------------------------------------------------------------------------- יומן הסבבים
def round_info(n):
    n = int(n or 1)
    kind, he, en = ROUND_NAMES.get(n, ("later", "סבב %d" % n, "Round %d" % n))
    rule = ROUND_RULE["first" if n == 1 else "other"]
    return {"n": n, "kind": kind, "label": he, "label_en": en, "rule": rule[0], "rule_en": rule[1],
            "ordinal_distinguished": n in ROUND_NAMES}


def round_view(state, compare=None):
    """מה הוסכם, מה פתוח ומה הצד השני החזיר לאחור, בסבב הנוכחי, מקובץ המצב (ומהשוואת הסבב כשהיא ניתנת).
    handle_only: הסעיפים היחידים שמטפלים בהם בסבב. must_not_touch: מה שהוסכם או שקיבלנו."""
    st = state or {}
    meta = st.get("meta") or {}
    try:
        from orchestrator import state_builder as SB
        n = SB.current_round(st)
    except Exception:  # noqa: BLE001
        n = int(meta.get("round_number") or 1)
    info = round_info(n)
    agreed, waiting, open_, back, handle = [], [], [], [], []
    seen_back = set()
    for c in st.get("clauses") or []:
        if not isinstance(c, dict):
            continue
        cid = c.get("clause_id")
        ref = c.get("contract_ref") or (st.get("numbering_map") or {}).get(cid) or cid
        rec = {"clause_id": cid, "clause": ref, "status": c.get("status")}
        stt = c.get("status")
        rb = c.get("reopened_by_counterparty") or {}
        if rb and int(rb.get("round") or 0) == n:
            back.append(dict(rec, round=n, how=rb.get("classification") or "reopened_by_counterparty"))
            seen_back.add(cid)
        if stt == "CLOSED":
            agreed.append(dict(rec, closed_in_round=c.get("closed_in_round")))
        elif stt == "ACCEPTED_PENDING":
            waiting.append(rec)
        else:
            open_.append(rec)
    for sc in st.get("silent_changes") or []:
        if isinstance(sc, dict) and sc.get("restore_agreed") or (isinstance(sc, dict) and sc.get("kind") == "restore_agreed"):
            cid = sc.get("clause_id")
            if cid and cid not in seen_back:
                seen_back.add(cid)
                back.append({"clause_id": cid, "clause": (st.get("numbering_map") or {}).get(cid) or cid,
                             "status": "CLOSED", "round": n, "how": "silent_change"})
    for ch in (compare or {}).get("clauses") or []:
        cid = ch.get("reopens_closed") if isinstance(ch, dict) else None
        if cid and cid not in seen_back:
            seen_back.add(cid)
            back.append({"clause_id": cid, "clause": ch.get("clause") or cid, "status": "CLOSED", "round": n,
                         "how": ch.get("classification") or "compare"})
    if n == 1:
        open_ = open_ + [x for x in waiting]
        waiting = []
    handle = []
    for x in open_ + back:
        if x.get("clause_id") and x["clause_id"] not in handle:
            handle.append(x["clause_id"])
    return {"round": n, "kind": info["kind"], "label": info["label"], "label_en": info["label_en"], "rule": info["rule"],
            "rule_en": info["rule_en"], "deal_id": meta.get("transaction_id") or "",
            "agreed": agreed, "awaiting_confirmation": waiting, "open": open_, "changed_back_by_counterparty": back,
            "handle_only": handle, "must_not_touch": [x["clause_id"] for x in agreed + waiting if x.get("clause_id")],
            "counts": {"agreed": len(agreed), "awaiting_confirmation": len(waiting), "open": len(open_),
                       "changed_back": len(back)}}


def check_round_discipline(view, decisions):
    """הכרעה שמשנה נוסח בסעיף שהוסכם (must_not_touch), כשהסעיף אינו ברשימת הפתיחה מחדש של הסבב. החסימה בפועל היא
    ROUND_REOPEN_CLOSED של השער; כאן הבדיקה על התצוגה, כדי שהיומן יאמר את זה."""
    out = []
    keep = set(view.get("must_not_touch") or []) - set(view.get("handle_only") or [])
    for d in decisions or []:
        cid = d.get("clause_id")
        if cid in keep and d.get("op") in ("replace", "replace_span", "delete_paragraph", "insert_paragraph") \
                and not (d.get("reopen") or d.get("conforming")):
            out.append(_f("ROUND_AGREED_POINT_TOUCHED", "ההכרעה %s משנה את %s, שהוסכם. סעיף מוסכם אינו נפתח מחדש "
                          "בלי הוראה רשומה" % (d.get("id"), cid), d.get("id"), True))
    return out


def update_ledger(state, view):
    """רושם את תצוגת הסבב ב-meta.round_ledger (רשומה לסבב, הרצה חוזרת באותו סבב מחליפה)."""
    meta = state.setdefault("meta", {})
    led = [x for x in meta.get("round_ledger") or [] if isinstance(x, dict) and x.get("round") != view["round"]]
    led.append(view)
    meta["round_ledger"] = sorted(led, key=lambda x: x.get("round") or 0)
    return meta["round_ledger"]


# --------------------------------------------------------------------------- כיסוי מלא של כללי הפלייבוק (n4d-rule-coverage.md)
# תוכנית כיסוי לפני העריכה (rule-coverage.json), ארבע תוצאות אחרי העריכה, שקילות מהותית ובסיס העמדה.
# הקובץ שייך לעסקה: <תיקיית העסקה>/rule-coverage.json. קובץ מצב או הכרעות ישנים, בלי השדות החדשים, נטענים כרגיל.
COVERAGE_FILE = "rule-coverage.json"
RESULTS = ("applied_full", "applied_partial", "not_applied", "not_applicable")
ACTIONS = ("amend", "keep", "clarify")
EQ_KEYS = ("protected_party", "event", "subject", "conditions", "duration", "exceptions")
EQ_VALUES = ("same", "broader", "narrower", "n/a")
BASES = ("approved_policy", "proposed_unapproved", "new_recommendation")
BODY_OPS = ("replace", "replace_span", "insert_paragraph", "delete_paragraph")
EXTRA_OUTCOMES = ("not_applied", "not_applicable")   # תוצאות שנגזרות מתוכנית הכיסוי בלבד
CODE_BLOCKING_COVERAGE = ("RULE_COVERAGE_PLAN_MISSING", "RULE_COVERAGE_PLAN_INCOMPLETE", "RULE_PLANNED_NOT_RESOLVED",
                          "RULE_APPLIED_BY_COMMENT_ONLY", "RULE_PARTIAL_MARKED_FULL", "EQUIVALENCE_MISSING",
                          "OPENING_DEPARTURE_UNEXPLAINED", "POSITION_BASIS_MISSING", "BASIS_APPROVAL_UNSUPPORTED")


def coverage_path(deal):
    return os.path.join(deal, COVERAGE_FILE)


def _now_iso():
    import datetime
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def _dlist(decisions):
    d = decisions.get("decisions") if isinstance(decisions, dict) else decisions
    return [x for x in d or [] if isinstance(x, dict)]


def rule_approved(rule, track="green"):
    """האם העמדה במסלול מאושרת במפורש בפלייבוק: ingest_result.counts_as_approved של התא (השדה שרכיב הפלייבוק כותב
    ב-status.cell_result), או policy_status == Confirmed של הכלל כולו. לעולם לא מתווית ירוק, ולא מטיוטה קודמת."""
    if not isinstance(rule, dict):
        return False
    tl = rule.get("traffic_light") if isinstance(rule.get("traffic_light"), dict) else {}
    cell = tl.get(track) if isinstance(tl.get(track), dict) else (rule.get(track) if isinstance(rule.get(track), dict) else {})
    ir = cell.get("ingest_result") if isinstance(cell.get("ingest_result"), dict) else None
    if ir is not None:
        return ir.get("counts_as_approved") is True
    return rule.get("policy_status") == "Confirmed"


def _offered_track(d):
    o = str(d.get("offered") or d.get("offered_now") or d.get("offered_track") or "").strip().lower()
    if o in ("", "green", "opening"):
        return "green", False
    if o.startswith("fallback") or o == "yellow":
        return "yellow", True
    return ("red" if o == "red" else "yellow"), True


def plan_skeleton(playbook, pm=None, deal_id="", playbook_name=""):
    """שלד תוכנית הכיסוי: כלל לכל כלל בגרעין, עם עמדת הפתיחה והנסיגות, והסעיפים בהסכם כשהמיפוי כבר נבנה.
    את applies, applies_reason, locations ו-action ממלא מי שמכין את העריכה."""
    by_rule = {e.get("rule_id"): e for e in (pm or {}).get("rules") or []}
    rules = []
    for r in rules_of(playbook):
        rid = rule_id(r)
        _t, opening = rule_position(r, "green")
        fb = []
        for tr in ("yellow",):
            tl = r.get("traffic_light") if isinstance(r.get("traffic_light"), dict) else {}
            cell = tl.get(tr) if isinstance(tl.get(tr), dict) else (r.get(tr) if isinstance(r.get(tr), dict) else {})
            txt = _text(cell.get("position"))
            if txt:
                fb.append(txt)
        rules.append({"rule_id": rid, "topic": rule_topic(r), "applies": None, "applies_reason": "",
                      "locations": list((by_rule.get(rid) or {}).get("agreement_clauses") or []),
                      "opening": opening if _t == "green" else "", "allowed_fallbacks": fb, "action": "",
                      "result": "", "result_reason": "", "result_decision_ids": []})
    return {"version": 1, "created_at": _now_iso(), "deal_id": deal_id, "playbook": playbook_name, "rules": rules}


def check_plan(plan, playbook):
    """בדיקת התוכנית: כל כלל בגרעין נמצא בה, וכל שדה מלא. applies:false דורש סיבה. ממצאים {code, message, where}."""
    out = []
    if not isinstance(plan, dict) or not isinstance(plan.get("rules"), list):
        return [{"code": "RULE_COVERAGE_PLAN_INCOMPLETE", "message": "תוכנית הכיסוי אינה במבנה: חסר rules", "where": ""}]
    have = {}
    for e in plan["rules"]:
        if isinstance(e, dict) and e.get("rule_id"):
            have.setdefault(e["rule_id"], e)
    for r in rules_of(playbook):
        rid = rule_id(r)
        e = have.get(rid)
        if not e:
            out.append({"code": "RULE_COVERAGE_PLAN_INCOMPLETE",
                        "message": "כלל בפלייבוק שאינו בתוכנית הכיסוי: %s (%s)" % (rid, rule_topic(r)), "where": rid})
            continue
        miss = []
        if not isinstance(e.get("applies"), bool):
            miss.append("applies (true/false)")
        if not str(e.get("applies_reason") or "").strip() and e.get("applies") is False:
            miss.append("applies_reason (חובה כשהכלל אינו חל)")
        if e.get("applies") is True:
            if not str(e.get("applies_reason") or "").strip():
                miss.append("applies_reason")
            if not e.get("locations") and not e.get("missing_clause"):
                miss.append("locations (או missing_clause:true כשאין בהסכם סעיף)")
            if not str(e.get("opening") or "").strip():
                miss.append("opening")
            if not isinstance(e.get("allowed_fallbacks"), list):
                miss.append("allowed_fallbacks (רשימה, אפשר ריקה)")
            if e.get("action") not in ACTIONS:
                miss.append("action (%s)" % "|".join(ACTIONS))
        if e.get("result") and e["result"] not in RESULTS:
            miss.append("result חייב להיות אחד מ: %s" % ", ".join(RESULTS))
        if miss:
            out.append({"code": "RULE_COVERAGE_PLAN_INCOMPLETE",
                        "message": "בתוכנית הכיסוי של %s (%s) חסר: %s" % (rid, rule_topic(r), "; ".join(miss)), "where": rid})
    return out


def _plan_before_work(plan, work):
    """False כשהתוכנית נוצרה אחרי קובץ העבודה (created_at מאוחר מזמן יצירת הקובץ). לא ניתן לקבוע: True."""
    import datetime
    try:
        created = datetime.datetime.fromisoformat(str(plan.get("created_at")))
        if created.tzinfo is None:
            created = created.replace(tzinfo=datetime.timezone.utc)
        wt = datetime.datetime.fromtimestamp(os.path.getctime(work), tz=datetime.timezone.utc)
    except (TypeError, ValueError, OSError):
        return True
    return created <= wt + datetime.timedelta(seconds=2)


def equivalence_problem(d):
    """None כשהשקילות של ההכרעה שלמה; אחרת תיאור הבעיה."""
    eq = d.get("equivalence")
    if not isinstance(eq, dict):
        return "חסר equivalence"
    bad = [k for k in EQ_KEYS if eq.get(k) not in EQ_VALUES]
    if bad:
        return "equivalence חסר או לא תקין ב: %s (ערכים: %s)" % (", ".join(bad), " | ".join(EQ_VALUES))
    return None


def has_open_entry(d, state=None, doc=None):
    """האם להכרעה יש רשומת הכרעה פתוחה: decision_required.required, או פריט ב-open_items של קובץ המצב או של קובץ
    ההכרעות (open_items/open_decisions) שמצביע על מזהה ההכרעה או על הסעיף שלה."""
    dr = d.get("decision_required")
    if isinstance(dr, dict) and dr.get("required"):
        return True
    ids = {x for x in (d.get("id"), d.get("clause_id")) if x}
    srcs = [(state or {}).get("open_items")]
    if isinstance(doc, dict):
        srcs += [doc.get("open_items"), doc.get("open_decisions")]
    for src in srcs:
        for it in src or []:
            if isinstance(it, dict) and ids & (set(it.get("decision_ids") or []) | set(it.get("clause_ids") or [])):
                return True
    return False


def check_coverage(plan, playbook, decisions, state=None, mode="send", work=None):
    """בדיקות הכיסוי אחרי העריכה. plan None: אין תוכנית (RULE_COVERAGE_PLAN_MISSING). ממצאים {code, message, where,
    blocking}. במצב work הכול אזהרה; במצב send הקודים ב-CODE_BLOCKING_COVERAGE חוסמים. APPROVAL_OPEN_MISSING לעולם אינו חוסם."""
    blk = mode != "work"
    out = []

    def add(code, msg, where=""):
        out.append(_f(code, msg, where, blk and code in CODE_BLOCKING_COVERAGE))

    rules = {rule_id(r): r for r in rules_of(playbook)}
    if not rules:
        return out
    if plan is None:
        add("RULE_COVERAGE_PLAN_MISSING", "אין תוכנית כיסוי לכללי הפלייבוק (rule-coverage.json). להריץ: playbook_map.py plan, "
            "למלא, ו-check-plan, לפני העריכה")
        return out
    if work and not _plan_before_work(plan, work):
        add("RULE_COVERAGE_PLAN_MISSING", "תוכנית הכיסוי נוצרה אחרי קובץ העבודה: התוכנית באה לפני העריכה, ולא אחריה")
    for f in check_plan(plan, playbook):
        add(f["code"], f["message"], f["where"])
    ds = _dlist(decisions)
    pr = {e["rule_id"]: e for e in plan.get("rules") or [] if isinstance(e, dict) and e.get("rule_id")}
    for rid, e in pr.items():
        mine = [d for d in ds if rid in (d.get("rule_ids") or [])]
        body = [d for d in mine if d.get("op") in BODY_OPS]
        res = e.get("result")
        if e.get("applies") is False:
            if body:
                out.append(_f("RULE_NOT_APPLICABLE_BUT_EDITED", "הכלל %s סומן כלא חל (%s), ויש הכרעות שמשנות נוסח: %s"
                              % (rid, e.get("applies_reason") or "-", ", ".join(str(d.get("id")) for d in body)), rid, False))
            continue
        if e.get("applies") is not True:
            continue
        if res not in RESULTS:
            add("RULE_PLANNED_NOT_RESOLVED", "הכלל %s (%s) תוכנן כחל וללא תוצאה רשומה (applied_full | applied_partial | "
                "not_applied | not_applicable). לרשום: playbook_map.py result" % (rid, e.get("topic") or rid), rid)
            continue
        if res in ("applied_full", "applied_partial"):
            comment_only = any(d.get("op") == "comment_only" for d in mine)
            if not body and (e.get("action") != "keep" or comment_only):
                add("RULE_APPLIED_BY_COMMENT_ONLY", "הכלל %s סומן %s, אבל ההכרעות שלו אינן משנות את גוף ההסכם (הערה בלבד). "
                    "הערה אינה יישום: או תיקון בגוף, או not_applied" % (rid, res), rid)
            if res == "applied_full":
                nar = [d for d in mine if isinstance(d.get("equivalence"), dict)
                       and "narrower" in d["equivalence"].values()]
                if nar:
                    add("RULE_PARTIAL_MARKED_FULL", "הכלל %s סומן applied_full, אבל בהכרעה %s יש רכיב שקילות צר יותר מהפלייבוק "
                        "(narrower). התוצאה היא applied_partial" % (rid, ", ".join(str(d.get("id")) for d in nar)), rid)
        elif res == "not_applied" and body:
            add("RULE_PARTIAL_MARKED_FULL", "הכלל %s סומן not_applied, אבל יש לו הכרעות שמשנות נוסח (%s)"
                % (rid, ", ".join(str(d.get("id")) for d in body)), rid)
    seen_eq = set()
    for d in ds:
        rids = [r for r in d.get("rule_ids") or [] if r in pr]
        if not rids or d.get("op") == "accept":
            continue
        did = d.get("id")
        if d.get("op") in BODY_OPS:
            prob = equivalence_problem(d)
            if prob and did not in seen_eq:
                seen_eq.add(did)
                add("EQUIVALENCE_MISSING", "ההכרעה %s משנה נוסח לפי כלל בפלייבוק, ו%s (שישה רכיבים: %s)"
                    % (did, prob, ", ".join(EQ_KEYS)), str(did))
        basis = d.get("position_basis")
        if basis not in BASES:
            add("POSITION_BASIS_MISSING", "בהכרעה %s חסר position_basis (%s)" % (did, " | ".join(BASES)), str(did))
        else:
            trk, departs = _offered_track(d)
            if basis == "approved_policy" and not all(rule_approved(rules.get(r), trk) for r in rids if r in rules):
                add("BASIS_APPROVAL_UNSUPPORTED", "ההכרעה %s רשומה approved_policy, והפלייבוק אינו מסמן את העמדה (מסלול %s) "
                    "כמאושרת (ingest_result.counts_as_approved או policy_status=Confirmed). אין להסיק אישור מתווית ירוק"
                    % (did, trk), str(did))
            if basis in ("proposed_unapproved", "new_recommendation") and not has_open_entry(d, state, decisions):
                add("APPROVAL_OPEN_MISSING", "ההכרעה %s נשענת על עמדה שלא אושרה (%s) ואין לה רשומת הכרעה פתוחה "
                    "(open_items). העבודה אינה נעצרת; ההכרעה נשארת פתוחה ללקוח" % (did, basis), str(did))
        trk, departs = _offered_track(d)
        if departs and not (str(d.get("departure_reason") or "").strip() or d.get("earlier_rejection")
                            or d.get("user_instruction")):
            add("OPENING_DEPARTURE_UNEXPLAINED", "ההכרעה %s מציעה עמדה שאינה עמדת הפתיחה (%s) בלי departure_reason "
                "(ובלי דחייה קודמת מתועדת או הנחיה). להסביר בדוח הפנימי" % (did, d.get("offered") or d.get("offered_now")
                                                                         or d.get("offered_track")), str(did))
    return out


def coverage_results_view(plan, pm_rules=None):
    """{rule_id: result} מהתוכנית, לצורך המיפוי."""
    out = {}
    for e in (plan or {}).get("rules") or []:
        if not isinstance(e, dict) or not e.get("rule_id"):
            continue
        if e.get("applies") is False and e.get("applies_reason"):
            out[e["rule_id"]] = e.get("result") if e.get("result") in RESULTS else "not_applicable"
        elif e.get("result") in RESULTS:
            out[e["rule_id"]] = e["result"]
    return out


# --------------------------------------------------------------------------- שורת הפקודה
def _load(path, what, required=True):
    if not path or not os.path.exists(path):
        if required:
            print("%s אינו קיים: %s" % (what, path))
            raise SystemExit(2)
        return None
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def _state_path(deal):
    return os.path.join(deal, LIVE)


def _state_or_skeleton(deal):
    """קובץ המצב של העסקה. בסבב 1 הוא עוד לא נכתב (write רץ בסוף הסבב): נוצר שלד, כמו ב-negotiation_state.py decide,
    ו-write ממשיך אותו וממזג את meta.playbook_map ו-meta.round_ledger כמו שהם."""
    path = _state_path(deal)
    if os.path.exists(path):
        return _load(path, "קובץ המצב")
    from orchestrator import state_builder as SB
    os.makedirs(deal, exist_ok=True)
    st = SB.skeleton()
    st["meta"].update(transaction_id=os.path.basename(os.path.abspath(deal)), round_number=1,
                      round_stage=SB.stage_for_round(1), generated_at=SB.now_iso(), last_updated=SB.now_iso())
    print("אין עדיין קובץ מצב בעסקה: נוצר שלד לסבב 1, והמיפוי נרשם בו")
    return st


def _save_state(deal, state):
    import negotiation_state as NS
    return NS.write_checked(deal, state)


def _decisions(path):
    doc = _load(path, "קובץ ההכרעות")
    return doc, (doc.get("decisions") if isinstance(doc, dict) else doc) or []


def _agreement(received):
    if not received:
        return None, None
    import content_checks as CC
    import common.docx_tracked as dt
    paras = dt.received_paragraphs(received)
    try:
        labels = CC.numbered_labels(received)
    except Exception:  # noqa: BLE001
        labels = None
    return paras, labels


def cmd_build(a):
    pb = _load(a.playbook, "הפלייבוק")
    doc, decisions = _decisions(a.decisions)
    st = _state_or_skeleton(a.deal) if a.deal else {}
    meta = (st or {}).get("meta") or {}
    prev = meta.get("playbook_map") or {}
    rnd = (doc.get("round") if isinstance(doc, dict) else None) or meta.get("round_number") or 1
    # ההכרזות (declare) נשמרות בין הסבבים: סעיף בפלייבוק שאין לו סעיף בהסכם נשאר כזה גם בסבב הבא, עד שהכרעה
    # חדשה נוגעת בו (אז ההכרעה גוברת, בלי "סתירה"). לפני התיקון כל סבב פתח 27 סעיפים "בלי תוצאה" מחדש
    declared = [dict(x, round=x.get("round") or prev.get("round") or rnd) for x in prev.get("declared") or []
                if isinstance(x, dict)]
    paras, labels = _agreement(a.received)
    cov = _load(coverage_path(a.deal), "תוכנית הכיסוי", required=False) if a.deal else None
    pm = build_map(pb, decisions, rnd, meta.get("transaction_id") or (doc.get("transaction_id") if isinstance(doc, dict) else ""),
                   paras, labels, declared, a.lang, coverage=cov)
    c = pm["counts"]
    print("מיפוי הפלייבוק להסכם, סבב %s: %d סעיפים בפלייבוק. הוחלו: %d, התקבלו כמו שהם: %d, אין סעיף מתאים בהסכם: %d, "
          "בלי תוצאה: %d. סעיפים בהסכם בלי סעיף בפלייבוק: %d"
          % (pm["round"], c["rules"], c["applied"], c["accepted_as_is"], c["no_matching_clause"], c["no_outcome"],
             c["unmatched_agreement_clauses"]))
    for e in pm["rules"]:
        if not e["outcome"]:
            print("  בלי תוצאה: %s (%s). לרשום: playbook_map.py declare --rule %s --outcome accepted_as_is|no_matching_clause"
                  % (e["rule_id"], e["topic"], e["rule_id"]))
        if not e["source_found"]:
            print("  %s (%s)" % (NO_SOURCE[a.lang], e["topic"]))
    for u in pm["unmatched_agreement_clauses"]:
        print("  %s: %s" % (u["clause"], u["notice"]))
    findings = check_map(pm, pb, a.mode)
    if a.deal and st:
        st.setdefault("meta", {})["playbook_map"] = pm
        # כלל יסוד 11: רשומת יומן לכל סבב, גם לסבב הראשון. רשומה שכבר נרשמה לסבב (write, או rounds עם ההשוואה) נשמרת
        if not any(isinstance(x, dict) and x.get("round") == int(rnd) for x in st["meta"].get("round_ledger") or []):
            update_ledger(st, round_view(st))
        if _save_state(a.deal, st):
            return 3
    return 3 if any(f["blocking"] for f in findings) else 0


def cmd_declare(a):
    st = _state_or_skeleton(a.deal)
    meta = st.setdefault("meta", {})
    pm = meta.setdefault("playbook_map", {"round": meta.get("round_number") or 1, "rules": [], "declared": [],
                                          "unmatched_agreement_clauses": []})
    dec = [x for x in pm.get("declared") or [] if x.get("rule_id") != a.rule]
    dec.append({"rule_id": a.rule, "outcome": a.outcome, "reason": a.reason or "",
                "agreement_paras": a.para or [], "track": a.track, "round": int(pm.get("round") or meta.get("round_number") or 1)})
    pm["declared"] = dec
    for e in pm.get("rules") or []:
        if e.get("rule_id") == a.rule and not e.get("decision_ids"):
            e["outcome"], e["reason"] = a.outcome, a.reason or ""
            e["paras"] = list(a.para or [])
            e["agreement_clauses"] = ["פסקה %s" % p for p in a.para or []]
            e.pop("conflict", None)
    print("נרשם: %s -> %s" % (a.rule, a.outcome))
    return _save_state(a.deal, st)


def cmd_check(a):
    pb = _load(a.playbook, "הפלייבוק")
    st = _load(_state_path(a.deal), "קובץ המצב")
    pm = (st.get("meta") or {}).get("playbook_map")
    fs = check_map(pm, pb, a.mode)
    if getattr(a, "decisions", None):
        doc, _ds = _decisions(a.decisions)
        plan = _load(coverage_path(a.deal), "תוכנית הכיסוי", required=False)
        fs = fs + check_coverage(plan, pb, doc, st, a.mode, getattr(a, "work", None))
    for f in fs:
        print("  %s [%s] %s%s" % ("כשל" if f["blocking"] else "אזהרה", f["code"], f["message"],
                                  "  (%s)" % f["where"] if f["where"] else ""))
    bad = [f for f in fs if f["blocking"]]
    print("תוצאה: %s" % ("נכשל: %d" % len(bad) if bad else "עבר"))
    return 3 if bad else 0


def cmd_plan(a):
    pb = _load(a.playbook, "הפלייבוק")
    path = coverage_path(a.deal)
    if os.path.exists(path) and not a.force:
        print("תוכנית כיסוי כבר קיימת (%s). לא נדרסת: זמן יצירתה הוא ההוכחה שנכתבה לפני העריכה. --force מחליף" % path)
        return 2
    st = _load(_state_path(a.deal), "קובץ המצב", required=False)
    pm = ((st or {}).get("meta") or {}).get("playbook_map")
    plan = plan_skeleton(pb, pm, os.path.basename(os.path.abspath(a.deal)), os.path.basename(a.playbook))
    os.makedirs(a.deal, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(plan, fh, ensure_ascii=False, indent=1)
    print("נכתב שלד תוכנית כיסוי ל-%d כללים: %s. למלא applies, applies_reason, locations, action; אחר כך check-plan"
          % (len(plan["rules"]), path))
    return 0


def cmd_check_plan(a):
    pb = _load(a.playbook, "הפלייבוק")
    plan = _load(coverage_path(a.deal), "תוכנית הכיסוי")
    fs = check_plan(plan, pb)
    for f in fs:
        print("  כשל [%s] %s" % (f["code"], f["message"]))
    print("תוצאה: %s" % ("נכשל: %d" % len(fs) if fs else "עבר"))
    return 3 if fs else 0


def cmd_result(a):
    path = coverage_path(a.deal)
    plan = _load(path, "תוכנית הכיסוי")
    for e in plan.get("rules") or []:
        if e.get("rule_id") == a.rule:
            e["result"], e["result_reason"] = a.result, a.reason or ""
            e["result_decision_ids"] = list(a.decision or [])
            break
    else:
        print("הכלל %s אינו בתוכנית הכיסוי" % a.rule)
        return 2
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(plan, fh, ensure_ascii=False, indent=1)
    print("נרשם: %s -> %s" % (a.rule, a.result))
    return 0


def cmd_annotate(a):
    pb = _load(a.playbook, "הפלייבוק")
    doc, decisions = _decisions(a.decisions)
    st = _load(_state_path(a.deal), "קובץ המצב", required=False) if a.deal else None
    pm = ((st or {}).get("meta") or {}).get("playbook_map") or build_map(pb, decisions, lang=a.lang)
    n = annotate(decisions, pm, a.lang)
    out = a.out or a.decisions
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, ensure_ascii=False, indent=1)
    print("שורת מקור נוספה ל-%d הכרעות (%s)" % (n, out))
    return 0


def cmd_rounds(a):
    st = _load(_state_path(a.deal), "קובץ המצב")
    view = round_view(st, _load(a.compare, "השוואת הסבב", required=False))
    print("%s (עסקה %s). %s" % (view["label"], view["deal_id"] or "-", view["rule"]))
    c = view["counts"]
    print("הוסכמו: %d. ממתינים לאישור הצד השני: %d. פתוחים: %d. הוחזרו לאחור בידי הצד השני: %d"
          % (c["agreed"], c["awaiting_confirmation"], c["open"], c["changed_back"]))
    for x in view["changed_back_by_counterparty"]:
        print("  סעיף מוסכם שהצד השני החזיר לאחור: %s (%s)" % (x["clause"], x["how"]))
    print("מטפלים רק ב: %s" % (", ".join(view["handle_only"]) or "-"))
    update_ledger(st, view)
    return _save_state(a.deal, st)


def main(argv=None):
    sys.dont_write_bytecode = True
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("build", "check", "annotate"):
        p = sub.add_parser(name)
        p.add_argument("--playbook", required=True, help="playbook-core.json או playbook-model.json")
        p.add_argument("--lang", choices=("he", "en"), default="he")
        p.add_argument("--deal", help="תיקיית העסקה")
        if name != "check":
            p.add_argument("--decisions", required=True)
        else:
            p.add_argument("--decisions", help="קובץ ההכרעות: מפעיל גם את בדיקות הכיסוי")
            p.add_argument("--work", help="קובץ העבודה: לבדיקה שהתוכנית נוצרה לפניו")
        if name == "build":
            p.add_argument("--received", help="הטיוטה שהתקבלה (docx): לזיהוי סעיפים בהסכם בלי סעיף בפלייבוק")
        if name != "annotate":
            p.add_argument("--mode", choices=("work", "send"), default="send")
        else:
            p.add_argument("--out")
    pl = sub.add_parser("plan")
    pl.add_argument("--playbook", required=True)
    pl.add_argument("--deal", required=True)
    pl.add_argument("--force", action="store_true")
    cp = sub.add_parser("check-plan")
    cp.add_argument("--playbook", required=True)
    cp.add_argument("--deal", required=True)
    rs = sub.add_parser("result")
    rs.add_argument("--deal", required=True)
    rs.add_argument("--rule", required=True)
    rs.add_argument("--result", required=True, choices=RESULTS)
    rs.add_argument("--reason")
    rs.add_argument("--decision", action="append")
    d = sub.add_parser("declare")
    d.add_argument("--deal", required=True)
    d.add_argument("--rule", required=True)
    d.add_argument("--outcome", required=True, choices=OUTCOMES)
    d.add_argument("--reason")
    d.add_argument("--para", type=int, action="append", help="פסקה בהסכם שהסעיף חל עליה (אפשר כמה)")
    d.add_argument("--track", choices=TRACKS)
    r = sub.add_parser("rounds")
    r.add_argument("--deal", required=True)
    r.add_argument("--compare")
    a = ap.parse_args(argv)
    return {"build": cmd_build, "declare": cmd_declare, "check": cmd_check, "annotate": cmd_annotate,
            "rounds": cmd_rounds, "plan": cmd_plan, "check-plan": cmd_check_plan,
            "result": cmd_result}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
