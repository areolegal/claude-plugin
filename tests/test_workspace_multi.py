# -*- coding: utf-8 -*-
"""סביבת עבודה אחת לכל הפלייבוקים של החברה.

קובץ פלייבוק אחד לכל סוג הסכם ופוזיציה, ודף אחד שקורא את כולם דרך
`playbooks/index.json` ומציג אותם עם בורר בראש. הבורר מחליף את כל מה
שמוצג, ולא מסנן רשימה מעורבבת: מקור INT-01 של הסכמי שירותים אינו INT-01
של הסכמי סודיות, ומדיניות של סוג אחד אינה חלה על אחר.

שלושה דברים שנבדקים כאן, ושניים מהם נשברו בכתיבה:
* **זהות הספר אינה נדרסת.** `--meta` של ההדגמה הכיל `ls_key`, והוחל על
  כל הספרים. כך שני סוגים חלקו מפתח שמירה, והערה על R-01 בהסכמי סודיות
  הופיעה גם בהסכמי שירותים. זה נתפס בדפדפן.
* **לכל סוג יש אשף משלו,** והכפתור בדף מוביל לאשף של הסוג שנבחר. קובץ
  ההערות שהאשף מוציא נושא את מזהה הפלייבוק, ולכן `apply_decisions.py`
  דוחה אותו כשהוא מועלה לפלייבוק אחר.
* **כל ספר עובר את אותה בדיקה** שעובר דף של פלייבוק אחד.
"""
import copy
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "plugin" / "areolegal" / "skills" / "contract-playbook-builder" / "scripts"
CONTENT = ROOT / "server" / "content" / "playbook-workspace"
PAYLOAD = SCRIPTS / "build_workspace_payload.py"
BUILD = SCRIPTS / "build_dashboard.py"
VALIDATE = SCRIPTS / "validate_data.py"

pytestmark = pytest.mark.skipif(not (CONTENT / "demo-playbook-model.json").exists(),
                                reason="עץ התוכן (../server) אינו מחולץ כאן")


def _run(script, args):
    return subprocess.run([sys.executable, str(script)] + [str(a) for a in args],
                          capture_output=True, text=True)


@pytest.fixture
def client(tmp_path):
    """לקוח עם שני סוגי הסכמים, כל אחד בקובץ משלו, ואינדקס."""
    base = json.loads((CONTENT / "demo-playbook-model.json").read_text(encoding="utf-8"))
    data = tmp_path / "Areo-נתונים"
    entries = []

    def put(fid, label, role, updated, keep=None):
        m = copy.deepcopy(base)
        m["family_id"] = m["playbook_id"] = fid
        m["last_updated"] = updated
        sc = m.setdefault("scope_summary", {})
        fams = sc.get("contract_families") or [{}]
        fams[0] = dict(fams[0] or {}, contract_family_name=label, company_role=role)
        sc["contract_families"] = fams
        if keep:
            m["rules"] = m["rules"][:keep]
        d = data / "playbooks" / fid
        d.mkdir(parents=True)
        (d / "playbook-model.json").write_text(json.dumps(m, ensure_ascii=False), encoding="utf-8")
        (d / "playbook-core.json").write_text("{}", encoding="utf-8")
        entries.append({"core_path": "playbooks/%s/playbook-core.json" % fid,
                        "family_id": fid, "company_role_code": role})
        return m

    svc = put("fam_services_recipient", "הסכם שירותים", "מקבל השירותים", "2026-10-10")
    nda = put("fam_nda_mutual", "הסכם סודיות", "הדדי", "2026-10-14", keep=3)
    (data / "playbooks" / "index.json").write_text(
        json.dumps({"playbooks": entries}, ensure_ascii=False), encoding="utf-8")
    return {"data": data, "dir": tmp_path, "svc": svc, "nda": nda}


def _payload(client, *extra):
    out = client["dir"] / "payload.json"
    r = _run(PAYLOAD, ["--data", client["data"], out] + list(extra))
    assert r.returncode == 0, r.stdout + r.stderr
    return json.loads(out.read_text(encoding="utf-8")), out


def test_every_playbook_in_the_index_is_a_book(client):
    p, _ = _payload(client)
    assert set(p["books"]) == {"fam_services_recipient", "fam_nda_mutual"}
    assert len(p["books"]["fam_services_recipient"]["rules"]) == len(client["svc"]["rules"])
    assert len(p["books"]["fam_nda_mutual"]["rules"]) == 3
    ids = [x["id"] for x in p["playbooks"]]
    assert sorted(ids) == sorted(p["books"])
    for bid, b in p["books"].items():
        assert all(r["pb"] == bid for r in b["rules"])
        assert b["pb"]["id"] == bid


def test_the_most_recently_updated_opens_first_unless_told_otherwise(client):
    p, _ = _payload(client)
    cur = [x for x in p["playbooks"] if x["current"]]
    assert [x["id"] for x in cur] == ["fam_nda_mutual"]
    assert len(p["rules"]) == 3
    p2, _ = _payload(client, "--current", "fam_services_recipient")
    assert [x["id"] for x in p2["playbooks"] if x["current"]] == ["fam_services_recipient"]


def test_an_unknown_current_is_refused(client):
    r = _run(PAYLOAD, ["--data", client["data"], client["dir"] / "p.json",
                       "--current", "fam_nothing"])
    assert r.returncode != 0
    assert "fam_nothing" in (r.stdout + r.stderr)


def test_shared_meta_never_overrides_a_books_identity(client):
    """--meta של ההדגמה כולל ls_key. מפתח משותף מעביר הערות בין סוגים."""
    p, _ = _payload(client, "--meta", CONTENT / "demo-playbook-meta.json")
    keys = {bid: b["meta"]["ls_key"] for bid, b in p["books"].items()}
    assert len(set(keys.values())) == 2, keys
    # מה שאינו זהות כן מגיע לכל הספרים
    assert all(b["meta"].get("evidence_disclaimer") for b in p["books"].values())


def test_a_missing_model_is_reported_and_not_swallowed(client):
    shutil.rmtree(client["data"] / "playbooks" / "fam_nda_mutual")
    out = client["dir"] / "payload.json"
    r = _run(PAYLOAD, ["--data", client["data"], out])
    assert r.returncode == 0, r.stderr
    assert "fam_nda_mutual" in r.stderr
    assert list(json.loads(out.read_text(encoding="utf-8"))["books"]) == ["fam_services_recipient"]


def test_a_single_model_still_builds_as_before(client, tmp_path):
    out = tmp_path / "one.json"
    r = _run(PAYLOAD, [CONTENT / "demo-playbook-model.json", out])
    assert r.returncode == 0, r.stderr
    assert "books" not in json.loads(out.read_text(encoding="utf-8"))


def test_every_book_is_validated(client):
    _, path = _payload(client)
    r = _run(VALIDATE, ["--data", path])
    assert r.returncode == 0, r.stdout
    assert "books[fam_nda_mutual]" in r.stdout      # אזהרת הנתונים של ההדגמה, לכל ספר


def test_each_type_gets_its_own_wizard_and_the_page_links_to_it(client):
    _, path = _payload(client)
    out = client["dir"] / "סביבה.html"
    r = _run(BUILD, [CONTENT / "dashboard_template.html", path, out,
                     "--wizard", CONTENT / "wizard_template.html"])
    assert r.returncode == 0, r.stdout + r.stderr
    page = out.read_text(encoding="utf-8")
    data = json.loads(re.search(r"const D = (\{.*?\});\n", page, re.S).group(1))
    for bid, b in data["books"].items():
        href = b["meta"]["wizard_href"]
        wiz = client["dir"] / href
        assert wiz.exists(), href
        w = wiz.read_text(encoding="utf-8")
        wd = json.loads(re.search(r"const D = (\{.*?\});\n", w, re.S).group(1))
        # האשף הוא של הסוג הזה בלבד, ומזהה הפלייבוק הוא מה שהקליטה בודקת
        assert wd["pb"]["id"] == bid and wd["meta"]["id"] == bid
        assert len(wd["rules"]) == len(b["rules"])
        assert "books" not in wd
        assert wd["meta"]["dashboard_href"] == out.name


@pytest.mark.skipif(not shutil.which("node"), reason="node אינו מותקן")
def test_the_built_pages_parse(client):
    _, path = _payload(client)
    out = client["dir"] / "dash.html"
    r = _run(BUILD, [CONTENT / "dashboard_template.html", path, out,
                     "--wizard", CONTENT / "wizard_template.html"])
    assert r.returncode == 0, r.stdout + r.stderr
    for f in [out] + list(client["dir"].glob("dash.wizard.*.html")):
        js = "\n".join(re.findall(r"<script>(.*?)</script>", f.read_text(encoding="utf-8"), re.S))
        tmp = f.with_suffix(".check.js")
        tmp.write_text(js, encoding="utf-8")
        chk = subprocess.run(["node", "--check", str(tmp)], capture_output=True, text=True)
        assert chk.returncode == 0, (f.name, chk.stderr[-600:])
