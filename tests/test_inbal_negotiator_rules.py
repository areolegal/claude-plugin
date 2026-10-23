# -*- coding: utf-8 -*-
"""הערות ענבל לנושא ונותן, 22.10.2026: כל כלל שנאכף בשער, עם מקרה שהשער חייב לתפוס ומקרה שעליו לעבור (כלל 16).

הבדיקות רצות על הנוסח שמתקבל אחרי ההכרעות (content_checks.review_2210), ועל מנוע הסימון כשבועה של אשכול נפרשת
על כמה פסקאות (כלל 8). נתוני דמה בלבד.
"""
import json
import sys
from pathlib import Path

import pytest

PLUGIN = Path(__file__).resolve().parents[1]
LIB = PLUGIN / "areolegal" / "lib"
ORCH = PLUGIN / "areolegal" / "skills" / "contract-negotiation-orchestrator" / "scripts"
sys.path[:0] = [str(LIB), str(ORCH), str(LIB / "tests")]
docx = pytest.importorskip("docx")

import content_checks as C  # noqa: E402
import common.docx_tracked as dt  # noqa: E402
from common import vague_terms  # noqa: E402
from orchestrator import proportionality as P, qa_gate  # noqa: E402


def _docx(tmp_path, paras, name="received.docx"):
    d = docx.Document()
    for t in paras:
        d.add_paragraph(t)
    p = tmp_path / name
    d.save(str(p))
    return str(p)


def _codes(theirs, decisions, tmp_path, state=None, core=None):
    out = []
    C.review_2210(out, theirs, decisions, state or {}, core, _docx(tmp_path, theirs))
    return out


def _has(out, code, blocking=None):
    return any(f["code"] == code and (blocking is None or f["blocking"] == blocking) for f in out)


# ---------------------------------------------------------------- כלל 1: שלמות מבנית
def test_rule1_a_proviso_reference_left_without_its_proviso_blocks(tmp_path):
    theirs = ["1. הספק ימסור את הסחורה, ובלבד שהלקוח שילם מקדמה.", "2. בכפוף לסייג האמור, המסירה תהיה במחסן."]
    dec = [{"id": "D1", "op": "replace_span", "para": 0, "old": ", ובלבד שהלקוח שילם מקדמה", "new": ""}]
    assert _has(_codes(theirs, dec, tmp_path), "STRUCT_ORPHAN_PROVISO", blocking=True)
    assert not _has(_codes(theirs, [], tmp_path), "STRUCT_ORPHAN_PROVISO")


def test_rule1_deleting_the_paragraph_a_backward_reference_points_to_blocks(tmp_path):
    theirs = ["1. הלקוח ישלם תוך 30 יום.", "2. כאמור לעיל, איחור יישא ריבית."]
    dec = [{"id": "D1", "op": "delete_paragraph", "para": 0}]
    assert _has(_codes(theirs, dec, tmp_path), "STRUCT_BACKREF", blocking=True)
    state = {"checks_reviewed": [{"code": "STRUCT_BACKREF", "para": 1, "reason": "מפנה לסעיף 1 בפרק הקודם"}]}
    assert not _has(_codes(theirs, dec, tmp_path, state), "STRUCT_BACKREF")


def test_rule1_a_conjunction_left_before_a_deleted_last_item_blocks(tmp_path):
    theirs = ["הלקוח רשאי לסיים את ההסכם אם:", "(א) הספק הפר הפרה יסודית; או", "(ב) הספק נכנס להליכי חדלות פירעון.",
              "3. ההודעה תימסר בכתב."]
    dec = [{"id": "D1", "op": "delete_paragraph", "para": 2}]
    assert _has(_codes(theirs, dec, tmp_path), "STRUCT_DANGLING_CONJ", blocking=True)
    # "או" בסוף פריט שאחריו פריט נוסף הוא תקין
    assert not _has(_codes(theirs, [], tmp_path), "STRUCT_DANGLING_CONJ")


def test_rule1_a_conjunction_in_our_span_before_the_full_stop_blocks(tmp_path):
    theirs = ["הספק יחזיר את המידע, ימחק אותו או ישמיד אותו."]
    dec = [{"id": "D1", "op": "replace_span", "para": 0, "old": " ישמיד אותו", "new": ""}]
    assert _has(_codes(theirs, dec, tmp_path), "STRUCT_DANGLING_CONJ", blocking=True)


def test_rule1_emptying_a_list_leaves_its_lead_in_and_blocks(tmp_path):
    theirs = ["החריגים הם כדלקמן:", "(א) כוונה.", "(ב) רשלנות חמורה.", "5. הדין החל."]
    dec = [{"id": "D1", "op": "delete_paragraph", "para": 1}, {"id": "D2", "op": "delete_paragraph", "para": 2}]
    assert _has(_codes(theirs, dec, tmp_path), "STRUCT_LIST_EMPTY", blocking=True)


def test_rule1_an_obligation_inserted_as_a_proviso_is_flagged(tmp_path):
    dec = [{"id": "N1", "op": "insert_paragraph", "after_para": 0,
            "text": "ובלבד שהספק יתחייב למסור הודעה מראש."}]
    out = _codes(["1. הספק יספק את השירותים."], dec, tmp_path)
    assert _has(out, "STRUCT_PROVISO_ROLE", blocking=False)


# ---------------------------------------------------------------- כלל 2: סעיפים תלויים
THEIRS2 = ["1. \"המידע הסודי\" - כל מידע שנמסר בכתב.", "2. הצד המקבל ישמור את המידע הסודי.",
           "3. בכפוף לסעיף 1, הגילוי מותר לפי דין.", "4. הדין החל הוא דין ישראל."]


def test_rule2_a_regime_change_needs_a_decision_on_every_dependent(tmp_path):
    dec = [{"id": "D1", "op": "replace_span", "para": 0, "old": "בכתב", "new": "בכתב או בעל פה", "regime": "definition"}]
    out = _codes(THEIRS2, dec, tmp_path)
    assert _has(out, "DEPENDENT_UNDECIDED", blocking=True)
    msg = next(f["message"] for f in out if f["code"] == "DEPENDENT_UNDECIDED")
    assert msg.endswith("פסקאות 1, 2")      # המונח המוגדר בפסקה 1, וההפניה "לסעיף 1" בפסקה 2; לא פסקה 3


def test_rule2_keeping_a_dependent_needs_a_reason(tmp_path):
    dec = [{"id": "D1", "op": "replace_span", "para": 0, "old": "בכתב", "new": "בכתב או בעל פה", "regime": "definition",
            "dependents": [{"para": 1, "keep": True, "reason": "השמירה חלה על כל מידע סודי, גם בעל פה"},
                           {"para": 2, "keep": True}]}]
    out = _codes(THEIRS2, dec, tmp_path)
    assert _has(out, "DEPENDENT_KEEP_NO_REASON", blocking=True)
    dec[0]["dependents"][1]["reason"] = "הגילוי לפי דין אינו תלוי בצורת המסירה"
    assert not [f for f in _codes(THEIRS2, dec, tmp_path) if f["code"].startswith("DEPENDENT")]


def test_rule2_touching_a_definition_without_declaring_the_regime_warns_only(tmp_path):
    dec = [{"id": "D1", "op": "replace_span", "para": 0, "old": "\"המידע הסודי\"", "new": "\"המידע החסוי\""}]
    out = _codes(THEIRS2, dec, tmp_path)
    assert _has(out, "REGIME_UNDECLARED", blocking=False)
    assert not _has(out, "DEPENDENT_UNDECIDED")


# ---------------------------------------------------------------- כלל 3: בדיקת תוצאה
CORE3 = {"clauses": [{"id": "R-1", "title": "תקרת אחריות", "importance": "critical",
                      "post_checks": [{"id": "PC-1", "intent": "התקרה אינה חלה על החריגים",
                                       "pass_when": {"absent": [r"התקרה תחול גם על"]}, "scope": "whole_agreement"}]}]}


def test_rule3_the_outcome_check_runs_on_the_resulting_text(tmp_path):
    theirs = ["1. האחריות מוגבלת לתמורה.", "8. התקרה תחול גם על הפרת סודיות."]
    dec = [{"id": "D1", "op": "replace_span", "para": 0, "old": "לתמורה", "new": "לתמורה, למעט בהפרת סודיות",
            "rule_ids": ["R-1"]}]
    assert _has(_codes(theirs, dec, tmp_path, core=CORE3), "POST_CHECK_FAILED", blocking=True)
    dec.append({"id": "D2", "op": "delete_paragraph", "para": 1, "rule_ids": ["R-1"]})
    assert not _has(_codes(theirs, dec, tmp_path, core=CORE3), "POST_CHECK_FAILED")


def test_rule3_a_written_outcome_check_must_be_recorded(tmp_path):
    core = {"clauses": [{"id": "R-1", "importance": "high", "post_checks": [{"id": "PC-1",
                                                                              "pass_when": "הבלעדיות נשללה גם בסעיף זכות הסירוב"}]}]}
    dec = [{"id": "D1", "op": "replace", "para": 0, "new_text": "אין בלעדיות.", "rule_ids": ["R-1"]}]
    assert _has(_codes(["יש בלעדיות."], dec, tmp_path, core=core), "POST_CHECK_MANUAL")
    st = {"post_checks_done": [{"rule_id": "R-1", "id": "PC-1", "result": "fail"}]}
    assert _has(_codes(["יש בלעדיות."], dec, tmp_path, st, core), "POST_CHECK_FAILED", blocking=False)


# ---------------------------------------------------------------- כלל 4: עוגני זמן
def test_rule4_a_past_start_date_and_an_empty_anchor_are_questions_before_deciding(tmp_path):
    theirs = ["ההסכם ייכנס לתוקף ביום 1.1.2020.", "תקופת האחריות תימנה מיום ____.", "בהמשך להסכם מיום 5.3.2019."]
    out = _codes(theirs, [], tmp_path)
    found = {(f["code"], f["where"]) for f in out if f["code"] == "TIME_ANCHOR"}
    assert ("TIME_ANCHOR", "פסקה 0") in found and ("TIME_ANCHOR", "פסקה 1") in found
    assert ("TIME_ANCHOR", "פסקה 2") not in found      # הפניה להסכם קודם אינה עוגן
    st = {"time_anchors": [{"para": 0, "issue": "past", "status": "answered"},
                           {"para": 1, "issue": "empty", "status": "answered"}]}
    assert not _has(_codes(theirs, [], tmp_path, st), "TIME_ANCHOR")


# ---------------------------------------------------------------- כלל 5: מונחים עמומים
def test_rule5_a_vague_term_in_our_wording_warns_unless_it_has_a_test():
    assert [f["term"] for f in vague_terms.undefined("הספק יפעל לפי best practices.")] == ["best practices"]
    assert not vague_terms.undefined("הספק יפעל ברמה גבוהה, בהתאם לתקן ISO 27001.")
    assert not vague_terms.undefined("הספק יגיב תוך זמן סביר של 4 שעות.")


def test_rule5_the_gate_warns_on_our_text(tmp_path):
    dec = [{"id": "D1", "op": "replace", "para": 0, "new_text": "הספק יעבוד כמקובל בענף."}]
    out = _codes(["הספק יעבוד."], dec, tmp_path)
    assert _has(out, "VAGUE_TERM", blocking=False)


# ---------------------------------------------------------------- כללים 6 ו-7: עובדות וישות
def test_rule6_a_fact_about_a_party_needs_a_source(tmp_path):
    dec = [{"id": "D1", "op": "comment_only", "para": 0,
            "external_comment": "מאחר שאתם פועלים גם באירופה, נבקש להוסיף התחייבות לעמוד בדין שם."}]
    assert _has(_codes(["x"], dec, tmp_path), "FACT_WITHOUT_SOURCE", blocking=True)
    dec[0]["fact_source"] = "user_answer"
    assert not _has(_codes(["x"], dec, tmp_path), "FACT_WITHOUT_SOURCE")
    ok = [{"id": "D2", "op": "comment_only", "para": 0, "external_comment": "החברה פועלת בהתאם לדין, ולכן הוספנו."}]
    assert not _has(_codes(["x"], ok, tmp_path), "FACT_WITHOUT_SOURCE")


def test_rule7_profile_facts_do_not_apply_to_a_different_entity(tmp_path):
    core = {"clauses": [{"id": "R-9", "title": "דין ושיפוט"}]}
    st = {"meta": {"entity_check": {"match": "related", "facts_confirmed": False}}}
    dec = [{"id": "D1", "op": "replace", "para": 0, "new_text": "דין ישראל.", "rule_ids": ["R-9"],
            "fact_source": "profile"}]
    out = _codes(["דין דלאוור."], dec, tmp_path, st, core)
    assert _has(out, "ENTITY_PROFILE_FACT", blocking=True) and _has(out, "ENTITY_RULE_UNCONFIRMED", blocking=True)
    st["meta"]["entity_check"]["facts_confirmed"] = True
    out = _codes(["דין דלאוור."], dec, tmp_path, st, core)
    assert not _has(out, "ENTITY_PROFILE_FACT") and not _has(out, "ENTITY_RULE_UNCONFIRMED")


# ---------------------------------------------------------------- כלל 8: בועה אחת לכל נושא
def test_rule8_a_reference_bubble_blocks(tmp_path):
    dec = [{"id": "D2", "op": "replace_span", "para": 0, "old": "30", "new": "60", "external_comment": "ראו הערתנו לעיל."}]
    assert _has(_codes(["תוך 30 יום."], dec, tmp_path), "REF_BUBBLE", blocking=True)
    dec[0]["external_comment"] = "Part of the same change."
    assert _has(_codes(["תוך 30 יום."], dec, tmp_path), "REF_BUBBLE", blocking=True)


def test_rule8_two_bubbles_for_the_same_rule_in_the_same_clause_block(tmp_path):
    theirs = ["הספק ישפה תוך 30 יום בסכום של 1,000 ש\"ח."]
    dec = [{"id": "D1", "op": "replace_span", "para": 0, "old": "30", "new": "14", "rule_ids": ["R-3"],
            "external_comment": "קיצרנו את המועד לשיפוי."},
           {"id": "D2", "op": "replace_span", "para": 0, "old": "1,000", "new": "5,000", "rule_ids": ["R-3"],
            "external_comment": "הגדלנו את סכום השיפוי."}]
    assert _has(_codes(theirs, dec, tmp_path), "BUBBLE_SAME_TOPIC", blocking=True)


def test_rule8_a_cluster_has_one_bubble_in_the_decisions_file():
    base = {"transaction_id": "t", "round": 1, "received_sha256": "x"}
    two = dict(base, decisions=[
        {"id": "D1", "op": "replace_span", "para": 0, "old": "a", "new": "b", "decision_code": "R1", "cluster_id": "K1",
         "external_comment": "אחת."},
        {"id": "D2", "op": "replace_span", "para": 1, "old": "c", "new": "d", "decision_code": "R1", "cluster_id": "K1",
         "external_comment": "שתיים."}])
    assert any("יותר מבועה חיצונית אחת" in e for e in dt.validate_decisions(two))
    one = json.loads(json.dumps(two))
    del one["decisions"][1]["external_comment"]
    assert dt.validate_decisions(one) == []
    none = json.loads(json.dumps(one))
    del none["decisions"][0]["external_comment"]
    assert any("אין בועה חיצונית" in e for e in dt.validate_decisions(none))


def test_rule8_the_cluster_bubble_spans_both_paragraphs_and_covers_them(tmp_path):
    """המנוע פורש את הבועה מהפסקה הראשונה של האשכול ועד האחרונה, הלוך ושוב נשמר, והשער סופר אותה ככיסוי."""
    received = _docx(tmp_path, ["5.1 הספק ימסור הודעה תוך 30 ימים.", "5.2 ההודעה תכלול את פרטי האירוע.",
                                "5.3 הספק ימסור דוח תוך 60 ימים."])
    dec = {"transaction_id": "t", "round": 1, "received_sha256": "x", "decisions": [
        {"id": "D1", "op": "replace_span", "para": 0, "old": "30", "new": "3", "decision_code": "R1",
         "cluster_id": "K1", "rule_ids": ["R-5"],
         "external_comment": "קיצרנו את מועדי ההודעה והדוח ל-3 ול-14 ימים, כדי שהחברה תוכל לעמוד בחובת הדיווח שלה."},
        {"id": "D2", "op": "replace_span", "para": 2, "old": "60", "new": "14", "decision_code": "R1",
         "cluster_id": "K1", "rule_ids": ["R-5"]}]}
    res = dt.apply_decisions(received, dec, out_path=str(tmp_path / "work.docx"), author="עו\"ד בדיקה")
    assert res["ok"], res
    root = dt.document_root(str(tmp_path / "work.docx"))
    spans = dt.comment_paragraph_spans(root)
    ours = [c for c in dt.read_comments(str(tmp_path / "work.docx")) if c["author"] == "עו\"ד בדיקה"]
    assert len(ours) == 1
    assert spans[ours[0]["id"]] == (0, 2)
    ext = {i: [ours[0]["text"]] for i in range(0, 3)}
    assert not [f for f in qa_gate.check_coverage(root, ext, "עו\"ד בדיקה") if f["code"] == "COV_CHANGE_WITHOUT_BUBBLE"]
    assert dt.paragraph_views(root, "accept")[2] == "5.3 הספק ימסור דוח תוך 14 ימים."
    assert dt.paragraph_views(root, "reject")[0] == "5.1 הספק ימסור הודעה תוך 30 ימים."


def test_rule8_a_cluster_with_an_inserted_paragraph_spans_it_too(tmp_path):
    """פסקה שהוספנו נכנסת לעץ רק בסוף הסימון. גם אז הבועה של האשכול נפרשת עליה (נבדק גם ב-Word, 23.10.2026:
    שתי בועות, וכל אחת מכסה את כל האשכול שלה)."""
    received = _docx(tmp_path, ["5.3 הספק ימסור דוח.", "6. סעיף אחר."])
    dec = {"transaction_id": "t", "round": 1, "received_sha256": "x", "decisions": [
        {"id": "N1", "op": "insert_paragraph", "after_para": 0, "text": "5.4 הספק ישמור את הדוחות שבע שנים.",
         "decision_code": "N1", "cluster_id": "K2",
         "external_comment": "הוספנו חובת שמירה, כדי שאפשר יהיה לבדוק את הדוחות בעתיד."},
        {"id": "D3", "op": "replace_span", "para": 1, "old": "אחר", "new": "שונה", "decision_code": "R1",
         "cluster_id": "K2"}]}
    res = dt.apply_decisions(received, dec, out_path=str(tmp_path / "work.docx"), author="עו\"ד בדיקה")
    assert res["ok"], res
    root = dt.document_root(str(tmp_path / "work.docx"))
    assert list(dt.comment_paragraph_spans(root).values()) == [(1, 2)]
    assert dt.paragraph_views(root, "reject") == ["5.3 הספק ימסור דוח.", "6. סעיף אחר."]


# ---------------------------------------------------------------- כלל 9: חולשה בנימוק
def test_rule9_a_weakness_in_the_reasoning_warns(tmp_path):
    dec = [{"id": "D1", "op": "comment_only", "para": 0, "external_comment": "אין לנו חלופה לספק הזה, ולכן נבקש."}]
    assert _has(_codes(["x"], dec, tmp_path), "WEAKNESS_IN_BUBBLE", blocking=False)
    ok = [{"id": "D1", "op": "comment_only", "para": 0,
           "external_comment": "החברה זקוקה לזמן כדי להעביר את השירות לספק אחר בלי הפסקה בפעילות."}]
    assert not _has(_codes(["x"], ok, tmp_path), "WEAKNESS_IN_BUBBLE")


# ---------------------------------------------------------------- כללים 10 ו-11: הנוסח שלהם ורשימת המאבק
def test_rule10_their_green_wording_is_not_marked(tmp_path):
    dec = [{"id": "D1", "op": "replace_span", "para": 0, "old": "30", "new": "60", "their_track": "green",
            "rule_ids": ["R-1"]}]
    assert _has(_codes(["תוך 30 יום."], dec, tmp_path), "THEIR_GREEN_MARKED", blocking=True)


def test_rule10_asking_more_than_their_yellow_is_a_bargaining_chip(tmp_path):
    dec = [{"id": "D1", "op": "replace_span", "para": 0, "old": "30", "new": "60", "their_track": "yellow",
            "decision_code": "R1", "rule_ids": ["R-1"]}]
    assert _has(_codes(["תוך 30 יום."], dec, tmp_path), "THEIR_YELLOW_NOT_CHIP")
    dec[0].update(tier="tradeable", fallback="their_wording")
    assert not _has(_codes(["תוך 30 יום."], dec, tmp_path), "THEIR_YELLOW_NOT_CHIP")


def test_rule11_concessions_start_with_clauses_where_their_wording_is_yellow():
    dec = [{"id": "A", "decision_code": "R1", "importance": "low"},
           {"id": "B", "decision_code": "R1", "importance": "medium", "their_track": "yellow"}]
    assert P._concession_candidates(dec)[0]["id"] == "B"


def test_rule11_too_many_asks_stops_before_marking(tmp_path):
    dec = [{"id": "D%d" % i, "op": "comment_only", "para": 0, "decision_code": "R1"} for i in range(5)]
    st = {"meta": {"deal_context": {"proportionality": {"fight_list_size": 3}}}}
    assert _has(_codes(["x"], dec, tmp_path, st), "PROPORTIONALITY_UNASKED", blocking=True)
    st["meta"]["deal_context"]["proportionality"]["user_choice"] = "focused"
    assert not _has(_codes(["x"], dec, tmp_path, st), "PROPORTIONALITY_UNASKED")


# ---------------------------------------------------------------- כלל 12: זהות הצד שכנגד
def test_rule12_a_law_rule_against_a_foreign_party_needs_a_condition_or_a_decision(tmp_path):
    core = {"clauses": [{"id": "R-9", "title": "דין ושיפוט", "activation_conditions": []}]}
    st = {"meta": {"deal_context": {"counterparty_kind": ["foreign", "large"]}}}
    dec = [{"id": "D1", "op": "replace", "para": 0, "new_text": "דין ישראל.", "rule_ids": ["R-9"]}]
    assert _has(_codes(["דין אנגליה."], dec, tmp_path, st, core), "COUNTERPARTY_KIND_UNDECIDED", blocking=True)
    core["clauses"][0]["activation_conditions"] = [{"condition": "צד זר", "counterparty_kind": "foreign"}]
    assert not _has(_codes(["דין אנגליה."], dec, tmp_path, st, core), "COUNTERPARTY_KIND_UNDECIDED")
    st["meta"]["deal_context"]["counterparty_kind"] = ["local"]
    core["clauses"][0]["activation_conditions"] = []
    assert not _has(_codes(["דין אנגליה."], dec, tmp_path, st, core), "COUNTERPARTY_KIND_UNDECIDED")


# ---------------------------------------------------------------- כללים 3 ו-12 בגרעין הפלייבוק
PB = PLUGIN / "areolegal" / "skills" / "contract-playbook-builder" / "scripts"


def test_the_core_carries_post_checks_and_the_counterparty_kind(tmp_path):
    import subprocess
    m = json.loads((LIB / "tests" / "fixtures" / "playbook" / "mutual_nda_model_good.json").read_text(encoding="utf-8"))
    m.update(schema_version="2.0", core_version="3.2")
    m["rules"][0]["activation_conditions"] = [{"condition": "צד זר", "counterparty_kind": "foreign"}]
    m["rules"][0]["post_checks"] = [{"id": "PC-1", "intent": "התקרה אינה חלה על החריגים",
                                     "pass_when": {"absent": ["התקרה תחול גם על"]}, "on_fail": "block"}]
    mp = tmp_path / "playbook-model.json"
    mp.write_text(json.dumps(m, ensure_ascii=False), encoding="utf-8")
    r = subprocess.run([sys.executable, "-B", str(PB / "build_playbook_core.py"), "--model", str(mp)],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    core = json.loads((tmp_path / "playbook-core.json").read_text(encoding="utf-8"))
    c0 = core["clauses"][0]
    assert c0["post_checks"][0]["id"] == "PC-1"
    assert c0["activation_conditions"][0]["counterparty_kind"] == "foreign"


def test_the_validator_rejects_a_wrong_counterparty_kind_and_a_broken_post_check():
    sys.path.insert(0, str(PB))
    import validate_playbook_model as VM
    errors = []
    VM.validate_activation_and_post_checks(errors, {
        "activation_conditions": [{"condition": "x", "counterparty_kind": "overseas"}],
        "post_checks": [{"id": "PC-1", "intent": "i", "pass_when": {"absent": ["(unclosed"]}, "on_fail": "stop"}]},
        "rules[0]")
    joined = " ".join(errors)
    assert "counterparty_kind" in joined and "invalid pattern" in joined and "on_fail" in joined
    errors = []
    VM.validate_activation_and_post_checks(errors, {
        "activation_conditions": [{"condition": "x", "counterparty_kind": "any"}],
        "post_checks": [{"id": "PC-1", "intent": "i", "pass_when": "בדיקה ידנית"}]}, "rules[0]")
    assert errors == []


def test_rule2_the_marking_script_records_the_dependents_in_the_decisions_file(tmp_path):
    import apply_redlines as AR
    received = _docx(tmp_path, THEIRS2)
    dp = tmp_path / "decisions_round_1.json"
    dp.write_text(json.dumps({"decisions": [
        {"id": "D1", "op": "replace_span", "para": 0, "old": "בכתב", "new": "בכתב או בעל פה", "regime": "definition"},
        {"id": "D2", "op": "replace_span", "para": 3, "old": "ישראל", "new": "ישראל בלבד"}]}, ensure_ascii=False),
        encoding="utf-8")
    assert AR.record_dependents(received, str(dp)) == [("D1", "definition", [1, 2])]
    saved = json.loads(dp.read_text(encoding="utf-8"))["decisions"]
    assert saved[0]["dependents_found"] == [1, 2] and "dependents_found" not in saved[1]


def test_rule4_the_intake_command_lists_the_anchors(tmp_path, capsys):
    received = _docx(tmp_path, ["ההסכם ייכנס לתוקף ביום 1.1.2020.", "סעיף רגיל."])
    assert C.main(["--received", received, "--anchors"]) == 0
    got = json.loads(capsys.readouterr().out)
    assert [(x["para"], x["issue"]) for x in got] == [(0, "past")]
