import datetime as dt
from clm import assemble
from helpers import make_extract

TODAY = dt.date(2026, 10, 22)


def scan_of(*items):
    return {"files": [{"path": p, "sha256": s, "status": st, "abs": None, "duplicate_of": None} for p, s, st in items]}


def sha(c):
    return c * 64


def test_full_assembly_contract():
    exts = {
        sha("a"): make_extract(sha("a"), "x/הסכם מסגרת שירותים - חתום.docx"),
        sha("b"): make_extract(sha("b"), "x/הסכם שירותים - הערות.docx", doc_kind="negotiation_version",
                               title="הסכם שירותים", version_by="them", version_date="2026-09-01",
                               counterparty={"name": "לקוח אחר בע\"מ", "company_number": None, "notice_address": None},
                               our_role={"value": "", "source": "none"}, events=[], commercials=[]),
        sha("c"): make_extract(sha("c"), "x/תבנית NDA.docx", doc_kind="template", events=[], commercials=[]),
    }
    scan = scan_of(("x/הסכם מסגרת שירותים - חתום.docx", sha("a"), "new"),
                   ("x/הסכם שירותים - הערות.docx", sha("b"), "new"),
                   ("x/תבנית NDA.docx", sha("c"), "new"),
                   ("x/ישן.docx", sha("d"), "removed"),
                   ("x/חדש-לא-חולץ.docx", sha("e"), "new"))
    data = assemble.assemble(scan, exts, "חברה בע\"מ", TODAY)
    assert data["meta"]["schema_version"] == "2.0" and data["meta"]["company"] == "חברה בע\"מ"
    ags = {a["title"]: a for a in data["agreements"]}
    assert set(ags) == {"הסכם בדיקה", "הסכם שירותים"}
    signed, nego = ags["הסכם בדיקה"], ags["הסכם שירותים"]
    assert signed["number"] == "CLM-2026-0001" and signed["agreement_state"] == "renewal_window"
    assert signed["family"] == "שירותים ומיקור חוץ" and signed["value"]["annual_by_currency"] == {"ILS": 384000}
    assert nego["handling_stage"] == "comments" and nego["waiting_on"] == "us" and nego["idle_days"] == 51
    assert nego["our_role"]["confirmed"] is False and nego["legal_owner"] is None
    ev = [e for e in data["events"] if e["agreementId"] == signed["id"]][0]
    assert ev["act_by"] == "2026-10-16" and ev["refs"] == [1] and "quote" not in ev
    assert data["footnotes"][0]["n"] == 1 and data["footnotes"][0]["quote"].startswith("אלא אם")
    assert {d["doc_kind"] for d in data["documents"]} == {"signed", "negotiation_version", "template"}
    kinds = {r["kind"] for r in data["review_queue"]}
    assert {"source_removed", "not_extracted", "role", "verify_critical"} <= kinds
    assert data["registers"]["not_signed"] == [nego["id"]] and data["registers"]["change_of_control"] is None
    assert data["catalog"]["nonrenewal_notice"]["lead_days"] == 45


def test_numbers_and_event_ids_are_stable_across_runs():
    exts = {sha("a"): make_extract(sha("a"), "x/a - חתום.docx")}
    scan = scan_of(("x/a - חתום.docx", sha("a"), "new"))
    first = assemble.assemble(scan, exts, "חברה", TODAY)
    exts[sha("f")] = make_extract(sha("f"), "x/b - חתום.docx", title="הסכם שני",
                                  counterparty={"name": "צד שני", "company_number": None, "notice_address": None})
    scan2 = scan_of(("x/b - חתום.docx", sha("f"), "new"), ("x/a - חתום.docx", sha("a"), "same"))
    second = assemble.assemble(scan2, exts, "חברה", TODAY, previous=first)
    num = {a["title"]: a["number"] for a in second["agreements"]}
    assert num["הסכם בדיקה"] == "CLM-2026-0001" and num["הסכם שני"] == "CLM-2026-0002"
    assert first["events"][0]["id"] in {e["id"] for e in second["events"]}


def test_term_passed_and_guarantee_direction_and_registers():
    ext = make_extract(sha("a"), "x/a - חתום.docx", key_clauses_checked=True,
                       key_clauses=[{"clause_code": "change_of_control", "summary": "נדרשת הסכמה", "value": "",
                                     "clause": "סעיף 20", "quote": "שינוי שליטה מחייב הסכמה",
           "bound_party": "both", "norm": {"requires": "consent"}}],
                       guarantees=[{"kind": "ערבות", "title": "ערבות בנקאית", "amount": "93,000 ₪", "expiry": "2026-09-05",
                                    "clause": "סעיף 9", "quote": "השוכר ימציא ערבות", "direction": "given"}])
    ext["events"] = [dict(ext["events"][0], event_code="term_end", consequence="auto_change", date="2026-08-31",
                          renewal_months=None, quote="ההסכם יעמוד בתוקפו עד 31.8.2026")]
    data = assemble.assemble(scan_of(("x/a - חתום.docx", sha("a"), "new")), {sha("a"): ext}, "חברה", TODAY)
    a = data["agreements"][0]
    assert a["agreement_state"] == "term_passed_unverified"
    assert data["registers"]["term_passed"] == [a["id"]] and data["registers"]["change_of_control"] == [a["id"]]
    assert data["guarantees"][0]["direction"] == "given" and data["guarantees"][0]["refs"]


def test_unknown_type_goes_to_review():
    ext = make_extract(sha("a"), "x/a - חתום.docx", type_code=None, type_label="ניסוי קליני")
    data = assemble.assemble(scan_of(("x/a - חתום.docx", sha("a"), "new")), {sha("a"): ext}, "חברה", TODAY)
    assert data["agreements"][0]["family"] == "ניסוי קליני" and data["agreements"][0]["type_code"] is None
    assert any(r["kind"] == "family" for r in data["review_queue"])


# ---- fix round 1: regression tests ----

CP2 = {"name": "צד שני", "company_number": None, "notice_address": None}


def test_split_keeps_one_number_and_adds_review_item():
    p1, p2 = "x/הסכם שירותים - חתום.docx", "x/הסכם שירותים - נוסח אחר חתום.docx"
    exts = {sha("a"): make_extract(sha("a"), p1),
            sha("b"): make_extract(sha("b"), p2, doc_kind="draft", version_date="2026-01-01")}
    first = assemble.assemble(scan_of((p1, sha("a"), "new"), (p2, sha("b"), "new")), exts, "חברה", TODAY)
    assert len(first["agreements"]) == 1 and first["agreements"][0]["number"] == "CLM-2026-0001"
    exts[sha("c")] = make_extract(sha("c"), p2)
    second = assemble.assemble(scan_of((p1, sha("a"), "same"), (p2, sha("c"), "changed")), exts, "חברה", TODAY,
                               previous=first)
    nums = sorted(a["number"] for a in second["agreements"])
    assert nums == ["CLM-2026-0001", "CLM-2026-0002"]
    kept = [a for a in second["agreements"] if a["number"] == "CLM-2026-0001"][0]
    assert kept["file"] == p1
    new = [a for a in second["agreements"] if a["number"] == "CLM-2026-0002"][0]
    split = [r for r in second["review_queue"] if r["kind"] == "split"]
    assert len(split) == 1 and split[0]["agreementId"] == new["id"] and split[0]["group"] == "קיבוץ לבדיקה"
    assert split[0]["text"] == "ההסכם CLM-2026-0001 פוצל. מספר חדש: CLM-2026-0002"


def test_number_not_reused_after_removal_across_three_runs():
    pa, pb, pc = "x/a - חתום.docx", "x/b - חתום.docx", "x/c - חתום.docx"
    exts = {sha("a"): make_extract(sha("a"), pa),
            sha("b"): make_extract(sha("b"), pb, title="שני", counterparty=CP2),
            sha("c"): make_extract(sha("c"), pc, title="שלישי",
                                   counterparty={"name": "צד שלישי", "company_number": None, "notice_address": None})}
    r1 = assemble.assemble(scan_of((pa, sha("a"), "new"), (pb, sha("b"), "new")), exts, "חברה", TODAY)
    assert r1["meta"]["number_seq"] == 2
    r2 = assemble.assemble(scan_of((pa, sha("a"), "same")), exts, "חברה", TODAY, previous=r1)
    assert [a["number"] for a in r2["agreements"]] == ["CLM-2026-0001"] and r2["meta"]["number_seq"] == 2
    r3 = assemble.assemble(scan_of((pa, sha("a"), "same"), (pc, sha("c"), "new")), exts, "חברה", TODAY, previous=r2)
    assert {a["title"]: a["number"] for a in r3["agreements"]}["שלישי"] == "CLM-2026-0003"
    assert r3["meta"]["number_seq"] == 3


def test_single_file_content_change_keeps_number():
    p = "x/a - חתום.docx"
    first = assemble.assemble(scan_of((p, sha("a"), "new")), {sha("a"): make_extract(sha("a"), p)}, "חברה", TODAY)
    ext2 = {sha("g"): make_extract(sha("g"), p)}
    second = assemble.assemble(scan_of((p, sha("g"), "changed")), ext2, "חברה", TODAY, previous=first)
    assert [a["number"] for a in second["agreements"]] == ["CLM-2026-0001"]
    assert second["agreements"][0]["id"] == first["agreements"][0]["id"]


def test_removed_source_carries_the_agreement():
    p = "x/a - חתום.docx"
    first = assemble.assemble(scan_of((p, sha("a"), "new")), {sha("a"): make_extract(sha("a"), p)}, "חברה", TODAY)
    second = assemble.assemble(scan_of((p, sha("a"), "removed")), {}, "חברה", TODAY, previous=first)
    assert len(second["agreements"]) == 1
    a = second["agreements"][0]
    assert a["source_removed"] is True and a["number"] == "CLM-2026-0001" and a["id"] == first["agreements"][0]["id"]
    assert len(second["events"]) == 1 and second["events"][0]["id"] == first["events"][0]["id"]
    removed = [r for r in second["review_queue"] if r["kind"] == "source_removed"]
    assert len(removed) == 1 and removed[0]["agreementId"] == a["id"]
    assert removed[0]["text"] == "המקור של \"%s\" הוסר מהתיקייה. ההסכם נשמר ומסומן" % a["title"]
    third = assemble.assemble(scan_of(), {}, "חברה", TODAY, previous=second)
    assert third["agreements"][0]["source_removed"] is True and third["meta"]["number_seq"] == 1


def test_duplicate_files_surface_in_review():
    scan = scan_of(("x/a - חתום.docx", sha("a"), "new"))
    scan["files"].append({"path": "x/עותק.docx", "sha256": sha("a"), "status": "duplicate", "abs": None,
                          "duplicate_of": "x/a - חתום.docx"})
    data = assemble.assemble(scan, {sha("a"): make_extract(sha("a"), "x/a - חתום.docx")}, "חברה", TODAY)
    dup = [r for r in data["review_queue"] if r["kind"] == "duplicate"]
    assert len(dup) == 1 and dup[0]["group"] == "כפילות"
    assert dup[0]["text"] == "x/עותק.docx זהה ל-x/a - חתום.docx"


def test_key_clause_registers_read_head_ext_and_list_unchecked():
    pd, ps, po = "x/הסכם ענן - טיוטה.docx", "x/הסכם ענן - חתום.docx", "x/אחר - חתום.docx"
    kc = [{"clause_code": "change_of_control", "summary": "נדרשת הסכמה", "value": "", "clause": "סעיף 20",
           "quote": "שינוי שליטה מחייב הסכמה",
           "bound_party": "both", "norm": {"requires": "consent"}}]
    exts = {sha("d"): make_extract(sha("d"), pd, doc_kind="draft", version_date="2024-01-01", key_clauses_checked=False),
            sha("s"): make_extract(sha("s"), ps, key_clauses_checked=True, key_clauses=kc),
            sha("o"): make_extract(sha("o"), po, title="אחר", counterparty=CP2)}
    scan = scan_of((pd, sha("d"), "new"), (ps, sha("s"), "new"), (po, sha("o"), "new"))
    data = assemble.assemble(scan, exts, "חברה", TODAY)
    ags = {a["title"]: a for a in data["agreements"]}
    cloud = [a for a in data["agreements"] if a["file"] == ps][0]
    assert data["registers"]["change_of_control"] == [cloud["id"]]
    assert data["registers"]["restrictions"] == []
    assert data["registers"]["key_clauses_unchecked"] == [ags["אחר"]["id"]]
    none_checked = assemble.assemble(scan_of((po, sha("o"), "new")), exts, "חברה", TODAY)
    assert none_checked["registers"]["change_of_control"] is None
    assert none_checked["registers"]["key_clauses_unchecked"] == [none_checked["agreements"][0]["id"]]


def test_orphan_unsigned_amendment_is_unknown_not_unsigned_draft():
    p = "x/תיקון להסכם.docx"
    ext = make_extract(sha("a"), p, doc_kind="amendment", title="תיקון",
                       dates={"signed": None, "start": None, "end": None}, events=[], commercials=[])
    data = assemble.assemble(scan_of((p, sha("a"), "new")), {sha("a"): ext}, "חברה", TODAY)
    a = data["agreements"][0]
    assert a["signature"] == "unknown" and a["handling_stage"] == "drafting" and a["agreement_state"] is None
    assert a["id"] not in data["registers"]["not_signed"]
    signed = make_extract(sha("b"), p, doc_kind="amendment", title="תיקון", events=[], commercials=[])
    data2 = assemble.assemble(scan_of((p, sha("b"), "new")), {sha("b"): signed}, "חברה", TODAY)
    b = data2["agreements"][0]
    assert b["signature"] == "signed_unverified" and b["agreement_state"] == "in_force" and b["handling_stage"] is None


def test_child_event_ids_include_child_doc():
    ph, pc = "x/הסכם ענן - חתום.docx", "x/תיקון 1.docx"
    exts = {sha("h"): make_extract(sha("h"), ph),
            sha("k"): make_extract(sha("k"), pc, doc_kind="amendment", title="תיקון 1")}
    data = assemble.assemble(scan_of((ph, sha("h"), "new"), (pc, sha("k"), "new")), exts, "חברה", TODAY)
    assert len(data["agreements"]) == 1
    ids = [e["id"] for e in data["events"]]
    assert len(ids) == 2 and len(set(ids)) == 2
    solo = assemble.assemble(scan_of((ph, sha("h"), "new")), {sha("h"): exts[sha("h")]}, "חברה", TODAY)
    assert solo["events"][0]["id"] in ids


def test_load_extracts_survives_broken_json(tmp_path):
    import json
    good = make_extract(sha("a"), "x/a - חתום.docx")
    (tmp_path / (sha("a") + ".json")).write_text(json.dumps(good, ensure_ascii=False), encoding="utf-8")
    (tmp_path / "trunc.json").write_text('{"file": "x/t.docx", "sha2', encoding="utf-8")
    (tmp_path / "list.json").write_text("[]", encoding="utf-8")
    (tmp_path / "bin.json").write_bytes(b"\xff\xfe\x00bad")
    ok, bad = assemble.load_extracts(str(tmp_path))
    assert list(ok) == [sha("a")]
    files = {b["file"] for b in bad}
    assert files == {"trunc.json", "list.json", "bin.json"}
    assert all(b["problems"] for b in bad)
    assert any("הקובץ פגום ולא נקרא" in b["problems"][0] for b in bad if b["file"] == "trunc.json")
