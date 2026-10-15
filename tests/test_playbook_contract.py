# -*- coding: utf-8 -*-
"""בדיקות ל-`check_playbook_contract.py`, הצד של הקורא.

`playbook-qa.md`, בדיקה 2: אפס שגיאות, "זהו חוזה הנתונים עם הרכיבים
שקוראים את הפלייבוק". הבדיקה אינה אימות סכמה: היא על השדות שהנושא
ונותן שולף בזמן הכרעה. פלייבוק שעובר את הסכמה ונכשל כאן הוא פלייבוק
שיישבר באמצע סבב אמיתי.

שני דברים שנבדקים כאן במיוחד, כי שניהם טעויות שקל לכתוב:

* **`round1_posture` חסר אינו שגיאה.** `decision_matrix.md` קובע מה
  קורה בלעדיו: מחזיקים בירוק ומציינים זאת בסיכום הפנימי. ערך שאינו
  מהשניים כן שגיאה, כי אין לו התנהגות מוגדרת.
* **הגרעין והמודל חייבים לאמר אותו דבר.** קורא שרואה שתי תשובות אינו
  יודע במי להאמין, וזו הייתה התקלה של סבב 2.
"""
import copy
import json
import subprocess
import sys
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[1]
SCRIPT = (PLUGIN / "areolegal" / "skills" / "contract-negotiation-orchestrator"
          / "scripts" / "check_playbook_contract.py")

GOOD_RULE = {
    "rule_id": "R-01", "topic": "תנאי תשלום", "importance": "high",
    "policy_ref": "4.1", "round1_posture": "hold_green",
    "fallback_wording": "התמורה תשולם בתוך 45 יום מהמצאת חשבונית.",
    "fallback_source": "client_answer",
    "traffic_light": {
        "green": {"position": "שוטף 30", "wording": "התמורה תשולם בתוך 30 יום."},
        "yellow": {"position": "שוטף 45", "wording": "התמורה תשולם בתוך 45 יום."},
        "red": {"position": "מעבר ל-60 יום", "cure_wording": "לא יותר מ-60 יום."}},
}

GOOD_MODEL = {
    "schema_version": "3.2", "core_version": "2.0.0", "family_id": "fam_services_recipient",
    "family_code": "services", "company_role_code": "service_recipient",
    "status_label": "פלייבוק מוצע, מבוסס הסכמים, טעון אישור",
    "playbook_status": "Draft",
    "produced_with": {"skill_version": "3.2", "notes_version": "5.5", "refs_sha256": "a" * 8},
    "rules": [GOOD_RULE],
}


def _write(tmp_path, model, core=None):
    mp = tmp_path / "playbook-model.json"
    mp.write_text(json.dumps(model, ensure_ascii=False), encoding="utf-8")
    if core is None:
        return [str(mp)]
    cp = tmp_path / "playbook-core.json"
    cp.write_text(json.dumps(core, ensure_ascii=False), encoding="utf-8")
    return [str(mp), "--core", str(cp)]


def _run(args):
    return subprocess.run([sys.executable, str(SCRIPT)] + [str(x) for x in args],
                          capture_output=True, text=True, cwd=str(SCRIPT.parent))


def test_a_playbook_that_meets_the_contract_passes(tmp_path):
    r = _run(_write(tmp_path, GOOD_MODEL))
    assert r.returncode == 0, r.stdout + r.stderr
    assert "CONTRACT MET" in r.stdout


def test_a_missing_round1_posture_is_a_note_and_not_an_error(tmp_path):
    """decision_matrix קובע מה קורה בלעדיו, ולכן אין כאן שגיאה."""
    model = copy.deepcopy(GOOD_MODEL)
    del model["rules"][0]["round1_posture"]
    r = _run(_write(tmp_path, model))
    assert r.returncode == 0, r.stdout
    assert "note:" in r.stdout and "round1_posture" in r.stdout
    assert "מחזיקים בירוק" in r.stdout


def test_an_unknown_round1_posture_is_an_error(tmp_path):
    """ערך בלי התנהגות מוגדרת הוא הכרעה שהמודל ימציא."""
    model = copy.deepcopy(GOOD_MODEL)
    model["rules"][0]["round1_posture"] = "default"
    r = _run(_write(tmp_path, model))
    assert r.returncode == 3, r.stdout
    assert "round1_posture" in r.stdout


def test_a_track_without_wording_is_an_error(tmp_path):
    """הנושא ונותן מכניס נוסח לגוף ההסכם, ולא תקציר."""
    model = copy.deepcopy(GOOD_MODEL)
    del model["rules"][0]["traffic_light"]["yellow"]["wording"]
    r = _run(_write(tmp_path, model))
    assert r.returncode == 3, r.stdout
    assert "אין נוסח להחלה" in r.stdout


def test_a_missing_track_is_an_error(tmp_path):
    model = copy.deepcopy(GOOD_MODEL)
    del model["rules"][0]["traffic_light"]["red"]
    r = _run(_write(tmp_path, model))
    assert r.returncode == 3, r.stdout
    assert "אין מסלול red" in r.stdout


def test_an_empty_fallback_is_an_error(tmp_path):
    model = copy.deepcopy(GOOD_MODEL)
    model["rules"][0]["fallback_source"] = "  "
    r = _run(_write(tmp_path, model))
    assert r.returncode == 3, r.stdout
    assert "fallback_source" in r.stdout


def test_a_field_the_core_supplies_is_accepted_from_the_core(tmp_path):
    """הקורא מסתכל בשניהם, ולכן שדה שבגרעין בלבד אינו חסר."""
    model = copy.deepcopy(GOOD_MODEL)
    del model["rules"][0]["fallback_wording"]
    core = {"clauses": [{"rule_id": "R-01",
                         "fallback_wording": "התמורה תשולם בתוך 45 יום."}]}
    r = _run(_write(tmp_path, model, core))
    assert r.returncode == 0, r.stdout


def test_a_core_that_contradicts_the_model_is_an_error(tmp_path):
    model = copy.deepcopy(GOOD_MODEL)
    core = {"clauses": [{"rule_id": "R-01"}],
            "status_label": "מדיניות מאושרת, 01.01.2026, בידי אחר, תפקיד"}
    r = _run(_write(tmp_path, model, core))
    assert r.returncode == 3, r.stdout
    assert "במי להאמין" in r.stdout


def test_a_rule_in_the_core_that_is_not_in_the_model_is_an_error(tmp_path):
    model = copy.deepcopy(GOOD_MODEL)
    core = {"clauses": [{"rule_id": "R-01"}, {"rule_id": "R-99"}]}
    r = _run(_write(tmp_path, model, core))
    assert r.returncode == 3, r.stdout
    assert "R-99" in r.stdout


def test_the_abolished_label_field_is_an_error(tmp_path):
    model = copy.deepcopy(GOOD_MODEL)
    model["presentation_label"] = model["status_label"]
    r = _run(_write(tmp_path, model))
    assert r.returncode == 3, r.stdout
    assert "presentation_label" in r.stdout


def test_a_playbook_built_with_an_older_builder_is_a_note(tmp_path):
    """overview: אל תוריד בשקט. זה נאמר, ואינו עוצר."""
    r = _run(_write(tmp_path, GOOD_MODEL) + ["--min-skill-version", "3.5"])
    assert r.returncode == 0, r.stdout
    assert "note:" in r.stdout and "3.5" in r.stdout


def test_a_playbook_without_rules_is_an_error(tmp_path):
    model = copy.deepcopy(GOOD_MODEL)
    model["rules"] = []
    r = _run(_write(tmp_path, model))
    assert r.returncode == 3, r.stdout
    assert "אין ממה להכריע" in r.stdout


def test_a_missing_file_is_two(tmp_path):
    r = _run([tmp_path / "אין-כזה.json"])
    assert r.returncode == 2, r.stdout
    assert "cannot read" in r.stdout
