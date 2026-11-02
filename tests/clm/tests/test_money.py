import datetime as dt

from clm import assemble, money
from clm.validate import check_data
from helpers import make_extract

T = dt.date(2026, 10, 22)


def row(value, unit="₪", period="חודשי", category="תעריף", label="תמורה", **kw):
    return dict({"category": category, "label": label, "value": value, "unit": unit, "period": period}, **kw)


def test_currency_from_row_unit_label_then_fallback():
    assert money.currency_of(row(1, currency="usd")) == "USD"
    assert money.currency_of(row(1, unit="EUR לפני מע״מ")) == "EUR"
    assert money.currency_of(row(1, unit="", label="התחייבות שנתית 186,000 דולר")) == "USD"
    assert money.currency_of(row(1, unit=""), "ILS") == "ILS"
    assert money.currency_of(row(1, unit=""), None) is None
    assert money.currency_of(row(1, unit="₪ או $")) is None


def test_per_unit_rates_are_detected():
    assert money.per_unit(row(9200, unit="₪ לעמדה"))
    assert money.per_unit(row(240, unit="EUR לשעה", period="לשעה"))
    assert money.per_unit(row(42000, period="לחודש למהנדס"))
    assert money.per_unit(row(10, unit="USD per seat"))
    assert not money.per_unit(row(186000, unit='דולר ארה"ב לשנה', period="שנתי"))
    assert not money.per_unit(row(1, unit="₪ לחודש"))
    assert not money.per_unit(row(1, unit='₪ בתוספת מע"מ'))
    assert not money.per_unit(row(1, unit="EUR לפני מע״מ"))


def test_annual_per_currency_never_adds_currencies():
    r = money.annual([row(21500, unit="EUR"), row(186000, unit="USD", period="שנתי"), row(1000)])
    assert r["by_currency"] == {"EUR": 258000, "ILS": 12000, "USD": 186000}


def test_annual_skips_per_unit_and_unknown_currency_and_lists_them():
    r = money.annual([row(138000), row(9200, unit="₪ לעמדה", label="תוספת לעמדה"), row(5, unit="", label="x")])
    assert r["by_currency"] == {"ILS": 1656000}
    assert r["not_counted"] == [{"label": "תוספת לעמדה", "reason": "תעריף ליחידה, תלוי בהיקף"}]
    assert r["unknown_currency"] == ["x"]


AM = dict(component="מקורי", operation="replace", effective_date="2025-05-01")


def test_signed_amendment_row_replaces_original_component():
    # עודכן: בלי רכיב, פעולה ותאריך תוקף תיקון כספי כבר אינו מחליף שורה (C-05); כאן הוא מצביע על הרכיב "מקורי"
    r = money.annual([row(171000, label="מקורי"), dict(row(177670, label="מתוקן"), _rank="2025-04-20", **AM)])
    assert r["by_currency"] == {"ILS": 2132040}
    assert r["amended_on"] == "2025-04-20"
    assert {"label": "מקורי", "reason": "הוחלף בתיקון להסכם"} in r["not_counted"]


def test_non_value_categories_and_one_off_rows_are_ignored():
    r = money.annual([row(2052000, category="חישוב", period="שנתי"), row(150000, period="חד-פעמי"), row("x")])
    assert r["by_currency"] == {} and r["not_counted"] == [] and r["unknown_currency"] == []


def f(path, sha):
    return {"path": path, "sha256": sha, "status": "new", "abs": None, "duplicate_of": None}


def test_assemble_value_has_no_currency_default_and_portfolio_flag():
    s1, s2 = "1" * 64, "2" * 64
    signed = make_extract(s1, "x/a - חתום.docx", currency=None,
                          commercials=[row(10000, unit="", label="תמורה", clause="7", quote="")])
    draft = make_extract(s2, "x/b טיוטה.docx", doc_kind="draft", title="טיוטה", counterparty={"name": "אחר", "company_number": None, "notice_address": None})
    d = assemble.assemble({"files": [f("x/a - חתום.docx", s1), f("x/b טיוטה.docx", s2)]}, {s1: signed, s2: draft}, "חברה", T)
    a = next(x for x in d["agreements"] if x["title"] == "הסכם בדיקה")
    b = next(x for x in d["agreements"] if x["title"] == "טיוטה")
    assert a["value"]["annual_by_currency"] == {} and a["value"]["currency"] is None
    assert a["value"]["unknown_currency"] == ["תמורה"]
    assert a["value"]["in_portfolio"] is True
    assert b["value"]["annual_by_currency"] == {"ILS": 384000} and b["value"]["in_portfolio"] is False
    cp = next(c for c in d["counterparties"] if c["name"] == "אחר")
    assert cp["annual_by_currency"] == {}


def test_assemble_uses_signed_amendment_price():
    s1, s2 = "3" * 64, "4" * 64
    head = make_extract(s1, "x/a - חתום.docx", commercials=[row(171000, clause="ד 1.1", quote="")])
    kid = make_extract(s2, "x/תוספת 1 - חתום.docx", doc_kind="amendment", title="תוספת 1",
                       relation={"kind": "amendment", "parent_hint": "הסכם מיום 1.3.2025"},
                       dates={"signed": "2025-04-20", "start": "2025-05-01", "end": None}, events=[],
                       commercials=[row(177670, unit="₪ לפני מע״מ", clause="2.1", quote="", component="תמורה",
                                        operation="replace", effective_date="2025-05-01")])
    d = assemble.assemble({"files": [f("x/a - חתום.docx", s1), f("x/תוספת 1 - חתום.docx", s2)]}, {s1: head, s2: kid}, "חברה", T)
    a = d["agreements"][0]
    assert len(d["agreements"]) == 1, "the amendment must attach to the agreement"
    assert a["value"]["annual_by_currency"] == {"ILS": 2132040}
    assert "20.4.2025" in a["value"]["basis"]


def test_normalize_upgrades_legacy_value():
    v = money.normalize({"annual": 5000, "currency": "USD", "total": None, "basis": "x"}, False)
    # המבנה הישן נתן מטבע ברירת מחדל ועירבב שורות: לא סומכים עליו
    assert v["annual_by_currency"] == {} and v["in_portfolio"] is False
    assert v["not_counted"] == [] and v["total_currency"] is None
    assert v["unknown_currency"] == ["שווי מהרצה קודמת, ממתין לחילוץ מחדש"]


def test_currency_marks_do_not_match_inside_other_words():
    for text in ("Payment details", "Ministry fee", "תשלום לאירוע", "Reunion fee", "Eurostar"):
        assert money.currency_of(row(1, unit=text)) is None, text
    assert money.currency_of(row(1, unit="תשלום לאירוע"), "ILS") == "ILS"


def test_currency_marks_that_are_real():
    for text, cur in (("₪", "ILS"), ("שקלים", "ILS"), ("באירו", "EUR"), ("USD", "USD"), ("usd", "USD"),
                      ("US$", "USD"), ("דולרים", "USD"), ("ש״ח", "ILS"), ('ליש"ט', "GBP"), ("בדולר", "USD"),
                      ("NIS", "ILS"), ("EUR לפני מע״מ", "EUR")):
        assert money.currency_of(row(1, unit=text)) == cur, text


def test_per_unit_not_triggered_by_ordinary_hebrew_words():
    assert not money.per_unit(row(1, unit='₪ ללא מע"מ'))
    assert not money.per_unit(row(1, unit="₪ לפי חשבונית"))
    assert not money.per_unit(row(1, period="חודשי לאחר ההנחה"))
    assert money.per_unit(row(9200, unit="₪ לעמדה"))


def test_tidy_rounds_and_sorts():
    assert list(money.tidy({"USD": 1.0, "EUR": 2.345})) == ["EUR", "USD"]
    assert money.tidy({"USD": 1.0, "EUR": 2.345}) == {"EUR": 2.35, "USD": 1}


def _run_amendment(kid_path, signed, **kw):
    s1, s2 = "5" * 64, "6" * 64
    head = make_extract(s1, "x/a - חתום.docx", commercials=[row(171000, clause="ד 1.1", quote="")])
    kid = make_extract(s2, kid_path, doc_kind="amendment", title="תוספת 1",
                       relation={"kind": "amendment", "parent_hint": "הסכם מיום 1.3.2025"},
                       dates={"signed": signed, "start": None, "end": None}, events=[],
                       commercials=[row(177670, unit="₪ לפני מע״מ", clause="2.1", quote="")])
    d = assemble.assemble({"files": [f("x/a - חתום.docx", s1), f(kid_path, s2)]}, {s1: head, s2: kid}, "חברה", T)
    assert len(d["agreements"]) == 1, "the amendment must attach to the agreement"
    return d


def test_unsigned_or_draft_named_amendment_does_not_change_value():
    for path, signed in (("x/תוספת 1.docx", None), ("x/תוספת 1 טיוטה.docx", "2025-04-20")):
        d = _run_amendment(path, signed)
        v = d["agreements"][0]["value"]
        assert v["annual_by_currency"] == {"ILS": 2052000}, path
        assert "תיקון להסכם" not in (v["basis"] or ""), path
        assert sorted(c["value"] for c in d["commercials"]) == [171000, 177670], path


def test_carry_normalizes_legacy_value_and_follows_recomputed_state():
    s1, s2 = "7" * 64, "9" * 64
    p, pd = "x/a - חתום.docx", "x/b טיוטה.docx"
    other = {"name": "אחר", "company_number": None, "notice_address": None}
    exts = {s1: make_extract(s1, p), s2: make_extract(s2, pd, doc_kind="draft", title="טיוטה", counterparty=other)}
    r1 = assemble.assemble({"files": [f(p, s1), f(pd, s2)]}, exts, "חברה", T)
    for a in r1["agreements"]:
        a["value"] = {"annual": 5000, "currency": "USD", "total": None, "basis": "x"}
    removed = {"files": [dict(f(p, s1), status="removed"), dict(f(pd, s2), status="removed")]}
    r2 = assemble.assemble(removed, {}, "חברה", T, previous=r1)
    by_title = {a["title"]: a for a in r2["agreements"]}
    assert all(a["source_removed"] is True for a in r2["agreements"])
    v = by_title["הסכם בדיקה"]["value"]
    assert v["annual_by_currency"] == {} and v["in_portfolio"] is True
    assert v["not_counted"] == [] and v["unknown_currency"] == ["שווי מהרצה קודמת, ממתין לחילוץ מחדש"]
    assert v["total_currency"] is None
    assert by_title["טיוטה"]["value"]["in_portfolio"] is False
    # מצב שנגזר מחדש בהרצה מאוחרת מוציא את ההסכם מהתיק: תום תקופה שחלף ואינו מתחדש
    end = {"event_code": "term_end", "label": "תום תקופת ההסכם", "date": "2025-04-30", "relative": False,
           "trigger": "", "clause": "סעיף 2", "quote": "ההסכם בתוקף עד ליום 30.4.2025.", "obligor": "us",
           "consequence": "auto_change", "impact": "critical", "if_nothing": "ההסכם מסתיים.", "action": "",
           "notice_days": None, "recurrence": None, "renewal_months": None, "renewal_max": None, "computed": False}
    s3 = "a" * 64
    e3 = make_extract(s3, p, events=[end], dates={"signed": "2024-05-01", "start": "2024-05-01", "end": "2025-04-30"})
    q1 = assemble.assemble({"files": [f(p, s3)]}, {s3: e3}, "חברה", dt.date(2025, 1, 1))
    assert q1["agreements"][0]["value"]["in_portfolio"] is True
    q2 = assemble.assemble({"files": [dict(f(p, s3), status="removed")]}, {}, "חברה", T, previous=q1)
    a2 = q2["agreements"][0]
    assert a2["agreement_state"] == "term_passed_unverified" and a2["value"]["in_portfolio"] is False
    assert check_data(q2)[0] == []


def test_counterparty_sums_only_portfolio_agreements_per_currency():
    cp = {"name": "ספק משותף", "company_number": None, "notice_address": None}
    items, exts = [], {}
    for i, (name, cur_unit, val, kind) in enumerate((("אחד", "₪", 1000.5, "signed"), ("שניים", "EUR", 500, "signed"),
                                                      ("שלושה", "₪", 250.25, "signed"), ("טיוטה", "₪", 99999, "draft"))):
        sh = str(i + 1) * 64
        path = "x/%s - חתום.docx" % name if kind == "signed" else "x/%s.docx" % name
        exts[sh] = make_extract(sh, path, doc_kind=kind, title=name, counterparty=cp,
                                commercials=[row(val, unit=cur_unit, period="שנתי", clause="1", quote="")])
        items.append(f(path, sh))
    d = assemble.assemble({"files": items}, exts, "חברה", T)
    assert len(d["agreements"]) == 4
    c = next(x for x in d["counterparties"] if x["name"] == "ספק משותף")
    assert len(c["agreements"]) == 4
    assert c["annual_by_currency"] == {"EUR": 500, "ILS": 1250.75} and list(c["annual_by_currency"]) == ["EUR", "ILS"]


def test_validate_reports_unknown_currency_key():
    s1 = "8" * 64
    p = "x/a - חתום.docx"
    d = assemble.assemble({"files": [f(p, s1)]}, {s1: make_extract(s1, p)}, "חברה", T)
    assert check_data(d)[0] == []
    d["agreements"][0]["value"]["annual_by_currency"]["12"] = 5
    errs = check_data(d)[0]
    assert any("12" in e and "מטבע" in e for e in errs)


def test_per_unit_ignores_currency_words_and_per_period_phrases():
    for unit in ('ליש"ט', "ליש״ט", "לירות שטרלינג", "לירה", "₪ לכל חודש", "₪ לכל שנה", "לשקלים", "שטרלינג"):
        assert not money.per_unit(row(1, unit=unit)), unit
    assert money.per_unit(row(1, unit="₪ לכל עמדה"))
    assert money.per_unit(row(1, unit="לירות לעמדה"))


def test_hebrew_pound_words_are_gbp():
    for text in ('ליש"ט', "ליש״ט", "לירות שטרלינג", "לירה שטרלינג", "בשטרלינג", "לירות"):
        assert money.currency_of(row(1, unit=text)) == "GBP", text
    r = money.annual([row(5000, unit="ליש״ט", period="חודשי")])
    assert r["by_currency"] == {"GBP": 60000} and r["not_counted"] == []


def test_one_off_row_is_never_labeled_per_unit():
    r = money.annual([row(100, unit="₪ לעמדה", period="חד-פעמי"), row(100, unit="ליש״ט", period="חד-פעמי")])
    assert r["not_counted"] == [] and r["by_currency"] == {} and r["unknown_currency"] == []


def test_estimate_period_stays_counted_and_basis_says_so():
    r = money.annual([row(1000, period="שנתי (אומדן)")])
    assert r["by_currency"] == {"ILS": 1000} and r["estimated"] is True
    assert money.annual([row(1000, period="שנתי")])["estimated"] is False
    s1 = "5" * 64
    ext = make_extract(s1, "x/a - חתום.docx", commercials=[
        {"category": "תעריף", "label": "אומדן שנתי", "value": 1000, "unit": "₪", "period": "שנתי (אומדן)",
         "clause": "סעיף 7", "quote": "אומדן"}])
    d = assemble.assemble({"files": [f("x/a - חתום.docx", s1)]}, {s1: ext}, "חברה", T)
    v = d["agreements"][0]["value"]
    assert v["annual_by_currency"] == {"ILS": 1000}
    assert v["basis"].endswith("; כולל אומדן")


def test_structured_value_kind_and_basis_win_over_text():
    rows = [{"category": "תעריף", "label": "דמי שירות", "value": 10000, "unit": "₪", "period": "", "value_kind": "monthly"},
            {"category": "תעריף", "label": "לפי עמדה", "value": 50, "unit": "₪", "period": "חודשי", "basis": "usage"},
            {"category": "תעריף", "label": "סך ההתקשרות", "value": 900000, "unit": "₪", "period": "שנתי", "value_kind": "total"},
            {"category": "תעריף", "label": "תקרה", "value": 200000, "unit": "₪", "period": "שנתי", "value_kind": "max"},
            {"category": "תעריף", "label": "אומדן", "value": 1000, "unit": "₪", "period": "שנתי", "basis": "estimate"}]
    out = money.annual(rows)
    assert out["by_currency"] == {"ILS": 121000}
    assert [x["reason"] for x in out["not_counted"]] == ["תעריף ליחידה, תלוי בהיקף", "סכום כולל, לא שנתי", "תקרה, לא שווי"]
    assert out["estimated"] is True


def _est(rows):
    return money.annual(rows)["estimated"]


def test_estimated_follows_each_counted_row_not_a_stale_variable():
    est = row(1000, period="שנתי", label="אומדן", basis="estimate")
    fixed = row(2000, period="שנתי", label="קבוע", basis="fixed")
    assert _est([est, fixed]) is True
    assert _est([fixed, est]) is True
    assert _est([fixed]) is False
    trailing = row(900000, period="שנתי", label="סך הכל", value_kind="total", basis="estimate")
    assert _est([fixed, trailing]) is False
    assert _est([est, trailing]) is True
