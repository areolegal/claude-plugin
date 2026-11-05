"""The drafter's cover page must pass the shared voice check it is held to. Found in the overnight end-to-end run,
05.11.2026: its own heading said "מצייני חוסר בטיוטה: 8", the check blocked it, and every cover page with
details to complete failed to build."""
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / "areolegal" / "skills" / "contract-drafter" / "scripts"
sys.path.insert(0, str(SCRIPTS))
docx = pytest.importorskip("docx")
import fill_template as F  # noqa: E402


def _report(n):
    # "replaced" ends the section before the decisions heading with "סעיף 8": the night run's exact case
    return {"template": "master.docx", "built_at": "2026-11-05T00:00:00Z", "placeholders": n, "unfilled": [],
            "filled": [], "defaulted": {}, "removed": [], "replaced": ["5", "8"], "added": [], "reference_changes": [],
            "dangling_references": [], "warnings": []}


@pytest.mark.parametrize("lang", ["he", "en"])
def test_cover_with_details_to_complete_builds(tmp_path, lang):
    out = tmp_path / "cover.docx"
    words = {"he": ("הסכם מנוי", "הגבלת האחריות נשארה כמו בפלייבוק"),
             "en": ("Subscription agreement", "The liability cap stayed as in the playbook")}[lang]
    vals = {"cover": {"title": words[0], "decisions": [words[1]]}, "variables": {}}
    F.write_cover(str(out), _report(8), vals, {"variables": []}, lang)   # exits on a blocked phrase
    assert out.is_file()
