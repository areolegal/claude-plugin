# -*- coding: utf-8 -*-
"""בדיקות התוכן של הסבב (`content_checks.py`), הערות הנושא ונותן 4.0 עד 4.7: לכל
בדיקה, מקרה שהיא תופסת ומקרה שהיא אינה תופסת. ההסכמים נבנים כאן, קטנים, כדי
שהבדיקה תהיה על הכלל ולא על סוג הסכם מסוים (החלטה 22).
"""
import sys
from pathlib import Path

import pytest

PLUGIN = Path(__file__).resolve().parents[1]
LIB = PLUGIN / "areolegal" / "lib"
S = PLUGIN / "areolegal" / "skills" / "contract-negotiation-orchestrator" / "scripts"
sys.path.insert(0, str(LIB))
sys.path.insert(0, str(S))
docx = pytest.importorskip("docx")

import common.docx_tracked as dt  # noqa: E402
import content_checks as C  # noqa: E402

BASE = ["1. הגדרות. \"המידע\" (להלן: \"המידע הסודי\") פירושו כל מידע.",
        "2. השירותים. הספק יספק את השירותים לפי נספח א.",
        "3. התמורה. הלקוח ישלם את התמורה בתוך 30 יום.",
        "4. כללי. אין באמור כדי לגרוע."]


def make(tmp_path, paras=BASE, name="received.docx", hidden=None, comment=None):
    d = docx.Document()
    for i, t in enumerate(paras):
        p = d.add_paragraph(t)
        if hidden is not None and i == hidden[0]:
            r = p.add_run(" " + hidden[1])
            r.font.hidden = True
        if comment is not None and i == comment[0]:
            d.add_comment(p.runs[0], text=comment[1], author=comment[2])
    out = tmp_path / name
    d.save(str(out))
    return str(out)


def run(tmp_path, decisions, paras=BASE, state=None, core=None, manifest=None, **kw):
    rec = make(tmp_path, paras, **kw)
    work = str(tmp_path / "work.docx")
    dec = {"transaction_id": "deal_x_2026-10-16", "round": 1, "received_sha256": "", "author": "עו\"ד בדיקה",
           "decisions": decisions}
    res = dt.apply_decisions(rec, dec, out_path=work, author="עו\"ד בדיקה")
    assert not res["errors"], res["errors"]
    return C.run_checks(work, rec, decisions, state=state, core=core, manifest=manifest)


def codes(found, blocking=None):
    return {f["code"] for f in found if blocking is None or f["blocking"] == blocking}


def ins(text, after=3, did="N1"):
    return {"id": did, "op": "insert_paragraph", "after_para": after, "decision_code": "N1", "text": text,
            "external_comment": "הוספנו סעיף.", "plain_effect": "x", "position_effect": "y"}


def test_a_clean_round_has_nothing_blocking(tmp_path):
    assert not codes(run(tmp_path, [ins("5. הודעות. הודעות יימסרו בכתב.")]), blocking=True)


def test_to_be_agreed_in_our_wording_blocks(tmp_path):
    assert "CON_TBA" in codes(run(tmp_path, [ins("5. מועד ההתחלה יוסכם בין הצדדים.")]), True)


def test_a_reference_in_our_wording_to_a_missing_section_blocks(tmp_path):
    found = run(tmp_path, [ins("5. בכפוף לסעיף 9.4 להלן.")])
    assert "CON_REF_MISSING" in codes(found, True)
    assert "CON_REF_MISSING" not in codes(run(tmp_path, [ins("5. בכפוף לסעיף 3 לעיל.")]), True)


def test_an_annex_that_prevails_over_the_agreement_blocks(tmp_path):
    paras = BASE + ["5. במקרה של סתירה, הוראות הנספח יגברו."]
    assert "PREC_ANNEX_PREVAILS" in codes(run(tmp_path, [], paras=paras), True)


def test_a_representation_needs_an_approved_record_or_brackets(tmp_path):
    rep = ins("5. החברה מצהירה כי היא עומדת בכל דין.", did="R5")
    assert "REP_UNAPPROVED" in codes(run(tmp_path, [rep]), True)
    st = {"company_representations": [{"clause_id": "R5", "status": "confirmed"}]}
    assert "REP_UNAPPROVED" not in codes(run(tmp_path, [rep], state=st))
    br = ins("5. [החברה מצהירה כי היא עומדת בכל דין.]", did="R6")
    assert "REP_UNAPPROVED" not in codes(run(tmp_path, [br]))


def test_no_conflicting_agreement_needs_a_conflict_check(tmp_path):
    d = ins("5. החברה מצהירה בזאת כי אין הסכם סותר.")
    found = run(tmp_path, [d], state={"company_representations": [{"clause_id": "N1", "status": "confirmed"}]})
    assert "CONFLICT_CHECK" in codes(found, True)
    st = {"meta": {"deal_context": {"existing_agreements_with_counterparty": []}},
          "company_representations": [{"clause_id": "N1", "status": "confirmed"}]}
    assert "CONFLICT_CHECK" not in codes(run(tmp_path, [d], state=st))


def test_a_compliance_clause_needs_an_explicit_user_decision(tmp_path):
    paras = BASE + ["5. הספק יעמוד בכל דין בעניין סנקציות ופיקוח על יצוא."]
    assert "COMPLIANCE" in codes(run(tmp_path, [], paras=paras), True)
    dec = [{"id": "C5", "op": "comment_only", "para": 4, "decision_code": "A3", "external_comment": "ראינו.",
            "user_decision": {"answer_kind": "explicit", "answer": "מאשרים"}}]
    assert "COMPLIANCE" not in codes(run(tmp_path, dec, paras=paras))


def test_a_playbook_party_label_that_is_not_in_the_agreement_blocks(tmp_path):
    assert "PARTY_LABEL" in codes(run(tmp_path, [ins("5. נותן השירותים יבטח את עצמו.")]), True)
    assert "PARTY_LABEL" not in codes(run(tmp_path, [ins("5. הספק יבטח את עצמו.")]))


def test_a_red_marker_of_an_applicable_rule_needs_a_decision(tmp_path):
    paras = BASE + ["5. הספק רשאי לקזז כל סכום ללא הודעה."]
    core = {"clauses": [{"id": "R-09", "red": {"red_flags": ["לקזז כל סכום"]}}]}
    assert "RED_MARKER" in codes(run(tmp_path, [], paras=paras, core=core), True)
    dec = [{"id": "D5", "op": "replace_span", "para": 4, "old": "ללא הודעה", "new": "בהודעה של 30 יום",
            "decision_code": "A3", "external_comment": "הוספנו הודעה.", "rule_ids": ["R-09"],
            "plain_effect": "x", "position_effect": "y"}]
    assert "RED_MARKER" not in codes(run(tmp_path, dec, paras=paras, core=core))


def test_hidden_text_in_their_draft_without_a_decision_blocks(tmp_path):
    found = run(tmp_path, [], hidden=(2, "הלקוח מוותר על כל טענה"))
    assert "HIDDEN_TEXT" in codes(found, True)
    hs = C.hidden_scan(str(tmp_path / "received.docx"))
    assert hs and hs[0]["how"] == "vanish" and "מוותר" in hs[0]["text"]


def test_an_internal_comment_of_theirs_must_be_recorded(tmp_path):
    found = run(tmp_path, [], comment=(2, "בינינו, אפשר לוותר על זה אם ילחצו", "Their Lawyer"))
    assert "THEIR_INTERNAL_COMMENT" in codes(found, True)
    st = {"meta": {"exposed_comments": [{"quote": "בינינו, אפשר לוותר על זה אם ילחצו"}]}}
    found = run(tmp_path, [], state=st, comment=(2, "בינינו, אפשר לוותר על זה אם ילחצו", "Their Lawyer"))
    assert "THEIR_INTERNAL_COMMENT" not in codes(found)
    assert "THEIR_COMMENT_UNANSWERED" in codes(found)


def test_a_name_from_another_signed_agreement_in_a_bubble_blocks(tmp_path):
    d = dict(ins("5. הודעות יימסרו בכתב."), external_comment="כך סיכמנו גם עם חברת דוגמה אחרת בע\"מ.")
    man = {"documents": [{"counterparty": "חברת דוגמה אחרת בע\"מ"}]}
    assert "OTHER_PARTY_NAME" in codes(run(tmp_path, [d], manifest=man), True)


def test_a_bilingual_agreement_must_be_declared_and_changed_on_both_sides(tmp_path):
    he = ["%d. סעיף בעברית עם תוכן מספיק ארוך כדי שייספר כפסקה." % i for i in range(1, 7)]
    en = ["%d. An English clause with long enough content to be counted." % i for i in range(1, 7)]
    assert "BILINGUAL_UNDECLARED" in codes(run(tmp_path, [], paras=he + en), True)
    st = {"meta": {"bilingual": {"is_bilingual": True, "map": {"0": 6}}}}
    one = [{"id": "B1", "op": "replace_span", "para": 0, "old": "בעברית", "new": "בשפה העברית", "decision_code": "A3",
            "external_comment": "דיוק.", "plain_effect": "x", "position_effect": "y"}]
    assert "BILINGUAL_ONE_SIDE" in codes(run(tmp_path, one, paras=he + en, state=st), True)


def test_a_playbook_of_the_opposite_side_blocks(tmp_path):
    st = {"playbook_resolution": {"playbook_match": "side_mismatch"}}
    assert "POSITION_MISMATCH" in codes(run(tmp_path, [], state=st), True)


def test_a_neutralizer_left_in_their_wording_is_reported_not_blocking(tmp_path):
    paras = BASE + ["5. הקביעה של הספק תהיה סופית ומכריעים לכל דבר."]
    found = run(tmp_path, [], paras=paras)
    assert "NEUTRALIZER" in codes(found, False) and "NEUTRALIZER" not in codes(found, True)


# ------------------------------------------------------------------ apply_redlines ו-qa_gate
import json  # noqa: E402
import subprocess  # noqa: E402
import zipfile  # noqa: E402


def _cli(script, *args):
    return subprocess.run([sys.executable, "-B", str(S / script)] + [str(x) for x in args],
                          capture_output=True, text=True, cwd=str(S))


def _dec(tmp_path, decisions):
    p = tmp_path / "dec.json"
    p.write_text(json.dumps({"transaction_id": "deal_x_2026-10-16", "round": 1, "received_sha256": "",
                             "author": "עו\"ד בדיקה", "decisions": decisions}, ensure_ascii=False), encoding="utf-8")
    return p


def test_our_answer_is_a_threaded_reply_to_their_comment(tmp_path):
    rec = make(tmp_path, comment=(2, "למה 30 יום?", "Their Lawyer"))
    cid = C.comment_info(rec)[0]["id"]
    dec = _dec(tmp_path, [{"id": "T1", "op": "comment_only", "para": 2, "decision_code": "A1",
                           "external_comment": "30 יום הם המועד שלנו לאישור חשבונית.", "reply_to_comment": cid}])
    out = tmp_path / "w.docx"
    r = _cli("apply_redlines.py", "--draft", rec, "--decisions", dec, "--out", out, "--author", "עו\"ד בדיקה")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "נענתה בשרשור" in r.stdout
    info = {c["id"]: c for c in C.comment_info(str(out))}
    assert info[cid]["has_reply"]
    assert any(c["parent"] == info[cid]["paraId"] for c in info.values())
    with zipfile.ZipFile(out) as z:
        assert "word/commentsExtended.xml" in z.namelist()
        assert "commentsExtended" in z.read("[Content_Types].xml").decode()
    docx.Document(str(out))   # הקובץ נפתח


def test_a_surviving_sentence_of_theirs_is_recorded_for_approval(tmp_path):
    rec = make(tmp_path)
    keep = "הלקוח ישלם את התמורה בתוך 30 יום."
    dec = _dec(tmp_path, [{"id": "S1", "op": "replace", "para": 2, "decision_code": "A3",
                           "new_text": "3. התמורה. " + keep + " החשבונית תוגש בסוף כל חודש.",
                           "external_comment": "הוספנו מועד להגשת חשבונית."}])
    out = tmp_path / "w.docx"
    r = _cli("apply_redlines.py", "--draft", rec, "--decisions", dec, "--out", out, "--author", "עו\"ד בדיקה")
    assert r.returncode in (0, 3), r.stdout + r.stderr
    assert "ששרדו בהחלפה S1" in r.stdout and keep in r.stdout


def test_a_tender_before_bidding_is_never_marked_up(tmp_path):
    rec = make(tmp_path)
    deal = tmp_path / "deal_x_2026-10-16"
    deal.mkdir()
    (deal / "negotiation_state.json").write_text(json.dumps({"meta": {"paper_type": "tender_pre_bid"}}),
                                                 encoding="utf-8")
    dec = _dec(tmp_path, [ins("5. הודעות.")])
    r = _cli("apply_redlines.py", "--draft", rec, "--decisions", dec, "--deal", deal, "--agreement-type", "מכרז",
             "--round", 1, "--author", "עו\"ד בדיקה")
    assert r.returncode == 2 and "tender_outputs.py" in r.stdout
    assert not list(deal.glob("*.docx"))


def test_a_blocking_content_finding_stops_the_send_copy(tmp_path):
    rec = make(tmp_path)
    dec = _dec(tmp_path, [ins("5. מועד ההתחלה יוסכם בין הצדדים.")])
    work = tmp_path / "w.docx"
    assert _cli("apply_redlines.py", "--draft", rec, "--decisions", dec, "--out", work,
                "--author", "עו\"ד בדיקה").returncode == 0
    prof = tmp_path / "p.json"
    prof.write_text(json.dumps({"lawyer_name": "עו\"ד בדיקה"}, ensure_ascii=False), encoding="utf-8")
    send = tmp_path / "send.docx"
    r = _cli("qa_gate.py", "--mode", "send", "--work", work, "--received", rec, "--profile", prof,
             "--decisions", dec, "--send", send)
    assert r.returncode == 3 and "CON_TBA" in r.stdout
    assert not send.exists()


def _tender_deal(tmp_path, paper, questions):
    deal = tmp_path / "deal_t_2026-10-16"
    deal.mkdir()
    (deal / "negotiation_state.json").write_text(json.dumps({"meta": {"paper_type": paper},
                                                             "clarification_questions": questions},
                                                            ensure_ascii=False), encoding="utf-8")
    memo = tmp_path / "memo.json"
    memo.write_text(json.dumps({"questions_deadline": "01.11.2026", "submission_deadline": "15.11.2026",
                                "items": [{"topic": "אחריות", "contract_ref": "סעיף 12", "what": "אחריות ללא תקרה",
                                           "nature": "commercial", "price_impact": "גבוהה", "risk_impact": "גבוה",
                                           "recommendation": "go_if_answered"}]}, ensure_ascii=False),
                    encoding="utf-8")
    return deal, memo


def test_a_tender_gets_a_questions_table_and_an_internal_memo(tmp_path):
    qs = [{"number": 2, "document": "החוזה", "contract_ref": "סעיף 12", "question": "נבקש להבהיר כי תקרת האחריות היא "
           "גובה התמורה.", "priority": "HIGH", "internal_reason": "סוד של החברה"},
          {"number": 1, "document": "החוזה", "contract_ref": "סעיף 3", "question": "נבקש להבהיר את מועד ההתחלה.",
           "priority": "LOW"}]
    deal, memo = _tender_deal(tmp_path, "tender_pre_bid", qs)
    r = _cli("tender_outputs.py", "--deal", deal, "--memo", memo, "--agreement-type", "מכרז שירותים",
             "--company", "החברה")
    assert r.returncode == 0, r.stdout + r.stderr
    files = sorted(p.name for p in deal.glob("*.docx"))
    assert any("שאלות הבהרה" in f for f in files) and any("תזכיר פנימי" in f for f in files)
    qdoc = docx.Document(str(next(deal.glob("*שאלות הבהרה*.docx"))))
    cells = [c.text for row in qdoc.tables[0].rows for c in row.cells]
    assert "סוד של החברה" not in " ".join(cells)
    assert cells.index("נבקש להבהיר כי תקרת האחריות היא גובה התמורה.") < cells.index("נבקש להבהיר את מועד ההתחלה.")


def test_a_question_worded_as_a_position_is_refused(tmp_path):
    deal, memo = _tender_deal(tmp_path, "tender_pre_bid",
                              [{"number": 1, "question": "סעיף 12 לא מוסכם על החברה.", "priority": "HIGH"}])
    r = _cli("tender_outputs.py", "--deal", deal, "--memo", memo, "--agreement-type", "מכרז")
    assert r.returncode == 3 and not list(deal.glob("*.docx"))


def test_online_terms_get_only_the_memo(tmp_path):
    deal, memo = _tender_deal(tmp_path, "standard_form_online", [])
    r = _cli("tender_outputs.py", "--deal", deal, "--memo", memo, "--agreement-type", "תנאי שימוש")
    assert r.returncode == 0, r.stdout + r.stderr
    assert [p.name for p in deal.glob("*.docx")] and not list(deal.glob("*שאלות הבהרה*"))


# ------------------------------------------------------------------ deal_tools
def _doc(path, paras):
    d = docx.Document()
    for t in paras:
        d.add_paragraph(t)
    d.save(str(path))
    return path


def test_documents_of_one_deal_are_compared(tmp_path):
    a = _doc(tmp_path / "master.docx", ["\"השירותים\" פירושו שירותי תוכנה.", "תקרת האחריות תהיה 100,000 ש\"ח.",
                                         "הדין החל הוא דיני מדינת ישראל, וסמכות השיפוט בתל אביב."])
    b = _doc(tmp_path / "order.docx", ["\"השירותים\" פירושו שירותי תמיכה בלבד.", "תקרת האחריות תהיה 250,000 ש\"ח.",
                                        "הדין החל הוא דיני מדינת ישראל, וסמכות השיפוט בתל אביב."])
    r = _cli("deal_tools.py", "compare-docs", a, b)
    assert r.returncode == 0, r.stdout + r.stderr
    topics = {c["topic"] for c in json.loads(r.stdout)["conflicts"]}
    assert {"definitions", "liability_cap"} <= topics and "governing_law" not in topics


def test_existing_agreements_with_the_counterparty_and_their_parties(tmp_path):
    root = tmp_path / "הסכמים"
    root.mkdir()
    _doc(root / "nda.docx", ["הסכם סודיות", "בין: חברת אלפא בע\"מ, ח.פ. 51-111111-1", "לבין: חברת בטא בע\"מ, ח.פ. 51-222222-2",
                              "תקופת ההסכם שלוש שנים, והוא יתחדש מאליו.", "ולראיה באו הצדדים על החתום"])
    _doc(root / "draft.docx", ["טיוטה עם חברת בטא בע\"מ, לא חתומה"])
    r = _cli("deal_tools.py", "existing", "--root", root, "--counterparty", "חברת בטא")
    found = json.loads(r.stdout)["found"]
    assert [f["file"] for f in found] == ["nda.docx"]
    assert found[0]["clauses"]["term_renewal"]
    r = _cli("deal_tools.py", "parties", "--root", root, "--out", tmp_path / "parties.json")
    names = json.loads(r.stdout)
    assert any("חברת אלפא" in n for n in names) and any("חברת בטא" in n for n in names)


def test_the_terms_map_reads_parenthetical_definitions(tmp_path):
    p = _doc(tmp_path / "a.docx", ["בין חברת גמא (\"הספק\" או \"נותן השירותים\") לבין חברת דלתא (\"הלקוח\")."])
    out = json.loads(_cli("deal_tools.py", "terms", p).stdout)
    assert {"הספק", "נותן השירותים", "הלקוח"} <= set(out["defined_terms"])
    assert out["party_labels"]["הלקוח"] == 1


def test_facts_already_given_are_collected_with_their_source(tmp_path):
    data = tmp_path / "Areo-נתונים"
    (data / "transactions" / "deal_b_2026-10-01").mkdir(parents=True)
    (data / "transactions" / "deal_b_2026-10-01" / "negotiation_state.json").write_text(json.dumps(
        {"meta": {"transaction_id": "deal_b_2026-10-01", "counterparty_name": "חברת בטא"},
         "client_answers": [{"question": "מה שווי העסקה?", "answer": "כמיליון ש\"ח"}]}, ensure_ascii=False),
        encoding="utf-8")
    out = json.loads(_cli("deal_tools.py", "facts", "--data", data, "--counterparty", "חברת בטא").stdout)
    assert out["facts"] and "deal_b_2026-10-01" in out["facts"][0]["source"]


# ------------------------------------------------------------------ read_playbook_doc
def test_a_client_playbook_in_word_is_read_from_headings_and_tables(tmp_path):
    d = docx.Document()
    d.add_heading("1. הגבלת אחריות", level=2)
    d.add_paragraph("ירוק: תקרה בגובה התמורה השנתית.")
    d.add_paragraph("צהוב: תקרה כפולה מהתמורה.")
    d.add_paragraph("אדום: אחריות בלתי מוגבלת.")
    d.add_paragraph("סימני אדום: ללא הגבלה; כל נזק")
    d.add_heading("הוראות הפעלה", level=2)
    d.add_paragraph("כל חריגה מהאדום מחייבת אישור היועץ המשפטי.")
    t = d.add_table(rows=2, cols=4)
    for i, h in enumerate(("נושא", "ירוק", "צהוב", "אדום")):
        t.rows[0].cells[i].text = h
    for i, v in enumerate(("סודיות", "חמש שנים", "שלוש שנים", "פחות משנה")):
        t.rows[1].cells[i].text = v
    src = tmp_path / "client" / "פלייבוק.docx"
    src.parent.mkdir()
    d.save(str(src))
    r = _cli("read_playbook_doc.py", src)
    assert r.returncode == 0, r.stdout + r.stderr
    out = json.loads(r.stdout[:r.stdout.rindex("}") + 1])
    topics = {x["topic"]: x for x in out["topics"]}
    assert topics["הגבלת אחריות"]["red"].startswith("אחריות בלתי מוגבלת")
    assert topics["הגבלת אחריות"]["red_flags"] == ["ללא הגבלה", "כל נזק"]
    assert topics["סודיות"]["yellow"] == "שלוש שנים"
    assert out["operating_rules"] == ["כל חריגה מהאדום מחייבת אישור היועץ המשפטי."]
    assert _cli("read_playbook_doc.py", src, "--out", src.parent / "x.json").returncode == 1


def test_a_document_without_tracks_is_not_a_playbook(tmp_path):
    p = _doc(tmp_path / "policy.docx", ["מדיניות כללית של החברה בנושא התקשרויות.", "יש לפעול בזהירות."])
    assert _cli("read_playbook_doc.py", p).returncode == 3


def test_their_hidden_text_is_deleted_with_tracking_and_the_rest_stays(tmp_path):
    rec = make(tmp_path, hidden=(2, "הלקוח מוותר על כל טענה"))
    dec = [{"id": "H1", "op": "replace_span", "para": 2, "old": " הלקוח מוותר על כל טענה", "new": "",
            "decision_code": "R2", "external_comment": "מחקנו טקסט שלא הופיע בגלוי.",
            "plain_effect": "x", "position_effect": "y"}]
    found = run(tmp_path, dec, hidden=(2, "הלקוח מוותר על כל טענה"))
    assert "HIDDEN_TEXT" not in codes(found, True)
    work = str(tmp_path / "work.docx")
    assert dt.accept_all(work)[2] == "3. התמורה. הלקוח ישלם את התמורה בתוך 30 יום."
    assert dt.reject_all(work)[2] == dt.received_paragraphs(rec)[2]



def test_a_paragraph_rewritten_with_most_words_kept_is_not_surgical(tmp_path):
    """הכרעת ניל, 18.10.2026: עקוב אחר שינויים כירורגי, לא פסקה במקום פסקה."""
    orig = BASE[2]   # "3. התמורה. הלקוח ישלם את התמורה בתוך 30 יום."
    rewrite = [{"id": "W1", "op": "replace", "para": 2, "decision_code": "A3",
                "new_text": "3. התמורה. הלקוח ישלם את התמורה בתוך 45 יום, ובניכוי כל סכום שמגיע לו.",
                "external_comment": "45 יום.", "plain_effect": "x", "position_effect": "y"}]
    found = run(tmp_path, rewrite)
    assert "REPLACE_COLLAPSED" not in codes(found, True)   # הבדל של מילים: הסימון כירורגי מאליו
    pair = [{"id": "D1", "op": "delete_paragraph", "para": 2, "decision_code": "R1", "external_comment": "מחקנו."},
            {"id": "I1", "op": "insert_paragraph", "after_para": 2, "decision_code": "N1",
             "text": "3. התמורה. הלקוח ישלם את התמורה בתוך 45 יום.", "external_comment": "הוספנו.",
             "plain_effect": "x", "position_effect": "y"}]
    assert "PARAGRAPH_REPLACED" in codes(run(tmp_path, pair), True)
