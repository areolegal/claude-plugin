import copy
import datetime as dt
from clm import acceptance, assemble
from helpers import make_extract


def data():
    s = "a" * 64
    scan = {"files": [{"path": "x/a - חתום.docx", "sha256": s, "status": "new", "abs": None, "duplicate_of": None}]}
    return assemble.assemble(scan, {s: make_extract(s, "x/a - חתום.docx")}, "חברה", dt.date(2026, 10, 22))


def test_clean_data_passes():
    ok, lines = acceptance.report(data())
    assert ok, lines


def test_failures_detected():
    d = copy.deepcopy(data())
    d["events"][0]["refs"] = []
    d["agreements"][0]["type_code"] = None
    m = acceptance.metrics(d)
    assert m["events_without_quote"] == 1 and m["other_pct"] == 100.0
    assert acceptance.report(d)[0] is False
