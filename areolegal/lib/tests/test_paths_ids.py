# -*- coding: utf-8 -*-
"""בדיקות ל-common/paths.py ול-common/ids.py."""
import os

import pytest

import orch_helpers  # noqa: F401  מוסיף את שורש החבילה ל-sys.path
from common import ids, paths


# --------------------------------------------------------------------------------- נתיבים
def _folder_of_length(tmp_path, n):
    base = str(tmp_path)
    pad = max(1, n - len(os.path.abspath(base)) - 1)
    return os.path.join(base, 'א' * pad)


def test_short_name_and_shared_shortening(tmp_path):
    folder = str(tmp_path / 'deal')
    r = paths.safe_out_paths(folder, 'הסכם ייעוץ', 'EXAMPLECO', 1, '14.10.2026')
    assert os.path.basename(r.work) == 'הסכם ייעוץ - EXAMPLECO - סבב 1 - 14.10.2026 - פנימי.docx'
    assert os.path.basename(r.send) == 'הסכם ייעוץ - EXAMPLECO - סבב 1 - 14.10.2026.docx'
    assert os.path.basename(r.as_produced) == 'הסכם ייעוץ - EXAMPLECO - סבב 1 - 14.10.2026 - כפי שהופק.docx'
    assert r.step == 0 and r.longest <= paths.PATH_LIMIT


def test_all_three_names_shortened_together_within_230(tmp_path):
    # תיקייה ארוכה: עם שם החברה העותק "כפי שהופק" חורג, ולכן שלושת השמות מאבדים את שם החברה יחד
    folder = _folder_of_length(tmp_path, 170)
    r = paths.safe_out_paths(folder, 'הסכם שירותי ייעוץ מקצועי', 'EXAMPLECO', 1, '14.10.2026')
    assert r.step >= 1
    for p in (r.work, r.send, r.as_produced):
        assert 'EXAMPLECO' not in os.path.basename(p)
        assert len(os.path.abspath(p)) + paths.COLLISION_RESERVE <= paths.PATH_LIMIT


def test_folder_too_long_raises_with_length(tmp_path):
    folder = _folder_of_length(tmp_path, 215)
    with pytest.raises(paths.PathTooLong) as e:
        paths.safe_out_paths(folder, 'הסכם ייעוץ', 'EXAMPLECO', 1, '14.10.2026')
    assert e.value.length > paths.PATH_LIMIT


def test_unique_path_adds_number_inside_reserve(tmp_path):
    r = paths.safe_out_paths(str(tmp_path), 'הסכם ייעוץ', 'EXAMPLECO', 1, '14.10.2026')
    open(r.send, 'w').close()
    u = paths.unique_path(r.send)
    assert u.endswith(' (2).docx') and len(u) <= r.longest
    assert paths.check_write_path(u) == len(os.path.abspath(u))


def test_clean_name_strips_forbidden_characters():
    assert paths.clean_name('הסכם: "שירותים"/ייעוץ?') == 'הסכם שירותיםייעוץ'


def test_long_path_prefix():
    p = paths.long_path(r'C:\x\y.docx')
    if os.name == 'nt':
        assert p.startswith('\\\\?\\C:')
    assert paths.long_path(p) == p


# --------------------------------------------------------------------------------- מספר תאגיד
@pytest.mark.parametrize('raw,valid,reason', [
    ('511111114', True, 'ok'),
    ('51-000000-3', True, 'ok'),
    ('11111111', False, 'wrong_length'),       # 8 ספרות: הומלץ בשתי השרשראות בסבב 2
    ('510000004', False, 'bad_check_digit'),
    ('580000008', False, 'not_company'),        # קידומת 58: עמותה ולא חברה
    ('', False, 'missing'),
    ('51000000X', False, 'not_digits'),
])
def test_company_number_validation(raw, valid, reason):
    v = ids.validate_company_number(raw)
    assert v['valid'] is valid and v['reason'] == reason


def test_eight_digits_never_padded():
    assert ids.validate_company_number('011111111')['valid'] is False


def test_folder_name_is_never_a_source():
    r = ids.resolve_company_number('11111111', [], folder_names=['ExampleCo 511111114 (1)'])
    assert r['status'] == 'invalid' and r['ask'] and r['number'] is None
    assert ('folder_name', 'ExampleCo 511111114 (1)') in r['ignored']
    assert 'recommended' not in r  # המספר שבשם התיקייה אינו מוצע


def test_company_document_can_correct_the_profile():
    r = ids.resolve_company_number('11111111', [('signed_agreement', '511111114')])
    assert r['status'] == 'invalid' and r['recommended'] == '511111114' and r['ask']


def test_confirmed_and_conflict():
    assert ids.resolve_company_number('511111114', [('letterhead', '511111114')])['status'] == 'confirmed'
    r = ids.resolve_company_number('511111114', [('signed_agreement', '510000011')])
    assert r['status'] == 'conflict' and r['ask']
    assert ids.resolve_company_number(None)['status'] == 'missing'


def test_unknown_source_rejected():
    r = ids.resolve_company_number('511111114', [('email_signature', '511111114')])
    assert r['status'] == 'confirmed' and ('email_signature', '511111114') in r['ignored']


def test_person_id():
    assert ids.validate_person_id('000000018')['valid']
    assert ids.validate_person_id('18')['valid'] is False


@pytest.mark.parametrize('answer,expected', [
    ('נשלים לפני החתימה', True), ('נשלים בחתימה', True), ('יושלם לפני החתימה', True),
    ('to be completed at signing', True), ('המספר הוא 511111114', False), (None, False)])
def test_complete_at_signing_answers(answer, expected):
    assert ids.is_complete_at_signing(answer) is expected


def test_detail_for_draft():
    assert ids.detail_for_draft('company_number', value='511111114', validator=ids.validate_company_number) == \
        ('511111114', 'value')
    assert ids.detail_for_draft('company_number', value='11111111', validator=ids.validate_company_number,
                                answer='נשלים לפני החתימה') == (ids.SIGNING_BLANK, 'signing_blank')
    assert ids.detail_for_draft('address') == (None, 'open')
