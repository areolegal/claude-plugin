# -*- coding: utf-8 -*-
"""בדיקות ל-orchestrator/qa_gate.py.

(1) ההכרעות של 4.8 על הטיוטה של C1ב עוברות את השער בשני המצבים, והעותק למשלוח מופק.
(2) הנוסחים שהתגובה של סבב 2 הכניסה, כלשונם, נכשלים בכל אחת ממחלקות הפגמים שהסוקרים מצאו.
(3) לכל מחלקה יש גם בדיקה ממוקדת על טיוטה קטנה, ובהן הכלל של שדה ריק לשלב החתימה.
"""
import datetime as _dt
import io
import os
import zipfile

import pytest
from lxml import etree

import orch_helpers as H
from common import docx_tracked as dt
from common import ids
from orchestrator import qa_gate

ROUND2_EXPECTED = [
    'COV_UNCOVERED_CHANGE',            # בועות שמתארות פחות ממה שהשתנה (שיפוי, העברה לחו"ל, מחיקה)
    'BUB_WHY_MISSING',                 # 4.9, החלטת מוצר 2: רכיבים שמרעים את עמדת הצד שכנגד, בלי נימוק
    'CON_CONTRADICTION',               # "התשלום מוגן בתנאי התשלום" אחרי שהתגובה הסירה את ההשהיה ושללה עיכבון
    'ID_COMPANY_NUMBER',               # ח.פ. בן 8 ספרות
    'GAP_PAYMENT_WORDING',             # "המועד המאוחר ביותר שהדין מתיר"
    'GAP_CONFIDENTIALITY_EXCEPTIONS',  # בלי גילוי לפי דין, יועצים ומבקר, צד שלישי ופיתוח עצמאי
    'GAP_DISPUTE_CARVEOUT',            # חריג המחלוקת רק על "סכום"
    'SAFE_WORDING_SELF_CERTIFIED',     # not_worse_than_default: true בלי מקור
    'STRUCT_DUP_NUMBER',               # הקיזוז קיבל את "2." של ההשהיה שנמחקה
]
# 4.9 (החלטה 22): GAP_PAYMENT_APPROVAL_WINDOW, GAP_CAP_VAT, GAP_CAP_HOLLOW, GAP_AI_TOO_BROAD, GAP_PRIVACY_ANON_ONLY,
# GAP_TWO_DELETION_RULES ו-GAP_TERMINATION_PAYMENT_CONFLICT הוסרו: תוכן משפטי שתלוי בסוג ההסכם שייך לפלייבוק.


def _apply(tmp_path, dec, name='work.docx', now=None):
    out = str(tmp_path / name)
    res = dt.apply_decisions(H.DRAFT, dec, out_path=out, now=now)
    assert not res['errors'], res['errors']
    return out, res


def _codes(g):
    return {f['code'] for f in g['failures']}


# --------------------------------------------------------------------------------- (1) תקין
def test_round3_decisions_pass_work_and_send(tmp_path):
    out, res = _apply(tmp_path, H.load_decisions('c1b_decisions_round3_clean.json'))
    g = qa_gate.run_gate(out, H.DRAFT, 'work', H.PROFILE, {}, res['expected_accept'])
    assert g['passed'], g['failures']
    send = str(tmp_path / 'send.docx')
    s = qa_gate.build_send_copy(out, H.DRAFT, send, H.PROFILE, {}, res['expected_accept'])
    assert s['passed'], s['failures']
    assert s['send_copy'] == send and os.path.exists(send)
    assert not os.path.exists(send[:-5] + '.tmp.docx')
    # מצייני המקום של הצד שכנגד (תאריך, שם הספק) מדווחים ואינם חוסמים
    assert {x['text'] for x in s['info']['placeholders']['theirs']} >= {'[להשלים]', '[שם הספק]'}


# --------------------------------------------------------------------------------- (2) סבב 2
@pytest.fixture(scope='module')
def round2(tmp_path_factory):
    tmp = tmp_path_factory.mktemp('r2')
    out, res = _apply(tmp, H.load_decisions('c1b_decisions_round2_defects.json'))
    state = {'clauses': [{'clause_id': 'D09', 'safe_wording': {'law_applies': 'הסייג חל', 'law_not_applies': '60',
                                                               'not_worse_than_position': True,
                                                               'not_worse_than_default': True}}]}
    work = qa_gate.run_gate(out, H.DRAFT, 'work', H.PROFILE, state, res['expected_accept'])
    send_path = str(tmp / 'send.docx')
    send = qa_gate.build_send_copy(out, H.DRAFT, send_path, H.PROFILE, state, res['expected_accept'])
    return work, send, send_path


@pytest.mark.parametrize('code', ROUND2_EXPECTED)
def test_round2_defect_class_is_caught(round2, code):
    work, send, _ = round2
    assert code in _codes(work)
    assert code in _codes(send)


def test_round2_send_copy_not_produced(round2):
    work, send, send_path = round2
    assert not work['passed'] and not send['passed']
    assert 'PH_OURS' in _codes(send) and 'PH_OURS' not in _codes(work)
    assert send['send_copy'] is None and not os.path.exists(send_path)


def test_round2_uncovered_change_names_the_missing_terms(round2):
    work, _, _ = round2
    msgs = ' '.join(f['message'] for f in work['failures'] if f['code'] == 'COV_UNCOVERED_CHANGE')
    for term in ('שיפוי וערבות', 'מידע אישי ואבטחת מידע', 'מחיקה והחזרה'):  # שמות של תפקידי סעיף, כלליים
        assert term in msgs


# --------------------------------------------------------------------------------- (3) ממוקד
def _small(tmp_path, paragraphs, *decisions, state=None, mode='work', name='s.docx'):
    src = H.small_draft(str(tmp_path / ('src_' + name)), paragraphs)
    out = str(tmp_path / name)
    res = dt.apply_decisions(src, H.decisions(*decisions), out_path=out)
    assert not res['errors'] and not res['not_marked'], (res['errors'], res['not_marked'])
    if mode == 'send':
        send = str(tmp_path / ('send_' + name))
        return qa_gate.build_send_copy(out, src, send, H.PROFILE, state or {}, res['expected_accept'])
    return qa_gate.run_gate(out, src, mode, H.PROFILE, state or {}, res['expected_accept'])


BASE = ['הסכם שירותים', '1. הספק יספק את השירותים.', '2. כל צד רשאי לסיים בהתראה של 30 יום.']


def test_forbidden_terms_in_external_bubble(tmp_path):
    g = _small(tmp_path, BASE, {'id': 'A', 'op': 'replace_span', 'para': 1, 'old': 'יספק', 'new': 'יעניק',
                                'decision_code': 'R1',
                                'external_comment': 'לפי המדיניות שלנו ובהתאם לפלייבוק (R-04), זה קו אדום.'})
    msgs = [f['message'] for f in g['failures'] if f['code'] == 'BUB_FORBIDDEN']
    assert any('מדיניות' in m for m in msgs) and any('פלייבוק' in m for m in msgs)


def test_contradictory_bubbles_translation_vs_hebrew_prevails(tmp_path):
    g = _small(tmp_path, BASE + ['3. סעיף שתורגם.'],
               {'id': 'A', 'op': 'replace_span', 'para': 3, 'old': 'שתורגם', 'new': 'שתוקן', 'decision_code': 'R1',
                'external_comment': 'הנוסח שלכם מתייחס לצו שניתן לצד השני, וככל הנראה זו טעות בתרגום.'},
               {'id': 'B', 'op': 'insert_paragraph', 'after_para': 3, 'number': '4. ', 'decision_code': 'N1',
                'text': 'הנוסח העברי של הסכם זה, כפי שנחתם, הוא הנוסח המחייב, והוא גובר על כל נוסח אחר.',
                'external_comment': 'קבענו איזה נוסח מחייב.'})
    assert 'CON_CONTRADICTION' in _codes(g)


def test_uncovered_substantive_change(tmp_path):
    g = _small(tmp_path, BASE, {'id': 'A', 'op': 'replace_span', 'para': 1, 'old': 'את השירותים.',
                                'new': 'את השירותים, והתמורה כוללת את כל הוצאותיו.', 'decision_code': 'R1',
                                'external_comment': 'הבהרנו את היקף השירותים.'})
    assert 'COV_UNCOVERED_CHANGE' in _codes(g)
    ok = _small(tmp_path, BASE, {'id': 'A', 'op': 'replace_span', 'para': 1, 'old': 'את השירותים.',
                                 'new': 'את השירותים, והתמורה כוללת את כל הוצאותיו.', 'decision_code': 'R1',
                                 'external_comment': 'התמורה כוללת גם את ההוצאות, כדי שהעלות תהיה ידועה מראש.'},
                name='ok.docx')
    assert 'COV_UNCOVERED_CHANGE' not in _codes(ok)


def test_termination_without_handover(tmp_path):
    g = _small(tmp_path, BASE, {'id': 'A', 'op': 'insert_paragraph', 'after_para': 2, 'number': '3. ',
                                'decision_code': 'N1',
                                'text': 'הלקוח רשאי לסיים את ההסכם בהודעה בכתב בתוקף מיידי.',
                                'external_comment': 'הוספנו זכות סיום מיידית.'})
    assert 'GAP_TERMINATION_HANDOVER' in _codes(g)


def test_dispute_carveout_must_cover_amount_timing_and_setoff(tmp_path):
    term = ('כל צד רשאי לסיים את ההסכם בשל הפרה שלא תוקנה בתוך 14 ימים. אי-תשלום של סכום שהלקוח חולק עליו בתום לב '
            'אינו הפרה לעניין סעיף זה. בכל סיום יבצע הספק העברה מסודרת של העבודה.')
    setoff = {'id': 'S', 'op': 'insert_paragraph', 'after_para': 1, 'number': '1א. ', 'decision_code': 'N1',
              'text': 'הלקוח רשאי לקזז סכום קצוב לפי הסכם זה.', 'external_comment': 'קבענו זכות קיזוז.'}
    g = _small(tmp_path, BASE, setoff, {'id': 'A', 'op': 'insert_paragraph', 'after_para': 2, 'number': '3. ',
                                        'decision_code': 'N1', 'text': term,
                                        'external_comment': 'הוספנו זכות סיום בהפרה עם חריג למחלוקת.'})
    msg = [f['message'] for f in g['failures'] if f['code'] == 'GAP_DISPUTE_CARVEOUT']
    assert msg and 'מועד' in msg[0] and 'קיזוז' in msg[0]
    fixed = term.replace('אי-תשלום של סכום שהלקוח חולק עליו בתום לב',
                         'אי-תשלום, תשלום חלקי או קיזוז של סכום שהלקוח חולק בתום לב על חיובו בו, על שיעורו או על מועד פירעונו,')
    g2 = _small(tmp_path, BASE, setoff, {'id': 'A', 'op': 'insert_paragraph', 'after_para': 2, 'number': '3. ',
                                         'decision_code': 'N1', 'text': fixed,
                                         'external_comment': 'הוספנו זכות סיום בהפרה עם חריג למחלוקת על סכום, מועד וקיזוז.'},
                name='ok.docx')
    assert 'GAP_DISPUTE_CARVEOUT' not in _codes(g2)


def test_confidentiality_needs_law_regulator_and_advisers_exceptions(tmp_path):
    g = _small(tmp_path, BASE, {'id': 'A', 'op': 'insert_paragraph', 'after_para': 2, 'number': '3. ',
                                'decision_code': 'N1', 'text': 'כל צד ישמור בסוד את המידע של הצד האחר.',
                                'external_comment': 'הוספנו חובת סודיות הדדית.'})
    msg = ' '.join(f['message'] for f in g['failures'] if f['code'] == 'GAP_CONFIDENTIALITY_EXCEPTIONS')
    assert 'גילוי לפי דין' in msg and 'המבקר הפנימי' in msg and 'פיתוח עצמאי' in msg


def test_payment_wording_needs_number_and_no_statutory_maximum(tmp_path):
    g = _small(tmp_path, BASE, {'id': 'A', 'op': 'insert_paragraph', 'after_para': 2, 'number': '3. ',
                                'decision_code': 'N1',
                                'text': 'התשלום ישולם בתוך המועד המאוחר ביותר שהדין מתיר מתום החודש.',
                                'external_comment': 'קבענו את מועד התשלום.'})
    assert 'GAP_PAYMENT_WORDING' in _codes(g)


# --------------------------------------------------------------------------------- מצייני מקום ושלב החתימה
PARTIES = ['הסכם שירותים', 'בין הספק לבין [שם הלקוח], ח.פ. [להשלים].', '1. הספק יספק את השירותים.']


def _parties(tmp_path, new, state, mode, name):
    return _small(tmp_path, PARTIES, {'id': 'P', 'op': 'replace_span', 'para': 1,
                                      'old': '[שם הלקוח], ח.פ. [להשלים]', 'new': new, 'decision_code': 'A2',
                                      'external_comment': 'השלמנו את פרטי הלקוח.'}, state=state, mode=mode, name=name)


SIGNING_STATE = {'entity_details': {'company_number': {'status': 'signing_blank', 'answer': 'נשלים לפני החתימה'}}}


def test_signing_blank_after_client_answer_does_not_block_send(tmp_path):
    assert ids.is_complete_at_signing('נשלים לפני החתימה')
    text, status = ids.detail_for_draft('company_number', answer='נשלים לפני החתימה')
    assert status == 'signing_blank' and text == ids.SIGNING_BLANK
    res = _parties(tmp_path, 'EXAMPLECO בע"מ, ח.פ. ' + ids.SIGNING_BLANK, SIGNING_STATE, 'send', 'blank.docx')
    assert res['passed'], res['failures']
    assert res['send_copy'] and os.path.exists(res['send_copy'])
    assert [x['item'] for x in res['info']['signing_checklist']].count('signing_blank') == 1


def test_signing_blank_without_client_answer_blocks_send(tmp_path):
    res = _parties(tmp_path, 'EXAMPLECO בע"מ, ח.פ. ' + ids.SIGNING_BLANK, {}, 'send', 'noanswer.docx')
    assert 'PH_OURS' in _codes(res) and res['send_copy'] is None


def test_any_other_placeholder_of_ours_still_blocks(tmp_path):
    res = _parties(tmp_path, 'EXAMPLECO בע"מ, ח.פ. ' + ids.SIGNING_BLANK + ', שכתובתה [כתובת]', SIGNING_STATE,
                   'send', 'other.docx')
    assert 'PH_OURS' in _codes(res)
    assert [x['text'] for x in res['info']['placeholders']['ours']] == ['[כתובת]']


def test_invalid_detail_never_inserted_as_valid(tmp_path):
    text, status = ids.detail_for_draft('company_number', value='11111111', validator=ids.validate_company_number)
    assert text is None and status == 'open'
    g = _parties(tmp_path, 'EXAMPLECO בע"מ, ח.פ. 11111111', {}, 'work', 'invalid.docx')
    assert 'ID_COMPANY_NUMBER' in _codes(g)  # כבר במצב עבודה
    g2 = _parties(tmp_path, 'EXAMPLECO בע"מ, ח.פ. 510000011', {}, 'work', 'other_valid.docx')
    assert ids.validate_company_number('510000011')['valid']
    assert 'ID_COMPANY_NUMBER' in _codes(g2)  # תקין, אבל שונה מהפרופיל


def test_their_placeholders_reported_not_blocking(tmp_path):
    res = _parties(tmp_path, 'EXAMPLECO בע"מ, ח.פ. 511111114', {}, 'send', 'theirs.docx')
    assert res['passed'], res['failures']


# --------------------------------------------------------------------------------- מצב וחבילה
def test_legal_review_open_blocks_send_only(tmp_path):
    state = {'clauses': [{'clause_id': 'R-22', 'legal_review_required': True, 'legal_review': {}}]}
    d = {'id': 'A', 'op': 'replace_span', 'para': 1, 'old': 'יספק', 'new': 'יעניק', 'decision_code': 'R1',
         'external_comment': 'תיקון מינוח.'}
    w = _small(tmp_path, BASE, d, state=state, mode='work', name='lr.docx')
    assert 'LEGAL_REVIEW_OPEN' not in _codes(w) and any(x['code'] == 'LEGAL_REVIEW_OPEN' for x in w['warnings'])
    s = _small(tmp_path, BASE, d, state=state, mode='send', name='lr2.docx')
    assert 'LEGAL_REVIEW_OPEN' in _codes(s)


def test_old_fixed_date_is_caught(tmp_path):
    src = H.small_draft(str(tmp_path / 'd.docx'), BASE)
    out = str(tmp_path / 'old.docx')
    res = dt.apply_decisions(src, H.decisions({'id': 'A', 'op': 'replace_span', 'para': 1, 'old': 'יספק', 'new': 'יעניק',
                                               'decision_code': 'R1', 'external_comment': 'תיקון.'}),
                             out_path=out, now=_dt.datetime(2026, 8, 13, 10, 0).astimezone())
    g = qa_gate.run_gate(out, src, 'work', H.PROFILE, {}, res['expected_accept'])
    assert 'PKG_DATE_RANGE' in _codes(g)


def test_namespace_cleanup_that_broke_word_is_caught(tmp_path):
    out, res = _apply(tmp_path, H.load_decisions('c1b_decisions_round3_clean.json'))
    parts = dt.read_package(out)
    root = etree.fromstring(parts['word/document.xml'])
    etree.cleanup_namespaces(root)  # מה שההדמיה של C2 עשתה, ו-Word דחה את הקובץ כפגום
    parts['word/document.xml'] = etree.tostring(root, xml_declaration=True, encoding='UTF-8', standalone=True)
    bad = str(tmp_path / 'ns_bad.docx')
    open(bad, 'wb').write(dt.write_package(parts))
    g = qa_gate.run_gate(bad, H.DRAFT, 'work', H.PROFILE, {}, res['expected_accept'])
    assert 'PKG_NAMESPACE_UNDECLARED' in _codes(g)


def test_track_changes_setting_is_caught(tmp_path):
    out, res = _apply(tmp_path, H.load_decisions('c1b_decisions_round3_clean.json'))
    parts = dt.read_package(out)
    parts['word/settings.xml'] = parts['word/settings.xml'].replace(b'<w:trackRevisions/>', b'<w:trackChanges/>')
    bad = str(tmp_path / 'tc_bad.docx')
    open(bad, 'wb').write(dt.write_package(parts))
    codes = _codes(qa_gate.run_gate(bad, H.DRAFT, 'work', H.PROFILE, {}, res['expected_accept']))
    assert {'PKG_TRACK_REVISIONS', 'PKG_TRACK_CHANGES_INVALID'} <= codes


def test_empty_inserted_paragraph_is_caught(tmp_path):
    src = H.small_draft(str(tmp_path / 'e.docx'), BASE)
    doc = dt.TrackedDocx(src, H.AUTHOR, H.INITIALS)
    p = doc.insert_paragraph(1, 'זמני')
    for ins in [e for e in p if dt.local(e.tag) == 'ins']:
        p.remove(ins)  # מדמה פסקה ריקה שנוספה בסימון הוספה, כמו P49 ב-C1ב
    out = doc.save(str(tmp_path / 'empty.docx'))
    g = qa_gate.run_gate(out, src, 'work', H.PROFILE, {})
    assert 'STRUCT_EMPTY_PARAGRAPH' in _codes(g)


def test_internal_layer_in_send_copy_is_caught(tmp_path):
    out, res = _apply(tmp_path, H.load_decisions('c1b_decisions_round3_clean.json'))
    g = qa_gate.run_gate(out, H.DRAFT, 'send', H.PROFILE, {}, res['expected_accept'])  # קובץ העבודה, בלי strip
    assert 'INT_IN_SEND' in _codes(g)
