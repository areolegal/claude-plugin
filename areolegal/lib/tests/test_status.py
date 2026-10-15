# -*- coding: utf-8 -*-
"""בדיקות ל-playbook/status.py: מעמד אחד ותווית אחת (status_label בלבד), נגזרים, וזהים בכל השכבות והמשטחים."""
import copy

import pb_helpers as H
from playbook import status as S


def _cells(model, n=None, **extra):
    keys = list(S.iter_cell_keys(model))
    n = len(keys) if n is None else n
    out = {}
    for k in keys[:n]:
        c = {'status': 'approved', 'policy_claim': True, 'approved_at': '2026-10-14'}
        c.update(extra)
        out[k] = c
    return out


def _close_all(model):
    for q in model.get('validation_queue') or []:
        q.update(status='closed', answered=True)
    return model


def test_zero_agreements_label_is_market_only():
    m = H.load('mutual_nda_round2_excerpt.json')
    assert m['corpus_basis']['agreement_units'] == 0
    st = S.derive_status(m)
    assert st['label'] == 'פלייבוק מוצע, מבוסס מחקר שוק, טעון אישור'
    assert st['playbook_status'] == 'Draft'
    assert 'מבוסס הסכמים' not in st['label']


def test_agreements_label_only_when_agreements_counted():
    m = H.good_model()
    m['corpus_origin'] = 'own_plus_market'
    m['corpus_basis']['agreement_units'] = 3
    assert S.base_label(m) == S.LABEL_MARKET
    m['rules'][0]['traffic_light']['green']['basis'] = 'company_agreement'
    assert S.base_label(m) == 'פלייבוק מוצע, מבוסס הסכמים ומחקר שוק, טעון אישור'
    m['corpus_basis']['agreement_units'] = 0
    assert S.base_label(m) == S.LABEL_MARKET


def test_full_approval_label_with_date_and_signer():
    m = _close_all(H.good_model())
    st = S.derive_status(m, _cells(m))
    assert st['playbook_status'] == 'Approved'
    assert st['label'] == 'מדיניות מאושרת, 14.10.2026'
    st = S.derive_status(m, _cells(m, signer='דנה לוי', role='יועצת משפטית ראשית'))
    assert st['label'] == 'מדיניות מאושרת, 14.10.2026, בידי דנה לוי, יועצת משפטית ראשית'


def test_open_decisive_question_blocks_its_rule():
    """סבב 3: Q-01 ו-Q-02 (חומרה גבוהה) נשארו פתוחות, והפלייבוק סומן "מאושר"."""
    m = H.good_model()
    st = S.derive_status(m, _cells(m))
    assert st['playbook_status'] == 'PartiallyApproved'
    assert all(not k.startswith('R-22|') for k in st['approved_keys'])
    assert st['open_questions'] == ['Q-02']
    g = S.policy_claim(m, _cells(m), 'R-22', 'green')
    assert not g['policy_claim'] and g['reason'] == 'open_decisive_question'


def test_partial_approval_label():
    m = _close_all(H.good_model())
    total = len(list(S.iter_cell_keys(m)))
    st = S.derive_status(m, _cells(m, n=total - 3))
    assert st['playbook_status'] == 'PartiallyApproved'
    assert st['label'].endswith('%d מתוך %d עמדות מאושרות' % (total - 3, total))
    assert st['label'].startswith(S.LABEL_MARKET)


def test_simulated_unreviewed_or_defective_cells_do_not_count():
    m = _close_all(H.good_model())
    assert S.derive_status(m, _cells(m, simulated=True))['playbook_status'] == 'Draft'
    cells = _cells(m)
    cells['R-22|-|green'].update(legal_review_required=True, legal_review_done_by=None)
    st = S.derive_status(m, cells)
    assert st['playbook_status'] == 'PartiallyApproved'
    assert not S.policy_claim(m, cells, 'R-22', 'green')['policy_claim']
    cells['R-22|-|green']['legal_review_done_by'] = 'עו"ד פלונית אלמונית'
    assert S.policy_claim(m, cells, 'R-22', 'green')['policy_claim']
    cells['R-22|-|green']['legal_review_done_at'] = None
    assert not S.policy_claim(m, cells, 'R-22', 'green')['policy_claim']
    cells['R-22|-|green'].update(legal_review_done_at='14.10.2026', needs_amendment=True)
    assert not S.policy_claim(m, cells, 'R-22', 'green')['policy_claim']


def test_one_label_field_everywhere():
    """סבב 3: presentation_label "טעון אישור" ו-status_label "מדיניות מאושרת" באותה רשומה."""
    m = _close_all(H.good_model())
    m['handoff']['presentation_label'] = S.LABEL_MARKET
    core = {'presentation_label': S.LABEL_MARKET, 'playbook_status': 'Draft',
            'clauses': [{'id': r['rule_id'], 'policy_status': 'Inferred'} for r in m['rules']]}
    index_entry = {'presentation_label': S.LABEL_MARKET, 'playbook_status': 'Draft'}
    cells = _cells(m)
    before = S.check_consistency(m, core, index_entry, cells)
    assert any('presentation_label' in p and 'כפול' in p for p in before)
    assert any('ingest_result' in p for p in before)
    st = S.stamp(m, core, index_entry, cells, record_id='APR-0002')
    assert S.check_consistency(m, core, index_entry, cells) == []
    for holder in (m, core, index_entry, m['handoff']):
        assert 'presentation_label' not in holder
        assert holder['status_label'] == st['label'] == 'מדיניות מאושרת, 14.10.2026'
        assert holder['playbook_status'] == 'Approved'
    g = m['rules'][0]['traffic_light']['green']['ingest_result']
    assert g['status'] == 'approved' and g['record_id'] == 'APR-0002' and g['counts_as_approved']
    assert all(r['policy_status'] == 'Confirmed' for r in m['rules'])
    assert all(c['policy_status'] == 'Confirmed' for c in core['clauses'])
    surf = S.surfaces(st)
    gate = S.policy_claim(m, cells, 'R-07', 'green')
    assert len({surf['word_header'], surf['workspace']['label_now'], surf['chat_first_line'], surf['model'],
                gate['status_label']}) == 1


def test_stale_cell_layer_is_detected():
    """סבב 3: 63 תאים נשארו {approved, policy_claim: false, simulated: true} מהרשומה הקודמת."""
    m = _close_all(H.good_model())
    sim = _cells(m, simulated=True, policy_claim=False)
    S.stamp(m, None, None, sim, record_id='APR-0001')
    real = _cells(m)
    m['playbook_status'], m['status_label'] = 'Approved', 'מדיניות מאושרת, 14.10.2026'
    problems = S.check_consistency(m, None, None, real)
    assert any('ingest_result' in p for p in problems)
    S.stamp(m, None, None, real, record_id='APR-0002')
    assert S.check_consistency(m, None, None, real) == []


def test_round2_contradiction_detected():
    m = H.load('mutual_nda_round2_excerpt.json')
    core = H.load('mutual_nda_round2_core_excerpt.json')
    cells = _cells(m)
    problems = S.check_consistency(m, core, None, cells)
    assert any('presentation_label' in p for p in problems)
    assert any('playbook_status' in p for p in problems)
    m2 = _close_all(copy.deepcopy(m))
    S.stamp(m2, None, None, cells)
    assert 'presentation_label' not in m2
    assert m2['status_label'] == 'מדיניות מאושרת, 14.10.2026'
