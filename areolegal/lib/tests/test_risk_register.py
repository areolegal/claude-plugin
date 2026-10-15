# -*- coding: utf-8 -*-
"""בדיקות ל-risk/validate_register.py, על שני המרשמים של סבב 2 (C1ב ו-C2) כ-fixtures שחייבים לעבור,
ועל שינויים קטנים בהם שחייבים להיכשל (כללי הערות מעריך הסיכונים 3.5)."""
import copy
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from risk.validate_register import (clause_ref_ok, deliberate_waivers, main, profile_status, validate,  # noqa: E402
                                    validate_entity_report)

FX = ROOT / 'tests' / 'fixtures' / 'risk'


def load(name):
    return json.loads((FX / name).read_text(encoding='utf-8'))


def errs(reg, **kw):
    E, _ = validate(reg, **kw)
    return E


# ---------- fixtures from round 2 pass ----------
def test_c1b_register_passes_with_corpus():
    assert errs(load('c1b_register.json'), corpus=load('c1b_corpus.json')) == []


def test_c2_register_passes_with_corpus():
    assert errs(load('c2_register.json'), corpus=load('c2_corpus.json')) == []


def test_cli_exit_codes(tmp_path, capsys):
    good = FX / 'c1b_register.json'
    assert main([str(good), '--corpus', str(FX / 'c1b_corpus.json')]) == 0
    reg = load('c1b_register.json')
    reg['risks'][0]['category'] = 'legal'
    bad = tmp_path / 'bad.json'
    bad.write_text(json.dumps(reg, ensure_ascii=False), encoding='utf-8')
    assert main([str(bad)]) == 1


# ---------- quotes ----------
def test_quote_not_found_fails():
    reg = load('c1b_register.json')
    reg['risks'][0]['anchors'][0]['quote'] = 'נוסח שאינו מופיע בהסכם בכלל'
    assert any('הציטוט לא נמצא' in e for e in errs(reg, corpus=load('c1b_corpus.json')))


# ---------- page budget: cell limits and clause references ----------
def test_cell_limit_fails_long_risk_name():
    reg = load('c1b_register.json')
    reg['risks'][1]['name'] = 'סיום ' * 15
    assert any('ארוך מ-70' in e for e in errs(reg))


def test_cell_limit_fails_long_pre_send_gap():
    reg = load('c1b_register.json')
    reg['pre_send_fixes'][0]['gap'] = 'א' * 81
    assert any('pre_send 0.gap' in e for e in errs(reg))


def test_clause_ref_format():
    ok = ['סעיף 7.2(א)', 'תמורה 1', 'היקף הייעוץ, סעיף 1', 'סודיות וסיום, סעיף 1ב', '6, 9', 'פתיח',
          'פתיח, חתימות', 'בלוק החתימות', 'נספח ב', 'חדש אחרי סעיף 5', 'סודיות וסיום 3; תמורה 2', 'היקף 1, 3, 5']
    bad = ['', 'הסעיף שעוסק בתשלום ובקיזוז ובכל מה שקשור אליו', 'פסקה 5 בטיוטה שהתקבלה מהצד השני והתגובה',
           '"ציטוט מההסכם"']
    for s in ok:
        assert clause_ref_ok(s), s
    for s in bad:
        assert not clause_ref_ok(s), s


def test_bad_clause_ref_in_register_fails():
    reg = load('c2_register.json')
    reg['pre_send_fixes'][0]['where'] = 'בסעיף שעוסק בסודיות המגעים ובתנאים'
    assert any('where שלא בתבנית' in e for e in errs(reg))


# ---------- deliberate waivers and numbering from the negotiation state ----------
def _c2_with_state_ids(reg):
    ids = ['E-028', 'E-004', 'D07', 'D12', 'D13', 'D01']
    for p, sc in zip(reg['pre_send_fixes'], ids):
        p['clause_ref'] = sc   # 3.6: clause_ref (מזהה סעיף מ-numbering_map) במקום state_clause_id
    return reg


def test_waivers_read_from_state():
    w = deliberate_waivers(load('c2_state_min.json'))
    assert 'E-028' in w and 'E-004' in w


def test_pre_send_row_from_deliberate_waiver_fails():
    reg = _c2_with_state_ids(load('c2_register.json'))
    E = errs(reg, state=load('c2_state_min.json'))
    assert any('pre_send 0' in e and 'ויתור מכוון' in e for e in E)
    assert any('pre_send 1' in e and 'ויתור מכוון' in e for e in E)
    assert not any('pre_send 2' in e for e in E)


def test_waiver_as_accepted_risk_passes():
    reg = _c2_with_state_ids(load('c2_register.json'))
    reg['pre_send_fixes'] = reg['pre_send_fixes'][2:]
    for rid, sc in (('RSK-001', 'E-028'), ('RSK-002', 'E-004')):
        r = next(x for x in reg['risks'] if x['id'] == rid)
        r['decision'] = {'status': 'accepted', 'basis': 'deliberate_waiver', 'state_clause_id': sc, 'note': '',
                         'decided_at': None}
    assert errs(reg, corpus=load('c2_corpus.json'), state=load('c2_state_min.json')) == []


def test_accepted_risk_cannot_stay_in_pre_send():
    reg = load('c2_register.json')
    reg['risks'][0]['decision'] = {'status': 'accepted', 'basis': 'deliberate_waiver'}
    assert any('סיכון שהתקבל בוויתור מכוון' in e for e in errs(reg))


def test_clause_ref_required_in_pre_send():
    reg = load('c2_register.json')
    del reg['pre_send_fixes'][2]['clause_ref']
    assert any('pre_send 2' in e and 'חסר clause_ref' in e for e in errs(reg, state=load('c2_state_min.json')))
    assert any('pre_send 2' in e and 'חסר clause_ref' in e for e in errs(reg))


# ---------- mutual agreement ----------
def test_mutual_requires_side():
    reg = load('c2_register.json')
    reg['risks'][3]['side'] = None
    assert any('side חובה' in e for e in errs(reg))


# ---------- playbook status from one source ----------
def test_benchmark_status_must_follow_derived_status():
    reg = load('c2_register.json')  # benchmark_status: approved
    assert any('benchmark_status' in e for e in errs(reg, playbook_status={'playbook_status': 'Draft'}))
    assert not any('benchmark_status' in e for e in errs(reg, playbook_status={'playbook_status': 'Approved'}))


# ---------- facts the profile decides are not assumptions (generic: keyed to the profile, not to a statute) ----------
def test_profile_status_is_generic():
    ps = profile_status(load('profile_min.json'))
    assert 'רשות ניירות ערך' in ps['confirmed_regulators'] and ps['listed'] is True
    assert 'רשות התחרות' not in ps['confirmed_regulators']   # Potential, לא Confirmed


def test_assumption_on_a_fact_the_profile_decides_fails():
    reg = load('c1b_register.json')
    reg['summary']['assumptions'].append('החברה מפוקחת בידי רשות ניירות ערך (לאישור עורך הדין).')
    assert any('הפרופיל קובע' in e for e in errs(reg, profile=load('profile_min.json')))
    assert not any('הפרופיל קובע' in e for e in errs(reg))


# ---------- currency of statutes ----------
def _with_old_regulations(label, why):
    reg = load('c1b_register.json')
    reg['research']['sources_checked'].append({
        'id': 'SRC-009', 'source': 'נבו, נוסח חקיקה: תקנות הגנת הפרטיות (אבטחת מידע)',
        'url': 'https://www.nevo.co.il/law_html/law00/144811.htm', 'subject': 'הסכם עם גורם חיצוני',
        'taken': 'מה ההסכם עם גורם חיצוני צריך לקבוע', 'date': '2026-10-14', 'version_date': '2023-09-18',
        'finding': '', 'excerpt': 'x'})
    reg['research']['confidence'].append({'source_id': 'SRC-009', 'label': label, 'why': why})
    return reg


# רשימת התיקונים הידועים היא נתון (מהכללים המשותפים או מההרצה), לא קבוע בקוד (החלטה 22)
AMEND = [{'match': 'הגנת הפרטיות', 'name': 'תיקון 13 לחוק הגנת הפרטיות', 'in_force': '2025-08-14'}]


def test_version_before_amendment_13_cannot_be_high_confidence():
    reg = _with_old_regulations('high', '')
    assert any('תיקון 13' in e for e in errs(reg, known_amendments=AMEND))
    assert not any('תיקון 13' in e for e in errs(reg))   # בלי נתון, אין כלל קבוע


def test_version_before_amendment_13_with_medium_and_reason_passes():
    reg = _with_old_regulations('medium', 'נוסח נכון ל-18.09.2023, קודם לתיקון 13 לחוק הגנת הפרטיות')
    assert not any('תיקון 13' in e for e in errs(reg, known_amendments=AMEND))


# ---------- tokens in URLs ----------
def test_token_in_research_url_fails():
    reg = load('c1b_register.json')
    reg['research']['raw_copies'][0]['final_url'] += '?X-Amz-Security-Token=abc&X-Amz-Signature=def'
    assert any('טוקן' in e for e in errs(reg))


# ---------- entity report ----------
def _entity(**over):
    rep = {
        'meta': {'counterparty': {'name': 'Example Corp LLC', 'country': 'US'}},
        'confidence': [{'source_no': 1, 'label': 'high', 'why': 'המרשם עצמו, הקובץ מהיום'}],
        'red_flags': [],
        'sources': [{'no': 1, 'source': 'OFAC', 'url': 'https://sanctionslist.ofac.treas.gov/SDN.CSV'}],
        'raw_copies': [{'final_url': 'https://sanctionslist.ofac.treas.gov/SDN.CSV', 'stored': 'match_window',
                        'full_size_bytes': 5_000_000}],
        'lookups': [{'source': 'Delaware Division of Corporations', 'url': 'https://icis.corp.delaware.gov/',
                     'result': 'blocked'}],
        'not_checked': [{'item': 'זהות ומעמד במרשם Delaware Division of Corporations', 'why': 'נחסם (CAPTCHA)',
                         'task': 'עורך הדין'}],
    }
    rep.update(over)
    return rep


def test_entity_report_clean_passes():
    assert validate_entity_report(_entity()) == []


def test_entity_report_defects_from_round2_fail():
    rep = _entity(
        confidence=[{'source_no': 1, 'label': 'high', 'why': ''}],
        red_flags=[{'summary': 'לא נמצא רישום בשם זה במאגר רשם החברות בישראל', 'blocking': False, 'match_on': 'none'},
                   {'summary': 'כינוי חלקי של אדם', 'blocking': True, 'match_on': 'near'}],
        raw_copies=[{'final_url': 'https://x.s3.amazonaws.com/sdn.csv?X-Amz-Security-Token=zz', 'stored': 'page',
                     'full_size_bytes': 50_000_000}],
        not_checked=[])
    E = validate_entity_report(rep)
    assert any('why חובה' in e for e in E)
    assert any('ישות זרה' in e for e in E)
    assert any('קרובה אינה חוסמת' in e for e in E)
    assert any('טוקן' in e for e in E)
    assert any('קובץ מלא גדול' in e for e in E)
    assert any('משימה לעורך הדין' in e for e in E)


def test_entity_report_bypass_is_rejected():
    rep = _entity(lookups=[{'source': 'SEC EDGAR', 'url': 'https://www.sec.gov/', 'result': 'found',
                            'note': 'captcha solver used'}])
    assert any('עקיפה' in e for e in validate_entity_report(rep))


# ---------- negotiation state per negotiation notes 4.8: deliberate_concessions, numbering_map, text_status ----------
def _state48():
    return {
        'text_status': 'our_unsent_response',
        'deliberate_concessions': [
            {'topic': 'סודיות קיום המגעים', 'clause_ref': 'E-028', 'reason': 'תגובה ממוקדת', 'report_as': 'accepted_risk'},
            {'topic': 'צמצום המטרה', 'clause_ref': 'E-004', 'reason': 'תגובה ממוקדת', 'report_as': 'accepted_risk'}],
        'numbering_map': {'E-028': 'סעיף 2', 'E-004': 'הפתיח', 'D07': 'סעיף 6', 'D12': 'סעיפים 6 ו-9',
                          'D13': 'סעיפים 6 ו-10', 'D01': 'הפתיח ובלוק החתימות'},
        'deal_context': {'proportionality': {'user_choice': 'focused_response'}},
    }


def test_state48_deliberate_concessions_are_read():
    w = deliberate_waivers(_state48())
    assert set(w) == {'E-028', 'E-004'}
    other = _state48()
    other['deliberate_concessions'][0]['report_as'] = 'note_only'
    assert set(deliberate_waivers(other)) == {'E-004'}


def test_state48_waiver_rows_fail_and_accepted_risk_passes():
    reg = _c2_with_state_ids(load('c2_register.json'))
    E = errs(reg, state=_state48())
    assert sum('ויתור מכוון' in e for e in E) == 2
    reg['pre_send_fixes'] = reg['pre_send_fixes'][2:]
    for rid, sc in (('RSK-001', 'E-028'), ('RSK-002', 'E-004')):
        r = next(x for x in reg['risks'] if x['id'] == rid)
        r['decision'] = {'status': 'accepted', 'basis': 'deliberate_waiver', 'state_clause_id': sc}
    assert errs(reg, corpus=load('c2_corpus.json'), state=_state48()) == []


def test_state48_numbering_map_mismatch_fails():
    reg = _c2_with_state_ids(load('c2_register.json'))
    reg['pre_send_fixes'] = reg['pre_send_fixes'][2:]
    reg['pre_send_fixes'][0]['where'] = 'סעיף 7'   # במספור התגובה שלנו זה סעיף 6
    assert any('numbering_map' in e for e in errs(reg, state=_state48()))


def test_state48_text_status_must_match():
    reg = load('c2_register.json')
    st = _state48()
    st['text_status'] = 'counterparty_draft'
    assert any('text_status' in e for e in errs(reg, state=st))
