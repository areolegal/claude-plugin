# -*- coding: utf-8 -*-
"""שער המדיניות (`contract-playbook-builder/scripts/policy_gate.py`), מקצה לקצה:
גיליון עמדות, חתימה, קליטה, ואז השאלה של הנושא ונותן לכל הכרעה.

* תא שנחתם, והנוסח שהנושא ונותן מחיל הוא הנוסח שנחתם: `claim: true`.
* אותו תא, ונוסח אחר: `claim: false`, `wording_differs_from_approved`.
* פלייבוק שלא נחתם: `claim: false`, והמעמד Draft.
"""
import json
import subprocess
import sys
from pathlib import Path

import pytest

PLUGIN = Path(__file__).resolve().parents[1]
LIB = PLUGIN / "areolegal" / "lib"
GATE = PLUGIN / "areolegal" / "skills" / "contract-playbook-builder" / "scripts" / "policy_gate.py"
sys.path.insert(0, str(LIB))
sys.path.insert(0, str(LIB / "tests"))
pytest.importorskip("docx")

import pb_helpers as H  # noqa: E402
import test_approval as TA  # noqa: E402
from playbook import after_ingest as AI  # noqa: E402
from playbook import approval_sheet as A  # noqa: E402
from playbook import ingest_approval as I  # noqa: E402


def _gate(model_path, *args):
    r = subprocess.run([sys.executable, "-B", str(GATE), "--model", str(model_path)] + [str(x) for x in args],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    return json.loads(r.stdout)


@pytest.fixture
def signed_model(tmp_path):
    m = H.good_model()
    path, manifest = A.build_sheet(m, str(tmp_path / "to_sign"), company="EXAMPLECO", token_uid="0123456789ab")
    signed = TA._sign(path, tmp_path)
    res = TA._ingest(signed, manifest, today="2026-10-14")
    rec = I.save_record(str(tmp_path / "records"), signed, res)
    AI.apply_ingest(m, None, None, res, rec)
    mp = tmp_path / "playbook-model.json"
    mp.write_text(json.dumps(m, ensure_ascii=False), encoding="utf-8")
    return mp, manifest


def test_the_signed_wording_is_policy(signed_model):
    mp, manifest = signed_model
    wording = manifest["cells"]["R-07|-|green"]["wording"]
    out = _gate(mp, "--rule", "R-07", "--track", "green", "--wording", "  " + wording + " ")
    assert out["claim"] is True, out
    assert out["checked_at"] and out["track"] == "green"


def test_a_different_wording_is_not_policy(signed_model):
    mp, manifest = signed_model
    wording = manifest["cells"]["R-07|-|green"]["wording"] + " בשינוי קטן"
    out = _gate(mp, "--rule", "R-07", "--track", "green", "--wording", wording)
    assert out["claim"] is False and out["reason"] == "wording_differs_from_approved"


def test_an_unsigned_playbook_is_never_policy(tmp_path):
    mp = tmp_path / "playbook-model.json"
    mp.write_text(json.dumps(H.good_model(), ensure_ascii=False), encoding="utf-8")
    out = _gate(mp, "--rule", "R-07", "--track", "green")
    assert out["claim"] is False and out["status"] == "Draft"


def test_an_unknown_rule_is_input_error(tmp_path):
    mp = tmp_path / "playbook-model.json"
    mp.write_text(json.dumps(H.good_model(), ensure_ascii=False), encoding="utf-8")
    r = subprocess.run([sys.executable, "-B", str(GATE), "--model", str(mp), "--rule", "R-999", "--track", "red"],
                       capture_output=True, text=True)
    assert r.returncode == 2
