"""סבב תיקונים 2: הסכם שסווג מחדש מחוץ למאגר, מועדים נגררים מחושבים מחדש, אישור משתמש, חלון חידוש."""
import datetime as dt
import json

import pytest

from clm import assemble, doc_kind
from clm.validate import check_data
from helpers import make_extract

T = dt.date(2026, 10, 22)
P = "x/הסכם שירותים.docx"
OTHER = {"name": "צד אחר", "company_number": None, "notice_address": None}


def scan_of(*items):
    return {"files": [{"path": p, "sha256": s, "status": st, "abs": None, "duplicate_of": d}
                      for p, s, st, d in [(i + (None,))[:4] for i in items]]}


def sha(c):
    return c * 64


def with_event(s, **kw):
    ext = make_extract(s, P)
    ext["events"] = [dict(ext["events"][0], **kw)]
    return ext


# ---- R2 ----

@pytest.mark.parametrize("kind,label", [("template", "תבנית"), ("non_agreement", "מסמך שאינו הסכם")])
def test_reclassified_out_of_register_is_not_carried(kind, label):
    r1 = assemble.assemble(scan_of((P, sha("a"), "new")), {sha("a"): make_extract(sha("a"), P)}, "c", T)
    e = make_extract(sha("a"), P, doc_kind=kind, events=[], commercials=[])
    r2 = assemble.assemble(scan_of((P, sha("a"), "same")), {sha("a"): e}, "c", T, previous=r1)
    assert r2["agreements"] == [] and r2["events"] == [] and r2["meta"]["number_seq"] == 1
    items = [r for r in r2["review_queue"] if r["kind"] == "removed_from_register"]
    assert len(items) == 1 and "CLM-2026-0001" in items[0]["text"] and label in items[0]["text"]
    assert check_data(r2)[0] == []
    r3 = assemble.assemble(scan_of((P, sha("a"), "same")), {sha("a"): e}, "c", T, previous=r2)
    assert r3["agreements"] == [] and r3["meta"]["number_seq"] == 1
    q = "x/חדש - חתום.docx"
    r4 = assemble.assemble(scan_of((P, sha("a"), "same"), (q, sha("q"), "new")),
                           {sha("a"): e, sha("q"): make_extract(sha("q"), q, counterparty=OTHER)}, "c", T, previous=r3)
    assert [a["number"] for a in r4["agreements"]] == ["CLM-2026-0002"]


def test_changed_and_reextracted_as_template_is_not_carried():
    r1 = assemble.assemble(scan_of((P, sha("a"), "new")), {sha("a"): make_extract(sha("a"), P)}, "c", T)
    e = make_extract(sha("b"), P, doc_kind="template", events=[], commercials=[])
    r2 = assemble.assemble(scan_of((P, sha("b"), "changed")), {sha("b"): e}, "c", T, previous=r1)
    assert r2["agreements"] == [] and [r["kind"] for r in r2["review_queue"]].count("removed_from_register") == 1


def test_duplicate_item_names_the_carried_agreement():
    q = "x/עותק.docx"
    r1 = assemble.assemble(scan_of((P, sha("a"), "new")), {sha("a"): make_extract(sha("a"), P)}, "c", T)
    exts = {sha("c"): make_extract(sha("c"), q, title="אחר", counterparty=OTHER)}
    r2 = assemble.assemble(scan_of((q, sha("c"), "new"), (P, sha("c"), "duplicate", q)), exts, "c", T, previous=r1)
    carried = [a for a in r2["agreements"] if a.get("extraction_pending")]
    assert [a["number"] for a in carried] == ["CLM-2026-0001"]
    dup = [r for r in r2["review_queue"] if r["kind"] == "duplicate"]
    assert len(dup) == 1 and "CLM-2026-0001" in dup[0]["text"] and dup[0]["agreementId"] == carried[0]["id"]


# ---- R3 ----

NOTICE = dict(event_code="nonrenewal_notice", label="הודעת אי-חידוש", date="2026-11-30", consequence="right_lapses",
              recurrence=None, renewal_months=None)
LATER = dt.date(2026, 12, 15)


@pytest.mark.parametrize("status", ["changed", "removed"])
def test_carried_deadline_is_rederived_against_today(status):
    q1 = assemble.assemble(scan_of((P, sha("a"), "new")), {sha("a"): with_event(sha("a"), **NOTICE)}, "c", T)
    assert q1["events"][0]["state"] == "upcoming"
    exts = {sha("a"): with_event(sha("a"), **NOTICE)} if status == "changed" else {}
    q2 = assemble.assemble(scan_of((P, sha("b") if status == "changed" else sha("a"), status)), exts, "c", LATER,
                           previous=q1)
    e = q2["events"][0]
    assert e["id"] == q1["events"][0]["id"] and e["state"] == "lapsed_pending" and e["act_by"] is None
    assert e["next_reminder"] is None and e["date"] == "2026-11-30"
    out = [r for r in q2["review_queue"] if r["kind"] == "outcome"]
    assert len(out) == 1 and out[0]["eventId"] == e["id"]
    assert check_data(q2)[0] == []
    again = assemble.assemble(scan_of((P, sha("b") if status == "changed" else sha("a"), status)), exts, "c", LATER,
                              previous=q2)
    assert json.dumps(again, sort_keys=True, ensure_ascii=False) == json.dumps(q2, sort_keys=True, ensure_ascii=False)


def test_carried_rolled_deadline_rolls_again_with_a_new_passed_occurrence():
    ins = dict(event_code="insurance_cert", label="אישור ביטוח", date="2025-10-15", consequence="we_breach",
               recurrence={"months": 12, "max": None}, renewal_months=None, impact="material")
    k1 = assemble.assemble(scan_of((P, sha("a"), "new")), {sha("a"): with_event(sha("a"), **ins)}, "c", T)
    main_id = k1["events"][0]["id"]
    far = dt.date(2027, 11, 1)
    k2 = assemble.assemble(scan_of((P, sha("a"), "removed")), {}, "c", far, previous=k1)
    assert [(e["state"], e["date"], e.get("occurrence")) for e in k2["events"]] == [
        ("upcoming", "2028-10-15", None), ("needs_action", "2027-10-15", "passed")]
    assert k2["events"][0]["id"] == main_id
    assert k2["events"][1]["id"] == "ev-" + assemble._sid(main_id, "occurrence", "2027-10-15")
    assert k2["events"][0]["refs"] == k2["events"][1]["refs"] and k2["events"][0]["refs"]
    assert check_data(k2)[0] == []


# ---- R4 ----

def test_prior_user_confirmation_beats_playbook_and_flags_contradiction():
    u1 = assemble.assemble(scan_of((P, sha("a"), "new")),
                           {sha("a"): make_extract(sha("a"), P, our_role={"value": "ספק", "source": "user"})}, "c", T)
    for source in ("playbook", "suggested"):
        e = make_extract(sha("b"), P, our_role={"value": "לקוח", "source": source})
        u2 = assemble.assemble(scan_of((P, sha("b"), "changed")), {sha("b"): e}, "c", T, previous=u1)
        assert u2["agreements"][0]["our_role"] == {"value": "ספק", "source": "user", "confirmed": True}
        items = [r for r in u2["review_queue"] if r["kind"] == "role_conflict"]
        assert len(items) == 1 and items[0]["group"] == "סתירה לבדיקה" and "לקוח" in items[0]["text"]
    same = make_extract(sha("b"), P, our_role={"value": "ספק", "source": "suggested"})
    u3 = assemble.assemble(scan_of((P, sha("b"), "changed")), {sha("b"): same}, "c", T, previous=u1)
    assert not [r for r in u3["review_queue"] if r["kind"] == "role_conflict"]
    fresh = make_extract(sha("b"), P, our_role={"value": "לקוח", "source": "user"})
    u4 = assemble.assemble(scan_of((P, sha("b"), "changed")), {sha("b"): fresh}, "c", T, previous=u1)
    assert u4["agreements"][0]["our_role"]["value"] == "לקוח"


# ---- R5 and optional ----

def test_renewal_window_reopens_after_an_auto_renewal():
    open_window = with_event(sha("a"), event_code="nonrenewal_notice", date="2025-11-30", renewal_months=12)
    d = assemble.assemble(scan_of((P, sha("a"), "new")), {sha("a"): open_window}, "c", T)
    assert d["agreements"][0]["agreement_state"] == "renewal_window"
    assert any(r["kind"] == "renewal_verify" for r in d["review_queue"])
    closed = with_event(sha("a"), event_code="nonrenewal_notice", date="2025-06-30", renewal_months=12)
    d2 = assemble.assemble(scan_of((P, sha("a"), "new")), {sha("a"): closed}, "c", T)
    assert d2["events"][0]["date"] == "2027-06-30" and d2["agreements"][0]["agreement_state"] == "extended"


def test_passed_occurrence_is_not_also_a_verify_critical_item():
    ev = with_event(sha("a"), event_code="nonrenewal_notice", date="2025-11-30", renewal_months=12,
                    consequence="we_breach")
    d = assemble.assemble(scan_of((P, sha("a"), "new")), {sha("a"): ev}, "c", T)
    passed = d["events"][1]
    assert passed["occurrence"] == "passed" and passed["state"] == "needs_action"
    assert not [r for r in d["review_queue"] if r["kind"] == "verify_critical" and r["eventId"] == passed["id"]]


@pytest.mark.parametrize("name", ["agreement non-signed.docx", "agreement not signed.docx", "NOT SIGNED copy.pdf"])
def test_more_negated_signed_names(name):
    assert doc_kind.suggest(name)[0] != "signed"
