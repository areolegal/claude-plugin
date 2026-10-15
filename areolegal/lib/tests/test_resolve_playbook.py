# -*- coding: utf-8 -*-
"""בדיקות ל-orchestrator/resolve_playbook.py: מסמך מדיניות ישן שמערבב משפחות ונשען על פסיקה לעולם אינו גובר על
פלייבוק, טבלת סמכויות שבו אינה נקראת (4.9, שינוי 83: אין שרשרת אישורים), ופריט אימות של דין בפלייבוק שנפסל
נשאר בתוקף."""
import io
import json
import os

import pytest

import orch_helpers as H
from docx import Document
from orchestrator import resolve_playbook as rp

FX = json.load(io.open(os.path.join(H.FIX, 'resolve', 'fixtures.json'), encoding='utf-8'))


def _json(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with io.open(path, 'w', encoding='utf-8') as fh:
        json.dump(obj, fh, ensure_ascii=False)


def _docx(path, paragraphs):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    d = Document()
    for t in paragraphs:
        d.add_paragraph(t)
    d.save(path)


def _folder(tmp_path, root=True, indexed=False, supplier=False, nda=False, mixed=True, review=True):
    folder = str(tmp_path / 'client')
    data = os.path.join(folder, 'Areo-נתונים')
    os.makedirs(data, exist_ok=True)
    if root:
        _json(os.path.join(data, 'playbook-core.json'), FX['root_single_contractor_core'])
        _json(os.path.join(data, 'playbook-model.json'), FX['root_single_contractor_model'])
    entries = []
    if indexed:
        _json(os.path.join(data, 'playbooks', 'fam_services', 'playbook-core.json'), FX['indexed_valid_core'])
        _json(os.path.join(data, 'playbooks', 'fam_services', 'playbook-model.json'), FX['indexed_valid_model'])
        entries.append({'core_path': 'playbooks/fam_services/playbook-core.json', 'family_code': 'services',
                        'company_role_code': 'service_recipient', 'language': 'he', 'last_updated': '2026-10-01'})
    if supplier:
        _json(os.path.join(data, 'playbooks', 'fam_supplier', 'playbook-core.json'), FX['supplier_side_core'])
        _json(os.path.join(data, 'playbooks', 'fam_supplier', 'playbook-model.json'), FX['supplier_side_model'])
        entries.append({'core_path': 'playbooks/fam_supplier/playbook-core.json', 'family_code': 'services',
                        'company_role_code': 'service_provider', 'language': 'he', 'last_updated': '2026-10-05'})
    if nda:
        _json(os.path.join(data, 'playbooks', 'fam_nda', 'playbook-core.json'), FX['one_way_nda_core'])
        entries.append({'core_path': 'playbooks/fam_nda/playbook-core.json', 'family_code': 'nda',
                        'company_role_code': 'disclosing', 'language': 'en', 'last_updated': '2026-10-14'})
    if entries:
        _json(os.path.join(data, 'playbooks', 'index.json'), {'playbooks': entries})
    if mixed:
        _docx(os.path.join(folder, '07 מדיניות', 'מדיניות חוזית - מקבל השירותים.docx'), FX['mixed_policy_paragraphs'])
    if review:
        _docx(os.path.join(folder, '06 דוחות', 'דוח סקירה מול מדיניות.docx'), FX['review_report_paragraphs'])
    return data, folder


def _cand(res, needle):
    return next(c for c in res['candidates'] if needle in c['path'])


def test_mixed_policy_with_case_law_never_beats_playbook(tmp_path):
    """C1ב: המסמך הישן (24.6.2026) שנגזר מכמה משפחות ומפנה לפסיקה נבחר בסבב 2. עכשיו הוא רקע בלבד, והפלייבוק
    של אותה משפחה ואותו צד נבחר, עם שאלת תנאי ההפעלה (מצב 4)."""
    data, folder = _folder(tmp_path)
    res = rp.resolve(data, folder, 'services', 'service_recipient', 'he', counterparty_kind='company')
    assert res['result'] == 'match' and res['chosen'] == 'playbook-core.json'
    assert res['activation_question'] is True
    mixed = _cand(res, 'מדיניות חוזית - מקבל השירותים')
    assert 'mixed_family_background' in mixed['excluded_because'] and not mixed['chosen']
    assert mixed['cites_case_law'] and set(mixed['derived_from']) >= {'outsourcing', 'freelance', 'employment'}
    assert [b['path'] for b in res['background_documents']] == [mixed['path']]
    assert 'not_a_policy' in _cand(res, 'דוח סקירה')['excluded_because']


def test_valid_indexed_playbook_beats_newer_or_older_background(tmp_path):
    data, folder = _folder(tmp_path, indexed=True)
    res = rp.resolve(data, folder, 'services', 'service_recipient', 'he')
    assert res['chosen'] == os.path.join('playbooks', 'fam_services', 'playbook-core.json')
    assert res['activation_question'] is False
    root = next(c for c in res['candidates'] if c['path'] == 'playbook-core.json')
    assert 'activation_mismatch' in root['excluded_because'] and root['chosen'] is False
    assert 'mixed_family_background' in _cand(res, 'מדיניות חוזית')['excluded_because']


def test_only_background_document_gives_no_match(tmp_path):
    data, folder = _folder(tmp_path, root=False)
    res = rp.resolve(data, folder, 'services', 'service_recipient', 'he')
    assert res['result'] == 'no_match' and res['chosen'] == ''
    assert res['background_documents'] and 'רקע בלבד' in res['reason']
    assert rp.source_label(res).startswith('ממסמך מדיניות שמעמדו לא נבדק')


def test_no_approval_chain_from_policy_document(tmp_path):
    """החלטת מוצר 1 (14.10.2026): אין טבלת סמכויות ואין מאשר נדרש, גם כשמסמך המדיניות כולל טבלה כזו."""
    data, folder = _folder(tmp_path)
    res = rp.resolve(data, folder, 'services', 'service_recipient', 'he')
    assert 'authority_table' not in res
    assert not hasattr(rp, 'required_approver') and not hasattr(rp, 'extract_authority_table')
    assert 'מאשר' not in __import__('json').dumps(res, ensure_ascii=False)


def test_activation_mismatch_label_needs_explicit_answer(tmp_path):
    """C1 בסבב 3: פלייבוק של קבלן יחיד הוחל על חברה בתשובה כללית, ותויג "מהפלייבוק"."""
    data, folder = _folder(tmp_path)
    res = rp.resolve(data, folder, 'services', 'service_recipient', 'he', counterparty_kind='company')
    assert res['activation_question']
    assert rp.source_label(res, 'delegated') == 'שיקול מקצועי, בהשראת פלייבוק של סוג אחר'
    assert rp.source_label(res, 'explicit') == 'מהפלייבוק'


def test_law_item_of_rejected_playbook_is_carried(tmp_path):
    data, folder = _folder(tmp_path, indexed=True, supplier=True)
    res = rp.resolve(data, folder, 'services', 'service_recipient', 'he')
    sup = _cand(res, 'fam_supplier')
    assert 'opposite_side' in sup['excluded_because']
    carried = {(x['from'], x['id']) for x in res['law_items_carried']}
    assert (sup['path'], 'QS1') in carried
    assert any(x['id'] == 'Q1' for x in res['law_items_carried'])  # גם מהפלייבוק שבשורש, שלא נבחר


def test_mutual_agreement_never_gets_one_way_playbook(tmp_path):
    data, folder = _folder(tmp_path, root=False, nda=True, mixed=False, review=False)
    res = rp.resolve(data, folder, 'nda', 'mutual', 'he', agreement_family_label='הסכם סודיות הדדי')
    nda = _cand(res, 'fam_nda')
    assert {'mutuality_mismatch', 'not_covered'} <= set(nda['excluded_because'])
    assert res['result'] == 'no_match'


def test_playbook_built_with_older_version_warns(tmp_path):
    data, folder = _folder(tmp_path, mixed=False, review=False)
    res = rp.resolve(data, folder, 'services', 'service_recipient', 'he', min_skill_version='5.4')
    assert 'built_with_older_version' in res['warnings']


@pytest.mark.parametrize('text,expected', [
    ('המסמך נבנה על בסיס נספח מיקור חוץ, הסכם לקבלן עצמאי והסכם עבודה.', True),
    ('המסמך נבנה על בסיס הסכמי השירותים של החברה.', False),
])
def test_mixed_family_detection(text, expected):
    assert rp.classify_document(text)['mixed_family'] is expected


def test_activation_conditions_object_form_does_not_crash():
    # Round 3: a builder model wrote activation_conditions as objects; ' '.join crashed with TypeError.
    model = {'rules': [
        {'activation_conditions': [{'condition': 'הצד שכנגד הוא קבלן עצמאי יחיד', 'deciding_question': 'האם הספק יחיד?'}]},
        {'activation_conditions': ['חל על כל ספק']},
        {'activation_conditions': 'הצד שכנגד יחיד'},
        {'activation_conditions': None},
    ]}
    assert rp._activation_share(model, 'company') == 0.5
    assert rp._activation_share(model, 'individual') == 0.0
