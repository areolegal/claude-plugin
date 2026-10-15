# -*- coding: utf-8 -*-
"""בדיקות ל-`resolve_playbook.py`: מה שהעטיפה מוסיפה מעל הספרייה.

הספרייה נבדקת אצל ענבל (`lib/tests/test_resolve_playbook.py`), ואין
טעם לשכפל את זה. מה שנבדק כאן הוא שלושת הדברים שהעטיפה אחראית להם,
ושני הראשונים נשברו בכתיבה:

1. **תרגום השם לקוד.** `resolve()` משווה קודים (`services`,
   `service_recipient`), והסקיל מקבל מהמשתמש שם בעברית ("הסכם
   שירותים", "מקבל השירותים"). בלי התרגום כל הרצה חוזרת `no_match`,
   וזו תשובה שקטה ושגויה: היא נראית כמו "אין פלייבוק".
2. **משפחה שלא זוהתה היא שגיאה, לא `no_match`.** אם השם אינו ניתן
   לתרגום, התשובה הנכונה היא לעצור ולהגיד זאת, ולא להמשיך עם קוד שאינו
   קיים ולדווח שאין פלייבוק.
3. **`source_label`** - המשפט שמוצג למשתמש - נכתב לקובץ, כי הרכיב
   מצטט אותו ואינו מנסח אותו מחדש.
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
    """השם שהמשתמש אומר, ולא הקוד שבמפתח."""
    out = tmp_path / "res.json"
    r = _run(client, "הסכם שירותים", "מקבל השירותים", out=out)
    assert r.returncode == 0, r.stdout + r.stderr
    res = json.loads(out.read_text(encoding="utf-8"))
    assert res["result"] != "no_match", r.stdout
    assert res["chosen"].endswith("fam_services/playbook-core.json")


def test_the_codes_themselves_still_work(client, tmp_path):
    """הרכיב עצמו מעביר קודים, והתרגום אינו אמור לפגוע בהם."""
    out = tmp_path / "res.json"
    r = _run(client, "services", "service_recipient", out=out)
    assert r.returncode == 0, r.stdout + r.stderr
    res = json.loads(out.read_text(encoding="utf-8"))
    assert res["chosen"].endswith("fam_services/playbook-core.json")


def test_a_family_name_that_cannot_be_translated_stops_with_an_error(client, tmp_path):
    """לא `no_match` בשקט: עצירה, והקודים הקיימים נאמרים למשתמש."""
    out = tmp_path / "res.json"
    r = _run(client, "הסכם שאינו קיים בשום רשימה", "מקבל השירותים", out=out)
    assert r.returncode == 2, r.stdout + r.stderr
    assert "לא זוהתה משפחה" in r.stdout
    assert not out.exists(), "לא נכתב קובץ תוצאה כשהקלט לא זוהה"


def test_a_role_name_that_cannot_be_translated_stops_with_an_error(client, tmp_path):
    """`side_of` מחזיר None ו-`family_of` מחזיר 'unknown': שתי בדיקות שונות."""
    out = tmp_path / "res.json"
    r = _run(client, "הסכם שירותים", "צד שאינו קיים בשום רשימה", out=out)
    assert r.returncode == 2, r.stdout + r.stderr
    assert "לא זוהתה פוזיציה" in r.stdout
    assert not out.exists()


def test_a_synonym_role_code_from_the_index_passes_through(client, tmp_path):
    """`customer` אינו במילון העברי אבל הוא קוד מוכר, והמפתח מחזיק קודים כאלה."""
    out = tmp_path / "res.json"
    r = _run(client, "services", "customer", out=out)
    assert r.returncode == 0, r.stdout + r.stderr
    res = json.loads(out.read_text(encoding="utf-8"))
    assert res["chosen"].endswith("fam_services/playbook-core.json"), res


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
