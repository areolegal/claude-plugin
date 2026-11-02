"""לוח הבקרה, שלב ב: הליבה המורחבת על המסך (תקופה, חידוש, יציאה, חותמים, שיפוט, עובדות, מרשמים). הסקריפט רץ ב-node."""
import datetime as dt
import json
import os
import re
import shutil
import subprocess
from html import unescape

import pytest

from clm import assemble, build
from helpers import CATEGORIES, make_extract

import clm_paths  # noqa: E402
ROOT = clm_paths.SKILL
TEMPLATE = os.path.join(ROOT, "assets", "workspace-template.html")
HARNESS = clm_paths.HARNESS
TODAY = dt.date(2026, 10, 29)
CO = "מדיקס שירותי בריאות דיגיטליים בע\"מ"
COV = [{"category": c, "status": "found", "count": 1} for c in CATEGORIES]
EXT_KEYS = ["term", "renewal", "exit", "signatories", "jurisdiction", "payment_terms", "facts"]

FULL = dict(
    term={"kind": "fixed", "initial_months": 24, "starts_on": "start", "max_end": None, "trigger": "",
          "clause": "סעיף 3.1", "quote": "תקופת ההסכם 24 חודשים מיום תחילתו."},
    renewal={"kind": "auto", "period_months": 12, "max_count": 3, "holder": None, "holder_name": None,
             "notice_days": 90, "clause": "סעיף 3.2", "quote": "ההסכם יתחדש אוטומטית."},
    exit={"who": "both", "who_name": None, "notice_days": 60, "min_commitment_months": 12,
          "clause": "סעיף 14", "quote": "כל צד רשאי לסיים בהודעה של 60 יום."},
    signatories=[{"party": "counterparty", "party_name": "ספק בדיקה בע\"מ", "name": "דנה לוי", "role": "מנכ\"לית",
                  "date": "2025-03-01", "status": "signed", "clause": "בלוק חתימות", "quote": "דנה לוי, מנכ\"לית"},
                 {"party": "contracting", "party_name": CO, "name": None, "role": None,
                  "date": None, "status": "blank", "clause": "בלוק חתימות", "quote": "מדיקס, חתימה"}],
    jurisdiction={"court": "בתי המשפט בתל אביב", "exclusive": True, "clause": "סעיף 20", "quote": "סמכות שיפוט ייחודית"},
    payment_terms={"days": 45, "basis": "eom", "text": None, "clause": "סעיף 7.3", "quote": "שוטף + 45"},
    facts=[{"code": "negotiation_stopped", "label": "המשא ומתן הופסק", "value": "הערה בשולי הטיוטה",
            "clause": "הערה", "quote": "המשא ומתן הופסק ביוזמת הלקוח"},
           {"code": "other", "label": "תוספת מחיר", "value": "עד 5 אחוזים", "clause": "נספח ב",
            "quote": "תוספת של עד 5 אחוזים"}],
)


def kc(code, **kw):
    row = {"clause_code": code, "summary": "סעיף מגבלה", "value": "", "clause": "סעיף 3", "quote": "ציטוט " + code}
    row.update(kw)
    return row


def cp(name):
    return {"name": name, "company_number": None, "notice_address": None}


def dataset():
    rows = []

    def add(i, title, **kw):
        sha, path = str(i) * 64, "x/%s.docx" % title
        rows.append(({"path": path, "sha256": sha, "status": "new", "abs": None, "duplicate_of": None},
                     make_extract(sha, path, title=title, coverage=COV, **kw)))
    add(1, "הסכם מלא", counterparty=cp("ספק בדיקה בע\"מ"), **FULL,
        key_clauses=[kc("non_compete", bound_party="contracting", bound_party_name=CO, norm={"until": "2032-08-20"}),
                     kc("exclusivity", bound_party="contracting", bound_party_name=CO, norm={"until": "2020-01-01"}),
                     kc("change_of_control", bound_party="contracting", bound_party_name=CO,
                        norm={"requires": "consent"})],
        key_clauses_checked=True)
    add(2, "הסכם צד לא ידוע", counterparty=cp("ספק ב בע\"מ"), our_role={"value": None, "source": "none"},
        key_clauses=[kc("exclusivity", bound_party="unknown"), kc("change_of_control", bound_party="both")],
        key_clauses_checked=True)
    add(3, "הסכם ישן", counterparty=cp("ספק ג בע\"מ"))
    add(4, "הסכם בלי הגבלת זמן", counterparty=cp("ספק ד בע\"מ"),
        dates={"signed": "2025-03-01", "start": "2025-03-01", "end": None},
        term={"kind": "indefinite", "initial_months": None, "starts_on": None, "max_end": None, "trigger": "",
              "clause": "סעיף 2", "quote": "ההסכם בתוקף עד להודעה"},
        renewal={"kind": "none", "period_months": None, "max_count": None, "holder": None, "holder_name": None,
                 "notice_days": None, "clause": None, "quote": None},
        signatories=[], events=[])
    add(5, "הסכם אופציה", counterparty=cp("ספק ה בע\"מ"),
        dates={"signed": "2024-03-01", "start": "2024-03-01", "end": "2026-02-28"},
        renewal={"kind": "option", "period_months": 12, "max_count": 2, "holder": "counterparty", "holder_name": None,
                 "notice_days": 30, "clause": "סעיף 4", "quote": "אופציה להארכה"},
        exit={"who": "none", "who_name": None, "notice_days": None, "min_commitment_months": None,
              "clause": "סעיף 9", "quote": "אין סיום ללא עילה"}, events=[])
    add(6, "הסכם צד לא ודאי", counterparty=cp("ספק ו בע\"מ"), our_role={"value": None, "source": "none"},
        signatories=[{"party": "contracting", "party_name": "הלקוח", "name": "רון כהן", "role": "מנהל",
                      "date": "2025-03-01", "status": "signed", "clause": "חתימות", "quote": "רון כהן"}],
        key_clauses=[kc("non_compete", bound_party="contracting", bound_party_name="הלקוח", norm={"until": "2031-05-01"})],
        key_clauses_checked=True)
    return assemble.assemble({"files": [r[0] for r in rows]}, {r[1]["sha256"]: r[1] for r in rows}, CO, TODAY)


def strip_js(aid, mode):
    pre = ("const a = A[%r]; const keep = {}; %s.forEach(k => { keep[k] = a[k]; %s }); const dd = {...a.dates}; "
           "Object.assign(a.dates, {max_end: null, max_end_basis: null, survival_end: null, survival_end_label: null});" %
           (aid, json.dumps(EXT_KEYS), "delete a[k];" if mode == "strip" else "a[k] = null;"))
    if mode == "null":
        pre += " const fs = {...a.field_status}; delete a.field_status.term_kind; delete a.field_status.signatories;"
    post = " Object.assign(a, keep); a.dates = dd;" + (" Object.assign(a.field_status, fs);" if mode == "null" else "")
    return ("(() => { %s const h = (openAg(%r, 'sum'), document.querySelector('#drawer').innerHTML);%s return h; })()"
            % (pre, aid, post))


@pytest.fixture(scope="module")
def page(tmp_path_factory):
    if not shutil.which("node"):
        pytest.skip("node אינו מותקן")
    data = dataset()
    d = tmp_path_factory.mktemp("stage_b")
    data_path, out, ex_path = str(d / "data.json"), str(d / "out.html"), str(d / "exprs.json")
    with open(data_path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False)
    build.build(data_path, TEMPLATE, out)
    ids = {a["title"]: a["id"] for a in data["agreements"]}
    card = "(openAg(%r, 'sum'), document.querySelector('#drawer').innerHTML)"
    keys = "(openAg(%r, 'keys'), document.querySelector('#drawer').innerHTML)"
    exprs = {
        "card_full": card % ids["הסכם מלא"], "card_old": card % ids["הסכם ישן"],
        "card_indef": card % ids["הסכם בלי הגבלת זמן"], "card_opt": card % ids["הסכם אופציה"],
        "card_unknown": card % ids["הסכם צד לא ידוע"], "card_uncertain": card % ids["הסכם צד לא ודאי"],
        "keys_uncertain": keys % ids["הסכם צד לא ודאי"], "keys_full": keys % ids["הסכם מלא"],
        "card_stripped": strip_js(ids["הסכם מלא"], "strip"), "card_nulls": strip_js(ids["הסכם ישן"], "null"),
        "card_dates": "(() => { const a = A[%r]; const d0 = {...a.dates}; Object.assign(a.dates, {max_end: '2029-10-31', max_end_basis: {kind: 'deadline', note: 'לפי תקרת החידושים'}, survival_end: '2030-06-17', survival_end_label: 'שלוש שנים מתום ההסכם'}); const h = (openAg(%r, 'sum'), document.querySelector('#drawer').innerHTML); a.dates = d0; return h; })()" % (ids["הסכם מלא"], ids["הסכם מלא"]),
        "card_court_none": "(() => { const a = A[%r]; const j = a.jurisdiction; a.jurisdiction = {...j, court: null}; const h = (openAg(%r, 'sum'), document.querySelector('#drawer').innerHTML); a.jurisdiction = j; return h; })()" % (ids["הסכם מלא"], ids["הסכם מלא"]),
        "repo": "V.repo()", "regs": "V.regs()", "dash": "V.dash()", "nav": "(nav(), document.querySelector('#nav').innerHTML)",
        "counts": "counts()", "rows": "repoRows()",
        "regs_null": "(() => { const r = D.registers; D.registers = {...r, restrictions: null, restrictions_review: null, change_of_control: null, change_of_control_review: null}; const h = V.regs(); D.registers = r; return h; })()",
        "regs_old": "(() => { const r = D.registers; const o = {...r}; delete o.restrictions_review; delete o.change_of_control_review; delete o.restriction_details; D.registers = o; const h = V.regs(); D.registers = r; return h; })()",
    }
    with open(ex_path, "w", encoding="utf-8") as fh:
        json.dump(exprs, fh, ensure_ascii=False)
    r = subprocess.run(["node", HARNESS, out, ex_path], capture_output=True, text=True, encoding="utf-8")
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout), data, ids


def text(html):
    return re.sub(r"\s+", " ", unescape(re.sub(r"<[^>]+>", " ", html)))


def block(html, title, nxt):
    i = html.index(title)
    j = html.find(nxt, i + len(title))
    return html[i:] if j < 0 else html[i:j]


def test_no_dashes_in_template():
    s = open(TEMPLATE, encoding="utf-8").read()
    assert chr(0x2013) not in s and chr(0x2014) not in s


def test_term_and_renewal_block(page):
    p, _, _ = page
    t = text(p["card_full"])
    assert 'class="blk">תקופה וחידוש<' in p["card_full"]
    for needle in ["סוג תקופה", "קצובה", "24 חודשים", "מנגנון חידוש", "חידוש אוטומטי",
                   "12 חודשים", "עד 3 חידושים", "90 ימים"]:
        assert needle in t, needle
    assert block(p["card_full"], "סוג תקופה", "מנגנון חידוש").count("data-ref") >= 1


def test_max_end_and_survival_rows(page):
    p, _, _ = page
    t = text(p["card_dates"])
    assert "סיום התקופה המרבית" in t and "31.10.2029" in t and "לפי תקרת החידושים" in t
    assert "פקיעת התחייבויות שורדות" in t and "17.6.2030" in t and "שלוש שנים מתום ההסכם" in t
    assert "סיום התקופה המרבית" not in text(p["card_old"])


def test_option_renewal_holder_label_and_exit_none(page):
    p, _, _ = page
    t = text(p["card_opt"])
    assert "אופציית הארכה" in t and "הצד שכנגד" in t
    assert "אין זכות סיום ללא עילה" in t
    assert "סיום התקופה המרבית" in t


def test_exit_payment_jurisdiction_rows(page):
    p, _, _ = page
    t = text(p["card_full"])
    for needle in ["יציאה ותשלום", "סיום ללא עילה", "שני הצדדים", "60 ימים", "12 חודשים", "תנאי תשלום", "45 ימים",
                   "שוטף", "שיפוט", "בתי המשפט בתל אביב", "ייחודית"]:
        assert needle in t, needle
    assert t.index("דין חל") < t.index("שיפוט")


def test_signatories_block_uses_company_and_counterparty_labels(page):
    p, _, _ = page
    seg = text(block(p["card_full"], ">חותמים<", ">עובדות נוספות<"))
    assert "דנה לוי" in seg and "מנכ\"לית" in seg and "הצד שכנגד" in seg and "החברה" in seg
    assert "נחתם" in seg and "ריק" in seg and "1.3.2025" in seg
    assert "אנחנו" not in seg and not re.search(r"(^|\s)הם(\s|$)", seg)


def test_empty_signatories_in_signed_agreement(page):
    p, _, _ = page
    assert re.search(r"חותמים\s*לא נמצאו", text(p["card_indef"]))


def test_facts_block_marks_negotiation_stopped(page):
    p, _, _ = page
    seg = block(p["card_full"], "עובדות נוספות", "עו\"ד אחראי")
    t = text(seg)
    assert "המשא ומתן הופסק" in t and "כדאי לבדוק" in t and "תוספת מחיר" in t and "עד 5 אחוזים" in t
    assert t.count("כדאי לבדוק") == 1 and "data-ref" in seg


def test_end_date_rows_for_not_relevant_and_indefinite(page):
    p, data, _ = page
    ag = next(a for a in data["agreements"] if a["title"] == "הסכם בלי הגבלת זמן")
    assert ag["field_status"]["end_date"] == "not_relevant"
    assert "לא רלוונטי (ללא הגבלת זמן)" in text(p["card_indef"])
    assert "להשלים" not in text(block(p["card_indef"], "<div>סיום</div>", "<div>שווי</div>"))


def test_option_pending_note_is_shown(page):
    p, data, _ = page
    ag = next(a for a in data["agreements"] if a["title"] == "הסכם אופציה")
    assert ag["dates"]["current_end_basis"]["kind"] == "option_pending"
    assert ag["dates"]["current_end_basis"]["note"] in text(p["card_opt"])


def test_legacy_agreement_renders_without_blocks_or_placeholders(page):
    p, _, _ = page
    for k in ["card_stripped", "card_nulls"]:
        t = text(p[k])
        for needle in ["סוג תקופה", "מנגנון חידוש", "יציאה ותשלום", "תנאי תשלום", "חותמים", "עובדות נוספות",
                       "שיפוט", "פרטי ההסכם", "לא נמצא"]:
            assert needle not in t, (k, needle)
    assert "דין חל" in text(p["card_stripped"])


def test_missing_field_status_shows_not_found_only_for_term_and_signatories(page):
    p, _, _ = page
    t = text(p["card_old"])
    assert re.search(r"סוג תקופה\s*לא נמצא", t) and re.search(r"חותמים\s*לא נמצאו", t)
    for needle in ["מנגנון חידוש", "יציאה ותשלום", "תנאי תשלום", "שיפוט", "עובדות נוספות"]:
        assert needle not in t, needle


def test_repository_column_and_row(page):
    p, _, _ = page
    head = re.search(r"<thead>(.*?)</thead>", p["repo"]).group(1)
    ths = re.findall(r"<th[^>]*>(.*?)</th>", head)
    assert ths.index("תקופה") == ths.index("סיום התקופה הנוכחית") + 1
    assert "קצובה, חידוש אוטומטי" in text(p["repo"])


def test_csv_has_new_columns_and_values(page):
    p, _, _ = page
    head = p["rows"][0]
    for c in ["סוג תקופה", "מנגנון חידוש", "סיום התקופה המרבית", "שיפוט", "חותמים"]:
        assert c in head, c
    row = next(r for r in p["rows"][1:] if r[1] == "הסכם מלא")
    assert row[head.index("סוג תקופה")].startswith("קצובה")
    assert "חידוש אוטומטי" in row[head.index("מנגנון חידוש")]
    assert "בתי המשפט בתל אביב" in row[head.index("שיפוט")]
    assert "דנה לוי" in row[head.index("חותמים")] and "הצד שכנגד" in row[head.index("חותמים")]
    assert all(len(r) == len(head) for r in p["rows"])


def test_registers_counted_review_and_details(page):
    p, data, ids = page
    R, L = data["registers"], data["key_clause_labels"]
    assert R["restrictions"] == [ids["הסכם מלא"]]
    assert sorted(R["restrictions_review"]) == sorted([ids["הסכם צד לא ידוע"], ids["הסכם צד לא ודאי"]])
    res = text(block(p["regs"], "מגבלות על החברה", "ייפויי כוח"))
    nc, ex = L["non_compete"], L["exclusivity"]
    assert "%s · החברה · פעילה עד 20.8.2032" % nc in res
    assert "%s · החברה · פקעה ב-1.1.2020" % ex in res
    counted, review = res.split("לבדיקה", 1)[0], res.split("לבדיקה", 1)[1]
    assert "%s · החברה · פעילה עד 20.8.2032" % nc in counted and "(לאימות)" not in counted
    assert "%s · לא ידוע · ללא תאריך סיום" % ex in review
    assert "%s · החברה (לאימות) · פעילה עד 1.5.2031" % nc in review
    assert "לבדיקה" in text(block(p["regs"], "שינוי שליטה והמחאה", "מגבלות על החברה"))


def test_uncertain_party_suffix_on_card_and_not_on_certain_party(page):
    p, _, _ = page
    seg = text(block(p["card_uncertain"], ">חותמים<", ">פרטי ההסכם<"))
    assert "החברה (לאימות)" in seg and "רון כהן" in seg
    full = text(block(p["card_full"], ">חותמים<", ">עובדות נוספות<"))
    assert "(לאימות)" not in full
    assert "הצד המתחייב: החברה (לאימות)" in text(p["keys_uncertain"])


def test_review_count_matches_list_and_hidden_when_empty(page):
    p, data, _ = page
    res = block(p["regs"], "מגבלות על החברה", "ייפויי כוח")
    m = re.search(r"לבדיקה <span class=\"n\">(\d+)</span>", res)
    assert m and int(m.group(1)) == len(data["registers"]["restrictions_review"])
    assert "לבדיקה" not in text(block(p["regs"], "טרם נחתמו", "שינוי שליטה"))
    assert "לבדיקה" not in text(p["regs_old"])


def test_null_registers_keep_not_checked(page):
    p, _, _ = page
    t = text(p["regs_null"])
    assert t.count("לא נבדק") >= 2 and "לבדיקה" not in t


def test_dashboard_tiles_count_only_counted_list(page):
    p, data, _ = page
    for label, key in [("מגבלות על החברה", "restrictions"), ("שינוי שליטה והמחאה", "change_of_control")]:
        m = re.search(label + r"<div class=\"xs mut\">[^<]*</div></span><b>(\d+)</b>", p["dash"])
        assert m and int(m.group(1)) == len(data["registers"][key])


def test_nav_counts_unchanged(page):
    p, data, _ = page
    assert p["counts"]["repo"] == len(data["agreements"])
    assert ">%d<" % len(data["agreements"]) in p["nav"]


def test_key_clauses_tab_shows_bound_party_and_activity(page):
    p, _, _ = page
    t = text(p["keys_full"])
    assert "הצד המתחייב: החברה · פעילה עד 20.8.2032" in t
    assert "הצד המתחייב: החברה · פקעה ב-1.1.2020" in t
    assert "המחויב" not in t


def test_terminology_wording_in_template():
    s = open(TEMPLATE, encoding="utf-8").read()
    assert "הצד המחויב" not in s and 'project:"עד פרויקט"' in s


def test_missing_court_without_status_shows_nothing_but_tag(page):
    p, _, _ = page
    assert "לא נמצא" not in text(p["card_court_none"])
    assert "ייחודית" in text(p["card_court_none"])


def test_repo_option_pending_tag_with_note_in_title(page):
    p, data, _ = page
    ag = next(a for a in data["agreements"] if a["title"] == "הסכם אופציה")
    note = ag["dates"]["current_end_basis"]["note"]
    assert 'title="%s">עד מימוש אופציה</span>' % note in p["repo"]


def test_signatory_and_fact_rows_stack_on_mobile(page):
    p, _, built = page
    assert p["card_full"].count('class="stk"') >= 2 * 2 + 2 * 2
    assert "@media (max-width:560px){.dl>div.stk{grid-column:1/-1}" in open(TEMPLATE, encoding="utf-8").read()
