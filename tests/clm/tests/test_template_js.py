"""לוח הבקרה: הסקריפט רץ ב-node עם DOM מינימלי, ונבדק ה-HTML שהוא מפיק. מדולג כשאין node."""
import datetime as dt
import glob
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
CP2 = {"name": "צד שני", "company_number": None, "notice_address": None}
CP3 = {"name": "צד שלישי", "company_number": None, "notice_address": None}


def f(path, sha, status):
    return {"path": path, "sha256": sha, "status": status, "abs": None, "duplicate_of": None}


def dataset():
    pa, pb, pc = "x/a - חתום.docx", "x/b - חתום.docx", "x/תיקון.docx"
    sa, sb, sc = "a" * 64, "b" * 64, "c" * 64
    cov = [{"category": c, "status": "found", "count": 1} for c in CATEGORIES]
    cov[5] = {"category": CATEGORIES[5], "status": "none_found", "note": "נסרק כל ההסכם"}
    cov[4] = {"category": CATEGORIES[4], "status": "not_checked", "note": "לא נבדק"}
    a = make_extract(sa, pa, total_value=500000, governing_law="ישראל", coverage=cov, key_clauses_checked=True,
                     guarantees=[{"kind": "ביטוח", "title": "פוליסת אחריות", "amount": "לא נקוב", "expiry": "2026-12-31",
                                  "clause": "סעיף 15", "quote": "החברה תחזיק פוליסה", "direction": "policy"}])
    e0 = a["events"][0]
    a["events"] = [
        dict(e0, event_code="term_end", label="תום תקופת ההסכם", date="2026-08-31", consequence="auto_change",
             renewal_months=12),
        dict(e0, event_code="payment_report", label="דוח תשלומים", date=None, consequence="we_breach",
             renewal_months=None, impact="material"),
        dict(e0, event_code="insurance_cert", label="אישור ביטוח", date="2026-12-15", consequence="we_breach",
             obligor="us", renewal_months=None, impact="material", recurrence=None),
    ]
    b = make_extract(sb, pb, title="הסכם שהוסר", counterparty=CP2)
    c = make_extract(sc, pc, doc_kind="amendment", title="תיקון יתום", counterparty=CP3,
                     dates={"signed": None, "start": None, "end": None}, events=[], commercials=[])
    exts = {sa: a, sb: b, sc: c}
    r1 = assemble.assemble({"files": [f(pa, sa, "new"), f(pb, sb, "new")]}, exts, "חברה", TODAY)
    r2 = assemble.assemble({"files": [f(pa, sa, "same"), f(pb, sb, "removed"), f(pc, sc, "new"),
                                      f("x/לא חולץ.docx", "d" * 64, "new")]}, exts, "חברה", TODAY, previous=r1)
    ids = {x["title"]: x["id"] for x in r2["agreements"]}
    return r2, ids["הסכם בדיקה"], ids["הסכם שהוסר"], ids["תיקון יתום"]


@pytest.fixture(scope="module")
def page(tmp_path_factory):
    if not shutil.which("node"):
        pytest.skip("node אינו מותקן")
    data, a_id, b_id, c_id = dataset()
    d = tmp_path_factory.mktemp("tpl")
    data_path, out = str(d / "data.json"), str(d / "out.html")
    with open(data_path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False)
    build.build(data_path, TEMPLATE, out)
    card = "(openAg(%r, %r), document.querySelector('#drawer').innerHTML)"
    exprs = {
        "dates": "V.dates()", "tasks": "V.tasks()", "repo": "V.repo()", "dash": "V.dash()",
        "review": "V.review()", "regs": "V.regs()", "obl": "V.obl()",
        "urg_missing": "urg(D.events.find(e => e.state === 'missing'))",
        "card_a": card % (a_id, "sum"), "card_b": card % (b_id, "sum"), "card_c": card % (c_id, "sum"),
        "keys_a": card % (a_id, "keys"),
        "docs_a": "(dtab = 'docs', " + (card % (a_id, "docs")) + ")",
        "review_open": "counts().review",
        "after_mark": "(S.review[rkey(D.review_queue[0])] = 'אושר', counts().review)",
    }
    ex_path = str(d / "exprs.json")
    with open(ex_path, "w", encoding="utf-8") as fh:
        json.dump(exprs, fh, ensure_ascii=False)
    r = subprocess.run(["node", HARNESS, out, ex_path], capture_output=True, text=True, encoding="utf-8")
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout), data


def test_missing_date_is_not_urgent(page):
    p, _ = page
    assert p["urg_missing"][0] == "חסר תאריך"
    for k in ("dates", "tasks", "card_a", "obl"):
        assert "null" not in p[k] and "NaN" not in p[k], k
    assert "חסר תאריך" in p["dates"]


def test_source_removed_tag_in_list_and_card(page):
    p, _ = page
    assert "המקור הוסר" in p["repo"] and "המקור הוסר" in p["card_b"] and "המקור הוסר" not in p["card_a"]


def test_card_states_extracted_facts(page):
    p, _ = page
    card = p["card_a"]
    assert "1.3.2025" in card and "500 אלף ₪" in card and "ישראל" in card
    assert "נבדק ולא נמצא" in card and "לא נבדק" in card
    assert "לא ידוע" in p["card_c"] and "טרם נחתם" not in p["card_c"]
    assert "נבדק ולא נמצאו" in p["keys_a"]


def test_extended_label_and_policy_kpi_without_type_condition(page):
    p, _ = page
    assert "בהארכה מכוח ההסכם" in p["repo"]
    assert "פוליסות החברה 1" in p["dash"]


def test_review_marks_keyed_by_stable_id_and_all_groups_shown(page):
    p, data = page
    assert 'data-k="rv-' in p["review"] and "data-i=" not in p["review"]
    for group in ("קובץ שלא חולץ", "מקור שהוסר", "תוצאת מועד שחלף"):
        assert group in p["review"], group
    assert "לאמת שההסכם התחדש" in p["review"]
    assert p["review_open"] == len(data["review_queue"]) and p["after_mark"] == len(data["review_queue"]) - 1


def test_register_hints_only_when_not_computed(page):
    p, _ = page
    assert "בהרצה הבאה" not in p["regs"] and "בהרצה הבאה" not in p["dash"]


def test_no_type_specific_conditions_in_code_or_template():
    labels = set()
    for path in glob.glob(os.path.join(ROOT, "catalog", "types", "*.json")):
        with open(path, encoding="utf-8") as fh:
            t = json.load(fh)
        labels |= {t["type_code"], t["label"]}
    sources = [TEMPLATE] + glob.glob(os.path.join(ROOT, "scripts", "**", "*.py"), recursive=True)
    for path in sources:
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
        assert not re.search(r"(family|type_code|type_label)\s*[!=]==?\s*[\"']", text), path
        for lab in labels:
            assert not re.search(r"[\"']%s[\"']" % re.escape(lab), text), (path, lab)
        assert '"ביטוח"' not in text, path


def test_glossary_labels_for_all_states():
    with open(TEMPLATE, encoding="utf-8") as fh:
        text = fh.read()
    for label in ("בהארכה מכוח ההסכם", "הסתיים מוקדם", "התחייבויות שורדות בלבד", "מוקפא", "נזנח", "הסתיים בתום תקופה"):
        assert label in text, label


def template_text():
    with open(TEMPLATE, encoding="utf-8") as fh:
        return fh.read()


def test_file_names_render_inside_bidi_isolated_element(page):
    p, _ = page
    html = template_text()
    assert re.search(r"\.fnm\{[^}]*unicode-bidi:isolate", html)
    assert 'const fnm = ' in html and '<bdi class="fnm" dir="auto">' in html
    for bad in ("esc(d.file", "esc(f.file", "esc(x.text)", "esc(a.original_location", "esc(t.source.name"):
        assert bad not in html, bad
    assert 'b.replace(EXT, "").length >= 8' in html
    assert 'dir="auto">' in p["docs_a"] and '<bdi dir="ltr">.docx</bdi>' in p["docs_a"]
    assert '<bdi class="fnm" dir="auto">חולץ<bdi dir="ltr">.docx</bdi></bdi>' in p["review"]


def test_dates_board_table_is_fixed_layout_without_nowrap_columns():
    html = template_text()
    assert re.search(r"\.dt\{table-layout:fixed;min-width:\d+px\}", html)
    assert int(re.search(r"\.dt\{table-layout:fixed;min-width:(\d+)px", html).group(1)) <= 960
    start = html.index('<table class="dt">')
    end = html.index("</table>", start)
    block = html[start:end]
    assert "white-space:nowrap" not in block and "min-width:" not in block
    assert "<colgroup>" in block
    assert not re.search(r"(?m)^th\{[^}]*white-space:nowrap", html)


@pytest.fixture(scope="module")
def amended_page(tmp_path_factory):
    if not shutil.which("node"):
        pytest.skip("node אינו מותקן")
    cov = [{"category": c, "status": "found", "count": 1} for c in CATEGORIES]

    def ev(code, date, label, cons="auto_change"):
        e = dict(make_extract("z" * 64, "x")["events"][0], event_code=code, date=date, label=label,
                 consequence=cons, renewal_months=None, clause="סעיף 2", quote="עד ליום %s" % date)
        return e
    head = make_extract("a" * 64, "x/הסכם ענן - חתום.docx", coverage=cov,
                        dates={"signed": "2022-04-10", "start": "2022-05-01", "end": "2027-01-31"},
                        events=[ev("term_end", "2027-01-31", "תום התקופה"), ev("term_end", "2025-04-30", "תום קודם")])
    am = make_extract("b" * 64, "x/תיקון 1.docx", doc_kind="amendment", title="תיקון", coverage=cov,
                      dates={"signed": "2025-03-23", "start": None, "end": "2029-04-30"},
                      events=[ev("term_end", "2029-04-30", "תום לפי התיקון")], commercials=[])
    scan = {"files": [f("x/הסכם ענן - חתום.docx", "a" * 64, "new"), f("x/תיקון 1.docx", "b" * 64, "new")]}
    data = assemble.assemble(scan, {"a" * 64: head, "b" * 64: am}, "חברה", TODAY)
    aid = data["agreements"][0]["id"]
    d = tmp_path_factory.mktemp("tpl2")
    data_path, out, ex_path = str(d / "data.json"), str(d / "out.html"), str(d / "exprs.json")
    with open(data_path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False)
    build.build(data_path, TEMPLATE, out)
    exprs = {"card": "(openAg(%r, 'sum'), document.querySelector('#drawer').innerHTML)" % aid,
             "dates": "(df.state = '', V.dates())", "tasks": "V.tasks()", "dash": "V.dash()", "renew": "V.renew()"}
    with open(ex_path, "w", encoding="utf-8") as fh:
        json.dump(exprs, fh, ensure_ascii=False)
    r = subprocess.run(["node", HARNESS, out, ex_path], capture_output=True, text=True, encoding="utf-8")
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout), data


def test_card_shows_end_date_with_amendment_hint(amended_page):
    p, data = amended_page
    assert data["agreements"][0]["dates"]["end_source"]
    assert '<bdi dir="ltr">30.4.2029</bdi> <span class="tag">לפי התיקון להסכם</span>' in p["card"]
    assert p["card"].count("הסיום שבהסכם המקורי: 31.1.2027") == 1
    assert "תוספת" not in p["card"] + p["dates"]


def test_superseded_upcoming_event_is_not_urgent_and_not_in_renewals_or_tasks(amended_page):
    p, data = amended_page
    sup = [e for e in data["events"] if e.get("superseded_by")]
    assert len(sup) == 2
    assert "הוחלף בתיקון להסכם" in p["dates"] and sup[0]["superseded_note"] in p["dates"]
    html = template_text()
    assert "(e.act_by && days(e.act_by) <= +df.win)" in html
    assert 'dates: datesOpen().length' in html
    assert "31.1.2027" not in p["renew"] and "תום קודם" not in p["renew"] and "תום לפי התיקון" in p["renew"]
    assert "תום התקופה</div>" not in p["tasks"]
