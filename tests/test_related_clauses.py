# -*- coding: utf-8 -*-
"""סעיפים קשורים (ps3-rule-and-evidence.md): עוברים לסביבת העבודה עם הכיוון, ההסבר והציטוט, ומסוננים כשהם שגויים."""
import sys
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN / "areolegal" / "lib"))
sys.path.insert(0, str(PLUGIN / "areolegal" / "skills" / "contract-playbook-builder" / "scripts"))

import build_workspace_payload as B  # noqa: E402

Q = "אחריותו הכוללת של הספק לא תעלה על פי 12 מהתמורה החודשית, למעט הפרת סודיות ונזקי גוף."


def _rule(rid, name, impacts=()):
    return {"rule_id": rid, "topic_name": name, "importance": "גבוהה",
            "traffic_light": {"green": {"position": "x", "evidence": []}}, "related_clause_impacts": list(impacts)}


def test_related_clauses_reach_the_workspace_and_bad_ones_are_dropped():
    m = {"company_name": "חברה", "rules": [
        _rule("R05", "הגבלת אחריות", [
            {"related_rule_id": "R04", "direction": "affected_by", "impact": "הפרת סודיות מוחרגת מהתקרה.",
             "action": "לשמור על החריג", "evidence": [{"source_ref": "S1", "clause_ref": "5.1", "quote": Q, "count": 4}]},
            {"related_rule_id": "R07", "direction": "affected_by", "impact": "הגנת מידע אינה בחריגים.", "basis": "areo_proposal"},
            {"related_rule_id": "R05", "direction": "mutual", "impact": "הנושא עצמו"},
            {"related_rule_id": "R99", "direction": "affects", "impact": "נושא שאינו קיים"},
            {"related_rule_id": "R04", "direction": "weird", "impact": ""},
        ]),
        _rule("R04", "סודיות"), _rule("R07", "הגנת מידע")]}
    rows = {r["id"]: r for r in B.build_rules(m, [])}
    imp = rows["R05"]["impacts"]
    assert [x["related_rule_id"] for x in imp] == ["R04", "R07"]
    assert imp[0]["direction"] == "affected_by" and imp[0]["basis"] == "corpus"
    assert imp[0]["evidence"][0]["clause"] == "5.1" and imp[0]["evidence"][0]["count"] == 4
    assert imp[1]["basis"] == "areo_proposal" and imp[1]["evidence"] == []
    assert "impacts" not in rows["R04"], "נושא בלי קשרים לא מציג סעיפים קשורים"
