"""צד החברה מהפלייבוק, מדדי הקבלה המורחבים, ותיעוד מקור צד החברה."""
import copy
import datetime as dt
import json
import os

from clm import acceptance, assemble
from helpers import make_extract

import clm_paths  # noqa: E402
ROOT = clm_paths.SKILL
TODAY = dt.date(2026, 10, 22)
P, S = "x/a - חתום.docx", "a" * 64
SCAN = {"files": [{"path": P, "sha256": S, "status": "new", "abs": None, "duplicate_of": None}]}
PENDING = {"value": "", "source": "none"}


def entry(**kw):
    """רשומה בצורה שכותב register_playbook.model_entry: אין בה company_role; התווית בקובץ הגרעין."""
    fid = kw.get("family_id", "fam_services_customer")
    row = {"core_path": "playbooks/%s/playbook-core.json" % fid, "family_id": fid, "family_code": "services_mgmt",
           "company_role_code": "customer", "family_aliases": ["שירותים מנוהלים"], "family_name": "הסכם שירותים",
           "language": "he", "last_updated": "2026-10-01", "playbook_status": "Draft", "status_label": "טיוטה",
           "corpus_origin": "own"}
    row.update(kw)
    return row


def books(tmp_path, *entries, labels=None):
    """כותב Areo-נתונים/playbooks/index.json וקובצי playbook-core.json, ומחזיר את מה ש-load_playbooks קורא."""
    data = tmp_path / "Areo-נתונים"
    for e in entries:
        label = (labels or {}).get(e["family_id"], "לקוח")
        if label is not None and e.get("core_path"):
            core = data / e["core_path"]
            core.parent.mkdir(parents=True, exist_ok=True)
            core.write_text(json.dumps({"family_code": e.get("family_code"), "company_role_code": e.get("company_role_code"),
                                        "company_role": label}, ensure_ascii=False), encoding="utf-8")
    (data / "playbooks").mkdir(parents=True, exist_ok=True)
    index = data / "playbooks" / "index.json"
    index.write_text(json.dumps({"playbooks": list(entries)}, ensure_ascii=False), encoding="utf-8")
    rows, err = assemble.load_playbooks(str(index))
    assert err is None
    return rows


def run(ext, playbooks):
    return assemble.assemble(SCAN, {S: ext}, "חברה", TODAY, playbooks=playbooks)


def test_role_from_playbook_core_by_alias_or_family_code(tmp_path):
    d = run(make_extract(S, P, our_role=PENDING), books(tmp_path, entry()))
    a = d["agreements"][0]
    assert a["our_role"] == {"value": "לקוח", "source": "playbook", "confirmed": True}
    assert not [r for r in d["review_queue"] if r["kind"] == "role"] and d["events"][0]["role_pending"] is False
    by_code = run(make_extract(S, P, our_role=PENDING, type_label="אחר"),
                  books(tmp_path / "b", entry(family_name="x", family_aliases=[], family_code="services")))
    assert by_code["agreements"][0]["our_role"]["source"] == "playbook"


def test_role_label_falls_back_to_code_and_legacy_shape_still_read(tmp_path):
    rows = books(tmp_path, entry(), labels={"fam_services_customer": None})
    assert run(make_extract(S, P, our_role=PENDING), rows)["agreements"][0]["our_role"]["value"] == "customer"
    legacy = books(tmp_path / "l", {"family_id": "fam_old", "family_name": "שירותים מנוהלים", "company_role": "לקוח",
                                    "path": "playbooks/fam_old/playbook-model.json"})
    assert run(make_extract(S, P, our_role=PENDING), legacy)["agreements"][0]["our_role"]["value"] == "לקוח"


def test_explicit_family_id_or_code_wins_and_unknown_id_stays_pending(tmp_path):
    rows = books(tmp_path, entry(), entry(family_id="fam_x", family_code="sup_code", family_name="y", family_aliases=[],
                                          company_role_code="supplier"), labels={"fam_x": "ספק"})
    ext = make_extract(S, P, our_role=PENDING, type_label="אחר", playbook_family_id="fam_x")
    assert run(ext, rows)["agreements"][0]["our_role"]["value"] == "ספק"
    by_code = make_extract(S, P, our_role=PENDING, type_label="אחר", playbook_family_id="sup_code")
    assert run(by_code, rows)["agreements"][0]["our_role"]["value"] == "ספק"
    gone = run(make_extract(S, P, our_role=PENDING, playbook_family_id="fam_missing"), rows)
    assert gone["agreements"][0]["our_role"]["confirmed"] is False
    assert any("fam_missing" in r["text"] for r in gone["review_queue"] if r["kind"] == "role")


def test_ambiguous_or_contradicting_playbook_does_not_confirm(tmp_path):
    rows = books(tmp_path, entry(), entry(family_id="fam_b", company_role_code="supplier"), labels={"fam_b": "ספק"})
    two = run(make_extract(S, P, our_role=PENDING), rows)
    assert two["agreements"][0]["our_role"]["confirmed"] is False
    clash = run(make_extract(S, P, our_role={"value": "ספק", "source": "suggested"}), books(tmp_path / "c", entry()))
    assert clash["agreements"][0]["our_role"] == {"value": "ספק", "source": "suggested", "confirmed": False}
    assert any("פלייבוק" in r["text"] for r in clash["review_queue"] if r["kind"] == "role")


def test_playbook_family_id_must_be_text():
    from clm.validate import check_extraction
    assert check_extraction(make_extract(S, P, playbook_family_id="fam_x")) == []
    assert any("playbook_family_id" in p for p in check_extraction(make_extract(S, P, playbook_family_id=5)))


def test_user_confirmation_in_extraction_wins_over_playbook():
    d = run(make_extract(S, P, our_role={"value": "ספק", "source": "user"}), [entry()])
    assert d["agreements"][0]["our_role"] == {"value": "ספק", "source": "user", "confirmed": True}


def test_user_confirmation_survives_a_new_head_version():
    r1 = run(make_extract(S, P, our_role={"value": "ספק", "source": "user"}), [])
    s2 = "b" * 64
    scan2 = {"files": [{"path": P, "sha256": s2, "status": "changed", "abs": None, "duplicate_of": None}]}
    r2 = assemble.assemble(scan2, {s2: make_extract(s2, P, our_role={"value": "לקוח", "source": "suggested"})},
                           "חברה", TODAY, previous=r1, playbooks=[entry()])
    assert r2["agreements"][0]["our_role"] == {"value": "ספק", "source": "user", "confirmed": True}


def test_load_playbooks(tmp_path):
    assert assemble.load_playbooks(str(tmp_path / "none.json")) == ([], None)
    rows = books(tmp_path, entry(), {"family_id": "no_role", "family_name": "z"})
    assert [r["family_id"] for r in rows] == ["fam_services_customer"] and rows[0]["company_role"] == "לקוח"
    p = tmp_path / "Areo-נתונים" / "playbooks" / "index.json"
    p.write_text("{bad", encoding="utf-8")
    rows, err = assemble.load_playbooks(str(p))
    assert rows == [] and err


def test_acceptance_fails_on_empty_register():
    ok, lines = acceptance.report({"documents": [], "agreements": [], "events": []})
    assert ok is False and any("יותר מ-0 הסכמים" in x and x.startswith("נכשל") for x in lines)


def test_missing_quotes_counted_across_all_items():
    ext = make_extract(S, P, guarantees=[{"kind": "ערבות", "title": "ע", "amount": "1", "expiry": None, "clause": "9",
                                          "quote": "", "direction": "given"}],
                       key_clauses=[{"clause_code": "liability_cap", "summary": "תקרה", "value": "", "clause": "12",
                                     "quote": ""}])
    ext["commercials"][0]["quote"] = ""
    d = assemble.assemble(SCAN, {S: ext}, "חברה", TODAY)
    m = acceptance.metrics(d)
    assert m["events_without_quote"] == 0 and m["items_without_quote"] == 3
    assert acceptance.report(d)[0] is False
    clean = copy.deepcopy(assemble.assemble(SCAN, {S: make_extract(S, P)}, "חברה", TODAY))
    assert acceptance.report(clean)[0] is True


def read(*p):
    # references/<file> is served content (get_resource), not in the plugin: read it from server/content
    base, p = (clm_paths.REFS_DIR, p[1:]) if p and p[0] == "references" else (ROOT, p)
    with open(os.path.join(base, *p), encoding="utf-8") as fh:
        return fh.read()


def test_docs_explain_playbook_role_and_per_browser_marks():
    skill, fmt = read("SKILL.md"), read("references", "extraction-format.md")
    for text in (skill, fmt):
        assert "playbooks/index.json" in text and '"source": "user"' in text
    assert "playbook_family_id" in fmt
    assert "בדפדפן" in skill
    assert "**ישות:**" not in skill and "החברה המתקשרת" in skill
    assert len(skill.encode("utf-8")) < 20000
