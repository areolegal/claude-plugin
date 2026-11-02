# -*- coding: utf-8 -*-
"""רשימת המקורות המאושרים נארזת בתוסף, ונקראת משם כשלא נמסר נתיב (החלטת ארכיטקטורה 02.11.2026: Cowork חוסם
הורדות מהשרת, ולכן שום דבר אינו מורד לדיסק בזמן ריצה).

הסדר, במקום אחד (risk/validate_register.sources_path): --approved-sources, אחריו AREO_APPROVED_SOURCES, ואחריהם
lib/מקורות-מאושרים.json. נתיב שנמסר ואינו קיים אינו נופל בשקט לעותק שבתוסף: אין רשימה, ואף מקור אינו מאושר.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

PLUGIN = Path(__file__).resolve().parents[1]
LIB = PLUGIN / "areolegal" / "lib"
SKILLS = PLUGIN / "areolegal" / "skills"
BUNDLED = LIB / "מקורות-מאושרים.json"
sys.path.insert(0, str(LIB))

from risk import validate_register as VR  # noqa: E402

LISTED = "https://www.sec.gov/Archives/edgar/data/1/x.htm"      # ברשימה שבתוסף
UNLISTED = "https://www.example.gov/x"                          # לא ברשימה שבתוסף


@pytest.fixture(autouse=True)
def no_env(monkeypatch):
    monkeypatch.delenv("AREO_APPROVED_SOURCES", raising=False)


@pytest.fixture
def other_list(tmp_path):
    p = tmp_path / "approved.json"
    p.write_text(json.dumps({"jurisdictions": [{"sources": [
        {"domain": "example.gov", "status": "approved", "include_subdomains": True}]}]}), encoding="utf-8")
    return p


def _env():
    env = dict(os.environ)
    env.pop("AREO_APPROVED_SOURCES", None)
    return env


def test_the_bundled_list_exists_and_is_the_default():
    assert BUNDLED.is_file()
    assert Path(VR.default_sources_path()) == BUNDLED
    rules, used = VR.approved_domains()
    assert rules and Path(used) == BUNDLED
    assert VR.domain_ok(LISTED, rules) and not VR.domain_ok(UNLISTED, rules)


def test_an_explicit_path_and_the_environment_win_over_the_bundled_copy(other_list, monkeypatch):
    rules, used = VR.approved_domains(str(other_list))
    assert used == str(other_list) and VR.domain_ok(UNLISTED, rules) and not VR.domain_ok(LISTED, rules)
    monkeypatch.setenv("AREO_APPROVED_SOURCES", str(other_list))
    rules, used = VR.approved_domains()
    assert used == str(other_list) and VR.domain_ok(UNLISTED, rules)


def test_a_given_path_that_does_not_exist_is_no_list_and_not_the_bundled_copy(tmp_path):
    assert VR.approved_domains(str(tmp_path / "missing.json")) == ((), None)


def test_the_one_url_lookup_reads_the_bundled_copy():
    from common.approved_sources import lookup
    assert lookup(LISTED)["status"] == "approved"
    assert lookup(UNLISTED)["status"] == "not_on_list"


def test_the_drafter_uses_the_same_default(other_list):
    sys.path.insert(0, str(SKILLS / "contract-drafter" / "scripts"))
    import research_sources as RS
    assert Path(RS.default_sources_path()) == BUNDLED
    rules, used = RS.load_approved_sources()
    assert rules and Path(used) == BUNDLED
    assert RS.law_source_problem(LISTED) is None and RS.law_source_problem(UNLISTED)
    assert RS.law_source_problem(UNLISTED, approved_sources=str(other_list)) is None


@pytest.mark.parametrize("script,args", [
    (SKILLS / "contract-drafter" / "scripts" / "research_sources.py", ["lookup"]),
    (SKILLS / "contract-playbook-builder" / "scripts" / "market_research.py", ["lookup"]),
    (LIB / "common" / "approved_sources.py", []),
])
def test_the_lookup_commands_work_without_the_argument(script, args, other_list):
    r = subprocess.run([sys.executable, "-B", str(script)] + args + ["--url", LISTED],
                       capture_output=True, text=True, env=_env(), cwd=str(script.parent))
    assert r.returncode == 0, r.stdout + r.stderr
    assert json.loads(r.stdout)["status"] == "approved"
    r = subprocess.run([sys.executable, "-B", str(script)] + args + ["--url", LISTED,
                                                                     "--approved-sources", str(other_list)],
                       capture_output=True, text=True, env=_env(), cwd=str(script.parent))
    assert r.returncode == 1 and json.loads(r.stdout)["status"] == "not_on_list"


def test_no_script_tells_the_model_to_download_the_sources_list():
    """הטקסטים של העזרה והסירוב מפנים לעותק שבתוסף, ולא ל-save_resource או resource_link."""
    files = [LIB / "risk" / "validate_register.py", LIB / "common" / "approved_sources.py"]
    files += [SKILLS / s for s in (
        "contract-drafter/scripts/research_sources.py", "contract-drafter/scripts/build_research_brief.py",
        "contract-drafter/scripts/build_regulatory_matrix.py", "contract-drafter/scripts/build_draft_docx.py",
        "contract-risk-assessor/scripts/fetch_source.py", "contract-risk-assessor/scripts/validate_data.py",
        "contract-playbook-builder/scripts/market_research.py",
        "contract-playbook-builder/scripts/validate_playbook_model.py")]
    bad = [f.name for f in files if any(w in f.read_text(encoding="utf-8") for w in ("save_resource", "resource_link"))]
    assert not bad, bad
