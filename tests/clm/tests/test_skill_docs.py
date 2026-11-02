import os
import re

import clm_paths  # noqa: E402
ROOT = clm_paths.SKILL
REFS = ["extraction-format.md", "core-model.md", "key-clauses.md", "intake-pipeline.md",
        "terminology.md", "sharing-and-access.md"]


def read(*p):
    # references/<file> is served content (get_resource), not in the plugin: read it from server/content
    base, p = (clm_paths.REFS_DIR, p[1:]) if p and p[0] == "references" else (ROOT, p)
    with open(os.path.join(base, *p), encoding="utf-8") as f:
        return f.read()


def test_skill_md_lean_and_linked():
    s = read("SKILL.md")
    assert len(s.encode("utf-8")) < 20000
    assert s.startswith("---\nname: clm-contract-lifecycle\n")
    for r in REFS:
        assert "references/" + r in s, r
        assert os.path.exists(os.path.join(clm_paths.REFS_DIR, r)), r
    # scripts run as `python3 -B` (never -I: it hides a user-installed python-docx on macOS), decision 02.11
    runs = re.findall(r"python3?[^\n`]*clm_cli\.py", s)
    assert runs and all(r.startswith("python3 -B ") for r in runs), runs
    assert not re.search(r"python3? +(-\w+ +)*-I\b", s)


def test_no_long_dash_or_forbidden_terms_in_docs():
    for path in ["SKILL.md"] + ["references/" + r for r in REFS]:
        text = read(*path.split("/"))
        assert not re.search("[\u2013\u2014]", text), path
    s = read("SKILL.md")
    for word in ("לפעול עד", "התממש", "הכדור אצלנו"):
        assert word not in s, word


def test_terminology_has_core_terms():
    t = read("references", "terminology.md")
    for term in ("מועד יעד לטיפול", "השלכת אי-פעולה", "באיחור", "צד החברה בהסכם", "סעיפי מפתח",
                 "אימות נתונים", "חלף, ממתין לאישור תוצאה", "היקף הבדיקה"):
        assert term in t, term
