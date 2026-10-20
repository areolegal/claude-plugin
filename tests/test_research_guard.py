# -*- coding: utf-8 -*-
"""שני הפערים של מחקר השוק שנסגרו (20.10.2026), בלי רשת.

1. **סוג המקור בקוד.** ארבעת סוגי המקורות של `market-research.md` היו רק בהוראות,
   ו-`fetch` קרא כל כתובת. עכשיו כל קריאה במחקר שוק מצהירה על הסוג, והאתר נבדק מולו.
2. **השאילתה נבדקת לפני החיפוש.** החיפוש נעשה בכלי של Claude, והבדיקה רצה רק בקריאה,
   אחרי שהשאילתה כבר יצאה. עכשיו: `start` פותח מושב, ה-hook של התוסף בודק כל WebSearch
   לפניו, `query` הוא הבדיקה הידנית, ו-`fetch` מסרב לשאילתה שלא נבדקה.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

PLUGIN = Path(__file__).resolve().parents[1]
LIB = PLUGIN / "areolegal" / "lib"
S = PLUGIN / "areolegal" / "skills" / "contract-playbook-builder" / "scripts"
HOOK = PLUGIN / "areolegal" / "hooks" / "research_guard.py"
sys.path.insert(0, str(LIB))
sys.path.insert(0, str(S))

import market_research as MR  # noqa: E402

CORPUS = {"documents": [{"paragraphs": [{"text": "הספק לא יישא באחריות לנזק עקיף בסך 250,000 ש\"ח"}]}]}
PROFILE = {"organization_name": "חברת בדיקה"}


@pytest.fixture
def research(tmp_path, monkeypatch):
    """מושב מחקר בתיקייה זמנית, עם חילוץ ופרופיל."""
    tmp = tmp_path / "tmp"
    tmp.mkdir()
    monkeypatch.setattr(MR.tempfile, "gettempdir", lambda: str(tmp))
    corpus, profile = tmp_path / "corpus.json", tmp_path / "profile.json"
    corpus.write_text(json.dumps(CORPUS, ensure_ascii=False), encoding="utf-8")
    profile.write_text(json.dumps(PROFILE, ensure_ascii=False), encoding="utf-8")
    fam = tmp_path / "playbooks" / "fam_saas"
    assert MR.main(["start", "--family-dir", str(fam), "--corpus", str(corpus), "--profile", str(profile)]) == 0
    return {"tmp": tmp, "fam": fam, "corpus": corpus, "profile": profile}


def _hook(event, tmp):
    env = dict(os.environ, TMPDIR=str(tmp), TEMP=str(tmp), TMP=str(tmp))
    return subprocess.run([sys.executable, "-B", str(HOOK)], input=json.dumps(event, ensure_ascii=False),
                          capture_output=True, text=True, env=env)


# ---------------------------------------------------------------- סוג המקור
@pytest.mark.parametrize("url,stype,vendor,ok", [
    ("https://www.sec.gov/Archives/edgar/data/1/x.htm", "public_filing", None, True),
    ("https://maya.tase.co.il/reports/details/1", "public_filing", None, True),
    ("https://www.example-blog.com/nda", "public_filing", None, False),
    ("https://www.gov.il/he/departments/x", "tender", None, True),
    ("https://commonpaper.com/standards/mutual-nda/1.0/", "model_agreement", None, True),
    ("https://some-template-site.com/nda", "model_agreement", None, False),
    ("https://www.lawinsider.com/clause/x", "public_filing", None, False),
    ("https://en.wikipedia.org/wiki/NDA", "vendor_terms", "Wiki", False),
    ("https://www.salesforce.com/company/legal/", "vendor_terms", "Salesforce", True),
    ("https://www.salesforce.com/company/legal/", "vendor_terms", None, False),
    ("https://www.sec.gov/x", None, None, False),
])
def test_each_source_type_has_its_own_sites(url, stype, vendor, ok):
    problem, allowed = MR.source_type_problem(url, stype, vendor)
    assert (problem is None) is ok, problem
    if ok:
        assert allowed


def test_vendor_terms_stay_on_the_vendor_site_after_redirects():
    _, allowed = MR.source_type_problem("https://www.salesforce.com/company/legal/", "vendor_terms", "Salesforce")
    assert allowed == ("salesforce.com",)


def test_a_market_fetch_without_a_source_type_is_refused():
    with pytest.raises(SystemExit):
        MR.main(["fetch", "--family-dir", "x", "--source-id", "W1", "--url", "https://www.sec.gov/x",
                 "--query", "q", "--purpose", "market"])


def test_vendor_terms_counted_as_balanced_fail_the_check():
    m = {"market_research": {"source_refs": [{"source_id": "W1", "source_type": 3, "drafted_by": "neutral_model"}]}}
    assert any("VENDOR_TERMS_AS_BALANCED" in e for e in MR.check_model(m))


# ---------------------------------------------------------------- השאילתה לפני החיפוש
def test_query_logs_a_good_query_and_refuses_a_client_detail(research):
    assert MR.main(["query", "--query", "SaaS agreement limitation of liability", "--purpose", "market"]) == 0
    assert MR.main(["query", "--query", "הסכם שירותים חברת בדיקה", "--purpose", "market"]) == 3
    log = MR.read_query_log(str(research["fam"]))
    assert [e["precheck"] for e in log] == ["passed", "failed"]
    assert MR.query_passed(str(research["fam"]), "SaaS agreement  limitation of liability")


def test_fetch_refuses_a_query_that_was_not_checked_before_the_search(research, monkeypatch, capsys):
    from common import net
    sent = []
    monkeypatch.setattr(net, "fetch", lambda *a, **k: sent.append(a) or {})
    rc = MR.main(["fetch", "--family-dir", str(research["fam"]), "--source-id", "W1",
                  "--url", "https://www.sec.gov/x", "--query", "never checked", "--purpose", "market",
                  "--source-type", "public_filing"])
    assert rc == 3 and not sent
    assert json.loads(capsys.readouterr().out)["precheck"] == "not_prechecked"


def test_fetch_refuses_a_site_outside_the_source_type(research, monkeypatch, capsys):
    from common import net
    sent = []
    monkeypatch.setattr(net, "fetch", lambda *a, **k: sent.append(a) or {})
    MR.main(["query", "--query", "mutual NDA exhibit", "--purpose", "market"])
    capsys.readouterr()
    rc = MR.main(["fetch", "--family-dir", str(research["fam"]), "--source-id", "W1",
                  "--url", "https://www.lawinsider.com/x", "--query", "mutual NDA exhibit", "--purpose", "market",
                  "--source-type", "public_filing"])
    assert rc == 3 and not sent
    assert json.loads(capsys.readouterr().out)["precheck"] == "source_type"


def test_fetch_passes_the_allowed_sites_to_the_network_layer(research, monkeypatch, capsys):
    from common import net
    seen = {}

    def fake(url, purpose, **kw):
        seen.update(kw)
        return {"status": 200, "blocked": False, "stored": True, "log": {"url": url}}
    monkeypatch.setattr(net, "fetch", fake)
    MR.main(["query", "--query", "mutual NDA exhibit", "--purpose", "market"])
    capsys.readouterr()
    rc = MR.main(["fetch", "--family-dir", str(research["fam"]), "--source-id", "W1",
                  "--url", "https://www.sec.gov/x", "--query", "mutual NDA exhibit", "--purpose", "market",
                  "--source-type", "public_filing"])
    assert rc == 0 and seen["allowed_domains"] == MR.SOURCE_DOMAINS["public_filing"]
    assert json.loads(capsys.readouterr().out)["source_type"] == 2


# ---------------------------------------------------------------- ה-hook
def test_the_hook_does_nothing_without_a_research_session(tmp_path):
    r = _hook({"tool_name": "WebSearch", "tool_input": {"query": "הסכם שירותים חברת בדיקה"}}, tmp_path)
    assert r.returncode == 0
    r = _hook({"tool_name": "WebFetch", "tool_input": {"url": "https://example.com"}}, tmp_path)
    assert r.returncode == 0


def test_the_hook_stops_a_search_with_a_client_detail_before_it_is_sent(research):
    r = _hook({"tool_name": "WebSearch", "tool_input": {"query": "הסכם שירותים חברת בדיקה"}}, research["tmp"])
    assert r.returncode == 2 and "נעצרה" in r.stderr
    r = _hook({"tool_name": "WebSearch", "tool_input": {"query": "limitation of liability 250,000"}}, research["tmp"])
    assert r.returncode == 2


def test_the_hook_lets_a_general_search_through_and_fetch_accepts_it(research):
    q = "SaaS agreement exhibit 10 limitation of liability"
    r = _hook({"tool_name": "WebSearch", "tool_input": {"query": q}}, research["tmp"])
    assert r.returncode == 0, r.stderr
    assert MR.query_passed(str(research["fam"]), q)


def test_the_hook_sends_page_reads_to_the_research_script(research):
    r = _hook({"tool_name": "WebFetch", "tool_input": {"url": "https://www.sec.gov/x"}}, research["tmp"])
    assert r.returncode == 2 and "market_research.py fetch" in r.stderr


def test_stop_closes_the_session(research):
    assert MR.main(["stop"]) == 0
    r = _hook({"tool_name": "WebFetch", "tool_input": {"url": "https://www.sec.gov/x"}}, research["tmp"])
    assert r.returncode == 0


def test_an_expired_session_is_no_session(research):
    s = json.loads(Path(MR.session_path()).read_text(encoding="utf-8"))
    s["expires_at"] = "2020-01-01T00:00:00+00:00"
    Path(MR.session_path()).write_text(json.dumps(s), encoding="utf-8")
    assert MR.load_session() is None


def test_the_plugin_registers_the_hook():
    cfg = json.loads((PLUGIN / "areolegal" / "hooks" / "hooks.json").read_text(encoding="utf-8"))
    entry = cfg["hooks"]["PreToolUse"][0]
    assert "WebSearch" in entry["matcher"] and "WebFetch" in entry["matcher"]
    assert "research_guard.py" in entry["hooks"][0]["command"]


# ---------------------------------------------------------------- מה שהבדיקה החיה מצאה (20.10.2026)
EDGAR = "https://www.sec.gov/Archives/edgar/data/1783032/000114036125023228/ny20050730x1_exd2.htm"


def test_an_edgar_address_is_not_a_client_detail():
    """בכתובת של EDGAR יש תמיד CIK ומספר הגשה. בדיקת השאילתה עצרה בגללם כל מסמך EDGAR."""
    assert MR.url_problem(EDGAR, CORPUS, PROFILE) is None
    assert MR.url_problem("https://x.gov.il/חברת בדיקה/doc.pdf", CORPUS, PROFILE)
    assert MR.url_problem("https://x.gov.il/files/511111114.pdf", CORPUS, PROFILE)


def test_a_hebrew_address_is_encoded_before_it_is_sent():
    """כתובת של מינהל הרכש עם עברית ורווח הפילה את הסקריפט (UnicodeEncodeError, InvalidURL)."""
    from common import net
    u = net.to_uri("https://mr.gov.il/ilgstorefront/he/p/attachment/0050/חוברת המכרז")
    assert u.isascii() and " " not in u and u.endswith("%D7%97%D7%95%D7%91%D7%A8%D7%AA%20%D7%94%D7%9E%D7%9B%D7%A8%D7%96")
    kept = "https://www.gov.il/x/%D7%9E%D7%A1.pdf"
    assert net.to_uri(kept) == kept
    assert net.to_uri("https://www.sec.gov/cgi-bin/browse?action=getcompany&CIK=1") == \
        "https://www.sec.gov/cgi-bin/browse?action=getcompany&CIK=1"


def test_a_large_document_gets_a_reading_copy_and_the_excerpt_is_saved_without_a_second_request(
        research, monkeypatch, capsys):
    """PDF של מכרז מעל 200 קילובייט נקרא ולא נשמר, והטקסט לא הגיע אל הבונה: אי אפשר היה לבחור קטע."""
    from common import net
    url = "https://www.gov.il/BlobFolder/x/he/מכרז.htm"
    body = ("<html><body>" + "מבוא " * 60000 +
            "<p>התחייבות זו תמשיך לחול אף לאחר תום תקופת ההסכם</p></body></html>").encode("utf-8")
    calls = []

    def fake(u, purpose, **kw):
        calls.append(u)
        clean = net.strip_secrets(net.to_uri(u))[0]
        return {"status": 200, "blocked": False, "content": body, "stored": None, "url": clean,
                "final_url": clean, "reason": "ok, not stored: דף גדול בלי קטע מילולי",
                "lawyer_task": None, "log": {"url": clean}}
    monkeypatch.setattr(net, "fetch", fake)
    q = "התחייבות לשמירת סודיות נספח מכרז"
    MR.main(["query", "--query", q, "--purpose", "market"])
    capsys.readouterr()
    args = ["fetch", "--family-dir", str(research["fam"]), "--source-id", "W7", "--url", url, "--query", q,
            "--purpose", "market", "--source-type", "tender"]
    assert MR.main(args) == 0
    first = json.loads(capsys.readouterr().out)
    assert "תום תקופת ההסכם" in Path(first["reading_copy"]).read_text(encoding="utf-8")
    assert MR.main(args + ["--excerpt", "התחייבות זו תמשיך לחול אף לאחר תום תקופת ההסכם"]) == 0
    second = json.loads(capsys.readouterr().out)
    assert second["stored"]["stored"] == "excerpt_window" and len(calls) == 1
    MR.main(["stop"])
    assert not Path(first["reading_copy"]).exists()


def _no_point_model(read=7, counted=7):
    refs = [{"source_id": "W%d" % i, "issuing_body": "b%d" % i, "template_family": "f%d" % i, "source_type": 2,
             "drafted_by": "negotiated", "doc_date": "2024-01-01", "read_status": "read",
             "url": "https://www.sec.gov/%d" % i, "document": "Mutual NDA"} for i in range(1, read + 1)]
    coding = [{"source_id": "W%d" % i, "topic": "משך", "level": (i % 5) - 2, "status": "agreed"}
              for i in range(1, counted + 1)]
    return {"rules": [], "corpus_origin": "market_built", "status_label": "x",
            "market_research": {"source_refs": refs, "coding": coding, "research_date": "2026-10-20"}}


def test_the_message_counts_bodies_even_when_no_point_has_three_sources():
    m = _no_point_model(7, 4)
    MR.compute_ranges(m)
    assert m["market_research"]["counts"]["bodies"] == 4
    text = MR.build_message(m)[1]
    assert "מ-0 גופים" not in text and "נוהל עליו משא ומתן" in text and "negotiated" not in text
    from playbook import market_counts as MC
    assert MC.count_claims(text, m) == []      # 7 שנקראו, 4 שנספרו: ההודעה אינה סותרת את עצמה


def test_link_check_keeps_an_edgar_exhibit_whose_title_is_the_file_name(tmp_path, monkeypatch):
    from common import net
    page = "<html><head><title>ny20050730x1_exd2.htm</title></head><body>MUTUAL NON-DISCLOSURE AGREEMENT</body></html>"
    m = _no_point_model(2, 2)
    for r in m["market_research"]["source_refs"]:
        r["document"] = "Mutual Non-Disclosure Agreement"
    m["market_research"]["source_refs"][0]["file_sha256"] = "abc"
    p = tmp_path / "m.json"
    p.write_text(json.dumps(m), encoding="utf-8")
    monkeypatch.setattr(net, "fetch", lambda url, purpose, **kw: {
        "status": 200, "blocked": False, "text": page, "sha256": "abc" if url.endswith("/1") else "zzz"})
    args = type("A", (), {"model": str(p), "family_dir": str(tmp_path / "fam")})
    assert MR.cmd_links(args) == 0


def test_parallel_queries_do_not_lose_log_entries(tmp_path):
    """בהרצה החיה Claude הריץ שאילתות במקביל, והיומן שנכתב מחדש בכל פעם איבד שורות."""
    fam = tmp_path / "fam"
    code = ("import sys; sys.path[:0]=[%r,%r]; import market_research as MR; "
            "MR.log_query(%r, {'query': 'q%%s' %% sys.argv[1], 'precheck': 'passed', 'via': 'query'})"
            % (str(LIB), str(S), str(fam)))
    procs = [subprocess.Popen([sys.executable, "-B", "-c", code, str(i)]) for i in range(24)]
    for p in procs:
        assert p.wait() == 0
    log = MR.read_query_log(str(fam))
    assert sorted(e["query"] for e in log) == sorted("q%d" % i for i in range(24))


# ---------------------------------------------------------------- שומר השפה (Stop)
LANG = PLUGIN / "areolegal" / "hooks" / "language_guard.py"


def _transcript(tmp_path, user, last, areo=True):
    p = tmp_path / "t.jsonl"
    rows = [{"type": "user", "message": {"role": "user", "content": user}},
            {"type": "assistant", "message": {"content": [{"type": "tool_use", "name": "Skill",
                                                            "input": {"skill": "areolegal:x" if areo else "y"}}]}},
            {"type": "assistant", "message": {"content": [{"type": "text", "text": last}]}}]
    p.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows), encoding="utf-8")
    return p


def _stop(path, active=False):
    r = subprocess.run([sys.executable, "-B", str(LANG)], capture_output=True, text=True,
                       input=json.dumps({"transcript_path": str(path), "stop_hook_active": active}))
    return r.stdout.strip()


ENGLISH = ("I produced the response draft, then the risk assessment ruled out sending it. Five gaps it found "
           "in our own response block sending, so there is currently no valid sendable copy.")


def test_an_english_final_message_in_a_hebrew_areo_conversation_is_sent_back(tmp_path):
    out = _stop(_transcript(tmp_path, "תכין לנו את הטיוטה החוזרת לפי הפלייבוק", ENGLISH))
    assert json.loads(out)["decision"] == "block"


def test_hebrew_answers_english_users_other_plugins_and_second_pass_are_left_alone(tmp_path):
    assert _stop(_transcript(tmp_path, "תכין לנו את הטיוטה", "הטיוטה מוכנה, עם שבעה שינויים.")) == ""
    assert _stop(_transcript(tmp_path, "Prepare the reply draft", ENGLISH)) == ""
    assert _stop(_transcript(tmp_path, "תכין לנו את הטיוטה", ENGLISH, areo=False)) == ""
    assert _stop(_transcript(tmp_path, "תכין לנו את הטיוטה", ENGLISH), active=True) == ""


def test_the_plugin_registers_the_language_guard():
    cfg = json.loads((PLUGIN / "areolegal" / "hooks" / "hooks.json").read_text(encoding="utf-8"))
    assert "language_guard.py" in cfg["hooks"]["Stop"][0]["hooks"][0]["command"]
