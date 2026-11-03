# -*- coding: utf-8 -*-
"""qa_summary.status Completed נבדק כבר בבנייה, ולא רק באישור (playbook-qa.md, "qa_summary").

בהרצה מקצה לקצה (02.11.2026) הבונה כתב qa_summary: {"status": "Completed"} בלי מספרים. הטיוטה עברה את
המאמת, ונפסלה ברגע שעורך הדין אישר אותה דרך ingest_approval.py --answer. מעכשיו הטיוטה עצמה נפסלת.
"""
import copy
import json
import sys
from pathlib import Path

import pytest

PLUGIN = Path(__file__).resolve().parents[1]
LIB = PLUGIN / "areolegal" / "lib"
PB = PLUGIN / "areolegal" / "skills" / "contract-playbook-builder" / "scripts"
FIX = LIB / "tests" / "fixtures" / "playbook"
sys.path[:0] = [str(LIB), str(PB)]

import validate_playbook_model as V  # noqa: E402


def _model():
    m = json.loads((FIX / "mutual_nda_model_good.json").read_text(encoding="utf-8"))
    rules = m["rules"]
    # וריאנט סגמנט אחד, כדי לבדוק שגם וריאנט צריך רשומת track_coherence
    rules[0]["segment_variants"] = [{"segment_id": "SEG1"}]
    return m


def _full_qa(m):
    tc = [{"rule_id": r["rule_id"], "result": "pass"} for r in m["rules"]]
    tc += [{"rule_id": r["rule_id"], "segment_id": v["segment_id"], "result": "pass"}
           for r in m["rules"] for v in r.get("segment_variants") or []]
    return {"status": "Completed", "tested_rule_count": len(m["rules"]), "tested_source_count": 3,
            "checked_at": "2026-11-02", "track_coherence": tc}


def _qa_errors(m):
    errors = []
    V.validate_qa_summary(errors, m)
    return errors


def test_a_draft_with_completed_and_no_counts_fails_at_build():
    m = _model()
    m["playbook_status"] = "Draft"
    m["qa_summary"] = {"status": "Completed"}       # מה שהבונה כתב בהרצה
    errs = " | ".join(_qa_errors(m))
    for key in ("tested_rule_count", "tested_source_count", "checked_at", "track_coherence"):
        assert key in errs


def test_a_complete_qa_summary_passes_as_draft_and_as_approved():
    m = _model()
    m["qa_summary"] = _full_qa(m)
    for status in ("Draft", "Approved"):
        m["playbook_status"] = status
        assert _qa_errors(m) == []


def test_tested_rule_count_must_equal_the_number_of_rules():
    m = _model()
    m["qa_summary"] = _full_qa(m)
    m["qa_summary"]["tested_rule_count"] = len(m["rules"]) - 1
    assert any("equal to the number of rules" in e for e in _qa_errors(m))


@pytest.mark.parametrize("drop", ["rule", "variant"])
def test_every_rule_and_every_variant_needs_a_track_coherence_entry(drop):
    m = _model()
    qa = _full_qa(m)
    rid = m["rules"][0]["rule_id"]
    if drop == "rule":
        qa["track_coherence"] = [e for e in qa["track_coherence"] if not (e["rule_id"] == rid and "segment_id" not in e)]
        want = rid
    else:
        qa["track_coherence"] = [e for e in qa["track_coherence"] if e.get("segment_id") != "SEG1"]
        want = f"{rid}/SEG1"
    m["qa_summary"] = qa
    errs = _qa_errors(m)
    assert len(errs) == 1 and want in errs[0]


def test_partial_and_notrun_do_not_need_the_counts():
    m = _model()
    m["playbook_status"] = "Draft"
    for status in ("Partial", "NotRun"):
        m["qa_summary"] = {"status": status}
        assert _qa_errors(m) == []


def test_approved_still_requires_completed():
    m = _model()
    m["playbook_status"] = "Approved"
    m["qa_summary"] = {"status": "Partial"}
    assert any("requires completed QA back-test" in e for e in _qa_errors(m))


def test_the_check_runs_inside_the_validator_command(tmp_path, capsys):
    m = _model()
    m["playbook_status"] = "Draft"
    m["qa_summary"] = {"status": "Completed"}
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps(m, ensure_ascii=False), encoding="utf-8")
    V.main(str(bad))
    assert "qa_summary status Completed requires tested_rule_count" in capsys.readouterr().out

    good = copy.deepcopy(m)
    good["qa_summary"] = _full_qa(good)
    ok = tmp_path / "ok.json"
    ok.write_text(json.dumps(good, ensure_ascii=False), encoding="utf-8")
    V.main(str(ok))
    assert "qa_summary status Completed" not in capsys.readouterr().out
