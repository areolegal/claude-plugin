# -*- coding: utf-8 -*-
"""בדיקות לבודק ולבונה של מעריך הסיכונים, על קוד הייחוס של ענבל.

* **הבודק** (`validate_data.py`): שני המרשמים של סבב 2 עוברים בו כמו שהם, ומרשם
  בסכמה הישנה נכשל בקוד 3 ולא בקריסה.
* **הבונה** (`build_risk_report.py`): כותב רק לתיקיית העסקה, בשם הקבוע; אינו
  דורס דוח של עסקה אחרת; מסרב לעותק תבנית בתוך תיקיית הלקוח; ודוח חקר הישות
  נבנה מהתבנית שלו.
* **התבנית שהשירות מגיש** עוברת את הבדיקה הסטטית (אין טעינה מהרשת), ובדפדפן
  אמיתי, כשיש Chrome או Edge: גוף לא ריק, בלי שגיאות JavaScript, בלי בקשות
  חיצוניות, ועד שמונה עמודים.
"""
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

PLUGIN = Path(__file__).resolve().parents[1]
ROOT = PLUGIN.parent
LIB = PLUGIN / "areolegal" / "lib"
S = PLUGIN / "areolegal" / "skills" / "contract-risk-assessor" / "scripts"
FX = LIB / "tests" / "fixtures" / "risk"
CONTENT = ROOT / "server" / "content" / "contract-risk-assessor"
RISK_TPL = CONTENT / "risk-report-template.html"
ENTITY_TPL = CONTENT / "entity-report-template.html"

sys.path.insert(0, str(LIB))


def _run(script, *args):
    return subprocess.run([sys.executable, "-B", str(S / script)] + [str(x) for x in args],
                          capture_output=True, text=True, cwd=str(S))


def _deal(tmp_path, register="c2_register.json"):
    reg = json.loads((FX / register).read_text(encoding="utf-8"))
    d = tmp_path / "Areo-נתונים" / "transactions" / reg["meta"]["transaction_id"]
    d.mkdir(parents=True)
    (d / "risk-register.json").write_text(json.dumps(reg, ensure_ascii=False), encoding="utf-8")
    tpl = tmp_path / "tmp-templates"
    tpl.mkdir()
    shutil.copy(RISK_TPL, tpl / RISK_TPL.name)
    shutil.copy(ENTITY_TPL, tpl / ENTITY_TPL.name)
    return d, tpl


@pytest.mark.parametrize("name", ["c1b", "c2"])
def test_the_round_two_registers_pass_as_they_are(name):
    r = _run("validate_data.py", "--data", FX / ("%s_register.json" % name),
             "--corpus", FX / ("%s_corpus.json" % name))
    assert r.returncode == 0, r.stdout + r.stderr
    assert "שגיאות: 0" in r.stdout


def test_an_old_schema_register_fails_with_three_and_no_traceback():
    r = _run("validate_data.py", "--data", PLUGIN / "tests" / "fixtures" / "risk_register_old_schema.json")
    assert r.returncode == 3, r.stdout + r.stderr
    assert "Traceback" not in r.stderr and "אינו נבנה" in r.stdout


def test_the_entity_report_is_checked_too():
    r = _run("validate_data.py", "--data", FX / "c2_register.json", "--entity", FX / "c2_entity_report.json")
    assert r.returncode in (0, 3), r.stdout + r.stderr
    assert "Traceback" not in r.stderr


def test_the_report_is_written_to_the_deal_folder_under_the_fixed_name(tmp_path):
    d, tpl = _deal(tmp_path)
    r = _run("build_risk_report.py", "--data", d / "risk-register.json", "--template", tpl / RISK_TPL.name)
    assert r.returncode == 0, r.stdout + r.stderr
    html = d / "Areo Workspace - סיכונים.html"
    assert html.exists()
    assert sorted(p.name for p in d.iterdir()) == ["Areo Workspace - סיכונים.html", "risk-register.json"]
    assert "\u2014" not in html.read_text(encoding="utf-8")
    from risk import render_check as RC
    if RC.find_browser():
        # בדיקת העמודים רצה בכל בנייה, ולא רק בבדיקות השחרור
        assert "בדיקת העמודים: עברה" in r.stdout, r.stdout


def test_a_report_of_another_deal_is_never_overwritten(tmp_path):
    d, tpl = _deal(tmp_path)
    assert _run("build_risk_report.py", "--data", d / "risk-register.json",
                "--template", tpl / RISK_TPL.name).returncode == 0
    html = d / "Areo Workspace - סיכונים.html"
    before = html.read_text(encoding="utf-8")
    other = json.loads((d / "risk-register.json").read_text(encoding="utf-8"))
    other["meta"]["transaction_id"] = "deal_other_2026-10-15"
    src = tmp_path / "other.json"
    src.write_text(json.dumps(other, ensure_ascii=False), encoding="utf-8")
    r = _run("build_risk_report.py", "--data", src, "--deal", d, "--template", tpl / RISK_TPL.name)
    assert r.returncode == 3, r.stdout + r.stderr
    assert html.read_text(encoding="utf-8") == before


def test_a_template_copy_inside_the_deal_folder_is_refused(tmp_path):
    d, tpl = _deal(tmp_path)
    inside = d / RISK_TPL.name
    shutil.copy(RISK_TPL, inside)
    r = _run("build_risk_report.py", "--data", d / "risk-register.json", "--template", inside)
    assert r.returncode == 1, r.stdout + r.stderr
    assert not (d / "Areo Workspace - סיכונים.html").exists()


def test_the_entity_report_builds_from_its_own_template(tmp_path):
    d, tpl = _deal(tmp_path)
    (d / "entity-report.json").write_bytes((FX / "c2_entity_report.json").read_bytes())
    r = _run("build_risk_report.py", "--kind", "entity", "--data", d / "entity-report.json",
             "--template", tpl / ENTITY_TPL.name)
    assert r.returncode == 0, r.stdout + r.stderr
    assert (d / "Areo Workspace - חקר ישות.html").exists()


@pytest.mark.parametrize("tpl", [RISK_TPL, ENTITY_TPL], ids=["risk", "entity"])
def test_the_served_templates_load_nothing_from_the_network(tpl):
    from risk.render_check import static_checks
    assert static_checks(tpl.read_text(encoding="utf-8")) == []


def test_the_served_risk_template_renders_in_a_real_browser(tmp_path):
    from risk import render_check as RC
    if not RC.find_browser():
        pytest.skip("אין Chrome או Edge במחשב הזה")
    out = tmp_path / "render"
    r = subprocess.run([sys.executable, "-B", str(LIB / "risk" / "render_check.py"), "--template", str(RISK_TPL),
                        "--register", str(FX / "c2_register.json"), "--out", str(out)],
                       capture_output=True, text=True, timeout=300)
    res = json.loads((out / "render_check.json").read_text(encoding="utf-8"))
    assert res["verdict"] == "PASS", (res.get("fails"), r.stdout[-2000:])
    assert not res["external_requests"] and not res["js_exceptions"]
    assert res["body_pages"] <= 8


def _fetch(tmp_path, *args):
    d = tmp_path / "deal_net_2026-10-15"
    d.mkdir(exist_ok=True)
    return d, _run("fetch_source.py", "--deal", d, "--source-id", "SRC-01", *args)


def test_a_domain_outside_the_approved_list_is_refused_before_any_request(tmp_path):
    d, r = _fetch(tmp_path, "--url", "https://www.calcalist.co.il/x", "--purpose", "חוק", "--question", "Q1")
    assert r.returncode == 3
    assert "אינו ברשימה המורשית" in json.loads(r.stdout)["reason"]
    assert not (d / "sources").exists()


def test_a_client_detail_in_the_query_stops_the_request(tmp_path):
    prof = tmp_path / "p.json"
    prof.write_text(json.dumps({"organization_name": "חברת בדיקה"}, ensure_ascii=False), encoding="utf-8")
    d, r = _fetch(tmp_path, "--url", "https://www.gov.il/he/search?q=חברת בדיקה", "--purpose", "רישוי",
                  "--question", "Q1", "--profile", prof)
    assert r.returncode == 3 and "פרט של הלקוח" in json.loads(r.stdout)["reason"]


def test_the_counterparty_name_is_refused_in_a_regulatory_query_but_not_in_entity_research(tmp_path):
    d, r = _fetch(tmp_path, "--url", "https://www.gov.il/he/search?q=Acme", "--purpose", "רישוי",
                  "--question", "Q1", "--counterparty", "Acme")
    assert r.returncode == 3 and "פרט של הלקוח" in json.loads(r.stdout)["reason"]
    d, r = _fetch(tmp_path, "--url", "https://www.calcalist.co.il/?q=Acme", "--purpose", "רישום",
                  "--question", "Q2", "--counterparty", "Acme", "--kind", "entity")
    # בחקר ישות השם אינו עוצר; הדומיין עדיין כן
    assert "אינו ברשימה המורשית" in json.loads(r.stdout)["reason"]


def test_a_single_document_is_extracted_and_its_quotes_are_checked_against_it(tmp_path):
    """חילוץ תמיד, גם למסמך יחיד; והבודק קורא את החילוץ בפורמט של ענבל, כך שציטוט
    שאינו במסמך נתפס, ולא נופל לשגיאת מבנה."""
    out = tmp_path / "corpus.json"
    draft = LIB / "tests" / "fixtures" / "orchestrator" / "c1b_counterparty_draft.docx"
    r = _run("extract_corpus.py", draft, "--out", out)
    assert r.returncode == 0, r.stdout + r.stderr
    sys.path.insert(0, str(S))
    import validate_data as VD
    docs = VD.corpus_for_check(json.loads(out.read_text(encoding="utf-8")))
    assert len(docs) == 1 and docs[0]["file"] == draft.name and docs[0]["parts"]
    r = _run("validate_data.py", "--data", FX / "c1b_register.json", "--corpus", out)
    assert r.returncode == 3 and "אין טקסט מקור למסמך" in r.stdout
    assert "אינו במבנה של הסכמה" not in r.stdout


def test_the_word_report_has_the_same_structure_and_the_privilege_band(tmp_path):
    docx = pytest.importorskip("docx")
    import zipfile
    d, _ = _deal(tmp_path)
    r = _run("build_risk_docx.py", "--data", d / "risk-register.json")
    assert r.returncode == 0, r.stdout + r.stderr
    out = next(d.glob("*דוח סיכונים*.docx"))
    text = "\n".join(p.text for p in docx.Document(str(out)).paragraphs)
    order = ["התמונה במבט אחד", "השורה התחתונה", "1. הסיכונים", "2. סתירות", "3. צירופים", "4. הסיכונים הקריטיים",
             "5. מה לא נבדק", "נספח: ציטוטים מילוליים"]
    pos = [text.index(x) for x in order]
    assert pos == sorted(pos)
    with zipfile.ZipFile(out) as z:
        names = z.namelist()
        hdr = "".join(z.read(n).decode("utf-8") for n in names if re.match(r"word/(header|footer)\d*\.xml", n))
        rels = z.read("word/_rels/document.xml.rels").decode("utf-8")
    assert "טיוטה, טעונה אישור" in hdr
    assert "nevo.co.il" in rels and "TargetMode=\"External\"" in rels
