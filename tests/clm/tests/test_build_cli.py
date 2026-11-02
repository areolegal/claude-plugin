import json
import os
import subprocess
import sys

from helpers import make_docx, make_extract

import clm_paths  # noqa: E402
ROOT = clm_paths.SKILL
CLI = os.path.join(ROOT, "scripts", "clm_cli.py")


def _load(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def _dump(obj, p):
    with open(p, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False)


def _read(p):
    with open(p, encoding="utf-8") as f:
        return f.read()


def run(*args):
    return subprocess.run([sys.executable, CLI, *args], capture_output=True, text=True, encoding="utf-8")


def test_end_to_end(tmp_path):
    folder = tmp_path / "הסכמים"
    folder.mkdir()
    make_docx(str(folder / "הסכם שירותים - חתום.docx"), body_xml="<w:p><w:r><w:t>הסכם</w:t></w:r></w:p>")
    make_docx(str(folder / "תבנית NDA.docx"), body_xml="<w:p><w:r><w:t>תבנית</w:t></w:r></w:p>")
    (folder / "HR").mkdir()
    make_docx(str(folder / "HR" / "הסכם העסקה - חתום.docx"))
    (folder / "HR2").mkdir()
    make_docx(str(folder / "HR2" / "אחר.docx"))
    data_dir = tmp_path / "Areo-נתונים"
    # --exclude: נתיב מוחלט, באותיות קטנות ובלוכסנים הפוכים, מתאים לגבול תיקייה בלבד (HR2 אינה מוחרגת)
    r = run("scan", "--folders", str(folder), "--data-dir", str(data_dir), "--exclude", str(folder / "hr").lower() + "\\")
    assert r.returncode == 0, r.stderr
    scan = _load(data_dir / "ingest" / "scan.json")
    assert sorted(f["path"] for f in scan["files"]) == ["הסכמים/HR2/אחר.docx", "הסכמים/הסכם שירותים - חתום.docx",
                                                       "הסכמים/תבנית NDA.docx"]
    os.remove(str(folder / "HR2" / "אחר.docx"))
    r = run("scan", "--folders", str(folder), "--data-dir", str(data_dir), "--exclude", "hr")
    assert r.returncode == 0, r.stderr
    scan = _load(data_dir / "ingest" / "scan.json")
    assert {f["suggested_kind"] for f in scan["files"]} == {"signed", "template"}
    os.makedirs(data_dir / "ingest" / "extract")
    for f in scan["files"]:
        kind = f["suggested_kind"]
        ext = make_extract(f["sha256"], f["path"], doc_kind=kind)
        if kind == "template":
            ext["events"], ext["commercials"] = [], []
        _dump(ext, data_dir / "ingest" / "extract" / (f["sha256"] + ".json"))
    r = run("assemble", "--data-dir", str(data_dir), "--company", "חברת בדיקה בע\"מ", "--today", "2026-10-22")
    assert r.returncode == 0, r.stderr
    data_file = str(data_dir / "clm-data.json")
    assert run("validate", "--data", data_file).returncode == 0
    out = str(tmp_path / "Areo Workspace - חוזים.html")
    assert run("build", "--data", data_file, "--out", out).returncode == 0
    html = _read(out)
    assert "__DATA__" not in html and "חברת בדיקה" in html and "תצוגה מקדימה" not in html
    state = _load(data_dir / "ingest" / "state.json")
    assert len(state) == 2


def test_validate_fails_on_bad_file(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps({"meta": {}}), encoding="utf-8")
    assert run("validate", "--data", str(bad)).returncode == 1


def _scan_two(tmp_path):
    folder = tmp_path / "הסכמים"
    folder.mkdir()
    make_docx(str(folder / "הסכם א - חתום.docx"), body_xml="<w:p><w:r><w:t>אחד</w:t></w:r></w:p>")
    make_docx(str(folder / "הסכם ב - חתום.docx"), body_xml="<w:p><w:r><w:t>שניים</w:t></w:r></w:p>")
    data_dir = tmp_path / "Areo-נתונים"
    r = run("scan", "--folders", str(folder), "--data-dir", str(data_dir))
    assert r.returncode == 0, r.stderr
    scan = _load(data_dir / "ingest" / "scan.json")
    return folder, data_dir, scan


def test_state_keeps_unextracted_files_in_the_queue(tmp_path):
    folder, data_dir, scan = _scan_two(tmp_path)
    assert len(scan["files"]) == 2
    done, pending = scan["files"][0], scan["files"][1]
    os.makedirs(data_dir / "ingest" / "extract")
    ext = make_extract(done["sha256"], done["path"], doc_kind="signed")
    _dump(ext, data_dir / "ingest" / "extract" / (done["sha256"] + ".json"))
    r = run("assemble", "--data-dir", str(data_dir), "--company", "חברה", "--today", "2026-10-22")
    assert r.returncode == 0, r.stderr
    state = _load(data_dir / "ingest" / "state.json")
    assert list(state) == [done["path"]]
    r = run("scan", "--folders", str(folder), "--data-dir", str(data_dir))
    assert "לחילוץ: 1" in r.stdout, r.stdout
    again = _load(data_dir / "ingest" / "scan.json")
    status = {f["path"]: f["status"] for f in again["files"]}
    assert status[pending["path"]] == "new" and status[done["path"]] == "same"


def test_key_clause_labels_reach_the_dataset_and_the_html(tmp_path):
    folder, data_dir, scan = _scan_two(tmp_path)
    f = scan["files"][0]
    os.makedirs(data_dir / "ingest" / "extract")
    ext = make_extract(f["sha256"], f["path"], doc_kind="signed", key_clauses_checked=True,
                       key_clauses=[{"clause_code": "change_of_control", "summary": "נדרשת הסכמה", "value": "",
                                     "clause": "סעיף 20", "quote": "שינוי שליטה מחייב הסכמה"}])
    _dump(ext, data_dir / "ingest" / "extract" / (f["sha256"] + ".json"))
    assert run("assemble", "--data-dir", str(data_dir), "--company", "חברה", "--today", "2026-10-22").returncode == 0
    data_file = str(data_dir / "clm-data.json")
    data = _load(data_file)
    assert data["key_clauses"][0]["clause_code"] == "change_of_control"
    assert data["key_clause_labels"]["change_of_control"] == "שינוי שליטה"
    assert run("validate", "--data", data_file).returncode == 0
    out = str(tmp_path / "out.html")
    assert run("build", "--data", data_file, "--out", out).returncode == 0
    assert "key_clause_labels" in _read(out)


def test_validate_reports_invalid_json_without_traceback(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text("{bad", encoding="utf-8")
    r = run("validate", "--data", str(bad))
    assert r.returncode == 1 and "אינו JSON תקין" in r.stdout and "Traceback" not in r.stderr


def test_validate_prints_warnings(tmp_path):
    folder, data_dir, scan = _scan_two(tmp_path)
    f = scan["files"][0]
    os.makedirs(data_dir / "ingest" / "extract")
    ext = make_extract(f["sha256"], f["path"], doc_kind="signed")
    _dump(ext, data_dir / "ingest" / "extract" / (f["sha256"] + ".json"))
    assert run("assemble", "--data-dir", str(data_dir), "--company", "חברה", "--today", "2026-10-22").returncode == 0
    data_file = data_dir / "clm-data.json"
    data = _load(data_file)
    data["events"][0]["refs"] = []
    _dump(data, data_file)
    r = run("validate", "--data", str(data_file))
    assert "אזהרה: " in r.stdout and "אין ציטוט" in r.stdout, r.stdout


def test_files_scanned_excludes_removed_and_duplicates():
    import datetime as dt
    from clm import assemble
    scan = {"files": [
        {"path": "a.docx", "sha256": "a" * 64, "status": "new", "abs": None, "duplicate_of": None},
        {"path": "b.docx", "sha256": "a" * 64, "status": "duplicate", "abs": None, "duplicate_of": "a.docx"},
        {"path": "c.docx", "sha256": "c" * 64, "status": "removed", "abs": None, "duplicate_of": None}]}
    data = assemble.assemble(scan, {"a" * 64: make_extract("a" * 64, "a.docx")}, "חברה", dt.date(2026, 10, 22))
    assert data["meta"]["files_scanned"] == 1
