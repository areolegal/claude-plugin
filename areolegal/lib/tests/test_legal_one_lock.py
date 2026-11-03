# -*- coding: utf-8 -*-
"""נעילה אחת לבדיקה משפטית: עורך דין שאישר תא טעון בדיקה ("נבדק ולאשר") סוגר גם את שאלת התור על אותה בדיקה."""
from playbook import after_ingest as AI
from playbook import status as S


def _cell(done_by='יוסי כהן', status='approved'):
    return {'status': status, 'policy_claim': True, 'simulated': False, 'legal_review_required': True,
            'legal_review_done_by': done_by, 'legal_review_done_at': '2026-11-02' if done_by else None,
            'approved_at': '2026-11-02', 'signer': 'יוסי כהן'}


def _model():
    return {'validation_queue': [
        {'id': 'Q1', 'rule_id': 'R1', 'severity': 'גבוהה', 'status': 'open', 'answered': False,
         'question': 'טעון בדיקה משפטית: האם הדין מגביל את מועד התשלום?'},
        {'id': 'Q2', 'rule_id': 'R2', 'rule_ids': ['R2', 'R3'], 'severity': 'גבוהה', 'status': 'open',
         'answered': False, 'question': 'טעון בדיקה משפטית: מה נדרש בהעברת מידע?'},
        {'id': 'Q3', 'rule_id': 'R1', 'severity': 'גבוהה', 'status': 'open', 'answered': False,
         'question': 'להוסיף זכות סיום מטעמי נוחות?'},
    ]}


def test_reviewed_cell_closes_its_legal_question_only():
    m = _model()
    cells = {S.cell_key('R1', 'green'): _cell()}
    closed = AI.close_legal_questions(m, cells, {'received_at': '2026-11-02'}, 'APR-9')
    q = {x['id']: x for x in m['validation_queue']}
    assert closed == ['Q1']
    assert q['Q1']['status'] == 'closed' and q['Q1']['answered'] and q['Q1']['answered_by'] == 'יוסי כהן'
    assert q['Q1']['answered_via'] == 'APR-9' and q['Q1']['closed_by'] == 'legal_review'
    assert q['Q3']['status'] == 'open', 'שאלה שאינה בדיקה משפטית אינה נסגרת כך'


def test_question_on_two_rules_waits_for_both():
    m = _model()
    cells = {S.cell_key('R2', 'green'): _cell(), S.cell_key('R3', 'green'): _cell(done_by=None, status='pending_legal_review')}
    assert 'Q2' not in AI.close_legal_questions(m, cells, {}, 'APR-9')
    cells[S.cell_key('R3', 'green')] = _cell()
    assert 'Q2' in AI.close_legal_questions(m, cells, {}, 'APR-10')


def test_approval_without_reviewer_does_not_close():
    m = _model()
    cells = {S.cell_key('R1', 'green'): _cell(done_by=None)}
    assert AI.close_legal_questions(m, cells, {}, 'APR-9') == []
    assert m['validation_queue'][0]['status'] == 'open'


def test_closed_question_stops_blocking_the_topic():
    m = _model()
    m['validation_queue'] = m['validation_queue'][:1]
    m['rules'] = [{'rule_id': 'R1', 'traffic_light': {'green': {'position': 'x'}}}]
    cells = {S.cell_key('R1', 'green'): _cell()}
    before = S.derive_status(m, cells)
    AI.close_legal_questions(m, cells, {}, 'APR-9')
    after = S.derive_status(m, cells)
    assert S.cell_key('R1', 'green') not in before['approved_keys']
    assert S.cell_key('R1', 'green') in after['approved_keys']
