"""תיקוני הסקירה הסופית של שלב ב: הפניות בהסכם שנשמר, תאריכי תקופה, מרשמים לחתומים בלבד, חישוב חודשים וניסוח."""
import copy
import datetime as dt
import json
import os
import re
import shutil
import subprocess

import pytest

from clm import assemble, build, catalog, core, dates
from clm.validate import check_data
from helpers import CATEGORIES, make_extract

import clm_paths  # noqa: E402
ROOT = clm_paths.SKILL
TEMPLATE = os.path.join(ROOT, "assets", "workspace-template.html")
HARNESS = clm_paths.HARNESS
T = dt.date(2026, 10, 23)
CO = "מדיקס שירותי בריאות דיגיטליים בע\"מ"
COV = [{"category": c, "status": "found", "count": 1} for c in CATEGORIES]
LATIN = "Granite Peak Health AI, Inc."
GONE = {"files": [{"path": "f0.docx", "sha256": None, "status": "removed"}]}


def scan_of(*items):
    return {"files": [{"path": p, "sha256": s, "status": st} for p, s, st in items]}


def run(*exts, today=T, **kw):
    scan = {"files": [{"path": "f%d.docx" % i, "sha256": e["sha256"], "status": "new"} for i, e in enumerate(exts)]}
    return assemble.assemble(scan, {e["sha256"]: e for e in exts}, CO, today, **kw)


def ag(d, i=0):
    return d["agreements"][i]


def kc(code, **kw):
    row = {"clause_code": code, "summary": "מגבלה", "value": "", "clause": "סעיף 3", "quote": "ציטוט " + code}
    row.update(kw)
    return row


def cp(name):
    return {"name": name, "company_number": None, "notice_address": None}


FULL = dict(
    term={"kind": "fixed", "initial_months": 24, "starts_on": "start", "max_end": None, "trigger": "",
          "clause": "סעיף 3.1", "quote": "תקופת ההסכם 24 חודשים"},
    renewal={"kind": "auto", "period_months": 12, "max_count": 3, "holder": None, "holder_name": None,
             "notice_days": 90, "clause": "סעיף 3.2", "quote": "ההסכם יתחדש אוטומטית"},
    exit={"who": "both", "who_name": None, "notice_days": 60, "min_commitment_months": 12,
          "clause": "סעיף 14", "quote": "כל צד רשאי לסיים בהודעה"},
    signatories=[{"party": "counterparty", "party_name": "ספק בדיקה בע\"מ", "name": "דנה לוי", "role": "מנכ\"לית",
                  "date": "2025-03-01", "status": "signed", "clause": "חתימות", "quote": "דנה לוי חתמה"},
                 {"party": "contracting", "party_name": CO, "name": "רון כהן", "role": "מנהל",
                  "date": None, "status": "blank", "clause": "חתימות", "quote": "רון כהן חתימה"}],
    jurisdiction={"court": "בתי המשפט בתל אביב", "exclusive": True, "clause": "סעיף 20", "quote": "סמכות ייחודית"},
    payment_terms={"days": 45, "basis": "eom", "text": None, "clause": "סעיף 7.3", "quote": "שוטף ועוד 45"},
    facts=[{"code": "other", "label": "תוספת מחיר", "value": "עד 5 אחוזים", "clause": "נספח ב",
            "quote": "תוספת של עד 5 אחוזים"}],
    key_clauses_checked=True,
    key_clauses=[kc("non_compete", bound_party="contracting", bound_party_name=CO, norm={"until": "2032-08-20"})],
)
FIELD_KEYS = ("term", "renewal", "exit", "jurisdiction", "payment_terms")


def field_quotes(d, aid):
    fn = {f["n"]: f for f in d["footnotes"]}
    a = next(x for x in d["agreements"] if x["id"] == aid)
    out = {}
    for k in FIELD_KEYS:
        if a.get(k):
            out[k] = [fn[n]["quote"] for n in a[k]["refs"]]
    for k in ("signatories", "facts"):
        out[k] = [[fn[n]["quote"] for n in x["refs"]] for x in a[k]]
    det = d["registers"]["restriction_details"].get(aid) or []
    out["details"] = [[fn[n]["quote"] for n in x["refs"]] for x in det]
    for refs in [a[k]["refs"] for k in FIELD_KEYS if a.get(k)] + [x["refs"] for k in ("signatories", "facts") for x in a[k]]:
        assert all(fn[n]["agreementId"] == aid for n in refs)
    return out


# ---------- C1 ----------
def test_carry_renumbers_refs_of_every_agreement_level_field():
    pa, pb = "x/a.docx", "x/b.docx"
    sa, sb, sc = "a" * 64, "b" * 64, "c" * 64
    other_kc = [kc("exclusivity", bound_party="both")]
    ea = make_extract(sa, pa, **FULL)
    eb = make_extract(sb, pb, title="שני", counterparty=cp("ספק ב"), **dict(FULL, key_clauses=other_kc))
    r1 = assemble.assemble(scan_of((pa, sa, "new"), (pb, sb, "new")), {sa: ea, sb: eb}, CO, T)
    ida = next(a["id"] for a in r1["agreements"] if a["file"] == pa)
    before = field_quotes(r1, ida)
    assert before["term"] and before["signatories"] and before["facts"] and before["details"]
    # הקובץ של א השתנה וטרם חולץ; ב חולץ מחדש, כך שהמספור משתנה
    eb2 = make_extract(sc, pb, title="שני", counterparty=cp("ספק ב"), **dict(FULL, key_clauses=other_kc))
    r2 = assemble.assemble(scan_of((pa, "z" * 64, "changed"), (pb, sc, "changed")), {sc: eb2}, CO, T, previous=r1)
    assert field_quotes(r2, ida) == before
    assert check_data(r2)[0] == []
    # הפניה שאינה בטבלת המספור נושרת
    r1b = copy.deepcopy(r1)
    next(a for a in r1b["agreements"] if a["id"] == ida)["term"]["refs"].append(9999)
    r2b = assemble.assemble(scan_of((pa, "z" * 64, "changed"), (pb, sc, "changed")), {sc: eb2}, CO, T, previous=r1b)
    assert field_quotes(r2b, ida) == before


def test_validate_checks_refs_of_agreement_fields_and_restriction_details():
    d = run(make_extract("a" * 64, "a.docx", **FULL))
    assert check_data(d)[0] == []
    for mutate in (lambda a, dd: a["term"]["refs"].append(999),
                   lambda a, dd: a["signatories"][0]["refs"].append(999),
                   lambda a, dd: a["facts"][0]["refs"].append(999),
                   lambda a, dd: dd["registers"]["restriction_details"][a["id"]][0]["refs"].append(999)):
        bad = copy.deepcopy(d)
        mutate(bad["agreements"][0], bad)
        assert any("999" in e for e in check_data(bad)[0])
    other = run(make_extract("a" * 64, "a.docx", **FULL), make_extract("b" * 64, "b.docx", title="שני", **FULL))
    bad = copy.deepcopy(other)
    foreign = next(f["n"] for f in bad["footnotes"] if f["agreementId"] != bad["agreements"][0]["id"])
    bad["agreements"][0]["exit"]["refs"] = [foreign]
    assert any("שייכת להסכם אחר" in e for e in check_data(bad)[0])


# ---------- I2 ----------
def _term_ev(date, role):
    return {"event_code": "term_end", "label": "סיום התחייבות מזערית", "date": date, "relative": False, "trigger": "",
            "clause": "סעיף 3", "quote": "התחייבות מזערית עד %s" % date, "obligor": "both", "consequence": "auto_change",
            "impact": "material", "if_nothing": "", "action": "", "notice_days": None, "recurrence": None,
            "renewal_months": None, "renewal_max": None, "computed": False, "term_role": role}


@pytest.mark.parametrize("role", ["min_commitment_end", "max_end"])
@pytest.mark.parametrize("date", ["2026-12-01", "2026-09-01"])
def test_min_commitment_and_max_end_do_not_set_agreement_state(role, date):
    ext = make_extract("1" * 64, "a.docx", events=[_term_ev(date, role)],
                       dates={"signed": "2025-01-01", "start": "2025-01-01", "end": None})
    d = run(ext)
    assert ag(d)["agreement_state"] == "in_force"
    assert any(e["event_code"] == "term_end" for e in d["events"])
    # וגם בהסכם שנשמר
    c = assemble.assemble(GONE, {}, CO, dt.date(2027, 3, 1), previous=d)
    assert ag(c)["agreement_state"] == "in_force"


def test_initial_end_still_sets_state():
    ext = make_extract("1" * 64, "a.docx", events=[_term_ev("2026-12-01", "initial_end")],
                       dates={"signed": "2025-01-01", "start": "2025-01-01", "end": None})
    assert ag(run(ext))["agreement_state"] == "renewal_window"


# ---------- registers: signed only ----------
def test_registers_ignore_drafts():
    cc = kc("change_of_control", bound_party="contracting", bound_party_name=CO, norm={"requires": "consent"})
    nc = kc("non_compete", bound_party="contracting", bound_party_name=CO, norm={"until": "2032-08-20"})
    unk = kc("exclusivity", bound_party="unknown")
    draft = make_extract("d" * 64, "d.docx", doc_kind="draft", title="טיוטה", key_clauses=[nc, cc, unk],
                         key_clauses_checked=True, counterparty=cp("אחרת"))
    signed = make_extract("e" * 64, "e.docx", title="חתום", key_clauses=[nc, cc, unk], key_clauses_checked=True)
    d = run(draft, signed)
    by = {a["title"]: a["id"] for a in d["agreements"]}
    assert next(a for a in d["agreements"] if a["title"] == "טיוטה")["signature"] == "not_signed"
    r = d["registers"]
    assert r["restrictions"] == [by["חתום"]] and r["restrictions_review"] == []
    assert r["change_of_control"] == [by["חתום"]] and r["change_of_control_review"] == []
    assert set(r["restriction_details"]) == {by["חתום"]}
    d2 = run(draft)
    assert d2["registers"]["restrictions"] == [] and d2["registers"]["restriction_details"] == {}
    assert d2["registers"]["change_of_control"] == [] and d2["registers"]["restrictions_review"] == []


# ---------- M3 ----------
def test_carry_recomputes_survival_max_end_and_key_clause_activity():
    ev = {"event_code": "post_term", "label": "תום חובת סודיות", "date": "2026-12-31", "relative": False, "trigger": "",
          "clause": "סעיף 9", "quote": "סודיות עד 31.12.2026", "obligor": "both", "consequence": "we_breach",
          "impact": "material", "if_nothing": "", "action": "", "notice_days": None, "recurrence": None,
          "renewal_months": None, "renewal_max": None, "computed": False}
    nc = kc("non_compete", bound_party="contracting", bound_party_name=CO, norm={"until": "2026-12-15"})
    ext = make_extract("1" * 64, "a.docx", events=[ev], key_clauses=[nc], key_clauses_checked=True,
                       renewal=FULL["renewal"], dates={"signed": "2025-01-01", "start": "2025-01-01", "end": "2026-12-31"})
    first = run(ext)
    a = ag(first)
    assert a["dates"]["survival_end"] == "2026-12-31" and a["dates"]["max_end_basis"]["kind"] == "derived"
    assert first["key_clauses"][0]["active"] is True
    stale = copy.deepcopy(first)
    sa = ag(stale)
    sa["dates"].update(survival_end="1999-01-01", survival_end_label="ישן", max_end="1999-01-01")
    c = assemble.assemble(GONE, {}, CO, dt.date(2027, 2, 1), previous=stale)
    cd = ag(c)["dates"]
    assert cd["survival_end"] == "2026-12-31" and cd["survival_end_label"] == "תום חובת סודיות"
    assert cd["max_end"] == a["dates"]["max_end"]
    assert c["key_clauses"][0]["active"] is False
    # תקרה שחולצה נשמרת
    sa["dates"].update(max_end="2031-01-01", max_end_basis={"kind": "extracted", "note": ""})
    c = assemble.assemble(GONE, {}, CO, dt.date(2027, 2, 1), previous=stale)
    assert ag(c)["dates"]["max_end"] == "2031-01-01"


# ---------- M4 ----------
def test_agreement_level_renewal_text_has_the_phrase_once_and_uses_cap_note():
    ren = dict(FULL["renewal"], max_count=None)
    ext = make_extract("1" * 64, "a.docx", events=[], renewal=ren,
                       dates={"signed": "2021-07-01", "start": "2021-07-01", "end": "2022-06-30"})
    d = run(ext)
    item = next(r for r in d["review_queue"] if r["kind"] == "renewal_verify" and not r.get("eventId"))
    assert item["text"].count("לאמת שההסכם התחדש") == 1 and item["text"].startswith(ag(d)["title"] + ": ")
    capped = make_extract("2" * 64, "a.docx", events=[], renewal=dict(ren, max_count=2),
                          dates={"signed": "2018-07-01", "start": "2018-07-01", "end": "2019-06-30"})
    item = next(r for r in run(capped)["review_queue"] if r["kind"] == "renewal_verify")
    assert "לאמת שההסכם התחדש" not in item["text"]
    assert "הגיע למספר החידושים המרבי (2)" in item["text"] and item["text"].endswith("לאמת את מצב ההסכם")


# ---------- M6 ----------
def test_signer_side_counts_only_when_party_is_certain():
    assert core.missing_party_sides([{"party": "contracting", "party_certain": False},
                                     {"party": "counterparty", "party_certain": True}]) == ["חותמים לחברה"]
    assert core.missing_party_sides([{"party": "contracting", "party_certain": True},
                                     {"party": "counterparty", "party_certain": True}]) == []
    sigs = [{"party": "counterparty", "party_name": "ספק בדיקה בע\"מ", "name": "א", "role": "", "date": None,
             "status": "signed", "clause": "ח", "quote": "א"},
            {"party": "contracting", "party_name": "הלקוח", "name": "ב", "role": "", "date": None,
             "status": "signed", "clause": "ח", "quote": "ב"}]
    ext = make_extract("1" * 64, "a.docx", signatories=sigs, our_role={"value": None, "source": "none"})
    item = next(r for r in run(ext)["review_queue"] if r["kind"] == "missing_core")
    assert "חותמים לחברה" in item["text"] and "חותמים לצד שכנגד" not in item["text"]


# ---------- M8 ----------
@pytest.mark.parametrize("start,months,end", [("2025-03-01", 12, "2026-02-28"), ("2025-01-31", 1, "2025-02-28"),
                                              ("2025-05-15", 6, "2025-11-14"), ("2024-02-29", 12, "2025-02-28"),
                                              ("2025-01-01", 12, "2025-12-31")])
def test_computed_end_month_edges(start, months, end):
    iso, _ = core.computed_end({"kind": "fixed", "initial_months": months, "clause": ""}, start)
    assert iso == end


@pytest.mark.parametrize("end,months,expect", [("2021-06-30", 12, "2022-06-30"), ("2023-02-28", 12, "2024-02-29"),
                                               ("2025-04-30", 1, "2025-05-31"), ("2025-04-15", 1, "2025-05-15")])
def test_roll_keeps_month_ends(end, months, expect):
    renewal = {"kind": "auto", "period_months": months, "max_count": None, "clause": ""}
    today = dt.date.fromisoformat(end) + dt.timedelta(days=1)
    iso, n, _ = core.roll(end, renewal, today)
    assert iso == expect and n == 1


def test_event_renewal_roll_keeps_month_end():
    ev = {"event_code": "term_end", "label": "תום תקופה", "date": "2023-02-28", "relative": False, "trigger": "",
          "consequence": "auto_change", "renewal_months": 12, "renewal_max": None}
    out = dates.derive_all(ev, dt.date(2023, 6, 1), catalog.load_events())[0]
    assert out["date"] == "2024-02-29"


# ---------- I1 + bdi (template) ----------
def _dataset():
    sha, path = "1" * 64, "x/הסכם חידוש.docx"
    ext = make_extract(sha, path, title="הסכם חידוש", coverage=COV, counterparty=cp(LATIN), events=[],
                       renewal=FULL["renewal"], dates={"signed": "2021-07-01", "start": "2021-07-01", "end": "2022-06-30"},
                       key_clauses=[kc("non_compete", bound_party="contracting", bound_party_name=CO)],
                       key_clauses_checked=True)
    return assemble.assemble({"files": [{"path": path, "sha256": sha, "status": "new", "abs": None,
                                         "duplicate_of": None}]}, {sha: ext}, CO, T)


@pytest.fixture(scope="module")
def page(tmp_path_factory):
    if not shutil.which("node"):
        pytest.skip("node אינו מותקן")
    data = _dataset()
    d = tmp_path_factory.mktemp("final_fixes")
    data_path, out, ex_path = str(d / "data.json"), str(d / "out.html"), str(d / "exprs.json")
    with open(data_path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False)
    build.build(data_path, TEMPLATE, out)
    item = "D.review_queue.find(x => x.kind === 'renewal_verify' && !x.eventId)"
    btn = "{target: {closest: () => ({classList: {contains: c => c === 'rv'}, dataset: {k: rkey(%s), t: 'אושר'}})}}" % item
    sel = "{target: {classList: {contains: c => c === 'rvo'}, dataset: {k: rkey(%s)}, value: 'הוארך'}}" % item
    exprs = {
        "review": "V.review()", "repo": "V.repo()", "regs": "V.regs()",
        "click": "(() => { delete S.review[rkey(%s)]; const before = reviewOpen(); onDocClick(%s); "
                 "return [before, reviewOpen(), S.review[rkey(%s)]]; })()" % (item, btn, item),
        "change": "(() => { delete S.review[rkey(%s)]; __L.change.forEach(f => f(%s)); "
                  "return [reviewOpen(), S.review[rkey(%s)], Object.keys(S.outcome)]; })()" % (item, sel, item),
    }
    with open(ex_path, "w", encoding="utf-8") as fh:
        json.dump(exprs, fh, ensure_ascii=False)
    r = subprocess.run(["node", HARNESS, out, ex_path], capture_output=True, text=True, encoding="utf-8")
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout), data


def test_agreement_level_renewal_verify_is_closable_without_js_error(page):
    p, data = page
    assert any(x["kind"] == "renewal_verify" and not x.get("eventId") for x in data["review_queue"])
    assert 'data-e="undefined"' not in p["review"] and "rvo" not in p["review"]
    assert 'class="btn sm rv"' in p["review"] and "אישור" in p["review"]
    before, after, state = p["click"]
    assert after == before - 1 and state == "אושר"
    _open, state, outcomes = p["change"]
    assert state == "נסגר: הוארך" and outcomes == []


def test_latin_counterparty_is_isolated_in_repository_and_registers(page):
    p, _ = page
    wrapped = '<bdi dir="auto">%s</bdi>' % LATIN
    assert wrapped in p["repo"] and wrapped in p["regs"]
    title = '<bdi dir="auto">הסכם חידוש</bdi>'
    assert title in p["repo"] and title in p["regs"]


# ---------- M7 ----------
def test_one_word_for_minimum_commitment_and_dictionary_has_screen_labels():
    tpl = open(TEMPLATE, encoding="utf-8").read()
    refs = clm_paths.REFS_DIR
    docs = "".join(open(os.path.join(refs, f), encoding="utf-8").read() for f in os.listdir(refs) if f.endswith(".md"))
    assert "מינימלית" not in tpl and "התחייבות מינימלית" not in docs and "תקופת התחייבות מזערית" in tpl
    term = open(os.path.join(refs, "terminology.md"), encoding="utf-8").read()
    for label in ("מועדי תקופה וחידוש", "מועדי יציאה", "סיום ללא עילה", "מחושב מהתחילה", "עד מימוש אופציה",
                  "כדאי לבדוק", "(לאימות)", "פרטי ההסכם", "תקופת התחייבות מזערית"):
        assert label in term and (label in tpl or label.startswith("(")), label
