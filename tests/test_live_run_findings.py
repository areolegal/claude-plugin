# -*- coding: utf-8 -*-
"""מה שהרצה חיה של Claude עם התוסף מצאה (20.10.2026), ושלא נתפס בשום בדיקה קודמת.

ההרצה: לקוח בדוי עם שלושה הסכמי מנוי חתומים וטיוטה נכנסת, מההקמה ועד הפלייבוק ומחקר
השוק. כל בדיקה כאן היא ממצא אחד מההרצה, וכל אחד מהם הוא שני רכיבים שכל אחד מהם עבר את
הבדיקה של עצמו ולא התאימו זה לזה.
"""
import json
import subprocess
import sys
from pathlib import Path

import pytest

PLUGIN = Path(__file__).resolve().parents[1]
LIB = PLUGIN / "areolegal" / "lib"
PB = PLUGIN / "areolegal" / "skills" / "contract-playbook-builder" / "scripts"
ORCH = PLUGIN / "areolegal" / "skills" / "contract-negotiation-orchestrator" / "scripts"
FIX = LIB / "tests" / "fixtures" / "playbook"
sys.path[:0] = [str(LIB), str(PB)]
pytest.importorskip("docx")

import build_playbook_core as CORE  # noqa: E402
import market_research as MR  # noqa: E402
import validate_playbook_model as V  # noqa: E402
from playbook import status as S  # noqa: E402


def _model(name="mutual_nda_model_good.json"):
    return json.loads((FIX / name).read_text(encoding="utf-8"))


# ---------------------------------------------------------------- הגרעין בסקריפט
def test_the_core_is_built_by_a_script_and_meets_the_negotiator_contract(tmp_path):
    """לא היה סקריפט לגרעין, והגרעין שנכתב ביד נכשל בחוזה מול הנושא ונותן."""
    m = _model()
    m.update(schema_version="2.0", core_version="3.2")   # הפיקסצ'ר הוא קטע, בלי שדות הגרסה
    mp, cp = tmp_path / "playbook-model.json", tmp_path / "playbook-core.json"
    mp.write_text(json.dumps(m, ensure_ascii=False), encoding="utf-8")
    r = subprocess.run([sys.executable, "-B", str(PB / "build_playbook_core.py"), "--model", str(mp)],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    core = json.loads(cp.read_text(encoding="utf-8"))
    assert core["company_role_code"] and core["family_code"]
    for c in core["clauses"]:
        assert c["preferred_wording"] and c["fallback_wording"] and c["fallback_source"], c["id"]
        assert c["policy_ref"] == c["id"]
    r = subprocess.run([sys.executable, "-B", str(ORCH / "check_playbook_contract.py"), str(mp), "--core", str(cp)],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stdout


def test_the_contract_reads_the_schema_field_names():
    """topic_name, rule_id ו-proposed_clause הם השמות של playbook-schema.md."""
    sys.path.insert(0, str(ORCH))
    import check_playbook_contract as C
    rule = _model()["rules"][0]
    assert "topic" not in rule and "policy_ref" not in rule
    assert C.rule_findings(rule, {"fallback_wording": "x", "fallback_source": "areo_proposal"}) == []


# ---------------------------------------------------------------- המאמת מול הסכמה
def test_track_basis_values_of_the_schema_are_valid_and_count_as_company():
    for basis in ("template", "own_paper_repeated", "established", "single", "client_answer"):
        assert basis in V.VALID_TRACK_BASIS
    m = {"rules": [{"traffic_light": {"green": {"basis": "own_paper_repeated"},
                                      "yellow": {"basis": "areo_proposal"}, "red": {"basis": "market_standard"}}}]}
    assert S.company_backed_tracks(m) == 1


def test_research_status_of_the_schema_and_automatic_regulatory_research_are_valid():
    assert {"Performed", "Partial", "NotPerformed"} <= V.VALID_RESEARCH_STATUS


def test_a_draft_rationale_is_checked_by_pass_a_and_not_by_minimum_length():
    errors = []
    r = {"rationale_status": "Draft", "executive_policy_rationale": "קצר.", "green_boundary_rationale": "א.",
         "yellow_boundary_rationale": "ב.", "red_boundary_rationale": "ג.", "internal_evidence_rationale": "ד.",
         "pass_b_pending": [k for k in V.RATIONALE_MIN if k not in V.PASS_A_FIELDS]}
    V.validate_rationale(errors, r, "rules[0].policy_rationale", V.RATIONALE_MIN)
    assert errors == []
    r["pass_b_pending"] = []
    V.validate_rationale(errors, r, "rules[0].policy_rationale", V.RATIONALE_MIN)
    assert any("pass_b_pending" in e for e in errors)


# ---------------------------------------------------------------- הקורפוס והחיפוש
def test_the_corpus_scan_skips_areo_own_folder(tmp_path):
    import build_corpus_manifest as M
    (tmp_path / "Areo-נתונים" / "playbooks").mkdir(parents=True)
    (tmp_path / "Areo-נתונים" / "פרופיל-לקוח.json").write_text("{}", encoding="utf-8")
    (tmp_path / "Areo-נתונים" / "playbooks" / "m.json").write_text("{}", encoding="utf-8")
    (tmp_path / "הסכם.txt").write_text("הסכם שירותים בין הצדדים", encoding="utf-8")
    assert [r["path"] for r in M.scan(tmp_path)] == ["הסכם.txt"]


def test_a_statute_name_from_the_agreements_is_allowed_in_a_legal_query():
    """ה-hook עצר את החיפוש של תקנות אבטחת המידע, כי השם מופיע בהסכמים."""
    corpus = {"documents": [{"paragraphs": [{"text": "ויקיים אמצעי אבטחה סבירים בהתאם לתקנות הגנת הפרטיות "
                                                    "(אבטחת מידע), התשע\"ז-2017."}]}]}
    q = "תקנות הגנת הפרטיות (אבטחת מידע) נוסח עדכני"
    assert MR.query_problem(q, "legal", corpus, None)[0] is None
    assert MR.query_problem(q, "market", corpus, None)[0]          # בשוק אין חריג
    assert MR.query_problem("ויקיים אמצעי אבטחה סבירים", "legal", corpus, None)[0]


# ---------------------------------------------------------------- ה-Word
def test_the_track_meaning_code_is_not_printed_and_placeholder_check_is_narrow(tmp_path):
    import re
    m = _model()
    for r in m["rules"]:
        for t, code in (("green", "Approved"), ("yellow", "AgreeWithComments"), ("red", "NotApproved")):
            r["traffic_light"][t]["meaning"] = code
    m["rules"][0]["clause_issue"] = "הצדדים מבקשים להשלים את ההעברה בתוך 30 יום"
    mp, prof, out = tmp_path / "m.json", tmp_path / "p.json", tmp_path / "pb.docx"
    mp.write_text(json.dumps(m, ensure_ascii=False), encoding="utf-8")
    prof.write_text(json.dumps({"organization_name": "EXAMPLECO"}), encoding="utf-8")
    assert subprocess.run([sys.executable, "-B", str(PB / "build_playbook_docx.py"), "--model", str(mp),
                           "--profile", str(prof), "--out", str(out)], capture_output=True).returncode == 0
    r = subprocess.run([sys.executable, "-B", str(PB / "verify_playbook_docx.py"), "--docx", str(out),
                        "--model", str(mp), "--profile", str(prof)], capture_output=True, text=True,
                       cwd=str(PB))
    assert r.returncode == 0, r.stdout
    import zipfile
    xml = zipfile.ZipFile(out).read("word/document.xml").decode("utf-8")
    assert not re.search(r">(Approved|AgreeWithComments|NotApproved)<", xml)


def test_a_market_playbook_gets_a_sources_chapter_with_real_links(tmp_path):
    """בהרצה החיה ה-Word של פלייבוק שנשען על השוק נכשל, כי לא היה בו פרק המקורות."""
    import zipfile
    m = _model()
    m["market_research"]["status"] = "Performed"
    m["market_research"]["limitations"] = ["אותר, לא נקרא: גוף כלשהו (404), https://not-in-records.example/x"]
    mp, prof, out = tmp_path / "m.json", tmp_path / "p.json", tmp_path / "pb.docx"
    mp.write_text(json.dumps(m, ensure_ascii=False), encoding="utf-8")
    prof.write_text(json.dumps({"organization_name": "EXAMPLECO"}), encoding="utf-8")
    assert subprocess.run([sys.executable, "-B", str(PB / "build_playbook_docx.py"), "--model", str(mp),
                           "--profile", str(prof), "--out", str(out)], capture_output=True).returncode == 0
    r = subprocess.run([sys.executable, "-B", str(PB / "verify_playbook_docx.py"), "--docx", str(out),
                        "--model", str(mp), "--profile", str(prof)], capture_output=True, text=True, cwd=str(PB))
    assert r.returncode == 0, r.stdout
    z = zipfile.ZipFile(out)
    xml = z.read("word/document.xml").decode("utf-8")
    rels = z.read("word/_rels/document.xml.rels").decode("utf-8")
    assert "המקורות שעליהם נשען הפלייבוק" in xml
    urls = {x["url"] for x in m["market_research"]["source_refs"] if x.get("url")}
    assert urls and all(u in rels for u in urls)
    assert "not-in-records.example" not in xml + rels


def test_a_source_that_was_not_read_needs_no_link_check():
    m = {"market_research": {"source_refs": [{"source_id": "W1", "url": "https://x.example", "read_status":
                                              "located_not_read"}]}}
    errs = MR.check_model(m)
    assert not any("LINK_CHECK" in e for e in errs)


def test_the_negotiator_finds_a_playbook_of_any_family_the_builder_made(tmp_path):
    """FAMILY_WORDS מכיר שש משפחות; פלייבוק של הסכמי מנוי לענן לא נמצא, גם עם הקוד המדויק."""
    data = tmp_path / "Areo-נתונים"
    fam = data / "playbooks" / "fam_saas_subscription_supplier"
    fam.mkdir(parents=True)
    core = {"family_id": "fam_saas_subscription_supplier", "family_code": "saas_subscription",
            "company_role_code": "supplier", "output_language": "he", "playbook_status": "Draft",
            "contract_families": [{"contract_family_name": "הסכמי שירותי מנוי למערכת ענן",
                                   "family_aliases": ["הסכם מנוי לענן", "SaaS"], "company_role_code": "supplier"}],
            "clauses": []}
    (fam / "playbook-core.json").write_text(json.dumps(core, ensure_ascii=False), encoding="utf-8")
    folder = tmp_path / "drafts"
    folder.mkdir()
    for name in ("saas_subscription", "הסכם מנוי לענן", "SaaS"):
        r = subprocess.run([sys.executable, "-B", str(ORCH / "resolve_playbook.py"), "--data", str(data),
                            "--folder", str(folder), "--family", name, "--role", "supplier", "--language", "he",
                            "--out", str(tmp_path / "res.json")], capture_output=True, text=True, cwd=str(ORCH))
        assert r.returncode == 0, r.stdout + r.stderr
        res = json.loads((tmp_path / "res.json").read_text(encoding="utf-8"))
        assert res["result"] == "match", (name, res)


def test_the_risk_assessor_reads_a_nevo_law_address(tmp_path, monkeypatch):
    """כל כתובת חוק בנבו (/law_html/law00/144811.htm) נחסמה כ"פרט של הלקוח" בגלל מספר המסמך."""
    RISK = PLUGIN / "areolegal" / "skills" / "contract-risk-assessor" / "scripts"
    sys.path.insert(0, str(RISK))
    import fetch_source as F
    from common import net
    seen = []
    monkeypatch.setattr(net, "fetch", lambda url, purpose, **kw: seen.append(url) or
                        {"status": 200, "blocked": False, "stored": None, "reason": "ok", "log": {}})
    deal = tmp_path / "deal"
    deal.mkdir()
    prof = tmp_path / "p.json"
    prof.write_text(json.dumps({"organization_name": "נבו-טק תוכנה"}, ensure_ascii=False), encoding="utf-8")
    base = ["--deal", str(deal), "--profile", str(prof), "--kind", "regulatory", "--question", "Q1",
            "--source-id", "L1", "--purpose", "תקנות אבטחת מידע, נוסח בתוקף"]
    try:
        F.main(base + ["--url", "https://www.nevo.co.il/law_html/law00/144811.htm"])
    except SystemExit:
        pass
    assert seen, "כתובת החוק נחסמה"
    seen.clear()
    try:
        F.main(base + ["--url", "https://www.nevo.co.il/law_html/law00/נבו-טק תוכנה.htm"])
    except SystemExit:
        pass
    assert not seen, "שם הלקוח בכתובת לא נחסם"


@pytest.mark.parametrize("text,number,want", [
    ("5א. הגנת מידע. הספק יעבד", "5א.‏ ", "הגנת מידע. הספק יעבד"),
    ("5א.5א. הגנת מידע", "5א.", "הגנת מידע"),
    ("הגנת מידע", "5א. ", "הגנת מידע"),
    ("12.3 סעיף משנה", "12. ", "12.3 סעיף משנה"),
    ("1. סעיף", "12. ", "1. סעיף"),
])
def test_a_new_clause_number_is_written_once(text, number, want):
    """בהרצה החיה הסעיף החדש יצא "5א.5א.": המספר נמסר גם בשדה number וגם בראש הטקסט."""
    sys.path.insert(0, str(ORCH))
    import apply_redlines as A
    d = {"op": "insert_paragraph", "number": number, "text": text}
    A.strip_repeated_number(d)
    assert d["text"] == want
