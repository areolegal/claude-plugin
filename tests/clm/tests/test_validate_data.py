import copy
import datetime as dt
from clm import assemble
from clm.validate import check_data
from helpers import make_extract


def good():
    s = "a" * 64
    scan = {"files": [{"path": "x/a - חתום.docx", "sha256": s, "status": "new", "abs": None, "duplicate_of": None}]}
    return assemble.assemble(scan, {s: make_extract(s, "x/a - חתום.docx")}, "חברה", dt.date(2026, 10, 22))


def test_assembled_data_is_valid():
    errors, _ = check_data(good())
    assert errors == []


def test_detects_broken_data():
    d = copy.deepcopy(good())
    d["events"][0]["state"] = "realized"
    d["events"][0]["refs"] = [99]
    d["events"][0]["action"] = "לבחון את הסעיף ולפעול לפי הנדרש בו."
    d["agreements"][0]["coverage"] = d["agreements"][0]["coverage"][:4]
    d["agreements"][0]["title"] = "הסכם \u2013 שבור"
    d["documents"][0]["doc_kind"] = "contract"
    errors = " | ".join(check_data(d)[0])
    for needle in ("realized", "99", "פעולה כללית", "coverage", "מקף ארוך", "doc_kind"):
        assert needle in errors, needle


def test_missing_top_level_key():
    d = good()
    del d["registers"]
    assert any("registers" in e for e in check_data(d)[0])


def test_non_dict_input_is_reported_not_raised():
    for bad in (None, []):
        errors, warns = check_data(bad)
        assert errors and warns == []


def test_malformed_event_is_reported_not_raised():
    d = copy.deepcopy(good())
    d["events"][0]["refs"] = None
    errors, _ = check_data(d)
    assert any("מבנה פגום" in e for e in errors)
    d = copy.deepcopy(good())
    del d["events"][0]["state"]
    errors, _ = check_data(d)
    assert any("מבנה פגום" in e for e in errors)


def test_source_removed_and_unknown_signature_are_valid():
    d = copy.deepcopy(good())
    carried = copy.deepcopy(d["agreements"][0])
    carried["id"], carried["number"], carried["source_removed"] = "ag-carried01", "CLM-2026-0099", True
    unknown = copy.deepcopy(d["agreements"][0])
    unknown["id"], unknown["number"], unknown["signature"] = "ag-unknown01", "CLM-2026-0100", "unknown"
    d["agreements"] += [carried, unknown]
    assert check_data(d)[0] == []


def test_duplicate_ids_and_numbers_are_errors():
    d = copy.deepcopy(good())
    d["agreements"].append(copy.deepcopy(d["agreements"][0]))
    d["events"].append(copy.deepcopy(d["events"][0]))
    errors = " | ".join(check_data(d)[0])
    assert "מזהה הסכם כפול" in errors and "מספר הסכם כפול" in errors and "מזהה מועד כפול" in errors
    d = copy.deepcopy(good())
    d["review_queue"].append(copy.deepcopy(d["review_queue"][0]))
    assert any("מזהה פריט אימות כפול" in e for e in check_data(d)[0])
