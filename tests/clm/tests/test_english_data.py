"""נתונים דו-לשוניים: meta.lang קובע את שפת כל מחרוזת שההרכבה כותבת ללקוח, והמפתחות והקודים זהים בשתי השפות.

המאגר כאן נבנה מחילוצים באנגלית בלבד. לכן כל אות עברית בפלט האנגלי באה מההרכבה עצמה, חוץ מקודים שנשארים
כפי שהם בכל שפה: קטגוריות (category) ותקופת תמורה (period).
"""
import datetime as dt
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys

import pytest

from clm import assemble, build, catalog, i18n
from clm.validate import check_data
from helpers import CATEGORIES, make_extract

import clm_paths  # noqa: E402
ROOT = clm_paths.SKILL
TODAY = dt.date(2026, 10, 22)
HEB = re.compile("[֐-׿]")
CODE_KEYS = {"category", "period"}
VOICE = clm_paths.VOICE


def sha(c):
    return c * 64


def cov():
    return [{"category": c, "status": "not_checked", "note": "Not checked in this reading"} for c in CATEGORIES]


def ev(code, label, date, **kw):
    row = {"event_code": code, "label": label, "date": date, "relative": False, "trigger": "", "clause": "Section 4",
           "quote": "The parties agree to the terms of Section 4 as written.", "obligor": "us",
           "consequence": catalog.load_events("he")[code]["consequence"], "impact": "material", "if_nothing": "",
           "action": "", "notice_days": None, "recurrence": None, "renewal_months": None, "renewal_max": None,
           "computed": False}
    row.update(kw)
    return row


def ext(c, path, title, cp, **kw):
    base = dict(title=title, type_code="services", type_label="Managed services",
                counterparty={"name": cp, "company_number": None, "notice_address": None},
                our_role={"value": "Customer", "source": "user"}, events=[], commercials=[], coverage=cov(),
                dates={"signed": "2025-01-01", "start": "2025-01-01", "end": "2027-12-31"})
    base.update(kw)
    return make_extract(sha(c), path, **base)


def dataset():
    exts = {
        sha("a"): ext("a", "deals/Hosting agreement - signed.docx", "Cloud hosting agreement", "Nimbus Hosting Ltd",
                      dates={"signed": "2023-01-01", "start": "2023-01-01", "end": "2024-12-31"},
                      governing_law="The laws of the State of Israel",
                      term={"kind": "fixed", "initial_months": 24, "starts_on": "start", "clause": "Section 3",
                            "quote": "The term is 24 months."},
                      events=[ev("nonrenewal_notice", "Non-renewal notice deadline", "2024-10-01", notice_days=90,
                                 renewal_months=12, impact="critical"),
                              ev("payment_milestone", "Quarterly payment", "2026-01-15", recurrence={"months": 3}),
                              ev("price_adjustment", "Annual indexation", "2025-01-01",
                                 recurrence={"months": 12, "max": 1})],
                      commercials=[{"category": "תעריף", "label": "Monthly fee", "value": 1000, "unit": "USD",
                                    "period": "חודשי", "currency": "USD", "clause": "Section 7", "quote": "USD 1,000 a month."},
                                   {"category": "תעריף", "label": "Seat fee", "value": 20, "unit": "per seat",
                                    "period": "חודשי", "currency": "USD", "clause": "Section 7", "quote": "USD 20 per seat."}],
                      key_clauses=[{"clause_code": "exclusivity", "summary": "Exclusive hosting for the customer",
                                    "value": "Exclusive", "clause": "Section 9", "quote": "The customer shall use only Nimbus.",
                                    "bound_party": "contracting", "bound_party_name": None}],
                      key_clauses_checked=True),
        sha("b"): ext("b", "deals/Reseller agreement - comments.docx", "Reseller agreement", "",
                      doc_kind="negotiation_version", type_code="distribution", version_by="them",
                      version_date="2026-09-01", our_role={"value": "", "source": "none"},
                      dates={"signed": None, "start": None, "end": None},
                      facts=[{"code": "negotiation_stopped", "label": "Negotiation stopped", "value": "Talks ended in May",
                              "clause": "Email", "quote": "We will not continue the negotiation."}]),
        sha("c"): ext("c", "deals/Widget supply - signed.docx", "Widget supply agreement", "Widget Works Inc",
                      type_code="widgets", type_label="Widget supply", our_role={"value": "Buyer", "source": "suggested"},
                      dates={"signed": "2025-02-01", "start": "2025-02-01", "end": None},
                      term={"kind": "indefinite", "clause": "Section 2", "quote": "This agreement has no fixed term."},
                      events=[ev("claim_window", "Claim deadline", None)]),
        sha("d"): ext("d", "deals/Office lease - signed.docx", "Office lease", "Tower Estates Ltd", type_code="real_estate",
                      our_role={"value": "Tenant", "source": "user"},
                      dates={"signed": "2024-06-01", "start": "2024-07-01", "end": "2027-06-30"},
                      renewal={"kind": "option", "period_months": 24, "max_count": 1, "holder": "contracting",
                               "holder_name": None, "notice_days": 90, "clause": "Section 5", "quote": "The tenant may extend."},
                      type_fields={"area": "500 sqm"}),
        sha("e"): ext("e", "deals/Office lease amendment - draft.docx", "Office lease amendment", "Tower Estates Ltd",
                      doc_kind="amendment", type_code="real_estate", relation={"kind": "amendment", "parent_hint": "Office lease"},
                      dates={"signed": "2026-05-01", "start": None, "end": "2028-06-30"}),
        sha("f"): ext("f", "deals/NDA template - signed.docx", "NDA template", "Any party", doc_kind="template"),
        sha("g"): ext("g", "deals/Board memo.docx", "Board memo", "Board", doc_kind="non_agreement"),
        sha("h"): ext("h", "deals/Consulting - signed.docx", "Consulting agreement", "Sage Advisors Ltd",
                      dates={"signed": "2026-01-01", "start": "2026-01-01", "end": None},
                      term={"kind": "fixed", "initial_months": 12, "starts_on": "start", "clause": "Section 2",
                            "quote": "The term is 12 months."}),
    }
    files = [(p["file"], s, "new") for s, p in exts.items()]
    files += [("deals/Old.docx", sha("i"), "removed"), ("deals/New.docx", sha("j"), "new"),
              ("deals/Locked.docx", sha("k"), "unreadable")]
    scan = {"files": [{"path": p, "sha256": s, "status": st, "abs": None, "duplicate_of": None} for p, s, st in files]}
    scan["files"].append({"path": "deals/Copy.docx", "sha256": sha("a"), "status": "duplicate", "abs": None,
                          "duplicate_of": "deals/Hosting agreement - signed.docx"})
    bad = [{"file": sha("m") + ".json", "problems": ["broken"]}]
    return scan, exts, bad


def run(lang, previous=None):
    scan, exts, bad = dataset()
    home = "Israel" if lang == "en" else "ישראל"   # כמו שה-CLI גוזר ממדינת ההתאגדות שבפרופיל
    return assemble.assemble(scan, exts, "Acme Ltd", TODAY, bad_extracts=bad, previous=previous, lang=lang,
                             home_law=home)


def walk(x, key=None, path=""):
    """(נתיב, מפתח, מחרוזת) לכל מחרוזת בפלט."""
    if isinstance(x, dict):
        for k, v in x.items():
            yield from walk(v, k, path + "." + str(k))
    elif isinstance(x, list):
        for i, v in enumerate(x):
            yield from walk(v, key, "%s[%d]" % (path, i))
    elif isinstance(x, str):
        yield path, key, x


def shape(x):
    """מבנה הפלט בלי הערכים: מפתחות, אורכי רשימות וסוגי ערכים."""
    if isinstance(x, dict):
        return {k: shape(v) for k, v in x.items()}
    if isinstance(x, list):
        return [shape(v) for v in x]
    return type(x).__name__


CLIENT = {"group", "text", "note", "action", "state_note", "superseded_note", "if_nothing", "basis", "reason", "label",
          "family", "counterparty"}


def client_strings(data):
    """המחרוזות שההרכבה כותבת ללקוח (לא שמות קבצים, מזהים או ציטוטים)."""
    out = [s for p, k, s in walk(data) if k in CLIENT and not p.startswith((".footnotes", ".catalog"))]  # הקטלוג: תבניות עם מצייני מקום
    for a in data["agreements"]:
        out += a["value"]["unknown_currency"]
    return out


@pytest.fixture(scope="module")
def both():
    return run("he"), run("en")


def test_english_catalog_covers_every_code_and_keeps_placeholders():
    he_ev, en_ev = catalog.load_events("he"), catalog.load_events("en")
    assert set(he_ev) == set(en_ev)
    for code, e in en_ev.items():
        for k in ("label", "action", "if_nothing"):
            assert e[k] != he_ev[code][k] and not HEB.search(e[k]), (code, k)
        assert set(re.findall(r"{(\w+)}", e["action"])) == set(re.findall(r"{(\w+)}", he_ev[code]["action"])), code
        assert {k: v for k, v in e.items() if k not in ("label", "action", "if_nothing")} == \
            {k: v for k, v in he_ev[code].items() if k not in ("label", "action", "if_nothing")}, code
    he_kc, en_kc = catalog.load_key_clauses("he"), catalog.load_key_clauses("en")
    assert set(he_kc) == set(en_kc) and not any(HEB.search(v) for v in en_kc.values())
    he_t, en_t = catalog.load_types("he"), catalog.load_types("en")
    assert set(he_t) == set(en_t)
    for code, t in en_t.items():
        assert not HEB.search(t["label"]) and t["aliases"] == he_t[code]["aliases"], code
        assert [f["key"] for f in t["type_fields"]] == [f["key"] for f in he_t[code]["type_fields"]], code
        assert not any(HEB.search(f["label"]) for f in t["type_fields"]), code
    text = open(os.path.join(ROOT, "catalog", "en.json"), encoding="utf-8").read()
    assert chr(0x2013) not in text and chr(0x2014) not in text
    # מחוץ להרכבה הקטלוג בעברית, כפי שהיה
    assert catalog.load_events()["term_end"]["label"] == "תום תקופה" and i18n.lang() == "he"


def test_meta_lang_and_language_does_not_leak_after_assemble(both):
    he, en = both
    assert he["meta"]["lang"] == "he" and en["meta"]["lang"] == "en"
    assert en["meta"]["home_law"] == "Israel" and he["meta"]["home_law"] == "ישראל"
    assert i18n.lang() == "he"
    # בלי lang: השפה של ההרצה הקודמת נשמרת
    assert run(None, previous=en)["meta"]["lang"] == "en" and run(None)["meta"]["lang"] == "he"


def test_english_data_has_no_hebrew_outside_codes(both):
    _, en = both
    leaks = [(p, s) for p, k, s in walk(en) if k not in CODE_KEYS and HEB.search(s)]
    assert not leaks, leaks[:10]


def test_english_data_covers_the_review_kinds_and_notes(both):
    _, en = both
    kinds = {r["kind"] for r in en["review_queue"]}
    assert {"role", "counterparty", "family", "non_agreement", "outcome", "verify_critical", "duplicate", "not_extracted",
            "bad_extract", "source_removed", "unreadable", "kind_conflict", "missing_core", "abandoned_evidence"} <= kinds
    groups = {r["kind"]: r["group"] for r in en["review_queue"]}
    assert groups["role"] == "Company's side in the agreement" and groups["outcome"] == "Outcome of a passed date"
    ags = {a["title"]: a for a in en["agreements"]}
    assert ags["Reseller agreement"]["counterparty"] == "[to complete]"
    assert ags["Widget supply agreement"]["family"] == "Widget supply"
    assert ags["Cloud hosting agreement"]["family"] == "Services and outsourcing"
    assert ags["Office lease"]["type_fields"][0] == {"label": "Leased area", "value": "500 sqm"}
    assert ags["Consulting agreement"]["dates"]["end_basis"]["note"].startswith("Computed: start 1.1.2026 plus 12 months")
    assert ags["Office lease"]["dates"]["current_end_basis"]["note"].startswith("The end stands until")
    assert ags["Widget supply agreement"]["dates"]["current_end_basis"]["note"] == "No end date"
    assert ags["Cloud hosting agreement"]["law_class"] == "home"
    assert ags["Cloud hosting agreement"]["value"]["not_counted"] == [{"label": "Seat fee", "reason": "Rate per unit, depends on volume"}]
    assert ags["Cloud hosting agreement"]["value"]["basis"] == "Computed from the payments in the agreement"
    assert en["key_clause_labels"]["exclusivity"] == "Exclusivity and territory"
    assert en["catalog"]["term_end"]["label"] == "End of term"
    details = en["registers"]["restriction_details"][ags["Cloud hosting agreement"]["id"]]
    assert details[0]["label"] == "Exclusivity and territory"
    actions = [e["action"] for e in en["events"]]
    assert any(a.startswith("Decide by ") and "Nimbus Hosting Ltd" in a for a in actions)
    assert any("Confirm what happened" in (e.get("state_note") or "") for e in en["events"])
    missing = [r["text"] for r in en["review_queue"] if r["kind"] == "missing_core"]
    assert any("Missing core field in \"Cloud hosting agreement\": Signatories" in t for t in missing)


def test_hebrew_and_english_have_the_same_keys_and_codes(both):
    he, en = both
    assert shape(he) == shape(en)
    assert [a["id"] for a in he["agreements"]] == [a["id"] for a in en["agreements"]]
    assert [(e["id"], e["event_code"], e["state"]) for e in he["events"]] == \
        [(e["id"], e["event_code"], e["state"]) for e in en["events"]]
    assert [r["kind"] for r in he["review_queue"]] == [r["kind"] for r in en["review_queue"]]
    assert he["footnotes"] == en["footnotes"]
    # העברית לא השתנתה: אותן מחרוזות כמו בלי lang
    assert run(None) == he


def test_carried_agreement_in_english(both):
    _, en = both
    scan, exts, bad = dataset()
    for f in scan["files"]:
        if f["path"] == "deals/Hosting agreement - signed.docx":
            f.update(status="changed", sha256=sha("n"))
    again = assemble.assemble(scan, exts, "Acme Ltd", TODAY, bad_extracts=bad, previous=en)
    assert again["meta"]["lang"] == "en"
    carried = [a for a in again["agreements"] if a.get("extraction_pending")]
    assert carried and carried[0]["title"] == "Cloud hosting agreement"
    texts = [r["text"] for r in again["review_queue"] if r["kind"] == "not_extracted"]
    assert any("is shown as last read" in t for t in texts)
    leaks = [(p, s) for p, k, s in walk(again) if k not in CODE_KEYS and HEB.search(s)]
    assert not leaks, leaks[:10]


def test_both_languages_pass_validation_and_the_page_gets_meta_lang(both, tmp_path):
    for data in both:
        errors, _ = check_data(data)
        # קובץ חילוץ שנפסל אינו שקט: זו השגיאה היחידה, והיא מציינת את הקובץ ואת הסיבה
        assert len(errors) == 1 and sha("m") + ".json" in errors[0] and "broken" in errors[0], errors[:5]
    path = tmp_path / "clm-data.json"
    path.write_text(json.dumps(both[1], ensure_ascii=False), encoding="utf-8")
    out = tmp_path / "page.html"
    build.build(str(path), os.path.join(ROOT, "assets", "workspace-template.html"), str(out))
    assert '"lang": "en"' in out.read_text(encoding="utf-8")


@pytest.mark.skipif(not os.path.exists(VOICE), reason="voice_check.py של הכללים המשותפים אינו לצד הסוכן")
def test_generated_client_strings_follow_the_areo_voice(both):
    sys.dont_write_bytecode = True
    spec = importlib.util.spec_from_file_location("areo_voice_check", VOICE)
    voice = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(voice)
    for data in both:
        found = [(s, f["term"]) for s in client_strings(data) for f in voice.check_text(s)]
        assert not found, found[:10]


def test_cli_reads_the_language_from_the_profile(tmp_path):
    sys.path.insert(0, os.path.join(ROOT, "scripts"))
    import clm_cli
    assert clm_cli._profile_lang(str(tmp_path)) is None
    (tmp_path / "פרופיל-לקוח.json").write_text(json.dumps({"display_language": "en"}), encoding="utf-8")
    assert clm_cli._profile_lang(str(tmp_path)) == "en"
    (tmp_path / "פרופיל-לקוח.json").write_text(json.dumps({"display_language": "en", "deliverable_language": "he"}),
                                               encoding="utf-8")
    assert clm_cli._profile_lang(str(tmp_path)) == "he"
    assert assemble.resolve_lang("en") == "en" and assemble.resolve_lang("both") == "he"
    assert assemble.resolve_lang(None, {"meta": {"lang": "en"}}) == "en"
    assert i18n.LANGS == ("he", "en")


def test_english_page_renders_without_hebrew(both, tmp_path):
    if not shutil.which("node"):
        pytest.skip("node אינו מותקן")
    data = both[1]
    data_path, out, ex_path = tmp_path / "data.json", tmp_path / "page.html", tmp_path / "exprs.json"
    data_path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    build.build(str(data_path), os.path.join(ROOT, "assets", "workspace-template.html"), str(out))
    exprs = {"lang": "LANG", "review": "V.review()", "repo": "V.repo()", "dash": "V.dash()", "regs": "V.regs()"}
    for a in data["agreements"]:
        exprs["card:" + a["title"]] = "(openAg(%r, 'sum'), document.querySelector('#drawer').innerHTML)" % a["id"]
    ex_path.write_text(json.dumps(exprs), encoding="utf-8")
    r = subprocess.run(["node", clm_paths.HARNESS, str(out), str(ex_path)],
                       capture_output=True, text=True, encoding="utf-8")
    assert r.returncode == 0, r.stderr
    page = json.loads(r.stdout)
    assert page.pop("lang") == "en"
    assert "Company&#39;s side in the agreement" in page["review"] or "Company's side in the agreement" in page["review"]
    for k, html in page.items():
        assert not HEB.search(re.sub(r"<[^>]+>", " ", html)), k
