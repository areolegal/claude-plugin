import datetime as dt

from clm import assemble
from helpers import make_extract

T = dt.date(2026, 10, 23)
P, S = "x/a - חתום.docx", "a" * 64


def f(path, sha, status="new"):
    return {"path": path, "sha256": sha, "status": status, "abs": None, "duplicate_of": None}


def ev(**kw):
    base = {"event_code": "term_end", "label": "תום התקופה הראשונה", "date": "2021-06-30", "relative": False,
            "trigger": "", "clause": "3", "quote": "ציטוט", "obligor": "both", "consequence": "auto_change",
            "impact": "material", "if_nothing": "", "action": "", "notice_days": None, "recurrence": None,
            "renewal_months": None, "renewal_max": None, "computed": False}
    base.update(kw)
    return base


def run(ext, **kw):
    return assemble.assemble({"files": [f(P, S)]}, {S: ext}, "חברה בע\"מ", T, **kw)


def test_end_taken_from_dated_term_end_deadline_when_empty():
    d = run(make_extract(S, P, dates={"signed": "2022-07-18", "start": "2022-07-18", "end": None},
                         events=[ev(date="2023-07-17", label="תום תקופת שירות")]))
    a = d["agreements"][0]
    assert a["dates"]["end"] == "2023-07-17"
    assert a["dates"]["end_basis"]["kind"] == "deadline" and "תום תקופת שירות" in a["dates"]["end_basis"]["note"]
    assert a["field_status"]["end_date"] == "derived"
    assert "end_source" not in a["dates"]


def test_current_end_follows_auto_renewal_roll_with_formula():
    d = run(make_extract(S, P, dates={"signed": "2020-06-14", "start": "2020-07-01", "end": "2021-06-30"},
                         events=[ev(renewal_months=12)]))
    a = d["agreements"][0]
    assert a["dates"]["end"] == "2021-06-30"
    assert a["dates"]["current_end"] == "2027-06-30"
    b = a["dates"]["current_end_basis"]
    assert b["kind"] == "auto_renewal" and "30.6.2021" in b["note"] and "12" in b["note"]
    assert a["field_status"]["end_date"] == "extracted"


def test_current_end_equals_end_without_renewal():
    a = run(make_extract(S, P))["agreements"][0]
    assert a["dates"]["current_end"] == a["dates"]["end"] == "2027-02-28"
    assert a["dates"]["current_end_basis"]["kind"] == "same_as_end"


def test_end_not_expected_by_catalog_type_and_missing_core_item():
    emp = make_extract(S, P, type_code="employment", type_label="העסקה",
                       dates={"signed": "2024-01-01", "start": "2024-01-01", "end": None}, events=[],
                       signatories=[{"party": "counterparty", "party_name": "ספק בדיקה בע\"מ", "name": "א", "role": "",
                                     "date": None, "status": "signed", "clause": "חתימות", "quote": "א"},
                                    {"party": "contracting", "party_name": "מדיקס שירותי בריאות דיגיטליים בע\"מ", "name": "ב",
                                     "role": "", "date": None, "status": "signed", "clause": "חתימות", "quote": "ב"}])
    d = run(emp)
    a = d["agreements"][0]
    assert a["field_status"]["end_date"] == "not_expected" and a["dates"]["current_end"] is None
    # סיום לא צפוי בסוג הזה: אין פריט על תאריך סיום (נשאר רק סוג התקופה, שלא חולץ)
    emp_items = [r for r in d["review_queue"] if r["kind"] == "missing_core"]
    assert all("תאריך סיום" not in r["text"] and "תאריך חתימה" not in r["text"] and "חותמים" not in r["text"]
               for r in emp_items)
    svc = make_extract(S, P, dates={"signed": None, "start": "2024-01-01", "end": None}, events=[])
    d2 = run(svc)
    items = [r for r in d2["review_queue"] if r["kind"] == "missing_core"]
    assert len(items) == 1 and items[0]["group"] == "שדה ליבה חסר"
    assert "תאריך חתימה" in items[0]["text"] and "תאריך סיום" in items[0]["text"]
    assert "סוג תקופה" in items[0]["text"] and "חותמים" in items[0]["text"]
    assert d2["agreements"][0]["field_status"]["end_date"] == "missing"


def test_kept_fields_notice_notes_not_found_entity_law():
    ext = make_extract(S, P, contracting_entity="חברה בע״מ", governing_law="אנגליה ווילס",
                       counterparty={"name": "ספק", "company_number": None, "notice_address": "רחוב הפלמ\"ח 15, ירושלים"},
                       notes=["משרה חלקית בהיקף 50%"], key_clauses_not_found=["mfn", "not_a_code", "exclusivity"])
    a = run(ext)["agreements"][0]
    assert a["counterparty_notice_address"] == "רחוב הפלמ\"ח 15, ירושלים"
    assert a["notes"] == [{"text": "משרה חלקית בהיקף 50%", "file": P}]
    assert a["key_clauses_not_found"] == ["exclusivity", "mfn"]
    assert a["contracting_entity"] == "חברה בע\"מ"
    # בלי דין מקומי ידוע אין סיווג "זר": unknown. עם דין מקומי: זר
    assert a["law_class"] == "unknown"
    assert run(ext, home_law="ישראל")["agreements"][0]["law_class"] == "foreign"
    assert run(make_extract(S, P, governing_law="ישראל"), home_law="ישראל")["agreements"][0]["law_class"] == "home"
    assert run(make_extract(S, P, governing_law="לא נקבע בנוסח; סמכות שיפוט: תל אביב"))["agreements"][0]["law_class"] == "unset"
    assert run(make_extract(S, P, governing_law=None))["agreements"][0]["law_class"] == "unset"
    assert run(make_extract(S, P, governing_law="Delaware"), home_law="Delaware")["agreements"][0]["law_class"] == "home"


def test_overdue_bucket_classification():
    evs = [ev(event_code="periodic_report", label="דוח שלנו", date="2026-03-01", obligor="us", consequence="we_breach"),
           ev(event_code="periodic_report", label="דוח שלהם", date="2026-03-02", obligor="them", consequence="they_breach_monitor"),
           ev(event_code="option_extend", label="אופציה", date="2026-03-03", obligor="us", consequence="right_lapses"),
           ev(event_code="periodic_report", label="ישן", date="2025-03-01", obligor="us", consequence="we_breach"),
           ev(event_code="periodic_report", label="עתידי", date="2026-12-01", obligor="us", consequence="we_breach")]
    d = run(make_extract(S, P, events=evs))
    by = {e["label"]: e.get("overdue_bucket") for e in d["events"]}
    assert by == {"דוח שלנו": "ours", "דוח שלהם": "theirs", "אופציה": "outcome", "ישן": "old", "עתידי": None}
    d2 = run(make_extract(S, P, our_role={"value": "", "source": "none"}, events=evs[:1]))
    assert d2["events"][0]["overdue_bucket"] == "role"


def test_extending_amendment_supersedes_conditional_options_and_buckets_them():
    head_path, am_path = "x/הסכם ענן - חתום.docx", "x/תיקון 1.docx"
    hs, ks = "h" * 64, "k" * 64
    options = [ev(event_code="option_extend", label="אופציה מותנית", date="2026-06-30", relative=True,
                  trigger="בהודעה מראש", obligor="us", consequence="right_lapses"),
               ev(event_code="option_extend", label="אופציה שחלפה", date="2025-06-30", obligor="us",
                  consequence="right_lapses")]
    head = make_extract(hs, head_path, dates={"signed": "2022-04-10", "start": "2022-05-01", "end": "2025-04-30"},
                        events=[ev(date="2025-04-30", label="תום התקופה לפי ההסכם")] + options
                        + [ev(date="2030-04-30", label="תום מאוחר", relative=False)])
    am = make_extract(ks, am_path, doc_kind="amendment", title="תיקון 1",
                      dates={"signed": "2025-03-23", "start": "2025-05-01", "end": "2027-04-30"},
                      events=[ev(date="2027-04-30", label="תום התקופה לפי התיקון")], commercials=[])
    scan = {"files": [f(head_path, hs), f(am_path, ks)]}
    d = assemble.assemble(scan, {hs: head, ks: am}, "חברה", T)
    by = {e["label"]: e for e in d["events"]}
    cond = by["אופציה מותנית"]
    assert cond["state"] == "pending_trigger" and cond["superseded_by"] == "doc-" + ks[:10]
    assert cond["overdue_bucket"] is None
    lapsed = by["אופציה שחלפה"]
    assert lapsed["state"] == "lapsed_pending" and lapsed["superseded_by"]
    assert lapsed["overdue_bucket"] == "superseded"
    assert "superseded_by" not in by["תום מאוחר"]


def test_not_found_accepts_code_objects():
    ext = make_extract(S, P, key_clauses_not_found=[{"clause_code": "mfn", "note": "נבדק ולא נמצא"}, "exclusivity",
                                                    {"note": "x"}, 7])
    assert run(ext)["agreements"][0]["key_clauses_not_found"] == ["exclusivity", "mfn"]


def test_carried_agreement_rolls_current_end_forward():
    ext = make_extract(S, P, dates={"signed": "2020-06-14", "start": "2020-07-01", "end": "2021-06-30"},
                       events=[ev(renewal_months=12)])
    r1 = assemble.assemble({"files": [f(P, S)]}, {S: ext}, "חברה", T)
    assert r1["agreements"][0]["dates"]["current_end"] == "2027-06-30"
    later = dt.date(2027, 10, 23)
    r2 = assemble.assemble({"files": [f(P, S, "removed")]}, {}, "חברה", later, previous=r1)
    a = r2["agreements"][0]
    assert a["source_removed"] is True
    assert a["dates"]["current_end"] == "2028-06-30"
    assert a["dates"]["current_end_basis"]["kind"] == "auto_renewal"
    # בלי חידוש: נופל חזרה לסיום ההסכם
    plain = make_extract(S, P)
    q1 = assemble.assemble({"files": [f(P, S)]}, {S: plain}, "חברה", T)
    q1["agreements"][0]["dates"]["current_end"] = "2099-01-01"
    q2 = assemble.assemble({"files": [f(P, S, "removed")]}, {}, "חברה", T, previous=q1)
    b = q2["agreements"][0]["dates"]
    assert b["current_end"] == b["end"] == "2027-02-28" and b["current_end_basis"]["kind"] == "same_as_end"


def _kid(sha, **kw):
    return make_extract(sha, "x/תוספת 1 - חתום.docx", doc_kind="amendment", title="תוספת 1",
                        relation={"kind": "amendment", "parent_hint": "הסכם מיום 1.3.2025"},
                        dates={"signed": "2025-04-20", "start": "2025-05-01", "end": None}, events=[], **kw)


def test_key_clauses_not_found_only_checked_sources_minus_found():
    kc = {"clause_code": "mfn", "summary": "x", "value": "", "clause": "2", "quote": "q"}
    head_ext = make_extract(S, P, key_clauses_checked=True,
                            key_clauses=[dict(kc, clause_code="change_of_control")],
                            key_clauses_not_found=["exclusivity", {"clause_code": "mfn"}])
    kid = "b" * 64
    KP = "x/תוספת 1 - חתום.docx"
    files = {"files": [f(P, S), f(KP, kid)]}
    kid_ext = _kid(kid, key_clauses_checked=False,
                   key_clauses_not_found=["change_of_control", "non_compete", "assignment"])
    d = assemble.assemble(files, {S: head_ext, kid: kid_ext}, "חברה", T)
    assert len(d["agreements"]) == 1
    assert d["agreements"][0]["key_clauses_not_found"] == ["exclusivity", "mfn"]
    # מקור שנבדק מוסיף; סעיף שנמצא באחד המקורות נגרע
    kid_ext2 = _kid(kid, key_clauses_checked=True, key_clauses=[kc],
                    key_clauses_not_found=["non_compete", "change_of_control"])
    d2 = assemble.assemble(files, {S: head_ext, kid: kid_ext2}, "חברה", T)
    assert d2["agreements"][0]["key_clauses_not_found"] == ["exclusivity", "non_compete"]
    # אף מקור לא נבדק: מהמסמך הראשי בלבד
    head3 = make_extract(S, P, key_clauses_checked=False, key_clauses_not_found=["exclusivity"])
    d3 = assemble.assemble(files, {S: head3, kid: kid_ext}, "חברה", T)
    assert d3["agreements"][0]["key_clauses_not_found"] == ["exclusivity"]
