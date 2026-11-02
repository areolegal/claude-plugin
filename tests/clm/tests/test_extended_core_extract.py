from clm.validate import check_extraction
from helpers import make_extract
import clm_paths  # noqa: E402

GOOD = dict(
    term={"kind": "fixed", "initial_months": 24, "starts_on": "start", "max_end": None, "trigger": "",
          "clause": "סעיף 3.1", "quote": "תקופת ההסכם 24 חודשים מיום תחילתו."},
    renewal={"kind": "auto", "period_months": 12, "max_count": 3, "holder": None, "holder_name": None,
             "notice_days": 90, "clause": "סעיף 3.2", "quote": "ההסכם יתחדש אוטומטית."},
    exit={"who": "both", "who_name": None, "notice_days": 60, "min_commitment_months": 12,
          "clause": "סעיף 14", "quote": "כל צד רשאי לסיים בהודעה של 60 יום."},
    signatories=[{"party": "counterparty", "party_name": "ספק בדיקה בע\"מ", "name": "דנה לוי", "role": "מנכ\"לית",
                  "date": "2025-03-01", "status": "signed", "clause": "בלוק חתימות", "quote": "דנה לוי, מנכ\"לית"}],
    jurisdiction={"court": "בתי המשפט בתל אביב", "exclusive": True, "clause": "סעיף 20", "quote": "סמכות שיפוט ייחודית"},
    payment_terms={"days": 45, "basis": "eom", "text": "שוטף ועוד 45", "clause": "סעיף 7.3", "quote": "שוטף + 45"},
    facts=[{"code": "negotiation_stopped", "label": "המשא ומתן הופסק", "value": "הערה בשולי הטיוטה",
            "clause": "הערה", "quote": "המשא ומתן הופסק ביוזמת הלקוח"}],
)


def test_full_extended_core_is_valid():
    assert check_extraction(make_extract("a" * 64, "x.docx", **GOOD)) == []


def test_extended_fields_are_optional():
    assert check_extraction(make_extract("a" * 64, "x.docx")) == []
    assert check_extraction(make_extract("a" * 64, "x.docx", term=None, renewal=None, signatories=None)) == []


def test_bad_enums_are_reported():
    bad = make_extract("a" * 64, "x.docx",
                       term=dict(GOOD["term"], kind="forever"),
                       renewal=dict(GOOD["renewal"], kind="sometimes"),
                       exit=dict(GOOD["exit"], who="us"),
                       signatories=[dict(GOOD["signatories"][0], status="maybe", date="1.3.2025")],
                       payment_terms=dict(GOOD["payment_terms"], basis="net"),
                       facts=[dict(GOOD["facts"][0], code="gossip")])
    p = " | ".join(check_extraction(bad))
    for frag in ("term.kind", "renewal.kind", "exit.who", "signatories[0].status", "signatories[0]",
                 "payment_terms.basis", "facts[0].code"):
        assert frag in p, frag


def test_months_and_days_must_be_whole_numbers():
    bad = make_extract("a" * 64, "x.docx", term=dict(GOOD["term"], initial_months="24"),
                       renewal=dict(GOOD["renewal"], notice_days=-5))
    p = " | ".join(check_extraction(bad))
    assert "term.initial_months" in p and "renewal.notice_days" in p


def test_commercial_and_key_clause_extensions():
    ext = make_extract("a" * 64, "x.docx")
    ext["commercials"][0].update(value_kind="monthly", basis="fixed")
    ext["key_clauses"] = [{"clause_code": "non_compete", "summary": "", "value": "", "clause": "3.2", "quote": "q",
                           "bound_party": "contracting", "bound_party_name": "מדיקס", "stance": "set",
                           "norm": {"months": 120, "until": "2032-08-20", "territory": "ישראל"}},
                          {"clause_code": "change_of_control", "summary": "", "value": "", "clause": "9", "quote": "q",
                           "bound_party": "counterparty", "stance": "set", "norm": {"requires": "consent"}}]
    assert check_extraction(ext) == []
    ext["commercials"][0]["value_kind"] = "weekly"
    ext["key_clauses"][0]["bound_party"] = "them"
    ext["key_clauses"][0]["norm"]["until"] = "20.8.2032"
    ext["key_clauses"][1]["norm"]["requires"] = "maybe"
    ext["key_clauses"][1]["stance"] = "kind_of"
    p = " | ".join(check_extraction(ext))
    for frag in ("commercials[0].value_kind", "key_clauses[0].bound_party", "key_clauses[0].norm.until",
                 "key_clauses[1].norm.requires", "key_clauses[1].stance"):
        assert frag in p, frag


def test_term_role_only_on_term_end():
    ext = make_extract("a" * 64, "x.docx")
    ext["events"][0]["term_role"] = "initial_end"  # the base event is nonrenewal_notice
    assert any("term_role" in x for x in check_extraction(ext))
    ext["events"][0].update(event_code="term_end", term_role="max_end")
    assert check_extraction(ext) == []
    ext["events"][0]["term_role"] = "whenever"
    assert any("term_role" in x for x in check_extraction(ext))


def _kc(**kw):
    row = {"clause_code": "change_of_control", "summary": "", "value": "", "clause": "9", "quote": "q"}
    row.update(kw)
    return row


def test_norm_fields_may_be_null():
    ext = make_extract("a" * 64, "x.docx")
    ext["key_clauses"] = [_kc(norm={"requires": None, "months": None, "until": None})]
    assert check_extraction(ext) == []


def test_null_optional_enums_are_valid():
    ext = make_extract("a" * 64, "x.docx",
                       term=dict(GOOD["term"], starts_on=None),
                       renewal=dict(GOOD["renewal"], holder=None),
                       payment_terms=dict(GOOD["payment_terms"], basis=None))
    ext["commercials"][0].update(value_kind=None, basis=None)
    ext["key_clauses"] = [_kc(bound_party=None, stance=None, norm=None)]
    ext["events"][0].update(event_code="term_end", term_role=None)
    assert check_extraction(ext) == []


def test_exclusive_must_be_a_real_bool():
    for bad in (1, 0, 1.0, "true"):
        p = check_extraction(make_extract("a" * 64, "x.docx",
                                          jurisdiction=dict(GOOD["jurisdiction"], exclusive=bad)))
        assert any("jurisdiction.exclusive" in x for x in p), bad
    for ok in (True, False, None):
        assert check_extraction(make_extract("a" * 64, "x.docx",
                                             jurisdiction=dict(GOOD["jurisdiction"], exclusive=ok))) == []


def test_free_text_fields_must_be_strings_or_null():
    bad = make_extract(
        "a" * 64, "x.docx",
        term=dict(GOOD["term"], trigger=5),
        renewal=dict(GOOD["renewal"], holder_name=["x"]),
        exit=dict(GOOD["exit"], who_name=7),
        signatories=[dict(GOOD["signatories"][0], party_name=1, name={}, role=2)],
        jurisdiction=dict(GOOD["jurisdiction"], court=3),
        payment_terms=dict(GOOD["payment_terms"], text=4),
        facts=[dict(GOOD["facts"][0], label=5, value=6)])
    bad["key_clauses"] = [_kc(bound_party_name=8)]
    p = " | ".join(check_extraction(bad))
    for frag in ("term.trigger", "renewal.holder_name", "exit.who_name", "signatories[0].party_name",
                 "signatories[0].name", "signatories[0].role", "jurisdiction.court", "payment_terms.text",
                 "facts[0].label", "facts[0].value", "key_clauses[0].bound_party_name"):
        assert frag in p, frag
    assert check_extraction(make_extract("a" * 64, "x.docx",
                                         facts=[dict(GOOD["facts"][0], label="  ")])) != []


def test_malformed_types_give_problems_not_crashes():
    cases = [
        ({"term": "fixed"}, "term"),
        ({"signatories": {"a": 1}}, "signatories"),
        ({"signatories": ["x"]}, "signatories[0]"),
        ({"payment_terms": [1]}, "payment_terms"),
        ({"term": {"kind": ["x"]}}, "term.kind"),
        ({"facts": "x"}, "facts"),
    ]
    for over, frag in cases:
        p = check_extraction(make_extract("a" * 64, "x.docx", **over))
        assert p and any(frag in x for x in p), (over, p)
        assert not any("TypeError" in x or "AttributeError" in x for x in p), (over, p)
    ext = make_extract("a" * 64, "x.docx")
    ext["key_clauses"] = [_kc(norm=[1])]
    p = check_extraction(ext)
    assert any("norm" in x for x in p) and not any("TypeError" in x for x in p)
    ext = make_extract("a" * 64, "x.docx")
    ext["events"][0]["term_role"] = ["a"]
    assert any("term_role" in x for x in check_extraction(ext))
    ext["events"][0]["event_code"] = "term_end"
    assert any("term_role" in x for x in check_extraction(ext))
    ext["events"][0]["term_role"] = None
    ext["key_clauses"] = [_kc(norm={"months": "12"})]
    assert any("norm.months" in x for x in check_extraction(ext))


def test_not_relevant_is_an_allowed_end_status():
    from clm.validate import END_STATUSES
    assert "not_relevant" in END_STATUSES


def test_docs_example_is_valid_and_consistent():
    import json
    import re
    from pathlib import Path
    doc = (Path(clm_paths.REFS_DIR) / "extraction-format.md").read_text(encoding="utf-8")
    ex = json.loads(re.search(r"```json\n(.*?)\n```", doc, re.S).group(1))
    ex["sha256"] = "a" * 64
    assert check_extraction(ex) == []
    codes = {e["event_code"] for e in ex["events"]}
    assert "post_term" in codes
    assert all(e.get("term_role") is None for e in ex["events"] if e["event_code"] != "term_end")
