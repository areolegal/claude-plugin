# -*- coding: utf-8 -*-
"""בדיקות ל-`compare_rounds.py`: חמשת הסיווגים, על קובץ אמיתי.

הבדיקה בונה את שני הקבצים מהפיקסצ'רים של ספריית הייחוס: מה שהחברה
שלחה (הטיוטה שהתקבלה + ההכרעות שלנו, בעקוב אחר שינויים), ומה שחזר,
אחרי שהצד שכנגד עשה בו את חמשת הדברים שהסקריפט אמור להבחין ביניהם:
קיבל הצעה אחת, דחה אחת, השאיר את השאר מסומנות, הוסיף שינוי במעקב,
ושינה פסקה אחת בלי מעקב בכלל.

שתי הטעויות שהבדיקה הזאת שומרת מהן, ושתיהן קרו בכתיבה:
1. **ההטלה הלא נכונה.** "מה הם פתחו בו" אינו `reject_all` של הקובץ
   שחזר: `reject_all` דוחה גם את הסימונים שלנו, ומחזיר את הנוסח שלפני
   ההצעה. הבסיס הנכון הוא לקבל את שלנו ולדחות את שלהם.
2. **דחייה שנראית כמו שינוי בשקט.** כשהצד שכנגד דוחה סימון שלנו, Word
   מסיר אותו ומחזיר את הנוסח הקודם. מהקובץ לבדו זה זהה לשינוי בלי
   מעקב, ולכן אותו סעיף דווח פעמיים. שינוי בשקט הוא רק הבדל שאינו
   מוסבר בגורל הסימון שלנו.
"""
import json
import subprocess
import sys
from pathlib import Path

import pytest

PLUGIN = Path(__file__).resolve().parents[1]
LIB = PLUGIN / "areolegal" / "lib"
SCRIPT = (PLUGIN / "areolegal" / "skills" / "contract-negotiation-orchestrator"
          / "scripts" / "compare_rounds.py")
FX = LIB / "tests" / "fixtures" / "orchestrator"

sys.path.insert(0, str(LIB))
pytest.importorskip("lxml")
pytest.importorskip("docx")

import common.docx_tracked as dt  # noqa: E402
from lxml import etree  # noqa: E402

W = dt.W


def _accept_ours(para, author):
    for el in list(para.iter(W + "ins")):
        if el.get(W + "author") == author:
            par = el.getparent()
            for ch in list(el):
                par.insert(list(par).index(el), ch)
            par.remove(el)
    for el in list(para.iter(W + "del")):
        if el.get(W + "author") == author:
            el.getparent().remove(el)


def _reject_ours(para, author):
    for el in list(para.iter(W + "ins")):
        if el.get(W + "author") == author:
            el.getparent().remove(el)
    for el in list(para.iter(W + "del")):
        if el.get(W + "author") == author:
            par = el.getparent()
            for ch in list(el):
                for node in ch.iter(W + "delText"):
                    node.tag = W + "t"
                par.insert(list(par).index(el), ch)
            par.remove(el)


@pytest.fixture(scope="module")
def round_pair(tmp_path_factory):
    """שני הקבצים, ומה נעשה בכל פסקה, כדי שהבדיקות יאשרו מול הכוונה."""
    out = tmp_path_factory.mktemp("rounds")
    received = FX / "services2_counterparty_draft.docx"
    dec = json.loads((FX / "services2_decisions_clean.json").read_text(encoding="utf-8"))
    author = dec["author"]
    sent = out / "sent.docx"
    res = dt.apply_decisions(str(received), dec, out_path=str(sent),
                             author=author, initials=dec["initials"])
    assert res["ok"] and not res["errors"], res["errors"]

    parts = dt.read_package(str(sent))
    root = etree.fromstring(parts["word/document.xml"])
    paras = dt.body_paragraphs(root)
    ours = [i for i, p in enumerate(paras)
            if dt.revision_text(p, "ins", author) or dt.revision_text(p, "del", author)]
    assert len(ours) >= 3, ours

    _accept_ours(paras[ours[0]], author)      # הצעה שהתקבלה
    _reject_ours(paras[ours[1]], author)      # הצעה שנדחתה
    # השאר נשארות מסומנות -> our_open

    silent = next(i for i, p in enumerate(paras)
                  if i not in ours and len(dt.para_text(p)) > 40)
    for node in paras[silent].iter(W + "t"):
        if (node.text or "").strip():
            node.text = (node.text or "") + " [שונה בשקט]"
            break

    theirs = next(i for i, p in enumerate(paras) if i not in ours and i != silent)
    ins = etree.SubElement(paras[theirs], W + "ins")
    ins.set(W + "id", "9001")
    ins.set(W + "author", "יועץ הצד שכנגד")
    ins.set(W + "date", "2026-10-15T10:00:00Z")
    run = etree.SubElement(ins, W + "r")
    node = etree.SubElement(run, W + "t")
    node.text = " תוספת של הצד שכנגד."
    node.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")

    parts["word/document.xml"] = etree.tostring(root, xml_declaration=True,
                                                encoding="UTF-8", standalone=True)
    back = out / "received.docx"
    back.write_bytes(dt.write_package(parts))
    return {"sent": sent, "received": back, "author": author,
            "open_count": len(ours) - 2}


def _run(pair, tmp_path):
    out = tmp_path / "compare.json"
    r = subprocess.run([sys.executable, str(SCRIPT), "--sent", str(pair["sent"]),
                        "--received", str(pair["received"]),
                        "--author", pair["author"], "--out", str(out)],
                       capture_output=True, text=True, cwd=str(SCRIPT.parent))
    assert r.returncode == 0, r.stdout + r.stderr
    return json.loads(out.read_text(encoding="utf-8")), r.stdout


def test_each_classification_is_counted_once(round_pair, tmp_path):
    data, _ = _run(round_pair, tmp_path)
    counts = data["counts"]
    assert counts.get("their_silent") == 1, "רק הפסקה שנשתנתה בלי מעקב"
    assert counts.get("their_tracked") == 1, "רק התוספת שלהם במעקב"
    assert counts.get("our_accepted") == 1
    assert counts.get("our_rejected") == 1
    assert counts.get("our_open") == round_pair["open_count"]


def test_a_rejected_proposal_is_not_reported_as_a_silent_change(round_pair, tmp_path):
    """דחייה מסירה את הסימון ומחזירה את הנוסח, וזה נראה כמו שינוי בשקט."""
    data, _ = _run(round_pair, tmp_path)
    rejected = [c for c in data["clauses"] if c["classification"] == "our_rejected"]
    silent = [c for c in data["clauses"] if c["classification"] == "their_silent"]
    assert len(rejected) == 1
    assert all(c.get("clause") != rejected[0].get("clause") for c in silent), \
        "אותו סעיף דווח גם כנדחה וגם כשינוי בשקט"


def test_the_silent_change_carries_both_texts(round_pair, tmp_path):
    """הממצא חסר ערך בלי שני הנוסחים: מה שלחנו, ומה הם פתחו בו."""
    data, _ = _run(round_pair, tmp_path)
    c = next(x for x in data["clauses"] if x["classification"] == "their_silent")
    assert c["we_sent"] and c["they_opened_with"]
    assert "[שונה בשקט]" in c["they_opened_with"]
    assert "[שונה בשקט]" not in c["we_sent"]


def test_the_silent_change_is_called_out_in_the_printed_summary(round_pair, tmp_path):
    _, printed = _run(round_pair, tmp_path)
    line = next(l for l in printed.split("\n") if "their_silent" in l)
    assert "הממצא החשוב ביותר" in line


def test_an_unchanged_round_reports_nothing(round_pair, tmp_path):
    """אותו קובץ מול עצמו: אין הבדל, ואין ממצא."""
    out = tmp_path / "same.json"
    r = subprocess.run([sys.executable, str(SCRIPT), "--sent", str(round_pair["sent"]),
                        "--received", str(round_pair["sent"]),
                        "--author", round_pair["author"], "--out", str(out)],
                       capture_output=True, text=True, cwd=str(SCRIPT.parent))
    assert r.returncode == 0, r.stdout + r.stderr
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["counts"].get("their_silent", 0) == 0
    assert data["counts"].get("our_accepted", 0) == 0
    assert data["counts"].get("our_rejected", 0) == 0
    # כל ההצעות עוד מסומנות, כי הקובץ הוא מה ששלחנו
    assert data["counts"].get("our_open", 0) > 0


def test_the_output_is_refused_when_it_would_overwrite_an_input(round_pair, tmp_path):
    """`--out` על קובץ הקלט הוא אובדן הטיוטה של הלקוח (common/cli.guard_out)."""
    r = subprocess.run([sys.executable, str(SCRIPT), "--sent", str(round_pair["sent"]),
                        "--received", str(round_pair["received"]),
                        "--author", round_pair["author"],
                        "--out", str(round_pair["received"])],
                       capture_output=True, text=True, cwd=str(SCRIPT.parent))
    assert r.returncode == 1
    assert "סירוב" in r.stdout
