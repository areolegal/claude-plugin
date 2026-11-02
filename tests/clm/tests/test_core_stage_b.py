import datetime as dt

from clm import assemble, core
from helpers import make_extract

T = dt.date(2026, 10, 23)
CO = "מדיקס שירותי בריאות דיגיטליים בע\"מ"


def scan_of(*shas):
    return {"files": [{"path": "f%d.docx" % i, "sha256": s, "status": "new"} for i, s in enumerate(shas)]}


def run(ext, today=T, **kw):
    return assemble.assemble(scan_of(ext["sha256"]), {ext["sha256"]: ext}, CO, today, **kw)


def ag(data):
    return data["agreements"][0]


def test_add_months_clamps_to_month_end():
    assert core.add_months(dt.date(2025, 1, 31), 1) == dt.date(2025, 2, 28)
    assert core.add_months(dt.date(2024, 11, 30), 3) == dt.date(2025, 2, 28)


def test_resolve_party_by_name_and_by_confirmed_role():
    assert core.resolve_party("unknown", "מדיקס שירותי בריאות דיגיטליים", CO, "ספק בע\"מ", False) == ("contracting", True)
    assert core.resolve_party(None, "ספק בע\"מ", CO, "ספק בע\"מ", False) == ("counterparty", True)
    assert core.resolve_party("both", None, CO, "ספק", False) == ("both", True)
    assert core.resolve_party("contracting", "הלקוח", CO, "ספק", False) == ("contracting", False)
    assert core.resolve_party("contracting", "הלקוח", CO, "ספק", True) == ("contracting", True)
    assert core.resolve_party(None, None, CO, "ספק", True) == ("unknown", False)


def test_resolve_party_company_aliases_and_ambiguous_name():
    names = [CO, "Medix Digital Health Ltd."]
    assert core.resolve_party(None, "Medix Digital Health Ltd. (Customer)", names, "Vendor Ltd.", False) == ("contracting", True)
    assert core.resolve_party("contracting", "מדיקס", "מדיקס בע\"מ", "מדיקס אחרים בע\"מ", True) == ("unknown", False)


def test_company_aliases_resolve_english_signatory_in_assemble():
    ext = make_extract("6" * 64, "a.docx",
                       signatories=[{"party": "unknown", "party_name": "Medix Digital Health Ltd. (Customer)", "name": None,
                                     "role": None, "date": None, "status": "blank", "clause": "Signatures",
                                     "quote": "Medix Digital Health Ltd. (Customer)"}])
    assert ag(run(ext))["signatories"][0]["party"] == "unknown"
    s = ag(run(ext, company_aliases=("Medix Digital Health Ltd.",)))["signatories"][0]
    assert (s["party"], s["party_certain"]) == ("contracting", True)


def test_computed_end_from_fixed_term():
    ext = make_extract("c" * 64, "a.docx", dates={"signed": "2025-03-01", "start": "2025-03-01", "end": None},
                       events=[], term={"kind": "fixed", "initial_months": 24, "starts_on": "start", "max_end": None,
                                        "trigger": "", "clause": "סעיף 3", "quote": "24 חודשים"})
    a = ag(run(ext))
    assert a["dates"]["end"] == "2027-02-28"
    assert a["dates"]["end_basis"]["kind"] == "computed" and "24 חודשים" in a["dates"]["end_basis"]["note"]
    assert a["field_status"]["end_date"] == "derived"


def test_auto_renewal_field_rolls_current_end_and_asks_to_verify():
    ext = make_extract("d" * 64, "a.docx", events=[],
                       dates={"signed": "2021-07-01", "start": "2021-07-01", "end": "2022-06-30"},
                       renewal={"kind": "auto", "period_months": 12, "max_count": None, "holder": None,
                                "holder_name": None, "notice_days": 60, "clause": "סעיף 2", "quote": "יתחדש"})
    d = run(ext)
    a = ag(d)
    assert a["dates"]["current_end"] == "2027-06-30"
    assert a["dates"]["current_end_basis"]["kind"] == "auto_renewal"
    assert "5 חידושים של 12 חודשים" in a["dates"]["current_end_basis"]["note"]
    assert any(r["kind"] == "renewal_verify" and r.get("agreementId") == a["id"] for r in d["review_queue"])


def test_max_end_from_renewal_cap_and_option_keeps_end():
    ext = make_extract("e" * 64, "a.docx", events=[],
                       renewal={"kind": "option", "period_months": 12, "max_count": 2, "holder": "contracting",
                                "holder_name": None, "notice_days": 90, "clause": "סעיף 4", "quote": "אופציה"})
    a = ag(run(ext))
    assert a["dates"]["current_end"] == "2027-02-28"
    assert a["dates"]["current_end_basis"]["kind"] == "option_pending"
    assert a["dates"]["max_end"] == "2029-02-28" and a["dates"]["max_end_basis"]["kind"] == "derived"
    assert a["renewal"]["holder"] == "contracting" and a["renewal"]["holder_certain"] is True  # base role is user-confirmed


def test_indefinite_term_end_not_relevant_and_no_missing_core_for_end():
    ext = make_extract("f" * 64, "a.docx", events=[], dates={"signed": "2024-01-01", "start": "2024-01-01", "end": None},
                       term={"kind": "indefinite", "initial_months": None, "starts_on": None, "max_end": None,
                             "trigger": "", "clause": "סעיף 2", "quote": "ללא הגבלת זמן"},
                       signatories=[{"party": "counterparty", "party_name": "ספק בדיקה בע\"מ", "name": "א", "role": "",
                                     "date": None, "status": "signed", "clause": "חתימות", "quote": "א"},
                                    {"party": "contracting", "party_name": CO, "name": "ב", "role": "", "date": None, "status": "signed",
                                     "clause": "חתימות", "quote": "ב"}])
    d = run(ext)
    a = ag(d)
    assert a["field_status"]["end_date"] == "not_relevant"
    assert a["dates"]["current_end"] is None and a["dates"]["current_end_basis"]["kind"] == "indefinite"
    assert not [r for r in d["review_queue"] if r["kind"] == "missing_core"]


def test_missing_core_lists_term_kind_and_signatories():
    d = run(make_extract("1" * 64, "a.docx"))
    item = next(r for r in d["review_queue"] if r["kind"] == "missing_core")
    assert "סוג תקופה" in item["text"] and "חותמים" in item["text"]


def test_deadline_end_ignores_max_end_role():
    ev = {"event_code": "term_end", "label": "סיום התקופה המרבית", "date": "2030-12-31", "relative": False,
          "trigger": "", "clause": "סעיף 3", "quote": "לא יאוחר מ-31.12.2030", "obligor": "both",
          "consequence": "auto_change", "impact": "material", "if_nothing": "", "action": "", "notice_days": None,
          "recurrence": None, "renewal_months": None, "renewal_max": None, "computed": False, "term_role": "max_end"}
    ext = make_extract("2" * 64, "a.docx", events=[ev], dates={"signed": "2025-01-01", "start": "2025-01-01", "end": None})
    a = ag(run(ext))
    assert a["dates"]["end"] is None
    assert a["dates"]["max_end"] == "2030-12-31" and a["dates"]["max_end_basis"]["kind"] == "deadline"


def test_survival_end_and_new_fields_with_refs():
    ev = {"event_code": "post_term", "label": "תום חובת סודיות", "date": "2032-02-28", "relative": False, "trigger": "",
          "clause": "סעיף 9", "quote": "5 שנים לאחר תום ההסכם", "obligor": "both", "consequence": "we_breach",
          "impact": "material", "if_nothing": "", "action": "", "notice_days": None, "recurrence": None,
          "renewal_months": None, "renewal_max": None, "computed": True}
    ext = make_extract("3" * 64, "a.docx", events=[ev],
                       jurisdiction={"court": "תל אביב", "exclusive": True, "clause": "סעיף 20", "quote": "ייחודית"},
                       payment_terms={"days": 30, "basis": "invoice", "text": "30 יום מחשבונית", "clause": "7",
                                      "quote": "30 יום ממועד החשבונית"},
                       exit={"who": "both", "who_name": None, "notice_days": 60, "min_commitment_months": None,
                             "clause": "14", "quote": "בהודעה של 60 יום"})
    d = run(ext)
    a = ag(d)
    assert a["dates"]["survival_end"] == "2032-02-28" and a["dates"]["survival_end_label"] == "תום חובת סודיות"
    assert a["jurisdiction"]["court"] == "תל אביב" and a["jurisdiction"]["refs"]
    assert a["payment_terms"]["days"] == 30 and a["exit"]["who"] == "both" and a["exit"]["who_certain"] is True
    assert a["term"] is None and a["renewal"] is None and a["signatories"] == [] and a["facts"] == []


def test_signatory_party_resolved_by_name_and_facts_open_abandoned_item():
    ext = make_extract("4" * 64, "a.docx", doc_kind="draft", our_role={"value": None, "source": "none"},
                       signatories=[{"party": "unknown", "party_name": CO, "name": None, "role": None, "date": None,
                                     "status": "blank", "clause": "חתימות", "quote": "____"}],
                       facts=[{"code": "negotiation_stopped", "label": "המשא ומתן הופסק", "value": "הערה מ-3.2026",
                               "clause": "הערה", "quote": "המשא ומתן הופסק"}])
    d = run(ext)
    a = ag(d)
    assert a["signatories"][0]["party"] == "contracting" and a["signatories"][0]["party_certain"] is True
    assert a["handling_stage"] != "abandoned"
    assert any(r["kind"] == "abandoned_evidence" for r in d["review_queue"])
    assert a["facts"][0]["file"] == "f0.docx" and a["facts"][0]["refs"]


def test_legacy_extract_without_new_fields_keeps_stage_a_output():
    a = ag(run(make_extract("5" * 64, "a.docx")))
    assert a["dates"]["end"] == "2027-02-28" and a["dates"]["max_end"] is None and a["dates"]["survival_end"] is None
    assert a["dates"]["current_end_basis"]["kind"] == "same_as_end"
    assert a["term"] is None and a["renewal"] is None and a["exit"] is None
    assert a["jurisdiction"] is None and a["payment_terms"] is None


def test_carried_agreement_gets_every_new_key_and_rolls_again():
    ext = make_extract("d" * 64, "a.docx", events=[],
                       dates={"signed": "2021-07-01", "start": "2021-07-01", "end": "2022-06-30"},
                       renewal={"kind": "auto", "period_months": 12, "max_count": None, "holder": None,
                                "holder_name": None, "notice_days": 60, "clause": "סעיף 2", "quote": "יתחדש"})
    first = run(ext)
    old = ag(first)
    for k in ("term", "renewal", "exit", "jurisdiction", "payment_terms", "signatories", "facts"):
        old.pop(k)
    for k in ("max_end", "max_end_basis", "survival_end", "survival_end_label"):
        old["dates"].pop(k)
    gone = {"files": [{"path": "f0.docx", "sha256": None, "status": "removed"}]}
    carried = assemble.assemble(gone, {}, CO, T, previous=first)
    c = ag(carried)
    assert c["term"] is None and c["signatories"] == [] and c["facts"] == [] and c["dates"]["max_end"] is None
    assert c["renewal"] is None and c["dates"]["current_end"] == "2022-06-30"
    assert c["dates"]["survival_end_label"] is None


def test_cli_reads_english_name_from_client_profile(tmp_path):
    import json
    import clm_cli
    assert clm_cli._company_aliases(str(tmp_path)) == ()
    prof = tmp_path / "פרופיל-לקוח.json"
    prof.write_text(json.dumps({"organization_name_en": " Medix Digital Health Ltd. "}), encoding="utf-8")
    assert clm_cli._company_aliases(str(tmp_path)) == ("Medix Digital Health Ltd.",)
    prof.write_text(json.dumps({"organization_name_en": ""}), encoding="utf-8")
    assert clm_cli._company_aliases(str(tmp_path)) == ()
    prof.write_text("{not json", encoding="utf-8")
    assert clm_cli._company_aliases(str(tmp_path)) == ()


# ---------- סבב תיקון 1 ----------
def _sig(party, name, status="signed"):
    return {"party": party, "party_name": name, "name": "א", "role": "", "date": None, "status": status,
            "clause": "חתימות", "quote": "א"}


def test_party_name_matches_whole_words_after_stripping_legal_forms():
    names = [CO, "Medix Digital Health Ltd."]
    for generic in ("Ltd.", "דיגיטל", "בע\"מ", "בע״מ", "Inc.", "(הלקוח)"):
        assert core.resolve_party(None, generic, names, "ספק אחר בע\"מ", False) == ("unknown", False), generic
    assert core.resolve_party(None, "Medix Digital Health Ltd. (Customer)", names, "Vendor Ltd.", False) == ("contracting", True)
    assert core.resolve_party(None, "אורבוס מערכות בע״מ (הספק)", CO, "אורבוס מערכות בע״מ", False) == ("counterparty", True)
    assert core.resolve_party(None, "מדיקס שירותי בריאות דיגיטליים", CO, "אורבוס מערכות בע״מ", False) == ("contracting", True)
    assert core.resolve_party(None, "שירותי בריאות", CO, "אחר", False) == ("contracting", True)


def test_carried_gets_field_status_and_abandoned_evidence():
    ext = make_extract("7" * 64, "a.docx", doc_kind="draft", our_role={"value": None, "source": "none"},
                       facts=[{"code": "negotiation_stopped", "label": "הופסק", "value": "מ-3.2026", "clause": "ה",
                               "quote": "הופסק"}])
    first = run(ext)
    old = ag(first)
    old["field_status"].pop("term_kind")
    old["field_status"].pop("signatories")
    gone = {"files": [{"path": "f0.docx", "sha256": None, "status": "removed"}]}
    c = ag(assemble.assemble(gone, {}, CO, T, previous=first))
    assert c["field_status"]["term_kind"] == "missing" and c["field_status"]["signatories"] == "missing"
    carried = assemble.assemble(gone, {}, CO, T, previous=first)
    assert any(r["kind"] == "abandoned_evidence" and r["agreementId"] == c["id"] for r in carried["review_queue"])


def test_roll_at_max_count_in_the_past_and_empty_clause_notes():
    r = {"kind": "auto", "period_months": 12, "max_count": 2, "clause": ""}
    iso, n, note = core.roll("2020-06-30", r, T)
    assert iso == "2022-06-30" and n == 2
    assert "הגיע למספר החידושים המרבי (2)" in note and "לאמת את מצב ההסכם" in note and "לאמת שההסכם התחדש" not in note
    assert "לפי" not in note and not note.endswith(" ")
    _, _, ok = core.roll("2025-06-30", dict(r, max_count=None, clause="סעיף 2"), T)
    assert "לפי סעיף 2; לאמת שההסכם התחדש" in ok
    _, note2 = core.computed_end({"kind": "fixed", "initial_months": 12, "clause": ""}, "2025-01-01")
    assert note2 == "מחושב: תחילה 1.1.2025 ועוד 12 חודשים, פחות יום"


def test_indefinite_keeps_stage_a_current_end_when_end_exists():
    ext = make_extract("8" * 64, "a.docx", events=[],
                       term={"kind": "indefinite", "initial_months": None, "starts_on": None, "max_end": None,
                             "trigger": "", "clause": "2", "quote": "ללא הגבלת זמן"})
    a = ag(run(ext))
    assert a["dates"]["current_end"] == "2027-02-28" and a["dates"]["current_end_basis"]["kind"] == "same_as_end"


def test_term_passed_from_dates_main_and_carry():
    ext = make_extract("9" * 64, "a.docx", events=[], dates={"signed": "2023-01-01", "start": "2023-01-01",
                                                              "end": "2023-12-31"})
    first = run(ext)
    assert ag(first)["agreement_state"] == "term_passed_unverified"
    ok = make_extract("a" * 64, "a.docx", events=[])
    assert ag(run(ok))["agreement_state"] == "in_force"
    ag(first)["agreement_state"] = "in_force"
    gone = {"files": [{"path": "f0.docx", "sha256": None, "status": "removed"}]}
    assert ag(assemble.assemble(gone, {}, CO, T, previous=first))["agreement_state"] == "term_passed_unverified"
    rolled = make_extract("b" * 64, "a.docx", events=[], dates={"signed": "2021-07-01", "start": "2021-07-01",
                                                                 "end": "2022-06-30"},
                          renewal={"kind": "auto", "period_months": 12, "max_count": None, "holder": None,
                                   "holder_name": None, "notice_days": 60, "clause": "2", "quote": "יתחדש"})
    assert ag(run(rolled))["agreement_state"] == "in_force"


def test_missing_core_lists_missing_signatory_side():
    def text(sigs):
        d = run(make_extract("e" * 64, "a.docx", events=[], signatories=sigs))
        return next(r for r in d["review_queue"] if r["kind"] == "missing_core")["text"]
    only_cp = text([_sig("counterparty", "ספק בדיקה בע\"מ")])
    assert "חותמים לחברה" in only_cp and "חותמים לצד שכנגד" not in only_cp
    only_co = text([_sig("contracting", CO)])
    assert "חותמים לצד שכנגד" in only_co and "חותמים לחברה" not in only_co
    unknown = text([_sig("unknown", None)])
    assert "חותמים לחברה" in unknown and "חותמים לצד שכנגד" in unknown
    empty = text([])
    assert "חותמים" in empty and "חותמים לחברה" not in empty and "חותמים לצד שכנגד" not in empty
