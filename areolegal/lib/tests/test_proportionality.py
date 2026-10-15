# -*- coding: utf-8 -*-
"""בדיקות ל-orchestrator/proportionality.py: N1 נספר, התרעה בעסקה קטנה מחייבת שאלה עם שלושה ויתורים,
מיקוד בסבב 1 מול טופס סטנדרטי של צד דומיננטי בלי מכתב צד, וויתורים מכוונים שעוברים למעריך הסיכונים."""
import orch_helpers  # noqa: F401
from orchestrator import proportionality as pr


def _c1b_like():
    rej = [{'id': 'D%02d' % i, 'decision_code': 'R1', 'importance': 'high'} for i in range(10)]
    add = [{'id': 'N%02d' % i, 'decision_code': 'N1', 'mandatory': i < 14, 'importance': 'medium' if i >= 14 else 'high'}
           for i in range(16)]
    return rej + add


def test_additions_are_counted():
    c = pr.count_asks(_c1b_like())
    assert c == {'rejections': 10, 'additions': 16, 'mandatory_additions': 14, 'asks': 26}
    line = pr.summary_line(c, '180,000 ש"ח')
    assert '10 דרישות על הנוסח שלהם' in line and '16 נושאים שהוספנו' in line and '26 בקשות' in line


def test_alert_counts_n1_and_requires_question_with_three_concessions():
    # בלי N1 היו 10 דחיות מול רשימת מאבק של 12, ואין התרעה. עם N1 יש 26 בקשות.
    res = pr.assess(_c1b_like(), fight_list_size=12, value_band='קטנה')
    assert res['alert'] and res['question_required']
    assert len(res['proposed_concessions']) == 3
    assert all(not d.startswith('N0') for d in res['proposed_concessions'][:0])
    mandatory = {'N%02d' % i for i in range(14)}
    assert not mandatory & set(res['proposed_concessions'])  # נושא חובה אינו מוצע כוויתור


def test_full_response_needs_explicit_answer():
    res = pr.assess(_c1b_like(), 12, user_choice='full_response', answer_kind='delegated')
    assert 'full_response_without_explicit_answer' in res['violations']
    ok = pr.assess(_c1b_like(), 12, user_choice='full_response', answer_kind='explicit')
    assert ok['violations'] == []


def test_small_deal_alert_without_question_is_a_violation():
    res = pr.assess(_c1b_like(), 12, value_band='קטנה', user_choice='unanswered')
    assert 'small_deal_alert_without_question' in res['violations']


GOOGLE = [
    {'id': 'P7', 'topic': 'מידע על לקוחות ופרטיות', 'kind': 'client_data', 'importance': 'critical'},
    {'id': 'R18', 'topic': 'סודיות קיום המגעים', 'kind': 'other', 'importance': 'critical', 'client_priority': True},
    {'id': 'R03', 'topic': 'המטרה', 'kind': 'other', 'importance': 'high', 'client_priority': True},
    {'id': 'R04', 'topic': 'חברות קשורות כצד', 'kind': 'red_line', 'importance': 'critical', 'playbook_red': True},
    {'id': 'R15', 'topic': 'דין ושיפוט', 'kind': 'governing_law', 'importance': 'high', 'playbook_red': False},
    {'id': 'R17', 'topic': 'נוסח עברי גובר', 'kind': 'language', 'importance': 'medium'},
    {'id': 'R10', 'topic': 'הנדסה חוזרת', 'kind': 'other', 'importance': 'medium'},
    {'id': 'N12', 'topic': 'הודעות', 'kind': 'other', 'importance': 'low'},
]


def test_dominant_standard_form_focus():
    res = pr.focus_round1(GOOGLE, client_confirmed_law=False)
    asked = {a['id'] for a in res['asks']}
    assert asked == {'P7', 'R18', 'R03', 'R04'}
    assert {'R15', 'R17', 'R10', 'N12'} == {a['id'] for a in res['accepted_as_is']}
    assert res['decision_row'].startswith('מקבלים כמות שהוא את:') and 'דין ושיפוט' in res['decision_row']
    assert res['violations'] == []


def test_law_forum_language_only_when_red_and_confirmed():
    items = [dict(GOOGLE[4], playbook_red=True)]
    assert pr.focus_round1(items, client_confirmed_law=False)['asks'] == []
    assert [a['id'] for a in pr.focus_round1(items, client_confirmed_law=True)['asks']] == ['R15']


def test_round2_google_response_violations():
    """סבב 2: ויתרנו על סודיות המגעים ועל המטרה, וביקשנו דין ישראלי, נוסח עברי גובר והודעות."""
    asks = [GOOGLE[0], GOOGLE[4], GOOGLE[5], GOOGLE[6], GOOGLE[7]]
    accepted = [GOOGLE[1], GOOGLE[2]]
    v = pr.check_round1_focus(asks, accepted, client_confirmed_law=False)
    assert 'priority_waived_while_low_value_asked' in v
    assert 'law_forum_language_without_red_and_confirmation' in v
    assert 'side_letter_route' in pr.check_round1_focus([], [], route='side_letter')


def test_waivers_go_to_risk_assessor_as_accepted_risk_without_approval_fields():
    """4.9, שינוי 83: אין שדה אישור ואין מאשר. הכרעת המשתמש נרשמת כמו שהיא."""
    state = {'deliberate_concessions': [
        {'topic': 'סודיות המגעים', 'clause_ref': 'E-012', 'reason': 'תגובה ממוקדת',
         'user_decision': {'answer_kind': 'explicit', 'answer': 'לוותר', 'recorded_at': '2026-10-14T14:17:38+03:00'}},
        {'topic': 'המטרה', 'clause_ref': 'E-002', 'reason': 'תגובה ממוקדת', 'answer_kind': 'delegated'},
        {'topic': 'בלי נימוק', 'user_decision': {'answer_kind': 'explicit'}}]}
    out = pr.waiver_handoff(state)
    assert [w['topic'] for w in out] == ['סודיות המגעים', 'המטרה']
    assert all(w['report_as'] == 'accepted_risk' for w in out)
    assert [w['user_decision']['answer_kind'] for w in out] == ['explicit', 'delegated']
    flat = repr(out)
    for banned in ('approval', 'required_by', 'approver', 'מנכ'):
        assert banned not in flat


# --------------------------------------------------------------------------------- 4.9
def test_structural_headings_are_not_counted():
    """C1 בסבב 3 (פער 1): שתי כותרות פרק נספרו כבקשות."""
    dec = [{'id': 'D1', 'decision_code': 'R1'}, {'id': 'N1', 'decision_code': 'N1', 'mandatory': True},
           {'id': 'H01', 'decision_code': 'N1', 'structural': True}, {'id': 'H02', 'decision_code': 'N1', 'structural': True}]
    assert pr.count_asks(dec) == {'rejections': 1, 'additions': 1, 'mandatory_additions': 1, 'asks': 2}
    assert 'H01' not in pr.assess(dec, fight_list_size=1)['proposed_concessions']


def test_playbook_cure_wording_enters_asks_when_red_item_is_accepted():
    """מנגנון כללי: כשמקבלים נוסח שהפלייבוק מסמן אדום, ולכלל יש בפלייבוק נוסח ריפוי, הריפוי נכנס לבקשות. התוכן של
    הריפוי בא מהפלייבוק; כאן מחרוזות לדוגמה."""
    items = [{'id': 'X-1', 'topic': 'נושא א', 'kind': 'governing_law', 'importance': 'high', 'playbook_red': True,
              'cure_wording': '<נוסח ריפוי א מהפלייבוק>'},
             {'id': 'X-2', 'topic': 'נושא ב', 'kind': 'other', 'importance': 'high', 'playbook_red': True,
              'cure_wording': '<נוסח ריפוי ב מהפלייבוק>'},
             {'id': 'X-3', 'topic': 'נושא ג', 'kind': 'other', 'importance': 'medium',
              'chosen_option_wording': '<הנוסח של החלופה שנבחרה בגיליון>'}]
    res = pr.focus_round1(items)
    asked = {a['id'] for a in res['asks']}
    assert {'X-1-cure', 'X-2-cure', 'X-3'} <= asked
    assert {'X-1', 'X-2'} <= {a['id'] for a in res['accepted_as_is']}
    assert res['violations'] == []
    # מה שקרה בסבב 3: האדום התקבל בלי הריפוי, והבחירה בגיליון נרשמה כוויתור
    v = pr.check_round1_focus([], [items[0], items[1]], concessions=[items[2]])
    assert {'red_line_waived_although_cure_exists', 'sheet_choice_with_wording_treated_as_waiver'} <= set(v)


def test_delegated_answer_never_crosses_red_line_without_cure():
    item = {'id': 'R-02', 'topic': 'הגדרת המידע', 'kind': 'other', 'importance': 'high', 'playbook_red': True}
    res = pr.focus_round1([item])
    assert [a['id'] for a in res['asks']] == ['R-02']
    v = pr.check_round1_focus([], [], concessions=[dict(item, user_decision={'answer_kind': 'delegated'})])
    assert 'red_line_crossed_without_user_decision' in v
    ok = pr.check_round1_focus([], [], concessions=[dict(item, user_decision={'answer_kind': 'explicit'})])
    assert ok == []


def test_concessions_prefer_high_friction_and_respect_never_concede():
    """בין פריטים שווים בחשיבות, קודם מה שהצד שכנגד צפוי להיאבק עליו; never_concede (מהפלייבוק) אינו מוצע."""
    dec = [{'id': 'A', 'decision_code': 'R1', 'importance': 'low', 'expected_friction': 'low'},
           {'id': 'B', 'decision_code': 'R1', 'importance': 'low', 'expected_friction': 'high'},
           {'id': 'H', 'decision_code': 'N1', 'importance': 'low', 'never_concede': True},
           {'id': 'C', 'decision_code': 'R1', 'importance': 'medium'}]
    assert pr.assess(dec, 1)['proposed_concessions'] == ['B', 'A', 'C']


def test_round1_opening_keeps_last_fallback():
    assert pr.round1_opening(False, True, intermediate='נקודת ביניים מהפלייבוק')['open_at'] == 'intermediate'
    assert pr.round1_opening(False, True)['question_required'] is True
    assert pr.round1_opening(True, True)['open_at'] == 'green'
