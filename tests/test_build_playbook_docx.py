# -*- coding: utf-8 -*-
"""הבונה של ה-Word ובדיקת הקבלה שלו, יחד.

בגרסה 1.20.0 כל Word שנבנה ב-`build_playbook_docx.py` נכשל ב-`verify_playbook_docx.py`,
בארבע בדיקות מתוך תשע: נוסח דו-לשוני הודפס כמילון (`{'he': ...}`), אין פרק "העמדות
בקצרה", מזהי הכללים לא הופיעו, אין `rtlGutter`, מאפייני הקובץ של python-docx מ-2013,
ו"Draft" באנגלית בתמונת המצב. הבונה נכתב לפי מבנה המודל הישן, והבדיקה נוספה אחריו,
ושום בדיקה לא הריצה את שניהם יחד. זו הבדיקה הזו: כל מודל לדוגמה, בכל גרסה, נבנה
ונבדק, וקוד היציאה של בדיקת הקבלה חייב להיות 0.
"""
import json
import re
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

PLUGIN = Path(__file__).resolve().parents[1]
LIB = PLUGIN / "areolegal" / "lib"
SKILL = PLUGIN / "areolegal" / "skills" / "contract-playbook-builder"
BUILD = SKILL / "scripts" / "build_playbook_docx.py"
VERIFY = SKILL / "scripts" / "verify_playbook_docx.py"
FIXTURES = LIB / "tests" / "fixtures" / "playbook"

sys.path.insert(0, str(LIB))
pytest.importorskip("docx")
pytest.importorskip("lxml")

from playbook import market_counts as MC  # noqa: E402

MODELS = sorted(p.name for p in FIXTURES.glob("*.json")
                if json.loads(p.read_text(encoding="utf-8")).get("rules"))


def _py(script, *args):
    return subprocess.run([sys.executable, "-B", str(script)] + [str(a) for a in args],
                          capture_output=True, text=True, cwd=str(script.parent))


@pytest.fixture
def profile(tmp_path):
    p = tmp_path / "פרופיל-לקוח.json"
    p.write_text(json.dumps({"organization_name": "EXAMPLECO"}), encoding="utf-8")
    return p


def _build(tmp_path, profile, model, version="one"):
    out = tmp_path / ("%s-%s.docx" % (Path(model).stem, version))
    r = _py(BUILD, "--model", model, "--profile", profile, "--version", version, "--out", out)
    assert r.returncode == 0, r.stdout + r.stderr
    return out


def _text(docx):
    with zipfile.ZipFile(docx) as z:
        xml = z.read("word/document.xml").decode("utf-8")
    return "".join(re.findall(r"<w:t(?: [^>]*)?>([^<]*)</w:t>", xml))


def test_there_are_models_to_build():
    assert len(MODELS) >= 5


@pytest.mark.parametrize("version", ["one", "short", "full"])
@pytest.mark.parametrize("name", MODELS)
def test_every_built_word_passes_its_own_acceptance_check(tmp_path, profile, name, version):
    model = FIXTURES / name
    docx = _build(tmp_path, profile, model, version)
    r = _py(VERIFY, "--docx", docx, "--model", model, "--profile", profile)
    assert r.returncode == 0, r.stdout


def test_the_demo_model_in_the_old_shape_also_passes(tmp_path, profile):
    """מודל ההדגמה שבשרת נושא את המבנה הישן (confidence, meaning, policy_rationale)."""
    model = PLUGIN.parent / "server" / "content" / "playbook-workspace" / "demo-playbook-model.json"
    if not model.exists():
        pytest.skip("ריפו השרת אינו לצד ריפו התוסף")
    docx = _build(tmp_path, profile, model)
    r = _py(VERIFY, "--docx", docx, "--model", model, "--profile", profile)
    assert r.returncode == 0, r.stdout


def test_bilingual_wording_is_printed_as_text_in_the_document_language(tmp_path, profile):
    model = FIXTURES / "mutual_nda_model_good.json"
    data = json.loads(model.read_text(encoding="utf-8"))
    he = data["rules"][0]["traffic_light"]["green"]["proposed_clause"]["he"]
    text = _text(_build(tmp_path, profile, model))
    assert "{'he'" not in text and '{"he"' not in text
    assert " ".join(he.split()) in text


def test_english_only_wording_is_a_left_to_right_run(tmp_path, profile):
    docx = _build(tmp_path, profile, FIXTURES / "mutual_nda_round3_excerpt.json")
    with zipfile.ZipFile(docx) as z:
        xml = z.read("word/document.xml").decode("utf-8")
    run = re.search(r'<w:r>(?:(?!</w:r>).)*"Confidential Information" means all', xml, re.S).group(0)
    assert '<w:rtl w:val="0"/>' in run


def test_brief_chapter_has_a_row_and_a_link_for_every_rule(tmp_path, profile):
    model = FIXTURES / "mutual_nda_model_good.json"
    rules = json.loads(model.read_text(encoding="utf-8"))["rules"]
    docx = _build(tmp_path, profile, model)
    text = _text(docx)
    after = text.split("העמדות בקצרה", 1)[1]
    for r in rules:
        assert r["rule_id"] in after
    with zipfile.ZipFile(docx) as z:
        xml = z.read("word/document.xml").decode("utf-8")
    anchors = set(re.findall(r'w:anchor="([^"]+)"', xml))
    marks = set(re.findall(r'<w:bookmarkStart [^>]*w:name="([^"]+)"', xml))
    assert {"card_%d" % i for i in range(1, len(rules) + 1)} <= anchors
    assert anchors <= marks


def test_label_is_on_the_cover_and_in_the_header_in_a_status_control(tmp_path, profile):
    model = FIXTURES / "mutual_nda_model_good.json"
    label = json.loads(model.read_text(encoding="utf-8"))["status_label"]
    docx = _build(tmp_path, profile, model)
    with zipfile.ZipFile(docx) as z:
        doc = z.read("word/document.xml").decode("utf-8")
        header = "".join(z.read(n).decode("utf-8") for n in z.namelist()
                         if re.match(r"word/header\d*\.xml$", n))
    for xml in (doc, header):
        assert 'w:val="areo:status_label"' in xml and label in xml
    assert "Draft" not in _text(docx)


def test_file_properties_are_the_company_and_today(tmp_path, profile):
    docx = _build(tmp_path, profile, FIXTURES / "mutual_nda_model_good.json")
    with zipfile.ZipFile(docx) as z:
        core = z.read("docProps/core.xml").decode("utf-8")
    assert "python-docx" not in core and "2013-" not in core
    assert "<dc:creator>EXAMPLECO</dc:creator>" in core


def test_count_claims_reads_one_line_at_a_time():
    """"4" בסוף שורה בטבלה ו"מסמכים" בראש השורה הבאה אינם טענה על מספר המסמכים."""
    m = {"market_research": {"counts": {"found": 9, "opened": 9, "read": 8, "counted": 8}}}
    assert MC.count_claims("נושאי מדיניות\n4\nמסמכים שנותחו", m) == []
    assert MC.count_claims("נבנו מ-4 מסמכים", m)


def test_company_agreements_are_not_read_as_market_counts():
    """שורת הבסיס של המפרט: "נבנה מ-5 הסכמים של החברה, בשילוב מחקר שוק"."""
    m = {"market_research": {"counts": {"found": 9, "opened": 9, "read": 8, "counted": 8}}}
    assert MC.count_claims("נבנה מ-5 הסכמים של החברה, בשילוב מחקר שוק.", m) == []
    assert MC.count_claims("נבנה מ-5 הסכמים שפורסמו ברשת.", m)
