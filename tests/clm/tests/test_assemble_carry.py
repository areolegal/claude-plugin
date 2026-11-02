"""הסכם שמקורו קיים אך לא חולץ, מקור שהוסר, איחוד, מזהים יציבים וטעינת קובצי חילוץ."""
import datetime as dt
import json

from clm import assemble
from clm.validate import check_data
from helpers import make_extract

TODAY = dt.date(2026, 10, 22)
CP2 = {"name": "צד שני", "company_number": None, "notice_address": None}
KC = [{"clause_code": "change_of_control", "summary": "נדרשת הסכמה", "value": "", "clause": "סעיף 20",
       "quote": "שינוי שליטה מחייב הסכמה",
           "bound_party": "both", "norm": {"requires": "consent"}}]
GU = [{"kind": "ערבות", "title": "ערבות בנקאית", "amount": "93,000 ₪", "expiry": "2027-09-05",
       "clause": "סעיף 9", "quote": "השוכר ימציא ערבות", "direction": "given"}]


def scan_of(*items):
    return {"files": [{"path": p, "sha256": s, "status": st, "abs": None, "duplicate_of": None} for p, s, st in items]}


def sha(c):
    return c * 64


def _rich(s, p, **kw):
    return make_extract(s, p, key_clauses_checked=True, key_clauses=KC, guarantees=GU, **kw)


def _quotes(data, aid):
    fn = {f["n"]: f for f in data["footnotes"]}
    out = []
    for coll in ("events", "commercials", "guarantees", "key_clauses"):
        for row in data[coll]:
            if row["agreementId"] == aid:
                out.append((coll, tuple(fn[n]["quote"] for n in row["refs"])))
                assert all(fn[n]["agreementId"] == aid for n in row["refs"])
    return sorted(out)


def test_changed_but_not_extracted_keeps_number_and_content_across_three_runs():
    p = "x/a - חתום.docx"
    r1 = assemble.assemble(scan_of((p, sha("a"), "new")), {sha("a"): _rich(sha("a"), p)}, "חברה", TODAY)
    a1 = r1["agreements"][0]
    assert a1["number"] == "CLM-2026-0001"
    # הרצה 2: הקובץ השתנה, והגרסה החדשה טרם חולצה
    r2 = assemble.assemble(scan_of((p, sha("b"), "changed")), {sha("a"): _rich(sha("a"), p)}, "חברה", TODAY,
                           previous=r1)
    assert [a["number"] for a in r2["agreements"]] == ["CLM-2026-0001"]
    a2 = r2["agreements"][0]
    assert a2["id"] == a1["id"] and not a2.get("source_removed") and a2["extraction_pending"] is True
    assert len(r2["events"]) == len(r1["events"]) and r2["events"][0]["id"] == r1["events"][0]["id"]
    assert _quotes(r2, a2["id"]) == _quotes(r1, a1["id"])
    assert len(r2["commercials"]) == 1 and len(r2["guarantees"]) == 1 and len(r2["key_clauses"]) == 1
    assert a2["id"] not in r2["registers"]["key_clauses_unchecked"]
    assert r2["registers"]["change_of_control"] == [a2["id"]]
    pend = [r for r in r2["review_queue"] if r["kind"] == "not_extracted"]
    assert len(pend) == 1 and pend[0]["agreementId"] == a2["id"] and "CLM-2026-0001" in pend[0]["text"]
    assert not any(r["kind"] == "source_removed" for r in r2["review_queue"])
    assert check_data(r2)[0] == []
    # הרצה 3: חולץ, והמספר נשמר
    r3 = assemble.assemble(scan_of((p, sha("b"), "changed")), {sha("b"): _rich(sha("b"), p)}, "חברה", TODAY,
                           previous=r2)
    assert [a["number"] for a in r3["agreements"]] == ["CLM-2026-0001"] and r3["meta"]["number_seq"] == 1
    assert "extraction_pending" not in r3["agreements"][0]


def test_invalid_new_extraction_keeps_previous_agreement():
    p = "x/a - חתום.docx"
    r1 = assemble.assemble(scan_of((p, sha("a"), "new")), {sha("a"): _rich(sha("a"), p)}, "חברה", TODAY)
    bad = [{"file": p, "problems": ["doc_kind 'bogus' אינו ברשימה הסגורה"]}]
    r2 = assemble.assemble(scan_of((p, sha("b"), "changed")), {sha("a"): _rich(sha("a"), p)}, "חברה", TODAY,
                           previous=r1, bad_extracts=bad)
    assert [a["number"] for a in r2["agreements"]] == ["CLM-2026-0001"] and len(r2["events"]) == 1
    assert {"not_extracted", "bad_extract"} <= {r["kind"] for r in r2["review_queue"]}
    r3 = assemble.assemble(scan_of((p, sha("b"), "changed")), {sha("b"): _rich(sha("b"), p)}, "חברה", TODAY,
                           previous=r2)
    assert [a["number"] for a in r3["agreements"]] == ["CLM-2026-0001"]


def test_carried_refs_are_renumbered_next_to_fresh_agreements():
    pa, pb = "x/a - חתום.docx", "x/b - חתום.docx"
    exts = {sha("a"): _rich(sha("a"), pa), sha("b"): _rich(sha("b"), pb, title="שני", counterparty=CP2)}
    r1 = assemble.assemble(scan_of((pa, sha("a"), "new"), (pb, sha("b"), "new")), exts, "חברה", TODAY)
    ida = [a for a in r1["agreements"] if a["file"] == pa][0]["id"]
    exts2 = {sha("a"): exts[sha("a")], sha("c"): _rich(sha("c"), pb, title="שני", counterparty=CP2)}
    r2 = assemble.assemble(scan_of((pa, sha("z"), "changed"), (pb, sha("c"), "changed")), exts2, "חברה", TODAY,
                           previous=r1)
    assert sorted(a["number"] for a in r2["agreements"]) == ["CLM-2026-0001", "CLM-2026-0002"]
    assert _quotes(r2, ida) == _quotes(r1, ida)
    assert [f["n"] for f in r2["footnotes"]] == list(range(1, len(r2["footnotes"]) + 1))
    assert check_data(r2)[0] == []


def test_source_removed_keeps_events_key_clauses_guarantees_and_quotes():
    p = "x/a - חתום.docx"
    r1 = assemble.assemble(scan_of((p, sha("a"), "new")), {sha("a"): _rich(sha("a"), p)}, "חברה", TODAY)
    aid = r1["agreements"][0]["id"]
    r2 = assemble.assemble(scan_of((p, sha("a"), "removed")), {}, "חברה", TODAY, previous=r1)
    assert r2["agreements"][0]["source_removed"] is True
    assert _quotes(r2, aid) == _quotes(r1, aid) and len(r2["events"]) == 1
    assert check_data(r2)[0] == []
    r3 = assemble.assemble(scan_of(), {}, "חברה", TODAY, previous=r2)
    assert _quotes(r3, aid) == _quotes(r1, aid)


def test_merged_previous_agreements_get_a_review_item_with_both_numbers():
    ps, pd = "x/הסכם שירותים - חתום.docx", "x/הסכם שירותים - טיוטה.docx"
    other = {"name": "צד אחר", "company_number": None, "notice_address": None}
    exts = {sha("a"): make_extract(sha("a"), ps),
            sha("b"): make_extract(sha("b"), pd, doc_kind="draft", counterparty=other, version_date="2025-01-01")}
    r1 = assemble.assemble(scan_of((ps, sha("a"), "new"), (pd, sha("b"), "new")), exts, "חברה", TODAY)
    assert len(r1["agreements"]) == 2
    exts[sha("c")] = make_extract(sha("c"), pd, doc_kind="draft", version_date="2025-01-01")
    r2 = assemble.assemble(scan_of((ps, sha("a"), "same"), (pd, sha("c"), "changed")), exts, "חברה", TODAY,
                           previous=r1)
    assert len(r2["agreements"]) == 1
    merged = [r for r in r2["review_queue"] if r["kind"] == "merged"]
    assert len(merged) == 1 and "CLM-2026-0001" in merged[0]["text"] and "CLM-2026-0002" in merged[0]["text"]
    assert merged[0]["agreementId"] == r2["agreements"][0]["id"]


def test_colliding_event_ids_get_a_stable_ordinal():
    p = "x/a - חתום.docx"
    ext = make_extract(sha("a"), p)
    e0 = dict(ext["events"][0], event_code="payment_milestone", label="תשלום", clause="סעיף 7",
              consequence="we_breach", recurrence=None, renewal_months=None)
    ext["events"] = [dict(e0, date="2027-06-01"), dict(e0, date="2026-12-01")]
    d = assemble.assemble(scan_of((p, sha("a"), "new")), {sha("a"): ext}, "חברה", TODAY)
    ids = [e["id"] for e in d["events"]]
    assert len(set(ids)) == 2 and check_data(d)[0] == []
    by_date = {e["date"]: e["id"] for e in d["events"]}
    ext2 = make_extract(sha("a"), p)
    ext2["events"] = list(reversed(ext["events"]))
    d2 = assemble.assemble(scan_of((p, sha("a"), "same")), {sha("a"): ext2}, "חברה", TODAY, previous=d)
    assert {e["date"]: e["id"] for e in d2["events"]} == by_date
    single = make_extract(sha("a"), p)
    single["events"] = [ext["events"][1]]
    d3 = assemble.assemble(scan_of((p, sha("a"), "new")), {sha("a"): single}, "חברה", TODAY)
    assert d3["events"][0]["id"] == by_date["2026-12-01"]


def test_review_items_have_stable_unique_ids():
    pa, pb = "x/a - חתום.docx", "x/b - חתום.docx"
    role = {"value": "לקוח", "source": "suggested"}
    exts = {sha("a"): make_extract(sha("a"), pa, our_role=role),
            sha("b"): make_extract(sha("b"), pb, title="שני", counterparty=CP2, our_role=role)}
    scan = scan_of((pa, sha("a"), "new"), (pb, sha("b"), "new"), ("x/c.docx", sha("c"), "new"))
    d = assemble.assemble(scan, exts, "חברה", TODAY)
    ids = [r["id"] for r in d["review_queue"]]
    assert all(i.startswith("rv-") for i in ids) and len(set(ids)) == len(ids)
    only_b = assemble.assemble(scan_of((pb, sha("b"), "new")), {sha("b"): exts[sha("b")]}, "חברה", TODAY)
    aid_b = only_b["agreements"][0]["id"]
    rid = [r["id"] for r in only_b["review_queue"] if r["kind"] == "role"][0]
    d2 = assemble.assemble(scan, exts, "חברה", TODAY, previous=only_b)
    assert rid in {r["id"] for r in d2["review_queue"] if r["kind"] == "role" and r["agreementId"] == aid_b}
    assert check_data(d)[0] == []


def test_load_extracts_flags_sha_mismatch_and_reads_bom(tmp_path):
    good = make_extract(sha("a"), "x/a - חתום.docx")
    (tmp_path / (sha("a") + ".json")).write_text(json.dumps(good, ensure_ascii=False), encoding="utf-8-sig")
    other = make_extract(sha("b"), "x/b - חתום.docx")
    (tmp_path / (sha("c") + ".json")).write_text(json.dumps(other, ensure_ascii=False), encoding="utf-8")
    ok, bad = assemble.load_extracts(str(tmp_path))
    assert list(ok) == [sha("a")]
    assert len(bad) == 1 and bad[0]["file"] == "x/b - חתום.docx" and "sha256" in bad[0]["problems"][0]


def test_idempotent_rerun_is_byte_identical():
    p = "x/a - חתום.docx"
    exts = {sha("a"): _rich(sha("a"), p)}
    r1 = assemble.assemble(scan_of((p, sha("a"), "new")), exts, "חברה", TODAY)
    r2 = assemble.assemble(scan_of((p, sha("a"), "same")), exts, "חברה", TODAY, previous=r1)
    r3 = assemble.assemble(scan_of((p, sha("a"), "same")), exts, "חברה", TODAY, previous=r2)
    dump = lambda d: json.dumps(d, ensure_ascii=False, indent=1)  # noqa: E731
    assert dump(r2) == dump(r3)
    c1 = assemble.assemble(scan_of((p, sha("b"), "changed")), exts, "חברה", TODAY, previous=r1)
    c2 = assemble.assemble(scan_of((p, sha("b"), "changed")), exts, "חברה", TODAY, previous=c1)
    assert dump(c1) == dump(c2)
