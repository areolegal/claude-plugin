import datetime as dt
from clm import catalog, dates

CAT = catalog.load_events()
TODAY = dt.date(2026, 10, 22)


def ev(**kw):
    base = {"event_code": "insurance_cert", "label": "חידוש אישור ביטוח", "date": "2025-10-15",
            "relative": False, "trigger": "", "clause": "סעיף 10", "obligor": "us",
            "consequence": "we_breach", "impact": "critical", "if_nothing": "", "action": "",
            "notice_days": None, "recurrence": {"months": 12, "max": None}}
    base.update(kw)
    return base


def test_rollable_annual_rolls_forward_and_is_derived():
    r = dates.derive(ev(), TODAY, CAT)
    assert r["state"] == "upcoming" and r["date"] == "2027-10-15" and r["derived"] is True
    assert r["history"] == ["2025-10-15", "2026-10-15"] and r["contract_date_original"] == "2025-10-15"
    r2 = dates.derive(ev(date="2025-11-15"), TODAY, CAT)
    assert r2["date"] == "2026-11-15" and r2["act_by"] == "2026-11-01"
    # החלטת אנוש (פריט 4): המופע האחרון שחלף (15.10.2026) נשאר פתוח לצד המועד שגולגל
    main, passed = dates.derive_all(ev(), TODAY, CAT)
    assert main == r and main["renewed"] is False
    assert passed["occurrence"] == "passed" and passed["date"] == "2026-10-15" and passed["derived"] is True
    assert passed["state"] == "needs_action" and passed["act_by"] is None and passed["next_reminder"] is None
    assert "15.10.2026" in passed["action"] and passed["history"] == []
    lapsed = dates.derive_all(ev(consequence="right_lapses"), TODAY, CAT)[1]
    assert lapsed["state"] == "lapsed_pending" and "לאשר מה קרה" in lapsed["action"]
    assert len(dates.derive_all(ev(date="2026-11-15"), TODAY, CAT)) == 1


def test_option_never_rolls_even_with_recurrence():
    r = dates.derive(ev(event_code="option_extend", consequence="right_lapses", date="2026-06-03"), TODAY, CAT)
    assert r["state"] == "lapsed_pending" and r["derived"] is False and r["date"] == "2026-06-03"
    assert "לאשר מה קרה" in r["action"]


def test_term_end_passed_needs_action_unless_renewal_known():
    r = dates.derive(ev(event_code="term_end", consequence="auto_change", date="2026-08-31", recurrence=None), TODAY, CAT)
    assert r["state"] == "needs_action"
    r2 = dates.derive(ev(event_code="term_end", consequence="auto_change", date="2026-08-31", recurrence=None,
                         renewal_months=12), TODAY, CAT)
    assert r2["state"] == "upcoming" and r2["date"] == "2027-08-31" and r2["derived"]
    # חידוש אוטומטי שחלף: ההסכם מוצג כמתחדש, והמופע שחלף פתוח לאימות החידוש
    main, passed = dates.derive_all(ev(event_code="term_end", consequence="auto_change", date="2026-08-31",
                                       recurrence=None, renewal_months=12), TODAY, CAT)
    assert main["renewed"] is True and passed["renewal_check"] is True
    assert passed["state"] == "lapsed_pending" and passed["date"] == "2026-08-31" and passed["derived"] is False
    assert "לאמת שההסכם התחדש" in passed["action"]


def test_recurrence_max_reached_stays_open():
    # עדכון לפי החלטת האנוש (פריט 4): המופע האחרון שחלף הוא "באיחור" כשההשלכה היא חשש להפרה מצדנו,
    # ו"חלף, ממתין לאישור תוצאה" בכל השלכה אחרת
    r = dates.derive(ev(date="2024-01-10", recurrence={"months": 12, "max": 1}), TODAY, CAT)
    assert r["state"] == "needs_action" and r["date"] == "2025-01-10"
    r2 = dates.derive(ev(date="2024-01-10", consequence="right_lapses", recurrence={"months": 12, "max": 1}), TODAY, CAT)
    assert r2["state"] == "lapsed_pending"
    assert len(dates.derive_all(ev(date="2024-01-10", recurrence={"months": 12, "max": 1}), TODAY, CAT)) == 1
    r3 = dates.derive(ev(event_code="term_end", consequence="auto_change", date="2024-08-31", recurrence=None,
                         renewal_months=12, renewal_max=1), TODAY, CAT)
    assert r3["state"] == "needs_action" and r3["date"] == "2025-08-31"


def test_relative_missing_and_role_pending():
    assert dates.derive(ev(date=None, relative=True, trigger="תום ההסכם"), TODAY, CAT)["state"] == "pending_trigger"
    assert dates.derive(ev(date=None), TODAY, CAT)["state"] == "missing"
    assert dates.derive(ev(), TODAY, CAT, role_confirmed=False)["role_pending"] is True


def test_generic_action_replaced_with_specific_one():
    r = dates.derive(ev(event_code="nonrenewal_notice", consequence="right_lapses", date="2026-11-30",
                        recurrence=None, notice_days=90, action="לבחון את הסעיף ולפעול לפי הנדרש בו."),
                     TODAY, CAT, cp="ספקטרה")
    assert r["act_by"] == "2026-10-16"
    assert "ספקטרה" in r["action"] and "16.10.2026" in r["action"] and "30.11.2026" in r["action"]
    assert "90 יום" in r["action"]


def test_states_closed_set_and_no_realized():
    for kw in ({}, {"date": None}, {"event_code": "audit_window", "consequence": "opportunity", "recurrence": None, "date": "2026-01-01"}):
        assert dates.derive(ev(**kw), TODAY, CAT)["state"] in dates.STATES
    assert "realized" not in dates.STATES


def test_next_reminder_ladder():
    r = dates.derive(ev(event_code="nonrenewal_notice", consequence="right_lapses", date="2026-12-31", recurrence=None), TODAY, CAT)
    assert r["act_by"] == "2026-11-16" and r["next_reminder"] == "2026-11-02"


def test_add_months_end_of_month():
    assert dates.add_months(dt.date(2027, 1, 31), 1) == dt.date(2027, 2, 28)


def test_annual_roll_keeps_leap_day_anchor():
    r = dates.derive(ev(date="2024-02-29"), dt.date(2028, 1, 1), CAT)
    assert r["date"] == "2028-02-29"
    assert r["history"] == ["2024-02-29", "2025-02-28", "2026-02-28", "2027-02-28"]


def test_monthly_roll_keeps_month_end_anchor():
    r = dates.derive(ev(date="2026-01-31", recurrence={"months": 1, "max": None}), dt.date(2026, 3, 15), CAT)
    assert r["date"] == "2026-03-31"


def test_rolled_event_gets_template_action_not_stale_extracted_one():
    r = dates.derive(ev(date="2025-10-15", action="להמציא אישור עד 15.10.2025"), TODAY, CAT)
    assert r["date"] == "2027-10-15" and r["state"] == "upcoming"
    assert "15.10.2027" in r["action"] and "15.10.2025" not in r["action"]


def test_non_positive_recurrence_does_not_roll_or_hang():
    r = dates.derive(ev(date="2025-10-15", recurrence={"months": -1, "max": None}), TODAY, CAT)
    assert r["state"] == "needs_action" and r["history"] == [] and r["derived"] is False
    r2 = dates.derive(ev(event_code="term_end", consequence="auto_change", date="2026-08-31", recurrence=None,
                         renewal_months=-1), TODAY, CAT)
    assert r2["state"] == "needs_action"
