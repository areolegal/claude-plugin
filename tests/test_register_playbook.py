# -*- coding: utf-8 -*-
"""בדיקות ל-`register_playbook.py`.

`playbook-schema.md`: "פלייבוק לעולם אינו נכתב על פלייבוק של סוג אחר או
של פוזיציה אחרת, ואינו דוחק אותו", והגרסה הקודמת של אותו פלייבוק נשמרת
ב-`versions/`. `playbook-qa.md`, בדיקה 3, היא שלושת הדברים: נשמר
בתיקייה שלו, הרשומה עודכנה, ולא השתנתה שום רשומה אחרת.

הסיכון שהבדיקות כאן שומרות מפניו הוא אובדן עבודה של הלקוח: רישום
שמוחק רשומה של פוזיציה אחרת, או בנייה מחדש שדורסת את הפלייבוק הקודם
בלי שמור. שניהם שקטים, ושניהם מתגלים רק כשמחפשים פלייבוק ואין.
"""
import json
import subprocess
import sys
from pathlib import Path

import pytest

PLUGIN = Path(__file__).resolve().parents[1]
LIB = PLUGIN / "areolegal" / "lib"
SCRIPT = (PLUGIN / "areolegal" / "skills" / "contract-playbook-builder"
          / "scripts" / "register_playbook.py")

sys.path.insert(0, str(LIB))
sys.path.insert(0, str(LIB / "tests"))
pytest.importorskip("docx")

import pb_helpers as H  # noqa: E402


def _run(args):
    return subprocess.run([sys.executable, str(SCRIPT)] + [str(x) for x in args],
                          capture_output=True, text=True, cwd=str(SCRIPT.parent))


@pytest.fixture
def built(tmp_path):
    """מודל וגרעין בתיקיית בנייה, ותיקיית נתונים של לקוח."""
    model = H.round3_model()
    model.setdefault("family_id", "fam_nda_mutual")
    model.setdefault("family_code", "nda")
    model.setdefault("company_role_code", "mutual")
    model.setdefault("output_language", "he")
    build = tmp_path / "בנייה"
    build.mkdir()
    mp, cp = build / "playbook-model.json", build / "playbook-core.json"
    mp.write_text(json.dumps(model, ensure_ascii=False), encoding="utf-8")
    cp.write_text(json.dumps({"clauses": [], "family_code": "nda",
                              "company_role_code": "mutual"},
                             ensure_ascii=False), encoding="utf-8")
    data = tmp_path / "Areo-נתונים"
    data.mkdir()
    return {"data": data, "model": mp, "core": cp, "spec": model}


def _index(data):
    return json.loads((data / "playbooks" / "index.json").read_text(encoding="utf-8"))


def test_the_playbook_lands_in_its_own_folder_with_an_entry(built):
    r = _run(["--data", built["data"], "--model", built["model"], "--core", built["core"]])
    assert r.returncode == 0, r.stdout + r.stderr
    folder = built["data"] / "playbooks" / "fam_nda_mutual"
    assert (folder / "playbook-model.json").exists()
    assert (folder / "playbook-core.json").exists()
    entries = _index(built["data"])["playbooks"]
    assert len(entries) == 1
    e = entries[0]
    # השדות שהאיתור קורא. בלעדיהם הרשומה קיימת ואינה נמצאת
    assert e["core_path"] == "playbooks/fam_nda_mutual/playbook-core.json"
    assert e["family_code"] == "nda" and e["company_role_code"] == "mutual"
    assert e["status_label"] and e["playbook_status"]


def test_another_position_is_not_pushed_out(built):
    """אותו סוג הסכם, הצד ההפוך: שתי רשומות, ולא אחת."""
    idx = built["data"] / "playbooks"
    idx.mkdir(parents=True)
    other = {"core_path": "playbooks/fam_nda_disclosing/playbook-core.json",
             "family_id": "fam_nda_disclosing", "family_code": "nda",
             "company_role_code": "disclosing", "language": "he",
             "last_updated": "2026-09-01"}
    (idx / "index.json").write_text(json.dumps({"playbooks": [other]}, ensure_ascii=False),
                                    encoding="utf-8")
    r = _run(["--data", built["data"], "--model", built["model"], "--core", built["core"]])
    assert r.returncode == 0, r.stdout + r.stderr
    entries = _index(built["data"])["playbooks"]
    assert other in entries, entries
    assert len(entries) == 2, entries
    assert "רשומות שלא נגעתי בהן: 1" in r.stdout


def test_registering_again_replaces_only_its_own_entry(built):
    r1 = _run(["--data", built["data"], "--model", built["model"], "--core", built["core"]])
    assert r1.returncode == 0, r1.stdout
    r2 = _run(["--data", built["data"], "--model", built["model"], "--core", built["core"]])
    assert r2.returncode == 0, r2.stdout
    entries = _index(built["data"])["playbooks"]
    assert len(entries) == 1, entries


def test_the_previous_version_is_kept_and_not_overwritten(built):
    """בנייה מחדש אינה דורסת: הקודם נשמר ב-versions/."""
    r1 = _run(["--data", built["data"], "--model", built["model"], "--core", built["core"]])
    assert r1.returncode == 0, r1.stdout
    first = (built["data"] / "playbooks" / "fam_nda_mutual"
             / "playbook-model.json").read_text(encoding="utf-8")

    model = dict(built["spec"])
    model["version"] = "1.1"
    built["model"].write_text(json.dumps(model, ensure_ascii=False), encoding="utf-8")
    r2 = _run(["--data", built["data"], "--model", built["model"], "--core", built["core"]])
    assert r2.returncode == 0, r2.stdout
    versions = list((built["data"] / "playbooks" / "fam_nda_mutual" / "versions").iterdir())
    kept = [p for p in versions if p.name.endswith("playbook-model.json")]
    assert kept, [p.name for p in versions]
    assert kept[0].read_text(encoding="utf-8") == first
    assert "הגרסה הקודמת נשמרה" in r2.stdout


def test_a_legacy_root_playbook_is_registered_without_moving_it(built):
    """פלייבוק במבנה הישן שאינו באינדקס אינו נמצא באיתור."""
    legacy = built["data"] / "playbook-core.json"
    legacy.write_text(json.dumps({"clauses": [], "family_code": "services",
                                  "company_role_code": "service_recipient"},
                                 ensure_ascii=False), encoding="utf-8")
    (built["data"] / "playbook-model.json").write_text(
        json.dumps({"family_id": "fam_services_recipient", "family_code": "services",
                    "company_role_code": "service_recipient"}, ensure_ascii=False),
        encoding="utf-8")
    r = _run(["--data", built["data"], "--model", built["model"], "--core", built["core"]])
    assert r.returncode == 0, r.stdout + r.stderr
    entries = _index(built["data"])["playbooks"]
    lg = [e for e in entries if e.get("legacy")]
    assert len(lg) == 1, entries
    assert lg[0]["core_path"] == "playbook-core.json"
    assert legacy.exists(), "הפלייבוק הישן הוזז"
    assert "בלי להזיז אותו" in r.stdout


def test_a_model_without_a_family_id_is_refused(built):
    """בלי family_id אין תיקייה ואין רשומה, ואין לנחש אותו."""
    model = dict(built["spec"])
    model.pop("family_id")
    built["model"].write_text(json.dumps(model, ensure_ascii=False), encoding="utf-8")
    r = _run(["--data", built["data"], "--model", built["model"], "--core", built["core"]])
    assert r.returncode == 3, r.stdout + r.stderr
    assert "family_id" in r.stdout
    assert not (built["data"] / "playbooks").exists()


def test_a_model_missing_the_fields_the_resolver_reads_is_refused(built):
    """רשומה בלי family_code או פוזיציה קיימת ואינה נמצאת. זה גרוע מכשל."""
    model = dict(built["spec"])
    model.pop("family_code")
    model.pop("company_role_code")
    built["model"].write_text(json.dumps(model, ensure_ascii=False), encoding="utf-8")
    built["core"].write_text(json.dumps({"clauses": []}, ensure_ascii=False), encoding="utf-8")
    r = _run(["--data", built["data"], "--model", built["model"], "--core", built["core"]])
    assert r.returncode == 3, r.stdout + r.stderr
    assert "לא תימצא באיתור" in r.stdout


def test_the_dry_run_writes_nothing(built):
    r = _run(["--data", built["data"], "--model", built["model"], "--core", built["core"],
              "--dry-run"])
    assert r.returncode == 0, r.stdout + r.stderr
    assert not (built["data"] / "playbooks").exists()
    assert "ריצה יבשה" in r.stdout


def test_the_registered_playbook_is_then_found_by_the_resolver(built):
    """המטרה כולה: שהאיתור ימצא אותו. זו הבדיקה שסוגרת את הלולאה."""
    r = _run(["--data", built["data"], "--model", built["model"], "--core", built["core"]])
    assert r.returncode == 0, r.stdout + r.stderr
    resolver = (PLUGIN / "areolegal" / "skills" / "contract-negotiation-orchestrator"
                / "scripts" / "resolve_playbook.py")
    out = subprocess.run([sys.executable, str(resolver), "--data", str(built["data"]),
                          "--folder", str(built["data"]), "--family", "nda",
                          "--role", "mutual", "--language", "he"],
                         capture_output=True, text=True, cwd=str(resolver.parent))
    assert out.returncode == 0, out.stdout + out.stderr
    assert "fam_nda_mutual" in out.stdout, out.stdout
