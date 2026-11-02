import datetime as dt

from clm import assemble, core
from clm.validate import check_data
from helpers import make_extract

T = dt.date(2026, 10, 23)
CO = "מדיקס שירותי בריאות דיגיטליים בע\"מ"


def kc(code, **kw):
    row = {"clause_code": code, "summary": "s", "value": "", "clause": "סעיף 3", "quote": "ציטוט"}
    row.update(kw)
    return row


def run(*exts):
    scan = {"files": [{"path": "f%d.docx" % i, "sha256": e["sha256"], "status": "new"} for i, e in enumerate(exts)]}
    return assemble.assemble(scan, {e["sha256"]: e for e in exts}, CO, T)


def ext(sha, clauses, role_source="user", cp="ספק בע\"מ"):
    return make_extract(sha * 64, sha + ".docx", key_clauses=clauses, key_clauses_checked=True,
                        counterparty={"name": cp, "company_number": None, "notice_address": None},
                        our_role={"value": "לקוח" if role_source != "none" else None, "source": role_source})


def ids(d, key):
    by = {a["id"]: a["counterparty"] for a in d["agreements"]}
    return sorted(by[x] for x in d["registers"][key])


def test_restriction_on_company_counted_by_name_even_without_confirmed_role():
    d = run(ext("a", [kc("non_compete", bound_party="unknown", bound_party_name="מדיקס שירותי בריאות דיגיטליים",
                         norm={"months": 120, "until": "2032-08-20", "territory": "ישראל"})], role_source="none", cp="אורבוס"),
            ext("b", [kc("exclusivity", bound_party="counterparty", bound_party_name="ספק ב")], cp="ספק ב"),
            ext("c", [kc("mfn", bound_party="contracting", bound_party_name="הלקוח")], role_source="none", cp="ספק ג"),
            ext("e", [kc("non_compete", bound_party="contracting", bound_party_name=CO,
                         norm={"until": "2025-01-01"})], cp="ספק ה"))
    assert ids(d, "restrictions") == ["אורבוס"]
    assert ids(d, "restrictions_review") == ["ספק ג"]
    orbus = next(a["id"] for a in d["agreements"] if a["counterparty"] == "אורבוס")
    det = d["registers"]["restriction_details"][orbus][0]
    assert det["active_until"] == "2032-08-20" and det["active"] is True and det["bound_party"] == "contracting"
    assert det["label"] and det["refs"] and det["summary"] == "s"
    assert check_data(d)[0] == []


def test_legacy_rows_without_party_go_to_review():
    d = run(ext("a", [kc("exclusivity")]))
    assert d["registers"]["restrictions"] == [] and len(d["registers"]["restrictions_review"]) == 1
    row = d["key_clauses"][0]
    assert row["bound_party"] == "unknown" and row["bound_party_certain"] is False
    assert row["stance"] == "set" and row["norm"] is None and row["active_until"] is None and row["active"] is True


def test_change_of_control_only_when_company_bound_and_consent_or_notice():
    d = run(ext("a", [kc("change_of_control", bound_party="counterparty", bound_party_name="ספק א",
                         norm={"requires": "consent"})], cp="ספק א"),
            ext("b", [kc("change_of_control", bound_party="both", norm={"requires": "notice"})], cp="ספק ב"),
            ext("c", [kc("assignment", bound_party="contracting", bound_party_name=CO,
                         norm={"consent_required": True})], cp="ספק ג"),
            ext("e", [kc("change_of_control", bound_party="both", norm={"requires": "termination_right"})], cp="ספק ה"),
            ext("f", [kc("change_of_control", bound_party="both")], cp="ספק ו"))
    assert ids(d, "change_of_control") == ["ספק ב", "ספק ג"]
    assert ids(d, "change_of_control_review") == ["ספק ו"]


def test_expressly_none_is_not_a_restriction():
    d = run(ext("a", [kc("exclusivity", stance="expressly_none", bound_party="both")]))
    assert d["registers"]["restrictions"] == [] and d["registers"]["restrictions_review"] == []


def test_registers_none_when_nothing_checked():
    e = make_extract("z" * 64, "z.docx", key_clauses=[kc("exclusivity", bound_party="both")])
    d = run(e)
    assert d["registers"]["restrictions"] is None and d["registers"]["restrictions_review"] is None
    assert d["registers"]["restriction_details"] is None and d["registers"]["change_of_control_review"] is None


def test_counted_agreement_never_also_in_review_and_details_sorted():
    d = run(ext("a", [kc("mfn", bound_party="unknown", summary="u"),
                      kc("exclusivity", bound_party="both", summary="x", norm={"until": "2030-01-01"}),
                      kc("non_compete", bound_party="both", summary="y", norm={"until": "2028-01-01"}),
                      kc("exclusivity", bound_party="both", summary="z", norm={"until": "2020-01-01"})]))
    r = d["registers"]
    assert len(r["restrictions"]) == 1 and r["restrictions_review"] == []
    det = r["restriction_details"][r["restrictions"][0]]
    assert [x["summary"] for x in det] == ["y", "x", "z", "u"]
    assert [x["active"] for x in det] == [True, True, False, True]


def test_validate_rejects_non_list_register():
    d = run(ext("a", [kc("exclusivity", bound_party="both")]))
    d["registers"]["restrictions"] = {"x": 1}
    assert any("restrictions" in e for e in check_data(d)[0])


def test_mutual_clause_is_both_whatever_the_name_says():
    both_names = "Medix Digital Health Ltd. and Brightwater Analytics, Inc."
    co = ["Medix Digital Health Ltd."]
    assert core.resolve_party("both", both_names, co, "Brightwater Analytics, Inc.", False) == ("both", True)
    assert core.resolve_party("both", "מדיקס שירותי בריאות דיגיטליים (החברה)", [CO], "ספק", False) == ("both", True)
    d = run(ext("a", [kc("non_compete", bound_party="both", bound_party_name="מדיקס שירותי בריאות דיגיטליים (החברה)")],
                role_source="none"))
    assert d["key_clauses"][0]["bound_party"] == "both" and d["key_clauses"][0]["bound_party_certain"] is True
    assert len(d["registers"]["restrictions"]) == 1 and d["registers"]["restrictions_review"] == []


def test_company_only_rows_come_before_both_then_dated_active_first():
    d = run(ext("a", [kc("exclusivity", bound_party="both", summary="b1", norm={"until": "2027-01-01"})], cp="א"),
            ext("b", [kc("exclusivity", bound_party="contracting", bound_party_name=CO, summary="c-open")], cp="ב"),
            ext("c", [kc("exclusivity", bound_party="contracting", bound_party_name=CO, summary="c-2030",
                         norm={"until": "2030-01-01"})], cp="ג"),
            ext("e", [kc("exclusivity", bound_party="contracting", bound_party_name=CO, summary="c-2028",
                         norm={"until": "2028-01-01"})], cp="ה"))
    by = {a["id"]: a["counterparty"] for a in d["agreements"]}
    assert [by[x] for x in d["registers"]["restrictions"]] == ["ה", "ג", "ב", "א"]
    d2 = run(ext("f", [kc("exclusivity", bound_party="both", summary="both", norm={"until": "2027-01-01"}),
                       kc("non_compete", bound_party="contracting", bound_party_name=CO, summary="open"),
                       kc("mfn", bound_party="contracting", bound_party_name=CO, summary="dated",
                          norm={"until": "2031-01-01"})]))
    det = next(iter(d2["registers"]["restriction_details"].values()))
    assert [x["summary"] for x in det] == ["dated", "open", "both"]


def test_unrecognized_requirement_values_go_to_review_not_excluded():
    d = run(ext("a", [kc("assignment", bound_party="both", norm={"consent_required": "yes"})], cp="א"),
            ext("b", [kc("change_of_control", bound_party="both", norm={"requires": "weird"})], cp="ב"),
            ext("c", [kc("assignment", bound_party="both", norm={"consent_required": False})], cp="ג"),
            ext("e", [kc("change_of_control", bound_party="both", norm={"requires": "none"})], cp="ה"),
            ext("f", [kc("change_of_control", bound_party="contracting", bound_party_name=CO, norm=None)], cp="ו"))
    assert ids(d, "change_of_control") == []
    assert ids(d, "change_of_control_review") == ["א", "ב", "ו"]


def test_registers_survive_non_string_until_and_order_by_today():
    rows = [{"agreementId": "x", "clause_code": "exclusivity", "bound_party": "both", "bound_party_certain": True,
             "norm": {"until": 2030}, "summary": "a", "refs": []},
            {"agreementId": "x", "clause_code": "mfn", "bound_party": "both", "bound_party_certain": True,
             "active_until": "2020-01-01", "active": True, "summary": "b", "refs": []}]
    out = core.registers([], rows, {"x"}, T)
    assert out["restrictions"] == ["x"]
    assert [r["summary"] for r in out["restriction_details"]["x"]] == ["a", "b"]
    assert [r["active"] for r in out["restriction_details"]["x"]] == [True, False]


def test_raw_bound_party_is_kept_next_to_resolved():
    d = run(ext("a", [kc("non_compete", bound_party="unknown", bound_party_name=CO)]))
    row = d["key_clauses"][0]
    assert row["bound_party"] == "contracting" and row["bound_party_raw"] == "unknown"
    d = run(ext("b", [kc("non_compete")]))
    assert d["key_clauses"][0]["bound_party_raw"] is None


def _legacy(row):
    for k in ("bound_party", "bound_party_certain", "bound_party_raw", "bound_party_name", "stance", "norm",
              "active_until", "active"):
        row.pop(k, None)
    return row


def test_carried_legacy_key_clause_row_goes_to_review():
    e = ext("a", [kc("exclusivity", bound_party="both")])
    first = run(e)
    assert len(first["registers"]["restrictions"]) == 1
    for r in first["key_clauses"]:
        _legacy(r)
    scan = {"files": [{"path": "f0.docx", "sha256": "b" * 64, "status": "changed"}]}
    second = assemble.assemble(scan, {e["sha256"]: e}, CO, T, previous=first)
    aid = second["agreements"][0]["id"]
    assert second["agreements"][0]["extraction_pending"] is True
    assert second["registers"]["restrictions"] == [] and second["registers"]["restrictions_review"] == [aid]
    assert check_data(second)[0] == []


def test_carried_row_expires_when_today_rolls_over():
    e = ext("a", [kc("exclusivity", bound_party="both", norm={"until": "2026-12-01"})])
    first = run(e)
    assert len(first["registers"]["restrictions"]) == 1
    scan = {"files": [{"path": "f0.docx", "sha256": "b" * 64, "status": "changed"}]}
    later = assemble.assemble(scan, {e["sha256"]: e}, CO, dt.date(2027, 1, 5), previous=first)
    assert later["registers"]["restrictions"] == [] and later["registers"]["restrictions_review"] == []


def test_restriction_details_carry_bound_party_certainty():
    d = run(ext("a", [kc("non_compete", bound_party="contracting", bound_party_name=CO, norm={"until": "2032-08-20"}),
                      kc("exclusivity", bound_party="contracting", bound_party_name="הלקוח")], role_source="none", cp="א"),
            ext("b", [kc("mfn", bound_party="unknown")], role_source="none", cp="ב"))
    by = {a["counterparty"]: a["id"] for a in d["agreements"]}
    det_a = {x["code"]: x for x in d["registers"]["restriction_details"][by["א"]]}
    assert det_a["non_compete"]["bound_party_certain"] is True
    assert det_a["exclusivity"]["bound_party_certain"] is False
    assert d["registers"]["restriction_details"][by["ב"]][0]["bound_party_certain"] is False
