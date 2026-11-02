# -*- coding: utf-8 -*-
"""בונה הפלייבוק רץ מהעותקים שבתוסף, ובדיקה שלא רצה אינה נבלעת.

* אין הורדה מהשרת בזמן ריצה (Cowork חוסם הורדות מ-areo.co.il): התבניות של סביבת העבודה והאשף נארזו ב-assets של
  הרכיב, ותבנית עמוד התשאול ב-areolegal/ui. בלי ארגומנט נלקח העותק שבתוסף; ארגומנט מפורש גובר.
* enforce_playbook_checks.py שהורץ ישירות לא הכניס את areolegal/lib לנתיב, ולכן בדיקת המספיקות
  (playbook.sufficiency) דולגה בשקט. עכשיו היא רצה גם בהרצה כתהליך נפרד, ב-python -B וב-python -I.
"""
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

PLUGIN = Path(__file__).resolve().parents[1]
SKILL = PLUGIN / "areolegal" / "skills" / "contract-playbook-builder"
SCRIPTS = SKILL / "scripts"
ASSETS = SKILL / "assets"
LIB = PLUGIN / "areolegal" / "lib"
FIXTURE_MODEL = LIB / "tests" / "fixtures" / "playbook" / "mutual_nda_model_good.json"


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, str(path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ---------------------------------------------------------------- enforce: בדיקת המספיקות רצה כתהליך נפרד
def _thin_model(limitations=None):
    """הסכם חתום אחד בסוג, בלי עקבות משא ומתן: insufficient לפי playbook/sufficiency.assess."""
    return {"rules": [], "source_log": [{"source_id": "S1", "doc_role": "signed", "family_id": "fam_x",
                                         "included": True, "paper": "ours"}],
            "scope_summary": {"limitations": limitations or []}}


@pytest.mark.parametrize("flags", [["-B"], ["-B", "-I"]])
def test_enforce_runs_the_sufficiency_check_when_run_directly(tmp_path, flags):
    mp = tmp_path / "playbook-model.json"
    mp.write_text(json.dumps(_thin_model(), ensure_ascii=False), encoding="utf-8")
    r = subprocess.run([sys.executable] + flags + [str(SCRIPTS / "enforce_playbook_checks.py"), str(mp)],
                       capture_output=True, text=True, cwd=str(tmp_path))
    out = r.stdout + r.stderr
    assert "בדיקת המספיקות לא רצה" not in out, out
    assert "המאגר מתחת לסף המספיקות (insufficient)" in out, out
    assert r.returncode == 3, out


def test_enforce_passes_the_sufficiency_check_when_the_limitation_is_recorded(tmp_path):
    mp = tmp_path / "playbook-model.json"
    mp.write_text(json.dumps(_thin_model(["מדגם של הסכם אחד בלבד"]), ensure_ascii=False), encoding="utf-8")
    r = subprocess.run([sys.executable, "-B", str(SCRIPTS / "enforce_playbook_checks.py"), str(mp)],
                       capture_output=True, text=True, cwd=str(tmp_path))
    assert "סף המספיקות" not in r.stdout and r.returncode == 0, r.stdout + r.stderr


# ---------------------------------------------------------------- finalize: התבניות מהתוסף כברירת מחדל
@pytest.fixture
def finalize(monkeypatch, tmp_path):
    mod = _load("finalize_playbook_under_test", SCRIPTS / "finalize_playbook.py")
    calls = []

    def fake_run(name, args, report):
        calls.append((name, [str(a) for a in args]))
        report.append({"step": name, "ok": True, "exit": 0, "tail": ""})
        return True
    monkeypatch.setattr(mod, "run", fake_run)
    files = {}
    for k in ("model", "profile", "extract"):
        p = tmp_path / ("%s.json" % k)
        p.write_text("{}", encoding="utf-8")
        files[k] = str(p)
    base = ["--model", files["model"], "--core", str(tmp_path / "core.json"), "--data", str(tmp_path),
            "--profile", files["profile"], "--lang", "he", "--extract", files["extract"],
            "--workspace", str(tmp_path / "ws.html"), "--out-dir", str(tmp_path / "out"),
            "--index", str(tmp_path / "index.json"), "--inventory", str(tmp_path / "inv.json")]
    return mod, calls, base, tmp_path


def _step(calls, name):
    return next(args for n, args in calls if n == name)


def test_the_default_templates_ship_in_the_plugin():
    mod = _load("finalize_playbook_paths", SCRIPTS / "finalize_playbook.py")
    assert Path(mod.DEFAULT_DASHBOARD_TEMPLATE) == ASSETS / "dashboard_template.html"
    assert Path(mod.DEFAULT_WIZARD_TEMPLATE) == ASSETS / "wizard_template.html"
    for p in (mod.DEFAULT_DASHBOARD_TEMPLATE, mod.DEFAULT_WIZARD_TEMPLATE, ASSETS / "chart.umd.js"):
        assert Path(p).is_file(), p
    assert (LIB / "מקורות-מאושרים.json").is_file()


def test_finalize_uses_the_plugin_templates_when_the_args_are_omitted(finalize):
    mod, calls, base, _ = finalize
    assert mod.main(base) == 0
    dash = _step(calls, "workspace")
    assert dash[1] == mod.DEFAULT_DASHBOARD_TEMPLATE
    assert dash[dash.index("--wizard") + 1] == mod.DEFAULT_WIZARD_TEMPLATE
    # בלי --approved-sources המאמת קורא את AREO_APPROVED_SOURCES ואחריו את העותק שבתוסף; לא מועבר נתיב ריק
    assert "--approved-sources" not in _step(calls, "validate_model")


def test_finalize_explicit_args_still_win(finalize):
    mod, calls, base, tmp_path = finalize
    dash_t, wiz_t, src = (tmp_path / "d.html", tmp_path / "w.html", tmp_path / "s.json")
    for p in (dash_t, wiz_t, src):
        p.write_text("x", encoding="utf-8")
    assert mod.main(base + ["--dashboard-template", str(dash_t), "--wizard-template", str(wiz_t),
                            "--approved-sources", str(src)]) == 0
    dash = _step(calls, "workspace")
    assert dash[1] == str(dash_t) and dash[dash.index("--wizard") + 1] == str(wiz_t)
    vm = _step(calls, "validate_model")
    assert vm[vm.index("--approved-sources") + 1] == str(src)


def test_finalize_runs_its_steps_without_isolated_mode():
    """-I מסתיר את ספריות המשתמש (python-docx שהותקן ב-pip --user ב-macOS)."""
    src = (SCRIPTS / "finalize_playbook.py").read_text(encoding="utf-8")
    assert "'-I'" not in src


# ---------------------------------------------------------------- build_dashboard: שני ארגומנטים = התבנית שבתוסף
def test_build_dashboard_without_a_template_uses_the_plugin_copy(tmp_path):
    mod = _load("build_dashboard_paths", SCRIPTS / "build_dashboard.py")
    assert Path(mod.DEFAULT_TEMPLATE) == ASSETS / "dashboard_template.html" and Path(mod.DEFAULT_TEMPLATE).is_file()
    pay = tmp_path / "payload.json"
    r = subprocess.run([sys.executable, "-B", str(SCRIPTS / "build_workspace_payload.py"), str(FIXTURE_MODEL),
                        str(pay)], capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    out = tmp_path / "ws.html"
    r = subprocess.run([sys.executable, "-B", str(SCRIPTS / "build_dashboard.py"), str(pay), str(out)],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    html = out.read_text(encoding="utf-8")
    assert len(html) > 100000
    # האשף נבנה מהתבנית שליד תבנית הדף, כלומר מהעותק שבתוסף
    assert list(tmp_path.glob("ws.wizard.*.html")), r.stdout


# ---------------------------------------------------------------- עמוד התשאול: התבנית שבתוסף
def test_the_intake_view_reads_the_template_in_the_plugin():
    mod = _load("build_intake_view_paths", LIB / "common" / "build_intake_view.py")
    assert Path(mod.TEMPLATE) == PLUGIN / "areolegal" / "ui" / "intake-view-template.html"
    assert Path(mod.TEMPLATE).is_file()
