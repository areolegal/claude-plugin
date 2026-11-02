"""בדיקות CLI מסבב התיקונים שאחרי הסקירה הכוללת."""
import json
import os
import subprocess
import sys

from helpers import make_docx, make_extract

import clm_paths  # noqa: E402
ROOT = clm_paths.SKILL
CLI = os.path.join(ROOT, "scripts", "clm_cli.py")


def run(*args):
    return subprocess.run([sys.executable, CLI, *args], capture_output=True, text=True, encoding="utf-8")


def load(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def write_extract(data_dir, ext):
    d = os.path.join(str(data_dir), "ingest", "extract")
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, ext["sha256"] + ".json"), "w", encoding="utf-8") as f:
        json.dump(ext, f, ensure_ascii=False)


def test_changed_file_not_extracted_keeps_previous_sha_and_number(tmp_path):
    folder = tmp_path / "הסכמים"
    folder.mkdir()
    doc = folder / "הסכם שירותים - חתום.docx"
    make_docx(str(doc), body_xml="<w:p><w:r><w:t>גרסה 1</w:t></w:r></w:p>")
    data_dir = tmp_path / "Areo-נתונים"
    assert run("scan", "--folders", str(folder), "--data-dir", str(data_dir)).returncode == 0
    f = load(data_dir / "ingest" / "scan.json")["files"][0]
    write_extract(data_dir, make_extract(f["sha256"], f["path"]))
    args = ("assemble", "--data-dir", str(data_dir), "--company", "חברה", "--today", "2026-10-22")
    assert run(*args).returncode == 0
    first_sha = f["sha256"]
    make_docx(str(doc), body_xml="<w:p><w:r><w:t>גרסה 2</w:t></w:r></w:p>")
    assert run("scan", "--folders", str(folder), "--data-dir", str(data_dir)).returncode == 0
    assert load(data_dir / "ingest" / "scan.json")["files"][0]["status"] == "changed"
    assert run(*args).returncode == 0
    assert load(data_dir / "ingest" / "state.json") == {f["path"]: first_sha}
    data = load(data_dir / "clm-data.json")
    assert [a["number"] for a in data["agreements"]] == ["CLM-2026-0001"] and len(data["events"]) == 1
    r = run("scan", "--folders", str(folder), "--data-dir", str(data_dir))
    assert "לחילוץ: 1" in r.stdout, r.stdout


def _one_agreement(tmp_path, our_role):
    folder = tmp_path / "הסכמים"
    folder.mkdir()
    make_docx(str(folder / "הסכם שירותים - חתום.docx"))
    data_dir = tmp_path / "Areo-נתונים"
    assert run("scan", "--folders", str(folder), "--data-dir", str(data_dir)).returncode == 0
    f = load(data_dir / "ingest" / "scan.json")["files"][0]
    write_extract(data_dir, make_extract(f["sha256"], f["path"], our_role=our_role))
    return data_dir


def test_assemble_reads_playbook_index_from_data_dir(tmp_path):
    data_dir = _one_agreement(tmp_path, {"value": "", "source": "none"})
    os.makedirs(data_dir / "playbooks" / "fam_services_customer")
    # הצורה שכותב register_playbook: company_role_code ו-core_path, והתווית בקובץ הגרעין
    index = {"playbooks": [{"core_path": "playbooks/fam_services_customer/playbook-core.json",
                            "family_id": "fam_services_customer", "family_code": "services_mgmt",
                            "company_role_code": "customer", "family_name": "הסכם שירותים",
                            "family_aliases": ["שירותים מנוהלים"], "last_updated": "2026-10-01"}]}
    with open(data_dir / "playbooks" / "index.json", "w", encoding="utf-8") as fh:
        json.dump(index, fh, ensure_ascii=False)
    with open(data_dir / "playbooks" / "fam_services_customer" / "playbook-core.json", "w", encoding="utf-8") as fh:
        json.dump({"family_code": "services_mgmt", "company_role_code": "customer", "company_role": "לקוח"}, fh,
                  ensure_ascii=False)
    r = run("assemble", "--data-dir", str(data_dir), "--company", "חברה", "--today", "2026-10-22")
    assert r.returncode == 0, r.stderr
    role = load(data_dir / "clm-data.json")["agreements"][0]["our_role"]
    assert role == {"value": "לקוח", "source": "playbook", "confirmed": True}


def test_build_creates_output_folder_and_acceptance_reports_missing_file(tmp_path):
    data_dir = _one_agreement(tmp_path, {"value": "לקוח", "source": "user"})
    assert run("assemble", "--data-dir", str(data_dir), "--company", "חברה", "--today", "2026-10-22").returncode == 0
    out = tmp_path / "חדש" / "פנימי" / "Areo Workspace - חוזים.html"
    r = run("build", "--data", str(data_dir / "clm-data.json"), "--out", str(out))
    assert r.returncode == 0, r.stderr
    assert out.exists()
    r = run("acceptance", "--data", str(tmp_path / "אין.json"))
    assert r.returncode == 1 and "לא נמצא קובץ הנתונים" in r.stdout and "Traceback" not in r.stderr
    bad = tmp_path / "bad.json"
    bad.write_text("{bad", encoding="utf-8")
    r = run("acceptance", "--data", str(bad))
    assert r.returncode == 1 and "אינו JSON תקין" in r.stdout and "Traceback" not in r.stderr
