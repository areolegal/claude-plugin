# -*- coding: utf-8 -*-
"""מחקר השוק של בונה הפלייבוק בקוד (`market_research.py`): הטווח, הבדיקות,
הקישורים, ההודעה והשאילתה. הכללים מ-`market-research.md`, "מהקידוד לטווח".
"""
import copy
import json
import subprocess
import sys
from pathlib import Path

import pytest

PLUGIN = Path(__file__).resolve().parents[1]
LIB = PLUGIN / "areolegal" / "lib"
S = PLUGIN / "areolegal" / "skills" / "contract-playbook-builder" / "scripts"
sys.path.insert(0, str(LIB))
sys.path.insert(0, str(S))

import market_research as MR  # noqa: E402

TOPIC = "הגבלת אחריות"


def ref(sid, drafted, body, family, stype=1, date="2024-03-01"):
    return {"source_id": sid, "drafted_by": drafted, "issuing_body": body, "template_family": family,
            "source_type": stype, "doc_date": date, "read_status": "read", "url": "https://example.gov/%s" % sid,
            "document": "מסמך %s" % sid, "agreement_type": "הסכם שירותים", "jurisdiction": "IL"}


def code(sid, level, status="agreed"):
    return {"source_id": sid, "topic": TOPIC, "level": level, "status": status}


def model(refs, coding, **kw):
    m = {"rules": [{"rule_id": "R-01", "topic": TOPIC, "traffic_light": {
            "green": {"basis": "market_standard", "range_point": "ours"},
            "yellow": {"basis": "market_standard", "range_point": "middle"},
            "red": {"basis": "market_standard", "range_point": "theirs"}}}],
         "corpus_origin": "market_built", "status_label": "פלייבוק מוצע, מבוסס מחקר שוק, טעון אישור",
         "market_research": {"source_refs": refs, "coding": coding, "research_date": "2026-10-15",
                             "question": {"agreement_type_he": "הסכם שירותים", "jurisdiction": "IL"}}}
    m.update(kw)
    return m


def full():
    refs = [ref("W1", "same_side", "a", "fa"), ref("W2", "same_side", "b", "fb", 2), ref("W3", "same_side", "c", "fc"),
            ref("W4", "negotiated", "d", "fd"), ref("W5", "negotiated", "e", "fe", 2), ref("W6", "neutral_model", "f", "ff"),
            ref("W7", "other_side", "g", "fg"), ref("W8", "other_side", "h", "fh"), ref("W9", "other_side", "i", "fi")]
    coding = [code("W1", 2), code("W2", 2), code("W3", 2), code("W4", 0), code("W5", 0), code("W6", 0),
              code("W7", -2), code("W8", -2), code("W9", -2)]
    return model(refs, coding)


def test_three_points_each_from_three_independent_sources():
    m = full()
    r = MR.compute_ranges(m)[0]
    assert r["ours"]["level"] == 2 and r["middle"]["level"] == 0 and r["theirs"]["level"] == -2
    assert r["yellow_from"] == "middle"
    assert m["market_research"]["counts"]["counted"] == 9


def test_two_sources_from_the_same_body_count_once():
    m = full()
    m["market_research"]["source_refs"][2]["issuing_body"] = "a"   # W3 מאותו גוף כמו W1
    r = MR.compute_ranges(m)[0]
    # ב-+2 נשארו שני גופים בלבד, ולכן "לטובתנו" יורדת לדרגה הבאה שיש לה שלושה (ההסכמים המנוהלים, 0)
    assert r["ours"]["level"] == 0 and "W3" not in r["ours"]["source_ids"]


def test_theirs_without_an_other_side_source_is_not_measured_and_red_fails():
    m = full()
    # אין מקור של הצד השני, ואין שלושה מקורות מנוהלים או מאוזנים: "לטובתם" אינה נמדדת
    for x in m["market_research"]["source_refs"][6:]:
        x["drafted_by"] = "same_side"
    m["market_research"]["coding"] = m["market_research"]["coding"][:4] + m["market_research"]["coding"][6:]
    r = MR.compute_ranges(m)[0]
    assert r["theirs"] is None and r["theirs_note"] == MR.NOT_MEASURED
    assert any(e.startswith("RED_THEIRS_NOT_MEASURED") for e in MR.check_model(m))


def test_when_the_middle_equals_green_yellow_is_not_the_middle():
    m = full()
    for c in m["market_research"]["coding"][3:6]:
        c["level"] = 2
    r = MR.compute_ranges(m)[0]
    assert r["ours"]["level"] == r["middle"]["level"] == 2
    assert r["yellow_from"] == "areo_compromise"


def test_uncertain_coding_is_expert_assessment():
    m = full()
    m["market_research"]["coding"].append(code("W4", 1, status="uncertain"))
    r = MR.compute_ranges(m)[0]
    assert r["middle"]["certainty"] == MR.CERTAINTY["expert"]


def test_accepted_wording_needs_a_point_that_meets_the_rule():
    m = full()
    MR.compute_ranges(m)
    m["rules"][0]["traffic_light"]["yellow"]["source_label"] = "הנוסח המקובל"
    assert not [e for e in MR.check_model(m) if e.startswith("MARKET_ACCEPTED")]
    m2 = full()
    m2["market_research"]["coding"] = m2["market_research"]["coding"][:5]   # רק שני מקורות באמצע
    MR.compute_ranges(m2)
    m2["rules"][0]["traffic_light"]["yellow"]["source_label"] = "הנוסח המקובל"
    assert [e for e in MR.check_model(m2) if e.startswith("MARKET_ACCEPTED")]


def test_market_playbook_without_a_disclosure_fails_and_the_message_fixes_it(tmp_path):
    m = full()
    MR.compute_ranges(m)
    assert any(e.startswith("MARKET_NO_DISCLOSURE") for e in MR.check_model(m))
    p = tmp_path / "m.json"
    p.write_text(json.dumps(m, ensure_ascii=False), encoding="utf-8")
    r = subprocess.run([sys.executable, "-B", str(S / "market_research.py"), "message", "--model", str(p)],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    saved = json.loads(p.read_text(encoding="utf-8"))
    disc = saved["market_research"]["disclosure"]
    assert disc["chat_message"].startswith(m["status_label"])
    assert "[פתיחה](https://example.gov/W1)" in disc["chat_message"]
    assert "9 משפחות תבנית" in disc["fixed_sentence"]
    assert not MR.check_model(saved)


def test_all_areo_sentence_is_refused_when_a_green_comes_from_the_company_template():
    m = full()
    MR.compute_ranges(m)
    m["market_research"]["disclosure"] = {"chat_message": "x " + MR.ALL_AREO, "fixed_sentence": MR.ALL_AREO}
    m["rules"][0]["traffic_light"]["green"]["basis"] = "own_paper_repeated"
    assert any(e.startswith("ALL_AREO_WITH_TEMPLATE") for e in MR.check_model(m))


def test_final_delivery_with_draft_rationale_needs_a_stop_reason():
    m = full()
    m["rules"][0]["rationale_status"] = "Draft"
    assert any(e.startswith("PASS_B_STOP_REASON") for e in MR.check_model(m, final=True))
    m["qa_summary"] = {"pass_b_stop_reason": "client_stop"}
    assert not [e for e in MR.check_model(m, final=True) if e.startswith("PASS_B")]


def test_the_query_never_carries_the_agreements_or_the_client():
    corpus = {"documents": [{"paragraphs": [{"text": "הספק לא יישא באחריות לנזק עקיף בסך 250,000 ש\"ח"}]}]}
    prof = {"organization_name": "חברת בדיקה"}
    assert MR.query_problem("לא יישא באחריות לנזק", "market", corpus, None)[0]
    assert "מספר" in MR.query_problem("limitation of liability 250,000", "market", corpus, None)[0]
    assert MR.query_problem("הסכם שירותים חברת בדיקה", "market", None, prof)[0]
    assert MR.query_problem("הסכם שירותי ענן הגבלת אחריות", "market", corpus, prof)[0] is None


def test_a_statute_name_is_allowed_only_in_a_legal_query():
    corpus = {"documents": [{"paragraphs": [{"text": "בהתאם לחוק הגנת הפרטיות התשמ\"א יחולו הוראות"}]}]}
    law = "חוק הגנת הפרטיות התשמ\"א"
    problem, allowed = MR.query_problem(law + " מאגר מידע", "legal", corpus, None, [law])
    assert problem is None and allowed == law
    assert MR.query_problem(law + " מאגר מידע", "market", corpus, None, [law])[0]


def test_a_failed_link_takes_the_source_out_and_the_range_is_recomputed(tmp_path, monkeypatch):
    from common import net
    m = full()
    MR.compute_ranges(m)
    p = tmp_path / "m.json"
    p.write_text(json.dumps(m, ensure_ascii=False), encoding="utf-8")

    def fake(url, purpose, **kw):
        bad = url.endswith("/W4")
        return {"status": 404 if bad else 200, "blocked": False, "reason": "http_error: 404" if bad else "ok",
                "text": None, "sha256": None}
    monkeypatch.setattr(net, "fetch", fake)
    args = type("A", (), {"model": str(p), "family_dir": str(tmp_path / "fam")})
    assert MR.cmd_links(args) == 3
    saved = json.loads(p.read_text(encoding="utf-8"))
    w4 = [r for r in saved["market_research"]["source_refs"] if r["source_id"] == "W4"][0]
    assert w4["read_status"] == "located_not_read" and "לא נפתח" in w4["read_reason"]
    assert all(r.get("link_checked_at") for r in saved["market_research"]["source_refs"])
    assert saved["market_research"]["ranges"][0]["middle"] is None   # נשארו שני מקורות באמצע


def test_no_network_code_in_the_builder_outside_the_shared_module():
    """שינוי 83.2: אין בבונה urllib, requests או זהות של דפדפן מחוץ לשכבת הרשת."""
    import re
    bad = []
    for f in S.glob("*.py"):
        t = f.read_text(encoding="utf-8")
        if re.search(r"^\s*(import|from)\s+(urllib\.request|requests|http\.client)\b", t, re.M) or \
                re.search(r"Mozilla/|Chrome/\d", t):
            bad.append(f.name)
    assert not bad, bad


def test_a_build_for_the_negotiator_returns_the_route_answer_and_at_most_three_decisions(tmp_path):
    import validate_playbook_model as V
    asked = {"asked_in": "builder", "answer_verbatim": "כן, תבנו", "choice": "market"}
    data = {"meta": {"build_request": {"requested_by": "negotiation_orchestrator", "route_answer": asked}},
            "handoff": {"route_answer": asked, "decisions_now": [{"question": "q", "recommendation": "r"}]},
            "validation_queue": [{"id": "Q-01", "question": "הבקשה נענתה. לאשר את הבחירה?"}]}
    errs = []
    V.handoff_findings(data, errs)
    assert any("Q-01" in e for e in errs)
    data["validation_queue"] = []
    errs = []
    V.handoff_findings(data, errs)
    assert errs == []
    data["handoff"]["decisions_now"] = [{"question": "q", "recommendation": "r"}] * 4
    data["handoff"]["route_answer"] = None
    errs = []
    V.handoff_findings(data, errs)
    assert len(errs) == 2


def test_the_word_is_one_file_in_two_parts(tmp_path):
    sys.path.insert(0, str(LIB / "tests"))
    import pb_helpers as H
    from docx import Document
    mp, pp, out = tmp_path / "m.json", tmp_path / "p.json", tmp_path / "pb.docx"
    mp.write_text(json.dumps(H.good_model(), ensure_ascii=False), encoding="utf-8")
    pp.write_text(json.dumps({"organization_name": "EXAMPLECO"}, ensure_ascii=False), encoding="utf-8")
    r = subprocess.run([sys.executable, "-B", str(S / "build_playbook_docx.py"), "--model", str(mp),
                        "--profile", str(pp), "--out", str(out)], capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    text = "\n".join(p.text for p in Document(str(out)).paragraphs)
    assert "חלק א: המדיניות לפי נושא" in text and "חלק ב: הנימוקים" in text
    assert text.index("חלק א: המדיניות") < text.index("חלק ב: הנימוקים")
