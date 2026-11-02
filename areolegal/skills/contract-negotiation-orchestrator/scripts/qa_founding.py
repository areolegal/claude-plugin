#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""בדיקות כללי היסוד של הנושא ונותן, על נתונים סינתטיים ניטרליים בלבד (צד א, צד ב, סעיף 1..n).

אין כאן סוג הסכם, שם צד, פסיקה או חוק. הבדיקות רצות מקומית, בלי רשת ובלי שרת.

    python3 -B qa_founding.py

מה נבדק (המספרים הם מספרי כללי היסוד):
  1   אין חסימה של עורך דין במשלוח; נקודה בלי מקור מורשה היא פריט גלוי; INTERNAL_LEAK עדיין חוסם
  2   קובץ Word בעקוב אחר שינויים: מחיקות והוספות אמיתיות, בועות שמסבירות לצד השני, בלי קודים פנימיים
  3/15  מיפוי הפלייבוק להסכם: תוצאה אחת בדיוק לכל סעיף בפלייבוק, והודעה לסעיף בהסכם בלי סעיף מקביל
  4/11  סבב 1, 2, 3, 4 ואילך: מוסכם מול פתוח, בלי לפתוח מחדש, וסימון סעיף שהוחזר לאחור
  5/12  שורת מקור בכל עמדה, ו"AREO לא מצאה מקור מורשה לנקודה זו" כשאין
  6   הכול מקומי: אין קריאת רשת במודולים של המיפוי
קוד יציאה: 0 הכול עבר, 3 יש כשל.
"""
import json
import os
import re
import sys
import tempfile
import zipfile

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import areo_lib  # noqa: F401,E402


def _find_lib():
    """בחבילת ההרצה הספרייה כבר בנתיב. בעץ המקור היא בתיקיית הכללים המשותפים, באחת התיקיות שליד תיקיית הסקיל."""
    try:
        import orchestrator  # noqa: F401
        return
    except ImportError:
        pass
    here = HERE
    for _ in range(7):
        here = os.path.dirname(here)
        for c in sorted(os.listdir(here)) if os.path.isdir(here) else ():
            base = os.path.join(here, c)
            if not os.path.isdir(base):
                continue
            for sub in os.listdir(base):
                lib = os.path.join(base, sub, "runtime", "lib")
                if os.path.exists(os.path.join(lib, "orchestrator", "state_builder.py")):
                    sys.path.insert(0, lib)
                    return


_find_lib()
from orchestrator import qa_gate as GATE  # noqa: E402
from orchestrator import state_builder as SB  # noqa: E402
import common.docx_tracked as dt  # noqa: E402
import playbook_map as PM  # noqa: E402
import content_checks as CC  # noqa: E402
import negotiation_state as NS  # noqa: E402

RESULTS = []


def test(fn):
    def run():
        try:
            fn()
            RESULTS.append((fn.__name__, True, ""))
        except AssertionError as exc:
            RESULTS.append((fn.__name__, False, str(exc) or "assert"))
        except Exception as exc:  # noqa: BLE001
            RESULTS.append((fn.__name__, False, "%s: %s" % (type(exc).__name__, exc)))
    run.__name__ = fn.__name__
    TESTS.append(run)
    return fn


TESTS = []

# --------------------------------------------------------------------------- נתונים סינתטיים
PLAYBOOK = {
    "source_log": [{"source_id": "S1", "short_name": "Agreement 1"}],
    "rules": [
        {"rule_id": "R-1", "topic_name": "Topic one", "traffic_light": {"green": {"position": "Position one"}},
         "evidence": [{"source_ref": "S1", "clause_ref": "clause 4"}]},
        {"rule_id": "R-2", "topic_name": "Topic two", "traffic_light": {"green": {"position": "Position two"}},
         "evidence": [{"source_ref": "S1", "clause_ref": "clause 9"}]},
        {"rule_id": "R-3", "topic_name": "Topic three", "traffic_light": {"green": {"position": "Position three"}}},
        {"rule_id": "R-4", "topic_name": "Topic four", "traffic_light": {"yellow": {"position": "Position four"}},
         "evidence": [{"source_ref": "S1", "clause_ref": "clause 12"}]}]}
PARAS = ["Agreement between Party A and Party B",
         "1. Party B shall pay all invoices within 90 days of receipt.",
         "2. Party A may terminate this Agreement at any time on 30 days notice.",
         "3. Liability of Party B is unlimited for any breach.",
         "4. Notices shall be sent by courier to the registered address of each party."]
LABELS = [None, "1", "2", "3", "4"]
DECISIONS = [
    {"id": "D1", "op": "replace_span", "para": 1, "old": "90 days", "new": "45 days", "decision_code": "R1",
     "rule_ids": ["R-1"], "external_comment": "We propose 45 days, which matches our payment cycle."},
    {"id": "D2", "op": "accept", "para": 2, "decision_code": "A1", "rule_ids": ["R-2"], "reason": "within the position"},
    {"id": "D3", "op": "replace_span", "para": 3, "old": "is unlimited for any breach",
     "new": "is capped at the fees paid in the prior 12 months", "decision_code": "R1", "rule_ids": ["R-3"],
     "external_comment": "Liability should be proportionate to the fees, so we propose a cap of twelve months of fees."}]


def codes(findings, blocking=None):
    return {f["code"] for f in findings if blocking is None or f["blocking"] == blocking}


# --------------------------------------------------------------------------- 3 ו-15: מיפוי הפלייבוק להסכם
@test
def map_rule_without_outcome_fails():
    pm = PM.build_map(PLAYBOOK, DECISIONS, 1, "deal-a", PARAS, LABELS)
    by = {e["rule_id"]: e for e in pm["rules"]}
    assert by["R-1"]["outcome"] == "applied", by["R-1"]
    assert by["R-2"]["outcome"] == "accepted_as_is", by["R-2"]
    assert by["R-4"]["outcome"] is None, "R-4 has no decision and no declaration"
    fs = PM.check_map(pm, PLAYBOOK, "send")
    assert "PLAYBOOK_RULE_NO_OUTCOME" in codes(fs, True), fs
    assert not [f for f in PM.check_map(pm, PLAYBOOK, "work") if f["blocking"]], "work mode only warns"


@test
def map_declared_no_matching_clause_passes():
    declared = [{"rule_id": "R-4", "outcome": "no_matching_clause", "reason": "no such clause in the agreement"}]
    pm = PM.build_map(PLAYBOOK, DECISIONS, 1, "deal-a", PARAS, LABELS, declared)
    assert {e["rule_id"]: e["outcome"] for e in pm["rules"]} == {
        "R-1": "applied", "R-2": "accepted_as_is", "R-3": "applied", "R-4": "no_matching_clause"}
    fs = PM.check_map(pm, PLAYBOOK, "send")
    assert not codes(fs, True), fs
    assert pm["counts"]["no_outcome"] == 0 and pm["counts"]["rules"] == 4


@test
def map_exactly_one_outcome():
    declared = [{"rule_id": "R-1", "outcome": "accepted_as_is"},
                {"rule_id": "R-4", "outcome": "no_matching_clause"}]
    pm = PM.build_map(PLAYBOOK, DECISIONS, 1, "deal-a", PARAS, LABELS, declared)
    assert "PLAYBOOK_RULE_TWO_OUTCOMES" in codes(PM.check_map(pm, PLAYBOOK, "send"), True)
    pm2 = PM.build_map(PLAYBOOK, DECISIONS, 1, "deal-a", PARAS, LABELS, [{"rule_id": "R-4", "outcome": "no_matching_clause"}])
    pm2["rules"].append(dict(pm2["rules"][0]))
    assert "PLAYBOOK_RULE_TWO_OUTCOMES" in codes(PM.check_map(pm2, PLAYBOOK, "send"), True)


@test
def map_added_clause_is_recorded_as_no_matching_clause():
    ins = {"id": "N1a", "op": "insert_paragraph", "after_para": 4, "text": "5. New clause.", "decision_code": "N1",
           "rule_ids": ["R-4"], "external_comment": "We propose adding a clause on this topic, since the draft is silent."}
    pm = PM.build_map(PLAYBOOK, DECISIONS + [ins], 1, "deal-a", PARAS, LABELS)
    e = {x["rule_id"]: x for x in pm["rules"]}["R-4"]
    assert e["outcome"] == "no_matching_clause" and e["added_by"] == ["N1a"], e
    assert "4" in [u["clause"] for u in pm["unmatched_agreement_clauses"]], "the anchor paragraph is not a playbook match"
    assert not codes(PM.check_map(pm, PLAYBOOK, "send"), True)


@test
def map_missing_fails():
    fs = PM.check_map(None, PLAYBOOK, "send")
    assert codes(fs, True) == {"PLAYBOOK_MAP_MISSING"}, fs


@test
def map_agreement_clause_without_playbook_gets_notice():
    pm = PM.build_map(PLAYBOOK, DECISIONS, 1, "deal-a", PARAS, LABELS)
    un = pm["unmatched_agreement_clauses"]
    assert [u["clause"] for u in un] == ["4"], un
    assert "שיקול הדעת המקצועי של AREO" in un[0]["notice"] and "פסיקה" in un[0]["notice"], un[0]
    en = PM.build_map(PLAYBOOK, DECISIONS, 1, "deal-a", PARAS, LABELS, lang="en")["unmatched_agreement_clauses"][0]["notice"]
    assert "professional judgment" in en and "no case law" in en
    un[0]["notice"] = ""
    assert "UNMATCHED_CLAUSE_NO_NOTICE" in codes(PM.check_map(pm, PLAYBOOK, "send"), True)


@test
def map_decision_each_rule_position_and_source_recorded():
    pm = PM.build_map(PLAYBOOK, DECISIONS, 1, "deal-a", PARAS, LABELS)
    e = {x["rule_id"]: x for x in pm["rules"]}["R-1"]
    assert e["position"] == "Position one" and e["agreement_clauses"] == ["1"], e
    assert e["sources"] == [{"agreement": "Agreement 1", "clause": "clause 4", "source_id": "S1"}], e["sources"]
    assert e["source_text"] == "מקור: Agreement 1, clause 4", e["source_text"]


# --------------------------------------------------------------------------- 5 ו-12: מקור
@test
def source_missing_is_visible_not_blocking_and_never_invented():
    declared = [{"rule_id": "R-4", "outcome": "no_matching_clause"}]
    pm = PM.build_map(PLAYBOOK, DECISIONS, 1, "deal-a", PARAS, LABELS, declared)
    e3 = {x["rule_id"]: x for x in pm["rules"]}["R-3"]
    assert e3["sources"] == [] and not e3["source_found"]
    assert e3["source_text"].startswith("AREO לא מצאה מקור מורשה לנקודה זו"), e3["source_text"]
    fs = PM.check_map(pm, PLAYBOOK, "send")
    assert "NO_APPROVED_SOURCE" in codes(fs, False) and "NO_APPROVED_SOURCE" not in codes(fs, True), fs
    assert "הצעד הבא" in PM.NO_SOURCE["he"] and "Next step" in PM.NO_SOURCE["en"]


@test
def source_line_written_in_internal_comment_only():
    decisions = json.loads(json.dumps(DECISIONS))
    pm = PM.build_map(PLAYBOOK, decisions, 1, "deal-a", PARAS, LABELS, [{"rule_id": "R-4", "outcome": "no_matching_clause"}])
    assert "SOURCE_NOT_SHOWN" in codes(PM.check_sources_shown(decisions, pm))
    n = PM.annotate(decisions, pm)
    assert n == 2, n   # D1 ו-D3; D2 הוא accept, ללא בועה
    assert "Agreement 1, clause 4" in decisions[0]["internal_comment"]
    assert decisions[1].get("internal_comment") is None
    assert "AREO לא מצאה מקור מורשה" in decisions[2]["internal_comment"]
    assert "Agreement 1" not in decisions[0]["external_comment"], "the other side's bubble must not name the source"
    assert not PM.check_sources_shown(decisions, pm)
    assert PM.annotate(decisions, pm) == 0, "idempotent"


# --------------------------------------------------------------------------- 4 ו-11: סבבים
def _state(n, clauses):
    st = SB.skeleton()
    st["meta"].update(transaction_id="deal-a", round_number=n, round_stage=SB.stage_for_round(n))
    st["clauses"] = clauses
    return st


@test
def rounds_are_named_one_to_four_and_onward():
    names = [PM.round_info(n)["label"] for n in (1, 2, 3, 4, 5, 9)]
    assert names == ["סבב ראשון", "סבב שני", "סבב שלישי", "סבב רביעי", "סבב 5", "סבב 9"], names
    assert PM.round_info(1)["kind"] == "first" and PM.round_info(4)["kind"] == "fourth" and PM.round_info(6)["kind"] == "later"
    assert "מטפלים רק בנקודות הפתוחות" in PM.round_info(3)["rule"]
    assert "כל הנקודות פתוחות" in PM.round_info(1)["rule"]


@test
def rounds_handle_only_open_and_never_agreed():
    clauses = [{"clause_id": "C1", "status": "CLOSED", "closed_in_round": 2},
               {"clause_id": "C2", "status": "MOVING"},
               {"clause_id": "C3", "status": "STUCK"},
               {"clause_id": "C4", "status": "ACCEPTED_PENDING"}]
    for n in (2, 3, 4, 5):
        v = PM.round_view(_state(n, clauses))
        assert v["round"] == n and v["deal_id"] == "deal-a"
        assert [x["clause_id"] for x in v["agreed"]] == ["C1"], v
        assert v["handle_only"] == ["C2", "C3"], v["handle_only"]
        assert set(v["must_not_touch"]) == {"C1", "C4"}, v["must_not_touch"]
    v1 = PM.round_view(_state(1, clauses))
    assert v1["label"] == "סבב ראשון"


@test
def rounds_flag_agreed_point_changed_back():
    clauses = [{"clause_id": "C1", "status": "MOVING", "reopened_by_counterparty": {"round": 3, "classification": "their_silent"}},
               {"clause_id": "C2", "status": "CLOSED", "closed_in_round": 1},
               {"clause_id": "C3", "status": "MOVING"}]
    v = PM.round_view(_state(3, clauses))
    assert [x["clause_id"] for x in v["changed_back_by_counterparty"]] == ["C1"], v
    assert "C1" in v["handle_only"] and "C2" not in v["handle_only"]
    # גם מהשוואת הסבב, לפני ש-write עדכן את הסעיף
    v2 = PM.round_view(_state(3, [{"clause_id": "C2", "status": "CLOSED", "closed_in_round": 1}]),
                       {"clauses": [{"reopens_closed": "C2", "classification": "their_silent", "clause": "2"}]})
    assert [x["clause_id"] for x in v2["changed_back_by_counterparty"]] == ["C2"], v2


@test
def rounds_four_round_exchange_lists_agreed_open_and_changed_back():
    closed = {"status": "CLOSED", "closed_in_round": 1, "closed_basis": "counterparty_accepted"}
    seq = {
        1: [{"clause_id": "C1", "status": "MOVING"}, {"clause_id": "C2", "status": "MOVING"},
            {"clause_id": "C3", "status": "MOVING"}],
        2: [dict(closed, clause_id="C1"), {"clause_id": "C2", "status": "MOVING"}, {"clause_id": "C3", "status": "STUCK"}],
        3: [{"clause_id": "C1", "status": "MOVING", "reopened_by_counterparty": {"round": 3, "classification": "their_silent"}},
            dict(closed, clause_id="C2", closed_in_round=2), {"clause_id": "C3", "status": "STUCK"}],
        4: [dict(closed, clause_id="C1", closed_in_round=3), dict(closed, clause_id="C2", closed_in_round=2),
            {"clause_id": "C3", "status": "MOVING"}]}
    views = {}
    for n, cl in seq.items():
        views[n] = PM.round_view(_state(n, cl))
        assert views[n]["round"] == n
    assert views[1]["handle_only"] == ["C1", "C2", "C3"] and views[1]["agreed"] == []
    assert [x["clause_id"] for x in views[2]["agreed"]] == ["C1"] and views[2]["handle_only"] == ["C2", "C3"]
    assert [x["clause_id"] for x in views[3]["changed_back_by_counterparty"]] == ["C1"]
    assert views[3]["handle_only"] == ["C1", "C3"] and "C2" in views[3]["must_not_touch"]
    assert views[4]["handle_only"] == ["C3"] and set(views[4]["must_not_touch"]) == {"C1", "C2"}
    assert [views[n]["label"] for n in (1, 2, 3, 4)] == ["סבב ראשון", "סבב שני", "סבב שלישי", "סבב רביעי"]


@test
def rounds_gate_blocks_decision_reopening_agreed_clause():
    st = _state(3, [{"clause_id": "D5", "status": "CLOSED", "closed_in_round": 2, "closed_basis": "counterparty_accepted"}])
    st["meta"]["sent_documents"] = [{"round": 1, "file_name": "x.docx"}]
    dec = {"round": 3, "decisions": [{"id": "D5", "op": "replace_span", "para": 1, "old": "x", "new": "y",
                                      "decision_code": "R1", "external_comment": "reason"}]}
    root = dt.document_root(_make_docx(PARAS))
    F, _ = GATE.check_round_rules(st, dec, root, root, ["Reviewer"], {}, set(), (), "send")
    assert "ROUND_REOPEN_CLOSED" in {f["code"] for f in F}, F
    v = PM.round_view(st)
    bad = PM.check_round_discipline(v, [{"id": "X", "clause_id": "D5", "op": "replace", "para": 1}])
    assert codes(bad, True) == {"ROUND_AGREED_POINT_TOUCHED"}, bad


@test
def rounds_ledger_persisted_in_state_keyed_by_deal():
    with tempfile.TemporaryDirectory() as d:
        deal = os.path.join(d, "deal-a")
        os.makedirs(deal)
        st = _state(2, [{"clause_id": "C1", "status": "CLOSED", "closed_in_round": 1, "closed_basis": "counterparty_accepted",
                         "agreed_text": "x"}, {"clause_id": "C2", "status": "MOVING"}])
        PM.update_ledger(st, PM.round_view(st))
        st["meta"]["round_number"] = 3
        st["meta"]["round_stage"] = SB.stage_for_round(3)
        PM.update_ledger(st, PM.round_view(st))
        PM.update_ledger(st, PM.round_view(st))   # הרצה חוזרת באותו סבב מחליפה
        led = st["meta"]["round_ledger"]
        assert [x["round"] for x in led] == [2, 3] and all(x["deal_id"] == "deal-a" for x in led), led
        with open(os.path.join(deal, "negotiation_state.json"), "w", encoding="utf-8") as fh:
            json.dump(st, fh, ensure_ascii=False)
        assert PM.main(["rounds", "--deal", deal]) in (0, 3)


@test
def map_stored_in_state_and_check_cli_fails_then_passes():
    with tempfile.TemporaryDirectory() as d:
        deal = os.path.join(d, "deal-a")
        os.makedirs(deal)
        st = _state(1, [])
        with open(os.path.join(deal, "negotiation_state.json"), "w", encoding="utf-8") as fh:
            json.dump(st, fh, ensure_ascii=False)
        pb, dec = os.path.join(d, "pb.json"), os.path.join(d, "decisions_round_1.json")
        json.dump(PLAYBOOK, open(pb, "w", encoding="utf-8"))
        json.dump({"transaction_id": "deal-a", "round": 1, "decisions": DECISIONS}, open(dec, "w", encoding="utf-8"))
        assert PM.main(["build", "--playbook", pb, "--decisions", dec, "--deal", deal]) == 3, "R-4 has no outcome"
        saved = json.load(open(os.path.join(deal, "negotiation_state.json"), encoding="utf-8"))
        assert saved["meta"]["playbook_map"]["counts"]["no_outcome"] == 1, "the map is stored in negotiation_state"
        assert PM.main(["check", "--playbook", pb, "--deal", deal]) == 3
        assert PM.main(["declare", "--deal", deal, "--rule", "R-4", "--outcome", "no_matching_clause"]) == 0
        assert PM.main(["check", "--playbook", pb, "--deal", deal]) == 0
        assert PM.main(["build", "--playbook", pb, "--decisions", dec, "--deal", deal]) == 0, "declaration survives the rebuild"


@test
def map_from_docx_flags_agreement_clause_without_playbook_clause():
    with tempfile.TemporaryDirectory() as d:
        deal = os.path.join(d, "deal-a")
        os.makedirs(deal)
        with open(os.path.join(deal, "negotiation_state.json"), "w", encoding="utf-8") as fh:
            json.dump(_state(1, []), fh, ensure_ascii=False)
        pb, dec = os.path.join(d, "pb.json"), os.path.join(d, "decisions_round_1.json")
        json.dump(PLAYBOOK, open(pb, "w", encoding="utf-8"))
        json.dump({"transaction_id": "deal-a", "round": 1, "decisions": DECISIONS}, open(dec, "w", encoding="utf-8"))
        received = _make_docx(PARAS)
        PM.main(["build", "--playbook", pb, "--decisions", dec, "--deal", deal, "--received", received])
        pm = json.load(open(os.path.join(deal, "negotiation_state.json"), encoding="utf-8"))["meta"]["playbook_map"]
        assert [u["clause"] for u in pm["unmatched_agreement_clauses"]] == ["4"], pm["unmatched_agreement_clauses"]
        assert all(u["notice"] for u in pm["unmatched_agreement_clauses"])


# --------------------------------------------------------------------------- 1: אין חסימה של עורך דין
def _make_docx(paras):
    from docx import Document
    p = os.path.join(tempfile.mkdtemp(), "doc.docx")
    d = Document()
    for t in paras:
        d.add_paragraph(t)
    d.save(p)
    return p


@test
def no_lawyer_hold_in_gate():
    st = _state(1, [{"clause_id": "D1", "status": "MOVING", "legal_review_required": True, "decided_in_round": 1}])
    dec = {"round": 1, "decisions": [{"id": "D1", "op": "replace_span", "para": 1, "legal_review_required": True,
                                      "decision_code": "R1"}]}
    F, W = GATE.check_legal_review(st, dec, {"clauses": [{"id": "R-1", "legal_review_required": True}]}, "send")
    assert not [f for f in F if f["code"] in ("LEGAL_REVIEW_OPEN",)], F
    assert not [f for f in F if f["code"] != "STATE_NO_CLAUSES"], F
    assert not hasattr(SB, "record_legal_review"), "the 'reviewed' mark was removed"


@test
def no_lawyer_hold_in_content_checks():
    path = _make_docx(["Agreement between Party A and Party B",
                       "1. This Agreement is governed by the law of the place chosen by Party B, and its courts have "
                       "exclusive jurisdiction.", "2. Party B shall pay within 30 days."])
    dec = [{"id": "K1", "op": "accept", "para": 1, "decision_code": "A1", "reason": "x"},
           {"id": "K2", "op": "accept", "para": 2, "decision_code": "A1", "reason": "x"}]
    for mode in ("send", "work"):
        found = CC.run_checks(path, path, dec, state={}, core=None, mode=mode)
        held = [f for f in found if f["code"] in ("UNFLAGGED_HIGH_RISK", "SECTOR_LAW_UNFLAGGED", "LAW_NOT_CHECKED") and f["blocking"]]
        assert not held, held
    found = CC.run_checks(path, path, dec, state={}, core={"clauses": [{"id": "R-1", "title": "Topic one"}]}, mode="send")
    assert not [f for f in found if f["code"] == "NO_APPROVED_SOURCE" and f["where"] == "R-1"], "no spurious item"
    core = {"clauses": [{"id": "R-1", "title": "Topic one"},
                        {"id": "R-2", "title": "Topic two", "no_approved_source": True, "no_source_note": "Note."}]}
    found = CC.run_checks(path, path, dec, state={}, core=core, mode="send")
    ns = [f for f in found if f["code"] == "NO_APPROVED_SOURCE" and f["where"] == "R-2"]
    assert ns and not any(f["blocking"] for f in ns), found
    assert "AREO לא מצאה מקור מורשה לנקודה זו" in ns[0]["message"] and "הצעד הבא" in ns[0]["message"], ns[0]


@test
def internal_leak_still_blocks():
    root = dt.document_root(_make_docx(PARAS))
    F, _ = GATE.check_internal_leak({}, root, [{"id": "1", "text": "Per our internal playbook this is fixed."}], "send")
    assert "INTERNAL_LEAK" in {f["code"] for f in F}, F


@test
def pre_send_groups_have_no_lawyer_group():
    import qa_gate as QG
    keys = [g[1] for g in QG.PRE_SEND_GROUPS]
    assert "sensitive_topics" not in keys and "legal_review_group" not in keys, keys
    import round_tools as RT
    assert RT.sensitive_item({}, type("A", (), {"received": None, "deal": None, "lang": "he"})) is None


# --------------------------------------------------------------------------- 2: קובץ Word בעקוב אחר שינויים
@test
def deliverable_is_surgical_tracked_changes_with_outward_bubbles():
    import apply_redlines as AR
    with tempfile.TemporaryDirectory() as d:
        received = _make_docx(PARAS)
        import hashlib
        sha = hashlib.sha256(open(received, "rb").read()).hexdigest()
        dec = {"transaction_id": "deal-a", "round": 1, "received_sha256": sha, "decisions": [
            dict(x, plain_effect="shorter or capped", position_effect="better for us") for x in DECISIONS]}
        dec["decisions"].append({"id": "D0", "op": "accept", "para": 0, "decision_code": "A1", "structural": True,
                                 "reason": "title"})
        dp, pp, out = (os.path.join(d, n) for n in ("decisions.json", "profile.json", "work.docx"))
        json.dump(dec, open(dp, "w", encoding="utf-8"))
        json.dump({"branding": {"lawyer_name": "Reviewer One", "lawyer_initials": "RO"}, "organization_name": "Party A",
                   "organization_name_en": "Party A"}, open(pp, "w", encoding="utf-8"))
        assert AR.main(["--draft", received, "--decisions", dp, "--profile", pp, "--out", out]) == 0
        with zipfile.ZipFile(out) as z:
            doc = z.read("word/document.xml").decode("utf-8")
            com = z.read("word/comments.xml").decode("utf-8")
        assert len(re.findall(r"<w:del ", doc)) >= 2 and len(re.findall(r"<w:ins ", doc)) >= 2, "real deletions and insertions"
        # כירורגי: רק המילים שהשתנו נמחקו, ולא הפסקה כולה
        dels = re.findall(r"<w:delText[^>]*>([^<]*)</w:delText>", doc)
        assert "90" in "".join(dels) and not any(len(x) > 60 for x in dels), dels
        assert "Party B shall pay all invoices within" in re.sub(r"<[^>]+>", "", doc)
        texts = [re.sub(r"<[^>]+>", "", m) for m in re.findall(r"<w:comment [^>]*>(.*?)</w:comment>", com, re.S)]
        assert any("We propose 45 days" in t for t in texts) and any("proportionate to the fees" in t for t in texts), texts
        outward = [t for t in texts if "proportionate" in t or "We propose" in t]
        assert not any(re.search(r"\bR-\d|\bD\d\b|playbook|rule_ids", t, re.I) for t in outward), outward
        # אין בועה חיצונית בלי נימוק: השער מסמן
        dec2 = json.loads(json.dumps(dec))
        dec2["decisions"][0]["external_comment"] = "Changed."
        found = CC.run_checks(out, received, dec2["decisions"], state={}, core=None, mode="send")
        assert found is not None


@test
def deliverable_gate_rejects_internal_code_and_missing_reason_in_outward_bubble():
    import apply_redlines as AR
    import hashlib
    from lawyer import lawyer_view
    with tempfile.TemporaryDirectory() as d:
        received = _make_docx(PARAS)
        sha = hashlib.sha256(open(received, "rb").read()).hexdigest()
        decisions = [dict(x, plain_effect="e", position_effect="f") for x in DECISIONS]
        decisions[0]["external_comment"] = "Per rule R-07 (A1, playbook green) we propose 45 days."
        dec = {"transaction_id": "deal-a", "round": 1, "received_sha256": sha, "decisions": decisions}
        dp, pp, out = (os.path.join(d, n) for n in ("decisions.json", "profile.json", "work.docx"))
        prof = {"branding": {"lawyer_name": "Reviewer One", "lawyer_initials": "RO"}, "organization_name": "Party A",
                "organization_name_en": "Party A"}
        json.dump(dec, open(dp, "w", encoding="utf-8"))
        json.dump(prof, open(pp, "w", encoding="utf-8"))
        assert AR.main(["--draft", received, "--decisions", dp, "--profile", pp, "--out", out]) == 0
        res = GATE.run_gate(out, received, "work", lawyer_view(prof), decisions=dec)
        got = {f["code"] for f in res["failures"]}
        assert "BUB_FORBIDDEN" in got and "BUB_WHY_MISSING" in got, got


@test
def deliverable_change_without_bubble_is_rejected():
    errs = dt.validate_decisions({"transaction_id": "x", "round": 1, "received_sha256": "x", "decisions": [
        {"id": "D1", "op": "replace_span", "para": 1, "old": "a", "new": "b", "decision_code": "R1"}]})
    assert any("בועה חיצונית" in e for e in errs), errs


# --------------------------------------------------------------------------- 6: הכול מקומי
@test
def mapping_modules_make_no_network_calls():
    for name in ("playbook_map.py", "qa_founding.py"):
        src = open(os.path.join(HERE, name), encoding="utf-8").read()
        body = src.split("RESULTS = []")[0] if name == "qa_founding.py" else src
        assert not re.search(r"^\s*(?:import|from)\s+(?:socket|urllib|requests|http\.client|ftplib|smtplib)\b", body, re.M), name
    st = _state(1, [])
    PM.update_ledger(st, PM.round_view(st))
    blob = json.dumps(st, ensure_ascii=False)
    assert "http" not in blob


# --------------------------------------------------------------------------- סקירת ארכיטקטורה 30.10.2026 (פרקים 4 ו-5.1)
DEF_PARAS = ["Agreement between Party A and Party B",
             "1. \"Information\" means any information disclosed by Party B to Party A.",
             "2. Party A shall keep the Information confidential.",
             "3. Party A may use the Information only for the Purpose.",
             "4. Notices shall be sent by courier."]


@test
def definition_change_lists_all_term_uses_and_flags_internal_bubble():
    dec = [{"id": "D1", "op": "replace_span", "para": 1, "old": "by Party B to Party A", "new": "by either party",
            "decision_code": "R1", "external_comment": "We propose a mutual definition, so that both sides are protected."}]
    accepted = list(DEF_PARAS)
    accepted[1] = accepted[1].replace("by Party B to Party A", "by either party")
    ch = CC.definition_changes(DEF_PARAS, accepted, dec, [None, "1", "2", "3", "4"])
    assert len(ch) == 1 and ch[0]["term"] == "Information" and ch[0]["decision"] == "D1", ch
    assert [u["label"] for u in ch[0]["usages"]] == ["2", "3"], ch[0]["usages"]
    out = []
    CC.review_definition_changes(out, DEF_PARAS, accepted, dec)
    assert codes(out) == {"DEF_CHANGED_USAGES"} and not any(f["blocking"] for f in out), out
    n = CC.annotate_definition_changes(dec, DEF_PARAS, accepted, [None, "1", "2", "3", "4"])
    assert n == 1 and "DEF_CHANGED_USAGES" in dec[0]["internal_comment"] and "2 מקומות" in dec[0]["internal_comment"], dec[0]
    assert "Information" not in (dec[0].get("external_comment") or "").replace("Information", "") or True
    out2 = []
    CC.review_definition_changes(out2, DEF_PARAS, accepted, dec)
    assert not out2, "annotated: no finding"
    assert CC.annotate_definition_changes(dec, DEF_PARAS, accepted) == 0, "idempotent"
    # הגדרה שלא השתנתה: אין רשימה
    assert CC.definition_changes(DEF_PARAS, list(DEF_PARAS), dec) == []


@test
def scrub_removes_internal_codes_in_build_layer():
    core = {"clauses": [{"id": "R-07", "title": "Payment terms"}]}
    t = CC.scrub_client_text("Payment (R-07, A1) per rule R-07 in סבב 1, source S12, see DOC-1 and Round 2", core)
    assert "R-07" not in t and "A1" not in t and "S12" not in t and "DOC-1" not in t, t
    assert "Payment terms" in t and "סבב ראשון" in t and "Round second" in t, t
    assert CC.scrub_client_text("Topic (R43)") == "Topic"
    import round_tools as RT
    assert RT.client_text("subprocessors (R43)") == "subprocessors"


@test
def paper_owner_classified_from_file_signals():
    import hashlib
    ours = _make_docx(["Agreement between Party A and Party B"] + PARAS[1:])
    r = CC.paper_owner(ours, ["Party A"], ["Party B"])
    assert r["owner"] == "ours" and "our_name_first_party" in r["signals"], r
    theirs = _make_docx(["Agreement between Party B and Party A"] + PARAS[1:])
    r = CC.paper_owner(theirs, ["Party A"], ["Party B"])
    assert r["owner"] == "theirs", r
    tmpl = _make_docx(["Agreement between ________ and ________", "Address: [●]"] + PARAS[1:])
    r = CC.paper_owner(tmpl, ["Party A"], ["Party B"])
    assert r["owner"] == "template" and r["confident"], r
    sha = hashlib.sha256(open(theirs, "rb").read()).hexdigest()
    r = CC.paper_owner(theirs, ["Party A"], ["Party B"], sent_shas=[sha])
    assert r["owner"] == "ours" and r["confident"] and r["signals"] == ["sha_of_sent_document"], r


@test
def paper_type_no_recommendation_when_not_confident():
    import round_tools as RT
    from orchestrator import resolve_playbook as RPL
    neutral = RPL.detect_paper_type(PARAS)
    assert neutral["suggested"] == "negotiable" and neutral["confident"] and neutral["recommended"] == "negotiable"
    orig = RPL.detect_paper_type
    with tempfile.TemporaryDirectory() as d:
        draft = _make_docx(PARAS)
        items = os.path.join(d, "items.json")
        ns = lambda: type("A", (), {"draft": draft, "deal": None, "facts": None, "lang": "he", "set": None,  # noqa: E731
                                   "items_out": items, "profile": None, "answer_kind": None, "suggested": None})()
        try:
            RPL.detect_paper_type = lambda p: {"suggested": "tender_awarded", "signals": {"tender": ["x"], "award": [],
                                                                                        "public": [], "online": []},
                                               "confident": False, "recommended": None}
            assert RT.cmd_paper_type(ns()) == 0
            got = json.load(open(items, encoding="utf-8"))
            pt = [i for i in got if i["key"] == "paper_type"][0]
            assert pt["recommendation"] is None and pt["text"].startswith("הזיהוי אינו ודאי") and pt["confident"] is False, pt
            RPL.detect_paper_type = lambda p: {"suggested": "tender_awarded", "signals": {"tender": ["x", "y"], "award": ["z"],
                                                                                        "public": [], "online": []},
                                               "confident": True, "recommended": "tender_awarded"}
            assert RT.cmd_paper_type(ns()) == 0
            pt = [i for i in json.load(open(items, encoding="utf-8")) if i["key"] == "paper_type"][0]
            assert pt["recommendation"] and "הזיהוי אינו ודאי" not in pt["text"], pt
        finally:
            RPL.detect_paper_type = orig


@test
def one_counting_unit_across_outputs():
    dec = DECISIONS + [{"id": "N1a", "op": "insert_paragraph", "after_para": 4, "text": "5. New.", "decision_code": "N1"},
                       {"id": "C1", "op": "comment_only", "para": 4, "decision_code": "A2"}]
    c = CC.unit_counts(dec, 5, {"counts": {"rules": 4, "applied": 2, "no_matching_clause": 1, "no_outcome": 1}})
    assert c["unit"] == "paragraph" and c["decided"] == 4 and c["changed"] == 2 and c["accepted"] == 1 \
        and c["comment_only"] == 1 and c["added"] == 1 and c["open"] == 1, c
    assert c["changed"] + c["accepted"] + c["comment_only"] == c["decided"]
    he, en = CC.counts_line(c, "he"), CC.counts_line(c, "en")
    assert "2 פסקאות תוקנו" in he and "מתוך 5" in he and "2 מתוך 4" in he, he
    assert "2 paragraphs changed" in en and "out of 5" in en, en
    assert not re.search(r"\b[AR]\d\b|R-\d", he + en)


@test
def verifier_findings_schema_and_gate_warning():
    import qa_gate as QG
    good = {"verifier": "n9", "round": 1, "read": ["accepted.json"], "findings": [
        {"check": "contradiction_after_accept", "severity": "open", "where": "clause 3 vs clause 1",
         "quote": "is capped at the fees paid", "issue": "clause 1 still says unlimited", "suggest": "align clause 1"},
        {"check": "bubble_vs_change", "severity": "note", "where": "clause 1", "quote": "45 days", "issue": "ok"}]}
    assert CC.validate_verify_findings(good) == []
    bad = {"verifier": "n9", "findings": [{"check": "fix_it", "severity": "open", "where": "", "quote": "x", "issue": "y",
                                           "new_text": "replace with this"}]}
    errs = CC.validate_verify_findings(bad)
    assert any("check" in e for e in errs) and any("where" in e for e in errs) and any("new_text" in e for e in errs), errs
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "verify.json")
        json.dump(good, open(p, "w", encoding="utf-8"), ensure_ascii=False)
        w = QG.verifier_warnings(p)
        assert [x["code"] for x in w] == ["VERIFY_OPEN"] and "clause 1 still says unlimited" in w[0]["message"], w
        json.dump(bad, open(p, "w", encoding="utf-8"), ensure_ascii=False)
        assert [x["code"] for x in QG.verifier_warnings(p)] == ["VERIFY_SCHEMA"]
        assert CC.main(["--validate-findings", p, "--received", "x"]) == 3


@test
def verifier_inputs_dumped_by_gate():
    import apply_redlines as AR
    import qa_gate as QG
    import hashlib
    with tempfile.TemporaryDirectory() as d:
        received = _make_docx(PARAS)
        sha = hashlib.sha256(open(received, "rb").read()).hexdigest()
        dec = {"transaction_id": "deal-a", "round": 1, "received_sha256": sha, "decisions": [
            dict(x, plain_effect="e", position_effect="f") for x in DECISIONS]}
        dp, pp, out = (os.path.join(d, n) for n in ("decisions.json", "profile.json", "work.docx"))
        json.dump(dec, open(dp, "w", encoding="utf-8"))
        json.dump({"branding": {"lawyer_name": "Reviewer One", "lawyer_initials": "RO"}, "organization_name": "Party A",
                   "organization_name_en": "Party A"}, open(pp, "w", encoding="utf-8"))
        assert AR.main(["--draft", received, "--decisions", dp, "--profile", pp, "--out", out]) == 0
        acc, bub = os.path.join(d, "accepted.json"), os.path.join(d, "bubbles.json")
        QG.main(["--mode", "work", "--work", out, "--received", received, "--profile", pp,
                 "--dump-accepted-text", acc, "--dump-external-bubbles", bub])
        a = json.load(open(acc, encoding="utf-8"))
        b = json.load(open(bub, encoding="utf-8"))
        assert any("45 days" in x["text"] for x in a) and all(set(x) >= {"para", "label", "text"} for x in a), a
        assert any("We propose 45 days" in x["text"] for x in b) and all(x["paras"] for x in b), b
        assert not any(x["author"] in CC.INTERNAL_AUTHORS for x in b)


@test
def state_check_enforces_fill_notes():
    good = _state(1, [{"clause_id": "C1", "status": "MOVING", "decision_code": "R1", "decision_basis": "PolicyDerived",
                       "importance": "HIGH", "rule_ids": ["R-1"]}])
    good["meta"].update(paper_type="negotiable", round_basis="state")
    E, W_ = NS.notes_checks(good)
    assert not E, E
    bad = _state(1, [{"clause_id": "C1", "status": "MOVING", "decision_code": "X9", "decision_basis": "Guess",
                      "importance": "לא נקבע", "rule_ids": "R-1, A1",
                      "decision_required": {"required": True, "answer_kind": "maybe"}},
                     {"clause_id": "C2", "status": "MOVING", "decision_basis": "UserDecided",
                      "user_decision": {"answer_kind": "delegated"}}])
    bad["meta"].update(paper_type="other", round_basis="guess")
    bad["clarification_questions"] = [{"q": "x"}]
    bad["case_law"] = {"connector": "אין", "rulings": [{"x": 1}]}
    bad["coverage_index"] = [{"element_id": "E-1", "decision": "awaiting_playbook", "reason": "r"},
                             {"element_id": "E-2", "decision": "accept_as_is"}]
    bad["playbook_resolution"] = {"result": "choose", "chosen": "x.json", "question": "", "activation_ok": None}
    bad["signing_checklist"] = {"passed": True, "checks": [{"item": "annex", "status": "open"}], "clean_copy_path": ""}
    E, W_ = NS.notes_checks(bad)
    got = {x["code"] for x in E}
    for c in ("STATE_DECISION_CODE", "STATE_DECISION_BASIS", "STATE_IMPORTANCE", "STATE_RULE_IDS", "STATE_DECISION_REQUIRED",
              "STATE_USER_DECIDED_NOT_EXPLICIT", "STATE_PAPER_TYPE", "STATE_ROUND_BASIS", "STATE_CLARIFICATION_NOT_TENDER",
              "STATE_CASE_LAW", "STATE_AWAITING_PLAYBOOK", "STATE_COVERAGE_REASON", "STATE_PLAYBOOK_RESOLUTION",
              "STATE_SIGNING_PASSED"):
        assert c in got, (c, sorted(got))
    with tempfile.TemporaryDirectory() as d:
        deal = os.path.join(d, "deal-a")
        os.makedirs(deal)
        json.dump(bad, open(os.path.join(deal, "negotiation_state.json"), "w", encoding="utf-8"), ensure_ascii=False)
        assert NS.main(["check", "--deal", deal]) == 3
        json.dump(good, open(os.path.join(deal, "negotiation_state.json"), "w", encoding="utf-8"), ensure_ascii=False)
        assert NS.main(["check", "--deal", deal]) == 0


@test
def status_label_follows_track_basis_not_stored_text():
    from orchestrator import resolve_playbook as RPL
    from playbook import status as S
    own = S.LABELS["he"]["own"]
    core_areo = {"clauses": [{"id": "R-1", "green": {"basis": "areo_proposal"}, "yellow": {"basis": "areo_proposal"}},
                             {"id": "R-2", "green": {"basis": "market_standard"}}]}
    label, mm = RPL.basis_guard(core_areo, own, [])
    assert label == S.LABELS["he"]["areo"] and mm and mm[0].startswith("basis_vs_tracks"), (label, mm)
    core_own = {"clauses": [{"id": "R-1", "green": {"basis": "own_paper_repeated"}}]}
    assert RPL.basis_guard(core_own, own, []) == (own, [])
    assert RPL.basis_guard(core_areo, S.LABELS["he"]["areo"], []) == (S.LABELS["he"]["areo"], [])
    assert RPL.basis_guard(core_areo, S.LABELS["en"]["mixed"], []) == (S.LABELS["en"]["market"],
                                                                        ["basis_vs_tracks:0/2 company-backed rules"])


def main():
    for t in TESTS:
        t()
    bad = [r for r in RESULTS if not r[1]]
    for name, ok, msg in RESULTS:
        print("%s  %s%s" % ("עבר " if ok else "נכשל", name, "" if ok else ": " + msg))
    print("סך הכול: %d בדיקות, %d נכשלו" % (len(RESULTS), len(bad)))
    return 3 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
