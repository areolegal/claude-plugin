"""החלטת אנוש, פריט 4: מועד חוזר מגולגל והמופע האחרון שחלף נשאר פתוח; חידוש אוטומטי שחלף."""
import datetime as dt
import json

from clm import assemble
from clm.validate import check_data
from helpers import make_extract

TODAY = dt.date(2026, 10, 22)
P = "x/a - חתום.docx"
S = "a" * 64


def scan(status="new"):
    return {"files": [{"path": P, "sha256": S, "status": status, "abs": None, "duplicate_of": None}]}


def with_event(**kw):
    ext = make_extract(S, P)
    ext["events"] = [dict(ext["events"][0], **kw)]
    return ext


INSURANCE = dict(event_code="insurance_cert", label="חידוש אישור ביטוח", date="2025-10-15", consequence="we_breach",
                 recurrence={"months": 12, "max": None}, renewal_months=None, notice_days=None, impact="material",
                 quote="הספק ימציא אישור ביטוח מדי שנה")


def test_rolled_insurance_certificate_keeps_its_passed_occurrence_open():
    d = assemble.assemble(scan(), {S: with_event(**INSURANCE)}, "חברה", TODAY)
    assert len(d["events"]) == 2
    main, passed = d["events"]
    assert main["date"] == "2027-10-15" and main["state"] == "upcoming"
    assert passed["date"] == "2026-10-15" and passed["state"] == "needs_action" and passed["occurrence"] == "passed"
    assert passed["id"] != main["id"] and passed["refs"] == main["refs"] == [1]
    assert check_data(d)[0] == []
    again = assemble.assemble(scan("same"), {S: with_event(**INSURANCE)}, "חברה", TODAY, previous=d)
    assert [e["id"] for e in again["events"]] == [e["id"] for e in d["events"]]
    assert json.dumps(again, sort_keys=True) == json.dumps(d, sort_keys=True)


def test_passed_occurrence_of_a_right_gets_an_outcome_item():
    d = assemble.assemble(scan(), {S: with_event(**dict(INSURANCE, consequence="right_lapses"))}, "חברה", TODAY)
    passed = d["events"][1]
    out = [r for r in d["review_queue"] if r["kind"] == "outcome"]
    assert passed["state"] == "lapsed_pending" and len(out) == 1 and out[0]["eventId"] == passed["id"]


def test_auto_renewal_that_passed_shows_extended_and_asks_to_verify():
    ev = dict(event_code="term_end", label="תום תקופת ההסכם", date="2026-08-31", consequence="auto_change",
              recurrence=None, renewal_months=12, quote="ההסכם יתחדש מאליו לתקופות של 12 חודשים")
    d = assemble.assemble(scan(), {S: with_event(**ev)}, "חברה", TODAY)
    a = d["agreements"][0]
    assert a["agreement_state"] == "extended"
    main, passed = d["events"]
    assert main["date"] == "2027-08-31" and passed["date"] == "2026-08-31" and passed["state"] == "lapsed_pending"
    items = [r for r in d["review_queue"] if r["kind"] == "renewal_verify"]
    assert len(items) == 1 and items[0]["eventId"] == passed["id"] and items[0]["agreementId"] == a["id"]
    assert "לאמת שההסכם התחדש" in items[0]["text"] and items[0]["group"] == "תוצאת מועד שחלף"
    assert not [r for r in d["review_queue"] if r["kind"] == "outcome"]
    assert check_data(d)[0] == []


def test_renewed_notice_inside_the_window_shows_renewal_window():
    # סבב 2, R5: חלון החידוש הבא גובר על "בהארכה" כשהוא פתוח
    ev = dict(event_code="nonrenewal_notice", date="2025-11-30", renewal_months=12)
    d = assemble.assemble(scan(), {S: with_event(**ev)}, "חברה", TODAY)
    assert d["agreements"][0]["agreement_state"] == "renewal_window"
    assert d["events"][0]["date"] == "2026-11-30" and d["events"][0]["state"] == "upcoming"
    assert d["events"][1]["renewal_check"] is True
