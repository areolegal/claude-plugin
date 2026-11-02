"""C-05: מטבע שנכתב נשמר, ותיקון כספי חל על רכיב. C-06: עותק לקהל מצומצם בלי ההסכמים המוסתרים בבתים שלו. הנתונים סינתטיים."""
import datetime as dt
import json
import os
import shutil
import subprocess
import sys

import pytest

from clm import assemble, build, money
from clm.validate import check_data, check_extraction
from helpers import make_extract

import clm_paths  # noqa: E402
ROOT = clm_paths.SKILL
TEMPLATE = os.path.join(ROOT, "assets", "workspace-template.html")
HARNESS = clm_paths.HARNESS
CLI = os.path.join(ROOT, "scripts", "clm_cli.py")
T = dt.date(2026, 10, 22)
NODE = pytest.mark.skipif(not shutil.which("node"), reason="node אינו מותקן")


def row(value, label, period="חודשי", unit="", **kw):
    return dict({"category": "תעריף", "label": label, "value": value, "unit": unit, "period": period,
                 "clause": "סעיף 7", "quote": ""}, **kw)


def cp(name):
    return {"name": name, "company_number": None, "notice_address": None}


def files(*pairs):
    return {"files": [{"path": p, "sha256": s, "status": "new", "abs": None, "duplicate_of": None} for p, s in pairs]}


def dump(obj, path):
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, ensure_ascii=False)


def node(html, exprs, tmp_path):
    ex = str(tmp_path / "exprs.json")
    dump(exprs, ex)
    r = subprocess.run(["node", HARNESS, html, ex], capture_output=True, text=True, encoding="utf-8")
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


# ---------- (1) מטבע לא מוכר נשמר ----------

def test_explicit_currency_not_in_symbol_list_is_kept_not_replaced():
    assert money.currency_of(row(1, "x", currency="CHF"), "ILS") == "CHF"
    assert money.currency_of(row(1, "x", currency="chf")) == "CHF"
    assert money.currency_of(row(1, "x"), "CHF") == "CHF"
    r = money.annual([row(100, "א", currency="CHF"), row(50, "ב", currency="ILS")], "ILS")
    assert r["by_currency"] == {"CHF": 1200, "ILS": 600} and r["unknown_currency"] == []


def test_chf_survives_assemble_validate_and_counterparty_totals():
    s, p = "a" * 64, "x/chf - חתום.docx"
    ext = make_extract(s, p, currency="CHF", commercials=[row(1000, "תמורה", unit="לחודש")])
    d = assemble.assemble(files((p, s)), {s: ext}, "חברה", T)
    v = d["agreements"][0]["value"]
    assert v["annual_by_currency"] == {"CHF": 12000} and v["currency"] == "CHF" and v["total_currency"] == "CHF"
    assert d["counterparties"][0]["annual_by_currency"] == {"CHF": 12000}
    assert check_data(d)[0] == []
    assert "ILS" not in json.dumps(v)


@NODE
def test_chf_is_formatted_with_its_code_in_every_template_output(tmp_path):
    s, p = "b" * 64, "x/chf - חתום.docx"
    ext = make_extract(s, p, currency="CHF", commercials=[row(1000, "תמורה", unit="לחודש")])
    d = assemble.assemble(files((p, s)), {s: ext}, "חברה", T)
    dp, out = str(tmp_path / "d.json"), str(tmp_path / "o.html")
    dump(d, dp)
    build.build(dp, TEMPLATE, out)
    o = node(out, {"m": "money(5000, 'CHF')", "by": "moneyBy({CHF: 12000})", "repo": "V.repo()", "dash": "V.dash()",
                   "rows": "JSON.stringify(repoRows())",
                   "card": "(openAg(%r, 'sum'), document.querySelector('#drawer').innerHTML)" % d["agreements"][0]["id"]},
             tmp_path)
    assert o["m"] == "5 אלף CHF" and o["by"] == "12 אלף CHF"
    for k in ("repo", "dash", "rows", "card"):
        assert "CHF" in o[k] and "₪" not in o[k] and "מטבע לא ידוע" not in o[k], k


# ---------- (2) תיקון כספי לפי רכיב ----------

def test_amendment_changes_one_component_total_is_sum_of_components():
    base = [row(100, "רכיב א", currency="USD", period="שנתי"), row(200, "רכיב ב", currency="USD", period="שנתי")]
    am = dict(row(150, "רכיב א", currency="USD", period="שנתי"), _rank="2026-01-10", component="רכיב א",
              operation="replace", effective_date="2026-02-01")
    r = money.annual(base + [am])
    assert r["by_currency"] == {"USD": 350}
    comps = {c["component"]: c for c in r["components"]}
    assert comps["רכיב א"]["annual_value"] == 150 and comps["רכיב א"]["source"] == "amendment"
    assert comps["רכיב א"]["effective_date"] == "2026-02-01"
    assert comps["רכיב ב"]["annual_value"] == 200 and comps["רכיב ב"]["source"] == "agreement"
    assert 150 not in r["by_currency"].values()
    assert {"label": "רכיב א", "reason": "הוחלף בתיקון להסכם"} in r["not_counted"]


def test_amendment_add_delete_and_incomplete_pointers():
    base = [row(100, "א", currency="USD", period="שנתי"), row(200, "ב", currency="USD", period="שנתי")]

    def am(label, value=30, **kw):
        return dict(row(value, label, currency="USD", period="שנתי"), _rank="2026-01-10", **kw)
    r = money.annual(base + [am("ג", component="ג", operation="add", effective_date="2026-03-01"),
                             am("ב", value=None, component="ב", operation="delete", effective_date="2026-03-01")])
    assert r["by_currency"] == {"USD": 130}
    # חסר רכיב / פעולה / תאריך תוקף: לא נספר, והשווי לא משתנה
    for bad in (dict(operation="replace", effective_date="2026-03-01"), dict(component="א", effective_date="2026-03-01"),
                dict(component="א", operation="replace"),
                dict(component="א", operation="merge", effective_date="2026-03-01")):
        r = money.annual(base + [am("א", **bad)])
        assert r["by_currency"] == {"USD": 300}, bad
        assert any("בלי רכיב, פעולה או תאריך תוקף" in n["reason"] for n in r["not_counted"])
    # תיקון שטרם נכנס לתוקף
    r = money.annual(base + [am("א", component="א", operation="replace", effective_date="2027-01-01")], None,
                     as_of="2026-10-22")
    assert r["by_currency"] == {"USD": 300}


def test_assemble_amendment_to_one_component_keeps_the_other():
    s1, s2 = "c" * 64, "d" * 64
    head = make_extract(s1, "x/a - חתום.docx", currency="USD",
                        commercials=[row(100, "רכיב א", period="שנתי"), row(200, "רכיב ב", period="שנתי")])
    kid = make_extract(s2, "x/תוספת 1 - חתום.docx", doc_kind="amendment", title="תוספת 1",
                       relation={"kind": "amendment", "parent_hint": "הסכם מיום 1.3.2025"},
                       dates={"signed": "2026-01-10", "start": None, "end": None}, events=[], currency="USD",
                       commercials=[row(150, "רכיב א", period="שנתי", component="רכיב א", operation="replace",
                                        effective_date="2026-02-01")])
    d = assemble.assemble(files(("x/a - חתום.docx", s1), ("x/תוספת 1 - חתום.docx", s2)), {s1: head, s2: kid},
                          "חברה", T)
    v = d["agreements"][0]["value"]
    assert v["annual_by_currency"] == {"USD": 350} and v["annual"] == 350
    assert sorted(c["annual_value"] for c in v["components"]) == [150, 200]
    assert check_data(d)[0] == []


def test_extraction_validation_rejects_bad_operation_and_date():
    s = "e" * 64
    ext = make_extract(s, "x/a - חתום.docx", commercials=[row(1, "א", operation="merge", effective_date="soon")])
    res = check_extraction(ext)
    text = "\n".join(res[0] if isinstance(res, tuple) else res)
    assert "operation" in text and "effective_date" in text


@NODE
def test_template_shows_component_rows_not_just_the_total(tmp_path):
    s1, s2 = "c" * 64, "d" * 64
    head = make_extract(s1, "x/a - חתום.docx", currency="USD",
                        commercials=[row(100, "רכיב א", period="שנתי"), row(200, "רכיב ב", period="שנתי")])
    kid = make_extract(s2, "x/תוספת 1 - חתום.docx", doc_kind="amendment", title="תוספת 1",
                       relation={"kind": "amendment", "parent_hint": "הסכם מיום 1.3.2025"},
                       dates={"signed": "2026-01-10", "start": None, "end": None}, events=[], currency="USD",
                       commercials=[row(150, "רכיב א", period="שנתי", component="רכיב א", operation="replace",
                                        effective_date="2026-02-01")])
    d = assemble.assemble(files(("x/a - חתום.docx", s1), ("x/תוספת 1 - חתום.docx", s2)), {s1: head, s2: kid},
                          "חברה", T)
    dp, out = str(tmp_path / "d.json"), str(tmp_path / "o.html")
    dump(d, dp)
    build.build(dp, TEMPLATE, out)
    card = node(out, {"c": "(openAg(%r, 'sum'), document.querySelector('#drawer').innerHTML)" % d["agreements"][0]["id"]},
                tmp_path)["c"]
    assert "רכיב א" in card and "רכיב ב" in card and "350" in card


# ---------- (3) עותק מצומצם ----------

HID_TITLE, HID_CP, HID_FILE = "ZQTITLE7731", "ZQCOUNTERPARTY8842", "ZQFILE1120"
HID_QUOTE, HID_AMT_M = "ZQQUOTE9953 clause text", 7600000
HID_AMT_Y = str(HID_AMT_M * 12)
MARKERS = [HID_TITLE, HID_FILE, "ZQQUOTE9953", str(HID_AMT_M), HID_AMT_Y, "ZQEVENT4410"]


def _dataset():
    rows = []
    specs = [("הסכם גלוי א", "צד גלוי בע\"מ", "visible-a", 1000, "services", "ציטוט גלוי"),
             ("הסכם גלוי ב", "ZQSHARED בע\"מ", "visible-b", 2000, "services", "ציטוט גלוי ב"),
             (HID_TITLE, "ZQSHARED בע\"מ", HID_FILE, HID_AMT_M, "insurance", HID_QUOTE),
             ("הסכם מוסתר שני", HID_CP, "hid2", 55, "insurance", "רגיש")]
    for i, (title, cpn, fname, val, tcode, quote) in enumerate(specs):
        s, p = str(i + 1) * 64, "x/%s - חתום.docx" % fname
        label = "ZQEVENT4410 מועד" if val == HID_AMT_M else "מועד רגיל"
        ev = dict(make_extract(s, p)["events"][0], label=label, quote=quote)
        rows.append((p, s, make_extract(s, p, title=title, counterparty=cp(cpn), type_code=tcode, currency="CHF",
                                        events=[ev], commercials=[row(val, "תמורה", unit="לחודש", quote=quote)])))
    return assemble.assemble(files(*[(p, s) for p, s, _ in rows]), {s: e for _, s, e in rows}, "חברה", T)


def _hidden_id(d):
    return {a["title"]: a["id"] for a in d["agreements"]}[HID_TITLE]


def test_restrict_removes_hidden_agreement_and_everything_derived():
    d = _dataset()
    hid = _hidden_id(d)
    assert all(m in json.dumps(d, ensure_ascii=False) for m in MARKERS)
    r = build.restrict(d, hide_ids=[hid])
    blob = json.dumps(r, ensure_ascii=False)
    for m in MARKERS:
        assert m not in blob, m
    assert hid not in blob and r["meta"]["audience"] == "restricted"
    for k in ("events", "commercials", "footnotes", "review_queue", "timeline"):
        assert all(x.get("agreementId") != hid for x in r[k]), k
    assert len(r["agreements"]) == 3
    # הצד שכנגד המשותף נשאר, אך סכומו מחושב מההסכמים הנותרים בלבד
    shared = [c for c in r["counterparties"] if c["name"].startswith("ZQSHARED")][0]
    assert shared["annual_by_currency"] == {"CHF": 24000} and hid not in shared["agreements"]
    assert HID_TITLE in json.dumps(d, ensure_ascii=False), "the input data must not be modified"


def test_restrict_by_type_and_failures():
    d = _dataset()
    r = build.restrict(d, hide_types=["insurance"])
    assert len(r["agreements"]) == 2
    blob = json.dumps(r, ensure_ascii=False)
    assert HID_CP not in blob and HID_TITLE not in blob and HID_AMT_Y not in blob
    with pytest.raises(build.AudienceError):
        build.restrict(d)
    with pytest.raises(build.AudienceError):
        build.restrict(d, hide_ids=["ag-does-not-exist"])
    with pytest.raises(build.AudienceError):
        build.restrict(d, hide_types=["no_such_type"])


@NODE
def test_restricted_file_has_none_of_the_markers_full_file_has_them(tmp_path):
    d = _dataset()
    hid = _hidden_id(d)
    dp = str(tmp_path / "d.json")
    dump(d, dp)
    full, res = str(tmp_path / "full.html"), str(tmp_path / "restricted.html")
    build.build(dp, TEMPLATE, full)
    build.build(dp, TEMPLATE, res, audience="restricted", hide_ids=[hid])
    with open(full, "rb") as fh:
        fb = fh.read()
    with open(res, "rb") as fh:
        rb = fh.read()
    for m in MARKERS:
        assert m.encode() in fb, m
        assert m.encode() not in rb, m
    searches = ",".join("'%s'" % m for m in (HID_TITLE, "ZQSHARED", "ZQQUOTE9953", "ZQEVENT4410"))
    exprs = {"rows": "JSON.stringify(repoRows())", "sum": "JSON.stringify(sumBy(D.agreements))", "dash": "V.dash()",
             "repo": "V.repo()", "money": "V.money()",
             "hits": "[%s].map(m => (document.querySelector('#q').value = m, AG().length))" % searches}
    o_full, o_res = node(full, exprs, tmp_path), node(res, exprs, tmp_path)
    assert o_full["hits"] == [1, 2, 1, 1]  # באינדקס החיפוש של העותק המלא
    assert o_res["hits"] == [0, 1, 0, 0]  # בעותק המצומצם נשאר רק ההסכם הגלוי של הצד המשותף
    for k in ("rows", "sum", "dash", "repo", "money"):
        for m in MARKERS:
            assert m not in o_res[k], (k, m)
    assert HID_TITLE in o_full["rows"] and json.loads(o_full["sum"]) == {"CHF": 91236660}
    assert json.loads(o_res["sum"]) == {"CHF": 36660}


def test_cli_restricted_flags(tmp_path):
    d = _dataset()
    dp, out = str(tmp_path / "d.json"), str(tmp_path / "r.html")
    dump(d, dp)

    def cli(*args):
        return subprocess.run([sys.executable, CLI, "build", "--data", dp, "--out", out, *args],
                              capture_output=True, text=True, encoding="utf-8")
    r = cli("--audience", "restricted", "--hide-type", "insurance")
    assert r.returncode == 0, r.stdout + r.stderr
    with open(out, encoding="utf-8") as fh:
        assert HID_TITLE not in fh.read()
    assert cli("--audience", "restricted").returncode == 1  # בלי מה להסתיר אין עותק מצומצם
    assert cli("--hide-id", "x").returncode == 1  # הסתרה בלי עותק מצומצם
