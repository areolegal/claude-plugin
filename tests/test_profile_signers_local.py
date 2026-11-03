# -*- coding: utf-8 -*-
"""מורשי החתימה ומאשר המדיניות (הכרעת ניל, 02.11.2026): נשמרים בפרופיל שבתיקייה, ולעולם לא בעותק שנשלח ל-Areo."""
import json
import subprocess
import sys
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[1]
BP = PLUGIN / "areolegal" / "skills" / "contract-setup-diagnostician" / "scripts" / "build_profile.py"

ANSWERS = {"organization_name": "נובה טק בע\"מ", "incorporation_country": "ישראל", "organization_type": "חברה פרטית",
           "sectors": ["טכנולוגיה ותוכנה"], "markets": ["ישראל"], "logo": "later", "display_language": "he"}


def _bp(*args):
    return subprocess.run([sys.executable, "-B", str(BP)] + [str(a) for a in args], capture_output=True, text=True)


def _profile(tmp_path):
    a = tmp_path / "answers.json"
    a.write_text(json.dumps(ANSWERS, ensure_ascii=False), encoding="utf-8")
    p = tmp_path / "פרופיל-לקוח.json"
    r = _bp("--answers", a, "--out", p)
    assert r.returncode == 0, r.stdout + r.stderr
    return p


def test_signers_and_approver_stay_in_the_folder_only(tmp_path):
    p = _profile(tmp_path)
    r = _bp("--out", p,
            "--set", 'branding.signatories=[{"name":"רונית בר","role":"מנכ\\"לית"},{"name":"עמית גל","role":"סמנכ\\"ל"}]',
            "--set", "branding.lawyer_name=רונית בר",
            "--set", 'branding.policy_approver={"name":"אורי שחר","role":"יועץ משפטי"}')
    assert r.returncode == 0, r.stdout + r.stderr
    prof = json.loads(p.read_text(encoding="utf-8"))
    assert prof["branding"]["policy_approver"] == {"name": "אורי שחר", "role": "יועץ משפטי"}
    assert [s["name"] for s in prof["branding"]["signatories"]] == ["רונית בר", "עמית גל"]
    copy = tmp_path / "areo-copy.json"
    assert _bp("--out", p, "--areo-copy", "--to", copy).returncode == 0
    text = copy.read_text(encoding="utf-8")
    for name in ("רונית בר", "עמית גל", "אורי שחר"):
        assert name not in text, "שם חותם או מאשר אינו נשלח ל-Areo"
    assert "policy_approver" not in text and "signatories" not in text


def test_the_approver_must_be_a_full_person_name(tmp_path):
    p = _profile(tmp_path)
    for bad in ('{"name":"אורי"}', '{"name":"היועץ המשפטי"}', '"אורי שחר"'):
        r = _bp("--out", p, "--set", "branding.policy_approver=" + bad)
        assert r.returncode == 2, bad
    assert "policy_approver" not in json.loads(p.read_text(encoding="utf-8"))["branding"]
