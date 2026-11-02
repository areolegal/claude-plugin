# -*- coding: utf-8 -*-
"""בדיקות ל-`resolve_playbook.py`: מה שהעטיפה מוסיפה מעל הספרייה.

הספרייה נבדקת אצל ענבל (`lib/tests/test_resolve_playbook.py`). כאן:

1. **אין מילון.** מגרסה 1.3.0 (`lib/orchestrator/resolve_playbook.py`, התיעוד; `n1b-learning.md`:56) המשפחה
   והתפקיד הם טקסט חופשי, ומושווים לשמות, לקודים ולכינויים של הפלייבוקים הקיימים בלבד. שם בעברית מוצא פלייבוק
   שנרשם בשם הזה; הוא אינו מתורגם לקוד.
2. **משפחה שאינה מוכרת אינה עצירה:** התוצאה `no_match` והמסלול "אין פלייבוק", עם קובץ תוצאה. תפקיד שאינו
   מזוהה, או כינוי של תפקיד, חוזר "לבחירה" עם שאלה, ולעולם אינו התאמה אוטומטית.
3. **`source_label`** - המשפט שמוצג למשתמש - נכתב לקובץ, כי הרכיב מצטט אותו ואינו מנסח אותו מחדש.
"""
import json
import subprocess
import sys
from pathlib import Path

import pytest

PLUGIN = Path(__file__).resolve().parents[1]
LIB = PLUGIN / "areolegal" / "lib"
SCRIPT = (PLUGIN / "areolegal" / "skills" / "contract-negotiation-orchestrator"
          / "scripts" / "resolve_playbook.py")

sys.path.insert(0, str(LIB))
sys.path.insert(0, str(LIB / "tests"))
pytest.importorskip("docx")

import orch_helpers as H  # noqa: E402

FX = json.loads((Path(H.FIX) / "resolve" / "fixtures.json").read_text(encoding="utf-8"))


def _json(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False), encoding="utf-8")


@pytest.fixture
def client(tmp_path):
    """לקוח עם פלייבוק אחד במפתח: שירותים, בצד מקבל השירותים."""
    folder = tmp_path / "client"
    data = folder / "Areo-נתונים"
    _json(data / "playbooks" / "fam_services" / "playbook-core.json",
          FX["indexed_valid_core"])
    _json(data / "playbooks" / "fam_services" / "playbook-model.json",
          FX["indexed_valid_model"])
    _json(data / "playbooks" / "index.json", {"playbooks": [
        {"core_path": "playbooks/fam_services/playbook-core.json",
         "family_code": "services", "company_role_code": "service_recipient",
         "language": "he", "last_updated": "2026-10-01"}]})
    return data, folder


def _run(client, family, role, out=None, language="he"):
    data, folder = client
    cmd = [sys.executable, str(SCRIPT), "--data", str(data), "--folder", str(folder),
           "--family", family, "--role", role, "--language", language]
    if out:
        cmd += ["--out", str(out)]
    r = subprocess.run(cmd, capture_output=True, text=True, cwd=str(SCRIPT.parent))
    return r


def test_the_hebrew_family_and_role_names_find_the_playbook(client, tmp_path):
    """השם שהמשתמש אומר מוצא פלייבוק שנרשם באותו שם (כך רכיב הפלייבוק כותב אותו), בלי מילון."""
    data, _ = client
    entry = {"core_path": "playbooks/fam_services/playbook-core.json", "family_code": "services",
             "family_name": "הסכם שירותים", "company_role_code": "מקבל השירותים", "language": "he",
             "last_updated": "2026-10-01"}
    _json(data / "playbooks" / "index.json", {"playbooks": [entry]})
    _json(data / "playbooks" / "fam_services" / "playbook-core.json",
          dict(FX["indexed_valid_core"], family_name="הסכם שירותים", company_role_code="מקבל השירותים"))
    out = tmp_path / "res.json"
    r = _run(client, "הסכם שירותים", "מקבל השירותים", out=out)
    assert r.returncode == 0, r.stdout + r.stderr
    res = json.loads(out.read_text(encoding="utf-8"))
    assert res["result"] == "match", r.stdout
    assert res["chosen"].endswith("fam_services/playbook-core.json")


def test_a_hebrew_name_is_not_translated_to_a_code(client, tmp_path):
    """פלייבוק שנרשם רק בקודים אינו נמצא בשם עברי: אין מילון שמתרגם (1.3.0)."""
    out = tmp_path / "res.json"
    r = _run(client, "הסכם שירותים", "מקבל השירותים", out=out)
    assert r.returncode == 0, r.stdout + r.stderr
    assert json.loads(out.read_text(encoding="utf-8"))["result"] == "no_match"


def test_the_codes_themselves_still_work(client, tmp_path):
    """הרכיב עצמו מעביר קודים, והתרגום אינו אמור לפגוע בהם."""
    out = tmp_path / "res.json"
    r = _run(client, "services", "service_recipient", out=out)
    assert r.returncode == 0, r.stdout + r.stderr
    res = json.loads(out.read_text(encoding="utf-8"))
    assert res["chosen"].endswith("fam_services/playbook-core.json")


def test_an_unknown_family_is_no_match_and_not_a_stop(client, tmp_path):
    """n1b-learning.md:56: "משפחה שאינה מוכרת אינה עצירה": אין התאמה, המסלול "אין פלייבוק", וקובץ תוצאה נכתב."""
    out = tmp_path / "res.json"
    r = _run(client, "הסכם שאינו קיים בשום רשימה", "service_recipient", out=out)
    assert r.returncode == 0, r.stdout + r.stderr
    res = json.loads(out.read_text(encoding="utf-8"))
    assert res["result"] == "no_match" and not res["chosen"]


def test_an_unknown_role_returns_for_choice_and_never_matches(client, tmp_path):
    """תפקיד שאינו מזוהה: "לבחירה" עם שאלה, ולא התאמה אוטומטית (n1b-learning.md:56)."""
    out = tmp_path / "res.json"
    r = _run(client, "services", "צד שאינו קיים בשום רשימה", out=out)
    assert r.returncode == 0, r.stdout + r.stderr
    res = json.loads(out.read_text(encoding="utf-8"))
    assert res["result"] == "choose" and not res["chosen"]


def test_a_synonym_role_code_is_for_choice_not_a_silent_match(client, tmp_path):
    """`customer` מול `service_recipient` שבמפתח: אין מילון תפקידים, ולכן "לבחירה" עם שאלה."""
    out = tmp_path / "res.json"
    r = _run(client, "services", "customer", out=out)
    assert r.returncode == 0, r.stdout + r.stderr
    res = json.loads(out.read_text(encoding="utf-8"))
    assert res["result"] == "choose" and not res["chosen"], res


def test_the_wrong_side_is_not_matched(client, tmp_path):
    """פלייבוק של הצד ההפוך אינו התאמה, והתשובה היא תשובה ולא שגיאה."""
    out = tmp_path / "res.json"
    r = _run(client, "הסכם שירותים", "נותן השירותים", out=out)
    assert r.returncode == 0, r.stdout + r.stderr
    res = json.loads(out.read_text(encoding="utf-8"))
    assert not (res.get("chosen") or "").endswith("fam_services/playbook-core.json")


def test_the_source_sentence_is_written_to_the_result(client, tmp_path):
    """הרכיב מצטט את `source_label`, ולכן הוא חייב להיות בקובץ."""
    out = tmp_path / "res.json"
    r = _run(client, "הסכם שירותים", "מקבל השירותים", out=out)
    assert r.returncode == 0, r.stdout + r.stderr
    res = json.loads(out.read_text(encoding="utf-8"))
    assert res.get("source_label"), res
    assert res["source_label"] in r.stdout
