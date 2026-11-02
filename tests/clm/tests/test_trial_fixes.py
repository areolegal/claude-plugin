"""תיקוני ניסוי ארבעת הסוגים: אף קובץ אינו נעלם בשקט, מייל, PDF סרוק, קובץ בודד ונתיב חסר, מקף בציטוט,
צד החברה מול הצדדים במסמך, שיוך תיקון להסכם, והרצה ב-python3 -B."""
import datetime as dt
import email.message
import json
import os
import re
import subprocess
import sys

import pytest

from clm import assemble, core, fingerprint
from clm.validate import check_data, check_extraction
from helpers import make_docx, make_extract

import clm_paths  # noqa: E402
ROOT = clm_paths.SKILL
CLI = os.path.join(ROOT, "scripts", "clm_cli.py")
TODAY = dt.date(2026, 10, 30)
DASH = chr(0x2013)  # מקף ארוך, בתוך ציטוט מילה במילה


def run(*args):
    # כמו שהסוכן מריץ: python3 -B (לעולם לא -I, שמסתיר python-docx שהותקן למשתמש ב-macOS; החלטה 02.11)
    return subprocess.run([sys.executable, "-B", CLI, *args], capture_output=True,
                          env={k: v for k, v in os.environ.items() if k != "PYTHONPATH"}, text=True, encoding="utf-8")


def sha(c):
    return c * 64


def scan_of(*items):
    return {"files": [dict({"path": p, "sha256": s, "status": st, "abs": None, "duplicate_of": None}, **kw)
                      for p, s, st, kw in items]}


def eml_bytes():
    msg = email.message.EmailMessage()
    msg["Subject"], msg["From"], msg["To"] = "Signed order", "legal@vendor.com", "legal@acme.com"
    msg.set_content("Attached is the signed order form.")
    msg.add_attachment(b"PK order", maintype="application", subtype="octet-stream", filename="Order Form - signed.docx")
    msg.add_attachment(b"\x89PNG", maintype="image", subtype="png", filename="logo.png")
    return msg.as_bytes()


# ---------- 4. אף קובץ אינו נעלם בשקט; מייל ----------
def test_eml_attachments_become_scan_entries_and_other_types_are_unsupported(tmp_path):
    root = tmp_path / "agreements"
    (root / "mail").mkdir(parents=True)
    (root / "mail" / "order.eml").write_bytes(eml_bytes())
    (root / "budget.xlsx").write_bytes(b"x")
    (root / "desktop.ini").write_bytes(b"x")
    (root / "Areo-נתונים").mkdir()
    (root / "Areo-נתונים" / "clm-data.json").write_text("{}", encoding="utf-8")
    report, work = {}, tmp_path / "ingest"
    by = {f["path"]: f for f in fingerprint.scan([str(root)], work_dir=str(work), report=report)}
    mail = by["agreements/mail/order.eml"]
    att = by["agreements/mail/order.eml/Order Form - signed.docx"]
    assert mail["status"] == "new" and mail["attachments"] == [att["path"], "agreements/mail/order.eml/logo.png"]
    assert att["status"] == "new" and att["container"] == mail["path"] and open(att["abs"], "rb").read() == b"PK order"
    assert "signed order form" in open(mail["text_path"], encoding="utf-8").read()
    assert by["agreements/mail/order.eml/logo.png"]["status"] == "unsupported"
    assert by["agreements/budget.xlsx"]["status"] == "unsupported"
    assert report["system"] == ["agreements/desktop.ini"] and report["data_dirs"][0].endswith("Areo-נתונים")
    assert not any("clm-data" in p for p in by)


def test_unsupported_file_opens_a_review_item_not_a_pending_extraction():
    scan = scan_of(("x/budget.xlsx", sha("a"), "unsupported", {"reason": "file_type"}))
    for lang in ("he", "en"):
        data = assemble.assemble(scan, {}, "חברה", TODAY, lang=lang)
        kinds = [r["kind"] for r in data["review_queue"]]
        assert kinds == ["unsupported"], kinds
        assert "x/budget.xlsx" in data["review_queue"][0]["text"]
        _, warns = check_data(data)
        assert any("budget.xlsx" in w for w in warns)


def test_eml_container_with_attachments_is_not_a_non_agreement_item():
    scan = scan_of(("x/order.eml", sha("a"), "new", {"attachments": ["x/order.eml/o.docx"]}),
                   ("x/order.eml/o.docx", sha("b"), "new", {"container": "x/order.eml"}))
    exts = {sha("a"): make_extract(sha("a"), "x/order.eml", doc_kind="non_agreement", events=[], commercials=[]),
            sha("b"): make_extract(sha("b"), "x/order.eml/o.docx")}
    data = assemble.assemble(scan, exts, "חברה", TODAY)
    assert "non_agreement" not in {r["kind"] for r in data["review_queue"]}
    assert [a["file"] for a in data["agreements"]] == ["x/order.eml/o.docx"]


# ---------- 5. PDF סרוק ----------
def _pdf(path, with_text):
    mu = fingerprint._pymupdf()
    doc = mu.open()
    page = doc.new_page()
    if with_text:
        page.insert_text((72, 100), "Services agreement between Acme Ltd and Nimbus Inc. Term 24 months.", fontsize=12)
    else:
        src = mu.open()
        sp = src.new_page()
        sp.insert_text((72, 100), "LEASE AGREEMENT", fontsize=20)
        page.insert_image(page.rect, stream=sp.get_pixmap(dpi=100).tobytes("png"))
    doc.save(path)


@pytest.mark.skipif(fingerprint._pymupdf() is None, reason="PyMuPDF אינו מותקן")
def test_scanned_pdf_is_flagged_and_warned_without_ocr(tmp_path, monkeypatch):
    root = tmp_path / "agreements"
    root.mkdir()
    _pdf(str(root / "lease - scan.pdf"), with_text=False)
    _pdf(str(root / "services.pdf"), with_text=True)
    monkeypatch.setattr(fingerprint, "tesseract", lambda: None)
    by = {f["path"]: f for f in fingerprint.scan([str(root)], work_dir=str(tmp_path / "ingest"))}
    assert by["agreements/lease - scan.pdf"]["scanned"] is True and by["agreements/lease - scan.pdf"]["ocr"] == "unavailable"
    assert "scanned" not in by["agreements/services.pdf"]
    scan = {"files": list(by.values())}
    for lang, word in (("he", "סרוק"), ("en", "scanned")):
        items = [r for r in assemble.assemble(scan, {}, "Acme", TODAY, lang=lang)["review_queue"] if r["kind"] == "scanned"]
        assert len(items) == 1 and word in items[0]["text"] and "lease - scan.pdf" in items[0]["text"]


@pytest.mark.skipif(fingerprint._pymupdf() is None or not fingerprint.tesseract(), reason="אין tesseract במחשב")
def test_scanned_pdf_gets_ocr_when_the_system_has_it(tmp_path):
    root = tmp_path / "agreements"
    root.mkdir()
    _pdf(str(root / "lease - scan.pdf"), with_text=False)
    f = fingerprint.scan([str(root)], work_dir=str(tmp_path / "ingest"))[0]
    assert f["ocr"] == "done" and "LEASE" in open(f["text_path"], encoding="utf-8").read().upper()


# ---------- 5. קובץ בודד ונתיב חסר; 19. python3 -B ----------
def test_cli_scan_accepts_a_single_file_and_stops_on_a_missing_path(tmp_path):
    folder = tmp_path / "הסכמים"
    folder.mkdir()
    make_docx(str(folder / "הסכם שירותים - חתום.docx"))
    (folder / "mail.eml").write_bytes(eml_bytes())
    data_dir = tmp_path / "Areo-נתונים"
    r = run("scan", "--folders", str(folder / "הסכם שירותים - חתום.docx"), "--data-dir", str(data_dir))
    assert r.returncode == 0, r.stderr
    scan = json.load(open(data_dir / "ingest" / "scan.json", encoding="utf-8"))
    assert [f["path"] for f in scan["files"]] == ["הסכמים/הסכם שירותים - חתום.docx"] and "נסרקו 1 קבצים" in r.stdout
    r = run("scan", "--folders", str(folder), "--data-dir", str(data_dir))
    assert r.returncode == 0 and "מייל: הסכמים/mail.eml, 2 קבצים מצורפים" in r.stdout and "logo.png" in r.stdout
    r = run("scan", "--folders", str(tmp_path / "אין כזו"), "--data-dir", str(data_dir))
    assert r.returncode == 2 and "לא נמצא" in r.stdout
    scan2 = json.load(open(data_dir / "ingest" / "scan.json", encoding="utf-8"))
    assert all(f["status"] != "removed" for f in scan2["files"])


# ---------- 5. מקף בציטוט ----------
def test_long_dash_in_a_quote_keeps_the_agreement_and_the_quote(tmp_path):
    quote = "כל צד רשאי להודיע " + DASH + " לפחות 90 ימים מראש."
    ext = make_extract(sha("a"), "x/a - חתום.docx", title="הסכם " + DASH + " בנק")
    ext["events"][0]["quote"] = quote
    assert check_extraction(ext) == ["נמצא מקף ארוך בטקסט שאינו ציטוט (בציטוט מותר): להחליף במקף רגיל"]
    (tmp_path / (sha("a") + ".json")).write_text(json.dumps(ext, ensure_ascii=False), encoding="utf-8")
    good, bad = assemble.load_extracts(str(tmp_path))
    assert not bad and good[sha("a")]["title"] == "הסכם - בנק" and good[sha("a")]["events"][0]["quote"] == quote
    data = assemble.assemble(scan_of(("x/a - חתום.docx", sha("a"), "new", {})), good, "חברה", TODAY)
    assert data["footnotes"][0]["quote"] == quote
    assert check_data(data)[0] == []


def test_rejected_extraction_is_a_validation_error_not_silence():
    ext = make_extract(sha("a"), "x/a - חתום.docx")
    scan = scan_of(("x/a - חתום.docx", sha("a"), "new", {}))
    bad = [{"file": "x/a - חתום.docx", "problems": ["events[0]: חסר clause"]}]
    for lang in ("he", "en"):
        data = assemble.assemble(scan, {}, "חברה", TODAY, bad_extracts=bad, lang=lang)
        errors, _ = check_data(data)
        assert len(errors) == 1 and "x/a - חתום.docx" in errors[0] and "חסר clause" in errors[0]
    assert ext  # החילוץ עצמו תקין; כאן נבדק רק המסלול של חילוץ שנפסל


# ---------- 5. צד החברה מול הצדדים במסמך ----------
PB_HE = [{"family_id": "fam_dpa_supplier", "family_code": "fam_dpa_supplier", "family_name": "DPA", "family_aliases": [],
          "company_role": "הספק (מחזיק / מעבד)"}]
PB_EN = [{"family_id": "fam_dpa", "family_code": "fam_dpa", "family_name": "DPA", "family_aliases": [],
          "company_role_code": "processor"}]


def _role(pb, lang, **kw):
    ext = make_extract(sha("a"), "x/dpa - signed.docx", our_role={"value": None, "source": "none"},
                       playbook_family_id=pb[0]["family_id"], **kw)
    data = assemble.assemble(scan_of(("x/dpa - signed.docx", sha("a"), "new", {})), {sha("a"): ext}, "ענןפלו", TODAY,
                             playbooks=pb, lang=lang)
    return data["agreements"][0]["our_role"], [r["text"] for r in data["review_queue"] if r["kind"] == "role"]


def test_playbook_side_is_pending_when_the_counterparty_holds_it_hebrew():
    role, items = _role(PB_HE, "he", counterparty={"name": "בזק בע\"מ", "company_number": None, "notice_address": None,
                                                    "role": "הספק"})
    assert role == {"value": "הספק (מחזיק / מעבד)", "source": "suggested", "confirmed": False}
    assert items and "בזק" in items[0] and "\"הספק\"" in items[0]


def test_playbook_side_is_pending_when_the_document_names_the_company_otherwise_english_delaware():
    role, items = _role(PB_EN, "en", governing_law="Delaware", contracting_role="Controller",
                        counterparty={"name": "Nimbus Inc.", "company_number": None, "notice_address": None})
    assert role["confirmed"] is False and "Controller" in items[0] and "processor" in items[0]


def test_playbook_side_is_confirmed_when_the_document_agrees():
    role, items = _role(PB_HE, "he", counterparty={"name": "קופת חולים", "company_number": None, "notice_address": None,
                                                    "role": "הלקוח"}, contracting_role="הספק")
    assert role == {"value": "הספק (מחזיק / מעבד)", "source": "playbook", "confirmed": True} and not items
    assert core.role_side("Landlord") == "provider" and core.role_side("השוכר") == "customer"
    assert core.role_side("הצד המקבל") is None


# ---------- 5. שיוך תיקון להסכם ----------
def test_amendment_links_to_its_framework_by_title_english():
    head = make_extract(sha("a"), "x/Datadog - Master Subscription Agreement.docx", title="Datadog Master Subscription Agreement",
                        counterparty={"name": "Datadog, Inc.", "company_number": None, "notice_address": None})
    kid = make_extract(sha("b"), "x/Datadog - Master Subscription Agreement - Amendment No. 1 (v2).docx", doc_kind="amendment",
                       title="Datadog Master Subscription Agreement, Amendment No. 1 (v2)",
                       counterparty={"name": "Datadog, Inc.", "company_number": None, "notice_address": None},
                       relation={"kind": "amendment", "parent_hint": "Datadog Master Subscription Agreement"},
                       dates={"signed": None, "start": "2025-03-01", "end": "2027-12-31"})
    other = make_extract(sha("c"), "x/Datadog - Order Form.docx", title="Datadog Order Form",
                         counterparty={"name": "Datadog, Inc.", "company_number": None, "notice_address": None})
    scan = scan_of(*((e["file"], e["sha256"], "new", {}) for e in (head, kid, other)))
    data = assemble.assemble(scan, {e["sha256"]: e for e in (head, kid, other)}, "Acme Ltd", TODAY, lang="en")
    by = {a["title"]: a for a in data["agreements"]}
    assert set(by) == {"Datadog Master Subscription Agreement", "Datadog Order Form"}
    assert len(by["Datadog Master Subscription Agreement"]["doc_ids"]) == 2
    kinds = [r["kind"] for r in data["review_queue"]]
    assert "orphan" not in kinds and "amendment_unconfirmed" in kinds
    # בלי תאריך חתימה התיקון אינו משנה את תאריך הסיום עד שאדם מאשר
    assert by["Datadog Master Subscription Agreement"]["dates"]["end"] == "2027-02-28"


def test_amendment_without_hint_uses_its_title_among_several_frameworks_hebrew():
    cp = {"name": "מגדלי הים בע\"מ", "company_number": None, "notice_address": None}
    lease = make_extract(sha("a"), "x/מגדלי הים - שכירות משרדים - חתום.docx", title="הסכם שכירות משרדים", counterparty=cp)
    parking = make_extract(sha("b"), "x/מגדלי הים - חניה - חתום.docx", title="הסכם חניה", counterparty=cp)
    kid = make_extract(sha("c"), "x/מגדלי הים - תיקון.docx", doc_kind="amendment", title="תיקון להסכם שכירות משרדים",
                       counterparty=cp, dates={"signed": "2026-01-01", "start": None, "end": "2028-02-28"})
    exts = {e["sha256"]: e for e in (lease, parking, kid)}
    data = assemble.assemble(scan_of(*((e["file"], e["sha256"], "new", {}) for e in exts.values())), exts, "חברה", TODAY)
    by = {a["title"]: a for a in data["agreements"]}
    assert len(by["הסכם שכירות משרדים"]["doc_ids"]) == 2 and len(by["הסכם חניה"]["doc_ids"]) == 1
    assert by["הסכם שכירות משרדים"]["dates"]["end"] == "2028-02-28"


def test_python_isolated_run_writes_no_bytecode_in_the_agent_folder(tmp_path):
    cache = os.path.join(ROOT, "scripts", "clm", "__pycache__")
    existed = os.path.isdir(cache)
    folder = tmp_path / "agreements"
    folder.mkdir()
    make_docx(str(folder / "a - signed.docx"))
    r = run("scan", "--folders", str(folder), "--data-dir", str(tmp_path / "Areo-נתונים"))
    assert r.returncode == 0, r.stderr
    assert existed or not os.path.isdir(cache)


# ---------- יתרת הניסוי 1: בלי חתימה ותחילה, לא "בתוקף" ----------
def _one(**kw):
    ext = make_extract(sha("a"), "x/a - חתום.docx", **kw)
    return assemble.assemble(scan_of(("x/a - חתום.docx", sha("a"), "new", {})), {sha("a"): ext}, "חברה", TODAY)


def test_no_dates_and_blank_signatures_is_never_in_force():
    blank = [{"party": "counterparty", "party_name": None, "name": None, "role": None, "date": None, "status": "blank",
              "clause": "חתימות", "quote": "____"}]
    for kw in ({"dates": {"signed": None, "start": None, "end": None}},
               {"dates": {"signed": None, "start": "2025-01-01", "end": None}, "signatories": blank}):
        d = _one(**kw)
        a = d["agreements"][0]
        assert a["agreement_state"] == "status_unverified" and a["signature"] == "unknown", kw
        assert a["value"]["in_portfolio"] is False
        assert any(r["kind"] == "signing_unverified" for r in d["review_queue"])
        assert check_data(d)[0] == []
    assert _one()["agreements"][0]["agreement_state"] != "status_unverified"   # יש תאריך חתימה


# ---------- יתרת הניסוי 2: מועד יעד שחלף ----------
def _notice_and_term():
    notice = dict(make_extract(sha("a"), "x")["events"][0], date="2026-10-02", renewal_months=12, label="הודעת אי-חידוש")
    term = dict(notice, event_code="term_end", label="תום התקופה", date="2026-12-31", consequence="auto_change",
                impact="material", renewal_months=12, quote="ההסכם מסתיים ב-31.12.2026.")
    return notice, term


def test_passed_notice_closes_the_renewal_decision_and_a_passed_act_by_is_overdue():
    notice, term = _notice_and_term()
    d = _one(events=[notice, term], dates={"signed": "2024-01-01", "start": "2025-01-01", "end": "2026-12-31"})
    t_end = [e for e in d["events"] if e["event_code"] == "term_end" and e.get("occurrence") != "passed"][0]
    assert t_end["decision_closed"] is True and t_end["overdue_bucket"] is None and "יתחדש" in t_end["action"]
    assert "ההחלטה הבאה" in t_end["action"]
    # בלי מועד הודעה שחלף: מועד היעד חלף והמועד עתידי, ולכן באיחור לפעולה שלנו
    lone = dict(term, date="2026-12-01", renewal_months=None)
    first = _one(events=[lone])
    e = [x for x in first["events"] if x["event_code"] == "term_end"][0]
    assert e["state"] == "upcoming" and e["act_by_passed"] is True and e["overdue_bucket"] == "ours"
    assert e["action"].startswith("מועד היעד לטיפול (2.9.2026) חלף.")
    again = assemble.assemble(scan_of(("x/a - חתום.docx", sha("a"), "same", {})), {}, "חברה", TODAY, previous=first)
    carried = [x for x in again["events"] if x["event_code"] == "term_end"][0]
    assert carried["action"].count("מועד היעד לטיפול") == 1


def _page(tmp_path, data, exprs, pre=""):
    import shutil
    if not shutil.which("node"):
        pytest.skip("node אינו מותקן")
    from clm import build
    dp, out, ex, hx = (tmp_path / n for n in ("d.json", "p.html", "e.json", "h.js"))
    dp.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    build.build(str(dp), os.path.join(ROOT, "assets", "workspace-template.html"), str(out))
    ex.write_text(json.dumps(exprs), encoding="utf-8")
    harness = open(clm_paths.HARNESS, encoding="utf-8").read()
    hx.write_text(harness.replace("global.window = global;", "global.window = global;" + pre), encoding="utf-8")
    r = subprocess.run(["node", str(hx), str(out), str(ex)], capture_output=True, text=True, encoding="utf-8")
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


def test_dashboard_counts_passed_act_by_and_renewals_skip_closed_decisions(tmp_path):
    notice, term = _notice_and_term()
    lone = dict(term, date="2026-12-01", label="תום תקופה אחר", renewal_months=None)
    ext_a = make_extract(sha("a"), "x/a - חתום.docx", events=[notice, term])
    ext_b = make_extract(sha("b"), "x/b - חתום.docx", title="הסכם שני", events=[lone],
                         counterparty={"name": "צד שני", "company_number": None, "notice_address": None})
    scan = scan_of(("x/a - חתום.docx", sha("a"), "new", {}), ("x/b - חתום.docx", sha("b"), "new", {}))
    data = assemble.assemble(scan, {sha("a"): ext_a, sha("b"): ext_b}, "חברה", TODAY)
    p = _page(tmp_path, data, {"od": "overdue().map(e => e.label)", "renew": "V.renew()",
                               "due": "due(400).map(e => e.label)"})
    assert "תום תקופה אחר" in p["od"] and "תום התקופה" not in p["od"]
    assert "תום התקופה" not in p["due"]
    # הסכם א מוצג לפי חלון ההודעה הבא, לא לפי ההחלטה שנסגרה; הסכם ב מוצג עם "מועד היעד חלף"
    assert p["renew"].count('class="st dec"') == 2 and "מועד היעד חלף" in p["renew"]


# ---------- יתרת הניסוי 3: קישור ל-#review ----------
def test_hash_link_opens_that_screen(tmp_path):
    data = _one()
    pre = ' global.location = {hash: "#review"}; global.history = {replaceState() {}};'
    assert _page(tmp_path, data, {"cur": "cur"}, pre=pre)["cur"] == "review"
    assert _page(tmp_path, data, {"cur": "cur"}, pre=' global.location = {hash: "#nothing"};')["cur"] == "dash"


# ---------- יתרת הניסוי 4: יחיד ורבים, ונקודה כפולה ----------
def test_singular_wording_and_no_double_period(tmp_path):
    ev = dict(make_extract(sha("a"), "x")["events"][0], event_code="payment_milestone", label="Payment",
              date="2027-05-01", consequence="we_breach", impact="material", renewal_months=None,
              action="Pay the invoice of Datadog, Inc..")
    ext = make_extract(sha("a"), "x/Datadog - signed.docx", title="Datadog MSA", events=[ev],
                       counterparty={"name": "Datadog, Inc.", "company_number": None, "notice_address": None})
    for lang, bad in (("en", r"(^|[^\d])1 (agreements|decisions|files|details|dates)\b"),
                      ("he", r"(^|[^\d])1 (הסכמים|החלטות|קבצים|פרטים|מועדים)")):
        data = assemble.assemble(scan_of(("x/Datadog - signed.docx", sha("a"), "new", {})), {sha("a"): ext},
                                 "Acme", TODAY, lang=lang)
        assert data["events"][0]["action"] == "Pay the invoice of Datadog, Inc."
        p = _page(tmp_path, data, {"dash": "V.dash()", "review": "V.review()", "repo": "V.repo()"})
        for k, html in p.items():
            assert not re.search(bad, re.sub(r"<[^>]+>", " ", html)), (lang, k)
    assert assemble.tidy_text("Wait... ok") == "Wait... ok"
    assert core.count(1, "חידוש אחד", "חידושים", "renewal", "renewals") == "חידוש אחד"


# ---------- יתרת הניסוי 5: הדין המקומי ----------
def test_home_law_from_profile_and_unknown_without_it(tmp_path):
    folder = tmp_path / "agreements"
    folder.mkdir()
    make_docx(str(folder / "a - signed.docx"))
    data_dir = tmp_path / "Areo-נתונים"
    assert run("scan", "--folders", str(folder), "--data-dir", str(data_dir)).returncode == 0
    f = json.load(open(data_dir / "ingest" / "scan.json", encoding="utf-8"))["files"][0]
    os.makedirs(data_dir / "ingest" / "extract")
    with open(data_dir / "ingest" / "extract" / (f["sha256"] + ".json"), "w", encoding="utf-8") as fh:
        json.dump(make_extract(f["sha256"], f["path"], governing_law="The laws of England and Wales"), fh, ensure_ascii=False)

    def assemble_with(profile, old=None):
        (data_dir / "פרופיל-לקוח.json").write_text(json.dumps(profile), encoding="utf-8")
        target = data_dir / "clm-data.json"
        if old is not None:
            target.write_text(json.dumps(old, ensure_ascii=False), encoding="utf-8")
        elif target.exists():
            os.remove(target)
        r = run("assemble", "--data-dir", str(data_dir), "--company", "Acme Ltd", "--today", "2026-10-30", "--lang", "en")
        assert r.returncode == 0, r.stderr
        return json.load(open(target, encoding="utf-8"))

    uk = assemble_with({"incorporation_country": "GB"})
    assert uk["meta"]["home_law"] == "United Kingdom" and uk["meta"]["home_law_source"] == "profile"
    assert uk["agreements"][0]["law_class"] == "home"
    il = assemble_with({"incorporation_country": "IL"})
    assert il["meta"]["home_law"] == "Israel" and il["agreements"][0]["law_class"] == "foreign"
    # פרופיל ישן בלי מדינת התאגדות, ונתונים ישנים עם ברירת המחדל הישנה: הדין המקומי לא ידוע, לא "ישראל"
    old = dict(il, meta=dict(il["meta"], home_law="ישראל"))
    old["meta"].pop("home_law_source")
    none = assemble_with({"display_language": "en"}, old=old)
    assert none["meta"]["home_law"] is None and none["agreements"][0]["law_class"] == "unknown"
    assert [r["kind"] for r in none["review_queue"]].count("home_law_unknown") == 1
