from clm.validate import check_extraction
from helpers import make_extract


def test_base_extract_is_valid():
    assert check_extraction(make_extract("a" * 64, "הסכמים/x.docx")) == []


def test_bad_values_are_reported():
    ext = make_extract("a" * 64, "הסכמים/x.docx", doc_kind="contract")
    ext["our_role"]["source"] = "inferred_from_text"
    ext["events"][0]["event_code"] = "contract_date"
    ext["events"][0]["date"] = "30/11/2026"
    ext["coverage"] = ext["coverage"][:5]
    problems = " | ".join(check_extraction(ext))
    for needle in ("doc_kind", "our_role.source", "event_code", "date", "coverage"):
        assert needle in problems, needle


def test_relative_event_needs_trigger_and_long_dash_blocked():
    ext = make_extract("a" * 64, "הסכמים/x.docx")
    ext["events"][0].update(relative=True, date=None, trigger="")
    ext["title"] = "הסכם \u2014 בדיקה"
    problems = " | ".join(check_extraction(ext))
    assert "trigger" in problems and "מקף ארוך" in problems


def test_guarantee_direction_required():
    ext = make_extract("a" * 64, "הסכמים/x.docx", guarantees=[
        {"kind": "ערבות", "title": "ערבות בנקאית", "amount": "93,000 ₪", "expiry": "2026-09-05",
         "clause": "סעיף 9", "quote": "השוכר ימציא ערבות", "direction": "sideways"}])
    assert any("direction" in p for p in check_extraction(ext))


def test_non_object_root_is_problem_not_crash():
    for bad in (None, [1], "x", 5):
        problems = check_extraction(bad)
        assert problems and all(isinstance(p, str) for p in problems)
        assert any("מבנה פגום" in p for p in problems)


def test_null_optional_lists_are_empty():
    ext = make_extract("a" * 64, "הסכמים/x.docx", guarantees=None, key_clauses=None)
    assert check_extraction(ext) == []


def test_null_our_role_is_structure_problem():
    ext = make_extract("a" * 64, "הסכמים/x.docx", our_role=None)
    assert any("מבנה פגום" in p for p in check_extraction(ext))


def test_string_inside_events_is_problem_not_crash():
    ext = make_extract("a" * 64, "הסכמים/x.docx", events=["nonrenewal_notice"])
    problems = check_extraction(ext)
    assert any("events[0]" in p and "מבנה פגום" in p for p in problems)


def test_impossible_or_padded_dates_are_problems():
    for bad in ("2026-02-30", "2026-13-45", "2026-01-01\n"):
        ext = make_extract("a" * 64, "הסכמים/x.docx",
                           dates={"signed": bad, "start": "2025-03-01", "end": "2027-02-28"})
        assert any("signed" in p for p in check_extraction(ext)), repr(bad)
