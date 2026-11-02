"""תיקון חתום משנה את התקופה: תאריך הסיום והמצב נגזרים ממנו, ומועדי הנוסח הקודם נשארים פתוחים עם הערה."""
import copy
import datetime as dt

from clm import assemble
from helpers import BASE_EXTRACT, make_extract

TODAY = dt.date(2026, 10, 22)
HEAD, AM1, AM2 = "x/הסכם ענן - חתום.docx", "x/תיקון 1.docx", "x/תיקון 2.docx"


def sha(c):
    return c * 64


def scan_of(*items):
    return {"files": [{"path": p, "sha256": s, "status": "new", "abs": None, "duplicate_of": None} for p, s in items]}


def term_end(date, label="תום תקופת ההסכם"):
    e = copy.deepcopy(BASE_EXTRACT["events"][0])
    e.update(event_code="term_end", label=label, date=date, clause="סעיף 2", consequence="auto_change",
             renewal_months=None, quote="ההסכם בתוקף עד ליום %s." % date)
    return e


def head_ext(end="2025-04-30", extra=()):
    return make_extract(sha("h"), HEAD, dates={"signed": "2022-04-10", "start": "2022-05-01", "end": end},
                        events=[term_end(end)] + list(extra))


def amendment(c, path, signed, end, **kw):
    return make_extract(sha(c), path, doc_kind="amendment", title="תיקון " + c,
                        dates={"signed": signed, "start": "2025-05-01" if end else None, "end": end},
                        events=[term_end(end, "תום התקופה לפי התיקון")] if end else [], commercials=[], **kw)


def run(*amendments, head=None, today=TODAY):
    exts = {sha("h"): head or head_ext()}
    items = [(HEAD, sha("h"))]
    for ext in amendments:
        exts[ext["sha256"]] = ext
        items.append((ext["file"], ext["sha256"]))
    data = assemble.assemble(scan_of(*items), exts, "חברה", today)
    assert len(data["agreements"]) == 1
    return data, data["agreements"][0]


def head_event(data, date="2025-04-30"):
    return [e for e in data["events"] if e["date"] == date and e["event_code"] == "term_end"][0]


def test_signed_amendment_extends_end_and_state_but_leaves_old_term_end_open():
    data, a = run(amendment("k", AM1, "2025-03-23", "2027-04-30"))
    assert a["dates"]["end"] == "2027-04-30" and a["dates"]["original_end"] == "2025-04-30"
    assert a["dates"]["end_source"] == "doc-" + sha("k")[:10]
    assert a["agreement_state"] == "in_force"
    old = head_event(data)
    assert old["state"] in ("needs_action", "lapsed_pending") and old["superseded_by"] == a["dates"]["end_source"]
    assert "תיקון להסכם מיום 23.3.2025 מאריך את התקופה עד 30.4.2027; לאשר את התוצאה" == old["state_note"]
    assert old["state_note"] == old["superseded_note"] and "תיקון להסכם" not in old["action"]
    new = [e for e in data["events"] if e["date"] == "2027-04-30"][0]
    assert new["state"] == "upcoming"
    assert "תוספת" not in old["state_note"]


def test_amendment_extended_agreement_with_future_start_is_signed_not_effective():
    head = head_ext()
    head["dates"]["start"] = "2027-01-01"
    data, a = run(amendment("k", AM1, "2025-03-23", "2027-04-30"), head=head)
    assert a["agreement_state"] == "signed_not_effective"


def test_unsigned_amendment_changes_nothing():
    data, a = run(amendment("k", AM1, None, "2027-04-30"))
    assert a["dates"]["end"] == "2025-04-30" and "end_source" not in a["dates"] and "original_end" not in a["dates"]
    assert a["agreement_state"] == "term_passed_unverified"
    assert "superseded_by" not in head_event(data)


def test_amendment_named_draft_changes_nothing_and_asks_for_confirmation():
    ext = amendment("k", "x/תיקון 1 - טיוטה.docx", "2025-03-23", "2027-04-30")
    data, a = run(ext)
    assert a["dates"]["end"] == "2025-04-30" and a["agreement_state"] == "term_passed_unverified"
    items = [r for r in data["review_queue"] if r["kind"] == "amendment_unconfirmed"]
    assert len(items) == 1 and "תיקון להסכם משנה את תאריך הסיום; לאשר שנחתם" in items[0]["text"]
    assert items[0]["agreementId"] == a["id"]


def test_later_signed_amendment_wins_regardless_of_input_order():
    first = amendment("k", AM1, "2025-03-23", "2027-04-30")
    second = amendment("m", AM2, "2026-02-01", "2029-04-30")
    for order in ((first, second), (second, first)):
        data, a = run(*order)
        assert a["dates"]["end"] == "2029-04-30" and a["dates"]["end_source"] == "doc-" + sha("m")[:10]
        assert a["dates"]["original_end"] == "2025-04-30"
        assert "עד 30.4.2029" in head_event(data)["state_note"]
        assert "תיקון להסכם מיום 1.2.2026" in head_event(data)["state_note"]


def test_upcoming_head_term_is_superseded_and_stops_driving_state_and_alerts():
    data, a = run(amendment("k", AM1, "2025-03-23", "2029-04-30"), head=head_ext("2027-01-31"))
    assert a["agreement_state"] == "in_force"
    old = head_event(data, "2027-01-31")
    assert old["state"] == "upcoming" and old["superseded_by"] == a["dates"]["end_source"]
    assert old["act_by"] is None and old["next_reminder"] is None
    assert "מאריך את התקופה עד 30.4.2029" in old["state_note"]
    assert not [r for r in data["review_queue"] if r.get("eventId") == old["id"]]


def test_shortening_amendment_says_shortens_and_supersedes_later_head_events():
    data, a = run(amendment("k", AM1, "2025-03-23", "2025-12-31"), head=head_ext("2026-12-31"))
    old = head_event(data, "2026-12-31")
    assert "מקצר את התקופה עד 31.12.2025" in old["state_note"] and old["superseded_by"]
    assert a["agreement_state"] == "term_passed_unverified"
    assert "superseded_by" not in head_event(data, "2025-12-31")


def test_outcome_review_item_of_superseded_event_carries_the_note():
    lapsed = term_end("2025-03-01", "הודעת אי-חידוש")
    lapsed.update(event_code="nonrenewal_notice", consequence="right_lapses")
    data, a = run(amendment("k", AM1, "2025-03-23", "2027-04-30"), head=head_ext(extra=[lapsed]))
    ev = [e for e in data["events"] if e["event_code"] == "nonrenewal_notice"][0]
    assert ev["state"] == "lapsed_pending" and ev["superseded_by"]
    item = [r for r in data["review_queue"] if r["kind"] == "outcome" and r["eventId"] == ev["id"]][0]
    assert ev["superseded_note"] in item["text"]


def test_extension_survives_carry_of_agreement_with_pending_extraction():
    first, a = run(amendment("k", AM1, "2025-03-23", "2027-04-30"))
    scan = scan_of((HEAD, sha("h")))
    scan["files"][0]["status"] = "same"
    # הקובץ קיים אך לא חולץ בהרצה הזו: ההסכם נגרר, והמצב לא חוזר ל"תום התקופה חלף"
    data = assemble.assemble(scan, {}, "חברה", TODAY, previous=first)
    c = [x for x in data["agreements"] if x["number"] == a["number"]][0]
    assert c["agreement_state"] == "in_force" and c["dates"]["end"] == "2027-04-30"
    assert head_event(data)["superseded_by"] and head_event(data)["state_note"].startswith("תיקון להסכם מיום")


def test_draft_word_in_folder_name_does_not_make_a_signed_amendment_doubtful():
    data, a = run(amendment("k", "טיוטות ישנות/תיקון 1 - חתום.docx", "2025-03-23", "2027-04-30"))
    assert a["dates"]["end"] == "2027-04-30"
    assert not [r for r in data["review_queue"] if r["kind"] == "amendment_unconfirmed"]
