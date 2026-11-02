# -*- coding: utf-8 -*-
"""הצדדים של סוג ההסכם נקראים משני הסכמים (הכרעת ניל, 18.10.2026): המניפסט מחזיר
לכל סוג את כינויי הצדדים מהפתיח, כדי שהטופס ישאל "איזה צד מביניהם" ולא "מזמין או מספק".
"""
import json
import subprocess
import sys
from pathlib import Path

import pytest

PLUGIN = Path(__file__).resolve().parents[1]
S = PLUGIN / "areolegal" / "skills" / "contract-playbook-builder" / "scripts"
docx = pytest.importorskip("docx")


def _doc(path, paras):
    d = docx.Document()
    for t in paras:
        d.add_paragraph(t)
    d.save(str(path))


def test_roles_come_from_two_agreements_of_the_family(tmp_path):
    root = tmp_path / "הסכמים"
    root.mkdir()
    for i in range(3):
        _doc(root / ("lease%d.docx" % i), ["הסכם שכירות",
                                           "בין: נכסי דוגמה בע\"מ (\"המשכיר\") לבין: חברת %d בע\"מ (\"השוכר\")" % i,
                                           "המשכיר משכיר לשוכר את המושכר לתקופה של 24 חודשים.",
                                           "ולראיה באו הצדדים על החתום"])
    fam = tmp_path / "families.json"
    fam.write_text(json.dumps({"families": [{"contract_family_id": "lease", "label": "שכירות",
                                             "company_role_code": "tenant",
                                             "paths": ["lease0.docx", "lease1.docx", "lease2.docx"]}]},
                              ensure_ascii=False), encoding="utf-8")
    out = tmp_path / "manifest.json"
    r = subprocess.run([sys.executable, "-B", str(S / "build_corpus_manifest.py"), str(root), "--families", str(fam),
                        "--out", str(out)], capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    m = json.loads(out.read_text(encoding="utf-8"))
    f = m["by_family"][0]
    assert f["roles_hint"][:2] == ["המשכיר", "השוכר"]
    # הצדדים נלמדים מההסכמים עצמם לפני הטופס (הכרעת ניל 18.10, סעיף 2). מאז 01.11 הקוד סופר את כינויי הפתיח בכל
    # מסמכי הסוג, לפי מספר המסמכים שבהם הופיעו (b1-intake.md:191, build_corpus_manifest.family_roles), ולכן
    # roles_read_from כולל לפחות את שני ההסכמים, ובפועל את כל ההסכמים של הסוג
    assert len(f["roles_read_from"]) >= 2
    assert sorted(Path(p).name for p in f["roles_read_from"]) == ["lease0.docx", "lease1.docx", "lease2.docx"]
    # רק כינויי תפקיד, לא שם של צד
    assert not any("בע\"מ" in g for g in f["roles_hint"])
    assert all(x["parties_hint"][:2] == ["המשכיר", "השוכר"] for x in m["files"])
