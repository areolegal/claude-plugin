"""The internal note's source line names the agreement, not the playbook's code. Found in the overnight run on
05.11.2026: evidence carried source_ref "S01#p6", the lookup used that whole value, and the lawyer saw
"מקור: S01#p5, 2; S02#p5, 2"."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "areolegal" / "skills" / "contract-negotiation-orchestrator"
                       / "scripts"))
import playbook_map as M  # noqa: E402

PB = {"source_log": [{"source_id": "S01", "file": "הסכמים חתומים/הסכם מנוי - אלון.docx", "short_name": "הסכם מנוי - אלון"},
                     {"source_id": "S02", "title": "הסכם מנוי - גלבוע"}]}


def test_anchor_in_source_ref_resolves_to_agreement_name():
    r = {"evidence": [{"source_ref": "S01#p6", "source_id": "S01", "clause_ref": "3"},
                      {"source_ref": "S02#p6", "clause_ref": "3"}]}
    txt = M.source_text(M.rule_sources(r, PB))
    assert txt == "מקור: הסכם מנוי - אלון, 3; הסכם מנוי - גלבוע, 3", txt
    assert "S0" not in txt and "#p" not in txt
