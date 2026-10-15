# -*- coding: utf-8 -*-
"""בדיקות לשומר הכתיבה של `extract_corpus.py` בשני הסקילים.

הקלט של הסקריפט הוא **ההסכמים של הלקוח**, ולפני התיקון `--out` נכתב בלי
שום בדיקה ועם ברירת מחדל שקטה. `--out` שהצביע על הסכם דרס אותו ב-JSON.
זה הבאג שענבל סימנה כקריטי בסבב 4 של הספרייה (`common/cli.py`), והעותקים
שבסקילים נכתבו לפניו.

שני העותקים זהים בתוכן, ולכן הבדיקה רצה על שניהם: תיקון באחד ולא בשני
הוא בדיוק מה שקורה לקוד משוכפל.
"""
import json
import subprocess
import sys
from pathlib import Path

import pytest

PLUGIN = Path(__file__).resolve().parents[1]
SKILLS = PLUGIN / "areolegal" / "skills"
COPIES = [SKILLS / "contract-risk-assessor" / "scripts" / "extract_corpus.py",
          SKILLS / "contract-playbook-builder" / "scripts" / "extract_corpus.py"]


@pytest.fixture
def corpus(tmp_path):
    d = tmp_path / "ההסכמים"
    d.mkdir()
    (d / "הסכם שירותים.txt").write_text("הסכם שירותים\n1. התמורה תשולם בתוך 30 יום.\n",
                                        encoding="utf-8")
    (d / "הסכם סודיות.md").write_text("הסכם סודיות\n2. הצד המקבל ישמור בסודיות.\n",
                                      encoding="utf-8")
    return d


def _run(script, args):
    return subprocess.run([sys.executable, str(script)] + [str(x) for x in args],
                          capture_output=True, text=True, cwd=str(script.parent))


@pytest.mark.parametrize("script", COPIES, ids=lambda p: p.parents[1].name)
def test_the_two_copies_are_identical(script):
    """עותק שמתקן רק אחד מהם הוא הסיבה שהבדיקה הזאת קיימת."""
    assert COPIES[0].read_bytes() == COPIES[1].read_bytes()


@pytest.mark.parametrize("script", COPIES, ids=lambda p: p.parents[1].name)
def test_the_extract_runs(script, corpus, tmp_path):
    out = tmp_path / "corpus.json"
    r = _run(script, [corpus, "--out", out])
    assert r.returncode == 0, r.stdout + r.stderr
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["document_count"] == 2, data


@pytest.mark.parametrize("script", COPIES, ids=lambda p: p.parents[1].name)
def test_an_output_on_top_of_an_agreement_is_refused(script, corpus):
    """הסכם של הלקוח אינו קובץ פלט, גם כשהמשתמש הקליד אותו."""
    victim = corpus / "הסכם שירותים.txt"
    before = victim.read_text(encoding="utf-8")
    r = _run(script, [corpus, "--out", victim])
    assert r.returncode == 1, r.stdout + r.stderr
    assert "סירוב" in r.stdout
    assert victim.read_text(encoding="utf-8") == before, "ההסכם נדרס"


@pytest.mark.parametrize("script", COPIES, ids=lambda p: p.parents[1].name)
def test_the_output_path_is_required(script, corpus):
    """ברירת מחדל כותבת לתיקייה שממנה הריצו, וזו כתיבה שלא התבקשה."""
    r = _run(script, [corpus])
    assert r.returncode != 0
    assert "--out" in (r.stderr + r.stdout)


@pytest.mark.parametrize("script", COPIES, ids=lambda p: p.parents[1].name)
def test_an_existing_word_file_is_refused_even_outside_the_corpus(script, corpus, tmp_path):
    """guard_out מסרב על מסמך Word קיים, ולא רק על קובץ שנקרא בריצה."""
    doc = tmp_path / "חוזה חתום.docx"
    doc.write_bytes(b"PK\x03\x04 not really a docx, but it is a .docx on disk")
    before = doc.read_bytes()
    r = _run(script, [corpus, "--out", doc])
    assert r.returncode == 1, r.stdout + r.stderr
    assert doc.read_bytes() == before
