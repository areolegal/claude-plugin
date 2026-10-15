# -*- coding: utf-8 -*-
"""בדיקות לסתירת מעמד בין השכבות, ב-`validate_playbook_model.py`.

`playbook-schema.md`: התווית היא "שדה התווית היחיד, והמשפט היחיד שמתאר
את מעמד הפלייבוק, **בכל תוצר ובכל רכיב**". כשהמודל אומר "מדיניות
מאושרת" והגרעין אומר "טעון אישור", שניהם שקריים: אחד מהם מוצג ללקוחה
ואין לדעת איזה. זה קרה בסבב 2, והמאמת דאז בדק שלושה שדות ברמה העליונה
והחזיר "תקין".

הבדיקה אינה דורשת מודל שלם וכשר: היא על **נוכחות הממצא**, כי מודל פגום
בשכבה אחרת אינו סיבה לפספס סתירת מעמד.
"""
import json
import subprocess
import sys
from pathlib import Path

import pytest

PLUGIN = Path(__file__).resolve().parents[1]
LIB = PLUGIN / "areolegal" / "lib"
VALIDATOR = (PLUGIN / "areolegal" / "skills" / "contract-playbook-builder"
             / "scripts" / "validate_playbook_model.py")

sys.path.insert(0, str(LIB))
sys.path.insert(0, str(LIB / "tests"))
pytest.importorskip("docx")

import pb_helpers as H  # noqa: E402


def _run(args):
    return subprocess.run([sys.executable, str(VALIDATOR)] + [str(x) for x in args],
                          capture_output=True, text=True, cwd=str(VALIDATOR.parent))


def _drift(stdout):
    return [l for l in stdout.split("\n") if "status drift" in l]


@pytest.fixture
def model_on_disk(tmp_path):
    m = H.round3_model()
    p = tmp_path / "playbook-model.json"
    p.write_text(json.dumps(m, ensure_ascii=False), encoding="utf-8")
    return m, p


def test_a_core_that_says_something_else_is_a_drift_finding(model_on_disk, tmp_path):
    m, path = model_on_disk
    core = tmp_path / "playbook-core.json"
    core.write_text(json.dumps({
        "clauses": [],
        "status_label": "מדיניות מאושרת, 01.01.2026, בידי מישהו אחר, תפקיד"},
        ensure_ascii=False), encoding="utf-8")
    r = _run([path, "--core", core])
    found = _drift(r.stdout)
    assert any("core.status_label" in l for l in found), r.stdout[-1500:]
    assert r.returncode == 1


def test_a_double_label_field_is_a_drift_finding(model_on_disk):
    """שתי תוויות באותה רשומה הן תקלה, גם כשהן אומרות אותו דבר."""
    m, path = model_on_disk
    r = _run([path])
    found = _drift(r.stdout)
    assert any("presentation_label" in l and "כפול" in l for l in found), r.stdout[-1500:]


def test_an_index_entry_that_lags_behind_is_a_drift_finding(model_on_disk, tmp_path):
    """הרשומה באינדקס היא מה שרכיב אחר קורא, ולכן היא שכבה ככל השכבות."""
    m, path = model_on_disk
    entry = tmp_path / "entry.json"
    entry.write_text(json.dumps({"playbook_status": "Approved"},
                                ensure_ascii=False), encoding="utf-8")
    r = _run([path, "--index", entry])
    assert any("index.playbook_status" in l for l in _drift(r.stdout)), r.stdout[-1500:]


def test_a_consistent_core_produces_no_drift_finding(model_on_disk, tmp_path):
    """הבדיקה אינה מרעישה: גרעין שאומר את המחושב אינו ממצא."""
    m, path = model_on_disk
    core = tmp_path / "playbook-core.json"
    core.write_text(json.dumps({"clauses": [], "status_label": m["status_label"],
                                "playbook_status": m["playbook_status"]},
                               ensure_ascii=False), encoding="utf-8")
    r = _run([path, "--core", core])
    assert not [l for l in _drift(r.stdout) if l.startswith("- status drift: core.")], r.stdout[-1500:]


def test_the_missing_library_is_reported_and_not_passed_over(model_on_disk, monkeypatch, tmp_path):
    """בדיקות שלא רצו אינן בדיקות שעברו."""
    m, path = model_on_disk
    stub = tmp_path / "scripts"
    stub.mkdir()
    (stub / "areo_lib.py").write_text("raise ImportError('אין ספרייה')\n", encoding="utf-8")
    (stub / "validate_playbook_model.py").write_bytes(VALIDATOR.read_bytes())
    r = subprocess.run([sys.executable, str(stub / "validate_playbook_model.py"), str(path)],
                       capture_output=True, text=True, cwd=str(stub))
    assert "not importable" in r.stdout, r.stdout[-800:]
    assert r.returncode == 1
