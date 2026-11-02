"""לוח הבקרה, שלב א: כסף לכל מטבע, איחור לפי דלי, מועדים שלא נעלמים. הסקריפט רץ ב-node."""
import datetime as dt
import json
import os
import re
import shutil
import subprocess

import pytest

from clm import assemble, build
from helpers import CATEGORIES, make_extract

import clm_paths  # noqa: E402
ROOT = clm_paths.SKILL
TEMPLATE = os.path.join(ROOT, "assets", "workspace-template.html")
HARNESS = clm_paths.HARNESS
TODAY = dt.date(2026, 10, 22)
COV = [{"category": c, "status": "found", "count": 1} for c in CATEGORIES]


def cp(name):
    return {"name": name, "company_number": None, "notice_address": None}


def ev(code, date, label, cons, obligor="us"):
    return dict(make_extract("z" * 64, "x")["events"][0], event_code=code, date=date, label=label,
                consequence=cons, obligor=obligor, renewal_months=None, impact="material", clause="סעיף 2",
                quote="עד ליום " + date)


def com(value, unit, period, cur):
    return [{"category": "תעריף", "label": "תמורה", "value": value, "unit": unit, "period": period,
             "currency": cur, "clause": "סעיף 7", "quote": "התמורה כתובה בהסכם"}]


def dataset():
    rows = []

    def add(i, title, fname=None, **kw):
        sha, path = str(i) * 64, "x/%s.docx" % (fname or title + " - חתום")
        rows.append(({"path": path, "sha256": sha, "status": "new", "abs": None, "duplicate_of": None},
                     make_extract(sha, path, title=title, coverage=COV, **kw)))
    add(1, "הסכם שקלי", counterparty=cp("שקל בע\"מ"), commercials=com(32000, "₪ לחודש", "חודשי", "ILS"), currency="ILS",
        guarantees=[{"kind": "ערבות בנקאית", "title": "ערבות ביצוע", "amount": "לא נקוב", "expiry": None,
                     "clause": "סעיף 15", "quote": "החברה תמציא ערבות", "direction": "given"}],
        events=[ev("payment_report", "2026-09-01", "דוח שלנו שחלף", "we_breach"),
                ev("payment_report", "2026-08-01", "דוח הצד שכנגד שחלף", "they_breach_monitor", "them"),
                ev("option_extend", "2026-07-01", "אופציה שחלפה", "opportunity"),
                ev("payment_report", "2025-06-01", "דוח ישן מהשנה שעברה", "we_breach"),
                ev("payment_report", "2026-07-15", "דוח שהוחלף בתיקון", "we_breach"),
                ev("insurance_cert", "2026-12-15", "אישור ביטוח משותף", "we_breach", "both")])
    add(2, "הסכם דולרי", counterparty=cp("USD Inc"), commercials=com(15500, "$ לחודש", "חודשי", "USD"), currency="USD",
        events=[])
    add(3, "הסכם אירו שחלף", counterparty=cp("אירו GmbH"), commercials=com(20000, "€ לחודש", "חודשי", "EUR"),
        currency="EUR", dates={"signed": "2024-01-01", "start": "2024-01-01", "end": "2026-06-30"},
        events=[ev("term_end", "2026-06-30", "תום תקופה שחלף", "auto_change")])
    add(4, "טיוטה שקלית", fname="טיוטה שקלית", doc_kind="draft", counterparty=cp("טיוטה בע\"מ"),
        commercials=com(777000, "₪ לשנה", "שנתי", "ILS"), currency="ILS",
        dates={"signed": None, "start": None, "end": None}, events=[])
    add(5, "הסכם תפקיד", counterparty=cp("תפקיד בע\"מ"), our_role={"value": "לקוח", "source": "suggested"},
        commercials=[], events=[ev("nonrenewal_notice", "2026-12-15", "הודעה שממתינה לתפקיד", "right_lapses"),
                                ev("payment_report", "2026-03-01", "דוח שחלף וממתין לתפקיד", "we_breach")])
    data = assemble.assemble({"files": [r[0] for r in rows]}, {r[1]["sha256"]: r[1] for r in rows}, "חברה", TODAY)
    sup = next(e for e in data["events"] if e["label"] == "דוח שהוחלף בתיקון")
    sup.update(superseded_by="doc-1", superseded_note="הוחלף בתיקון", overdue_bucket="superseded")
    return data


@pytest.fixture(scope="module")
def page(tmp_path_factory):
    if not shutil.which("node"):
        pytest.skip("node אינו מותקן")
    data = dataset()
    d = tmp_path_factory.mktemp("stage_a")
    data_path, out, ex_path = str(d / "data.json"), str(d / "out.html"), str(d / "exprs.json")
    with open(data_path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False)
    build.build(data_path, TEMPLATE, out)
    ids = {a["title"]: a["id"] for a in data["agreements"]}
    card = "(openAg(%r, 'sum'), document.querySelector('#drawer').innerHTML)"
    exprs = {
        "repo": "V.repo()", "dash": "V.dash()", "tasks": "V.tasks()", "obl": "V.obl()", "renew": "V.renew()",
        "cps": "V.cps()", "n_tasks": "counts().tasks", "n_dates": "counts().dates",
        "dates_default": "(df.state = 'open', df.win = 'all', df.cons = '', V.dates())",
        "m_999600": "money(999600, 'ILS')", "m_999400": "money(999400, 'ILS')", "m_999500": "money(999500, 'ILS')",
        "m_1e6": "money(1000000, 'ILS')",
        "m_usd": "money(186000, 'USD')", "m_ils": "money(1656000, 'ILS')", "m_eur": "money(5000, 'EUR')",
        "m_gbp": "money(12, 'GBP')", "m_unknown": "money(5, null)", "m_none": "moneyBy({})",
        "m_by": "moneyBy({USD: 186000, ILS: 384000})",
        "sum_by": "sumBy([A[%r], A[%r]])" % (ids["הסכם שקלי"], ids["הסכם דולרי"]),
        "odb": "ODB",
        "nav_team": "(scope = 'team', nav(), document.querySelector('#nav').innerHTML)",
        "title_me": "(scope = 'me', [ttl('tasks')].map(x => (scope = 'team', x))[0])",
        "nav_me": "(scope = 'me', nav(), [document.querySelector('#nav').innerHTML].map(x => (scope = 'team', x))[0])",
        "dash_no_sec": "(() => { const s = D.events; D.events = s.filter(e => !['insurance_cert', 'guarantee_expiry'].includes(e.event_code)); const h = V.dash(); D.events = s; return h; })()",
        "tasks_me": "(() => { scope = 'me'; S.owner[%r] = 'me'; const r = [counts().tasks, V.tasks()]; scope = 'team'; delete S.owner[%r]; return r; })()" % (ids["הסכם תפקיד"], ids["הסכם תפקיד"]),
        "repo_late": "(rf.flag = 'late', [V.repo()].map(h => (rf.flag = '', h))[0])",
        "money": "V.money()",
        "card_ils": card % ids["הסכם שקלי"], "card_draft": card % ids["טיוטה שקלית"],
        "buckets": "EV().filter(e => ['needs_action','lapsed_pending'].includes(e.state)).reduce((m, e) => (m[e.overdue_bucket] = (m[e.overdue_bucket] || 0) + 1, m), {})",
        "live_sup": "D.events.filter(e => e.superseded_by).map(live)",
    }
    with open(ex_path, "w", encoding="utf-8") as fh:
        json.dump(exprs, fh, ensure_ascii=False)
    r = subprocess.run(["node", HARNESS, out, ex_path], capture_output=True, text=True, encoding="utf-8")
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout), data


def footer(repo):
    m = re.search(r"שווי שנתי של ההסכמים החתומים והפעילים: ([^<]*)</span>", repo)
    assert m, "no portfolio footer"
    return m.group(1)


def test_money_formats_per_currency_in_compact_hebrew(page):
    p, _ = page
    assert p["m_usd"] == "186 אלף $" and p["m_ils"] == "1.66 מיליון ₪"
    assert p["m_eur"] == "5 אלף €" and p["m_gbp"] == "12 £"
    assert "מטבע לא ידוע" in p["m_unknown"] and "5" in p["m_unknown"]
    assert p["m_none"] == ""
    assert p["m_by"] == "384 אלף ₪ · 186 אלף $"


def test_sum_by_adds_each_currency_separately(page):
    p, _ = page
    assert p["sum_by"] == {"ILS": 384000, "USD": 186000}


def test_repo_footer_sums_only_agreements_in_force_per_currency(page):
    p, data = page
    states = {a["title"]: a["value"]["in_portfolio"] for a in data["agreements"]}
    assert states["הסכם שקלי"] and states["הסכם דולרי"]
    assert not states["הסכם אירו שחלף"] and not states["טיוטה שקלית"]
    f = footer(p["repo"])
    assert "384 אלף ₪" in f and "186 אלף $" in f
    assert "240" not in f and "€" not in f and "777" not in f
    assert "570" not in f and "570 אלף" not in p["repo"]


def test_hero_and_kpi_are_built_from_buckets_without_warning_glyph(page):
    p, _ = page
    assert p["buckets"] == {"ours": 2, "theirs": 1, "outcome": 1, "old": 1, "role": 1}
    hero = re.search(r"<h2>(.*?)</h2>", p["dash"]).group(1)
    assert "2 באיחור, פעולה שלנו" in hero and "1 באיחור, פעולה של הצד שכנגד" in hero
    # מספר אחד ביחיד: "1 ממתין", "החלטה אחת"
    assert "2 ממתינים לאישור תוצאה" in hero and "1 ממתין לאישור צד החברה" in hero
    assert "החלטות ב-30 הימים הקרובים" in hero or "החלטה אחת ב-30 הימים הקרובים" in hero
    assert not re.search(r"(^|[^\d])1 (הסכמים|החלטות|מועדים|ממתינים)", hero)
    assert "⚠" not in p["dash"]
    assert "מתוך 6 מועדים שחלפו ולא נסגרו" in p["dash"]


def test_tasks_nav_count_equals_rows_on_the_screen(page):
    p, _ = page
    assert p["n_tasks"] == p["tasks"].count('class="row"') and p["n_tasks"] > 0
    for group in ("באיחור", "באיחור, פעולה של הצד שכנגד", "ממתין לאישור תוצאה", "ממתין לאישור צד החברה"):
        assert "<h3>%s <span" % group in p["tasks"], group


def test_superseded_event_never_in_tasks_and_not_live(page):
    p, _ = page
    assert "דוח שהוחלף בתיקון" not in p["tasks"] and "דוח שהוחלף בתיקון" not in p["renew"]
    assert p["live_sup"] == [False]
    ours = p["tasks"].split("<h3>באיחור <span")[1].split("</h3>")[1].split("<h3>")[0]
    assert "דוח שלנו שחלף" in ours and "דוח הצד שכנגד שחלף" not in ours and "דוח שהוחלף" not in ours


def test_tasks_title_and_nav_label_follow_scope(page):
    p, _ = page
    assert p["title_me"] == "המשימות שלי" and ">המשימות שלי<" in p["nav_me"]
    assert ">משימות<" in p["nav_team"] and "המשימות שלי" not in p["nav_team"]


def test_role_pending_in_chart_with_hatched_segment_and_legend(page):
    p, _ = page
    assert "repeating-linear-gradient" in open(TEMPLATE, encoding="utf-8").read()
    assert 'class="seg2 role"' in p["dash"] and "ממתין לאישור צד החברה" in p["dash"]


def test_obligations_have_third_card_for_both_sides(page):
    p, _ = page
    assert "התחייבויות של שני הצדדים" in p["obl"] and "אישור ביטוח משותף" in p["obl"]
    counts = [int(x) for x in re.findall(r'<h3>[^<]* <span class="n">(\d+)</span>', p["obl"])]
    assert len(counts) == 3 and sum(counts) == p["obl"].count('class="row"')


def kpi_tile(dash):
    return dash.split("בטוחות וביטוחים ב-90 יום")[0].rsplit('<div class="kpi"', 1)[1] + "בטוחות וביטוחים ב-90 יום" +         dash.split("בטוחות וביטוחים ב-90 יום")[1].split("</div></div>")[0]


def test_guarantee_kpi_keeps_real_deadlines_and_adds_message_without_expiry(page):
    p, _ = page
    msg = "לבטוחות לא נמצא תאריך פקיעה"
    with_event = kpi_tile(p["dash"])
    assert '<div class="v">1</div>' in with_event and msg in with_event
    without = kpi_tile(p["dash_no_sec"])
    assert '<div class="v">0</div>' in without and msg in without
    for t in (with_event, without):
        assert chr(0x2014) not in t and chr(0x2013) not in t


def test_tasks_count_equals_rows_also_in_scope_me(page):
    p, data = page
    n, html = p["tasks_me"]
    assert n == html.count('class="row"') and n > 0
    assert "דוח שחלף וממתין לתפקיד" in html


def test_chart_month_total_includes_role_pending_events(page):
    p, data = page
    totals = [int(x) if x else 0 for x in re.findall(r"<span>(\d*)</span>", p["dash"].split('<div class="tlv">')[1].split("</div>")[0])]
    expect = [0] * 12
    for e in data["events"]:
        if e["state"] == "upcoming" and e["act_by"] and not e.get("superseded_by"):
            d = max(dt.date.fromisoformat(e["act_by"]), TODAY)
            idx = (d.year - TODAY.year) * 12 + d.month - TODAY.month
            if 0 <= idx < 12:
                expect[idx] += 1
    assert totals == expect
    role = [e for e in data["events"] if e["role_pending"] and e["state"] == "upcoming" and e["act_by"]]
    assert role and sum(expect) > sum(1 for e in data["events"] if e["state"] == "upcoming" and e["act_by"] and not e["role_pending"])


def test_repo_late_filter_uses_only_our_overdue_actions(page):
    p, _ = page
    late = p["repo_late"]
    assert "הסכם שקלי" in late and "הסכם אירו שחלף" in late
    assert "הסכם תפקיד" not in late and "הסכם דולרי" not in late


def test_cps_distinguishes_no_value_from_no_agreement_in_force(page):
    p, _ = page
    assert "אין הסכם בתוקף עם שווי" in p["cps"] and "לא נקוב" in p["cps"]
    row = lambda name: p["cps"].split('<b><bdi dir="auto">' + name)[1].split("</tr>")[0]
    assert "אין הסכם בתוקף עם שווי" in row("אירו GmbH") and "לא נקוב" in row("תפקיד")


def test_guarantee_without_expiry_gets_no_warning_class(page):
    p, _ = page
    assert "c-warn" not in p["money"] and "c-crit" not in p["money"]


def test_card_shows_own_value_per_currency_with_basis_and_uncounted(page):
    p, data = page
    ils = next(a for a in data["agreements"] if a["title"] == "הסכם שקלי")
    assert "384 אלף ₪" in p["card_ils"] and ils["value"]["basis"] in p["card_ils"]
    assert "777 אלף ₪" in p["card_draft"]


def test_counterparties_screen_and_chart_use_currency_per_row(page):
    p, _ = page
    assert "384 אלף ₪" in p["cps"] and "186 אלף $" in p["cps"]
    assert "570" not in p["cps"] and "570" not in p["dash"]
    assert "186 אלף $" in p["dash"] and "240 אלף" not in p["dash"] and "240 אלף" not in p["cps"]


def test_no_nis_helper_remains_and_no_dashes():
    with open(TEMPLATE, encoding="utf-8") as fh:
        text = fh.read()
    assert not re.search(r"\bnis\(", text) and "const nis" not in text
    assert chr(0x2013) not in text and chr(0x2014) not in text


# ---------- משימה 4: מאגר עם תאריכים ודין, סינון, ייצוא וכרטיס ----------
REPO_HEAD = ["מספר", "הסכם", "סוג", "צד שכנגד", "מצב", "נחתם", "תחילה", "סיום התקופה הנוכחית", "תקופה", "דין", "שווי שנתי",
             "מועד היעד הבא"]
NOTE = "מחושב: 31.3.2026 ועוד חידוש אחד של 12 חודשים לפי סעיף 4; לאמת שההסכם התחדש"
NAMES = ("אחד", "שני", "שלישי", "רביעי", "חמישי", "טיוטה")


def dataset4():
    rows = []

    def add(i, title, **kw):
        sha, path = str(i) * 64, "x/%s - חתום.docx" % title
        rows.append(({"path": path, "sha256": sha, "status": "new", "abs": None, "duplicate_of": None},
                     make_extract(sha, path, title=title, coverage=COV, events=[], **kw)))
    add(1, "אחד", counterparty=cp("אחד בע\"מ"), commercials=com(32000, "₪ לחודש", "חודשי", "ILS"), currency="ILS")
    add(2, "שני", counterparty=cp("שני בע\"מ"), commercials=com(15500, "$ לחודש", "חודשי", "USD"), currency="USD")
    add(3, "שלישי", counterparty=cp("שלישי בע\"מ"), commercials=[])
    add(4, "רביעי", counterparty=cp("רביעי בע\"מ"), commercials=[])
    add(5, "חמישי", counterparty=cp("חמישי בע\"מ"), commercials=[], our_role={"value": "לקוח", "source": "suggested"})
    sha = "7" * 64
    rows.append(({"path": "x/טיוטה", "sha256": sha, "status": "new", "abs": None, "duplicate_of": None},
                 make_extract(sha, "x/טיוטה", title="טיוטה", doc_kind="draft", counterparty=cp("טיוטה בע\"מ"),
                              commercials=[], coverage=COV, events=[],
                              dates={"signed": None, "start": None, "end": None})))
    data = assemble.assemble({"files": [r[0] for r in rows]}, {r[1]["sha256"]: r[1] for r in rows}, "חברה", TODAY,
                             home_law="ישראל")
    by = {a["title"]: a for a in data["agreements"]}
    one = by["אחד"]
    one["dates"].update(signed="2024-03-01", start="2024-04-01", end="2026-03-31", current_end="2027-03-31",
                        current_end_basis={"kind": "auto_renewal", "note": NOTE},
                        end_basis={"kind": "contract", "note": ""})
    one.update(law_class="home", governing_law="דין ישראלי", counterparty_notice_address="הרצל 1, תל אביב",
               notes=[{"text": "ההערה הראשונה מהמסמך", "file": "x/אחד - חתום.docx"}],
               key_clauses_not_found=["liability_cap"])
    one["field_status"]["end_date"] = "extracted"
    two = by["שני"]
    two["dates"].update(signed="2025-06-01", start="2025-06-01", end="2027-12-31", original_end="2026-12-31",
                        end_source="doc-2", current_end="2027-12-31",
                        current_end_basis={"kind": "same_as_end", "note": ""},
                        end_basis={"kind": "amendment", "note": "לפי התיקון להסכם מיום 1.1.2026"})
    two.update(law_class="foreign", governing_law="דין אנגליה")
    three = by["שלישי"]
    three["dates"].update(signed="2023-01-10", start="2023-01-10", end=None, current_end=None,
                          current_end_basis={"kind": None, "note": ""}, end_basis={"kind": None, "note": ""})
    three.update(law_class="unset", governing_law=None)
    three["field_status"]["end_date"] = "not_expected"
    four = by["רביעי"]
    four["dates"].update(signed="2022-05-05", start=None, end=None, current_end=None,
                         current_end_basis={"kind": None, "note": ""}, end_basis={"kind": None, "note": ""})
    four.update(law_class="foreign", governing_law="דין ניו יורק")
    four["field_status"]["end_date"] = "missing"
    five = by["חמישי"]
    five["dates"].update(signed="2025-12-01", start="2025-12-01", end="2026-11-30", current_end="2026-11-30",
                         current_end_basis={"kind": "same_as_end", "note": ""},
                         end_basis={"kind": "deadline", "note": "לפי המועד: הודעת אי-חידוש"})
    five.update(law_class="home", governing_law="דין ישראלי")
    five["field_status"]["end_date"] = "derived"
    # הסכם שנשמר מהרצה ישנה: בלי השדות החדשים
    for k in ("law_class", "counterparty_notice_address", "notes", "key_clauses_not_found"):
        by["טיוטה"].pop(k, None)
    for k in ("current_end", "end_basis", "current_end_basis"):
        by["טיוטה"]["dates"].pop(k, None)
    data["key_clause_labels"] = dict(data.get("key_clause_labels") or {}, liability_cap="תקרת אחריות")
    return data


@pytest.fixture(scope="module")
def page4(tmp_path_factory):
    if not shutil.which("node"):
        pytest.skip("node אינו מותקן")
    data = dataset4()
    d = tmp_path_factory.mktemp("stage_a4")
    data_path, out, ex_path = str(d / "data.json"), str(d / "out.html"), str(d / "exprs.json")
    with open(data_path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False)
    build.build(data_path, TEMPLATE, out)
    ids = {a["title"]: a["id"] for a in data["agreements"]}
    card = "(openAg(%r, %r), document.querySelector('#drawer').innerHTML)"

    def with_rf(patch):
        return ("(Object.assign(rf, %s), [V.repo()].map(h => (Object.assign(rf, {from: '', to: '', law: '', sort: 'num'}), h))[0])"
                % patch)
    exprs = {
        "repo": "V.repo()",
        "signed_2024_2025": with_rf("{from: '2024-01-01', to: '2025-12-31'}"),
        "signed_from": with_rf("{from: '2025-06-01'}"),
        "signed_to": with_rf("{to: '2023-12-31'}"),
        "law_foreign": with_rf("{law: 'foreign'}"), "law_home": with_rf("{law: 'home'}"),
        "law_unset": with_rf("{law: 'unset'}"),
        "sort_signed": with_rf("{sort: 'signed'}"), "sort_end": with_rf("{sort: 'end'}"),
        "rows": "repoRows()", "n_dates": "counts().dates", "dates_default": "(df.state = 'open', df.win = 'all', df.cons = '', V.dates())",
        "law_label_other": "(D.meta.home_law = 'צרפת', [V.repo()].map(h => (D.meta.home_law = 'ישראל', h))[0])",
        "law_label_none": "(delete D.meta.home_law, [V.repo()].map(h => (D.meta.home_law = 'ישראל', h))[0])",
        "card_one": card % (ids["אחד"], "sum"), "card_two": card % (ids["שני"], "sum"),
        "card_three": card % (ids["שלישי"], "sum"), "card_four": card % (ids["רביעי"], "sum"),
        "card_five": card % (ids["חמישי"], "sum"), "card_draft": card % (ids["טיוטה"], "sum"),
        "keys_one": card % (ids["אחד"], "keys"), "keys_two": card % (ids["שני"], "keys"),
        "stage": "A[%r].handling_stage" % ids["טיוטה"],
        "card_orphan": "(() => { const a = A[%r], s = a.signature; a.signature = 'unknown'; openAg(a.id, 'sum'); const h = document.querySelector('#drawer').innerHTML; a.signature = s; return h; })()" % ids["טיוטה"],
        "rows_null": "(() => { const a = A[%r], v = a.value.annual_by_currency; a.value.annual_by_currency = {...v, GBP: null}; const r = repoRows(); a.value.annual_by_currency = v; return r; })()" % ids["אחד"],
    }
    with open(ex_path, "w", encoding="utf-8") as fh:
        json.dump(exprs, fh, ensure_ascii=False)
    r = subprocess.run(["node", HARNESS, out, ex_path], capture_output=True, text=True, encoding="utf-8")
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout), data


def heads(html):
    return re.findall(r"<th(?:\s[^>]*)?>(.*?)</th>", html)


def titles(html):
    return [n for n in re.findall(r'<td><b><bdi dir="auto">([^<]*)</bdi></b>', html) if n in NAMES]


def row_of(html, title):
    return html.split('<td><b><bdi dir="auto">%s</bdi></b>' % title)[1].split("</tr>")[0]


def part(card, label, next_label):
    return card.split("<div>%s</div>" % label)[1].split("<div>%s</div>" % next_label)[0]


def test_repo_columns_in_order_without_owner_and_company_side(page4):
    p, _ = page4
    assert heads(p["repo"]) == REPO_HEAD
    assert "עו\"ד אחראי" not in p["repo"] and "<th>צד החברה</th>" not in p["repo"]


def test_repo_company_side_pending_stays_visible_next_to_title(page4):
    p, data = page4
    pending = [a["title"] for a in data["agreements"] if not a["our_role"]["confirmed"]]
    assert pending
    for t in pending:
        assert "ממתין לאישור" in row_of(p["repo"], t).split("</td>")[0]


def test_repo_date_cells_do_not_wrap(page4):
    p, _ = page4
    r = row_of(p["repo"], "אחד")
    assert re.search(r'<td[^>]*white-space:nowrap[^>]*>1\.3\.2024</td>', r), r
    assert re.search(r'<td[^>]*white-space:nowrap[^>]*>1\.4\.2024</td>', r)
    assert re.search(r'white-space:nowrap[^>]*>31\.3\.2027', r)


def test_current_end_cell_auto_renewal_shows_derived_tag_original_and_formula_title(page4):
    p, _ = page4
    r = row_of(p["repo"], "אחד")
    # תווית המסך שייכת לתבנית: "נגזר" כיום, "מחושב" לפי מדריך הקול. הבדיקה אינה מחייבת את הנוסח הישן
    assert "31.3.2027" in r and re.search(r'class="tag" title="%s">(?:נגזר|מחושב)<' % re.escape(NOTE), r)
    assert re.search(r'class="xs mut"[^>]*>סיום מקורי 31\.3\.2026</div>', r)


def test_current_end_cell_deadline_missing_and_not_expected(page4):
    p, _ = page4
    five = row_of(p["repo"], "חמישי")
    assert "30.11.2026" in five and 'title="לפי המועד: הודעת אי-חידוש">ממועד' in five and "נגזר" not in five
    assert "לא נקבע (מקובל בסוג זה)" in row_of(p["repo"], "שלישי")
    assert 'class="tag w">להשלים' in row_of(p["repo"], "רביעי")
    two = row_of(p["repo"], "שני")
    assert "31.12.2027" in two and "נגזר" not in two and "סיום מקורי" not in two


def test_law_column_shows_governing_law_or_not_set(page4):
    p, _ = page4
    assert "דין אנגליה" in row_of(p["repo"], "שני") and "דין ישראלי" in row_of(p["repo"], "אחד")
    assert 'class="mut">לא נקבע</span>' in row_of(p["repo"], "שלישי")


def test_filter_controls_signed_range_law_and_sort(page4):
    p, _ = page4
    assert p["repo"].count('type="date"') == 2
    assert "נחתם מתאריך" in p["repo"] and "עד תאריך" in p["repo"]
    assert 'data-rf="from"' in p["repo"] and 'data-rf="to"' in p["repo"]
    for t in ("כל הדינים", "דין ישראל", "דין זר", "לא נקבע", "לפי מספר", "לפי תאריך חתימה", "לפי סיום התקופה הנוכחית"):
        assert t in p["repo"], t
    assert 'data-rf="law"' in p["repo"] and 'data-rf="sort"' in p["repo"]


def test_filter_by_signed_range_uses_dates_signed(page4):
    p, _ = page4
    assert sorted(titles(p["signed_2024_2025"])) == sorted(["אחד", "שני", "חמישי"])
    assert sorted(titles(p["signed_from"])) == sorted(["שני", "חמישי"])
    assert sorted(titles(p["signed_to"])) == sorted(["שלישי", "רביעי"])
    assert p["signed_2024_2025"].count('class="ck ag"') == 3 and "3 הסכמים" in p["signed_2024_2025"]
    assert len(titles(p["repo"])) == 6


def test_filter_by_law_class(page4):
    p, _ = page4
    assert sorted(titles(p["law_foreign"])) == sorted(["רביעי", "שני"])
    assert sorted(titles(p["law_home"])) == sorted(["אחד", "חמישי"])
    assert sorted(titles(p["law_unset"])) == sorted(["טיוטה", "שלישי"])


def test_sort_by_number_signed_and_current_end(page4):
    p, _ = page4
    assert titles(p["repo"]) == ["אחד", "שני", "שלישי", "רביעי", "חמישי", "טיוטה"]
    assert titles(p["sort_signed"]) == ["חמישי", "שני", "אחד", "שלישי", "רביעי", "טיוטה"]
    assert titles(p["sort_end"]) == ["חמישי", "אחד", "שני", "שלישי", "רביעי", "טיוטה"]


def test_repo_rows_header_and_one_value_column_per_currency(page4):
    p, _ = page4
    head, *rows = p["rows"]
    assert head == ["מספר", "הסכם", "סוג", "צד החברה", "צד שכנגד", "מצב", "נחתם", "תחילה", "סיום", "בסיס הסיום",
                    "סיום התקופה הנוכחית", "בסיס סיום התקופה הנוכחית", "דין", "שווי שנתי ILS", "שווי שנתי USD",
                    "בסיס השווי", "כתובת להודעות", "סוג תקופה", "מנגנון חידוש", "סיום התקופה המרבית", "שיפוט", "חותמים", "נכון ליום"]
    assert len(rows) == 6 and all(len(r) == len(head) for r in rows)
    one = next(r for r in rows if r[1] == "אחד")
    assert one[6:13] == ["1.3.2024", "1.4.2024", "31.3.2026", "", "31.3.2027", NOTE, "דין ישראלי"]
    assert one[13] == 384000 and one[14] in ("", None) and one[15] == "מחושב מהתמורה שבהסכם"
    assert one[16] == "הרצל 1, תל אביב"
    two = next(r for r in rows if r[1] == "שני")
    assert two[8] == "31.12.2027" and two[9] == "לפי התיקון להסכם מיום 1.1.2026" and two[10] == "31.12.2027"
    assert two[14] == 186000 and two[13] in ("", None)
    three = next(r for r in rows if r[1] == "שלישי")
    assert three[8] == "" and three[9] == "" and three[10] == "" and three[11] == "" and three[12] == "לא נקבע"
    assert three[15] == "" and three[16] == ""


def test_card_dates_split_into_three_rows_with_visible_formula(page4):
    p, _ = page4
    c = p["card_one"]
    for label in ("<div>תאריכים</div>", "<div>סיום</div>", "<div>סיום התקופה הנוכחית</div>"):
        assert label in c, label
    assert "חתימה 1.3.2024" in c and "תחילה 1.4.2024" in c
    cur = c.split("<div>סיום התקופה הנוכחית</div>")[1].split("<div>שווי</div>")[0]
    assert "31.3.2027" in cur and re.search(r'class="tag">(?:נגזר|מחושב)<', cur) and 'class="xs mut">%s' % NOTE in cur
    end = part(c, "סיום", "סיום התקופה הנוכחית")
    assert "31.3.2026" in end and NOTE not in end


def test_card_end_row_shows_amendment_basis_and_original(page4):
    p, _ = page4
    end = part(p["card_two"], "סיום", "סיום התקופה הנוכחית")
    assert "31.12.2027" in end and "לפי התיקון להסכם" in end and "31.12.2026" in end
    assert "לפי התיקון להסכם מיום 1.1.2026" in end
    five = part(p["card_five"], "סיום", "סיום התקופה הנוכחית")
    assert "ממועד" in five and "לפי המועד: הודעת אי-חידוש" in five


def test_card_end_rows_when_not_expected_or_missing(page4):
    p, _ = page4
    assert part(p["card_three"], "סיום", "סיום התקופה הנוכחית").count("לא נקבע (מקובל בסוג זה)") == 1
    assert "לא נקבע (מקובל בסוג זה)" in p["card_three"].split("<div>סיום התקופה הנוכחית</div>")[1].split("<div>שווי</div>")[0]
    assert "להשלים" in part(p["card_four"], "סיום", "סיום התקופה הנוכחית")


def test_card_shows_notice_address_and_document_notes_with_file(page4):
    p, _ = page4
    c = p["card_one"]
    assert "<div>כתובת להודעות</div>" in c and "הרצל 1, תל אביב" in c
    assert "<div>הערות מהמסמך</div>" in c and "ההערה הראשונה מהמסמך" in c
    assert '<bdi class="fnm" dir="auto">אחד - חתום' in c
    assert "<div>כתובת להודעות</div>" not in p["card_two"] and "<div>הערות מהמסמך</div>" not in p["card_two"]


def test_keys_tab_lists_clauses_checked_and_not_found(page4):
    p, _ = page4
    assert "נבדק ולא נמצא: תקרת אחריות" in p["keys_one"]
    assert "נבדק ולא נמצא: " not in p["keys_two"]


def test_draft_card_says_last_file_and_not_yet_signed(page4):
    p, _ = page4
    assert p["stage"]
    c = p["card_draft"]
    assert "<div>קובץ אחרון</div>" in c and "מקור חתום" not in c
    assert "חתימה: טרם נחתם" in c
    assert "<div>מקור חתום</div>" in p["card_one"] and "קובץ אחרון" not in p["card_one"]


def test_old_agreements_without_new_fields_render_with_defaults(page4):
    p, _ = page4
    assert "טיוטה" in titles(p["repo"]) and "<div>כתובת להודעות</div>" not in p["card_draft"]
    assert "<div>הערות מהמסמך</div>" not in p["card_draft"] and "נבדק ולא נמצא: " not in p["card_draft"]


def test_orphan_draft_signature_stays_unknown_and_real_draft_not_signed(page4):
    p, data = page4
    # טיוטה אמיתית: "טרם נחתם" מהערך not_signed; יתום (חתימה לא ידועה) אינו נדרס
    assert "חתימה: טרם נחתם" in p["card_draft"]
    assert "חתימה: לא ידוע" in p["card_orphan"] and "חתימה: טרם נחתם" not in p["card_orphan"]
    assert "<div>קובץ אחרון</div>" in p["card_orphan"]


def test_repo_rows_currency_columns_ignore_null_values(page4):
    p, _ = page4
    assert p["rows_null"][0].count("שווי שנתי GBP") == 0 and "שווי שנתי ILS" in p["rows_null"][0]


def test_date_inputs_have_color_scheme_for_both_themes():
    text = open(TEMPLATE, encoding="utf-8").read()
    assert ".ctl input[type=date]{color-scheme:light}" in text
    assert text.count("input[type=date]{color-scheme:dark}") == 2


# ---------- משימה 5: פגמי תצוגה ----------
@pytest.fixture(scope="module")
def page5(tmp_path_factory):
    if not shutil.which("node"):
        pytest.skip("node אינו מותקן")
    data = dataset()
    d = tmp_path_factory.mktemp("stage_a5")
    data_path, out, ex_path = str(d / "data.json"), str(d / "out.html"), str(d / "exprs.json")
    with open(data_path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False)
    build.build(data_path, TEMPLATE, out)
    ids = {a["title"]: a["id"] for a in data["agreements"]}
    fake = "{target: {closest: () => (%s)}, clientX: 300, clientY: 200}"
    ref_t = "{dataset: {ref: String(D.footnotes[0].n)}, classList: {contains: () => false}, id: ''}"
    show = "showQuote(D.footnotes[0].n, 300, 200)"
    qs = "document.querySelector('#qpop')"
    card = "(openAg(%r, %r), document.querySelector('#drawer').innerHTML)"
    exprs = {
        "fnm_date": 'fnm("הסכם 10.04.2022.docx")',
        "fnm_mixed": 'fnm("הסכם שירות Master_Agreement-v2 final.pdf")',
        "fnm_heb": 'fnm("חולץ.docx")',
        "fnm_plain": 'fnm("ללא סיומת")',
        "repo": "V.repo()", "tasks": "V.tasks()", "dates": "V.dates()", "settings": "V.settings()",
        "nav_team": "(scope = 'team', nav(), document.querySelector('#nav').innerHTML)",
        "card_ils": card % (ids["הסכם שקלי"], "sum"),
        "card_dates": card % (ids["הסכם שקלי"], "dates"),
        "card_docs": card % (ids["הסכם שקלי"], "docs"),
        "n_fn": "D.footnotes.length",
        "refs_html": "refs([D.footnotes[0].n])",
        "pop_html": "(%s, %s.innerHTML)" % (show, qs),
        "pop_open": "(%s, %s.style.display)" % (show, qs),
        "pop_pos": "(%s, [%s.style.left, %s.style.top])" % (show, qs, qs),
        "pop_fn": "FN[D.footnotes[0].n]",
        "pop_closed_by_btn": "(%s, onDocClick(%s), %s.style.display)"
                             % (show, fake % "{dataset: {}, classList: {contains: () => false}, id: 'qclose'}", qs),
        "pop_closed_by_esc": "(%s, onKey({key: 'Escape'}), %s.style.display)" % (show, qs),
        "pop_closed_by_outside": "(%s, onDocClick({target: {closest: () => null}, clientX: 1, clientY: 1}), %s.style.display)" % (show, qs),
        "pop_ref_click": "(cur = 'dash', %s.style.display = 'none', onDocClick(%s), [cur, %s.style.display])" % (qs, fake % ref_t, qs),
        "pop_clamp_low": "(innerHeight = 800, %s.offsetHeight = 300, %s.offsetWidth = 380, showQuote(D.footnotes[0].n, 600, 790), [%s.style.top, %s.style.left])" % (qs, qs, qs, qs),
        "pop_clamp_high": "(showQuote(D.footnotes[0].n, 5, 20), [%s.style.top, %s.style.left])" % (qs, qs),
        "pop_clamp_right": "(showQuote(D.footnotes[0].n, 1195, 300), [%s.style.top, %s.style.left])" % (qs, qs),
        "pop_clamp_tall": "(%s.offsetHeight = 2000, showQuote(D.footnotes[0].n, 600, 400), %s.style.top)" % (qs, qs),
        "repo_long": "(() => { const a = Object.values(A)[0], t = a.title, c = a.counterparty; a.title = 'x'.repeat(40); a.counterparty = 'y'.repeat(31) + ' z'; const h = V.repo(); a.title = t; a.counterparty = c; return h; })()",
        "cites": "V.cites()", "reports": "V.reports()",
        "pop_other_key": "(%s, onKey({key: 'a'}), %s.style.display)" % (show, qs),
    }
    with open(ex_path, "w", encoding="utf-8") as fh:
        json.dump(exprs, fh, ensure_ascii=False)
    r = subprocess.run(["node", HARNESS, out, ex_path], capture_output=True, text=True, encoding="utf-8")
    assert r.returncode == 0, r.stderr
    with open(out, encoding="utf-8") as fh:
        built = fh.read()
    return json.loads(r.stdout), data, built


def css_rules(text):
    style = text.split("<style>")[1].split("</style>")[0]
    return re.findall(r"([^{}]+)\{([^{}]*)\}", style)


def test_overflow_wrap_anywhere_only_on_wrap_class_cells(page5):
    _, _, built = page5
    assert ".tw td{overflow-wrap:anywhere}" not in built
    anywhere = [sel.strip() for sel, body in css_rules(built) if "overflow-wrap:anywhere" in body]
    assert anywhere and all(".wrap" in s for s in anywhere), anywhere
    th = [b for s, b in css_rules(built) if s.strip() == "th"]
    assert th and "anywhere" not in th[0]
    assert not re.search(r"\.dt td,\.dt th\{[^}]*anywhere", built)


def test_type_column_does_not_break_letter_by_letter(page5):
    p, _, built = page5
    nr = [b for s, b in css_rules(built) if ".nowrapish" in s]
    assert nr and all("word-break:normal" in b and "overflow-wrap:normal" in b and "min-width:7em" in b for b in nr)
    assert '<th class="nowrapish">סוג</th>' in p["repo"]
    cells = re.findall(r'<td class="nowrapish">[^<]*</td>', p["repo"])
    assert cells and len(cells) == p["repo"].count('<tr class="ck ag"')
    assert 'sm wrap">' in p["card_docs"] and 'class="wrap"' not in p["repo"]


def test_fnm_isolates_whole_trailing_latin_run_with_extension(page5):
    p, _, _ = page5
    assert '<bdi dir="ltr">10.04.2022.docx</bdi>' in p["fnm_date"]
    assert p["fnm_date"].startswith('<bdi class="fnm" dir="auto">הסכם ')
    assert '<bdi dir="ltr">Master_Agreement-v2 final.pdf</bdi>' in p["fnm_mixed"]
    assert p["fnm_heb"] == '<bdi class="fnm" dir="auto">חולץ<bdi dir="ltr">.docx</bdi></bdi>'
    assert p["fnm_plain"] == '<bdi class="fnm" dir="auto">ללא סיומת</bdi>'


def test_tasks_when_column_is_wide_and_state_label_sits_under_the_date(page5):
    p, _, built = page5
    when = [b for s, b in css_rules(built) if s.strip() == ".when"]
    assert when and "min-width:118px" in when[0] and "white-space:normal" in when[0]
    small = [b for s, b in css_rules(built) if s.strip() == ".when small"]
    assert small and "display:block" in small[0]
    row = [b for s, b in css_rules(built) if s.strip() == ".row"]
    assert row and "grid-template-columns:118px" in row[0]
    assert "חלף, ממתין לאישור תוצאה</small>" in p["tasks"]
    assert re.search(r'<div class="when [^"]*"><span class="dn">[^<]+</span><small>', p["tasks"])


def test_dates_never_break_inside_a_year(page5):
    p, _, built = page5
    dn = [b for s, b in css_rules(built) if s.strip() == ".dn"]
    assert dn and "white-space:nowrap" in dn[0]
    assert re.search(r'<td><b><span class="dn">\d+\.\d+\.\d{4}</span></b>', p["dates"])
    assert re.search(r'המועד בהסכם <span class="dn">\d+\.\d+\.\d{4}</span>', p["dates"])
    assert re.search(r'<span class="dn">\d+\.\d+\.\d{4}</span>', p["card_dates"])


def test_reference_click_opens_floating_panel_and_keeps_context(page5):
    p, _, built = page5
    assert p["n_fn"] > 0
    assert '<div id="qpop"' in built and 'style="display:none"' in built.split('<div id="qpop"')[1][:80]
    f, h = p["pop_fn"], p["pop_html"]
    assert f["clause"] in h and f["quote"] in h and 'id="qclose"' in h and "<bdi" in h
    assert p["pop_open"] == "block"
    assert re.match(r"\d+px", p["pop_pos"][0]) and re.match(r"\d+px", p["pop_pos"][1])
    assert p["pop_ref_click"] == ["dash", "block"]
    assert 'data-ref="' in p["refs_html"] and 'data-ref="' in p["card_dates"] and 'data-ref="' in p["dates"]
    handler = built.split("function onDocClick")[1].split("\ndocument.addEventListener")[0]
    ref_branch = handler.split("t.dataset.ref")[1].split("\n")[0]
    assert "closeAg()" not in ref_branch and 'go("cites")' not in ref_branch
    assert 'data-v="cites"' in p["nav_team"] and "ציטוטים" in p["nav_team"]


def test_quote_panel_closes_on_button_escape_and_outside_click(page5):
    p, _, built = page5
    assert p["pop_closed_by_btn"] == "none"
    assert p["pop_closed_by_esc"] == "none"
    assert p["pop_closed_by_outside"] == "none"
    assert p["pop_other_key"] == "block"
    rules = {s.strip(): b for s, b in css_rules(built)}
    q = rules["#qpop"]
    assert "var(--surface)" in q and "var(--line" in q and "var(--shl)" in q and "position:fixed" in q
    assert "closeAg" not in built.split("function showQuote")[1].split("\n}\n")[0]


REMOVED = ["יתמלא אחרי חיבור המייל", "בגרסה המלאה", "ייחלץ בהרצה הבאה", "ייחלצו בהרצה הבאה", "יוצג כעץ",
           "קובץ ICS זמין", "הוספת שדה", "בהרצה הבאה", "תיחלץ", "⚠"]


def test_built_page_has_no_developer_notes_promises_or_warning_glyph(page5):
    _, _, built = page5
    for s in REMOVED:
        assert s not in built, s
    assert "עד הפעלת המסד המשותף" not in built and "בגרסה זו" not in built


def test_connections_card_states_current_limits_as_facts(page5):
    p, _, _ = page5
    s = p["settings"]
    for label, val in (("מייל", "לא חובר"), ("יומן", "לא חובר"), ("סריקה מתוזמנת", "כבויה")):
        assert "<div>%s</div><div><span class=\"tag\">%s</span></div>" % (label, val) in s
    assert "מייל: לא חובר" not in s
    assert "<button" not in s


def test_expiring_right_label_is_displayed_as_will_expire(page5):
    p, data, _ = page5
    c = p["card_ils"]
    assert "זכות שתפקע: " in c and "זכות שפוקעת" not in c
    assert any(x["category"] == "זכות שפוקעת" for a in data["agreements"] for x in a["coverage"])


def test_drawer_has_no_horizontal_scroll_at_wide_screens(page5):
    _, _, built = page5
    rules = {s.strip(): b for s, b in css_rules(built)}
    assert "#drawer" in rules
    assert "max-width:min(860px,100vw)" in rules["#drawer"] and "overflow-x:hidden" in rules["#drawer"]
    assert "grid-template-columns:180px minmax(0,1fr)" in rules[".dl"]
    assert "overflow-wrap" in rules[".dl>div"] or "min-width:0" in rules[".dl>div"]


def test_mobile_row_first_column_matches_when_min_width(page5):
    _, _, built = page5
    media = re.search(r"@media \(max-width:860px\)\{(.*)\}", built[built.index("/* AREO-KIT:END */"):]).group(1)
    assert ".row{grid-template-columns:118px minmax(0,1fr)}" in media
    assert "80px" not in media


def test_quote_panel_clamps_with_measured_size_inside_viewport(page5):
    p, _, built = page5
    # פאנל בגובה 300 בחלון בגובה 800, לחיצה בשורה 790: מעל הלחיצה ובתוך החלון (top <= 800 - 300 - 8 = 492)
    assert p["pop_clamp_low"] == ["472px", "410px"]
    assert p["pop_clamp_high"][0] == "38px" and p["pop_clamp_high"][1] == "8px"
    assert p["pop_clamp_right"][1] == "812px"
    assert p["pop_clamp_tall"] == "8px"
    body = built.split("function showQuote")[1].split("\n}\n")[0]
    assert "offsetHeight" in body and "documentElement.clientWidth" in body
    q = [b for s, b in css_rules(built) if s.strip() == "#qpop"][0]
    assert "max-height:calc(100vh - 16px)" in q and "overflow:auto" in q


def test_wrap_class_only_for_long_unbroken_tokens_in_repo(page5):
    p, _, _ = page5
    assert '<td class="wrap"><b><bdi dir="auto">' + "x" * 40 in p["repo_long"]
    assert '<td class="wrap"><bdi dir="auto">' + "y" * 31 in p["repo_long"]
    assert 'class="wrap"' not in p["repo"]
    assert 'xs mut wrap">' in p["cites"]


def test_reports_screen_uses_factual_wording(page5):
    p, _, built = page5
    # מדריך הקול: בלי סוגי קבצים בטקסט ללקוח. הבדיקה אינה מחייבת "כקובץ Word"
    assert "מפיקים בצ'אט עם Claude" in p["reports"]
    assert "מופק כ-Word בעברית בבקשה בצ'אט" not in built


# ---------- תיקוני סקירה סופית ----------
def test_nav_dates_count_equals_default_screen_count(page4, page):
    for p, _ in (page4, page):
        n = p["n_dates"]
        assert n == p["dates_default"].count("<tr><td><b>") and n == int(re.search(r"(\d+) מועדים", p["dates_default"]).group(1))


def test_money_rounds_at_the_million_threshold(page):
    p, _ = page
    assert p["m_999600"] == "1 מיליון ₪" and p["m_999400"] == "999 אלף ₪" and p["m_1e6"] == "1 מיליון ₪"
    assert "1000 אלף" not in p["m_999600"] + p["m_999500"] and p["m_999500"] == "1 מיליון ₪"


def test_home_law_label_follows_meta(page4):
    p, data = page4
    assert data["meta"]["home_law"] == "ישראל"
    assert "דין ישראל</option>" in p["repo"]
    assert "דין ישראל</option>" not in p["law_label_other"] and "דין צרפת</option>" in p["law_label_other"]
    assert "דין הבית</option>" in p["law_label_none"]


def test_amendment_end_row_shows_original_end_once(page4):
    p, _ = page4
    end = part(p["card_two"], "סיום", "סיום התקופה הנוכחית")
    assert end.count("31.12.2026") == 1 and "title=" not in end


def test_draft_card_never_shows_signature_to_complete(page4):
    p, _ = page4
    assert "חתימה להשלים" not in p["card_draft"] and "חתימה טרם נחתם" in p["card_draft"]
    assert "חתימה להשלים" not in p["card_orphan"] and "חתימה לא ידוע" in p["card_orphan"]
