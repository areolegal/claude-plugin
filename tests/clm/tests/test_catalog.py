import re
from clm import catalog

FORBIDDEN = ["לפעול עד", "התממש", "משפחה", "סעיפים מהותיים", "\u2014", "\u2013"]
ALLOWED_FIELDS = {"cp", "date", "act_by", "notice", "title"}


def test_events_complete_and_valid():
    ev = catalog.load_events()
    assert len(ev) == 21
    for code, e in ev.items():
        for k in ("label", "category", "lead_days", "consequence", "rollable", "critical", "action", "if_nothing"):
            assert k in e, (code, k)
        assert e["category"] in catalog.CATEGORIES, code
        assert e["consequence"] in catalog.CONSEQUENCES, code
        assert isinstance(e["lead_days"], int) and e["lead_days"] >= 0
        fields = set(re.findall(r"{(\w+)}", e["action"]))
        assert fields <= ALLOWED_FIELDS, (code, fields)
        for word in FORBIDDEN:
            assert word not in e["label"] + e["action"] + e["if_nothing"], (code, word)


def test_types_have_required_keys():
    types = catalog.load_types()
    assert len(types) >= 8
    for code, t in types.items():
        assert t["type_code"] == code
        assert t["label"] and isinstance(t["aliases"], list) and isinstance(t["type_fields"], list)
        for f in t["type_fields"]:
            assert set(f) == {"key", "label", "kind"} and f["kind"] in {"text", "date", "money", "number", "list"}


def test_key_clauses_catalog():
    kc = catalog.load_key_clauses()
    for code in ("liability_cap", "indemnity", "exclusivity", "non_compete", "mfn", "assignment",
                 "change_of_control", "ip", "confidentiality", "data_protection", "data_transfer",
                 "set_off", "force_majeure", "governing_law"):
        assert code in kc
