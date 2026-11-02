"""קובץ שלא נקרא, וסיווג תבנית או מסמך שאינו הסכם לקובץ ששמו מעיד על הסכם חתום."""
import datetime as dt

from clm import assemble
from helpers import make_extract

TODAY = dt.date(2026, 10, 22)


def f(path, sha, status, **kw):
    row = {"path": path, "sha256": sha, "status": status, "abs": None, "duplicate_of": None}
    row.update(kw)
    return row


def test_unreadable_file_keeps_previous_extraction_and_is_reported():
    p, s = "x/a - חתום.docx", "a" * 64
    exts = {s: make_extract(s, p)}
    r1 = assemble.assemble({"files": [f(p, s, "new")]}, exts, "חברה", TODAY)
    r2 = assemble.assemble({"files": [f(p, s, "unreadable")]}, exts, "חברה", TODAY, previous=r1)
    assert [a["number"] for a in r2["agreements"]] == ["CLM-2026-0001"] and len(r2["events"]) == 1
    items = [r for r in r2["review_queue"] if r["kind"] == "unreadable"]
    assert len(items) == 1 and p in items[0]["text"] and items[0]["group"] == "קובץ שלא נקרא"
    fresh = assemble.assemble({"files": [f(p, None, "unreadable")]}, {}, "חברה", TODAY)
    assert fresh["agreements"] == [] and {"unreadable", "not_extracted"} <= {r["kind"] for r in fresh["review_queue"]}


def test_template_classification_of_a_signed_name_is_flagged():
    p, s = "x/הסכם שירותים - חתום.docx", "b" * 64
    ext = make_extract(s, p, doc_kind="template", events=[], commercials=[])
    d = assemble.assemble({"files": [f(p, s, "new")]}, {s: ext}, "חברה", TODAY)
    items = [r for r in d["review_queue"] if r["kind"] == "kind_conflict"]
    assert len(items) == 1 and "הסכם שירותים - חתום" in items[0]["text"] and "תבנית" in items[0]["text"]
    q, t = "x/מסמך.docx", "c" * 64
    ext2 = make_extract(t, q, doc_kind="non_agreement", events=[], commercials=[])
    d2 = assemble.assemble({"files": [f(q, t, "new", suggested_kind="signed")]}, {t: ext2}, "חברה", TODAY)
    assert [r["kind"] for r in d2["review_queue"]].count("kind_conflict") == 1
    plain = assemble.assemble({"files": [f(q, t, "new", suggested_kind="draft")]}, {t: ext2}, "חברה", TODAY)
    assert "kind_conflict" not in [r["kind"] for r in plain["review_queue"]]
