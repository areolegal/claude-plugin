# -*- coding: utf-8 -*-
"""הכלליות של מעריך הסיכונים (החלטה 22, כלל 2.26): אותם מנגנונים על שלוש משפחות הסכמים נוספות, ולא רק על
הסכמי הייעוץ והסודיות של סבב 2 ו-3 (שנשארים כבדיקות רגרסיה בלבד):
- רישיון שימוש בשירות ענן, טיוטה של הצד השני;
- הסכם אספקה, התגובה שלנו שטרם נשלחה, עם הוספה במעקב שינויים, ויתור מכוון ושורת "לתיקון";
- הסכם שכירות מוסכם, מול אדם פרטי.
ולחקר ישות: חברה ישראלית, חברה זרה, אדם ושותפות. הקבצים סינתטיים (tests/fixtures/risk/families)."""
import copy
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from risk.entity_store import match_name, normalize_name, scan_rows  # noqa: E402
from risk.extract_corpus import extract  # noqa: E402
from risk.render_check import band_text_from_register, build_report, find_browser, run_check  # noqa: E402
from risk.validate_register import validate, validate_entity_report  # noqa: E402

FX = ROOT / 'tests' / 'fixtures' / 'risk' / 'families'
TPL = (ROOT / 'tests' / 'fixtures' / 'risk' / 'risk-report-template.html').read_text(encoding='utf-8')
FAMILIES = [('saas', 'saas_licence_draft.docx', None), ('supply', 'supply_response.docx', 'supply_state.json'),
            ('lease', 'lease_agreed.docx', None)]
BROWSER = find_browser()


def load(name):
    return json.loads((FX / name).read_text(encoding='utf-8'))


@pytest.mark.parametrize('fam,docx,state', FAMILIES)
def test_extract_and_validate_every_family(fam, docx, state):
    corpus = [extract(str(FX / docx))]
    assert corpus[0]['parts']['word/document.xml']
    st = load(state) if state else None
    E, W = validate(load('%s_register.json' % fam), corpus, state=st)
    assert E == [], E


def test_tracked_insertion_in_supply_response_is_seen_and_reject_all_is_clean():
    d = extract(str(FX / 'supply_response.docx'))
    assert d['tracked']['ins'] == 1
    changed = [p for p in d['parts']['word/document.xml'] if p.get('changed')]
    assert len(changed) == 1 and 'איחור' in changed[0]['text_accept_all'] and 'איחור' not in changed[0]['text_reject_all']


@pytest.mark.parametrize('fam,docx,state', FAMILIES)
def test_quote_not_in_document_fails_in_every_family(fam, docx, state):
    reg = load('%s_register.json' % fam)
    reg['risks'][0]['anchors'][0]['quote'] = 'נוסח שאינו מופיע בהסכם הזה בכלל'
    E, _ = validate(reg, [extract(str(FX / docx))])
    assert any('הציטוט לא נמצא' in e for e in E)


def test_supply_concession_and_pre_send_contract():
    reg, st = load('supply_register.json'), load('supply_state.json')
    corpus = [extract(str(FX / 'supply_response.docx'))]
    # הוויתור על ההצמדה (S02) חייב להופיע כסיכון שהתקבל
    bad = copy.deepcopy(reg)
    for r in bad['risks']:
        if r['decision'].get('basis') == 'deliberate_waiver':
            r['decision'] = {'status': 'open', 'basis': None, 'state_clause_id': None, 'note': '', 'decided_at': None}
    assert any('S02' in e and 'אינו מופיע כסיכון שהתקבל' in e for e in validate(bad, corpus, state=st)[0])
    # שורת "לתיקון" עם מזהה כלל במקום מזהה סעיף
    bad = copy.deepcopy(reg)
    bad['pre_send_fixes'][0]['clause_ref'] = 'R-04'
    assert any('מזהה כלל' in e for e in validate(bad, corpus, state=st)[0])
    # בלי שרשרת אישורים
    bad = copy.deepcopy(reg)
    bad['risks'][-1]['decision']['note'] = 'ממתין לאישור מנכ"ל'
    assert any('שרשרת אישורים' in e for e in validate(bad, corpus, state=st)[0])


@pytest.mark.skipif(not BROWSER, reason='אין Chrome או Edge')
@pytest.mark.parametrize('fam', ['saas', 'supply', 'lease'])
def test_render_every_family(tmp_path, fam):
    reg = load('%s_register.json' % fam)
    page = tmp_path / 'report.html'
    page.write_text(build_report(TPL, reg), encoding='utf-8')
    res = run_check(str(page), str(tmp_path / 'out'), band_text_from_register(reg), browser=BROWSER)
    assert res['verdict'] == 'PASS', res.get('fails')
    assert res['external_requests'] == [] and res['overlaps'] == [] and res['body_pages'] <= 8


# ---------------------------------------------------------------- entity research for any counterparty
@pytest.mark.parametrize('query,record,qtype,rtype,expect', [
    ('חברה לדוגמה בע"מ', 'חברה לדוגמה', 'entity', 'entity', 'exact'),                 # חברה ישראלית
    ('Example Holdings GmbH', 'EXAMPLE HOLDINGS', 'entity', 'entity', 'exact'),          # חברה זרה
    ('Example Partners LP', 'Example Partners', 'entity', 'entity', 'exact'),            # שותפות זרה
    ('שותפים לדוגמה שותפות מוגבלת', 'שותפים לדוגמה', 'entity', 'entity', 'exact'),     # שותפות ישראלית
    ('משה כהן', 'משה כהן', 'individual', 'individual', 'exact'),                         # אדם
    ('משה כהן', 'משה כהן', 'individual', 'entity', 'near'),                              # אדם מול תאגיד: לא התאמה
])
def test_match_name_for_any_counterparty(query, record, qtype, rtype, expect):
    assert match_name(query, record, query_type=qtype, record_type=rtype)[0] == expect


def test_entity_report_for_individual_and_israeli_company_validates():
    for cp in ({'name': 'משה כהן', 'country': 'IL', 'type': 'individual'},
               {'name': 'חברה לדוגמה בע"מ', 'country': 'IL', 'registration_no': '510000000'},
               {'name': 'Example Partners LP', 'country': 'US', 'type': 'partnership'}):
        rep = {'meta': {'counterparty': cp}, 'confidence': [{'source_no': 1, 'label': 'high', 'why': 'המרשם עצמו'}],
               'red_flags': [], 'sources': [{'no': 1, 'source': 'רשם', 'url': 'https://www.gov.il/x'}],
               'raw_copies': [], 'lookups': [], 'not_checked': []}
        assert validate_entity_report(rep) == [], cp
