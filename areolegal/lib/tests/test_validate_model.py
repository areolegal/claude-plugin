# -*- coding: utf-8 -*-
"""בדיקות ל-playbook/validate_model.py: מאמת תוכן כללי (הערות 5.4 ו-5.5, החלטה 22).

הקטעים של הסכם הסודיות ההדדי (סבב 2 וסבב 3) הם בדיקות רגרסיה בלבד. הכלליות נבדקת גם על שלוש משפחות
אחרות, ב-tests/test_generic_families.py."""
import pytest

import pb_helpers as H
from playbook import validate_model as V

GAP_TEXT = 'הספק רשאי לסיים את ההסכם בשל הפרה של חובת התשלום.'


def _rule(m, rid):
    return [r for r in m['rules'] if r['rule_id'] == rid][0]


def test_good_model_has_no_errors():
    f = V.validate(H.good_model())
    assert V.errors(f) == [], f


def test_round2_excerpt_regression():
    m = H.load('mutual_nda_round2_excerpt.json')
    core = H.load('mutual_nda_round2_core_excerpt.json')
    c = V.codes(V.validate(m, core), 'error')
    for code in ('WALKAWAY_ALL', 'HOLD_GREEN_ALL', 'LABEL_DUAL_FIELD', 'ROLE_EFFECT_MISSING', 'PRODUCED_WITH'):
        assert code in c, code


def test_round3_excerpt_regression():
    """הפלייבוק ההדדי של סבב 3, כפי שנבנה: הפגמים הכלליים נתפסים בקוד שלהם."""
    c = V.codes(V.validate(H.round3_model()), 'error')
    for code in ('MARKET_COUNT_MISMATCH', 'UNVERIFIED_LABEL_FORMAT', 'APPROVER_FIELD', 'LABEL_DUAL_FIELD'):
        assert code in c, code


@pytest.mark.parametrize('track', ['green', 'yellow'])
def test_wording_gate_runs_on_every_wording(track):
    m = H.good_model()
    t = _rule(m, 'R-07')['traffic_light'][track]
    if track == 'yellow':
        t['fallback_wording']['text'] = GAP_TEXT
    else:
        t['proposed_clause']['he'] = GAP_TEXT
    hits = [x for x in V.validate(m) if x['code'] == 'WORDING_GAP']
    assert hits and hits[0]['rule_id'] == 'R-07' and hits[0]['track'] == track
    assert hits[0]['gap_code'] == 'GAP_DISPUTE_CARVEOUT'


def test_every_rule_walk_away_flagged():
    m = H.good_model()
    for r in m['rules']:
        r['walk_away'] = True
    c = V.codes(V.validate(m), 'error')
    assert {'WALKAWAY_ALL', 'WALKAWAY_NOT_CRITICAL', 'WALKAWAY_NO_SOURCE'} <= c


def test_walk_away_needs_critical_importance_and_a_source():
    m = H.good_model()
    r22 = _rule(m, 'R-22')
    assert r22['walk_away'] and r22['walk_away_source'] == 'client_answer'
    r22.pop('walk_away_source')
    assert 'WALKAWAY_NO_SOURCE' in V.codes(V.validate(m), 'error')
    r22['walk_away_source'] = 'statute'
    r22['importance'] = 'high'
    assert 'WALKAWAY_NOT_CRITICAL' in V.codes(V.validate(m), 'error')


def test_every_rule_hold_green_flagged():
    m = H.good_model()
    for r in m['rules']:
        r['round1_posture'] = 'hold_green'
    c = V.codes(V.validate(m), 'error')
    assert 'HOLD_GREEN_ALL' in c
    assert 'HOLD_GREEN_LOW' in c


def test_role_effects_follow_the_roles_the_playbook_declares():
    m = H.good_model()
    _rule(m, 'R-07')['traffic_light']['yellow'].pop('as_recipient_effect')
    hits = [x for x in V.validate(m) if x['code'] == 'ROLE_EFFECT_MISSING']
    assert hits and hits[0]['rule_id'] == 'R-07' and 'recipient' in hits[0]['message']


def test_single_label_field():
    m = H.good_model()
    assert 'presentation_label' not in m
    m['presentation_label'] = m['status_label']
    assert 'LABEL_DUAL_FIELD' in V.codes(V.validate(m), 'error')
    m.pop('presentation_label')
    m['status_label'] = 'פלייבוק מוצע, מבוסס הסכמים ומחקר שוק, טעון אישור'
    hits = [x for x in V.validate(m) if x['code'] == 'LABEL_MISMATCH']
    assert hits and 'market_built' in hits[0]['message']


def test_no_approval_chain_fields():
    m = H.good_model()
    _rule(m, 'R-15')['approval_required'] = 'היועץ המשפטי הראשי וגם מנכ"ל החברה'
    m['authority'] = {'escalation': 'מנכ"ל'}
    hits = [x for x in V.validate(m) if x['code'] == 'APPROVER_FIELD']
    assert len(hits) == 2


def test_market_counts_must_match_everywhere():
    m = H.good_model()
    m['market_research']['disclosure']['fixed_sentence'] = 'הפלייבוק נבנה כולו לפי 11 הסכמים שפורסמו ברשת, מ-11 גופים.'
    m['handoff']['counted_sources'] = 11
    hits = [x for x in V.validate(m) if x['code'] == 'MARKET_COUNT_MISMATCH']
    assert len(hits) == 3


def test_unverified_label_format():
    m = H.good_model()
    m['market_research']['unverified_findings'].append(
        {'rule_id': 'R-07', 'level': 1, 'source_ids': ['W4'], 'sources_found': 1, 'label': 'ממצא לא מאומת, 1 מקורות',
         'reason': 'x'})
    assert 'UNVERIFIED_LABEL_FORMAT' in V.codes(V.validate(m), 'error')


def test_market_sample_purpose_per_family():
    m = H.good_model()
    mr = m['market_research']
    mr['question'] = {'engagement_purpose': 'business'}
    for s in mr['source_refs']:
        s['engagement_purpose'] = 'other'
    assert 'MARKET_SAMPLE_PURPOSE' in V.codes(V.validate(m), 'error')
    mr['source_refs'][0]['engagement_purpose'] = 'business'
    c = V.codes(V.validate(m))
    assert 'MARKET_SAMPLE_PURPOSE' in V.codes(V.validate(m), 'warning') and 'MARKET_SAMPLE_PURPOSE' not in \
        V.codes(V.validate(m), 'error') and c


def test_no_local_source_needs_a_note():
    m = H.good_model()
    m['market_research'].pop('jurisdiction_note')
    assert 'MARKET_NO_LOCAL_SOURCE' in V.codes(V.validate(m), 'error')


def test_statutory_override_on_outdated_version():
    m = H.good_model()
    _rule(m, 'R-22')['statutory_override'][0]['fact_id'] = 'LF4'
    assert 'LEGAL_FACT_STALE' in V.codes(V.validate(m), 'error')


def test_legal_fact_without_currency_check():
    m = H.good_model()
    m['regulatory_research']['facts'][0].pop('currency_check')
    assert 'LEGAL_FACT_SOURCE' in V.codes(V.validate(m), 'error')


def test_forbidden_two_source_label():
    m = H.good_model()
    m['rules'][0]['traffic_light']['green']['label'] = 'אומת בשני מקורות בלבד'
    assert 'FORBIDDEN_LABEL' in V.codes(V.validate(m), 'error')


def test_yellow_equal_to_green():
    m = H.good_model()
    r = m['rules'][0]
    r['traffic_light']['yellow']['position'] = r['traffic_light']['green']['position']
    assert 'YELLOW_EQUALS_GREEN' in V.codes(V.validate(m), 'error')
